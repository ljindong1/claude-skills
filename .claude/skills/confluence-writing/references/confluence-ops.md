# Confluence MCP 운영 규약

Atlassian MCP(`createConfluencePage` / `updateConfluencePage` / `getConfluencePage`)로 발행·수정하는 메커니즘 전부. 본문 표현은 formatting-cheatsheet.md 담당.

---

## 1. 인스턴스·전제

접근 가능한 Confluence 인스턴스는 두 개이며, **혼동하면 안 된다**:

| 인스턴스 | 성격 | 선택 규칙 |
| --- | --- | --- |
| **mobaseasec.atlassian.net** | **사내** Confluence | ⭐ **기본값** — 별도 언급 없으면 여기에 발행 |
| **ljindong.atlassian.net** (TECH 스페이스) | **개인** Confluence | 사용자가 지정할 때만: "개인 위키에", "TECH 스페이스에", "내 컨플루언스에" |

- 작업 시작 시 `getAccessibleAtlassianResources`로 대상 인스턴스의 cloudId를 확인해 사용한다.
- **스페이스·부모 페이지는 매번 확인**한다 — 특히 사내(mobaseasec)는 스페이스가 여럿이므로 어느 스페이스/부모 밑에 둘지 가정하지 않는다. 개인은 TECH 스페이스가 기본.
- mobaseasec **신규 프로젝트 페이지 세트 개설**은 본 스킬이 아니라 `confluence-project-page` 스킬 담당 — 본 스킬은 기술 문서·일반 페이지 작성.
- MCP는 **부분 수정을 지원하지 않는다** — `updateConfluencePage`의 `body`는 페이지 전체 본문. 일부만 보내면 나머지가 사라진다.
- MCP에는 **첨부파일 업로드 도구가 없다** (`attachmentId`는 기존 첨부 참조용).

## 2. contentFormat 선택 ⭐⭐⭐ (가장 먼저 정할 것)

```
enum: markdown / adf / html

[신규 페이지 — createConfluencePage]
  ⭕ "markdown"  ← 표 없는 페이지 기본값. GFM으로 작성하면 서버가 ADF 변환
  ⭐ "html"      ← 표가 포함된 페이지는 이것 — 셀 data-colwidth + 표
                   data-display-mode="fixed"로 컬럼 폭 배분 (formatting-cheatsheet §2.2)
  ❌ "adf"       ← JSON 노드 트리, 손으로 작성 비현실적
  ❌ 생략        ← default가 ADF로 해석돼 파싱 실패 가능

[첨부(SVG·이미지) 있는 페이지 수정 — get → update]
  ⭐ "html"      ← 반드시. storage XHTML을 받아 첨부 참조 보존 (§4.3)
  ❌ "markdown"  ← <figure> 참조가 깨져 들어오고 send 시 첨부 소실
```

> 📌 **검증 이력**: 초판 스킬은 "html은 enum 위반으로 거부됨"이라 기록했으나, **2026-05 재검증에서 get/update 모두 `contentFormat: "html"` 정상 동작 확인** (ljindong 개인 인스턴스 실측). 구판의 "html 금지" 서술은 전부 폐기됐다 — 본 문서가 정본이다.
>
> **2026-07-13 사내(mobaseasec) 실측 완료**: html 왕복 정상 동작. 단 `<colgroup>` 직접 작성은 create/update 모두 저장 시 제거됨(균등 폭 렌더링). 컬럼 폭은 셀 `data-colwidth="N"` + 표 `data-display-mode="fixed"`로 지정 — 저장 시 서버가 `<colgroup><col style="width: N.0px;"/>` + `data-table-display-mode="fixed"`로 변환·보존 (formatting-cheatsheet §2.2). ISO 26262 가이드(대표 268861441) 8개 페이지 17개 표에 적용 완료.

- 첨부 없는 단순 수정: markdown/html 어느 쪽이든 가능하나 **fetch 형식 = send 형식**을 일치시킨다.
- markdown 모드 body에 HTML 태그 인라인 금지 (`<div data-type="panel-info">` 등 — escape되어 노출). ADF 전용 요소는 markdown 대체 수단 사용 (formatting-cheatsheet §6). html 모드에서는 storage XHTML 태그(`<table>`, `<figure>`) 사용 가능 — 단 `<colgroup>` 직접 작성은 저장 시 제거되므로 컬럼 폭은 `data-colwidth`로 (formatting-cheatsheet §2.2).

## 3. 생성 워크플로우

### 3.1 신규 가이드 (대표 + 하위 N개)

