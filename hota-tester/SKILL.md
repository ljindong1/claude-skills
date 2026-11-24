---
name: hota-tester
description: H-OTA Tester(GIT, 웹 UI localhost:7048 + 서버 7047 + Monitor.CommandConsole)로 리프로그래밍 평가를 돌리기 위한 **시험 케이스(TC)를 만들고 유지하는** 스킬. 실행은 회사 저장소 Joule(D:\Mobase\asec_autotest_tool)의 joule-hota tester-project · tester-tc · run 을 그 자리에서 부른다 - 롬패키지로 프로젝트 만들기, 공식 TC(TC_TAR_*) 복사해 당사 TC(TC_MB_*) 만들기, 훅 끄고 기대값 블록에 박기, bin·OEUK 개발키·STmin 바꿔 끼우기, 프로젝트 TC 차례 맞추기, 여러 TC 를 한 번 실행으로 묶어 리포트 하나로 받기, 보드 상태 사슬(싱글 메모리는 차단 뒤 APP 가 지워진다) 잡기, Vector 채널 배정 확인. 사용자가 "Tester TC 만들어줘", "HOTA Tester 로 리프로그래밍", "Tester 케이스 추가", "TC 이름 바꿔줘", "한 번에 다 돌리게 해줘", "리포트 하나로", "묶어서 돌려줘", "TC_MB 만들어줘", "공식 TC 복사", "OEUK 개발키 TC", "다운그레이드 차단 TC", "Tester 프로젝트 만들어줘", "tester-tc", "tester-project", "Tester 가 TC 를 다 SKIP 해", "PASSED 인데 아무것도 안 돌았어", "버전 칸 때문에 로그인이 필요해", "Tester 리포트가 여러 개로 쌓여" 등을 말하거나 H-OTA Tester 로 평가를 자동화하려는 의도를 보이면 반드시 이 스킬을 사용하라. Claude Code CLI(H-OTA Tester·Studio·CVD·VN1640A·릴레이 박스가 있는 사용자 PC, 관리자 PowerShell) 전용. 공식 Updater·Studio 로 하는 A·B 그룹 평가 진행은 hota 스킬, 보드 쓰기는 cvd-project 담당이다.
---

# hota-tester - H-OTA Tester 시험 케이스 만들기

Tester 로 평가를 돌리는 일에서 손이 많이 가는 쪽은 실행이 아니라 **TC 를 만들고 차례를 잡는 것**이다
(2026-11-12 사용자 요청으로 이 스킬을 만들었다). 실행 도구는 Joule 이고, 이 스킬은 **무엇을 어떤 순서로 만들고
무엇을 확인받는지**만 다룬다.

## 도구

- 저장소 `D:\Mobase\asec_autotest_tool` (Joule). 그 폴더에서 `uv run <명령>`. 저장소가 없으면 멈추고 알린다.
- 정본 문서 둘을 **먼저 읽는다**:
  - **`docs/joule-hota.md`** - Tester 조작·계획 형식·함정 ("Tester" 메모, "싱글 메모리 제어기의 Tester").
  - **`docs/joule-reprog.md` 의 "OTA 세대 x 메모리 종류"** - **TC 를 어떻게 짜야 하는지가 거기서 나온다.**
    세대(1세대 `ES98765_01` / 2세대 `_02`)가 UDS 루틴 집합을, 메모리 종류(`FOTA_MMU_TYPE` 듀얼 /
    `FOTA_SINGLE_TYPE` 싱글)가 무선 흐름 유무·차단 뒤 보드 상태·앱 OEUK 보안 레벨을 가른다.
    새 제어기를 받으면 그 표에서 **세대·메모리 종류를 먼저 확정**하고 TC 를 짠다 (`Ecud_Fota.arxml` 의
    ECUC `<VALUE>`. `ADMIN-DATA` 의 `SD` 에는 낡은 값이 남아 있다).
  매뉴얼은 Tester kor 판(10.3.1 CLI, 9.5.2 OEUK, 11.4 리포트).
- **고치는 것은 계획 파일 `configs/hota/<제어기>.toml` 과 제어기 `configs/ecus/<제어기>.toml` 의 `[hota.tester]` 뿐이다.**
  코드(`src/`)가 막히면 그 자리에서 멈추고 요청 문구(현상 · 근거 파일:행 · 원인 · 요청 · 테스트)로 사용자에게 넘긴다.

