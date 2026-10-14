import json
import os

DIGIDEX_DATA = [
    {
        "id": "agumon",
        "name_ko": "아구몬",
        "name_en": "Agumon",
        "name_ja": "アグモン",
        "level": "성장기",
        "attribute": "백신 (Vaccine)",
        "type": "파충류형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Agumon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/e/ee/Agumon_vpet_dm.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT1-010.jpg"
            }
        ],
        "skills": [
            {"name": "베이비 플레임 (Baby Flame)", "desc": "입에서 작지만 고열의 화염구를 토해내어 적을 공격한다."},
            {"name": "스핏파이어 (Spitfire)", "desc": "입에서 화염 탄환을 연사하여 견제하는 기술."},
            {"name": "크로스 파이트 (Cross Fight)", "desc": "양발의 날카로운 발톱을 교차하여 전방의 적을 할퀴는 육탄 기술."}
        ],
        "profile": "두 발로 걸어 다닐 수 있게 진화하여 작은 공룡의 모습을 한 파충류형 디지몬. 아직 성장기라 힘은 약하지만 성격은 매우 용감하고 두려움을 모른다. 손발에는 단단하고 날카로운 발톱이 자라나 있으며 전투 시에 위력을 발휘한다. 앞으로 거대하고 강력한 디지몬으로 진화할 가능성을 품고 있다."
    },
    {
        "id": "omegamon",
        "name_ko": "오메가몬",
        "name_en": "Omegamon",
        "name_ja": "オメガモン",
        "level": "궁극체",
        "attribute": "백신 (Vaccine)",
        "type": "성기사형 (로얄 나이츠)",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Omegamon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/7/75/Omegamon_vpet_penp.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT1-084.jpg"
            },
            {
                "type": "alt",
                "label": "✨ 머시풀 모드",
                "url": "https://digi-api.com/images/digimon/w/Omegamon_Merciful_Mode.png"
            }
        ],
        "skills": [
            {"name": "그레이 소드 (Grey Sword)", "desc": "워그레이몬의 형태를 한 왼팔에서 출현하는 무적의 대검. 칼날에 새겨진 올-델리트(All-Delete)의 룬 문자로 모든 것을 일도양단한다."},
            {"name": "가루루 캐논 (Garuru Cannon)", "desc": "메탈가루루몬의 형태를 한 오른팔에서 절대영도의 냉기 탄환을 연속 포격하는 거대 캐논포."},
            {"name": "소드 오브 루인 (Sword of Ruin)", "desc": "그레이 소드로 거대한 파괴의 충격파를 전방으로 날려 전장을 초토화시킨다."}
        ],
        "profile": "바이러스 근절을 바라는 사람들의 강한 의지에 의해, 선(善)을 바라는 마음이 기적을 일으켜 워그레이몬과 메탈가루루몬이 융합하여 탄생한 성기사형 디지몬. 네트워크의 최고위 수호신 집단인 '로얄 나이츠'의 일원이다. 어떠한 상황에서도 능력을 유감없이 발휘할 수 있는 멀티 타입 파이터로, 왼손의 그레이 소드와 오른손의 가루루 캐논으로 적을 격파한다."
    },
    {
        "id": "wargreymon",
        "name_ko": "워그레이몬",
        "name_en": "War Greymon",
        "name_ja": "ウォーグレイモン",
        "level": "궁극체",
        "attribute": "백신 (Vaccine)",
        "type": "용인형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/War_Greymon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/b/ba/Wargreymon_vpet_pen.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT1-025.jpg"
            }
        ],
        "skills": [
            {"name": "가이아 포스 (Gaia Force)", "desc": "대기 중에 존재하는 모든 에너지를 한 점에 모아 초고열의 거대한 에너지 탄환을 발사하는 필살기."},
            {"name": "드라몬 킬러 (Dramon Killer)", "desc": "양팔에 장착된 용족 특효의 클로로 강력한 일격을 날린다."},
            {"name": "브레이브 실드 (Brave Shield)", "desc": "등에 장비된 최강의 방패를 전면에 펼쳐 적의 어떠한 공격도 튕겨낸다."}
        ],
        "profile": "초금속 크롬디지조이드의 갑옷을 두른 최강의 용전사이며 그레이몬 계열 디지몬의 궁극체 형태. 그레이몬 계열의 거대한 모습과는 달리 인간형의 모습을 취하고 있지만, 속도와 파워는 비약적으로 상승하여 성숙기 디지몬의 공격으로는 상처조차 낼 수 없다. 양팔에 장비한 '드라몬 킬러'는 드라몬계 디지몬에게 절대한 위력을 발휘한다."
    },
    {
        "id": "guilmon",
        "name_ko": "길몬",
        "name_en": "Guilmon",
        "name_ja": "ギルモン",
        "level": "성장기",
        "attribute": "바이러스 (Virus)",
        "type": "파충류형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Guilmon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/3/37/Guilmon_vpet_dv.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/EX2-008.jpg"
            }
        ],
        "skills": [
            {"name": "파이어 볼 (Fire Ball)", "desc": "입에서 작지만 강력한 고열의 화염구를 발사한다."},
            {"name": "록 브레이커 (Rock Breaker)", "desc": "날카로운 거대 발톱으로 단단한 바위도 두 동강 내며 적을 찢어발긴다."}
        ],
        "profile": "아직 유년기의 흔적이 남아 있는 파충류형 디지몬이지만, 잠재력은 극히 높으며 '디지털 해저드(Digital Hazard)'의 위험성을 내포하고 있다. 호기심이 많고 천진난만한 성격이나 전투 본능에 불이 붙으면 바이러스종 특유의 사나운 맹수와도 같은 흉폭함을 드러낸다. 디지몬 테이머즈에서 주인공 오유민이 직접 스케치북에 그려 D-Ark를 통해 탄생시킨 파트너 디지몬이다."
    },
    {
        "id": "dukemon",
        "name_ko": "듀크몬",
        "name_en": "Dukemon",
        "name_ja": "デュークモン",
        "level": "궁극체",
        "attribute": "바이러스 (Virus)",
        "type": "성기사형 (로얄 나이츠)",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Dukemon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/4/4b/Dukemon_vpet_dv.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT2-020.jpg"
            },
            {
                "type": "alt",
                "label": "✨ 크림슨 모드",
                "url": "https://digi-api.com/images/digimon/w/Dukemon_Crimson_Mode.png"
            }
        ],
        "skills": [
            {"name": "파이널 엘리시온 (Final Elysion)", "desc": "왼팔의 성순 이지스에서 모든 것을 정화하는 성스러운 극광의 빔포를 발사한다."},
            {"name": "로얄 세이버 (Royal Saber)", "desc": "오른팔의 성창 그람에서 강력한 에너지 참격을 뿜어내며 적을 꿰뚫는다."},
            {"name": "인빈시블 실드 (Invincible Shield)", "desc": "성순 이지스로 적의 공격을 완벽히 차단하고 튕겨낸다."}
        ],
        "profile": "바이러스종이면서도 네트워크의 최고위 수호 집단인 '로얄 나이츠'에 속해 있는 성기사형 디지몬. 99.9% 고순도의 크롬디지조이드로 정제된 성스러운 갑옷을 걸치고 있으며, 오른손에는 성창 '그람', 왼손에는 성순 '이지스'를 들고 있다. 기사도를 중시하며 주군을 향한 절대적인 충성을 바친다. 만약 밸런스가 무너지면 세상을 멸망시키는 위험한 존재가 될 수도 있다."
    },
    {
        "id": "agnimon",
        "name_ko": "아그니몬",
        "name_en": "Agnimon",
        "name_ja": "アグニモン",
        "level": "하이브리드체 (성숙기급)",
        "attribute": "배리어블 (Variable)",
        "type": "마인형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Agnimon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/9/9f/Agnimon_vpet_dv.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT4-011.jpg"
            }
        ],
        "skills": [
            {"name": "버닝 살라맨더 (Burning Salamander)", "desc": "양 주먹에 홍련의 불꽃을 휘감아 불의 용과 같은 강력한 타격을 날린다."},
            {"name": "샐러맨더 브레이크 (Salamander Break)", "desc": "공중에서 전신에 불꽃을 두르고 회전하며 낙하하는 불꽃 킥."},
            {"name": "파이어 다트 (Fire Dart)", "desc": "손끝에서 소형 불꽃 탄환을 기관총처럼 연속 발사한다."}
        ],
        "profile": "전설의 십투사 중 하나인 '에이션트그레이몬'의 힘을 이어받은 불꽃의 휴먼 하이브리드체 디지몬. 신체에 불꽃을 휘감고 자유자재로 다루며 동양의 무술을 연상케 하는 날렵하고 화려한 체술로 상대를 제압한다. 2027년 25주년을 맞이하는 '디지몬 프론티어'의 주인공 우정훈(칸바라 타쿠야)이 스피릿 에볼루션한 대표 주역 디지몬이다."
    },
    {
        "id": "beelzebumon",
        "name_ko": "베르제브몬",
        "name_en": "Beelzebumon",
        "name_ja": "ベルゼブモン",
        "level": "궁극체",
        "attribute": "바이러스 (Virus)",
        "type": "마왕형 (7대 마왕)",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Beelzebumon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/5/52/Beelzebumon_vpet_dv.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT2-068.jpg"
            },
            {
                "type": "alt",
                "label": "✨ 블라스트 모드",
                "url": "https://digi-api.com/images/digimon/w/Beelzebumon_Blast_Mode.png"
            }
        ],
        "skills": [
            {"name": "더블 임팩트 (Double Impact)", "desc": "애총 '베히모스'와 함께 소지한 두 정의 샷건 '베렌헤나'를 난사하여 적을 벌집으로 만든다."},
            {"name": "다크니스 클로 (Darkness Claw)", "desc": "손톱에 암흑의 오라를 집중시켜 적의 심장을 꿰뚫는다."},
            {"name": "하트 브레이크 샷 (Heartbreak Shot)", "desc": "적의 급소를 노려 일격필살의 탄환을 발사한다."}
        ],
        "profile": "칠대마왕의 일원으로 '폭식'을 관장하는 마왕형 디지몬. 거대한 오토바이 '베히모스'를 몰고 다니며 두 정의 애총 '베렌헤나'를 난사한다. 고고한 긍지를 지니고 있어 다수가 한 명을 공격하는 비겁한 짓을 극도로 혐오하며 언제나 단독으로 행동한다. 디지몬 테이머즈에서 임프몬이 궁극 진화하여 절대적인 카리스마를 뽐낸 인기 디지몬이다."
    },
    {
        "id": "alphamon",
        "name_ko": "알파몬",
        "name_en": "Alphamon",
        "name_ja": "アルファモン",
        "level": "궁극체",
        "attribute": "백신 (Vaccine)",
        "type": "성기사형 (로얄 나이츠)",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Alphamon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/4/41/Alphamon_vpet_penx.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT6-111.jpg"
            },
            {
                "type": "alt",
                "label": "✨ 왕룡검",
                "url": "https://digi-api.com/images/digimon/w/Alphamon_Ouryuken.png"
            }
        ],
        "skills": [
            {"name": "디지털라이즈 오브 소울 (Digitalize of Soul)", "desc": "손바닥에 마법진을 전개하여 다른 차원에서 전설의 거대 몬스터를 소환해 적을 분쇄한다."},
            {"name": "성검 그레이달파 (Seiken Gradalpha)", "desc": "빛의 성검을 마법진에서 꺼내 적을 베어 가른다."},
            {"name": "알파인포스 (Alpha inForce)", "desc": "흘러간 전투의 시간을 순간적으로 되감아 무수한 공격을 상대에게 일순간에 쏟아붓는 궁극의 비기."}
        ],
        "profile": "13체의 성기사 '로얄 나이츠' 중에서도 '공백의 자리'에 위치한다고 전해지는 고고한 은자. 결코 모습을 드러내지 않아 '푸른 고고의 은사'라 불리며 로얄 나이츠에 대한 억제력 역할을 수행한다. 지나간 전투 시간을 순간적으로 되돌리는 궁극의 힘 '알파인포스'를 지니고 있어, 상대는 자신이 몇 번 공격당했는지조차 알지 못한 채 쓰러지게 된다."
    },
    {
        "id": "vmon",
        "name_ko": "브이몬",
        "name_en": "V-mon",
        "name_ja": "ブイモン",
        "level": "성장기",
        "attribute": "프리 (Free)",
        "type": "소룡형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/V-mon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/0/07/Vmon_vpet_d3.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT2-021.jpg"
            }
        ],
        "skills": [
            {"name": "브이몬 헤드 (V-mon Head)", "desc": "온몸의 탄력을 살려 단단한 이마로 맹렬하게 들이받는 박치기 공격."},
            {"name": "붕붕 펀치 (Boom Boom Punch)", "desc": "양팔을 풍차처럼 회전시키며 묵직한 연속 펀치를 날린다."}
        ],
        "profile": "고대 번영했던 고대종의 후예로 '아머 진화'를 할 수 있는 능력을 지닌 소룡형 디지몬. 정의감이 강하고 장난치기를 좋아하며 명랑하고 쾌활한 성격이다. 이마에 새겨진 V자 문양이 트레이드마크이다. 디지몬 어드벤처 02(파워 디지몬)의 주인공 최산해의 파트너 디지몬으로 활약했다."
    },
    {
        "id": "imperialdramon",
        "name_ko": "황제드라몬",
        "name_en": "Imperialdramon: Dragon Mode",
        "name_ja": "インペリアルドラモン：ドラゴンモード",
        "level": "궁극체",
        "attribute": "프리 (Free)",
        "type": "고대용형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Imperialdramon_Dragon_Mode.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/2/23/Imperialdramondragon_vpet_d3.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT3-031.jpg"
            },
            {
                "type": "alt",
                "label": "✨ 파이터 모드",
                "url": "https://digi-api.com/images/digimon/w/Imperialdramon_Fighter_Mode.png"
            }
        ],
        "skills": [
            {"name": "메가 데스 (Mega Death)", "desc": "등의 거대한 포문에서 초암흑 물질의 포탄을 발사하여 반경 수 킬로미터를 일순간에 소멸시킨다."},
            {"name": "스플렌더 블레이드 (Splendor Blade)", "desc": "전신의 발톱에 에너지를 집중시켜 적을 산산조각 낸다."}
        ],
        "profile": "고대에 존재했던 궁극의 고대용형 디지몬. 다른 디지몬과는 확연히 구분되는 압도적인 존재감과 힘을 지니고 있으며 '용들의 황제'라 불린다. 파이터 모드로 모드 체인지하면 모든 지성을 해방하여 궁극의 전사로 변모한다. 디지몬 어드벤처 02에서 파일드라몬이 진화한 최강의 파트너 디지몬이다."
    },
    {
        "id": "tailmon",
        "name_ko": "가트몬",
        "name_en": "Tailmon",
        "name_ja": "テイルモン",
        "level": "성숙기",
        "attribute": "백신 (Vaccine)",
        "type": "성수형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Tailmon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/3/3b/Tailmon_vpet_pen.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT3-035.jpg"
            }
        ],
        "skills": [
            {"name": "네코 펀치 (Neko Punch)", "desc": "거대한 신성한 발톱으로 고속의 연속 펀치를 퍼붓는다."},
            {"name": "캣츠 아이 (Cat's Eye)", "desc": "신비로운 눈빛으로 상대를 응시하여 최면에 빠뜨린다."}
        ],
        "profile": "호기심이 왕성하고 장난치기를 좋아하는 성수형 디지몬. 꼬리에 장착된 홀리링(Holy Ring)에 의해 성스러운 힘을 유지하고 있으며, 체구는 작지만 성숙기급의 막강한 전투 능력을 지니고 있다. 디지몬 어드벤처에서 신나리의 든든한 파트너 디지몬으로 등장하여 큰 사랑을 받았다."
    },
    {
        "id": "patamon",
        "name_ko": "파닥몬",
        "name_en": "Patamon",
        "name_ja": "パタモン",
        "level": "성장기",
        "attribute": "데이터 (Data)",
        "type": "포유류형",
        "images": [
            {
                "type": "official",
                "label": "🎨 공식 도감",
                "url": "https://digi-api.com/images/digimon/w/Patamon.png"
            },
            {
                "type": "dot",
                "label": "👾 클래식 도트",
                "url": "https://wikimon.net/images/9/9f/Patamon_vpet_pen.gif"
            },
            {
                "type": "tcg",
                "label": "🃏 TCG 카드",
                "url": "https://images.digimoncard.io/images/cards/BT1-048.jpg"
            }
        ],
        "skills": [
            {"name": "공기팡 (Air Shot)", "desc": "숨을 크게 들이마신 후 압축된 공기 탄환을 입에서 발사한다."},
            {"name": "날개 치기 (Hane Binta)", "desc": "큰 귀날개로 적을 찰싹 때려 기절시킨다."}
        ],
        "profile": "큰 귀를 날개처럼 펄럭이며 하늘을 날아다니는 포유류형 디지몬. 비행 속도는 시속 1km 정도로 걷는 것보다 느리지만, 본인은 날고 있는 것 자체를 매우 좋아한다. 솔직하고 순종적인 성격이며 고대 종족의 유전자를 이어받아 성스러운 엔젤몬으로 진화하는 힘을 품고 있다."
    }
]

def main():
    os.makedirs("docs/data", exist_ok=True)
    os.makedirs("public/data", exist_ok=True)
    
    for path in ["docs/data/digidex_ko.json", "public/data/digidex_ko.json"]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"total": len(DIGIDEX_DATA), "digimons": DIGIDEX_DATA}, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(DIGIDEX_DATA)} digimons to {path}")

if __name__ == "__main__":
    main()
