"""도감 설명(Digi-API 영어 프로필·필살기) 한국어 미리 번역 — Gemini

입력   public/data/dex.json (api_id·공식 한국어 이름 → 용어집)
       Digi-API /digimon/{id} (영어 원문)
저장   data/translations/dex_ko.json        번역 원장 (원문 해시 포함 → 원문이 바뀐 것만 다시 번역)
       public|docs/data/dex_ko/{n}.json     앱이 읽는 파일 (api_id // 100 단위로 나눠 필요한 조각만 받음)

무료 등급 한도에 걸리면 지금까지 번역한 것을 저장하고 멈춤 → 다음 실행 때 이어서 진행.
원문에 있는 문장(프로필·필살기 이름·설명)이 하나라도 번역 결과에 빠지면 원장에 기록하지 않음 → 다음 실행 때 다시 번역.
(예전 방식으로 필살기 설명이 빈 채 기록된 항목은 원문과 한 번 대조해서, 빠진 게 있으면 다시 번역)

사용: python scraper/translate_dex.py              # 아직 번역 안 된 것만
      python scraper/translate_dex.py --recheck    # 번역된 것도 원문을 다시 받아 바뀐 것만 재번역
      python scraper/translate_dex.py --max 100    # 이번 실행에서 최대 100종까지
"""
import hashlib
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini  # noqa: E402
from jsonio import load_json as load, write_json  # noqa: E402

DEX_FILE = "public/data/dex.json"
LEDGER = "data/translations/dex_ko.json"
OUT_DIRS = ["public/data/dex_ko", "docs/data/dex_ko"]
DIGI_API = "https://digi-api.com/api/v1/digimon/"
BATCH_CHARS = 9000
BATCH_ITEMS = 15  # 무료 등급은 요청 수(모델당 하루 약 20회)가 한계라 한 번에 많이 묶음
MAX_SKILLS = 6  # 앱에 보여주는 필살기 수와 맞춤
# 워크플로 제한(120분) 안에서 저장·커밋까지 끝나도록
TIME_BUDGET = 80 * 60  # 이 시간이 지나면 새 묶음(번역 요청)을 시작하지 않음
HARD_LIMIT = 105 * 60  # 번역 요청 하나가 늦어져도 이 시간 안에는 끝나도록 요청마다 남은 시간을 넘겨줌
MAX_EMPTY_BATCHES = 3  # 연달아 한 종도 못 건진 묶음이 이만큼이면 한도만 낭비 → 멈춤
VERIFIED = "complete"  # 원장 항목 표시: 원문과 대조해 빠진 번역이 없음을 확인함


def fetch_source(session, api_id):
    for attempt in range(3):
        try:
            r = session.get(f"{DIGI_API}{api_id}", timeout=20)
            if r.status_code == 200:
                a = r.json()
                descs = a.get("descriptions") or []
                d = next((x for x in descs if x.get("language") == "en_us"), descs[0] if descs else None)
                return {
                    "profile": (d or {}).get("description", "") or "",
                    "skills": [{"name": s.get("skill", ""), "desc": s.get("description", "") or ""}
                               for s in (a.get("skills") or [])[:MAX_SKILLS]],
                }
            if r.status_code == 404:
                return None
        except Exception as e:
            print(f"  Digi-API 오류 {api_id}: {e}")
        if attempt < 2:
            time.sleep(1 + attempt * 2)
    return None


