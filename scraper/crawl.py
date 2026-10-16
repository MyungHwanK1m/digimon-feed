import os
import sys
import json
import hashlib
import re
import html
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
    "calgary", "roughnecks", "spinkr", "casino", "slot", "toto", "bet",
    "p-bandai.jp", "p-bandai.com", "premium bandai", "프리미엄 반다이",
    "prom.pudding", "jawasjunkyard", "reddit.com", "reddit"
]

TRUSTED_NEWS_SOURCES = [
    "인벤", "게임메카", "디스이즈게임", "지디넷", "아이뉴스24", "연합뉴스",
    "kbs", "sbs", "mbc", "jtbc", "ytn", "한국경제", "매일경제", "전자신문",
    "경향신문", "한겨레", "조선일보", "중앙일보", "동아일보", "뉴시스", "뉴스1",
    "스포츠조선", "스포츠서울", "데일리스포츠", "게임포커스", "게임샷", "게임톡",
    "스마트pc사랑", "반다이", "youtube", "유튜브", "포모스", "경향게임스",
    "디지몬", "haveagood-holiday", "x.com", "twitter", "트위터", "toei", "토에이",
    "digimoncard", "wikimon", "bandai", "dengeki", "hobby.watch", "impress",
    "animenewsnetwork", "crunchyroll", "ign", "kotaku", "siliconera", "famitsu", "4gamer", "gamebiz",
    "oricon", "natalie", "mantan-web", "daewon", "대원",
    "digimonmeta", "egmanevents", "amiami", "goodsmile", "hlj", "arca.live", "naver", "네이버"
]

def is_spam(item: dict) -> bool:
    """불법 도박/스팸 사이트, 차단 사이트(레딧, 프반), 무관 인스타 판별"""
    title = (item.get("title") or "").lower()
    snippet = (item.get("snippet") or "").lower()
    source = (item.get("source") or "").lower()
    link = (item.get("link") or "").lower()
    sbadge = item.get("source_badge") or ""

    # 1. 차단 소스 / 도메인 / 뱃지 체크 (레딧, 프리미엄 반다이 직접 링크 차단)
    if sbadge == "레딧" or any(b in source or b in link for b in BLOCKED_SOURCES) or "market/board" in link or "board/1020" in link:
        return True

    # 2. 스팸 키워드 포함 여부 체크
    for kw in SPAM_KEYWORDS:
        if kw in title or kw in snippet:
            return True

    # 3. 구글 뉴스 출처 검증 (검증된 언론사/공식 채널만 허용)
    if sbadge == "뉴스":
        matched_trusted = any(t in source for t in TRUSTED_NEWS_SOURCES)
        if not matched_trusted:
            return True

    # 4. 글로벌/해외/일본 뉴스, 하비, 인스타그램 디지몬 키워드 엄격 검증
    if sbadge in ["해외뉴스", "일본뉴스", "프반/하비", "하비뉴스", "애니뉴스", "인스타그램"]:
        full = f"{title} {snippet} {link}".lower()
        digi_kws = ["디지몬", "digimon", "デジモン", "디지바이스", "digivice", "デジヴァイス", "vpet", "v-pet", "아구몬", "agumon", "vital", "바이탈", "seekers", "liberator"]
        if not any(k in full for k in digi_kws):
            return True

    # 5. 인스타그램은 디지몬 키워드가 제목/본문에 직접 있어야 하며 프로필 페이지는 제외
    if sbadge == "인스타그램":
        if any(b in link or b in title for b in ["prom.pudding", "jawasjunkyard"]):
            return True
        if not any(k in title for k in ["디지몬", "digimon", "デジモン", "디지바이스", "아구몬"]):
            return True

    return False

# 디지몬 전 시리즈 키워드 사전 (애니/극장판/웹툰/소설/게임/완구)
DIGIMON_SERIES_KEYWORDS = {
    "adventure": ["어드벤처", "adventure", "파워디지몬", "어드벤처 02", "02", "라스트 에볼루션", "더 비기닝", "워게임", "디아블로몬", "tri."],
    "tamers": ["테이머즈", "tamers", "길몬", "듀크몬", "디지인", "블루카드", "매트릭스 에볼루션"],
    "frontier": ["프론티어", "frontier", "스피릿 에볼루션", "아그니몬", "볼프몬", "카이저그레이몬", "매그너가루루몬", "스사노오몬"],
    "savers": ["세이버즈", "savers", "샤인그레이몬", "미라주가오가몬", "다이몬"],
    "xros": ["크로스워즈", "xros", "샤우트몬", "디지크로스"],
    "appmon": ["어플몬", "어플리 몬스터즈", "appmon", "갓치몬"],
    "adventure_colon": ["어드벤처:", "어드벤처 리부트"],
    "ghost_game": ["고스트 게임", "ghost game", "감마몬", "베텔감마몬"],
    "beatbreak": ["비트브레이크", "beatbreak"],
    "media_novel": ["디지몬 시커즈", "seekers", "디지몬 리베레이터", "liberator", "v테이머", "크로니클", "chronicle"],
    "games": ["디지몬 월드", "디지몬 스토리", "사이버 슬루스", "해커스 메모리", "서바이브", "디지몬 rpg", "디지몬 마스터즈", "슈퍼 럼블", "신세기", "next 0rder", "넥스트 오더", "선버스트", "문라이트"],
    "vpet_toy": ["디지바이스", "펜들럼", "pendulum", "바이탈 브레스", "vital bracelet", "be", "디지몬 컬러", "color", "d-3", "d-ark", "d-scanner"]
}

