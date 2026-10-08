# python-can 모드 — Joule 실행

CANoe 없이 Vector 장비에 파이썬으로 직접 붙는다. 실행 도구는 사용자 저장소 **Joule** 이다.
스킬은 Joule 을 복사하지 않고 **그 자리에서 실행**한다 — 사용자가 Joule 을 고치면 다음 실행부터
바로 반영된다. 그래서 이 문서에는 흐름과 판단만 두고, 옵션·판정 기준·설정 항목의 세부는
**실행할 때 Joule 의 문서와 `--help` 를 읽어** 따른다(복제하면 낡는다).

## 실행 환경

```
Joule      환경변수 JOULE_HOME, 없으면 D:\Ljindong\joule
           (git@github.com-ljindong:ljindong1/Joule.git, uv + CPython 3.12 32비트)
실행       uv run --directory <Joule> <명령> <결선> [옵션]     (작업 폴더를 옮기지 않는다)
설정       <Joule>\configs\  devices / targets / benches / tests
기록       <Joule>\runs\<시각>_<도구>_<결선>\   (git 제외 — 시드/키 바이트가 들어간다)
문서       <Joule>\docs\joule-bench.md · joule-sleep.md · joule-deep.md, 전체 joule-guide.html
프로젝트   스킬을 부른 폴더 (예: D:\Mobase\psu_master) — 기본정보만 읽는다
```

| 명령 | 하는 일 | 버스 송신 |
|---|---|---|
| `joule-bench <결선>` | 계획만 출력 | 없음 (연결 안 함) |
| `joule-bench <결선> --listen` | 받기만, DB 대조 | 없음 |
| `joule-bench <결선> --run` | 레스트버스로 깨우고 받기, DB 대조 (수신·길이·FD·주기·카운터·CRC) | **있음** |
| `joule-sleep <결선>` | 시험 대상이 잠들었는지 (SLEEP / NM 만 / AWAKE) | 없음 |
| `joule-deep <결선>` | 심화 TC 계획만 | 없음 |
| `joule-deep <결선> --run [--tc …] [--expect DID=값]` | 자극 → 응답 TC (명령 echo, 타임아웃, 게이트웨이, 슬립, UDS DID·DTC) | **있음** |

종료 코드는 세 명령 모두 `0` 통과 / `1` 실패 / `2` 설정·연결 오류 또는 중단.
`joule-hota`·`joule-reprog` 는 보드에 쓰는 도구라 이 스킬 범위 밖이다.

## 순서

```
① 조용히 확인 ─ ② 시작 질문 ─ ③ 설정 ─ ④ 계획 ─ ⑤ 실행 ─ ⑥ 보고
 연결 안 함       한 번에 묻기   (필요 시)  연결 안 함  고른 만큼
```

**묻는 것은 ②에서 한 번에 끝낸다.** 그 뒤로는 답한 대로 끝까지 간다. 멈추는 것은 오류이거나 ②의 답과 다른 상황(예: 결선 채널을 가진 장비가 없음)을 만났을 때뿐이다.

### ① 조용히 확인 — 연결하지 않는다, 묻지 않는다

1. **Joule 상태.**
   ```
   git -C <Joule> log -1 --format="%h %ad %s" --date=short
   git -C <Joule> status --short
   ```
   - Joule 폴더가 없거나 `uv` 가 없으면 여기서 멈추고 안내한다(경로는 `JOULE_HOME`).
   - **커밋하지 않은 수정이 있으면** ②에서 알린다 — 그 상태 그대로 시험에 쓰인다. Joule 은 실행 기록 `run.json` 에 커밋과 수정 여부를 남긴다.
2. **이번에 쓸 명령의 문서를 읽는다** — `docs/joule-bench.md`(·`joule-sleep.md`·`joule-deep.md`). 옵션이나 판정 기준이 이 문서와 다르면 **Joule 문서를 따른다.**
3. **프로젝트 정보** — 스킬을 부른 폴더에서 읽기만 한다.
   ```
   uv run --directory <Joule> python "<스킬>\scripts\project_info.py" <프로젝트 폴더> --json
   ```
   (Joule 의 파이썬으로 돌린다 — 표준 라이브러리만 쓰는 스크립트다.) 읽는 것은 SKILL.md "공통 근거" 표. 종료 코드 2(앱 폴더 없음)면 프로젝트 폴더에서 부른 게 아니다 — ②에서 묻거나 결선만으로 진행한다.
