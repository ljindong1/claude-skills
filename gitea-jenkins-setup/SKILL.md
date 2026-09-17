---
name: gitea-jenkins-setup
description: 사내 Gitea 저장소를 Fork해 Jenkins 자동 빌드 환경을 처음 구축하는 스킬 — Fork → build 계정 공동작업자(쓰기) → Clone·devel_ 작업 브랜치 생성 → 표준 배치 파일(Build_Hook_GIT_ASEC.bat, GitPush.bat) 추가·push → Jenkins Job 생성(비활성)·검증까지 한 번에 진행한다. 사용자가 "젠킨스 빌드 환경 만들어줘", "새 과제 젠킨스 설정", "Gitea 포크하고 Job 만들어줘", "빌드 자동화 세팅", "Jenkins Job 생성", "fork부터 젠킨스까지", "새 제어기 빌드 서버 등록", "랩원 젠킨스 환경 구축", "gitea jenkins setup" 등을 말하거나, AUTOSAR 제어기 저장소를 Jenkins 빌드에 처음 연결하려는 의도를 보이면 반드시 이 스킬을 사용하라. Claude Code CLI(사용자 PC, 사내망) 전용이며, API 토큰(GITEA_TOKEN·JENKINS_TOKEN)이 있으면 API로, 없으면 Claude in Chrome 연동으로 진행한다. 생성만 하고 기존 저장소·브랜치·파일·Job은 절대 수정·삭제하지 않는다. 첫 빌드 실행·패치 작업·PR 생성은 범위가 아니다.
---

# gitea-jenkins-setup

사내 Gitea(`ccm.mobaseelec.com:3000`)의 제어기 저장소를 Fork하고, Jenkins(`wiki.mobaseelec.com:5151`)에 자동 빌드 Job을 만들어 **"작업 브랜치에 push하면 Jenkins가 빌드하고 결과물을 같은 브랜치에 커밋"**하는 환경을 구축한다.

HE1I PSU 과제(2026-09)에서 사람이 수작업으로 진행하며 겪은 실수(제외 필터 앞 공백·`(?s)` 누락으로 인한 연속 빌드, bat 줄바꿈 깨짐, 권한 누락)를 없애는 것이 목적이다. 값은 skill이 직접 넣고, 넣은 뒤 다시 읽어 확인한다.

## 절대 규칙

1. **Claude Code CLI 전용.** 사용자 PC에서 실행 중이 아니면(웹·Cowork 샌드박스) 사내 주소에 닿지 않는다. 그 경우 "Claude Code CLI에서 실행해 달라"고 안내하고 멈춘다.
2. **생성만 한다. 수정·삭제는 하지 않는다.**
   - 이미 있고 기대와 같으면 → 재사용하고 다음 단계로 (`status: exists`)
   - 이미 있는데 기대와 다르면 → 건드리지 않고 사용자에게 보고, 해당 단계에서 멈춤 (`status: conflict`)
   - 예외: skill이 이번 실행에서 **방금 만든 것**의 초기값 조정(Chrome 모드에서 방금 추가한 공동작업자 권한을 쓰기로)은 허용
3. **생성 단계마다 확인을 받지 않는다.** 입력을 모두 받은 뒤 **요약 1회 확인** 후 끝까지 진행한다. 단, Job **활성화**는 첫 빌드가 바로 시작되므로 마지막에 따로 묻는다.
4. **토큰은 출력하지 않는다.** 환경변수 값을 echo·print하지 않고, 존재 여부만 확인한다.
5. **남의 자원은 읽기만.** 원본 저장소, 다른 사람의 Job(인증정보 ID를 읽는 참고 Job 포함)은 GET만 한다.

## 도구

- `scripts/gjsetup.py` — 모든 API·git 작업. 명령마다 JSON 한 개를 출력한다 (`ok`, `status`, `message`, 추가 필드).
  실행: `python "<이 SKILL.md가 있는 폴더>\scripts\gjsetup.py" <명령> [옵션]`
- `assets/` — 표준 bat 2개(CRLF·ASCII, 수정 금지), Job XML 템플릿
- `references/token_guide.md` — 토큰 발급·등록 (토큰이 없을 때 사용자에게 안내)
- `references/chrome_mode.md` — 토큰이 없는 시스템을 Chrome으로 처리하는 절차
- `references/troubleshooting.md` — 실패·conflict 대응

