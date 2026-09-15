---
name: ecody-ecm-monitor
description: 현대오토에버 eCoDY-ECM(ecody-ecm.autoever.com, mobilgene Classic FAQ 등 고객 기술지원 Confluence)의 변경사항을 "직전 수집 이후~지금" 구간으로 빠짐없이 수집해 중요도순(공지 → Policy → IA/VC 점검규칙 → SAG → IM → UM → 기타)으로 분류·요약하고, 사내 Confluence(mobaseasec) "eCoDY ECM" 페이지 아래에 그룹별 누적 원장(문서 1개 = 1행, 새 문서는 맨 위에 추가, 이미 있는 문서는 그 행을 갱신)과 날짜별 변경 기록 페이지(같은 날 재실행분은 당일 페이지에 추가)로 발행하고, 실패 페이지는 다음 성공 때 복구 표시하는 매일 모니터링 스킬. Cowork 예약 작업이 매일 호출하는 무인 실행용이며 크롬 연동(Claude in Chrome)으로 로그인 세션을 사용한다. 사용자(또는 예약 루틴)가 "eCoDY 모니터링", "ECM 모니터링 실행", "eCoDY 변경사항 정리", "모빌진 FAQ 새 소식", "오토에버 기술지원 사이트 업데이트 확인", "오늘 eCoDY 뭐 바뀌었어", "ECM 일일 리포트" 등을 언급하거나 eCoDY-ECM 변경분을 주기적으로 정리·기록하려는 의도를 보이면 반드시 이 스킬을 사용하라. 특정 주제·설정 방법을 찾아 답하는 요청(예를 들어 "CanSM Bus-Off 설정 찾아줘")은 이 스킬이 아니라 ecody-ecm-search 담당이다.
---

# eCoDY-ECM 일일 변경 모니터링

오토에버 eCoDY-ECM 사이트의 변경분을 모아 사내 Confluence에 두 가지로 쌓는다. **그룹별 원장**은 문서마다 한 행을 두고 계속 누적·갱신하는 "현재 상태 장부"이고, **날짜별 기록**은 그날 무엇이 바뀌었는지 남기는 "일지"다. 매일 아침 Cowork 예약 작업이 부르는 무인 실행이 기본이므로, **실행 중 사용자에게 되묻지 않는다** — 막히면 막힌 사실을 페이지로 남기고 끝낸다.

## 고정 설정

| 항목 | 값 |
| --- | --- |
| 수집 대상 | `https://ecody-ecm.autoever.com` (Confluence DC 9.2, 크롬 로그인 세션 필요) |
| 발행 인스턴스 | `mobaseasec.atlassian.net` |
| 발행 스페이스 | `mobaseasec4` (spaceId `43843599`) |
| 부모 페이지 | `330366991` "eCoDY ECM" |
| 날짜별 기록 제목 | `eCoDY ECM 변경 모니터링 YYYY-MM-DD (요일)` |
| 원장 제목 | `eCoDY 원장 - 공지 (NOTICE)` 외 7종 — `references/ledger.md` §1 |
| 원장 시작일 | 2026-09-15 첫 실행부터. 과거 자료는 가져오지 않는다 |

발행 형식·톤은 `confluence-writing` 스킬 규약(H3부터, html + `data-colwidth` 표, 첨부 있는 페이지는 html 왕복, 수정 직전 fetch)을 따른다. 단 **"수정 전 사용자 허락" 규칙은 이 스킬이 관리하는 페이지(그룹별 원장·부모 안내 영역·자신이 만든 기록 페이지)에 한해 사용자가 사전 승인했다**(2026-09-15). 부모·스페이스는 위 표로 고정되어 매번 확인하지 않는다.


## 권한 원칙

