# 진화 체계 · 도감 DB 규칙 (기준 문서)

도감의 진화 표시와 도감 데이터 관리는 **이 문서가 기준**입니다. 규칙을 바꿀 때는 이 문서를 먼저 고치고 코드를 맞춥니다.

## 1. 데이터 관리 방식

도감 정보(기술·도감 설정·진화 루트)는 **`data/digidex_db.yaml` 한 파일**에서 관리합니다(DB 원본).
진화 루트는 따로 관리하지 않고 **각 디지몬의 도감 항목(`dex`) 안에 속한 정보**로 둡니다.

```
data/digidex_db.yaml ──(scraper/build_db.py)──┬─> public/data/digidex_db.json  (앱이 읽음)
   (직접 수정)                                 └─> 이 문서의 다이어그램·표       (그림으로 확인)
```

도감 항목 예시:

```yaml
Agumon:
  dex:
    name_ko: 아구몬
    level: 성장기
    skills:
    - {name: 베이비 플레임 (Baby Flame), desc: 입에서 작지만 고열의 화염구를 토해낸다.}
    profile: 두 발로 걸어 다닐 수 있게 진화하여…
    evolution: {prior: [Koromon], next: [Greymon]}   # 선택
```

- 키는 **Digi-API 영문명 그대로** 적습니다. ID·한글명은 인덱스에서 찾습니다.
- `evolution`의 `prior`/`next`는 바로 이전/다음 진화만 적습니다. 조그레스는 재료 두 디지몬을 `prior`에 적고 `jogress: true`를 붙입니다.
- `python scraper/build_db.py`가 없는 이름·잘못된 형식을 오류로 막고, 단계가 맞지 않으면 경고합니다. main에 push하면 Actions가 자동으로 실행합니다.

## 2. 전제: 진화는 출처마다 다르다

디지몬에는 모든 작품이 따르는 하나의 공식 진화 트리가 없습니다.
애니메이션·게임·육성기기(V-Pet, 펜듈럼, 바이탈 브레스)·TCG가 각자 진화 경로를 정합니다.
Digi-API는 이 모든 출처를 **구분 없이 한 목록에 합쳐** 제공합니다. 그래서 아구몬의 다음 진화가 75개나 됩니다.

## 3. 화면의 진화 보기

| 보기 | 데이터 | 언제 보이나 |
|---|---|---|
| **도감** | 도감 항목의 `evolution` | `evolution`이 적힌 디지몬에서 기본. **[도감 \| 전체]** 전환 버튼이 나옴 |
| **전체** | Digi-API 진화 목록 그대로 | `evolution`이 없는 디지몬은 항상 이 보기 |

마지막으로 고른 보기는 브라우저에 저장됩니다.

### "전체" 보기 표시 규칙

1. Digi-API의 진화 전/후 목록을 가져옵니다.
2. 인덱스의 단계(level)로 각 항목을 분류합니다.
   - 역방향(퇴화 데이터) → 제외
   - 워프진화 → 아래 접이식 **🌀 워프진화** 패널
   - 나머지 → 일반 진화 목록
3. 같은 단계끼리 진화 전·후에 모두 들어 있는 항목은 진화 후에만 둡니다. 단, 도감 `evolution.prior`에 적힌 것은 유지합니다.
4. 정렬 순서: 도감 `evolution`에 적힌 진화 → 바로 다음 단계 → 같은 계열 이름 → 조건 없는 진화 → 나머지
5. 8개를 넘으면 "N체 더 보기"로 펼칩니다.
6. 궁극체 이상인데 진화 후(일반·워프)가 하나도 없으면 "최종 진화 형태"로 표시합니다.

## 4. 용어

