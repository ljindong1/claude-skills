# python-can 모드

CANoe 없이 Vector 장비에 파이썬으로 직접 붙는다. 레스트버스로 DUT 주변 ECU
인 척 주기 송신해 DUT 를 깨우고, DUT 가 보내는 프레임을 DBC 와 대조한다.

## 실행 환경

```
파이썬   D:\Ljindong\python-tutorial\.venv\Scripts\python.exe
         (Python 3.12 — tomllib 필요 / python-can 4.6.1 / cantools)
작업폴더 <스킬>\scripts\pycan      반드시 여기서 실행한다
설정     <스킬>\projects\<이름>.toml
기록     <스킬>\projects\trace\     --trace 로 준다. git 에 올리지 않는다
장비     Vector XL Driver Library (vxlapi64.dll) — Vector Driver Setup
```

**작업폴더가 중요하다.** 스크립트끼리 `from CanModule import …` 로 불러오는
플랫 모듈이라 그 폴더에서 실행해야 한다. 아래 명령은 전부 이렇게 돈다.

```powershell
$py = "D:\Ljindong\python-tutorial\.venv\Scripts\python.exe"
Set-Location "$env:USERPROFILE\.claude\skills\can-bench-setup\scripts\pycan"
& $py can_bench.py ..\..\projects\psu_drv.toml
```

serial 방식(`app_name` 없음)이라 Vector Hardware Manager 에 채널을 배정할
필요가 없다.

## 순서

```
① 확인    ─ ② 설정 ─ ③ DB 점검 ─ ④ 계획 ─ ⑤ 받기만 ─ ⑥ 판정 ─ ⑦ 보고
 연결 안 함                         연결 안 함  송신 없음   송신함
                                                         (매번 묻는다)
```

### ① 확인 — 연결하지 않는다

1. 원본이 앞서 있는지 — `SOURCE.txt` 의 방법. 앞서 있으면 알리기만 한다.
2. 파이썬 환경
   ```
   & $py -c "import sys, can, cantools; print(sys.version.split()[0], can.__version__, cantools.__version__)"
   ```
3. 장비 목록 — 연결·송신하지 않고 목록만 본다
   ```
   & $py -c "from CanModule import CanBase; print(CanBase.detect(['vector']))"
   ```
   설정의 채널(hw_channel)을 모두 가진 장비가 있어야 한다. 없으면
   troubleshooting.md "장비를 못 찾는다".