| 명령 | 하는 일 |
|---|---|
| `uv run joule-hota <bench> check` | 서버·포트 15554·관리자·프로젝트 Vehicle Type·**Vector 채널 배정**까지 미리 본다 |
| `uv run joule-hota <bench> tester-project --name <이름> --package <빌드폴더> --tc TC_TAR_...` | 롬패키지를 올려 공식 TC 로 프로젝트를 만든다 (보드 아님) |
| `uv run joule-hota <bench> tester-tc [이름..] [--replace]` | 계획 `[[tester_tc]]` 의 당사 TC 를 만들고 base 와 대조, 끝에 **TC 차례를 계획 차례로** 맞춘다 (보드 아님) |
| `uv run joule-hota <bench> run [케이스..]` | 케이스 실행 (**보드**). 묶음 케이스면 Tester 를 한 번만 부르고 리포트도 하나다 |

## 흐름

```
T0 확인      check  (서버 응답 · 15554 비어 있음 · 관리자 · 채널 배정 = bench 진단 버스)
T1 프로젝트  롬패키지(= joule-hota build 결과 rompackage\<빌드폴더>)로 tester-project
             -> 결과가 알려 주는 config_dir 을 제어기 [hota.tester] 에 적는다 (login_id 도)
T2 조사      프로젝트의 공식 TC 블록 이름과 VersionCheck 안 rx 기대값을 본다 (아래 "조사")
T3 계획      [[tester_tc]] 로 당사 TC 를, [[case]] 로 묶음 케이스를 적는다 (아래 "짓는 법")
T4 만들기    tester-tc --replace  -> 전부 [통과] + "TC 차례:" 줄이 평가 차례와 같은지 본다
T5 보드      시작 버전을 맞춘다 (joule-reprog --wired --package <zip>, 내림은 --oeuk)
T6 실행      사용자 확인 뒤 run  -> 리포트 1개 PASS n / FAIL 0 을 확인하고 결과를 전한다
```

**프로젝트가 이미 있어도 T1 을 건너뛰기 전에 셋을 본다** (2026-11-23 에 이것으로 세 번 헛걸음했다 -
전에 이 자리에 "웹 화면에서 만들어 둔 것도 그대로 쓴다" 고 적어 두었는데 **그것이 틀렸다**):

| 보는 것 | 안 되면 | 까닭 |
|---|---|---|
| `Testcases\<id>\*.xml` 의 노드 `id` 가 비었나 | `Exec/Total 0/0` 인데 **PASSED 로 보인다** | `schemaVersion 1.0.0.010` 프로젝트는 UDS 노드 `id` 가 전부 `""` 고 서버가 조용히 건너뛴다. 1.0.0.015 이상으로 **다시 만들어야 한다**. 틀(`root`·`test-rule`·`rule`·`test`)의 빈 `id` 는 정상이라 **개수로 가린다** - 도는 프로젝트가 32개(`test` 태그), 못 도는 것이 674개였다 |
| `requestDownload` 가 몇 구간인가 | `34` 에서 깨진다 | **웹 화면에서 만든 프로젝트는 주소·크기 0 인 빈 틀 1구간**이다. `tester-project`(= 웹의 "자동 생성(Test Case)") 만 실제 구간을 채운다 |
| `transferData` 에 `localSTMinTx` 속성이 있나 | 전송이 10배 느리다 | 1세대 프로젝트는 그 속성이 **아예 없고** Tester 가 10ms 로 보낸다 |

`tester-tc` 가 끝에 TC 마다 "블록 n, 다운로드 n구간" 을 찍으므로 둘째는 그 줄로 본다.
제어기 `[hota.tester]` 의 `config_dir` 이 쓸 프로젝트를 가리키는지도 본다.
회차 롬패키지는 그때도 새로 만든다 - **TC 의 bin 은 프로젝트를 만든 롬패키지가 아니라 `[[package]]` 가 정한다.**

## 짓는 법 (이 셋이 핵심이다)

### 1. 평가하는 TC 는 **모두 당사 복사본**이다

공식 TC(`TC_TAR_*`)를 직접 돌리지 않는다. 까닭 둘:

1. **한 번 실행에 같은 TC 를 두 번 넣을 수 없다.** A1(올림)과 B1(OEUK 회차 앞 올림)은 같은 공식 TC 이므로
   이름이 다른 복사본 두 개여야 한다.