## 실행 위치

- **권장: Claude Code를 저장소를 받을 상위 폴더에서 실행한다** (예: `D:\Mobase`에서 `claude`). 그러면 입력 없이 그 폴더가 기본값이 되고, Claude Code가 작업 폴더 밖 파일 접근을 매번 허락받는 일도 줄어든다.
- 다른 곳에서 실행했어도 된다. 폴더를 입력받으면 모든 명령이 **절대경로**로 동작하므로 CLI 위치와 무관하다. `cd`로 이동하지 않는다.
- 입력은 **상위 폴더**(`D:\Mobase`)와 **저장소 폴더**(`D:\Mobase\psu_master`) 모두 받는다. 폴더 이름이 저장소 이름과 같으면 저장소 폴더로, 아니면 상위 폴더로 해석한다(`resolve-path`).

## 전체 흐름

```
0 사전 점검(API/Chrome 모드 결정) → 입력 수집 → 요약 확인 1회
→ 1 Fork → 2 공동작업자 → 3 Clone·작업 브랜치 → 4 표준 bat → 5 Job 생성(비활성) → 6 검증·보고
→ (선택) Job 활성화
```

---

## 0. 사전 점검

```
python gjsetup.py preflight
```

결과의 `mode`로 시스템별 진행 방식을 정한다.

| 결과 | 진행 |
| --- | --- |
| `git: false` | git 설치 안내 후 **중단** |
| `git_identity`의 `user.name`/`user.email`이 false | **중단하지 않는다.** 4단계 커밋은 `--commit-name`/`--email`을 그 커밋에만 적용하므로 진행에 지장이 없다. 다만 사용자가 앞으로 이 PC에서 직접 커밋할 때 걸리므로 보고에 한 줄 남긴다 |
| `mode.gitea = api`, `mode.jenkins = api` | API 모드 |
| 한쪽 또는 둘 다 `chrome` | 사용자에게 알린다: "토큰이 없어 ○○는 Chrome 연동으로 진행합니다. 토큰을 등록하면 더 빠르고 정확합니다(`references/token_guide.md`)." 그다음 Chrome 도구(`mcp__claude-in-chrome__*`) 사용 가능 여부를 확인한다 |
| Chrome 모드가 필요한데 Chrome 도구도 없음 | 토큰 발급·등록 방법(`token_guide.md`)과 Chrome 연동(`/chrome`) 방법을 안내하고 **중단** |
| 토큰은 있는데 `http` 401/403/-1 | `hint`를 보여주고 토큰 재발급 안내 후 **중단** (Chrome으로 우회하지 않는다 — 토큰 문제를 먼저 해결) |

Chrome 모드 시스템의 모든 단계는 `references/chrome_mode.md`의 해당 절을 따른다. 로컬 git 단계(3·4)와 `detect-project`·`render-job`은 모드와 무관하게 스크립트로 한다.

## 입력 수집

사용자에게 **묶음 단위로** 묻는다. 자동으로 알 수 있는 값은 먼저 조회해 **제안값**으로 보여주고 확인만 받는다. 이미 대화에 나온 값은 다시 묻지 않는다.

### A. 저장소

| 항목 | 받는 방법 |
| --- | --- |
| 원본 저장소 `owner/repo` | 사용자 입력 (URL을 주면 `owner/repo`로 변환) |
| 조회 | `repo-info --repo owner/repo` → 기본 브랜치, 브랜치 목록, 서브모듈, 본인 계정 동명 저장소 여부 |
| 기준 브랜치 | 브랜치 목록에서 선택 (기본값: 기본 브랜치) |
| Fork 방식 | 개인 Fork(기본, 소유자 = 로그인 ID) / 랩 공용 Fork(조직 이름 입력) |
| 추가 공동작업자 | 선택. 랩원 Gitea ID 목록 (없으면 `build`만) |

원본이 404면 권한 문제일 수 있다 — `troubleshooting.md` 참고 후 사용자에게 확인.

### B. 로컬 · 브랜치

