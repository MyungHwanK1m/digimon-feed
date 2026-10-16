"""TCG 카드 데이터 수집 및 매칭 스크립트

digimoncard.io API로부터 전체 디지몬 카드(3,700여 장)를 조회하여,
도감 내 각 디지몬(Digi-API api_name 기준)의 대표 TCG 카드 이미지 URL을 data/tcg/cards.json에 매핑 저장합니다.
"""
import json
import os
import re
import urllib.request

INDEX_FILE = "public/data/digimon_all_index.json"
OUT_FILE = "data/tcg/cards.json"

TCG_ALIASES = {
    'omegamon': 'omnimon',
    'dukemon': 'gallantmon',
    'tailmon': 'gatomon',
    'vamdemon': 'myotismon',
    'piyomon': 'biyomon',
    'plotmon': 'salamon',
    'diablomon': 'diaboromon',
    'mugendramon': 'machinedramon',
    'pinochimon': 'puppetmon',
    'piemon': 'piedmon',
    'hououmon': 'phoenixmon',
    'heraklekabuterimon': 'herculeskabuterimon',
    'atlurkabuterimon': 'megakabuterimon',
    'holyangemon': 'magnaangemon',
    'ofanimon': 'ophanimon',
    'beelzebumon': 'beelzemon',
    'lordknightmon': 'crusadermon',
    'duftmon': 'leopardmon',
    'sleipmon': 'kentaurosmon',
    'craniummon': 'craniamon',
    'ulforcevdramon': 'ulforceveedramon',
    'vdramon': 'veedramon',
    'aerovdramon': 'aeroveedramon',
    'vmon': 'veemon',
    'xvmon': 'exveemon',
    'fladramon': 'flamedramon',
    'lighdramon': 'raidramon',
    'armadimon': 'armadillomon',
    'dukemoncrimsonmode': 'gallantmoncrimsonmode',
    'omegamonmercifulmode': 'omnimonmercifulmode',
    'beelzebumonblastmode': 'beelzemonblastmode',
    'magnamon': 'magnamon',
    'chibimon': 'demiveemon',
    'chibikomon': 'chibimon',
    'terriermon': 'terriermon',
    'lopmon': 'lopmon',
    'renamon': 'renamon',
    'lucemon': 'lucemon',
    'susanoomon': 'susanoomon',
    'astamon': 'astamon',
    'baalmon': 'reapmon',
}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def main():
    print("Fetching Digimon TCG cards from digimoncard.io...")
    req = urllib.request.Request(
        "https://digimoncard.io/api-public/search?type=Digimon",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        cards = json.loads(res.read().decode("utf-8"))
    print(f"Fetched {len(cards)} TCG cards.")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    # Build card lookup by normalized name
    card_by_norm = {}
    for c in cards:
        cid = c.get("id")
        cname = c.get("name")
        if not cid or not cname:
            continue
        nk = norm(cname)
        if nk not in card_by_norm:
            card_by_norm[nk] = []
        card_by_norm[nk].append(cid)

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        api_index = json.load(f)["digimons"]

    matched = {}
    for a in api_index:
        name = a.get("name") or ""
        # E.g. "Agumon (Black)" -> "Agumon", "Agumon (X-Antibody)" -> "Agumon X-Antibody"
        cleaned_no_paren = re.sub(r'\s*\(.*?\)\s*', '', name).strip()
        cleaned_x = name.replace("X-Antibody", "X Antibody").replace("(X-Antibody)", "X Antibody").strip()
        
        candidates = [
            norm(name),
            norm(cleaned_no_paren),
            norm(cleaned_x),
            TCG_ALIASES.get(norm(name)),
            TCG_ALIASES.get(norm(cleaned_no_paren)),
            TCG_ALIASES.get(norm(cleaned_x)),
        ]
        candidates = [c for c in candidates if c]

        found_id = None
        for cand in candidates:
            if cand in card_by_norm:
                found_id = card_by_norm[cand][0]
                break

        if found_id:
            matched[name] = f"https://images.digimoncard.io/images/cards/{found_id}.jpg"

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)

    print(f"Successfully matched and saved {len(matched)} TCG card images to {OUT_FILE}")


if __name__ == "__main__":
    main()
