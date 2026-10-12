---
name: swp-delivery-patch
description: 현대오토에버(HAE) mobilgene Classic(R44/R4x) SWP Delivery_Patch 를 당사 제어기 프로젝트(FBL·APP, 차종·제어기 무관)에 적용하는 전 과정 — eCoDY-IMS 티켓 수집, 배포본 판별, HAE 이전/현재 형상과 당사 설정의 3-way 판정(그대로 복사해도 되는지, 당사 전용 설정은 어떻게 반영할지), 과거 회차 이력 대조, 적용, 정적 검수, Jenkins 빌드 결과 검수(생성물 diff·RAM/ROM), 버전업, 실기 검증 순서, 리뷰어 지적 대응, Redmine·IMS·Confluence 기록, PR 까지 — 을 안내하고 반복 작업은 동봉 스크립트로 처리하는 스킬. 사용자가 "Delivery_Patch", "SWP 패치", "패치 딜리버리", "MCP0806-xxx 패치 적용", "eCoDY-IMS 패치 티켓", "모듈 패치 적용해줘", "HAE 패치 받았어", "v3.0.xx 패치", "FBL 패치", "APP 패치", "재배포본", "배포본 비교", "패치 검수", "HAE 형상 그대로 복사해도 돼?", "당사 설정이랑 충돌", "IMS 에 질문 댓글", "패치 누락 지적", "리뷰 코멘트 반영", "버전업", "JENKINS_BUILD_TARGET ALL" 등을 말하거나, HAE 가 배포한 모듈·설정 변경을 당사 저장소에 반영하려는 의도를 보이면 반드시 이 스킬을 사용하라. Claude Code CLI(사내망, 사용자 PC) 전용. 개별 도구 작업은 담당 스킬로 넘긴다 — Redmine 쓰기는 redmine-issue, eCoDY-ECM·IMS 읽기·검색은 ecody-search, 보드 라이팅은 cvd-project, CAN 확인은 can-bench-setup / canoe-project-setup, H-OTA 평가는 hota-eval, Confluence 규약은 confluence-writing, 작업 브랜치·Jenkins Job 신설은 gitea-jenkins-setup.
---

# SWP Delivery_Patch 적용

HAE 가 eCoDY-IMS 로 배포한 SWP 패치를 당사 제어기 프로젝트에 적용하고, 검수·기록하는 절차다. 차종·제어기·FBL/APP 공통이고, 프로젝트마다 다른 값(저장소, Job, 버전 위치, 당사 수정 파일, 보호 설정)은 프로젝트 프로필에 둔다.

사고가 나는 지점은 거의 정해져 있다 — HAE 참고 설정을 통째로 복사해 당사 설정을 덮음, 재배포·재가이드·이전 회차 보정을 놓침, 버전·산출물명 위치 하나를 빠뜨림, 확인하지 않은 것을 확인된 것처럼 말함. 절차는 이 넷을 막도록 짜여 있다.

## 용어

| 용어 | 뜻 |
|---|---|
| 패치 파일 / 배포본 | HAE 가 IMS 티켓에 첨부한 zip. 회차(3.0.18, 3.0.19 …)마다 있고, 같은 회차 안에서도 재배포본·보정본이 있다 |
| Prev / Cur / Ours | 3-way 의 세 형상 — HAE 직전 회차 / HAE 이번 회차 / 당사 저장소. **스크립트·내부 용어**다. 사람에게 보내는 글에는 `communication.md` §2 이름으로 바꿔 쓴다 |
| 참고 설정 | 배포본 안의 .arxml (HAE 대표 차종 기준). "참고용"이며 정답이 아니다 |
| VC 견본 | Validation Checker 참고 파일. Harmonize 결과물과 같다 |
| 보호 설정 | 당사가 일부러 HAE·VC 와 다르게 둔 값 (프로필 표) |
| 판정표 | 요청·차이 항목마다 판정·경로·처리·근거·이력을 적는 표 (`three-way-merge.md` §6) |

