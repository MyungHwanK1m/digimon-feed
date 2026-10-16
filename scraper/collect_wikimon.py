"""Wikimon 진화 데이터 수집 (출처 포함)

Wikimon(wikimon.net) 각 디지몬 문서의 "Evolves From" / "Evolves To" 목록을 읽어
진화마다 어디서 나온 진화인지(애니·게임·TCG·기기 등)와 조건(함께 진화하는 디지몬 등)을 저장한다.

예의 지키기
  - MediaWiki API(api.php)만 사용 (robots.txt가 막는 /index.php? 는 쓰지 않음)
  - 한 번에 50문서씩, 요청 사이 60초 (robots.txt Crawl-delay: 60)
  - 프로젝트를 밝히는 User-Agent
  - 저장하는 것은 진화 연결·조건·출처 이름뿐 (문서 본문은 저장하지 않음), 화면에 "출처: Wikimon" 표시

입력  public/data/dex.json (Digi-API 이름 = Wikimon 문서 제목)
출력  data/wikimon/evolutions.json   {제목: {"from": [...], "to": [...]}}
      data/wikimon/report.md         분류 안 된 출처·템플릿 통계 (규칙 손볼 때 확인용)

사용: python scraper/collect_wikimon.py [--max-requests N]
"""
import collections
import json
import os
import re
import sys
import time

import requests

API = "https://wikimon.net/api.php"
DEX_FILE = "public/data/dex.json"
OUT_DIR = "data/wikimon"
OUT_FILE = os.path.join(OUT_DIR, "evolutions.json")
REPORT_FILE = os.path.join(OUT_DIR, "report.md")
DELAY = 60  # robots.txt Crawl-delay
BATCH = 50
UA = "digimon-feed (non-commercial fan dex; https://github.com/MyungHwanK1m/digimon-feed)"

# 출처 분류 규칙 (작품명 → 분류). 위에서부터 먼저 맞는 것
CAT_RULES = [
    ("game", r"Tag Tamers|D1 Tamers|Anode|Cathode|Digimon World|Digimon Story|Rumble|Battle Spirit|Digimon Masters|Linkz|ReArise|"
             r"New Century|Survive|Digimon Heroes|Crusader|Soul Chaser|Collectors|D-Project|Brave Tamer|Racing|Tamer Battle|"
             r"Digimon Medal|Card Arena|Card Battle|Digimon Fortune|Digimon Frontier: |Next Order|Cyber Sleuth|Hacker'?s Memory|"
             r"Time Stranger|Re:Digitize|Digimon Adventure \(PSP\)|Digimon Universe|Appli Monsters \(game\)|Digimon Seekers|"
             r"Super Xros Wars|Lost Evolution|Digital Card|Digimon Tamers: |Digimon Neo|Battle Chronicle|"
             r"Digimon Generations|Digimon Alysion|Digimon Con|Digimon Life|Digimon Ranch|DigiTama Hatch|Digimon Fight|"
             r"Digimon Championship|Source Code|Digimon RPG|Digimon Super Rumble|Digimon All-Star"),
    ("device", r"Pendulum|Digital Monster|Digivice|Vital Bracelet|Vital Hero|\bD-3\b|D-Ark|D-Power|D-Scanner|D-Tector|Digimon Mini|"
               r"Data Link|Xros Loader|\bBurst\b|\biC\b|\bTwin\b|Fusion Loader|\bVer\.|\bCOLOR\b|Dim Card|Digimon Pocket|"
               r"Appmon Drive|Accelerator|\bVital\b|Digimon Twin|Digimon Accel"),
    ("tcg", r"Card Game|\(DCG\)|Hyper Colosseum|Battle Terminal|Digimon Collectors Card|Battle-spirits|DCGMakeLink|"
            r"^(?:Bo|St|Sp|Ta|Vj|Dw|Da|DM|Dα|BT\d*|EX\d*|ST\d*|RB\d*|LM)-?\d"),
    ("anime", r"Digimon Adventure|Digimon Tamers|Digimon Frontier|Digimon Savers|Digimon Data Squad|Digimon Xros Wars|Digimon Fusion|"
              r"Digimon Universe: Appli|Appmon|Ghost Game|Last Evolution|Our War Game|Movie|Hurricane|Runaway Locomotive|"
              r"Battle of Adventurers|Revenge of Diaboromon|Ultimate Power|tri\.|Digimon Beatbreak|kizuna", re.I),
]
CAT_RE = [(c, re.compile(p, re.I)) for c, p, *_ in CAT_RULES]

