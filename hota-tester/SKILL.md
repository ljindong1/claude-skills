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
- 정본 문서는 저장소 **`docs/joule-hota.md`** (특히 "Tester" 메모와 "싱글 메모리 제어기의 Tester").
  조작·함정 질문은 그 문서를 읽고 답한다. 매뉴얼은 Tester kor 판(10.3.1 CLI, 9.5.2 OEUK, 11.4 리포트).
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

## 짓는 법 (이 셋이 핵심이다)

### 1. 평가하는 TC 는 **모두 당사 복사본**이다

공식 TC(`TC_TAR_*`)를 직접 돌리지 않는다. 까닭 둘:

1. **한 번 실행에 같은 TC 를 두 번 넣을 수 없다.** A1(올림)과 B1(OEUK 회차 앞 올림)은 같은 공식 TC 이므로
   이름이 다른 복사본 두 개여야 한다.
2. **훅(VersionCheck)을 끄려면 복사본이어야 한다.** 훅은 실행할 때 서버가 *프로젝트 버전 칸*을 읽어 기대값을 채우고,
   그 칸을 바꾸는 API 가 로그인 토큰을 쓴다. 방향이 다른 TC 를 묶으려면 훅을 끄고 기대값을 블록에 박아야 한다.

이름은 **하는 일**에 맞춘다 (`TC_MB_<케이스>_<하는 일>_<유선/무선>`):

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

- **있으면** `set` 으로 그 블록의 rx 노드를 고친다 - `index = 1` 이 부품번호(F187), `index = 2` 가 SW 버전(F1B1).
  롬패키지로 자동 생성한 TC 는 기대값이 이미 박혀 있을 수 있다 (그러면 올림 TC 는 손댈 것이 없고 내림만 바꾼다).
- **없으면** `version_check = { part = "...", sw = "..." }` 로 두 노드짜리 블록을 새로 만들어 붙인다.
  `ensure_block` 은 같은 이름이 있으면 **넣지 않는다** - 블록이 이미 있는데 이것을 쓰면 조용히 아무 일도 안 한다.
- **차단 케이스에는 버전 확인을 두지 않는다.** 차단되면 보드가 FBL 에 남아 `22` 가 NRC 0x11 이다 (싱글 메모리).

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

## 보드 상태 사슬 (메모리 종류로 갈린다)

케이스마다 시작 버전이 다르다. 묶음이 되려면 앞 케이스의 끝이 다음 케이스의 시작이어야 한다.

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

- 블록 이름과 `VersionCheck` 안의 rx 기대값은 REST 로 읽는다 (`/testcase/<cfg>/list` -> `/testcase/<cfg>/<id>` ->
  `/ruledatabase/<cfg>/<tc>/<block>`). 노드 태그는 `<xfrm:rx ...>` 다 (`rx` 로 찾으면 안 걸린다).
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
4. **복사 원본을 지울지는 사용자에게 묻는다.** 만들어 둔 TC 는 블록을 자기 안에 갖고 있어 원본이 없어도 돌지만,
   원본을 지우면 `tester-tc` 가 **다시 만들지 못한다** (웹 "자동 생성(Test Case)" 으로 되찍어야 한다).
   지우면 그 복구 절차를 계획 파일 주석에 남긴다.
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
| 두 번째 TC 가 `27` 에서 NRC 0x22 | 앞 TC 의 리셋 직후라 조건이 안 된다 - `wait_after_s = 30` 으로 `delay` 블록을 붙인다 |
| 무선 전송이 유선의 4배 느리다 | ECU 가 아니라 TC 설정이다 - `transferData localSTMinTx` 를 `0x00` 으로 (`index = 0` = 그 이름 노드 모두) |
| 시간 초과 뒤 뒤 케이스가 `Tx transmission failed` | `-stop` 뒤 서버가 실제로 멈추기를 기다려야 한다 (joule 이 한다). `timeout_s` 를 넉넉히 |
| TEST 빌드 보드에서 공식 정보 TC 가 실패 | 공식 TC 는 일반 빌드 부품번호를 기대한다 (`expect=[...000] recv=[...TEST0]`) |
| 앱 OEUK TC(`TC_TAR_02060`)가 `7F 27 12` | 그 제어기는 OEUK(`27 13/14`)가 **FBL 에만** 있다 (앱 Dcm 보안 행이 L9 하나). 그 TC 를 쓰지 않고 강제 내림 TC 로 본다 |
| post 블록 직후 `22 F1B1` 이 0 으로 온다 | 2026-11-12 TPMS 실기. 같은 실행에서 Tester 는 제대로 읽었고 전원 재투입 뒤에도 정상이다 - **까닭은 모른다**. 읽기 앞에 `wait` 를 둔다 |
| 리포트 zip 받기만 실패 | 그것만 로그인 토큰이 필요한 REST 다. 평가 자체는 남은 세션으로 돈다 (`auto_login = false`) |

## 실기 기준 (이 스킬을 만든 회차)

TPMS RF 수신기 LT2 (2세대 · 싱글 메모리), 2026-11-12:
`T_ALL` 한 케이스가 `A1 -> A2 -> B1 -> B2` 를 한 번 실행으로 돌아 **리포트 1개 PASS 4 / FAIL 0, 506초, 사람 손 없음**
(`runs/20261112_171144`). 보드 쓰기(flash)가 끼지 않았고 OEUK 는 개발키(`27 13/14` -> `67`)로 돌았다.
