import json
import os
import requests

# 주요 한국어 더빙명 <-> 일본 원칭(가타카나 음차) 매핑 테이블
KO_JA_NAME_MAP = {
    "agumon": {"ko": "아구몬", "ja_ko": "아구몬", "aliases": ["아구몬"]},
    "gabumon": {"ko": "파피몬", "ja_ko": "가부몬", "aliases": ["파피몬", "가부몬"]},
    "gomamon": {"ko": "쉬라몬", "ja_ko": "고마몬", "aliases": ["쉬라몬", "고마몬"]},
    "palmon": {"ko": "팔몬", "ja_ko": "파르몬", "aliases": ["팔몬", "파르몬"]},
    "tentomon": {"ko": "텐타몬", "ja_ko": "텐토몬", "aliases": ["텐타몬", "텐토몬"]},
    "piyomon": {"ko": "피요몬", "ja_ko": "피요몬", "aliases": ["피요몬"]},
    "biyomon": {"ko": "피요몬", "ja_ko": "피요몬", "aliases": ["피요몬", "비요몬"]},
    "patamon": {"ko": "파닥몬", "ja_ko": "파타몬", "aliases": ["파닥몬", "파타몬"]},
    "tailmon": {"ko": "가트몬", "ja_ko": "테일몬", "aliases": ["가트몬", "테일몬", "테이루몬"]},
    "gatomon": {"ko": "가트몬", "ja_ko": "테일몬", "aliases": ["가트몬", "테일몬"]},
    "wormmon": {"ko": "웜몬", "ja_ko": "츄츄몬", "aliases": ["웜몬", "츄츄몬", "추추몬"]},
    "chibimon": {"ko": "꼬마몬", "ja_ko": "치비몬", "aliases": ["꼬마몬", "치비몬"]},
    "v-mon": {"ko": "브이몬", "ja_ko": "브이몬", "aliases": ["브이몬", "뷔몬", "브이몬"]},
    "veemon": {"ko": "브이몬", "ja_ko": "브이몬", "aliases": ["브이몬"]},
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
    "impmon": {"ko": "임프몬", "ja_ko": "임프몬", "aliases": ["임프몬"]},
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
    "daemon": {"ko": "마왕몬", "ja_ko": "데몬", "aliases": ["마왕몬", "데몬"]},
    "creepymon": {"ko": "마왕몬", "ja_ko": "데몬", "aliases": ["마왕몬", "데몬"]},
    "dukemon": {"ko": "듀크몬", "ja_ko": "듀크몬", "aliases": ["듀크몬", "갈란트몬"]},
    "gallantmon": {"ko": "듀크몬", "ja_ko": "듀크몬", "aliases": ["듀크몬", "갈란트몬"]},
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
    "beelzebumon": {"ko": "베르제브몬", "ja_ko": "베르제브몬", "aliases": ["베르제브몬", "베엘제몬"]},
    "beelzemon": {"ko": "베르제브몬", "ja_ko": "베르제브몬", "aliases": ["베르제브몬", "베엘제몬"]},
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
    "imperialdramon": {"ko": "황제드라몬", "ja_ko": "인페리얼드라몬", "aliases": ["황제드라몬", "임페리얼드라몬"]},
    "wargreymon": {"ko": "워그레이몬", "ja_ko": "워그레이몬", "aliases": ["워그레이몬"]},
    "metalgarurumon": {"ko": "메탈가루루몬", "ja_ko": "메탈가루루몬", "aliases": ["메탈가루루몬"]},
    "blackwargreymon": {"ko": "블랙워그레이몬", "ja_ko": "블랙워그레이몬", "aliases": ["블랙워그레이몬"]},
    "greymon": {"ko": "그레이몬", "ja_ko": "그레이몬", "aliases": ["그레이몬"]},
    "garurumon": {"ko": "가루루몬", "ja_ko": "가루루몬", "aliases": ["가루루몬"]},
    "metalgreymon": {"ko": "메탈그레이몬", "ja_ko": "메탈그레이몬", "aliases": ["메탈그레이몬"]},
    "weregarurumon": {"ko": "워가루루몬", "ja_ko": "웨어가루루몬", "aliases": ["워가루루몬", "웨어가루루몬"]},
    "skullgreymon": {"ko": "스컬그레이몬", "ja_ko": "스컬그레이몬", "aliases": ["스컬그레이몬"]},
    "shinegreymon": {"ko": "샤인그레이몬", "ja_ko": "샤인그레이몬", "aliases": ["샤인그레이몬"]},
    "miragegaogamon": {"ko": "미라주가오가몬", "ja_ko": "미라주가오가몬", "aliases": ["미라주가오가몬"]},
    "gammamon": {"ko": "감마몬", "ja_ko": "감마몬", "aliases": ["감마몬"]},
    "siriusmon": {"ko": "시리우스몬", "ja_ko": "시리우스몬", "aliases": ["시리우스몬"]},
    "devimon": {"ko": "데블몬", "ja_ko": "데비몬", "aliases": ["데블몬", "데비몬"]},
    "leomon": {"ko": "레오몬", "ja_ko": "레오몬", "aliases": ["레오몬"]},
    "ogremon": {"ko": "우가몬", "ja_ko": "오가몬", "aliases": ["우가몬", "오가몬"]},
    "etemon": {"ko": "에테몬", "ja_ko": "에테몬", "aliases": ["에테몬"]},
    "metaletemon": {"ko": "메탈에테몬", "ja_ko": "메탈에테몬", "aliases": ["메탈에테몬"]},
    "pinocchimon": {"ko": "피노키몬", "ja_ko": "피노키몬", "aliases": ["피노키몬", "퍼펫몬"]},
    "puppetmon": {"ko": "피노키몬", "ja_ko": "피노키몬", "aliases": ["피노키몬", "퍼펫몬"]},
    "mugendramon": {"ko": "파워드라몬", "ja_ko": "무겐드라몬", "aliases": ["파워드라몬", "무겐드라몬", "머시ンド라몬"]},
    "machinedramon": {"ko": "파워드라몬", "ja_ko": "무겐드라몬", "aliases": ["파워드라몬", "무겐드라몬"]},
    "metalseadramon": {"ko": "메탈시드라몬", "ja_ko": "메탈시드라몬", "aliases": ["메탈시드라몬"]},
    "apocalymon": {"ko": "아포카리몬", "ja_ko": "아포카리몬", "aliases": ["아포카리몬"]},
    "diablomon": {"ko": "디아블로몬", "ja_ko": "디아블로몬", "aliases": ["디아블로몬", "디아보로몬"]},
    "diaboromon": {"ko": "디아블로몬", "ja_ko": "디아블로몬", "aliases": ["디아블로몬", "디아보로몬"]}
}

