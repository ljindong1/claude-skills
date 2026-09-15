# 사내 Confluence 수정 절차 (정본)

이 문서는 당일 기록 페이지(§1), 실패 페이지(§2), 부모 안내 영역(§3)의 수정 절차다. 그룹별 원장은 `ledger.md`가 정본이다. 사용자가 2026-09-15에 이 범위의 무인 수정을 사전 승인했다. 삭제·이동은 하지 않는다.

## 0. 공통 수정 규칙

1. **직전 fetch**: `getConfluencePage(cloudId="mobaseasec.atlassian.net", pageId=…, contentFormat="html")`. 받은 html과 `version.number`를 기억한다.
2. **국소 변경**: 아래 절에서 정한 위치만 바꾼다. 나머지 html은 **받은 그대로** 이어 붙인다. `data-id`, `data-collection`, `<figure>`, 매크로 노드 등 모르는 요소는 한 글자도 건드리지 않는다 — 사람이 페이지에 댓글·이미지·설명을 붙였을 수 있다.
3. **송신**: `updateConfluencePage(cloudId, pageId, contentFormat="html", body=…, versionMessage="[ecody-ecm-monitor] <무엇을 바꿨나>")`. 제목을 바꿀 때만 `title`을 넣는다. `parentId`·`spaceId`는 넣지 않는다(이동 방지).
4. **검증**: 응답 version이 fetch 때보다 +1인지 확인한다. 충돌·거부되면 1번부터 한 번만 다시 한다. 두 번째도 실패하면 그 수정은 포기하고 결과 보고에 적는다(무인 실행을 멈추지 않는다).
5. **위치를 못 찾으면 쓰지 않는다**: 기대한 마커·구조가 없으면 추측으로 끼워 넣지 말고, §별 폴백 규칙을 따른다.

## 1. 당일 페이지에 추가 수집분 덧붙이기 (M7-B)

### 1.1 끼워 넣을 위치

푸터는 본문 마지막 `<hr/>`부터 끝까지다. **마지막 `<hr/>` 바로 앞**에 추가 블록을 넣는다. 이전 추가 블록이 있으면 그 뒤(=역시 마지막 `<hr/>` 앞)에 순서대로 쌓인다.

폴백: `<hr/>`나 `ECM-WINDOW-END-UTC`가 안 보이면(사람이 푸터를 지웠음) 덧붙이지 말고 제목 `eCoDY ECM 변경 모니터링 YYYY-MM-DD (요일) -2`로 신규 페이지를 만든다(형식은 일반 신규 페이지와 동일, 개요에 "당일 페이지 구조 손상으로 분리 발행" 표기).

### 1.2 추가 블록 형식

```html
<h3>🔁 추가 수집 14:05 (구간 11:30 ~ 14:05 KST)</h3>
<p>신규 1 · 수정 6 · 이미지 첨부 4건 제외 — IA 3 · SAG 2 · UM 2</p>
<h4>🛠️ SW Application Guide (SAG)</h4>
<table data-layout="default" data-display-mode="fixed"> … page-format.md 와 같은 표 … </table>
```

- 그룹 제목은 `page-format.md`의 H3 이름을 **H4**로 쓴다(추가 블록 H3 아래 계층).
- 표 칸·접기·태그·링크 규칙은 `page-format.md` 그대로.
- 이 페이지에 이미 행으로 실린 pageId가 다시 나오면 구분 칸을 `🔄 재수정`으로 하고 요약 앞에 `(오전 게재분 이후)`를 붙인다. html 안의 `pageId=<id>` 링크로 판별한다.
- 추가분이 0건이면 표 없이 `<p>구간 내 변경 없음</p>`만.

### 1.3 함께 갱신할 곳

| 위치 | 변경 |
| --- | --- |
| `📌 수집 개요` 박스 | 구간 줄의 끝 시각을 새 WINDOW_END(KST)로, 건수 줄 뒤에 `(추가 수집 N회 포함 누적)`과 누적 건수 |
| `💡 오늘의 핵심` 박스 | 추가분에 공지·Policy·신규 IA/VC·신규 SAG가 있으면 `<li>(14:05 추가) …</li>`를 최대 2개 덧붙임. 없으면 그대로 |
| 푸터 | `ECM-WINDOW-START-UTC` 줄 **앞**에 `<p><em>추가 수집 14:05: 원시 … → 구간 내 rows N = 게재 N · 이미지 첨부 M건 제외 · 정독 body a · diff b</em></p>` 한 줄 추가 |
| `ECM-WINDOW-END-UTC` | 값만 새 WINDOW_END로 교체. `ECM-WINDOW-START-UTC`는 첫 실행 값 유지 |

