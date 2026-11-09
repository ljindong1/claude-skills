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

**결과를 그대로 받지 않는다** — 옵션·되돌림 점검·공식 변경점 확인 절차는 `protected-settings.md` §6.

## 6. 버전업

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
- **잔존 확인**: `python scripts/version_bump_check.py <앱 또는 FBL 폴더> <이전 토큰> <새 토큰>` — 이전 토큰이 남은 곳이 0 이고, 새 토큰이 프로필 목록에 모두 들어갔는지 본다.
- **Doc**: ReleaseNote·ModuleList·Module Change List 를 프로필 규칙대로 추가한다.
