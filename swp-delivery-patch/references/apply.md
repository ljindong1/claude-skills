# 적용 — 수단과 방법

**들어가기 전** — 판정표가 있고, 행마다 "무엇을 어디에"가 정해져 있어야 한다. 판정 없이 손대지 않는다.
**끝났다고 말하려면** — 판정표의 모든 행이 처리·제외·보류 중 하나로 닫혔고, 바뀐 자리 목록이 판정표와 1:1 이고, 적용 직후 `protected_check.py` 를 돌렸어야 한다.

## 1. 수단 셋 — 직접 편집 / C Studio GUI / CLI

| 수단 | 쓰는 자리 | 주의 |
|---|---|---|
| **직접 편집** (`scripts/arxml_block.py`) | 값·컨테이너 몇 개(추가·삭제·이동·이름 변경). 배포본에 원본 블록이 있어 이식하면 되는 경우 | ADMIN-DATA `SD GID` 기록값도 VALUE 와 같이, 줄바꿈·인코딩 유지, XML 파싱 확인 |
| **C Studio GUI** | Harmonize(Generate ECU Configuration), 새 기능 설정(기본값·필수 하위 항목을 툴이 채워야 할 때), ECUC Compare | 옵션이 **기본으로 켜져 있어** 당사 값을 덮는다 → `protected-settings.md` |
| **mobilgene-cli** | 같은 일을 **옵션을 명시해 재현 가능하게**. `-harmonize <json>`·`-script <py>`·`-validation <경로>`·`-regenHandleIds`. 오류 시 자동 롤백 | 아래 전제와 경고 |

CLI 전제 (근거: ECM `[C Studio] CLI` pageId 281118205, `CLI - 10. Harmonize` 281118249, `CLI - 16. Validation` 319476356)

```
mobilgene-cli.exe -nosplash -data <빈 폴더> -consolelog -project <프로젝트> \
                  -validation <저장 폴더> -AgreeTermsEarlyCLI y
```

- C Studio 설치 폴더의 번들 JRE 를 쓴다 — **별도 JRE 설치 불필요**. 요구 버전은 C Studio 2.0 2025-10-R12.0.0 이상.
- `-data` 는 **빈 폴더**여야 한다. 끝나면 지운다.
- **생성 도구 미러 폴더(`ts_mirr` 류)가 필요 없다** — 생성·컴파일 도구가 없는 PC 에서도 Harmonize·Validation·스크립트는 돈다.
- `-harmonize` 의 `ecucGenOptions` 키가 GUI 옵션과 1:1 이다(`overwriteUserConfiguredParametersAndReferences`, `removeUnnecessaryContainers`, `autoRegenerationOfHandleId`, `canEnableBasicTxCanGreaterThan` …) → 옵션표는 `protected-settings.md` §6.
- 배포본 patch_tool 이 만드는 `PREHarmonize.json`·`GENHarmonize.json` 이 이 입력 파일이다.

⚠ **읽기 기능도 프로젝트를 저장한다.** 실측(2026-11-09, C Studio 2.0 2026-06-R13.0.0): `-validation` 만 돌려도 로그에 `Saving project … Done Saving` 이 찍힌다. 그 실행에서 파일 변화는 0 이었지만(3070개 파일 전수 비교), 저장 동작이 있는 것은 사실이다 → **형상을 바꾸는 도구는 복사본·시험 브랜치에서 먼저 돌린다**(기본 원칙).

어느 수단을 쓸지는 판정표 행마다 정한다.

| 직접 편집으로 충분 (모두 해당) | 툴을 써야 함 (하나라도 해당) |
|---|---|
| 바뀌는 값·블록이 적고 위치가 정해져 있음 | **Harmonize 가 실제로 필요** — DBC 재import, Can/CanIf 재생성, Rte 대량 변경 |
| 새로 만드는 항목의 원본 블록이 배포본에 있음 (그대로 이식) | 배포본에 원본 블록이 없는 **새 기능 설정** |
| patch_tool 자동 수정 규칙을 당사 설정에 대 보니 위반 0 | patch_tool 자동 수정이 **실제로 여러 건 걸림** |
| 참조처를 `git grep` 으로 모두 찾을 수 있음 | 여러 파일에 걸친 **구조 변경**(예: 모듈 제거 5곳) |

