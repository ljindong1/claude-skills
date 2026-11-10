# 보호 설정과 덮어쓰기 점검 — Harmonize·도구·수동 반영 공통

**들어가기 전** — 프로필의 '보호 설정' 표(이번 대상 FBL/APP 행)가 있어야 한다. 없으면 판정 단계에서 채울 항목으로 표시하고 시작한다.
**끝났다고 말하려면** — `protected_check.py` 의 '확인 필요'가 0 이거나 남은 항목이 모두 판정표 결정과 1:1 이고, 되돌린 값마다 사유·사용자 확인 날짜가 적혀 있어야 한다.

## 목차
1. 왜 따로 점검하나
2. 덮어써지는 세 경로
3. 변경 분류 (a)~(d)
4. 규칙
5. 시점별로 하는 일
6. Harmonize 를 돌릴 때
7. 기록 형식

## 1. 왜 따로 점검하나

패치 후 당사 로직 문제의 대부분은 **당사가 일부러 정한 값이 다른 값으로 바뀌었는데 바꾼 쪽도 검토하는 쪽도 의식하지 못한 경우**였다. 바뀐 Ecud 는 Jenkins 가 다시 생성해 자동 커밋하므로, 설정 단계에서 놓치면 생성 코드까지 조용히 바뀐 채 지나간다.

그 순간에는 "지금 쓰는 곳이 없다", "동작 차이 없다"로 판단되는 경우가 많다. 그런데 그 판단이 틀렸거나, 나중에 그 기능을 쓰게 되면서 문제가 드러났다. 그래서 **보호 설정이 바뀌는 것은 영향 분석 결과와 상관없이 사람이 확인한다.**

사례 (FBL V3.0.19, 2026-10-10 Harmonize 시험, Can·CanIf 만 선택, 옵션 기본값):
- `CanIfMetaDataSupport` 1 → 0 (Overwrite User-Configured 옵션). 쓰는 PDU 는 없었다.
- 0x7AB `CanFdPaddingValue` 없음(생성 0xFF) → 0 명시. CAN FD 송신의 빈 바이트 값이 바뀔 수 있다.
- 진단 수신 `CanHwObjectCount` 10 → 64, 0x7DF 객체 이름 변경, ObjectId·RxPduId 재배정.
- 결과는 VC 견본과 Can/CanIf 기준으로 완전히 같았다 — **VC 견본 = Harmonize 결과물**이다. VC 와 맞추는 것은 곧 Harmonize 로 덮어쓰는 것과 같다.

## 2. 덮어써지는 세 경로

| 경로 | 어떻게 바뀌나 | 놓치기 쉬운 이유 |
|---|---|---|
| Harmonize (C Studio "Generate ECU Configuration", mobilgene CLI) | Overwrite User-Configured / Remove Invalid / Auto-Regeneration of Handle Id 가 **기본으로 켜져 있다** | 바뀐 내역이 git 무시 폴더 `Automation-Results/*.xls` 에만 남는다. 텍스트 diff 는 타임스탬프 잡음에 묻힌다 |
| 이 스킬·사람의 반영 | HAE Cur·VC 를 정답으로 보고 "차이를 맞춘다" | 3-way 에서 VC = 정답이라는 편향. 당사 값의 이유가 저장소에 없는 경우가 많다 |
| 생성기 기본값 | 값이 **없는** 파라미터는 생성기 기본값을 쓴다. 누가 값을 명시하거나 지우면, 또는 모듈 버전이 바뀌어 기본값이 바뀌면 생성 코드가 바뀐다 | 설정 diff 에는 "파라미터 추가"로만 보이거나 아예 안 보인다. 생성 코드 diff 에서만 드러난다 |

## 3. 변경 분류 (a)~(d)

적용·Harmonize 뒤 Ecud 전후 차이를 이렇게 나눈다. three_way.py `--check`, protected_check.py, 의미 비교(타임스탬프·UUID 제외) 결과를 합쳐 본다.

