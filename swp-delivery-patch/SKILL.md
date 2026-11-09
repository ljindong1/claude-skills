# SWP Delivery_Patch 적용

HAE 가 eCoDY-IMS 로 배포한 SWP 패치를 당사 제어기 프로젝트에 적용하고, 검수·기록하는 절차다. 차종·제어기·FBL/APP 공통이고, 프로젝트마다 다른 값(저장소, Job, 버전 위치, 당사 수정 파일, 보호 설정)은 프로젝트 프로필에 둔다.

사고가 나는 지점은 거의 정해져 있다 — HAE 참고 설정을 통째로 복사해 당사 설정을 덮음, 재배포·재가이드·이전 회차 보정을 놓침, 버전·산출물명 위치 하나를 빠뜨림, 확인하지 않은 것을 확인된 것처럼 말함. 절차는 이 넷을 막도록 짜여 있다.

## 세 자료와 번호

작업에는 자료가 셋 있다. 역할이 다르니 섞지 않는다.

| 자료 | 역할 | 이 스킬의 관계 |
|---|---|---|
| **Redmine 작업 지시서 일감** | 이번 회차에 무엇을·어떤 순서로·어디까지 하는지. 단계 번호·요청 항목·질문 목록·완료 기준이 여기 있다 | **읽는다.** 본문 작성·갱신은 `redmine-patch-issue` 스킬이 한다. 이 스킬은 결과를 코멘트로 적는다 |
| **당사 저장소 / 작업 브랜치** | 바꿀 대상 | 판정·적용·검수의 현장 |
| **배포본 + 패치 자료 폴더** | HAE 가 보낸 것 (참고 설정, 모듈, patch_tool, Doc) | 판정의 입력. 정답이 아니라 참고 |

**번호는 일감 것 하나만 쓴다.** 이 스킬은 자체 단계 번호를 갖지 않는다 — 두 체계가 있으면 "S8" 이 서로 다른 것을 가리켜 엉뚱한 단계의 점검을 적용한다. 일감이 없으면 IMS 티켓에서 **요청 항목 목록**을 직접 만들고(`ims-workflow.md` §1) 그 목록이 일감 자리를 대신한다.

## 용어

| 용어 | 뜻 |
|---|---|
| 패치 파일 / 배포본 | HAE 가 IMS 티켓에 첨부한 zip. 회차마다 있고, 같은 회차 안에서도 재배포본·보정본이 있다 |
| Prev / Cur / Ours | 3-way 의 세 형상 — HAE 직전 회차 / HAE 이번 회차 / 당사 저장소. **스크립트·내부 용어**다. 사람에게 보내는 글에는 `communication.md` §2 이름으로 바꿔 쓴다 |
| 참고 설정 | 배포본 안의 .arxml (HAE 대표 차종 기준). "참고용"이며 정답이 아니다 |
| VC 견본 | Validation Checker 참고 파일. Harmonize 결과물과 같다 |
| 보호 설정 | 당사가 일부러 HAE·VC 와 다르게 둔 값 (프로필 표) |
| 판정표 | 요청·차이 항목마다 판정·경로·처리·근거·이력을 적는 표 (`three-way-merge.md` §6) |

## 기본 원칙

1. **판단 기준은 HAE 원본이다** — IMS 티켓 본문·댓글 전체·첨부 전부·변경 이력·연결 수평전개, 그리고 IM/IA/SAG. 일감과 다른 사람의 적용본(Redmine, Gitea)은 정리물이고 참고다.
2. **참고 설정은 통째로 복사하지 않는다.** 3-way 판정에서 "복사 가능"인 항목만 그 위치에 반영한다.
3. **모르는 것은 추정하지 않는다.** 애매하거나 당사 설정과 충돌하면 사용자에게 묻고, 원하면 IMS 로 HAE 에 확인한다.
4. **외부에 쓰는 일은 모두 미리보기 → 승인 → 실행이다.** IMS 댓글, Redmine, Confluence, git commit / push(= Jenkins 빌드), 보드 라이팅, CAN 송신. 승인은 그 한 건에만 유효하다. 커밋·push 는 사용자가 지시할 때만 하고 먼저 제안하지 않는다.
5. **확인한 것과 하지 않은 것을 구분해 보고한다.** 빌드 성공은 실기 검증이 아니고, 정적 검수는 동작 검증이 아니다.
6. **확인한 것만, 이름을 밝혀, 쉽게 말한다.** 파일을 열어 본 뒤에만 경로·행과 함께 말하고, 비교는 "A 에는 있는데 B 에는 없다"로 먼저 쓴다. 보내기 전 점검 → `communication.md`.
7. **보호 설정이 바뀌면 "동작 차이 없음"이어도 사용자 확인을 받는다.** 값이 없던 파라미터가 생기거나 사라지는 것(생성기 기본값 의존)도 같다. Harmonize·CLI·수동·이 스킬 반영 어느 경로든 → `protected-settings.md`.
8. **이전 대비 변경사항이 있으면 무조건 과거 이력까지 분석해 함께 알린다.** 판정 라벨("기존 충족"·"무관"·"부산물")·크기·출처와 상관없다. 이전 회차 보정본·HAE 답변·git 이력·이전 일감을 회차순으로 대조하고 "이번 값 / 이전 회차 값·근거"로 보고한다. 찾지 않았으면 "이력 미확인". HAE 최신 배포본이 이전 보정을 되돌린 채 나온 적이 있다 → `three-way-merge.md` §4.8.
9. **형상을 바꾸는 도구는 복사본·시험 브랜치에서 먼저 돌린다.** 측정으로 확인된 사실이다 — C Studio CLI 는 읽기 기능(`-validation`)에서도 프로젝트를 저장하고, 배포본 patch_tool 은 중간에 실패해도 그때까지의 변경이 남고, Harmonize 는 기본 옵션으로 당사 값을 덮는다. 되돌리는 길은 git 뿐이다.

