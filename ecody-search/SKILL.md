---
name: ecody-search
description: 현대오토에버 eCoDY 두 사이트 — eCoDY-ECM(ecody-ecm.autoever.com, 가이드: mobilgene Classic FAQ의 공지·Policy·IM·SAG·IA/VC·R44 User Manual·C Studio 매뉴얼)과 eCoDY-IMS(ecody-ims.autoever.com, Jira: 모듈 릴리즈 노트·수평전개·Delivery_Patch·문의와 답변) — 를 CQL/JQL 다중 검색·정독해 근거 링크와 함께 답하는 읽기 전용 스킬. 첫 매개변수로 범위를 고른다 — ECM 이면 ECM 만, IMS 면 IMS 만, 없으면 둘 다. 두 사이트 모두 API 토큰(환경변수 ECODY_IMS_TOKEN·ECODY_ECM_TOKEN)으로 PC 에서 바로 조회하며, 토큰이 없거나 만료된 사이트만 크롬 연동(Claude in Chrome) 로그인 세션으로 폴백한다. 사용자가 "eCoDY에서 찾아줘", "ECM 검색", "IMS 검색", "IMS에 이런 이슈 있었나", "어느 버전에서 고쳐졌어", "릴리즈 노트 찾아줘", "수평전개 있었나", "모빌진 FAQ에 ○○ 있어?", "○○ 설정 방법 오토에버 가이드", "IA-087 내용", "CPINFO-4186 내용", "CanSM Bus-Off 설정 어떻게 하라고 돼 있지", "C Studio CLI 사용법", "오토에버에 문의하기 전에 조사해줘" 등을 말하거나, mobilgene/AUTOSAR BSW·MCAL·FBL·Fota·진단·생성기 동작을 오토에버 공식 자료 기준으로 확인하려 하면 반드시 이 스킬을 사용하라. "모빌진 기준", "오토에버 가이드 기준"이 붙은 일반 AUTOSAR 질문도 해당한다. ECM 일일 수집은 ecody-ecm-monitor, Delivery_Patch 적용과 IMS 댓글은 swp-delivery-patch 담당. (구 이름: ecody-ecm-search)
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

- 두 사이트 모두 **조회(GET)만** 한다. 스크립트(`ims_api.py`·`ecm_api.py`·`_ecody_common.py`, `*_search.js`, `*_read.js`)는 GET 이외 요청을 스스로 차단하는 가드를 품고 있으며, 스크립트 밖에서 임의의 `fetch`·폼 제출·편집/삭제/댓글/좋아요/감시/상태 변경 버튼 클릭을 하지 않는다.
- IMS 댓글은 HAE 로 나가는 외부 메시지다. 이 스킬은 쓰지 않는다 — 질문 초안이 필요하면 초안만 채팅으로 주고, 등록은 swp-delivery-patch 의 승인 절차를 따른다.
- 탭 DOM 덮어쓰기(검색·정독 결과 펼치기)는 내 브라우저 화면에만 적용되는 로컬 동작이다. 끝나면 탭을 닫거나 원복한다.
- 로그인·OTP·비밀번호는 입력하지 않는다. 토큰 값도 화면·대화·커밋에 출력하지 않는다.
- 접속 계정(토큰 소유자 또는 브라우저 로그인)이 사용자 본인 것이 아니면(공용 계정 등) 그 사실을 답변에 한 줄 남긴다 — 2026-11-04 실측: IMS·ECM 토큰 모두 사용자 본인이 아닌 공용 계정이다(계정명은 `check` 출력으로 확인한다).
- 결과를 Confluence 에 남기는 것은 사용자가 요청할 때만, `confluence-writing` 스킬 규약으로 한다.

## 전체 흐름

```
S0 접속 준비       범위 결정(ECM/IMS/둘 다) → 범위의 사이트만 토큰 check
S1 질문 분석       의도 · 키워드 · 식별자 · 모듈/MCU/버전 · 어느 사이트
S2 쿼리 설계       ECM CQL 4~8개 / IMS JQL 4~8개
S3 후보 수집       ecm_api.py search / ims_api.py search
S4 선별            의도-그룹 적합도로 3~6건씩
S5 정독            ecm_api.py read / ims_api.py read
S6 답변            형식대로 · 근거 링크 · 관련 공지 경고 · 우리 과제 적용 여부
S7 정리            토큰 모드면 할 것 없음 (크롬 폴백을 썼다면 탭 닫기)
```

## S0. 접속 준비

**두 사이트 모두 API 토큰이 기본이다** — 크롬·OTP 세션이 필요 없다. 토큰이 없거나 401 이면 그 사이트만 크롬으로 폴백한다.

