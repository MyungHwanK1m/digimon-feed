"""Gemini 번역 도우미 (Google AI Studio 무료 키로 동작)

환경 변수
  GEMINI_API_KEY   필수. 없으면 available() 이 False → 호출하는 쪽은 번역을 건너뜀
  GEMINI_MODEL     선택. 기본 gemini-2.5-flash, 없어진 모델이면 사용 가능한 flash 모델을 자동으로 고름

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


def _pick_model():
    """설정된 모델이 없으면 generateContent 를 지원하는 최신 flash 모델을 고름"""
    global _model
    if _model:
        return _model
    wanted = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    try:
        r = requests.get(f"{API}/models", headers=_headers(), params={"pageSize": 200}, timeout=30)
        r.raise_for_status()
        names = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception as e:
        print(f"  [gemini] 모델 목록 조회 실패({e}) — {wanted} 사용")
        _model = wanted
        return _model
    if wanted in names:
        _model = wanted
    else:
        flash = [n for n in names if re.fullmatch(r"gemini-[\d.]+-flash", n)]
        _model = sorted(flash, key=lambda n: [int(x) for x in re.findall(r"\d+", n)])[-1] if flash else wanted
        print(f"  [gemini] {wanted} 없음 → {_model} 사용")
    return _model


PROMPT = """너는 디지몬 전문 번역가다. 아래 JSON의 각 값을 자연스러운 한국어로 번역해라.
규칙:
- 같은 키를 그대로 쓰고, 값만 한국어 번역으로 바꾼 JSON 객체 하나만 출력한다.
- 디지몬 이름·용어는 아래 용어집을 반드시 따른다. 용어집에 없는 디지몬 이름은 한국 정발 표기(국내 방영·게임 표기)를 쓴다.
- 일본어 원문의 상품명·작품명은 한국 정발명이 있으면 그것을, 없으면 자연스럽게 옮긴다. 가격·날짜·숫자는 바꾸지 않는다.
- 설명을 덧붙이거나 줄이지 말고 원문 의미 그대로 옮긴다.
{glossary}
번역할 JSON:
{payload}"""


def translate_map(texts, glossary=None, retries=4):
    global _last_call
    texts = {k: v for k, v in texts.items() if v and v.strip()}
    if not texts:
        return {}
    gl = ""
    if glossary:
        gl = "용어집(영어/일본어 → 한국어):\n" + "\n".join(f"- {k} → {v}" for k, v in glossary.items())
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(glossary=gl, payload=json.dumps(texts, ensure_ascii=False))}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
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