직접 편집했을 때 툴 대신 지켜야 할 것: (1) `SD GID` 기록값 동기화, (2) XML 파싱 확인, (3) 재대조로 사유 없는 차이 0, (4) 빌드의 생성기 Error 0 · Rte Validation 0 errors 로 툴 검증을 대신, (5) 생성 코드 변화를 하나씩 설명.

## 2. 배포본 patch_tool

배포본의 `patch_tool/` 은 HAE 가 이번 패치를 자기 기준 프로젝트에 적용할 때 쓴 자동 패치 툴이다(`AutomatePatch.bat` → `customer_patch.py` → mobilgene-cli). HAE 입장은 "팀 내 개발 툴, **필수 아님**"(MCP1001-193 [8])이고 사용 가이드가 없다 — ECM 전문 검색에서 `patch_tool`·`AutomatePatch` 0건(2026-11-09).

**읽는 것은 필수다.** 안내에 없는 변경(공통 보정·VC 항목)이 스크립트에만 적혀 있다. 일감에 그 목록을 정리한 절이 있으면 그것이 기준이고, 없으면 계획서를 만든다.

```
python scripts/patch_tool_plan.py --pkg <배포본 루트> --app <당사 앱> [--part FBL|APP] [--search <키워드> …] --out patch_tool_계획.md
```

| 절 | 내용 | 판정표로 |
|---|---|---|
| 1 모듈·버전 | manifest current→target 과 당사 `.ver` 대조 | 모듈 교체 행 |
| 2 실행 순서 | `script_collector.py` 규칙: clear_harmonize → Os_* → **Integrator common** → 모듈(common + 버전 스크립트 `current < v <= target`) → integration_MemMap → Fota → **EcucValueCollection common** → **SCons common** → **ValidationChecker common** → SCons 버전. manifest `scripts` 는 쓰이지 않고 순서도 다르다 | — |
| 3 모듈 스크립트 | docstring 표준: `Previous/Target version`, `Changes`, `Checklist`, `References`(IM 링크). `report_action(...)` 은 실제로 바꾸는 위치·사유. `requestHarmonize / GenPatch / PostPatch` 는 추가 단계 요청 | 항목마다 행 |
| 4 공통 스크립트 | **모든 패치에 붙는** HAE 보정 — Integrator, EcucValueCollection, SCons, ValidationChecker(**VC-nnn = ECM IA-nnn**) | 당사 해당 항목만 행으로, 보호 설정과 대조 |
| 5 툴만 하는 일 | GenerateAll 전 `Generated/`·`Debug/` 삭제, orphan 파라미터 삭제, Harmonize 앞뒤 보정 | 직접 편집할 때 사람이 대신 챙길 것 |
| 7 키워드 검색 | 패치 대상이 아닌 모듈 버전에서 온 규칙을 찾는다 | 이력 칸 |

주의 — 배포본마다 스크립트 묶음이 다르다(그 회차 배포본만 그 회차 기준). 계획서의 APP/FBL·MCU 표시는 docstring 문구로 판단한 **추정**이라 조건은 당사 설정을 열어 확인한다. 스크립트는 mobilgene Script API 전용이라 일반 Python 으로 실행되지 않는다.

**단계는 두 토막이다.** 9단계 중 **1·2 는 설정 변경**(모듈 폴더 복사 + arxml 패치 스크립트), **3~9 는 생성·하모나이즈·컴파일**(`Build.bat GenerateXml` → Gen Patch → Harmonize → Post Patch → `GenerateAll` → 후처리 → `Compile`). 요구 조건과 대체 수단이 다르므로 따로 판단한다.

**실행 여부와 범위는 결정 사항이다.** 결론을 미리 정해 두지 않고 전제를 확인해 정하며, 결정과 사유를 판정표(또는 일감의 해당 `Q` 항목)에 남긴다.

| 전제 | 어디서 보나 |
|---|---|
| 요구 Python·toolset | 배포본 `AutomatePatch.bat`·`customer_patch.py` 머리말 |
| 요구 mobilgene / C Studio ↔ 당사 버전 | 배포본 `Doc/ReleaseNote/*.docx` ↔ 프로필. 다르면 Script API 호환이 확인되지 않은 상태다 |
| 생성·컴파일 도구 보유 (3~9 단계에만 영향) | 프로필 "구성 전제" (`jenkins-flow.md` §3-1·§3-2) |
| 이미 수동으로 한 작업 | 같은 자리를 두 번 고치거나 수동으로 정한 값이 덮인다 |

