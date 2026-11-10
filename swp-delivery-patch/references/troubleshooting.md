# 실제 재작업 사례 (누적)

단계를 시작하기 전에 그 주제의 행을 훑는다. 이 파일에는 **사례만** 둔다. 사례에서 나온 규칙은 "반영 위치" 칸의 문서 한 곳에만 쓴다.

**추가 방법** — 해당 주제 묶음의 맨 아래에 한 행을 넣는다. 칸마다 한두 문장으로 쓰고, 긴 설명은 반영 위치 문서에 둔다. 주제 순서(준비 → 수집 → 형상 → 판정 → 질문 → 적용 → 빌드 → 기록 → 실기)를 지킨다.

| 주제 | 일감·날짜 | 일어난 일 | 원인 | 예방 (반영 위치) |
|---|---|---|---|---|
| 준비 | #48891 note-21, 10-12 | **patch_tool 을 읽지 않아 거기 적힌 보정을 놓침.** FBL PMem_Driver EcuM ListTwo 규칙이 3.0.19 patch_tool `Dcm/patch_Dcm_common.py` 3번과 3.0.18 `Mem_76_Pfls_Common v2.1.0.0` [7] 에 있었다. Com 제거도 `Integrator common` 11번에 목록이 있었다 | 툴을 "쓰지 않는다"를 "읽지 않는다"로 다룸. 배포본 참고 설정만 대조 | P 단계 첫 작업으로 `patch_tool_plan.py` 계획서, 항목을 판정표로 (apply §2, SKILL 대응표) |
| 수집 | MCP0806-279/280 | 재배포본이 있는데 이전 파일로 작업할 뻔함 | 같은 이름 첨부 여러 개, HAE 가 이전 안내 댓글 삭제 | 첨부 날짜·크기·변경 이력 확인 (ims-workflow §1) |
| 수집 | MCP0806-280 | 개정 안내에서 harmonize 대상이 바뀐 것을 놓칠 뻔함 | 같은 티켓에 안내 댓글이 다시 달림 | 안내 댓글 날짜순 정독, 항목별 최신값 (ims-workflow §1) |
| 수집 | 279·280·272·256 등 | IM 링크가 권한 없음 | HAE IM 링크 일괄 이전(2026 하반기) | 새 제목으로 ECM 검색 (ims-workflow §4 대응표) |
| 수집 | MCP1001-193 [27][28] | 배포본 `ModuleChangeList/*.xlsx` 가 열리지 않음(헤더 `SCDSA002`) | HAE 사내 DRM 암호화 상태로 배포 | IMS 에 해제본 요청 → `Doc.zip` 재첨부 받음 |
| 기록 | #47967 → #48891 | 리뷰어 지적 항목(infineon_ucb 삭제, 미사용 Routine)이 다음 회차까지 남음. #48891 본문에 "#48292 note-2~4 검토"를 적어 두고 결론을 내지 않음 | 직전 일감 지적사항 미이관, 일감 본문 검토 항목을 결과 코멘트에서 닫지 않음 | 일감 본문 "이전 회차 누락 반영" 절, 결과 코멘트에서 검토 항목마다 결론 (templates §1) |
| 형상 | MCP0806-280, #48891 10-12 | **재배포본만 쓰다가 이전본의 요청 누락.** CRC 대조(86개 중 84개 동일)만 보고 "10-06 본이 09-04 를 모두 포함"이라고 말해, 09-04 Ecud_EcuM 의 Crypto_76_HaeModule_Init ListOne 이동이 빠짐. 리뷰어 지적 후 `4a777484d` 로 반영 | CRC 는 개정 여부만 알려 줌. 안내 문구에서 빠진 것을 철회로 단정. 같은 날 문답과의 불일치를 놓침 | CRC 다른 파일 내용 비교, 이전본 전용 설정은 철회 확인 항목 (decision-rules 공통, three-way §2.1) |
| 판정 | v3.0.27 #48881, 10-12 지적 | **patch_tool Action Report 만 기준으로 삼아 참고 설정의 변경 누락.** SCons `Swcd_Bsw_Dem` 의 `Dcm_ECU_Configuration_PDF` 가 HE1i 에 없었음. missing 목록을 뽑아 놓고 "레퍼런스 프로젝트라 다름"으로 묶어 넘김 | Report 는 자기 모듈 PDF 자동 추가 기록뿐. Prev 없이 2-way 로 해 HAE 델타와 SP3i 고유 차이를 가르지 못함 | 차이 항목별 분류, Prev 없으면 직전 회차 배포본으로 3-way (three-way §2·§6) |
| 판정 | MCP0806-256/279, #48891 note-21 | **이번 배포본이 이전 회차 보정을 되돌렸는데 "기존 충족"으로 통과.** 3.0.18 08-31 보정본은 PMem_Driver_StartUp 을 EcuM ListTwo 로 옮겼는데 3.0.19 배포본은 BswM 방식. HE1i 가 3.0.19 와 같아 넘어감 | 3-way 는 이번 회차 델타만 봄. Prev(3.0.18+보정본)→Cur 의 "EcuM→BswM" 을 HAE 의도로 봄 | 모든 행 과거 회차 이력 대조, 되돌림 의심은 사용자 확인·C 경로 (기본 원칙 9, three-way §4.8) |
| 판정 | 이전 담당자 경험 | HAE 참고 설정을 그대로 넣어 당사 로직 문제 | 참고 프로젝트 기준 설정 | 3-way 판정, 통째 복사 금지 (기본 원칙 2) |
| 판정 | MCP0806-280 | 참고 설정의 새 PDF 입력이 당사에 없는 파일 | HAE 참고 프로젝트의 다른 모듈 버전(Crypto 2.0) | patch_tool 주석으로 이유 확인 → 제외, 묶음 판정 (three-way §4.4, decision-rules 공통) |
| 판정 | #49949·#49951, 11-09~10 | **규칙은 있는데 수행하지 않아 하루에 네 건이 샘.** A 경로 항목을 "전제"로 적어 두고 닫지 않음, 짝 일감(FBL→APP) 문장을 값 재확인 없이 옮겨 적음, HAE 표기를 당사 파일명으로 확정 | 전제를 결론 칸에 적으면 빈 칸이 아니게 되어 확인 동기가 사라진다. 판정표가 산문이라 **사실을 사람이 타이핑**했다 | 판정표를 데이터로 바꿨다 — 사실 칸은 생성되고 사람은 경로·처리만 채운다. `three_way.py --json` → `issue_table.py --probe --strict` (three-way §6) |
| 질문 | MCP0806-280, 10-12 | **IMS 질문이 거꾸로 읽히고, 확인하지 않은 전제가 들어감.** "참고 SCons 에 IM 표준에 없는 항목"을 HAE 가 "당사 누락"으로 읽음. CDD_Router 초기화를 파일을 열지 않고 전제로 씀 | 모호한 이름("참고 형상"), 한 문장에 세 곳을 섞음, 추정을 사실처럼 | 확인한 것만·이름 고정표·"A 에는 있고 B 에는 없다" (communication §1~3) |
| 적용 | #38061 | 모듈 폴더 통째 교체로 당사 수정 소실 위험 | 당사가 HAE 모듈 파일을 직접 수정(CanTrcv) | `owner_edits.py` 로 교체 전 확인 (three-way §5.1, 프로필) |
| 적용 | FBL V3.0.19 시험 10-10 | **Harmonize 기본 옵션이 당사 수동 값을 덮어씀** — CanIfMetaDataSupport 1→0, CanFdPaddingValue 0 명시, Rx 버퍼 10→64 등. 결과가 VC 와 같았음 | Overwrite / Remove Invalid / Auto-Regeneration 기본 켬, 내역은 git 무시 폴더 xls 에만 | 시험 브랜치, xls 보관, `protected_check.py` (protected-settings §6) |
| 적용 | v3.0.28 `434a0c2c0`, 10-12 지적 | 보정 zip 을 풀다가 `Build\bat_package\bat_package\` 로 한 단계 더 생김 | zip 최상위 폴더 미확인, diff 의 `{ => bat_package}/` rename 을 못 봄 | `unzip -l` 확인, `git diff --cached -M --summary` (apply §3) |
| 적용 | — | 산출물명이 다른 차종 이름(sx3e_)으로 나옴 / UTIP Writing·aSIMs ini 누락으로 재빌드 | `.project` 미변경, 위치 목록 일부만 변경 | 위치 목록 전부, `version_bump_check.py` (apply §6, 프로필) |
| 적용 | — | sed 로 고친 파일 줄바꿈 경고 / 경로 문자열의 `\v` 가 제어문자로 바뀜 | LF·CRLF 혼재, 파이썬 이스케이프 | `git diff --stat` 줄 수 확인, raw 문자열·`os.sep`, 쓰기 후 제어문자 검사 (apply §3) |
| 적용 | #49949 Jenkins #7, 11-09 (LT2 TPMS FBL) | **항목을 다른 컨테이너로 옮기고 빈 컨테이너를 남겨 생성이 멈춤.** KeyM 초기화를 EcuM `ListThree` → `ListTwo` 로 옮긴 뒤 빈 `EcuMDriverInitListThree` 를 남겨 `ERR000012 Expected min 1 subcontainers ... Found 0` → `ERR000029 [EcuM] Validation FAILED`. 빌드가 38초에 멈춰 `Generated` 가 갱신되지 않아 그 회차의 생성 코드 확인도 함께 밀렸다 | 컨테이너는 `LOWER=0`(선택)인데 그 안의 항목은 `LOWER=1`. "컨테이너째 지우거나 항목을 채우거나" 둘 중 하나인데 빈 채로 둠 | 마지막 항목을 빼면 **컨테이너도 함께 지운다**. 정의의 다중도를 먼저 읽고, 배포본 참고 설정에 그 컨테이너가 있는지로 가른다 (apply §3) |
| 빌드 | #47967 | Jenkins 후처리가 건너뛰어 rom/차종 산출물 없음 | Hook 이 Post-build 미실행 | 과제 Hook·PostPackage 분리 (jenkins-flow §1) |
| 빌드 | — | 증분 빌드와 비교해 경고 수가 의미 없음 | 비교 대상 빌드에 Generate 없음 | 직전 회차 전체 재생성 빌드와 비교 (verification §2) |
| 빌드 | #48891 Jenkins #18, 10-12 | **설정에서 모듈을 뺐는데 이전 생성물이 남아 컴파일 실패.** FBL Com 제거 후 `Com_Cfg.c: cannot open source file "Com.h"`. 남은 생성물 5개 삭제(`3e94476b`) 후 #19 성공 | SCons 가 `Generated/Bsw_Output` 의 추가 파일도 컴파일. Com 생성기가 돌지 않아 10-08 생성물이 남음 | 모듈을 빼면 생성물도 삭제, 빌드 후 작업 폴더 생성물 날짜 확인 (apply §3, jenkins-flow §5, review_all) |
| 빌드 | #49949, 2026-11-03 (LT2 TPMS FBL) | **Com 을 쓰지 않는 FBL 인데 BswM 생성물이 `Com.h` 를 include 해 컴파일 실패.** `BswM_Cfg.c`(line 64)·`BswM_ActionList.c`·`BswM_Rule.c` 에서 `fatal error #2330: cannot open source file "Com.h"` → `scons: *** [BswM_Cfg.o] Error 1` (로컬 빌드 로그에서 확인) | **원인 미확정** — 조치 근거 티켓 MCP0858-296 은 권한 없음(2026-11-07). 위 HE1i 사례와 증상은 같지만 경로가 다를 수 있다 | 세 자리를 함께 본다 — SCons ExcludeList 의 `Com_R44`(삭제가 아니라 제외) · BswM `AC_UserCallout_Com_DeInit` · BswM `BswMUserIncludeFiles` 의 `Com.h`. Harmonize 가 되살렸는지도 확인 (protected-settings, 일감 #49949 `Q8`) |
| 빌드 | — | javascript_tool 결과가 잘리거나 "Cookie/query string data" 로 차단 | 반환값 길이·필터 | DOM 에 펼쳐 get_page_text (ecody-search) |
| 기록 | — | 요약만 보여 주고 등록 원문으로 착각하게 함 | 미리보기 대신 설명 제시 | 등록될 원문 전체를 보여 줌 (templates §2) |
| 기록 | #48891 note-21, 10-12 | **리뷰어가 "False 로 변경 후 테스트"를 요청했는데 "유지"로 회신할 뻔함.** 바꾸면 리프로그래밍이 실패할 거라는 분석만으로 정함. "기존에도 False 였나"도 어느 시점인지 확인 없이 답함 | 원문 요청과 회신을 대조하지 않음, 분석을 시험 결과처럼 다룸, 이력 기준 시점 모호 | 회신 전 원문 요청 대조, 하지 않은 일은 그대로 적기, 두 시점 값 병기 (communication §4·§5, templates §2-1) |
| 실기 | #48891 #32/#33/#34 | **서명받은 이미지와 저장소 이미지가 달라짐** — 서명 후 push 로 재빌드되어 `.s19` 10바이트 다름 | Os 생성기가 재생성 때 태스크 스택 배치 순서를 바꿈 → `MAINSW_CRC` 변경 | 서명 후 실기 끝까지 APP 재빌드 push 금지, 바이트 비교 (jenkins-flow §3, verification §2) |
| 실기 | — | 한쪽 뱅크만 기록 → E_NOTMATCHED_DESTINATION | 라이팅 옵션 | 양 뱅크 기록 (verification §2) |
| 실기 | — | `.asc.asc` 확장자 중복 / 보고서에 이전 회차 첨부 잔존 | 저장 대화상자, 템플릿 복사 | 파일명 규칙, 이번 회차 파일로 교체 (verification §3) |
| 실기 | #48881 | BG 리프로그래밍 1차 E_INVALIDRESPONSE | 간헐 | 재실행 후 기록 |
| 실기 | #48909 | 리셋 중 레스트버스 송신 막힘 | 실험대 ACK 노드 부재 | 리셋 동안 1초 정지, 실험대 특이사항으로 기록 (verification §2) |
| 실기 | — | ALL 전환 후 CURRENT 복귀 누락 위험 | 평가 끝난 뒤 잊음 | 실기 마지막 단계에 복귀 커밋 체크 (jenkins-flow §2) |

