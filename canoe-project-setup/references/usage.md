# CANoe 조작 — 컨피그를 만든 다음

차종에 상관없이 같다. CANoe 19 기준(리본 UI).

---

## 컨피그 열기

```
CANoe 실행  ->  File  ->  Open Configuration  ->  <폴더>\<차종>_PSU_*.cfg
```

**세대가 낮은 컨피그를 열면 변환 확인이 뜬다.** CANoe 11 이 만든 컨피그를
CANoe 19 에서 열면 그렇다. 한 번 저장하면 `<VFileName V7 …>` 이 `V9` 로
올라가고, 그 뒤로는 안 뜬다.

변환 후 **반드시 `verify` 를 다시 돌린다.** 변환하면서 참조가 조용히 빠질 수
있다 — HE1i 컨피그는 이 과정에서 CDD 참조를 잃었다.

```
python scripts\canoesetup.py verify --dir . --repo "D:\...\psu_app" --model HE1i
```

---

## CAN DB 교체

저장소 `References\DB` **최상위**에 있는 것이 현행이다. 구버전은 `unused\` 로
내려가 있으므로, 최상위에 무엇이 있는지가 곧 "지금 맞는 DB" 다.

```
python scripts\canoesetup.py verify --dir . --repo "D:\...\psu_app"
```

`[실패] B2 DB 가 저장소 현행과 다르다` 가 뜨면 바꿔야 한다. `create` 는
갱신까지 하지만, 이미 만들어 둔 폴더를 고칠 때는 CANoe 에서 한다.

```
Simulation Setup  ->  해당 DB 우클릭  ->  Replace
       또는
Configuration  ->  Databases  ->  Remove 후 Add
```

교체 후 **네트워크 배정을 확인한다.** DB 를 바꾸면 노드-네트워크 연결이
풀릴 수 있다. `Node Synchronization` 대화상자가 뜨면 기존 노드에 새 DB 의
같은 이름 노드를 맞춰 준다.

DB 이름(별칭)도 확인한다 — `FD_B2` / `Local_FD_PSU_DRV` 처럼 CAPL 과 패널이
그 이름으로 신호를 찾는다. 별칭이 바뀌면 컴파일이 깨진다.

---

## 채널 배정

CANoe 안의 채널 번호는 **논리 번호**다. 실제 장비 채널은 Vector Hardware
Manager 에서 배정한다. VN1640A 의 CH3 / CH4 에 꽂았어도 CANoe 채널 1 / 2 에
배정하면 된다.

```
CANoe 채널 1   Body CAN  (B2)
CANoe 채널 2   Local CAN (PSU_DRV)
```

```
Hardware  ->  Network Hardware Configuration
   또는  Vector Hardware Manager 를 직접 실행
```

**여기서 CAN 과 CAN FD 를 고른다. 이것이 .cfg 에 들어 있지 않다.**
자세한 것은 troubleshooting.md 를 본다 — 데이터가 안 나올 때 첫 번째로
볼 곳이다.

보율은 저장소 `Configuration\Ecu\Mcal\Ecud_Can.arxml` 이 근거다.
`CanControllerBaudRate` 가 중재 구간, `CanControllerFdBaudRate` 가 데이터
구간이다.

---

## 진단(CDD) 물리기

`verify` 가 아래를 내면 CDD 가 폴더에 있는데 컨피그가 안 쓰고 있는 것이다.

```
[실패] .cdd 가 폴더에 있는데 컨피그가 참조하지 않는다
```

```
Diagnostics / ISO TP  ->  진단 기술 추가  ->  <차종>_PSU_*.cdd
   Seed&Key DLL 도 같이 지정  ->  HKMC_AdvancedSeedKey_Win32.dll
저장
```

물린 뒤 `verify` 를 다시 돌려 `[통과] 진단 기술 참조 1건` 이 나오는지 본다.

> `VBasicDiagnosticStreamer` 블록의 숫자로 판단하지 않는다. CDD 가 물려 있는
> 원본에서도 그 값은 `0` 이다. 판단 근거는 `.cdd` 참조다.

### CDD 가 무엇인가

ECU 진단 사양서를 기계가 읽는 형태로 만든 것이다 (CANdela XML). DTC 목록,
DID 와 그 해석 규칙, 지원 서비스, 보안접근(`0x27`) 규칙이 들어 있다.
CANoe 에 물리면 Diagnostic Console 에서 버튼으로 진단을 보내고 응답을 사람이
읽는 형태로 풀어준다. 없으면 raw hex 로 직접 쳐야 한다.

파일명의 `95486_02` 같은 것은 부품번호 체계이고 `_R5` 는 리비전이다.

**남의 차종 CDD 를 쓰고 있으면 안내문(`읽어보세요.txt`)에 적혀 있다.**
그 경우 DTC·DID 해석이 원래 차종 기준이므로, 이 차종에만 있는 항목은
안 보이거나 잘못 풀린다.

---

## 측정 시작 전에 볼 것

측정을 시작하면 시뮬레이션 노드가 **버스로 송신한다.** 실차·실보드에 붙은
상태라면 그 전에 확인한다.

```
1. 보드에 전원과 IGN 이 들어갔나      B+ 만으로는 슬립에 머문다
2. 디버거가 CPU 를 세워 두지 않았나   main 에서 멈춘 상태면 송신이 없다
3. 채널이 CAN FD 인가                 Hardware Manager
4. 종단저항
```

2번은 특히 잘 놓친다. CVD/T32 로 `RE` 를 눌러 `main` 에서 멈춘 상태는
**CPU 가 정지한 것**이라 CAN 이 안 나간다. 디버거를 떼고 전원만으로 띄운
상태가 실차 조건이다.

---

## 열지 않고 확인

```
python scripts\canoesetup.py check --dir <폴더>
```

CANoe 를 COM 으로 잠깐 띄워 컨피그를 열고 DB 목록과 시뮬레이션 노드를 읽은 뒤
닫는다. **측정을 시작하지 않으므로 버스로 아무것도 내보내지 않는다.**

산출물은 `<폴더>\_autorun\` 에 남는다 (`check.ps1`, `check_log.txt`).

CANoe 창이 뜨므로 사람이 보고 있는 화면이면 미리 알린다.

---

## 빌드가 새로 나왔을 때

CANoe 컨피그는 빌드 산출물을 쓰지 않으므로 대부분 손댈 것이 없다.
**CAN DB 가 바뀌었을 때만** 갱신한다.

```
git pull                                       Jenkins 가 자동 커밋한다
python scripts\canoesetup.py verify --dir . --repo "D:\...\psu_app"
```

DB 가 바뀌었으면 위의 "CAN DB 교체" 절차를 따른다.
