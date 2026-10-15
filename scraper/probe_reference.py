"""(임시) digimon.net/reference_ko 구조 점검: 원본 HTML·JS를 tmp_probe/ 에 저장하고 요약을 출력"""
import os
import re

import requests

OUT = "tmp_probe"
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (digimon-feed fan project; structure check)"})


def save(name, url):
    try:
        r = S.get(url, timeout=30)
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(r.content)
        print(f"=== {url} -> HTTP {r.status_code}, {len(r.content)} bytes, type={r.headers.get('content-type')}")
        return r.text if r.ok else ""
    except Exception as e:
        print(f"=== {url} -> error {e}")
        return ""


save("robots.txt", "https://digimon.net/robots.txt")
top = save("reference_ko.html", "https://digimon.net/reference_ko/")
links = sorted(set(re.findall(r'href="([^"]+)"', top)))
print("links:", len(links))
for l in links[:80]:
    print("  ", l)
scripts = sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', top)))
print("scripts:", scripts)
for i, s in enumerate(scripts):
    url = s if s.startswith("http") else requests.compat.urljoin("https://digimon.net/reference_ko/", s)
    js = save(f"script_{i}.js", url)
    for m in sorted(set(re.findall(r'["\']([^"\']*(?:json|api|search|list|detail)[^"\']*)["\']', js)))[:40]:
        print("   js ref:", m)
detail = next((l for l in links if "detail" in l), None)
if detail:
    url = detail if detail.startswith("http") else requests.compat.urljoin("https://digimon.net/reference_ko/", detail)
    save("detail_sample.html", url)
for cand in ["https://digimon.net/reference_ko/detail.php?directory_name=agumon",
             "https://digimon.net/reference_ko/search.php", "https://digimon.net/reference_ko/list.php"]:
    save(re.sub(r"[^a-z0-9]+", "_", cand.split("reference_ko/")[1]) + ".html", cand)