## 기본 원칙

1. **출발점은 eCoDY-IMS 티켓이다.** 본문·댓글 전체·첨부 전부·변경 이력·연결 수평전개를 읽는다. 다른 사람의 적용본(Redmine, Gitea)은 참고일 뿐이고 판단 기준은 HAE 원본(IMS 안내·배포본·IM)이다.
2. **참고 설정은 통째로 복사하지 않는다.** 3-way 판정에서 "복사 가능"인 항목만 그 위치에 반영한다.
3. **모르는 것은 추정하지 않는다.** 애매하거나 당사 설정과 충돌하면 사용자에게 묻고, 원하면 IMS 로 HAE 에 확인한다.
4. **외부에 쓰는 일은 모두 미리보기 → 승인 → 실행이다.** IMS 댓글, Redmine, Confluence, git commit / push(= Jenkins 빌드), 보드 라이팅, CAN 송신. 승인은 그 한 건에만 유효하다. 커밋·push 는 사용자가 지시할 때만 하고 먼저 제안하지 않는다.
5. **확인한 것과 하지 않은 것을 구분해 보고한다.** 빌드 성공은 실기 검증이 아니고, 정적 검수는 동작 검증이 아니다.
6. **확인한 것만, 이름을 밝혀, 쉽게 말한다.** 파일을 열어 본 뒤에만 경로·행과 함께 말하고, 비교는 "A 에는 있는데 B 에는 없다"로 먼저 쓴다. 보내기 전 점검 → `references/communication.md`.
7. **보호 설정이 바뀌면 "동작 차이 없음"이어도 사용자 확인을 받는다.** 값이 없던 파라미터가 생기거나 사라지는 것(생성기 기본값 의존)도 같다. Harmonize·CLI·수동·이 스킬 반영 어느 경로든 → `references/protected-settings.md`.
8. **이전 대비 변경사항이 있으면 무조건 과거 이력까지 분석해 함께 알린다.** 판정 라벨("기존 충족"·"무관"·"부산물")·크기·출처(배포본, 재배포본, 당사 설정, 생성 코드, 빌드 결과, 리뷰어 지적)와 상관없다. 이전 회차 보정본·HAE 답변·git 이력·이전 일감을 회차순으로 대조하고 "이번 값 / 이전 회차 값·근거"로 보고한다. 찾지 않았으면 "이력 미확인". HAE 최신 배포본이 이전 보정을 되돌린 채 나온 적이 있다 → `references/three-way-merge.md` §4.8.

## 실행 환경

- Claude Code CLI(사용자 PC, 사내망). Redmine·Gitea·Jenkins 가 사설망에 있다.
- eCoDY-IMS·ECM 은 Claude in Chrome 로그인 세션. **읽기·검색은 `ecody-search` 스킬**, **IMS 질문 댓글 쓰기만 이 스킬** → `references/ims-workflow.md`.
- 환경변수: `JENKINS_URL`·`JENKINS_USER`·`JENKINS_TOKEN`, `GITEA_TOKEN`, Redmine 은 redmine-issue 스킬.
- 스크립트는 `scripts/`, 파이썬 표준 라이브러리만(`-h` 로 사용법). 출력 UTF-8. 한글 경로 인자는 PowerShell 에서 안전하다. 긴 출력은 파일로 받는다.

## 전체 흐름

