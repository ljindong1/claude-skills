# 접근 경로 판정과 읽기 방법

## 1. 사이트 목록 확인

```
getAccessibleAtlassianResources()
→ [{ id: "37df4bda-...", url: "https://mobaseasec.atlassian.net", name: "mobaseasec", scopes: [...] }, ...]
```

- `id`가 cloudId다. 이후 모든 MCP 호출에 쓴다.
- 사이트 호스트를 cloudId 자리에 그대로 넣어도 동작하는 경우가 있으나, **미승인 사이트는 다음과 같이 거부된다**:
  `Cloud id: 48fa62be-... isn't explicitly granted by the user.`
- 이 오류는 권한 부족이 아니라 **승인 목록에 없다**는 뜻이다. 사용자에게 그렇게 설명한다.

## 2. URL 파싱

```
https://<host>/wiki/spaces/<SPACEKEY>/pages/<pageId>/<제목슬러그>
                                              ^^^^^^^^ 이것만 쓰면 된다
```

짧은 링크(`/wiki/x/AbCdEf`)를 받았다면 그 인코딩 부분을 pageId 자리에 넣어도 MCP가 해석한다.

## 3. 경로 A — MCP 읽기 (소스가 승인된 경우)

```
getConfluencePage(cloudId, pageId, contentFormat: "html")
getConfluencePageDescendants(cloudId, pageId, depth, limit)
```

`contentFormat: "html"`로 받으면 MCP HTML 형식 그대로라 변환 부담이 적다. 단 첨부 `<figure>` 참조는 타겟 사이트에서 무효다 (§5).

## 4. 경로 B — 브라우저 읽기 (소스가 미승인인 경우)

Claude in Chrome으로 소스 사이트의 REST 엔드포인트를 열어 읽는다. 사용자가 이미 그 사이트에 로그인돼 있으므로 쿠키로 인증된다.

### 4.1 사전 준비

1. `list_connected_browsers`로 연결된 브라우저 확인
2. **어느 브라우저를 쓸지 사용자에게 반드시 확인** — 연결된 모든 브라우저를 선택지로 제시하고, 마지막 선택지로 "모든 확장에 확인 창 띄우기"를 넣는다
3. `select_browser(deviceId)`

### 4.2 하위 페이지 목록

```
https://<host>/wiki/rest/api/content/<pageId>/child/page?limit=100
```

`navigate` → `get_page_text` 순으로 JSON을 읽는다. 응답의 `results[]`에서 `id`, `title`, `extensions.position`(정렬 순서)을 취한다.

### 4.3 본문 (저장 포맷)

```
https://<host>/wiki/rest/api/content/<pageId>?expand=body.storage
```

`body.storage.value`가 storage XHTML이다. 화면을 긁는 것보다 훨씬 충실하다 — 표 구조, 코드 블록, 매크로가 다 살아 있다.

빈 페이지는 `"<p />"` 또는 `""`로 온다. 이 둘 다 **본문 없음**으로 판정한다.

### 4.4 하지 말 것

- **`browser_batch`에 navigate를 넣지 않는다.** navigate는 단독 호출, 그다음 배치로 페이지 위 동작. 배치는 tabId 하나만 다룬다.
- **`javascript_tool`의 같은 출처 `fetch`는 동작한다.** 막히는 것은 *결과 표시*다 — 반환값에 쿠키·토큰·base64·긴 원문이 섞이면 `[BLOCKED: Cookie/query string data]`로 가려진다. 원문 대신 길이·개수·앞뒤 60자만 반환하고, 원문은 textarea에 두고 클립보드로 옮긴다(`clipboard-automation.md` §0).
- **`web_fetch`를 쓰지 않는다.** Atlassian이 자동 접근을 막는다(`ROBOTS_DISALLOWED`).
- 사용자가 접근 확인 창에서 거부하면 재시도하지 말고 현재까지 진행 상황을 보고한 뒤 지시를 기다린다.

### 4.5 호출 비용

페이지당 2회(navigate + get_page_text)다. 10개면 20회 + 발행 10회. 페이지가 20개를 넘어가면 시작 전에 소요를 알리고 범위를 좁힐지 묻는다.

## 5. 경로 C — 클립보드 쓰기

타겟이 MCP에 없거나, 서식·첨부를 그대로 가져오고 싶을 때 쓴다. 같은 Confluence 제품끼리는 에디터 클립보드가 내부 문서 포맷을 실어 나르므로 표·코드 블록·패널·형광펜이 **번역 없이** 넘어간다.

절차·스크립트·검증식·첨부 복원은 **`clipboard-automation.md`가 정본**이다. 요점만:

- 소스는 보기 화면만. 발행은 사용자 확인(또는 일괄 승인) 아래서만.
- 검증은 화면이 아니라 **ProseMirror 문서 모델**로 한다(긴 코드블록은 DOM에 일부만 그려진다).
- 사람이 하면 페이지당 1~2분, 자동화하면 약 40초. 40페이지 트리도 한 세션에 끝난다.
- Chrome 창이 포그라운드가 아니면 클립보드가 비어 붙여넣기가 0바이트가 된다.

## 6. 첨부 파일

**경로 C에서는 자동 복원된다** (`clipboard-automation.md` §5): 소스에서 파일을 읽어 클립보드로 넘기고 타겟 "첨부 파일" 화면 폼으로 올린 뒤 본문의 `ri:filename="Invalid file id…"` 참조를 파일명으로 바꾼다. SVG·PNG 모두 원본과 같은 바이트로 들어갔다.

**MCP 쓰기 경로에는 업로드 수단이 없다.** 소스 본문의 `<figure data-type="media">`의 `data-id`/`data-collection`은 소스 전용 식별자라 타겟에서 깨진다. 이 경로를 써야 하면 해당 위치에 자리 표시를 남긴다:

```html
<blockquote><p>📌 첨부 필요: diagram.svg — 편집 모드에서 드래그 앤 드롭</p></blockquote>
```

첨부가 있는 페이지가 많다면 처음부터 경로 C를 권한다.

## 7. 내부 링크

소스 사이트를 가리키는 링크(`https://<소스host>/wiki/...`)는 타겟에서 열리지 않는다.

- 링크 대상이 이번 복사 범위 안에 있으면 → 새로 만든 타겟 페이지 URL로 치환
- 범위 밖이면 → 사용자에게 알리고, 링크를 남길지 텍스트로 풀지 확인
