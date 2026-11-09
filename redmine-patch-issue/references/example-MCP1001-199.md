## 0. 한눈에

| 항목 | 값 |
| --- | --- |
| 모듈 | `Dcm_R44` 2.1.1.0_HF2 → **2.1.1.0_HF4** ★ 중간 버전 **HF3 변경 6 건이 함께 들어온다** |
| SWP | `e_bj_tpms_asr_swp_app` v2.1.10 → **v2.1.11** |
| 고치는 곳 | **arxml 4 개 · 8 군데** (§3) |
| 작업 순서 | `S1`~`S11` (§4) — ★ **순서가 고정이다.** `EcucValueCollection` 등록이 harmonize 의 전제다 |
| Generate 후 | 새 Validation **신규 16 + 변경 1**. `ERR053310`·`ERR053311` 은 **걸릴 가능성이 높다** (§6) |
| 가장 위험한 것 | **`S2`** — EcuM 초기화 리스트에서 `Dcm` 삭제. ⚠ 안내가 쓴 컨테이너 이름(`EcuMDriverInitListTwo`)이 **RTSW 기준과 어긋난다.** 엉뚱한 컨테이너를 지우면 **다른 모듈의 초기화가 사라진다** → `Q1` |
| 설정만이 아니다 | HF3 `CPINFO-3953` — `KeyM_SetCertificate()`·`KeyM_VerifyCertificate()` 를 **같은 task context** 에서 호출할 것. 설정값이 아니라 **ASW 구조** 요구다 → `S6` |
| 돌리지 않는 시험 | OTA `TransferData` Repeat Block · IA-079 BASIC CAN 전환 (§7 `X1`·`X2`) |
| 짝 패치 | `MCP1001-198` (FBL **V.2.1.10**) — 같은 모듈·같은 버전인데 **설정 변경은 겹치지 않는다** |
| 적용 대상 | MCU **S32K3xx** · MCAL `S32K3xx_RTD_4.0.0_P24` · BJ/TPMS **양산(SOP 완료)** · LT2/TPMS **P2 배포 중, M 단계 예정** → **둘 다 MCAL 업데이트 불가** |

**[기입] 작업 정보** — 아래는 이 일감을 받는 사람이 채운다. 추측으로 채우지 않았다.

| | |
| --- | --- |
| 저장소 | |
| 작업 브랜치 | |
| PR 대상 브랜치 | |
| 적용 차종/제어기 | BJ/TPMS (※ 파생 LT2/TPMS 도 수평전개 대상이다 — §9 참고) |
| 착수일 / 완료일 | |

---

## 1. 목적 — 왜 이 패치를 받는가

### 1.1 승급 모듈

```
Dcm_R44   2.1.1.0_HF2 -> 2.1.1.0_HF4     ★ 중간 버전 HF3 의 변경 6 건이 함께 들어온다
```

- SWP — `e_bj_tpms_asr_swp_app` v2.1.10 -> **v2.1.11** (`S9`)
- **의존 모듈 — 늘어난 요구가 없다.** HF4 의 의존 목록이 HF3 대비 증가하지 않았다. 단 **CSAC(L21) 기능을 쓰는 경우에만** `autosar_integration_Dcm_R44-1.5.3.0` 가 필요하다 (`P5`)
- 근거 — 딜리버리 티켓 `MCP1001-199` · 수평전개 사본 `MCP1001-196`(2026-09-15 닫힘) → 원본 `CPINFO-4110`

### 1.2 받는 이유 셋

1. **짝 패치와의 버전 정합성.** FBL(`MCP1001-198`)이 `HF4` 로 올라간다. APP 이 `HF2` 에 남으면 **같은 제어기 안에 `Dcm_R44` 두 버전이 공존한다.**
2. **버전을 올리면 HF3 6 건 + HF4 개선 7 건이 함께 들어온다.** 그중 `DcmResponseToEcuReset = AFTER_RESET` 를 쓰면 **지금 바로 걸리는** 결함 개선이 있다(`CPINFO-3955`). → `S6`
3. **새 Validation 16 개.** 어차피 다음 Generate 에서 터진다. **패치 시점에 한 번에 정리하는 것이 싸다.** → §6

### 1.3 ★ 수평전개 결함 두 건 — 우리 판정을 먼저 읽는다

이 패치는 결함 수정으로 왔지만, **두 결함 모두 APP 에서는 "조건부" 또는 "해당 없음" 이다.** 이것을 모르고 시작하면 **돌릴 수 없는 시험을 붙든다.**

| 결함 | 무엇 | APP 판정 | 근거 |
| --- | --- | --- | --- |
| ① 우선순위 높은 프로토콜의 간헐적 무응답 | 진단 서비스 진행 중 우선순위 높은 신규 요청이 오면 그 요청에 응답이 안 나간다(간헐적). **재시도하면 정상 동작** | ⚠ **미확정** — 대상 조건이 "두 개 이상 프로토콜로 **동시에** 진단하는 제어기" 다. 우리 구성인지 확인되지 않았다 → `Q5` | `CPINFO-4110` |
| ② OTA `TransferData` Repeat Block `NRC 0x71` | 잔여 memory 보다 큰 Repeat Block 요청에 `NRC 0x71`. **복구 방법 없음 · 문제 상황에서 항상 · 협력사 테스트에서 발견** | **해당 없음** — 영향 범위가 FBL 영역이고 당사 제어기는 **Single Bank** 로 리프로그래밍이 FBL 단에서 끝난다. 2026-11-02 당사 제시 → **HAE 같은 날 동의** | 티켓 댓글 \[12\]\[13\] |