```
S0  프로젝트 프로필        프로필 로드(구성 전제·보호 설정), 없으면 저장소 조사로 초안
P   사전 점검              구성 전제 · 배포본 완결성 · 위험 포인트 · 과거 Q&A · 작업 수단 → 항목별 경로 A~D
S1  IMS 수집              티켓·댓글·첨부(날짜순 전부)·이력·수평전개 → 요청 항목 목록
S2  가이드 정독            IM / SAG / IA·VC (ecody-search)
S3  선행 작업 조회 (선택)   같은 패치의 다른 일감·브랜치·IMS 문답 → 참고 목록
S4  일감·문서              Redmine 일감 본문, Confluence 분석 페이지
S5  배포본 판별            유효 배포본(내용 비교), Prev / Cur 확보, 완결성
S6  3-way 판정            Prev / Cur / Ours + 과거 회차 이력 → 판정표 (핵심)
S7  IMS 질문 (필요 시)      C 경로만, 초안 → 승인 → 등록 → 번호별 답변 대조
S8  적용                  모듈 교체 → ARXML → usercode → 버전업 → Doc
S9  정적 검수              review_all.py — 재대조·심볼·Validation·버전 잔존·보호 설정
S10 빌드·빌드 검수          (지시 시) commit/push → Jenkins → 생성물 diff·남은 생성물·RAM/ROM
S11 기록·리뷰 대응          Redmine 결과 코멘트, 리뷰어 지적 → 항목별 처리 → 번호별 회신
S12 실기                  ALL → 라이팅 → CAN → 고유 시험 → 서명 → H-OTA → CURRENT
S13 마무리                PR, IMS·Redmine 상태
```

사용자는 대개 중간 단계에서 부른다("배포본 비교해줘", "검수해줘", "지적 사항 반영해줘"). 앞 단계 산출물(요청 항목 목록, 판정표)이 있는지 보고, 없으면 필요한 만큼만 빠르게 만든다.

## S0. 프로젝트 프로필

`references/projects/<차종>_<제어기>.md` 를 연다(예: `he1i_psu.md`). 없으면 `_template.md` 를 복사해 저장소를 조사하며 채우고, 조사로 알 수 없는 것만 한 번에 묻는다. 새 프로필·갱신은 사용자 확인 후 저장한다. 보호 설정 표의 이번 대상(FBL/APP) 행이 비어 있으면 S6 에서 채울 항목으로 표시한다.

## P. 사전 점검

`references/precheck.md` 대로 다섯 가지를 점검한다 — ① 구성 전제(프로필 표, FBL/APP 따로) ② 배포본 완결성(보정본·정정·재배포 포함) ③ 모듈별 위험 포인트 → 판정표 초기 행 ④ 과거 Q&A 조사 순서 ⑤ 작업 수단(ARXML 직접 편집 / 툴). 그리고 요청 항목마다 판단 경로를 정한다: **D 회사 기준 보류 → A 스스로 확정 → B 과거 자료 조사 → C HAE 질문** 순으로 처음 맞는 것, 애매하면 한 단계 보수적으로.

## S1. eCoDY-IMS 수집

`ecody-search`(IMS)의 `ims_read.js` 로 패치 티켓과 연결 수평전개를 함께 읽는다(`__MAX__` 60000). 뽑을 것과 읽는 법 → `references/ims-workflow.md` §1. 놓치기 쉬운 것:

- **재배포·안내 개정** — 첨부는 최신본만 받지 않고 날짜순으로 모두 받는다. 안내 댓글도 날짜순으로 다 읽고 항목별 최신값(harmonize 대상 등)을 쓴다.
- **개정 안내에서 빠진 요청은 철회로 단정하지 않는다** — IM 링크·같은 날 문답과 대조한다.
- **수평전개 티켓** — 결함·적용 조건·당사 회신. 실기 고유 시험의 근거다.
- **당사 문의와 HAE 답변** — 안내문을 사실상 바꾼다.
- **이전 회차 티켓의 보정본·정정** — 이번 배포본에 반영됐는지 S6 에서 대조할 목록으로 적어 둔다(원칙 8).
- 권한 없는 가이드 링크 → 새 IM 페이지 검색(ims-workflow §4).

산출물: **요청 항목 목록**(항목 / 출처 댓글·날짜 / 필수·참고). 판정표의 행이 된다.

## S2. 가이드 정독

요청 항목마다 IM 절, IA/VC 규칙, SAG 를 ecody-search 로 읽는다. 버전별 변경 절의 **의존성**과 **신규 Validation**(S9 사전 점검 대상), IM 표준 설정(참고 설정과 다르면 IM 을 따르고 기록), 더 최신 버전 존재 여부(범위 밖이면 기록만).

