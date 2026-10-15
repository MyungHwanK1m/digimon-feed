"""(임시) 인스타그램 게시물을 공개 검색 피드로 가져올 수 있는지 점검"""
import feedparser
import requests

QUERIES = [
    "site:instagram.com 디지몬",
    "site:instagram.com digimon",
    "site:instagram.com デジモン",
    "site:instagram.com digimon_official OR digimoncard OR bandaispirits digimon",
]

for q in QUERIES:
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    print(f"=== Google News RSS: {q!r} -> {len(feed.entries)} entries")
    for e in feed.entries[:8]:
        src = getattr(getattr(e, "source", None), "href", "") if hasattr(e, "source") else ""
        print(f"   {getattr(e, 'published', '')[:16]} | {e.title[:90]} | {src}")

for name in ["digimon_official", "digimoncard_official"]:
    try:
        r = requests.get(f"https://www.instagram.com/{name}/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15, allow_redirects=False)
        print(f"=== instagram.com/{name}/ -> HTTP {r.status_code}, location={r.headers.get('location')}, bytes={len(r.content)}")
    except Exception as ex:
        print(f"=== instagram.com/{name}/ -> error {ex}")
