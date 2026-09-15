---
name: ecody-ecm-search
description: 현대오토에버 eCoDY-ECM(ecody-ecm.autoever.com — mobilgene Classic FAQ의 공지·Policy·IM·SAG·IA/VC 점검규칙·R44 User Manual·C Studio 매뉴얼, FoD·m.Security 채널)에서 사용자가 묻는 기술 정보를 CQL 다중 검색으로 찾아 관련 문서를 정독한 뒤, 근거 링크와 함께 답변으로 정리해 주는 스킬. 크롬 연동(Claude in Chrome) 로그인 세션을 사용한다. 사용자가 "eCoDY에서 찾아줘", "ECM 검색", "모빌진 FAQ에 ○○ 있어?", "오토에버 기술지원 사이트에서 ○○ 설정 방법", "mobilgene Classic ○○ 가이드", "IA-087 내용 알려줘", "CYT Wdg 리셋 관련 공지 있었나", "CanSM Bus-Off 설정 어떻게 하라고 돼 있지", "UPD_TAR_02054 대응 가이드", "C Studio CLI 사용법" 등을 언급하거나, mobilgene/AUTOSAR BSW 모듈·MCAL·FBL·Fota·진단 설정 질문을 오토에버 공식 가이드 기준으로 확인하려 하면 반드시 이 스킬을 사용하라. 일반 AUTOSAR 개념 질문도 "모빌진 기준", "오토에버 가이드 기준"이 붙으면 이 스킬이다. 매일 변경분을 수집해 Confluence에 누적하는 일은 ecody-ecm-monitor 담당이다.
---

# eCoDY-ECM 검색·답변

사용자의 질문을 **오토에버 공식 기술지원 문서 기준**으로 답한다. 핵심은 세 가지다: 여러 각도로 검색해 후보를 넓게 잡고, 상위 문서를 **실제로 읽고**, 답의 각 주장에 **근거 문서 링크**를 붙인다. 문서에 없는 내용을 일반 지식으로 메우지 않는다.


## 권한 원칙 — 읽기 전용

- eCoDY-ECM에는 **조회(GET)만** 한다. 스크립트는 GET 이외 요청을 스스로 차단하는 가드를 품고 있으며, 스크립트 밖에서 임의의 `fetch`·폼 제출·편집/삭제/댓글/좋아요/감시 버튼 클릭을 하지 않는다. (2026-09-15 실측: 현재 로그인 계정은 페이지 권한이 `read`뿐이라 서버에서도 쓰기가 거부된다 — 그래도 계정 권한이 바뀔 수 있으므로 스킬이 먼저 지킨다.)
- 탭 DOM 덮어쓰기(dump·read)는 내 브라우저 화면에만 적용되는 로컬 동작이며 서버 데이터와 무관하다. 끝나면 `index.action`으로 다시 열어 원복한다.
- 로그인·OTP·비밀번호는 입력하지 않는다.
- 이 스킬 자체는 어디에도 쓰지 않는다. 결과를 Confluence에 남기는 것은 사용자가 요청할 때만, `confluence-writing` 스킬 규약으로 한다(발행 위치만 확인하면 된다 — 사내 Confluence는 삭제 외 작업이 허용되어 있다).

## 사이트 지도 (검색 설계에 필요)

| 그룹 | 위치 (mobilgene Classic FAQ 공간) | 규모 | 어떤 질문에 강한가 |
| --- | --- | --- | --- |
| NOTICE | Notice > 공지(舊 수평공지), Planning & Roadmap, Changes & Maintenance | 약 30 | 결함 수평전개, 단종, 릴리즈 계획, 지원 트랜시버 |
| POLICY | Policy | 약 30 | 입수물 점검, STR, 라이선스, 교육, Baseline Release |
| IM | 기술지원 지식공유 > IM | 약 800 | 모듈별 통합 매뉴얼, 필수 통합 점검 사항 |
| IA / VC | IM > Integration Auditor Guide / Validation Checker Guide | 각 약 85 | "이 설정이 점검에 걸리는 이유·조건·대상 MCU" |
| SAG | 기술지원 지식공유 > SAG (1.시스템 ~ 13.프로젝트 특화) | 약 960 | 실무 설정·구현 가이드, 문제 대응 |
| UM | Autosar Module User Manual > [R44] User Manual | 약 775 | 모듈 Overview·Limitations·Configuration Guide·API·Generator |
| CSTUDIO | mobilgene C Studio Manual | 약 60 | Installer, Features, CLI, Script, DBScriptGenerator, FAQ |
| OTHER | `FODM`(FoD Library), `msec`(HSM2·CIDS2·SFM 등), `etoolchain` | 소규모 | FoD 릴리즈, 보안 제품 FAQ, 계정·OTP |