★ **따라서 이 일감의 성공은 "결함이 고쳐졌음" 으로 보일 수 없다.** 완료 기준은 §8 이고, 그것이 이 패치의 정직한 모습이다.

---

## 2. 작업 전 준비

| | 할 일 | 주의 |
| --- | --- | --- |
| ☐ `P1` | 배포본 `BJ_TPMS_2.1.11_APP.zip`(10,117 KB) 확보 | ⚠ **2026-11-03 10:04 에 같은 파일명으로 재배포됐다**(최초 09-04 11:40). **9 월에 받아 둔 파일로 작업 중이었다면 반드시 다시 받아 대조한다.** 압축 PW 는 티켓이 아니라 **이메일**로 왔다 |
| ☐ `P2` | 설정 변경 안내(배포 댓글 \[2\]) 최신판 확인 | ⚠ **이 댓글은 2026-09-04 작성 → 2026-11-03 13:42 에 수정됐다.** 처음 받아 둔 안내로 작업하면 **IM 링크가 옛것이다** |
| ☐ `P3` | zip 안의 `.arxml` 용도 확인 | ※ **적용본이 아니다.** HAE 가 "설정 변경 사항 및 Validation Checker 적용을 위한 **참고용**" 이라고 명시했다. 우리 형상에 **덮어쓰지 않는다** |
| ☐ `P4` | 기준 형상 확인 | 현재 `Dcm_R44` 가 **2.1.1.0_HF2** 인지, MCAL 이 `S32K3xx_RTD_4.0.0_P24` 인지 |
| ☐ `P5` | 의존 모듈 확인 | **늘어난 요구가 없다** — HF4 의존 목록이 HF3 대비 증가 없음. 단 **CSAC(L21) 기능을 쓰는 경우에만** `autosar_integration_Dcm_R44-1.5.3.0` 필요 |
| ☐ `P6` | 작업 브랜치 생성 | [기입] §0 |
| ☐ `P7` | 정리 페이지 **부록 B** 를 열어 둔다 | 적용하는 동안 계속 본다 (§10 링크) |

---

## 3. 변경 지도 — arxml 4 개 · 8 군데

★ **"다 했나" 를 세는 자리다.** 경로와 바꿀 값은 §4 의 해당 단계에 있다.

| | 파일 | 군데 | 무엇을 | 단계 |
| --- | --- | --- | --- | --- |
| ☐ | `Build/SCons.arxml` | 2 | `Compile/ASW`·`Compile/BSW` 의 `DefineOption` 에 `__GHS__` 추가 | `S5` |
| ☐ | EcuM 초기화 리스트 | 2 | `Dcm` 를 Os 시작 후 리스트에서 삭제 · `Dcm_Init` 을 `EcuMDriverInitListOne` 에 추가 | `S2` ⚠ **최대 함정** |
| ☐ | `EcucValueCollection` | 2 | BSW 모듈 등록 · `EcucValues` 에 `DataLog` 추가 | `S1` **먼저** |
| ☐ | `Ecud_Rte.arxml` | 2 | `BswInstance_Crypto` ShortName 정정 · `MeasureCPULoad` task 매핑 | `S3` |

**8 군데 전부 HAE 설정 변경 안내에 적혀 있다** — "안내에 없고 IM 에만 있는 항목" 은 이번에 확인되지 않았다.

※ 짝 패치 198(FBL)은 **17 군데**다(`SCons` 5 · `EcuM` 6 · `Rte` 3 · `BswM` 3). **군데 수도 내용도 다르다 — 198 의 표를 가져다 쓰지 않는다.**

---

## 4. 작업 단계 — 순서가 고정이다

★ **왜 고정인가** — `S1`(BSW 모듈 등록)이 harmonize 가 `BswModuleInstance` 를 만드는 전제다. 이것이 없으면 `S3`(`Ecud_Rte` 의 `BswInstance_*`)이 **참조할 대상이 없어 연쇄로 막힌다.**

#### ☐ S1. `EcucValueCollection` 등록 (2 군데)

> 근거 — HAE 설정 변경 안내 댓글 \[2\]

