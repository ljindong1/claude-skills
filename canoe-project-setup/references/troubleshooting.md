# CANoe 함정

전부 HE1i PSU 작업(2026-09-22~23)에서 실제로 밟은 것들이다.
공통점은 **설정이 멀쩡해 보이는데 결과만 틀린다**는 것이다.

---

## 데이터가 안 나온다 — 첫 번째로 볼 것

**채널이 CAN FD 가 아니라 Classic CAN 으로 설정돼 있는지 본다.**

HE1i 작업에서 가장 오래 잡아먹은 것이다. 종단저항·보율·컨피그·DB 를 전부
뒤진 끝에, 채널이 Classic CAN 으로 잡혀 있던 것이 원인이었다.

```
증상   수신 프레임 0, 에러 프레임 초당 4000건대
곳     Vector Hardware Manager  ->  해당 채널  ->  CAN FD
```

**이 설정은 `.cfg` 안에 없다.** 보율도 CAN/CAN FD 구분도 없다. Vector
Hardware Manager 의 `Startup.Profile` 에 있고 **바이너리라 파일로는 확인도
수정도 못 한다.**

```
C:\Users\<계정>\AppData\Local\Vector\VectorHardwareManager\Startup.Profile
```

그래서 `verify` 로는 영원히 안 잡힌다. 컨피그는 완벽한데 데이터만 0 이다.
**스킬이 파일 검사로 잡을 수 없는 유일한 부류이므로 사람에게 먼저 묻는다.**

CAN FD 버스에 Classic CAN 컨트롤러를 붙이면, BRS 가 선 프레임을 해석하지
못해 에러 프레임을 쏟아내고 버스를 방해한다. 수신이 0 인 것뿐 아니라
**실제로 버스를 망가뜨리고 있는 상태**다.

보율은 저장소가 근거다.

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
4. 채널 배정          Hardware Manager 에서 논리 채널 1/2 에 물려 있나
```

2번은 특히 잘 놓친다. `RE` 로 `main` 에서 멈춘 뒤 `Go` 를 안 눌렀으면
애플리케이션이 한 줄도 안 돈다. 디버거를 떼고 전원만으로 띄운 것이
실차 조건이다.

---

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
python scripts\canoesetup.py verify --dir <폴더> --repo <psu_app> --model <차종>
```
