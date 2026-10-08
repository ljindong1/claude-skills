---
name: ecody-search
description: 현대오토에버 eCoDY 두 사이트 — eCoDY-ECM(ecody-ecm.autoever.com, 가이드: mobilgene Classic FAQ의 공지·Policy·IM·SAG·IA/VC·R44 User Manual·C Studio 매뉴얼)과 eCoDY-IMS(ecody-ims.autoever.com, Jira: 모듈 릴리즈 노트·수평전개·Delivery_Patch·문의와 답변) — 를 CQL/JQL 다중 검색·정독해 근거 링크와 함께 답하는 읽기 전용 스킬. 첫 매개변수로 범위를 고른다 — ECM 이면 ECM 만, IMS 면 IMS 만, 없으면 둘 다. 크롬 연동(Claude in Chrome) 로그인 세션을 쓴다. 사용자가 "eCoDY에서 찾아줘", "ECM 검색", "IMS 검색", "IMS에 이런 이슈 있었나", "어느 버전에서 고쳐졌어", "릴리즈 노트 찾아줘", "수평전개 있었나", "모빌진 FAQ에 ○○ 있어?", "○○ 설정 방법 오토에버 가이드", "IA-087 내용", "CPINFO-4186 내용", "CanSM Bus-Off 설정 어떻게 하라고 돼 있지", "C Studio CLI 사용법", "오토에버에 문의하기 전에 조사해줘" 등을 말하거나, mobilgene/AUTOSAR BSW·MCAL·FBL·Fota·진단·생성기 동작을 오토에버 공식 자료 기준으로 확인하려 하면 반드시 이 스킬을 사용하라. "모빌진 기준", "오토에버 가이드 기준"이 붙은 일반 AUTOSAR 질문도 해당한다. ECM 일일 수집은 ecody-ecm-monitor, Delivery_Patch 적용과 IMS 댓글은 swp-delivery-patch 담당. (구 이름: ecody-ecm-search)
---

# eCoDY 검색·답변 (ECM + IMS)

사용자의 질문을 **오토에버 공식 자료 기준으로** 답한다. 핵심은 세 가지다: 여러 각도로 검색해 후보를 넓게 잡고, 상위 문서·이슈를 **실제로 읽고**, 답의 각 주장에 **근거 링크**를 붙인다. 자료에 없는 내용을 일반 지식으로 메우지 않는다.

## 두 사이트의 역할

| 사이트 | 성격 | 이런 질문에 |
| --- | --- | --- |
| **ECM** `ecody-ecm.autoever.com` (Confluence DC 9.2) | 가이드 문서 | "어떻게 설정하라고 돼 있나", 점검 규칙 이유, API·사양, 도구 사용법, 정책 |
| **IMS** `ecody-ims.autoever.com` (Jira DC 10.3) | 이슈·릴리즈 기록 | "이런 현상이 보고된 적 있나", "어느 버전에서 고쳐졌나", 수평전개(결함 공지), 우리 과제 Delivery_Patch 안내, 과거 문의·답변 |

## 검색 범위 매개변수

호출 인자(args)의 **첫 단어**로 검색할 사이트를 고른다. 대소문자는 가리지 않는다.

| 첫 단어 | 범위 | 예 |
| --- | --- | --- |
| `ECM` | ECM 만 검색. IMS 에는 접속하지 않는다 | `/ecody-search ECM C Studio 설치 방법` |
| `IMS` | IMS 만 검색. ECM 에는 접속하지 않는다 | `/ecody-search IMS Os 스택 슬라이싱 순서` |
| 그 외(없음) | **ECM + IMS 둘 다** | `/ecody-search CanSM Bus-Off 설정` |

- 매개변수 단어는 질문에서 떼어 내고 나머지를 질문으로 쓴다.
- 대화로 호출됐을 때 사용자가 "ECM 에서만", "IMS 만 봐줘" 처럼 범위를 말하면 같은 규칙을 적용한다. 말이 없으면 둘 다.
- 한쪽만 검색했는데 결과에 다른 사이트 식별자(CPINFO-xxxx, IM 링크)가 나오면 **따라가지 말고** 답변의 "확인 못 한 점"에 "IMS(또는 ECM)에서 추가 확인 가능"으로 적는다 — 사용자가 고른 범위를 넘지 않는다.
- 둘 다 검색할 때 한 사이트 세션이 만료됐으면 다른 사이트는 계속 진행하고, 만료된 사이트는 로그인 안내와 함께 "확인 못 한 점"에 남긴다.