# 애니 회차 템플릿 {{rfe|코드|화|제목}} 의 코드 → 작품
ANIME_CODES = {
    "DA": "Digimon Adventure", "DA:": "Digimon Adventure: (2020)", "DA02": "Digimon Adventure 02", "D02": "Digimon Adventure 02",
    "DT": "Digimon Tamers", "DF": "Digimon Frontier", "DS": "Digimon Savers", "DSav": "Digimon Savers",
    "DX": "Digimon Xros Wars", "DXW": "Digimon Xros Wars", "XW": "Digimon Xros Wars", "DXH": "Digimon Xros Wars Hunters",
    "DU": "Digimon Universe: Appli Monsters", "DGG": "Digimon Ghost Game", "GG": "Digimon Ghost Game",
    "tri": "Digimon Adventure tri.", "DAt": "Digimon Adventure tri.", "DBB": "Digimon Beatbreak", "DB": "Digimon Beatbreak",
    "ZT": "Digimon Adventure: (2020)",
}

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
SKIP_TARGET = re.compile(r"Colors and Levels|Attributes and Levels|Levels#|^Any |DigiXros|Jogress$|Evolution$", re.I)
STRIP_CHARS = re.compile(r"[\u200b-\u200f\ufeff]")
XROS_PLUS = re.compile(
    r"\s+\((Starmons|Revolmon|Cyberdramon|Skull Knightmon|Golemon|Cyber Launcher|Jet Sparrow|Dorulu Cannon|Skull Greymon|Star Sword)\)$"
)


def clean_str(s):
    return STRIP_CHARS.sub("", s or "").strip()


def wikimon_query_title(api_name):
    """Digi-API 영문명을 Wikimon 문서 제목 형식으로 변환"""
    if api_name == "Hackmon":
        return "Huckmon"
    if api_name == "Great King Sukamon":
        return "Great King Scumon"
    s = XROS_PLUS.sub(r" + \1", api_name)
    return re.sub(r"^([^(]*[^\s(])\((.+)\)$", r"\1: \2", s)


def norm_target(name):
    s = clean_str(name).lower()
    s = s.replace("scumon", "sukamon").replace("huckmon", "hackmon")
    return re.sub(r"[^a-z0-9]", "", s)