def src_hash(src):
    return hashlib.sha1(json.dumps(src, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def has_text(s):
    return bool(s and str(s).strip())


def required_keys(api_id, src):
    """원문에 내용이 있어서 번역 결과에 반드시 있어야 하는 키"""
    keys = [f"{api_id}.p"] if has_text(src["profile"]) else []
    for i, s in enumerate(src["skills"]):
        if has_text(s["name"]):
            keys.append(f"{api_id}.s{i}.n")
        if has_text(s["desc"]):
            keys.append(f"{api_id}.s{i}.d")
    return keys


def ledger_complete(v, src):
    """원장 항목이 원문 대비 빠진 번역 없이 채워졌는지 (필살기 이름은 영어로 대체 저장되므로 설명·프로필만 확인)"""
    if has_text(src["profile"]) and not has_text(v.get("profile")):
        return False
    skills = v.get("skills") or []
    if len(skills) != len(src["skills"]):
        return False
    return all(has_text(t.get("desc")) for s, t in zip(src["skills"], skills) if has_text(s["desc"]))


def looks_incomplete(v):
    """예전 방식으로 기록돼 필살기 설명이 빈 항목 (원문도 비었는지는 원문을 받아 봐야 앎)"""
    return not v.get(VERIFIED) and any(not has_text(s.get("desc")) for s in v.get("skills") or [])


def build_glossary(entries):
    """Digi-API 영문 이름 → 공식 한국어 이름 (괄호 표기를 뺀 이름도 추가)"""
    g = {}
    for e in entries:
        en, ko = e.get("api_name"), e.get("name")
        if not en or not ko or not re.search(r"[가-힣]", ko):
            continue
        g.setdefault(en, ko)
        base = re.sub(r"\s*\(.*?\)\s*", " ", en).strip()
        if base and base != en and e.get("official"):
            g.setdefault(base, re.sub(r"\s*\(.*?\)\s*", "", ko).strip() or ko)
    # Digi-API 이름은 'War Greymon'처럼 띄어 쓰지만 설명문은 'WarGreymon'으로 붙여 씀 → 둘 다 등록
    for en, ko in list(g.items()):
        if " " in en and "(" not in en:
            g.setdefault(en.replace(" ", ""), ko)
    return dict(sorted(g.items(), key=lambda kv: -len(kv[0])))


def glossary_for(text, glossary, limit=60):
    out = {}
    low = text.lower()
    for en, ko in glossary.items():
        if len(en) > 2 and en.lower() in low:
            out[en] = ko
            if len(out) >= limit:
                break
    return out


def write_outputs(ledger):
    buckets = {}
    for api_id, v in ledger.items():
        item = {k: v[k] for k in ("profile", "skills") if v.get(k)}
        buckets.setdefault(int(api_id) // 100, {})[api_id] = item
    for d in OUT_DIRS:
        for n, items in buckets.items():
            write_json(os.path.join(d, f"{n}.json"), dict(sorted(items.items(), key=lambda kv: int(kv[0]))),
                       separators=(",", ":"))
    write_json(LEDGER, dict(sorted(ledger.items(), key=lambda kv: int(kv[0]))), indent=1)


def main():
    if not gemini.available():
        print("GEMINI_API_KEY 가 없어 번역을 건너뜁니다.")
        return
    recheck = "--recheck" in sys.argv
    max_n = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10 ** 9

    entries = load(DEX_FILE, {"digimons": []})["digimons"]
    glossary = build_glossary(entries)
    ledger = load(LEDGER, {})
    own_names = {str(e["api_id"]): (e["api_name"], e["name"]) for e in entries
                 if e.get("api_id") and e.get("api_name") and re.search(r"[가-힣]", e.get("name") or "")}
    ids = list(dict.fromkeys(str(e["api_id"]) for e in entries if e.get("api_id")))  # 공식 번호순 → EX
    todo = [i for i in ids if recheck or i not in ledger or looks_incomplete(ledger[i])]
    print(f"대상 {len(todo)}종 (전체 {len(ids)}, 번역 완료 {len(ledger)})")

    session = requests.Session()
    session.headers["User-Agent"] = "digimon-feed (fan project)"
    pending, done, chars, empty_batches = [], 0, 0, 0
    started = time.time()

    def elapsed():
        return time.time() - started

    def flush():
        nonlocal pending, chars, done, empty_batches
        if not pending:
            return
        batch, pending, chars = pending, [], 0
        texts = {}
        for api_id, src, _ in batch:
            texts[f"{api_id}.p"] = src["profile"]
            for i, s in enumerate(src["skills"]):
                texts[f"{api_id}.s{i}.n"] = s["name"]
                texts[f"{api_id}.s{i}.d"] = s["desc"]
        gl = glossary_for(" ".join(t for t in texts.values() if t), glossary)
        for api_id, _, _ in batch:  # 설명의 주인공 이름도 항상 용어집에 포함
            if api_id in own_names:
                gl.setdefault(*own_names[api_id])
        while True:
            try:
                out = gemini.translate_map(texts, gl, max_seconds=max(30, min(gemini.CALL_BUDGET, HARD_LIMIT - elapsed())))
                break
            except gemini.Busy as e:
                # 무료 등급은 혼잡할 때 밀려남 → 시간 예산 안에서 쉬었다가 같은 묶음을 다시 시도
                if elapsed() + 180 > TIME_BUDGET:
                    raise
                print(f"  혼잡 — 3분 뒤 다시 시도 ({e})")
                time.sleep(180)
            except gemini.BadResponse as e:
                # 이 묶음만 번역 불가(안전 차단·해석 불가 등) → 건너뛰고 다음 실행 때 다시
                print(f"  묶음 번역 실패 — 건너뜀 ({e})")
                out = {}
                break
        ok = 0
        for api_id, src, h in batch:
            lost = [k for k in required_keys(api_id, src) if not has_text(out.get(k))]
            if lost:
                print(f"  {api_id}: 번역 누락 {len(lost)}곳 — 기록하지 않고 다음에 다시")
                continue
            ledger[api_id] = {
                "hash": h,
                VERIFIED: True,
                "profile": out.get(f"{api_id}.p", ""),
                "skills": [{"name": out.get(f"{api_id}.s{i}.n") or s["name"], "name_en": s["name"],
                            "desc": out.get(f"{api_id}.s{i}.d", "")} for i, s in enumerate(src["skills"])],
            }
            ok += 1
        done += ok
        empty_batches = 0 if ok else empty_batches + 1
        print(f"  번역 {done}종")
        write_outputs(ledger)  # 묶음마다 저장
        if empty_batches >= MAX_EMPTY_BATCHES:
            raise RuntimeError(f"연달아 {empty_batches}개 묶음에서 한 종도 번역되지 않음")

    try:
        for api_id in todo:
            if done + len(pending) >= max_n or elapsed() > TIME_BUDGET:
                break
            src = fetch_source(session, api_id)
            time.sleep(0.1)
            if src is None:
                continue
            h = src_hash(src)
            prev = ledger.get(api_id)
            if prev and prev.get("hash") == h and ledger_complete(prev, src):
                if not prev.get(VERIFIED):
                    prev[VERIFIED] = True  # 원문과 대조 완료 → 다음부터 다시 받지 않음
                continue
            if not has_text(src["profile"]) and not any(has_text(s["name"]) or has_text(s["desc"]) for s in src["skills"]):
                ledger[api_id] = {"hash": h, VERIFIED: True}
                continue
            size = len(src["profile"]) + sum(len(s["name"] or "") + len(s["desc"]) for s in src["skills"])
            if pending and (chars + size > BATCH_CHARS or len(pending) >= BATCH_ITEMS):
                flush()
            pending.append((api_id, src, h))
            chars += size
        if elapsed() <= TIME_BUDGET:
            flush()
        elif pending:
            print(f"시간 예산 초과 — 남은 {len(pending)}종은 다음 실행 때")
    except gemini.Busy as e:
        print(f"시간 예산 안에 혼잡이 풀리지 않음 — 저장 후 다음 실행 때 이어서: {e}")
    except gemini.QuotaExceeded as e:
        print(f"Gemini 한도 도달 — 여기까지 저장하고 다음 실행 때 이어서 진행: {e}")
    except RuntimeError as e:
        print(f"Gemini 오류 — 여기까지 저장하고 멈춤: {e}")
    write_outputs(ledger)
    print(f"완료: 번역 원장 {len(ledger)}종 / 이번 실행 {done}종")


if __name__ == "__main__":
    main()