# 신작/속보 무누락 휴리스틱 트리거 (New Project Zero-Miss Triggers)
NEW_PROJECT_TRIGGERS = [
    # 한국어
    "신작", "신프로젝트", "신시리즈", "제작 결정", "방영 결정", "발매 결정", "신규 디지몬", 
    "티저", "공식 발표", "새로운 프로젝트", "25주년", "신규 애니", "신규 게임", "신규 tcg", "신규 프로젝트",
    # 영어
    "new project", "new anime", "new game", "new series", "announcement", "teaser", "reveal", 
    "unveiled", "new digimon", "25th anniversary", "upcoming", "brand new",
    # 일본어
    "新作", "新プロジェクト", "新シリーズ", "制作決定", "発表", "解禁", "アニメ化", "ゲーム化", "25周年"
]

# 1차 공식 출처 화이트리스트 (신작 발표 시 무조건 통과)
OFFICIAL_SOURCES = [
    "반다이", "bandai", "toei", "토에이", "digimon.net", "digimonweb_net", "digimon_tcg", "withthewill"
]

def get_hash_id(url: str) -> str:
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()

def classify_category(title: str, default_cat: str = "general", source_badge: str = "") -> tuple:
    title_lower = title.lower()
    
    # [0순위] 신작/속보 트리거 감지 (새로운 타이틀이라도 신작 속보로 즉시 캐치)
    is_new = any(k in title_lower for k in NEW_PROJECT_TRIGGERS)
    if is_new:
        if any(k in title_lower for k in ["카드", "tcg", "디지카", "부스터", "덱"]):
            return "card", "신작 카드(TCG)"
        if any(k in title_lower for k in ["피규어", "프라모델", "쿠지", "완구", "디지바이스", "굿즈"]):
            return "figure", "신작 굿즈/완구"
        return "game", "신작/공식속보"

    # [1순위] 유튜브 노래 커버곡 / 팬 음악 / OST (무조건 SNS 카테고리로 격리)
    if any(k in title_lower for k in [
        "butter-fly", "butterfly", "brave heart", "커버", "cover", "tula", 
        "노래", "ost", "음악", "라이브", "불러보았다", "mr", "target", "an Endless tale"
    ]) or (source_badge == "유튜브" and not any(k in title_lower for k in ["공식", "pv", "트레일러", "발매", "신작"])):
        return "sns", "SNS/영상"

    # [2순위] 피규어 / 굿즈 / 쿠지(이치방쿠지) / 완구(디지바이스, 펜들럼) / 프론티어 25주년
    if any(k in title_lower for k in [
        "피규어", "프라모델", "굿즈", "쿠지", "이치방쿠지", "반다이", "figurerise", 
        "shf", "스탠다드", "예약", "발매", "디지바이스", "완구", "아크릴", "인형", 
        "가챠", "캡슐", "스피릿", "프론티어", "아머체", "d-arts", "g.e.m", "gem", 
        "프레임", "스탠드", "펜들럼", "바이탈 브레스", "컬러", "디지몬 컬러", "be"
    ]):
        return "figure", "피규어/굿즈"

    # [3순위] 카드게임 (TCG / 디지카 / 리베레이터 연계)
    if any(k in title_lower for k in [
        "디지카", "tcg", "카드", "부스터", "패러렐", "시크릿", "덱리", "덱 리스트", 
        "스타터", "챔피언십", "에이스", "디지몬카드", "시크릿 크라이시스", "bt", "ex", 
        "리베레이터", "liberator"
    ]):
        return "card", "카드게임(TCG)"

    # [4순위] 정식 게임 / 공식 극장판/애니 / 웹코믹/소설
    if any(k in title_lower for k in [
        "사이버 슬루스", "서바이브", "신작 게임", "스팀", "극장판", "애니메이션", 
        "더빙", "방영", "닌텐도", "플레이스테이션", "공식 pv", "티저 pv", "시커즈", "seekers",
        "고스트 게임", "어드벤처", "테이머즈", "세이버즈", "크로스워즈", "어플몬", "비트브레이크"
    ]):
        return "game", "게임/공식애니"

    # [5순위] 소스 기반 매핑
    if source_badge in ["X(트위터)", "유튜브", "인스타그램"]:
        return "sns", "SNS/해외"
    if source_badge in ["디시", "아카라이브"]:
        return "community", "커뮤니티"
    if source_badge in ["루리웹", "프반/하비", "하비뉴스"]:
        return "figure", "피규어/굿즈"
    if source_badge == "디지카":
        return "card", "카드게임(TCG)"
    if source_badge in ["애니뉴스", "네이버"]:
        return "game", "게임/공식애니"
    if source_badge in ["위키몬", "위키몬 신규"]:
        return "general", "도감/위키"

    return default_cat, "일반/뉴스"

