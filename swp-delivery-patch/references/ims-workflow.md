# eCoDY-IMS 작업 방법

eCoDY-IMS 는 HAE 의 Jira(`https://ecody-ims.autoever.com`)다. 패치 티켓은 `MCP0806-xxx` 처럼 프로젝트 키 + 번호다. 당사 Atlassian MCP(mobaseasec)와는 다른 인스턴스이므로, **현재는 Claude in Chrome 의 로그인 세션으로 읽고 쓴다.**

## 1. 준비

1. claude-in-chrome 도구를 한 번에 로드: `tabs_context_mcp, tabs_create_mcp, navigate, get_page_text, javascript_tool, find, computer, tabs_close_mcp`.
2. `tabs_context_mcp(createIfEmpty=true)` → 새 탭에서 작업한다(사용자 탭 재사용 금지).
3. `navigate` 는 단독 호출한다(batch 안에서는 사이트 권한 확인에 걸려 멈추는 경우가 있다).
4. 로그인·OTP 가 필요하면 멈추고 사용자에게 로그인을 요청한다. 비밀번호를 대신 입력하지 않는다.
5. 끝나면 열었던 탭을 닫는다.

## 2. 티켓 읽기

### 화면 텍스트로 읽기 (가장 간단)

`navigate https://ecody-ims.autoever.com/browse/<KEY>` → `get_page_text`. 본문·첨부 목록·연결 티켓·최근 댓글이 나온다. 단점: 오래된 댓글은 "더 많은 이전 댓글 로드" 뒤에 숨어 있어 빠진다.

### REST 로 전부 읽기 (권장)

같은 탭에서 `scripts/ims_fetch.js` 의 내용을 `javascript_tool` 로 실행하고(맨 위 `KEYS` 배열만 바꿈), 이어서 `get_page_text` 로 읽는다. 스크립트는 `/rest/api/2/issue/<KEY>?expand=changelog,renderedFields` 를 호출해 본문·**댓글 전체(HTML 렌더본)**·첨부(이름·크기·날짜·작성자)·연결 티켓·**변경 이력**을 텍스트로 바꿔 탭 DOM 에 펼친다.

왜 DOM 에 펼치나: `javascript_tool` 의 반환값은 약 1,000자에서 잘리고, 키=값 형태가 섞이면 "Cookie/query string data" 필터에 막혀 통째로 차단된다. `get_page_text` 는 이 제한이 없다.

읽은 뒤에는 탭이 원래 화면이 아니므로, 계속 쓸 탭이면 `navigate` 로 티켓을 다시 연다.

### 읽을 것

- **설명**: 모듈 목록(이전 → 이후), 기존 SWP 버전, UserCode/Reference_Code 안내, MCAL 보증 범위
- **댓글**: 설정변경 안내(1.Information / 2.설정변경 표 / 3.Generator / 4.harmonize / 기타 통합필수점검), VC/IA 안내, 당사 문의와 HAE 답변. 같은 안내가 개정돼 다시 달리는지 날짜순으로 본다.
- **첨부**: 배포본 zip(분할 압축 `.z01`+`.zip` 가능), VC 참고 zip. 같은 이름이 여러 개면 날짜·크기로 구분한다. 압축 비밀번호는 이메일로 온다.
- **변경 이력**: 상태(New / In Progress / 해결), 담당자 이동, 첨부 삭제, 스프린트
- **연결 티켓**: 수평전개(`[수평전개][R44][모듈-버전] …`) — 결함 현상·원인·재현 조건·FBL 영향·적용 대상 조건, 당사 회신 댓글

### 첨부 받기

브라우저 다운로드는 사용자가 한다(파일 다운로드는 승인 대상이고 비밀번호가 필요하다). 받을 위치는 프로젝트 프로필의 "패치 자료 폴더"(예: `D:\Mobase\패치업무\<라인>\v<버전>\<IMS키>\`)를 안내한다. 같은 이름 파일은 브라우저가 `.1` 등을 붙이므로 날짜로 구분해 둔다.

## 3. 질문 댓글

### 양식

`references/templates.md` 의 "IMS 질문 댓글"을 쓴다. 원칙:
- 한 댓글에 질문은 번호를 매겨 묶는다. 무엇을 확인했고(당사 현황) 무엇이 다른지(HAE 안내/배포본) 먼저 쓰고 질문은 예/아니오나 선택지로 답할 수 있게 쓴다.
- 담당자 멘션: 설정변경 안내 댓글의 작성자(배포 담당), VC/IA 는 VC 안내 작성자.
- 화면 캡처가 필요하면 사용자가 붙인다.

### 등록

- **기본**: 초안을 사용자에게 주고 사용자가 직접 등록한다.
- **대행**: 사용자가 그 댓글 하나의 등록을 승인했을 때만. 방법은 둘 중 하나.
  - 화면: 티켓 하단 "댓글 추가" 클릭 → 편집기에 입력 → 저장. 입력 후 저장 전에 화면을 캡처해 사용자에게 보여 주면 더 안전하다.
  - REST: `POST /rest/api/2/issue/<KEY>/comment` (`{"body": "..."}`), 헤더에 `X-Atlassian-Token: no-check`. 본문 표기는 Jira wiki 문법.
- 등록 후 티켓을 다시 읽어 댓글이 올라갔는지 확인하고, 댓글 시각을 Redmine 일감에 기록한다.

상태 변경·담당자 변경·첨부 삭제 같은 다른 쓰기는 이 스킬에서 하지 않는다. 필요하면 사용자에게 화면에서 직접 하도록 안내한다.

## 4. MCP 연결 시 (향후)

eCoDY-IMS 가 Atlassian MCP 등으로 연결되면 Chrome 대신 MCP 를 쓴다. 대응:

| 작업 | Chrome (현재) | MCP (연결 시) |
|---|---|---|
| 접속 확인 | 로그인 화면 여부 | `getAccessibleAtlassianResources` 로 IMS 인스턴스 cloudId 확인 |
| 티켓 읽기 | `ims_fetch.js` + `get_page_text` | `getJiraIssue`(필요 시 changelog·comment 확장), `searchJiraIssuesUsingJql` |
| 연결 티켓 | 스크립트의 links 항목 | `getJiraIssue` 결과의 issuelinks, 또는 JQL `issue in linkedIssues(KEY)` |
| 댓글 등록 | 화면 입력 / REST POST | `addCommentToJiraIssue` |
| 첨부 | 사용자 다운로드 | MCP 가 첨부 다운로드를 지원하지 않으면 계속 사용자 다운로드 |

연결되면 먼저 확인할 것: 어느 cloudId 가 IMS 인지(당사 mobaseasec 와 혼동 금지), 댓글 본문 형식(ADF/markdown/wiki), 계정 권한(읽기만인지). 승인 규칙은 바뀌지 않는다 — MCP 로 쓰든 화면으로 쓰든 IMS 댓글은 HAE 로 나가는 외부 메시지다.

## 5. eCoDY-ECM (가이드)

IM / SAG / IA·VC / UM 정독은 ecody-search 스킬로 한다. IMS 안내 표의 IM 링크가 "권한 없음"이면 같은 제목으로 ECM 을 검색하고, 그래도 없으면 IMS 질문 후보로 올린다. 실제 사례: IA-092 의 원래 링크(pageId 237345493)가 권한 없음이었고, HAE 가 다른 페이지로 재전달했다.