| 분류 | 뜻 | 처리 |
|---|---|---|
| (a) 의도된 변경 | IMS 안내·IM·IA/VC 규칙이 명시한 변경, 3-way "복사 가능" | 판정표 근거대로 |
| (b) **보호 설정 변경** | 프로필 '보호 설정' 표의 값이 바뀜, 또는 키가 없어짐(이름 변경·삭제) | **4장 규칙 — 반드시 사용자 확인** |
| (c) 이름·순서·ID | 컨테이너 이름, ObjectId, Handle ID, 순서만 바뀜 | 손으로 쓴 코드(Application, usercode, Static_Code)가 그 이름·번호를 쓰는지 `git grep` 으로 확인. 쓰면 (b) 로 올린다 |
| (d) **기본값 의존 변화** | 양쪽에 있는 컨테이너 안에서 파라미터가 새로 생기거나 사라짐 | **4장 규칙 — 반드시 사용자 확인**. 생성 코드에서 기본값 → 명시값 차이를 찾는다 |

보호 설정 표에 없는 값이라도 당사 값이 HAE Prev·Cur·VC 와 모두 다르면(3-way "충돌") 보호 후보다. 이유를 찾아 표에 올리자고 제안한다.

## 4. 규칙

1. **(b)·(d) 는 "동작 차이 없음"으로 판단했어도 자동 통과시키지 않는다.** 판정표에 현재 값 / 바뀐 값 / 영향 분석 / 근거를 쓰고 사용자 확인을 받는다. 결정은 둘 중 하나다.
   - 당사 값 유지: 반영 뒤 되돌리고, Harmonize 를 다시 돌리면 또 바뀐다는 것을 판정표·Redmine 에 적는다.
   - HAE 값 채택: 보호 설정 표에서 그 행을 고치거나 지우고, 이유를 적는다.
2. **이유를 모르는 당사 값도 보호 대상이다.** "이유 미상"으로 표에 두고, 바꿀지는 사용자가 정한다. 모른다고 HAE 값으로 맞추지 않는다.
3. **VC·Harmonize 결과와 맞추자는 제안은 보호 설정 표와 먼저 대조한다.** 겹치면 "VC 와 다름 = 당사 의도일 수 있음"으로 표시하고 1 을 따른다.
4. **(d) 는 설정이 아니라 생성 코드로 확인한다.** 빌드 결과 검수의 Generated diff 에서 그 파라미터가 쓰이는 값(예: `PaddingValue 255u → 0u`)을 찾아 판정표 행과 잇는다.
5. 새로 확정한 보호 설정은 작업이 끝날 때 프로필 표에 추가한다.

## 5. 시점별로 하는 일

일감의 단계 번호와 따로, 아래 **시점**마다 한다.

| 시점 | 할 일 |
|---|---|
| 프로필 확보 | '보호 설정' 표가 있는지 본다. 없으면 판정 단계에서 채울 항목으로 표시 |
| 판정 | `three_way.py` 결과의 "충돌"과 VC/Cur 대비 당사 고유값을 보호 설정 표와 대조. 판정표의 해당 행에 "보호" 표시 |
| 적용·Harmonize 직후 | `protected_check.py --profile … --root <앱> --part FBL|APP --before-rev HEAD` — 커밋 전 작업 폴더를 HEAD 와 비교한다. Harmonize 를 썼으면 6장 절차를 함께 한다 |
| 정적 검수 | 위 명령을 다시 돌려 확인 필요 0건이거나, 남은 항목이 모두 판정표 사유와 1:1 인지 본다 |
| 빌드 결과 검수 | 생성 커밋에서 (b)·(d) 에 해당하는 생성 코드 변화를 찾아 설명한다. 설정을 바꾸지 않았는데 생성 코드가 바뀌었으면 기본값 변화(모듈 버전업)를 의심한다 |
| 기록 | 결과 코멘트의 "적용 제외·당사 값 유지" 절에 (b)·(d) 결정을 적는다 |

## 6. Harmonize 를 돌릴 때

