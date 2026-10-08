# 3-way 판정 — HAE 형상과 당사 설정

## 목차
1. 왜 3-way 인가
2. 세 형상 확보
3. ARXML 판정 절차
4. 판정 유형별 규칙과 사례
5. 소스 파일 판정
6. 판정표 형식
7. 적용 후 재대조와 Validation 사전 점검

## 1. 왜 3-way 인가

HAE 배포본의 설정 파일은 HAE **참고 프로젝트**(대표 차종) 기준이다. 당사 프로젝트는 같은 SWP 계열이라도 버스 구성, 사용 모듈·버전, 진단 사양, 당사 기능(예: Fota 다운그레이드 콜아웃) 때문에 값이 다르다. 그래서

- HAE Cur 와 당사(Ours)만 비교하면(2-way) "HAE 가 이번에 바꾼 것"과 "원래부터 다른 당사 설정"이 구분되지 않는다. 그대로 복사하면 당사 설정이 HAE 참고값으로 덮인다 — 이전 담당자들이 겪은 "패치 후 당사 로직 문제"의 전형적 원인이다.
- HAE 이전 형상(Prev)을 함께 보면 "HAE 가 바꾼 것"만 정확히 골라낼 수 있고, 그 위치의 당사 값이 HAE 원래 값 그대로였는지(복사 가능) 당사가 손댄 값인지(충돌)도 알 수 있다.

## 2. 세 형상 확보

| 형상 | 1순위 | 2순위 | 없을 때 |
|---|---|---|---|
| Prev | 배포본 `VersionComparison/PreviousVersion` | 직전 회차 IMS 티켓 배포본의 참고 설정 | 2-way 로 하고 "Prev 없음" 표시, git 이력으로 당사 수정 여부 보완 |
| Cur | 배포본 `VersionComparison/CurrentVersion` | 배포본 `Configuration`, `Build` | — |
| Ours | 작업 브랜치 현재 파일 | — | — |

배포본 경로와 저장소 경로를 맞춘다: 배포본 `Configuration/Ecu/X.arxml` ↔ 저장소 `<app>/Configuration/Ecu/X.arxml`. MCAL 설정은 저장소에서 `Configuration/Ecu/Mcal/` 아래인 경우가 있다.

## 3. ARXML 판정 절차

```
python scripts/three_way.py --prev <Prev 폴더> --cur <Cur 폴더> --ours <저장소 앱 폴더> \
       [--files Configuration/Ecu/Ecud_EcuM.arxml Build/SCons.arxml ...] [--md 판정표.md]
```

- `--files` 를 생략하면 Prev ↔ Cur 에서 달라진 ARXML 을 자동으로 찾는다.
- 비교 단위: `컨테이너 경로#파라미터 정의명` → 값 목록. 같은 파라미터가 여러 번 나오는 리스트(예: SCons InputFilesList)는 집합으로 비교한다.
- UUID, ADMIN-DATA, 컨테이너 순서는 비교에서 뺀다(Harmonize 부산물).
- 출력: 항목별 `판정 / Prev / Cur / Ours`. 리스트 값은 추가·삭제 요소로 보여 준다.

판정 결과를 그대로 믿지 말고 "다른 구성 전제" 여부를 사람이 본다 — 스크립트는 그 항목이 이 프로젝트에 해당하는지 모른다.

## 4. 판정 유형별 규칙과 사례

### 4.1 복사 가능 (HAE 변경, Ours = Prev)

해당 요소만 Cur 값으로 바꾼다. `ADMIN-DATA` 의 `SD GID="<파라미터명>"` 값과 시각도 같이 바꾼다(HAE 배포본이 그렇게 함).

- 예: Rte `BswInstance_Crypto_HaeModule` → `BswInstance_Crypto_76_HaeModule` (모듈명과 ShortName 일치). 다른 파일 참조가 없는지 `git grep` 로 확인 후 변경.
- 예: EcucValueCollection 에 `/AUTOEVER/DataLog` 추가 — 당사 `Ecud_DataLog.arxml` 의 패키지 경로가 같은지 먼저 확인.

### 4.2 기존 충족 (Ours = Cur)

바꾸지 않는다. 판정표에 "기존 충족"과 근거(현재 값)를 남긴다 — 이게 없으면 리뷰어가 누락인지 해당 없음인지 모른다.

- 예: OsImp MeasureCPULoad → OsTask_BSW_FG1_100ms (이미 매핑됨)
- 예: IA-079 진단 Rx BASIC CAN — 당사 진단 Rx HOH 를 CanIf → HRH → HOH 로 따라가 BASIC·Count≥2 확인

