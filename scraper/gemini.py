"""Gemini 번역 도우미 (Google AI Studio 무료 키로 동작)

환경 변수
  GEMINI_API_KEY   필수. 없으면 available() 이 False → 호출하는 쪽은 번역을 건너뜀
  GEMINI_MODEL     선택. 비우면 사용 가능한 최신 flash 모델을 자동으로 고름 (막힌 모델이면 다음 모델로 교체)

translate_map({"키": "원문", ...}, glossary={"Agumon": "아구몬"}) → {"키": "한국어"}
  - 여러 문장을 한 번에 JSON으로 주고받아 요청 수를 줄임 (무료 등급은 분당·일일 요청 수 제한이 있음)
  - 한 번 호출에 쓰는 시간은 max_seconds(기본 CALL_BUDGET)를 넘지 않음
  - 예외
      QuotaExceeded  모든 후보 모델이 일일 한도 → 지금까지 결과를 저장하고 멈추면 다음 실행 때 이어서 진행
      Busy           혼잡·응답 없음으로 재시도/시간 한도 초과 → 잠시 후 다시 시도하면 됨
      BadResponse    이 묶음 자체가 번역 불가(안전 차단, 해석 불가 응답, 잘못된 요청) → 같은 요청을 반복해도 소용없음.
                     이 묶음만 건너뛰면 됨 (RuntimeError 하위 클래스)
      AuthError      키가 잘못됐거나 권한 없음 → 전체 중단 (RuntimeError 하위 클래스)
"""
import json
import os
import re
import time

import requests

API = "https://generativelanguage.googleapis.com/v1beta"
MIN_INTERVAL = 6.5     # 무료 등급 분당 요청 제한(약 10회)에 맞춘 간격(초)
MAX_RETRIES = 6        # translate_map 한 번의 최대 요청 횟수
CALL_BUDGET = 600      # translate_map 한 번에 쓰는 최대 시간(초) — 최악의 경우에도 이 시간 안에 끝남
REQUEST_TIMEOUT = 180  # 요청 하나의 최대 대기(초)
MAX_SLEEP = 60         # 분당 한도·혼잡 때 한 번에 쉬는 최대 시간(초)

_last_call = 0.0


class QuotaExceeded(Exception):
    """일일 한도 — 오늘은 더 진행 불가"""


class Busy(Exception):
    """모든 모델이 혼잡하거나 응답 없음 — 잠시 후 다시 시도하면 됨"""


class BadResponse(RuntimeError):
    """이 요청(묶음) 자체를 처리할 수 없음 — 안전 차단, 해석 불가 응답, 잘못된 요청(HTTP 400 등)"""


class AuthError(RuntimeError):
    """API 키가 잘못됐거나 권한 없음 — 다른 묶음도 모두 실패하므로 중단"""


def available():
    return bool(os.environ.get("GEMINI_API_KEY"))


def _headers():
    return {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}


def _list_flash_models():
    """generateContent 를 지원하는 flash 모델, 최신 버전부터"""
    r = requests.get(f"{API}/models", headers=_headers(), params={"pageSize": 200}, timeout=30)
    r.raise_for_status()
    names = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    ver = lambda n: [int(x) for x in re.findall(r"\d+", n)]
    flash = sorted([n for n in names if re.fullmatch(r"gemini-[\d.]+-flash", n)], key=ver, reverse=True)
    lite = sorted([n for n in names if re.fullmatch(r"gemini-[\d.]+-flash-lite", n)], key=ver, reverse=True)
    return flash + lite  # 혼잡(503)·제한(404) 때 다음 후보로 넘어감


_models = None
_exhausted = set()  # 이번 실행에서 일일 한도에 걸렸거나 쓸 수 없는 모델 (무료 한도는 모델별로 따로 셈)


def _candidates():
    """GEMINI_MODEL(있으면) → 최신 flash → … → flash-lite 순서"""
    global _models
    if _models is None:
        try:
            listed = _list_flash_models()
        except Exception as e:
            raise RuntimeError(f"모델 목록 조회 실패: {e}")
        wanted = os.environ.get("GEMINI_MODEL")
        _models = ([wanted] if wanted else []) + [m for m in listed if m != wanted]
        print(f"  [gemini] 후보 모델: {', '.join(_models)}")
    return [m for m in _models if m not in _exhausted]


TERMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "translations", "terms.json")
_terms = None


def load_terms():
    """고정 용어집 (data/translations/terms.json, '_'로 시작하는 키는 메모). 실행 중 한 번만 읽음"""
    global _terms
    if _terms is None:
        try:
            with open(TERMS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            _terms = {k: v for k, v in data.items() if not k.startswith("_")} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _terms = {}
    return dict(_terms)


PROMPT = """너는 디지몬 공식 도감 번역가다. 아래 JSON의 각 값을 한국어로 번역해라. 원작 고증이 최우선이다.
출력: 같은 키를 그대로 쓰고 값만 한국어 번역으로 바꾼 JSON 객체 하나만 출력한다.

고증 규칙
1. 디지몬 이름과 세계관 용어는 아래 용어집 표기를 반드시 그대로 쓴다. 용어집에 없는 디지몬 이름은 뜻을 풀어 의역하지 말고 일본 원작 이름을 한글로 옮긴다(공식 도감 방식).
2. 진화 단계·속성은 용어집 표기만 쓴다(예: Ultimate는 '궁극체', Perfect는 '완전체', Vaccine은 '백신종'). 영어 더빙식 단계명으로 해석하지 않는다.
3. 필살기 이름은 일본 원작 기술명을 확실히 아는 경우에만 그 한글 표기(예: Pepper Breath → 베이비 플레임)를 쓰고, 확실하지 않으면 영어 기술명을 그대로 한글 음역한다. 기술명을 지어내지 않는다.
4. 원문에 없는 설정·정보를 덧붙이거나 빼지 않는다. 모호한 부분은 원문 그대로의 의미로 옮긴다.
5. 인물(사람) 이름은 일본 원작 이름을 한글로 쓰고, 용어집에 '원작 이름(더빙 이름)' 형태가 있으면 그 표기를 그대로 쓴다.
6. 문체: 도감 설명은 '~이다/~한다'체 평서문. 상품명·작품명은 한국 정발명이 있으면 그것을, 없으면 원문을 자연스럽게 옮기고 가격·날짜·숫자는 그대로 둔다.
{glossary}
번역할 JSON:
{payload}"""

# 이 값이면 같은 요청을 다시 보내도 결과가 같음 → 바로 BadResponse
_BLOCK_FINISH = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


def _sleep(seconds, deadline):
    """deadline 을 넘지 않는 만큼만 쉼"""
    seconds = min(seconds, deadline - time.time())
    if seconds > 0:
        time.sleep(seconds)


def _quota_info(r):
    """429 응답 → (일일 한도인지, 서버가 권하는 대기 초)
    일일 한도는 QuotaFailure 의 quotaId/quotaMetric 에 'PerDay' 가 있을 때만으로 판단
    (무료 등급은 분당 한도도 quotaMetric 이 '...free_tier_requests' 라서 그 문자열로는 구분할 수 없음)"""
    daily, delay = False, None
    try:
        details = (r.json().get("error") or {}).get("details") or []
        for d in details:
            kind = str(d.get("@type", ""))
            if kind.endswith("QuotaFailure"):
                for v in d.get("violations") or []:
                    if "PerDay" in f"{v.get('quotaId', '')} {v.get('quotaMetric', '')}":
                        daily = True
            elif kind.endswith("RetryInfo"):
                m = re.match(r"([\d.]+)s", str(d.get("retryDelay", "")))
                if m:
                    delay = float(m.group(1))
    except (ValueError, AttributeError, TypeError):
        daily = "PerDay" in r.text  # JSON 이 아니면 본문 문자열로만 판단
    return daily, delay


def translate_map(texts, glossary=None, retries=MAX_RETRIES, max_seconds=CALL_BUDGET):
    global _last_call
    texts = {k: v for k, v in texts.items() if v and v.strip()}
    if not texts:
        return {}
    joined = " ".join(texts.values())
    # 대소문자 구분 + 단어 단위로만 찾음 (일반 단어 'data', 'free' 등이 용어로 잡히지 않도록)
    terms = {k: v for k, v in load_terms().items() if re.search(rf"(?<![\w-]){re.escape(k)}(?![\w-])", joined)}
    terms.update(glossary or {})
    gl = ""
    if terms:
        gl = "\n용어집(영어/일본어 → 한국어):\n" + "\n".join(f"- {k} → {v}" for k, v in terms.items())
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(glossary=gl, payload=json.dumps(texts, ensure_ascii=False))}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    deadline = time.time() + max_seconds
    busy = {}
    parse_failures = 0
    for attempt in range(retries):
        models = _candidates()
        if not models:
            raise QuotaExceeded("모든 모델이 오늘 한도에 도달")
        # 이번 요청에서 두 번 이상 혼잡했던 모델은 건너뜀 (다 혼잡하면 그중 덜 실패한 모델)
        model = min(models, key=lambda m: (busy.get(m, 0) >= 2, models.index(m)))
        _sleep(_last_call + MIN_INTERVAL - time.time(), deadline)
        remaining = deadline - time.time()
        if remaining < 10:
            break
        _last_call = time.time()
        try:
            r = requests.post(f"{API}/models/{model}:generateContent", headers=_headers(), json=body,
                              timeout=min(REQUEST_TIMEOUT, remaining))
        except Exception as e:
            print(f"  [gemini] {model} 요청 오류: {e}")
            busy[model] = busy.get(model, 0) + 1
            continue
        if r.status_code == 429:
            daily, delay = _quota_info(r)
            if daily:
                # 무료 등급 일일 한도는 모델마다 따로 → 다음 모델로
                _exhausted.add(model)
                print(f"  [gemini] {model} 오늘 한도 도달 → 다른 모델")
                continue
            pause = min(MAX_SLEEP, delay if delay else 15 * (attempt + 1))
            print(f"  [gemini] {model} 분당 한도 - {pause:.0f}초 대기")
            _sleep(pause, deadline)
            continue
        if r.status_code >= 500:
            busy[model] = busy.get(model, 0) + 1
            print(f"  [gemini] {model} 혼잡(HTTP {r.status_code})")
            if all(busy.get(m, 0) >= 2 for m in models):
                _sleep(20, deadline)
            continue
        if r.status_code == 404:
            _exhausted.add(model)
            print(f"  [gemini] {model} 사용 불가 → 다른 모델")
            continue
        if r.status_code in (401, 403) or (r.status_code == 400 and ("API_KEY" in r.text or "API key" in r.text)):
            raise AuthError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
        if r.status_code != 200:
            # 400 등 요청 자체의 문제 → 같은 요청을 반복해도 실패
            raise BadResponse(f"Gemini HTTP {r.status_code}: {r.text[:300]}")

        try:
            data = r.json()
        except ValueError:
            data = None
        if not isinstance(data, dict):
            data = {}
        block = (data.get("promptFeedback") or {}).get("blockReason")
        cands = data.get("candidates") or []
        if block or not cands:
            raise BadResponse(f"응답 후보 없음 (blockReason={block}): {r.text[:300]}")
        cand = cands[0] if isinstance(cands[0], dict) else {}
        finish = cand.get("finishReason")
        if finish in _BLOCK_FINISH:
            raise BadResponse(f"생성 중단 (finishReason={finish})")
        parts = (cand.get("content") or {}).get("parts") or []
        raw = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        try:
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
            out = json.loads(raw)
            if not isinstance(out, dict):
                raise ValueError("JSON 객체가 아님")
        except ValueError as e:
            parse_failures += 1
            print(f"  [gemini] 응답 해석 실패({e}, finishReason={finish}): {raw[:200]}")
            # 잘린 응답(MAX_TOKENS)이거나 두 번째 실패면 이 묶음은 포기 (같은 요청 반복은 한도만 낭비)
            if finish == "MAX_TOKENS" or parse_failures >= 2:
                raise BadResponse(f"응답 해석 실패: {e}")
            continue
        return {k: str(out[k]).strip() for k in texts if out.get(k)}
    raise Busy("재시도·시간 한도 초과 (모델 혼잡 또는 응답 없음)")
