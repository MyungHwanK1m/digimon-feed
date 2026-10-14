import json
import os
import re
import sys
import time

import requests

# 주요 한국어 더빙명 <-> 일본 원칭(가타카나 음차) 매핑 테이블 (기본형 기준)
KO_JA_NAME_MAP = {
    "agumon": {"ko": "아구몬", "ja_ko": "아구몬", "aliases": ["아구몬"]},
    "pagumon": {"ko": "파구몬", "ja_ko": "파구몬", "aliases": ["파구몬", "포구몬", "뽀구몬"]},
    "koromon": {"ko": "코로몬", "ja_ko": "코로몬", "aliases": ["코로몬"]},
    "botamon": {"ko": "깜몬", "ja_ko": "보타몬", "aliases": ["깜몬", "보타몬"]},
    "tunomon": {"ko": "뿔몬", "ja_ko": "츠노몬", "aliases": ["뿔몬", "츠노몬"]},
    "tsunomon": {"ko": "뿔몬", "ja_ko": "츠노몬", "aliases": ["뿔몬", "츠노몬"]},
    "gabumon": {"ko": "파피몬", "ja_ko": "가부몬", "aliases": ["파피몬", "가부몬"]},
    "garurumon": {"ko": "가루몬", "ja_ko": "가루루몬", "aliases": ["가루몬", "가루루몬"]},
    "weregarurumon": {"ko": "워가루몬", "ja_ko": "웨어가루루몬", "aliases": ["워가루몬", "워가루루몬", "웨어가루루몬"]},
    "metalgarurumon": {"ko": "메탈가루몬", "ja_ko": "메탈가루루몬", "aliases": ["메탈가루몬", "메탈가루루몬"]},
    "gomamon": {"ko": "쉬라몬", "ja_ko": "고마몬", "aliases": ["쉬라몬", "고마몬"]},
    "palmon": {"ko": "팔몬", "ja_ko": "파르몬", "aliases": ["팔몬", "파르몬"]},
    "tentomon": {"ko": "텐타몬", "ja_ko": "텐토몬", "aliases": ["텐타몬", "텐토몬"]},
    "kabuterimon": {"ko": "캅테리몬", "ja_ko": "카부테리몬", "aliases": ["캅테리몬", "카부테리몬"]},
    "atlurkabuterimon": {"ko": "아트라캅테리몬", "ja_ko": "아틀라카부테리몬", "aliases": ["아트라캅테리몬", "아틀라캅테리몬"]},
    "heraklekabuterimon": {"ko": "헤라클레스캅테리몬", "ja_ko": "헤라클레스카부테리몬", "aliases": ["헤라클레스캅테리몬", "헤라클레스카부테리몬"]},
    "piyomon": {"ko": "피요몬", "ja_ko": "피요몬", "aliases": ["피요몬"]},
    "biyomon": {"ko": "피요몬", "ja_ko": "피요몬", "aliases": ["피요몬", "비요몬"]},
    "patamon": {"ko": "파닥몬", "ja_ko": "파타몬", "aliases": ["파닥몬", "파타몬"]},
    "tokomon": {"ko": "토코몬", "ja_ko": "토코몬", "aliases": ["토코몬"]},
    "tailmon": {"ko": "가트몬", "ja_ko": "테일몬", "aliases": ["가트몬", "테일몬", "테이루몬"]},
    "gatomon": {"ko": "가트몬", "ja_ko": "테일몬", "aliases": ["가트몬", "테일몬"]},
    "plotmon": {"ko": "플롯트몬", "ja_ko": "프로트몬", "aliases": ["플롯트몬", "프로트몬"]},
    "salamon": {"ko": "플롯트몬", "ja_ko": "프로트몬", "aliases": ["플롯트몬", "샐러몬"]},
    "nyaromon": {"ko": "야옹몬", "ja_ko": "냐로몬", "aliases": ["야옹몬", "냐로몬"]},
    "wormmon": {"ko": "츄츄몬", "ja_ko": "웜몬", "aliases": ["츄츄몬", "추추몬", "웜몬"]},
    "chibimon": {"ko": "꼬마몬", "ja_ko": "치비몬", "aliases": ["꼬마몬", "치비몬"]},
    "chicomon": {"ko": "치코몬", "ja_ko": "치코몬", "aliases": ["치코몬"]},
    "v-mon": {"ko": "브이몬", "ja_ko": "브이몬", "aliases": ["브이몬", "뷔몬"]},
    "veemon": {"ko": "브이몬", "ja_ko": "브이몬", "aliases": ["브이몬"]},
    "vmon": {"ko": "브이몬", "ja_ko": "브이몬", "aliases": ["브이몬"]},
    "xv-mon": {"ko": "엑스브이몬", "ja_ko": "엑스브이몬", "aliases": ["엑스브이몬"]},
    "exveemon": {"ko": "엑스브이몬", "ja_ko": "엑스브이몬", "aliases": ["엑스브이몬"]},
    "stingmon": {"ko": "스팅몬", "ja_ko": "스팅몬", "aliases": ["스팅몬"]},
    "paildramon": {"ko": "파일드라몬", "ja_ko": "파일드라몬", "aliases": ["파일드라몬"]},
    "hawkmon": {"ko": "호크몬", "ja_ko": "호크몬", "aliases": ["호크몬"]},
    "armadimon": {"ko": "아르마몬", "ja_ko": "아르마디몬", "aliases": ["아르마몬", "아르마디몬"]},
    "armadillomon": {"ko": "아르마몬", "ja_ko": "아르마디몬", "aliases": ["아르마몬", "아르마디몬"]},
    "terriermon": {"ko": "테리어몬", "ja_ko": "테리아몬", "aliases": ["테리어몬", "테리아몬"]},
    "renamon": {"ko": "레나몬", "ja_ko": "레나몬", "aliases": ["레나몬"]},
    "guilmon": {"ko": "길몬", "ja_ko": "기루몬", "aliases": ["길몬", "기루몬"]},
    "gigimon": {"ko": "기기몬", "ja_ko": "기기몬", "aliases": ["기기몬"]},
    "growmon": {"ko": "그라우몬", "ja_ko": "그라우몬", "aliases": ["그라우몬"]},
    "megalogrowmon": {"ko": "메가로그라우몬", "ja_ko": "메가로그라우몬", "aliases": ["메가로그라우몬", "워그라우몬"]},
    "wargrowmon": {"ko": "메가로그라우몬", "ja_ko": "메가로그라우몬", "aliases": ["메가로그라우몬", "워그라우몬"]},
    "dukemon": {"ko": "듀크몬", "ja_ko": "듀크몬", "aliases": ["듀크몬", "갈란트몬"]},
    "gallantmon": {"ko": "듀크몬", "ja_ko": "듀크몬", "aliases": ["듀크몬", "갈란트몬"]},
    "impmon": {"ko": "임프몬", "ja_ko": "임프몬", "aliases": ["임프몬"]},
    "beelzebumon": {"ko": "베르제브몬", "ja_ko": "베르제브몬", "aliases": ["베르제브몬", "베엘제몬"]},
    "beelzemon": {"ko": "베르제브몬", "ja_ko": "베르제브몬", "aliases": ["베르제브몬", "베엘제몬"]},
    "culumon": {"ko": "동글몬", "ja_ko": "쿠루몬", "aliases": ["동글몬", "쿠루몬"]},
    "calumon": {"ko": "동글몬", "ja_ko": "쿠루몬", "aliases": ["동글몬", "쿠루몬"]},
    "monodramon": {"ko": "모노드라몬", "ja_ko": "모노드라몬", "aliases": ["모노드라몬"]},
    "justimon": {"ko": "저스티몬", "ja_ko": "져스티몬", "aliases": ["저스티몬", "져스티몬"]},
    "bokomon": {"ko": "포코몬", "ja_ko": "보코몬", "aliases": ["포코몬", "보코몬"]},
    "neemon": {"ko": "네몬", "ja_ko": "닙몬", "aliases": ["네몬", "닙몬", "네에몬"]},
    "vamdemon": {"ko": "묘티스몬", "ja_ko": "반데몬", "aliases": ["묘티스몬", "반데몬"]},
    "myotismon": {"ko": "묘티스몬", "ja_ko": "반데몬", "aliases": ["묘티스몬", "반데몬"]},
    "piemon": {"ko": "피에몬", "ja_ko": "피에로몬", "aliases": ["피에몬", "피에로몬"]},
    "piedmon": {"ko": "피에몬", "ja_ko": "피에로몬", "aliases": ["피에몬", "피에로몬"]},
    "piccolomon": {"ko": "피콜몬", "ja_ko": "피콜로몬", "aliases": ["피콜몬", "피콜로몬"]},
    "piximon": {"ko": "피콜몬", "ja_ko": "피콜로몬", "aliases": ["피콜몬", "피콜로몬"]},
    "demon": {"ko": "마왕몬", "ja_ko": "데몬", "aliases": ["마왕몬", "데몬"]},
    "daemon": {"ko": "마왕몬", "ja_ko": "데몬", "aliases": ["마왕몬", "데몬"]},
    "creepymon": {"ko": "마왕몬", "ja_ko": "데몬", "aliases": ["마왕몬", "데몬"]},
    "omegamon": {"ko": "오메가몬", "ja_ko": "오메가몬", "aliases": ["오메가몬", "옴니몬"]},
    "omnimon": {"ko": "오메가몬", "ja_ko": "오메가몬", "aliases": ["오메가몬", "옴니몬"]},
    "magnamon": {"ko": "매그너몬", "ja_ko": "매그너몬", "aliases": ["매그너몬"]},
    "angemon": {"ko": "엔젤몬", "ja_ko": "엔제몬", "aliases": ["엔젤몬", "엔제몬"]},
    "angewomon": {"ko": "엔젤우몬", "ja_ko": "엔제우몬", "aliases": ["엔젤우몬", "엔제우몬"]},
    "holyangemon": {"ko": "홀리엔젤몬", "ja_ko": "홀리엔제몬", "aliases": ["홀리엔젤몬", "홀리엔제몬", "마그나엔젤몬"]},
    "magnaangemon": {"ko": "홀리엔젤몬", "ja_ko": "홀리엔제몬", "aliases": ["홀리엔젤몬", "홀리엔제몬", "마그나엔젤몬"]},
    "seraphimon": {"ko": "세라피몬", "ja_ko": "세라피몬", "aliases": ["세라피몬"]},
    "ofanimon": {"ko": "오파니몬", "ja_ko": "오파니몬", "aliases": ["오파니몬"]},
    "ophanimon": {"ko": "오파니몬", "ja_ko": "오파니몬", "aliases": ["오파니몬"]},
    "lucemon": {"ko": "루체몬", "ja_ko": "루체몬", "aliases": ["루체몬"]},
    "agnimon": {"ko": "아그니몬", "ja_ko": "아그니몬", "aliases": ["아그니몬"]},
    "wolfmon": {"ko": "볼프몬", "ja_ko": "볼프몬", "aliases": ["볼프몬", "울프몬"]},
    "lobomon": {"ko": "볼프몬", "ja_ko": "볼프몬", "aliases": ["볼프몬", "울프몬"]},
    "fairimon": {"ko": "페어리몬", "ja_ko": "페어리몬", "aliases": ["페어리몬", "카제몬"]},
    "kazemon": {"ko": "페어리몬", "ja_ko": "페어리몬", "aliases": ["페어리몬", "카제몬"]},
    "chackmon": {"ko": "차크몬", "ja_ko": "차크몬", "aliases": ["차크몬", "쿠마몬"]},
    "kumamon": {"ko": "차크몬", "ja_ko": "차크몬", "aliases": ["차크몬", "쿠마몬"]},
    "blitzmon": {"ko": "블리츠몬", "ja_ko": "블리츠몬", "aliases": ["블리츠몬", "비틀몬"]},
    "beetlemon": {"ko": "블리츠몬", "ja_ko": "블리츠몬", "aliases": ["블리츠몬", "비틀몬"]},
    "löwemon": {"ko": "레베몬", "ja_ko": "뢰베몬", "aliases": ["레베몬", "뢰베몬"]},
    "lowemon": {"ko": "레베몬", "ja_ko": "뢰베몬", "aliases": ["레베몬", "뢰베몬"]},
    "kaisergreymon": {"ko": "카이저그레이몬", "ja_ko": "카이저그레이몬", "aliases": ["카이저그레이몬", "엠페러그레이몬"]},
    "magnagarurumon": {"ko": "매그너가루루몬", "ja_ko": "매그너가루루몬", "aliases": ["매그너가루루몬"]},
    "susanoomon": {"ko": "스사노오몬", "ja_ko": "스사노오몬", "aliases": ["스사노오몬"]},
    "alphamon": {"ko": "알파몬", "ja_ko": "알파몬", "aliases": ["알파몬"]},
    "jesmon": {"ko": "제스몬", "ja_ko": "제스몬", "aliases": ["제스몬"]},
    "gankoomon": {"ko": "간쿠몬", "ja_ko": "간쿠몬", "aliases": ["간쿠몬"]},
    "craniummon": {"ko": "크레니엄몬", "ja_ko": "크레니엄몬", "aliases": ["크레니엄몬"]},
    "craniamon": {"ko": "크레니엄몬", "ja_ko": "크레니엄몬", "aliases": ["크레니엄몬"]},
    "lordknightmon": {"ko": "로드나이트몬", "ja_ko": "로드나이트몬", "aliases": ["로드나이트몬", "크루세이더몬"]},
    "dynasmon": {"ko": "듀나스몬", "ja_ko": "듀나스몬", "aliases": ["듀나스몬"]},
    "sleipmon": {"ko": "슬레이프몬", "ja_ko": "슬레이프몬", "aliases": ["슬레이프몬", "켄타우로스몬"]},
    "kentaurosmon": {"ko": "슬레이프몬", "ja_ko": "슬레이프몬", "aliases": ["슬레이프몬", "켄타우로스몬"]},
    "duftmon": {"ko": "두프트몬", "ja_ko": "두프트몬", "aliases": ["두프트몬", "레오파드몬"]},
    "leopardmon": {"ko": "두프트몬", "ja_ko": "두프트몬", "aliases": ["두프트몬", "레오파드몬"]},
    "examon": {"ko": "엑자몬", "ja_ko": "엑자몬", "aliases": ["엑자몬"]},
    "lilithmon": {"ko": "리리스몬", "ja_ko": "리리스몬", "aliases": ["리리스몬", "라일리스몬"]},
    "laylamon": {"ko": "리리스몬", "ja_ko": "리리스몬", "aliases": ["리리스몬", "라일리스몬"]},
    "leviamon": {"ko": "레비아몬", "ja_ko": "레비아몬", "aliases": ["레비아몬"]},
    "belphemon": {"ko": "벨페몬", "ja_ko": "벨페몬", "aliases": ["벨페몬"]},
    "barbamon": {"ko": "발바몬", "ja_ko": "발바몬", "aliases": ["발바몬"]},
    "imperialdramon": {"ko": "황제드라몬", "ja_ko": "임페리얼드라몬", "aliases": ["황제드라몬", "임페리얼드라몬"]},
    "wargreymon": {"ko": "워그레이몬", "ja_ko": "워그레이몬", "aliases": ["워그레이몬"]},
    "blackwargreymon": {"ko": "블랙워그레이몬", "ja_ko": "블랙워그레이몬", "aliases": ["블랙워그레이몬"]},
    "greymon": {"ko": "그레이몬", "ja_ko": "그레이몬", "aliases": ["그레이몬"]},
    "metalgreymon": {"ko": "메탈그레이몬", "ja_ko": "메탈그레이몬", "aliases": ["메탈그레이몬"]},
    "skullgreymon": {"ko": "스컬그레이몬", "ja_ko": "스컬그레이몬", "aliases": ["스컬그레이몬"]},
    "shinegreymon": {"ko": "샤인그레이몬", "ja_ko": "샤인그레이몬", "aliases": ["샤인그레이몬"]},
    "miragegaogamon": {"ko": "미라주가오가몬", "ja_ko": "미라주가오가몬", "aliases": ["미라주가오가몬"]},
    "gammamon": {"ko": "감마몬", "ja_ko": "감마몬", "aliases": ["감마몬"]},
    "siriusmon": {"ko": "시리우스몬", "ja_ko": "시리우스몬", "aliases": ["시리우스몬"]},
    "devimon": {"ko": "데블몬", "ja_ko": "데비몬", "aliases": ["데블몬", "데비몬"]},
    "leomon": {"ko": "레오몬", "ja_ko": "레오몬", "aliases": ["레오몬"]},
    "orgemon": {"ko": "우가몬", "ja_ko": "오가몬", "aliases": ["우가몬", "오가몬"]},
    "ogremon": {"ko": "우가몬", "ja_ko": "오가몬", "aliases": ["우가몬", "오가몬"]},
    "etemon": {"ko": "에테몬", "ja_ko": "에테몬", "aliases": ["에테몬"]},
    "metaletemon": {"ko": "메탈에테몬", "ja_ko": "메탈에테몬", "aliases": ["메탈에테몬"]},
    "pinochimon": {"ko": "피노키몬", "ja_ko": "피노키몬", "aliases": ["피노키몬", "퍼펫몬"]},
    "pinocchimon": {"ko": "피노키몬", "ja_ko": "피노키몬", "aliases": ["피노키몬", "퍼펫몬"]},
    "puppetmon": {"ko": "피노키몬", "ja_ko": "피노키몬", "aliases": ["피노키몬", "퍼펫몬"]},
    "mugendramon": {"ko": "파워드라몬", "ja_ko": "무겐드라몬", "aliases": ["파워드라몬", "무겐드라몬"]},
    "machinedramon": {"ko": "파워드라몬", "ja_ko": "무겐드라몬", "aliases": ["파워드라몬", "무겐드라몬"]},
    "metalseadramon": {"ko": "메탈시드라몬", "ja_ko": "메탈시드라몬", "aliases": ["메탈시드라몬"]},
    "seadramon": {"ko": "시드라몬", "ja_ko": "시드라몬", "aliases": ["시드라몬"]},
    "apocalymon": {"ko": "아포카리몬", "ja_ko": "아포카리몬", "aliases": ["아포카리몬"]},
    "diablomon": {"ko": "디아블로몬", "ja_ko": "디아블로몬", "aliases": ["디아블로몬", "디아보로몬"]},
    "mochimon": {"ko": "모티몬", "ja_ko": "모치몬", "aliases": ["모티몬", "모치몬"]},
    "pukamon": {"ko": "둥실몬", "ja_ko": "푸카몬", "aliases": ["둥실몬", "푸카몬"]},
    "tanemon": {"ko": "시드몬", "ja_ko": "타네몬", "aliases": ["시드몬", "타네몬"]},
    "pyocomon": {"ko": "어니언몬", "ja_ko": "표코몬", "aliases": ["어니언몬", "표코몬", "요코몬"]},
    "zudomon": {"ko": "쥬드몬", "ja_ko": "쥬드몬", "aliases": ["쥬드몬", "주드몬"]},
    "togemon": {"ko": "니드몬", "ja_ko": "토게몬", "aliases": ["니드몬", "토게몬"]},
    "ikkakumon": {"ko": "원뿔몬", "ja_ko": "잇카쿠몬", "aliases": ["원뿔몬", "잇카쿠몬"]},
    "birdramon": {"ko": "버드라몬", "ja_ko": "버드라몬", "aliases": ["버드라몬"]},
    "lilimon": {"ko": "릴리몬", "ja_ko": "릴리몬", "aliases": ["릴리몬"]},
    "garudamon": {"ko": "가루다몬", "ja_ko": "가루다몬", "aliases": ["가루다몬"]},
    "tyranomon": {"ko": "티라노몬", "ja_ko": "티라노몬", "aliases": ["티라노몬"]},
    "geogreymon": {"ko": "지오그레이몬", "ja_ko": "지오그레이몬", "aliases": ["지오그레이몬"]},
    "rizegreymon": {"ko": "라이즈그레이몬", "ja_ko": "라이즈그레이몬", "aliases": ["라이즈그레이몬"]},
    "fladramon": {"ko": "플레이드라몬", "ja_ko": "플레이드라몬", "aliases": ["플레이드라몬", "플라드라몬"]},
    "lighdramon": {"ko": "라이드라몬", "ja_ko": "라이드라몬", "aliases": ["라이드라몬"]},
    "rosemon": {"ko": "로제몬", "ja_ko": "로제몬", "aliases": ["로제몬"]},
    "diaboromon": {"ko": "디아블로몬", "ja_ko": "디아블로몬", "aliases": ["디아블로몬", "디아보로몬"]}
}

