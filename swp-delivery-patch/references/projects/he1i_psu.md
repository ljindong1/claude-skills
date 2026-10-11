# 프로젝트 프로필: HE1i PSU (확인 2026-10-08)

## 기본
| 항목 | 값 |
|---|---|
| SWP 계열 | [R44] SP3i/PSU 계열 (CYT2BL7CAS, 144핀, with OTA 메모리이중화) |
| IMS 프로젝트 | CP_MOBASE_SP3i_PSU (MCP0806-xxx). 대표 차종 SP3i 기준이며 HE1i 는 파생 — HAE 참고 설정은 SP3i 형상 |
| 같은 계열 | SP3i, BJ1, HE1i, NQ6e, NQ6a, SX3e (수평전개 회신 단위) |
| Redmine | mobilgene Classic - MOBASE ASEC / Task. 사용자정의: 일감검토자, 일감완료자, SWP 계열(공용화), SWP 계열 버전, 차량단계 P2(LP2) |
| 상태 규칙 | ASEC Task: 상태 4 → 2 → 18 한 단계씩(담당자일 때만), 진척률은 상태가 정함, 해결 시 담당자 = 검토자(이승빈) 자동 |
| 패치 자료 폴더 | `D:\Mobase\패치업무\HE1i_실기검증\v<버전>[(fbl)]\<IMS키>\` |
| 정리 문서 위치 | Confluence mobaseasec4 폴더 347930626 (PSU Power Seat Unit), 페이지 제목 `[#일감] HE1i PSU <FBL/APP> V<x> Delivery_Patch` |

## 저장소
| | FBL | APP |
|---|---|---|
| 저장소 | http://ccm.mobaseelec.com:3000/tglee/psu_fbl_master | http://ccm.mobaseelec.com:3000/tglee/psu_master |
| 로컬 경로 | `D:\Mobase\psu_fbl_master` | `D:\Mobase\psu_master` |
| 하위 프로젝트 | `psu_fbl/` | `psu_app/` |
| 작업 브랜치 | `devel_HE1i_jdlee_FBL_patch_Update` | `devel_HE1i_jdlee_R44_DeliveryPatch` |
| PR | `feature/swp_patch_v<x>_HE1i` 에 **squash 한 커밋** → `develop_he1i` | 버전별 `feature/he1i_swp_patch_v<x>` 에 패치 커밋 cherry-pick + Generated 갱신 + H-OTA 결과 + 산출물 → `develop_he1i` (이전엔 앞 버전 feature 위에 쌓음) |
| Jenkins Job | `HE1i_PSU_FBL_jdlee` | `HE1i_PSU_AUTOSAR_jdlee` |
| 참고 브랜치 | develop (SX3e), APSU 적용본 `apsu_master_sjyoo` | 같음 |

## 버전 위치
| 대상 | 파일 | 규칙 |
|---|---|---|
| APP 산출물명 | `psu_app/.project` `<name>`, `References/Doc_MB/01_CRT_UTIP_CFG/psu_sf2.0_utip_Reprogramming.utp`, `psu_sf2.0_utip_Writing.utp`, `aSIMs_sample_ini.ini` | `he1i_psu_app_v3_0_xx` 4곳 모두 |
| APP ECU SW 버전 | `Application/app_code/a_app_service/src/PJ_Define.h` SOFTWARE_VERSION_0~4 (OEUK_HE1I / OEUK_TEST 블록) | 26810 유지. 평가용 26820 은 ALL 빌드가 임시 생성 |
| JENKINS_BUILD_TARGET | 같은 `PJ_Define.h` | CURRENT / ALL |
| FBL 버전 문자 | `psu_fbl/Application/app_code/a_app_service/src/PJ_Define.h` SOFTWARE_VERSION_5 | 'H'=3.0.17, 'I'=3.0.18, 'J'=3.0.19 → HE130J02 / DEV30J02, 내부 02 유지 |
| FBL 산출물명 | `psu_fbl/.project` | `he1i_psu_fbl_v3_0_xx` |
| FBL 확인 | `.sre` 0x10029000 MainSW_Version_Info | |
| FBL 바이너리 (APP) | `psu_app/References/02_Fbl_Binary/OEUK_HE1I{,_TEST}/` elf/hex/map/sre, readme | FBL 검증 통과 후 |
| Doc | `References/Doc/ReleaseNote/SWP_ReleaseNote_SP3I_PSU(<날짜>)_v<x>.docx`, `References/Doc/ModuleChangeList/SP3I_PSU_APP_ModuleList_<날짜>_v<x>.xlsx`, `SP3I_PSU_APP_SWP_Module_Change_List_<날짜>_v<x>.xlsx` | 날짜 = HAE ReleaseNote 날짜 |

## 당사가 수정한 HAE 파일 (교체 시 병합 대상)
| 파일 | 내용 | 근거 |
|---|---|---|
| `Static_Code/Modules/CanTrcv_255_Autoever/CanTrcv_255_Autoever.c` | nSTB·Port 핀 처리, include | #38061 |
| `integration_EcuM_R44/usercode/src/EcuM_Callout_Stubs.c`, `inc/EcuM_Cbk.h` | 당사 EcuM 콜아웃, DataLog 호출 | #38061, V3.0.28 |
| `integration_Fota_F/usercode/Fota_User_Callouts.c/.h` | Fota_DualMemDownGradeChk_UserCallout | #47539 |
| `integration_Dcm_R44/usercode/Dcm_Callout_User.c`, `Dcm_Callout_SecureService.c` | 보안접근·인증 콜아웃 (Dcm 내부 심볼 사용) | #38061 |
| `integration_Wdg/usercode/WdgStack_Callout.h` | | #38061 |
| `integration_MemMap_R44/usercode/User_MemMap.h` | | #38061 |
| `integration_Pfls_R44/usercode/*`, `integration_Mem/usercode/*` | | #38061 |

## 당사 빌드 후처리
`Build/Build_Hook_HE1I.bat`(ALL/CURRENT 분기), `BuildVariants.bat`(4벌), `PostPackage.bat`(Debug/OEUK_HE1I/<버전> 정리, rom zip), `MemoryUsage.bat`, UTIP 후처리, `GitPush.bat`. toolset 교체 때 공식 Build.bat 을 쓰더라도 이 호출들은 유지.

## 구성 전제 (사전 점검 P ① — 확인 2026-10-08)
HAE 의 조건부 답변("당사가 X 면 해당 없음")을 판정하는 기준. 패치마다 바뀐 것이 없는지 확인한다.

| 전제 | FBL | APP | 확인 위치 |
|---|---|---|---|
| Os 확장 등급 / MPU / Timing Protection | SC1 / 미사용 / 미사용 | SC1 / 미사용 / 미사용 (V3.0.27 때 SC4→SC1, MCP0806-270) | Ecud_Os `OsScalabilityClass`, NonTrusted Application 유무 |
| PFee 사용 | **사용** (Attempt Counter, `OsTask_BSW_PFee_Process` 스택 512) | 미사용 (PFee Task·PFEE_PART 없음 → PMem_Driver 추가 안 함) | Ecud_Os, Ecud_Mem_76_Pfls, App_DiagnosticService.c |
| UseRamCode | true (HSM TempStop/Restart callout 필요, MCP0806-271) | false (Pre/Post callout 설정 안 함, MCP0806-210) | Ecud_Mem_76_Pfls MemGeneral |
| 컴파일러 (SRS 고정) | GHS ARM.V2017.1.4 | 같음 | SCons.arxml |
| mobilgene C Studio | 2.0 2026-06-R13.0.0 (`C:\mobilgene\mobilgene_C_Studio_2.0_2026_06_R13.0.0`, 워크스페이스 `D:\mobilgene_workspace`) | 같음 | Harmonize 옵션이 버전마다 다름. 이 버전에는 IA-079 가이드의 "Select Rx Diag Messages for OTA" 옵션이 없음(2026-10-10) |
| 사용자 PC 생성 도구 | `D:\ts_mirr` 없음 → C Studio Generate Code·Build 불가(2026-10-11 시험). mobilgene 생성기 라이선스는 보유, 본체 미설치. 생성 결과는 Jenkins 커밋으로 확인 | 같음 | jenkins-flow §3-1 |
| MCU | CYT2BL (Mcal_Infineon_CYTxxx 1.18.1_Aut01) | CYT2BL (Mcal 버전은 APP .ver 로 확인) | Static_Code/Modules/b_mcal_* .ver |
| 같은 계열 양산 단계 | SP3i·BJ1 양산 / HE1i·NQ6e·NQ6a·SX3e 개발 (2026-08 기준) | 같음 | 양산 호환 판단(D 경로) |
| 대표 차종 | HAE 참고 설정은 SP3i 형상 (CDD_Router, L2/L3CAN 등 SP3i 고유 포함) | 같음 | |

## 프로젝트 사실 (판정에 쓰임)
- Dcm: `DCM_NUM_OF_PROTOCOLCONFIG = 1` (프로토콜 1개), `DcmDemIntegrated = true`(APP) / `0`(FBL), `DCM_AUTHENTICATION_ES_SUPPORT = STD_OFF`
- PFee: FBL 사용 / APP 미사용 (위 구성 전제)
- Crypto_76_HaeModule 1.0.4.0 (HAE 참고 프로젝트보다 낮을 수 있음)
- FBL: Fota GPT 채널 TCPWM_0_18 / CLOCKS18 5000Hz (#38061), Attempt Counter 사용
- 진단 Rx: 0x7A3 물리 / 0x7DF 기능

## 보호 설정 (당사가 일부러 정한 값 — 확인 2026-10-11)
HAE 참고 설정·VC·Harmonize 결과와 **다른 것이 정상**인 값이다. Harmonize, CLI, 수동 편집, 이 스킬의 반영 중 무엇으로든 바뀌면 "동작 차이 없음"이어도 판정표에 사유를 쓰고 사용자 확인을 받는다(`references/protected-settings.md`). `scripts/protected_check.py` 가 이 표를 읽는다 — 키는 three_way.py 와 같은 `컨테이너 경로#파라미터` 형식, '(없음)' 은 파라미터가 없어야 함(생성기 기본값 사용). 이유를 모르는 값도 "이유 미상"으로 올려 둔다.

| 구분 | 파일 | 키 | 당사 값 | 이유·근거 |
|---|---|---|---|---|
| FBL | Ecud_CanIf | `/CanIf/CanIfPublicCfg#CanIfMetaDataSupport` | 1 | 이유 미상(#38061 부터). VC·Harmonize 는 0. 2026-10-10 시험에서 Harmonize 가 0 으로 덮어씀 — 현재 쓰는 PDU 없음 |
| FBL | Ecud_Can | `/Can/CanConfigSet/OUT_HwObj_FBL_BCAN_0x7ab_BCAN_DPSU_PSU_DRV_GST#CanFdPaddingValue` | (없음) | 없으면 생성 255(0xFF). Harmonize·VC 는 0 명시. 0x7AB 는 STANDARD_FD_CAN 송신(CanTp 패딩 0xAA 활성) |
| FBL | Ecud_Can | `/Can/CanConfigSet/IN_HwObj_0x7a3_0x7a3_FBL_BCAN#CanHwObjectCount` | 10 | IA-079 수동 적용(#48891). SAG "2 이상" vs VC 64 → MCP0806-279 10-08 질문, 잠정 10 |
| FBL | Ecud_Can | `/Can/CanConfigSet/IN_HwObj_FBL_BCAN_0x7df_BCAN_GST_ALL#CanHwObjectCount` | 10 | 위와 같음. Harmonize 는 객체 이름을 `IN_HwObj_0x7df_0x7df_FBL_BCAN` 으로 바꾼다(키 없음으로 나옴) |
| FBL | Ecud_Can | `/Can/CanConfigSet/IN_HwObj_FBL_BCAN_0x7df_BCAN_GST_ALL#CanRxBufferSelection` | CAN_RX_FIFO1 | IA-079 (#48891 db33bf33) |
| FBL | Ecud_Gpt | `/Gpt/GptChannelConfigSet_0/GptChannelConfiguration_Fota#GptTimer` | TCPWM_0_18 | IA-092 를 VC 의 TCPWM_0_54 대신 18 로 적용(#38061). 이유 기록 없음 |
| FBL | Ecud_Gpt | `/Gpt/GptDriverConfiguration/GptClockReferencePoint_Fota#GptClockReference` | /Mcu/Mcu/McuModuleConfiguration_0/McuClockSettingConfig_0/McuClockReferencePoint_TCPWM0_CLOCKS18 | 위와 같음 |
| FBL | Ecud_Mcu | `/Mcu/McuModuleConfiguration_0/McuClockSettingConfig_0/McuClockReferencePoint_TCPWM0_CLOCKS18#McuClockReferencePointFrequency` | 5000 | 위와 같음. VC 는 CLOCKS54 를 5000 으로 씀 |

APP 보호 설정은 아직 정리하지 않았다 — 다음 APP 패치 S6 에서 VC/HAE Cur 대비 당사 고유값을 뽑아 채운다.

## 실기 기준값
| 항목 | 기준 |
|---|---|
| 라이팅 | cvd-project, 과제 `HE1I_PSU`, `--mode IMAGE --banks AB`, FBL 짝 자동(`_test` ↔ OEUK_HE1I_TEST). 검증 지점 16 + 다른 뱅크 4 |
| CAN 벤치 | VN1640A, CH3 B-CAN / CH4 Local. 기준(V3.0.27~28): B-CAN 실패 0 / 주의 0 / 정보 12 / 통과 3, Local 정보 8 / 통과 21, 에러 프레임 0 |
| 진단 | CDD 가 실제로는 SP3i 사양서 — HE1i 사양 적합으로 단정 금지, cfg 의 CDD 연결부터 확인 |
| 보드 이미지 확인 | DID F1C1(APP SHA-256)을 aSIMS 해시와 대조 (SW 버전 26810 고정이라 버전 DID 로는 회차 구별 불가) |
| 서명 | rom zip 4개 → 플랫폼설계팀(aSIMS) → `aSIMS_enc_signed_{he1i|test}_psu_app_v3_0_xx_<버전>` |
| H-OTA | A1~A4(OEUK_HE1I) / B1~B4(OEUK_TEST), TC_004~009 매핑. 체크리스트 Confluence 348160048(V3.0.28) 복사 사용 |
| 결과 폴더 | `References/Doc_MB/04_Reprogramming/v<x>/<YYMMDD>/` |
| 첨부 이름 | `HE1i_PSU_v<x>_<YYMMDD>_{HOTA_asc|HOTA_log|HOTA_png|aSIMS_bin|CAN_bench|<고유>|report_xlsx}.zip` |

## 프로젝트 고유 판단 이력
| 규칙 | 근거 |
|---|---|
| Dem_R44 3.0.2.0_HF1 미적용 | #47075 note-17/18 |
| RXSWIN UINT8_DYN(#46778)은 별건 — develop 패치 커밋에서 분리 (Ecud_Dcm, Ecud_Rte, App_Dcm, PJ_Define.h 제외, App_DiagnosticService.c 마지막 hunk 제외) | #46778 |
| IA-079 APP 기존 충족(0x7A3/0x7DF BASIC). FBL 은 0x7DF FULL → 변경 필요 | #48909, #48891 |
| Rte/BswM Harmonize 는 이식으로 대체 (V3.0.27~29) | #48881, #48909, #48891 |
| EcuM ListTwo: HsmDriver 0 / Crypto_76 1 / Mem_ReadAll 2 (PMem_Driver 없음) | MCP0806-280, #48891 |
