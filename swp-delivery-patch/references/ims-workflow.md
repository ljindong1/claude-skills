# eCoDY-IMS 작업 방법

eCoDY-IMS 는 HAE 의 Jira(`https://ecody-ims.autoever.com`)다. 패치 티켓은 `MCP0806-xxx` 처럼 프로젝트 키 + 번호다. 당사 Atlassian MCP(mobaseasec)와는 다른 인스턴스이므로, **현재는 Claude in Chrome 의 로그인 세션으로 읽고 쓴다.**

역할 분담:
- **읽기·검색 → `ecody-search` 스킬(IMS 범위)**. 세션 확인, JQL 검색(`ims_search.js`), 정독(`ims_read.js` — 본문·댓글·첨부·연결·하위작업·변경 이력), 읽기 전용 가드, 차단 필터 회피(DOM 에 펼쳐 `get_page_text`)가 그 스킬에 있다. 이 스킬은 IMS 를 직접 읽는 스크립트를 따로 두지 않는다.
- **쓰기(질문 댓글) → 이 스킬**. `ecody-search` 는 읽기 전용이고 IMS 댓글을 이 스킬로 넘긴다.

## 1. 패치 티켓 읽기 (S1)

`ecody-search` 스킬을 IMS 범위로 쓴다(`/ecody-search IMS …` 또는 대화로 "IMS 만"). 패치 티켓에 맞춘 사용법:
- 정독: `ims_read.js` 에 `__KEYS__ = ["<패치 키>", "<연결 수평전개 키>"]`, `__MAX__` 는 **60000 정도** — 설정변경 안내 댓글 하나가 1만 자를 넘는다(MCP0806-279 실측 약 1.7만 자). 기본값 8000 이면 안내 표가 잘린다.
- 검색(S3·선행 작업): 같은 모듈·버전의 다른 과제 Delivery_Patch, 수평전개 원본(CPINFO), 과거 문의·답변을 JQL 로 찾는다(그 스킬의 `references/ims-query-guide.md`).
- 화면 텍스트(`navigate` → `get_page_text`)만으로 읽으면 오래된 댓글이 "더 많은 이전 댓글 로드" 뒤에 숨어 빠진다. 반드시 `ims_read.js` 로 읽는다.

### 읽을 것 (요청 항목 목록을 만들기 위한 기준)

- **설명**: 모듈 목록(이전 → 이후), 기존 SWP 버전, UserCode/Reference_Code 안내, MCAL 보증 범위
- **댓글**: 설정변경 안내(1.Information / 2.설정변경 표 / 3.Generator / 4.harmonize / 기타 통합필수점검), VC/IA 안내, 당사 문의와 HAE 답변. 같은 안내가 개정돼 다시 달리는지 날짜순으로 본다. `(수정 …)` 표시가 붙은 댓글은 내용이 바뀐 것이다.
- **첨부**: 배포본 zip(분할 압축 `.z01`+`.zip` 가능), VC 참고 zip. 같은 이름이 여러 개면 날짜·크기·작성자로 구분한다. 압축 비밀번호는 이메일로 온다.
- **변경 이력**: `Attachment [이름 → ]` 는 첨부 삭제, `[ → 이름]` 은 추가 — 같은 시각의 삭제+추가는 **재배포(교체)** 다. 상태(New / In Progress / 해결), 담당자 이동(문의·답변 흐름), 스프린트.
- **연결 티켓**: 수평전개(`[수평전개][R44][모듈-버전] …`) — 결함 현상·원인·재현 조건·FBL 영향·적용 대상 조건, 당사 회신 댓글

### 첨부 받기