## 보고 — 당사 실측 사례

| 증상 | 원인 | 조치 |
|---|---|---|
| 사용자가 "어떻게 작성했는지 여기 출력하라" 고 함 | 스크립트 미리보기를 세 번 찍고 "미리보기 그대로입니다" 로 가리켰다. **도구 출력은 사용자 화면에 보이지 않는다** | 승인 대상 글은 답변 본문에 전문을 싣는다 (`communication.md` §0) |
| 사용자가 "무슨 말인지 모르겠다" 고 함 | 내 편집 전후 diff·수정 내역을 설명했다. 사용자는 **결과물**만 알면 된다 | 내가 무엇을 고쳤는지가 아니라 **지금 무엇을 승인해야 하는지**를 쓴다 |
| "권고 2, 3 같은 말은 왜 적었나" | 값 두 개 중 하나를 고르는 질문에 `선택지`·`권고` 양식을 기계적으로 끼웠다 | 양식은 판단이 갈리는 건에만 쓴다. 값 선택 질문은 **두 값과 각 근거, 그리고 질문 한 줄** |
| "무엇에 대한 것인지는 알려줘야지" | 질문만 적고 어떤 패치·어디까지 진행됐는지를 뺐다 | 코멘트 머리에 **무슨 건인지 / 진행 상황 / 묻는 이유** 세 줄 |