1. **시험 브랜치에서 먼저 돌린다**(`test/harmonize_<대상>_<날짜>`, 로컬 전용, push 금지). push 하면 Jenkins 가 빌드하고 자동 커밋한다.
2. **모듈은 꼭 필요한 것만 고른다.** 이 C Studio 버전은 기본 선택이 없다. "Check prerequisite modules automatically"·"Check previous selection" 은 범위를 넓히므로 끈다. 위쪽 "may be selected for prerequisite: EcuC" 는 안내일 뿐이다.
3. 옵션 화면을 캡처해 판정표에 남긴다. 기본값:

   | 옵션 | 기본 | 영향 |
   |---|---|---|
   | Auto-Regeneration of Handle Id | 켬 | PDU Handle ID 재배정 → (c) |
   | Remove Invalid Configurations | 켬 | DB·EcuExtract 와 안 맞는 컨테이너 삭제 → (b) 후보 |
   | Overwrite User-Configured Parameters and References | 켬 | **당사 수동 값 덮어씀** → (b) |
   | Create Json For CLI | 끔 | — |
   | Can: Enable Basic TX CAN greater than | 32 | 송신 메시지 수 기준 BASIC 전환 |
   | CanIf: split routing tx … same Basic CAN | 끔 | — |

   Overwrite 를 끄면 덮어쓰기는 줄지만 HAE 가 의도한 변경도 빠질 수 있다. 미리 보기는 기본값으로 돌려 전체 영향을 보고, 실제 반영 방식은 그 결과를 보고 정한다.
4. CLI 로 돌리면 같은 옵션을 **파일에 명시**할 수 있다 — 화면 캡처 대신 입력 파일이 기록이 된다. `-harmonize <json>` 의 `ecucGenOptions` 키가 위 GUI 옵션과 1:1 이다.

   | GUI 옵션 | JSON 키 |
   |---|---|
   | Auto-Regeneration of Handle Id | `autoRegenerationOfHandleId` |
   | Remove Invalid Configurations | `removeUnnecessaryContainers` |
   | Overwrite User-Configured Parameters and References | `overwriteUserConfiguredParametersAndReferences` |
   | Can: Enable Basic TX CAN greater than | `canEnableBasicTxCanGreaterThan` |
   | BswM: App Mode in ECU State | `bswmAppModeInECUState` |

   배포본 patch_tool 의 `PREHarmonize.json`·`GENHarmonize.json` 이 이 입력 파일이다 — HAE 가 어떤 옵션으로 돌렸는지 그 파일로 알 수 있다. 실행 방법·전제는 `apply.md` §1·§5.
5. **변경점 전수 대조는 ECUC Compare 가 정본이다**(C Studio 내장, HAE 공식 하모나이즈 후 검토 절차). 절차: 대상 Ecud 파일을 백업 → 그 파일을 지우고 다시 Harmonize 해서 **순수 Harmonize 결과**를 따로 만든다 → 백업을 원복 → 두 파일을 ECUC Compare 로 비교 → 임시 파일 삭제.
6. 끝나면 바로 `Automation-Results/Automation_<시각>.xls`(git 무시)와 `.log/ODX_<시각>` 을 작업 폴더 밖에 보관하고 읽는다. "value Change from A to B", "Removed Container", "Created Container" 줄이 덮어쓰기 목록이다.
7. `git status`·`git diff --stat`, 의미 비교, `protected_check.py --before-rev HEAD` 로 (a)~(d) 를 나눈다. `.settings/com.autron.odin.auto.config.prefs` 에 선택 모듈·옵션이 기록된다(이전에 누가 무엇을 Harmonize 했는지도 보인다).
8. 채택할 변경만 작업 브랜치에 항목 단위로 옮긴다(decision-rules: Harmonize 부산물 이식 금지). 시험 브랜치는 C Studio 를 **완전히 닫은 뒤** 되돌리고 지운다 — 열린 채로 되돌리면 메모리의 결과를 다시 저장할 수 있다. 다시 열면 F5, 저장 묻으면 "No".

### HAE 권고와 충돌하는 지점

HAE 는 "하모나이즈로 생성된 설정은 임의로 바꾸지 말 것"을 권고한다(BswM 등). 당사는 보호 설정이 덮인 경우 되돌린다 — 방향이 반대다. 그래서 되돌릴 때는 다음을 함께 남긴다.

- 되돌린 값, 사유(그 값이 왜 당사에 필요한지), 사용자 확인 날짜
- **다시 Harmonize 하면 같은 값이 또 덮인다**는 사실 한 줄
- 같은 되돌림이 회차마다 반복되면 그 항목은 C 경로로 "이 값을 유지해도 되는지" HAE 에 확인해 근거를 받아 둔다 — 반복 되돌림은 언젠가 빠진다