| 사이트 | 기본 (토큰) | 폴백 (크롬) |
| --- | --- | --- |
| **IMS** | `scripts/ims_api.py` — 환경변수 `ECODY_IMS_TOKEN` | `ims_search.js` / `ims_read.js` |
| **ECM** | `scripts/ecm_api.py` — 환경변수 `ECODY_ECM_TOKEN` | `ecm_search.js` / `ecm_read.js` |

### 토큰 모드 (기본)

범위에 든 사이트만 확인한다.

```powershell
python <스킬폴더>\scripts\ims_api.py check
python <스킬폴더>\scripts\ecm_api.py check
```

- `..._CHECK OK ... : <계정명>` 이면 그대로 진행한다.
- `TOKEN_MISSING` 이면 `references/api-token.md` 의 발급·등록(`setx ECODY_<SITE>_TOKEN`)을 안내하고, 사용자가 원하면 그 자리에서 크롬 폴백으로 진행한다.
- `setx` 직후라 이미 떠 있는 세션이 환경변수를 못 읽으면 명령 앞에 붙인다: `$env:ECODY_ECM_TOKEN=[Environment]::GetEnvironmentVariable('ECODY_ECM_TOKEN','User');`
- `HTTP 401` 은 토큰 만료·무효다(재발급 — 현재 발급분 만료는 `references/api-token.md`). `HTTP 403`·네트워크 오류는 사내망·프록시를 확인한다(`ECODY_<SITE>_NOPROXY=1`, `ECODY_<SITE>_INSECURE=1`).
- 두 사이트 토큰은 **따로 만료된다**. 한쪽이 막히면 다른 쪽 조사는 계속하고, 막힌 쪽은 "확인 못 한 점"에 남긴다.

### 크롬 폴백

> ⚠️ **실측**: `navigate`는 `browser_batch` 안에서 호출하면 사이트 권한 확인에 걸려 멈춘다 — **항상 단독 호출**한다. Claude in Chrome 확장에서 사이트 권한을 "항상 허용"으로 두어야 무인 진행된다. 크롬 로그인(OTP) 세션도 두 사이트가 따로 만료된다(2026-10-08 실측: IMS 는 살아 있고 ECM 만 401).

1. claude-in-chrome 도구를 한 번에 로드(`tabs_context_mcp, navigate, javascript_tool, get_page_text, tabs_close_mcp`). **토큰 모드로 끝나면 크롬 도구를 로드하지 않는다.**
2. `navigate` → 사이트 루트, 2~3초 대기.
3. 세션 검사 (`javascript_tool`): ECM 은 `fetch('/rest/api/user/current')` → `type` 이 `known`, IMS 는 `fetch('/rest/api/2/myself')` → HTTP 200.
   - 실패하면 그 사이트만 멈추고 "크롬에서 로그인(OTP) 후 다시 요청"을 안내한다. 다른 사이트 조사는 계속한다.

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

| 사이트 | 실행 (기본) | 입력 | 출력 형식 |
| --- | --- | --- | --- |
| **IMS** | `python scripts\ims_api.py search --queries <q.json> [--per-query 30] --out <파일>` | 스크래치패드에 `[{"tag","jql"}]` JSON | `순번\|키\|프로젝트\|유형\|상태\|생성\|갱신\|댓글수\|적중쿼리\|보고자\|제목` |
| **ECM** | `python scripts\ecm_api.py search --queries <q.json> [--per-query 25] --out <파일>` | 스크래치패드에 `[{"tag","cql"}]` JSON | `순번\|pageId\|그룹\|하위분류\|최종수정(KST)\|버전\|적중쿼리\|제목` |
| 폴백 | `scripts/ims_search.js` · `ecm_search.js` + `javascript_tool` | `__QUERIES__` = `[{tag, jql}]` / `[{tag, cql}]` | 같음 |

- 토큰 모드: JSON 안의 큰따옴표는 `\"` 로 적는다. `--out` 으로 스크래치패드 파일에 받아 그대로 읽는다.
- 크롬 폴백: 스크립트 내용을 치환해 `javascript_tool` 로 실행하고 곧바로 `get_page_text` 로 읽는다(반환값은 잘리고 필터에 막히므로 DOM 에 펼친다 — 실측).
- 출력 형식이 양쪽 모드에서 같아 S4 이후는 동일하다. `#LOG` 줄에서 쿼리별 건수를 먼저 본다. 여러 쿼리에 적중한 것이 위로 온다.
- ECM 그룹 칸(IA/VC/NOTICE/POLICY/IM/SAG/UM/CSTUDIO/ToU)은 조상 페이지 제목으로 정한다. 트리 제목에 이모지·번호 접두사가 붙어 있어 스크립트가 앞쪽 비문자를 떼고 비교한다(2026-11-04 실측 트리 기준).

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

