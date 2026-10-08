---
name: swp-delivery-patch
description: 현대오토에버(HAE) mobilgene Classic(R44/R4x) SWP Delivery_Patch 를 당사 제어기 프로젝트(FBL·APP, 차종·제어기 무관)에 적용하는 전 과정 — eCoDY-IMS 티켓 수집, 배포본 판별, HAE 이전/현재 형상과 당사 설정의 3-way 판정(그대로 복사해도 되는지, 당사 전용 설정은 어떻게 반영할지), 적용, 정적 검수, Jenkins 빌드 결과 검수(생성물 diff·RAM/ROM), 버전업, 실기 검증 순서, Redmine·IMS·Confluence 기록, PR 까지 — 을 안내하고 반복 작업은 동봉 스크립트로 처리하는 스킬. 사용자가 "Delivery_Patch", "SWP 패치", "패치 딜리버리", "MCP0806-xxx 패치 적용", "eCoDY-IMS 패치 티켓", "모듈 패치 적용해줘", "HAE 패치 받았어", "v3.0.xx 패치", "FBL 패치", "APP 패치", "재배포본", "배포본 비교", "패치 검수", "HAE 형상 그대로 복사해도 돼?", "당사 설정이랑 충돌", "IMS 에 질문 댓글", "버전업", "JENKINS_BUILD_TARGET ALL" 등을 말하거나, HAE 가 배포한 모듈·설정 변경을 당사 저장소에 반영하려는 의도를 보이면 반드시 이 스킬을 사용하라. Claude Code CLI(사내망, 사용자 PC) 전용. 개별 도구 작업은 담당 스킬로 넘긴다 — Redmine 쓰기는 redmine-issue, eCoDY-ECM 가이드 검색은 ecody-search, 보드 라이팅은 cvd-project, CAN 확인은 can-bench-setup / canoe-project-setup, Confluence 규약은 confluence-writing, 작업 브랜치·Jenkins Job 신설은 gitea-jenkins-setup.
---

# SWP Delivery_Patch 적용

HAE 가 eCoDY-IMS 로 배포한 SWP 패치를 당사 제어기 프로젝트에 적용하고, 그 결과를 검수·기록하는 절차다. 차종·제어기와 FBL / APP 에 공통으로 쓰고, 프로젝트마다 다른 값(저장소, Job, 버전 위치, 당사 수정 파일)은 프로젝트 프로필에 둔다.

이 업무에서 사고가 나는 지점은 거의 정해져 있다. **HAE 참고 설정을 통째로 복사해 당사 전용 설정을 덮는 것**, 재배포·재가이드를 놓치는 것, 버전·산출물명 위치 하나를 빠뜨리는 것, 확인되지 않은 것을 확인된 것처럼 기록하는 것이다. 절차는 이 네 가지를 막도록 짜여 있다.

## 기본 원칙

1. **출발점은 eCoDY-IMS 티켓이다.** 본문·댓글 전체·첨부·변경 이력과 연결된 수평전개 티켓을 읽고 요청 항목을 뽑는다. 다른 사람이 같은 패치를 먼저 했더라도(Redmine 일감, Gitea 브랜치) 그것은 참고 자료일 뿐이고, 판단 기준은 항상 HAE 원본(IMS 안내·배포본·IM)이다. 남의 적용본에는 그 차종 고유 설정이 섞여 있기 때문이다.
2. **HAE 참고 설정은 "참고용"이다.** 배포본 안내문 자체가 ".arxml 은 설정 변경 사항 및 Validation Checker 적용을 위한 참고용"이라고 적는다. 파일을 통째로 복사하지 않고, 3-way 판정에서 "복사 가능"으로 나온 항목만 반영한다.
3. **모르는 것은 추정하지 않는다.** HAE 안내가 애매하거나 당사 설정과 충돌하면 사용자에게 판단을 묻고, 사용자가 원하면 IMS 질문 댓글로 HAE 에 확인한다.
4. **외부에 쓰는 일은 모두 미리보기 → 승인 → 실행이다.** IMS 댓글, Redmine, Confluence, git commit / push, 보드 라이팅, CAN 송신이 해당한다. 특히 push 는 Jenkins 빌드를 바로 일으키고 IMS 댓글은 HAE 로 나가는 메시지라서, 한 번 승인이 다음 행동으로 이어지지 않는다. 커밋·push 는 사용자가 지시할 때만 하고 먼저 제안하지 않는다.
5. **확인한 것과 하지 않은 것을 구분해 보고한다.** 빌드 성공은 실기 검증이 아니고, 정적 검수는 동작 검증이 아니다.

