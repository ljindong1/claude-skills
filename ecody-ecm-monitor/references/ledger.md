# 그룹별 누적 원장 (정본)

원장은 **eCoDY 문서 1개 = 1행**인 누적 장부다. 2026-09-15 첫 실행부터 쌓으며 과거 자료는 채우지 않는다. 사용자 요구 그대로: **새로 잡힌 문서는 표 맨 위에 추가하고, 이미 있는 문서가 다시 바뀌면 그 행을 제자리에서 갱신한다.**

## 1. 원장 페이지 8종

| 원장 그룹 | 제목 (부모 330366991 아래) | 담는 수집 그룹 |
| --- | --- | --- |
| NOTICE | `eCoDY 원장 - 공지 (NOTICE)` | NOTICE |
| POLICY | `eCoDY 원장 - Policy` | POLICY |
| IA | `eCoDY 원장 - Integration Auditor (IA)` | IA |
| VC | `eCoDY 원장 - Validation Checker (VC)` | VC |
| SAG | `eCoDY 원장 - SW Application Guide (SAG)` | SAG |
| IM | `eCoDY 원장 - Integration Manual (IM)` | IM |
| UM | `eCoDY 원장 - R44 User Manual (UM)` | UM |
| 기타 | `eCoDY 원장 - 기타 (C Studio · FoD · m.Security · Tool Chain)` | CSTUDIO · OTHER · MISC |

원장 페이지가 없으면(M2 4-2) 그 그룹에 반영할 행이 생긴 실행에서 `createConfluencePage`로 만든다(§3 골격). 반영할 행이 없는 그룹의 빈 원장은 미리 만들지 않는다.

## 2. 행 = 문서

**행 식별자는 eCoDY pageId**다. 문서 칸의 링크 `https://ecody-ecm.autoever.com/pages/viewpage.action?pageId=<id>`로 찾는다. 제목은 바뀔 수 있으므로 제목으로 찾지 않는다.

비이미지 첨부 행(`A`)은 독립 행을 만들지 않는다. 컨테이너 pageId의 행에 합쳐 그날 이력에 `첨부 추가: <파일명>`을 붙인다. 컨테이너 문서가 이번 rows에 없으면(첨부만 추가됨) 첨부를 근거로 그 문서 행을 추가·갱신한다. 댓글 행(`C`)도 같은 방식으로 `댓글 N건`.

한 실행 안에서 같은 pageId는 한 번만 반영한다.

## 3. 원장 페이지 골격

```html
<blockquote>
  <p>📒 <strong>eCoDY 원장 - 공지 (NOTICE)</strong></p>
  <p>2026-09-15부터 누적 · 문서 1개 = 1행 · 새 문서는 맨 위에 추가, 기존 문서는 해당 행 갱신 · 자동 관리 표입니다(행 순서·링크를 바꾸면 갱신이 어긋날 수 있습니다)</p>
</blockquote>
<table data-layout="default" data-display-mode="fixed">
  <thead><tr>
    <th data-colwidth="45"><p><strong>No</strong></p></th>
    <th data-colwidth="215"><p><strong>문서</strong></p></th>
    <th data-colwidth="95"><p><strong>상태</strong></p></th>
    <th data-colwidth="90"><p><strong>최초 · 최근</strong></p></th>
    <th data-colwidth="45"><p><strong>횟수</strong></p></th>
    <th data-colwidth="270"><p><strong>변경 이력 (최신이 위)</strong></p></th>
  </tr></thead>
  <tbody>
  </tbody>
</table>
<p><em>ECM-LEDGER-ROWS: 0</em></p>
```

폭 합계 760. 본문 헤더는 쓰지 않는다(표 하나짜리 페이지).

## 4. 칸 채우기

| 칸 | 새 행 | 기존 행 갱신 |
| --- | --- | --- |
| No | 현재 표의 최대 No + 1 (첫 행은 1) | 그대로 |
| 문서 | `<a href="…pageId=<id>">제목</a>` + 줄바꿈 후 작게 `하위분류 · 태그` (없으면 생략) | 제목이 바뀌었으면 새 제목으로, 링크 id는 그대로 |
| 상태 | 구간 내 생성(`NEW`) → `🆕 신규 문서` / 기존 문서의 첫 기록(`MOD`) → `📝 기록 시작` | `🔄 변경` (최근 실행에서 바뀐 행의 표시) |
| 최초 · 최근 | `09-15` · `09-15` | 최초 그대로 · 최근을 오늘 `MM-DD`로 |
| 횟수 | 1 | 기존 값 + 1 (같은 날 추가 수집으로 두 번째 반영이면 +1 하지 않는다 — **날짜 기준 횟수**) |
| 변경 이력 | `<p>09-15 · v17 · 요약</p>` 한 줄 | 맨 위에 새 줄 삽입. 같은 날 줄이 이미 있으면 새 줄 대신 그 줄 요약 뒤에 `; 14:05 추가 요약`을 덧붙인다 |

