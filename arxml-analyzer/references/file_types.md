# ARXML 파일 종류 판별

ARXML은 한 종류가 아니다. 분석 전에 먼저 "이 파일이 무슨 종류인가"를 정해야
무엇을 봐야 할지 결정된다. 아래 표로 판별한다. 판별 근거는 `arxml_inspect.py`
출력의 `root`, `system.CATEGORY`, `element_counts`, `package_tree`에서 얻는다.

| 종류 | 판별 신호 | 한 줄 정체 | 라벨 |
|---|---|---|---|
| **ECU Extract** | `SYSTEM` 있고 `CATEGORY=ECU_EXTRACT`, `ECU-INSTANCE` 1개 | 제어기 한 대 분량으로 잘라낸 시스템 명세 (RTE/BSW 생성 입력) | 시스템 구조 정의 |
| **System Description** | `SYSTEM` 있고 `CATEGORY=SYSTEM`, `ECU-INSTANCE` 여러 개 | 차량/네트워크 전체 명세 | 시스템 구조 정의 |
| **SWC Type 정의** | `*-SW-COMPONENT-TYPE`가 다수, `SYSTEM` 없음 | 소프트웨어 부품 설계도 | 시스템 구조 정의 |
| **ECUC Parameter Definition (.epd)** | `ECUC-MODULE-DEF` 있고 값(`*-CONFIGURATION-VALUES`) 없음 | 모듈 파라미터의 양식(스키마). 구조체 정의 + 멤버 제약 | 파라미터 양식 정의 |
| **ECU Configuration Values** | `ECUC-MODULE-CONFIGURATION-VALUES` | BSW/MCAL 모듈 파라미터의 실제 설정값 | 파라미터 값 |
| **Communication / Cluster** | `CAN-CLUSTER`/`LIN-CLUSTER` 정의 + `I-SIGNAL`/`CAN-FRAME` 실체 | 통신 정의 (DBC/LDF 변환 원본) | 시스템 구조 정의 |
| **Diagnostic Extract** | `DIAGNOSTIC-CONTRIBUTION-SET` 다수 | UDS 진단 정의 | 시스템 구조 정의 |
| **BSW Module Description** | `BSW-MODULE-DESCRIPTION` 다수 | BSW 모듈 인터페이스 명세 | 시스템 구조 정의 |

라벨은 도입부 블록 1과 세부 분석에서 공통으로 쓴다. 한국어 기본 + 영문 괄호 병기.
핵심 3분류: **시스템 구조 정의 / 파라미터 양식 정의(.epd) / 파라미터 값**.
"파라미터 양식 정의"와 "파라미터 값"은 짝(.epd가 빈 양식, 값 파일이 채운 인스턴스)이나,
이 스킬은 각 파일을 독립적으로 분석한다(대조하지 않음).

## 정의(define) vs 참조(reference) 구분이 핵심

같은 요소라도 *정의된* 파일과 *참조만 하는* 파일이 다르다.

- `element_counts`에 `I-SIGNAL`이 잡히면 → 그 신호가 이 파일에 **정의**됨
- `fibex_refs`에 `I-SIGNAL`이 잡히면 → 이 파일은 신호를 **이름으로 가리키기만** 함
  (실체는 다른 파일에 있음)

ECU Extract는 보통 `fibex_refs`만 잔뜩 있고 정의는 거의 없다. 즉 **단독으로는
불완전하며**, SWC Type 파일·Communication 파일과 함께 묶여야 완성된다. 보고서에
이 점을 반드시 한 줄로 명시한다.

## 빈 패키지

`empty_packages`에 이름만 있고 비어 있는 패키지가 잡히는 일이 흔하다. 이는 export
툴이 만들어 둔 자리(placeholder)인 경우가 대부분이다. 구조 사실로만 담담히 적고,
"문제"로 규정하거나 수정 권고를 하지 않는다(이 스킬은 구조 분석 전용).