둘 다 볼 때의 읽는 순서: **어떻게 해야 하나 → ECM 먼저**, **이런 일이 있었나/고쳐졌나 → IMS 먼저**. 한쪽 결과에 다른 쪽 식별자가 나오면 따라가서 읽는다.

## 권한 원칙 — 읽기 전용

- 두 사이트 모두 **조회(GET)만** 한다. 스크립트는 GET 이외 요청을 스스로 차단하는 가드를 품고 있으며, 스크립트 밖에서 임의의 `fetch`·폼 제출·편집/삭제/댓글/좋아요/감시/상태 변경 버튼 클릭을 하지 않는다.
- IMS 댓글은 HAE 로 나가는 외부 메시지다. 이 스킬은 쓰지 않는다 — 질문 초안이 필요하면 초안만 채팅으로 주고, 등록은 swp-delivery-patch 의 승인 절차를 따른다.
- 탭 DOM 덮어쓰기(검색·정독 결과 펼치기)는 내 브라우저 화면에만 적용되는 로컬 동작이다. 끝나면 탭을 닫거나 원복한다.
- 로그인·OTP·비밀번호는 입력하지 않는다. 브라우저의 로그인 계정이 사용자 본인 것이 아니면(공용 계정 등) 그 사실을 답변에 한 줄 남긴다.
- 결과를 Confluence 에 남기는 것은 사용자가 요청할 때만, `confluence-writing` 스킬 규약으로 한다.

## 전체 흐름

```
S0 브라우저·세션   범위 결정(ECM/IMS/둘 다) → 탭 확보 → 범위의 사이트만 접속 → 세션 검사
S1 질문 분석       의도 · 키워드 · 식별자 · 모듈/MCU/버전 · 어느 사이트
S2 쿼리 설계       ECM CQL 4~8개 / IMS JQL 4~8개
S3 후보 수집       ecm_search.js / ims_search.js → get_page_text
S4 선별            의도-그룹 적합도로 3~6건씩
S5 정독            ecm_read.js / ims_read.js → get_page_text
S6 답변            형식대로 · 근거 링크 · 관련 공지 경고 · 우리 과제 적용 여부
S7 정리            탭 닫기
```

## S0. 브라우저·세션

> ⚠️ **실측**: `navigate`는 `browser_batch` 안에서 호출하면 사이트 권한 확인에 걸려 멈춘다 — **항상 단독 호출**한다. Claude in Chrome 확장에서 두 사이트 권한을 "항상 허용"으로 두어야 무인 진행된다. 크롬이 켜져 있고 해당 사이트 로그인(OTP)이 살아 있어야 한다. 두 사이트의 세션은 **따로 만료된다**(2026-10-08 실측: IMS 는 살아 있고 ECM 만 401).

1. claude-in-chrome 도구를 한 번에 로드(`tabs_context_mcp, navigate, javascript_tool, get_page_text, tabs_close_mcp`).
2. `navigate` → 사이트 루트, 2~3초 대기.
3. 세션 검사 (`javascript_tool`):
   - ECM: `fetch('/rest/api/user/current')` → `type` 이 `known`
   - IMS: `fetch('/rest/api/2/myself')` → HTTP 200 과 `displayName`
   - 실패(401/로그인 페이지로 이동)면 그 사이트만 멈추고 "크롬에서 eCoDY-ECM(또는 IMS) 로그인(OTP) 후 다시 요청"을 안내한다. 다른 사이트 조사는 계속해도 된다.

## S1. 질문 분석

다음을 한 줄로 정리해 두고 쿼리 설계에 쓴다.

- **의도**: 설정·구현 방법 / 점검 규칙 이유 / 결함·공지 여부 / 보고 이력·수정 버전 / API·사양 / 도구 사용법 / 일정·릴리즈
- **식별자** (있으면 최우선): `IA-087`, `VC-034`, `CPINFO-3469`, `MCP0806-298`, `CPDLV-503`, `UPD_TAR_02054`, `SAFERTE_ERR_0329`, `NRC 22`
- **심볼·파일명**: 생성 코드에 나오는 이름(`Os_GaaRamTaskStackSize0`, `Os_Cfg.c`)은 IMS 에서 가장 정확한 검색어다
- **모듈 약어**: 한글 표현을 약어로 — `references/ecm-query-guide.md` §3 용어 사전
- **R버전 / MCU / 모듈 버전**: 우리 과제 버전은 저장소의 `Static_Code/Modules/<모듈>/*.ver` 로 확인할 수 있다(예 psu_master `Os_CYTxxx_R44-2.1.0.0_HF1`)

