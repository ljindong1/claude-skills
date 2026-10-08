# Jenkins·빌드 흐름

프로젝트 공통 구조(LAB 표준)와 HE1i 에서 확인한 동작이다. 프로젝트별 Job 이름·브랜치는 프로필.

## 1. 트리거와 Hook

- 작업 브랜치(`devel_*`)에 push 하면 Jenkins Job 이 폴링으로 빌드를 시작한다. **push = 빌드**이므로 커밋·push 는 사용자 지시가 있을 때만.
- `Build_Hook_GIT_ASEC.bat`(표준, 수정 금지)은 인자가 Hook 이면 **마지막 커밋 제목**을 빌드 동작으로 쓴다: `Build`, `Compile`, `GenerateAll`, `Rebuild`, `Clean`. 제목이 이 단어 하나인 빈 커밋이 그 동작의 트리거다. 일반 커밋 제목은 기본 동작(Build: 변경분 생성+컴파일).
- 과제 Hook(예: `Build_Hook_HE1I.bat`)은 `PJ_Define.h` 의 `JENKINS_BUILD_TARGET` 을 읽어 `ALL` 이면 변형 빌드(`BuildVariants.bat`), 아니면 단일 빌드 + `PostPackage.bat`.
- 빌드 성공 시 `GitPush.bat` 이 `git add -f .` 후 `Auto commit from Jenkins #N` 으로 커밋해 같은 브랜치에 push 한다(의도된 동작 — 지적하지 않는다). 그래서 사람 커밋 뒤에는 항상 pull 이 필요하다.

## 2. ALL / CURRENT

| 값 | 결과물 | 용도 |
|---|---|---|
| CURRENT | 현재 버전 한 벌 | 패치 적용·검수 빌드 |
| ALL | 현재 / 현재_test / 상위(+10) / 상위_test 네 벌 | H-OTA 업·다운그레이드 평가 |

- 전환은 `PJ_Define.h` 한 줄 변경 커밋. 제목 예: `[<제어기>][<차종>][V3.0.xx] JENKINS_BUILD_TARGET ALL 로 전환 (H-OTA 평가용 4벌 빌드)`.
- 평가가 끝나면 **반드시 CURRENT 로 되돌리는 커밋**을 한다. 잊으면 이후 빌드가 계속 4벌로 오래 걸리고, PR 에 ALL 이 섞인다.
- 변형 빌드는 PJ_Define.h 를 임시로 바꿨다가 원복하므로 그 변경은 커밋되지 않는다.

## 3. 산출물 구조 (HE1i APP 예)

```
Debug/OEUK_HE1I/
  26810/        he1i_psu_app_v3_0_xx.{elf,hex,map,s19,sre}, _Writing.s19, BuildWarning.xlsx, rom_26810.zip, rom_26810/
  26810_test/   …  rom_26810_test.zip
  26820/        …
  26820_test/   …
```
- `_Writing.s19`: CVD/T32 라이팅용. `rom_<버전>.zip`: aSIMS 서명 입력.
- CURRENT 빌드는 26810 폴더만 갱신한다. ALL 빌드 후 네 폴더 모두 새 SWP 버전 파일만 있는지 확인한다(이전 버전 파일 잔존 여부).
- **같은 소스라도 재빌드하면 이미지가 달라질 수 있다.** Os 생성기가 재생성 때 태스크 스택 배치 순서를 바꿔 `Os_GaaStack`·`MAINSW_CRC` 가 변한다. 서명 요청 후에는 실기가 끝날 때까지 APP 빌드를 일으키는 push 를 하지 않는다(troubleshooting S12).
- FBL 은 버전 폴더 없이 `OEUK_HE1I`, `OEUK_HE1I_TEST` 바로 아래.

## 4. 빌드 결과 읽기

`scripts/jenkins_wait.py <job> <번호> [--compare <비교 빌드>] [--log <저장 경로>]`
- 빌드가 끝날 때까지 30초 간격으로 기다리고 콘솔 로그를 저장한다.
- 요약: 결과, 소요 시간, 생성기 `INF000004: n Error(s) and m Warning(s)`, `Rte Validation Finished. n errors, m warnings`, SAFERTE_ERR/WARN 종류별 건수, 산출물(`Making binary(...)`, `[PostPackage] Built artifact`).
- `--compare`: 직전 회차에서 **전체 재생성이 일어난 빌드**(Rebuild 또는 패치 커밋 빌드)와 비교. 증분 빌드(Generate 로그 없음)와 비교하면 의미가 없다.
- 오래 걸리면 Bash `run_in_background` 로 돌리고 완료 알림을 기다린다(폴링 sleep 금지).

## 5. 커밋 시 주의

- 사람 커밋에는 Generated·Debug·.log 를 넣지 않는다(Jenkins 가 넣는다). 패치 커밋 본문에 "Generated 는 빌드로 재생성"이라고 적어도 좋다.
- `.gitignore` 와 실제 폴더 대소문자가 달라 의도치 않은 폴더가 들어간 적이 있다(`Workspace` vs `workspace`) — Auto commit 의 파일 목록을 가끔 본다.
- 큰 바이너리(보고서 xlsx, .dla 등)가 커밋에 들어간다. LFS 없음. 결과 압축은 Redmine 첨부로 두고 저장소에는 프로필이 정한 결과 폴더만.
- 커밋 메시지 끝에 프로젝트 관례상 필요한 태그(일감 번호, end #nnnn 등)는 프로필을 따른다.
