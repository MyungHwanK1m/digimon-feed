"""도감 데이터 빌드

입력
  data/official/reference.json        공식 도감 기본 정보 (collect_official.py)
  public/data/digimon_all_index.json  Digi-API 인덱스 (generate_digidex.py) — 그림, 한국 더빙명
  data/official/api_map.json          (선택) 공식 디렉터리명 → Digi-API 이름 수동 매핑
  data/game_evolutions.json           (선택, 나중에) 게임 진화

출력
  public/data/dex.json, docs/data/dex.json   앱이 읽는 도감 데이터
  data/official/match_report.md               Digi-API 연결 결과 (확인용)

규칙
  - 번호: 공식 도감은 data/official/numbers.json 번호 그대로, 공식에 없는 Digi-API 디지몬은 EX-0001 부터 (Digi-API id 순)
  - 관련 디지몬: 공식 "관련된 디지몬" 목록 그대로. 진화 관계가 아니므로 진화 전/후로 추측하지 않음
  - 진화 전/후: 출처가 확실한 진화 데이터(data/game_evolutions.json)가 있을 때만
"""
import difflib
import json
import os
import re

REF_FILE = "data/official/reference.json"
INDEX_FILE = "public/data/digimon_all_index.json"
API_MAP_FILE = "data/official/api_map.json"
GAME_EVO_FILE = "data/game_evolutions.json"
APPMON_FILE = "data/official/appmon.json"
WIKIMON_FILE = "data/wikimon/evolutions.json"
EVO_DIRS = ["public/data/evo", "docs/data/evo"]
OUT_FILES = ["public/data/dex.json", "docs/data/dex.json"]
REPORT_FILE = "data/official/match_report.md"

