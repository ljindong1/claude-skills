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

## 3-1. 생성 경로 — 어디서 무엇이 생성되나

| 경로 | 생성 범위 | 필요한 도구 |
|---|---|---|
| C Studio **Generate Code**(도구 모음 톱니바퀴) / .arxml 오른쪽 클릭 **Generation** | **BSW·Os·Rte 만** → `Generated/Bsw_Output` (`Build/input_files.yml` 의 모듈 목록. MCAL 없음) | Python 2.7 + SCons(입력 파일 생성), mobilgene 생성기 본체(gentool-fw), Rte 생성기. 컴파일러 불필요 |
| **Jenkins 빌드**(build.bat → SCons) / C Studio Build(망치) | BSW·Os·Rte **+ MCAL**(Can·Mcu·Gpt·Port·Dio·Spi·Wdg → `Generated/Mcal_Output`, EB tresos) + 컴파일 | 위 도구 + EB tresos(모듈별 라이선스 검사) + 컴파일러 |
| C Studio **Generate ECU Configuration**(Harmonize) | 코드가 아니라 **Ecud 설정(arxml)** | C Studio 만 |

- 도구 경로는 `Build.bat`·`bat_package/*.bat`·`SCons.arxml` 에 `D:\ts_mirr\...` 로 고정돼 있다. 이 폴더가 없는 PC 에서 Generate Code 를 누르면 "Failed to create input files" / `Cannot run program ...python.exe` 로 멈춘다(파일 변경 없음).
- 그래서 **MCAL 설정을 바꾼 패치의 생성 결과는 Jenkins 에서만** 볼 수 있다. BSW·Rte 만 바꿨으면 도구를 갖춘 PC 의 C Studio 로 push 전에 미리 볼 수 있다. 어느 경우든 로컬 생성은 시험 브랜치에서 하고 되돌린다(`Generated/` 는 git 추적).
- 프로젝트의 PC 별 도구 보유 상황은 프로필 "구성 전제"에 적는다.

### 3-2. 로컬 빌드 도구 확보 (필요할 때만)

기본 방침: **설치하지 않는다.** 직접 편집 → push → Jenkins 결과 확인으로 충분하다. push 전 로컬 빌드가 자주 필요해질 때만 확보하고, 그때도 하나씩 설치하지 말고 **팀·Jenkins 서버의 `D:\ts_mirr` 세트를 같은 하위 구조 그대로 복사**한다(경로가 Build.bat·SCons.arxml 에 고정돼 있음).

| 도구 | 출처 | 비고 |
|---|---|---|
| Portable Python 2.7.17 x64, SCons-local 2.3.4 | HAE 미배포 — 외부 다운로드 링크 CPINFO-2090. 설치판 `Setup.zip`(+z01) CPINFO-2059 | 설치판은 PYTHON_HOME·SCONS_HOME 환경변수를 등록한다. 쓰려면 Build.bat 을 `IF "%PYTHON_HOME%"=="" set PYTHON_HOME=…` 형태로 바꿔야 인식(현재 Build.bat 은 IF 없이 고정) |
| gentool-fw, Rte 생성기, JRE 1.8.0_121 | CPINFO-2089(GenTool), ECM SW generator 게시판, ECM `[C Studio][R4X] 초기 개발환경 설정`(pageId 202543574, JRE 첨부) | `ts_mirr\xml` 아래 |
| GHS 컴파일러 | 사내 보유 라이선스 | `ts_mirr\gh\ARM.V2017.1.4` |
| EB tresos (MCAL 생성기) | **HAE 제공 불가**(정책, MCP0806-279 안내) → 팀 내부·Infineon. ECM 가이드상 빌드 확인용 임시 generator 는 배포 담당자에게 요청 가능 | 없으면 Build·GenerateAll 이 MCAL 생성에서 멈춤 → **부분 설치는 의미가 적다** |