def crawl_google_news_digimon():
    items = []
    # 굿즈/쿠지/프론티어 25주년/카드게임/신작/전시리즈를 아우르는 다중 검색 쿼리
    queries = [
        "디지몬 굿즈 OR 디지몬 피규어 OR 디지몬 쿠지 OR 디지몬 이치방쿠지 OR \"디지몬 프론티어\" OR 디지바이스 OR \"디지몬 25주년\"",
        "디지카 OR \"디지몬 카드게임\" OR \"디지몬 리베레이터\" OR \"디지몬 시커즈\"",
        "디지몬 신작 OR \"디지몬 어드벤처\" OR \"디지몬 테이머즈\" OR \"고스트 게임\" OR \"디지몬 월드\" OR \"사이버 슬루스\"",
        "디지몬"
    ]
    
    for q in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                title = entry.title
                link = entry.link
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))
                
                source_name = "뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source_name = parts[1]

                category, cat_name = classify_category(title, "general", "뉴스")
                ts = parse_to_timestamp(published)

                items.append({
                    "id": get_hash_id(link),
                    "title": title.strip(),
                    "snippet": summary[:120].strip() if summary else f"{source_name} 보도자료",
                    "source": source_name,
                    "source_badge": "뉴스",
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Google News ({q}) crawling failed: {e}")
    return items

def crawl_ruliweb_hobby():
    items = []
    # 디지몬, 프론티어, 쿠지, 완구/디지바이스 검색 교차 수집
    search_keys = ["디지몬", "프론티어", "이치방쿠지 디지몬", "디지바이스"]
    for skey in search_keys:
        url = f"https://bbs.ruliweb.com/family/242/board/300017?search_type=subject&search_key={requests.utils.quote(skey)}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                rows = soup.select("tr.table_body")
                for row in rows[:18]:
                    title_elem = row.select_one("td.subject a.text_over") or row.select_one("td.subject a")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    
                    if not link or "board/300017/read/" not in link or "#cmt" in link:
                        continue
                    if "notice" in row.get("class", []):
                        continue
                    if link and not link.startswith("http"):
                        link = "https://bbs.ruliweb.com" + link

                    # 검색어 관련성 검증
                    title_l = title.lower()
                    if skey == "프론티어" and not any(k in title_l for k in ["디지몬", "스피릿", "아그니몬", "볼프몬"]):
                        continue
                    if skey == "디지바이스" and not any(k in title_l for k in ["디지몬", "디지바이스", "펜들럼", "컬러"]):
                        continue

                    title = re.sub(r'\(\d+\)$', '', title).strip()

                    img_elem = row.select_one("img.thumb")
                    img_src = img_elem.get("src") if img_elem else None
                    if img_src and img_src.startswith("//"):
                        img_src = "https:" + img_src

                    time_elem = row.select_one("td.time")
                    raw_time = time_elem.get_text(strip=True) if time_elem else ""
                    ts = parse_to_timestamp(raw_time)

                    category, cat_name = classify_category(title, "figure", "루리웹")

                    items.append({
                        "id": get_hash_id(link),
                        "title": title,
                        "snippet": "루리웹 피규어/프라모델/굿즈 정보 게시판 소식입니다.",
                        "source": "루리웹 모형정보",
                        "source_badge": "루리웹",
                        "category": category,
                        "category_name": cat_name,
                        "link": link,
                        "image": img_src,
                        "timestamp": ts,
                        "created_at": format_display_date(ts)
                    })
        except Exception as e:
            print(f"[Error] Ruliweb ({skey}) crawling failed: {e}")
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

                cat, cat_name = classify_category(title, default_cat, "디시")

                items.append({
                    "id": get_hash_id(link),
                    "title": title,
                    "snippet": f"디시인사이드 {badge_name} 갤러리 추천 개념글입니다.",
                    "source": f"디시 {badge_name}",
                    "source_badge": "디시",
                    "category": cat,
                    "category_name": cat_name,
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
            cat, cat_name = classify_category(title, "game", "공식/글로벌")

            items.append({
                "id": get_hash_id(link),
                "title": f"[해외공식] {title}",
                "snippet": summary or "WithTheWill 글로벌 디지몬 최신 뉴스입니다.",
                "source": "WithTheWill",
                "source_badge": "공식/글로벌",
                "category": cat,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] WithTheWill crawling failed: {e}")
    return items

def crawl_reddit_digimon():
    items = []
    subreddits = [
        ("digimon", "r/digimon", "community"),
        ("DigimonCardGame2020", "r/디지카", "card")
    ]
    reddit_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DigimonTracker/1.0"
    }
    for sub, badge, def_cat in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.rss"
        try:
            feed = feedparser.parse(url, request_headers=reddit_headers)
            for entry in feed.entries[:8]:
                title = entry.title
                link = entry.link
                published = getattr(entry, "published", "")
                ts = parse_to_timestamp(published)
                cat, cat_name = classify_category(title, def_cat, "레딧")

                # 썸네일 이미지 추출
                img_url = None
                if "media_thumbnail" in entry and entry.media_thumbnail:
                    img_url = entry.media_thumbnail[0].get("url")
                elif "content" in entry and entry.content:
                    m = re.search(r'https://preview\.redd\.it/[^\"&? ]+', entry.content[0].value)
                    if m:
                        img_url = m.group(0)

                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()

                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title}",
                    "snippet": summary or f"Reddit {badge} 인기 게시글입니다.",
                    "source": f"Reddit {sub}",
                    "source_badge": "레딧",
                    "category": cat,
                    "category_name": cat_name,
                    "link": link,
                    "image": img_url,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Reddit {sub} crawling failed: {e}")
    return items

def crawl_youtube_digimon():
    items = []
    feed_url = "https://news.google.com/rss/search?q=site:youtube.com+%22%EB%94%94%EC%A7%80%EB%AA%AC%22&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:15]:
            title = entry.title.replace(" - YouTube", "").strip()
            link = entry.link
            published = getattr(entry, "published", "")
            ts = parse_to_timestamp(published)
            
            # 노래/커버/음악은 SNS/영상으로 자동 분류됨
            category, cat_name = classify_category(title, "sns", "유튜브")

            items.append({
                "id": get_hash_id(link),
                "title": f"[영상] {title}",
                "snippet": "YouTube 최신 디지몬 공식/인기 영상입니다.",
                "source": "YouTube",
                "source_badge": "유튜브",
                "category": category,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] YouTube crawling failed: {e}")
    return items

def crawl_twitter_digimon():
    items = []
    # 굿즈, 쿠지, 프론티어, 공식 계정, 신작, 해외/일본 공식 계정을 아우르는 X 검색
    feed_url = 'https://news.google.com/rss/search?q=site:x.com+OR+site:twitter.com+(%22digimonweb_net%22+OR+%22digimon_tcg%22+OR+%22toei_anim_goods%22+OR+%22%E3%83%87%E3%82%B8%E3%83%A2%E3%83%B3%22+OR+%22DigimonTCG%22+OR+%22%EB%94%94%EC%A7%80%EB%AA%AC+%EA%B5%BF%EC%A6%88%22+OR+%22%EB%94%94%EC%A7%80%EB%AA%AC+%EC%BF%A0%EC%A7%80%22+OR+%22%EB%94%94%EC%A7%80%EB%AA%AC+%ED%94%84%EB%A1%A0%ED%8B%B0%EC%96%B4%22+OR+%22%EB%94%94%EC%A7%80%EB%AA%AC+%EC%8B%A0%EC%9E%91%22+OR+%22%EB%94%94%EC%A7%80%EB%AA%AC%22)&hl=ko&gl=KR&ceid=KR:ko'
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:
            title = entry.title
            if " on X: " in title:
                parts = title.split(" on X: ", 1)
                author = parts[0]
                text = parts[1].replace('"', "").strip()
                title = f"@{author}: {text}"
            link = entry.link
            published = getattr(entry, "published", "")
            ts = parse_to_timestamp(published)
            category, cat_name = classify_category(title, "sns", "X(트위터)")

            items.append({
                "id": get_hash_id(link),
                "title": f"[트윗] {title}",
                "snippet": "X(트위터) 디지몬 공식/굿즈 속보 트윗입니다.",
                "source": "X(트위터)",
                "source_badge": "X(트위터)",
                "category": category,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] Twitter crawling failed: {e}")
    return items

def crawl_instagram_digimon():
    """인스타그램은 비로그인 직접 접근이 막혀 있어 구글뉴스 RSS site: 검색으로 공개 디지몬 게시물(/p/, /reel/)만 수집"""
    items = []
    queries = [
        'site:instagram.com/p/ "#디지몬"',
        'site:instagram.com/p/ "#digimon"',
        'site:instagram.com/p/ "#デジモン"',
        'site:instagram.com/p/ "디지몬"',
        'site:instagram.com/p/ "digimon"',
        'site:instagram.com/reel/ "디지몬"',
    ]
    seen = set()
    digi_check = ["디지몬", "digimon", "デジモン", "디지바이스", "아구몬", "테이머즈", "v-pet"]
    for q in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = re.sub(r"\s*[-•|]\s*Instagram.*$", "", entry.title).strip()
                title = re.sub(r"^[•·\s]+", "", title).strip()
                if not title:
                    continue
                # 제목/본문에 디지몬 관련 단어가 명시되지 않은 일반 계정/글은 즉시 배제
                if not any(k in title.lower() for k in digi_check):
                    continue
                published = getattr(entry, "published", "")
                ts = parse_to_timestamp(published)
                category, cat_name = classify_category(title, "sns", "인스타그램")
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[인스타] {title}",
                    "snippet": "인스타그램 디지몬 관련 공개 게시물입니다.",
                    "source": "Instagram",
                    "source_badge": "인스타그램",
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Instagram crawling failed ({q}): {e}")
    return items

def crawl_google_news_global_en():
    """구글 뉴스 글로벌 영어 피드 수집 (US:en)"""
    items = []
    queries = [
        '"Digimon" OR "Digimon Card Game" OR "Digimon Liberator" OR "Digimon Seekers"',
        '"Digimon Adventure" OR "Digimon World" OR "Digivice" OR "Vital Bracelet"',
        '"Digimon" ("Bandai" OR "Toei Animation" OR "Anime")'
    ]
    seen = set()
    for q in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:12]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))
                source_name = "Global News"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source_name = parts[1]
                category, cat_name = classify_category(title, "general", "해외뉴스")
                ts = parse_to_timestamp(published)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[해외뉴스] {title.strip()}",
                    "snippet": summary[:120].strip() if summary else f"{source_name} 보도자료",
                    "source": source_name,
                    "source_badge": "해외뉴스",
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Global EN News ({q}) crawling failed: {e}")
    return items

def crawl_google_news_global_ja():
    """구글 뉴스 일본어 피드 수집 (JP:ja)"""
    items = []
    queries = [
        '"デジモン" OR "デジモンカードゲーム" OR "デジモンリベレイター" OR "デジモンシーカーズ"',
        '"デジモン フィギュア" OR "デジヴァイス" OR "デジタルモンスター" OR "バイタルブレス"',
        '"デジモン" ("バンダイ" OR "東映アニメーション" OR "プレミアムバンダイ")'
    ]
    seen = set()
    for q in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:12]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))
                source_name = "일본 뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source_name = parts[1]
                category, cat_name = classify_category(title, "general", "일본뉴스")
                ts = parse_to_timestamp(published)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[일본뉴스] {title.strip()}",
                    "snippet": summary[:120].strip() if summary else f"{source_name} 보도자료",
                    "source": source_name,
                    "source_badge": "일본뉴스",
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Global JA News ({q}) crawling failed: {e}")
    return items