⚠ **중간에 실패해도 그때까지의 변경은 남는다.** 1·2 단계가 끝난 뒤 3 단계에서 멈추면 툴은 실패로 끝나지만 설정과 모듈은 이미 바뀐 상태다. 되돌리는 길은 git 뿐이다 — 백업 zip 은 모듈 복사 **이후**에 만들어지고 성공하면 지워진다. **"실패"를 "변경 없음"으로 읽지 않는다.**

### 돌렸으면 — 바뀐 자리 목록을 뽑는다

⭐⭐ **이 목록은 적용 후보가 아니라 보고 대상이다.** 담당자 방침(2026-11-10) - "도구에 의한 것은 참조만 합니다. 작업의 고려 대상도 아닙니다. **알려만 주고 패치 작업에는 반영하지 않습니다.**"

그래서 돌린 뒤 하는 일은 셋이다.

1. 모든 줄에 `[도구 산물]` 을 붙여 **사용자에게 목록으로 보고**한다
2. 안내 `2 설정변경`(또는 일감 요청 항목)에 **같은 줄이 적혀 있는 것만** `[안내 요청]` 으로 떼어내 `decision-rules.md` 0 의 A~D 로 판정한다
3. 남은 `[도구 산물]` 은 **판정하지 않고, 적용하지 않고, HAE 에 묻지도 않는다.** 판정표에 `도구 산물 / 미반영` 한 줄로 남긴다

⚠ **가르는 기준은 안내에 그 줄이 있는지 하나다.** `IA-xxx`·`VC-xxx` 사유가 붙어 있다는 것은 기준이 아니다 - 스크립트는 자기가 하는 모든 일에 그럴듯한 사유를 달고 있다.

⚠ **시험 브랜치를 쓰는 이유가 여기서 하나 더 늘어난다.** 적용하지 않을 것을 읽기 위해 돌리는 것이므로, 작업 브랜치에서 돌리면 안 된다 - 되돌리는 길은 git 뿐이다(원칙 10).

판정 경로 -> `decision-rules.md` 0 경로 E. 라벨·보고 양식 -> `communication.md` 7.

툴은 판정 없이 공통 보정을 한꺼번에 넣으므로, **무엇이 바뀌었는지가 손에 있어야** 끝난 것이다.

```
git worktree add ../_before <실행 전 커밋>
python scripts/three_way.py --prev ../_before --cur <현재 작업 폴더> --md 도구변경.md
git worktree remove ../_before
```

- 나온 목록을 판정표와 1:1 로 대조한다. 판정표에 없는 변경은 되돌리거나 사용자 확인을 받는다(`protected-settings.md`).
- **기능이 꺼졌는지 따로 본다** — 자동 교정이 `…Used = false` 로 바꾸는 경우가 있다. `--files Configuration/Ecu/Ecud_Dcm.arxml` 처럼 좁혀 `DcmDsdServiceUsed`·`DcmDsdSubServiceUsed` 의 전후를 표로 만들고, 꺼진 서비스가 이 제어기에서 필요한지 판단한다.
- 툴을 썼으면 `Automation-Results/*.xls` 를 작업 폴더 밖에 보관한다.

## 3. ARXML 편집