## 실행 환경

- Claude Code CLI(사용자 PC, 사내망). Redmine·Gitea·Jenkins 가 사설망에 있다.
- eCoDY-IMS(HAE Jira, `ecody-ims.autoever.com`)·eCoDY-ECM 은 **Claude in Chrome** 의 로그인 세션으로 읽고 쓴다. 사용법과 함정은 `references/ims-workflow.md`. 당사 Jira/Confluence(mobaseasec)는 Atlassian MCP 로 연결돼 있지만 HAE IMS 는 아니다.
  - 나중에 IMS 가 MCP 로 연결되면 `references/ims-workflow.md` 의 "MCP 연결 시" 절을 따른다(조회·댓글 도구 대응표). 승인 규칙은 같다.
- Jenkins API: 환경변수 `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`. Redmine: `REDMINE_URL`, `REDMINE_API_KEY`(redmine-issue 스킬).
- 스크립트는 이 스킬 폴더의 `scripts/` 에 있고 파이썬 표준 라이브러리만 쓴다(`python <스킬폴더>/scripts/<이름>.py -h` 로 사용법). 출력은 UTF-8 로 고정돼 있다. 한글 경로 인자는 PowerShell 에서 실행하면 안전하다. 긴 출력은 파일로 받아 필요한 줄만 본다.

## 전체 흐름

```
S0  프로젝트 프로필        projects/<프로젝트>.md 로드, 없으면 저장소 조사로 초안
S1  IMS 수집              티켓·댓글·첨부·이력·수평전개 → 요청 항목 목록
S2  가이드 정독            IM / SAG / IA·VC (ecody-search)
S3  선행 작업 조회 (선택)   같은 패치의 다른 일감·브랜치 → 참고 목록
S4  일감·문서              Redmine 일감 본문, Confluence 분석 페이지
S5  배포본 판별            유효 배포본, HAE 이전(Prev)/현재(Cur) 기준 형상
S6  3-way 판정            Prev / Cur / Ours → 판정표 (핵심)
S7  IMS 질문 (필요 시)      초안 → 승인 → 등록 → 답변 반영
S8  적용                  모듈 교체, ARXML 줄 단위, usercode 3-way, 버전업
S9  정적 검수              Cur 재대조, 심볼·매크로, Validation 사전 점검, 버전 잔존
S10 빌드·빌드 검수          (지시 시) commit/push → Jenkins → 생성물 diff, RAM/ROM
S11 기록                  Redmine 코멘트: 요청 → 처리 → 빌드
S12 실기                  ALL 전환 → 라이팅 → CAN → 고유 시험 → 서명 → H-OTA → CURRENT 복귀
S13 마무리                PR, IMS·Redmine 상태
```

사용자는 대개 중간 단계에서 부른다("배포본 비교해줘", "검수해줘"). 그때는 앞 단계 산출물이 있는지 확인하고(요청 항목 목록, 판정표), 없으면 필요한 만큼만 앞 단계를 빠르게 수행한다.

## S0. 프로젝트 프로필

`references/projects/` 에서 대상 프로젝트 파일을 찾는다(예: `he1i_psu.md`). 프로필에는 FBL / APP 저장소·작업 브랜치·PR 대상, Jenkins Job, 버전·산출물명 위치, 당사가 수정한 HAE 파일 목록, 실기 기준값이 있다.