2. **훅(VersionCheck)을 끄려면 복사본이어야 한다.** 훅은 실행할 때 서버가 *프로젝트 버전 칸*을 읽어 기대값을 채우고,
   그 칸을 바꾸는 API 가 로그인 토큰을 쓴다. 방향이 다른 TC 를 묶으려면 훅을 끄고 기대값을 블록에 박아야 한다.

이름은 **하는 일**에 맞춘다 (`TC_MB_<케이스>_<하는 일>_<경로>`). **경로 이름은 세대마다 다르다** -
2세대는 유선/무선(`_WIRED`·`_WIRELESS`), 1세대는 External / BG -> Repro(`_EXTERNAL`·`_BGREPRO`).
**바탕 TC 번호도 세대마다 다르다** - 아래 "세대별로 갈리는 것" 표를 보고 적는다. 2세대 예:

| 케이스 | 당사 TC 이름 | 바탕(유선) |
|---|---|---|
| A1 올림 | `TC_MB_A1_UPGRADE_WIRED` | `TC_TAR_03010` |
| A2 내림 차단 | `TC_MB_A2_DGPREVENT_WIRED` | `TC_TAR_03030` |
| B1 올림 (OEUK 회차 앞) | `TC_MB_B1_UPGRADE_WIRED` | `TC_TAR_03010` |
| B2 OEUK 강제 내림 | `TC_MB_B2_DG_OEUK_WIRED` | `TC_TAR_03010` + OEUK dev |

무선을 평가하면 A3·A4·B3·B4 가 같은 모양으로 붙는다 (바탕 `TC_TAR_01021` 등, `keep` 으로 IGOff 를 뺀다).
크게 보면 **유선만 평가하는 제어기는 네 개면 된다** (A1·A2·B1·B2 - 공식 8케이스에서 무선을 뺀 것).

### 2. 훅을 끄고 기대값을 블록에 박는다

```toml
[[tester_tc]]
name = "TC_MB_A1_UPGRADE_WIRED"
base = "TC_TAR_03010"
bin  = "<롬패키지 폴더 이름>"      # 결과 폴더 rompackage\<그 이름>\ 의 RomData01.bin
description = "A1 유선 올림 {low} -> {high}. TC_TAR_03010 복사"
hooks = false                       # 훅 끔 - 버전 칸(로그인 토큰) 의존이 사라진다
```

기대값을 박는 길이 둘이고 **base 에 `VersionCheck` 블록이 있는지로 갈린다**:

- **있으면** `set` 으로 그 블록의 rx 노드를 고친다.
  **rx 번호(`index`)는 블록 XML 을 열어 센다 - 다른 제어기·다른 세대에서 베끼지 않는다.**
  `index` 는 "그 블록 안에서 그 이름의 몇 번째 노드인가" 라서 블록이 조금만 달라도 자리가 밀린다
  (2세대 `VersionCheck` 는 rx 둘(1 F187 · 2 F1B1)인데 1세대는 **rx[1] 하나(F1B1)** 다. 2026-11-21 HE1i).
  롬패키지로 자동 생성한 TC 는 기대값이 이미 박혀 있을 수 있다 (그러면 올림 TC 는 손댈 것이 없고 내림만 바꾼다).
- **없으면** `version_check = { part = "...", sw = "..." }` 로 두 노드짜리 블록을 새로 만들어 붙인다.
  `ensure_block` 은 같은 이름이 있으면 **넣지 않는다** - 블록이 이미 있는데 이것을 쓰면 조용히 아무 일도 안 한다.
- **차단 케이스에 버전 확인을 두는지는 메모리 종류가 정한다.**
  **싱글**은 두지 않는다 - 차단되면 ECU 가 받은 이미지를 지워 FBL 에 남고 `22` 가 NRC 0x11 이다.
  **듀얼뱅크**는 둔다 - APP 가 남아 읽히고, 그 값이 상위 그대로인 것이 "차단됐다" 의 증거다
  (HE1i A2 는 504 에 `VersionCheck` 가 없어 `version_check` 로 붙였다).

### 3. 한 케이스에 TC 를 모두 넣는다 (리포트 하나)

