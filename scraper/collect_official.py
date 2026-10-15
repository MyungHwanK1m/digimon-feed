"""공식 디지몬 도감(digimon.net/reference_ko) 기본 정보 수집

저장하는 것: 공식 목록 순서 기반 번호, 디렉터리명, 공식 한국어 이름, 영문 표기, 등급, 유형, 속성,
            X항체 여부, 관련된 디지몬(디렉터리명), 공식 상세 페이지 주소
저장하지 않는 것: 프로필 문장, 필살기, 그림 (공식 사이트 이용 조건 — 화면에서는 공식 페이지로 연결)

번호 규칙: 오래된 등록이 1번(공식 목록은 최신순이라 역순으로 매김). data/official/numbers.json 에 한 번 매긴 번호는 고정하고,
새로 생긴 디지몬은 등록 순서대로 뒤에 이어 붙임.

아프몬 도감(digimon.net/appmon_ko)도 같은 원칙으로 수집: 이름·등급·앱 이름·속성·관련 아프몬·공식 주소 → data/official/appmon.json

사용: python scraper/collect_official.py             # 디지몬 전체 수집 (상세 페이지 포함, 약 30분) + 아프몬
      python scraper/collect_official.py --list-only  # 디지몬 목록만 + 아프몬
      python scraper/collect_official.py --appmon-only
"""
import html
import json
import os
import re
import sys
import time

import requests

BASE = "https://digimon.net/reference_ko/"
OUT_DIR = "data/official"
NUMBERS_FILE = os.path.join(OUT_DIR, "numbers.json")
REFERENCE_FILE = os.path.join(OUT_DIR, "reference.json")
DELAY = 0.6  # 공식 서버 부담을 줄이기 위한 요청 간격(초)

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (digimon-feed non-commercial fan project)",
    "Referer": BASE,
    "X-Requested-With": "XMLHttpRequest",
})


def get(url, **kw):
    for attempt in range(4):
        try:
            r = S.get(url, timeout=30, **kw)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code}: {r.url}")
        except Exception as e:
            print(f"  error {e}: {url}")
        time.sleep(2 + attempt * 3)
    return None