def crawl_tcg_portals():
    """디지몬 카드게임 전문 포털 수집 (digimoncard.io, digimoncard.co.kr, digimoncard.com)"""
    items = []
    queries = [
        ('site:digimoncard.io', 'DigimonCard.io', '디지카'),
        ('site:digimoncard.co.kr', '공식 디지카KR', '디지카'),
        ('site:digimoncard.com', '반다이 공식 디지카', '디지카'),
    ]
    seen = set()
    for q, sname, badge in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
                ts = parse_to_timestamp(published)
                category, cat_name = classify_category(title, "card", badge)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title.strip()}",
                    "snippet": summary or f"{sname} 디지몬 카드게임 소식입니다.",
                    "source": sname,
                    "source_badge": badge,
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] TCG portal ({q}) crawling failed: {e}")
    return items

def crawl_wikimon_updates():
    """위키몬(Wikimon) 신규 등록 문서(New Pages) 전용 수집 (오타 수정 제외, 100% 공개 본문 링크)"""
    items = []
    url = "https://wikimon.net/api.php?action=query&list=recentchanges&rctype=new&rcnamespace=0&rclimit=15&format=json"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (DigimonTracker/1.0)"}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            rcs = data.get("query", {}).get("recentchanges", [])
            for rc in rcs:
                raw_title = rc.get("title", "").strip()
                if not raw_title:
                    continue
                # 로그인 필요한 diff= 대신 100% 공개되는 문서 본문 링크로 생성
                clean_name = raw_title.replace(" ", "_")
                clean_link = f"https://wikimon.net/{requests.utils.quote(clean_name)}"
                ts = parse_to_timestamp(rc.get("timestamp", ""))
                items.append({
                    "id": get_hash_id(clean_link),
                    "title": f"[위키몬 신규] {raw_title}",
                    "snippet": f"Wikimon에 새로 등록된 공식 신규 문서 ({raw_title})입니다.",
                    "source": "Wikimon",
                    "source_badge": "위키몬",
                    "category": "general",
                    "category_name": "도감/위키",
                    "link": clean_link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
    except Exception as e:
        print(f"[Error] Wikimon API crawling failed: {e}")
    return items

def crawl_premium_bandai_hobby():
    """하비 전문 매체 수집 (IP 차단 없는 전격하비, 하비워치만 수집)"""
    items = []
    queries = [
        ('site:hobby.dengeki.com "デジモン"', '전격하비', '하비뉴스', 'figure'),
        ('site:hobby.watch.impress.co.jp "デジモン"', '하비워치', '하비뉴스', 'figure'),
    ]
    seen = set()
    for q, sname, badge, def_cat in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
                ts = parse_to_timestamp(published)
                category, cat_name = classify_category(title, def_cat, badge)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title.strip()}",
                    "snippet": summary or f"{sname} 디지몬 하비/완구 소식입니다.",
                    "source": sname,
                    "source_badge": badge,
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Hobby portal ({q}) crawling failed: {e}")
    return items

def crawl_global_anime_news():
    """글로벌 애니메이션 웹진 디지몬 소식 수집"""
    items = []
    queries = [
        ('site:animenewsnetwork.com "Digimon"', 'Anime News Network', '애니뉴스'),
        ('site:crunchyroll.com/news "Digimon"', 'Crunchyroll News', '애니뉴스'),
    ]
    seen = set()
    for q, sname, badge in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
                ts = parse_to_timestamp(published)
                category, cat_name = classify_category(title, "game", badge)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title.strip()}",
                    "snippet": summary or f"{sname} 디지몬 글로벌 보도입니다.",
                    "source": sname,
                    "source_badge": badge,
                    "category": category,
                    "category_name": cat_name,
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Anime news ({q}) crawling failed: {e}")
    return items