| 사이트 | 실행 (기본) | 입력 |
| --- | --- | --- |
| **IMS** | `python scripts\ims_api.py read <KEY...> [--max 8000] --out <파일>` | 5건 이하. Delivery_Patch 티켓은 `--max 60000` 정도 — 본문·댓글·첨부·연결·하위작업 + 변경 이력(첨부 추가·삭제, 상태, 담당자) |
| **ECM** | `python scripts\ecm_api.py read <pageId...> [--max 6000] --out <파일>` | 5건 이하 — 본문·경로(조상)·문서첨부(이미지 제외)·버전·최종수정자 |
| 폴백 | `scripts/ims_read.js` · `ecm_read.js` + `javascript_tool` | `__KEYS__`/`__IDS__` (5건 이하), `__MAX__` (같은 기준) |

`(이하 N자 생략)` 이 붙었는데 필요한 절이 뒤에 있으면 그 건만 `--max`(크롬 폴백은 `__MAX__`)를 늘려 다시 읽는다. 본문이 다른 문서·이슈(CPINFO, IM 링크, 연결 이슈·하위작업)를 참조하고 답에 필요하면 한 번 더 찾아 읽는다. IMS 릴리즈 노트는 개선 항목이 표로 여러 개다 — 질문과 관련된 항목의 **Target MCU · Detailed Changes · Dependent module version** 을 뽑는다.

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

토큰 모드로만 봤으면 정리할 것이 없다(스크래치패드 파일은 세션용이라 둔다).

크롬 폴백을 썼다면: 검색·정독 스크립트가 탭 DOM 을 덮어썼으므로 이 스킬이 연 탭은 닫는다. 기존 탭을 썼다면 `navigate` 로 사이트 루트를 다시 연다. 로그인 대기 중이라 사용자가 그 탭을 써야 하면 열어 둔다고 말한다.

## 사이트 지도 (ECM)

2026-11-04 실측 최상위 7개: `📢 Notice` · `🏁 Terms of Use (ToU)` · `🔧 Technical Reference` · `📝Autosar Module User Manual` · `📚mobilgene Tool Manual` · `✅ Quality & Verification` · `파일 목록`. 제목에 이모지·번호 접두사가 붙으므로 검색은 조상 ID 대신 제목 관례로 한정한다(`references/ecm-query-guide.md` §1).

| 그룹 | 위치 (mobilgene Classic FAQ 공간) | 규모 | 어떤 질문에 강한가 |
| --- | --- | --- | --- |
| NOTICE | 📢 Notice > [Notice 1] Announcement(舊 수평공지) ~ [Notice 5] Phase-Out Plan | 약 30 | 결함 수평전개, 단종, 릴리즈 계획, 지원 트랜시버 |
| POLICY | ✅ Quality & Verification > [Q&V 1] SWP Technical Review(STR) … | 약 30 | 입수물 점검, STR, 라이선스, 교육, Baseline Release |
| IM | 🔧 Technical Reference > 1️⃣ IM (Integration Manual) | 약 800 | 모듈별 통합 매뉴얼, 필수 통합 점검 사항 |
| IA / VC | ✅ Quality & Verification > Integration Auditor Guide / 필수 통합 점검 (구) | 각 약 85 | "이 설정이 점검에 걸리는 이유·조건·대상 MCU" |
| SAG | 🔧 Technical Reference > 2️⃣ SAG (SWP Application Guide) (1.시스템 ~ 13.프로젝트 특화) | 약 960 | 실무 설정·구현 가이드, 문제 대응 |
| UM | 📝Autosar Module User Manual > [R44] User Manual | 약 775 | 모듈 Overview·Limitations·Configuration Guide·API·Generator |
| CSTUDIO | 📚mobilgene Tool Manual > [C Studio] …, [UM] Scons/Gentool/Build | 약 60 | Installer, Features, CLI, Script, C Compare, DBScriptGenerator, FAQ |
| ToU | 🏁 Terms of Use (ToU) | 소규모 | C-Studio 라이선스 요청·설치, Project Kickoff |
| OTHER | `FODM`(FoD Library), `msec`(HSM2·CIDS2·SFM 등), `etoolchain` | 소규모 | FoD 릴리즈, 보안 제품 FAQ, 계정·OTP |

공간 키: `mclassicfaq`, `FODM`, `msec`, `etoolchain`. IMS 프로젝트 지도는 `references/ims-query-guide.md` §1.
