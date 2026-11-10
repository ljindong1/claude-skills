# 프로젝트 프로필: BJ/TPMS RF Receiver (BJ1·LT2 공용, 확인 2026-11-10)

작업 브랜치 기준 커밋: FBL `3512d80e`(2026-11-09). 그 위에 Jenkins Auto commit #6(`7c1dfa75`)이 올라가 있으니 작업 전 `git pull` 이 필요하다.

파일 단위는 **저장소(SWP 계열)**다. BJ1·LT2 는 같은 저장소·같은 `PJ_Define.h` 를 쓰므로 차종 차이는 아래 표의 행으로 둔다.
`[확인 필요]` 는 저장소 조사로 알 수 없어 비워 둔 칸이다. **시작 전에 닫을 칸**은 저장소·브랜치·Jenkins Job(gitea-jenkins-setup)과 빌드 대상·일정뿐이다. PR 방식은 마무리 때, APP 버전 위치는 첫 APP 패치 때, 실기 기준값은 실기를 수행한 뒤 그 회차 실측으로 채운다 — 비어 있어도 작업을 막지 않는다. 채우면 **같은 값을 일감 본문의 `[기입]` 에도 반영**한다(일감 수정은 redmine-patch-issue).

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
| Jenkins Job | `LT2_TPMS_FBL_jdlee` | `LT2_TPMS_AUTOSAR_jdlee` |
| Job 설정 (확인 2026-11-09) | 브랜치 스펙 `*/devel_LT2_jdlee_*`(패턴이라 같은 접두의 새 브랜치도 이 Job 이 받는다), 파라미터 `BuildType`, 빌드 명령 `Build\Build_Hook_LT2.bat %BuildType% -j8`(없으면 `Build_Hook_GIT_ASEC.bat`), 활성. 최근 빌드 #6 SUCCESS | 같은 설정. 최근 빌드 #2 SUCCESS |
| 빌드 Hook | `Build/Build_Hook_LT2.bat`(과제 Hook) + `BuildVariants.bat`·`PJ_Variant.ps1`·`PostPackage.bat`·`GitPush.bat`. 표준 `Build_Hook_GIT_ASEC.bat` 은 그대로 둔다 | 같은 구성(`Build_Hook_LT2.bat`·`BuildVariants.bat`·`PJ_Variant.ps1`·`PostPackage.bat`). APP 쪽 `PJ_Define.h` 는 `Application/` 아래에서 찾지 못했다 — 위치 [확인 필요] |