없으면 `references/projects/_template.md` 를 복사해 저장소를 조사하며 채운다. 조사로 알 수 없는 것(PR 대상, 검토자, 실기 장비)만 사용자에게 한 번에 묻는다. 새 프로필은 사용자 확인 후 저장한다 — 다음 사람이 그대로 쓰기 때문이다.

## S1. eCoDY-IMS 수집

`references/ims-workflow.md` 의 방법으로 패치 티켓 전체를 읽는다. 놓치기 쉬운 것:

- **재배포·안내 개정.** 같은 티켓에 배포본이 두 번 이상 올라오거나, 설정변경 안내 댓글이 다시 달리거나, HAE 가 이전 파일·댓글을 삭제한다. 변경 이력(changelog)과 첨부 날짜를 함께 본다.
- **harmonize 필요 모듈** 표기는 개정 때 바뀐다(예: "해당없음" → "EcuM, Rte").
- **연결된 수평전개 티켓**의 결함 내용, 적용 대상 조건, 당사 회신(적용/미적용 사유). 이것이 "왜 이 패치를 하는가"와 실기 검증 항목의 근거다.
- **당사 담당자의 문의와 HAE 답변.** 답변이 안내문을 사실상 바꾼다(예: "PFee 미설정이면 PMem_Driver 추가 불필요").
- 권한 없음으로 열리지 않는 가이드 링크 — 기록해 두고, 다른 링크로 재전달됐는지 찾는다.

산출물: **요청 항목 목록**(항목 / 출처 댓글·날짜 / 필수·참고 구분). 이후 판정표의 행이 된다.

## S2. 가이드 정독

요청 항목마다 연결된 IM 절, IA/VC 규칙, SAG 를 ecody-search 스킬로 읽는다. 특히 확인할 것:

- 모듈 버전별 변경사항 절의 **의존성**과 **신규 Validation**(예: Dcm HF4 의 ERR053296~). 신규 Validation 은 S9 에서 당사 설정을 미리 점검한다.
- IM 의 표준 설정(예: SCons InputFilesList 목록) — HAE 참고 설정과 IM 이 다르면 IM 을 따르되 기록한다.
- 이미 더 최신 버전(예: HF5)이 나와 있는지 — 범위 밖이면 기록만 한다.

## S3. 선행 작업 조회 (선택)

같은 패치를 다른 차종에 먼저 적용한 Redmine 일감이나 Gitea 브랜치가 있으면 찾아 목록에 올린다. 쓸모는 "어떤 파일이 바뀌는지 미리 보기", "그쪽에서 HAE 에 물어 받은 답변"이다. 그대로 이식하지 않는다 — 그 차종의 고유 설정과 Harmonize 부산물이 섞여 있다. 이식할 때도 S6 판정을 거친다.

## S4. 일감·문서

Redmine 일감 본문은 `references/templates.md` 의 표준 구성(목적 / 업무 내용 / 검증 계획 / 참고 / 검색 태그)으로 쓰고, redmine-issue 스킬의 미리보기 → 승인 규칙으로 등록·갱신한다. 일감 상태 전이 규칙이 프로젝트 프로필에 있으면 따른다.

분석이 길면 Confluence 분석 페이지를 confluence-writing 규약으로 만든다(부모 위치는 프로필 또는 사용자 확인).

## S5. 배포본 판별

1. 유효 배포본을 정한다. 재배포가 있으면 `scripts/zip_crc_compare.py` 로 이전본과 비교해 "새 본만 쓰면 되는지"를 근거와 함께 판정한다. 비밀번호가 걸린 zip 도 목록의 CRC 로 비교된다(압축 해제 불필요).
2. **HAE 기준 형상 두 벌을 확보한다.** Prev(HAE 의 직전 버전 형상)와 Cur(이번 버전 형상).
   - 배포본에 `VersionComparison/PreviousVersion`·`CurrentVersion` 이 있으면 그대로 쓴다. 이 형식에서는 **모듈 본체도 `CurrentVersion/Static_Code/Modules/` 아래**에 있다(최상위에 `Static_Code` 가 없다고 모듈 교체가 없는 패치로 오판하지 않는다). 판정표에는 모듈 교체 행을 항상 첫 행으로 둔다.
   - 없으면 Cur 는 배포본의 참고 설정, Prev 는 직전 회차 IMS 티켓의 배포본에서 가져온다. 둘 다 없으면 3-way 대신 2-way(Cur vs Ours)로 하되, 판정표에 "Prev 없음 — 당사 전용 여부 수동 확인"을 표시하고 git 이력으로 보완한다.