### 4.3 당사 전용 충돌 (Ours ≠ Prev, Ours ≠ Cur)

1. 당사 값의 유래: `git log -S '<값>' -- <파일>` / `git log -L` 로 커밋·일감을 찾는다.
2. HAE 변경 의도: IM 절, 안내 댓글, patch_tool 스크립트 주석.
3. 두 의도를 합친 값을 제안하고 사용자 확인. 애매하면 IMS 질문.

- 예: EcuM ListTwo — HAE Cur 는 `PMem_Driver 0 / HsmDriver 1 / Crypto_76 2 / Mem_ReadAll 3`. 당사는 PFee 를 쓰지 않아 PMem_Driver 가 없고 `HsmDriver 1 / Crypto_76 2 / Mem_ReadAll 3`. HAE 의도는 "Dcm 을 ListTwo 에서 빼고 Index 를 0부터 순차". 합친 결과 `HsmDriver 0 / Crypto_76 1 / Mem_ReadAll 2`. PMem_Driver 는 IMS 답변("PFee 미설정이면 RTSW 는 추가하지 말 것")을 근거로 추가하지 않음.
- 예: 안내문은 "Crypto_76 Init 을 ListOne 으로"였다가 개정 안내에서 빠짐 → Cur 형상(ListTwo 유지)을 근거로 옮기지 않음. 안내문과 형상이 다르면 형상과 최신 답변을 우선하고 기록한다.

### 4.4 제외 (다른 구성 전제)

- **모듈 버전 차이**: HAE 참고 프로젝트가 더 높은 버전의 다른 모듈을 쓴다. 예: SCons 입력에 `Crypto_76_HaeModule_ECU_Configuration_PDF` 추가 — Crypto_76_HaeModule **2.0.0.0** 부터 바뀐 PDF 파일명(patch_tool 의 `patch_Crypto_76_HaeModule_v2_0_0_0.py` 주석). 당사가 1.0.4.0 이면 해당 파일이 없으므로 제외.
- **구성 차이**: 참고 프로젝트에만 있는 모듈·버스(CDD_Router, L2CAN/L3CAN, Eth/Lin).
- **기능 미사용**: PFee, Authentication ES 등.
- **Harmonize 부산물**: 컨테이너 순서, CATEGORY 태그, UUID, 같은 내용의 재배치. 실제 값 변화가 없으면 이식하지 않는다.
- **잘못 첨부**: HAE 가 "무시"라고 답한 파일(예: MODE_PortInterfaces.arxml).

### 4.5 보류 (회사 규칙)

`decision-rules.md` 의 규칙에 해당하면 적용하지 않고 근거를 남긴다(예: Dem_R44 3.0.2.0 — NvM/Fee 레이아웃 변경으로 양산·OTA 호환 깨짐).

### 4.6 HAE 가 이미 고친 당사 과거 이슈

안내에 "IM 과 다른 항목이 많아 일괄 수정, 필수 아님"처럼 HAE 형상 정리가 섞여 오면, 각 항목을 4.1~4.5 로 다시 분류한다. "필수 아님"이어도 IM 이 요구하는 것(예: Dcm_Init 은 ListOne)은 필수로 다룬다.

### 4.7 순번·초기화 규칙 (EcuM / BswM)

HAE 답변(MCP0806-256 08-31, 280 10-06)으로 확인된 규칙. 번호를 HAE 와 똑같이 맞출 필요는 없고 규칙만 지키면 된다.

- BswM `BswMActionListItemIndex` 는 10 부터 10 단위(10, 20, 30 …). EcuM `EcuMDriverInitItemIndex` 는 0 부터 순차.
- StartUp 계열 콜아웃(예: `PMem_Driver_StartUp`)은 BswM 이든 EcuM 이든 **한 번만** 호출되게 한다. 양쪽에 다 있으면 이중 호출.
- `AI_EcuMDriverInitListThree` 는 반드시 `AI_EcuMDriverInitListTwo` 보다 뒤. FBL 은 HAE 형상에 STARTUP_THREE 단계가 없다 — 사용 여부는 BswM 에 `TrueAL_EcuState_StartUpThree` 가 있는지로 판정.
- 목록에서 항목을 빼거나 옮기면 남은 항목의 번호를 HAE 의 번호 규칙대로 당사 구성에 다시 매긴다(4.3 예시).

