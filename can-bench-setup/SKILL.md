---
name: can-bench-setup
description: 실험대의 ECU 가 CAN 을 DB 대로 보내는지 확인하는 스킬. 모드가 둘이다. 기본(매개변수 없음)은 python-can 모드로, Vector 장비(VN1640A)에 파이썬으로 직접 붙어 레스트버스로 깨우고 받은 프레임을 DBC 와 대조(주기·길이·FD 형식·카운터·CRC)한다. 설정은 차종별 .toml 하나다. 매개변수 `canoe` 를 주면 CANoe 모드로, 통폴더에서 차종 cfg 와 참조 파일만 뽑아 단독 컨피그를 만들고 저장소 현행 DB 로 갱신·검증하며 CANoe COM 으로 확인·측정한다. 사용자가 "CAN 벤치", "can-bench", "CAN 검사 돌려줘", "새 빌드 CAN 나오는지 봐줘", "DB 대로 나오나", "레스트버스로 깨워줘", "주기 맞나", "CRC 맞나", "벤치 설정 만들어줘", "새 차종 toml", "CAN 이 안 나와", "에러 프레임" 등을 말하면 python-can 모드, "CANoe 컨피그 뽑아줘", "CANoe 설정 만들어줘", "cfg 검증", "CDD 물려 있나", "CANoe 열어서 확인" 처럼 CANoe 를 콕 집으면 CANoe 모드다. Claude Code CLI(사용자 PC) 전용. CVD/T32 보드 라이팅은 cvd-project 담당이다.
---

# can-bench-setup

ECU 가 CAN 을 **DB 대로 보내는지** 실험대에서 확인한다. 도구는 두 가지다.

| 호출 | 모드 | 도구 | 자세한 것 |
|---|---|---|---|
| `/can-bench-setup` (매개변수 없음) | **python-can** | `scripts/pycan/` | `references/pycan.md` |
| `/can-bench-setup canoe` | CANoe | `scripts/canoe/canoesetup.py` | `references/canoe.md` |

**모드 고르기.** 매개변수 첫 단어가 `canoe` 면 CANoe 모드다. 매개변수가 없거나
다른 말이면 python-can 모드다. 다만 요청이 `.cfg` 추출·CDD·CAPL 처럼 CANoe
컨피그 자체에 관한 것이 분명하면 CANoe 모드로 가고, 그렇게 골랐다고 말한다.

모드를 정하면 **그 모드의 references 문서를 먼저 읽고** 거기 순서대로 한다.

## 공통 절대 규칙

- **버스로 송신하는 일은 매번 사용자에게 묻고 한다.** python-can 의 `--run`,
  CANoe 의 `run` 이 여기에 든다. 레스트버스·시뮬레이션 노드가 실제 버스로
  프레임을 보낸다. 한 번 허락받았다고 다음 실행까지 허락된 것이 아니다.
- **저장소(`psu_app`)는 읽기만 한다.** DB 경로와 보율의 근거로 쓸 뿐이다.
- **제어기가 다르면 = 다른 프로젝트다.** 다른 프로젝트의 설정(.toml)이나
  CANoe 컨피그를 도너로 쓰지 않는다. 판단 근거는 저장소
  `References\01_HSM_Framework\*.sre` 의 `rel_<차종>_<제어기>_V` 다.
- **모르는 값을 추정해서 채우지 않는다.** 채널 결선, IGN 신호 조합처럼
  저장소에 없는 값은 비워 두고 묻는다. 틀린 값은 엉뚱한 ID 를 버스로 보낸다.
- 스크립트를 고쳐서 문제를 피하지 않는다. 스크립트 결함이면 보고한다.

## 공통 근거 — 저장소에서 읽는 것

| 항목 | 출처 |
|---|---|
| 차종 · 제어기 | `References\01_HSM_Framework\*.sre` 의 `rel_<차종>_<제어기>_V` |
| 현행 CAN DB | `References\DB\` **최상위**, 같은 버스 DB 가 여럿이면 **날짜 접두사가 가장 늦은 것** |
| 보율 · 샘플포인트 | `Configuration\Ecu\Mcal\Ecud_Can.arxml` |
| 네트워크 구성 | `Configuration\System\DBImport\BCAN.arxml` · `L1CAN.arxml` |

구버전은 보통 `unused\` 로 내려가지만, 최상위에 옛 판이 남아 있기도 하다
(2026-09-30 psu_app: B2·Local 모두 2025 판과 2026-05 판이 최상위에 같이 있다).
그래서 날짜로 고르고, 옛 판이 최상위에 남아 있으면 보고에 적는다.

## 스크립트 출처

`scripts/pycan/` 은 사용자가 만든 `D:\Ljindong\python-tutorial\python-can_tutorial`
에서 복사한 것이다. 출처와 커밋은 `SOURCE.txt` 에 있다.

- python-can 모드를 시작할 때 **원본이 앞서 있는지** `SOURCE.txt` 의 방법으로
  본다. 앞서 있으면 알리기만 하고, 다시 복사할지는 사용자가 정한다.
- 복사본은 원본과 같게 유지한다. 스킬 쪽에서만 고치지 않는다.

## 데이터가 안 나온다는 문의

두 모드 공통으로 `references/troubleshooting.md` 를 먼저 읽는다. 첫 번째
의심은 **CAN FD 인데 Classic 으로 잡힌 것**, 그다음이 전원·IGN → 디버거가
CPU 를 세워 둔 것 → 종단저항 → 채널 배정이다.

## 범위 밖

- 판정 기준을 바꾸는 것 — 스크립트(원본) 쪽 일이다
- CVD / T32 보드 라이팅 — `cvd-project` 담당
- CAPL · PANEL · CDD 작성·수정
- Vector Hardware Manager 설정 변경 — 바이너리라 읽지도 쓰지도 않는다
