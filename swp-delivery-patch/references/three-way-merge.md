# 3-way 판정 — HAE 형상과 당사 설정

## 목차
1. 왜 3-way 인가
2. 세 형상 확보
3. ARXML 판정 절차
4. 판정 유형별 규칙과 사례 (4.7 순번·초기화 규칙, **4.8 과거 회차 이력 — 되돌림 확인**)
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

Prev 를 "직전 회차 배포본 + 그 회차 보정본"으로 구성했으면, Prev→Cur 차이 중 **보정본이 바꾼 위치는 HAE 의 새 변경이 아니라 되돌림 의심**이다(4.8). 보정본만 따로 한 번 더 대조한다.

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

- 예 (**APP**, HE1i V3.0.29): EcuM ListTwo — MCP0806-280 10-06 패치 파일 Cur 는 `PMem_Driver 0 / HsmDriver 1 / Crypto_76 2 / Mem_ReadAll 3`. 당사 APP 은 PFee 를 쓰지 않아 PMem_Driver 가 없다. IMS 10-06 답변("PFee 미설정이면 RTSW 는 PMem_Driver 추가 불필요")으로 PMem_Driver 는 넣지 않고, HAE 번호 규칙(0부터 순차)만 적용한다. 같은 패치의 09-04 패치 파일·Crypto IM 은 `Crypto_76_HaeModule_Init` 을 ListOne 으로 옮긴다 — 최종 결과는 ListOne Crypto(Index 29), ListTwo `HsmDriver 0 / Mem_ReadAll 1` (당사 HE1i `4a777484d`). 처음에는 10-06 본만 보고 Crypto 를 ListTwo 에 남겨 리뷰어 지적을 받았다(troubleshooting S5).
- 예 (**FBL**, HE1i V3.0.19): FBL 은 PFee 를 쓰므로(Attempt Counter) PMem_Driver 가 필요하다. 3.0.18 08-31 보정본 기준 EcuM ListTwo `PMem_Driver 0 / HsmDriver 1 / Crypto_76 2 / KeyM 3`, BswM 의 같은 호출은 삭제 (`ca6273a4`). **같은 모듈이라도 APP / FBL 구성 전제가 다르면 결론이 반대가 된다** — 예시를 옮겨 쓸 때 대상(APP/FBL)부터 확인한다.
- 안내 문구·최신 배포본·이전 보정본이 서로 다르면 어느 쪽도 자동으로 우선하지 않는다(decision-rules 공통, 4.8).

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

### 4.8 과거 회차 이력 — 이번 배포본이 이전 보정을 되돌렸나

3-way 는 "이번 회차 HAE 가 무엇을 바꿨나"만 본다. 그런데 HAE 배포본은 **직전 회차의 보정본·정정을 빠뜨린 채 예전 형상으로** 나오기도 한다. 이 경우 Ours = Cur 라서 "기존 충족", Prev = Cur 라서 "무관"으로 넘어간다.

**언제 확인하나.** 판정표의 모든 행. 특히 ① HAE 변경 항목, ② 안내·IM 이 언급한 컨테이너, ③ 리뷰어 지적 항목, ④ Prev 를 이전 회차 배포본 + 보정본으로 구성했을 때 Prev→Cur 가 "보정 이전 값으로 돌아가는" 방향인 항목.

**어떻게 확인하나.**
0. 같은 위치를 다루는 HAE patch_tool 규칙을 찾는다 — `patch_tool_plan.py --pkg <이번·이전 회차 배포본> --search <컨테이너·항목명>`. 모듈 버전 스크립트에 규칙이 있으면(예: `Mem_76_Pfls_Common v2.1.0.0` [7] PMem_Driver ListTwo, `Crypto_76_HaeModule v1.0.7.0` Crypto Init ListOne) 그 버전이 당사에 적용됐는지, 이번 배포본 참고 설정이 그 규칙과 맞는지 본다.
1. 같은 위치(컨테이너·파라미터)를 이전 회차 IMS 티켓에서 찾는다 — 보정본 첨부(날짜순 전부), 정정 댓글, 당사 문의와 HAE 답변. 수평전개 티켓도 본다.
2. 당사 git 이력: `git log -S '<값>' -- <파일>` / `git log -G '<컨테이너명>'` 로 그 값이 들어오거나 빠진 커밋·일감을 찾는다. 다른 차종 브랜치(develop 등)도 같은 위치를 본다.
3. 이전 Redmine 일감(같은 계열 Delivery_Patch, 리뷰어 코멘트)에서 그 위치가 언급됐는지 본다.
4. 결과를 회차 순서로 늘어놓는다: `회차·파일(날짜) → 값`. 설정 값은 `scripts/history_trace.py` 가 뽑아 준다 — `--rev` 를 회차순으로(보정본은 이름에 "보정"), `--ours` 로 당사, `--git-text` 로 당사 커밋까지. 같은 키가 A→B→A 로 돌아오거나 보정본 값이 마지막 회차에서 달라지면 ★ 표시가 붙는다. 마지막 보정 이후 값이 바뀐 근거(안내·답변)가 없는데 이번 배포본만 예전 값이면 **되돌림 의심**이다.