3. 배포본의 Doc(ReleaseNote, ModuleList, Module Change List)과 patch_tool 스크립트도 본다. patch_tool 의 모듈별 스크립트 주석은 "왜 이 설정이 바뀌는지"(예: 모듈 2.0.0.0 부터 PDF 파일명 변경)를 알려 준다.

## S6. 3-way 판정 — 그대로 복사해도 되나, 당사 설정은 어떻게 하나

이 스킬의 핵심이다. 상세 규칙·사례는 `references/three-way-merge.md`.

**ARXML** 은 `scripts/three_way.py` 로 파일마다 Prev / Cur / Ours 를 파라미터 단위로 비교해 판정표 초안을 만든다(`--md` 로 표 저장). 스크립트는 세 가지를 알아서 다룬다.
- 리스트형 파라미터(InputFilesList 등)는 **HAE 델타(Prev→Cur 추가·삭제)만**으로 판정한다. 당사 고유 항목 차이는 비고에 개수로만 적는다 — 당사 목록이 HAE 와 원래 달라도 HAE 가 이번에 더한 것만 반영하면 되기 때문이다.
- 순번 파라미터(…Index / Position / Order)는 값만 비교하면 틀린다. '순번 목록' 절에서 Prev / Cur / Ours 순서를 나란히 보여 주고, 목록 구성이 다르면(HAE 에만 있는 항목 등) 경고한다. 이때는 번호를 복사하지 말고 HAE 의 번호 규칙을 당사 구성에 적용한다.
- 하위 값이 같은 삭제+추가 컨테이너는 '이름변경' 한 줄로 묶는다.

| 경우 | 판정 | 처리 |
|---|---|---|
| Prev = Cur (HAE 미변경) | 무관 | 당사 값 유지 |
| HAE 변경, Ours = Prev | 복사 가능 | Cur 값을 해당 위치에만 반영 |
| HAE 변경, Ours = Cur | 기존 충족 | 변경 없음 |
| HAE 변경, Ours ≠ Prev 이고 ≠ Cur | 당사 전용 충돌 | 자동 반영 금지 → 판단 |
| HAE 변경이 다른 구성 전제 | 제외 | 근거 기록 |
| 회사 보류·예외 규칙 해당 | 보류 | `references/decision-rules.md` 근거 |

**당사 전용 충돌**은 이렇게 판단한다.
1. 당사 값이 왜 그런지 찾는다 — `git log -L` / `git log -S` 로 그 값을 넣은 커밋과 일감.
2. HAE 변경의 의도를 찾는다 — IM 절, 안내 댓글, patch_tool 주석.
3. 두 의도를 함께 살리는 값을 제안한다(예: 당사가 추가한 항목은 유지하고 HAE 가 바꾼 인덱스 규칙만 적용).
4. 사용자에게 판정표 행과 제안을 보여 확정받는다. 애매하면 S7 IMS 질문 후보로 올린다.

**다른 구성 전제**의 전형: HAE 참고 프로젝트와 모듈 버전이 다름(예: Crypto 2.0 의 새 PDF 파일명을 1.x 프로젝트에 넣으면 안 됨), MCU·채널·버스 구성이 다름(SP3i 고유 CDD_Router, L2CAN 입력), PFee 같은 기능 미사용, Harmonize 부산물(컨테이너 순서·CATEGORY 태그·UUID 변경).

