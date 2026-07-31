---
name: arxml-analyzer
description: AUTOSAR ARXML 파일을 분석해 구조를 개념 중심으로 정리하고, 지정한 Confluence 페이지에 보고서로 출력하는 스킬. 사용자가 "ARXML 분석", "arxml 파일 분석", ".arxml 정리", "ECU Extract 분석", "이 arxml 뭔지 봐줘", "arxml 구조 설명", "EcuExtract 분석해줘", "시스템 명세 정리" 등을 언급하거나 .arxml 파일을 올리며 내용을 알고 싶어 하면 반드시 이 스킬을 사용하라. ECU Extract, System Description, ECU Configuration, SWC Type, 통신/진단 Extract 등 모든 ARXML 종류에 적용된다. 비트 단위 구현이나 SWS 스펙 인용이 아니라, 시스템 안에서의 역할과 관계를 개념 중심으로 설명하는 것이 목표다. 구조 분석 전용이며 검증·문제 진단은 하지 않는다.
---

# ARXML Analyzer

ARXML 파일의 구조를 기계적으로 추출하고, 그 결과를 **개념 중심(역할·관계 위주)**으로
해석해 사용자가 지정한 Confluence 페이지에 보고서로 작성한다.

설계 원칙: **추출은 스크립트, 해석은 이 지침.** 개수·트리·참조 집계 같은 반복·기계적
작업은 `scripts/arxml_inspect.py`가 정확히 처리하고, "그래서 이게 무슨 의미인가"의
개념 해석만 여기서 한다. 숫자를 직접 grep하거나 손으로 세지 말 것 — 스크립트가 센다.

## 가장 중요한 원칙: 전송된 ARXML 파일이 유일한 근거

이 스킬의 목적은 **사용자가 전송한 그 ARXML 파일 자체를 공부**하는 것이다. 따라서
보고서의 모든 내용은 **그 파일을 파싱한 결과만**을 근거로 한다.

- 일반적인 AUTOSAR 표준 데이터플로, "보통 이런 파일은 이런 입력을 받는다" 같은
  일반론·교과서적 추정은 **넣지 않는다.** 그 파일에 실제로 없으면 쓰지 않는다.
- 특히 블록 2(생성 흐름/의존)의 INPUT은 추정하지 말고, 파일 안의 실제 참조
  (`DEFINITION-REF`, `MODULE-DESCRIPTION-REF`, `VALUE-REF`, `FIBEX-ELEMENT-REF`,
  `*-TREF` 등)를 파싱해 **이 파일이 실제로 가리키는 대상만** 그린다.
  예: MCAL Can 컨피그가 ECU Extract를 가리키지 않으면 흐름도에 ECU Extract를
  넣지 않는다. 대신 실제 가리키는 벤더 드라이버 정의·Mcu·EcuM 등을 넣는다.
- 파일에서 근거를 못 찾은 항목은 "그릴 수 없음/해당 없음"으로 두지, 일반론으로
  채우지 않는다.

## 적용 범위

- 한다: 구조 추출 + 개념 해석 + Confluence 출력
- 안 한다: 검증·문제 진단(빈 폴더/dangling 참조/오타를 "문제"로 규정하거나 수정
  권고하지 않는다). 빈 패키지 같은 건 구조 사실로만 담담히 적는다.
- 설명 깊이: **개념 중심**. 비트 위치, ARXML 전문 발췌, SWS 항목 인용은 기본적으로
  넣지 않는다. "이것이 무엇이고 왜 있는가, 다른 것과 어떻게 연결되는가"에 집중.
- 도구 표기: 생성/설정 도구는 **Mobilgene C Studio를 기본**으로 적되, 그 작업을
  Mobilgene C Studio가 지원하지 못하면 실제 지원 도구(EB tresos, Vector DaVinci 등)로 적는다.

## 워크플로

이 스킬은 작업 중 두 스킬을 **함께 사용한다**:
- `svg-creation` — 보고서의 모든 SVG(생성 흐름·트리·계층·매핑 등)를 그릴 때.
- `confluence-writing` — 보고서를 Confluence 페이지로 작성·발행할 때.

단, `confluence-writing`은 "대표 페이지 + 하위 N개" 2레벨 트리를 추천하지만,
**ARXML 분석 보고서는 한 ARXML당 단일 페이지로 작성한다**(본/하위 페이지로 쪼개지
않는다). 예외는 "정의+값 짝"을 함께 받은 경우뿐이며, 이때만 정의 1페이지 +
정의포함값 1페이지의 2개를 만든다(서로 독립 페이지, 본/하위 관계 아님).

### 1. 구조 추출 (스크립트 실행)

업로드된 파일은 보통 `/mnt/user-data/uploads/`에 있다. 먼저 실행:

```bash
python3 scripts/arxml_inspect.py <파일경로>
```

