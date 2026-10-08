# 문제 해결

HE1i PSU 작업(2026-09-22~23, CANoe)과 python-can 벤치 작업(2026-09-28~30)에서
실제로 밟은 것들이다. 공통점은 **설정이 멀쩡해 보이는데 결과만 틀린다**는 것이다.

순서: 공통 → python-can 모드 → CANoe 모드.

---

# 공통

## 데이터가 안 나온다 — 첫 번째로 볼 것

**채널이 CAN FD 가 아니라 Classic CAN 으로 잡혀 있는지 본다.**

HE1i 작업에서 가장 오래 잡아먹은 것이다. 종단저항·보율·컨피그·DB 를 전부
뒤진 끝에, 채널이 Classic CAN 으로 잡혀 있던 것이 원인이었다.

```
증상   수신 프레임 0, 에러 프레임 초당 4000건대
```

CAN FD 버스에 Classic CAN 컨트롤러를 붙이면, BRS 가 선 프레임을 해석하지
못해 에러 프레임을 쏟아내고 버스를 방해한다. 수신이 0 인 것뿐 아니라
**실제로 버스를 망가뜨리고 있는 상태**다.

어디서 정하는지는 모드마다 다르다.

| 모드 | FD 여부를 정하는 곳 |
|---|---|
| python-can (Joule) | 제어기 설정 `configs/targets/<이름>.toml` 의 `[[bus]] fd` (빼면 `true`) 와 보율·샘플포인트 |
| CANoe | Vector Hardware Manager — `.cfg` 에 없고 바이너리라 파일로 확인 불가 |

보율 근거는 저장소다.

```
Configuration\Ecu\Mcal\Ecud_Can.arxml
   CanControllerBaudRate     중재 구간
   CanControllerFdBaudRate   데이터 구간
```

### 그다음 순서

```
1. 전원과 IGN         B+ 만으로는 슬립에 머물러 CAN 을 안 쏜다
2. 디버거 상태        CVD/T32 로 main 에서 멈춰 둔 상태 = CPU 정지 = 송신 없음
3. 종단저항
4. 채널 배정·결선     설정의 채널이 실제로 꽂힌 채널인가
```

2번은 특히 잘 놓친다. `RE` 로 `main` 에서 멈춘 뒤 `Go` 를 안 눌렀으면
애플리케이션이 한 줄도 안 돈다. 디버거를 떼고 전원만으로 띄운 것이
실차 조건이다.

## 두 모드를 번갈아 쓸 때

같은 장비(VN1640A)를 두 모드가 다른 방식으로 잡는다.

```
python-can   serial 방식 — Hardware Manager 배정 없이 장비·채널을 직접 잡는다
CANoe        애플리케이션 이름 단위로 Hardware Manager 에서 배정받는다
```

- **CANoe 가 떠 있으면** python-can 이 채널을 못 잡는다 → CANoe 를 닫는다.
- **python-can 은 되는데 CANoe 는 전부 0** 이면 CANoe 애플리케이션 쪽에 채널이
  배정 안 된 것이다. 측정은 정상으로 돌기 때문에 에러 없이 0 만 보인다.

---

# python-can 모드 (Joule)

아래 메시지는 Joule(`<JOULE_HOME>`) 이 낸다. 메시지·동작이 바뀌었으면 Joule 문서(`docs/`)를 따른다.

## 장비를 못 찾는다

```
채널 [2, 3] 을 모두 가진 Vector 장비가 없습니다. 감지된 장비: ...
```

1. USB 연결과 Vector 드라이버
2. **다른 프로그램(CANoe 등)이 채널을 잡고 있지 않은가**
3. 결선(`configs/benches/`)의 `channel` 은 **hw_channel** 이다. 장비 표기 CH3 은 `2`, CH4 는 `3`.

장비가 여러 대면 `serial = "auto"` 는 고르지 않고 멈춘다 — 잘못 고르면 엉뚱한
장비로 송신하기 때문이다. 오류 메시지의 감지된 장비 목록을 보고 결선에 `serial = <숫자>` 를 적는다.

## 연결 오류 — vxlapi64.dll

python-can 은 pip 로 깔리지만 Vector XL Driver Library 는 아니다. Vector Driver
Setup 으로 설치한다. 없으면 `[연결 오류]` 에 그 사실이 나온다.

## 설정 오류 — 모르는 항목

```
[[bus]] 1번째에 모르는 항목 'bitrat'. 'bitrate' 를 쓰려던 것인가요?
```

일부러 멈추게 만든 것이다. 오타를 조용히 무시하면 기본값으로 돌아 실물 ECU 와
같은 ID 를 보낼 수 있다. 제안된 이름으로 고친다.