- `EcucValueCollection` 에 **BSW 모듈들을 등록**한다. HAE 설명 그대로: "Harmonize 를 위해 `BswModuleInstance` 생성이 필요하므로 BSW 모듈을 `EcucValueCollection` 에 등록해야 한다."
- `EcucValueCollection/EcucValues` 에 `DataLog` 를 **추가**한다.
- ⚠ **"BSW 모듈" 이 어느 모듈들인지 안내가 뭉개 놓았다** — 구체적으로 적힌 것은 `DataLog` 하나뿐이고 나머지는 "Register BSW modules" 다 → `Q4`
- ※ `EcucValues` 는 목록이다. **기존 항목을 건드리지 않는다.**
- **단계 완료 조건** — 등록이 끝났고, `S4` 의 harmonize 로그에 `BswModuleInstance` 생성 실패가 없다.
- **안 하면** — harmonize 가 `BswModuleInstance` 를 못 만들고 `S3` 가 통째로 막힌다.

#### ☐ S2. EcuM 초기화 리스트 (2 군데) ★ 이번 패치의 최대 함정

> 근거 — IM `380186298` §2.2.7 *(구체 항목·순서는 Sample Image 로만 있다)* · 안내 댓글 \[2\]

- **고칠 것 둘** — ① **Os 시작 후** 초기화 리스트의 `Dcm` 항목 **삭제** ② `EcuMDriverInitListOne` 에 `Dcm_Init` **추가** (`EcuMModuleParameter: NULL_PTR` · `EcuMModuleService: Init` · `EcuMDriverInitItemIndex: 55`)
- **무엇을 하는 변경인가** — `Dcm` 초기화를 **Os 기동 전으로 끌어올린다.** `EcuMDriverInitListOne` 이 "모든 종류의 Os 시작 **전**" 수행이다.
- ⚠ **`Q1` 을 닫기 전에 아무것도 지우지 않는다.** HAE 안내는 `EcuMDriverInitListTwo` 라고 썼지만 **IM 은 "RTSW 기준 `EcuMDriverInitListThree` 이며, FBL 기준으로는 `EcuMDriverInitListTwo` 에 설정" 이라고 적는다.** 199 는 **APP(RTSW)** 다. 이름이 단(段)에 따라 한 칸씩 밀린다.
- ⚠ `index=55` 도 그대로 믿지 않는다 → `Q2`
- **단계 완료 조건** — `Dcm` 이 Os 시작 후 리스트에 **더 이상 없고**, `EcuMDriverInitListOne` 에 `Dcm_Init` 이 **한 번만** 있다.
- **안 하면** — 삭제 누락 시 `Dcm` 초기화가 **두 번** 돈다. 추가 누락 시 Os 기동 전 진단 요청을 받을 준비가 안 된다(HF4 의 "`Dcm_MainFunction` 동작 전 수신 진단 메시지 처리 로직 개선" 이 **바로 이 구간**이라 초기화 위치가 틀리면 그 개선이 무의미해진다). **엉뚱한 컨테이너를 지우면 다른 모듈의 초기화가 사라진다 — 가장 나쁜 경우다.**

#### ☐ S3. `Ecud_Rte.arxml` (2 군데)

> 근거 — 안내 댓글 \[2\]

- `Rte/RteBswModuleInstance/BswInstance_Crypto` → `BswInstance_Crypto_76_HaeModule`. **ShortName 이 모듈명과 같아야 한다** — Rte 생성기가 ShortName 으로 모듈을 찾는다.
- `Rte/BswInstance_OsImp/BswTE_OsImp_MeasureCPULoad/RteBswMappedToTaskRef` 를 `OsTask_BSW_FG1_100ms` 에 매핑한다. 매핑이 없으면 `SAFERTE_ERR_0329` 가 뜬다 — **ERR 번호가 안내에 있으니 그대로 검색해 확인한다.**
- ⚠ 그 task 가 우리 형상에 **존재하는지 먼저 본다** → `Q3`
- ※ 이 이벤트가 **CPU Load 측정**이다. 이 패치 논의에서 당사가 제시한 부하율(평균 16.9% / 최대 22.7%)이 이 측정에서 나왔다. **매핑이 빠지면 그 수치를 더 못 낸다.**
- **단계 완료 조건** — Rte Generate 에서 `SAFERTE_ERR_0329` 가 뜨지 않는다.

#### ☐ S4. harmonize — `Rte`, `EcuM`

- 대상은 **두 모듈뿐**이다(안내 4 항).
- ⚠ **로그를 본다.** `BswModuleInstance` 생성 실패가 `S1` 누락을 알려 주는 **유일한 신호**다.
- ※ **SWP Generator 변경은 해당 없음** — Gentool · `Rte_R44` · mobilgene c studio 모두 "해당없음" 으로 안내됐다. **MCAL generator 는 HAE 정책상 제공되지 않는다.**

#### ☐ S5. `SCons.arxml` DefineOption (2 군데)

> 근거 — SAG `210284000` **§3.3.1.2** (S32K31X)