출력에는 파일 정체, 패키지 트리, 요소 개수, FIBEX 참조 대상, 통신 방향(IN/OUT),
PNC, ECU-INSTANCE 토폴로지, SWC 조립 정보가 들어 있다. 더 상세한 원자료가 필요하면
`--json`을 붙인다. 큰 파일도 한 번에 처리되므로 이 출력만으로 보고서를 쓴다.

### 2. 파일 종류 판별

`references/file_types.md`를 읽고, 스크립트 출력의 `root`/`CATEGORY`/`element_counts`/
`package_tree`로 종류를 정한다(ECU Extract / System Description / ECU Configuration /
SWC Type / Communication / Diagnostic 등). 종류에 따라 강조할 부분이 달라진다.

여기서 **정의(define) vs 참조(reference)**를 반드시 짚는다. `fibex_refs`만 많고
정의가 거의 없으면 "이 파일은 단독으로 불완전하며 다른 파일과 묶여야 한다"를
보고서에 한 줄로 명시한다.

### 3. 개념 해석

`references/element_glossary.md`를 참조해, 추출된 요소들을 **역할과 관계**로 해석한다.
- 통신 요소는 "ISignal(정보) → I-PDU(묶음) → Frame(전송) → I-PDU-GROUP(켜고 끔)"의
  계층으로 꿴다.
- 통신 방향 IN/OUT 비율로 이 제어기의 성격(주로 듣는지/알리는지)을 한 줄 해석.
- SWC `by_kind`를 응용/서비스/CDD/추상화의 개념적 역할로 묶어 설명.
- `provenance`(DBC/LDF/ETH 경로)에서 어떤 통신 DB가 통합됐는지, 경로의 MCU·프로젝트명
  으로 타깃을 짐작.

수치는 스크립트 출력값을 그대로 쓴다. 추정·창작 금지.

### 3-1. 보고서 도입부 작성 (4블록)

세부 해석에 앞서 보고서 첫머리는 `references/report_intro.md`의 4블록 규칙을 따른다:
서문(모듈 역할) → 1.정의용/값용(1~2줄) → 2.생성 - 변환 - 출력 흐름(SVG) → 3.AR-PATH 폴더트리(SVG) → 4.특유 태그 표.
스크립트 출력의 `path_tree`, `specific_tags`가 블록 3·4의 재료다. AR-PATH 트리는 항상
`svg-creation`의 「폴더트리 패턴」으로 동일하게 그린다(기준: `references/arpath_tree_example.svg`).
"개념 정리 파트다" 같은 메타 안내 문구는 넣지 않는다.

### 3-2. 세부 분석 (A/B/C 갈래)

도입부 다음, `references/detail_analysis.md`의 규칙을 따른다. 파일 종류에 따라
세 갈래 중 하나만 실행하며, 다른 파일을 끌어오거나 대조하지 않는다:
- A 시스템 구조 정의(EcuExtract): 통신구조 / 토폴로지 / SW구성 / 매핑(핵심)
- B 파라미터 양식 정의(.epd): **구조체 코드 관점** — B-1 구조체 정의(C 코드,
  `ecuc_to_struct.py`로 생성, ARXML 전체) / B-2 AR-PATH 폴더트리(SVG, depth 3~4).
  모듈개요·타입분포는 안 만듦. struct 연결성 다이어그램은 이 단계에선 안 만듦.
- C 파라미터 값(Ecud_Can): 모듈개요 / AR-PATH 폴더트리(SVG, depth 3~4) / 파라미터 값 상세 /
  설정값의 C 표현(designated initializer, B-1 빈 구조체와 짝)

스크립트 재료: A는 `fibex_refs`/`comm_direction`/`compositions` 등, B는
`ecuc_def_*`, C는 `ecuc_tree`(C-1~C-3) + `ecuc_to_init.py`(C-4 설정값 C 표현).
모두 파일 파싱값만 사용(추정 금지).

**값+정의를 함께 받은 경우**: `scripts/ecuc_pair_check.py <값> <정의>`로 짝을
먼저 검사한다. 짝이면 정의 분석 페이지 + "정의 포함 값" 페이지 2개를 만들고,
짝이 아니면 페이지를 만들지 말고 "짝 아님 + 필요한 정의 위치"를 안내한다.
자세한 입력 조합별 동작은 `detail_analysis.md`의 표를 따른다.

### 4. 출력 대상 Confluence 페이지 확인

이 스킬은 **사용자가 지정한 Confluence 페이지**에 쓴다. 진행 전에 다음을 사용자에게
확인한다(아직 안 알려줬다면 질문):
- 새 페이지인가, 기존 페이지 수정인가
- (새 페이지면) 상위 페이지와 제목 / (수정이면) 대상 페이지 URL 또는 ID

권한이 필요한 동작(페이지 생성·수정)은 사용자 확인 후 진행한다.

### 4-1. 페이지 제목 규칙 (★ 파일명 원문 필수)

분석 페이지 제목은 **"개념 라벨 + (업로드된 파일명 원문)"** 형식으로 짓는다. 괄호 안에는
설명적 별칭(예: "S32K312 .epd", "ECU Configuration")이 아니라 **사용자가 올린 파일명을
확장자까지 글자 그대로** 넣는다. 추측·축약·번역·대소문자 변경 금지.