# 공식 사이트 표기 → 앱 표기
LEVEL_NAME = {"유아기Ⅰ": "유년기 I", "유년기Ⅰ": "유년기 I", "유년기Ⅱ": "유년기 II"}
LEVEL_RANK = {"유년기 I": 1, "유년기 II": 2, "성장기": 3, "성숙기": 4, "완전체": 5, "궁극체": 6}
API_LEVEL = {"Baby I": "유년기 I", "Baby II": "유년기 II", "Child": "성장기", "Adult": "성숙기",
             "Perfect": "완전체", "Ultimate": "궁극체", "Armor": "아머체", "Hybrid": "하이브리드체", "Unknown": "불명"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def split_level(raw):
    """'성숙기(크로스워즈)' → ('성숙기', True)"""
    raw = (raw or "").strip()
    xros = "크로스워즈" in raw
    base = re.sub(r"\(?크로스워즈\)?", "", raw).strip() or ("크로스워즈" if xros and not raw.replace("크로스워즈", "") else "")
    return LEVEL_NAME.get(base, base) or "불명", xros


def load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def candidates(name_en):
    """공식 영문 표기에서 Digi-API 이름 후보(정규화) 만들기"""
    s = name_en.strip()
    out = [s]
    m = re.match(r"(.+?)[-_ ]X$", s, re.I)
    if m:
        out.append(f"{m.group(1)} (X-Antibody)")
    m = re.match(r"(.+?)[-_ ](2006)$", s)
    if m:
        out.append(f"{m.group(1)} (2006 Anime Version)")
    m = re.match(r"(.+?)[-_ ](XWARS|2010)$", s, re.I)
    if m:
        out.append(f"{m.group(1)} (2010 Anime Version)")
        out.append(m.group(1))
    m = re.match(r"(.+?):\s*(.+?)MODE$", s, re.I)
    if m:
        out.append(f"{m.group(1)}({m.group(2)} Mode)")
    out.append(re.sub(r"[-_ ](\d+|[A-Z])$", "", s))  # WHAMON_2, COREDRAMON_B 등 꼬리 제거
    return [norm(x) for x in out]


CAT_ORDER = ["anime", "game", "tcg", "device", "other"]


def write_wikimon_evolutions(entries):
    """{api_id: {"f": [진화 전...], "t": [진화 후...]}}, 각 항목 {"n": 도감번호, "c": [분류], "w": [작품], "p": [함께 진화 번호], "x": 조건}"""
    wk = load(WIKIMON_FILE, {}).get("digimons", {})
    if not wk:
        return
    no_by_name = {e["api_name"]: e["no"] for e in entries if e.get("api_name")}
    buckets, count = {}, 0
    for e in entries:
        w = wk.get(e.get("api_name") or "")
        if not w:
            continue
        item = {}
        for key, short in (("from", "f"), ("to", "t")):
            by_no = {}
            for it in w.get(key, []):
                no = no_by_name.get(it["t"])
                if not no or no == e["no"]:
                    continue
                cats = [c for c, _ in it.get("src", [])]
                works = [n for _, n in it.get("src", [])]
                partners = [no_by_name[p] for p in it.get("with", []) if p in no_by_name]
                cond = it.get("cond")
                if no not in by_no:
                    by_no[no] = {"n": no, "_c": set(cats), "w": list(dict.fromkeys(works)), "p": list(dict.fromkeys(partners)), "x": cond}
                else:
                    cur = by_no[no]
                    cur["_c"].update(cats)
                    for wn in works:
                        if wn not in cur["w"]:
                            cur["w"].append(wn)
                    for pn in partners:
                        if pn not in cur["p"]:
                            cur["p"].append(pn)
                    if cond and not cur.get("x"):
                        cur["x"] = cond
            rows = []
            for r in by_no.values():
                cats_sorted = sorted(r.pop("_c"), key=CAT_ORDER.index)
                row = {"n": r["n"], "c": cats_sorted or ["other"], "w": r["w"]}
                if r["p"]:
                    row["p"] = r["p"]
                if r.get("x"):
                    row["x"] = r["x"]
                rows.append(row)
            rows.sort(key=lambda r: (-len(r["w"]), "anime" not in r["c"]))
            if rows:
                item[short] = rows
        if item:
            buckets.setdefault(e["api_id"] // 100, {})[str(e["api_id"])] = item
            e["evo_wikimon"] = True
            count += 1
    for d in EVO_DIRS:
        os.makedirs(d, exist_ok=True)
        for n, items in buckets.items():
            with open(os.path.join(d, f"{n}.json"), "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wikimon 진화: {count}종")


def main():
    ref = load(REF_FILE, {"digimons": []})["digimons"]
    api = load(INDEX_FILE, {"digimons": []})["digimons"]
    manual = load(API_MAP_FILE, {})
    api_by_norm = {norm(a["name"]): a for a in api}
    api_by_name = {a["name"]: a for a in api}

    # 1) 공식 ↔ Digi-API 연결
    matched, used, report = {}, set(), {"exact": [], "rule": [], "fuzzy": [], "manual": [], "none": []}
    # 수동 지정을 먼저 확정해서 자동 연결이 같은 Digi-API 항목을 가져가지 않도록 함
    pre = {}
    for o in ref:
        a = api_by_name.get(manual.get(o["directory_name"], ""))
        if a:
            pre[o["directory_name"]] = a
            used.add(a["id"])
    for o in ref:
        d = o["directory_name"]
        level, _ = split_level(o.get("level"))
        hit, how = (pre[d], "manual") if d in pre else (None, None)
        if not hit:
            cands = candidates(o.get("name_en", ""))
            for i, c in enumerate(cands):
                if c in api_by_norm and api_by_norm[c]["id"] not in used:
                    hit, how = api_by_norm[c], ("exact" if i == 0 else "rule")
                    break
        if not hit:
            # 같은 단계 안에서 영문 표기 유사도 비교 (오탈자·표기 차이)
            key = norm(o.get("name_en", ""))
            pool = [a for a in api if a["id"] not in used and API_LEVEL.get(a.get("level")) == level]
            best = max(pool, key=lambda a: difflib.SequenceMatcher(None, key, norm(a["name"])).ratio(), default=None)
            if best and difflib.SequenceMatcher(None, key, norm(best["name"])).ratio() >= 0.86:
                hit, how = best, "fuzzy"
        if hit:
            assert how == "manual" or hit["id"] not in used, (d, hit["name"])
            matched[d] = hit
            used.add(hit["id"])
            report[how].append(f"| {o['no']} | {o['name_ko']} | {o.get('name_en','')} | {hit['name']} |")
        else:
            report["none"].append(f"| {o['no']} | {o['name_ko']} | {o.get('name_en','')} | - |")

    # 2) 도감 항목
    entries, by_dir = [], {}
    for o in ref:
        d = o["directory_name"]
        level, xros = split_level(o.get("level"))
        a = matched.get(d)
        dub = a.get("name_ko") if a else None
        e = {
            "no": f"{o['no']:04d}",
            "official": True,
            "dir": d,
            "name": o.get("name_ko") or o.get("name_en"),
            "name_en": o.get("name_en"),
            "level": level,
            "type": o.get("type") or "",
            "attribute": o.get("attribute") or "",
            "url": o.get("url"),
        }
        if xros:
            e["xros"] = True
        if o.get("x_antibody"):
            e["x_antibody"] = True
        if dub and re.search(r"[가-힣]", dub) and norm(dub) != norm(e["name"]) and dub.replace(" ", "") != e["name"].replace(" ", ""):
            e["name_dub"] = dub
        if a:
            e["api_id"] = a["id"]
            e["api_name"] = a["name"]
            if a.get("image"):
                e["image"] = a["image"]
        e["_related"] = o.get("related", [])
        entries.append(e)
        by_dir[d] = e

    ex_no = 1
    for a in sorted(api, key=lambda x: x["id"]):
        if a["id"] in used:
            continue
        ko = a.get("name_ko") if re.search(r"[가-힣]", a.get("name_ko") or "") else None
        e = {
            "no": f"EX-{ex_no:04d}",
            "official": False,
            "name": ko or a["name"],
            "name_en": a["name"],
            "level": API_LEVEL.get(a.get("level"), "불명"),
            "type": "",
            "attribute": "",
            "api_id": a["id"],
            "api_name": a["name"],
        }
        if a.get("image"):
            e["image"] = a["image"]
        entries.append(e)
        ex_no += 1

    # 3) 관련 디지몬: 공식 "관련된 디지몬" 목록을 그대로 (공식 페이지 순서)
    #    ※ 이 목록은 진화 관계가 아님 (예: 밀레니엄몬 ↔ 피라니몬). 단계로 진화 전/후를 추측하지 않음
    #    진화 전/후는 출처가 확실한 데이터(data/game_evolutions.json 등)가 있을 때만 채움
    game = load(GAME_EVO_FILE, {})  # {"<no>": {"prior": [...], "next": [...], "source": "..."}}
    for e in entries:
        no = e["no"]
        evo = {}
        related = list(dict.fromkeys(by_dir[rd]["no"] for rd in e.pop("_related", []) or [] if rd in by_dir and by_dir[rd]["no"] != no))
        if related:
            evo["related"] = related
        if no in game:
            g = game[no]
            for k in ("prior", "next"):
                if g.get(k):
                    evo[k] = g[k]
            if g.get("source"):
                evo["source"] = g["source"]
        if evo:
            e["evolution"] = evo

    # 3-1) Wikimon 진화 (출처 포함) → data/evo/<api_id//100>.json (상세 화면에서 필요한 조각만 받음)
    write_wikimon_evolutions(entries)

    # 아프몬 도감 (공식 appmon_ko): 번호 A-001 = 공식 id
    appmons = []
    for a in sorted(load(APPMON_FILE, {"appmons": []})["appmons"], key=lambda x: x["id"]):
        no = f"A-{a['id']:03d}"
        item = {"no": no, "kind": "appmon", "official": True, "name": a.get("name_ko") or no,
                "level": a.get("grade") or "불명", "app": a.get("app", ""), "attribute": a.get("attribute", ""),
                "url": a.get("url")}
        rel = [f"A-{r:03d}" for r in a.get("related", [])]
        if rel:
            item["evolution"] = {"related": rel}
        appmons.append(item)

    data = {
        "source": "digimon.net/reference_ko (기본 정보) + Digi-API (그림·더빙명)",
        "official_total": len(ref),
        "ex_total": ex_no - 1,
        "appmon_total": len(appmons),
        "digimons": entries,
        "appmons": appmons,
    }
    for target in OUT_FILES:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"저장: {target}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# 공식 도감 ↔ Digi-API 연결 결과\n\n")
        f.write("자동 생성 파일입니다. 잘못 연결된 항목은 `data/official/api_map.json`에 `\"공식 디렉터리명\": \"Digi-API 이름\"`으로 지정하세요.\n\n")
        labels = {"exact": "영문명 일치", "rule": "표기 규칙(X항체·2006·모드 등)", "fuzzy": "유사도 (확인 필요)", "manual": "수동 지정", "none": "연결 안 됨 (공식 전용)"}
        for k in ["fuzzy", "rule", "manual", "none", "exact"]:
            rows = report[k]
            f.write(f"## {labels[k]}: {len(rows)}건\n\n")
            if k == "exact":
                f.write("(목록 생략)\n\n")
                continue
            f.write("| 번호 | 공식 이름 | 공식 영문 | Digi-API |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n")
    print("연결: " + ", ".join(f"{k} {len(v)}" for k, v in report.items()) + f" / EX {ex_no - 1}종")


if __name__ == "__main__":
    main()
