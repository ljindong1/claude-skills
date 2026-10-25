# storage XHTML → MCP HTML 변환

브라우저로 읽은 본문은 **storage 포맷**이다. `createConfluencePage`/`updateConfluencePage`가 받는 것은 **MCP HTML**이다. 둘은 다른 형식이며, storage 태그(`<ac:...>`)를 그대로 보내면 거부되거나 텍스트로 노출된다.

MCP로 `contentFormat: "html"`로 읽었다면 이미 MCP HTML이므로 이 변환은 대부분 불필요하다 (첨부·링크 처리만 §6, §7 참조).

## 1. 대응표

| storage 원본 | MCP HTML | 비고 |
| --- | --- | --- |
| `<ac:structured-macro ac:name="code">` + `<ac:plain-text-body><![CDATA[...]]>` | `<pre><code>...</code></pre>` | `<ac:parameter ac:name="language">json</ac:parameter>`이 있으면 `class="language-json"` |
| `<ac:structured-macro ac:name="expand">` + `<ac:parameter ac:name="title">` | `<details><summary>제목</summary>...</details>` | `data-layout="wide"` → `data-breakout="wide"` |
| `<ac:task-list>` / `<ac:task>` | `<ul data-type="task-list">` / `<li data-type="task-item"><input type="checkbox"> 내용</li>` | 완료 상태는 `<input type="checkbox" checked>` |
| `<table>` + `<colgroup><col style="width: 154.0px;">` | `<table data-display-mode="fixed">` + 각 셀에 `data-colwidth="154"` | ⭐ `<colgroup>` 직접 작성 금지 — 저장 시 제거되고 균등 폭이 된다 |
| `<th class="numberingColumn">` (빈 헤더 셀) | 표에 `data-number-column="true"`, 해당 열은 삭제 | 번호 열은 자동 생성되므로 셀을 쓰지 않는다 |
| `<ol start="5">` | `<ol start="5">` | 그대로 유지. 중간에 매크로가 끼어 목록이 끊긴 경우 필요 |
| `<p style="margin-left: 30.0px;">` | `<p>` | 들여쓰기는 유지되지 않는다. 의미상 목록이면 `<ul>`로 바꾸는 편이 낫다 |
| `<span style="color: rgb(7,71,166);">` | `<span style="color: #0747a6">` | 글자색은 이관된다 |
| `<span style="background-color: ...">` | **불가 — §2 참조** | |
| `local-id` / `ac:local-id` 속성 | **전부 제거** | 소스 사이트 전용 식별자. 새 페이지에 넣지 않는다 |
| `&rarr;` `&hellip;` `&quot;` 등 엔티티 | 실제 문자(`→` `…` `"`)로 풀어도 되고 유지해도 된다 | 코드 블록 안에서는 `&lt;` `&gt;` `&amp;` 이스케이프 유지 필수 |

## 2. ⚠️ 형광펜은 이관 불가

MCP HTML은 본문 텍스트의 **배경색(형광펜)을 지원하지 않는다.**

`<span style="background-color: rgb(254,222,200);">텍스트</span>`를 그대로 보내면 서버가 이를 **글자색으로 오변환**한다:

```html
<!-- 보낸 것 -->
<span style="background-color: rgb(254,222,200);">권장 항목</span>
<!-- 저장된 것 -->
<span style="color: #fedec8">권장 항목</span>   ← 글자색 = 배경색 → 안 보임
```

**대응**: 형광펜은 `<strong>`으로 바꾼다. 강조가 문단 전체에 걸린다면 패널이 더 낫다.

```html
<div data-type="panel-info"><p>권장 항목 설명</p></div>
```

되돌리려면 페이지 수정을 한 번 더 해야 하므로, **처음부터 굵게로 넣는다.** 완료 보고에 "형광펜 → 굵게로 대체"를 명시한다.

표 셀 배경은 예외적으로 가능하다: 셀에 `data-background="#색상"`.

## 3. ADF 중첩 규칙

MCP HTML은 ADF로 변환되므로 중첩 제약을 지킨다. 어기면 오류로 거부된다.

- 리스트 항목(`<li>`) 안에 헤딩·표·패널·expand를 넣을 수 없다 — 코드 블록(`<pre>`)은 가능
- 패널 안에 표·expand·blockquote·패널을 넣을 수 없다
- 표 셀 안에 표나 일반 expand를 넣을 수 없다 (중첩 expand는 `<details data-type="nested-expand">`)
- `<html>`, `<head>`, `<body>`로 감싸지 않는다

원본이 이 제약을 위반하는 구조라면(예: 리스트 안의 표) 해당 부분을 리스트 밖으로 빼고, 완료 보고에 알린다.

## 4. 코드 블록 주의

- CDATA 안의 `\n`은 실제 줄바꿈으로 푼다
- 원본이 이스케이프한 백슬래시(`\\\\`)는 실제 값(`\\`)으로 되돌린다 — JSON 응답 안의 이중 이스케이프에 속지 않는다
- 코드 안에 `<`, `>`, `&`가 있으면 `&lt;`, `&gt;`, `&amp;`로 이스케이프한다
- 발행 후 코드 블록 끝에 잔재 토큰이 섞여 들어간 사례가 있다 — 첫 페이지는 발행 직후 확인한다

## 5. 헤더

**원본 헤더 레벨을 그대로 유지한다.** 올리지도 내리지도 않는다.

소스 페이지는 이미 H3 기준으로 작성돼 있다 — `confluence-writing`의 "본문은 H3부터" 규약이 원본 단계에서 충족된 상태다. 그러므로 그대로 복사하면 타겟에서도 규약이 지켜진다. 강등 작업 자체가 불필요하다.

**H2가 보이면 의도적 예외로 간주한다.** 작성자가 해당 구간을 상위 구획으로 삼으려 쓴 것이다. H3로 낮추면 그 위계가 사라지므로 손대지 않는다.

사용자가 명시적으로 조정을 요청한 경우에만 바꾸고, 완료 보고에 어느 페이지의 어느 헤더를 어떻게 바꿨는지 남긴다.

## 6. 첨부

`<figure>` / `<div data-type="media">`의 `data-id`, `data-collection`은 소스 사이트 전용이다. 타겟에 넣으면 깨진다.

자리 표시로 대체한다 (access-routing.md §6).

## 7. 링크

소스 사이트를 가리키는 절대 URL은 타겟에서 접근 불가일 수 있다. access-routing.md §7 참조.

외부 링크(`code.visualstudio.com` 등)는 그대로 두면 된다.
인라인 카드(`<a href="..." data-card-appearance="inline">`)는 그대로 이관된다.

## 8. 발행 후 확인

첫 페이지만 발행 직후 `getConfluencePage(contentFormat: "html")`로 되읽어 확인한다.

- `**` 같은 마크다운 기호가 텍스트로 노출되지 않았는지
- 표 폭(`data-colwidth`)이 반영됐는지
- 코드 블록 끝이 깨끗한지
- **글자색이 배경색과 같아진 곳이 없는지** (§2)

이상 없으면 나머지 페이지는 생략한다. 매 페이지 되읽기는 호출 낭비다.