versionMessage 예: `[ecody-ecm-monitor] 추가 수집 14:05 (rows 7)`.

## 2. 실패 페이지

### 2.1 복구 표시 (M8)

본문 **맨 앞**에 넣는다:

```html
<blockquote>
  <p>✅ <strong>복구됨</strong></p>
  <p>2026-09-17 (목) 08:00 KST 실행이 이 실패 구간을 포함해 수집했습니다 → <a href="…">eCoDY ECM 변경 모니터링 2026-09-17 (목)</a></p>
</blockquote>
```

제목은 `… (수집 실패)` → `… (수집 실패 → 복구됨)`. 이미 `복구됨`이 들어 있으면 아무것도 하지 않는다. versionMessage `[ecody-ecm-monitor] 복구 표시`.

### 2.2 재실패 기록 (M7-F, 같은 날 실패 페이지가 이미 있을 때)

본문 **맨 끝**에 한 줄: `<p>⚠️ 재실패 14:05 KST — <단계> · <오류 요약></p>`. 제목은 바꾸지 않는다.

## 3. 부모 안내 영역 (M10)

### 3.1 관리 영역

부모 `330366991` 본문에서 `<p><em>ECM-INDEX-BEGIN</em></p>` 부터 `<p><em>ECM-INDEX-END</em></p>` 까지(두 줄 포함)만 이 스킬 소유다. 영역 밖은 받은 html 그대로 둔다.
- 영역이 없으면 받은 html **앞에** 새 영역을 붙인다(최초 1회 — 2026-09-15 현재 부모 본문은 비어 있다).
- BEGIN만 있고 END가 없는 등 영역이 깨졌으면 건드리지 말고 결과 보고에 "부모 안내 마커 손상 — 수동 확인 필요"를 적는다.

### 3.2 영역 형식

```html
<p><em>ECM-INDEX-BEGIN</em></p>
<blockquote>
  <p>📌 <strong>eCoDY-ECM 변경 모니터링</strong></p>
  <p>오토에버 eCoDY-ECM(mobilgene Classic FAQ · FoD · m.Security · Tool Chain)의 변경을 매일 수집합니다. 2026-09-15부터 누적하며 과거 자료는 포함하지 않습니다.</p>
  <p>마지막 실행: 2026-09-16 (수) 08:00 KST · ✅ 성공 · <a href="…">당일 기록</a></p>
</blockquote>
<h3>그룹별 원장</h3>
<p>문서 1개가 1행입니다. 새로 잡힌 문서는 표 맨 위에 추가되고, 이미 있는 문서가 다시 바뀌면 그 행의 최근 변경·이력이 갱신됩니다.</p>
<table data-layout="default" data-display-mode="fixed">
  <thead><tr>
    <th data-colwidth="260"><p><strong>원장</strong></p></th>
    <th data-colwidth="90"><p><strong>문서 수</strong></p></th>
    <th data-colwidth="410"><p><strong>마지막 실행 반영</strong></p></th>
  </tr></thead>
  <tbody>
    <tr><td data-colwidth="260"><p><a href="…">eCoDY 원장 - 공지 (NOTICE)</a></p></td><td data-colwidth="90"><p>3</p></td><td data-colwidth="410"><p>09-16 · 새 행 1 · 갱신 1</p></td></tr>
  </tbody>
</table>
<h3>날짜별 기록</h3>
<p>하위의 <code>eCoDY ECM 변경 모니터링 YYYY-MM-DD</code> 페이지에 그날 바뀐 내용이 중요도순으로 정리됩니다.</p>
<p><em>ECM-INDEX-END</em></p>
```

### 3.3 갱신 규칙

- 원장 표는 8개 원장을 `ledger.md` §1 순서로 늘 모두 싣는다(아직 없는 원장은 `-`·`아직 없음`). 원장 volume이 나뉘었으면(`ledger.md` §6) 각 volume을 행으로 싣는다.
- 문서 수: 각 원장 표의 현재 행 수(M8 update 뒤 값).
- 마지막 실행 반영: 이번 실행에서 그 원장에 반영한 결과. 이번에 반영 없던 원장은 이전 값을 유지한다. 미반영(PENDING)이면 `⚠️ 반영 실패 — 다음 실행에서 보충`.
- 마지막 실행 줄: 성공 `✅ 성공` / 추가 수집 `🔁 추가 수집 성공` / 실패 `❌ 실패 (<단계>) — 크롬 재로그인 후 수동 실행 필요`.

versionMessage 예: `[ecody-ecm-monitor] 안내 영역 09-16 갱신`.