- 판정표 "복사 가능"만, **그 요소만** 바꾼다. 통째 복사 금지(기본 원칙).
- `arxml_block.py` 로 블록 이식·삭제·이름 변경·값 변경(SD 기록값 동기화·CRLF 보존).
- **모듈·인스턴스를 빼는 변경**(예: Com 제거)은 설정 참조를 모두 끊고(`git grep`), 그 모듈의 **기존 생성물**도 지운다(`jenkins-flow.md` §5). 참조가 끊긴 채 남으면 Validation 의 미해결 참조로, 빌드에서는 헤더 미발견으로 드러난다(`verification.md` §1).
- **항목을 옮기거나 지웠으면 빈 컨테이너를 남기지 않는다.** ECUC 정의는 컨테이너와 그 하위 항목의 다중도가 따로다 — 컨테이너가 `LOWER=0`(선택)이어도 하위 항목이 `LOWER=1` 이면 **컨테이너가 있는 한 항목이 최소 1개** 있어야 한다. 마지막 항목을 빼면 컨테이너째 지운다. 다중도는 `Configuration/Definition/ECUConfigurationParameters.arxml` 의 그 컨테이너 정의에서 `LOWER-MULTIPLICITY` 로 확인하고, 지울지 채울지는 **배포본 참고 설정에 그 컨테이너가 있는지**로 가른다. 빈 컨테이너는 Validation 에서 `ERR000012 Expected min 1 subcontainers ... Found 0` 으로 드러나며, 생성 단계에서 멈추므로 그 빌드의 생성 코드 확인까지 함께 밀린다(troubleshooting 적용 행).
- 바꾼 직후 `protected_check.py --profile <프로필> --root <앱> --part FBL|APP --before-rev HEAD`.
- 단계마다 `git diff --stat` 으로 줄 수를 확인한다. zip 을 풀 때는 `unzip -l` 로 최상위 폴더를 먼저 보고, 적용 후 `git diff --cached -M --summary` 에 의도하지 않은 rename 이 없는지 본다.

## 4. 모듈 폴더·usercode

판정(무엇을 병합 대상으로 보나)은 `three-way-merge.md` §5. 작업은 이렇게 한다.

- 모듈 폴더: `owner_edits.py` 로 당사 수정 파일을 찾고 → 폴더 삭제 → 배포본 복사 → `diff -rq` 로 바이트 일치 확인. 당사 수정 파일만 `git merge-file -p ours prev cur` 병합본으로 되돌린다.
- `usercode`·`Reference_Code`: 항상 3-way 병합 + 전수 검토. HAE 가 매 티켓에 "모든 c/h 를 사용자가 검토·확정"하라고 적는 영역이다.

## 5. 하모나이즈 실행 — 버전 구간을 먼저 본다

C Studio 버전에 따라 **동작과 필요한 순서가 다르다**(근거: ECM `[C Studio][R44] BswM 하모나이즈 안내 사항` pageId 338741027).

| 구간 | 동작 |
|---|---|
| 12.5.0 미만 | Bswmd 선행 요구 없음 |
| **12.5.0 이상** | 모듈별 **Bswmd 가 있어야 Rule 이 생성된다** — 없으면 그 Rule 이 **조용히 안 생긴다** |
| **13.1.0 이상** | Ecud_Dcm 의 서비스 `Used` 를 보고 notification port 를 자동 생성·삭제 → 순서 의존성 소멸, BswM 만 Harmonize |

당사 버전과 **배포본이 적은 적용 버전이 다른 구간일 수 있다** — 그러면 HAE 는 그 요구가 없던 환경에서 패치를 만든 것이다. 두 버전을 프로필에서 확인하고 시작한다.

12.5.0 이상 · 13.1.0 미만 구간의 순서:

1. `Build.bat GenerateXML`(또는 GenerateAll 을 오류가 날 때까지)
2. 프로젝트 새로고침(F5)
3. `Generated` 에 `bswmd`·`swcd_bsw` 가 생겼는지 **확인**
4. Harmonize(대상 모듈만) → Rte Harmonize → Generation

⚠ 거꾸로 하면 실패한다 — Harmonize 는 `bswmd`·`swcd_bsw` 산출물을 입력으로 쓴다. 파일명에 `" - 복사본"` 이 들어간 arxml 이 있으면 `Cannot Find File` 로 죽는다(patch_tool 은 `.arxml_` 로 바꿔 피한다). patch_tool 을 돌렸다면 `PREHarmonize.json`·`GENHarmonize.json` 은 이미 지워져 있다.

**로컬에 생성 도구(`ts_mirr` 류)가 없으면 1~3 을 Jenkins 가 대신한다** — 설정 변경을 push 하고 `Auto commit from Jenkins #N` 을 pull 하면 `bswmd`·`swcd_bsw` 가 갱신된 상태로 들어온다. 그 뒤에 Harmonize 를 돌리고 다시 push 한다(push 두 번, `jenkins-flow.md` §3-1).

