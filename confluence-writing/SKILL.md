---
name: confluence-writing
description: 'Confluence 페이지 작성·수정 시 쓰는 공용 규약 스킬 — 글쓰기 톤·구조·서식(헤더 H3 시작, 표는 html+셀 data-colwidth 폭 배분, blockquote 박스, SVG 다이어그램 첨부)과 MCP 발행·수정 메커니즘(첨부 있는 수정은 html 왕복 필수, 모든 수정은 허락+직전 fetch)의 정본. 대상 인스턴스는 사내 mobaseasec.atlassian.net(기본)과 개인 ljindong.atlassian.net TECH 스페이스(사용자가 "개인 위키", "TECH 스페이스" 등으로 지정 시). 사용자가 "컨플루언스 페이지 작성/수정", "위키 페이지", "Atlassian 페이지", "이 내용 컨플루언스에 올려줘", "그 페이지 고쳐줘" 등을 언급하거나 산출물이 Confluence 페이지인 모든 작업에서 반드시 사용하라. 다른 스킬(tech-research-to-confluence, arxml-analyzer 등)이 Confluence에 발행할 때도 본 스킬의 규약을 정본으로 따른다. markdown으로 첨부 있는 페이지를 왕복하면 이미지가 사라진다. SVG 작성 시 svg-creation 스킬 병용(사용자 드래그앤드롭 첨부). 외부 지식을 조사해 새 가이드를 만드는 요청은 tech-research-to-confluence 스킬을 먼저(기획·조사·목차 승인), 본 스킬은 그 작성·발행 단계를 담당. mobaseasec 신규 프로젝트 페이지 세트 개설은 confluence-project-page 스킬 담당. 단순 마크다운 문서나 외부 블로그엔 쓰지 않는다.'
---

# Confluence Writing

Confluence 페이지를 **어떻게 쓰고 올릴까**의 정본 규약. 톤·구조·서식·시각화·MCP 발행/수정 메커니즘을 담당한다.

**무엇을 담을까**(조사, 깊이 프로파일, 목차 승인)는 상위 스킬 `tech-research-to-confluence` 담당 — 외부 지식을 조사해 새 가이드를 만드는 요청이면 그 스킬을 먼저 적용하고, 본 스킬은 작성·발행 단계에서 위임받는다. 다른 스킬(arxml-analyzer 등)이 Confluence에 출력할 때도 본 스킬이 정본이다.

---

## 1. 인스턴스 선택 (가장 먼저)

| 인스턴스 | 성격 | 선택 규칙 |
| --- | --- | --- |
| **mobaseasec.atlassian.net** | **사내** | ⭐ **기본값** — 별도 언급 없으면 여기 |
| **ljindong.atlassian.net** (TECH) | **개인** | 사용자가 지정 시: "개인 위키에", "TECH 스페이스에", "내 컨플루언스에" |

- `getAccessibleAtlassianResources`로 대상 cloudId 확인.
- **스페이스·부모 페이지는 매번 확인** — 특히 사내는 스페이스가 여럿이므로 가정 금지. 개인은 TECH 기본.
- mobaseasec **신규 프로젝트 페이지 세트 개설**은 `confluence-project-page` 스킬로 — 본 스킬은 기술 문서·일반 페이지.

## 2. 작업 유형 결정 트리

| 유형 | 예시 | 흐름 | 필독 |
| --- | --- | --- | --- |
| **A. 신규 페이지 작성** | "이 내용으로 페이지 만들어줘" | 인스턴스·부모 확인 → 작성 → 발행 | writing-style, page-structure, formatting-cheatsheet → confluence-ops |
| **B. 다중 페이지 신규 가이드** | "○○ 가이드 만들어줘" (하위 여러 개) | ⭐ `tech-research-to-confluence`의 목차 승인 게이트 먼저 → 이후 A와 동일 | + tech-research의 content-planning |
| **C. 단순 수정 (첨부 없음)** | "그 페이지 §3 표 고쳐줘" | 변경안 제시 → 허락 → fetch → 교체 → 전체 send | confluence-ops §4 |
| **D. 첨부 있는 페이지 수정** | SVG·이미지가 있는 페이지 | C와 동일하되 **html 왕복 필수** | confluence-ops §4.3 ⭐ |
| **E. 기존 트리 확장** | "그 가이드에 페이지 추가/보강" | 기존 트리 조회(중복 방지) → 신규/수정 분류 → 승인 → 진행 | confluence-ops §3.2~3.3 |

첨부 유무가 불확실하면 D로 간주한다 (html fetch로 확인하는 것이 안전).

## 3. 🚫 사고 방지 절대 규칙

