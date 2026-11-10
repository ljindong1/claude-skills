# 3-way 판정 — HAE 형상과 당사 설정

**들어가기 전** — 요청 항목 목록과 세 형상(Prev/Cur/Ours)이 있어야 한다. Prev 가 없으면 "Prev 없음"으로 표시하고 시작한다.
**끝났다고 말하려면** — 모든 항목에 판정·경로·근거가 있고, 행마다 과거 회차 이력을 확인했고(원칙 9), 보호 설정에 걸리는 행이 표시돼 있어야 한다.

## 목차
1. 왜 3-way 인가 · 1.5 모듈 계열별 볼 곳
2. 세 형상 확보 · 배포본 완결성
3. ARXML 판정 절차
4. 판정 유형별 규칙과 사례 (4.7 순번·초기화 규칙, **4.8 과거 회차 이력 — 되돌림 확인**)
5. 소스 파일 판정 (**5.4 코드 영향 판정**)
6. 판정표 형식
7. 적용 후 재대조와 Validation 사전 점검

## 1. 왜 3-way 인가

HAE 배포본의 설정 파일은 HAE **참고 프로젝트**(대표 차종) 기준이다. 당사 프로젝트는 같은 SWP 계열이라도 버스 구성, 사용 모듈·버전, 진단 사양, 당사 기능(예: Fota 다운그레이드 콜아웃) 때문에 값이 다르다. 그래서

- HAE Cur 와 당사(Ours)만 비교하면(2-way) "HAE 가 이번에 바꾼 것"과 "원래부터 다른 당사 설정"이 구분되지 않는다. 그대로 복사하면 당사 설정이 HAE 참고값으로 덮인다 — 이전 담당자들이 겪은 "패치 후 당사 로직 문제"의 전형적 원인이다.
- HAE 이전 형상(Prev)을 함께 보면 "HAE 가 바꾼 것"만 정확히 골라낼 수 있고, 그 위치의 당사 값이 HAE 원래 값 그대로였는지(복사 가능) 당사가 손댄 값인지(충돌)도 알 수 있다.

## 1.5 모듈 계열별 볼 곳

모듈 성격에 따라 볼 곳과 기본 경로(A~D, `decision-rules.md` §0)가 다르다. 이번 패치 모듈과 안내에 등장한 모듈을 이 표에 대 보고, 해당 행의 "확인할 것"을 판정표 행으로 미리 만든다.

| 모듈 계열 | 확인할 것 | 기본 경로 |
|---|---|---|
| 저장 계열 — NvM, Fee, Dem, DataLog, Mem_76_Pfls(데이터) | 블록 크기·개수·배치가 바뀌는지, 양산 SW 와 OTA 호환 | D 검토 → 필요 시 C |
| Os | SC 등급·MPU·스택(2^n, SC3/4)·.ld 정렬·LSL, 폴더 대소문자, 컴파일 옵션 | 구성 전제로 판정, 다르면 C |
| EcuM / BswM | 초기화 목록·순번 규칙(§4.7), StartUp 계열 1회 호출, STARTUP_THREE 사용 여부 | A (규칙 적용) |
| Fota / Mem_76_Pfls / Crypto / HSM (주로 FBL) | RamCode·callout·HSM TempStop/Restart 가 **인스턴스마다 빠짐없이** 설정됐는지(빠지면 양산 이슈 MCP0806-271), Gpt 채널, .ld RAM 영역 | A + 실기 |
| Can / CanIf | Harmonize·C Studio 버전 의존, HwObject·HRH 경로 | B → C |
| Dcm | 신규 Validation(사전 점검 §7), SCons 입력, 수평전개 usercode(코드 변경 §5.4), 보안 콜아웃 | A + Validation 점검 |
| Rte | BswInstance 이름 = 모듈명, Harmonize 필요 여부 | A |
| SCons / System(Bswmd, Swcd_Bsw, PortInterfaces) / ECUC 순서·UUID | 대부분 Harmonize·참고 프로젝트 부산물 | 가이드에 있으면 A, 없으면 제외(근거: HAE 답변) |
| usercode / Reference_Code | HAE "사용자 검토·확정" 영역, 수평전개 코드 반영 여부 | 3-way 병합 + 수평전개 대조 |
| 링커(.ld) | 섹션 크기·시작 주소 변경 | 배포본 .ld 와 대조, 다르면 C |

## 2. 세 형상 확보

| 형상 | 1순위 | 2순위 | 없을 때 |
|---|---|---|---|
| Prev | 배포본 `VersionComparison/PreviousVersion` | 직전 회차 IMS 티켓 배포본의 참고 설정 | manifest `project_name`(HAE 기준 형상)이 당사 직전 SWP 와 같으면 **당사 직전 커밋**을 Prev 로 쓰고 그 사실 표시. 그것도 아니면 2-way 로 하고 "Prev 없음" 표시, git 이력으로 당사 수정 여부 보완 |
| Cur | 배포본 `VersionComparison/CurrentVersion` | 배포본 `Configuration`, `Build` | — |
| Ours | 작업 브랜치 현재 파일 | — | — |