def section(text, name):
    m = re.search(r"^=+\s*" + name + r"\s*=+\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(r"^=+[^=\n]+=+\s*$", rest, re.M)
    return rest[: end.start()] if end else rest


def split_templates(line):
    """줄에서 {{...}} 템플릿(중첩 포함)과 <ref>...</ref> 를 뽑아내고, 나머지 본문을 돌려줌"""
    templates, out, depth, buf, i = [], [], 0, "", 0
    while i < len(line):
        if line.startswith("{{", i):
            if depth == 0:
                buf = ""
            depth += 1
            buf += "{{"
            i += 2
            continue
        if line.startswith("}}", i) and depth:
            depth -= 1
            buf += "}}"
            i += 2
            if depth == 0:
                templates.append(buf)
            continue
        if depth:
            buf += line[i]
        else:
            out.append(line[i])
        i += 1
    body = "".join(out)
    refs = re.findall(r"<ref[^>/]*>(.*?)</ref>", body, re.S)
    named = re.findall(r"<ref\s+name\s*=\s*\"?([^\"/>]+?)\"?\s*/>", body)
    body = re.sub(r"<ref[^>/]*>.*?</ref>|<ref[^>]*/>", "", body, flags=re.S)
    return body, templates, refs, named


def classify(name):
    for cat, rx in CAT_RE:
        if rx.search(name):
            return cat
    return "other"


def sources_from(templates, refs, named, ref_defs, stats):
    out = []

    def add(cat, name):
        name = clean_str(re.sub(r"''+", "", name))
        if name and (cat, name) not in out:
            out.append((cat, name))

    def from_text(t):
        links = [clean_str(l) for l in LINK.findall(t)]
        if links:
            for l in links:
                add(classify(l), l)
        else:
            plain = clean_str(re.sub(r"<[^>]+>|\{\{[^}]*\}\}|\[https?://\S+\s*([^\]]*)\]", r"\1", t))
            if plain:
                add(classify(plain), plain[:80])

    all_templates = list(templates)
    for n in named:
        if n in ref_defs:
            r_body, r_tpls, _, _ = split_templates(ref_defs[n])
            all_templates.extend(r_tpls)
            if r_body.strip():
                refs.append(r_body)
        else:
            stats["unresolved_ref"] += 1

    for t in all_templates:
        inner = t[2:-2]
        parts = [p.strip() for p in inner.split("|")]
        name = parts[0].lower()
        stats["template:" + name] += 1
        if name == "ref":
            from_text(inner[4:])
        elif name in ("rfc", "dcgmakelink"):
            add("tcg", "Digimon Card Game" if ("DCG" in inner or name == "dcgmakelink") else "Digimon Card Game (1999)")
        elif name == "rfe":
            code = parts[1] if len(parts) > 1 else ""
            stats["anime_code:" + code] += 1
            ep = parts[2] if len(parts) > 2 else ""
            add("anime", f"{ANIME_CODES.get(code, code)} #{ep}".strip())
        elif name in ("refd", "dd"):
            add("other", "Digimon Reference Book" if name == "refd" else "Digimon Dictionary")
        elif name in ("note", "nowrap"):
            continue
        else:
            from_text(inner)
    for r in refs:
        from_text(r)
    return out


def parse_list(text, by_norm, ref_defs, stats):
    items = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line.startswith("*"):
            continue
        line = line.lstrip("*").strip()
        body, templates, refs, named = split_templates(line)
        links = [clean_str(l) for l in LINK.findall(body)]
        if not links:
            continue
        raw_target = links[0]
        target = by_norm.get(norm_target(raw_target))
        if SKIP_TARGET.search(raw_target) or not target:
            stats["skipped_target"] += 1
            continue
        partners = []
        for l in links[1:]:
            p = by_norm.get(norm_target(l))
            if p and p != target and p not in partners:
                partners.append(p)
        cond = re.sub(r"\s+", " ", LINK.sub(lambda m: clean_str(m.group(1)), body)).strip()
        cond = re.sub(r"'''?", "", cond)
        cond = cond[len(raw_target):].strip() if cond.lower().startswith(raw_target.lower()) else cond
        src = sources_from(templates, refs, named, ref_defs, stats)
        if not src:
            stats["no_source"] += 1
        for cat, name in src:
            if cat == "other":
                stats["other:" + name] += 1
        item = {"t": target, "src": [[c, n] for c, n in src]}
        if partners:
            item["with"] = partners
        if cond and cond != "()":
            item["cond"] = cond.strip("() ")
        items.append(item)
    return items


def fetch_batch(session, titles, delay=DELAY):
    params = {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
              "titles": "|".join(titles), "format": "json", "formatversion": "2", "redirects": "1", "maxlag": "5"}
    for attempt in range(4):
        try:
            r = session.get(API, params=params, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if "error" in data and data["error"].get("code") == "maxlag":
                    print(f"  서버 바쁨(maxlag) — {delay}초 대기", flush=True)
                else:
                    return data
            else:
                print(f"  HTTP {r.status_code}: {r.text[:200]}", flush=True)
        except Exception as e:
            print(f"  오류: {e}", flush=True)
        time.sleep(delay * (attempt + 1))
    return None


TIME_BUDGET = 75 * 60  # 워크플로 제한 안에서 저장할 여유를 남김 — 못 끝낸 것은 다음 실행 때 이어서


def save(out, stats, missing):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": "https://wikimon.net (Evolves From / Evolves To)", "updated": time.strftime("%Y-%m-%d"),
                   "digimons": dict(sorted(out.items()))}, f, ensure_ascii=False, separators=(",", ":"))
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# Wikimon 수집 보고\n\n")
        f.write(f"- 문서 {len(out)}종, 찾지 못한 제목 {len(missing)}개\n")
        f.write(f"- 진화 항목: 출처 없음 {stats['no_source']}, 건너뛴 대상(카드게임 묶음 등) {stats['skipped_target']}, 해석 못한 이름 참조 {stats['unresolved_ref']}\n\n")
        f.write("## 찾지 못한 제목\n\n" + ", ".join(missing) + "\n\n")
        f.write("## 템플릿·애니 코드\n\n" + "\n".join(f"- {k}: {v}" for k, v in stats.most_common() if k.startswith(("template:", "anime_code:"))) + "\n\n")
        f.write("## 분류 안 된 출처(기타)\n\n" + "\n".join(f"- {k[6:]}: {v}" for k, v in stats.most_common(400) if k.startswith("other:")) + "\n")