**결과를 그대로 받지 않는다** — 옵션·되돌림 점검·공식 변경점 확인 절차는 `protected-settings.md` §6.

### 5.1 CLI 로 HAE 절차를 그대로 재현하기

`ts_mirr` 없이도 돌아간다(§1). HAE `src/patch_manager` 와 같은 순서·같은 옵션으로 돌리려면 배포본 `patch_tool/module_patch/_harmonize/` 의 스크립트를 쓴다.

```
pre_harmonize.py  -> References/MIA/json/PREHarmonize.json -> -harmonize        (PRE: EcuM 등)
rte_pre_harmonize.py (+ bswm_pre_harmonize.py)                                  스냅샷
gen_harmonize.py  -> GENHarmonize.json -> -harmonize + -script 후처리           (GEN: Rte/BswM/EthSM)
```

- 대상 모듈은 `References/MIA/json/harmonize_registry.json` 에 `{"modules": ["EcuM","BswM"]}` 로 적는다. GEN 단계는 그중 `Rte`·`BswM`·`EthSM` 만 맡고 나머지는 PRE 단계가 맡는다.
- **ODIN 스크립트를 CLI 에 직접 넘기지 않는다.** 배포본 `patch_tool/src/patch_manager/cli_runner.py` 를 **유일한 `-script`** 로 주고, 환경변수 `CP44_RUNNER_CONFIG` 에 JSON(`{"inject_scripts": [], "scripts": [{"path": …, "script_dir": …, "fn": "apply_patch"}]}`)을 담는다. 스크립트가 쓰는 `SCRIPT_DIR` 은 CLI 가 아니라 이 runner 가 넣어 준다 — 직접 넘기면 `NameError: SCRIPT_DIR` 로 죽는다.
- `-harmonize <json>` 과 `-script cli_runner.py` 를 **한 번의 호출에 같이** 준다. 그래야 후처리가 저장 전에 돈다.
- CLI 는 함수를 끝낼 때마다 프로젝트를 저장한다 — 읽기만 하는 함수도 그렇다. 그래서 본 형상에 시험 삼아 돌리지 않고 **복사본에서 먼저** 돌린다.
- 생기는 부산물은 본 형상에 넣지 않는다 — `PREHarmonize.json`·`GENHarmonize.json`·`harmonize_registry.json`·스냅샷 json·`Static_Code/modulesVersion.json`. 대조표 `Automation-Results/*.xls` 는 작업 폴더 밖에 보관한다(`protected-settings.md` §6).

### 5.2 ★ `bswm_post_harmonize.py` 는 직접 돌려야 한다

배포본에 `bswm_pre_harmonize.py`·`bswm_post_harmonize.py` 가 있어도 **HAE 도구는 호출하지 않는다** — `harmonize()` 의 docstring 에만 적혀 있다(`grep -rn bswm_post_harmonize src/` 로 확인된다). BswM harmonize 는 `Com.h` 와 `Com_DeInit` 콜아웃을 **되살리므로**, `Com` 을 쓰지 않는 FBL 에서는 이 후처리를 직접 돌리지 않으면 빌드가 깨진다(troubleshooting 빌드 행).

후처리는 컨테이너는 지우지만 **`DEF-ITEM` 장부 항목은 남긴다** — 끊긴 항목이 되므로 손으로 지운다.

### 5.3 되살아나는 것은 당사에 남은 흔적에서 나온다

harmonize 는 한쪽 설정의 **존재**를 보고 다른 쪽 짝을 만든다. 그래서 "지웠는데 되살아난다"는 대개 **덜 지운 것**이다. 되살림이 보이면 재삭제를 반복하기 전에 **무엇이 그것의 근거로 남아 있는지** 찾는다.

#49949 사례 — EcuM `EcuMDriverInitListThree` 를 빈 컨테이너로 남겨 둔 상태에서는 BswM harmonize 가 `AC/AI_EcuMDriverInitListThree` 짝을 만들고 `BswMActionListItemIndex` 를 밀었다. 컨테이너째 지운 뒤 같은 절차를 다시 돌리니 **되살아나지 않았고 설정값 변화가 0** 이 됐다. 빈 컨테이너 하나가 Validation 오류(§3)와 harmonize 되돌림을 동시에 만든 것이다.