def crawl_digimon_meta_and_egman():
    """디지몬 카드게임 대회 우승 덱 & 메타 분석 사이트 (Digimon Meta, Egman Events)"""
    items = []
    queries = [
        ('site:digimonmeta.com "deck"', 'Digimon Meta', '디지카'),
        ('site:digimonmeta.com', 'Digimon Meta', '디지카'),
        ('site:egmanevents.com "digimon"', 'Egman Events', '디지카'),
    ]
    seen = set()
    for q, sname, badge in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
                ts = parse_to_timestamp(published)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title.strip()}",
                    "snippet": summary or f"{sname} 디지카 대회 우승 덱/메타 정보입니다.",
                    "source": sname,
                    "source_badge": badge,
                    "category": "card",
                    "category_name": "카드게임(TCG)",
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] TCG meta ({q}) crawling failed: {e}")
    return items

def crawl_figure_shops():
    """피규어/굿즈 예약 전문 샵 (AmiAmi, GoodSmile, HLJ)"""
    items = []
    queries = [
        ('site:amiami.com "Digimon"', 'AmiAmi', '하비뉴스'),
        ('site:amiami.jp "デジモン"', '아미아미', '하비뉴스'),
        ('site:goodsmile.info "デジモン" OR site:goodsmile.com "Digimon"', '굿스마일', '하비뉴스'),
        ('site:hlj.com "Digimon"', 'HLJ', '하비뉴스'),
    ]
    seen = set()
    for q, sname, badge in queries:
        feed_url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                link = entry.link
                if link in seen:
                    continue
                seen.add(link)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                published = getattr(entry, "published", "")
                summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
                ts = parse_to_timestamp(published)
                items.append({
                    "id": get_hash_id(link),
                    "title": f"[{badge}] {title.strip()}",
                    "snippet": summary or f"{sname} 디지몬 피규어/굿즈 예약 정보입니다.",
                    "source": sname,
                    "source_badge": badge,
                    "category": "figure",
                    "category_name": "피규어/굿즈",
                    "link": link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts)
                })
        except Exception as e:
            print(f"[Error] Figure shop ({q}) crawling failed: {e}")
    return items