# 접두사 한글 변환 (반드시 뒤에 공백이 있어야 접두사로 인정: "Chaosmon", "Darkdramon" 오분리 방지)
PREFIX_RULES = [
    (r"^Toy\s+", "토이"),
    (r"^Clear\s+", "클리어"),
    (r"^Yuki\s+", "유키"),
    (r"^Snow\s+", "스노"),
    (r"^Bushi\s+", "부시"),
    (r"^Nise\s+", "가짜 "),
    (r"^Dot\s+", "도트 "),
    (r"^Santa\s+", "산타"),
    (r"^Black\s+", "블랙"),
    (r"^Dark\s+", "다크"),
    (r"^Chaos\s+", "카오스"),
]

# 모드 이름 한글 표기
MODE_WORDS_KO = {
    "burst": "버스트", "merciful": "머시풀", "paladin": "팔라딘", "crimson": "크림슨",
    "blast": "블래스트", "future": "퓨처", "satan": "사탄", "fighter": "파이터",
    "fighting": "파이터", "dragon": "드래곤", "rage": "레이지", "sleep": "슬립",
    "darkness": "다크니스", "destroy": "디스트로이", "holy": "홀리", "superior": "슈피리어",
    "falldown": "폴다운", "sagittarius": "사지타리우스", "chaos": "카오스", "hell": "헬",
    "wild": "와일드", "float": "플로트", "priest": "프리스트", "ruin": "루인",
    "leopard": "레오파드", "alterous": "알터러스",
}