```toml
[[case]]
id = "T_ALL"
title = "Tester 유선 4케이스를 한 번 실행으로 (A1·A2·B1·B2)"
  [[case.step]]
  action = "tester"
  testcases = ["TC_MB_A1_UPGRADE_WIRED", "TC_MB_A2_DGPREVENT_WIRED",
               "TC_MB_B1_UPGRADE_WIRED", "TC_MB_B2_DG_OEUK_WIRED"]
  timeout_s = 3600          # 기본 30분으로는 모자랄 수 있다 (NQ6e 8케이스가 30분에 걸려 끊겼다)
  log_save_mode = "always"
  expect = "pass"
  [[case.step]]
  action = "wait"
  seconds = 5               # post 블록 바로 뒤 읽기는 못 믿는다 (아래 함정)
  [[case.step]]
  action = "read_version"
  expect = ".*<상위/하위 버전>.*"
```

- **`source_version`/`target_version` 을 쓰지 않는다** - 그것이 버전 칸을 바꾸는 API(로그인 토큰)를 부른다.
  훅을 끄고 기대값을 박았으면 필요 없고, 안 쓰면 **오프라인에서도 돈다**.
- 낱개로 보고 싶은 케이스는 `enabled = false` 로 남겨 둔다 (`run T_A1` 처럼 이름을 줄 때만 돈다).
  기본 실행(`run`)은 묶음 하나여야 한다.
- **실행 차례는 고른 차례가 아니라 프로젝트에 적힌 차례**다. `tester-tc` 가 끝에 계획 `[[tester_tc]]` 차례로
  맞추고 그 줄을 찍는다 - 그 줄이 평가 차례와 같은지 꼭 본다.

## 세대별로 갈리는 것 (번호·이름을 베끼지 않는다)

**세대가 TC 번호 체계와 블록 이름을 가른다.** 메모리 종류와는 다른 축이다 (그쪽은 아래 "보드 상태 사슬").
2026-11-21 에 1세대(HE1i PSU)를 하면서 드러난 자리다 - 2세대 번호로 적으면 `tester-tc` 가 base 를 못 찾는다.

| | 2세대 (`ES98765_02`) | 1세대 (`ES98765_01`) |
|---|---|---|
| 공식 TC 번호 | **5자리** (`TC_TAR_03010`·`01021`·`01053`) | **3자리** (`TC_TAR_501`·`504`·`201`·`207`) |
| 평가 축 | 유선 / 무선 | External / BG -> Repro |
| 유선(External) 성공 | `03010` | `501` pre > `Reprogram_normal` > post > `VersionCheck` |
| 유선 내림 차단 | `03030` | `504` pre > `Reprogram_normal_downgrade` > post (**`VersionCheck` 없음**) |
| 무선(BG -> Repro) 성공 | `01021` | `201` Background > IGOff > `PreCondition_alive` > `Reprogram_background_mmu` > post |
| BG 쪽 OEUK 강제 내림 | **공식 TC 없음** (올림 틀 + 하위 bin + OEUK dev 로 만든다) | **`207` 이 있다** (보안 노드가 이미 `oeuk`/`dev`) |
| UDS 루틴 | `FF00` 지우기 / `0200` 검사 / `FF01` 활성화 | `0210` > `0212` 지우기 > 전송 > `FF01` 의존성 확인 > `0213` 활성화 |

- **BG 쪽 내림 차단(A4)은 양쪽 다 바탕이 없다** - 올림 TC(`201`·`01021`)를 복사해 활성화 응답 기대를
  `0x7F31F4` 로 바꾼다 (`set` 에 `pos = "0"`, `length = "3"`). 1세대에서 `207` 을 쓰지 않는 까닭은
  그 TC 의 보안 노드가 `oeuk`/`dev` 라서다 (그건 B4 몫이다).
- **세대·메모리 종류를 `Ecud_Fota.arxml` 로 먼저 확정한다** (위 "도구" 절). 번호를 보고 거꾸로 짐작하지 않는다.

## 보드 상태 사슬 (메모리 종류로 갈린다)

케이스마다 시작 버전이 다르다. 묶음이 되려면 앞 케이스의 끝이 다음 케이스의 시작이어야 한다.
**왜 갈리는지는 `docs/joule-reprog.md` 의 "OTA 세대 x 메모리 종류" 가 정본이다** - 여기 적는 것은 그 결과다.