4. **결선·제어기 목록** — `configs/benches/*.toml` 의 `target`·`device`, 그 제어기의 `[dut].node`, 버스별 `dbc`·보율.
5. **프로젝트와 맞대기** — 3의 결과와 4의 제어기를 비교한다.

   | 비교 | 같은 것으로 보는 조건 |
   |---|---|
   | 대상 | 제어기 `[dut].node` == 프로젝트의 시험 대상 노드 |
   | DB | 버스별 `dbc` 파일 이름 == 프로젝트 **빌드 DB** |
   | 보율 | `bitrate` `data_bitrate` `sample_point` `data_sample_point` == 프로젝트 값 |

   대상이 같은 결선이 **이 프로젝트의 결선**이다. DB·보율이 다르면 ②에서 그 차이를 보여 준다(Joule 의 DBC 는 `can_db/<차종>/` 사본이라 저장소 새 DB 가 반영 안 됐을 수 있다). 대상이 같은 결선이 없으면 ②에서 "새 제어기·결선 설정 만들기" 를 추천으로 올린다.

### ② 시작 질문 — AskUserQuestion 한 번

질문 앞에 두세 줄로 적는다: 프로젝트(차종·제어기·브랜치·시험 대상·빌드 DB), **Joule 커밋과 수정 여부**. 이미 정해진 것은 묻지 않고 "○○ 로 한다" 고 한 줄 적는다. 최대 4개.

| # | 질문 | 선택지 |
|---|---|---|
| 1 | 어느 결선으로 할까요? | 이 프로젝트의 결선 (추천) / 다른 결선 / 새 제어기·결선 설정 만들기 |
| 2 | 무엇을 할까요? | 기본 검증 `joule-bench --run` (추천, **송신**) / 받기만 `--listen` / 슬립 확인 `joule-sleep` / 심화 TC `joule-deep --run` (**송신**) / 계획만 |
| 3 | DB 가 프로젝트 빌드 DB 와 다를 때만: 어떻게 할까요? | Joule DB 사본을 빌드 DB 로 갱신 후 진행 / 이번엔 Joule 사본대로 진행 |
| 4 | 실험대에 실물 ECU 가 같이 붙어 있나요? (송신할 때만) | 없다 / 있다 — 이름 (결선 `exclude`) |

- **질문 2 에서 송신을 고른 것이 이번 실행의 송신 허락이다.** ⑤ 직전에 다시 묻지 않는다. 다음 실행에는 다시 묻는다.
- 제어기는 보통 자고 있어서 받기만으로는 "수신 없음" 만 나온다 — 기본 추천은 `--run`.
- 심화 TC 를 고르면 TC 목록(`joule-deep <결선>` 계획 출력)을 보여 주고 고를 TC 를 같은 질문에서 받는다. 처음 돌리는 제어기는 나눠서(진단 읽기 → 자극·응답 → 슬립) 돌리기를 권한다. `manual` TC 는 사람이 Enter 를 눌러야 한다.
- 보율이 프로젝트와 다르면 묻지 않는다 — ③에서 결선·제어기 설정을 고치자고 보고 끝에 제안한다(틀린 보율은 에러 프레임으로 버스를 망가뜨리므로 이번 실행은 하지 않고 멈춘다).

### ③ 설정 — Joule `configs/` 에 쓴다 (필요할 때만)

Joule 설정은 **사용자 저장소 파일**이다. 쓰기 전에 바꿀 내용(새 파일이면 전체, 기존 파일이면 바뀌는 줄)을 보여 주고 확인받는다. **Joule 저장소 커밋은 하지 않는다** — 사용자가 한다.

