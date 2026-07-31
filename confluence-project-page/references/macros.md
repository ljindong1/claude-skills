# 매크로 상세 참고

이 스킬이 생성하는 메인 페이지에 들어가는 네이티브 Confluence 매크로 4종의 동작 메모.
템플릿(`assets/main_page_body.html`)을 수정하거나, 생성 결과가 깨졌을 때 진단용으로 읽는다.

## 1. Page Properties (`details`, bodied-extension)

- `<div data-type="bodied-extension" data-extension-key="details" ...>` 가 `<table>` 을 감싼다.
- 테이블은 라벨 열(`<th>`, 굵게)과 값 열(`<td>`)의 2열. **`<thead>` 를 쓰지 않고 전 행을 `<tbody>`**
  에 둔다. `<thead>` 행에 넣으면 변환기가 값 셀까지 `<th>` 로 만들어 프로젝트명 값이 헤더처럼 굵게/음영
  처리된다(검증됨). 전부 tbody 에 두고 라벨만 `<th>`, 값은 `<td>`.
- 열 너비: 라벨 `data-colwidth="129"`, 값 `data-colwidth="455"`, 테이블 `data-width="760"`.
- 이 매크로로 감싸면 Page Properties Report 매크로로 여러 프로젝트의 개요를 한 표에 집계할 수 있다.
  (집계를 안 써도 단순 표로 정상 렌더링된다.)
- `macroMetadata.macroId.value` 는 매크로 인스턴스 식별자. 페이지마다 새 UUID 권장.

## 2. Child pages (`children`)

- `<div data-type="extension" data-extension-key="children" ...>` (빈 div, body 없음).
- `macroParams.allChildren.value = "true"` → 직속 자식 전체를 목록으로 렌더링.
- 자식 페이지("진행 현황")가 생성되면 자동으로 여기에 나타난다.

## 3. Roadmap Planner (`roadmap`)

- `<div data-type="extension" data-extension-key="roadmap" ...>` (빈 div).
- 핵심은 `data-parameters` 안의 두 값:
  - `source` : URL-encoded JSON. 타임라인 기간, lanes(행), bars(막대), markers(표식)를 담는다.
  - `hash`   : `source` 에 대응하는 체크섬. 정적 미리보기 이미지 URL(`placeholder`)에도 같은 hash 가 쓰인다.
- **source 를 바꾸면 hash 가 어긋난다.** 코드로 날짜/막대를 수정하려 하면 미리보기가 깨지거나
  매크로가 로드 실패할 수 있다. 그래서 이 스킬은 **원본 골격을 그대로 삽입**하고,
  실제 일정은 사용자가 Confluence 편집기(매크로 더블클릭)에서 채우게 한다.
- 편집기에서 저장하면 Confluence 가 source/hash 를 새로 계산해 정합성을 맞춘다.
- 기본 골격 내용: 행 1(노랑)/행 2(파랑), 막대 1·2·3, 표식 1, 기간 2026-06-25~2027-05-25(월 단위).

## 4. 2단 레이아웃 (`layout-two-equal`)

- `<section data-breakout="full-width" data-type="layout-two-equal">`
- `data-breakout="full-width"` → 섹션이 화면 끝까지 펼쳐진다(저장 시 `ac:breakout-mode="full-width"`).
  과거엔 `data-breakout="wide" data-breakout-width="1800"` 도 가능하나, 최대 폭은 full-width 가 낫다.
- 단일 컬럼 full-width 섹션(`data-type="layout-one"`)은 **미지원**(400). 로드맵은 자체 고정 폭이라
  굳이 full-width 로 감쌀 필요가 적어 일반 흐름(자동 fixed-width 섹션)에 둔다.
- 안에 `<div data-type="column" data-width="50">` 2개.
- 왼쪽 = 개요(h3 + Page Properties), 오른쪽 = 하위 페이지(children) + 과제 참여 인원(ul).
- **로드맵 매크로와 구분선(`<hr>`)은 이 section 밖**에 있다 (전체 폭 사용).

## 생성 후 검증

```
getConfluencePage(cloudId, pageId, contentFormat="html")
```
로 다시 읽어 4개 매크로 div 가 모두 살아있는지 확인한다. 매크로가 `<p>텍스트</p>` 로
바뀌어 있으면 contentFormat 이 html 이 아니었거나 data-parameters 가 손상된 것이다.