**eCoDY-ECM — 읽기 전용**
- **조회(GET)만** 한다. 스크립트는 GET 이외 요청을 스스로 차단하는 가드를 품고 있으며, 스크립트 밖에서 임의의 `fetch`·폼 제출·편집/삭제/댓글/좋아요/감시 버튼 클릭을 하지 않는다. (2026-09-15 실측: 현재 로그인 계정은 페이지 권한이 `read`뿐이라 서버에서도 쓰기가 거부된다 — 그래도 계정 권한이 바뀔 수 있으므로 스킬이 먼저 지킨다.)
- 탭 DOM 덮어쓰기(dump·read)는 내 브라우저 화면에만 적용되는 로컬 동작이며 서버 데이터와 무관하다. 끝나면 `index.action`으로 다시 열어 원복한다.
- 로그인·OTP·비밀번호는 입력하지 않는다.

**사내 Confluence(mobaseasec) — 생성·수정 가능, 삭제 금지** (사용자 설정: MCP는 삭제 외 전부 허용)
- 생성: 부모 `330366991` 아래 날짜별 기록 페이지, 없는 원장 페이지(최초 1회).
- 수정 허용 범위는 세 가지뿐이다: ① 그룹별 원장 페이지(행 추가·갱신), ② 부모 페이지의 `ECM-INDEX` 관리 영역, ③ 같은 날 이 스킬이 만든 당일 기록 페이지(추가 수집분 덧붙이기), ④ 이 스킬이 만든 `(수집 실패)` 페이지(복구 표시). 그 밖의 페이지는 읽기만 한다.
- 모든 수정은 **직전 `getConfluencePage(contentFormat="html")` → 필요한 부분만 바꿈 → 나머지는 받은 html 그대로 → `updateConfluencePage`** 순서를 지킨다. MCP는 본문 전체를 교체하므로, 받은 html을 건너뛰고 새로 쓰면 사람이 붙여 둔 내용·첨부가 사라진다.
- 삭제·이동(`parentId` 변경)은 하지 않는다. 오래된 페이지 정리도 하지 않는다.

## 설계 원칙 — 왜 이렇게 하는가

- **수집은 기계적으로, 판단은 나중에.** 수집기(`scripts/collect.js`)가 구간 내 변경을 전부 가져와 그룹 분류까지 결정적으로 끝낸다. 제목만 보고 "중요해 보이는 것만" 고르면 빠진다.
- **구간은 직전 페이지가 정한다.** 직전 성공 페이지 본문의 `ECM-WINDOW-END-UTC` 마커가 다음 구간의 시작이다. 주말·휴일·실패가 끼어도 빈틈이 생기지 않는다.
- **조용한 실패가 최악이다.** 세션 만료로 0건이 나오면 "변경 없음"과 구별되지 않는다. 그래서 세션을 먼저 검사하고, 실패하면 실패 페이지를 만들고 부모 안내 영역의 마지막 실행을 실패로 바꾼다.
- **원장은 문서 단위로 누적한다.** 같은 문서가 여러 날 바뀌어도 행은 하나이고, 그 행에 최근 변경과 이력이 쌓인다. 새 문서만 맨 위에 올라가므로 "새로 생긴 것"이 늘 위에 보인다.
- **원장을 그룹별로 나눈 이유**: 하루 수십 문서가 바뀌어 한 표에 쌓으면 금세 수백~천 행이 된다. MCP 수정은 본문 전체를 주고받으므로 표가 작아야 빠르고 안전하다.
- **고객사 전용 자료다.** 요약·링크 중심으로 쓰고 본문을 옮겨 적지 않는다. 설정값·버전 같은 사실은 짧게 인용해도 된다.

## 전체 흐름