- `build.pyc` 헤더 `03 f3 0d 0a` = Python 2.7 컴파일물 → toolset 2.x 는 2.7 이 반드시 필요하다.
- **toolset_scons 3.0.1 이상**은 Python 3.12.10 + SCons 4.10.0 가상환경(`MOBILGENE_PYTHON\.venv`, Build.bat 이 최초 1회 자동 설치)으로 바뀐다 — Python 2.7·SCons-local 불필요. 3.x 로 올리는 패치가 오면 `.pyc` 가 빠지고 기존 `site_scons` 를 지우고 새것으로 교체한다(MCP1001-193 [15][17], ECM `[KR] toolset_scons 사용자 매뉴얼` pageId 371172222 §3.1.2·§3.2.2).
- Compile 만 할 때(기존 `Generated/` 사용)는 EB tresos 가 필요 없다. `Generated/Mcal_Output` 은 Jenkins 가 빌드마다 재생성해 커밋한다.

## 4. 빌드 결과 읽기

`scripts/jenkins_wait.py <job> <번호> [--compare <비교 빌드>] [--log <저장 경로>]`
- 빌드가 끝날 때까지 30초 간격으로 기다리고 콘솔 로그를 저장한다.
- 요약: 결과, 소요 시간, 생성기 `INF000004: n Error(s) and m Warning(s)`, `Rte Validation Finished. n errors, m warnings`, SAFERTE_ERR/WARN 종류별 건수, 산출물(`Making binary(...)`, `[PostPackage] Built artifact`).
- `--compare`: 직전 회차에서 **전체 재생성이 일어난 빌드**(Rebuild 또는 패치 커밋 빌드)와 비교. 증분 빌드(Generate 로그 없음)와 비교하면 의미가 없다.
- 오래 걸리면 Bash `run_in_background` 로 돌리고 완료 알림을 기다린다(폴링 sleep 금지).

## 5. 커밋 시 주의

- 사람 커밋에는 Generated·Debug·.log 를 넣지 않는다(Jenkins 가 넣는다). 패치 커밋 본문에 "Generated 는 빌드로 재생성"이라고 적어도 좋다.
- **예외 — 남은 생성물 삭제.** SCons 는 `Generated/Bsw_Output` 에 있는 `.c` 를 모듈 생성 목록에 없어도 컴파일한다(로그 `More generated file "…" found for compile`). 모듈 생성을 끄거나(SCons Generation Used false) BswInstance 를 지우면 그 모듈 생성기가 돌지 않아 **이전 생성물이 남는다**(`<모듈>_Cfg.c/.h`, Rte 가 만든 `SchM_<모듈>*.h`, PduR 의 `PduR_<모듈>.h` 등). 모듈 소스를 ExcludeList 로 뺐으면 헤더를 못 찾아 컴파일이 실패한다. 이때는 사람이 그 생성물을 `git rm` 하는 커밋을 한다(#48891 #18 실패 → `3e94476b` → #19 성공).
  - HAE patch_tool 은 GenerateAll 직전에 `Generated/`·`Debug/` 를 통째로 지워서 이 문제가 없다(build_executor). Jenkins Build·Hook 은 지우지 않는다.
  - 찾는 법: 빌드 작업 폴더(`<JENKINS_URL>/job/<Job>/ws/<앱>/Generated/Bsw_Output/src/*zip*/src.zip`)의 파일 날짜가 이번 빌드보다 오래된 것. 그중 다른 도구가 만드는 것(Os·Crypto·HwResource 등 이번에 생성하지 않은 모듈)은 정상이다. 사전에는 `review_all.py` 의 남은 생성물 점검을 쓴다.
  - 지우기 전에 남은 파일을 include 하는 곳이 새 생성물에 없는지 확인한다(작업 폴더 생성물 grep).
- `.gitignore` 와 실제 폴더 대소문자가 달라 의도치 않은 폴더가 들어간 적이 있다(`Workspace` vs `workspace`) — Auto commit 의 파일 목록을 가끔 본다.
- 큰 바이너리(보고서 xlsx, .dla 등)가 커밋에 들어간다. LFS 없음. 결과 압축은 Redmine 첨부로 두고 저장소에는 프로필이 정한 결과 폴더만.
- 커밋 메시지 끝에 프로젝트 관례상 필요한 태그(일감 번호, end #nnnn 등)는 프로필을 따른다.