| 항목 | 받는 방법 |
| --- | --- |
| 로컬 폴더 | 아래 "로컬 폴더 확인" 절차로 **실행 폴더를 기본값으로 보여주고 선택**받는다 |
| 개발 단계 | 사용자 입력 (예: `LP2`) |
| 작업 주제 | 사용자 입력 (예: `R44_DeliveryPatch`). 공백은 `_`로 바꿔 제안 |
| 작업 브랜치 | 제안: `devel_<단계>_<로그인ID>_<작업주제>` |
| 프로젝트 폴더 | Clone 후 `detect-project`로 찾아 제안 (예: `psu_app`). 후보가 여럿이면 선택. 입력 수집 시점에는 "Clone 후 자동 확인"으로 둔다 |

#### 로컬 폴더 확인

A 묶음(원본 저장소)이 정해지면 바로 진행한다.

1. `resolve-path --repo <owner/repo>`를 **경로 없이** 실행해 현재 CLI 폴더 기준 값을 얻는다.
2. 아래 형식으로 보여주고 두 가지 중 고르게 한다 (Claude Code의 선택형 질문 도구가 있으면 그것을 쓴다).

```
저장소를 받을 위치
  현재 실행 폴더 : D:\Mobase
  받을 경로      : D:\Mobase\psu_master   (새로 받음 | 이미 받아져 있어 재사용)

  1) 여기로 진행
  2) 다른 폴더 입력
```

3. `2`를 고르면 폴더를 입력받아 `resolve-path --repo <owner/repo> --path <입력>`으로 다시 계산하고, **같은 형식으로 다시 보여준 뒤** 1)/2)를 묻는다. 상위 폴더·저장소 폴더 어느 쪽을 입력해도 된다.
4. 값에 따라 처리한다.

| `target_state` / `warnings` | 처리 |
| --- | --- |
| `new` | "새로 받음"으로 표시하고 진행 |
| `same_repo` | "이미 받아져 있어 재사용"으로 표시하고 진행 |
| `other_repo` / `not_empty` | 1) 선택지를 빼고 "이 폴더에는 다른 내용이 있어 사용할 수 없습니다"라며 다른 폴더를 입력받는다 |
| `warnings`(한글·공백) | 경고를 함께 보여주고, 그래도 1)을 고르면 진행 |

확정된 `target` 절대경로를 이후 모든 명령에 쓴다.

### C. Jenkins

| 항목 | 받는 방법 |
| --- | --- |
| 차종 · 제어기 | 사용자 입력 (예: `HE1I`, `PSU`) |
| Job 이름 | 제안: `<차종>_<제어기>_AUTOSAR_<로그인ID>` (대문자 차종·제어기) |
| 조회 | `job-info --name <Job> --ref-job <참고 Job>` → Job 존재, 뷰 목록, 인증정보 ID 후보 |
| 뷰 | 뷰 목록에서 선택 (예: `PSU`), 없으면 뷰 없이 생성 |
| 참고 Job (인증정보 ID용) | 기본 `ASEC_BJ1_PSU`. 읽기만 한다. 후보가 1개면 그 값, 여럿·0개면 사용자에게 확인. 사내 `build` 계정 인증정보 ID 확인값: `4c818a67-cf87-405f-a290-c24aae743ac9` (2026-09 기준) |
| 커밋 작성자 | 이름 제안: 로그인 ID. 이메일: 사용자 입력. **영문·숫자·기호만**(한글은 Jenkins 콘솔에서 깨짐) |
| Job 설명 | 제안: `<차종> <제어기> <단계> <작업주제> - <로그인ID> Fork 빌드` |

Job이 이미 있으면(`exists: true`) 입력 단계에서 알리고, 이름을 바꿀지 사용자에게 묻는다(기존 Job은 수정하지 않는다).

### 요약 확인 (1회)

아래 형식으로 보여주고 "이대로 진행할까요?" 한 번만 묻는다. 확인 후에는 6단계까지 멈추지 않는다(conflict·오류 제외).

```
원본 저장소     tglee/psu_master (기준 브랜치 develop)
Fork           jdlee/psu_master (개인)
공동작업자      build(쓰기) [+ 추가 인원]
로컬 경로       D:\Mobase\psu_master (CLI 위치: <cwd>)
작업 브랜치     devel_LP2_jdlee_R44_DeliveryPatch
커밋 작성자     jdlee / jdlee@…
Jenkins Job    HE1I_PSU_AUTOSAR_jdlee (뷰 PSU, 비활성 생성)
진행 방식       Gitea: API|Chrome, Jenkins: API|Chrome
```