4. 저장소 현행 DB — `References\DB\` **최상위** `.dbc` 를 버스별(B2 / Local)로 묶고
   **날짜 접두사가 가장 늦은 것**을 현행으로 본다. 설정의 `dbc` 경로와 다르면
   ②에서 경로를 고칠지 묻는다. 최상위에 옛 판이 같이 있으면 그 사실도 알린다.

### ② 설정 — `projects\<이름>.toml`

**기존 설정이 있으면** 그것을 쓴다. `projects\` 목록을 보여 주고 고르게 한다.
하나뿐이면 그것을 쓴다고 말하고 진행한다.

**새 차종·새 제품이면** `assets\bench_template.toml` 로 초안을 만든다.

| 항목 | 채우는 곳 | 모르면 |
|---|---|---|
| `bus.dbc` | 저장소 `References\DB` 최상위의 최신 날짜 판. **절대 경로** | — |
| `bitrate` `data_bitrate` `sample_point` `data_sample_point` | `Ecud_Can.arxml` 의 `CanControllerBaudRate` / `CanControllerFdBaudRate` / 샘플포인트 | 묻는다 |
| `dut.node` | DBC 노드 이름. `CanDbc.py <dbc>` 결과나 DBC 의 `BU_` | 후보를 보여 주고 묻는다 |
| `bus.channel` | 실제 결선 | **반드시 묻는다** |
| `bus.signals` (IGN 등) | 기존 CANoe 패널·CAPL 이 조작하던 신호 | 비워 두고 묻는다 |
| `exclude` | 실험대에 실물로 붙어 있는 ECU | 묻는다 |
| `dut.e2e` | 같은 프로젝트 기존 설정 | `""` 로 두고 알린다 |

- 초안의 각 값 옆 주석에 **근거(파일·날짜)** 를 적는다.
- 같은 프로젝트(같은 제어기)의 기존 `.toml` 은 틀로 써도 된다. 다른 프로젝트
  것은 쓰지 않는다.
- 저장 전 사용자에게 표로 보여 주고 확인받는다.

설정 항목은 `can_bench.py` 의 `SETTINGS_KEYS` 에 있는 것만 쓴다. 모르는 이름은
오타로 보고 `can_bench` 가 멈춘다 (조용히 기본값으로 돌면 실물 ECU 와 같은 ID 를
보낼 수 있어서 일부러 그렇게 만들어졌다).

### ③ DB 점검 — 장비 없이

```
& $py CanDbc.py <dbc> <dut.node>
```

버스마다 한 번. 종료 코드 0 결함 없음 / 1 결함 있음 / 2 오류.
결함이 있어도 벤치는 진행한다 — DB 담당에게 넘길 목록이다. 넘길 파일이
필요하면 `--all --out ..\..\projects\trace\DB_<버스>_<노드>.txt`.

### ④ 계획 — 연결하지 않는다

```
& $py can_bench.py ..\..\projects\<이름>.toml
```

버스별 채널·보율·DB·판정 대상 메시지 수·레스트버스가 흉내 낼 ECU 와 메시지
수·초기값 대신 보낼 신호가 나온다. **⑥에서 무엇을 송신하는지가 여기 다
나온다.** 사용자에게 이것을 보여 준 뒤 ⑤로 간다.

### ⑤ 받기만 — 송신 없음

```
& $py can_bench.py ..\..\projects\<이름>.toml --listen --trace ..\..\projects\trace
```

DUT 가 이미 깨어 있으면 이것만으로 판정이 나온다. 전부 "수신 없음"이면
DUT 가 자고 있는 것이다 — ⑥으로 깨운다.

### ⑥ 판정 — 버스로 송신한다. 매번 묻는다

```
& $py can_bench.py ..\..\projects\<이름>.toml --run --trace ..\..\projects\trace
```

묻기 전에 알릴 것: 송신할 주기 메시지 수(④의 레스트버스 요약), `exclude`
가 비어 있으면 "실물 ECU 가 같이 붙어 있지 않은지", 수신 시간.

`--seconds N` 으로 판정 시간을 바꿀 수 있다 (첫 프레임부터 센다).

### ⑦ 보고

종료 코드 `0` 통과 / `1` 실패 / `2` 설정·연결 오류 또는 중단.

```
## CAN 벤치 결과

| 항목 | 값 |
| 설정 | projects\psu_drv.toml |
| 대상 | GW_PSU_DRV_FD |
| 장비 | VN1640A serial 78463 |
| 방식 | --run, 10초 (앞 2초 제외) |
| B-CAN | 실패 7 / 주의 0 / 정보 5 / 통과 3 |
| Local | … |
| 기록 | projects\trace\PSU_DRV_<시각>.txt, *.blf |
```

그 아래에 **실패·주의 줄만** 메시지 이름과 이유 그대로 옮기고, 이유별로 무엇을
볼지 한 줄씩 붙인다.

| 이유 | 뜻 / 볼 것 |
|---|---|
| 수신 없음 (주기 메시지) | DUT 가 안 보낸다. 깨우기 조건(IGN 신호·NM·PN), 해당 기능 활성 조건 |
| 수신 없음 (이벤트·NM) — 정보 | 조건이 없으면 안 오는 게 정상일 수 있다 |
| 평균 주기 벗어남 | DUT 송신 주기 설정 또는 DB 주기 |
| 간격 1.5배 초과 — 주의 | 프레임이 빠졌다. DUT 가 안 보냈는지 이쪽이 놓쳤는지는 구분 못 한다 |
| 길이 / 형식(FD·Classic) | DB 와 DUT 설정 불일치 |
| 카운터 멈춤·건너뜀 | DUT E2E 카운터 |
| CRC 틀림 | E2E 방식이 HkmcE2E 와 같은지부터 의심 (미확인 사항) |
| CRC 확인 안 함 — 정보 | 그 메시지는 CRC 를 보지 않았다. 통과가 CRC 까지 맞았다는 뜻이 아니다 |

판정 줄의 시각(첫 프레임부터 잰 초)으로 `.blf` 에서 그 자리를 찾을 수 있다.

## 하지 않는 것

- 판정 로직·허용오차 기본값 변경 — 원본 스크립트 쪽 일이다. 설정의 `cycle_tol`
  은 사용자가 정하면 바꾼다.
- 사용자 확인 없는 `--run`.
- `projects\trace\` 를 git 에 넣는 것.