- `Build/SCons.arxml` 의 `SCons/Build/Compile/ASW` 와 `SCons/Build/Compile/BSW`, **두 곳의 `DefineOption` 에 `__GHS__` 를 추가**한다.
- 빌드 설정이라 harmonize 와 무관하지만 **Generate 전에 끝내 둔다.**
- **왜** — "GHS 기반 MCU 는 `__GHS__` 를 자동으로 정의하지 않으므로 `DefineOption` 에 명시해야 한다."
- ⚠ **MCU 절을 보고 넣는다.** 근거 문서 §3.3.1 이 MCU 별로 갈린다 — §3.3.1.1 `CYTXXX` / **§3.3.1.2 `S32K31X`(우리)** / §3.3.1.3 `TC3XX` / §3.3.1.4 `SPC58X`. **`TC3XX` 는 변경 없음**이고, 문서가 "Tasking 컴파일러에 `__TASKING__` 을 추가하면 **컴파일 에러가 난다**" 고 못 박는다.
- ※ **근거 문서 제목이 "FBL 3.0" 이다**(199 는 APP). **제목만 보고 "우리 것 아니다" 라고 넘기면 두 군데를 놓친다.** APP 전용 IM(`380175655`)의 Define Option 절에는 `__GHS__` 가 없다(그쪽은 `DCM_FOTA_USED` 를 다루고, 그건 §9 대로 우리 대상이 아니다).
- **안 하면** — `__GHS__` 로 갈라지는 코드가 **컴파일에서 빠진다.** 빌드가 되더라도 동작이 달라지거나 링크에서 터진다. **ASW·BSW 두 쪽 모두** 넣는다 — 한쪽만 넣으면 경계에서 어긋난다.

#### ☐ S6. 함께 들어오는 변경의 영향 확인 — 설정과 ASW 코드

★ **티켓은 `HF2 → HF4` 한 줄이지만 HF3 변경 6 건이 함께 들어온다. 어느 안내에도 없다.** Generate 전에 확인해 같은 Generate 에 태운다.

| | 무엇을 확인 | 왜 |
| --- | --- | --- |
| ☐ | `KeyM_SetCertificate()` 와 `KeyM_VerifyCertificate()` 를 **우리 ASW 가 같은 task context 에서 부르는가** | HF3 `CPINFO-3953`. **설정이 아니라 호출하는 쪽(ASW) 의 구조 요구다.** 다른 task 에서 부르고 있으면 **패치만 받아서는 끝나지 않는다** |
| ☐ | `DcmResponseToEcuReset` 설정값 | `AFTER_RESET` 이면 HF3 `CPINFO-3955` — `EcuReset` 긍정 응답에 `SubFunctionId` 가 실리는지 본다. IM 이 "`AFTER_RESET` 를 쓸 필요가 있으면 **이 버전부터 사용**" 이라고 적은 항목이다. `BEFORE_RESET` 이면 HF4 `CPINFO-4057` 쪽 |
| ☐ | WhiteList Service 사용 여부 | HF3 `CPINFO-3956` — WhiteList 에 포함된 DID/RID 의 **권한 검사 계층이 `DSD` → `DSP` 로 바뀐다.** 쓰고 있으면 동작 확인이 필요하다 |
| ☐ | C-SAC Authentication 사용 여부 | HF3 — `pSchMSwitchAuthenticationStateFun` 호출 시점이 바뀐다. **안 쓰면 영향 없다** |
| ☐ | `0x85`(ControlDTCSetting)·`0x28`(CommunicationControl)에 `DcmDsdSubServiceFnc` 를 걸어 두었나 | HF4 — `msgContext` 의 `SubService` 미전달이 개선됐다. **걸어 두었으면 동작이 달라진다** |
| ☐ | 길이 검증 강화 | HF4 — 요청 길이(`SduLength`)와 실제 수신 길이가 **같을 때만** 서비스를 수행한다. **기존에 통과했던 비정상 길이 요청이 이제 거절된다** → `V4` 회귀 |
| ☐ | 정적 분석 결과 비교 | HF3 — Polyspace 정당화 주석이 바뀌었다. **기능 영향은 없고 diff 만 난다**(놀라지 않기 위해 적는다) |

#### ☐ S7. Generate

- 여기서 **새 Validation 16 개가 처음 돈다** → §6 을 펼쳐 놓고 돈다.
- ※ HF4 개선 덕에 **에러가 하나씩 끊기지 않고 한 번에 표출된다.**
- **단계 완료 조건** — 걸린 ERR **하나하나에 "왜 걸렸고 어떻게 닫았는지" 가 기록돼 있다.** 설명되지 않은 ERR 이 없는 상태가 §8 의 기준이다.

#### ☐ S8. 빌드

- ⚠ 짝 패치 198(FBL)에서 `fatal error #2330: cannot open source file "Com.h"` → Jenkins `FAILURE` 가 있었다. **`Com_R44` 를 ExcludeList 에 넣는 설정과 맞물린 자리**였다. APP 에서 같은 증상이 나오면 **198 의 부록 C 를 먼저 읽는다**(같은 저장소·같은 제어기).
- ※ 198 쪽이 조치 근거로 가리킨 `MCP0858-296` 은 **다른 과제라 권한이 없다**(`403`). 무엇으로 고쳤는지는 **작업자나 커밋 이력**으로 확인해야 한다.

#### ☐ S9. SWP 버전업

- `e_bj_tpms_asr_swp_app` **v2.1.10 → v2.1.11**

#### ☐ S10. 실기 검증