```
형식:  <개념 라벨> (<업로드 파일명 원문>)

⭕  Adc 파라미터 양식 정의 (Adc_s32k312_hdqfp172.epd)
⭕  Adc 파라미터 값 (Ecud_Adc.arxml)
❌  Adc 파라미터 양식 정의 (S32K312 .epd)        ← 별칭 금지
❌  Adc 파라미터 값 (ECU Configuration)          ← 설명어 금지
❌  Adc 파라미터 값 (ecud_adc.arxml)             ← 대소문자 변경 금지
```

- 파일명은 `/mnt/user-data/uploads/`의 실제 basename을 그대로 복사한다(손으로 다시
  타이핑하지 말 것 — 오타·대소문자 어긋남 방지).
- **정의+값 짝**으로 2페이지를 만들 때는 각 페이지 괄호에 **그 페이지가 다루는 파일의
  이름만** 넣는다(정의 페이지=.epd 파일명, 값 페이지=값 파일명). 서로의 파일명을 섞지 않는다.
- 개념 라벨은 file_types.md의 한국어 라벨("파라미터 양식 정의", "파라미터 값",
  "시스템 구조 정의" 등)을 따른다.

### 5. Confluence 작성 (confluence-writing 스킬에 위임)

페이지 작성·수정의 톤·구조·서식 규약과 MCP 호출 방식은 **`confluence-writing`
스킬을 함께 활성화해 그 규칙을 따른다.** 이 스킬은 출력 메커니즘을 재발명하지 않는다.
- **단일 페이지로 작성한다.** confluence-writing의 "대표+하위 N개" 트리 추천을
  여기서는 따르지 않는다. 한 ARXML = 한 페이지. (정의+값 짝일 때만 독립 2페이지)
- 신규 작성은 `contentFormat=markdown`
- 첨부(SVG 등) 있는 기존 페이지 수정은 fetch 후 `contentFormat=html`로 텍스트만 교체
- SVG는 `svg-creation` 스킬로 만들어 첨부 흐름을 따른다.

## 보고서 구조 (개념 중심)

다음 순서로 구성한다. 각 항목은 산문 위주로, 과한 글머리표·굵게는 피한다.

1. **이 파일은 무엇인가** — 종류 + 한 줄 정체 + (참조형이면) 단독 불완전성 한 줄.
2. **출처** — 어떤 원본(DBC/LDF/ETH)에서 왔는지, 타깃 MCU 짐작.
3. **구조 한눈에** — 패키지 트리(빈 패키지 포함, 담담히). 트리는 항상 폴더트리 스타일(블록 3 규격).
4. **무엇이 들어 있나** — 요소 개수와 FIBEX 참조를 개념 단위로 묶어 설명
   (정보/묶음/전송 단위의 계층으로).
5. **제어기 통신 성격** — ECU-INSTANCE의 단자, IN/OUT 비율 해석, PNC.
6. **소프트웨어 구조** — 조립체와 SWC를 역할별(응용/서비스/CDD/추상화)로 묶어 설명.
   필요하면 계층 구조도(SVG) 첨부.

종류가 ECU Extract가 아니면(예: ECU Configuration) 위 골격을 종류에 맞게 변형한다.
핵심은 항상 "역할과 관계 중심"이라는 점.

## 참조 파일

- `references/report_intro.md` — 보고서 도입부 4블록 작성 규칙(목적/생성흐름/트리/태그)
- `references/arpath_tree_example.svg` — AR-PATH 폴더트리 기준 예시(이 모양으로 항상 동일하게)
- `references/detail_analysis.md` — 세부 분석 A/B/C 갈래 규칙(구조정의/양식정의/값)
- `references/file_types.md` — ARXML 종류 판별표, 정의 vs 참조 구분
- `references/element_glossary.md` — 요소별 개념(역할·관계) 사전
- `scripts/arxml_inspect.py` — 구조 추출 스크립트
- `scripts/ecuc_pair_check.py` — 값↔정의 짝 판정(값 ⊆ 정의) 스크립트
- `scripts/ecuc_to_struct.py` — .epd 컨테이너 정의를 C 구조체 코드로 생성(B-1).
  중첩을 풀지 않고 각 컨테이너를 독립 typedef로, 부모→자식 순서로 출력(분석용 flat).
  **ARXML에 정의된 컨테이너 전체를 출력 — 생략·발췌 금지**
- `scripts/ecuc_to_init.py` — 값 파일을 designated initializer C 코드로 생성(C-4).
  `--def <.epd>`를 주면 타입 변환 + 기본값 차이 주석(완전판), 없으면 raw 값(축약판).
  중첩/반복 컨테이너는 각각 독립 const로 flat 출력, 부모는 포인터로 참조, 부모→자식 순서.
  **ARXML에 있는 인스턴스 전체를 출력 — "대표 1개"·생략 금지**