| 경우 | 하는 일 |
|---|---|
| 실물 ECU 가 있다 | 결선 `[bus."<버스>"].exclude` 에 추가 |
| DB 사본 갱신 | 프로젝트 `References\DB` 의 빌드 DB 를 `<Joule>\can_db\<차종>\` 로 복사하고, 제어기 `[[bus]].dbc` 파일 이름을 바꾼다 (DBC 사본은 git 제외) |
| **새 제어기·결선** | 아래 "새 설정 만들기" |

#### 새 설정 만들기

같은 제어기(= 같은 `rel_<차종>_<제어기>`)의 기존 Joule 설정이 있으면 그것을 틀로 쓴다. 다른 제어기 것은 쓰지 않는다. 형식과 항목은 `src/joule/config.py`·기존 `configs/` 주석을 따른다(모르는 항목은 Joule 이 오타로 보고 멈춘다).

| 파일 | 항목 | 채우는 곳 | 모르면 |
|---|---|---|---|
| `targets/<차종>_<제어기>_<위치>.toml` | `[dut].node` | 프로젝트 시험 대상 노드 | 여럿이면 묻는다 |
| | `[[bus]] name` · `dbc` · `bitrate` · `data_bitrate` · `sample_point` · `data_sample_point` | 프로젝트 빌드 DB(사본 경로) · `Ecud_Can.arxml` | — |
| | `[dut].e2e` · `[bus.signals]`(IGN 등) | 같은 제어기 기존 설정, CANoe 패널·CAPL | 비워 두고 묻는다 |
| `benches/<결선>.toml` | `device` · `target` · 버스별 `channel` | 장비 파일, 실제 결선 | **채널은 반드시 묻는다** |
| | `exclude` | ②의 질문 4 | — |

- 각 값 옆 주석에 **근거(파일·날짜)** 를 적는다.
- 모르는 값(채널·IGN 신호)은 추정하지 않고 한 번에 모아 묻는다.
- 저장 전 초안을 표로 보여 주고 확인받는다.

### ④ 계획 — 연결하지 않는다

```
uv run --directory <Joule> joule-bench <결선>        (또는 joule-sleep / joule-deep)
```

버스별 채널·보율·DB·판정 대상·흉내 낼 ECU·DB 예외 적용 건수가 나온다. 요약만 보여 주고 ⑤로 간다. ②에서 "계획만" 이면 ⑥으로.

### ⑤ 실행 — ②에서 고른 만큼

```
uv run --directory <Joule> joule-bench <결선> --run   [--seconds N]
uv run --directory <Joule> joule-bench <결선> --listen
uv run --directory <Joule> joule-sleep <결선>          [--seconds N]
uv run --directory <Joule> joule-deep  <결선> --run   [--tc …] [--expect DID=값]
```

- 한글이 깨지면 `PYTHONIOENCODING=utf-8` 을 붙인다.
- CANoe 가 같은 채널을 잡고 있으면 `--run` 은 채널 설정이 같아야 한다(Joule 문서). 연결 오류면 `troubleshooting.md`.
- 빌드 확인이 목적이면 `joule-deep --tc version_dids --expect F1B1=<버전>` 처럼 기대값을 준다(보드에 쓴 버전이 실제로 도는지).

### ⑥ 보고

결과는 화면 출력과 `runs/<…>/result.txt`·`run.json` 에서 읽는다.

```
## CAN 실험대 결과

| 항목 | 값 |
| 명령 | joule-bench he1i_psu_drv --run, 10초 |
| 대상 | GW_PSU_DRV_FD (HE1i / PSU, 브랜치, 빌드) |
| Joule | 5f4bad7 (수정 없음)            ← run.json 의 git |
| 장비 | VN1640A serial … |
| DB | 빌드 DB 와 같음 / 다름 — 무엇이 |
| B-CAN | 실패 n / 주의 n / 정보 n / 통과 n |
| Local | … |
| 기록 | <Joule>\runs\<폴더> (트레이스 .asc) |
```

그 아래에 **실패·주의 줄만** 메시지 이름과 이유 그대로 옮기고, 이유별로 무엇을 볼지 한 줄씩 붙인다. 이유의 뜻은 Joule 문서(`joule-bench.md` 판정 항목, `joule-deep.md` TC)를 따른다. 판정 줄의 시각(첫 프레임부터 잰 초)으로 트레이스에서 그 자리를 찾는다.

DB 예외(`can_db/<차종>/exceptions.toml`)로 바뀐 판정은 결과표 머리의 "예외 적용 N건" 을 함께 적는다. 새 예외가 필요해 보이면 **제안만** 한다 — 확인된 사양만 적는 파일이다.

## 하지 않는 것

- Joule 코드 수정 — 판정 로직·허용오차 기본값은 Joule 쪽 일이다. 결함이면 보고한다.
- Joule 저장소 커밋·push.
- ②에서 송신을 고르지 않았는데 `--run` 하는 것.
- `joule-hota`·`joule-reprog` 실행 (보드에 쓴다).
