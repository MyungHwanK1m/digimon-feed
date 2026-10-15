"""(임시) digimon.net 홈페이지 구조 점검: 원본 HTML을 tmp_site/ 에 저장하고 링크 구조를 출력"""
import os
import re

import requests

OUT = "tmp_site"
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (digimon-feed fan project; structure check)"})
PAGES = {
    "appmon_detail": "https://digimon.net/appmon_ko/detail.php?id=1",
    "topic_cat1": "https://digimon.net/topic/?cat=1",
    "product_game": "https://digimon.net/product/game/",
    "product_others": "https://digimon.net/product/others/",
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


# 번역 경로 점검
for label, url in [
    ("mymemory", "https://api.mymemory.translated.net/get?q=" + requests.utils.quote("A small dinosaur Digimon.") + "&langpair=en|ko"),
    ("google-gtx", "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q=" + requests.utils.quote("A small dinosaur Digimon. It is brave.")),
]:
    try:
        r = S.get(url, timeout=30, headers={"Origin": "https://example.github.io"})
        print(f"=== {label}: HTTP {r.status_code} acao={r.headers.get('access-control-allow-origin')} body={r.text[:300]}")
    except Exception as e:
        print(f"=== {label}: error {e}")
