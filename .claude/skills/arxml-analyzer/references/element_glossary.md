# ARXML 요소 개념 사전 (개념 중심 / 추상화)

목적: 보고서를 "개념 중심"으로 쓰기 위한 참조. 각 요소를 **비트 단위 구현이나
SWS 스펙 인용이 아니라, 시스템 안에서의 역할과 다른 요소와의 관계**로 설명한다.
독자가 "이게 무엇이고 왜 있는가"를 잡게 하는 것이 목표.

## 통신 계층 (데이터가 포장되는 단위)

추상화의 핵심은 "정보 한 조각 → 묶음 → 전송 단위"의 계층이다.

- **ISignal** — 의미 있는 정보 한 조각(최소 단위). 더 쪼개면 의미를 잃는다.
  예: "스위치 눌림 여부", "온도값". *역할*: 응용이 실제로 읽고 쓰는 값.
- **I-PDU (I-SIGNAL-I-PDU)** — 여러 ISignal을 한데 모은 묶음. *역할*: 전송 효율을
  위해 정보들을 함께 포장한 단위. ISignal 여러 개가 한 I-PDU의 자리들을 나눠 갖는다.
- **Frame (CAN-FRAME 등)** — I-PDU를 실어 버스 위로 실제 전송되는 단위. *역할*:
  하드웨어가 다루는 바깥 봉투. Frame 안에 식별자(헤더) + 데이터부가 들어가고,
  데이터부에 I-PDU가 담긴다.
- **I-PDU-GROUP** — I-PDU들을 다시 묶은 그룹. *역할*: 통신을 켜고 끄는 단위.
  ECU가 깨어나거나 잠들 때 그룹 단위로 활성/비활성한다.
- **System Signal** — ISignal의 "시스템 관점" 짝. *역할*: 네트워크 전체에서 통용되는
  논리적 신호 이름. ISignal이 이 System Signal에 매핑된다.

개념 요약: **ISignal(정보) → I-PDU(묶음) → Frame(전송 단위)**, 그리고 그 묶음들을
**I-PDU-GROUP**으로 켜고 끈다.

## 네트워크 관리

- **PNC (Partial Network Cluster)** — "필요한 제어기 무리만 깨우는" 부분 네트워킹의
  한 묶음. PNC-IDENTIFIER는 그 무리의 번호표. *역할*: 안 쓰는 ECU를 재워 전력 절약.
- **NM-PDU** — 네트워크 관리용 메시지. *역할*: 누가 깨어 있고 누가 잘지를 조율.

## 제어기 / 시스템 골격

- **SYSTEM** — 명세 전체의 루트. CATEGORY가 종류를 결정(ECU_EXTRACT 등).
- **ECU-INSTANCE** — 물리적 제어기 한 대. *역할*: 이름 + 통신 컨트롤러(단자) 보유.
- **COMM-CONTROLLER** (CAN/LIN 등) — 통신 단자 그 자체("콘센트").
- **Communication Connector** — 그 단자에 실제로 연결된 배선("플러그+선").
  컨트롤러는 단자, 커넥터는 연결. 둘은 다른 층이다.
- **ECU-COMM-PORT-INSTANCE / I-SIGNAL-PORT** — 그 커넥터로 오가는 신호의 입출구.
  COMMUNICATION-DIRECTION(IN/OUT)으로 수신/송신이 갈린다. IN이 많으면 "주로 듣는"
  제어기, OUT이 많으면 "주로 알리는" 제어기.

## 소프트웨어 구조

- **COMPOSITION-SW-COMPONENT-TYPE** — 부품들을 담는 "조립 도면". 어떤 SWC들이
  들어가고 서로 어떻게 연결되는지를 담는다.
- **SW-COMPONENT-PROTOTYPE** — 그 도면 안에 배치된 부품 한 개(직원 한 명). TYPE-TREF가
  "이 부품의 설계도가 어디 있는지"를 가리킨다(실체는 보통 다른 파일).
- SWC 종류(by_kind)의 개념적 역할:
  - **APPLICATION-SW-COMPONENT-TYPE** — 실제 기능(제어 로직). 현업 부서.
  - **SERVICE-SW-COMPONENT-TYPE** — BSW 서비스의 SWC 표현(통신/진단/메모리/감시 등).
    인프라/총무.
  - **COMPLEX-DEVICE-DRIVER (CDD)** — 표준 BSW로 못 다루는 하드웨어 직접 제어
    (예: 모터 드라이버). 현장 특수팀.
  - **ECU-ABSTRACTION-SW-COMPONENT-TYPE** — 하드웨어 I/O를 응용에서 추상화(IoHwAb).
- **Connector**:
  - **ASSEMBLY-SW-CONNECTOR** — 부품과 부품을 잇는 내부 배선(동등한 부품끼리).
  - **DELEGATION-SW-CONNECTOR** — 조립체 경계의 포트를 안쪽 부품에 위임. 0개면
    경계로 노출되는 포트가 없는 "완결형" 조립체.

## 매핑

- **SYSTEM-MAPPING** — 여러 짝짓기를 담는 칸. 흔히 (1) 신호↔SWC 포트 데이터 매핑,
  (2) SWC↔ECU 배치, (3) PNC 매핑이 들어간다.

## 값용 (ECU Configuration / MCAL) 요소

값용 파일은 구조 정의가 아니라 파라미터의 실제 값을 담는다.

- **ECUC-MODULE-CONFIGURATION-VALUES** — 한 BSW 모듈(Can, Port, Com 등)의 설정값
  전체. *역할*: 이 파일의 최상위 기둥. `IMPLEMENTATION-CONFIG-VARIANT`로
  Pre-compile/Link-time/Post-build 중 무엇인지 가린다.
- **ECUC-CONTAINER-VALUE** — 파라미터들을 담는 설정 컨테이너. *역할*: 모듈 안의
  논리적 묶음(예: CanConfigSet, CanController). 중첩(SUB-CONTAINERS)된다.
- **ECUC-*-PARAM-VALUE** (NUMERICAL/TEXTUAL) — 개별 파라미터의 실제 값. *역할*:
  보드레이트·핀번호·플래그 같은 구체 설정값.
- **DEFINITION-REF** — 이 값/컨테이너가 따르는 파라미터 *정의*로의 참조. *역할*:
  "이 값이 무엇에 대한 값인지"를 벤더 드라이버 정의에 연결. 값용의 핵심 참조.
- **ECUC-REFERENCE-VALUE / VALUE-REF** — 다른 컨테이너·모듈을 가리키는 참조 값.
  *역할*: 모듈 간 연결(예: Can이 Mcu 클럭이나 EcuM 웨이크업 소스를 가리킴).
- **MODULE-DESCRIPTION-REF** — 이 설정값이 묶이는 BSW 구현(BSWMD)으로의 참조.
- MCAL 맥락: CanController(컨트롤러 설정), CanHardwareObject(송수신 메일박스)처럼
  하드웨어에 직접 대응하는 컨테이너가 많다. 정의용의 추상적 단자가 여기선 실제
  HW 설정으로 구체화된다.

## 출처(provenance)

- **ANNOTATION-ORIGIN** — 이 명세가 어느 원본에서 변환됐는지의 흔적. `DBC_...`는
  CAN DB, `LDF_...`는 LIN DB, `ETH_...`는 Ethernet DB. 여러 개면 여러 통신 DB가
  통합된 것이고, 경로의 MCU명/프로젝트명으로 타깃과 출처를 짐작할 수 있다.
