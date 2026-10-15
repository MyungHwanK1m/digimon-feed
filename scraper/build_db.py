"""디지몬 도감 DB 빌드

원본: data/digidex_db.yaml (직접 수정)
출력: public/data/digidex_db.json, docs/data/digidex_db.json (웹앱이 읽음)
      EVOLUTION.md 의 "진화 다이어그램" 구역 (Mermaid, GitHub에서 그림으로 보임)

사용: python scraper/build_db.py          # 검사 + 생성
      python scraper/build_db.py --check  # 검사만 (파일 변경 없음)
오류(없는 디지몬 이름 등)가 있으면 종료 코드 1로 끝나고 아무 파일도 쓰지 않습니다.
"""
import json
import os
import re
import sys

import yaml

DB_FILE = "data/digidex_db.yaml"
INDEX_FILE = "public/data/digimon_all_index.json"
OUT_FILES = ["public/data/digidex_db.json", "docs/data/digidex_db.json"]
DOC_FILE = "EVOLUTION.md"
BEGIN = "<!-- BEGIN:DIAGRAMS (scraper/build_db.py 가 자동 생성 — 직접 수정하지 마세요) -->"
END = "<!-- END:DIAGRAMS -->"

ENTRY_FIELDS = {"dex"}
EVOLUTION_FIELDS = {"prior", "next", "jogress"}
DEX_FIELDS = {"name_ko", "name_ja", "level", "attribute", "type", "images", "skills", "profile", "evolution"}
LEVEL_RANK = {"Baby I": 1, "Baby II": 2, "Child": 3, "Adult": 4, "Perfect": 5, "Ultimate": 6}
LEVEL_KO = {"Baby I": "유년기 I", "Baby II": "유년기 II", "Child": "성장기", "Adult": "성숙기",
            "Perfect": "완전체", "Ultimate": "궁극체", "Armor": "아머체", "Hybrid": "하이브리드체"}


def norm(s):
    return re.sub(r"[^a-z0-9À-ɏ]", "", str(s).lower())


def load():
    with open(DB_FILE, encoding="utf-8") as f:
        db = yaml.safe_load(f) or {}
    with open(INDEX_FILE, encoding="utf-8") as f:
        index = {norm(d["name"]): d for d in json.load(f)["digimons"]}
    return db, index


def validate(db, index):
    errors, warnings = [], []
    for key, entry in db.items():
        where = f"[{key}]"
        if norm(key) not in index:
            errors.append(f"{where} Digi-API에 없는 이름입니다 (영문명을 인덱스와 똑같이 적어주세요)")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{where} 내용이 비어 있거나 형식이 잘못됐습니다")
            continue
        for k in entry:
            if k not in ENTRY_FIELDS:
                warnings.append(f"{where} 알 수 없는 항목 '{k}' (무시됨)")
        dex = entry.get("dex") or {}
        for k in dex:
            if k not in DEX_FIELDS:
                warnings.append(f"{where} dex 에 알 수 없는 항목 '{k}'")
        for sk in dex.get("skills") or []:
            if not isinstance(sk, dict) or "name" not in sk:
                errors.append(f"{where} skills 항목은 {{name, desc}} 형태여야 합니다")
        evo = dex.get("evolution") or {}
        for k in evo:
            if k not in EVOLUTION_FIELDS:
                warnings.append(f"{where} evolution 에 알 수 없는 항목 '{k}'")
        cur = LEVEL_RANK.get(index[norm(key)].get("level"))
        for side, step in (("prior", -1), ("next", 1)):
            for name in evo.get(side) or []:
                target = index.get(norm(name))
                if not target:
                    errors.append(f"{where} evolution.{side} 의 '{name}' 은(는) Digi-API에 없는 이름입니다")
                    continue
                r = LEVEL_RANK.get(target.get("level"))
                if cur and r and (r - cur) * step not in (0, 1):
                    warnings.append(f"{where} evolution.{side} '{name}': 단계가 {abs(r - cur)}칸 차이 (워프진화·조그레스면 무시)")
    return errors, warnings