공간 키: `mclassicfaq`, `FODM`, `msec`, `etoolchain`. 스페이스 루트의 `v1.0.0.0` 같은 페이지는 UM 버전별 사본이다.

## 전체 흐름

```
S0 브라우저·세션   탭 확보 → 접속 → 세션 검사
S1 질문 분석       의도 · 키워드 · 식별자 · R버전 · MCU
S2 쿼리 설계       4~8개 CQL (references/query-guide.md)
S3 후보 수집       search.js → get_page_text
S4 선별            의도-그룹 적합도로 3~6건
S5 정독            read_body.js → get_page_text
S6 답변            형식대로 · 근거 링크 · 관련 공지 경고
S7 정리            탭 원복
```

## S0. 브라우저·세션

> ⚠️ **무인 실행 전제 (실측)**: `navigate`는 `browser_batch` 안에서 호출하면 사이트 권한 확인에 걸려 멈춘다 — **항상 단독 호출**한다. 또 실행이 권한 팝업에서 서지 않도록 Claude in Chrome 확장에서 `ecody-ecm.autoever.com` 사이트 권한을 "항상 허용"으로 두어야 한다. 크롬이 켜져 있고 eCoDY-ECM 로그인(OTP)이 살아 있어야 한다.

1. `tool_search`로 claude-in-chrome 도구를 불러오고 `tabs_context_mcp(createIfEmpty=true)`.
2. `navigate` → `https://ecody-ecm.autoever.com/`, 3초 대기.
3. `javascript_tool`: `fetch('/rest/api/user/current')`로 `type`이 `known`인지 확인. 아니면 멈추고 사용자에게 "크롬에서 eCoDY-ECM 로그인(OTP) 후 다시 요청"을 안내한다. 로그인 정보를 대신 입력하지 않는다.

## S1. 질문 분석

다음을 뽑아 한 줄로 정리해 두고 쿼리 설계에 쓴다.

- **의도**: 설정·구현 방법 / 점검 규칙 이유 / 결함·공지 여부 / API·사양 / 도구 사용법 / 일정·릴리즈
- **식별자** (있으면 최우선): `IA-087`, `VC-034`, `CPINFO-3469`, `CPDLV-503`, `CP44STD-44376`, `UPD_TAR_02054`, `NRC 22`, `ES95489`
- **모듈 약어**: 한글 표현을 약어로 바꾼다 — `references/query-guide.md` §용어 사전
- **R버전**: R40 / R44 / R4X. 질문에 없으면 둘 다 찾되 답에서 구분한다
- **MCU**: CYTxxx, TC3xx, S32K3xx, S32G2x, F1KM, U2A, SPC58x, RCAR U5L 등

질문이 너무 넓어 쿼리를 못 세우면(예: "Dcm 알려줘") 되묻지 말고 UM `Dcm - 0~5` 목차 수준으로 답한 뒤 좁혀 달라고 제안한다.

## S2. 쿼리 설계

**`references/query-guide.md`를 읽고 따른다.** 요지: 식별자 제목 일치 → 제목 키워드 조합 → 본문 구문 → 의도에 맞는 그룹 한정 → `siteSearch` 광역, 이렇게 계층을 섞어 4~8개를 만든다. 공지 확인 쿼리(`title ~ "공지"` + 모듈)는 거의 항상 하나 넣는다 — 설정 방법을 물어도 관련 결함 공지가 있으면 반드시 알려야 하기 때문이다.

## S3. 후보 수집