**묶음 판정.** patch_tool 의 한 함수가 여러 곳에 함께 넣은 항목(예: `ensure_haemodule_scons()` 의 PDF 4곳 + Rte 입력 Ecud)은 함수 docstring 의 전제로 묶음 전체를 판정한다. 일부만 "파일이 있으니 반영"으로 떼어 내면 근거가 갈리고, 하나라도 사유 없이 빠지면 S9 재대조에서 누락으로 보인다. 판정이 갈릴 만한 항목은 근거 두 가지를 나란히 보여 주고 사용자가 정하게 한다.

**소스 파일**:
- `Static_Code/Modules/<모듈>` 은 교체하기 전에 `scripts/owner_edits.py` 로 당사 폴더와 HAE Prev 를 비교한다. 다른 파일이 있으면 당사 수정이다 — 그 파일은 통째 교체하지 말고 3-way 병합한다.
- `Integration_Code/*/usercode`, `Reference_Code` 는 HAE 가 "사용자가 검토하고 최종 코드를 fix 해야 한다"고 명시한 영역이다. 항상 `git merge-file ours prev cur` 로 3-way 병합하고 충돌은 사람이 결정한다. 전수 검토 목록을 판정표에 남긴다.
- `fixedcode` 는 HAE 소유라 교체하되, 당사 수정 이력이 있으면 위와 같이 처리한다.

판정표는 그대로 Redmine 코멘트·Confluence 표가 된다(`references/templates.md` 의 "HAE 요청 / 이전 상태 / 처리 / 확인 근거" 형식).

## S7. IMS 질문 댓글 (필요 시)

질문이 필요한 경우: 당사 전용 충돌의 방향을 정할 수 없을 때, 안내와 배포본이 다를 때, 가이드 링크가 열리지 않을 때, 같은 성격의 변경인데 FBL / APP 안내가 다를 때.

1. `references/templates.md` 의 IMS 질문 양식(대상 / 당사 현황 / HAE 안내·배포본 내용 / 질문 / 첨부)으로 초안을 쓴다. 담당자 멘션은 안내 댓글 작성자로 한다.
2. **기본은 초안을 사용자에게 주고 사용자가 직접 등록**한다. HAE 로 나가는 외부 메시지이기 때문이다.
3. 사용자가 대신 등록을 원하면 그 댓글 하나에 대한 승인을 받고 Claude in Chrome 으로 등록한다(`references/ims-workflow.md`). 등록 후 화면에서 확인해 보고한다.
4. 답변을 기다리는 동안 그 항목은 판정표에 "HAE 확인 중"으로 두고, 다른 항목은 진행할 수 있다.

## S8. 적용

순서: 모듈 교체 → ARXML → usercode → 버전업 → Doc. 단계마다 `git diff --stat` 으로 범위를 확인한다.

- **모듈 교체**: 폴더를 지우고 HAE Cur 폴더를 복사한 뒤 `diff -rq` 로 바이트 일치를 확인한다. S6 에서 찾은 당사 수정 파일은 병합본으로 되돌린다.
- **ARXML**: 판정표의 "복사 가능" 항목만, 해당 요소만 고친다. ODIN 도구가 남기는 `ADMIN-DATA` 의 `SD GID="<파라미터명>"`(USER_CONFIGURED 기록)도 VALUE 와 같이 바꾼다 — HAE 배포본이 그렇게 하고, 도구가 다음에 열 때 값이 어긋나지 않게 하기 위함이다. 줄바꿈(CRLF/LF)과 인코딩은 원래 파일 그대로 유지한다(`git diff --stat` 의 줄 수로 확인).
- **usercode**: S6 병합 결과를 반영.
- **버전업**: `references/version-up.md` 와 프로필의 위치 목록대로. `scripts/version_bump_check.py` 로 이전 버전 문자열 잔존이 없는지 확인한다.
- **Doc**: ReleaseNote·ModuleList 를 프로필의 위치·파일명 규칙으로 추가.
- 바꾼 파일은 XML 파싱으로 깨지지 않았는지 확인한다.

## S9. 정적 검수 (빌드 전)

빌드 한 번에 6~50분이 걸리고 push 가 필요하므로, 빌드 전에 잡을 수 있는 것은 여기서 잡는다.