def build_json(db, index):
    out = []
    for key, entry in db.items():
        d = index[norm(key)]
        item = {"name": d["name"], "id": d["id"]}
        dex = {k: v for k, v in (entry.get("dex") or {}).items() if k in DEX_FIELDS}
        if dex.get("evolution"):
            dex["evolution"] = {k: v for k, v in dex["evolution"].items() if k in EVOLUTION_FIELDS}
        if dex:
            item["dex"] = dex
        out.append(item)
    return {"source": DB_FILE, "total": len(out), "digimons": out}


def label(name, db, index):
    d = index[norm(name)]
    dex = (db.get(d["name"]) or {}).get("dex") or {}
    ko = dex.get("name_ko") or d.get("name_ko") or d["name"]
    if not re.search(r"[가-힣]", ko):
        ko = d["name"]
    lv = LEVEL_KO.get(d.get("level"), "")
    text = f"{ko}<br/><small>{lv}</small>" if lv else ko
    return text.replace('"', "'")


def diagrams(db, index):
    # 도감(dex)의 evolution 에 적힌 진화를 하나의 다이어그램으로
    edges = {}
    for key, entry in db.items():
        evo = ((entry.get("dex") or {}).get("evolution")) or {}
        me = index[norm(key)]["name"]
        for p in evo.get("prior") or []:
            edges[(index[norm(p)]["name"], me)] = bool(evo.get("jogress"))
        for n in evo.get("next") or []:
            edges.setdefault((me, index[norm(n)]["name"]), False)

    parts = []
    if edges:
        ids = {}
        def nid(name):
            if name not in ids:
                ids[name] = f"n{len(ids)}"
            return ids[name]
        lines = []
        for (a, b), jog in edges.items():
            arrow = '-. "조그레스" .->' if jog else "-->"
            lines.append(f"  {nid(a)} {arrow} {nid(b)}")
        nodes = [f'  {i}["{label(n, db, index)}"]' for n, i in ids.items()]
        parts.append("### 도감 진화 루트\n\n```mermaid\nflowchart TD\n" + "\n".join(nodes + lines) + "\n```\n")
    else:
        parts.append("### 도감 진화 루트\n\n아직 `evolution`이 적힌 도감 항목이 없습니다. 모든 디지몬이 Digi-API 진화 목록으로 표시됩니다.\n")

    rows = []
    for k, e in db.items():
        dex = e.get("dex") or {}
        if not dex:
            continue
        evo = dex.get("evolution") or {}
        route = " / ".join(filter(None, [
            ("← " + ", ".join(evo.get("prior") or [])) if evo.get("prior") else "",
            ("→ " + ", ".join(evo.get("next") or [])) if evo.get("next") else "",
        ])) or "-"
        rows.append(f"| {dex.get('name_ko', k)} | {k} | {len(dex.get('skills') or [])} | {'있음' if dex.get('profile') else '-'} | {route} |")
    parts.append("### 도감 항목\n\n| 이름 | 키 | 기술 수 | 도감 설정 | 진화 루트 |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
    return "\n".join(parts)


def update_doc(body):
    with open(DOC_FILE, encoding="utf-8") as f:
        doc = f.read()
    block = f"{BEGIN}\n\n{body}\n{END}"
    if BEGIN in doc and END in doc:
        doc = doc[: doc.index(BEGIN)] + block + doc[doc.index(END) + len(END):]
    else:
        doc = doc.rstrip() + "\n\n## 진화 다이어그램\n\n" + block + "\n"
    with open(DOC_FILE, "w", encoding="utf-8") as f:
        f.write(doc)


def main():
    db, index = load()
    errors, warnings = validate(db, index)
    for w in warnings:
        print(f"[경고] {w}")
    for e in errors:
        print(f"[오류] {e}")
    if errors:
        print(f"오류 {len(errors)}건 — 파일을 생성하지 않았습니다.")
        sys.exit(1)
    print(f"검사 통과: {len(db)}종, 경고 {len(warnings)}건")
    if "--check" in sys.argv:
        return
    data = build_json(db, index)
    for target in OUT_FILES:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"저장: {target}")
    update_doc(diagrams(db, index))
    print(f"갱신: {DOC_FILE} 진화 다이어그램")


if __name__ == "__main__":
    main()