배포본 형태가 둘이다. 어느 쪽인지 폴더를 먼저 본다.

| 형태 | 특징 | Prev / Cur | 모듈 본체 | Doc |
|---|---|---|---|---|
| **VersionComparison 형** | `VersionComparison/PreviousVersion`·`CurrentVersion` 제공 | 그대로 | `CurrentVersion/Static_Code/Modules/<모듈>` | 배포본 `Doc` |
| **AutomatePatch 형** | `AutomatePatch.bat` + `patch_tool/` 중심. VersionComparison 없음 | Cur = `Configuration/Ecu/*.arxml` + `Build/SCons.arxml` (안내가 건드리는 파일만 몇 개). Prev 는 위 표의 "없을 때" | `Static_Code/Modules/<모듈>` 과 `patch_tool/Static_Code/Modules/<모듈>` **두 곳 — 내용이 같은지 `diff -rq` 로 확인하고 한쪽만 쓴다** | `Doc/ReleaseNote`, `Doc/ModuleChangeList` |

AutomatePatch 형은 참고 설정이 몇 개뿐이라 **"배포본에 없으니 변경 없음"이 성립하지 않는다** — 안내·IM·patch_tool 계획서가 요구한 자리를 판정표의 기준으로 삼는다(참고 설정은 그중 일부만 보여 준다).

Prev 를 "직전 회차 배포본 + 그 회차 보정본"으로 구성했으면, Prev→Cur 차이 중 **보정본이 바꾼 위치는 HAE 의 새 변경이 아니라 되돌림 의심**이다(4.8). 보정본만 따로 한 번 더 대조한다.

배포본 경로와 저장소 경로를 맞춘다: 배포본 `Configuration/Ecu/X.arxml` ↔ 저장소 `<app>/Configuration/Ecu/X.arxml`. MCAL 설정은 저장소에서 `Configuration/Ecu/Mcal/` 아래인 경우가 있다.

### 2.1 배포본 완결성

형상을 확보했으면 **배포본이 완결된 것인지** 먼저 본다. 배포본이 틀렸던 사례가 1년에 5건 이상이었다 — 배포본은 정답이 아니라 참고다.

- 안내 댓글·IM 이 언급한 파일 목록 ↔ 배포본에 실제 있는 파일을 표로 대조한다. 언급됐는데 없는 파일, 있는데 언급 없는 파일 둘 다 적는다. 빠진 것은 C 후보다.
- 티켓의 이후 댓글·첨부에서 보정본·정정·재배포·삭제를 찾는다(날짜순으로 전부).
- **Prev 형상도 그 회차의 보정본까지 합쳐야 완성이다.** 이번 배포본(Cur)이 그 보정을 담고 있는지는 §4.8 에서 행마다 대조한다 — 최신 배포본이 보정 이전 값으로 나온 사례가 있다.
- 의존 모듈·버전의 정본은 ECM `[ToU 6] SWP 모듈 Baseline Release`(pageId 338751142)다. 배포본 manifest·IM Dependency 와 이 문서를 함께 본다.

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

**함정 — 안내문은 "무엇을 바꿔라"만 말하고 결과 형상을 말하지 않는다.** HAE 안내문과 일감 문구는 HAE **참고 프로젝트**에서 그 변경을 했을 때의 결과를 전제로 쓰여 있다. 당사 구성이 다르면 문구를 글자대로 따른 **중간 상태가 정의 위반**이 되거나, 문구가 가리키는 대상이 당사에 없을 수 있다. 그래서 안내가 언급한 컨테이너는 문구만 보고 편집하지 말고, **배포본 참고 설정에서 그 컨테이너의 최종 모습**(아예 없는지, 몇 개가 남는지, 이름이 무엇인지, 무엇이 그것을 부르는지)을 먼저 확인하고 거기에 맞춘다.

참고 설정에는 **쓰임이 둘**이고 이를 구분한다 — **값을 복사하는 데는 쓰지 않지만**(기본 원칙 2), **최종 형상을 확인하는 데는 반드시 쓴다.**

#49949 에서 같은 안내 한 줄이 양쪽으로 어긋났다.

| 안내 문구 | 당사 실제 | 참고 설정의 최종 형상 | 했어야 할 일 |
|---|---|---|---|
| EcuM `ListThree` 의 KeyM 항목을 삭제 | 항목만 지우니 **빈 컨테이너**가 남아 `ERR000012` 로 생성 중단 | `EcuMDriverInitListThree` 가 **아예 없음** | 컨테이너째 삭제 |
| BswM `AI_EcuMDriverInitListThree` 를 삭제 | 당사에는 `ListTwo` 를 부르는 항목이 없어 그대로 지우면 KeyM 초기화가 사라짐 | `AI_EcuMDriverInitListTwo` 가 **있음** | 참조 교체(실행 슬롯 유지) |