- §7 의 `V1`~`V6` 로 한다. ⚠ `X1`·`X2` 는 **돌리지 않는다.**

#### ☐ S11. 기록과 종결

- ☐ 걸린 ERR 과 조치, `Q1`~`Q7` 의 답을 이 일감 **댓글**에 남긴다(다음 회차가 같은 곳을 다시 뒤지지 않게)
- ☐ 짝 패치 198 과 **함께** 올라가는지 확인 — 버전 정합성이 이 패치의 첫째 이유다
- ☐ PR 생성
- ☐ 딜리버리 티켓 `MCP1001-199` 종결 기록. ※ 수평전개 사본 `MCP1001-196` 은 **2026-09-15 에 이미 닫혔다** — 지금 종결 대상은 딜리버리 티켓 쪽이다

---

## 5. 작업 중 멈춰서 확인할 것 — 7 건

★ **답을 모른 채 지나가면 안 되는 것부터 적었다.** 각 항목에 **어떻게 확인하는지**까지 적었다. 답을 찾으면 이 일감 댓글에 남긴다.

| | ID | 무엇이 불확실한가 | 어떻게 확인하나 | 막는 것 |
| --- | --- | --- | --- | --- |
| ☐ | `Q1` | **"Os 시작 후" 초기화 리스트가 우리 형상에서 어느 컨테이너인가.** 안내는 `EcuMDriverInitListTwo`, IM 은 "RTSW 기준 `EcuMDriverInitListThree`", 그리고 IM 에서 그 리스트의 실제 arxml 경로는 `EcuMConfiguration/EcuMFlexConfiguration/EcuMDriverInitListBswM` 이다 | **이름을 믿지 말고 `Dcm` 이 실제로 들어 있는 컨테이너를 열어서 찾는다.** 그것을 지운다 | `S2` 의 삭제 — **틀리면 다른 모듈 초기화가 사라진다** |
| ☐ | `Q2` | **`Dcm_Init` 의 `index=55` 가 우리 리스트에서도 55 인가.** IM 은 "사용하는 모듈에 따라 초기화 항목은 변경될 수 있고, RTU 의 설정된 항목을 참고해 제어기 특성에 맞게 설정한다" 고만 적는다 | `EcuMDriverInitListOne` 의 **앞뒤 항목 index 를 보고 정한다.** IM §2.2.7 의 구체 항목은 **Sample Image 로만 있어** 글자 근거가 없다 | `S2` 의 추가 |
| ☐ | `Q3` | **`OsTask_BSW_FG1_100ms` 가 우리 형상에 존재하는가** | Os 설정에서 찾는다. 없으면 **이름이 비슷한 task 에 임의로 걸지 말고** 100ms 주기 BSW task 를 찾아 맞춘다 | `S3` 의 task 매핑 |
| ☐ | `Q4` | **`EcucValueCollection` 에 등록할 "BSW 모듈" 이 정확히 어느 모듈들인가.** 안내는 `DataLog` 만 구체적으로 적고 나머지는 "Register BSW modules" 로 뭉개 놓았다 | `S4` **harmonize 로그**가 알려 준다 — `BswModuleInstance` 를 만들지 못하는 모듈이 있으면 거기서 드러난다. **로그를 버리지 않는다** | `S1` 의 BSW 모듈 등록 |
| ☐ | `Q5` | **우리 APP 이 두 개 이상 프로토콜로 동시에 진단하는 구성인가.** 결함 ①의 대상 조건이다 | Dcm 프로토콜 설정(`DcmDslProtocolRow` 구성)을 센다 | §1.3 판정 · `V1` 을 돌릴지 말지 |
| ☐ | `Q6` | **IA-079 의 목표 MCAL 버전이 문서 안에서 다르다** — 해결 방법 절은 `4.0.0_HF04`, FAIL #7 가이드는 `4.0.0_HF03`. 티켓에서는 협력사가 `4.0.0_HF2`, HAE 기술 답변이 `4.0.0_HF3` 를 말했다 | **문서로는 닫히지 않는다.** 지금은 "업데이트 불가" 로 종결됐으니 당장 걸리지 않는다 — **MCAL 을 올릴 수 있게 되는 시점에 HAE 에 확인한다** | 이번 작업은 막지 않는다. §9 참고 |
| ☐ | `Q7` | **MCAL 보증 범위 안내(`364422955`)를 못 봤다** — 티켓 본문 링크가 `HTTP 404 {"authorized": false}`(2026-11-07 확인) | **권한 요청**을 하거나, 우회로인 **배포 zip 의 `Doc` 폴더**를 본다 | 이번 작업은 막지 않는다 |

---

## 6. Generate 후 새로 뜨는 Validation — 신규 16 + 변경 1

★ **이 절을 모르고 `S7` 을 돌리면 당황한다.** 출처는 IM `371179712` **§4.1.1.28**(`Dcm_R44-2.1.1.0_HF4`). **티켓과 릴리즈 노트에는 ERR 코드가 하나도 없다.**

