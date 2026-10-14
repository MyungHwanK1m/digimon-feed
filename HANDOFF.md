# 작업 인수인계 (PC에서 이어서 작업하기)

클라우드 세션에서는 네트워크 정책 때문에 `digi-api.com`, `wikimon.net` 등에 접속할 수 없어 일부 검증을 하지 못했습니다.
PC(로컬)에서는 인터넷이 열려 있으므로 아래 순서대로 이어서 진행하면 됩니다.

## 1. 현재 상태

- 작업 브랜치: `claude/tender-davinci-dcqvn9` (main 기준 + 수정 커밋 1개, 아직 PR 없음)
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

### 3-2. 인덱스에 레벨 데이터 채우기 (Digi-API 필요)
```bash
pip install -r scraper/requirements.txt
python scraper/generate_digidex.py        # 1,488종 상세 조회, 수 분 소요
```
- 이 단계가 끝나야 진화 목록의 "역진화 필터"와 카드의 단계 표시가 동작합니다.
- 또는 GitHub Actions 탭 → `Build Digi-Dex Index` → Run workflow (단, 이 워크플로는 브랜치가 main에 머지된 뒤에 목록에 나타남)

### 3-3. 실제 API 응답으로 검증
```bash
curl -s https://digi-api.com/api/v1/digimon/Omegamon | python -m json.tool | head -80
curl -s "https://digi-api.com/api/v1/level?pageSize=50"
curl -s "https://digi-api.com/api/v1/type?pageSize=300"
```
확인할 것:
- [ ] `levels` 값이 `Baby I / Baby II / Child / Adult / Perfect / Ultimate / Armor / Hybrid / Unknown` 인지
      (다르면 `index.html`의 `LEVEL_KO` 수정)
- [ ] 조그레스 진화의 `condition` 형식 (예: `with Metal Garurumon`)
      → `isJogressCondition()`이 올바르게 잡는지
- [ ] 타입 목록 중 `DIGI_TYPES_KO`에 없는 것 추가 (현재 없는 타입은 영어 그대로 표시됨)

### 3-4. 앱 실행해서 눈으로 확인
```bash
cd public
python -m http.server 8080
# 브라우저에서 http://localhost:8080 접속 → "디지몬 도감/설정집" 탭
```
- [ ] 추천 칩(오메가몬, 듀크몬, 아구몬, 길몬, 워그레이몬, 아그니몬, 베르제브몬, 알파몬, 황제드라몬, 브이몬, 가트몬) 각각 열어보기
- [ ] 진화 카드 클릭 시 올바른 디지몬으로 이동하는지
- [ ] 그레이몬 → 진화 전에 스카몬 같은 역진화가 섞이지 않는지 (3-2 이후)
- [ ] 궁극체 디지몬에서 "최종 진화 형태" 표시가 적절한지
- [ ] 서비스 워커 캐시 때문에 옛 화면이 보이면 강력 새로고침(Ctrl+Shift+R)

### 3-5. 위키와 대조할 항목 (확실하지 않은 것)
| 항목 | 현재 값 | 확인처 |
|---|---|---|
| 가루루몬 계열 한국 더빙명 | 가루몬 / 워가루몬 / 메탈가루몬 (기존 '가루루몬'은 별칭으로 유지) | 나무위키 |
| 웜몬 한국 더빙명 | 츄츄몬 (일본명 웜몬) | 나무위키 |
| 꼬마몬(Chibimon), 시드몬(Tanemon), 둥실몬(Pukamon), 어니언몬(Pyocomon), 모티몬(Mochimon) 더빙명 | 기존 작성자 값 유지 | 나무위키 |
| 플레이드라몬(Fladramon) 표기 | 플레이드라몬 (별칭: 플라드라몬) | 나무위키 |
| `CANONICAL_LINES`의 각 진화 라인 | 애니메이션 기준으로 작성 | wikimon.net |

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