## 실행 환경

- Claude Code CLI(사용자 PC, 사내망). Redmine·Gitea·Jenkins 가 사설망에 있다.
- eCoDY-IMS·ECM 은 **읽기·검색은 `ecody-search` 스킬**, **IMS 질문 댓글 쓰기만 이 스킬** → `ims-workflow.md`.
- 환경변수: `JENKINS_URL`·`JENKINS_USER`·`JENKINS_TOKEN`, `GITEA_TOKEN`. Redmine 은 redmine-issue 스킬.
- 스크립트는 `scripts/`, 파이썬 표준 라이브러리만(`-h` 로 사용법). 출력 UTF-8. 한글 경로 인자는 PowerShell 에서 안전하다. 긴 출력은 파일로 받는다.
- 생성·컴파일 도구(`ts_mirr` 류 미러 폴더)는 Jenkins 쪽에만 있는 경우가 많다. Harmonize·Validation·Script 는 그것 없이도 된다 → `apply.md` §1, `jenkins-flow.md` §3-1.

## 시작 절차

1. **프로젝트 프로필** — `references/projects/<차종>_<제어기>.md` 를 연다. 없으면 `_template.md` 를 복사해 저장소를 조사하며 채우고, 조사로 알 수 없는 것만 한 번에 묻는다. 새 프로필·갱신은 사용자 확인 후 저장한다. 보호 설정 표의 이번 대상(FBL/APP) 행이 비어 있으면 판정 때 채울 항목으로 표시한다.
2. **일감** — 전체를 읽는다. 단계·요청 항목·질문·완료 기준이 이번 회차의 좌표다. 일감이 없으면 위의 요청 항목 목록을 만든다.
3. **배포본** — 형태(VersionComparison 형 / AutomatePatch 형)를 보고 Prev·Cur 를 확보한다(`three-way-merge.md` §2). 재배포가 있으면 날짜순으로 모두 받아 비교한다.

사용자는 대개 중간에서 부른다("배포본 비교해줘", "검수해줘", "지적 사항 반영해줘"). 앞 산출물(요청 항목 목록, 판정표)이 있는지 보고, 없으면 필요한 만큼만 빠르게 만든다.

## 일감 단계 ↔ 문서·도구

일감의 절 성격으로 찾는다. 회차마다 번호와 내용이 다르므로 번호를 외우지 않는다.

| 일감의 절 | 하는 일 | 문서 | 도구 |
|---|---|---|---|
| 한눈에 · 작업 환경 | 프로필과 대조, 다른 점 갱신 | `projects/*.md` | — |
| 준비 (배포본·도구·의존 모듈) | 배포본 확보·완결성, 도구 전제, 의존 모듈 | `three-way-merge.md` §2 | `zip_crc_compare.py` |
| 변경 지도 | 판정표 초기 행 만들기 | `three-way-merge.md` §6 | — |
| 패치 도구 | 계획서로 읽기(필수), 실행 여부 결정, 돌렸으면 전후 비교 | `apply.md` §2 | `patch_tool_plan.py`, `three_way.py` |
| 설정 변경 (arxml) | 3-way 판정 → 수단 선택 → 적용 | `three-way-merge.md` §3·§4, `apply.md` §1·§3 | `three_way.py`, `arxml_block.py`, `history_trace.py`, `protected_check.py` |
| 모듈 교체 · usercode | 당사 수정 탐지 → 교체 → 병합 | `three-way-merge.md` §5, `apply.md` §4 | `owner_edits.py` |
| Harmonize | 버전 구간 확인 → 실행 → 결과 전수 대조 | `apply.md` §5, `protected-settings.md` §6 | ECUC Compare, `protected_check.py` |
| Generate · Validation | 정적 검수 (재대조·참조 끊김·ERR 대조) | `verification.md` §1 | `review_all.py`, `mobilgene-cli -validation` |
| 빌드 | 빌드 검수 (생성물 diff·남은 생성물·RAM/ROM) | `verification.md` §2 | `jenkins_wait.py`, `gen_diff_review.py`, `gen_stale_check.py`, `map_mem.py` |
| 코드 영향 (수평전개·API 변경) | 코드 영향 판정 | `three-way-merge.md` §5.4 | `git grep`, `symbol_crosscheck.py` |
| 버전업 | 버전 세 종류·위치·잔존 확인 | `apply.md` §6 | `version_bump_check.py` |
| 실기 | 판정 기준·순서 (실행은 각 스킬) | `verification.md` §3 | cvd-project, can-bench-setup, hota |
| 질문 (Q 목록) | 경로 A~D 로 분류 → C 만 질문 | `decision-rules.md` §0, `ims-workflow.md` §2 | — |
| 검증·완료 기준 | 항목마다 결과·판정, 미수행은 미수행으로 | `verification.md` | `review_all.py` |
| 참고 문서 | 근거 읽기 | — | ecody-search |
| 마무리 | PR, 상태 변경 | `pr-assembly.md` | gitea-jenkins-setup 모드 D |

