# JQL 쿼리 설계 가이드 (eCoDY-IMS, Jira DC 10.3 실측 기준)

eCoDY-IMS(`https://ecody-ims.autoever.com`)는 HAE 의 Jira 다. ECM 이 "가이드 문서"라면 IMS 는 **모듈 릴리즈 노트·수평전개(결함 공지)·당사 문의와 HAE 답변**이 쌓이는 곳이다. "이런 현상이 보고된 적 있나", "어느 버전에서 고쳐졌나"는 IMS 가 1차 소스다.

## 1. 프로젝트 지도 (2026-10 실측, 계정 권한 기준)

| 키 | 이름 | 무엇이 있나 |
| --- | --- | --- |
| `CPINFO` | Classic SWP Information | **모듈 릴리즈 노트**(`CP_ModuleRelease`, 제목 = 모듈명-버전 예 `Os_CYTxxx_R44-2.1.0.0`), 수평전개 원본(`CP_HorizontalDeployment`), 결함 하위작업(`sub-task_SWCR`) |
| `CPIMP` | Classic SWP - New Feature Management | 신규 기능 관리 |
| `MCP0806` | CP_MOBASE_SP3i_PSU | **psu_master** 과제 — Delivery_Patch(`SWP_Module_Release`), 수평전개 사본(`Information`), 당사 문의 |
| `MCP1001` | CP_MOBASE_BJ_TPMS_RF_Receiver | BJ TPMS 과제 |
| `MCP0838` | CP_MOBASE_JG_WPC | JG WPC 과제 |
| `MCP1105` | CP_MOBASE_SV1_PE_PWSW | SV1 PE/PWSW 과제 |

수평전개는 CPINFO 원본 1건이 각 과제(MCPxxxx)에 `Information` 사본으로 복제된다 — 같은 제목이 여러 키로 나오면 CPINFO 원본을 읽고, 우리 과제 사본의 댓글(당사 회신)을 따로 본다.

## 2. 문법 요점

| 형태 | 예 | 메모 |
| --- | --- | --- |
| 전문 검색 | `text ~ "Os_Cfg"` | 요약+설명+댓글. 단어 단위. 영문 식별자는 그대로 잘 잡힘 |
| 요약 검색 | `summary ~ "Os_CYTxxx"` | 릴리즈 노트 찾을 때 |
| AND/OR | `text ~ "스택" AND text ~ "순서"` | 한글 구문은 단어로 쪼개 AND |
| 프로젝트 | `project = CPINFO` / `project in (MCP0806, CPINFO)` | |
| 유형 | `issuetype = CP_ModuleRelease` | 릴리즈 노트만 |
| 기간 | `created >= "2026/07/01"` | |
| 정렬 | `ORDER BY updated DESC` | 스크립트가 없으면 자동으로 붙인다 |

JS 작은따옴표로 감싸면 JQL 큰따옴표 이스케이프가 필요 없다: `{tag:"Q1", jql:'text ~ "Os_Cfg"'}`.

릴리즈 노트 본문은 **영문 + 한글 병기**(`[EN] … [KR] …`)라서, 현상을 찾을 때 영문 기술 용어 쿼리와 한글 쿼리를 둘 다 넣는다.

## 3. 쿼리 세트 (4~8개)

| 태그 | 목적 | 템플릿 |
| --- | --- | --- |
| ID | 식별자 | `key = CPINFO-4186` / `text ~ "SAFERTE_ERR_0329"` |
| S | 심볼·파일명 | `text ~ "<심볼 또는 파일명>"` (예 `GaaRamTaskStackSize`, `Os_Cfg`) |
| K | 한글 현상 | `text ~ "<단어1>" AND text ~ "<단어2>"` |
| E | 영문 현상 | `text ~ "<word1>" AND text ~ "<word2>" AND text ~ "<모듈>"` |
| R | 릴리즈 노트 | `summary ~ "<모듈>_<MCU>*"` 또는 `project = CPINFO AND issuetype = CP_ModuleRelease AND text ~ "<키워드>"` |
| H | 수평전개 | `summary ~ "수평전개" AND text ~ "<모듈 또는 MCU>"` |
| P | 우리 과제 | `project = MCP0806 AND text ~ "<키워드>"` |

## 4. 실측 예 — "빌드마다 Os_Cfg.c 의 태스크 스택 위치가 바뀐다" (2026-10-08)

- S `text ~ "Os_Cfg"` 18건, `text ~ "GaaRamTaskStackSize"` **2건**, K `"스택" AND "순서"` 4건, E `stack AND order AND Os` 18건
- 결론 문서: `CPINFO-4186 Os_U2Ax_R44-2.1.2.0`, `CPINFO-4185 Os_TC3xx_R44-2.1.1.0_HF1` (둘 다 2026-10-01) 의 개선 항목 "동일한 스택 크기의 Extended Task 간 Os_GaaRamTaskStackSize 슬라이싱 순서 비일관성 개선"
- 교훈: **생성 파일 속 심볼명**(S 쿼리)이 가장 정확했다. 결과 수가 적은 쿼리부터 읽는다.

## 5. 함정

- `javascript_tool` 반환값은 짧게 잘리고, `key=value` 형태가 섞이면 "Cookie/query string data" 필터로 통째로 차단된다 → 결과는 항상 DOM 에 펼쳐 `get_page_text` 로 읽는다(스크립트가 그렇게 한다).
- 로그인 계정은 과제별 권한만 있다. 다른 협력사 과제는 안 보인다.
- 댓글은 HAE 로 나가는 외부 메시지다 — 이 스킬은 쓰지 않는다(댓글 작성은 swp-delivery-patch 의 승인 절차).