def fetch_list():
    """공식 목록 순서 그대로 (request.php 페이지 단위)"""
    get(BASE)  # 세션 쿠키
    rows, offset, seen = [], 0, set()
    while True:
        r = get(BASE + "request.php", params={
            "digimon_name": "", "digimon_level": "", "attribute": "", "type": "",
            "next": offset, "view_more": 1 if offset else "",
        })
        if r is None:
            raise SystemExit("목록 요청 실패")
        try:
            data = r.json()
        except ValueError:
            raise SystemExit(f"목록 응답이 JSON이 아닙니다: {r.text[:200]}")
        if not data:
            break
        for row in data.get("rows", []):
            d = row.get("directory_name")
            if d and d not in seen:
                seen.add(d)
                rows.append(row)
        nxt = data.get("next", -1)
        print(f"  목록 {len(rows)}건 (next={nxt})")
        if nxt in (-1, None, "-1") or int(nxt) == offset:
            break
        offset = int(nxt)
        time.sleep(DELAY)
    return rows


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def parse_detail(page):
    out = {}
    m = re.search(r'c-titleSet__sub">(.*?)</div>\s*<h3[^>]*>(.*?)</h3>', page, re.S)
    if m:
        out["name_en"] = text(m.group(1))
        out["name_ko"] = text(m.group(2))
    info = {text(k): text(v) for k, v in re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S)}
    for key, field in (("등급", "level"), ("유형", "type"), ("속성", "attribute")):
        if info.get(key):
            out[field] = info[key]
    rel = page.split('class="p-ref__related"', 1)
    if len(rel) == 2:
        out["related"] = re.findall(r'detail\.php\?directory_name=([^"&]+)"', rel[1].split("</section>", 1)[0])
    return out


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("공식 목록 수집…")
    rows = fetch_list()
    print(f"목록 {len(rows)}건")

    # 공식 목록은 최신 등록순 → 뒤에서부터(오래된 것부터) 번호를 매겨 새 디지몬이 항상 뒤에 붙도록 함
    numbers = load_json(NUMBERS_FILE, {})
    next_no = max(numbers.values(), default=0) + 1
    for row in reversed(rows):
        d = row["directory_name"]
        if d not in numbers:
            numbers[d] = next_no
            next_no += 1

    old = {e["directory_name"]: e for e in load_json(REFERENCE_FILE, {"digimons": []})["digimons"]}
    entries = []
    list_only = "--list-only" in sys.argv
    for i, row in enumerate(rows):
        d = row["directory_name"]
        e = {
            "no": numbers[d],
            "directory_name": d,
            "name_ko": row.get("name"),
            "level": row.get("level"),
            "x_antibody": row.get("relate_word6") == "〇",
            "url": f"{BASE}detail.php?directory_name={d}",
        }
        if row.get("level_2"):
            e["level_2"] = row["level_2"]
        if list_only:
            prev = old.get(d, {})
            e.update({k: prev[k] for k in ("name_en", "type", "attribute", "related") if k in prev})
        else:
            r = get(BASE + "detail.php", params={"directory_name": d})
            if r is not None:
                e.update(parse_detail(r.text))
            time.sleep(DELAY)
            if (i + 1) % 100 == 0:
                print(f"  상세 {i + 1}/{len(rows)}")
        entries.append(e)

    entries.sort(key=lambda x: x["no"])
    with open(NUMBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(numbers.items(), key=lambda kv: kv[1])), f, ensure_ascii=False, indent=1)
    with open(REFERENCE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "source": BASE,
            "note": "기본 정보만 저장 (프로필·필살기·그림은 공식 페이지 참고)",
            "total": len(entries),
            "digimons": entries,
        }, f, ensure_ascii=False, indent=1)
    print(f"저장: {REFERENCE_FILE} ({len(entries)}종), {NUMBERS_FILE}")


APPMON_BASE = "https://digimon.net/appmon_ko/"
APPMON_FILE = os.path.join(OUT_DIR, "appmon.json")


def collect_appmon():
    print("아프몬 도감 수집…")
    r = get(APPMON_BASE)
    if r is None:
        print("아프몬 목록 요청 실패 — 건너뜀")
        return
    ids = []
    for m in re.finditer(r'href="\./detail\.php\?id=(\d+)"', r.text):
        if int(m.group(1)) not in ids:
            ids.append(int(m.group(1)))
    entries = []
    for i in ids:
        d = get(APPMON_BASE + "detail.php", params={"id": i})
        time.sleep(DELAY)
        if d is None:
            continue
        page = d.text
        name = re.search(r'c-titleSet__main[^>]*>(.*?)</h3>', page, re.S)
        info = {text(k): text(v) for k, v in re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S)}
        rel = page.split('class="p-ref__related"', 1)
        related = [int(x) for x in re.findall(r'detail\.php\?id=(\d+)"', rel[1])] if len(rel) == 2 else []
        entries.append({
            "id": i,
            "name_ko": text(name.group(1)) if name else "",
            "grade": info.get("등급", ""),
            "app": info.get("앱 이름", ""),
            "attribute": info.get("속성", ""),
            "related": [x for x in dict.fromkeys(related) if x != i],
            "url": f"{APPMON_BASE}detail.php?id={i}",
        })
    with open(APPMON_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": APPMON_BASE, "note": "기본 정보만 저장 (프로필·필살기·그림은 공식 페이지 참고)",
                   "total": len(entries), "appmons": entries}, f, ensure_ascii=False, indent=1)
    print(f"저장: {APPMON_FILE} ({len(entries)}종)")


if __name__ == "__main__":
    if "--appmon-only" not in sys.argv:
        main()
    collect_appmon()