DB 경로가 상대 경로면 **제어기 설정 파일이 있는 폴더(`configs/targets/`) 기준**이다
(Joule 은 `../../can_db/<차종>/…` 처럼 쓴다). 실행 폴더 기준이 아니다.

## `--listen` 에서 전부 "수신 없음"

DUT 가 자고 있다. 정상일 수 있다 — `--run` 으로 깨운다. `--listen` 은 아무것도
보내지 않으므로 깨우지 못한다.

## `--run` 인데도 DUT 가 안 깨어난다

```
<버스>: 10초 동안 받은 프레임 없음
```

1. 공통의 순서 (전원·IGN·디버거·종단·결선)
2. `[bus.signals]` 의 IGN 신호 — DB 초기값은 전부 Off(0) 라 켜 줘야 한다.
   PSU DRV 는 `BCM_Ign1InSta` `BCM_Ign2InSta` `BCM_AccInSta` `IGN3State` 를 1 로 둔다
   (SP3i CANoe 패널이 조작하던 신호에서 가져온 가정)
3. `pn` — NM 부분 네트워크 비트가 필요한 제어기면 `"all"` 로 바꿔 본다.
   PSU DRV 는 2026-09-30 확인 결과 `"all"` 로 바꿔도 동작이 같아 `"none"` 이다.
4. `wake_timeout_s` 가 너무 짧지 않은가

## 에러 프레임이 난다

보율·샘플포인트가 버스와 다를 때 난다. `f_clock`(Vector FD 는 80MHz),
`sample_point`, `data_sample_point` 가 `Ecud_Can.arxml` 과 같은지 본다.
`fd` 가 버스와 맞는지도 본다 (공통 첫 절).

## CRC 틀림

`e2e = "HKMC"` 는 SP3i CANoe CAPL 에서 옮긴 방식이다. **PSU 송신 CRC 가 이
방식과 같은지는 아직 확인되지 않았다.** 한 메시지만 틀리면 그 메시지 문제,
전부 틀리면 방식 자체가 다른 것을 먼저 의심한다.

## 판정은 "주의"인데 트레이스에는 다 있다

"간격 1.5배 초과"는 프레임이 빠졌다는 뜻이다. DUT 가 안 보냈는지 이쪽(PC 수신)이
놓쳤는지는 구분하지 못한다. 판정 줄의 시각으로 `.blf` 를 열어 그 자리를 본다.

---

# CANoe 모드

## CDD 참조가 사라진다

세대가 낮은 컨피그를 CANoe 19 에서 열어 저장하면 **진단 기술 참조가 조용히
빠질 수 있다.** HE1i 컨피그가 그렇게 됐다.

```
원본(CANoe 11)  <VFileName V7 BQL> 1 base=cfg "SP3i_PSU_95486_02_R5.cdd"
저장 후(19)     (없음)
```

파일은 폴더에 그대로 있고 CANoe 도 아무 말이 없다. 진단을 걸어 보기 전까지
모른다. **변환 후에는 반드시 `verify` 를 돌린다.**

> `VBasicDiagnosticStreamer` 블록의 숫자로 판단하면 안 된다. CDD 가 물려 있는
> 원본에서도 그 값은 `0` 이다. 판단 근거는 `.cdd` 참조다.

---

## 남의 차종 자산을 이 차종 것으로 착각한다

통폴더는 **컨피그 여러 개가 CAPL / PANEL / CDD 를 돌려쓰는 구조**다.
HE1i 원본(`15.SP3i_PSU`)에 HE1i 이름으로 있던 것은 셋뿐이었다.

```
HE1i_PSU_MCar_R1.cfg / .stcfg / .run\
```

CDD·PANEL·CAPL·vsysvar 는 전부 SP3i 것을 참조하고 있었다. 이름을 HE1i 로
바꾸면 **공유하고 있다는 사실이 감춰진다.**

```
HE1i_PSU_95486_02_R5.cdd 안에서
   SP3i  8회   Motor_Type_SP3i / SP3i_Slide_Tilt_Height_Recl …
   HE1i  2회   문서 제목뿐
```

남은 8개는 **DID 의 데이터 정의 이름**이라 문자열만 바꾸면 진단 의미가
깨진다. 그래서 못 바꾼다 — 즉 진단은 원래 차종 기준으로 해석된다.

**공유 자체가 틀린 게 아니다.** 같은 프로젝트(제어기)면 부품번호가 같아
사양서도 같다. 문제는 그게 안 보이게 되는 것이다. 그래서 `create` 는
`읽어보세요.txt` 에 **파일별 출처표**를 남긴다.