### 5-1. CLI 를 맨손으로 부르지 않는다 — HAE 실행기를 쓴다

`mobilgene-cli.exe` 를 직접 부르면 콘솔에서 **대화형 약관 확인에 걸려 멈춘다.**

```
Do you agree to the terms of service? (y/n) :
```

`mobilgene-cli.ini` 에 `-clearPersistedState` 가 들어 있어 **동의가 보존되지 않는다** — 실행마다 묻는다. GUI 로만 써 온 사용자는 이 프롬프트를 본 적이 없으므로, **이것을 사용자에게 동의해 달라고 요청하면 없는 요구를 만드는 것이다.** 배포본이 이미 답을 갖고 있다.

배포본 `patch_tool/src/patch_manager/mobilgene_executor.py` 가 호출마다 인자를 붙인다(2026-11-10 확인, 88·102·179·211행).

```python
cmd.extend(["-AgreeTermsEarlyCLI", "y"])
```

⚠ 형태를 틀리지 않는다 — **하이픈 하나에 값 `y`** 다. `--AgreeTermsEarlyCLI true` 로 넘기면 듣지 않는다. 실행기가 만드는 전체 명령은 이렇다.

```
mobilgene-cli.exe -nosplash -data <mobilgene설치폴더>\.mobilgene_workspace
                  -consolelog -project <프로젝트>
                  -harmonize <json> [-script cli_runner.py] -AgreeTermsEarlyCLI y
```

`-data` 가 **별도 워크스페이스**를 쓰는 것도 중요하다. 프로젝트 안의 `workspace/.metadata` 를 건드리지 않는다.

**그래서 직접 구현하지 말고 그 클래스를 불러 쓴다.** 인자·순서·후처리가 다 들어 있다.

```python
sys.path.insert(0, str(BUNDLE / "src"))
from patch_manager.mobilgene_executor import MobilgeneExecutor
ex = MobilgeneExecutor(mobilgene_path=<C Studio 설치폴더>, project_path=<저장소>,
                       platform_root=<저장소>,            # project/Configuration 이 있으면 저장소 자신
                       patches_dir=BUNDLE / "module_patch", ar_version="R44")
ex.run_pre_harmonize()   # pre_harmonize.py -> PREHarmonize.json -> -harmonize
ex.harmonize()           # rte_pre -> gen_harmonize.py -> GENHarmonize.json -> -harmonize + rte_post
```

`platform_root` 판정은 `src/common/project_layout.py` 규칙이다 — `project/Configuration` 이 있으면 프로젝트 자신, 없으면 한 단계 아래에서 찾는다.

### 5-2. 두 번으로 나뉘는 이유와 대상 모듈

| 호출 | 하는 일 | 대상 |
|---|---|---|
| `run_pre_harmonize()` | `pre_harmonize.py` 가 `References/MIA/json/PREHarmonize.json` 을 만들고, **그 파일이 생겼을 때만** `-harmonize` 를 부른다 | EcuM |
| `harmonize()` | `rte_pre_harmonize.py`(BswModuleInstance 스냅샷) → `gen_harmonize.py`(`GENHarmonize.json`) → `-harmonize` → `rte_post_harmonize.py`(새로 생긴 BswModuleInstance 삭제) | Rte |

**대상 모듈은 추측하지 않는다 — IMS 안내 댓글 §4 "harmonize 필요 모듈" 에 적혀 있다.** 실측: #49949 FBL = `EcuM, BswM`, #49951 APP = `Rte, EcuM`. 안내를 읽으면 전수 대조 범위가 그 자리에서 좁혀진다(`ims-workflow.md`).