# 괄호 접미사 한글 변환
SUFFIX_RULES = [
    (r"\(Black\)", "(흑)"),
    (r"\(Blue\)", "(청)"),
    (r"\(Red\)", "(적)"),
    (r"\(X-Antibody\)", "(X항체)"),
    (r"\(2006\s*Anime\s*Version\)", "(2006 애니판)"),
    (r"\(Blitz\s*Arm\)", "(블리츠 암)"),
    (r"\(Accel\s*Arm\)", "(액셀 암)"),
    (r"\(Critical\s*Arm\)", "(크리티컬 암)"),
]

# 이름 끝 접미어
TRAILING_RULES = [
    (r"\s+Hakase$", "박사"),
    (r"\s+Zwart\s+Defeat$", "즈와르트 디피트"),
    (r"\s+Zwart$", "즈와르트"),
]


def clean_key(name: str) -> str:
    return re.sub(r"[\s\-:_()]", "", name.lower())


# 사전 키도 동일 규칙으로 정규화 ("xv-mon" -> "xvmon")
NAME_MAP = {clean_key(k): v for k, v in KO_JA_NAME_MAP.items()}


def _mode_ko(words: str):
    parts = words.split()
    if any(w.lower() not in MODE_WORDS_KO for w in parts):
        return None
    return " ".join(MODE_WORDS_KO[w.lower()] for w in parts) + " 모드"


