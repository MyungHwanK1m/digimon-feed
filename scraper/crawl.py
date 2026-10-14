import os
import json
import hashlib
import re
import email.utils
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup
import feedparser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
FEEDS_FILE = os.path.join(DATA_DIR, "digimon_feeds.json")
DOCS_DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "digimon_feeds.json"))
PUBLIC_DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "digimon_feeds.json"))

def parse_to_timestamp(date_str: str) -> int:
    """다양한 날짜 형식을 Unix timestamp(초)로 정규화"""
    if not date_str:
        return int(datetime.now().timestamp())
    
    date_str = str(date_str).strip()
    now = datetime.now()

    # 1. RFC 2822 (RSS 포맷: Sun, 11 Oct 2026 16:54:48 GMT 등)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return int(dt.timestamp())
    except Exception:
        pass

    # 2. ISO 포맷 (2026-10-14T14:27:06 등)
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        pass

    # 3. 'HH:MM' (당일 등록된 글 - 루리웹/디시)
    if re.match(r"^\d{1,2}:\d{2}$", date_str):
        parts = date_str.split(":")
        dt = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
        return int(dt.timestamp())

    # 4. 'YYYY.MM.DD' or 'YYYY-MM-DD'
    match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", date_str)
    if match:
        y, m, d = match.groups()
        dt = datetime(int(y), int(m), int(d))
        return int(dt.timestamp())

    # 5. 'YY.MM.DD' (모바일 웹 축약형)
    match = re.search(r"(\d{2})[.-](\d{1,2})[.-](\d{1,2})", date_str)
    if match:
        y, m, d = match.groups()
        dt = datetime(2000 + int(y), int(m), int(d))
        return int(dt.timestamp())

    return int(now.timestamp())