⚠ **`bswm_pre/post_harmonize.py` 는 실행기가 부르지 않는다.** docstring 에 "FBL only" 로 적혀 있고 `harmonize()` 는 `rte_*` 만 연결한다. BswM harmonize 가 `BswMUserIncludeFiles` 의 `Com.h` 와 `AC_UserCallout_Com_DeInit` 을 되살리므로, **Com 을 제외한 프로젝트는 `bswm_post_harmonize.py` 를 직접 돌려야 한다**(#49949 실측, `troubleshooting.md`).

### 5-3. 끝났다고 말하려면

- ⭐ **`References/MIA/json/` 에 `PREHarmonize.json`·`GENHarmonize.json` 이 실제로 생겼는지 눈으로 봤다.** 실행기는 그 파일이 없으면 **건너뛰면서 성공을 돌린다**(`if not pre_json.exists(): return True`) — `OK` 는 돌았다는 근거가 아니다. 드라이버는 `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` 로 띄운다(cp949 콘솔에서 실행기의 출력 스레드가 죽어 JSON 이 안 생긴다 → `troubleshooting.md`)
- `Static_Code/modulesVersion.json` 의 `tool_info` 가 **로컬 C Studio 버전으로 덮였는지** 본다. 당사 기준 버전과 다르면 되돌린다
- 시험 브랜치에서 돌렸고, **컨테이너·파라미터 전수 비교**로 값 변화를 세었다(#49949 실측 형식: "컨테이너 1351 · 파라미터 2266 에서 값 변화 0")
- 보호 설정이 살아 있는지 이름을 들어 확인했다(`protected-settings.md` §6)
- 되살아난 것(`Com.h`·콜아웃·InitList 짝)을 다시 지웠거나, 되살아날 근거가 없음을 확인했다
- harmonize JSON(`PRE`/`GEN`/registry)과 `modulesVersion.json` 은 **부산물이라 커밋하지 않는다**

## 6. 버전업

**끝났다고 말하려면** `version_bump_check.py` 를 돌려 "이전 토큰 잔존 0곳"과 "기대 위치 누락 없음"을 본 뒤여야 한다. 눈으로 훑고 끝내지 않는다 — #49951 에서 `.project` 만 올리고 `.utp` 두 개를 빠뜨렸는데, 빌드는 성공하고 `.s19` 만 조용히 구 버전으로 나왔다. 스크립트를 돌렸으면 그 자리에서 걸렸다.

패치마다 바꾸는 "버전"은 세 종류다. 섞어 쓰면 안 된다.

| 종류 | 의미 | 패치 때 |
|---|---|---|
| SWP 버전 | HAE 플랫폼 패키지 버전 | 바뀜 |
| 산출물명 | 빌드 결과 파일 이름 (SWP 버전 포함) | 바뀜 |
| ECU SW 버전 | 차량이 보는 제어기 SW 버전 (진단 DID, OTA 판정) | **APP 은 바꾸지 않음**, FBL 은 프로젝트 규칙에 따름 |

**어디에 적는지는 프로젝트마다 다르다 — 프로필의 "버전 위치" 표가 정본이다.**

- **APP**: `.project` 의 `<name>`(SConstruct 가 산출물명을 여기서 정한다) 외에 **라이팅·서명 설정 파일**(UTIP `.utp` 의 LOAD/save 경로, aSIMS `.ini` 의 FirmwareFileName)에도 들어간다 — 이쪽을 빠뜨려 재빌드한 사례가 있다. ECU SW 버전(`PJ_Define.h`)은 패치 때 바꾸지 않는다. 평가용 상위 버전은 Jenkins ALL 빌드 스크립트가 임시로 만들고 원복한다.
- **FBL**: 버전 문자가 있는 프로젝트는 `PJ_Define.h` 의 버전 문자를 올린다. 없는 프로젝트는 `.project` `<name>` 한 곳뿐이고 후처리가 `.sre` 이름으로 폴더·접두를 정한다. **다른 과제의 문자 규칙을 적용하지 않는다.**
- **확인**: 버전 문자열을 코드에 두는 프로젝트는 빌드된 `.sre` 의 버전 영역(주소는 프로필)을 판독한다. 없으면 산출물 이름·`.project` 로만 확인하고 판독 방법을 프로필에 적는다.
- **APP 저장소 반영**: 검증을 통과한 FBL 바이너리를 APP 의 `References/02_Fbl_Binary/<변형>/` 에 교체(elf/hex/map/sre, readme). FBL 검증 전에 넣지 않는다 — APP 라이팅이 이 바이너리를 짝으로 쓴다.
- **잔존 확인**: `python scripts/version_bump_check.py <앱 또는 FBL 폴더> <이전 토큰> <새 토큰> --expect <프로필의 버전 위치 파일...>` — 이전 토큰이 남은 곳이 0 이고, 새 토큰이 프로필 목록에 모두 들어갔는지 본다. git 이 추적하는 텍스트 파일 전부를 보므로 프로필에 적히지 않은 위치도 드러난다(T32 `.cmm` 등). 남은 곳이 있으면 **하나씩 판정**한다 — 올릴 것인지, 그 회차에 해당 없는 것인지.
- **Doc**: ReleaseNote·ModuleList·Module Change List 를 프로필 규칙대로 추가한다.

## 7. FBL 산출물 등록 — 세트가 빠지는 것은 아무 검사에도 걸리지 않는다

**들어가기 전** — 프로필의 `FBL 산출물 등록` 절에서 **세트 확장자 목록**과 **이름 규칙**을 읽는다. 프로젝트마다 다르고, 기억으로 하면 빠진다.

APP 저장소가 FBL 빌드 결과를 형상으로 들고 있는 프로젝트가 있다(예 `References/FBL_Output/OEUK_<차종>/`). 이것은 **APP 빌드의 입력이 아니다** — 참조하는 빌드 설정이 없는지 먼저 확인하고, 없으면 "형상 보관"으로 다룬다.

### 왜 따로 절을 두나

플래시에 올라가지 않는 파일이 세트에 섞여 있다. GHS(Green Hills) 컴파일 옵션 `-dual_debug` 가 디버그 정보를 `.elf` 에서 떼어 둘로 내보낸다.

| | 정체 | 타겟에 올라가나 |
|---|---|---|
| `.dla` | `ar` 아카이브. 안에 `.dlo`(번역 단위별 디버그 오브젝트) 수백 개 | **아니오** |
| `.dnm` | `\x7fGHS` 로 시작하는 색인. `.elf` 과 `.dla` 를 잇는다 | **아니오** |
| `.elf` · `.hex` · `.map` · `.sre` | 이미지와 지도 | `.sre`·`.hex` 는 예 |

⭐ **그래서 `.dla`·`.dnm` 이 빠져도 빌드도 Validation 도 실기도 통과한다.** 없으면 디버거가 변수·행 번호를 못 찾을 때 비로소 드러난다 — 그때는 이미 회차가 끝나 있다. **사람이 세는 수밖에 없고, 그래서 스크립트로 센다.**

### 이름을 바꿔 넣어야 하는 경우

FBL 빌드 산출물의 이름은 **FBL `PJ_Define.h` 의 OEUK 선택과 무관하게 고정**인 경우가 있다(TPMS: 항상 `e_bj_...`). 등록 폴더의 관례가 다르면(`OEUK_LT2` → `e_lt2_...`) **복사할 때 바꾼다.** 폴더와 파일의 차종이 어긋나면 나중에 어느 FBL 인지 알 수 없다.

판단 기준은 **그 폴더의 직전 버전 이름**이다. 폴더 이름에서 유추하지 않는다 — `OEUK_TEST` 는 차종이 아니라서 유추가 틀린다.

### 끝났다고 말하려면

```
python <스킬>/scripts/fbl_output_check.py --root <APP 저장소> --fbl-root <FBL 저장소>
```

- **1. 폴더별 등록 상태** — `빠진 확장자` 가 `없음` 인지. 하나라도 있으면 FBL 저장소 `Debug/` 에서 가져온다
- **2. 이름 규칙** — 직전 버전과 base 이름이 같은지
- **3. 빌드가 만든 것 중 옮기지 않은 것** — FBL `Debug/` 에 남아 있는 세트가 등록된 버전인지

`확인 필요 0 건` 이 아니면 **등록이 끝난 것이 아니다.** 커밋 메시지에 "의도된 것인지 확인 필요"로 적어 넘기지 않는다 — 그것은 확인하지 않았다는 말이다.

> 2026-11-10 실측(#49951) — `.elf`·`.hex`·`.map`·`.sre` 4개만 옮겨 `.dla`·`.dnm` 이 빠졌다. 빌드는 둘 다 만들어 FBL `Debug/` 에 그대로 있었다. 커밋 메시지에 "확인 필요"로 적어 두었지만 그것으로는 막히지 않았다. 다른 사람의 같은 회차 작업과 대조해서야 드러났다.