## S3. 선행 작업 조회 (선택)

같은 패치를 먼저 적용한 Redmine 일감·Gitea 브랜치, 같은 모듈·버전의 다른 과제 IMS 문답(ecody-search JQL)을 목록에 올린다. "어떤 파일이 바뀌는지", "HAE 에 물어 받은 답"용이며 그대로 이식하지 않는다(이식해도 S6 판정을 거친다).

## S4. 일감·문서

Redmine 일감 본문은 `references/templates.md` §1 구성으로, redmine-issue 스킬의 미리보기 → 승인 규칙으로 등록·갱신한다. 상태 전이 규칙은 프로필. 일감 본문의 "검토 항목"은 S11 결과 코멘트에서 하나씩 결론을 적는다(결론 없이 남기면 누락이 된다). 분석이 길면 Confluence 페이지(confluence-writing, 위치는 프로필).

## S5. 배포본 판별

1. **유효 배포본** — 재배포가 있으면 `zip_crc_compare.py` 로 비교한다. 비밀번호가 걸린 zip 도 목록의 CRC 로 비교된다(내용 비교에는 압축 해제가 필요하니 사용자에게 요청). CRC 는 "어느 파일이 개정됐나"까지만 알려 준다. CRC 가 다른 ARXML 은 `three_way.py --prev <이전본> --cur <새본> --ours <당사>` 로 내용까지 비교하고, 이전본에만 있는 설정은 철회 확인 항목으로 판정표에 올린다. "이전본은 필요 없다"는 이 결과를 보인 뒤에만 말한다(decision-rules 공통).
2. **Prev / Cur 확보** — `VersionComparison/PreviousVersion`·`CurrentVersion` 이 있으면 쓴다(모듈 본체도 `CurrentVersion/Static_Code/Modules/` 아래 — 판정표 첫 행은 모듈 교체). 없으면 Cur = 배포본 참고 설정, Prev = 직전 회차 배포본 + 그 회차 보정본. 둘 다 없으면 2-way 로 하고 "Prev 없음" 표시, git 이력으로 보완. 상세 `three-way-merge.md` §2.
3. **완결성** — 안내가 언급한 파일 ↔ 실제 파일, 이후 보정본·정정(precheck ②). 빠진 것은 C 후보.
4. **patch_tool Action Report 는 요청의 일부일 뿐이다** — SCons 항목은 각 생성기에 자기 모듈 PDF 를 자동으로 넣은 기록뿐이다. 참고 설정 대조는 S6 에서 따로 한다.
5. Doc(ReleaseNote, ModuleList, Module Change List)과 patch_tool 스크립트 주석("왜 바뀌는지")을 본다.

## S6. 3-way 판정

핵심 단계다. 규칙·사례 → `references/three-way-merge.md`.

`three_way.py` 로 Prev / Cur / Ours 를 파라미터 단위로 비교해 판정표 초안을 만든다(`--md`). 리스트형은 HAE 델타만, 순번(Index 등)은 '순번 목록'으로 구성까지, 같은 내용의 삭제+추가는 '이름변경'으로 묶어 준다.

| 경우 | 판정 | 처리 |
|---|---|---|
| Prev = Cur | 무관 | 당사 값 유지 (안내가 직접 언급한 위치면 §4.7 함정 확인) |
| HAE 변경, Ours = Prev | 복사 가능 | Cur 값을 그 위치에만 |
| HAE 변경, Ours = Cur | 기존 충족 | 변경 없음 |
| HAE 변경, Ours ≠ Prev·Cur | 당사 전용 충돌 | 자동 반영 금지 → 유래·의도 조사 → 제안 → 사용자 확정 |
| 다른 구성 전제 | 제외 | 근거 기록 (모듈 버전·구성·기능 미사용·Harmonize 부산물) |
| 회사 규칙 해당 | 보류 | `decision-rules.md` 근거 |