def crawl_ruliweb_game_and_anime():
    """루리웹 콘솔/PC 게임 정보 및 애니메이션 정보 게시판"""
    items = []
    boards = [
        ("https://bbs.ruliweb.com/news/board/1001?search_type=subject&search_key=디지몬", "루리웹 콘솔뉴스", "game", "게임/공식애니"),
        ("https://bbs.ruliweb.com/news/board/1003?search_type=subject&search_key=디지몬", "루리웹 PC뉴스", "game", "게임/공식애니"),
        ("https://bbs.ruliweb.com/family/211/board/300015?search_type=subject&search_key=디지몬", "루리웹 애니정보", "game", "게임/공식애니"),
    ]
    for url, sname, cat, cat_name in boards:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                rows = soup.select("tr.table_body")
                for row in rows[:10]:
                    title_elem = row.select_one("td.subject a.text_over") or row.select_one("td.subject a")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    if not link or "read/" not in link or "#cmt" in link or "notice" in row.get("class", []):
                        continue
                    if link and not link.startswith("http"):
                        link = "https://bbs.ruliweb.com" + link
                    title = re.sub(r'\(\d+\)$', '', title).strip()
                    time_elem = row.select_one("td.time")
                    raw_time = time_elem.get_text(strip=True) if time_elem else ""
                    ts = parse_to_timestamp(raw_time)
                    items.append({
                        "id": get_hash_id(link),
                        "title": f"[루리웹] {title}",
                        "snippet": f"{sname} 디지몬 최신 소식입니다.",
                        "source": sname,
                        "source_badge": "루리웹",
                        "category": cat,
                        "category_name": cat_name,
                        "link": link,
                        "image": None,
                        "timestamp": ts,
                        "created_at": format_display_date(ts)
                    })
        except Exception as e:
            print(f"[Error] Ruliweb board ({url}) crawling failed: {e}")
    return items

def crawl_arcalive_digimon():
    """아카라이브 디지몬 채널 인기 정보글"""
    items = []
    query = requests.utils.quote('site:arca.live/b/digimon "디지몬"')
    feed_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:12]:
            title = entry.title
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            link = entry.link
            published = getattr(entry, "published", "")
            summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
            ts = parse_to_timestamp(published)
            category, cat_name = classify_category(title, "community", "아카라이브")
            items.append({
                "id": get_hash_id(link),
                "title": f"[아카라이브] {title.strip()}",
                "snippet": summary or "아카라이브 디지몬 채널 게시글입니다.",
                "source": "아카라이브",
                "source_badge": "아카라이브",
                "category": category,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] Arcalive crawling failed: {e}")
    return items

def crawl_naver_game():
    """네이버 게임 라운지 및 공식 소식"""
    items = []
    query = requests.utils.quote('site:game.naver.com "디지몬"')
    feed_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:8]:
            title = entry.title
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            link = entry.link
            published = getattr(entry, "published", "")
            summary = re.sub(r'<[^>]+>', '', getattr(entry, "summary", ""))[:120].strip()
            ts = parse_to_timestamp(published)
            category, cat_name = classify_category(title, "game", "네이버")
            items.append({
                "id": get_hash_id(link),
                "title": f"[네이버] {title.strip()}",
                "snippet": summary or "네이버 게임 디지몬 관련 소식입니다.",
                "source": "네이버 게임",
                "source_badge": "네이버",
                "category": category,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts)
            })
    except Exception as e:
        print(f"[Error] Naver Game crawling failed: {e}")
    return items

OFFICIAL_SITE = "https://digimon.net/"


