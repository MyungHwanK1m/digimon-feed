"""(임시) digimon.net 홈페이지 구조 점검: 원본 HTML을 tmp_site/ 에 저장하고 링크 구조를 출력"""
import os
import re

import requests

OUT = "tmp_site"
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (digimon-feed fan project; structure check)"})
PAGES = {
    "home_ko": "https://digimon.net/ko/",
    "home": "https://digimon.net/",
    "news": "https://digimon.net/news/",
    "news_ko": "https://digimon.net/ko/news/",
    "goods": "https://digimon.net/goods/",
    "appmon_ko": "https://digimon.net/appmon_reference_ko/",
    "appmon": "https://digimon.net/appmon_reference/",
    "about_ko": "https://digimon.net/about_ko/",
    "rss": "https://digimon.net/feed/",
    "sitemap": "https://digimon.net/sitemap.xml",
}
for name, url in PAGES.items():
    try:
        r = S.get(url, timeout=30)
        with open(os.path.join(OUT, name + ".html"), "wb") as f:
            f.write(r.content)
        links = sorted(set(re.findall(r'href="([^"#]+)"', r.text)))
        print(f"=== {name} {url} -> HTTP {r.status_code}, {len(r.content)} bytes, final={r.url}, links={len(links)}")
        for l in [x for x in links if re.search(r"news|goods|appmon|reference|detail|toy|game|card|\.json|rss|feed", x)][:40]:
            print("    ", l)
    except Exception as e:
        print(f"=== {name} -> error {e}")