- **싱글 메모리** (예: TPMS RF 수신기 LT2, S32K312): 내림이 차단되면 ECU 가 받은 이미지를 스스로 지워
  **APP 가 사라지고 FBL 에 남는다** (정상 거동). 그래서 `A1 -> A2 -> B1 -> B2` 가 저절로 이어진다 -
  A2 가 지운 APP 를 B1 이 처음부터 다시 받는다. **보드 쓰기(flash)가 끼지 않는다.**
- **듀얼 뱅크** (예: NQ6e PSU/APSU, CYT2BL): 차단돼도 APP 가 남으므로 다음 케이스 앞에서 버전을 내려야 한다.
  TC 끝에 `flash_wait = "<버전>"` (대기 블록 `WaitForFlash__<버전>`)을 두고 단계에 `flash_on_wait = true` 를 주면
  Tester 가 멈춘 동안 joule 이 보드에 쓴다. 대기(최대 180초) > 쓰기 시간이어야 한다.
- 어느 쪽이든 **첫 케이스의 시작 버전은 사람이 맞춘다** (`joule-reprog --wired --package <zip>`, 내림은 `--oeuk`).

## 조사 (프로젝트를 받으면 먼저 본다)

메모리 종류에 따라 **TC 분류 키와 블록 이름이 다르다.** 짐작하지 말고 확인한다.

| 롬패키지 | `parsedMeta.redundancy` | 분류 키 | 활성화·롤백 블록 |
|---|---|---|---|
| 듀얼 | `background` | `mmu` / `nonMmu` | `Activate_Background_MemorySwap` · `Rollback` |
| 싱글 | `basic` | `testcaseGroups` | `Activate_basic` · `Rollback_basic_nonoeuk`, 내림 차단은 `CPD_downgrade` |

- 위 표의 블록 이름은 **2세대 것이다** - 1세대는 `Reprogram_normal`·`Reprogram_background_mmu(_downgrade)`·
  `procedure_pre/post_ES9876501` 이다 (위 "세대별로 갈리는 것").
- 블록 이름과 rx 기대값은 REST 로 읽는다 (`/testcase/<cfg>/list` -> `/testcase/<cfg>/<id>` ->
  `/ruledatabase/<cfg>/<tc>/<block>`). 노드 태그는 `<xfrm:rx ...>` 다 (`rx` 로 찾으면 안 걸린다).
  **`<cfg>` 는 폴더 이름이 아니라 `project.json` 의 `id`(GUID)** 다 - 폴더 이름을 주면 "not valid" 다.
- **REST 조회는 로그인 토큰을 요구한다** (토큰 없이 부르면 400·406). 토큰이 없으면 **프로젝트 폴더를
  직접 읽는다** - `Configuration\<로그인ID>\<config_dir>\Testcases\<id>\TC_*.json` 이 블록 차례를,
  같은 폴더의 `<블록 uuid>.xml` 이 노드와 기대값을 가진다. `CLI\cli_config.json` 의 `testcases` 가
  실행 차례다. **만든 뒤 확인도 이 파일들로 한다** (bin 경로·`enable`·`hooks[].enable`·차례를 한 번에 본다).
- 싱글에는 Background Transfer 분류가 없다 (돌고 있는 APP 자리밖에 없어 받아 둘 곳이 없다).
  그래서 무선 TC 도 유선과 프레임 순서가 같다 - 무선을 따로 평가할 이유가 적다.
- `Rollback_basic_nonoeuk` 안에는 이미 `securityAccess type="oeuk" option="dev"` 가 들어 있을 수 있다.
- **`VersionCheck` 블록이 둘인 공식 TC 는 `keep` 의 바탕으로 쓸 수 없다** (블록을 이름으로 찾아 하나로 뭉갠다).
  그런 TC(예: 롤백 `TC_TAR_01045`) 대신 올림 틀 + 하위 bin + OEUK dev 로 만든다.

## 규칙

1. **보드에 보내는 실행은 매번 사용자 확인 뒤.** `tester-project`·`tester-tc` 는 보드를 건드리지 않으니 그냥 한다
   (`--yes`). `run` 은 보드에 쓴다 - 무엇을 어느 버전으로 보내고 끝에 보드가 어떤 상태로 남는지 먼저 말하고 확인받는다.