**다른 프로젝트면 이야기가 다르다.** 제어기가 다르면 CDD·Local DB·PANEL 이
전부 다르므로 물려쓰면 안 된다. 그 프로젝트의 원본을 받아야 한다.

---

## 참조 태그를 고정하면 절반을 놓친다

```
CANoe 11 이 만든 컨피그   <VFileName V7 QL>   <VFileName V7 BQL>
CANoe 19 에서 저장하면    <VFileName V9 QL>   <VFileName V9 BQL>
```

버전을 고정하면 다른 세대 컨피그에서 참조를 **0건** 찾는다. 통폴더에는
두 세대가 섞여 있다.

**`QL` 만 보면 CDD 를 놓친다.** CDD 는 `BQL` 태그에 `base=cfg` 를 달고 온다.
`base=app` 은 CANoe 설치 폴더 기준이라 우리 폴더와 무관하다.

---

## cfg 를 편집기로 열지 않는다

`.cfg` 는 줄 단위 텍스트지만 **utf-8 로도 cp949 로도 통째로 디코드되지
않는다.** 바이너리 조각이 섞여 있다.

```
utf-8  position 8333 의 0xc6 에서 실패
cp949  position 5014 의 0xbf 에서 실패
```

일반 편집기로 열어 저장하면 깨진다. 스크립트는 latin-1 왕복으로 바이트를
보존한다. CRLF 도 그대로 유지된다 (HE1i 컨피그 102,226줄 전부 CRLF).

### 치환할 때 역슬래시

경로를 정규식 치환의 **치환 문자열**로 그냥 넣으면 안 된다.

```
잘못   re.sub(pat, "CAN DB\20260529_...", txt)     \2 가 그룹 참조로 해석된다
결과   "CAN DB60529_..."                            경로가 깨진다
맞게   re.sub(pat, lambda m: "CAN DB\20260529_...", txt)
```

스크립트를 만들면서 실제로 이 버그를 냈고, `verify` 가 잡았다.

---

## 파일 참조로 안 나오는 파일이 있다

환경변수 `.ini` 는 cfg 안에 **파일 참조로 등장하지 않는다.** 심볼트리
노드 키로만 나온다.

```
<NodeKey>{RootSymbolItem/PSM_envvars{NetworkAggregateItem</NodeKey>
```

참조만 따라가면 `PSM_envvars_<차종>.ini` 가 통째로 빠진다. 이름 규칙으로
찾아야 한다. 통폴더에는 남의 차종 것(`PSM_envvars_RG3_EV_PE.ini`)도 같이
있으므로 차종 코드로 거른다.

CAPL `.cin` 도 마찬가지다 — cfg 가 아니라 `.can` 의 `#include` 로만 등장한다.

---

## 남의 PC · 남의 프로젝트 경로 잔재

HE1i 원본 컨피그에는 폴더 밖을 가리키는 참조가 **206건** 있었다.

```
145건  C:\Users\ADMINI~1            다른 계정의 임시 폴더
 24건  E:\14_VINFAST PSM\...        완전히 다른 프로젝트의 CAPL 경로
 15건  ..\Public                    CANoe 기본 템플릿
 14건  ..\30_Log                    로그 출력 경로
  4건  E:\00_Log\SP3i               다른 PC 의 로그
```

측정을 막지는 않는다. 다만 **로깅을 쓸 때 출력 경로를 먼저 확인한다** —
없는 드라이브를 가리키고 있으면 로깅이 실패한다.

`VFileName` 태그 **밖**에 맨 절대경로로 있는 것도 있다. CAPL 컴파일 출력
(`.cbf`) 경로가 원작성자 PC 를 가리킨 채 남는다. CANoe 가 다시 컴파일하면
덮어쓰므로 막지는 않는다.

---

## .cbf 가 없다고 나올 때

```
[실패] 참조하는데 없는 파일 1건
       CAPL\HE1i_PSU_FD_PSS_CRC_R0.cbf
```

`.cbf` 는 CAPL 컴파일 출력이다. CANoe 가 컨피그를 열 때 `.can` 에서 다시
만들므로 치명적이지 않다. 다만 `.can` 까지 없으면 노드가 통째로 빠진 것이라
심각하다. **둘 다 있는지 확인한다.**

---

## 대상 폴더가 이미 있을 때

`create` 는 **중단한다.** 덮어쓰지 않는다. 기존 폴더에 사람이 손본 내용이
있을 수 있기 때문이다.

기존 폴더를 점검만 하려면 `verify` 를 쓴다.

```
python scripts\canoe\canoesetup.py verify --dir <폴더> --repo <psu_app> --model <차종>
```