질문이 너무 넓으면(예: "Dcm 알려줘") 되묻지 말고 UM `Dcm - 0~5` 목차 수준으로 답한 뒤 좁혀 달라고 제안한다.

## S2. 쿼리 설계

- **ECM**: `references/ecm-query-guide.md` 를 따른다. 식별자 제목 일치 → 제목 키워드 조합 → 본문 구문 → 의도 그룹 한정 → `siteSearch` 광역. 공지 확인 쿼리(`title ~ "공지"` + 모듈)는 거의 항상 하나 넣는다.
- **IMS**: `references/ims-query-guide.md` 를 따른다. 심볼·파일명 → 한글 현상 → 영문 현상 → 릴리즈 노트(`summary ~ "<모듈>_<MCU>*"`) → 수평전개 → 우리 과제 프로젝트 한정. 릴리즈 노트는 영문·한글 병기라 두 언어 쿼리를 다 넣는다.

## S3. 후보 수집

| 사이트 | 스크립트 | 치환 | 출력 형식 |
| --- | --- | --- | --- |
| ECM | `scripts/ecm_search.js` | `__QUERIES__` = `[{tag, cql}]` | `순번\|pageId\|그룹\|하위분류\|최종수정\|버전\|적중쿼리\|제목` |
| IMS | `scripts/ims_search.js` | `__QUERIES__` = `[{tag, jql}]` | `순번\|키\|프로젝트\|유형\|상태\|생성\|갱신\|댓글수\|적중쿼리\|보고자\|제목` |

스크립트 내용을 치환해 `javascript_tool` 로 실행하고 곧바로 `get_page_text` 로 읽는다(반환값은 잘리고 필터에 막히므로 DOM 에 펼친다 — 실측). `#LOG` 줄에서 쿼리별 건수를 먼저 본다. 여러 쿼리에 적중한 것이 위로 온다.

- 전체 0~2건이면 조건을 완화해 한 번 더: MCU·R버전 제거 → 영문↔한글 교체 → 단일 키워드 → 광역.
- `HTTP 400` 은 쿼리 문법 오류다. 그 쿼리만 고쳐 다시 돈다.

## S4. 선별

| 의도 | 우선 |
| --- | --- |
| 설정·구현 방법 | ECM: SAG → UM `Configuration Guide` → IM |
| 점검에 왜 걸리나 | ECM: IA / VC → 연결된 SAG·공지 |
| 결함·주의사항 | IMS: 수평전개(CPINFO 원본) → ECM: NOTICE → SAG → VC |
| 보고 이력·어느 버전에서 고쳐졌나 | IMS: 릴리즈 노트(`CP_ModuleRelease`) → 결함 하위작업 → 과제 문의 |
| 우리 과제에 내려온 안내 | IMS: 해당 과제 프로젝트(예 MCP0806) Delivery_Patch·Information |
| API·사양·제약 | ECM: UM (`API Reference`, `Limitations and Deviations`) |
| 도구 | ECM: CSTUDIO / etoolchain |
| 릴리즈·단종·일정 | ECM: NOTICE(Planning & Roadmap, Changes & Maintenance) → POLICY, IMS: 릴리즈 노트 |

목차 역할만 하는 ECM 상위 페이지, 같은 수평전개의 과제별 사본 여러 건은 근거로 중복 인용하지 않는다(원본 1건 + 우리 과제 사본 1건). 같은 주제의 R40·R44, 다른 MCU 릴리즈가 함께 나오면 **우리 MCU 에 해당하는지**를 반드시 구분한다.

## S5. 정독

| 사이트 | 스크립트 | 치환 |
| --- | --- | --- |
| ECM | `scripts/ecm_read.js` | `__IDS__` (5건 이하), `__MAX__` (기본 6000) |
| IMS | `scripts/ims_read.js` | `__KEYS__` (5건 이하), `__MAX__` (기본 8000, Delivery_Patch 티켓은 60000 정도) — 본문·댓글·첨부·연결·하위작업 + 변경 이력(첨부 추가·삭제, 상태, 담당자) |

