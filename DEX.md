# 디지몬 도감 구조

도감은 **공식 디지몬 도감([digimon.net/reference_ko](https://digimon.net/reference_ko/))** 을 기준으로 합니다. 피드와는 별개입니다.

## 데이터 흐름

```
공식 도감 ──(collect_official.py)──> data/official/reference.json  기본 정보·번호
                                     data/official/numbers.json    번호 고정표
Digi-API  ──(generate_digidex.py)──> public/data/digimon_all_index.json  그림·더빙명
                                         │
                          (build_dex.py) ▼
                       public/data/dex.json (+ docs/)  ← 앱이 읽는 파일
                       data/official/match_report.md   ← 공식↔Digi-API 연결 결과
```

- Actions `Collect Official Reference`: 매주 화요일 공식 도감 재수집 → `build_dex.py`
- Actions `Build Digi-Dex Index`: 매주 월요일 Digi-API 인덱스 갱신 → `build_dex.py`

## 저장하는 것 / 하지 않는 것

공식 사이트는 이미지·문장·데이터의 무단 전재를 금지하고 있어 **기본 정보만** 저장합니다.

| 저장 | 저장하지 않음 (공식 페이지로 연결) |
|---|---|
| 번호, 공식 한국어 이름, 영문 표기, 등급, 유형, 속성, X항체·크로스워즈 여부, 관련된 디지몬, 공식 페이지 주소 | 프로필 문장, 필살기, 공식 일러스트 |

그림은 Digi-API 이미지 주소를 사용합니다.

## 상세 화면에서 바로 보는 정보 (실행 중 불러옴, 저장 안 함)

| 항목 | 출처 | 비고 |
|---|---|---|
| 도감 설명·필살기 | Digi-API 영문 설명 → Gemini로 미리 번역 (`data/dex_ko/`) | 아직 번역 안 된 디지몬만 화면에서 MyMemory/Google 실시간 번역. 공식 문장과 다를 수 있음 |
| TCG 카드 사진 | digimoncard.io 공개 API (`search.php?n=영문명`) | 카드게임은 북미식 이름이라 이름이 다른 디지몬(예: 듀크몬=Gallantmon)은 못 찾을 수 있음 |

넣지 않은 것과 이유:
- **공식 페이지 미리보기**: 공식 사이트가 다른 사이트 안에 띄우는 것(`X-Frame-Options: SAMEORIGIN`)과 외부에서 내용을 불러오는 것(CORS)을 막음
- **공식 일러스트**: 기술적으로는 공식 서버 주소로 표시 가능하지만, 공식 이용 조건(무단 사용 금지) 때문에 사용하지 않음
- **도트 그림**: 팬 위키(Wikimon)에 모여 있으나 위키가 자동 접근을 막아(403) 디지몬별 파일 주소를 모을 수 없음

## 번호

- 공식 도감: `No.0001`부터. **오래된 등록이 1번**(공식 목록은 최신순이라 역순으로 매김).
- 한 번 매긴 번호는 `data/official/numbers.json`에 고정되고, 새 디지몬은 뒤에 이어 붙습니다.
- 공식 도감에 없는 Digi-API 디지몬: `EX-0001`부터 (Digi-API id 순). 목록에서 "공식 외 디지몬(EX) 포함"을 켜야 보입니다.

## 이름

- 기본은 공식 한국어 표기. 공식 한국어 페이지는 일본어 기계 번역이라 더빙명과 다를 수 있어, Digi-API 인덱스의 한국 더빙명이 다르면 함께 표시합니다.

## 진화

- 공식 도감의 "관련된 디지몬"은 **진화 관계가 아니므로** 진화 전/후로 추측하지 않고 "관련 디지몬"으로 그대로 보여 줍니다.
  (예전에는 단계 차이로 진화 전/후를 추측했는데, 밀레니엄몬의 진화 전이 피라니몬으로 나오는 등 틀린 결과가 생겨 폐기)
- 진화 전/후는 출처가 붙어 있는 Wikimon 데이터로 표시합니다 (아래 "진화 (Wikimon)").
- 게임(타임스트레인저·해커스 메모리) 진화는 **보류**. 자료가 생기면 `data/game_evolutions.json`에 `{"0066": {"prior": [...], "next": [...], "source": "..."}}` 형태로 넣으면 `build_dex.py`가 반영합니다.

## 공식 ↔ Digi-API 연결

영문 표기 일치 → 표기 규칙(X항체·2006·모드 등) → 같은 단계 안 유사도 순으로 자동 연결합니다.
잘못 연결되거나 빠진 것은 `data/official/api_map.json`에 `"공식 디렉터리명": "Digi-API 이름"`으로 지정한 뒤 `python scraper/build_dex.py`를 실행합니다. 결과는 `data/official/match_report.md`에서 확인합니다.

## 진화 (Wikimon)

- 출처: [Wikimon](https://wikimon.net) 각 디지몬 문서의 "Evolves From / Evolves To". 진화마다 붙은 출처(애니 회차·게임·기기·카드)를 함께 저장합니다.
- 수집: `scraper/collect_wikimon.py` — MediaWiki API(`api.php`)만 사용, 50문서씩, 요청 간 60초(robots.txt Crawl-delay), 프로젝트를 밝힌 User-Agent. 문서 본문은 저장하지 않고 진화 연결·조건·출처 이름만 저장.
- 결과: `data/wikimon/evolutions.json`, 분류 점검용 `data/wikimon/report.md`. `build_dex.py`가 `data/evo/<api_id//100>.json`으로 나눠 앱에 제공.
- 출처 분류: 📺애니 · 🎮게임 · 🃏TCG · 📟기기(V-pet) · 📚기타(공식 사전 등). 규칙은 `collect_wikimon.py`의 `CAT_RULES`.
- 화면: 출처 필터 + 진화 전 | 현재·아종 | 진화 후. 기본은 전체, 배지를 누르면 작품명·조건. 상세 화면에 "출처: Wikimon" 링크.
- 갱신: `collect-wikimon.yml` 매주 수요일.

## 미리 번역 (Gemini)

- `scraper/translate_dex.py`: Digi-API 영어 프로필·필살기를 Gemini로 번역 → `public|docs/data/dex_ko/<api_id//100>.json` (앱은 필요한 조각만 받음), 원장 `data/translations/dex_ko.json`
- 공식 한국어 이름을 용어집으로 넣어 이름 표기를 통일 (예: WarGreymon → 워그레이몬)
- 워크플로 `translate-dex.yml`: 매일 04:41 UTC, 안 된 것만 번역. 무료 등급 한도에 걸리면 저장 후 다음 날 이어서
- 피드: 공식 사이트(일본어) 제목도 `crawl.py`에서 Gemini 번역, 원제는 `title_ja`, 캐시 `data/translations/feed_titles.json`. 인물 이름은 `data/translations/names.json` 기준 "원작 이름(더빙 이름)"
- 필요: 저장소 Settings → Secrets and variables → Actions 에 `GEMINI_API_KEY` (선택: Variables 에 `GEMINI_MODEL`). 키가 없으면 번역 단계만 건너뜀
