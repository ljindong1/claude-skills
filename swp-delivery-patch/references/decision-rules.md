# 적용·보류 판단 규칙 (누적)

패치마다 반복해서 나오는 판단을 모은다. 새 규칙은 근거(일감·IMS 댓글·날짜)와 함께 **해당 표(공통 / 모듈별)의 맨 아래 행**으로 추가한다. 프로젝트 하나에만 해당하는 것은 프로젝트 프로필에 둔다. 규칙을 낳은 사례는 `troubleshooting.md` 에 두고 여기에는 근거 칸에 일감·날짜만 적는다.

## 공통

| 규칙 | 근거 | 적용 |
|---|---|---|
| HAE 참고 설정(.arxml)은 참고용 — 통째 복사 금지, 3-way 판정 후 항목 단위 반영 | 모든 배포 안내 "참고용" 문구 | 전 패치 |
| 재배포가 있으면 첨부를 날짜순으로 **모두** 받아 비교한다. CRC 는 "어느 파일이 개정됐나"까지만 알려 준다 — CRC 가 다른 파일은 내용(three_way.py 이전본→새본)까지 비교하고, 이전본에만 있는 설정은 철회 확인 항목으로 판정표에 올린다. "새 본만으로 충분"은 이 내용 비교 결과를 보인 뒤에만 말한다 | MCP0806-280 09-04 본의 Crypto ListOne 이동이 10-06 본에서 빠져 누락 (#48891 10-12 지적) | 전 패치 |
| 안내 문구·최신 배포본·이전 회차 보정본·HAE 답변이 서로 다르면 **어느 하나를 자동으로 우선하지 않는다.** 최신 배포본도 이전 보정을 빠뜨린 채 나올 수 있다. 회차순으로 값과 근거를 늘어놓고(three-way-merge 4.8) 사용자에게 보이며, 엇갈리면 C 경로로 "어느 쪽이 최종인지" 묻는다. 안내 문구에서 빠진 요청은 IM 링크·같은 날 문답과 대조 전에는 철회로 보지 않는다 | MCP0806-280 Crypto_76 Init 위치(10-06 문구 누락), MCP0806-279 PMem_Driver 위치(3.0.19 배포본이 3.0.18 08-31 보정 이전 값) | 전 패치 |
| "필수 아님"으로 온 HAE 형상 정리도 IM 이 요구하는 항목은 필수 취급 | MCP0806-279 Dcm_Init ListOne | 전 패치 |
| 다른 모듈 버전·구성을 전제로 한 변경은 제외 (PDF 파일명, 참고 프로젝트 고유 모듈·버스) | MCP0806-280 Crypto 2.0 PDF, CDD_Router | 전 패치 |
| **patch_tool 이 한 함수에서 함께 넣은 항목은 한 묶음으로 판정**한다. 묶음 중 일부(예: 파일이 존재하는 Ecud 입력)만 떼어 반영하지 않고, 함수 docstring 의 전제(모듈 버전·IM)로 묶음 전체의 적용 여부를 정한다. 판정표에는 묶음의 모든 항목을 같은 사유로 적는다 — 하나라도 사유 없이 빠지면 검수에서 누락으로 보인다 | MCP0806-280 `ensure_haemodule_scons()` (Crypto 2.X: PDF 4곳 + Rte 입력 Ecud_Crypto_76_HaeModule), #48891 10-08 | 전 패치 |
| **배포본 patch_tool 은 실행하지 않고 읽는다.** 스크립트 docstring·report_action 이 HAE 자동 보정의 목록이다 — P 단계에서 계획서를 만들어 항목마다 판정한다. 툴 docstring 과 IM 이 다르면 IM 을 따르고 기록. 이전 회차 규칙은 그 회차 배포본의 patch_tool 에서 찾는다(배포본마다 스크립트 묶음이 다름) | #48891 note-21 (PMem 규칙이 3.0.18·3.0.19 patch_tool 에 있었음), MCP1001-193 [8] | 전 패치 |
| Harmonize 부산물(순서·CATEGORY·UUID)은 이식하지 않음 | #48909, #48891 | 전 패치 |
| Harmonize 요구 시 C Studio 대신 HAE 결과를 이식하고 Rte Validation 0 errors·Rte API 생성으로 확인 가능 (사용자 동의 하에) | #48881, #48909, #48891 | 전 패치 |
| IA/VC 항목은 실제 경로(CanIf→HRH→HOH 등)를 따라가 기존 충족 여부를 먼저 확인. 충족이면 HAE 의 대량 Can/CanIf 변경은 이식하지 않음 | #48909 IA-079 | 전 패치 |
| PFee 를 쓰지 않는 RTSW 는 PMem_Driver 를 EcuM 에 추가하지 않음 | MCP0806-280 10-06 HAE 답변 | PFee 미사용 APP |
| NvM/Fee 블록 레이아웃을 바꾸는 변경은 양산·OTA 호환을 먼저 확인. HAE 가 "기존 플랫폼은 블록 유지" 재가이드를 낸 사례 있음 | MCP0806-272 10-02 (NvMBlock_DataLog 유지) | NvM 사용 모듈 |
| usercode/Reference_Code 는 HAE 안내대로 전수 검토, 3-way 병합 | 모든 티켓 표준 문구 | 전 패치 |
| **[D 경로] 컴파일러·툴체인 버전 변경을 요구하는 가이드는 채택하지 않는다.** SRS 고정 개발 환경이 우선. 구성을 바꿔(예: MPU 미사용이면 SC1) 요구를 피하고, 피할 수 없으면 VoC 로 올린다 | MCP0806-270 (GHS 2019 요구 → SC1 전환) | 전 패치 |
| **[D 경로] 양산·양산 임박 차종과 같은 SW 를 쓰는 라인은 NvM/Fee 블록·메모리 맵 고정 영역이 바뀌는 모듈 업데이트를 보류**하고 사유를 IMS 에 회신한다. 개발 차종만 적용할지는 별도 검토 | MCP0806-255, MCP1105-113 (Dem), MCP0806-272 (DataLog NvM) | 저장 계열 모듈 |
| 배포본의 `Configuration/System`(Bswmd_*, Swcd_Bsw_*, *_PortInterfaces) 차이는 안내에 없으면 Harmonize 부산물로 보고 제외. HAE 가 세 번 같은 답("무시") | MCP0806-279 [12], 280 [6], 272 | 전 패치 |
| HAE 배포본·.ld 값도 틀릴 수 있다 — 가이드·IM 과 다르면 가이드를 근거로 질문(C). 보정본·정정 댓글을 확인 | MCP0806-256 (PFee 파일 누락), 270 (.ld 스택 정렬 4K→8K), 280 (SCons Ecud_EcuC 누락), MCP1105-104 (SC1용 .ld) | 전 패치 |
| 평가용 상위 버전은 끝에서 두 번째 자리 +1 (26810 → 26820). 마지막 자리 변경 금지 | #47539 | H-OTA |
| 보호 설정(이유 미상 포함)이 바뀌거나 값이 없던 파라미터가 생기거나 사라지면 "동작 차이 없음"이어도 사용자 확인 후에만 반영 — 상세는 `protected-settings.md` §4 에만 둔다 | FBL V3.0.19 Harmonize 시험 2026-10-10 | 전 패치 |

## 모듈별

| 모듈 | 규칙 | 근거 |
|---|---|---|
| Dem_R44 | 3.0.2.0_HF1 은 적용하지 않음 — NvM/Fee 블록 16→17B 로 양산 SW·OTA 호환 깨짐(오토에버 권고). 3.0.1.1_HF5, `DEM_SIZE_OF_EVENT_DATA (6)` 유지. Dem 버전업 요청이 오면 이 판단부터 | #47075 note-17/18, #47967 |
| Dcm (RXSWIN) | RXSWIN UINT8_DYN 동적 길이 변경은 SWP 패치가 아닌 별건(#46778). develop 패치 커밋에 섞여 있으면 분리 | #46778, #47967 |
| Os | SC4→SC1 전환 시 MPU 요구 확인, stack align 은 HAE 정정값(8K) | #48881, #48089 |
| Os | SC1 이면 PFee 가이드의 "MPU 시 스택 통일(8192)" 문구 무시 — 기존 Task 스택 유지, PFee_Process 만 512. SC3/4 는 스택 2^n·32 이상(Os 신규 Validation) | MCP0806-256 [24], MCP1105-104 [8] |
| Mem_76_Pfls | UseRamCode=false 면 Pre/Post callout 설정 안 함. true 면 HSM TempStop/Restart callout 을 **모든 MemInstance** 에(MemInstance1 누락으로 양산 이슈). Wdg callout 은 현재 버전 불필요 | MCP0806-210 [8], 256 [33], MCP0806-271 |
| EcuM / BswM | 순번 규칙(10 단위, StartUp 1회, ListThree 는 ListTwo 뒤) — three-way-merge §4.7 | MCP0806-256 [6][13][18] |
| Mem_76_Pfls | WdgDisable/Enable Callout 대신 HwSecurityUnitTempStop/Restart (IA-006), 순서는 Wdg 뒤/앞 | #48292, IA-006 |
| Dcm HF4 | 신규 Validation ERR053296~053312 — 적용 전 당사 Ecud_Dcm 사전 점검 | IM Dcm 4.1.28 |