```
0. 목차 + 페이지 범위 승인 완료 상태에서 시작 (content-planning §4 — 승인 전 생성 금지)
1. 부모 페이지 ID·spaceId 확인 (대표 페이지를 어디 밑에 둘지 사용자 확인)
2. 대표 페이지 작성·생성 (3블록: 개념/다이어그램/하위 목차 — 목차는 링크 없이 제목 텍스트만)
   → 대표 페이지 ID 획득
3. 하위 페이지 N개를 승인된 목차 순서로 생성 (parentId = 대표 페이지 ID)
   → 매 페이지마다 "N개 중 M번째 완료 + 제목 + ID" 보고 (SKILL.md §4 세션 관리)
4. 발행 후 스팟 검증 (§6)
```

> ⚠️ 구판의 "모든 하위 페이지 생성 후 대표 페이지 목차에 URL 채워 update" 단계는 **폐기** — 연결 최소화 정책(page-structure §3)과 모순이며 불필요한 수정 작업(별도 허락 필요)을 유발한다. 링크는 사용자 명시 요청 시에만.

### 3.2 단일 페이지 추가

```
1. 대표 페이지 ID 확인 + 기존 하위 트리 조회 (중복 주제 페이지 확인 ⭐)
   → 중복이면 신규 생성 대신 §4 수정 워크플로우 전환을 제안
2. 제목 + 다룰 범위 제시 → 승인
3. 동일 spaceId, parentId=대표 ID로 createConfluencePage
```

### 3.3 기존 트리 확장/보강 (신설)

"기존 ○○ 가이드에 최신 내용 보강해줘" 류 요청:

```
1. 대표 페이지와 하위 트리 전체를 조회 (search / getConfluencePage)
   → 어떤 페이지가 이미 있는지 목록화. 조회 없이 작성 시작 금지 (중복 생성 위험)
2. 요청 내용을 [기존 페이지 수정 대상]과 [신규 페이지 대상]으로 분류해 사용자에게 제시
3. 승인 후: 신규는 §3.2, 수정은 §4 워크플로우로 각각 진행
```

## 4. 수정 워크플로우 ⭐⭐

### 4.1 정식 5단계 (변경 규모 무관, 반드시)

> 🚫 **절대 금지 — 사고 위험**
>
> - **사용자 허락 없이 update 호출** — 오타 한 글자도 금지
> - **update 직전 fetch 없이 호출** — 메모리의 본문은 stale (사용자가 직접 편집했을 수 있음)

```
1. 변경안 제시 → 명시적 허락 ("네", "진행" 등 명확 신호. 모호하면 재확인)
2. 허락 직후 getConfluencePage로 최신 본문 fetch
   → 첨부 있으면 contentFormat: "html" (§4.3), 없으면 markdown 가능
   → version 번호 확인: 기억한 값과 다르면 사용자 직접 편집 있었음 → 보존 대상 파악
3. fetch한 본문 위에서 필요한 부분만 교체 (사용자 편집·첨부 참조 그대로 유지)
4. 수정한 전체 본문을 update의 body로 전송 (fetch 형식과 동일 형식)
5. versionMessage에 "[구체 위치] 수정" 명시 → 응답 version이 이전 +1인지 확인 → 사용자 보고
```

변경 규모별로 달라지는 것은 3단계 교체 범위뿐: 한 줄/한 표(패턴 A), 섹션 재작성(패턴 B), 전면 개편(패턴 C — 이 경우도 허락+fetch는 동일 수행).

### 4.2 생성과 수정의 권한 차이

| 작업 | 허락 | fetch |
| --- | --- | --- |
| 생성 (create) | 목차 승인이 곧 권한 (승인된 항목 생성은 OK) | 불필요 |
| **수정 (update)** | **항상 별도 허락** | **항상 직전 fetch** |

새 페이지 생성의 결과로 기존 페이지에 영향이 가더라도(예: 부모 목차 갱신 욕구) 그것은 **별개의 수정 작업** — 기본 정책상 하지 않으며(§3.1), 사용자가 요청하면 5단계를 거친다.

### 4.3 ⭐⭐ 첨부(SVG·이미지) 있는 페이지 — html 왕복 필수

첨부는 본문(storage XHTML)과 별도 자산이며, 본문에서 이렇게 참조된다:

```html
<figure data-type="media-single" data-layout="center" data-width="702" data-width-type="pixel">
  <div data-type="media" data-media-type="file"
       data-id="e7336ec5-...-623037898b10"
       data-collection="contentId-504594449"
       data-width="720" data-height="760">adc-container-tree.svg</div>
</figure>
```

**2026-05 실측**:

| 방식 | 결과 |
| --- | --- |
| markdown fetch → markdown send | ❌ `<figure>`가 `![](blob:...)`로 깨져 들어오고 send 시 참조 소실 → 이미지 사라짐 |
| **html fetch → html send** | ⭐ `<figure>` 그대로 유지 → 첨부 보존 |