`(이하 N자 생략)` 이 붙었는데 필요한 절이 뒤에 있으면 그 건만 `__MAX__` 를 늘려 다시 읽는다. 본문이 다른 문서·이슈(CPINFO, IM 링크, 연결 이슈·하위작업)를 참조하고 답에 필요하면 한 번 더 찾아 읽는다. IMS 릴리즈 노트는 개선 항목이 표로 여러 개다 — 질문과 관련된 항목의 **Target MCU · Detailed Changes · Dependent module version** 을 뽑는다.

## S6. 답변 형식

채팅으로 답한다. 과한 서식 없이, 아래 순서를 지킨다.

1. **결론** — 2~4문장. 각 주장 끝에 근거 번호 `[1]`.
2. **상세** — 설정 경로·파라미터·값·대상 MCU/R버전·수정 버전·주의 조건을 자료 기준으로. 문단을 옮겨 적지 않고 재서술한다(파라미터명·값·버전·식별자는 그대로).
3. **우리 과제 적용 여부** — 사용자의 과제(모듈 버전·MCU)를 알면 "해당/미해당/아직 미배포"를 한 줄로.
4. **⚠️ 관련 공지·주의** — 같은 모듈·MCU의 수평전개·공지·VC/IA 규칙이 있으면 한두 줄. 없으면 생략.
5. **근거** — 표: `번호 | 사이트·그룹 | 제목(링크) | 날짜`. 링크: ECM `https://ecody-ecm.autoever.com/pages/viewpage.action?pageId=<id>`, IMS `https://ecody-ims.autoever.com/browse/<KEY>`.
6. **확인 못 한 점** — 찾지 못한 부분, 세션 만료로 못 본 사이트, R버전·MCU가 달라 그대로 적용할지 불확실한 부분.

자료가 질문에 답하지 못하면 그렇게 말하고, 가장 가까운 자료와 찾아본 경로(쿼리 방향)를 알려준다. 일반 지식을 덧붙이려면 `(자료 외 일반 지식)` 이라고 분명히 구분한다. "오토에버에 문의하기 전 조사"였다면 마지막에 **문의할 필요가 있는지**와, 필요하면 문의에 넣을 핵심(현상·근거 이슈·질문)을 제안한다.

## S7. 정리

검색·정독 스크립트가 탭 DOM 을 덮어썼으므로, 이 스킬이 연 탭은 닫는다. 기존 탭을 썼다면 `navigate` 로 사이트 루트를 다시 연다. 로그인 대기 중이라 사용자가 그 탭을 써야 하면 열어 둔다고 말한다.

## 사이트 지도 (ECM)

| 그룹 | 위치 (mobilgene Classic FAQ 공간) | 규모 | 어떤 질문에 강한가 |
| --- | --- | --- | --- |
| NOTICE | Notice > 공지(舊 수평공지), Planning & Roadmap, Changes & Maintenance | 약 30 | 결함 수평전개, 단종, 릴리즈 계획, 지원 트랜시버 |
| POLICY | Policy | 약 30 | 입수물 점검, STR, 라이선스, 교육, Baseline Release |
| IM | 기술지원 지식공유 > IM | 약 800 | 모듈별 통합 매뉴얼, 필수 통합 점검 사항 |
| IA / VC | IM > Integration Auditor Guide / Validation Checker Guide | 각 약 85 | "이 설정이 점검에 걸리는 이유·조건·대상 MCU" |
| SAG | 기술지원 지식공유 > SAG (1.시스템 ~ 13.프로젝트 특화) | 약 960 | 실무 설정·구현 가이드, 문제 대응 |
| UM | Autosar Module User Manual > [R44] User Manual | 약 775 | 모듈 Overview·Limitations·Configuration Guide·API·Generator |
| CSTUDIO | mobilgene C Studio Manual | 약 60 | Installer, Features, CLI, Script, DBScriptGenerator, FAQ |
| ToU | Terms of Use | 소규모 | C-Studio 라이선스 요청·설치, Project Kickoff |
| OTHER | `FODM`(FoD Library), `msec`(HSM2·CIDS2·SFM 등), `etoolchain` | 소규모 | FoD 릴리즈, 보안 제품 FAQ, 계정·OTP |

공간 키: `mclassicfaq`, `FODM`, `msec`, `etoolchain`. IMS 프로젝트 지도는 `references/ims-query-guide.md` §1.
