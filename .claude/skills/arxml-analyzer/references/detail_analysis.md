# 세부 분석 (도입부 다음 단계)

도입부 4블록으로 "이 파일이 뭔지" 잡은 뒤, 세부 분석은 "파일이 담은 내용을 깊이
판다". 파일 종류에 따라 **A / B / C 세 갈래 중 하나만** 실행한다. 세 갈래는 서로
대조하거나 다른 파일을 끌어오지 않는다 — 전송된 그 파일 하나만으로 완결한다.
(정의↔값 대조 같은 통합은 현재 범위 밖. 추후 과제.)

**시각화 형식**: 구조·계층·관계·흐름은 **SVG**(svg-creation 스킬), 단순 속성·수치
나열은 **표**. ASCII 트리/다이어그램은 쓰지 않는다(Confluence에서 깨짐). 각 항목에
(**SVG**)/(**표**)로 표시해 둔다.

## 종류 판정 → 라벨 → 갈래

| element_counts 신호 | 라벨(블록1·세부 공통) | 세부 갈래 |
|---|---|---|
| `SYSTEM` / `CATEGORY=ECU_EXTRACT` | **시스템 구조 정의** (System Description) | A |
| `ECUC-MODULE-DEF` (값 없이 정의만) | **파라미터 양식 정의** (ECUC Parameter Definition) | B |
| `ECUC-MODULE-CONFIGURATION-VALUES` | **파라미터 값** (ECUC Configuration Values) | C |

라벨은 한국어 기본 + 영문 괄호 병기. 도입부 블록 1 첫 행에 이 라벨을 찍는다.

---

## 갈래 A — 시스템 구조 정의 (EcuExtract)

ECU 한 대당 하나뿐인 파일. "이 파일이 기술하는 시스템이 실제로 어떻게 구성·연결돼
있는지"를 바깥(통신)→경계(단자)→안(SWC)→연결(매핑) 순으로 좁혀 들어간다.

**A-1. 통신 구조** — 무엇을 주고받나
- 통신 요소 계층표: 정보(I-SIGNAL) → 묶음(I-SIGNAL-GROUP) → 봉투(I-SIGNAL-I-PDU)
  → 전송(CAN-FRAME/LIN-FRAME), 그리고 관리(NM-PDU)·진단(DCM-I-PDU/N-PDU). 개수 인용.
- 정보→봉투→전송 **계층도는 SVG**. 메시지 그룹 Rx/Tx × 범위(LIN/PNC) 구조도 **SVG**.
- 채널 요약: CAN-CLUSTER / LIN-CLUSTER, CAN-TP-CONFIG·NM-CONFIG 유무.
- 신호 562개를 전부 나열하지 말 것. 이름 패턴으로 묶는다(예: LHSwitchRes_*,
  RHSwitchRes_*, BCAN_*).

**A-2. 제어기 토폴로지** — 어디 붙나 (**SVG**)
- ECU-INSTANCE의 단자(COMM-CONTROLLERS: CAN/LIN), 커넥터, 버스 연결을 SVG로.
  IN/OUT 방향 분포로 "버스에서의 위치·성격(주로 듣는지/알리는지)"을 해석.

**A-3. 소프트웨어 구성** — 누가 일하나 (**SVG**)
- SW-COMPONENT-PROTOTYPE을 종류별(APPLICATION/SERVICE/CDD/ECU-ABSTRACTION)·역할별로
  묶은 구성도. 전부 나열보다 묶음 + 대표 이름.

**A-4. 연결과 매핑(핵심)** — 어떻게 이어지나 (**SVG**)
- SYSTEM-MAPPING 3종: DataMappings(신호↔SWC 데이터), SwMappings(SWC↔ECU 배치),
  PncMappings(PNC 매핑). A-1·A-2·A-3을 잇는 배선도. 비중을 가장 크게.

근거: 스크립트의 `fibex_refs`, `comm_direction`, `pnc`, `ecu_instances`,
`compositions`, `outgoing_refs`.

---

## 갈래 B — 파라미터 양식 정의 (.epd)

핵심 관점: **이 파일은 C 구조체(struct) 정의와 같다.** 컨테이너=구조체,
파라미터=멤버(타입+제약), 서브컨테이너=중첩 구조체, REFERENCE=포인터 멤버.
값 파일(C)은 이 구조체를 채운 인스턴스다. B의 산출물은 "구조체 코드"여야 한다 —
개수 요약 트리로 끝내지 말 것.

