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

## 번호

- 공식 도감: `No.0001`부터. **오래된 등록이 1번**(공식 목록은 최신순이라 역순으로 매김).
- 한 번 매긴 번호는 `data/official/numbers.json`에 고정되고, 새 디지몬은 뒤에 이어 붙습니다.
- 공식 도감에 없는 Digi-API 디지몬: `EX-0001`부터 (Digi-API id 순). 목록에서 "공식 외 디지몬(EX) 포함"을 켜야 보입니다.

## 이름

- 기본은 공식 한국어 표기. 공식 한국어 페이지는 일본어 기계 번역이라 더빙명과 다를 수 있어, Digi-API 인덱스의 한국 더빙명이 다르면 함께 표시합니다.

## 진화

- 공식 상세 페이지의 **"관련된 디지몬"** 을 단계로 나눕니다.
  - 단계가 바로 하나 아래 → 진화 전, 바로 하나 위 → 진화 후, 나머지 → 관련 디지몬
  - A의 진화 후에 B가 있으면 B의 진화 전에도 A를 넣어 양방향을 맞춥니다.
- 게임(타임스트레인저·해커스 메모리) 진화는 **보류**. 자료가 생기면 `data/game_evolutions.json`에 `{"0066": {"prior": [...], "next": [...], "source": "..."}}` 형태로 넣으면 `build_dex.py`가 반영합니다.

## 공식 ↔ Digi-API 연결

영문 표기 일치 → 표기 규칙(X항체·2006·모드 등) → 같은 단계 안 유사도 순으로 자동 연결합니다.
잘못 연결되거나 빠진 것은 `data/official/api_map.json`에 `"공식 디렉터리명": "Digi-API 이름"`으로 지정한 뒤 `python scraper/build_dex.py`를 실행합니다. 결과는 `data/official/match_report.md`에서 확인합니다.