```
M0  컨텍스트     KST 날짜·요일, 현재 UTC
M1  브라우저     탭 확보 → ECM 접속 → 세션 검사              (실패 시 M7-F)
M2  구간 확정    하위 페이지 목록 → 직전 마커 · 당일 기록 여부 · 미복구 실패 · 원장 id · 원장 미반영분
M3  수집         collect.js → dump.js → get_page_text
M4  정독         read_pages.js 로 신규 본문 / 변경 줄 확보
M5  작성         references/page-format.md 형식
M6  회계 검사    본문에 실린 건수 = 수집 rows
M7  기록 발행    A. 당일 기록 없음 → 신규 생성 / B. 있음 → 추가 수집분 덧붙이기
M8  원장 반영    그룹별: 새 문서 → 맨 위 행 추가 / 기존 문서 → 그 행 갱신
M9  실패 복구    미복구 (수집 실패) 페이지에 복구 표시
M10 부모 안내    ECM-INDEX 영역(원장 목록·행 수·마지막 실행) 갱신
M11 마무리      탭 원복 → 결과 보고
```

세부 절차 정본: 기록 페이지 형식은 **`references/page-format.md`**, 원장은 **`references/ledger.md`**, 그 밖의 수정(당일 추가·실패 복구·부모 안내)은 **`references/confluence-updates.md`**. 해당 단계에 들어가기 전에 반드시 읽는다.

## M0. 컨텍스트

```bash
TZ=Asia/Seoul date '+%Y-%m-%d %u %H:%M'; date -u '+%Y-%m-%dT%H:%M:%SZ'
```

요일 매핑 `1=월 … 7=일`. 이 값만 오늘의 날짜로 쓰고, 이전 페이지 제목의 날짜를 복사하지 않는다. 이 시각(UTC)이 `WINDOW_END`다.

## M1. 브라우저·세션

> ⚠️ **무인 실행 전제 (실측)**: `navigate`는 `browser_batch` 안에서 호출하면 사이트 권한 확인에 걸려 멈춘다 — **항상 단독 호출**한다. 또 예약 실행이 권한 팝업에서 서지 않도록 Claude in Chrome 확장에서 `ecody-ecm.autoever.com` 사이트 권한을 "항상 허용"으로 두어야 한다. 크롬이 켜져 있고 eCoDY-ECM 로그인(OTP)이 살아 있어야 한다.

1. `tool_search`로 claude-in-chrome 도구를 불러온 뒤 `tabs_context_mcp(createIfEmpty=true)`로 탭을 확보한다.
2. `navigate` → `https://ecody-ecm.autoever.com/` , 3초 대기.
3. 세션 검사 (`javascript_tool`):
   ```js
   const r = await fetch('/rest/api/user/current', {credentials:'include'});
   const u = r.ok ? await r.json() : null;
   JSON.stringify({status:r.status, url:location.href, type:u?.type, name:u?.displayName})
   ```
   `type`이 `known`이 아니거나, 주소가 로그인 페이지이거나, 크롬 연결 자체가 안 되면 **세션 실패** → M7-F로 간다. 로그인·OTP를 대신 입력하지 않는다(비밀번호·인증 입력은 사용자만 한다).

## M2. 구간 확정

1. `getConfluencePageDescendants(cloudId="mobaseasec.atlassian.net", pageId="330366991", depth=1)`로 하위 페이지 목록(id·제목)을 받는다.
2. 제목을 세 부류로 나눈다.
   - **성공 페이지**: `eCoDY ECM 변경 모니터링 YYYY-MM-DD (요일)` — `(수집 실패)` 없음
   - **미복구 실패 페이지**: `(수집 실패)`가 있고 `복구됨`이 없음 → M8 대상 목록으로 기억
   - **복구된 실패 페이지**: `(수집 실패 → 복구됨)` → 무시