def clean_key(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "").replace(":", "").replace("_", "")

def fetch_and_build_all_index():
    print("Fetching all 1,488 Digimon from Digi-API...")
    url = "https://digi-api.com/api/v1/digimon?pageSize=1500"
    res = requests.get(url, timeout=30).json()
    items = res.get("content", [])
    print(f"Total fetched from Digi-API: {len(items)}")

    master_list = []
    for item in items:
        digi_id = item["id"]
        raw_name = item["name"]
        k = clean_key(raw_name)

        # 기본 이름 설정
        name_ko = raw_name
        name_ja_ko = raw_name
        aliases = [raw_name]

        # 정밀 매핑 확인
        matched = False
        for map_k, map_v in KO_JA_NAME_MAP.items():
            if map_k in k or k in map_k:
                name_ko = map_v["ko"]
                name_ja_ko = map_v["ja_ko"]
                aliases.extend(map_v["aliases"])
                matched = True
                break

        if not matched:
            # -mon 형태면 한국어 음차 보정
            if raw_name.endswith("mon"):
                base = raw_name[:-3]
                name_ko = f"{base}몬"
                aliases.append(name_ko)

        aliases = list(set(aliases))

        master_list.append({
            "id": digi_id,
            "name": raw_name,
            "name_ko": name_ko,
            "name_ja_ko": name_ja_ko,
            "aliases": aliases,
            "image": item.get("image")
        })

    print(f"Built master index with {len(master_list)} entries.")
    
    os.makedirs("docs/data", exist_ok=True)
    os.makedirs("public/data", exist_ok=True)

    for target in ["docs/data/digimon_all_index.json", "public/data/digimon_all_index.json"]:
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"total": len(master_list), "digimons": master_list}, f, ensure_ascii=False, indent=2)
        print(f"Saved master index to {target}")

if __name__ == "__main__":
    fetch_and_build_all_index()