---

## 1. Fork

```
python gjsetup.py fork --repo <원본 owner/repo> [--org <조직>]
```

- `created` / `exists` → 다음 단계
- `conflict` → 사용자에게 보고하고 중단
- Fork 대상 주소는 이후 `<GITEA_URL>/<소유자>/<repo>.git`

## 2. 공동작업자

```
python gjsetup.py collab --repo <소유자>/<repo> --user build --perm write
```

추가 인원도 같은 명령을 사람마다 실행한다 (`--perm write`). `conflict`(이미 읽기 권한)는 보고만 하고 계속 진행하되, `build`가 conflict면 결과물 push가 실패하므로 **중단**하고 사용자에게 권한 변경을 요청한다.

## 3. Clone · 작업 브랜치

```
python gjsetup.py clone --repo <소유자>/<repo> --dest <resolve-path의 target> [--gitea-url <URL>]
python gjsetup.py branch --path <target> --base <기준 브랜치> --name <작업 브랜치>
python gjsetup.py detect-project --path <target>
```

- **순서를 지킨다: `branch`가 `detect-project`보다 먼저다.** `clone`은 기준 브랜치가 아니라 저장소 **기본 브랜치**를 받는다(기준 브랜치는 `branch`가 `origin/<기준 브랜치>`에서 새 브랜치를 만들 때 쓴다). `detect-project`는 현재 체크아웃된 트리를 훑으므로, 기본 브랜치가 비어 있는 저장소(예: `main`에 README만 있는 `psu_fbl_master`)에서 `branch`보다 먼저 돌면 `not_found`가 난다.
- 이후 모든 명령의 `--path`에는 `resolve-path`가 돌려준 **`target` 절대경로**를 그대로 쓴다.
- `clone`의 `warnings`에 서브모듈 실패가 있으면 사용자에게 알린다. 빌드에 필요한지는 `troubleshooting.md` 로컬 git 표를 따라 판단해 보고한다(중단하지 않는다).
- `detect-project` 후보에서 프로젝트 폴더를 확정한다. 후보가 1개면 그대로, 여럿이면 사용자에게 고르게 한다.
  - `has_hook_std`/`has_gitpush`가 true면 4단계에서 기존 파일과 비교된다.
  - `other_hooks`(예: `Build_Hook.bat`)는 기존 파일이다. **건드리지 않는다.**
- Chrome 모드(토큰 없음)에서는 `--gitea-url`을 지정하고, git이 자격 증명을 물으면 사용자가 로그인하도록 안내한다.

## 4. 표준 배치 파일

```
python gjsetup.py add-bat --path <target> --project <프로젝트 폴더> --name <작업 브랜치> --commit-name <이름> --email <이메일>
```

