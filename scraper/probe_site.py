"""(임시) digimon.net 홈페이지 구조 점검: 원본 HTML을 tmp_site/ 에 저장하고 링크 구조를 출력"""
import os
import re

import requests

OUT = "tmp_site"
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (digimon-feed fan project; structure check)"})
PAGES = {
    "topic_list": "https://digimon.net/topic/?cat=ALL",
    "topic_detail": "https://digimon.net/topic/detail.php?id=2096",
    "product": "https://digimon.net/product/",
    "product_card": "https://digimon.net/product/card/",
    "product_goods": "https://digimon.net/product/goods/",
    "product_detail_item": "https://digimon.net/product/detail.php?item_type=1&id=970",
    "product_detail_jan": "https://digimon.net/product/detail.php?item_type=0&jan_cd=4573102725592000",
    "appmon_ko": "https://digimon.net/appmon_ko/",
    "history": "https://digimon.net/history/",
    "profile": "https://digimon.net/profile/",
    "iliad": "https://digimon.net/digitalworld-Iliad/",
}
for name, url in PAGES.items():
    try:
        r = S.get(url, timeout=30)
        with open(os.path.join(OUT, name + ".html"), "wb") as f:
            f.write(r.content)
        links = sorted(set(re.findall(r'href="([^"#]+)"', r.text)))
        print(f"=== {name} {url} -> HTTP {r.status_code}, {len(r.content)} bytes, final={r.url}, links={len(links)}")
        for l in [x for x in links if re.search(r"topic|product|appmon|detail|request|ajax|\.json|\.php", x)][:40]:
            print("    ", l)
        for m in sorted(set(re.findall(r"(?:getJSON|ajax|fetch)\(\s*['\"]([^'\"]+)", r.text)))[:10]:
            print("     json endpoint:", m)
    except Exception as e:
        print(f"=== {name} -> error {e}")