**B-1. 구조체 정의 (C 코드)** — B의 핵심
- `scripts/ecuc_to_struct.py <정의.epd>`로 각 컨테이너를 **실제 C 구조체 코드**로
  출력한다. 멤버 = 파라미터(C 타입), 주석 = 제약(MIN..MAX / default / enum 선택지),
  중첩 컨테이너 = 중첩 struct, REFERENCE = 포인터 멤버(`void* ... // ref -> 대상`).
- 맨 위 한 줄로 모듈 정체만 흡수(예: "Can 모듈, AUTOSAR Can을 벤더가 refine,
  POST-BUILD 지원"). 별도 "모듈 개요" 항목으로 부풀리지 않는다.
- **ARXML에 정의된 컨테이너를 전부 출력한다. 생략·발췌 금지.** 26종이면 26종 typedef를
  모두, 각 구조체의 멤버도 빠짐없이 낸다. "핵심만 보이고 나머지는 이름만"은 하지 않는다 —
  스크립트(`ecuc_to_struct.py`)가 전체를 출력하므로 그 출력을 그대로 싣는다. 양이 많아도
  자른 코드는 정의의 일부일 뿐이라 분석 가치가 떨어진다. 코드 블록으로 제시(Confluence 코드 매크로).

**B-2. AR-PATH 폴더트리 (SVG)** — 3절의 주력
- ARXML의 AR-PATH 계층(MODULE-DEF → CONTAINER-DEF → SUB-CONTAINER)을 **파일 탐색기식
  폴더트리**로 그린다. 규격·글리프·색·간격은 `report_intro.md` 블록 3과
  `references/arpath_tree_example.svg`를 그대로 따른다(여기서 새로 만들지 않는다).
- **depth 기본 3, 필요시 4까지.** 그 아래로 더 깊은 노드가 있으면 펼치지 말고 개수 칩으로만
  표기(예: `AdcHwUnit  member 24 · ref 3 · sub 7`). 재료는 `ecuc_def_tree`.
- 이 트리는 "경로 계층이 어떻게 생겼나"를 보여주는 것이지 struct 연결성 그림이 아니다.
  박스+화살표로 struct 간 포함·참조를 그리는 연결성 다이어그램은 **이 단계에서 만들지 않는다**
  (필요해지면 보조로 추가). B-1 코드가 멤버·참조를 이미 담고 있으므로 중복도 적다.

(기존의 "모듈 개요"·"멤버 타입 분포(INTEGER N개…)" 항목은 공부에 도움이 적어 제거.
타입·제약은 B-1 구조체 코드 안에 멤버별로 녹아 있다.)

근거: 스크립트의 `ecuc_to_struct.py`(B-1 구조체 코드), `ecuc_def_tree`(B-2 AR-PATH 폴더트리).

---

## 입력 조합별 동작 (정의·값 함께 올 때)

값 파일(C)과 정의 파일(B, .epd)을 함께 받으면 짝 여부에 따라 동작이 갈린다. 짝
판정은 `scripts/ecuc_pair_check.py`로 한다 — 값 파일의 모든 `DEFINITION-REF`가
정의 파일 안에서 해결되면(값 ⊆ 정의) 짝, 하나라도 못 찾으면 짝 아님.

| 입력 | 동작 |
|---|---|
| 값(C)만 | 값 분석 1개(C-1~C-4) + "범위·기본값·선택지·의미는 정의 파일 있어야 안다" 한계 명시. C-4는 `ecuc_to_init.py`를 `--def` 없이 돌린 축약판 |
| 정의(B)만 | 정의 분석 1개 (B 갈래) |
| 정의+값, **짝 맞음** | 2개 — ① 정의 분석(B, 빈 구조체) ② "정의 포함 값" 분석(C). 값 페이지에는 C-4 "설정값의 C 표현"을 `ecuc_to_init.py --def <.epd>` 완전판(기본값 차이 주석 포함)으로 넣어 ①의 빈 구조체와 대칭을 이룬다 |
| 정의+값, **짝 아님** | **아무것도 생성하지 않음.** "둘은 짝이 아님" + 값 파일이 실제 요구하는 정의의 참조 위치(`ecuc_pair_check`의 value_module_paths)를 안내 |

짝일 때 두 페이지를 따로 두는 이유: 정의(.epd)는 그 자체로 모듈 전체 양식이라
값과 무관하게 볼 가치가 있고(값엔 안 쓰인 파라미터도 정의엔 있음), 값 페이지는
"이 ECU가 실제로 어떻게 설정됐나"라 목적이 다르다.

## 갈래 C — 파라미터 값 (Ecud_Can)

값 파일 단독으로 완결. 정의가 함께 오면 위 표대로 처리.

**C-1. 모듈 설정 개요** — 어떤 모듈·어떤 variant(IMPLEMENTATION-CONFIG-VARIANT).
**C-2. AR-PATH 폴더트리** (**SVG**) — 3절의 주력. `ecuc_tree`로 MODULE → CONTAINER → SUB의
  AR-PATH 계층을 **파일 탐색기식 폴더트리**로 그린다(규격은 `report_intro.md` 블록 3 +
  `arpath_tree_example.svg`). **depth 기본 3, 필요시 4까지**, 더 깊으면 개수 칩(param/ref/sub)으로만
  표기. 실제 설정된 컨테이너와 그 수가 트리에 드러나면 충분하다 — struct 연결성(박스+화살표)
  다이어그램은 이 단계에서 만들지 않는다(필요 시 보조).
**C-3. 파라미터 값 상세** (**표**) — 컨테이너별 param/ref 수, 대표 값. 전부 나열보다 묶음.

**C-4. 설정값의 C 표현 (designated initializer)** — B-1(빈 구조체)과 짝을 이루는 C
갈래의 핵심 산출물. `scripts/ecuc_to_init.py`로 각 컨테이너 값을
`const <Def>_t <ShortName> = { .member = value, ... };` 형태로 출력한다(코드 블록).
- **값은 ARXML 실제값**, C 초기화 문법(변수명·`.멤버 =`·포인터)은 B 구조체에 값을
  대입해 보여주는 **표현 틀**일 뿐이다. 벤더 생성물(`*_PBcfg.c`)과는 다르다 —
  생성 코드는 멤버명이 레지스터 지향 내부 필드로 바뀌고 값도 비트 인코딩 상수가
  된다. 이 점을 코드 위 한 줄로 반드시 명시한다(실제 생성 코드로 오해 방지).
- **짝(정의+값)일 때**: `--def <.epd>`를 주면 boolean은 TRUE/FALSE, 정수는 `u`
  접미사로 렌더되고, **기본값과 다른 값엔 `/* 정의 기본 X */` 주석**이 붙는다(완전판).
- **값 단독일 때**: `--def` 없이 raw 값만, 기본값 주석 없음(축약판). 타입을 모르므로
  추정하지 않는다.
- 중첩/반복 컨테이너는 **각각 독립 `const`로 평평하게(flat)** 출력하고, 부모는 자식을
  타입·변수명으로만 참조한다(`.AdcChannel = { &AdcChannel_0, &AdcChannel_1 }`). 부모 안에
  자식 본문을 풀어넣지 않는다. 출력 순서는 **부모→자식**(읽기용 분석 뷰이며 컴파일용이
  아니므로 forward 선언은 두지 않는다). 이는 B-1 정의 구조체(`ecuc_to_struct.py`)의
  flat·부모순 배치와 1:1로 대칭이다.
- **ARXML에 있는 인스턴스를 전부 출력한다. 생략·발췌·"대표 1개" 금지.** 채널 21개·그룹
  23개면 101개 const를 모두 낸다. 스크립트(`ecuc_to_init.py`)가 전체를 출력하므로 그
  출력을 그대로 싣는다. B-1과 동일하게 "일부만"은 분석 가치가 떨어진다.

값 파일 단독 분석의 한계(보고서에 한 줄 명시): 값 파일로는 구조 뼈대(DEFINITION-REF
경로)·이름·실제 값·숫자/텍스트 구분까지만 안다. **각 값의 허용범위(MIN/MAX)·기본값·
enum 선택지·의미·multiplicity는 이 파일에 없다 — 정의 파일(.epd)이 있어야 안다.**
없는 정의를 추정해 "아마 0~255일 것" 식으로 채우지 않는다.

근거: 스크립트의 `ecuc_tree`, `outgoing_refs`(C-1~C-3), `ecuc_to_init.py`(C-4).