작업 문서 네 개(three-way-merge · apply · protected-settings · verification)는 머리에 **들어가기 전 / 끝났다고 말하려면** 두 줄을 갖는다. 그 단계를 시작할 때와 끝났다고 말하기 전에 그 두 줄을 본다.

## 보고

단계를 마칠 때마다 짧게 보고한다. 형식과 이력 표기 → `communication.md` §6. 확인하지 못한 것(권한 없는 링크, 열지 못한 파일, 실기 미수행, 이력 미확인)은 따로 한 줄.

## 참고 문서 — 주제마다 한 곳

| 파일 | 담당 (이 주제의 규칙은 여기에만 둔다) |
|---|---|
| `references/three-way-merge.md` | 형상 확보·배포본 완결성, 모듈 계열별 볼 곳, 판정 규칙·사례, 과거 회차 이력(§4.8), 소스·**코드 영향 판정(§5.4)**, 판정표 형식(§6), 재대조·Validation 사전 점검 |
| `references/apply.md` | 적용 — 수단 셋(직접 편집·GUI·CLI), 배포본 patch_tool, ARXML 편집, 모듈·usercode, Harmonize 실행, 버전업 |
| `references/protected-settings.md` | 보호 설정 — 덮어쓰기 세 경로, 변경 분류 (a)~(d), 시점별 할 일, Harmonize 옵션·ECUC Compare, HAE 권고와의 충돌 |
| `references/verification.md` | 검수 — 정적 검수(참조 끊김·ERR 대조), 빌드 검수, 실기 판정 기준, 결과 파일 규칙 |
| `references/jenkins-flow.md` | Hook, ALL/CURRENT, 산출물 구조, 생성 경로, 로컬 도구, 남은 생성물, 커밋 주의 |
| `references/decision-rules.md` | **판단 경로 A~D(§0)** 와 적용·보류 판단 규칙(누적, 근거 포함) |
| `references/communication.md` | 사람에게 보내는 모든 글 — 확인한 것만, 이름 고정표, 비교 문장, 두 종류의 이력, 보내기 전 점검, 단계 보고 형식 |
| `references/templates.md` | 양식만 — 결과 코멘트·리뷰 회신, IMS 질문, 수평전개 회신, 커밋 메시지, Confluence 골격 |
| `references/ims-workflow.md` | IMS 에서 뽑을 것, 첨부 받기, 질문 등록, **기술지원 절차(ToU)**, ECM IM 페이지 대응표 |
| `references/pr-assembly.md` | 패치 PR 에서 덧붙일 것 (PR 구성 정본은 gitea-jenkins-setup 모드 D) |
| `references/troubleshooting.md` | 실제 재작업 사례만 (주제순). 그 주제를 시작하기 전에 해당 행을 훑는다 |
| `references/projects/*.md` | 프로젝트 프로필 — 저장소·Job·버전 위치·구성 전제·보호 설정·고유 판단 이력 |

**문서를 고칠 때 규칙** — 새 함정은 `troubleshooting.md` 에 사례 한 행, 거기서 나온 규칙은 담당 문서 **한 곳**에만 쓰고 다른 곳에는 링크만 둔다. 프로젝트 하나에만 해당하면 프로필에. 이번 회차에만 해당하는 값은 일감에 두고 스킬에 넣지 않는다. 작업이 끝날 때 이 추가를 사용자에게 제안한다.

## 범위 밖

- 일감 본문 작성·갱신 → redmine-patch-issue
- 작업 브랜치·Jenkins Job 신설, PR 구성 → gitea-jenkins-setup
- eCoDY-ECM·IMS 읽기·검색 → ecody-search (이 스킬은 IMS 댓글 쓰기만)
- 라이팅·CAN 측정 → cvd-project, can-bench-setup, canoe-project-setup
- H-OTA A·B 그룹 평가·산출물 → hota
- Redmine 일감 단순 조회 → redmine-issue
- PR 머지, 공유 브랜치 정리