def translate_digimon_name(raw_name: str):
    name = raw_name.strip()

    # "(Dragon Mode (Black))" -> "(Dragon Mode) (Black)" 중첩 괄호 평탄화
    name_flat = re.sub(r"\(([^()]*?)\s*\((Black|Blue|Red)\)\)", r"(\1) (\2)", name)
    k_clean = clean_key(name_flat)

    # 1. 완전 일치 사전 검사
    if k_clean in NAME_MAP:
        entry = NAME_MAP[k_clean]
        return entry["ko"], entry["ja_ko"], list(dict.fromkeys(entry["aliases"] + [raw_name]))

    prefix_ko = ""
    suffix_parts = []
    trailing_ko = ""
    core_name = name_flat

    for pattern, ko_sub in PREFIX_RULES:
        if re.search(pattern, core_name, re.IGNORECASE):
            prefix_ko += ko_sub
            core_name = re.sub(pattern, "", core_name, flags=re.IGNORECASE).strip()

    for pattern, ko_sub in SUFFIX_RULES:
        if re.search(pattern, core_name, re.IGNORECASE):
            suffix_parts.append(ko_sub)
            core_name = re.sub(pattern, "", core_name, flags=re.IGNORECASE).strip()

    # "(XXX Mode)" 또는 이름 끝 "XXX Mode"
    m = re.search(r"\(\s*([A-Za-z ]+?)\s+Mode\s*\)", core_name) or re.search(r"\s+([A-Za-z]+)\s+Mode$", core_name)
    if m and _mode_ko(m.group(1)):
        suffix_parts.insert(0, f"({_mode_ko(m.group(1))})")
        core_name = (core_name[:m.start()] + core_name[m.end():]).strip()

    for pattern, ko_sub in TRAILING_RULES:
        if re.search(pattern, core_name, re.IGNORECASE):
            trailing_ko = ko_sub
            core_name = re.sub(pattern, "", core_name, flags=re.IGNORECASE).strip()
            break

    core_k = clean_key(core_name)
    aliases = [raw_name]
    translated = True

    if core_k in NAME_MAP:
        core_ko = NAME_MAP[core_k]["ko"]
        core_ja_ko = NAME_MAP[core_k]["ja_ko"]
        aliases.extend(NAME_MAP[core_k]["aliases"])
    else:
        # 사전에 없는 이름은 억지로 "Xxx몬" 형태로 바꾸지 않고 영문 원명을 유지
        core_ko = core_name
        core_ja_ko = core_name
        translated = False

    def join(core):
        base = f"{prefix_ko}{core}"
        if trailing_ko:
            base = f"{base} {trailing_ko}"
        if suffix_parts:
            base = f"{base} {' '.join(suffix_parts)}"
        return re.sub(r"\s{2,}", " ", base).strip()

    if not translated and (prefix_ko or suffix_parts or trailing_ko):
        # 코어가 미번역이면 부분 한글화로 "카오스 Dukemon Core" 같은 혼종을 만들지 않음
        return name, name, aliases

    final_ko = join(core_ko)
    final_ja = join(core_ja_ko)
    aliases.append(final_ko)
    aliases.append(final_ja)
    return final_ko, final_ja, list(dict.fromkeys(aliases))


