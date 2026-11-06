# 제어기 프로필: LT2/TPMS RF Receiver (확인 2026-11-06)

## 기본
| 항목 | 값 | 출처 |
| --- | --- | --- |
| 제목의 차종/제어기 표기 | `LT2/TPMS RF Receiver` | 사내 일감 선례. **IMS 티켓은 `BJ/TPMS` 지만 당사 적용 대상은 LT2 다** |
| SWP 계열(공용화) (108) | `[R44] BJ/TPMS RF Receiver(S32K312, 100핀)` | ASEC `meta` 분포에 실재 |
| 차량단계 (110) | `P2(LP2)` | ⚠ **필수 필드다** — 비우고 보냈다가 422 로 거부당했다. 페이지 §1 이 "LT2/TPMS **P2 배포 중**, M단계 **예정**" 이라 현재 시점은 P2 다. M 단계로 넘어가면 그때 바꾼다 |
| IMS 프로젝트 | `CP_MOBASE_BJ_TPMS_RF_Receiver` (MCP1001-xxx) | 페이지 §1 |
| MCU | S32K312(NXP), 100핀 · MCAL `S32K3xx_RTD_4.0.0_P24` | 페이지 §1 |
| 제어기 단계 | BJ/TPMS 양산(SOP 완료) · LT2/TPMS P2 배포 중, M단계 예정 | 페이지 §1 |
| 적용 건 일감 | **없다 — 만들지 않았다**(2026-11-06). 회차가 쌓이면 그때 만든다 | ASEC 선례 조회 |
| 패치 자료 폴더 | `D:\Mobase\패치업무\TPMS 실기검증\<차종>\<구분>\<구분>_v<버전>(<IMS키>)\` | 사용자가 넘겨준 경로 |
| 정리 페이지 | Confluence `mobaseasec4` — `<IMS키> [R44][BJ/TPMS][<구분>][V.<x>] Delivery_Patch …` | ecody-ims-patch-monitor |

## 저장소
| | FBL | APP |
| --- | --- | --- |
| 저장소 | **미확인 — 물어본다** | **미확인 — 물어본다** |
| 작업 브랜치 | **미확인** | **미확인** |
| PR 대상 | **미확인** | **미확인** |
| 작업자 로컬 경로 (참고) | `C:\01.Project\00.Mobase\10.Delivery_patch\01.LT2_TPMS\01.tpms_rf_receiver_bj_fbl` | — |

로컬 경로는 첨부의 Generate 로그 머리에서 읽은 것이다(`Generated/Bsw_Output/log/module/Dcm.log`).
**다른 사람의 PC 경로**이므로 내 작업 경로가 아니고, 저장소·브랜치의 근거도 되지 못한다.

## 회차 이력
| 구분 | 버전 | 일감 | IMS |
| --- | --- | --- | --- |
| FBL | 2.1.9 → **2.1.10** | **#49949** (2026-11-06 생성) | MCP1001-198 |
| APP | 2.1.10 → 2.1.11 | (FBL 뒤에 합침) | MCP1001-199 |

## 이 제어기 고유 주의

- **짝 패치와 설정 변경이 거의 겹치지 않는다.** 같은 `Dcm_R44 2.1.1.0_HF2 → HF4` 인데
  DefineOption 이 FBL `DCM_FOTA_USED_FBL` / APP `__GHS__` 로 다르고, harmonize 대상도
  FBL `EcuM·BswM` / APP `Rte·EcuM` 으로 다르다. **"짝과 같겠지"로 넘기면 안 된다.**
- **FBL 설정 변경의 절반은 Dcm 패치와 무관한 정리 작업**이다(Com_R44 빌드 제외,
  EcuMDriverInitListThree 폐지, SCons ShortName 대소문자 2건, FBL 2.0 잔존물 삭제).
  HAE 가 배포할 때 눈에 걸린 것을 함께 안내하는 관행이다.
- **`Com_R44` 는 폴더를 지우지 말고 빌드·Generate 에서만 제외한다**(HAE 답변 11-03).
  빌드 실패(`Com.h` 못 찾음)의 원인이 이 항목이고, 조치 방법은 다른 과제 티켓
  `MCP0858-296` 에 있는데 **403 으로 볼 수 없다**. 작업자나 커밋 이력에서 확인해 기록해야 한다.
- **IA-079 는 처리 불필요로 확정**됐다(10-30). 근거는 "진단 Rx 가 이미 Enhanced FIFO 로
  올바름 + FBL 에는 NM 메시지가 없음". APP 은 다른 근거로 닫혔으니 **한쪽 결론을 일반화하지 마라.**
- **IA-086(`ComMSynchronousWakeUp`)은 Advisory** 이고 문서 지침은 "프로젝트에 맞추어 값을
  정한다" 다. "false 로 바꿔라"가 아니다.

## Harmonize 가 설정 변경 ④와 반대로 작용한다 (2026-11-06 확인)

V2.1.10 회차의 Harmonize 대조표(`Automation_2026-11-02 17_26_19.462.xls`, `Summary` 시트의
`Removed/Created Container` 목록과 `Apply Done`)로 확인한 것이다. **다음 회차에도 같은 일이
일어난다.**

| Harmonize 가 한 일 | 11-03 형상 | 뜻 |
| --- | --- | --- |
| `AC_UserCallout_Com_DeInit`, `AL_DriverDeinit/AI_UserCallout_Com_DeInit` **생성** | 남아 있다 | ⚠ 설정 변경 ④는 이것을 **삭제**하라고 한다. 남으면 BswM 생성 코드가 `Com.h` 를 include 하고, `Com_R44` 는 빌드에서 제외했으니 `fatal error #2330` 이 난다 |
| `AC_EcumDriverInitListTwoEcuMDriverInitItem`, `AL_DriverInitTwo/AI_EcuMDriverInitListTwo` **생성** | 남아 있다 | ⑥이 요구한 것. HAE 는 "이미 되어 있을 것으로 기대"했지만 **없어서 Harmonize 가 만들었다** |
| `TrueAL_CanBorNotification_LCAN_*`, `TrueAL_CanStateNotification_LCAN_*`, `TrueAL_ComModeNotification_LCAN_*`, `CanSMState_LCAN`, `ComMMode_LCAN`, `Dcm_ModeRapidPowerShutDown…` **삭제** | **전부 되살아나 있다** | 당사 고유 설정이다. 작업자가 되돌렸다. 소실이 아니라 **판단의 기록**이다 |

**그래서 이 제어기에서 Harmonize 는 결과를 그대로 받으면 안 된다.** 만든 것 중 ④에 걸리는
것은 지우고, 지운 것 중 당사 고유 설정은 되살린다. 그리고 **Harmonize 를 다시 돌리면 또
같은 상태가 된다** — `swp-delivery-patch/references/protected-settings.md` 가 말하는
"다시 돌리면 또 바뀐다"의 실제 사례다.

EcuM 시트는 **차이 0건**이었다. harmonize 대상이 EcuM·BswM 둘인데 실제로 움직인 것은
BswM 뿐이다.
