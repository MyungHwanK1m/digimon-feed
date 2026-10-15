"""(임시) 도감 화면 미리보기·그림 출처 점검 (헤더·응답만 출력)"""
import requests

S = requests.Session()
UA = {"User-Agent": "Mozilla/5.0 (digimon-feed fan project; check)"}


def show(label, r):
    h = {k: v for k, v in r.headers.items() if k.lower() in (
        "content-type", "content-length", "x-frame-options", "content-security-policy",
        "access-control-allow-origin", "cache-control", "cf-ray", "server")}
    print(f"=== {label}: HTTP {r.status_code} bytes={len(r.content)} {h}")


def get(label, url, **headers):
    try:
        r = S.get(url, headers={**UA, **headers}, timeout=30)
        show(label, r)
        return r
    except Exception as e:
        print(f"=== {label}: error {e}")


get("official detail (iframe/CORS headers)", "https://digimon.net/reference_ko/detail.php?directory_name=agumon", Origin="https://example.github.io")
get("official image, no referer", "https://digimon.net/cimages/digimon/agumon.jpg")
get("official image, foreign referer", "https://digimon.net/cimages/digimon/agumon.jpg", Referer="https://example.github.io/")
r = get("official img_detail (other illustrations)", "https://digimon.net/reference_ko/img_detail.php?directory_name=agumon")
if r is not None and r.ok:
    import re
    print("   images:", sorted(set(re.findall(r'(?:src|href)="([^"]*cimages[^"]*)"', r.text)))[:20])
r = get("digimoncard.io search", "https://digimoncard.io/api-public/search.php?n=Agumon")
if r is not None and r.ok:
    try:
        data = r.json()
        print("   cards:", len(data), "sample keys:", list(data[0].keys())[:20] if data else None)
        print("   sample:", [(c.get("id"), c.get("name"), c.get("type")) for c in data[:6]])
    except Exception as e:
        print("   not json:", r.text[:200])
get("digimoncard image", "https://images.digimoncard.io/images/cards/BT1-010.jpg", Referer="https://example.github.io/")
get("wikimon dot image", "https://wikimon.net/images/e/ee/Agumon_vpet_dm.gif", Referer="https://example.github.io/")
get("wikimon api", "https://wikimon.net/api.php?action=query&list=search&srsearch=Agumon&format=json")