둘 다 "참고 설정의 최종 형상을 먼저 봤는가"로 갈렸다. 아래쪽은 일감 `Q1` 이 미리 지적해 피했고, 위쪽은 확인하지 않아 빌드 한 번을 버렸다.

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

### 5.4 코드 영향 판정

패치가 모듈 **코드**를 바꾸면(수평전개 결함 수정, API 동작 변경) 설정 판정만으로 끝나지 않는다. 바뀐 코드가 당사 ASW·usercode 의 전제를 깨는지 확인한다. 릴리즈 노트·Module Change List·수평전개(CPINFO) 티켓의 변경 설명이 입력이다.

| 변경 성격 | 확인할 것 | 보는 곳 |
|---|---|---|
| API 호출 문맥 요구 (태스크/인터럽트 문맥, 재진입 금지) | 그 API 를 당사가 어디서 부르는지 → 그 함수가 어느 Task·ISR 에서 도는지 | `git grep -n "<API>"` → 호출 함수 → `Ecud_Os` 의 Task·Alarm·ISR 설정 |
| 호출 순서·선행 조건 추가 (Init 전/후, 상태 조건) | 당사 호출 지점이 그 조건을 만족하는지 | usercode·ASW 호출 지점, EcuM/BswM 초기화 순번(§4.7) |
| 검사·권한 주체 이동 (A 모듈 → B 모듈) | 옮겨 간 쪽에 당사 설정이 있는지. 없으면 검사가 **빠진 상태**가 된다 | 해당 모듈 Ecud 의 권한·역할 참조 |
| 반환값·에러 코드 추가 | 당사 호출부가 새 반환값을 처리하는지 — 무시하면 조용히 실패한다 | 호출부 코드 |
| 콜백·콜아웃 시그니처 변경 | 당사 콜아웃 구현의 선언과 일치하는지 | usercode, 빌드 경고 증감 |

판정은 셋 중 하나다 — **해당 없음**(사유: 그 API 를 쓰지 않음, 그 기능 미사용), **확인 완료**(호출 지점·문맥을 적고 영향 없음), **조치 필요**(바꿀 코드·설정을 판정표 행으로). "코드라서 설정과 무관"은 사유가 아니다.

도구: `git grep -n`, `symbol_crosscheck.py`(Prev 가 있을 때 심볼·매크로 변화), 빌드 경고 증감(`verification.md` §2).

## 6. 판정표 — 데이터이고, 표는 생성물이다

**판정표는 마크다운 표가 아니라 `three_way.py --json` 이 만든 데이터 파일이다.** 사람이 쓰는 표는 거기서 `issue_table.py` 가 뽑아낸다. 이 순서를 지키면 **사실을 사람이 타이핑할 자리가 없어진다** — 틀린 값이 들어갈 길 자체가 없다.

```
three_way.py --json 판정표.json        사실 칸을 만든다 (file·key·verdict·prev·cur·ours·basis_auto)
   ↓  사람은 path(A~E)·action 만 채운다. C 면 question 도.
issue_table.py --table 판정표.json --probe <당사 루트> --md 본문절.md --strict
   ↓  ours 가 빈 행(안내·수평전개에서 온 항목)은 --probe 가 실제 ARXML 에서 읽어 채운다
일감 본문에 붙인다
```

- **사람이 채우는 칸은 `path`·`action` 뿐이다.** 값·경로·파일명은 전부 생성된다.
- **`ours` 를 손으로 적지 않는다.** arxml 차이가 아닌 항목(HAE 안내 요청, 수평전개 적용 조건, 의존 모듈 승급 조건)은 `file`·`key` 만 적고 `--probe` 로 읽힌다. "설정을 본다"를 도구가 한다.
- **근거**는 A·E 면 `basis_auto`(= `파일 : 경로 = 현재값`)가 그대로 근거다. B·D 는 따라갈 출처(티켓·댓글·커밋·날짜·IM/SAG 절)를 직접 적어야 하고, 없으면 `issue_table.py` 가 미결로 센다.
- **`Q` 번호는 C 행에만, `issue_table.py` 가 붙인다.** A·B 로 닫힌 것을 Q 목록에 올리지 않는다.
- **"끝났다"는 계산된다** — `--strict` 가 미결 0 이어야 통과한다. 게이트를 글로 지키지 않는다.
- 이력(§4.8)은 `history_trace.py` 결과를 `basis` 에 출처와 함께 적는다. 찾았는데 없으면 "이전 회차 언급 없음", 찾지 않았으면 "미확인".
- 적용 제외·보류는 `action` 으로 구분되어 생성 표에 그대로 나온다.
- 열 정의는 **여기 하나뿐이다.** 다른 문서는 이 절을 가리키고 사본을 두지 않는다. Redmine 결과 코멘트는 생성 표에서 4열(위치 / 처리 / 당사 현재값 / 근거)만 쓴다(templates §2).

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