def _official_date(text: str) -> str:
    """'2026/10/14' · '2026年10月03日発売' → '2026-10-14' (parse_to_timestamp 가 읽는 형식)"""
    m = re.search(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", text or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def _official_cards(html_text: str):
    """digimon.net 목록 카드(<li class="c-cardList ...">)에서 링크·제목·태그·날짜 추출"""
    for block in re.findall(r'<li class="c-cardList c-card">(.*?)</a></li>', html_text, re.S):
        link = re.search(r'href="([^"]+)"', block)
        title = re.search(r'<p class="c-card__tit">(.*?)</p>', block, re.S)
        if not link or not title:
            continue
        tag = re.search(r'<li class="c-cardTagList">(.*?)</li>', block, re.S)
        date = re.search(r'<p class="c-card__date">(.*?)</p>', block, re.S)
        release = re.search(r'発売日\s*:\s*</dt>\s*<dd[^>]*>(.*?)</dd>', block, re.S)
        price = re.search(r'価\s*格\s*:\s*</dt>\s*<dd[^>]*>(.*?)</dd>', block, re.S)
        strip = lambda m: html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        yield {
            "link": link.group(1),
            "title": strip(title),
            "tag": strip(tag),
            "date": strip(date),
            "release": strip(release),
            "price": strip(price),
        }


def crawl_official_topics():
    """공식 사이트 뉴스(digimon.net/topic) — 제목·날짜·링크만 저장 (본문은 공식 페이지로 연결)"""
    items = []
    url = OFFICIAL_SITE + "topic/?cat=ALL"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (digimon-feed fan project)"}, timeout=20)
        res.raise_for_status()
        for c in list(_official_cards(res.text))[:20]:
            link = requests.compat.urljoin(url, c["link"])
            ts = parse_to_timestamp(_official_date(c["date"]))
            category, cat_name = classify_category(c["title"], "game", "디지몬웹")
            items.append({
                "id": get_hash_id(link),
                "title": f"[공식] {c['title']}",
                "snippet": f"디지몬 공식 사이트 {c['tag'] or '뉴스'}",
                "source": "digimon.net",
                "source_badge": "디지몬웹",
                "category": category,
                "category_name": cat_name,
                "link": link,
                "image": None,
                "timestamp": ts,
                "created_at": format_display_date(ts),
            })
    except Exception as e:
        print(f"[Error] Official topics crawling failed: {e}")
    return items


def crawl_official_products():
    """공식 사이트 상품(digimon.net/product/…) — 상품명·발매일·가격·링크만 저장"""
    items = []
    sections = [("card", "card", "카드게임(TCG)"), ("game", "game", "게임/공식애니"),
                ("goods", "figure", "피규어/굿즈"), ("others", "figure", "피규어/굿즈")]
    now_ts = int(datetime.now().timestamp())
    for path, cat, cat_name in sections:
        url = f"{OFFICIAL_SITE}product/{path}/"
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (digimon-feed fan project)"}, timeout=20)
            res.raise_for_status()
            for c in list(_official_cards(res.text))[:8]:
                raw_link = requests.compat.urljoin(url, c["link"])
                # item_type=1 은 p-bandai.jp 로 302 강제 리다이렉트되어 해외 접속 시 차단됨
                # 차단당하지 않는 디지몬웹 해당 카테고리 공식 목록 페이지로 안전 연결 (방안 A)
                safe_link = url if "item_type=1" in raw_link else raw_link
                release = _official_date(c["release"])
                # 발매 예정 상품은 미래 날짜라 지금 시각으로 맞춤 (발매일은 요약에 표시)
                ts = min(parse_to_timestamp(release), now_ts) if release else now_ts
                info = " · ".join(x for x in [f"발매 {release}" if release else c["release"], c["price"]] if x)
                items.append({
                    "id": get_hash_id(f"{raw_link}_{c['title']}"),
                    "title": f"[공식 상품] {c['title']}",
                    "snippet": info or "디지몬 공식 사이트 상품 정보",
                    "source": "digimon.net",
                    "source_badge": "디지몬웹",
                    "category": cat,
                    "category_name": cat_name,
                    "link": safe_link,
                    "image": None,
                    "timestamp": ts,
                    "created_at": format_display_date(ts),
                    "keep_first_seen": True,
                })
        except Exception as e:
            print(f"[Error] Official products crawling failed ({path}): {e}")
    return items

TITLE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "translations", "feed_titles.json")
KO_RE = re.compile(r"[\uac00-\ud7a3]")
JA_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
EN_WORD_RE = re.compile(r"[a-zA-Z]{3,}")

NAMES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "translations", "names.json")
TERMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "translations", "terms.json")