def main():
    max_req = int(sys.argv[sys.argv.index("--max-requests") + 1]) if "--max-requests" in sys.argv else 10 ** 6
    delay = float(sys.argv[sys.argv.index("--delay") + 1]) if "--delay" in sys.argv else DELAY
    batch_size = int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else BATCH
    refresh = "--refresh" in sys.argv
    dex = json.load(open(DEX_FILE, encoding="utf-8"))["digimons"]
    all_titles = sorted({e["api_name"] for e in dex if e.get("api_name")})
    by_norm = {norm_target(t): t for t in all_titles}
    out = {} if refresh or not os.path.exists(OUT_FILE) else json.load(open(OUT_FILE, encoding="utf-8")).get("digimons", {})
    titles = [t for t in all_titles if t not in out]  # 이어받기: 아직 없는 것만 (전체 갱신은 --refresh)
    print(f"대상 {len(titles)}종 (보유 {len(out)}종)", flush=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    stats, missing, deferred_titles, started = collections.Counter(), [], [], time.time()
    for n, i in enumerate(range(0, len(titles), batch_size)):
        if n >= max_req or time.time() - started > TIME_BUDGET:
            print("요청 수·시간 한도 — 여기까지 저장", flush=True)
            break
        if n:
            time.sleep(delay)
        chunk = titles[i:i + batch_size]
        q_to_api = {wikimon_query_title(t): t for t in chunk}
        data = fetch_batch(session, list(q_to_api.keys()), delay=delay)
        if not data:
            print(f"  묶음 {n + 1} 실패 — 건너뜀", flush=True)
            continue
        q = data.get("query", {})
        back = dict(q_to_api)
        for m in (q.get("normalized") or []) + (q.get("redirects") or []):
            src = back.get(m["from"], m["from"])
            back[m["to"]] = src
        for page in q.get("pages", []):
            raw_title = page["title"]
            title = back.get(raw_title) or by_norm.get(norm_target(raw_title)) or raw_title
            if page.get("missing"):
                missing.append(title)
                continue
            if not page.get("revisions"):  # 응답 크기 한도로 잘린 문서
                stats["deferred"] += 1
                deferred_titles.append(title)
                continue
            text = page["revisions"][0]["slots"]["main"]["content"]
            ref_defs = dict(re.findall(r"<ref\s+name\s*=\s*\"?([^\">/]+?)\"?\s*>(.*?)</ref>", text, re.S))
            out[title] = {
                "from": parse_list(section(text, "Evolves From"), by_norm, ref_defs, stats),
                "to": parse_list(section(text, "Evolves To"), by_norm, ref_defs, stats),
            }
        print(f"  묶음 {n + 1}/{(len(titles) + batch_size - 1) // batch_size}: 누적 {len(out)}종", flush=True)
        save(out, stats, missing)  # 묶음마다 저장 (중간에 끊겨도 이어받기)

    # 응답 크기 한도로 잘린 문서(deferred)가 있으면 소량 묶음(10개씩)으로 이어서 수집
    for i in range(0, len(deferred_titles), 10):
        if time.time() - started > TIME_BUDGET:
            break
        time.sleep(delay)
        chunk = [t for t in deferred_titles[i:i + 10] if t not in out]
        if not chunk:
            continue
        q_to_api = {wikimon_query_title(t): t for t in chunk}
        data = fetch_batch(session, list(q_to_api.keys()), delay=delay)
        if not data:
            continue
        q = data.get("query", {})
        back = dict(q_to_api)
        for m in (q.get("normalized") or []) + (q.get("redirects") or []):
            back[m["to"]] = back.get(m["from"], m["from"])
        for page in q.get("pages", []):
            raw_title = page["title"]
            title = back.get(raw_title) or by_norm.get(norm_target(raw_title)) or raw_title
            if page.get("missing") or not page.get("revisions"):
                continue
            text = page["revisions"][0]["slots"]["main"]["content"]
            ref_defs = dict(re.findall(r"<ref\s+name\s*=\s*\"?([^\">/]+?)\"?\s*>(.*?)</ref>", text, re.S))
            out[title] = {
                "from": parse_list(section(text, "Evolves From"), by_norm, ref_defs, stats),
                "to": parse_list(section(text, "Evolves To"), by_norm, ref_defs, stats),
            }
        save(out, stats, missing)

    save(out, stats, missing)
    print(f"저장: {OUT_FILE} ({len(out)}종), 찾지 못함 {len(missing)}", flush=True)


if __name__ == "__main__":
    main()