1. **사용자 허락 없이 `updateConfluencePage`를 호출하지 않는다.** 오타 한 글자도 예외 없음. 새 페이지 생성의 후속(부모 목차 갱신 등)도 별개의 수정 작업 — 기본은 하지 않음(연결 최소화 정책), 요청 시 별도 허락.
2. **update 직전에 반드시 `getConfluencePage`로 최신 본문 fetch.** MCP는 부분 수정 미지원 — body는 전체 교체이며, fetch 생략 시 사용자 편집이 통째로 사라진다.
3. **첨부(SVG·이미지) 있는 페이지는 반드시 `contentFormat: "html"` 왕복.** markdown 왕복 시 `<figure>` 참조가 깨져 이미지가 사라진다. `data-id`/`data-collection`은 한 글자도 변경 금지.
4. **표가 포함된 신규 페이지는 `html`로 작성 + 셀 `data-colwidth` 폭 배분** (formatting-cheatsheet §2.2 — `<colgroup>` 직접 작성 금지, 저장 시 제거됨). 표 없는 페이지만 markdown.
5. **본문 헤더는 H3부터.** H1(title 중복)·H2(과대) 금지 — 모든 페이지 예외 없음.
6. **SVG는 `svg-creation` 스킬을 먼저 활성화**해 작성 (viewBox-only, 한글 폰트 스택). MCP 자동 첨부 불가 — 파일 제공 + 자리 표시 blockquote + 사용자 드래그앤드롭.
7. **사용자 요청 없이 3레벨 이상 트리 금지.** 기본 2레벨, Part 묶음 페이지 금지, 대표 목차에 하드 링크 금지(명시 요청 시만).
8. **인스턴스 혼동 금지.** 기본은 사내(mobaseasec), 개인(ljindong TECH)은 지정 시만.

## 4. 세션 관리 (다중 페이지 발행 시)

- 페이지 하나 생성마다 **"N개 중 M번째 완료 + 제목 + ID"** 보고.
- 생성 실패 시 즉시 중단·보고 (묵묵히 건너뛰지 않음).
- 재개 시 대표 페이지 하위 트리를 먼저 조회해 이미 생성된 페이지 확인 후 이어서 진행.

## 5. 참조 문서 로드맵

| 파일 | 언제 읽나 |
| --- | --- |
| `references/writing-style.md` | 본문 작성 전 — 개발자 톤, 분야 판단·비유 매트릭스 |
| `references/page-structure.md` | 구조 설계 시 — 2레벨 트리, 페이지 종류별 구조, 명명, 보일러플레이트, 연결 정책 |
| `references/formatting-cheatsheet.md` | 본문 작성 시 — 헤더 위계(H3), blockquote 박스, 표+data-colwidth 폭, 코드, 시각화 표현 |
| `references/confluence-ops.md` | 발행·수정 시 — 인스턴스/cloudId, contentFormat, 워크플로우, 첨부 html 왕복, 함정, 스팟 검증 |

## 6. 발행 전 최종 체크리스트

**신규 작성 (A/B/E 신규분)**
- [ ] 인스턴스가 맞는가? (기본 사내 mobaseasec / 개인은 지정 시) 스페이스·부모를 확인받았는가?
- [ ] (유형 B) 목차+범위 승인을 받았는가? (tech-research-to-confluence 게이트)
- [ ] 본문 H1·H2 없이 H3부터 시작하는가?
- [ ] 표 포함 페이지를 html + data-colwidth로 작성했는가? (`<colgroup>` 직접 작성 아님)
- [ ] 구조/흐름 페이지에 다이어그램(+색상/화살표/통찰 블록)이 있는가? SVG면 자리 표시 blockquote가 있는가?
- [ ] 분야에 맞는 비유·코드, 마케팅/위로 톤 없음, 2레벨 트리, 목차에 하드 링크 없음?
- [ ] 발행 후 대표+첫 하위 페이지만 스팟 검증 (`**` 노출·표 깨짐·data-colwidth 폭 반영·코드 블록 끝)

**수정 (C/D/E 수정분)**
- [ ] 변경안 제시 + 명시적 허락 (규모 무관)
- [ ] update 직전 fetch + version으로 사용자 편집 확인
- [ ] 첨부 있으면 html 왕복 + `data-id` 보존
- [ ] 기존 트리 조회로 중복 생성 아님 확인 (유형 E)
- [ ] versionMessage에 구체 위치 + 응답 version이 +1 확인

## 7. 핵심 메시지 (한 문장)

> **사내(mobaseasec) 기본으로, H3부터 시작하는 본문·html+data-colwidth 표·다이어그램 우선으로 작성하고 — 수정은 허락+직전 fetch, 첨부 있으면 html 왕복으로 발행한다.**