**한 번에 돌리기**: `scripts/review_all.py --prev … --cur … --app … --old-token … --new-token … --expect … --out 검수보고서.md` 가 아래 1·2·4 와 모듈 바이트 일치, 의존 모듈 .ver 목록까지 돌려 검수 보고서 한 장(요약표 + 상세 + 확인 못 한 것)을 만든다. 빌드 후에는 같은 명령에 `--job --build --compare --gen-old --gen-new --map-old --map-new` 를 더해 S10 까지 한 보고서로 낸다. 사용자가 "검수해줘"라고 하면 이것부터 돌리고, 요약표의 '확인' 항목을 판정표 사유와 하나씩 대조해 설명한다. 보고서의 '확인'은 오류가 아니라 사람이 사유를 확인할 항목이라는 뜻이다.

개별로 돌릴 때:

1. `scripts/three_way.py --prev … --cur … --ours … --check` 로 적용 후에도 HAE 변경과 다른 항목만 뽑는다(--prev 없이 하면 당사 고유 차이 수천 건이 섞인다). **남은 항목은 전부 판정표의 제외·보류·당사 구성 반영 사유와 1:1 이어야 한다.** 사유 없는 항목은 누락이다.
2. `scripts/symbol_crosscheck.py` — 교체한 모듈에서 당사 코드가 쓰는 심볼의 선언 변화·삭제, 새로 쓰이는 `#if` 매크로(생성 헤더에 없으면 조용히 0 처리됨).
3. IM 의 신규 Validation 규칙을 당사 Ecud 설정에 미리 적용해 본다(규칙별로 짧은 파이썬 점검. 예시는 `references/three-way-merge.md`).
4. `scripts/version_bump_check.py` — 버전 잔존 0.
5. 결과를 사용자에게 요약하고 커밋 여부를 묻지 말고 기다린다(사용자가 지시하면 커밋).

## S10. 빌드·빌드 검수

사용자가 커밋·push 를 지시하면 진행한다. 커밋 메시지는 `references/templates.md` 의 패치 커밋 양식(일감·원 일감·IMS 번호, 모듈 버전 변화, 설정 변경, 일부러 적용하지 않은 것과 사유, 참조 배포본). Jenkins Hook 이 **커밋 제목**으로 빌드 동작을 정하는 프로젝트가 있으니(`references/jenkins-flow.md`) 제목을 "Rebuild" 같은 단어 하나로 쓰지 않는다.

1. `scripts/jenkins_wait.py <job> <번호> --compare <직전 전체 생성 빌드 번호>` 를 백그라운드로 돌려 결과를 기다린다. 비교 대상은 **직전 회차에서 전체 재생성을 한 빌드**여야 한다(증분 빌드는 Generate 로그가 없다).
2. 확인 항목: 결과, 생성기 Error, Rte Validation errors(warnings 는 직전과 같은지), SAFERTE_ERR, 종류별 SAFERTE_WARN 증감, 산출물 이름.
3. Jenkins Auto commit 을 pull 하고 `scripts/gen_diff_review.py` 로 직전 버전 대비 Generated 변화를 본다. **당사 설정을 바꾸지 않았는데 바뀐 생성 코드가 있으면 원인을 설명할 수 있어야 한다.** 설정을 바꿨는데 생성 코드가 그대로면 그것도 설명한다(예: 인덱스만 당겨 순서 불변).
4. `scripts/map_mem.py` 로 RAM / ROM 을 직전 회차와 같은 방식으로 계산한다. 직전 값이 그대로 재현되는지 먼저 확인한다.

1~4 는 `review_all.py` 에 빌드 인자를 붙여 S9 와 한 보고서로 낼 수 있다(빌드 완료 후 실행 — 대기는 jenkins_wait.py 를 백그라운드로 먼저).

## S11. 기록