def translate_feed_titles(items):
    """공식 사이트(일본어) 및 해외 글로벌 피드(영어/일본어) 제목을 Gemini로 한국어 번역.
    원제는 title_orig (일어인 경우 title_ja)에 보관, 번역 결과는 feed_titles.json에 캐시.
    디지몬 고증 이름은 names.json 및 terms.json 기준 표기.
    GEMINI_API_KEY 가 없거나 실패하면 원문 그대로 둠."""
    try:
        import gemini
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import gemini
    cache = {}
    if os.path.exists(TITLE_CACHE):
        with open(TITLE_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    names = {}
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, encoding="utf-8") as f:
            names = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    terms = {}
    if os.path.exists(TERMS_FILE):
        with open(TERMS_FILE, encoding="utf-8") as f:
            terms = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    def glossary_in(text):
        gl = {k: v for k, v in names.items() if k in text}
        gl.update({k: v for k, v in terms.items() if k.lower() in text.lower()})
        return gl

    targets = []
    for item in items:
        raw_title = item.get("title", "")
        m = re.match(r"^(\[[^\]]+\]\s*)(.*)", raw_title, re.S)
        prefix = m.group(1) if m else ""
        body = m.group(2).strip() if m else raw_title.strip()
        body = item.get("title_orig") or item.get("title_ja") or body

        # 한글이 전혀 없고, 일본어 또는 영어 단어가 포함된 경우 번역 대상
        if not KO_RE.search(body) and (JA_RE.search(body) or EN_WORD_RE.search(body)):
            targets.append((item, prefix, body))

    # 캐시에 없는 항목만 번역
    missing = list(dict.fromkeys(b for _, _, b in targets if b not in cache))
    if missing and gemini.available():
        try:
            for i in range(0, len(missing), 30):
                chunk = missing[i:i + 30]
                gl = {}
                for t in chunk:
                    gl.update(glossary_in(t))
                out = gemini.translate_map({str(n): t for n, t in enumerate(chunk)}, gl)
                for n, t in enumerate(chunk):
                    ko = out.get(str(n))
                    if not ko:
                        continue
                    # 모델이 괄호 더빙명을 빠뜨리면 원작 이름 뒤에 붙여 맞춤
                    for full in names.values():
                        base = full.split("(")[0]
                        if full not in ko and base in ko:
                            ko = ko.replace(base, full, 1)
                    cache[t] = ko
        except Exception as e:
            print(f"[Warning] Feed title translation stopped: {e}")
        os.makedirs(os.path.dirname(TITLE_CACHE), exist_ok=True)
        with open(TITLE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
    elif missing:
        print(f"[Info] GEMINI_API_KEY 미설정 또는 할당량 초과 ({len(missing)}건 번역 대기 - 원문 유지)")

    for item, prefix, body in targets:
        if body in cache:
            item["title_orig"] = body
            if JA_RE.search(body):
                item["title_ja"] = body
            item["title"] = prefix + cache[body]

def translate_official_titles(items):
    return translate_feed_titles(items)


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Digimon feeds crawl...")
    all_new_items = []
    
    print("1. Crawling Google News (KR)...")
    all_new_items.extend(crawl_google_news_digimon())

    print("2. Crawling Google News Global (EN)...")
    all_new_items.extend(crawl_google_news_global_en())

    print("3. Crawling Google News Global (JA)...")
    all_new_items.extend(crawl_google_news_global_ja())

    print("4. Crawling Ruliweb Hobby...")
    all_new_items.extend(crawl_ruliweb_hobby())

    print("5. Crawling DC Digimon...")
    all_new_items.extend(crawl_dc_gallery("digimon", "디지몬", "community"))

    print("6. Crawling DC TCG Digimon...")
    all_new_items.extend(crawl_dc_gallery("tcg_digimon", "디지카", "card"))

    print("7. Crawling TCG Portals (digimoncard.io, digimoncard.co.kr, digimoncard.com)...")
    all_new_items.extend(crawl_tcg_portals())

    print("8. Crawling WithTheWill...")
    all_new_items.extend(crawl_withthewill_news())

    print("9. Crawling Wikimon Updates...")
    all_new_items.extend(crawl_wikimon_updates())

    print("10. Crawling YouTube...")
    all_new_items.extend(crawl_youtube_digimon())

    print("11. Crawling Twitter (X)...")
    all_new_items.extend(crawl_twitter_digimon())

    print("12. Crawling Instagram (via Google News)...")
    all_new_items.extend(crawl_instagram_digimon())

    print("13. Crawling Hobby Media...")
    all_new_items.extend(crawl_premium_bandai_hobby())

    print("14. Crawling Global Anime News...")
    all_new_items.extend(crawl_global_anime_news())

    print("15. Crawling official site news & products (digimon.net)...")
    all_new_items.extend(crawl_official_topics())
    all_new_items.extend(crawl_official_products())

    print("16. Crawling Digimon Meta & Egman Events (TCG)...")
    all_new_items.extend(crawl_digimon_meta_and_egman())

    print("17. Crawling Figure & Hobby Shops (AmiAmi, GoodSmile, HLJ)...")
    all_new_items.extend(crawl_figure_shops())

    print("18. Crawling Ruliweb Game & Anime Info...")
    all_new_items.extend(crawl_ruliweb_game_and_anime())

    print("19. Crawling Arca.live Digimon Channel...")
    all_new_items.extend(crawl_arcalive_digimon())

    print("20. Crawling Naver Game Lounge...")
    all_new_items.extend(crawl_naver_game())

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

    # 기존 데이터 timestamp 및 카테고리 보정 (정규화 및 불필요 소스 즉시 숙청)
    valid_existing = []
    for item in existing_items:
        # 차단 소스 (레딧, 프반, 무관 인스타 등) 즉시 탈락
        if is_spam(item):
            continue

        # 디지몬웹 프반 302 리다이렉트 상품 링크 안전 처리 (방안 A)
        if item.get("source_badge") == "디지몬웹" and "item_type=1" in item.get("link", ""):
            item["link"] = "https://digimon.net/product/goods/"

        # 위키몬: 신규 등록 문서([위키몬 신규])만 유지하고 과거 일반 수정글은 제외
        if item.get("source_badge") == "위키몬":
            if not item.get("title", "").startswith("[위키몬 신규]"):
                continue

        if "timestamp" not in item:
            item["timestamp"] = parse_to_timestamp(item.get("created_at", ""))
            item["created_at"] = format_display_date(item["timestamp"])
        
        # category가 리스트나 튜플 형태인 경우 문자열로 복구
        if isinstance(item.get("category"), (list, tuple)):
            item["category"] = item["category"][0]
        
        # 카테고리 최신 규칙에 따라 재분류
        title = item.get("title", "")
        sbadge = item.get("source_badge", "")
        new_cat, new_name = classify_category(title, item.get("category", "general"), sbadge)
        item["category"] = new_cat
        item["category_name"] = new_name
        valid_existing.append(item)

    # ID 기준 중복 제거 및 최신 데이터 우선 병합
    feed_map = {item["id"]: item for item in valid_existing if not is_spam(item)}
    for item in all_new_items:
        if not is_spam(item):
            # 새로 수집된 아이템도 category 정규화
            if isinstance(item.get("category"), (list, tuple)):
                item["category"] = item["category"][0]
            # 발매 예정 상품처럼 날짜가 '지금'으로 찍히는 항목은 처음 수집한 시각을 유지 (매시간 맨 위로 올라오지 않도록)
            prev = feed_map.get(item["id"])
            if item.pop("keep_first_seen", False) and prev:
                item["timestamp"] = prev.get("timestamp", item["timestamp"])
                item["created_at"] = prev.get("created_at", item["created_at"])
            feed_map[item["id"]] = item

    # [핵심 1] 최근 90일(약 3달) 이내 데이터 보관 (사용자가 앱에서 기간 필터 선택 가능)
    cutoff_timestamp = int((datetime.now() - timedelta(days=90)).timestamp())
    filtered_feeds = [
        item for item in feed_map.values()
        if item.get("timestamp", 0) >= cutoff_timestamp and not is_spam(item)
    ]

    translate_official_titles(filtered_feeds)

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

    print(f"Successfully filtered (last 90 days) & sorted newest-first: {len(filtered_feeds)} items saved.")

if __name__ == "__main__":
    main()