`scripts/search.js`의 `__QUERIES__`를 치환해 실행하고 곧바로 `get_page_text`로 읽는다. (`javascript_tool` 반환값은 수천 자에서 잘리므로 DOM에 펼쳐 읽는다 — 실측.)

출력: `#LOG`(쿼리별 건수), 이어서 `순번|pageId|그룹|하위분류|최종수정(KST)|버전|적중쿼리|제목`. 여러 쿼리에 적중한 문서가 위로 온다.

- 전체 0~2건이면 조건을 완화해 한 번 더: MCU·R버전 제거 → 영문↔한글 교체 → `text ~` 단일 키워드 → `siteSearch`.
- 쿼리 하나가 `HTTP 400`이면 CQL 문법 오류다. 따옴표·와일드카드 위치를 고쳐 그 쿼리만 다시 돈다.

## S4. 선별

의도-그룹 적합도를 먼저 보고, 그다음 적중 수·최신성으로 3~6건을 고른다.

| 의도 | 우선 그룹 |
| --- | --- |
| 설정·구현 방법 | SAG → UM `Configuration Guide` → IM |
| 점검에 왜 걸리나 | IA / VC → 연결된 SAG·공지 |
| 결함·주의사항 | NOTICE → SAG → VC |
| API·사양·제약 | UM (`API Reference`, `Limitations and Deviations`) |
| 도구 | CSTUDIO / etoolchain |
| 릴리즈·단종·일정 | NOTICE(Planning & Roadmap, Changes & Maintenance) → POLICY |

`Integration Auditor Guide`, `9. WatchDog`처럼 **목차 역할만 하는 상위 페이지**는 답의 근거로 쓰지 않는다(찾아갈 위치로만 언급). 같은 주제의 R40·R44 문서가 둘 다 있으면 둘 다 고른다.

## S5. 정독

`scripts/read_body.js`의 `__IDS__`(5건 이하씩)와 `__MAX__`(기본 6000)를 치환해 실행하고 `get_page_text`로 읽는다. 문서에 `(이하 N자 생략)`이 붙었는데 필요한 절이 뒤에 있으면 그 문서만 `__MAX__`를 늘려 다시 읽는다. 본문에 다른 문서(CPINFO 공지, 다른 SAG)를 참조하고 그게 답에 필요하면 제목으로 한 번 더 찾아 읽는다.

## S6. 답변 형식

채팅으로 답한다. 과한 서식 없이, 아래 순서를 지킨다.

1. **결론** — 질문에 대한 답을 2~4문장. 각 주장 끝에 근거 번호 `[1]`.
2. **상세** — 필요한 만큼. 설정 경로·파라미터·값·대상 MCU/R버전·주의 조건을 문서 기준으로. 절차는 번호 목록 가능. 문서 문단을 옮겨 적지 않고 재서술한다(파라미터명·값·버전은 그대로).
3. **⚠️ 관련 공지·주의** — 같은 모듈·MCU의 공지나 VC/IA 규칙이 있으면 반드시 한두 줄. 없으면 생략.
4. **근거 문서** — 표: `번호 | 그룹 | 제목(링크) | 최종수정`. 링크 `https://ecody-ecm.autoever.com/pages/viewpage.action?pageId=<id>`.
5. **확인 못 한 점** — 문서에서 찾지 못한 부분, R버전·MCU가 달라 그대로 적용할지 불확실한 부분.

문서가 질문에 답하지 못하면 그렇게 말하고, 가장 가까운 문서와 찾아본 경로(쿼리 방향)를 알려준다. 일반 AUTOSAR 지식을 덧붙이려면 `(문서 외 일반 지식)`이라고 분명히 구분한다.

사용자가 결과를 Confluence에 정리해 달라고 하면 그때 `confluence-writing` 스킬로 넘긴다(발행 위치는 사용자에게 확인). 기본은 채팅 답변만.

## S7. 정리

search.js / read_body.js가 탭 DOM을 덮어썼으므로 `navigate`로 `https://ecody-ecm.autoever.com/index.action`를 다시 연다. 이 스킬이 새로 연 탭이면 닫는다.
