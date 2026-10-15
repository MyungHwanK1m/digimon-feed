"""(임시) 게임 진화 데이터 후보 사이트 점검: 응답 상태와 링크 구조만 출력하고 원본은 tmp_games/ 에 저장"""
import os
import re

import requests

OUT = "tmp_games"
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (digimon-feed fan project; structure check)"})
CANDIDATES = [
    "https://www.grindosaur.com/en/games/digimon-story-time-stranger/digimon",
    "https://www.grindosaur.com/en/games/digimon-story-cyber-sleuth-hackers-memory/digimon",
    "https://www.grindosaur.com/robots.txt",
    "https://game8.co/games/Digimon-Story-Time-Stranger",
    "https://game8.co/robots.txt",
    "https://digimon.fandom.com/wiki/Digimon_Story:_Time_Stranger",
    "https://digimon.fandom.com/wiki/Digimon_Story:_Cyber_Sleuth_Hacker%27s_Memory",
    "https://wikimon.net/Digimon_Story:_Time_Stranger",
    "https://wikimon.net/Digimon_Story:_Cyber_Sleuth_Hacker%27s_Memory",
]
for i, url in enumerate(CANDIDATES):
    try:
        r = S.get(url, timeout=30)
        name = f"{i:02d}_" + re.sub(r"[^a-z0-9]+", "_", url.split("//", 1)[1].lower())[:80] + ".html"
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(r.content)
        links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        dig = [l for l in links if re.search(r"digimon|evol|digivol", l, re.I)]
        print(f"=== {url} -> HTTP {r.status_code}, {len(r.content)} bytes, links={len(links)}, digimon-links={len(dig)}")
        for l in dig[:25]:
            print("    ", l)
        if url.endswith("robots.txt"):
            print(r.text[:800])
    except Exception as e:
        print(f"=== {url} -> error {e}")