## 6-1. ADMIN-DATA 장부를 읽으면 "언제 덮일지" 를 미리 안다

ECUC arxml 은 파라미터마다 **유효값과 별도로 세 가지 장부**를 ADMIN-DATA 의 `SDG` 에 남긴다. 이것을 읽으면 Harmonize 를 돌리기 **전에** 어느 보호 설정이 위험한지 알 수 있다.

| SDG GID | 뜻 |
|---|---|
| `ODIN_WRITER_TYPE:USER_CONFIGURED` | **사람이 넣은 값**과 넣은 날짜 |
| `ODIN_AUTO_CONFIG_PROPERTY` | `true` 면 그 파라미터가 **자동구성 대상** |
| `ODIN_WRITER_TYPE:AUTO_CONFIGURED` | **도구가 넣으려는 값**과 그 날짜 |

**유효값은 이 셋이 아니라** `<DEFINITION-REF …/><VALUE>` 쌍이다. 장부만 보고 값을 말하면 틀린다.

실측 — `#49951` APP `Configuration/Ecu/Ecud_Dcm.arxml` 9005~9065행:

```xml
<SDG GID="ODIN_WRITER_TYPE:USER_CONFIGURED">
  <SD T="2024-09-03T16:07:43Z" GID="DcmTaskTime">0.01</SD>      <- 사람이 2024-09-03 에 넣음
<SDG GID="ODIN_AUTO_CONFIG_PROPERTY">
  <SD GID="DcmTaskTime">true</SD>                               <- 자동구성 대상
<SDG GID="ODIN_WRITER_TYPE:AUTO_CONFIGURED">
  <SD T="2026-02-05T15:56:47Z" GID="DcmTaskTime">0.005</SD>     <- 도구가 넣으려는 값
...
  <DEFINITION-REF DEST="ECUC-FLOAT-PARAM-DEF">/AUTRON/Dcm/DcmGeneral/DcmTaskTime</DEFINITION-REF>
  <VALUE>0.01</VALUE>                                           <- 유효값
```

읽히는 것: **HAE 가 권고하는 `0.005`(IA-059)가 2026-02-05 부터 이미 장부에 들어와 있고**, 당사 `0.01` 이 `USER_CONFIGURED` 로 그것을 누르고 있다. `AUTO_CONFIG_PROPERTY` 가 `true` 이므로

> ⚠ **Dcm 을 Harmonize 대상에 넣고 `overwriteUserConfiguredParametersAndReferences` 가 켜져 있으면 `0.01` 이 `0.005` 로 덮인다.**

이번 회차에 살아남은 이유는 **Dcm 이 harmonize 대상이 아니었기** 때문이다(안내 §4 = `Rte, EcuM`). 운이 아니라 대상 목록 덕이다 — 그러나 다음 회차에 Dcm 이 대상에 들어오면 그대로 덮인다. **보호 설정 중 `AUTO_CONFIG_PROPERTY=true` 이고 `AUTO_CONFIGURED` 값이 당사 값과 다른 것은 "지금 안전" 이 아니라 "대상에 들어오면 즉시 위험" 으로 분류한다.**

⚠ **`scripts/protected_check.py` 의 한계(2026-11-10 확인).** 이 스크립트는 `#49951` 프로필의 보호 설정 3건을 모두 `키 없음(컨테이너 이름 변경·삭제 의심)` 으로 낸다 — 오탐이다. `DcmTaskTime` 은 `SD GID=` 안에 있고, `tool_info` 는 arxml 이 아닌 JSON 이며, `BswInstance_Crypto` 행은 키가 아니라 "개명하지 않는다" 라는 지시문이다. **스크립트 결과만으로 보호 설정을 판정하지 말고 위 구조로 직접 확인한다.**

## 6-2. 보호 설정 표를 쓰는 규칙 — `protected_check.py` 가 읽는 형식

표를 잘못 쓰면 **오류가 아니라 침묵**으로 나타난다. 조용히 검사에서 빠지거나, `키 없음(컨테이너 이름 변경·삭제 의심)` 이라는 **엉뚱한 경고**가 harmonize 직후에 뜬다. 2026-11-10 에 `tpms_rf_receiver.md` 가 네 가지를 동시에 틀렸다.

