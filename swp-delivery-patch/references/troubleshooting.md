# 실제 재작업 사례 (누적)

단계를 시작하기 전에 그 단계 행을 훑는다. 이 파일에는 **사례만** 둔다. 사례에서 나온 규칙은 "반영 위치" 칸의 문서 한 곳에만 쓴다.

**추가 방법** — 해당 단계 묶음의 맨 아래에 한 행을 넣는다. 칸마다 한두 문장으로 쓰고, 긴 설명은 반영 위치 문서에 둔다. 단계 순서(S0→S13)를 지킨다.

| 단계 | 일감·날짜 | 일어난 일 | 원인 | 예방 (반영 위치) |
|---|---|---|---|---|
| S1 | MCP0806-279/280 | 재배포본이 있는데 이전 파일로 작업할 뻔함 | 같은 이름 첨부 여러 개, HAE 가 이전 안내 댓글 삭제 | 첨부 날짜·크기·변경 이력 확인 (ims-workflow §1) |
| S1 | MCP0806-280 | 개정 안내에서 harmonize 대상이 바뀐 것을 놓칠 뻔함 | 같은 티켓에 안내 댓글이 다시 달림 | 안내 댓글 날짜순 정독, 항목별 최신값 (SKILL S1) |
| S1 | 279·280·272·256 등 | IM 링크가 권한 없음 | HAE IM 링크 일괄 이전(2026 하반기) | 새 제목으로 ECM 검색 (ims-workflow §4 대응표) |
| S1 | MCP1001-193 [27][28] | 배포본 `ModuleChangeList/*.xlsx` 가 열리지 않음(헤더 `SCDSA002`) | HAE 사내 DRM 암호화 상태로 배포 | IMS 에 해제본 요청 → `Doc.zip` 재첨부 받음 |
| S4·S13 | #47967 → #48891 | 리뷰어 지적 항목(infineon_ucb 삭제, 미사용 Routine)이 다음 회차까지 남음. #48891 본문에 "#48292 note-2~4 검토"를 적어 두고 결론을 내지 않음 | 직전 일감 지적사항 미이관, 일감 본문 검토 항목을 결과 코멘트에서 닫지 않음 | 일감 본문 "이전 회차 누락 반영" 절, 결과 코멘트에서 검토 항목마다 결론 (SKILL S4, templates §1) |
| S5 | MCP0806-280, #48891 10-12 | **재배포본만 쓰다가 이전본의 요청 누락.** CRC 대조(86개 중 84개 동일)만 보고 "10-06 본이 09-04 를 모두 포함"이라고 말해, 09-04 Ecud_EcuM 의 Crypto_76_HaeModule_Init ListOne 이동이 빠짐. 리뷰어 지적 후 `4a777484d` 로 반영 | CRC 는 개정 여부만 알려 줌. 안내 문구에서 빠진 것을 철회로 단정. 같은 날 문답과의 불일치를 놓침 | CRC 다른 파일 내용 비교, 이전본 전용 설정은 철회 확인 항목 (decision-rules 공통, SKILL S5) |
| S6 | v3.0.27 #48881, 10-12 지적 | **patch_tool Action Report 만 기준으로 삼아 참고 설정의 변경 누락.** SCons `Swcd_Bsw_Dem` 의 `Dcm_ECU_Configuration_PDF` 가 HE1i 에 없었음. missing 목록을 뽑아 놓고 "레퍼런스 프로젝트라 다름"으로 묶어 넘김 | Report 는 자기 모듈 PDF 자동 추가 기록뿐. Prev 없이 2-way 로 해 HAE 델타와 SP3i 고유 차이를 가르지 못함 | 차이 항목별 분류, Prev 없으면 직전 회차 배포본으로 3-way (SKILL S5-4·S6 체크리스트, three-way §2) |
| S6 | MCP0806-256/279, #48891 note-21 | **이번 배포본이 이전 회차 보정을 되돌렸는데 "기존 충족"으로 통과.** 3.0.18 08-31 보정본은 PMem_Driver_StartUp 을 EcuM ListTwo 로 옮겼는데 3.0.19 배포본은 BswM 방식. HE1i 가 3.0.19 와 같아 넘어감 | 3-way 는 이번 회차 델타만 봄. Prev(3.0.18+보정본)→Cur 의 "EcuM→BswM" 을 HAE 의도로 봄 | 모든 행 과거 회차 이력 대조, 되돌림 의심은 사용자 확인·C 경로 (기본 원칙 8, three-way §4.8) |
| S6 | 이전 담당자 경험 | HAE 참고 설정을 그대로 넣어 당사 로직 문제 | 참고 프로젝트 기준 설정 | 3-way 판정, 통째 복사 금지 (기본 원칙 2) |
| S6 | MCP0806-280 | 참고 설정의 새 PDF 입력이 당사에 없는 파일 | HAE 참고 프로젝트의 다른 모듈 버전(Crypto 2.0) | patch_tool 주석으로 이유 확인 → 제외, 묶음 판정 (three-way §4.4, decision-rules 공통) |
| S7 | MCP0806-280, 10-12 | **IMS 질문이 거꾸로 읽히고, 확인하지 않은 전제가 들어감.** "참고 SCons 에 IM 표준에 없는 항목"을 HAE 가 "당사 누락"으로 읽음. CDD_Router 초기화를 파일을 열지 않고 전제로 씀 | 모호한 이름("참고 형상"), 한 문장에 세 곳을 섞음, 추정을 사실처럼 | 확인한 것만·이름 고정표·"A 에는 있고 B 에는 없다" (communication §1~3) |
| S8 | #38061 | 모듈 폴더 통째 교체로 당사 수정 소실 위험 | 당사가 HAE 모듈 파일을 직접 수정(CanTrcv) | `owner_edits.py` 로 교체 전 확인 (three-way §5.1, 프로필) |
| S8 | FBL V3.0.19 시험 10-10 | **Harmonize 기본 옵션이 당사 수동 값을 덮어씀** — CanIfMetaDataSupport 1→0, CanFdPaddingValue 0 명시, Rx 버퍼 10→64 등. 결과가 VC 와 같았음 | Overwrite / Remove Invalid / Auto-Regeneration 기본 켬, 내역은 git 무시 폴더 xls 에만 | 시험 브랜치, xls 보관, `protected_check.py` (protected-settings §6) |
| S8 | v3.0.28 `434a0c2c0`, 10-12 지적 | 보정 zip 을 풀다가 `Build\bat_package\bat_package\` 로 한 단계 더 생김 | zip 최상위 폴더 미확인, diff 의 `{ => bat_package}/` rename 을 못 봄 | `unzip -l` 확인, `git diff --cached -M --summary` (SKILL S8) |
| S8 | — | 산출물명이 다른 차종 이름(sx3e_)으로 나옴 / UTIP Writing·aSIMs ini 누락으로 재빌드 | `.project` 미변경, 위치 목록 일부만 변경 | 위치 목록 전부, `version_bump_check.py` (version-up, 프로필) |
| S8 | — | sed 로 고친 파일 줄바꿈 경고 / 경로 문자열의 `\v` 가 제어문자로 바뀜 | LF·CRLF 혼재, 파이썬 이스케이프 | `git diff --stat` 줄 수 확인, raw 문자열·`os.sep`, 쓰기 후 제어문자 검사 (SKILL S8) |
| S10 | #47967 | Jenkins 후처리가 건너뛰어 rom/차종 산출물 없음 | Hook 이 Post-build 미실행 | 과제 Hook·PostPackage 분리 (jenkins-flow §1) |
| S10 | — | 증분 빌드와 비교해 경고 수가 의미 없음 | 비교 대상 빌드에 Generate 없음 | 직전 회차 전체 재생성 빌드와 비교 (SKILL S10) |
| S10 | #48891 Jenkins #18, 10-12 | **설정에서 모듈을 뺐는데 이전 생성물이 남아 컴파일 실패.** FBL Com 제거 후 `Com_Cfg.c: cannot open source file "Com.h"`. 남은 생성물 5개 삭제(`3e94476b`) 후 #19 성공 | SCons 가 `Generated/Bsw_Output` 의 추가 파일도 컴파일. Com 생성기가 돌지 않아 10-08 생성물이 남음 | 모듈을 빼면 생성물도 삭제, 빌드 후 작업 폴더 생성물 날짜 확인 (SKILL S8, jenkins-flow §5, review_all) |
| S10 | — | javascript_tool 결과가 잘리거나 "Cookie/query string data" 로 차단 | 반환값 길이·필터 | DOM 에 펼쳐 get_page_text (ecody-search) |
| S11 | — | 요약만 보여 주고 등록 원문으로 착각하게 함 | 미리보기 대신 설명 제시 | 등록될 원문 전체를 보여 줌 (SKILL S11) |
| S11 | #48891 note-21, 10-12 | **리뷰어가 "False 로 변경 후 테스트"를 요청했는데 "유지"로 회신할 뻔함.** 바꾸면 리프로그래밍이 실패할 거라는 분석만으로 정함. "기존에도 False 였나"도 어느 시점인지 확인 없이 답함 | 원문 요청과 회신을 대조하지 않음, 분석을 시험 결과처럼 다룸, 이력 기준 시점 모호 | 회신 전 원문 요청 대조, 하지 않은 일은 그대로 적기, 두 시점 값 병기 (communication §4·§5, templates §2-1) |
| S12 | #48891 #32/#33/#34 | **서명받은 이미지와 저장소 이미지가 달라짐** — 서명 후 push 로 재빌드되어 `.s19` 10바이트 다름 | Os 생성기가 재생성 때 태스크 스택 배치 순서를 바꿈 → `MAINSW_CRC` 변경 | 서명 후 실기 끝까지 APP 재빌드 push 금지, 바이트 비교 (jenkins-flow §3, verification §2) |
| S12 | — | 한쪽 뱅크만 기록 → E_NOTMATCHED_DESTINATION | 라이팅 옵션 | 양 뱅크 기록 (verification §2) |
| S12 | — | `.asc.asc` 확장자 중복 / 보고서에 이전 회차 첨부 잔존 | 저장 대화상자, 템플릿 복사 | 파일명 규칙, 이번 회차 파일로 교체 (verification §3) |
| S12 | #48881 | BG 리프로그래밍 1차 E_INVALIDRESPONSE | 간헐 | 재실행 후 기록 |
| S12 | #48909 | 리셋 중 레스트버스 송신 막힘 | 실험대 ACK 노드 부재 | 리셋 동안 1초 정지, 실험대 특이사항으로 기록 (verification §2) |
| S12 | — | ALL 전환 후 CURRENT 복귀 누락 위험 | 평가 끝난 뒤 잊음 | 실기 마지막 단계에 복귀 커밋 체크 (jenkins-flow §2) |

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
| 모듈을 뺀 뒤 `<모듈>_Cfg.c` 에서 헤더 없음 | 이전 생성물이 남아 컴파일됨 → 그 모듈 생성물 삭제 | #48891 #18 (위 S10) |