판정표를 완성하기 전에 행마다 확인한다:

- [ ] **과거 회차 이력** (원칙 8, §4.8) — 라벨과 무관하게 모든 행. 이번 배포본이 이전 보정을 되돌렸으면 "되돌림 의심"으로 두고 사용자 확인, 엇갈리면 C.
- [ ] **보호 설정** (원칙 7, protected-settings §5) — "복사 가능"·"충돌" 행이 보호 설정을 건드리면 "보호" 표시. 이유 모르는 당사 고유값은 "이유 미상" 후보.
- [ ] **참고 설정과의 차이는 항목마다** 반영 / 제외(사유) / 확인 필요로 분류 — "레퍼런스 프로젝트라 다르다"로 묶지 않는다.
- [ ] **묶음 판정** — patch_tool 한 함수가 함께 넣은 항목은 함수 전제로 묶음 전체를 같은 사유로.
- [ ] **대상 구분** — 같은 모듈도 APP / FBL 구성 전제(PFee 등)가 다르면 결론이 다르다.
- [ ] **경로(A~D)와 근거** — 재현 가능한 근거만.

소스 파일: `Static_Code/Modules/<모듈>` 은 교체 전 `owner_edits.py` 로 당사 수정 파일을 찾아 그 파일만 3-way 병합. `usercode`·`Reference_Code` 는 항상 `git merge-file` 3-way 병합 + 전수 검토 목록. `fixedcode` 는 교체하되 당사 수정 이력이 있으면 병합(§5).

## S7. IMS 질문 (필요 시)

C 경로 항목만, 한 패치의 질문은 한 댓글에 번호를 매겨 모은다. 양식 → `templates.md` §3, 문장 점검 → `communication.md` §5, 등록 → `ims-workflow.md` §2. 기본은 사용자가 직접 등록하고, 대행은 그 댓글 하나의 승인을 받았을 때만. 답을 기다리는 항목은 판정표에 "HAE 확인 중"과 잠정 처리(보수적 값). 답이 오면 질문 번호마다 대조하고 빠진 번호는 다시 묻는다.

## S8. 적용

순서: 모듈 교체 → ARXML → usercode → 버전업 → Doc. 단계마다 `git diff --stat`.