| 칸 | 규칙 | 틀리면 |
|---|---|---|
| 키 | `컨테이너 SHORT-NAME 경로#파라미터 정의명` (`three_way.py` `parse()` 형식, 예 `/Dcm/DcmGeneral#DcmTaskTime`) | 사람이 읽는 이름(`DcmTaskTime`)은 `키 없음` — 컨테이너가 사라진 것처럼 보인다 |
| 당사 값 | **값만.** 백틱은 벗겨지지만 `**` 와 괄호 설명은 남는다 | `**0.01** (IA-059 권고는 0.005)` → 실제 `0.01` 과 문자열이 달라 `바뀜` |
| 구분 | `APP` · `FBL` · `공통` 중 하나와 **정확히 일치** | `APP·FBL` 은 `--part APP` 에도 `--part FBL` 에도 걸리지 않아 **조용히 빠진다** |
| 파일 | 실제 경로 | MCAL 모듈은 `Configuration/Ecu/Mcal/` 아래다. `Configuration/Ecu/Ecud_Can.arxml` 로 적으면 안 된다 |

⭐ **절 안에 다른 표를 두지 않는다.** 파서는 `## 보호 설정…` 절에서 **처음 만난 표의 머리글**을 헤더로 삼고, `###` 소제목으로는 초기화하지 않는다(`read_rules()`). 설명용 표를 앞에 두면 `키` 칸이 사라져 **그 절의 모든 행이 무효가 된다.** 설명은 글머리표로 쓰고, 성격이 다른 항목은 **"보호 설정" 으로 시작하지 않는 별도 `##` 절**에 둔다.

**스크립트가 원리적으로 못 보는 것** — `.arxml` 의 ECUC 파라미터만 비교한다(`if not n.endswith(".arxml"): continue`). 아래는 표에 넣지 말고 별도 절에 "사람이 확인" 으로 둔다.

- JSON·텍스트 설정 (`Static_Code/modulesVersion.json` 의 `tool_info`)
- 폴더·모듈 버전 (MCAL `S32K3xx_RTD_4.0.0_P24`)
- 값이 아닌 **지시문** (`BswInstance_Crypto` 를 개명하지 않는다 — 확인은 `grep -c "SHORT-NAME>…<"`)
- 도구 상태 파일 (`.settings/com.autron.odin.auto.config.prefs`)

**키는 추측하지 말고 뽑는다.**

```
python -c "import sys;sys.path.insert(0,r'<스킬>/scripts');from three_way import parse;
           [print(k,'=',v) for k,v in parse('<파일>.arxml').items() if '<파라미터>' in k]"
```

쓴 뒤에는 **반드시 돌려서 `✅ 유지` 가 뜨는지 본다.** 행을 추가하고 돌리지 않으면 그 행이 읽히는지조차 모른다.

## 7. 기록 형식

판정표는 데이터이고 표는 생성물이다 — 형식은 `three-way-merge.md` §6 하나뿐이니 여기에 사본을 두지 않는다. 보호 설정 행은 판정표 데이터에 이렇게 들어간다(사람이 채우는 칸만 적었다).

```json
{"id": "R042", "file": "Configuration/Ecu/Ecud_CanIf.arxml",
 "key": "/CanIf/CanIfPrivateCfg#CanIfMetaDataSupport",
 "path": "B", "action": "보호 — 당사 값 유지 (되돌림)",
 "basis": "#38061 부터 1, HAE 배포본·VC 는 0 (3.0.18·3.0.19 동일). 쓰는 PDU 0건 — CanIf_Cfg.c 전부 INVALID_METADATA_TYPE. 사용자 확인 2026-10-11"}
```

`verdict`·`ours`(= 당사 현재값)는 생성되므로 적지 않는다. **보호 설정은 거의 항상 B 다** — 왜 당사 값이 그렇게 되었는지의 출처가 근거이고, `basis_auto`(현재값)로는 닫히지 않는다.

Redmine "적용 제외·당사 값 유지" 절에는 위 행을 그대로 옮기고, Harmonize 를 다시 돌리면 같은 값이 덮어써진다는 것을 한 줄 적는다.