※ **중간 버전 HF3(§4.1.1.27)에는 Validation 신규가 없다** — 아래 16 개는 전부 HF4 에서 들어온다. **짝 패치 198 과 이 목록은 같다.**

### 6.1 ★ 먼저 손보면 Generate 가 조용해지는 것 둘

| ERR | 조건 | 왜 걸릴 가능성이 높은가 |
| --- | --- | --- |
| `ERR053310` | UDS **서비스**가 `DcmDsdServiceUsed=true` 인데 `DcmDemIntegrated=false` 이고 사용자 함수(`DcmDsdSidTabFnc`)도 없다. 해당 Service Id: `0x02`·`0x03`·`0x04`·`0x06`·`0x07`·`0x0A`·`0x14` | 조건에 `DcmDemIntegrated = false` 가 들어 있다. 이 값이 `false` 면 **조건의 절반이 기본으로 충족**되고 남는 것은 "쓰는데 사용자 함수가 없다" 뿐이다. 뿌리도 분명하다 — HF4 하위작업 `CPINFO-4052` 가 "Dem 미연동 환경 컴파일 에러 수정 및 **UDS 서비스 Validation 추가**" 다 |
| `ERR053311` | 같은 조건의 **SubService** 판. 해당 Service Id: `0x19`·`0x85` | 위와 같다 |

☐ **선제 점검** — `S7` 전에 우리 `DcmDemIntegrated` 값과 **아홉 서비스**(`0x02`·`0x03`·`0x04`·`0x06`·`0x07`·`0x0A`·`0x14`·`0x19`·`0x85`)의 사용자 함수 설정을 먼저 본다. ※ **"걸린다" 가 아니라 "걸릴 가능성이 높다"** 다 — 우리 실제 설정값은 확인되지 않았다.

### 6.2 나머지 신규 14 개

| ERR | 조건 |
| --- | --- |
| `ERR053296` | `DcmDspRoutineUsePort` 가 `false` 면 `<Fnc Parameter Name>` 를 설정해야 한다 |
| `ERR053297` | `DcmDspVehInfoDataUsePort` 가 `false` 면 `DcmDspVehInfoDataReadFnc` 를 설정해야 한다 |
| `ERR053312` | 반대 — `DcmDspVehInfoDataUsePort` 가 `true` 면 `DcmDspVehInfoDataReadFnc` 를 설정하면 **안 된다** |
| `ERR053298` | `DcmDspPidDataUsePort` 가 `USE_DATA_SYNCH_FNC` 가 아니면 `DcmDspPidDataReadFnc` 를 설정하면 안 된다 |
| `ERR053299` | 반대 — `USE_DATA_SYNCH_FNC` 면 `DcmDspPidDataReadFnc` 를 설정해야 한다 |
| `ERR053300` | `DcmDspPidService` 가 `DCM_SERVICE_01` 이면 `DcmDspPidService02` 컨테이너가 없어야 한다(그 반대도) |
| `ERR053301` | `DcmDspPidDataType` 이 Primitive 면 `DcmDspPidDataByteSize` 가 기대 크기이거나 미설정이어야 한다 |
| `ERR053302` | `DcmDspPid` 는 `DcmDspPidData` 하위 컨테이너를 **최소 하나** 가져야 한다 |
| `ERR053304` | DEM 이 제공하는 PID(`DemIntegrated TRUE`)는 `DcmDspPidData` 가 **하나만** 설정돼야 한다 |
| `ERR053305` | 같은 경우 `DcmDspPidSize` 가 기대 크기여야 한다 |
| `ERR053306` | `DcmDspPidByteOffset + DcmDspPidDataByteSize` 가 `DcmDspPidSize` 를 넘는다 |
| `ERR053307` | `DcmDspPid` 안에서 두 PidData 의 **데이터 범위가 겹친다** |
| `ERR053308` | `DcmDsdSidTabSubfuncAvail` 이 `false` 인데 `DcmDsdSubServiceUsed=true` 인 SubService 가 있다 |
| `ERR053309` | 반대 — `DcmDsdSidTabSubfuncAvail` 이 `true` 인데 쓰이는 SubService 가 하나도 없다 |

### 6.3 변경 1 개

| ERR | 내용 |
| --- | --- |
| `ERR053065` | `DcmStandardSupport` 와 함께 쓸 수 없는 ServiceId 안내. **로그 문구만 개선됐고 로직은 그대로다** — 새로 걸리는 것이 아니다 |

---

## 7. 검증 — 돌릴 것과 돌리지 않을 것

### 7.1 돌릴 것

