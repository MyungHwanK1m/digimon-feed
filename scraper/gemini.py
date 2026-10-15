"""Gemini 번역 도우미 (Google AI Studio 무료 키로 동작)

환경 변수
  GEMINI_API_KEY   필수. 없으면 available() 이 False → 호출하는 쪽은 번역을 건너뜀
  GEMINI_MODEL     선택. 비우면 사용 가능한 최신 flash 모델을 자동으로 고름 (막힌 모델이면 다음 모델로 교체)

translate_map({"키": "원문", ...}, glossary={"Agumon": "아구몬"}) → {"키": "한국어"}
  - 여러 문장을 한 번에 JSON으로 주고받아 요청 수를 줄임 (무료 등급은 분당·일일 요청 수 제한이 있음)
  - 일일 한도에 걸리면 QuotaExceeded 를 던짐 → 호출하는 쪽에서 지금까지 결과를 저장하고 멈추면 다음 실행 때 이어서 진행
"""
import json
import os
import re
import time

import requests

API = "https://generativelanguage.googleapis.com/v1beta"
MIN_INTERVAL = 6.5  # 무료 등급 분당 요청 제한(약 10회)에 맞춘 간격(초)

_model = None
_last_call = 0.0


class QuotaExceeded(Exception):
    pass


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
    flash = [n for n in names if re.fullmatch(r"gemini-[\d.]+-flash", n)]
    return sorted(flash, key=lambda n: [int(x) for x in re.findall(r"\d+", n)], reverse=True)


def _pick_model(exclude=()):
    """GEMINI_MODEL 이 있으면 그것, 없으면 사용 가능한 최신 flash 모델"""
    global _model
    if _model and _model not in exclude:
        return _model
    wanted = os.environ.get("GEMINI_MODEL")
    if wanted and wanted not in exclude:
        _model = wanted
        return _model
    try:
        flash = [n for n in _list_flash_models() if n not in exclude]
    except Exception as e:
        raise RuntimeError(f"모델 목록 조회 실패: {e}")
    if not flash:
        raise RuntimeError("사용 가능한 flash 모델이 없습니다")
    _model = flash[0]
    print(f"  [gemini] 모델: {_model}")
    return _model


TERMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "translations", "terms.json")


def load_terms():
    """고정 용어집 (data/translations/terms.json, '_'로 시작하는 키는 메모)"""
    try:
        with open(TERMS_FILE, encoding="utf-8") as f:
            return {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    except (OSError, ValueError):
        return {}


PROMPT = """너는 디지몬 공식 도감 번역가다. 아래 JSON의 각 값을 한국어로 번역해라. 원작 고증이 최우선이다.
출력: 같은 키를 그대로 쓰고 값만 한국어 번역으로 바꾼 JSON 객체 하나만 출력한다.

고증 규칙
1. 디지몬 이름과 세계관 용어는 아래 용어집 표기를 반드시 그대로 쓴다. 용어집에 없는 디지몬 이름은 뜻을 풀어 의역하지 말고 일본 원작 이름을 한글로 옮긴다(공식 도감 방식).
2. 진화 단계·속성은 용어집 표기만 쓴다(예: Ultimate는 '궁극체', Perfect는 '완전체', Vaccine은 '백신종'). 영어 더빙식 단계명으로 해석하지 않는다.
3. 필살기 이름은 일본 원작 기술명을 확실히 아는 경우에만 그 한글 표기(예: Pepper Breath → 베이비 플레임)를 쓰고, 확실하지 않으면 영어 기술명을 그대로 한글 음역한다. 기술명을 지어내지 않는다.
4. 원문에 없는 설정·정보를 덧붙이거나 빼지 않는다. 모호한 부분은 원문 그대로의 의미로 옮긴다.
5. 문체: 도감 설명은 '~이다/~한다'체 평서문. 상품명·작품명은 한국 정발명이 있으면 그것을, 없으면 원문을 자연스럽게 옮기고 가격·날짜·숫자는 그대로 둔다.
{glossary}
번역할 JSON:
{payload}"""


def translate_map(texts, glossary=None, retries=4):
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
    tried = set()
    model = _pick_model()
    for attempt in range(retries):
        wait = _last_call + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            r = requests.post(f"{API}/models/{model}:generateContent", headers=_headers(), json=body, timeout=120)
        except Exception as e:
            print(f"  [gemini] 요청 오류: {e}")
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 429:
            msg = r.text
            # 일일 한도(PerDay)면 오늘은 그만, 분당 한도면 잠깐 쉬고 재시도
            if "PerDay" in msg or "per day" in msg.lower():
                raise QuotaExceeded(msg[:300])
            time.sleep(30 * (attempt + 1))
            continue
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 404:
            # 단종·신규 사용자 제한 모델 → 다음 최신 flash 모델로 교체
            tried.add(model)
            print(f"  [gemini] {model} 사용 불가 → 다른 모델 시도")
            model = _pick_model(exclude=tried)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
        try:
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
            out = json.loads(raw)
        except Exception as e:
            print(f"  [gemini] 응답 해석 실패({e}) — 재시도")
            continue
        return {k: str(out[k]).strip() for k in texts if isinstance(out, dict) and out.get(k)}
    raise QuotaExceeded("재시도 한도 초과")
