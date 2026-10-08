# CQL 쿼리 설계 가이드 (eCoDY-ECM, Confluence DC 9.2 실측 기준)

## 1. 문법 요점

| 형태 | 예 | 메모 |
| --- | --- | --- |
| 제목 포함 | `title ~ "Wdg"` | 단어 단위 매칭 |
| 끝 와일드카드 | `title ~ "CYT*"` | CYTxxx·CYTxx 모두 잡음 (실측 OK). 앞 와일드카드는 쓰지 않는다 |
| 본문 구문 | `text ~ "Watchdog Reset"` | 제목+본문 |
| 광역 | `siteSearch ~ "CYT Wdg Reset"` | 사이트 검색 랭킹, 공간 전체 |
| 공간 한정 | `space=mclassicfaq` | 키: mclassicfaq · FODM · msec · etoolchain |
| 형식 | `type=page` | 첨부 찾을 때만 `type=attachment` |
| 조합 | `and` / `or` / 괄호 | `(title ~ "CanSM" or title ~ "BusOff")` |
| 최근 | `lastmodified >= "2026/09/01"` | 서버가 UTC로 해석 |
| 정렬 | `order by lastmodified desc` | 공지·릴리즈 질문에 |

CQL 문자열 안의 큰따옴표는 JS 작은따옴표 문자열로 감싸면 이스케이프가 필요 없다: `{tag:"T1", cql:'space=mclassicfaq and type=page and title ~ "Wdg"'}`.

그룹을 CQL로 직접 한정할 조상 ID는 쓰지 않는다(바뀔 수 있음). 대신 제목 관례를 쓴다.

| 그룹 | 제목 관례로 한정 |
| --- | --- |
| 공지 | `title ~ "공지"` (예: `[260121][공지][R40/R44][Wdg][CYTxxx] …`) |
| IA / VC | `title ~ "IA"` 대신 번호가 있으면 `title ~ "IA-087"`, 없으면 본문 키워드 + 결과의 그룹 칸으로 거른다 |
| SAG | `title ~ "SAG"` (예: `[Wdg][R4X][SAG] …`) |
| IM | `title ~ "IM"` (예: `[Wdg][R44] IM`) |
| UM | `title ~ "Configuration Guide"`, `"API Reference"`, `"Limitations"` (예: `Dcm - 3. Configuration Guide`) |

## 2. 계층형 쿼리 세트 (4~8개)

| 태그 | 목적 | 템플릿 |
| --- | --- | --- |
| ID | 식별자 정조준 | `title ~ "IA-087"` / `text ~ "CPINFO-3469"` |
| T | 제목 조합 | `space=mclassicfaq and type=page and title ~ "<모듈>" and title ~ "<MCU*>"` |
| X | 본문 구문 | `space=mclassicfaq and type=page and text ~ "<핵심 구문>"` |
| G | 의도 그룹 | 설정이면 `… and title ~ "<모듈>" and title ~ "SAG"`, 사양이면 `title ~ "<모듈> - "` |
| N | 공지 확인 | `space=mclassicfaq and type=page and title ~ "공지" and title ~ "<모듈 또는 MCU>"` |
| S | 광역 | `siteSearch ~ "<모듈> <현상> <MCU>" and type=page` |
| O | 타 공간 | 보안·HSM이면 `space=msec`, FoD면 `space=FODM` |

실측 예 — "CYT에서 워치독 리셋 문제": T(`Wdg`+`CYT*`) 2건, X(`Watchdog Reset`+`CYT*`) 25건, 제목 `Watchdog` 15건, N(`공지`+`Wdg`) 1건, S 25건 → 병합 48건, 1위 CYTxxx Watchdog Timeout 공지(5개 쿼리 모두 적중), 2위 SAG StartUp Wdg Timer 가이드, 3~5위 IA/VC Reset 규칙.

## 3. 용어 사전 (한글·현상 → 검색어)

| 질문 표현 | 검색어 |
| --- | --- |
| 워치독, WDT | `Wdg`, `WdgM`, `Watchdog` |
| 리프로그래밍, OTA, 부트로더 | `Fota`, `Pfls`, `FBL`, `Reprogram`, `DualM`, `Single Memory` |
| 플래시 쓰기·지우기 | `Fls`, `Pfls`, `Erase`, `Mem_76_Pfls` |
| 진단, UDS | `Dcm`, `Dem`, `DoIP`, `NRC`, `SecurityAccess`, `RoutineControl` |
| 고장코드, DTC | `Dem`, `EventId`, `DTC` |
| 버스오프 | `Bus-Off`, `BusOff`, `CanSM` |
| CAN 통신·신호 | `Com`, `PduR`, `CanIf`, `CanTp`, `IpduM`, `Can` |
| 네트워크 관리, 슬립·웨이크업 | `CanNm`, `OsekNm`, `Nm`, `ComM`, `EcuM`, `Wakeup` |
| LIN | `Lin`, `LinIf`, `LinSM`, `LinTrcv` |
| 이더넷 | `Eth`, `SoAd`, `TcpIp`, `DoIP` |
| 비휘발 메모리 | `NvM`, `Fee`, `Ea`, `MemIf`, `Eep` |
| 보안, 암호, 키 | `Csm`, `CryIf`, `Crypto`, `KeyM`, `SecOC`, `HSM` (+ `space=msec`) |
| 서명 검증 | `Signature Verify`, `RSA`, `CryptoStack` |
| 모드 전환, 초기화 순서 | `BswM`, `EcuM`, `Startup`, `Mode`, `DriverInit` |
| 리셋 원인 | `Reset`, `Mcu`, `How to debug the cause of reset` |
| OS, 태스크, 멀티코어 | `Os`, `Task`, `MultiCore`, `MPU`, `IOC` |
| RTE, 포트 연결 | `Rte`, `Sender-Receiver`, `Client-Server` |
| 시간 동기 | `StbM`, `Global Time` |
| 캘리브레이션, 측정 | `XCP`, `INCA`, `Calibration` |
| 빌드, 컴파일러 | `SCons`, `Compiler`, `build.bat`, `GentoolFWPath` |
| 도구 | `C Studio`, `CLI`, `Script`, `DBScriptGenerator`, `Harmonize` |
| 점검 규칙 | `Validation Checker`, `Integration Auditor`, `IA-`, `VC-` |
| 기능안전 | `FuSa`, `E2E`, `WdgM`, `Safety` |
| 입출력 | `IoHwAb`, `Dio`, `Port`, `Adc`, `Pwm`, `Icu`, `Gpt` |

MCU 표기 흔들림: `CYTxxx`/`CYTxx`/`CYT4BF` → `CYT*`, `TC3xx`/`TC39x` → `TC3*`, `S32K3xx`/`S32K314`/`S32K566` → `S32K*`, `F1KM-S4` → `F1K*`, `SPC58ec` → `SPC58*`.