## 빌드·검수 — 당사 실측 사례

| 증상 | 원인 | 조치 |
|---|---|---|
| 빌드 SUCCESS, `ERR` 0건인데 교체한 모듈의 신규 Validation 이 하나도 안 걸림 | 증분 빌드가 그 모듈을 생성기 `-M` 목록에서 뺐다. `ERR` 0건은 **미수행** | `BuildType=Rebuild`(= `do_clean()`)로 재실행. `Validation SUCCESS` 모듈 목록으로 수행 여부를 확인 (#49951 빌드 #3) |
| 빌드 SUCCESS 인데 `.s19` 가 만들어지지 않고, 이어진 Auto commit 이 저장소의 `.s19` 를 지움 | `.utp` 가 낡은 산출물명(`..._v2110.sre`)을 LOAD 하는데 `Rebuild` 가 `Debug/` 를 지워 그 파일이 없었다. `UTIP_FAIL` 은 훅의 성패에 반영되지 않는다 | `.utp` 의 LOAD 경로를 버전업한다. 버전업 단계에서 `version_bump_check.py` 를 돌리면 사전에 걸린다 (#49951 빌드 #4) |
| 증분 빌드가 `UTIP_SUCCESS` 인데 `.s19` 내용이 구 버전 | `Debug/` 에 남아 있던 직전 회차 `.sre` 를 읽었다. 로그만 보면 정상으로 보인다 | 같음 — `.utp` 버전업. 산출물 해시를 패치 전과 대조해 실제로 바뀌었는지 본다 (#49951 빌드 #3) |
| 설정 파일(`.utp`·문서·바이너리)만 바꾼 커밋의 빌드가 FAILURE, 산출물이 커밋되지 않음 | 재컴파일할 것이 없어 새 `.elf` 가 없고, 훅이 `No new .elf file - treated as build failure.` 로 Git Push 를 건너뛴다 | 산출물을 저장소에 넣어야 하면 `BuildType=Rebuild` 로 다시 돌린다 (#49951 빌드 #5) |
| `jenkins_wait.py` 가 "생성기 실행 0회", "Validation 오류 없음"으로 보고 | Toolset 3.0.3 의 문구가 `INF000004: <0> Error(s)...` 로 숫자가 꺾쇠 안이고, 모듈별 Validation 수행 여부를 보지 않았다 | 2026-11-10 스크립트 수정(정규식·모듈 목록·UTIP·훅 ERROR LEVEL 추가). 백업 `jenkins_wait.py.bak` |
| `Ecud_Rte.arxml` 에서 배포본 안내대로 BswInstance 를 개명했더니 SHORT-NAME 중복 | 같은 이름의 인스턴스가 파일 뒤쪽에 이미 있었다(MCAL 쪽 하나 + HAE 모듈 쪽 하나) | 개명하지 않고 그대로 둔다. 개명 안내를 받으면 **그 이름이 파일에 이미 있는지 먼저 grep** (#49951) |
| `Ecud_Dem_Mcal.arxml` DemEventId 를 IA-068 대로 맞추니 다른 이벤트와 번호 충돌 | 미사용 Eth 이벤트가 그 번호대를 쓰고 있었다 | 충돌하는 쪽을 빈 번호로 옮기고, 유지/제외 판단은 당사 담당자에게 질의 (#49951) |
| FBL 에서 `BswM` 생성물이 `Com.h` 를 include 해 빌드 실패(`Com.h` 미발견), 같은 설정의 APP 은 통과 | `BswM/BswMGeneral/BswMUserIncludeFiles` 에 `Com.h` 항목이 남아 있다. **FBL 은 `Generation/Com` 을 `Used=False` 로 꺼서 헤더가 생기지 않고**, APP 은 Com 을 컴파일에서만 제외(`ExcludeList`)하고 모듈 폴더를 그대로 둬 `Static_Code/Modules/Com_R44/delivery/inc/Com.h` 가 남아 있다 | `BswMUserIncludeFiles` 의 `Com.h` 를 지운다. ⚠ **harmonize 가 되살리므로** 배포본 `bswm_post_harmonize.py` 를 직접 돌려 다시 지운다. APP 은 지금 안 깨지지만 **`Generation/Com` 을 끄면 같은 실패가 난다** — Com 제외 작업을 할 때 이 항목을 함께 본다 (#49949 FBL 2026-11-03·11-09, #49951 APP 확인) |
| 패치 스크립트가 참조로 거는 ECM 문서가 정리 페이지에 없어 적용 여부를 알 수 없다 | 문서 조건이 "○○.arxml **설정 변경 시**" 인 경우가 많다 | **문서를 못 열어도 전제부터 본다** — 그 파일이 이번 회차에 실제로 바뀌었는지 `git diff` 로 확인한다. 변경 0건이면 해당 없음으로 닫히고 문서를 구할 필요가 없다. 실측 — ECM `334008428`(`Ecud_Dcm.arxml` 변경 시 `Bswmd_BswM.arxml` 수동 설정)은 `Ecud_Dcm.arxml` 변경 0건으로 해당 없음 (#49951) |
| HAE `mobilgene_executor.py` 로 harmonize 를 돌렸는데 `PRE-Harmonize : OK` 가 찍히고 **실제로는 아무것도 안 바뀜** | 윈도우 콘솔이 cp949 라 실행기의 출력 읽기 스레드가 `UnicodeEncodeError: 'cp949' codec can't encode character` 로 **죽는다**(`mobilgene_executor.py:369` 의 `print`). CLI 스크립트가 `PREHarmonize.json`·`GENHarmonize.json` 을 못 만들고, 실행기는 `if not pre_json.exists(): return True` 로 **건너뛰며 성공을 돌린다** | 드라이버를 `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` 로 실행한다. ⚠ **끝났다고 말하기 전에 `References/MIA/json/` 에 `PREHarmonize.json`·`GENHarmonize.json` 이 실제로 생겼는지 본다** — 없으면 돌지 않은 것이다. `OK` 는 근거가 아니다 (#49951 2026-11-10) |
| CLI 로그에 `mobilgene Studio Terms of Service / Please read the following terms carefully` 가 찍힌다 | `-AgreeTermsEarlyCLI y` 는 **약관을 출력하고 기다리지 않는** 것이다(Agree Terms **Early**). 멈춘 것이 아니다 | 정상이다. 이 줄을 보고 "사용자 동의가 필요하다" 고 판단하지 않는다. **인자 없이** 맨손으로 부를 때만 `(y/n) :` 에서 실제로 멈춘다 (#49951) |
| 배경 실행의 종료코드가 0 인데 로그 끝에 파이썬 traceback 이 있다 | `python x.py > log 2>&1` 뒤에 `echo` 를 붙이면 보고되는 종료코드가 **`echo` 것**이다 | 파이썬을 그 명령의 마지막(또는 유일한) 명령으로 둔다. 로그 **끝 10줄**을 읽고 판단한다 — 종료코드만 보지 않는다 (#49951) |

## 빌드 오류 — 다른 담당자 사례 (IMS)

| 증상 | 원인 / 해결 | 근거 |
|---|---|---|
| Os 모듈 컴파일 에러 (Os_CYTXXX_R44) | 폴더명 대소문자 `Os_CYTxxx_R44` 로, SCons Compile 경로도 소문자. bat 은 AUTOSAR44=1 이면 영향 없음 | MCP0806-270 [14][16] |
| Os_Arch_SystemCall.h 어셈블 에러 | SCons DefaultCompileOption 에 `--gnu_asm` 추가 (HAE 배포본은 BSW 옵션에 이미 있음) | MCP0806-270 [17][18] |
| `.text` 가 `.LIB_CODE` 침범 overlap, "too many user-defined sections" 경고 | GHS 2017 은 사용자 섹션 94개 초과 시 .text 로 몰림. MPU 미사용이면 SC1 + .ld 의 MPU용 ABS 제거로 해결. 경고는 MPU 미사용 시 무시 | MCP0806-270 [36]~[45] |
| SCons `Compile/CompileCmdChoice/Compile` unresolved proxy | Compile 컨테이너는 toolset 3.0.3 부터 미사용(Build 하나로 통합). 삭제해도 되고 두어도 동작 | MCP0806-272 [22] |
| toolset 2.x → 3.x 패치 후 `Build/site_scons` 에 `.pyc` 가 없음 / Compile 옵션 사라짐 | 3.x 는 Python 3.12 가상환경으로 `.py` 를 직접 실행. 기존 `site_scons` 를 지우고 새것으로 교체, SCons Compile 컨테이너 삭제 | MCP1001-193 [9][10][15][17] |
| 패치 후 Os 관련 빌드 에러가 HAE 에서는 재현 안 됨 | 모듈 폴더가 잘못 복사됨 → 폴더 완전 삭제 후 배포본에서 다시 복사, Rebuild | MCP1105-105 [16] |
| Os 신규 Validation (SC3/4) | Task 스택은 2^n, 32 이상. .ld 의 task stack 은 Ecud_Os 최대값 | MCP1105-104 [8][12] |
| 사용 안 하는 callout 설정 에러 (FlashcMain…Callout) | 모듈에서 함수 삭제됨 → 설정에서도 제거 (IA-057) | MCP0806-255 [10][11] |
| 모듈을 뺀 뒤 `<모듈>_Cfg.c` 에서 헤더 없음 | 이전 생성물이 남아 컴파일됨 → 그 모듈 생성물 삭제 | #48891 #18 (위 빌드 행) |
| FBL 산출물 | `References/FBL_Output/OEUK_*/` 에 `.elf`·`.hex`·`.map`·`.sre` 만 넣고 **`.dla`·`.dnm` 을 빠뜨렸다** | 세트가 6종인 것을 기억으로 했다. 이 둘은 GHS `-dual_debug` 가 만드는 디버그 정보라 **플래시에 올라가지 않아 빌드·Validation·실기 전부 통과한다** | ⭐ `fbl_output_check.py --root . --fbl-root <FBL 저장소>` 를 회차마다 돌린다. 세트 목록은 프로필 `FBL 산출물 등록` 절에 적혀 있다. 커밋 메시지에 "확인 필요"로 적는 것으로는 막히지 않았다(2026-11-10 #49951) |
| FBL 산출물 | `OEUK_LT2` 폴더에 `e_bj_...` 이름을 넣어 폴더와 파일의 차종이 어긋났다 | FBL 빌드 산출물명은 OEUK 선택과 무관하게 고정(`e_bj_...`)인데 그대로 복사했다 | 그 폴더의 **직전 버전 이름**을 보고 맞춘다. 폴더 이름에서 유추하지 않는다 — `OEUK_TEST` 는 차종이 아니다. `fbl_output_check.py` 의 §2 가 본다 |
| 보고·질문 | 배포본 patch_tool 을 돌려서 나온 `DcmTaskTime 0.01 vs 0.005` 를 **담당자 확인 목록에 올렸다** | 항목에 출처를 적지 않아 "도구를 돌려서 나온 것" 과 "안내가 글로 요청한 것" 이 한 목록에 섞였다. **담당자 기준으로 도구 산물은 참조일 뿐 작업의 고려 대상이 아니다** - 물을 필요가 없는 항목이었다 | 항목마다 `[안내 요청]`/`[도구 산물]`/`[부산물]`/`[당사 판단]` 을 붙이고, 보내기 전 **항목 수와 라벨 수가 같은지 센다**. 가르는 기준은 안내 `2 설정변경` 에 그 줄이 있는지 하나다(IA 번호 유무가 아니다) -> `communication.md` 7 |