3. 성공 페이지 중 제목 날짜 최신 1건을 `getConfluencePage(contentFormat="markdown")`로 읽어 `ECM-WINDOW-END-UTC: <ISO>`를 정규식 `ECM-WINDOW-END-UTC:\s*(\S+)`로 뽑는다. 이 값이 `WINDOW_START`.
4. 그 최신 성공 페이지의 제목 날짜가 **오늘(KST)**이면 → **당일 재실행 모드**(M7-B). 페이지 id를 기억한다.
4-1. 같은 최신 성공 페이지 푸터에 `ECM-LEDGER-PENDING: <그룹들>`이 있으면 → 직전 실행의 원장 반영이 덜 끝난 것이다. 그룹 목록을 기억해 M8에서 먼저 처리한다(`references/ledger.md` §5).
4-2. 목록에서 제목이 `eCoDY 원장 - `으로 시작하는 페이지의 id를 그룹별로 기억한다(M8에서 사용). 없는 그룹은 M8에서 만든다.
5. 성공 페이지가 없거나 마커가 없으면 → **오늘 00:00 KST**(= 전날 15:00 UTC)로 폴백하고 페이지에 "최초 실행" 표시. 사용자 방침이 "과거는 가져오지 않고 오늘부터 누적"이기 때문이다.
6. 구간이 7일을 넘으면 그대로 수집하되 개요에 "장기 공백(N일)"을 명시한다.

## M3. 수집

1. `scripts/collect.js`를 읽어 `__WINDOW_START_UTC__`, `__WINDOW_END_UTC__`를 치환하고, 첫 줄 주석들은 빼고 `javascript_tool`로 실행한다. 반환값은 통계 JSON(`raw`, `rows`, `imgExcluded`, `byGroup`)이다.
2. `scripts/dump.js` 실행 → 곧바로 `get_page_text`. 탭 DOM에 펼친 전체 목록이 온다.
   - **왜 두 단계인가**: `javascript_tool` 반환값은 수천 자에서 잘린다(실측). `get_page_text`는 긴 본문도 온전히 준다.
   - 줄 형식: `n|종류(P/B/C/A)|id|그룹|하위분류|NEW/MOD/CMT|버전|KST시각|작성자|제목|버전메시지|태그`, 끝에 `IMG|컨테이너|개수`.
3. `#STATS`의 `rows`와 실제 줄 수가 같은지 확인한다. 다르면 dump를 다시 실행한다.

그룹 코드: `NOTICE`(공지) `POLICY` `IA`(Integration Auditor) `VC`(Validation Checker) `SAG` `IM` `UM`(R44 User Manual) `CSTUDIO` `OTHER`(FoD·m.Security·Tool Chain 공간) `MISC`(분류 밖 — 스페이스 루트의 버전 사본 등).

**수집기 실측 사실** (2026-09-15 검증): CQL 날짜는 서버에서 UTC로 해석되므로 하루 앞당겨 받고 `version.when`으로 정밀 필터한다 / 한 번에 최대 200건이라 `_links.next`로 넘긴다 / 첨부 대부분은 스크린샷 png이므로 이미지는 건수만 세고, xlsm·zip·pdf 등은 행으로 남긴다(예: Policy "SWP 모듈 Baseline Release" 정보 파일).

## M4. 정독 — 무엇을 읽는가

`scripts/read_pages.js`의 `__WINDOW_START_UTC__`와 `__JOBS__`를 치환해 실행하고 `get_page_text`로 읽는다. 한 번에 8건 이하로 끊는다.

| 대상 | mode | 이유 |
| --- | --- | --- |
| NOTICE·POLICY 전부 | NEW=`body`, MOD=`diff` | 양산 영향 공지는 "무엇이 바뀌었나"가 핵심 |
| OTHER 전부 | 동일 | 드물게 오며 FoD 릴리즈 노트 등 중요 |
| IA·VC·SAG·IM·UM·CSTUDIO의 NEW | `body` | 한 줄 요약에 본문이 필요 |
| SAG·IM의 MOD | `diff` (10건 초과 시 최근 10건) | 가이드 내용 변경은 실무 영향 |
| IA·VC·UM·CSTUDIO의 MOD | 읽지 않음 | 제목·버전메시지로 충분, 일괄 편집이 대부분 |

