"""TCG 카드 데이터 수집 및 매칭 스크립트

digimoncard.io API로부터 전체 디지몬 카드(3,700여 장)를 조회하여,
도감 내 각 디지몬(Digi-API api_name 기준)의 대표 TCG 카드 이미지 URL을 data/tcg/cards.json에 매핑 저장합니다.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonio import load_json, write_json  # noqa: E402

MIN_KEEP_RATIO = 0.9  # 기존 매칭 수의 90% 미만이면 일시 오류로 보고 저장하지 않음
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


def fetch_cards(tries=4):
    """429(요청 과다)·5xx·네트워크 오류는 잠시 기다렸다가 재시도"""
    req = urllib.request.Request(
        "https://digimoncard.io/api-public/search?type=Digimon",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            retry_after = e.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  요청 실패: {e}")
            wait = 30 * (attempt + 1)
        if attempt + 1 < tries:
            wait = min(wait, 120)
            print(f"  {wait}초 후 재시도 ({attempt + 1}/{tries})")
            time.sleep(wait)
    sys.exit("digimoncard.io 요청이 계속 실패했습니다 — 저장하지 않음")


def main():
    print("Fetching Digimon TCG cards from digimoncard.io...")
    cards = fetch_cards()
    if not isinstance(cards, list) or not cards:
        sys.exit(f"TCG 카드 응답이 비었거나 형식이 다릅니다 ({type(cards).__name__}) — 저장하지 않음")
    print(f"Fetched {len(cards)} TCG cards.")

    # Build card lookup by normalized name
    card_by_norm = {}
    for c in cards:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        cname = c.get("name")
        if not cid or not cname:
            continue
        card_by_norm.setdefault(norm(cname), []).append(cid)

    api_index = load_json(INDEX_FILE, {}).get("digimons", [])
    if not api_index:
        sys.exit(f"{INDEX_FILE} 가 비어 있음 — 저장하지 않음")

    matched = {}
    for a in api_index:
        name = a.get("name") or ""
        # E.g. "Agumon (Black)" -> "Agumon" (X항체 표기는 norm 이 기호를 지우므로 원래 이름 후보로 충분)
        cleaned_no_paren = re.sub(r'\s*\(.*?\)\s*', '', name).strip()
        candidates = [
            norm(name),
            norm(cleaned_no_paren),
            TCG_ALIASES.get(norm(name)),
            TCG_ALIASES.get(norm(cleaned_no_paren)),
        ]
        for cand in (c for c in candidates if c):
            if cand in card_by_norm:
                matched[name] = f"https://images.digimoncard.io/images/cards/{card_by_norm[cand][0]}.jpg"
                break

    old_count = len(load_json(OUT_FILE, {}))
    if not matched or (old_count and len(matched) < old_count * MIN_KEEP_RATIO):
        sys.exit(f"매칭이 비었거나 크게 줄었습니다 (기존 {old_count} → {len(matched)}) — 저장하지 않음")
    write_json(OUT_FILE, matched, indent=2)

    print(f"Successfully matched and saved {len(matched)} TCG card images to {OUT_FILE}")


if __name__ == "__main__":
    main()
