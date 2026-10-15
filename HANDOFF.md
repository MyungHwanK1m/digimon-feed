# 작업 인수인계 (PC에서 이어서 작업하기)

클라우드 세션에서는 네트워크 정책 때문에 `digi-api.com`, `wikimon.net` 등에 접속할 수 없어 일부 검증을 하지 못했습니다.
PC(로컬)에서는 인터넷이 열려 있으므로 아래 순서대로 이어서 진행하면 됩니다.

## 1. 현재 상태

- 작업 브랜치: `claude/tender-davinci-dcqvn9` (1차 작업은 PR #1로 main에 머지됨)

### 2차 작업 (진화 체계 Digi-API 기준 전환 · 인스타그램)
- 진화 목록은 **Digi-API 데이터를 그대로 사용**. `CANONICAL_LINES`(원작 애니 라인)는 목록을 바꾸지 않고 **앞쪽 정렬에만** 사용
- 일반 진화 = 바로 다음/이전 단계(같은 단계 모드·변종 포함), **워프진화** = 조건에 "Warp" 또는 2단계 이상 건너뜀 → 접이식 "🌀 워프진화" 패널
- 역방향(퇴화) 항목은 인덱스 레벨로 제외. 긴 목록은 "N체 더 보기"
- 점검용 진화 데이터: `data/digimon_evolutions.json` (인덱스 빌드 시 함께 갱신, 웹앱은 미사용)
  - 1,488종 전수 점검 결과: 워프 751건, 역방향 601건 제외, 원작 라인은 모두 목록 맨 앞
- 인스타그램: 직접 접근은 로그인 리다이렉트라 불가 → 구글뉴스 `site:instagram.com` 검색으로 수집 (`scraper/crawl.py`의 `crawl_instagram_digimon`)
- 앱 이름에서 "블루 카드" 표기 제거 (디자인 테마는 유지)
- 진화 보기 전환: 원작 라인이 있는 디지몬은 기본 **"애니"** 보기(원작 진화만), **"전체"** 보기는 Digi-API 전체 + 워프 패널. 선택은 브라우저에 저장
- 출처 배지: 진화 조건 문구로 `바이탈`·`펜듈럼`·`TCG`·`아머진화`·`스피릿`·`버스트`·`X항체` 표시 (조건 문구가 있는 약 40% 항목에만 해당)

### 1차 작업
- 수정 완료 내용 (커밋 `6ad0b80`)
  - 진화 엔진 재작성: 대표 진화 라인(`CANONICAL_LINES`)을 영문명 기준으로 정리, ID·한글명은 인덱스에서 조회
  - 단계 번역: Digi-API 일본식 표기 기준 (Ultimate = 궁극체, Baby II = 유년기 II)
  - 최종 형태 판정: 이름 키워드 → "궁극체 이상 + 다음 진화 없음"
  - 조그레스 재료는 지우지 않고 `조그레스` 배지로 표시
  - 로컬 한국어 도감(`data/digidex_ko.json`) 12종 다시 연결
  - 유형 번역 순서 버그 수정, 한글명 생성 규칙 수정 (130종 → 230종 번역)
  - XSS 방지(피드·API 텍스트 이스케이프), 서비스 워커 캐시 범위 제한
  - `scraper/generate_digidex.py`에 레벨 수집 + `--offline` 모드 추가
  - `.github/workflows/build-digidex.yml` (인덱스 재생성 워크플로) 추가

## 2. 파일 구조 메모

- 웹앱 원본: `public/` → **수정 후 반드시 `docs/`에 같은 파일 복사** (GitHub Pages가 `docs/`를 서빙)
  ```bash
  cp public/index.html docs/index.html
  cp public/sw.js docs/sw.js
  ```
- 진화 엔진: `public/index.html` 안의 `Korean Translation & Evolution Engine` 구역
  (`translateLevel`, `translateType`, `CANONICAL_LINES`, `cleanAndPrioritizeEvolutions`)
- 한글 이름 사전: `scraper/generate_digidex.py`의 `KO_JA_NAME_MAP`
- 인덱스 데이터: `public/data/digimon_all_index.json` (스크립트가 `docs/data/`에도 같이 저장)

## 3. PC에서 할 일 (순서대로)

### 3-1. 브랜치 받기
```bash
git fetch origin
git checkout claude/tender-davinci-dcqvn9
git pull
```

### 3-2. ✅ 인덱스 레벨 데이터 (완료)
- GitHub Actions에서 실행해 커밋 `642fe93`으로 반영됨 (1,488종 중 1,347종 레벨 확보, 나머지는 API에 레벨 없음)
- 이후 갱신: main 머지 후 Actions → `Build Digi-Dex Index` → Run workflow (또는 매주 자동)

### 3-3. ✅ 실제 API 응답 형식 확인 (완료, Actions 로그 기준)
- 단계: `Baby I / Baby II / Child / Adult / Perfect / Ultimate / Armor / Hybrid / Unknown` → `LEVEL_KO`와 일치
- 조그레스 조건: `with Garurumon`(조그레스), `with or without ...`(선택), `with X Eraser`·`with the Human Spirit of Fire`(아이템/스피릿), `Warp Evolution`
  → `isJogressCondition()`을 이 형식에 맞게 수정
- 진화 목록에 역방향 항목 포함 확인 (아구몬 진화 전에 그레이몬·스카몬) → 레벨 필터로 제거됨
- 그레이몬 다음 진화가 175개 → 같은 계열 이름·조건 없는 진화를 앞쪽에 정렬
- 유형 `Lesser`(레서형) 추가. 유형 전체 목록은 API 페이지 제한으로 일부만 확인됨 → 화면에 영어로 나오는 유형이 보이면 `DIGI_TYPES_KO`에 추가

### 3-4. ✅ 앱 실행해서 눈으로 확인 (완료, PC)
- 추천 칩 11개 모두 확인. 듀크몬 칩이 카오스듀크몬을 열던 문제 수정 (이름 일치를 별칭 일치보다 우선)
- 진화 카드 이동, 단계 표시, "최종 진화 형태"(블래스트 모드·팔라딘 모드) 정상
- 같은 단계 양방향 항목(알파몬 ↔ 알파몬 왕룡검)은 진화 전 목록에서 제외
- 유형 150종 전체를 `DIGI_TYPES_KO`에 반영 (`/type` API 전 페이지 기준), 조그레스 판정에서 디지멘탈·"with the ..." 제외, X항체 동료는 조그레스로 인정

### 3-5. ✅ 위키 대조 결과 (완료, 나무위키 문서 제목 기준)
| 항목 | 결과 |
|---|---|
| 가루몬 / 워가루몬 / 메탈가루몬, 꼬마몬, 시드몬, 둥실몬, 모티몬, 플롯트몬 | 맞음 |
| 웜몬 | 츄츄몬 → **추추몬** |
| 표코몬(Pyocomon) | 어니언몬 → **어니몬** |
| 플레이드라몬(Fladramon) | → **화염드라몬** |
| 라이드라몬(Lighdramon) | → **번개드라몬** |
| 바이크몬(Vikemon), 호우오몬(Hououmon) | 사전에 추가 (**바이킹몬**, 호우오몬) |
| `CANONICAL_LINES` | 아구몬 → 티라노몬 제거(애니 진화 아님), 화염드라몬·번개드라몬 진화 전 = 브이몬 추가 |

더빙명을 고칠 때는 `scraper/generate_digidex.py`의 사전을 수정한 뒤:
```bash
python scraper/generate_digidex.py --offline   # 네트워크 없이 한글명만 다시 생성
```

### 3-6. 마무리
```bash
git add -A
git commit -m "..."
git push
```
이후 GitHub에서 `claude/tender-davinci-dcqvn9` → `main` PR 생성 후 머지.

## 4. Claude Code로 이어서 작업할 때

PC의 Claude Code에서 이 저장소를 열고 이렇게 요청하면 됩니다:
> HANDOFF.md 읽고 3번 할 일 이어서 진행해줘