- **첨부 zip** 은 `unzip -l` 로 최상위 폴더부터 보고 `X\X\` 가 되지 않게 푼다. 적용 후 `git diff --cached -M --summary` 에 의도하지 않은 rename 이 없는지.
- **모듈 교체** — 폴더 삭제 → Cur 복사 → `diff -rq` 바이트 일치. 당사 수정 파일은 병합본으로.
- **ARXML** — 판정표 "복사 가능"만, 그 요소만. 직접 편집은 `arxml_block.py`(블록 이식·삭제·이름 변경·값 변경), 툴 항목은 mobilgene CLI / C Studio. `ADMIN-DATA` 의 `SD GID` 기록값도 VALUE 와 같이, 줄바꿈·인코딩 유지, XML 파싱 확인.
- **모듈·인스턴스를 빼는 변경**(예: Com 제거) — 설정 참조를 모두 끊고(`git grep`), 그 모듈의 **기존 생성물**(`Generated/Bsw_Output` 의 `<모듈>_Cfg.*`, `SchM_<모듈>*`, `PduR_<모듈>.h` 등)도 지운다. 생성기가 돌지 않으면 옛 파일이 남고 SCons 가 그것을 컴파일한다(jenkins-flow §5).
- **툴(Harmonize·CLI)을 썼으면** `Automation-Results/*.xls` 를 밖에 보관하고 판정표와 대조, 판정표에 없는 변경은 되돌리거나 확인(protected-settings §6).
- **ARXML 을 바꾼 직후** `protected_check.py --profile <프로필> --root <앱> --part FBL|APP --before-rev HEAD`.
- **버전업** → `version-up.md` + 프로필 위치 목록, `version_bump_check.py` 로 잔존 0.
- **Doc** — ReleaseNote·ModuleList 를 프로필 규칙으로.

## S9. 정적 검수 (빌드 전)

빌드는 6~50분 + push 가 필요하므로 여기서 잡을 수 있는 것은 잡는다(C Studio Generate Code 는 BSW·Os·Rte 만, MCAL 은 Jenkins 에서만 — jenkins-flow §3-1).

`review_all.py --prev … --cur … --app … --old-token … --new-token … --expect … --out 검수보고서.md` 를 먼저 돌린다. 설정 재대조(`three_way.py --check`), 모듈 바이트 일치, 심볼·매크로(`symbol_crosscheck.py`), 버전 잔존, 의존 .ver 목록, 빼낸 모듈의 남은 생성물을 한 보고서로 낸다. 이어서:

1. `--check` 남은 항목이 **전부 판정표의 제외·보류·당사 구성 사유와 1:1**인지 — 사유 없는 항목은 누락.
2. IM 신규 Validation 규칙을 당사 Ecud 에 미리 적용(예시 three-way §7).
3. `protected_check.py … --before-rev <작업 시작 커밋>` — 확인 필요 0 이거나 판정표 결정과 1:1.
4. 결과를 요약하고 커밋 지시를 기다린다.

보고서의 '확인'은 오류가 아니라 사람이 사유를 맞춰 볼 항목이다.

## S10. 빌드·빌드 검수

사용자가 지시하면 커밋·push 한다. 커밋 메시지 → `templates.md` §4. Hook 이 **커밋 제목**으로 빌드 동작을 정하므로 제목을 "Rebuild" 같은 단어 하나로 쓰지 않는다(jenkins-flow §1).

1. `jenkins_wait.py <job> <번호> --compare <직전 전체 생성 빌드>` 를 백그라운드로. 증분 빌드와는 비교하지 않는다.
2. 결과, 생성기 Error, Rte Validation(warnings 증감 설명), SAFERTE_ERR·종류별 WARN, 산출물 이름. 실패하면 로그의 첫 에러부터 원인을 찾고, **고치기 전에 원인 분석을 사용자에게 보인다.**
3. Auto commit 을 pull 하고 `gen_diff_review.py` 로 Generated 변화를 본다. 설정을 안 바꿨는데 바뀐 코드, 바꿨는데 안 바뀐 코드를 모두 설명한다. 보호 설정·기본값 의존 항목은 생성 코드의 실제 값 변화와 판정표 행을 잇는다. 변화가 있으면 원칙 8 대로 이력도 함께.
4. `map_mem.py` 로 RAM / ROM — 직전 값이 같은 방식으로 재현되는지 먼저.

빌드 인자를 붙인 `review_all.py` 로 S9 와 한 보고서로 낼 수 있다.

## S11. 기록·리뷰 대응

- **결과 코멘트** — `templates.md` §2 양식(HAE 요청 → 요청별 처리 표 → 적용 제외 사유 → 빌드 → 남은 작업). **등록될 원문 전체**를 보여 주고 승인 후 등록한다.
- **리뷰어 지적 대응** — 절차는 `templates.md` §2-1. 요지: 지적을 번호별 항목으로 나눈다 → 항목마다 현재 상태·원인·과거 이력(원칙 8)을 확인한다 → 사용자가 처리 방향을 정한다 → 처리·빌드한다. 회신은 사용자가 "다 처리한 뒤 한 번에"를 원하면 그때까지 쓰지 않는다. 회신은 지적 번호에 맞춘 단답형이고, 원문 요청(예: "변경 후 테스트")을 하지 않았으면 그 사실과 예정을 그대로 적는다.

## S12. 실기 검증

판정 기준 → `references/verification.md`, 실행 → 각 스킬과 프로필 체크리스트.

```
ALL 빌드 전환(지시 시 커밋) → 산출물 4벌 확인
→ 라이팅 (cvd-project, 양 뱅크) → CAN 출력 (can-bench-setup)
→ 진단 회귀 · 패치 고유 시험 (수평전개 결함 재현 조건)
→ 서명 요청 → H-OTA (hota-eval)
→ 결과 정리 → CURRENT 복귀 (지시 시 커밋)
```

정상 흐름 H-OTA 만으로는 패치 효과가 확인되지 않는다 — 수평전개 결함의 재현 조건을 케이스로 만든다. 서명 요청 뒤에는 실기가 끝날 때까지 APP 재빌드 push 를 하지 않는다. 진단 결과는 프로필의 CDD 주의사항을 먼저 본다.

## S13. 마무리

PR 방식·대상·머지 순서는 프로필, 브랜치 구성·검증은 `references/pr-assembly.md`. Redmine·IMS 상태 변경은 사용자 확인 후.

## 보고

단계를 마칠 때마다 짧게 보고한다. 형식과 이력 표기 → `communication.md` §6. 확인하지 못한 것(권한 없는 링크, 열지 못한 파일, 실기 미수행, 이력 미확인)은 따로 한 줄.

## 참고 문서 — 주제마다 한 곳

| 파일 | 담당 (이 주제의 규칙은 여기에만 둔다) |
|---|---|
| `references/communication.md` | 사람에게 보내는 모든 글 — 확인한 것만, 이름 고정표, 비교 문장, 두 종류의 이력, 보내기 전 점검, 단계 보고 형식 |
| `references/decision-rules.md` | 적용·보류 판단 규칙 (누적, 근거 포함) |
| `references/precheck.md` | P — 구성 전제, 완결성, 위험 포인트, 과거 자료 조사 순서, 작업 수단, 판단 경로 A~D, patch_tool 동작 |
| `references/three-way-merge.md` | S5·S6·S9 — 형상 확보, 판정 규칙·사례, 과거 회차 이력(§4.8), 판정표 형식(§6), 재대조·Validation |
| `references/protected-settings.md` | 보호 설정 — 덮어쓰기 세 경로, 변경 분류 (a)~(d), 단계별 할 일, Harmonize 절차 |
| `references/ims-workflow.md` | S1·S7 — IMS 에서 뽑을 것, 첨부 받기, 질문 등록, ECM IM 페이지 대응표, MCP 연결 시 |
| `references/templates.md` | 양식만 — Redmine 본문·결과 코멘트·리뷰 회신, IMS 질문, 수평전개 회신, 커밋 메시지, Confluence 골격 |
| `references/jenkins-flow.md` | S10·S12 — Hook, ALL/CURRENT, 산출물 구조, 생성 경로, 남은 생성물, 커밋 주의 |
| `references/verification.md` | 빌드 검수·실기 판정 기준, 결과 파일 규칙 |
| `references/version-up.md` | 버전 세 종류, 산출물명·버전 문자 위치 |
| `references/pr-assembly.md` | PR 브랜치 구성·검증 |
| `references/troubleshooting.md` | 실제 재작업 사례만 (단계순). 단계를 시작하기 전에 그 단계 행을 훑는다 |
| `references/projects/*.md` | 프로젝트 프로필 — 저장소·Job·버전 위치·구성 전제·보호 설정·고유 판단 이력 |

**문서를 고칠 때 규칙** — 새 함정은 `troubleshooting.md` 에 사례 한 행, 거기서 나온 규칙은 담당 문서 **한 곳**에만 쓰고 다른 곳에는 링크만 둔다. 프로젝트 하나에만 해당하면 프로필에. 작업이 끝날 때 이 추가를 사용자에게 제안한다.

## 범위 밖

- 작업 브랜치·Jenkins Job 신설 → gitea-jenkins-setup
- eCoDY-ECM·IMS 읽기·검색 → ecody-search (이 스킬은 IMS 댓글 쓰기만)
- 라이팅·CAN 측정 → cvd-project, can-bench-setup, canoe-project-setup
- H-OTA A·B 그룹 평가·산출물 → hota-eval
- Redmine 일감 단순 조회 → redmine-issue
- PR 머지, 공유 브랜치 정리