def format_display_date(timestamp: int) -> str:
    """화면 표시용 YYYY-MM-DD HH:MM 포맷"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

SPAM_KEYWORDS = [
    "릴", "슬롯", "스핀", "카지노", "바카라", "토토", "베팅", "환전", "먹튀",
    "꽁머니", "룰렛", "홀덤", "파워볼", "사설", "배팅", "spinkr", "프리스핀", "잭팟"
]

BLOCKED_SOURCES = [
    "calgary", "roughnecks", "spinkr", "casino", "slot", "toto", "bet"
]

TRUSTED_NEWS_SOURCES = [
    "인벤", "게임메카", "디스이즈게임", "지디넷", "아이뉴스24", "연합뉴스",
    "kbs", "sbs", "mbc", "jtbc", "ytn", "한국경제", "매일경제", "전자신문",
    "경향신문", "한겨레", "조선일보", "중앙일보", "동아일보", "뉴시스", "뉴스1",
    "스포츠조선", "스포츠서울", "데일리스포츠", "게임포커스", "게임샷", "게임톡",
    "스마트pc사랑", "반다이", "youtube", "유튜브", "포모스", "경향게임스",
    "디지몬", "haveagood-holiday"
]

def is_spam(item: dict) -> bool:
    """불법 도박/스팸 사이트 및 이상한 출처 판별"""
    title = (item.get("title") or "").lower()
    snippet = (item.get("snippet") or "").lower()
    source = (item.get("source") or "").lower()
    link = (item.get("link") or "").lower()

    # 1. 차단 소스 / 도메인 체크
    if any(b in source or b in link for b in BLOCKED_SOURCES):
        return True

    # 2. 스팸 키워드 포함 여부 체크
    for kw in SPAM_KEYWORDS:
        if kw in title or kw in snippet:
            return True

    # 3. 구글 뉴스 출처 검증 (검증된 언론사/공식 채널만 허용)
    if item.get("source_badge") == "뉴스":
        matched_trusted = any(t in source for t in TRUSTED_NEWS_SOURCES)
        if not matched_trusted:
            return True

    return False

def get_hash_id(url: str) -> str:
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()

def classify_category(title: str, default_cat: str = "general") -> str:
    title_lower = title.lower()
    
    # 카드게임
    if any(k in title_lower for k in ["디지카", "tcg", "카드", "부스터", "패러렐", "시크릿", "덱리", "덱 리스트", "스타터"]):
        return "card"
    # 피규어 / 굿즈
    if any(k in title_lower for k in ["피규어", "프라모델", "굿즈", "반다이", "figurerise", "shf", "스탠다드", "예약", "발매", "디지바이스", "완구"]):
        return "figure"
    # 게임 / 애니
    if any(k in title_lower for k in ["사이버 슬루스", "서바이브", "신작", "게임", "스팀", "극장판", "애니", "더빙", "방영", "ost"]):
        return "game"
    
    return default_cat

def crawl_google_news_digimon():
    items = []
    feed_url = "https://news.google.com/rss/search?q=%EB%94%94%EC%A7%80%EB%AA%AC&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:15]:
            title = entry.title
            link = entry.link
            published = getattr(entry, "published", "")
            summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))
            
            # 언론사 분리 (보통 제목 끝에 ' - 매체명' 형태)
            source_name = "뉴스"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source_name = parts[1]

            category = classify_category(title, "general")
            ts = parse_to_timestamp(published)

            items.append({
                "id": get_hash_id(link),
                "title": title.strip(),
                "snippet": summary[:120].strip() if summary else f"{source_name} 보도자료",
                "source": source_name,
                "source_badge": "뉴스",
                "category": category,
                "category_name": "뉴스/보도",
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] Google News crawling failed: {e}")
    return items

def crawl_ruliweb_hobby():
    items = []
    # 루리웹 피규어/프라모델 정보 게시판 '디지몬' 검색
    url = "https://bbs.ruliweb.com/family/242/board/300017?search_type=subject&search_key=%EB%94%94%EC%A7%80%EB%AA%AC"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("tr.table_body")
            for row in rows[:20]:
                title_elem = row.select_one("td.subject a.text_over") or row.select_one("td.subject a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")
                
                # 공지사항이나 댓글 앵커 건너뛰기
                if not link or "read/169" in link or "#cmt" in link:
                    continue
                if link and not link.startswith("http"):
                    link = "https://bbs.ruliweb.com" + link

                # 댓글 수 분리: (5) 등 제거
                title = re.sub(r'\(\d+\)$', '', title).strip()

                img_elem = row.select_one("img.thumb")
                img_src = img_elem.get("src") if img_elem else None
                if img_src and img_src.startswith("//"):
                    img_src = "https:" + img_src

                time_elem = row.select_one("td.time")
                raw_time = time_elem.get_text(strip=True) if time_elem else ""
                ts = parse_to_timestamp(raw_time)

                category = classify_category(title, "figure")

                items.append({
                    "id": get_hash_id(link),
                    "title": title,
                    "snippet": "루리웹 피규어/프라모델 정보 게시판 등록 소식입니다.",
                    "source": "루리웹 모형정보",
                    "source_badge": "루리웹",
                    "category": category,
                    "category_name": "피규어/굿즈" if category == "figure" else "커뮤니티",
                    "link": link,
                    "image": img_src,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
    except Exception as e:
        print(f"[Error] Ruliweb crawling failed: {e}")
    return items

def crawl_dc_gallery(gallery_id: str, badge_name: str, default_cat: str):
    items = []
    # 모바일 웹은 차단이 적고 심플함
    url = f"https://m.dcinside.com/board/{gallery_id}?recommend=1"
    m_headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "Referer": "https://m.dcinside.com/"
    }
    try:
        res = requests.get(url, headers=m_headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("ul.gall-detail-lst > li")
            for row in rows[:15]:
                title_elem = row.select_one(".subjectin")
                link_elem = row.select_one("a:not(.btn-reply-more)")
                if not title_elem or not link_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link = link_elem.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://m.dcinside.com" + link

                time_elem = row.select_one(".ginfo li:nth-child(2)")
                raw_time = time_elem.get_text(strip=True) if time_elem else ""
                ts = parse_to_timestamp(raw_time)

                cat = classify_category(title, default_cat)

                items.append({
                    "id": get_hash_id(link),
                    "title": title,
                    "snippet": f"디시인사이드 {badge_name} 갤러리 추천 개념글입니다.",
                    "source": f"디시 {badge_name}",
                    "source_badge": "디시",
                    "category": cat,
                    "category_name": "카드게임(TCG)" if cat == "card" else "커뮤니티 인기글",
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
    except Exception as e:
        print(f"[Error] DC {gallery_id} crawling failed: {e}")
    return items

def crawl_withthewill_news():
    items = []
    feed_url = "https://withthewill.net/forums/digimon-news.20/index.rss"
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:8]:
            title = entry.title
            link = entry.link
            published = getattr(entry, "published", "")
            summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
            ts = parse_to_timestamp(published)

            items.append({
                "id": get_hash_id(link),
                "title": f"[해외공식] {title}",
                "snippet": summary or "WithTheWill 글로벌 디지몬 최신 뉴스입니다.",
                "source": "WithTheWill",
                "source_badge": "공식/글로벌",
                "category": classify_category(title, "game"),
                "category_name": "해외 소식",
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] WithTheWill crawling failed: {e}")
    return items

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Digimon feeds crawl...")
    all_new_items = []
    
    print("1. Crawling Google News...")
    all_new_items.extend(crawl_google_news_digimon())

    print("2. Crawling Ruliweb Hobby...")
    all_new_items.extend(crawl_ruliweb_hobby())

    print("3. Crawling DC Digimon...")
    all_new_items.extend(crawl_dc_gallery("digimon", "디지몬", "community"))

    print("4. Crawling DC TCG Digimon...")
    all_new_items.extend(crawl_dc_gallery("tcg_digimon", "디지카", "card"))

    print("5. Crawling WithTheWill...")
    all_new_items.extend(crawl_withthewill_news())

    print(f"Total fetched: {len(all_new_items)} items")

    # 기존 데이터 로드 및 병합
    existing_items = []
    if os.path.exists(FEEDS_FILE):
        try:
            with open(FEEDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_items = data.get("feeds", [])
        except Exception as e:
            print(f"[Warning] Failed to read existing feeds: {e}")

    # 기존 데이터 timestamp 보정
    for item in existing_items:
        if "timestamp" not in item:
            item["timestamp"] = parse_to_timestamp(item.get("created_at", ""))
            item["created_at"] = format_display_date(item["timestamp"])

    # ID 기준 중복 제거 및 최신 데이터 우선 병합
    feed_map = {item["id"]: item for item in existing_items if not is_spam(item)}
    for item in all_new_items:
        if not is_spam(item):
            feed_map[item["id"]] = item

    # [핵심 1] 최근 90일(약 3달) 이내 데이터 보관 (사용자가 앱에서 기간 필터 선택 가능)
    cutoff_timestamp = int((datetime.now() - timedelta(days=90)).timestamp())
    filtered_feeds = [
        item for item in feed_map.values()
        if item.get("timestamp", 0) >= cutoff_timestamp and not is_spam(item)
    ]

    # [핵심 2] 최신순 내림차순 정렬 (가장 최신글이 index 0)
    filtered_feeds.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(filtered_feeds),
        "retention_days": 90,
        "feeds": filtered_feeds
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # public 및 docs 폴더에도 복사하여 GitHub Pages와 웹 프론트엔드가 바로 서빙할 수 있도록 함
    for target in [PUBLIC_DATA_FILE, DOCS_DATA_FILE]:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Successfully filtered (last 30 days) & sorted newest-first: {len(filtered_feeds)} items saved.")

if __name__ == "__main__":
    main()