- `assets`의 bat 2개를 `<프로젝트 폴더>\Build\`에 **바이트 그대로**(CRLF) 복사하고 `GitPush.bat`의 `[USER]` 2줄만 채운 뒤, 두 파일만 커밋·push한다.
- 기존 `Build.bat`, `Build_Hook.bat`, `Build_all.bat` 등은 건드리지 않는다. 다른 개발자와 공유하는 파일이라 PR로 원본에 들어가면 남의 빌드가 바뀌기 때문이다.
- `conflict`(같은 이름, 다른 내용) → 덮어쓰지 않고 보고 후 중단.
- bat 파일을 직접 편집하지 않는다. `sed` 등은 CRLF를 LF로 바꿔 bat 동작이 깨질 수 있다.

## 5. Jenkins Job 생성 (비활성)

```
python gjsetup.py render-job --name <Job> --repo-url <GITEA_URL>/<소유자>/<repo>.git --branch-spec "*/devel_<단계>_<로그인ID>_*" --project <프로젝트 폴더> --user <Jenkins ID> --cred-id <인증정보 ID> --description "<설명>" --out <임시폴더>\<Job>.xml
python gjsetup.py job-create --name <Job> --xml <임시폴더>\<Job>.xml [--view <뷰>]
```

템플릿이 넣는 값 (모두 HE1I PSU 첫 적용에서 동작 확인):

| 항목 | 값 | 이유 |
| --- | --- | --- |
| 상태 | **비활성** | 생성 즉시 Poll SCM이 첫 빌드를 시작하지 않도록 |
| 권한 | 본인: Job Build·Cancel·Configure·Read·Workspace, Run Delete·Update | 본인이 빌드·설정 가능 |
| 매개변수 `BuildType` | Hook(기본)·Build·Compile·GenerateAll·Rebuild·Clean | 첫 줄이 기본값, 자동 빌드는 커밋 메시지로 동작 결정 |
| Repository URL · Credentials | Fork 주소 · `build` 인증정보 | |
| Branch Specifier | `*/devel_<단계>_<ID>_*` | 같은 사람의 작업 브랜치를 한 Job으로. `GitPush.bat`이 브랜치를 자동으로 따라감 |
| 제외 메시지 필터 | `(?s).*Auto commit from Jenkins.*` | 결과물 커밋에 반응한 연속 빌드 방지. `(?s)`는 메시지 끝 줄바꿈 대응 |
| Poll SCM | `* * * * *` | push 후 1분 안에 빌드 |
| 빌드 명령 | `<프로젝트 폴더>\Build\Build_Hook_GIT_ASEC.bat %BuildType% -j8` | |
| 서브모듈 · 빌드 후 조치 · 동시 빌드 | 없음 · 없음 · 끔 | |

`job-create` 결과가 `conflict`면 기존 Job은 수정하지 않고 중단한다. HTTP 오류는 `detail`을 보여주고 `troubleshooting.md` Jenkins 표를 따른다.

## 6. 검증 · 보고

```
python gjsetup.py repo-info --repo <원본 owner/repo>          # my_repo_same_name이 Fork로 보이는지
python gjsetup.py collab --repo <소유자>/<repo> --user build   # exists / write
python gjsetup.py job-verify --name <Job> --repo-url <…> --branch-spec "<…>" --project <…> --user <Jenkins ID>
```

`job-verify`의 `checks`가 모두 true여야 한다. 특히 `exclusion_exact`(필터가 정확히 일치, 공백 없음). false 항목이 있으면 **수정하지 않고** 사용자에게 보고한다(skill이 방금 만든 Job이므로 원인은 템플릿·플러그인 형식 차이일 가능성이 크다).

### 최종 보고 형식

```
## Jenkins 빌드 환경 구축 결과

| 단계 | 결과 | 내용 |
| --- | --- | --- |
| 1. Fork | ✅ 생성 / ♻️ 재사용 / ⛔ 충돌 | <소유자>/<repo> |
| 2. 공동작업자 | … | build 쓰기 [+ 인원] |
| 3. Clone·브랜치 | … | <로컬 경로>, <작업 브랜치> (<커밋>) |
| 4. 표준 bat | … | <프로젝트>\Build\ 2개, 커밋 <해시> |
| 5. Job | … | <Job> (뷰 <뷰>, 비활성) |
| 6. 검증 | ✅ 8/8 | 필터·URL·브랜치·명령·권한·매개변수 |

경고: <서브모듈 실패 등>
Jenkins: <JENKINS_URL>/job/<Job>/
```

## 활성화 (마지막 질문)

보고 후 한 번 묻는다: "Job을 활성화할까요? 활성화하면 1분 안에 첫 빌드가 자동으로 시작되고 약 10~15분 걸립니다."

- 예 → `python gjsetup.py job-enable --name <Job>` 후, 첫 빌드 확인 방법만 안내한다(이 skill은 빌드 결과 판정을 하지 않는다):
  - Console Output에서 `[HOOK] Build/Git Push/Final ERROR LEVEL : 0` → `Finished: SUCCESS`
  - 빌드 종료 후 2~3분 동안 결과물 커밋에 반응한 추가 빌드가 **생기지 않는지**
  - 결과물 받기: 로컬에서 `git pull`
- 아니오 → Job 화면의 `프로젝트 활성화` 버튼으로 나중에 켤 수 있다고 안내한다.

## 범위 밖

첫 빌드 결과 판정, 패치 작업·커밋, 원본 동기화(upstream merge), PR 생성, 기존 Job·저장소 설정 변경은 하지 않는다. 요청받으면 이 skill의 범위가 아님을 알리고 필요한 절차만 안내한다.