| | ID | 시험 | 비고 |
| --- | --- | --- | --- |
| ☐ | `V1` | **조건부** — 결함 ① 재현 TC. 진단 서비스 응답 송신 요청 후 `Dcm_TpTxConfirmation` 호출 **전에** 우선순위 높은 프로토콜의 신규 요청을 넣고, **그 요청에 응답이 나오는지** 본다(패치 전에는 특정 타이밍에 무응답) | `Q5` 가 "해당" 일 때만 돌린다. 패치 전 상태에서 **간헐적**이라 한 번에 안 나올 수 있다 |
| ☐ | `V2` | `DcmResponseToEcuReset` 확인. `AFTER_RESET` 이면 `EcuReset` **긍정 응답에 `SubFunctionId` 가 실리는지** 본다 | HF3 `CPINFO-3955`. `BEFORE_RESET` 이면 HF4 `CPINFO-4057` 쪽을 본다 |
| ☐ | `V3` | WhiteList 를 쓰면 DID/RID **권한 검사 동작** 확인 | 검사 계층이 `DSD` → `DSP` 로 바뀌었다 (HF3 `CPINFO-3956`) |
| ☐ | `V4` | 기존 진단 TC **회귀** — 특히 요청 길이가 어긋난 케이스 | HF4 의 `SduLength` 검증 강화로 **기존에 통과했던 비정상 요청이 거절된다.** 통과하던 TC 가 실패로 바뀌면 그게 정상일 수 있다 |
| ☐ | `V5` | `0x85`·`0x28` 에 사용자 함수를 걸어 두었으면 `SubService` 전달 동작 확인 | HF4 개선 |
| ☐ | `V6` | **정적 확인** — Generate 결과에 **설명되지 않은 ERR 이 없다** · 빌드 성공 · `SAFERTE_ERR_0329` 가 사라졌다 · 생성물 diff 가 §3 의 **8 군데 범위 안**이다 | 이 항목이 사실상의 합격선이다 |

### 7.2 ⚠ 돌리지 않을 것 — 적어 두지 않으면 돌릴 수 없는 시험을 붙든다

| ID | 시험 | 왜 안 돌리나 |
| --- | --- | --- |
| `X1` | **OTA `TransferData` Repeat Block** (980 byte 요청 → 200 byte 씩 4 회 → 잔여 180 에서 직전 200 을 Repeat) | **APP 에 재현 경로가 없다.** Single Bank 제어기라 리프로그래밍이 FBL 단에서 끝난다 — 2026-11-02 HAE 동의. **짝 패치 198 이 이 몫을 진다** |
| `X2` | **IA-079 BASIC CAN 전환 확인** | 이 패치의 작업 범위가 아니고 **현 상태 유지로 종결**됐다 → §9 |

---

## 8. 완료 기준

☐ §3 의 **8 군데 전부** 반영됐고 생성물 diff 가 그 범위를 벗어나지 않는다
☐ `Q1`~`Q5` 의 **답이 이 일감 댓글에 적혀 있다**(`Q6`·`Q7` 은 이번 작업을 막지 않으므로 남겨도 된다)
☐ `S6` 의 동반 변경 **7 항목이 전부 확인**됐다 — 특히 **KeyM 두 API 의 호출 context**(ASW 코드)
☐ Generate 에 **설명되지 않은 ERR 이 없다.** 걸린 ERR 마다 **사유와 조치가 기록**돼 있다
☐ 빌드 성공 · `SAFERTE_ERR_0329` 소멸
☐ SWP 버전이 **v2.1.11**
☐ §7 의 `V` 항목 결과가 기록돼 있고, `X1`·`X2` 를 돌리지 않은 사유가 명시돼 있다
☐ 짝 패치 **`MCP1001-198`(FBL V.2.1.10) 과 함께** 올라간다
☐ PR 생성 · 딜리버리 티켓 `MCP1001-199` 종결 기록

---

## 9. 작업 범위가 아닌 것 — 다시 꺼내지 않는다