2. **공식 TC(`TC_TAR_*`)는 고치지 않는다.** 복사해서 복사본만 고친다.
3. **채널 배정을 먼저 본다.** Studio·Updater·Tester 는 채널을 인자로 받지 않고
   `HKLM\SOFTWARE\Vector\CANDriver 1.0\Software\H-OTA Studio0` 의 `hwChannel`(= 장비 CH - 1)을 쓴다.
   bench 채널을 옮기면 같이 옮겨야 한다 - `check` 가 대조해 `reg add` 한 줄까지 알려 준다.
   **읽기만 하고 고치지는 않는다** (PC 전체에 영향). 시험을 위해 바꿨으면 **끝나고 되돌린다**.
4. **복사 원본(`TC_TAR_*`)은 사용자가 웹 화면에서 지운다 - Claude 는 지우지 않는다** (2026-11-24 사용자 결정).
   지우는 때는 **당사 TC 를 다 만들고 `tester-tc` base 대조를 통과한 뒤**다.
   **`tester-project` 로 만든 프로젝트는 그 삭제가 막혀 있다** - 아래 "저장이 `0x10000001` 로 막힌다" 를
   먼저 푼다 (2026-11-24 HE1i. 넷을 그렇게 지웠다).
   **디스크가 정본이다** - `run` 과 `tester-tc` 가 읽는 것이 그것이고 화면은 증거가 아니다.
   그러니 **지운 뒤에는 파일로 센다**: `Testcases\<id>\TC_*.json` 과 `CLI\cli_config.json` 의 줄 수
   (`joule-hota projects` 가 "당사 n · 공식 m" 으로 찍어 준다).
   Claude 몫은 둘이다 - 지우기 전에 **`Testcases\<id>\` 백업**과 **"다시 만들 일이 남았는지"** 를 짚어 주는 것.
   까닭 셋: joule 에 그 명령이 없어(REST `DELETE /testcase/...` 는 로그인 토큰을 요구한다) 임시 스크립트를
   쓰게 되고 · 웹 화면은 `Testcases\` 와 `CLI\cli_config.json` 을 함께 정리하고 · **지운 뒤에는
   `tester-tc --replace` 가 base 를 못 찾아 당사 TC 를 다시 만들 수 없으므로** 그 시점 판단(bin 이 최종인가,
   서명본이 또 올 일정인가)이 사람 몫이다. 만들어 둔 TC 는 블록을 자기 안에 갖고 있어 **원본이 없어도 돈다**
   (회차에 끼지도 않는다 - 묶음이 부르는 것은 `TC_MB_*` 뿐이다). 되찍는 길은 웹 "자동 생성(Test Case)" 이고
   지웠으면 그 복구 절차를 계획 파일 주석에 남긴다.
5. 서버가 `0x10012703` 로 멈추면 네트워크 주소가 바뀐 것이다 - 옛 WebApi·mosquitto 를 끄고 서비스를 다시 시작하고
   REST(7047)가 열리기까지 30초쯤 기다린다.

## 함정 (모두 실기에서 당한 것)

| 증상 | 까닭·대처 |
|---|---|
| TC 가 블록을 모두 SKIP 하고 PASSED | 복사한 블록의 **노드 uuid 가 다른 TC 와 같다**. `tester-tc` 가 잡아 준다 - `--replace` 로 다시 만든다 |
| 같은 증상 | TC 나 블록의 `enable` 이 꺼져 있다 (`tester-tc` 가 알려 준다) |
| 넣은 블록이 사라진다 | `PUT /testcase` 는 `testBlocks` 를 통째로 덮어쓴다 - **훅을 먼저** 저장하고 블록을 나중에 넣는다 |
| 블록 XML 을 고쳤는데 그대로다 | `PUT /ruledatabase` 는 HTTP 200 을 주고도 파일을 바꾸지 않는다 - TC 를 다시 만들거나 `Testcases\<id>\*.xml` 을 고치고 **서버 재시작** |
| "있는 TC: 0개" | 싱글 메모리 분류 키(`testcaseGroups`)를 못 읽은 것. joule 은 둘 다 받는다 - 다른 키가 오면 멈춘다 |
| 리포트가 케이스마다 쌓인다 | 콘솔 실행 1회 = 리포트 1개다. 묶음 케이스로 바꾼다 |
| 두 번째 TC 가 `27` 에서 NRC 0x22 | 앞 TC 의 리셋 직후라 조건이 안 된다 - `wait_after_s = 30` 으로 `delay` 블록을 붙인다. **BG 올림 뒤가 그 자리다** (활성화가 뱅크를 바꾸면 ECU 가 스스로 재부팅한다). 유선은 `11 01` 뒤 post 가 기다려 주므로 필요 없다. 안 두면 전송이 **아예 없어** 활성화가 `7F 31 31`(스테이징된 것이 없다)로 와서 **뒤 TC 가 엉뚱한 까닭으로 떨어진다** (2026-11-24 HE1i A4·B4) |
| 무선 전송이 유선의 4배 느리다 | ECU 가 아니라 TC 설정이다 - `transferData localSTMinTx` 를 `0x00` 으로 (`index = 0` = 그 이름 노드 모두). **1세대 프로젝트는 그 속성이 아예 없다** (Tester 가 10ms 로 보낸다 - 블록당 696ms -> 35ms). **201·207 은 전송이 `Background` 블록에 있다** - 블록 이름을 틀리면 조용히 안 먹는다 |
| 내림 차단 TC 인데 활성화가 **성공**한다 | TC 가 아니라 차례다 - `tester-tc` 를 낱개로 돌리면 그 TC 가 **뒤에 붙어** 묶음의 보드 상태 사슬이 깨진다. 올린 것이 내림이 아니라 같은 버전이 된다 (2026-11-24 HE1i A2). **묶음 전에 이름 없이 `tester-tc --replace` 를 돌려 차례를 맞추고 `TC 차례:` 줄을 읽는다** |
| `31 01 02 13` 이 `7F 31 13 incorrectMessageLength` | `TC_TAR_207` 의 활성화 노드만 `routineControlOptionRecord=""` 다 (**벤더 공식 TC 쪽 결함** - 프로젝트의 TC 열둘 가운데 그 하나뿐이고 201·501·504 는 `0x00F1B1`). 복사본에서 `{ node = "routineControl", index = 1, routineControlOptionRecord = "0x00F1B1" }` 로 메운다. 같은 블록의 `0x0300`·`0x0211` 은 비어 있는 것이 정상이다 |
| `set` 으로 rx 아닌 것을 고치고 싶다 | 된다 - 고정 칸 셋(`block`·`node`·`index`) 밖의 키는 **그 태그의 속성**이 된다. `routineControl`·`securityAccess`·`transferData` 를 같은 길로 고친다 |
| 웹 화면 저장이 `0x10000001 ... (Source Version)` 으로 막힌다 | **`tester-project`(REST)로 만든 프로젝트는 `sourceVersion` 이 비어 있다** - 올린 펌웨어에서 `targetVersion` 만 채운다. 저장할 때 일반 설정 검사가 걸려 **저장이 통째로 거절되므로 TC 삭제도 설정 저장도 안 들어간다** (화면에서는 사라져 보였다가 새로 고치면 되살아난다. 그 칸을 채우는 저장도 같은 경로라 화면으로는 못 푼다). 푸는 법: `VehicleInfo\vehicleInfo.json` 의 `ecuInfo.versionInfo.versionScenarios.sourceVersion` 을 하위 버전으로 채우고(백업 먼저, BOM 없는 UTF-8 로 그 문자열만 치환) **WebApi 를 끈다** - 서비스가 1분쯤 뒤 다시 띄우며 디스크를 다시 읽는다. 웹 화면에서 만든 프로젝트에는 이 칸이 차 있어 이 일이 없다 (`web_config.json` 이 있는지로도 갈린다 - REST 로 만든 쪽에는 없다) |
| `-status` 가 `Running` 인데 시험이 도는지 모르겠다 | `-status` 는 **서버 프로세스만** 본다. 그리고 회차를 중간에 끊어 `-stop` 을 건너뛰면 서버가 "이미 테스트가 진행 중" 으로 거절하고 엔진이 `test/streamJson` 을 뿜으며 남는다 (`call TesterConsole stop` 이 200 을 줘도 MQTT 만 끊는다). 서비스 재시작으로만 되살아난다 - **그래서 도는 회차를 끊지 않는다** (백그라운드로 띄우고 기다린다) |
| 시간 초과 뒤 뒤 케이스가 `Tx transmission failed` | `-stop` 뒤 서버가 실제로 멈추기를 기다려야 한다 (joule 이 한다). `timeout_s` 를 넉넉히 |
| TEST 빌드 보드에서 공식 정보 TC 가 실패 | 공식 TC 는 일반 빌드 부품번호를 기대한다 (`expect=[...000] recv=[...TEST0]`) |
| 앱 OEUK TC(`TC_TAR_02060`)가 `7F 27 12` | 그 제어기는 OEUK(`27 13/14`)가 **FBL 에만** 있다 (앱 Dcm 보안 행이 L9 하나). **메모리 종류와 같이 가는 축이다** - 근거·범위는 `docs/joule-reprog.md` "OTA 세대 x 메모리 종류". 그 TC 를 쓰지 않고 강제 내림 TC(B2)로 본다 |
| post 블록 직후 `22 F1B1` 이 0 으로 온다 | 2026-11-12 TPMS 실기. **이것은 메모리 종류·세대와 무관하고 그 제어기의 응용 설계다** (LT2 는 한 이미지가 두 단계를 담아 SW 버전을 NvM 부품번호로 고른다 - 버전이 빌드 상수인 제어기에는 없는 일이다). 같은 실행에서 Tester 는 제대로 읽었고 전원 재투입 뒤에도 정상이다 - 방아쇠는 모른다. 읽기 앞에 `wait` 를 둔다 |
| 리포트 zip 받기만 실패 | 그것만 로그인 토큰이 필요한 REST 다. 평가 자체는 남은 세션으로 돈다 (`auto_login = false`) |
| `build` 가 시작도 못 하고 멈춘다 | 롬패키지 만들기(Studio `-Convert`/`-Rompackage`)는 **관리자 권한**이다. 관리자 터미널에서 다시 연다 |
| `bin` 으로 적은 폴더를 못 찾는다 | 롬패키지가 간 폴더 이름이 패키지 적는 법에 따라 다르다 - `variant` 는 **빌드 폴더**(`26810_test`), `source` 는 **패키지 이름**(`he1i_low@26810`). `rompackage\` 를 열어 보고 적는다 |
| 올리기는 됐는데 "롬패키지가 … 로 들어가지 않았습니다" | 서버가 펌웨어 이름 끝에 `__FW` 를 붙이기도 하고 안 붙이기도 한다 (1세대 HE1i 프로젝트는 안 붙였다). joule 이 2026-11-21 에 둘 다 받게 고쳤다 - 더 옛 joule 이면 그 자리다 |

## 실기 기준 (이 스킬을 만든 회차)

TPMS RF 수신기 LT2 (2세대 · 싱글 메모리), 2026-11-12:
`T_ALL` 한 케이스가 `A1 -> A2 -> B1 -> B2` 를 한 번 실행으로 돌아 **리포트 1개 PASS 4 / FAIL 0, 506초, 사람 손 없음**
(`runs/20261112_171144`). 보드 쓰기(flash)가 끼지 않았고 OEUK 는 개발키(`27 13/14` -> `67`)로 돌았다.

HE1i PSU 운전석 (1세대 · 듀얼뱅크), 2026-11-24:
`T_ALL` 한 케이스가 `flash 26810` 부터 `A1 -> A2 -> A3 -> A4 -> B1 -> B2 -> B3 -> B4` 까지 돌아
**리포트 1개 PASS 8 / FAIL 0, 1407초, 사람 손 없음** (`runs/20261124_114429`). 듀얼뱅크라 묶음 안에
보드 쓰기가 **세 자리** 낀다 (A2·A4·B2 끝의 `flash_wait` - `26810`·`26810_test`·`26810_test`).
OEUK 는 개발키(`27 13/14` -> `67`)로 돌았고 끝 버전은 `22 F1B1` = 26810 이다.

여기까지 오는 데 **막은 것이 여섯**이었고 모두 위 표에 한 줄씩 있다 - 프로젝트 쪽 셋(노드 `id` ·
다운로드 구간 · `localSTMinTx`)과 회차 쪽 셋(차례 · BG 뒤 대기 · `TC_TAR_207` 결함)이다.
**보드에 쓰는 것은 평문 빌드본이다** (서명본은 암호문이라 디버거로 쓰면 APP 가 부팅하지 않는다 -
`docs/joule-hota.md` "올리는 것은 서명본, 보드에 쓰는 것은 평문 빌드본").
계획은 joule `configs/hota/he1i_psu_drv.toml` 이고 자세한 것은 그 파일 주석과
`docs/joule-hota.md` 의 "1세대(CCU1) 제어기의 Tester" 절에 있다.