`diff`는 **구간 시작 시점 버전 → 현재**를 비교한다. 장 번호 체계 도입 같은 형식 재편은 거의 모든 줄이 `+`로 잡힌다(2026-09-15 실측) — 이때는 "형식 재편, 실질 변경은 비교 화면 확인 필요"로 적고 추측으로 내용 변경을 만들지 않는다. 또한 비교는(하루 16번 고친 페이지도 누적 변화가 보인다). 표 재배치 때문에 줄이 뒤섞여 보이면 실제 의미 변화만 골라 요약한다. `(텍스트 변화 없음)`이면 "서식·첨부 수정"으로 적는다. `ERROR`가 난 페이지는 제목만 싣고 "본문 조회 실패"를 표기한다.

## M5. 작성

**`references/page-format.md`가 형식의 정본이다.** 요지:

- 맨 위 개요 박스: 구간(KST), 그룹별 건수, **오늘의 핵심 3줄**(공지 변화·신규 규칙·신규 가이드 중 실무 영향 큰 순).
- 건수가 있는 그룹만 섹션으로, 고정 순서(NOTICE → POLICY → IA → VC → SAG → IM → UM → CSTUDIO → OTHER → MISC → 비이미지 첨부).
- **일괄 편집 접기**: 같은 그룹에서 같은 작성자·같은 버전메시지 MOD가 3건 이상이면 한 행으로 접고 ID·번호를 나열한다(오늘 IA 34건이 이런 경우였다). 접은 행의 건수도 회계에 넣는다.
- 모든 행에 `태그`(R버전·MCU·모듈) 칸을 둔다 — 추후 "우리 과제 MCU·모듈만" 필터의 근거 데이터다.
- 페이지 끝 감사 푸터와 `ECM-WINDOW-END-UTC` 마커는 **글자 그대로** 쓴다. 마커가 틀리면 다음 날 구간이 어긋난다.

## M6. 회계 검사 (발행 전 필수)

본문 각 섹션에 실린 건수(접은 행은 묶인 건수)를 더한 값이 `#STATS.rows`와 같아야 한다. 다르면 빠진 행을 찾아 넣고 다시 센다. 푸터에 `수집 rows N = 게재 N`을 적는다.

## M7. 발행

먼저 `getContentFormatGuide(toolName="createConfluencePage")`와 `getContentFormatGuide(toolName="updateConfluencePage")`를 읽는다.

### M7-A. 당일 페이지가 없을 때 — 신규 생성

`createConfluencePage(cloudId="mobaseasec.atlassian.net", spaceId="43843599", parentId="330366991", title="eCoDY ECM 변경 모니터링 YYYY-MM-DD (요일)", contentFormat="html", body=…)`. 발행 후 `getConfluencePage`로 한 번 읽어 마커 줄과 표가 살아 있는지 확인한다.

### M7-B. 당일 페이지가 있을 때 — 추가 수집분 덧붙이기

새 페이지를 만들지 않는다. `references/confluence-updates.md` §1 절차로 당일 페이지에 `🔁 추가 수집 HH:MM` 블록을 끼워 넣고, 핵심 박스·푸터·`ECM-WINDOW-END-UTC` 마커를 갱신한다. 추가분이 0건이어도 마커와 푸터는 갱신한다(구간 사슬 유지).

### M7-F. 실패 처리

세션 실패·크롬 미연결·수집 예외가 나면:
- **당일 성공 페이지가 없으면** 제목 `eCoDY ECM 변경 모니터링 YYYY-MM-DD (요일) (수집 실패)`로 짧은 페이지를 만든다. 같은 제목이 이미 있으면 새로 만들지 않고 그 페이지에 `references/confluence-updates.md` §2의 "재실패 기록" 한 줄만 추가한다. 내용: 실패 단계, 오류 메시지, 조치("크롬에서 eCoDY-ECM 재로그인 후 수동 실행: 'eCoDY 모니터링 실행'"). **마커는 넣지 않는다** — 다음 성공 실행이 직전 성공 지점부터 이어 받는다.
- **당일 성공 페이지가 이미 있으면** 실패 페이지를 만들지 않는다(그 페이지 마커가 여전히 유효하다). 부모 안내 영역의 마지막 실행만 실패로 바꾼다.
- 어느 경우든 M10 부모 안내 갱신은 수행한다(Confluence 자체는 정상이므로). M8 원장 반영과 M9 복구 표시는 건너뛴다.
- Confluence 발행까지 실패하면 결과 보고에 그 사실을 분명히 적는다.