Redmine 코멘트는 `references/templates.md` 의 "패치 작업 — HAE 요청사항과 처리 결과" 양식: HAE 요청 → 요청별 처리 결과 표(요청 / 이전 상태 / 처리(파일) / 확인 근거) + 적용 제외 사유 → 빌드 결과 → 남은 작업. 원문 전체를 사용자에게 보여 주고 승인 후 등록한다. 요약만 보여 주고 "이게 들어간다"고 하면 안 된다 — 사용자가 승인하는 대상은 실제 등록될 원문이다.

## S12. 실기 검증

절차와 판정 기준은 `references/verification.md`, 세부 실행은 각 스킬과 프로젝트의 체크리스트(프로필에 링크)를 따른다.

```
ALL 빌드 전환(지시 시 커밋) → 산출물 4벌 확인
→ 라이팅 (cvd-project, 양 뱅크) → CAN 출력 (can-bench-setup)
→ 진단 회귀 · 패치 고유 시험 (수평전개 결함 재현 조건 포함)
→ 서명 요청 → H-OTA 업/다운그레이드
→ 결과 폴더·첨부 정리 → CURRENT 복귀 (지시 시 커밋)
```

수평전개 결함의 **재현 조건**을 그대로 시험 케이스로 만든다(예: TransferData Repeat Block). 정상 흐름 H-OTA 만으로는 패치 효과가 확인되지 않는다. 진단 결과는 프로필의 CDD 주의사항을 먼저 본다.

## S13. 마무리

PR 방식(APP cherry-pick 쌓기 / FBL squash 등), 대상 브랜치, 머지 순서는 프로필을 따른다. Redmine 상태 전이와 IMS 상태(수평전개 티켓 Closed 처리 요청 등)는 사용자에게 확인 후 처리한다.

## 보고 형식

단계를 마칠 때마다 짧게:

```
[S6 3-way 판정] 대상 6파일 · 요청 9항목
  복사 가능 4 / 기존 충족 2 / 당사 전용 충돌 1 / 제외 2
  충돌: Ecud_EcuM ListTwo Index — 당사 3단 vs HAE 4단(PMem_Driver), 제안 …
  다음: 충돌 1건 확인 필요 → 확정되면 S8
```

확인하지 못한 것(권한 없는 링크, 비밀번호로 열지 못한 파일, 실기 미수행)은 따로 한 줄로 적는다.

## 참고 문서

| 파일 | 언제 읽나 |
|---|---|
| `references/ims-workflow.md` | S1·S7 — IMS 읽기·댓글, MCP 연결 시 대응 |
| `references/three-way-merge.md` | S6·S9 — 판정 규칙 상세, 사례, Validation 사전 점검 예 |
| `references/decision-rules.md` | S6 — 회사 공통 보류·예외 규칙 (누적) |
| `references/version-up.md` | S8 — 버전·산출물명 규칙 |
| `references/jenkins-flow.md` | S10·S12 — Hook 동작, ALL/CURRENT, 산출물 구조, 커밋 주의 |
| `references/verification.md` | S10·S12 — 빌드·실기 판정 기준, 결과 파일 규칙 |
| `references/templates.md` | S4·S7·S10·S11 — Redmine 본문, 코멘트, IMS 질문, 커밋 메시지, Confluence 골격 |
| `references/troubleshooting.md` | 막혔을 때, 그리고 단계를 시작하기 전에 해당 절 — 실제 재작업 사례 |
| `references/projects/*.md` | S0 — 프로젝트 프로필 |

새로 겪은 함정이나 HAE 답변으로 생긴 규칙은 작업이 끝날 때 `troubleshooting.md` / `decision-rules.md` / 프로필에 한 줄씩 추가하자고 사용자에게 제안한다. 이 스킬은 쓸수록 정확해져야 한다.

## 범위 밖

- 작업 브랜치·Jenkins Job 신설 → gitea-jenkins-setup
- eCoDY-ECM 주제 검색 자체 → ecody-search (이 스킬은 패치에 필요한 가이드만 그 스킬로 읽는다)
- 라이팅·CAN 측정 로직 → cvd-project, can-bench-setup, canoe-project-setup
- Redmine 일감 단순 조회 → redmine-issue
- PR 머지, 공유 브랜치 정리