**함정 — Prev = Cur 인데 당사만 다른 항목.** 스크립트는 HAE 가 바꾸지 않은 위치를 "무관"으로 보고 넘긴다. 그런데 당사 값이 과거부터 HAE 와 달랐고 이번 안내가 그 위치를 요구하면 놓친다(예: 3.0.19 에서 `Dcm_Init` 은 Prev·Cur 모두 ListOne 에 있었지만 당사는 ListTwo 에만 있었음). 초기화 목록처럼 안내가 직접 언급한 컨테이너는 '순번 목록' 절에서 Prev / Cur / Ours 구성을 나란히 보고 판정한다.

## 5. 소스 파일 판정

### 5.1 모듈 폴더 (`Static_Code/Modules/<모듈>`)

```
python scripts/owner_edits.py --prev <Prev>/Static_Code/Modules/<모듈> --ours <앱>/Static_Code/Modules/<모듈> --repo <앱 저장소>
```
- Ours 와 Prev 가 다른 파일 = 당사 수정(또는 다른 버전). 스크립트가 그 파일들의 git 커밋 제목을 붙여 보여 준다.
- 다른 파일이 없으면 폴더 통째 교체 → `diff -rq Cur Ours` 로 바이트 일치 확인.
- 있으면 그 파일만 `git merge-file -p ours prev cur > merged` 로 병합하고, 나머지는 교체.
- 사례: `CanTrcv_255_Autoever.c` 는 당사가 nSTB·Port 처리를 넣은 이력이 있어 교체 시 병합 대상.

### 5.2 usercode / Reference_Code

HAE 가 매 티켓에 "모든 c/h 를 사용자가 검토하고 최종 코드를 fix·검증"하라고 적는 영역이다. 배포본에 들어 있으면 항상 3-way 병합한다. Prev 가 없으면 직전 배포본에서 같은 파일을 찾는다. 당사가 손댄 대표 파일은 프로젝트 프로필에 목록이 있다(EcuM_Callout_Stubs, Dcm_Callout_*, Fota_User_Callouts 등).

### 5.3 빌드 스크립트·툴셋

`Build/*.bat`, `site_scons`, `bat_package` 는 당사 빌드 후처리(UTIP, MemoryUsage, PostPackage, Hook)가 붙어 있는 경우가 많다. 공식본을 기준으로 하되 당사 후처리 호출을 유지하고, 프로필의 "당사 빌드 후처리" 목록과 대조한다.

## 6. 판정표 형식

| HAE 요청 | 판정 | 경로 | 이전 상태 (Ours) | 처리 (파일) | 확인 근거 |
|---|---|---|---|---|---|

- 행 = IMS 요청 항목(S1) + 사전 점검(P)의 위험 포인트 행 + 스크립트가 찾은 추가 차이.
- "경로"는 `precheck.md` 의 A(스스로 확정) / B(과거 자료) / C(HAE 질문 — 답 오기 전에는 "확인 중"과 잠정 처리) / D(회사 기준 보류).
- "확인 근거"에는 재현 가능한 근거만 쓴다: "HAE Cur 와 바이트 일치", "다른 파일 참조 0건", "IMS 10-06 답변", "빌드 Rte Validation 0 errors".
- 적용 제외·보류는 표 아래에 사유와 함께 따로 모은다.

## 7. 적용 후 재대조와 Validation 사전 점검

### 재대조

`python scripts/three_way.py ... --check` — Ours(적용 후)와 Cur 의 남은 차이만 출력한다. 남은 차이 = 판정표의 제외·보류·충돌 처리 항목과 1:1 이어야 한다.

### 생성물 영향 예측

설정을 바꿨으면 어떤 생성 파일이 바뀔지 미리 적어 두고 빌드 후 `gen_diff_review.py` 결과와 맞춰 본다. 예상과 다르면(바뀌어야 하는데 안 바뀜, 안 바뀌어야 하는데 바뀜) 원인을 설명할 수 있어야 한다.

### 신규 Validation 사전 점검 (예: Dcm HF4)

IM 의 "Validation 신규" 항목을 당사 Ecud 에 적용해 본다. 예시 규칙:
- ERR053296: `DcmDspRoutineUsePort=false` 인데 Routine 관련 Fnc 미설정
- ERR053308 / 309: `DcmDsdSidTabSubfuncAvail` 과 활성 SubService 존재 여부 불일치
- ERR053310 / 311: `DcmDemIntegrated=false` 인데 DEM 계열 서비스에 사용자 함수 없음
- ERR053297 / 312: VehInfoData UsePort ↔ ReadFnc 불일치

`xml.etree` 로 컨테이너를 순회하며 조건을 검사하는 짧은 스크립트로 충분하다. HAE patch_tool 에 같은 이름의 자동 수정 스크립트(`patch_<모듈>_<버전>.py`)가 있으면 그 docstring 이 규칙 목록이다.