| 무엇 | 왜 범위가 아닌가 |
| --- | --- |
| **IA-079** 진단 RX 메시지 BASIC CAN 전환 (FAIL #5·#7) | HAE 가 **배포와 별개**로 안내한 잠재 이슈다(안내 본문에 "패치 딜리버리와 별개" 라고 적혀 있다). 당사는 **BJ/TPMS 양산 완료 · LT2/TPMS P2 배포 중**이라 **MCAL 업데이트 불가**로 회신(2026-10-20)하고 **현 상태 유지**로 정리했다. ⚠ **지적이 철회된 것은 아니다** — #5 는 등급이 **Error** 이고 **다음 단계(M 이후·신규 파생)에서 다시 올라온다.** 그리고 **#5 를 고치면 #6(`BASIC` 인데 `CanHwObjectCount < 2`)이 새로 걸릴 수 있다** |
| **"진단 vs Nm 중 어느 쪽을 Basic CAN 으로" 논의** | 2 주를 끌고 **당사 판단으로 닫혔다** — 현 상태(진단 Full CAN + Nm Basic CAN) 유지. 근거는 CPU 부하율 평균 16.9% / 최대 22.7%. ⚠ **HAE 는 "확답을 드리기 어렵다" 고 했다 — 승인이 아니다.** **CPU 부하가 올라가면 이 근거가 무효가 된다** |
| `DCM_FOTA_USED` DefineOption | RTSW IM(`380175655` §2.3.1)이 "RTSW 는 OTA 이중화를 쓰는 경우가 아니면 Fota 모듈이 추가되지 않음(**Single 인 경우 미적용**)" 이라고 적는다. 우리 제어기는 **Single Bank** 다 |
| **SWP Generator** (Gentool · `Rte_R44` · c studio) | 안내 3 항이 **"해당없음"** 으로 명시했다. MCAL generator 는 **HAE 정책상 제공되지 않는다** |
| **의존 모듈 업데이트** | HF4 의존 목록이 HF3 보다 **늘지 않았다**. CSAC(L21)을 쓰는 경우에만 `autosar_integration_Dcm_R44-1.5.3.0` |
| **`Dcm` 외 모듈의 버전업** | 이 패치가 올리는 모듈은 `Dcm_R44` **하나**다. `EcuM`·`Rte`·`EcucValueCollection` 을 건드리는 것은 **Dcm 을 붙이기 위한 통합 설정**이지 그 모듈들의 버전업이 아니다 |

---

## 10. 참고

### 10.1 이 일감의 정본 — 사내 정리 페이지

**본문은 지시만 담았다. 근거와 왕복 기록은 아래에 있다.**

- 대표 — `MCP1001-199` 패치 정리 (page 381714654)
- **부록 A** 변경의 뿌리 (381714679) — 결함 2 건 12 항목 · 버전 경로 · **HF3 6 건** · 의존 모듈 · 자료 공백
- **부록 B** 우리 형상 변경 지도 (381681880) — ★ **적용 중 열어 둔다.** 파일별 변경 · harmonize 순서 · Validation 16+1
- **부록 C** 막힌 것과 끝난 논의 (381747412) — 응대 담당 · 끝난 논의 3 건 · 198 의 빌드 실패 · 문서 권한 전말
- **부록 D** 근거 문서와 첨부 (381681903) — 안내의 절 번호 어긋남 3 건 · 첨부 재배포

### 10.2 근거 문서 (eCoDY-ECM)

| 문서 | 무엇의 근거 | 주의 |
| --- | --- | --- |
| `371179712` **§4.1.1.28** | Validation 16+1 (§6) | ⚠ 안내는 `5.1.1.29` 라고 적었다. **번호가 아니라 버전 문자열 `Dcm_R44-2.1.1.0_HF4` 로 찾는다** |
| `210284000` **§3.3.1.2** | `__GHS__` (`S5`) | ⚠ 안내의 **링크 자체가 잘못됐다** — 제목으로 검색해 찾는다. 제목이 "FBL 3.0" 이지만 **이것이 유일한 근거다** |
| `380186298` **§2.2.7** | EcuM 초기화 리스트 (`S2`) | ⚠ 구체 항목·순서는 **Sample Image 로만** 있다 → `Q2` |
| `380175655` | RTSW SWP 의 Dcm 설정 — `DCM_FOTA_USED` 가 우리 대상이 아닌 근거 | 안내가 가리키지 않았지만 **199 가 APP 이므로 원래 이 문서가 짝이다.** §3.3.1 에 `Scons.arxml` 조건이 추가된 이력(2026-06-02)이 있어 **다음 회차에 다시 본다** |
| `364421062` v28 | IA-079 FAIL 등급 (#5 Error · #6 Error · #7 Advisory) | ⚠ **문서 내부가 어긋난다** → `Q6` |
| `364422955` | MCAL 보증 범위 | ⚠ **404, 못 봤다** → `Q7` |

### 10.3 티켓

- 딜리버리 **`MCP1001-199`** — 댓글 23 건 · 첨부 1 건(재배포) · 담당자 왕복 19 회
- 짝 패치 **`MCP1001-198`** (FBL V.2.1.10)
- 수평전개 사본 `MCP1001-196`(2026-09-15 닫힘) → 원본 `CPINFO-4110`(결함 12 항목)
- 릴리즈 노트 — `CPINFO-3846`(HF2, 시작점) · **`CPINFO-3952`(HF3)** · `CPINFO-4051`(HF4, 목표) · `CPINFO-4170`(HF5, **범위 밖 — 다음 패치가 여기서 출발한다**)
- ※ 하위작업 **10 건의 본문이 전부 비어 있다** — **제목이 자료의 전부다.** 더 찾을 곳이 없다

### 10.4 같은 질문을 다시 할 때 가는 곳

- 일감 생성·보고 — 민병규 / 클래식오토사1팀 *(배포·기술지원 공통 창구)*
- 배포·첨부·문서 권한 — 곽동희 / 클래식오토사2팀
- **CAN·FIFO 기술 답변** — 김형태 / 클래식오토사1팀 *(유선 문의 가능하다고 직접 밝혔다)*
- 통합필수점검(IA-079) — 김경화 / 협력사
- ※ **차량보안모듈(ASK·SFM·CryptoLib·HSM Stack)은 이 창구가 아니다** — 별도 프로젝트다

---

※ 이 일감의 모든 근거는 위 정리 페이지와 부록이고, 그 페이지는 **2026-11-07 17:50 KST** 기준으로 eCoDY 를 조회한 것이다. **그 이후의 티켓 변화는 반영돼 있지 않다.**

---

## 검색 태그

[Delivery_Patch] [패치] [Dcm_R44] [TPMS RF Receiver] [APP] [Validation] [EcuM]
