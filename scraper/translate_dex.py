"""도감 설명(Digi-API 영어 프로필·필살기) 한국어 미리 번역 — Gemini

입력   public/data/dex.json (api_id·공식 한국어 이름 → 용어집)
       Digi-API /digimon/{id} (영어 원문)
저장   data/translations/dex_ko.json        번역 원장 (원문 해시 포함 → 원문이 바뀐 것만 다시 번역)
       public|docs/data/dex_ko/{n}.json     앱이 읽는 파일 (api_id // 100 단위로 나눠 필요한 조각만 받음)

무료 등급 한도에 걸리면 지금까지 번역한 것을 저장하고 멈춤 → 다음 실행 때 이어서 진행.

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

sys.path.insert(0, os.path.dirname(__file__))
import gemini  # noqa: E402

DEX_FILE = "public/data/dex.json"
LEDGER = "data/translations/dex_ko.json"
OUT_DIRS = ["public/data/dex_ko", "docs/data/dex_ko"]
DIGI_API = "https://digi-api.com/api/v1/digimon/"
BATCH_CHARS = 6000
BATCH_ITEMS = 12
MAX_SKILLS = 6  # 앱에 보여주는 필살기 수와 맞춤


def load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


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
        time.sleep(1 + attempt * 2)
    return None


def src_hash(src):
    return hashlib.sha1(json.dumps(src, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


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
        os.makedirs(d, exist_ok=True)
        for n, items in buckets.items():
            with open(os.path.join(d, f"{n}.json"), "w", encoding="utf-8") as f:
                json.dump(dict(sorted(items.items(), key=lambda kv: int(kv[0]))), f, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(ledger.items(), key=lambda kv: int(kv[0]))), f, ensure_ascii=False, indent=1)


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
                 if e.get("api_id") and e.get("api_name") and re.search(r"[가-힣]", e.get("name", ""))}
    ids = list(dict.fromkeys(str(e["api_id"]) for e in entries if e.get("api_id")))  # 공식 번호순 → EX
    todo = [i for i in ids if recheck or i not in ledger]
    print(f"대상 {len(todo)}종 (전체 {len(ids)}, 번역 완료 {len(ledger)})")

    session = requests.Session()
    session.headers["User-Agent"] = "digimon-feed (fan project)"
    pending, done, chars = [], 0, 0

    def flush():
        nonlocal pending, chars, done
        if not pending:
            return
        texts = {}
        for api_id, src, _ in pending:
            texts[f"{api_id}.p"] = src["profile"]
            for i, s in enumerate(src["skills"]):
                texts[f"{api_id}.s{i}.n"] = s["name"]
                texts[f"{api_id}.s{i}.d"] = s["desc"]
        gl = glossary_for(" ".join(texts.values()), glossary)
        for api_id, _, _ in pending:  # 설명의 주인공 이름도 항상 용어집에 포함
            if api_id in own_names:
                gl.setdefault(*own_names[api_id])
        out = gemini.translate_map(texts, gl)
        for api_id, src, h in pending:
            if src["profile"] and f"{api_id}.p" not in out:
                print(f"  {api_id}: 프로필 번역 누락 — 다음에 다시")
                continue
            ledger[api_id] = {
                "hash": h,
                "profile": out.get(f"{api_id}.p", ""),
                "skills": [{"name": out.get(f"{api_id}.s{i}.n") or s["name"], "name_en": s["name"],
                            "desc": out.get(f"{api_id}.s{i}.d", "")} for i, s in enumerate(src["skills"])],
            }
            done += 1
        print(f"  번역 {done}종")
        pending, chars = [], 0

    try:
        for api_id in todo:
            if done + len(pending) >= max_n:
                break
            src = fetch_source(session, api_id)
            time.sleep(0.1)
            if src is None:
                continue
            h = src_hash(src)
            if ledger.get(api_id, {}).get("hash") == h:
                continue
            if not src["profile"] and not src["skills"]:
                ledger[api_id] = {"hash": h}
                continue
            size = len(src["profile"]) + sum(len(s["name"]) + len(s["desc"]) for s in src["skills"])
            if pending and (chars + size > BATCH_CHARS or len(pending) >= BATCH_ITEMS):
                flush()
                if done % 120 < BATCH_ITEMS:
                    write_outputs(ledger)  # 중간 저장
            pending.append((api_id, src, h))
            chars += size
        flush()
    except gemini.QuotaExceeded as e:
        print(f"Gemini 한도 도달 — 여기까지 저장하고 다음 실행 때 이어서 진행: {e}")
    except RuntimeError as e:
        print(f"Gemini 오류 — 여기까지 저장하고 멈춤: {e}")
    write_outputs(ledger)
    print(f"완료: 번역 원장 {len(ledger)}종 / 이번 실행 {done}종")


if __name__ == "__main__":
    main()