**어떻게 처리하나.**
- 판정표 "이력" 칸에 회차별 값과 근거를 적고, 판정은 "되돌림 의심 — 확인 필요"로 둔다. 자동으로 어느 쪽도 고르지 않는다.
- 사용자에게 두 근거를 나란히 보여 정하게 한다. 근거가 엇갈리면 IMS 질문(C 경로): "3.0.18 08-31 보정본은 X, 3.0.19 배포본은 Y 입니다. 어느 쪽이 최종입니까?"
- 반영했다면 회신·Redmine 에 "이번 배포본은 Y 였으나 이전 보정(X)을 따름"을 적는다.

**사례 — FBL PMem_Driver 위치 (HE1i, 2026-10).**

| 회차·파일 | `PMem_Driver_StartUp` 호출 위치 |
|---|---|
| 3.0.18 최초 배포 (MCP0806-256) | BswM `AL_DriverInitTwo` user callout |
| 3.0.18 08-31 보정본 (`Ecu.zip`, PFee 설정 가이드) | EcuM ListTwo Index 0 (`PMem_Driver`, VOID, StartUp), BswM AL 항목 삭제 |
| 3.0.19 배포본 (MCP0806-279, 09-07) | BswM `AL_DriverInitTwo` (보정 이전 값) |
| HE1i V3.0.19 적용 (#48891, 10-08) | BswM — 3.0.19 와 같아 "기존 충족"으로 통과 |

Prev 를 "3.0.18 + 08-31 보정본"으로 구성했으므로 Prev→Cur 에 "EcuM → BswM" 변경이 보였다. 그런데 이것을 HAE 의 의도된 변경으로 보고 넘겼다. 2026-10-12 리뷰어(#48891 note-21)가 #48292 note-3 의 보정본 미반영을 지적했고, EcuM 방식으로 반영했다(`ca6273a4`). 같은 위치는 마스터 `origin/develop` 도 BswM 방식이었다.

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

| HAE 요청 | 판정 | 경로 | 이전 상태 (Ours) | 처리 (파일) | 확인 근거 | 이력 (이전 회차) |
|---|---|---|---|---|---|---|

- 행 = IMS 요청 항목(S1) + 사전 점검(P)의 위험 포인트 행 + 스크립트가 찾은 추가 차이.
- "경로"는 `precheck.md` 의 A(스스로 확정) / B(과거 자료) / C(HAE 질문 — 답 오기 전에는 "확인 중"과 잠정 처리) / D(회사 기준 보류).
- "확인 근거"에는 재현 가능한 근거만 쓴다: "HAE Cur 와 바이트 일치", "다른 파일 참조 0건", "IMS 10-06 답변", "빌드 Rte Validation 0 errors".
- "이력"에는 4.8 로 찾은 이전 회차 값과 근거(회차·티켓·댓글 날짜, 당사 커밋·일감)를 적는다. 찾았는데 없으면 "이전 회차 언급 없음", 찾지 않았으면 비워 두지 말고 "미확인".
- 적용 제외·보류는 표 아래에 사유와 함께 따로 모은다.
- 이 표가 판정표의 **유일한 형식**이다. 다른 문서(protected-settings §7 등)의 예시 행도 이 열 순서를 따른다. Redmine 결과 코멘트는 이 중 4열(요청 / 이전 상태 / 처리 / 근거)만 쓴다(templates §2).

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