브라우저 다운로드는 사용자가 한다(파일 다운로드는 승인 대상이고 비밀번호가 필요하다). 받을 위치는 프로젝트 프로필의 "패치 자료 폴더"(예: `D:\Mobase\패치업무\<라인>\v<버전>\<IMS키>\`)를 안내한다. 같은 이름 파일은 브라우저가 `.1`·`(1)` 등을 붙이므로 날짜로 구분해 둔다.

## 2. 질문 댓글 (S7)

### 양식

`references/templates.md` 의 "IMS 질문 댓글"을 쓴다. 원칙:
- 한 댓글에 질문은 번호를 매겨 묶는다. 무엇을 확인했고(당사 현황) 무엇이 다른지(HAE 안내/배포본) 먼저 쓰고 질문은 예/아니오나 선택지로 답할 수 있게 쓴다.
- 담당자 멘션·인사·맺음말은 넣지 않는다. 배정은 HAE 가 한다. 한 줄 서두("<FBL|APP> V<x> 패치 적용 중 아래 N건 확인 부탁드립니다.") 뒤 바로 번호 매긴 본론.
- 화면 캡처가 필요하면 사용자가 붙인다.
- 묻기 전에 `ecody-search` 로 같은 질문이 다른 과제 티켓·ECM 에 이미 답이 있는지 찾아본다(HAE 의 "기술지원 문의 전 FAQ 사전 확인" 안내).
- 질문은 판단 경로 C 항목만(`precheck.md`). 등록 후 답이 오면 질문 번호마다 받았는지 대조하고, 빠진 번호는 다시 묻는다.

### 등록

- **기본**: 초안을 사용자에게 주고 사용자가 직접 등록한다.
- **대행**: 사용자가 그 댓글 하나의 등록을 승인했을 때만. Chrome 탭 준비(`tabs_context_mcp` → 새 탭, `navigate` 는 단독 호출, 로그인·OTP 는 사용자가) 후 둘 중 하나.
  - 화면: 티켓 하단 "댓글 추가" 클릭 → 편집기에 입력 → 저장. 저장 전에 화면을 캡처해 사용자에게 보여 주면 더 안전하다.
  - REST: `POST /rest/api/2/issue/<KEY>/comment` (`{"body": "..."}`), 헤더에 `X-Atlassian-Token: no-check`. 본문 표기는 Jira wiki 문법.
- 등록 후 `ims_read.js` 로 다시 읽어 댓글이 올라갔는지 확인하고, 댓글 시각을 Redmine 일감에 기록한다. 끝나면 탭을 닫는다.

상태 변경·담당자 변경·첨부 삭제 같은 다른 쓰기는 이 스킬에서 하지 않는다. 필요하면 사용자에게 화면에서 직접 하도록 안내한다.

## 3. MCP 연결 시 (향후)

eCoDY-IMS 가 Atlassian MCP 등으로 연결되면 Chrome 대신 MCP 를 쓴다. 읽기 쪽은 `ecody-search` 스킬도 함께 바꿔야 한다. 대응:

| 작업 | Chrome (현재) | MCP (연결 시) |
|---|---|---|
| 접속 확인 | ecody-search S0 (`/rest/api/2/myself`) | `getAccessibleAtlassianResources` 로 IMS 인스턴스 cloudId 확인 |
| 티켓 읽기 | ecody-search `ims_read.js` + `get_page_text` | `getJiraIssue`(changelog·comment 확장), `searchJiraIssuesUsingJql` |
| 연결 티켓 | `ims_read.js` 의 연결·하위작업 | `getJiraIssue` 결과의 issuelinks, 또는 JQL `issue in linkedIssues(KEY)` |
| 댓글 등록 | 화면 입력 / REST POST (이 스킬) | `addCommentToJiraIssue` |
| 첨부 | 사용자 다운로드 | MCP 가 첨부 다운로드를 지원하지 않으면 계속 사용자 다운로드 |

연결되면 먼저 확인할 것: 어느 cloudId 가 IMS 인지(당사 mobaseasec 와 혼동 금지), 댓글 본문 형식(ADF/markdown/wiki), 계정 권한(읽기만인지). 승인 규칙은 바뀌지 않는다 — MCP 로 쓰든 화면으로 쓰든 IMS 댓글은 HAE 로 나가는 외부 메시지다.

## 4. eCoDY-ECM (가이드)

**IM 페이지 이전(2026 하반기).** 옛 IM 링크가 일괄로 새 페이지로 옮겨져, 안내 댓글의 링크가 "권한 없음"으로 뜨는 일이 반복됐다(6개 티켓). 질문하기 전에 새 제목으로 ECM 을 검색한다(판단 경로 B).

| 옛 페이지 (권한 없음) | 새 페이지 |
|---|---|
| `210274216` [Dcm][R44] IM | `371179712` [IM] Dcm - R44 |
| `202544131` [Crypto_76_HaeModule][R4X] IM with HSM | `380194776` [Crypto_76_HaeModule][1.x] IM with HSM, `371179526` [IM] Crypto_76_HaeModule - 2.X |
| `202543662` [Com][R44] IM | `371166481` [IM] COM |
| `202543677` [DataLog][R44] IM | `380185856` [IM] DataLog - R44 |
| `202543543` [Os][R44] IM | `380181792` [IM] Os - R44 |
| (Fota/Pfls) | `371163753` [IM] Fota/Pfls, `371179824` [IM] Fota/Pfls - 2. GptChannel for Fota |

검색어 형식: `[IM] <모듈> - R44` 또는 `[IM] <모듈> - 2.X`. 절 번호도 바뀌었으니(예: Dcm HF4 5.1.1.29 → 4.1.28) 절 제목으로 찾는다.

IM / SAG / IA·VC / UM 정독도 `ecody-search` 스킬(ECM 범위)로 한다. IMS 안내 표의 IM 링크가 "권한 없음"이면 같은 제목으로 ECM 을 검색하고, 그래도 없으면 IMS 질문 후보로 올린다. 실제 사례: IA-092 의 원래 링크(pageId 237345493)가 권한 없음이었고, HAE 가 다른 페이지로 재전달했다.
