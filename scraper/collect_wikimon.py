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
             r"Digimon Generations|Digimon Alysion|Digimon Con|Digimon Life|Digimon Ranch|DigiTama Hatch|Digimon Fight"),
    ("device", r"Pendulum|Digital Monster|Digivice|Vital Bracelet|Vital Hero|\bD-3\b|D-Ark|D-Power|D-Scanner|D-Tector|Digimon Mini|"
               r"Data Link|Xros Loader|\bBurst\b|\biC\b|\bTwin\b|Fusion Loader|\bVer\.|\bCOLOR\b|Dim Card|Digimon Pocket|"
               r"Appmon Drive|Accelerator|\bVital\b"),
    ("tcg", r"Card Game|\(DCG\)|Hyper Colosseum|Battle Terminal|Digimon Collectors Card"),
    ("anime", r"Digimon Adventure|Digimon Tamers|Digimon Frontier|Digimon Savers|Digimon Data Squad|Digimon Xros Wars|Digimon Fusion|"
              r"Digimon Universe: Appli|Appmon|Ghost Game|Last Evolution|Our War Game|Movie|Hurricane|Runaway Locomotive|"
              r"Battle of Adventurers|Revenge of Diaboromon|Ultimate Power|tri\.|Digimon Beatbreak|kizuna", re.I),
]
CAT_RE = [(c, re.compile(p, re.I)) for c, p, *_ in CAT_RULES]

# 애니 회차 템플릿 {{rfe|코드|화|제목}} 의 코드 → 작품
ANIME_CODES = {
    "DA": "Digimon Adventure", "DA:": "Digimon Adventure: (2020)", "DA02": "Digimon Adventure 02", "D02": "Digimon Adventure 02",
    "DT": "Digimon Tamers", "DF": "Digimon Frontier", "DS": "Digimon Savers", "DSav": "Digimon Savers",
    "DX": "Digimon Xros Wars", "DXW": "Digimon Xros Wars", "DXH": "Digimon Xros Wars Hunters", "DU": "Digimon Universe: Appli Monsters",
    "DGG": "Digimon Ghost Game", "tri": "Digimon Adventure tri.", "DAt": "Digimon Adventure tri.", "DBB": "Digimon Beatbreak",
}

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
SKIP_TARGET = re.compile(r"Colors and Levels|Attributes and Levels|Levels#|^Any |DigiXros|Jogress$|Evolution$", re.I)


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
        name = re.sub(r"''+", "", name).strip()
        if name and (cat, name) not in out:
            out.append((cat, name))

    def from_text(t):
        links = [l.strip() for l in LINK.findall(t)]
        if links:
            for l in links:
                add(classify(l), l)
        else:
            plain = re.sub(r"<[^>]+>|\{\{[^}]*\}\}|\[https?://\S+\s*([^\]]*)\]", r"\1", t).strip()
            if plain:
                add(classify(plain), plain[:80])

    for t in templates:
        inner = t[2:-2]
        parts = [p.strip() for p in inner.split("|")]
        name = parts[0].lower()
        stats["template:" + name] += 1
        if name == "ref":
            from_text(inner[4:])
        elif name == "rfc":
            add("tcg", "Digimon Card Game" if "DCG" in inner else "Digimon Card Game (1999)")
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
    for n in named:
        if n in ref_defs:
            from_text(ref_defs[n])
        else:
            stats["unresolved_ref"] += 1
    return out


def parse_list(text, titles, ref_defs, stats):
    items = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line.startswith("*"):
            continue
        line = line.lstrip("*").strip()
        body, templates, refs, named = split_templates(line)
        links = [l.strip() for l in LINK.findall(body)]
        if not links:
            continue
        target = links[0]
        if SKIP_TARGET.search(target) or target not in titles:
            stats["skipped_target"] += 1
            continue
        partners = [l for l in links[1:] if l in titles and l != target]
        cond = re.sub(r"\s+", " ", LINK.sub(lambda m: m.group(1), body)).strip()
        cond = re.sub(r"'''?", "", cond)
        cond = cond[len(target):].strip() if cond.startswith(target) else cond
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


def fetch_batch(session, titles):
    params = {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
              "titles": "|".join(titles), "format": "json", "formatversion": "2", "redirects": "1"}
    for attempt in range(4):
        try:
            r = session.get(API, params=params, timeout=90)
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code}")
        except Exception as e:
            print(f"  오류: {e}")
        time.sleep(DELAY * (attempt + 1))
    return None


def main():
    max_req = int(sys.argv[sys.argv.index("--max-requests") + 1]) if "--max-requests" in sys.argv else 10 ** 6
    dex = json.load(open(DEX_FILE, encoding="utf-8"))["digimons"]
    titles = sorted({e["api_name"] for e in dex if e.get("api_name")})
    title_set = set(titles)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    out, stats, missing = {}, collections.Counter(), []
    for n, i in enumerate(range(0, len(titles), BATCH)):
        if n >= max_req:
            break
        if n:
            time.sleep(DELAY)
        chunk = titles[i:i + BATCH]
        data = fetch_batch(session, chunk)
        if not data:
            print(f"  묶음 {n + 1} 실패 — 건너뜀")
            continue
        q = data.get("query", {})
        back = {}
        for m in (q.get("normalized") or []) + (q.get("redirects") or []):
            back[m["to"]] = back.get(m["from"], m["from"])
        for page in q.get("pages", []):
            title = back.get(page["title"], page["title"])
            if page.get("missing") or not page.get("revisions"):
                missing.append(title)
                continue
            text = page["revisions"][0]["slots"]["main"]["content"]
            ref_defs = dict(re.findall(r"<ref\s+name\s*=\s*\"?([^\">/]+?)\"?\s*>(.*?)</ref>", text, re.S))
            out[title] = {
                "from": parse_list(section(text, "Evolves From"), title_set, ref_defs, stats),
                "to": parse_list(section(text, "Evolves To"), title_set, ref_defs, stats),
            }
        print(f"  묶음 {n + 1}/{(len(titles) + BATCH - 1) // BATCH}: 누적 {len(out)}종")

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(OUT_FILE):  # 일부만 받은 실행이면 기존 데이터와 합침
        old = json.load(open(OUT_FILE, encoding="utf-8")).get("digimons", {})
        old.update(out)
        out = old
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": "https://wikimon.net (Evolves From / Evolves To)", "updated": time.strftime("%Y-%m-%d"),
                   "digimons": dict(sorted(out.items()))}, f, ensure_ascii=False, separators=(",", ":"))
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# Wikimon 수집 보고\n\n")
        f.write(f"- 문서 {len(out)}종, 찾지 못한 제목 {len(missing)}개\n")
        f.write(f"- 진화 항목: 출처 없음 {stats['no_source']}, 건너뛴 대상(카드게임 묶음 등) {stats['skipped_target']}, 해석 못한 이름 참조 {stats['unresolved_ref']}\n\n")
        f.write("## 찾지 못한 제목\n\n" + ", ".join(missing) + "\n\n")
        f.write("## 템플릿·애니 코드\n\n" + "\n".join(f"- {k}: {v}" for k, v in stats.most_common() if k.startswith(("template:", "anime_code:"))) + "\n\n")
        f.write("## 분류 안 된 출처(기타) 상위 150\n\n" + "\n".join(f"- {k[6:]}: {v}" for k, v in stats.most_common() if k.startswith("other:"))[:20000] + "\n")
    print(f"저장: {OUT_FILE} ({len(out)}종), 찾지 못함 {len(missing)}")


if __name__ == "__main__":
    main()
