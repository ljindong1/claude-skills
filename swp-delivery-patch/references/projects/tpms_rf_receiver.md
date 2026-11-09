# 프로젝트 프로필: BJ/TPMS RF Receiver (BJ1·LT2 공용, 확인 2026-11-09)

파일 단위는 **저장소(SWP 계열)**다. BJ1·LT2 는 같은 저장소·같은 `PJ_Define.h` 를 쓰므로 차종 차이는 아래 표의 행으로 둔다.
`[확인 필요]` 는 저장소 조사로 알 수 없어 비워 둔 칸이다. 칸마다 값이 오는 곳이 정해져 있다(SKILL S0 "빈 칸은 어디서 채우고 어디에 반영하나") — **시작 전에 닫을 칸**은 저장소·브랜치·Jenkins Job(gitea-jenkins-setup)과 빌드 대상·일정뿐이다. PR 은 S13, APP 버전 위치는 첫 APP 패치 S8, 실기 기준값은 S12 를 수행한 뒤 그 회차 실측으로 채운다 — 비어 있어도 작업을 막지 않는다. 채우면 **같은 값을 일감 본문의 `[기입]` 에도 반영**한다(SKILL S4).

## 기본
| 항목 | 값 |
|---|---|
| SWP 계열 | [R44] BJ/TPMS RF Receiver (S32K312, 100핀). MCAL `S32K3xx_RTD_4.0.0_P24` |
| 차종·단계 | BJ1 양산(SOP 완료) / LT2 P2 배포 중·M 단계 예정 (2026-11, 당사 회신 2026-10-20) |
| IMS 프로젝트 | `MCP1001-xxx`. v2.1.10 FBL = MCP1001-198 / APP v2.1.11 = MCP1001-199 / 수평전개 사본 MCP1001-196 → 원본 CPINFO-4110 |
| Redmine | mobilgene Classic - MOBASE ASEC / Task. 사용자정의: 일감검토자 141, 일감완료자 545, SWP 계열(공용화) `[R44] BJ/TPMS RF Receiver(S32K312, 100핀)`, SWP 계열 버전, 차량단계 P2(LP2) |
| 일감 예 | FBL #49949 (V2.1.10) / APP #49951 (V2.1.11). 직전 회차 #47378, #46767 |
| 패치 자료 폴더 | `D:\Mobase\패치업무\TPMS 실기검증\LT2\<FBL\|APP>\<FBL\|APP>_v<버전>(<IMS키>)\` — HE1i 와 규칙이 다르다(차종 폴더 아래 FBL/APP) |
| 정리 문서 | Confluence 대표 381747206, 부록 A 381779978 · B 381714492 · C 381780001 · D 381681670 |

## 저장소
| | FBL | APP |
|---|---|---|
| 저장소 | http://ccm.mobaseelec.com:3000/Kahuz/tpms_rf_receiver_bj_fbl | http://ccm.mobaseelec.com:3000/Kahuz/tpms_rf_receiver_bj |
| 로컬 경로 | `D:\Mobase\TPMS\tpms_rf_receiver_bj_fbl` | `D:\Mobase\TPMS\tpms_rf_receiver_bj` |
| 하위 프로젝트 폴더 | **없음 — 저장소 루트가 앱 루트**(`Build/`, `Configuration/`, `Static_Code/` 가 바로 있다). HE1i(`psu_fbl/`)와 다르다 | 같음 |
| 작업 브랜치 | `devel_LT2_jdlee_p1_R44_DeliveryPatch` | `devel_LT2_jdlee_p2_R44_DeliveryPatch` |
| 기본·PR 대상 | `03_P1` (origin/HEAD). 다른 단계 브랜치: 01_Proto, 02_MCAR, 05_M | 같음 |
| PR 방식 | [확인 필요 — gitea-jenkins-setup 모드 D] | [확인 필요 — gitea-jenkins-setup 모드 D] |
| Jenkins Job | [확인 필요 — gitea-jenkins-setup 모드 A~C 결과] | [확인 필요 — gitea-jenkins-setup 모드 A~C 결과] |
| 빌드 Hook | `Build/Build_Hook_LT2.bat`(과제 Hook) + `BuildVariants.bat`·`PJ_Variant.ps1`·`PostPackage.bat`·`GitPush.bat`. 표준 `Build_Hook_GIT_ASEC.bat` 은 그대로 둔다 | [확인 필요] |

## 버전 위치
| 대상 | 파일 | 규칙 |
|---|---|---|
| FBL SWP·산출물명 | `.project` 의 `<name>` — **이 한 곳뿐** | `e_bj_tpms_asr_swp_fbl_v219` → 다음 회차 `..._v2110`. SCons 가 이 이름으로 `.elf/.hex/.map/.sre` 를 만든다 |
| FBL 버전 문자 | **없음** — `Application/app_code/type/PJ_Define.h` 에 `SOFTWARE_VERSION_*` 정의가 없다(OEUK 선택 3줄뿐). HE1i 의 `SOFTWARE_VERSION_5` 문자 규칙은 이 과제에 해당하지 않는다 | 버전 판독 방법 [확인 필요] |
| JENKINS_BUILD_TARGET | **정의 없음** → Hook 이 항상 CURRENT 단일 빌드(`PJ_Variant.ps1` 기본값). ALL 4벌 빌드를 쓰려면 정의를 먼저 넣어야 한다 | jenkins-flow §2 |
| OEUK 변형 | 같은 `PJ_Define.h`: `OEUK_TEST`(주석) / `OEUK_BJ1`(주석) / `OEUK_LT2`(활성) — **한 번에 하나만** 활성 | 2026-11 기준 LT2 전용 빌드 |
| FBL 산출물 위치 | `Debug/OEUK_LT2/` **평면**(버전 하위 폴더 없음, 커밋 3512d80e). `Debug/OEUK_LT2/UNKNOWN/` 은 평면 전환 전 잔존물 | PostPackage.bat 이 `.sre` 이름으로 접두·폴더를 정한다 |
| 과거 산출물 | `References/OEUK_OUTPUT/e_bj_tpms_asr_swp_fbl_v212.*` | |
| APP 버전 위치 | [확인 필요 — 첫 APP 패치 S8 에서 APP 저장소 조사] | |
| FBL 바이너리(APP 저장소) | [확인 필요] | |
| Doc | `References/Doc/ReleaseNote/`, `References/Doc/ModuleChangeList/` | 배포본 `Doc/` 와 같은 구조 |
| 실기 결과 폴더 | `References/Doc_MobaseElec/08_Reprogramming/` (HE1i 는 `Doc_MB/04_Reprogramming`) | |

## 구성 전제 (사전 점검 P ① — FBL 확인 2026-11-09, 저장소 조사)
| 전제 | FBL | APP | 확인 위치 |
|---|---|---|---|
| Os 확장 등급 / MPU / Timing Protection | **SC1** / [확인 필요] / [확인 필요] | [확인 필요] | `Configuration/Ecu/Ecud_Os.arxml` `OsScalabilityClass` |
| PFee 사용 | **사용** (`OsTask_BSW_PFee_Process`, `PFEE_PART`) | [확인 필요] | Ecud_Os, Ecud_Mem_76_Pfls |
| UseRamCode | **false** (`MemUseRamCode = 0`) | [확인 필요] | Ecud_Mem_76_Pfls MemGeneral |
| 컴파일러 (SRS 고정) | **GHS ARM.V2021.1.4** (HE1i 는 2017.1.4 — 가이드의 컴파일러 조건을 그대로 옮기지 않는다) | [확인 필요] | `Build/SCons.arxml` |
| mobilgene C Studio | 당사 버전 [확인 필요]. 배포본 ReleaseNote 가 적은 적용본은 `2.0 2026-01-R12.2.0` | 같음 | 배포본 `Doc/ReleaseNote/...docx` |
| toolset | `customer_patch.py` 가 **Python 3.12.10 이상** 요구 → toolset_scons 3.x 계열. HE1i 의 Python 2.7 전제가 아니다 | 같음 | 배포본 `AutomatePatch.bat` |
| MCU | S32K312 (`Static_Code/Modules/b_mcal_nxp_S32K3xx`, `Os_S32K3xx_R44`, `OsImp_S32K3xx_R44`) | 같음 | Static_Code/Modules |
| 대표 차종 (HAE 참고 설정 기준) | HAE 기준 형상은 `e_bj_tpms_asr_swp_fbl-2.1.9` = **당사 직전 형상 그 자체**(배포본 manifest `project_name`) — 다른 과제와 달리 참고 설정이 당사 계열 기준이다 | `e_bj_tpms_asr_swp_app-2.1.10` [확인 필요] | 배포본 `patch_tool/patch_manifest.json` |
| Com 사용 | **미사용** — `SCons.arxml` ExcludeList 에 `Static_Code\Modules\Com_R44`(폴더는 남겨 둔다, HAE 답 "제외") | [확인 필요] | Build/SCons.arxml |

## 프로젝트 사실 (판정에 쓰임)
- Dcm: `DcmDemIntegrated = 0`(FBL). 진단 Rx **0x7D6 물리 / 0x7DF 기능**, Tx 0x7DE
- FBL 에 NM 메시지 없음 — 진단 메시지만 존재(2026-10-22 HAE 문답). IA-079 는 2026-10-30 종결(Tx `CanHwObjectCount = 1` 유지)
- MCAL 업데이트 불가(양산·P2 배포 단계) — 배포 ReleaseNote Notes 4 와 어긋난 상태

## 보호 설정 (당사가 일부러 정한 값)
아직 정리하지 않았다 — 다음 패치 S6 에서 HAE Cur·VC 대비 당사 고유값을 뽑아 채운다. `protected_check.py` 가 이 표를 읽는다(형식은 `he1i_psu.md` 참고).

| 구분 | 파일 | 키 | 당사 값 | 이유·근거 |
|---|---|---|---|---|

## 프로젝트 고유 판단 이력
| 규칙 | 근거 |
|---|---|
| Com 은 삭제가 아니라 **제외** — `Ecud_Com.arxml`·`Static_Code/Modules/Com_R44` 를 남기고 SCons ExcludeList 에만 넣는다 | MCP1001-198 댓글[21] |
| MCAL 업데이트 미적용 (IA-079 #7 Advisory) | 당사 회신 2026-10-20, 일감 #49949 §9 |
| IA-086 은 Advisory — 값을 정하고 근거를 남기는 항목 | 일감 #49949 §9 |
| 2026-11-02~03 작업은 HAE 안내를 보고 **수동**으로 진행한 기록이 있다 — patch_tool 을 뒤늦게 돌리면 같은 자리를 두 번 고친다 | 일감 #49949 `Q11` |