## M8. 원장 반영

**`references/ledger.md`를 읽고 그대로 수행한다.** 요지:

- 먼저 M2 4-1의 미반영 그룹이 있으면 그 기록 페이지의 해당 섹션 행으로 원장을 보충한다.
- 이번 수집 rows를 원장 그룹으로 나눈다(NOTICE·POLICY·IA·VC·SAG·IM·UM은 각자, CSTUDIO·OTHER·MISC는 `기타`). 비이미지 첨부 행은 **첨부가 달린 문서(컨테이너 pageId)의 행**에 "첨부 추가: 파일명"으로 합친다.
- 그룹마다: 원장 html fetch → 표에서 `pageId=<id>` 링크로 기존 행 탐색 → 없으면 **tbody 맨 위에 새 행**, 있으면 **그 행을 제자리에서 갱신** → update.
- rows가 없는 그룹은 건드리지 않는다.
- 일괄 편집 접기는 기록 페이지에서만 한다. 원장에서는 문서마다 각자 행을 갱신한다(같은 요약이 여러 행에 들어가도 된다).
- 그룹 반영이 두 번 실패하면 그 그룹을 건너뛰고, 기록 페이지 푸터에 `ECM-LEDGER-PENDING: <그룹들>`을 남긴다(다음 실행이 보충). 전부 성공하면 `ECM-LEDGER-PENDING` 줄이 없어야 한다.

## M9. 실패 복구 표시

M7-A/B가 성공했고 M2에서 미복구 실패 페이지가 있었다면, 각 페이지에 `references/confluence-updates.md` §2 절차로 맨 위 복구 박스를 넣고 제목을 `… (수집 실패 → 복구됨)`으로 바꾼다. 복구 판단 근거: 이번 성공 구간 `[WINDOW_START, WINDOW_END]`는 직전 성공 지점부터 이어지므로, 그 사이의 실패 날짜 구간을 반드시 포함한다.

## M10. 부모 안내 영역

부모 `330366991`의 `ECM-INDEX-BEGIN` ~ `ECM-INDEX-END` 영역만 `references/confluence-updates.md` §3 형식으로 다시 쓴다(원장 링크·행 수·마지막 실행 결과). 영역 밖은 받은 html 그대로 보존한다. 실패 실행(M7-F)이어도 이 단계는 수행한다.

## M11. 마무리

1. 탭 원복: `navigate`(단독 호출)로 `https://ecody-ecm.autoever.com/index.action`을 다시 연다(dump가 DOM을 덮어썼다 — 해시만 다른 주소는 새로고침이 안 된다). 이 스킬이 만든 탭이면 닫는다.
2. 실행 결과를 짧게 보고한다: 모드(신규/추가/실패), 기록 페이지 링크, 구간, 그룹별 건수, 핵심 3줄, 원장별 "새 행 N · 갱신 N", 미반영 그룹, 복구 표시한 페이지 수.

## 추후 확장 — 과제 MCU·모듈 필터 (검토 중)

현재는 전체 변경을 중요도순으로 싣는다. 필터 도입 시 근거는 두 가지다: 제목 태그(`[R44]`, `[CYTxxx]`, `[Wdg]` 등 — 수집기가 이미 추출)와 IA/VC 본문의 "MCU" 필드. 제목에 MCU가 없는 항목이 많으므로(예: `[IA-094] CanSM … 검증`) 필터는 "관심 대상 강조 + 나머지 접기"로 설계하고 완전 제외는 하지 않는 편이 안전하다. 적용하려면 과제 프로파일(MCU 목록·사용 모듈·R버전)을 받아 `references/`에 추가한다.