- **상태 칸의 의미**: 행을 옮기지 않으므로 "최근에 바뀐 기존 문서"는 `🔄 변경`과 최근 날짜로 알아본다. 다음 실행에서 그 문서가 안 바뀌어도 상태는 그대로 두고(최근 날짜가 오래되며 자연히 구분된다) 되돌리지 않는다.
- **요약**: 기록 페이지에 쓴 그 문서의 변경 요약을 40~80자로 재서술. 읽지 않은 MOD는 버전메시지(짧게) 또는 `내용 수정`. 첨부·댓글 합침은 `첨부 추가: x.xlsm` 식으로 뒤에 붙인다.
- **이력 길이 제한**: 이력 줄이 8줄을 넘으면 가장 오래된 줄들을 지우고 맨 아래에 `<p>… 이전 N건은 날짜별 기록 참조</p>` 한 줄로 합친다(이미 있으면 N만 늘린다). 행이 끝없이 길어지는 것을 막기 위해서다.
- 새 행은 **tbody의 첫 `<tr>` 앞**에 넣는다. 한 실행에서 새 행이 여러 개면: 최근 시각 오름차순(같은 분이면 수집 목록 역순)으로 No를 매기고, **No 내림차순**으로 끼워 넣는다. 결과적으로 표는 늘 위에서 아래로 No가 줄어든다(같은 분에 일괄 수정된 문서들의 번호가 뒤섞이지 않게 — 2026-09-15 실측).
- 기존 행 갱신 시 그 `<tr>`만 교체하고 **위치는 옮기지 않는다**.
- 표 아래 `ECM-LEDGER-ROWS: N`을 현재 행 수로 고친다.

## 5. 절차 (그룹마다)

1. 원장 id가 없으면 §3 골격으로 생성하고 그 id·html을 쓴다. 있으면 `getConfluencePage(contentFormat="html")`.
2. 이번 rows(그룹 해당분 + 합칠 첨부·댓글)를 pageId별로 묶는다.
3. 각 pageId: html에서 `pageId=<id>"` 를 포함한 `<tr>`을 찾는다 → 있으면 §4 갱신, 없으면 새 행 목록에 넣는다.
4. 새 행을 No 내림차순으로 tbody 맨 앞에 넣는다(최신이 가장 위, §4 규칙).
5. **검산**: 갱신 후 행 수 = 갱신 전 행 수 + 새 행 수. 표 안 pageId 링크가 중복되지 않는다. 틀리면 3번부터 다시 한다.
6. `updateConfluencePage(contentFormat="html", versionMessage="[ecody-ecm-monitor] 09-16 원장 반영: 새 행 N · 갱신 M")`. 공통 규칙은 `confluence-updates.md` §0.
7. 두 번 실패하면 이 그룹을 `ECM-LEDGER-PENDING` 목록에 넣고 다음 그룹으로 넘어간다.

모든 그룹이 끝나면: PENDING이 있으면 당일 기록 페이지 푸터의 `ECM-WINDOW-START-UTC` 줄 앞에 `<p><em>ECM-LEDGER-PENDING: SAG, IM</em></p>`를 넣는다(이미 있으면 목록을 교체). 모두 성공했고 그 줄이 있었다면 그 줄을 지운다.

### 5.1 미반영 보충 (M2 4-1)

직전 기록 페이지에 `ECM-LEDGER-PENDING`이 있으면, 이번 수집분보다 **먼저** 그 페이지의 해당 그룹 섹션 표(추가 수집 블록 포함)를 읽어 행을 복원해 원장에 반영한다. 기록 페이지 행에는 pageId 링크·날짜·요약이 있으므로 충분하다. 접힌 일괄 편집 행은 나열된 ID(IA-063 등)를 원장 표 제목과 대조하거나, 대조가 안 되면 eCoDY에서 `title ~ "IA-063"`으로 pageId를 조회해 복원한다. 보충이 끝나면 그 기록 페이지의 PENDING 줄에서 해당 그룹을 지운다.

## 6. 원장이 커질 때

`ECM-LEDGER-ROWS`가 300을 넘으면 새 volume `eCoDY 원장 - SW Application Guide (SAG) (2)`를 만들고, **새 행은 최신 volume에** 추가한다. 기존 문서 갱신은 그 행이 있는 volume에서 한다(그래서 3단계 탐색은 그룹의 모든 volume을 뒤진다). IA·VC·공지·Policy는 사이트 문서 수 자체가 100 안팎이라 나뉠 일이 거의 없고, SAG·IM·UM이 대상이다.