def fetch_level(session, digi_id):
    url = f"https://digi-api.com/api/v1/digimon/{digi_id}"
    for attempt in range(3):
        try:
            data = session.get(url, timeout=20).json()
            levels = data.get("levels") or []
            return levels[0]["level"] if levels else None
        except Exception:
            time.sleep(1 + attempt * 2)
    return None


def write_index(master_list):
    os.makedirs("docs/data", exist_ok=True)
    os.makedirs("public/data", exist_ok=True)
    for target in ["docs/data/digimon_all_index.json", "public/data/digimon_all_index.json"]:
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"total": len(master_list), "digimons": master_list}, f, ensure_ascii=False, indent=2)
        print(f"Saved master index to {target}")


def load_existing_index():
    path = "public/data/digimon_all_index.json"
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {d["id"]: d for d in json.load(f).get("digimons", [])}


def build_entry(digi_id, raw_name, image, level):
    name_ko, name_ja_ko, aliases = translate_digimon_name(raw_name)
    entry = {
        "id": digi_id,
        "name": raw_name,
        "name_ko": name_ko,
        "name_ja_ko": name_ja_ko,
        "aliases": aliases,
        "image": image,
    }
    if level:
        entry["level"] = level
    return entry


def retranslate_offline():
    """네트워크 없이 기존 인덱스의 영문명으로 한글명만 다시 생성"""
    existing = load_existing_index()
    master_list = [
        build_entry(d["id"], d["name"], d.get("image"), d.get("level"))
        for d in sorted(existing.values(), key=lambda x: x["id"])
    ]
    write_index(master_list)


def fetch_and_build_all_index(with_levels=True):
    print("Fetching all Digimon from Digi-API...")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    url = "https://digi-api.com/api/v1/digimon?pageSize=1500"
    items = session.get(url, timeout=30).json().get("content", [])
    print(f"Total fetched from Digi-API: {len(items)}")

    existing = load_existing_index()
    master_list = []
    for i, item in enumerate(items):
        digi_id = item["id"]
        level = existing.get(digi_id, {}).get("level")
        if with_levels and not level:
            level = fetch_level(session, digi_id)
            time.sleep(0.05)
        master_list.append(build_entry(digi_id, item["name"], item.get("image"), level))
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(items)}")

    print(f"Built master index with {len(master_list)} entries.")
    write_index(master_list)


if __name__ == "__main__":
    if "--offline" in sys.argv:
        retranslate_offline()
    else:
        fetch_and_build_all_index(with_levels="--no-levels" not in sys.argv)