| 용어 | 뜻 |
|---|---|
| 단계 | 유년기 I(1) → 유년기 II(2) → 성장기(3) → 성숙기(4) → 완전체(5) → 궁극체(6). Digi-API 표기는 Baby I / Baby II / Child / Adult / Perfect / Ultimate. 아머체·하이브리드체는 단계 비교를 하지 않음 |
| 일반 진화 | 바로 다음(또는 이전) 단계로의 진화. 같은 단계의 모드 체인지·변종도 포함 |
| 워프진화 | 조건에 "Warp"가 있거나 단계를 2칸 이상 건너뛰는 진화 |
| 역방향 항목 | "다음 진화"인데 단계가 더 낮은 항목 등. Digi-API의 퇴화 데이터라 표시하지 않음 |
| 조그레스 | 두 디지몬이 합체하는 진화. Digi-API 조건이 `with <디지몬>` 형태이거나, 도감 `evolution`에 `jogress: true`가 있을 때 표시 |
| 출처 배지 | Digi-API 조건 문구에서 찾은 출처·방식: 바이탈, 펜듈럼, TCG, 아머진화, 스피릿, 버스트, X항체. 조건이 비어 있는 항목(약 60%)에는 붙지 않음 |

## 5. 현재 DB 내용

아래는 `data/digidex_db.yaml`에서 자동으로 만들어집니다. GitHub에서 이 파일을 열면 진화 루트가 그림으로 보입니다.

<!-- BEGIN:DIAGRAMS (scraper/build_db.py 가 자동 생성 — 직접 수정하지 마세요) -->

### 도감 진화 루트

아직 `evolution`이 적힌 도감 항목이 없습니다. 모든 디지몬이 Digi-API 진화 목록으로 표시됩니다.

### 도감 항목

| 이름 | 키 | 기술 수 | 도감 설정 | 진화 루트 |
|---|---|---|---|---|
| 아구몬 | Agumon | 3 | 있음 | - |
| 워그레이몬 | War Greymon | 3 | 있음 | - |
| 오메가몬 | Omegamon | 3 | 있음 | - |
| 파닥몬 | Patamon | 2 | 있음 | - |
| 가트몬 | Tailmon | 2 | 있음 | - |
| 브이몬 | V-mon | 2 | 있음 | - |
| 황제드라몬 | Imperialdramon(Dragon Mode) | 2 | 있음 | - |
| 길몬 | Guilmon | 2 | 있음 | - |
| 듀크몬 | Dukemon | 3 | 있음 | - |
| 베르제브몬 | Beelzebumon | 3 | 있음 | - |
| 아그니몬 | Agnimon | 3 | 있음 | - |
| 알파몬 | Alphamon | 3 | 있음 | - |

<!-- END:DIAGRAMS -->

## 6. 아직 정하지 않은 것

- [ ] 도감 항목 늘리기: 지금은 12종만 직접 작성됨. 나머지는 Digi-API 영문 설명을 기계 번역해서 보여줌
- [ ] 도감 항목에 `evolution` 채우기: 지금은 비어 있어 모든 디지몬이 "전체" 보기
- [ ] 인덱스 한글명 보강: 1,488종 중 약 230종만 한글명이 있음 (`scraper/generate_digidex.py`의 사전)

## 7. 관련 파일

| 파일 | 역할 |
|---|---|
| `data/digidex_db.yaml` | **DB 원본 (직접 수정)**: 직접 작성한 도감(기술·도감 설정·진화 루트) |
| `scraper/build_db.py` | DB 검사 → `digidex_db.json` 생성 + 이 문서 5장 갱신 (`--check`는 검사만) |
| `public/data/digidex_db.json` | 앱이 읽는 빌드 결과 (직접 수정하지 않음, `docs/`에도 같은 파일) |
| `public/index.html` | 진화 엔진 (`cleanAndPrioritizeEvolutions`), 화면 |
| `public/data/digimon_all_index.json` | 1,488종 이름·한글명·단계 (Actions가 매주 갱신) |
| `data/digimon_evolutions.json` | Digi-API 진화 전체 사본 (점검용, 웹앱은 사용 안 함) |
| `scraper/generate_digidex.py` | 인덱스·진화 사본 생성, 한글명 사전 |
| `.github/workflows/build-db.yml` | DB가 바뀌면 `build_db.py` 자동 실행 |
| `.github/workflows/build-digidex.yml` | 인덱스 주간 갱신 (끝나고 `build_db.py`도 실행) |