## 버전 위치
| 대상 | 파일 | 규칙 |
|---|---|---|
| FBL SWP·산출물명 | `.project` 의 `<name>` — **이 한 곳뿐** | `e_bj_tpms_asr_swp_fbl_v219` → 다음 회차 `..._v2110`. SCons 가 이 이름으로 `.elf/.hex/.map/.sre` 를 만든다 |
| FBL 버전 문자 | **없음** — `Application/app_code/type/PJ_Define.h` 에 `SOFTWARE_VERSION_*` 정의가 없다(OEUK 선택 3줄뿐). HE1i 의 `SOFTWARE_VERSION_5` 문자 규칙은 이 과제에 해당하지 않는다 | 버전 판독 방법 [확인 필요] |
| JENKINS_BUILD_TARGET | **정의 없음** → Hook 이 항상 CURRENT 단일 빌드(`PJ_Variant.ps1` 기본값). ALL 4벌 빌드를 쓰려면 정의를 먼저 넣어야 한다 | jenkins-flow §2 |
| OEUK 변형 | 같은 `PJ_Define.h`: `OEUK_TEST`(주석) / `OEUK_BJ1`(주석) / `OEUK_LT2`(활성) — **한 번에 하나만** 활성 | 2026-11 기준 LT2 전용 빌드 |
| FBL 산출물 위치 | `Debug/OEUK_LT2/` **평면**(버전 하위 폴더 없음, 커밋 3512d80e). `Debug/OEUK_LT2/UNKNOWN/` 은 평면 전환 전 잔존물 | PostPackage.bat 이 `.sre` 이름으로 접두·폴더를 정한다 |
| 과거 산출물 | `References/OEUK_OUTPUT/e_bj_tpms_asr_swp_fbl_v212.*` | |
| APP SWP·산출물명 | **세 곳이다** ① `.project` 의 `<name>` ② `References/Doc_MobaseElec/02_CRT_UTIP_CFG/bj_tpms_asr_swp_rtsw_0x5D_1FFF_Reprogramming.utp` 의 `LOAD` ③ 같은 폴더 `..._Writing.utp` 의 `LOAD` | `e_bj_tpms_asr_swp_app_v2110` → `..._v2111`. **버전업 뒤 반드시 `version_bump_check.py` 를 돌린다** — ①만 올리고 ②③을 빠뜨리면 UTIP 이 낡은 `.sre` 를 읽어 `.s19` 가 구 버전으로 조용히 만들어진다(#49951 실측) |
| APP T32 디버그 스크립트 | `References/JTAG/s32k3_BJ_TPMS.cmm` — `GOSUB v2110_dev`(93행), 라벨 `v2110_dev:`(272행), `&elf_rtsw`(275행) | 빌드에는 쓰이지 않는다. 이 파일의 FBL 경로는 다른 PC 절대경로(`D:_Project
_TPMS\...`)다 — 회차마다 올릴지 사용자에게 확인 |
| FBL 바이너리(APP 저장소) | `References/FBL_Output/OEUK_LT2/` **평면** — `e_lt2_tpms_asr_swp_fbl_v<버전>.{elf,hex,map,sre}` + `<날짜시각>_BuildWarning.xlsx` | APP 빌드의 입력이 **아니다**(SCons·site_scons·bat·UTIP 어디서도 참조하지 않음, 2026-11-10 확인). 짝 FBL 회차 산출물을 형상 등록하는 자리다. v2.1.9 세트에 있던 `.dla`·`.dnm` 은 v2.1.10 세트에 없다 |
| Doc | `References/Doc/ReleaseNote/`, `References/Doc/ModuleChangeList/` | 배포본 `Doc/` 와 같은 구조 |
| 실기 결과 폴더 | `References/Doc_MobaseElec/08_Reprogramming/` (HE1i 는 `Doc_MB/04_Reprogramming`) | |

## 구성 전제 (사전 점검 P ① — FBL 확인 2026-11-09, 저장소 조사)
| 전제 | FBL | APP | 확인 위치 |
|---|---|---|---|
| Os 확장 등급 / MPU / Timing Protection | **SC1** / [확인 필요] / [확인 필요] | [확인 필요] | `Configuration/Ecu/Ecud_Os.arxml` `OsScalabilityClass` |
| PFee 사용 | **사용** (`OsTask_BSW_PFee_Process`, `PFEE_PART`) | [확인 필요] | Ecud_Os, Ecud_Mem_76_Pfls |
| UseRamCode | **false** (`MemUseRamCode = 0`) | [확인 필요] | Ecud_Mem_76_Pfls MemGeneral |
| 컴파일러 (SRS 고정) | **GHS ARM.V2021.1.4** (HE1i 는 2017.1.4 — 가이드의 컴파일러 조건을 그대로 옮기지 않는다) | [확인 필요] | `Build/SCons.arxml` |
| mobilgene C Studio | 당사 버전 [확인 필요]. 배포본 ReleaseNote 가 적은 적용본은 `2.0 2026-01-R12.2.0` | **`2.0 2026-03-R12.4.0`** (`Static_Code/modulesVersion.json` 의 `tool_info`). APP v2.1.11 배포본은 `2026-06-R13.0.0` 을 적지만 당사 생성 환경은 올리지 않았다 — patch_tool 이 이 값을 덮으므로 되돌린다 | 배포본 `Doc/ReleaseNote/...docx`, `modulesVersion.json` |
| toolset | `customer_patch.py` 가 **Python 3.12.10 이상** 요구 → toolset_scons 3.x 계열. HE1i 의 Python 2.7 전제가 아니다 | 같음 | 배포본 `AutomatePatch.bat` |
| MCU | S32K312 (`Static_Code/Modules/b_mcal_nxp_S32K3xx`, `Os_S32K3xx_R44`, `OsImp_S32K3xx_R44`) | 같음 | Static_Code/Modules |
| 대표 차종 (HAE 참고 설정 기준) | HAE 기준 형상은 `e_bj_tpms_asr_swp_fbl-2.1.9` = **당사 직전 형상 그 자체**(배포본 manifest `project_name`) — 다른 과제와 달리 참고 설정이 당사 계열 기준이다 | `e_bj_tpms_asr_swp_app-2.1.10` — FBL 과 같이 당사 직전 형상 그 자체 | 배포본 `patch_tool/patch_manifest.json` |
| Com 사용 | **미사용** — `SCons.arxml` ExcludeList 에 `Static_Code\Modules\Com_R44`(폴더는 남겨 둔다, HAE 답 "제외") | [확인 필요] | Build/SCons.arxml |

## 프로젝트 사실 (판정에 쓰임)
- Dcm: `DcmDemIntegrated = 0`(FBL) / **`= 1`(APP)**. 진단 Rx **0x7D6 물리 / 0x7DF 기능**, Tx 0x7DE
- APP 는 **진단 프로토콜 1개**다 — 이번 패치가 고친 "우선순위 높은 프로토콜 무응답"의 전제가 성립하지 않는다(#49951)
- **Single Bank / Single Mem** — `SWP_USE_DUALM = STD_OFF`, `FOTA_INTEGRATION_SINGLEMEM_PLATFORM`. 그래서 OTA `TransferData` 반복 블록 `NRC 0x71` 결함과 HF4 신규 `ERR053310`·`ERR053311` 이 모두 해당 없다 (HAE 김형태 2026-11-02 "Single 이면 RTSW 에서 고려하지 않아도 될 것 같습니다")
- FBL 에 NM 메시지 없음 — 진단 메시지만 존재(2026-10-22 HAE 문답). IA-079 는 2026-10-30 종결(Tx `CanHwObjectCount = 1` 유지)
- MCAL 업데이트 불가(양산·P2 배포 단계) — 배포 ReleaseNote Notes 4 와 어긋난 상태

## 보호 설정 (당사가 일부러 정한 값)
`protected_check.py` 가 아래 표를 읽는다. **쓸 때 지킬 것 셋**(2026-11-10 실측으로 확인한 파서 규칙, `read_rules()`):

- **키** — `컨테이너 SHORT-NAME 경로#파라미터 정의명`. `three_way.py` `parse()` 와 같은 형식(예 `/Dcm/DcmGeneral#DcmTaskTime`). 사람이 읽는 이름(`DcmTaskTime`)으로 적으면 전부 `키 없음(컨테이너 이름 변경·삭제 의심)` 으로 나와 harmonize 직후에 오해를 부른다.
- **당사 값** — **값만** 적는다. `**0.01** (IA-059 권고는 0.005)` 처럼 강조·설명을 붙이면 문자열 비교가 어긋나 `바뀜` 으로 나온다. 설명은 이유 칸에.
- **구분** — `APP` · `FBL` · `공통` 중 하나와 **정확히 일치**해야 한다. `APP·FBL` 로 적으면 `--part APP` 에도 `--part FBL` 에도 걸리지 않아 **조용히 빠진다**.
- ⭐ **이 절에 다른 표를 두지 않는다.** 파서는 절 안에서 **처음 만난 표의 머리글**을 헤더로 삼고 `###` 로는 초기화하지 않는다. 설명용 표를 앞에 두면 `키` 칸이 사라져 **모든 행이 조용히 무효가 된다**(2026-11-10 실측 — 이 문서 자신이 그 실수를 했다). 설명은 글머리표로, 성격이 다른 항목은 별도 `##` 절로.

⚠ `###` 소제목은 이 절을 닫지 않는다 — 스크립트는 다음 `##` 까지 모든 표를 읽는다. 성격이 다른 항목은 **별도 `##` 절**에 둔다(아래 "사람이 확인하는 설정").

키는 추측하지 말고 뽑는다.

```
python -c "import sys;sys.path.insert(0,r'<스킬>/scripts');from three_way import parse;
           [print(k,'=',v) for k,v in parse('Configuration/Ecu/Ecud_Dcm.arxml').items() if 'DcmTaskTime' in k]"
```

| 구분 | 파일 | 키 | 당사 값 | 이유·근거 |
|---|---|---|---|---|
| APP | `Configuration/Ecu/Ecud_Dcm.arxml` | `/Dcm/DcmGeneral#DcmTaskTime` | 0.01 | IA-059 권고는 0.005. 주기를 절반으로 줄이면 CPU 부하가 오른다 — 같은 티켓에서 진단 CAN 설정 유지의 당사 근거가 CPU 부하(평균 16.9% / 최대 22.7%)였으므로 함께 판단해야 한다. ⚠ **ADMIN-DATA 에 `AUTO_CONFIGURED 0.005`(2026-02-05)가 이미 있고 `AUTO_CONFIG_PROPERTY=true` 다 — Dcm 이 harmonize 대상에 들어오면 덮인다**(`protected-settings.md` §6-1). **당사 담당자 확인 대기** (#49951) |
| 공통 | `Configuration/Ecu/Mcal/Ecud_Can.arxml` | `/Can/CanConfigSet/IN_HwObj_0x7d6_0x7df_TPMS_LCAN#CanHandleType` | BASIC | 진단 Rx 다 — `CanIfHrhCfg_IN_0x7d6_0x7df_TPMS_LCAN` → `CanIfRxPduCfg_IN_TPMS_LCAN_0x7d6_LCAN_GST_TPMS`(물리)·`0x7df_LCAN_GST_ALL`(기능) → CanTp `DcmIPdu_LCAN_GST_TPMS`·`GST_ALL` → Dcm (2026-11-10 추적). `STANDARD` id. **선언은 BASIC 이지만 아래 `CanHwObjectCount` 가 1 이라 IA-079 가 노리는 FIFO 완충이 없다** — 둘을 함께 본다 |
| 공통 | `Configuration/Ecu/Mcal/Ecud_Can.arxml` | `/Can/CanConfigSet/IN_HwObj_0x7d6_0x7df_TPMS_LCAN#CanHwObjectCount` | 1 | ⭐ **IA-079 의 실질 쟁점이 이 값이다.** he1i 는 IA-079 로 64 를 썼다. 1 로 두는 근거 4단 — ① MCAL 제약: `S32K3xx_RTD_4.0.0_HF3` 이전에는 `STANDARD`(진단)와 `EXTENDED`(NM) id 를 **같은 FIFO 에 묶으면 수신이 안 된다**(HAE 2026-10-22, 댓글\[8\]) → 진단·NM 중 하나만 FIFO 가능 ② 당사 MCAL 은 `S32K3xx_RTD_4.0.0_P24` 미갱신(아래 '사람이 확인하는 설정') ③ NM 을 FIFO 쪽으로 쓰고 있어 진단은 못 쓴다 — 진단을 FIFO 로 바꾸면 **DB 에 없는 Nm 메시지 수신 불가**(Full CAN 은 ID Range 불가) ④ CPU 부하 평균 16.9% / 최대 22.7% / 최소 15.9% 로 누락 발생빈도 낮다고 당사 판단, HAE 는 "확답을 드리기에는 조금 어렵습니다"(2026-10-30, 댓글\[10\]) ⑤ **최종 — LT2 는 Single Bank 이고 리프로그래밍이 FBL 단에서 되므로 `FULL CAN → OTA TransferData 무응답` 은 RTSW 가 고려하지 않아도 된다**(HAE 김형태 2026-11-02, 댓글\[13\]). IA-079 는 "현 상태 유지" 로 종결 |
| 공통 | `Configuration/Ecu/Mcal/Ecud_Can.arxml` | `/Can/CanConfigSet/IN_HwObj_TPMS_LCAN_0x43f_LCAN_CCU_01_00ms#CanHandleType` | FULL | 애플리케이션 Rx 다(진단 아님). 같은 성격 7개가 FULL — `0x2e9`·`0x3d1`·`0x3e4`·`0x43f`·`0x8000060`·`0xc000002`·`0xc000003`. IA-079 의 대상이 아니다. 주기가 가장 빠른 `0x43f` 를 대표 감시 키로 둔다 |
| 공통 | `Configuration/Ecu/Mcal/Ecud_Can.arxml` | `/Can/CanConfigSet/IN_HwObj_0x17fc0000_0x17fc00fe_TPMS_LCAN_NM_Message#CanHandleType` | BASIC | NM Rx, `EXTENDED` id, 범위 `0x17fc0000~0x17fc00fe` 수신. `CanHwObjectCount` 는 1. **진단과 NM 중 FIFO 를 쓸 수 있는 것은 하나뿐**이라 이 쪽을 Range 수신으로 쓰고 있다 — 바꾸면 DB 에 없는 Nm 메시지를 못 받는다 |

⚠ **2026-11-10 정정 2회** — 앞 판(#49951 작성)에는 `진단 Rx CanHandleType = FULL 유지` 로 적혀 있었다. 저장소를 추적해 보니 진단 Rx 는 **2026-02-05(#39676 Diagnostic Time Out)부터 `BASIC` + `CanHwObjectCount 1`** 이고 2026-03-03 이후 바뀐 적이 없다. 파일 경로도 `Ecud_Can.arxml` 이 아니라 `Mcal/Ecud_Can.arxml` 이었다. 그다음 "IA-079 권고를 이미 만족한다" 로 고쳤는데 **그것도 틀렸다** — 선언만 BASIC 이고 하드웨어 오브젝트가 1개라 FIFO 완충이 없다. 이 파일에 FIFO 파라미터가 **하나도 없다.** HAE 가 "진단 메시지 Basic CAN : Full CAN + Hw Object 1 일 경우 고속 수신 transfer data 누락 가능성" 이라 쓴 상태가 바로 이것이다(댓글\[8\]). **IA-079 의 쟁점은 `CanHandleType` 이 아니라 `CanHwObjectCount` 다.**

FBL 전용 행은 아직 비어 있다.

## 사람이 확인하는 설정 (protected_check.py 범위 밖)

`protected_check.py` 는 **`.arxml` 의 ECUC 파라미터만** 비교한다(`if not n.endswith(".arxml"): continue`). 아래는 성격이 달라 보호 설정 표에 넣으면 안 된다 — 넣으면 `키 없음` 오탐이 되고, 표가 섞여 다른 행의 판정까지 깨진다.

| 구분 | 대상 | 당사 값 | 확인 방법 | 이유·근거 |
|---|---|---|---|---|
| APP | `Static_Code/modulesVersion.json` 의 `tool_info` | `mobilgene C Studio 2.0 2026-03-R12.4.0` | `grep -o '"tool_info": "[^"]*"'` — JSON 이라 스크립트가 못 본다 | 당사 생성 환경이 그 버전이다. patch_tool 과 CLI 실행이 로컬 값(`2026-06-R13.0.0`)으로 덮으므로 **매 회차 되돌린다**(harmonize 만 돌려도 덮인다, 2026-11-10 실측) |
| 공통 | `Static_Code/Modules/b_mcal_nxp_S32K3xx` MCAL 버전 | 미갱신 (`S32K3xx_RTD_4.0.0_P24`) | 폴더·`.ver` 확인 — 파라미터가 아니다 | 양산·P2 배포 단계. ReleaseNote SWP Notice 4 와 어긋난 상태이며 그 품질 책임은 Tier 에 있다 |
| APP | `Configuration/Ecu/Ecud_Rte.arxml` 의 `BswInstance_Crypto` | 개명하지 않는다 | `grep -c "SHORT-NAME>BswInstance_Crypto<"` = 1, `..._Crypto_76_HaeModule<` = 1 — 값이 아니라 지시문이다 | 배포본은 `BswInstance_Crypto_76_HaeModule` 로 바꾸라 하지만 같은 이름이 이미 따로 있어 SHORT-NAME 중복이 된다. 이 인스턴스는 MCAL 의 `/Crypto/Crypto`(`BswImplementation_Crypto_43`)를 가리킨다 (#49951) |
| APP | `.settings/com.autron.odin.auto.config.prefs` | 도구 상태 — 커밋하지 않는다 | `git checkout --` 로 되돌린다 | harmonize 가 `Rte_BOOLEAN_BswInstance_Enable` 을 `false`→`true` 로 바꾼다(2026-11-10 실측). 형상이 아니라 도구 상태다 |

## FBL 산출물 등록 (References/FBL_Output)

APP 저장소가 FBL 빌드 결과를 형상으로 들고 있다. **APP 빌드의 입력은 아니다** — `Build/SCons.arxml`·`Build/site_scons/*.py`·`Build/*.bat`·UTIP `.utp` 어디에서도 이 폴더를 참조하지 않는다(2026-11-09 확인). 벤치에서 FBL 을 디버깅하고 어느 FBL 과 짝인지 남기기 위한 자료다.

| 항목 | 규칙 |
|---|---|
| 폴더 | `References/FBL_Output/OEUK_BJ1` · `OEUK_LT2` · `OEUK_TEST` |
| **세트** | **6종 — `.dla` `.dnm` `.elf` `.hex` `.map` `.sre`** |
| 가져오는 곳 | FBL 저장소 `tpms_rf_receiver_bj_fbl/Debug/` |
| 이름 | 폴더의 **직전 버전과 같은 규칙**으로 맞춘다. `OEUK_LT2` 는 `e_lt2_...`, `OEUK_BJ1`·`OEUK_TEST` 는 `e_bj_...` |
| ⚠ 이름 바꿔 넣는다 | FBL 빌드 산출물은 **항상 `e_bj_tpms_asr_swp_fbl_v<ver>`** 다(FBL `PJ_Define.h` 가 OEUK 만 바꾸고 산출물명은 안 바꾼다). `OEUK_LT2` 에 넣을 때 `e_bj_` → `e_lt2_` 로 **반드시 바꾼다** |
| 선택 | `<날짜>_BuildWarning.xlsx` 는 넣어도 되고 안 넣어도 된다 |

⭐ **`.dla`·`.dnm` 이 빠지는 것이 이 프로젝트의 단골 실수다.** GHS 컴파일 옵션 `-dual_debug` 가 디버그 정보를 `.elf` 에서 떼어 두 파일로 내보낸다 — `.dla` 는 `.dlo` 묶음 `ar` 아카이브, `.dnm` 은 `.elf`↔`.dla` 색인. **플래시에 올라가지 않으므로 빌드도 Validation 도 실기도 이것을 걸러내지 못한다.** 없으면 디버거가 변수·행 번호를 못 찾는다.

> 2026-11-10 실측 — 회차 `97536898` 에서 `.elf`·`.hex`·`.map`·`.sre` 4개만 옮겨 `.dla`·`.dnm` 이 빠졌다. FBL 빌드는 둘 다 만들어 `tpms_rf_receiver_bj_fbl/Debug/` 에 그대로 두고 있었다(`e_bj_tpms_asr_swp_fbl_v2110.dla` 8,170,352 B · `.dnm` 1,860,437 B, 2026-11-09 17:35). **빌드 설정이 아니라 복사 누락이었다.**

**점검** — 회차마다 돌린다.

```
python <스킬>/scripts/fbl_output_check.py --root . --fbl-root D:/Mobase/TPMS/tpms_rf_receiver_bj_fbl
```

## 프로젝트 고유 판단 이력
| 규칙 | 근거 |
|---|---|
| Com 은 삭제가 아니라 **제외** — `Ecud_Com.arxml`·`Static_Code/Modules/Com_R44` 를 남기고 SCons ExcludeList 에만 넣는다 | MCP1001-198 댓글[21] |
| MCAL 업데이트 미적용 (IA-079 #7 Advisory) | 당사 회신 2026-10-20, 일감 #49949 §9 |
| IA-086 은 Advisory — 값을 정하고 근거를 남기는 항목 | 일감 #49949 §9 |
| 2026-11-02~03 작업은 HAE 안내를 보고 **수동**으로 진행한 기록이 있다 — patch_tool 을 뒤늦게 돌리면 같은 자리를 두 번 고친다 | 일감 #49949 `Q11` |
| `Ecud_Dem_Mcal.arxml` 의 DemEventId 를 `Ecud_Dem.arxml` 과 맞출 때(IA-068) **미사용 Eth 이벤트(id 9~17)와 충돌**한다. #49951 에서는 `ETH_E_OVERSIZEFRAME` 만 14→18 로 옮겼다. Eth 9개를 유지할지 제외할지 당사 담당자 확인 대기 | #49951 |
| `Ecud_EcuM.arxml` `EcuMDriverInitListTwo` 에서 `Dcm` 을 지워도 `ERR000012`·`ERR000029` 가 나지 않는다(남은 2개 `Nml`·`Mem_ReadAll` 로 충분) | #49951 빌드 #4 실측 |
| APP `.utp` 두 개가 산출물명을 하드코딩한다 — 버전업 위치다. 빠뜨리면 빌드는 성공하는데 `.s19` 가 구 버전으로 나온다 | #49951 빌드 #3·#4 실측 |
