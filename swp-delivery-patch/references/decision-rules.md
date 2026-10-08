# 적용·보류 판단 규칙 (누적)

패치마다 반복해서 나오는 판단을 모은다. 새 규칙은 근거(일감·IMS 댓글·날짜)와 함께 맨 아래에 추가한다. 프로젝트 하나에만 해당하는 것은 프로젝트 프로필에 둔다.

## 공통

| 규칙 | 근거 | 적용 |
|---|---|---|
| HAE 참고 설정(.arxml)은 참고용 — 통째 복사 금지, 3-way 판정 후 항목 단위 반영 | 모든 배포 안내 "참고용" 문구 | 전 패치 |
| 재배포가 있으면 최신본만 쓰고, 이전본과 CRC 대조로 "새 본만으로 충분"을 확인해 기록 | MCP0806-279 (09-04→09-07), MCP0806-280 (09-04→10-06) | 전 패치 |
| 안내문과 배포 형상이 다르면 **최신 형상 + 최신 HAE 답변** 우선, 차이는 기록 | MCP0806-280 Crypto_76 Init 위치 | 전 패치 |
| "필수 아님"으로 온 HAE 형상 정리도 IM 이 요구하는 항목은 필수 취급 | MCP0806-279 Dcm_Init ListOne | 전 패치 |
| 다른 모듈 버전·구성을 전제로 한 변경은 제외 (PDF 파일명, 참고 프로젝트 고유 모듈·버스) | MCP0806-280 Crypto 2.0 PDF, CDD_Router | 전 패치 |
| **patch_tool 이 한 함수에서 함께 넣은 항목은 한 묶음으로 판정**한다. 묶음 중 일부(예: 파일이 존재하는 Ecud 입력)만 떼어 반영하지 않고, 함수 docstring 의 전제(모듈 버전·IM)로 묶음 전체의 적용 여부를 정한다. 판정표에는 묶음의 모든 항목을 같은 사유로 적는다 — 하나라도 사유 없이 빠지면 검수에서 누락으로 보인다 | MCP0806-280 `ensure_haemodule_scons()` (Crypto 2.X: PDF 4곳 + Rte 입력 Ecud_Crypto_76_HaeModule), #48891 10-08 | 전 패치 |
| Harmonize 부산물(순서·CATEGORY·UUID)은 이식하지 않음 | #48909, #48891 | 전 패치 |
| Harmonize 요구 시 C Studio 대신 HAE 결과를 이식하고 Rte Validation 0 errors·Rte API 생성으로 확인 가능 (사용자 동의 하에) | #48881, #48909, #48891 | 전 패치 |
| IA/VC 항목은 실제 경로(CanIf→HRH→HOH 등)를 따라가 기존 충족 여부를 먼저 확인. 충족이면 HAE 의 대량 Can/CanIf 변경은 이식하지 않음 | #48909 IA-079 | 전 패치 |
| PFee 를 쓰지 않는 RTSW 는 PMem_Driver 를 EcuM 에 추가하지 않음 | MCP0806-280 10-06 HAE 답변 | PFee 미사용 APP |
| NvM/Fee 블록 레이아웃을 바꾸는 변경은 양산·OTA 호환을 먼저 확인. HAE 가 "기존 플랫폼은 블록 유지" 재가이드를 낸 사례 있음 | MCP0806-272 10-02 (NvMBlock_DataLog 유지) | NvM 사용 모듈 |
| usercode/Reference_Code 는 HAE 안내대로 전수 검토, 3-way 병합 | 모든 티켓 표준 문구 | 전 패치 |
| 평가용 상위 버전은 끝에서 두 번째 자리 +1 (26810 → 26820). 마지막 자리 변경 금지 | #47539 | H-OTA |

## 모듈별

| 모듈 | 규칙 | 근거 |
|---|---|---|
| Dem_R44 | 3.0.2.0_HF1 은 적용하지 않음 — NvM/Fee 블록 16→17B 로 양산 SW·OTA 호환 깨짐(오토에버 권고). 3.0.1.1_HF5, `DEM_SIZE_OF_EVENT_DATA (6)` 유지. Dem 버전업 요청이 오면 이 판단부터 | #47075 note-17/18, #47967 |
| Dcm (RXSWIN) | RXSWIN UINT8_DYN 동적 길이 변경은 SWP 패치가 아닌 별건(#46778). develop 패치 커밋에 섞여 있으면 분리 | #46778, #47967 |
| Os | SC4→SC1 전환 시 MPU 요구 확인, stack align 은 HAE 정정값(8K) | #48881, #48089 |
| Mem_76_Pfls | WdgDisable/Enable Callout 대신 HwSecurityUnitTempStop/Restart (IA-006), 순서는 Wdg 뒤/앞 | #48292, IA-006 |
| Dcm HF4 | 신규 Validation ERR053296~053312 — 적용 전 당사 Ecud_Dcm 사전 점검 | IM Dcm 4.1.28 |

## 추가 기록

(새 규칙은 여기에 `| 규칙 | 근거 | 적용 |` 형식으로 추가)
