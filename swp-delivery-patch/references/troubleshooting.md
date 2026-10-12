# 실제 재작업 사례 (누적)

단계를 시작할 때 해당 단계 행을 먼저 훑는다. 새 사례는 맨 아래에 추가한다.

| 단계 | 일어난 일 | 원인 | 예방 |
|---|---|---|---|
| S1 | 재배포본이 있는데 이전 파일로 작업할 뻔함 | 같은 이름 첨부 여러 개, HAE 가 이전 안내 댓글 삭제 | 첨부 날짜·크기·변경 이력 확인, CRC 대조로 유효본 판정 (MCP0806-279/280) |
| S5 | **재배포본만 쓰다가 이전본의 요청 누락.** MCP0806-280 09-04 본 → 10-06 본에서 CRC 대조 "86개 중 84개 동일, SCons·Ecud_EcuM 만 다름"만 보고 "10-06 본이 09-04 를 모두 포함"이라고 사용자에게 말했다. 사용자는 10-06 본만 풀어 줬다. 실제로는 09-04 Ecud_EcuM 의 `Crypto_76_HaeModule_Init` ListOne 이동(Index 29)과 ListTwo 삭제가 10-06 본에서 빠져 있었다. 10-06 개정 안내 문구에서도 빠졌지만 Crypto IM 링크는 남아 있었다. HE1i v3.0.29 에 반영되지 않았고, 2026-10-12 유수진 책임이 지적했다 (#48891) | CRC 는 파일 개정 여부만 알려 줌. 다른 파일 안의 "이전본에만 있는 설정"을 보지 않음. 안내 문구에서 빠진 것을 철회로 단정. 같은 날 문답(ListTwo HsmDriver 0 / Mem_ReadAll 1 = Crypto 없는 구성)과의 불일치를 놓침 | CRC 가 다른 파일은 `three_way.py --prev 이전본 --cur 새본` 으로 내용 비교. 이전본에만 있는 설정은 철회 확인 항목으로 판정표에 올림. IM 링크 본문·같은 날 문답과 대조. "이전본 불필요"는 비교 결과를 보인 뒤에만 말함 |
| S6 | **patch_tool Action Report 만 기준으로 삼아 참고 형상의 변경 누락.** SCons `Swcd_Bsw_Dem` InputFilesList 의 `Dcm_ECU_Configuration_PDF` 가 HE1i 에 없음(2026-10-12 유수진 책임 지적, image 의 IM "Swcd_Bsw_Dem Input File List 에 Ecud_Dcm, Dcm_ECU_Configuration_PDF 추가"). HAE v3.0.27 배포본 SCons 에는 이미 있었음(SD 2026-07-31). v3.0.27 작업(10-06, #48881, `64a147ef0`) 때 참고 형상과 비교해 `Swcd_Bsw_Dem: missing_in_ours=['Dcm_ECU_Configuration_PDF', …]` 까지 뽑았다. 그런데 결론은 Action Report(HTML 69건) 기준으로 "SCons 35건 모두 반영"이라고 냈다 | ① Action Report 의 SCons 항목은 patch_tool 이 **자기 모듈 PDF 를 자동 추가한 기록**(`Swcd_Bsw_Dem -> Dem_ECU_Configuration_PDF`)뿐이다. 다른 모듈 PDF(Dcm)·IM 지시 항목은 실리지 않는다 — Report 는 요청의 일부다. ② 나머지 missing 목록을 "레퍼런스 프로젝트라 구성이 다름(Eth·Lin 등)"으로 한꺼번에 미판정하고 넘어감. ③ v3.0.27 배포본에 VersionComparison(Prev)이 없는데 직전 회차 배포본으로 3-way 를 하지 않아, HAE 이번 델타와 SP3i 고유 차이를 가르지 못함. ④ 해당 IM 미확인 | Action Report 는 체크리스트의 일부로만 쓴다. 참고 형상과 당사의 차이는 **항목마다** 반영 / 제외(사유: 당사 구성에 없는 모듈·채널 등) / 확인 필요로 분류하고, "구성이 다름"으로 묶어 넘기지 않는다. Prev 가 없으면 직전 회차 배포본을 구해 3-way 로 한다. 리스트형 파라미터는 회차마다 `--check` 로 Cur 대비 남은 차이를 보고 판정표 사유와 1:1 대조 |
| S6 | **이번 배포본이 이전 회차 보정을 되돌렸는데 "기존 충족"으로 통과.** FBL 3.0.18 08-31 보정본(MCP0806-256 `Ecu.zip`)은 `PMem_Driver_StartUp` 을 BswM `AL_DriverInitTwo` → EcuM ListTwo Index 0 으로 옮겼다. 3.0.19 배포본(09-07)은 보정 이전 BswM 방식으로 나왔고, HE1i V3.0.19(#48891 10-08)는 이와 같아서 손대지 않았다. Prev(3.0.18+보정본)→Cur 의 "EcuM → BswM" 차이도 HAE 의도 변경으로 보고 넘겼다. 2026-10-12 유수진 책임이 #48292 note-3 미반영으로 지적 (#48891 note-21) | 3-way 는 이번 회차 델타만 본다. Ours = Cur 이면 이전 회차 보정 여부를 묻지 않음. 일감 본문에 "#48292 note-2~4 검토"를 적어 두고도 결론을 내지 않음 | 판정표 모든 행에 "이력" 칸 — 이전 회차 보정본·답변·git 이력을 회차순으로 대조(`three-way-merge.md` 4.8). 이번 배포본만 예전 값이면 "되돌림 의심"으로 사용자 확인, 엇갈리면 IMS 에 "어느 쪽이 최종인지" 질문. 일감 본문의 검토 항목은 결과 코멘트에 하나씩 결론을 적음 |
| S10 | **설정에서 모듈을 뺐는데 이전 생성물이 남아 컴파일 실패.** FBL Com 제거(Generation Com Used false + ExcludeList Com_R44) 후 Jenkins #18 에서 `Generated/Bsw_Output/src/Com_Cfg.c: cannot open source file "Com.h"` | SCons 는 `Generated/Bsw_Output` 에 있는 파일을 생성 목록에 없어도 컴파일한다(`More generated file … found for compile`). Com 생성기가 돌지 않아 10-08 생성물(Com_Cfg.c/.h, SchM_Com*.h, PduR_Com.h)이 저장소에 그대로 남음 | 모듈 생성을 끄거나 BswInstance 를 지울 때 그 모듈 생성물을 함께 삭제. 빌드 후 작업 폴더 생성물의 날짜를 보고 재생성되지 않은 파일을 찾는다(#48891 `3e94476b`, #19 성공) |
| S7 | **IMS 질문이 거꾸로 읽히고, 확인하지 않은 전제가 들어감.** MCP0806-280 SCons 문의에서 ① "패치 참고 SCons.arxml 의 … InputFilesList 에 IM 표준에 없는 항목이 있습니다"라고 써서, 사용자와 HAE 담당자 모두 "당사가 IM 항목을 누락"으로 읽었다. HAE 는 "누락 근거가 어디 있냐"고 되물었다. ② "SP3i(HAE 파일)는 EcuM 에서 CDD_Router 를 초기화한다"를 파일을 열어 보지 않고 말하고 질문 전제로 넣었다. 실제로는 패치 파일·당사 SP3i·HE1i·APSU 모두 초기화하지 않았다. SP3i 가 당사 차종인데 HAE 것처럼 썼다 (2026-10-12) | "참고 형상" 같은 모호한 이름. 세 곳(패치 파일·IM·당사)을 한 문장에 섞음. 추정을 사실처럼 말함 | `communication.md` — 확인한 것만 경로·행과 함께, 이름 고정표, "A 에는 있고 B 에는 없다" 문장, 보내기 전 점검 5개 |
| S1 | 개정 안내에서 harmonize 대상이 바뀐 것을 놓칠 뻔함 | 같은 티켓에 안내 댓글이 다시 달림 | 안내 댓글을 날짜순으로 모두 읽고 항목별로 최신값 사용 |
| S1 | IM 링크가 권한 없음 | HAE IM 링크 일괄 변경 | ECM 에서 제목 검색, 그래도 없으면 IMS 에 재전달 요청 |
| S1 | 배포본 `Doc/ModuleChangeList/*.xlsx` 가 열리지 않음 (헤더 `SCDSA002`) | HAE 사내 DRM 암호화 상태로 배포 | IMS 티켓에 암호화 해제본 요청 → HAE 가 `Doc.zip` 재첨부 (MCP1001-193 [27][28]) |
| S6 | HAE 참고 설정을 그대로 넣으면 당사 로직 문제 (이전 담당자 경험) | 참고 프로젝트 기준 설정 | 3-way 판정, 통째 복사 금지 |
| S6 | 참고 형상의 새 PDF 입력이 당사에 없는 파일 | HAE 참고 프로젝트의 다른 모듈 버전(Crypto 2.0) | patch_tool 스크립트 주석으로 변경 이유 확인 → 제외 |
| S8 | 모듈 폴더 통째 교체로 당사 수정 소실 위험 | 당사가 HAE 모듈 파일을 직접 수정(CanTrcv) | owner_edits.py 로 교체 전 확인 |
| S8 | **Harmonize 기본 옵션이 당사 수동 값을 덮어씀** — Can·CanIf 만 골라 돌렸는데 CanIfMetaDataSupport 1→0, 0x7AB CanFdPaddingValue 0 명시(생성 0xFF→0x00), 진단 Rx 버퍼 10→64, 0x7DF 객체 이름·ObjectId·RxPduId 변경. 결과가 VC 와 완전히 같았음 | Overwrite User-Configured / Remove Invalid / Auto-Regeneration of Handle Id 가 기본 켬. 바뀐 내역은 git 무시 폴더의 `Automation-Results/*.xls` 에만 남음 (FBL V3.0.19 시험 2026-10-10) | 시험 브랜치에서 먼저 돌리고 xls 보관, `protected_check.py --before-rev HEAD` 로 보호 설정·기본값 의존 변화 확인, C Studio 닫은 뒤 복구 (`protected-settings.md` §6) |
| S12 | **서명받은 이미지와 저장소 이미지가 달라짐.** ALL 빌드(#32) rom 으로 서명을 받은 뒤, FBL 바이너리 반영 + CURRENT 복귀 커밋을 push → 26810 만 재빌드(#33) → `.s19` 10바이트 다름. CVD 로 저장소 이미지를 쓰면 서명본·F1C1 해시와 불일치 | APP 소스가 같아도 **Os 생성기가 재생성 때마다 같은 크기 태스크 스택의 칸 배치(`Os_GaaStack`) 순서를 바꿈** → 스택 주소 표 + `MAINSW_CRC` 변경. ALL 빌드도 변형마다 생성이 따로 돌아 4벌의 배치가 서로 다름 (#48891 2026-10-08, #32/#33/#34) | ① 서명 요청한 뒤 실기가 끝날 때까지 **APP 를 다시 빌드시키는 push 를 하지 않는다** — 문서·바이너리 반영·CURRENT 복귀도 실기 후에 몰아서. ② 꼭 push 해야 하면 ALL 로 4벌을 다시 만들고 서명을 다시 받는다. ③ "define 하나만 바꿨으니 같을 것"이라고 단정하지 말고, 빌드 후 `.s19` 를 바이트 비교해 확인한다. ④ 급하면 서명받은 빌드 커밋에서 `_Writing.s19`·elf 를 꺼내 cvd-project `--app --elf` 로 기록 |
| S8 | **보정 zip 을 풀다가 폴더가 한 단계 더 생김.** v3.0.28 의 HAE `bat_package.zip`(MCP0806-272, 08-10) 은 압축 안에 최상위 `bat_package/` 폴더가 있다. 이것을 `Build\bat_package\` 안에 그대로 풀어 `Build\bat_package\bat_package\*.bat` 가 됐다(`434a0c2c0`, 66개 이동). 빌드는 모듈별 `generator\*.bat`(AUTOSAR44=True)를 써서 영향이 없었고, 그래서 아무도 몰랐다. 2026-10-12 유수진 책임이 "`\Build\bat_package\…` 로 경로 설정"을 요청했다 | 첨부 zip 의 최상위 폴더 구조를 확인하지 않고 대상 폴더 안에 풀었음. 커밋 diff 의 `{ => bat_package}/` 이름 변경을 보지 못했음 | 첨부 zip 은 `unzip -l` 로 최상위 폴더부터 확인하고, 상위 폴더에 풀거나 내용물만 옮긴다. 적용 후 `git diff --cached -M --summary` 에서 의도하지 않은 `rename`(특히 `{ => 폴더}/`)이 없는지 본다. HAE 배포본·develop·APSU 의 같은 폴더와 구조를 대조한다 |
| S8 | 산출물명이 다른 차종 이름(sx3e_)으로 나옴 | `.project` 미변경 | 버전 위치 4곳 체크, version_bump_check.py |
| S8 | UTIP Writing·aSIMs ini 산출물명 누락 → 재빌드 | 위치 목록 일부만 변경 | 위와 같음 |
| S8 | sed 로 고친 파일의 줄바꿈 경고 | LF/CRLF 혼재 파일 | 고친 뒤 `git diff --stat` 줄 수 확인 |
| S8 | 경로 문자열의 `\v` 등이 제어문자로 바뀜 | 파이썬 문자열 이스케이프 | 경로는 raw 문자열·`chr(92)`·`os.sep` 사용, 쓰기 후 제어문자 검사 |
| S10 | Jenkins 후처리가 건너뛰어 rom/차종 산출물 없음 | Hook 이 Post-build 미실행 | 과제 Hook·PostPackage 분리 (#47967) |
| S10 | 증분 빌드와 비교해 경고 수가 의미 없음 | 비교 대상 빌드에 Generate 없음 | 직전 회차 전체 재생성 빌드와 비교 |
| S10 | javascript_tool 결과가 잘리거나 "Cookie/query string data" 로 차단 | 반환값 길이·필터 | DOM 에 펼쳐 get_page_text 로 읽기 |
| S11 | 요약만 보여 주고 등록 원문으로 착각하게 함 | 미리보기 대신 설명 제시 | 등록될 원문 전체를 그대로 보여 줌 |
| S12 | 한쪽 뱅크만 기록 → E_NOTMATCHED_DESTINATION | 라이팅 옵션 | 양 뱅크 기록 |
| S12 | `.asc.asc` 확장자 중복 | 저장 대화상자 | 파일명 규칙 확인 |
| S12 | 보드평가레포트에 이전 회차 첨부 잔존 | 템플릿 복사 | 이번 회차 파일로 교체 |
| S12 | BG 리프로그래밍 1차 E_INVALIDRESPONSE | 간헐 | 재실행 후 기록 (#48881) |
| S12 | 리셋 중 레스트버스 송신 막힘 | 실험대 ACK 노드 부재 | 리셋 동안 1초 정지, 실험대 특이사항으로 기록 (#48909) |
| S12 | ALL 전환 후 CURRENT 복귀 누락 위험 | 평가 끝난 뒤 잊음 | 실기 마지막 단계에 복귀 커밋 체크 |
| S13 | 리뷰어 지적 누락 항목(infineon_ucb 삭제, 미사용 Routine) | 직전 회차 지적사항 미이관 | 직전 일감 코멘트의 지적사항을 S4 본문 "이전 회차 누락 반영"에 옮김 |

## 빌드 오류 — 다른 담당자 사례 (IMS)
| 증상 | 원인 / 해결 | 근거 |
|---|---|---|
| Os 모듈 컴파일 에러 (Os_CYTXXX_R44) | 폴더명 대소문자 `Os_CYTxxx_R44` 로, SCons Compile 경로도 소문자. bat 은 AUTOSAR44=1 이면 영향 없음 | MCP0806-270 [14][16] |
| Os_Arch_SystemCall.h 어셈블 에러 | SCons DefaultCompileOption 에 `--gnu_asm` 추가 (HAE 형상은 BSW 옵션에 이미 있음) | MCP0806-270 [17][18] |
| `.text` 가 `.LIB_CODE` 침범 overlap, "too many user-defined sections" 경고 | GHS 2017 은 사용자 섹션 94개 초과 시 .text 로 몰림. MPU 미사용이면 SC1 + .ld 의 MPU용 ABS 제거로 해결. 경고는 MPU 미사용 시 무시 | MCP0806-270 [36]~[45] |
| SCons `Compile/CompileCmdChoice/Compile` unresolved proxy | Compile 컨테이너는 toolset 3.0.3 부터 미사용(Build 하나로 통합). 삭제해도 되고 두어도 동작 | MCP0806-272 [22] |
| toolset 2.x → 3.x 패치 후 `Build/site_scons` 에 `.pyc` 가 없음 / Compile 옵션 사라짐 | 3.x 는 Python 3.12 가상환경으로 `.py` 를 직접 실행(.pyc 는 산출물이라 배포 제외). 기존 `site_scons` 를 지우고 새것으로 교체, SCons Compile 컨테이너 삭제 | MCP1001-193 [9][10][15][17] |
| 패치 후 Os 관련 빌드 에러가 HAE 에서는 재현 안 됨 | 모듈 폴더가 잘못 복사됨 → 폴더 완전 삭제 후 배포본에서 다시 복사, Rebuild | MCP1105-105 [16] |
| Os 신규 Validation (SC3/4) | Task 스택은 2^n, 32 이상. .ld 의 task stack 은 Ecud_Os 최대값 | MCP1105-104 [8][12] |
| 사용 안 하는 callout 설정 에러 (FlashcMain…Callout) | 모듈에서 함수 삭제됨 → 설정에서도 제거 (IA-057) | MCP0806-255 [10][11] |

## 추가 기록