절차 (5단계의 구체화): ② `getConfluencePage(contentFormat: "html")` → ③ XHTML 위에서 **텍스트만** 교체 — `<figure>...<div data-type="media" data-id=... data-collection=...>` 블록은 한 글자도 손대지 않음 → ④ `updateConfluencePage(contentFormat: "html", body: 전체 XHTML)`.

> 💡 **첨부가 이미 사라진 경우 복구**: 과거 markdown 왕복 사고로 참조가 사라졌어도 첨부 파일 자체는 attachments 패널에 남아 있다. 사용자가 편집 모드에서 재삽입하거나, Claude가 html fetch 후 해당 `data-id`로 `<figure>` 블록을 다시 끼워 넣으면 복구된다.

### 4.4 자주 발생하는 함정

| 함정 | 결과 | 방지 |
| --- | --- | --- |
| "작은 변경이니 허락 생략" | 한 줄 변경에도 본문 전체 교체 — fetch 안 했으면 사용자 편집 소실 | 규모 무관 5단계 |
| "방금 fetch했으니 또 안 해도 됨" | 그 사이 사용자가 페이지를 만졌을 수 있음 | update 직전 매번 새로 fetch |
| "일부분만 보내면 되겠지" | body는 전체 필수 — 나머지 소실 | 항상 전체 body |
| "부모 목차 갱신은 자연스러운 후속" | 별개 수정 작업 | 기본 안 함, 요청 시 별도 허락 |
| 첨부 페이지를 markdown 왕복 | 이미지 소실 | 첨부 있으면 무조건 html |

## 5. SVG 다이어그램 첨부 메커니즘

MCP 자동 삽입은 전부 차단되어 있다 (2026-05 검증):

- ❌ body 내 `<svg>` 인라인 → 텍스트로 노출
- ❌ `![](data:image/svg+xml;base64,...)` → ADF 파싱에서 소실
- ❌ `<img src="data:...">` → 텍스트 노출
- ⚠️ `![](https://외부 공개 URL)` → Atlassian media가 자동 수입해 렌더링되나 공개 호스팅 필요 — 사내 비공개 환경 불가
- ❌ MCP 첨부 업로드 도구 없음

**채택 경로**: Claude가 SVG 파일 생성(`svg-creation` 스킬 활성화 + formatting-cheatsheet §5.3 규칙) → `/mnt/user-data/outputs/[가이드명]-[다이어그램명].svg` 저장 → `present_files`로 제공 → 본문에는 blockquote(📌) "SVG 첨부 필요" 자리 표시 → **사용자가 편집 모드에서 드래그 앤 드롭** (Confluence가 SVG 그대로 렌더링, PNG 변환 불필요, 페이지당 30초 이내).

자리 표시 없이 발행 금지 — 사용자가 어디에 무엇을 올릴지 알 수 없다. SVG 원본은 수정 편의를 위해 Claude 측 작업물도 보존 권장 (수정 시: 사용자가 파일 재제공 → 수정본 제공 → 사용자가 첨부 교체).

Mermaid/draw.io 매크로: 플러그인 설치를 가정하지 않는다. markdown 모드에서 `{macro:...}` wiki markup은 변환 중 소실 — 플러그인 활용은 사용자가 편집 모드에서 직접 삽입.

## 6. 발행 후 스팟 검증 (가볍게)

굵게(`**`) 토큰 깨짐 등 렌더링 이슈가 간헐 발생하므로 (formatting-cheatsheet §4.1):

- **대표 페이지 + 첫 하위 페이지만** 발행 직후 fetch해 확인: `**` 기호 노출 여부, 표 구조 깨짐, (html 작성 시) `data-colwidth` 폭 반영 여부.
- (html 작성 시) **코드 블록 끝 확인**: `<pre><code>` 안 텍스트에 HTML 태그 유사 문자열이 있으면 잔재 토큰이 섞여 들어가는 사례 관찰됨 (2026-07-13, 1회) — 발행 직후 코드 블록 끝이 깨끗한지 본다.
- **한글 유사 글자 오타**(키릴 문자 혼입 등)는 정적 검사로 안 잡힌다 — 발행 전 본문의 영문 단어를 눈으로 확인.
- 이상 없으면 이후 페이지는 생략 — 매 페이지 fetch는 호출 낭비.
- 이상 발견 시: 해당 패턴을 formatting-cheatsheet §4.1 회피 규칙으로 수정한 뒤, §4 수정 워크플로우(허락 포함)로 갱신.

## 7. versionMessage

수정 시 항상 변경 내용 요약을 남긴다 — 위치를 구체적으로: "§3.2 표 한 행 추가", "PduR 라우팅 절 보강", "롤백 전략 섹션 신규".
