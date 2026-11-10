---
name: gitea-jenkins-setup
description: 사내 Gitea 저장소로 Jenkins 자동 빌드 환경을 구축하는 스킬. 모드 A(처음 구축) — Fork → build 계정 공동작업자(쓰기) → Clone·devel_ 작업 브랜치 생성 → 표준 배치 파일(Build_Hook_GIT_ASEC.bat, GitPush.bat) 추가·push → Jenkins Job 생성(비활성)·검증까지 한 번에 진행한다. 모드 B(브랜치 추가) — 이미 Fork된 내 저장소의 아무 브랜치(develop_*·feature/* 등)를 기준으로 devel_ 작업 브랜치를 새로 만들고 bat을 넣은 뒤, 그 브랜치를 이미 받아주는 Job이 있으면 재사용하고 없을 때만 새로 만든다. 모드 C(공유 Fork 직접 작업) — 다른 사람의 Fork(예: tglee/psu_master)에 내가 쓰기 권한이 있으면 개인 Fork 없이 그 저장소에서 바로 clone·작업 브랜치·bat·Job 을 진행한다. 모드 D(PR 구성) — 작업이 끝난 devel_ 작업 브랜치에서 Jenkins 자동 커밋·빌드 스크립트·JENKINS_BUILD_TARGET·중간 산출물을 걸러 PR 브랜치를 새로 만들고(평가한 빌드의 산출물 기준, 다른 차종 산출물 유지), 검증 후 승인을 받아 push·Gitea PR 생성·PR 제목/본문 수정까지 한다(references/pr_assembly.md). 개인 Fork 를 공유 Fork 로 옮기고 개인 Fork 를 없애는 이전 절차(references/migrate_to_shared_fork.md)는 사용자가 명시적으로 요청할 때만 쓴다. 사용자가 "젠킨스 빌드 환경 만들어줘", "새 과제 젠킨스 설정", "Gitea 포크하고 Job 만들어줘", "빌드 자동화 세팅", "Jenkins Job 생성", "fork부터 젠킨스까지", "새 제어기 빌드 서버 등록", "랩원 젠킨스 환경 구축", "gitea jenkins setup", "이미 포크한 저장소에 브랜치 추가해줘", "devel_ 브랜치 새로 만들어줘", "이 브랜치로 작업 브랜치 만들어줘", "빌드용 브랜치 추가", "tglee 저장소에서 바로 작업", "jdlee fork 없애줘", "개인 fork 제거", "공유 fork 로 옮겨줘", "PR 만들어줘", "PR 브랜치 만들어줘", "PR 진행해줘", "작업 브랜치 PR", "PR 어떻게 할지", "PR 제목 고쳐줘" 등을 말하거나, AUTOSAR 제어기 저장소를 Jenkins 빌드에 처음 연결하려는 의도나 devel_ 작업 브랜치 결과를 PR 로 올리려는 의도를 보이면 반드시 이 스킬을 사용하라. Claude Code CLI(사용자 PC, 사내망) 전용이며, API 토큰(GITEA_TOKEN·JENKINS_TOKEN)이 있으면 API로, 없으면 Claude in Chrome 연동으로 진행한다. 생성만 하고 기존 저장소·브랜치·파일·Job은 수정·삭제하지 않는다(사용자가 요청한 이전 절차와 이 스킬이 만든 PR 의 제목·본문 수정만 예외). 첫 빌드 실행·패치 작업·PR 머지·Redmine 기록은 범위가 아니다.
---

# gitea-jenkins-setup

사내 Gitea(`ccm.mobaseelec.com:3000`)의 제어기 저장소를 Fork하거나(쓰기 권한이 있는 공유 Fork면 그대로 쓰고), Jenkins(`wiki.mobaseelec.com:5151`)에 자동 빌드 Job을 만들어 **"작업 브랜치에 push하면 Jenkins가 빌드하고 결과물을 같은 브랜치에 커밋"**하는 환경을 구축한다.

HE1I PSU 과제(2026-09)에서 사람이 수작업으로 진행하며 겪은 실수(제외 필터 앞 공백·`(?s)` 누락으로 인한 연속 빌드, bat 줄바꿈 깨짐, 권한 누락)를 없애는 것이 목적이다. 값은 skill이 직접 넣고, 넣은 뒤 다시 읽어 확인한다.

## 절대 규칙

1. **Claude Code CLI 전용.** 사용자 PC에서 실행 중이 아니면(웹·Cowork 샌드박스) 사내 주소에 닿지 않는다. 그 경우 "Claude Code CLI에서 실행해 달라"고 안내하고 멈춘다.
2. **생성만 한다. 수정·삭제는 하지 않는다.**
   - 이미 있고 기대와 같으면 → 재사용하고 다음 단계로 (`status: exists`)
   - 이미 있는데 기대와 다르면 → 건드리지 않고 사용자에게 보고, 해당 단계에서 멈춤 (`status: conflict`)
   - 예외: skill이 이번 실행에서 **방금 만든 것**의 초기값 조정(Chrome 모드에서 방금 추가한 공동작업자 권한을 쓰기로)은 허용
   - 예외: **사용자가 명시적으로 요청한 이전 절차**(`references/migrate_to_shared_fork.md` — 개인 Fork → 공유 Fork, 기존 Job 전환·이름 변경, 개인 Fork 삭제). 계획을 보여 주고 승인받은 뒤에만 하고, Fork 삭제는 실행 직전에 한 번 더 묻는다
   - 예외: 모드 D 에서 **이 스킬이 만든 PR** 의 제목·본문 수정(예: 일감 번호 교체). PR 브랜치 강제 push 는 따로 묻는다
   - 예외: 4단계의 **Jenkins 전용 bat 6개**. 이것은 공유 소스가 아니라 **이 스킬 자신의 산출물**이고 모드 D 가 PR 에서 걸러내므로 원본에 들어가지도 않는다. `devel_*` 작업 브랜치에서 내용이 다르면 **표준본으로 교체**한다(`status: created`, `replaced` 필드). git 이 추적하는 파일일 때만 교체한다 — 원본을 되돌릴 수 있어야 하기 때문이다. 공유 소스(`Build.bat`·`Build_all.bat`·`Build_Hook.bat`·`PJ_Define.h`)는 여전히 손대지 않는다. 사용자가 교체를 원치 않으면 `--no-replace` 로 옛 동작(멈춤)을 쓴다
   - **멈출 때는 원자적으로 멈춘다.** `conflict` 로 끝나면 같은 실행에서 먼저 쓴 파일을 전부 지워 디스크를 원래대로 되돌린다(`rolled_back` 필드). 반쪽 상태를 남기지 않는다
   - **멈출 때는 판단 재료를 함께 낸다.** `details` 에 파일별 `diff`(기존 vs 표준본), `risk`(기존 파일을 두면 실제로 무슨 일이 생기는지), `reason`(왜 교체하지 않았는지)이 들어온다. 이것을 **사용자에게 그대로 보여주고** 한 줄로 답할 수 있게 물어라 — "내용이 다름"만 전하고 멈추지 말 것
3. **생성 단계마다 확인을 받지 않는다.** 입력을 모두 받은 뒤 **요약 1회 확인** 후 끝까지 진행한다. 단, Job **활성화**는 첫 빌드가 바로 시작되므로 마지막에 따로 묻는다. 모드 D 는 PR 브랜치를 로컬에 만들고 검증한 뒤 **push·PR 생성 전에** 한 번 확인받는다.
4. **토큰은 출력하지 않는다.** 환경변수 값을 echo·print하지 않고, 존재 여부만 확인한다.
5. **남의 자원은 읽기만.** 원본 저장소, 다른 사람의 Job(인증정보 ID를 읽는 참고 Job 포함)은 GET만 한다.

## 도구

- `scripts/gjsetup.py` — 모든 API·git 작업. 명령마다 JSON 한 개를 출력한다 (`ok`, `status`, `message`, 추가 필드).
  실행: `python "<이 SKILL.md가 있는 폴더>\scripts\gjsetup.py" <명령> [옵션]`
- `assets/` — 배포용 파일(CRLF·ASCII, 수정 금지: 표준 훅 `Build_Hook_GIT_ASEC.bat`, `GitPush.bat`, `PostPackage.bat`, `BuildVariants.bat`, `PJ_Variant.ps1`), Job XML 템플릿
- `references/token_guide.md` — 토큰 발급·등록 (토큰이 없을 때 사용자에게 안내)
- `references/chrome_mode.md` — 토큰이 없는 시스템을 Chrome으로 처리하는 절차
- `references/troubleshooting.md` — 실패·conflict 대응
- `references/migrate_to_shared_fork.md` — 개인 Fork → 공유 Fork 이전 (요청 시에만)
- `references/pr_assembly.md` — 모드 D: PR 브랜치 구성(넣을 것·뺄 것), 명령 골격, 검증, push·PR 생성, 함정

## 실행 위치

- **권장: Claude Code를 저장소를 받을 상위 폴더에서 실행한다** (예: `D:\Mobase`에서 `claude`). 그러면 입력 없이 그 폴더가 기본값이 되고, Claude Code가 작업 폴더 밖 파일 접근을 매번 허락받는 일도 줄어든다.
- 다른 곳에서 실행했어도 된다. 폴더를 입력받으면 모든 명령이 **절대경로**로 동작하므로 CLI 위치와 무관하다. `cd`로 이동하지 않는다.
- 입력은 **상위 폴더**(`D:\Mobase`)와 **저장소 폴더**(`D:\Mobase\psu_master`) 모두 받는다. 폴더 이름이 저장소 이름과 같으면 저장소 폴더로, 아니면 상위 폴더로 해석한다(`resolve-path`).

## 전체 흐름

구축 모드 A·B·C 는 **입력받은 저장소가 누구의 무엇인지**로 갈린다 (`repo-info`의 `mode` — `owner_is_me`·`is_fork`·`can_push`로 판정). 모드 D(PR 구성)는 구축이 끝난 작업 브랜치의 결과를 올릴 때 쓴다.

```
[모드 A] 처음 구축 — 원본 저장소를 준 경우
0 사전 점검 → 입력 수집 → 요약 확인 1회
→ 1 Fork → 2 공동작업자 → 3 Clone·작업 브랜치 → 4 표준 bat → 5 Job 생성(비활성) → 6 검증·보고
→ (선택) Job 활성화

[모드 B] 브랜치 추가 — 이미 있는 내 Fork를 준 경우
0 사전 점검 → 입력 수집 → 요약 확인 1회
→ 1·2 확인만(Fork·build 권한이 있는지) → 3 Clone(재사용)·작업 브랜치 → 4 표준 bat
→ 5 job-match: 받아주는 Job이 있으면 재사용, 없으면 생성 → 6 검증·보고

[모드 C] 공유 Fork 직접 작업 — 남의 Fork(예: tglee/psu_master)인데 내가 쓰기 권한이 있는 경우
0 사전 점검 → 입력 수집 → 요약 확인 1회
→ 1 Fork 안 함 → 2 build 권한 확인만(--check-only) → 3 Clone·작업 브랜치 → 4 표준 bat
→ 5 job-match: 받아주는 Job이 있으면 재사용, 없으면 생성 → 6 검증·보고

[모드 D] PR 구성 — 작업 브랜치(devel_*) 결과를 PR 로 올릴 때 (references/pr_assembly.md)
기준 커밋·PR 대상·일감 번호·평가 빌드 확인 → 넣을 것/뺄 것 분류 → 임시 인덱스로 PR 브랜치 생성(로컬)
→ 검증(diff 0, 남은 차이 = 뺄 것) → 커밋·대상·본문 미리보기 → 승인 → push · Gitea PR 생성 → 보고
```

모드 D 는 FBL·APP 저장소를 따로 진행한다(FBL 은 squash 1개, APP 는 커밋 여러 개). 일감 번호는 사용자에게 받고, Redmine 기록은 redmine-issue 스킬이 한다.

모드 C 는 `원본 → tglee(공유 Fork) → jdlee(개인 Fork) → clone` 에서 개인 Fork 층을 뺀 구조다. 작업 브랜치와 Jenkins 결과물이 공유 Fork 에 바로 쌓인다. HE1i PSU APP·FBL 이 2026-10 부터 이 구조다. 이미 개인 Fork 로 구축된 과제를 이 구조로 옮기는 것은 별도 절차(`references/migrate_to_shared_fork.md`)이고, 사용자가 요청할 때만 한다.

모드 B는 **새 기능이 아니라 같은 단계의 축약**이다. 1·2·5단계가 대개 `exists`/재사용으로 지나갈 뿐, 실제 작업(3·4)과 검증(6)은 같다.

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
| 저장소 `owner/repo` | 사용자 입력 (URL을 주면 `owner/repo`로 변환). **원본이든 내 Fork든 받는다** |
| 조회 | `repo-info --repo owner/repo` → 기본 브랜치, 브랜치 목록, 서브모듈, `owner_is_me`·`is_fork`·`upstream` |
| **모드 판정** | `repo-info`의 `mode`. 내 Fork → **B**(브랜치 추가) / 남의 Fork + `can_push` → **C**(공유 Fork 직접 작업) / 그 밖(원본 등) → **A**(처음 구축). C 로 판정돼도 사용자가 개인 Fork 를 원하면 A 로 진행한다 |
| 기준 브랜치 | 브랜치 목록에서 선택. **제한하지 않는다** — `develop_*`·`feature/*`·다른 `devel_*` 모두 가능 (기본값: 모드 A는 기본 브랜치, 모드 B는 사용자가 고르게 한다) |
| Fork 방식 | 모드 A만. 개인 Fork(기본, 소유자 = 로그인 ID) / 랩 공용 Fork(조직 이름 입력) |
| 추가 공동작업자 | 모드 A만. 랩원 Gitea ID 목록 (없으면 `build`만) |

모드 B·C에서는 Fork 방식·추가 공동작업자를 **묻지 않는다.** B 는 이미 정해져 있고, C 는 남의 저장소라 공동작업자를 바꾸지 않는다.

원본이 404면 권한 문제일 수 있다 — `troubleshooting.md` 참고 후 사용자에게 확인.

### B. 로컬 · 브랜치

| 항목 | 받는 방법 |
| --- | --- |
| 로컬 폴더 | 아래 "로컬 폴더 확인" 절차로 **실행 폴더를 기본값으로 보여주고 선택**받는다 |
| **차종 코드** | 사용자 입력 (예: `HE1i`). 브랜치 이름과 **전용 훅 파일명**에 쓰인다 |
| 작업 주제 | 사용자 입력 (예: `R44_DeliveryPatch`). 공백은 `_`로 바꿔 제안 |
| 작업 브랜치 | 제안: `devel_<차종>_<로그인ID>_<기준표식>_<작업주제>` |
| 프로젝트 폴더 | Clone 후 `detect-project`로 찾아 제안 (예: `psu_app`). 후보가 여럿이면 선택. 입력 수집 시점에는 "Clone 후 자동 확인"으로 둔다 |

**차종 코드는 브랜치 2번째 칸에 넣고, 전용 훅 이름(`Build_Hook_<차종>.bat`)에도 그대로 쓴다.** 기존 저장소에는 이 자리에 개발 단계(`LP2`)가 들어간 브랜치도 있다. 그런 저장소에 브랜치를 추가할 때는 **브랜치명에서 뽑은 값을 제안하되 차종이 맞는지 반드시 확인받는다** — 훅 이름은 단계가 아니라 차종이어야 한다.

```
차종 코드
  브랜치명에서 추출 : HE1i   →  Build_Hook_HE1I.bat
  이대로 진행할까요? (아니면 차종 코드를 입력)
```

**`<기준표식>`은 기준 브랜치를 이름에 남기기 위한 것이다.** 저장소에 `develop`·`develop_he1i`·`develop_bj1`처럼 비슷한 브랜치가 여럿이면, 브랜치 이름만 보고는 어디서 딴 것인지 알 수 없어 나중에 `git merge-base`로 캐야 한다. 기준 브랜치 이름에서 `develop_` 접두어를 뗀 나머지를 쓴다.

| 기준 브랜치 | `<기준표식>` | 작업 브랜치 예 |
| --- | --- | --- |
| `develop_he1i` | `he1i` | `devel_HE1i_jdlee_he1i_FBL_patch_Update` |
| `develop_bj1` | `bj1` | `devel_BJ1_jdlee_bj1_R44_DeliveryPatch` |
| `develop` | `dev` | `devel_HE1i_jdlee_dev_R44_DeliveryPatch` |
| `main` | `main` | `devel_HE1i_jdlee_main_R44_DeliveryPatch` |

표식은 `<로그인ID>` **뒤**에 온다. Branch Specifier가 `*/devel_<차종>_<ID>_*`로 앞 3칸만 고정하므로 매칭에는 영향이 없다. 사용자가 표식을 빼고 싶어 하면 그대로 따른다 — 강제하지 않는다.

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
| 제어기 | 사용자 입력 (예: `PSU`). 차종은 B 묶음에서 이미 받았다 |
| Job 이름 | 제안: `<차종>_<제어기>_<AUTOSAR\|FBL>_<로그인ID>` — **차종은 입력한 표기 그대로**, 제어기는 대문자 (예: `HE1i_PSU_AUTOSAR_jdlee`, `HE1i_PSU_FBL_jdlee`). 전용 훅 파일명만 대문자(`Build_Hook_HE1I.bat`) |
| 조회 | `job-info --name <Job> --ref-job <참고 Job>` → Job 존재, 뷰 목록, 인증정보 ID 후보 |
| 뷰 | 뷰 목록에서 선택 (예: `PSU`), 없으면 뷰 없이 생성 |
| 참고 Job (인증정보 ID용) | 기본 `ASEC_BJ1_PSU`. 읽기만 한다. 후보가 1개면 그 값, 여럿·0개면 사용자에게 확인. 사내 `build` 계정 인증정보 ID 확인값: `4c818a67-cf87-405f-a290-c24aae743ac9` (2026-09 기준) |
| 커밋 작성자 | 이름 제안: 로그인 ID. 이메일: 사용자 입력. **영문·숫자·기호만**(한글은 Jenkins 콘솔에서 깨짐) |
| Job 설명 | 제안: 모드 A·B `<차종> <제어기> <작업주제> - <로그인ID> Fork 빌드`, 모드 C `<차종> <제어기> <APP\|FBL> - <공유 Fork> 작업 브랜치(devel_<차종>_<ID>_*) 빌드` |

Job이 이미 있으면(`exists: true`) 입력 단계에서 알리고, 이름을 바꿀지 사용자에게 묻는다(기존 Job은 수정하지 않는다). **Jenkins 는 대소문자만 다른 이름을 같은 이름으로 본다**(Windows 서버) — `HE1I_PSU_FBL_jdlee` 가 있으면 `HE1i_PSU_FBL_jdlee` 도 `exists` 로 나온다.

### 요약 확인 (1회)

아래 형식으로 보여주고 "이대로 진행할까요?" 한 번만 묻는다. 확인 후에는 6단계까지 멈추지 않는다(conflict·오류 제외).

모드 A:

```
원본 저장소     tglee/psu_master (기준 브랜치 develop)
Fork           jdlee/psu_master (개인)
공동작업자      build(쓰기) [+ 추가 인원]
로컬 경로       D:\Mobase\psu_master (CLI 위치: <cwd>)
작업 브랜치     devel_HE1i_jdlee_dev_R44_DeliveryPatch
커밋 작성자     jdlee / jdlee@…
Jenkins Job    HE1i_PSU_AUTOSAR_jdlee (뷰 PSU, 비활성 생성)
진행 방식       Gitea: API|Chrome, Jenkins: API|Chrome
```

모드 B — Fork·공동작업자 줄이 "확인"으로 바뀌고, **Job 줄에 재사용/생성이 드러나야 한다**:

```
저장소          jdlee/psu_fbl_master (내 Fork, 원본 tglee/psu_fbl_master)
기준 브랜치     feature/swp_patch_v3.0.17
공동작업자      build(쓰기) — 확인만
로컬 경로       D:\Mobase\psu_fbl_master (이미 받아져 있어 재사용)
작업 브랜치     devel_HE1i_jdlee_swp_v3017   ← 새로 생성
표준 bat        기준 브랜치에 없으면 추가·커밋
Jenkins Job     HE1i_PSU_FBL_jdlee 재사용 (새로 만들지 않음)
진행 방식       Gitea: API, Jenkins: API
```

모드 C:

```
저장소          tglee/psu_fbl_master (공유 Fork, 원본 git/psu_fbl_master, 쓰기 권한 있음)
Fork            만들지 않음
기준 브랜치     develop_he1i
build 권한      write — 확인만 (남의 저장소라 추가하지 않음)
로컬 경로       D:\Mobase\psu_fbl_master (새로 받음)
작업 브랜치     devel_HE1i_jdlee_he1i_FBL_patch_Update   ← tglee 에 생성
Jenkins Job     HE1i_PSU_FBL_jdlee 새로 생성 (뷰 PSU, 비활성)
진행 방식       Gitea: API, Jenkins: API
```

Job이 `no_match`면 그 줄을 `<Job 이름> 새로 생성 (뷰 PSU, 비활성)`으로 바꿔 보여준다. 사용자는 이 화면에서 Job을 만들지 말지까지 함께 확인하는 셈이다.

---

## 1. Fork

```
python gjsetup.py fork --repo <원본 owner/repo> [--org <조직>]
```

- `created` / `exists` → 다음 단계
- `conflict` → 사용자에게 보고하고 중단
- Fork 대상 주소는 이후 `<GITEA_URL>/<소유자>/<repo>.git`

**모드 B·C에서는 이 명령을 실행하지 않는다.** C 는 공유 Fork 를 그대로 쓴다. B 는 입력받은 저장소가 이미 내 Fork임을 `repo-info`로 확인했으므로 `exists`가 자명하다. `fork --repo`는 **원본**을 받는 자리라 Fork 주소를 주면 `conflict`가 난다 — 넘기지 않는다.

## 2. 공동작업자

```
python gjsetup.py collab --repo <소유자>/<repo> --user build --perm write
```

추가 인원도 같은 명령을 사람마다 실행한다 (`--perm write`). `conflict`(이미 읽기 권한)는 보고만 하고 계속 진행하되, `build`가 conflict면 결과물 push가 실패하므로 **중단**하고 사용자에게 권한 변경을 요청한다.

**모드 B에서도 이 명령은 실행한다.** 이미 있으면 `exists`로 지나가고, 빠져 있으면 그때 붙는다 — 결과물 push 권한은 브랜치를 추가할 때마다 확인할 값어치가 있다.

**모드 C에서는 `--check-only`를 붙인다.** 남의 저장소라 공동작업자를 추가하지 않고 권한만 본다. `missing`이면 결과물 push 가 실패하므로 **중단**하고, 저장소 소유자에게 build 쓰기 권한을 요청하도록 안내한다.

```
python gjsetup.py collab --repo tglee/<repo> --user build --check-only
```

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
python gjsetup.py add-bat --path <target> --project <프로젝트 폴더> --name <작업 브랜치> --model <차종> --commit-name <이름> --email <이메일>
```

`<프로젝트 폴더>\Build\`에 **6개**를 넣고 한 번에 커밋·push한다.

| 파일 | 출처 | 역할 |
| --- | --- | --- |
| `Build_Hook_GIT_ASEC.bat` | `assets` 바이트 그대로 | 랩 표준 훅. **수정하지 않는다.** 전용 훅이 없는 브랜치를 위한 fallback |
| `GitPush.bat` | `assets` + `[USER]` 2줄 치환 | 빌드 결과물 자동 커밋·push |
| `Build_Hook_<차종>.bat` | 표준 훅에서 생성 | ⭐ **Job이 실제로 부르는 훅.** 표준 훅 + **서브모듈 체크아웃 블록(0단계)** + `PostPackage` 호출 블록 + `ALL` 분기·push 블록 |
| `PostPackage.bat` | `assets` 바이트 그대로 | `Build_all.bat`의 `[Post-build] Archiving` 블록 기반. APP는 **버전별 폴더** `Debug\OEUK_xxxx\<버전>\`에 차종명 산출물(`_Writing.s19` 등)과 `rom_<버전>\`(aSIMS 서명 입력) 생성. `OEUK_TEST` 빌드는 기준 OEUK 폴더의 `<기준 버전>_test\`(같은 레벨)로, rom 패키지도 `rom_<기준 버전>_test\`·`.zip`으로 만든다. FBL은 **평면 폴더** `Debug\OEUK_HE1I\`·`Debug\OEUK_HE1I_TEST\`(APP 저장소 `02_Fbl_Binary\`와 같은 이름). `.s19`가 없으면(FBL) `rom` 패키징 생략 |
| `BuildVariants.bat` | `assets` 바이트 그대로 | `JENKINS_BUILD_TARGET ALL`일 때 빌드 1회 안에서 가능한 조합(APP 4개, FBL 2개)을 차례로 빌드·패키징 |
| `PJ_Variant.ps1` | `assets` 바이트 그대로 | `PJ_Define.h` 읽기·임시 전환(설정값, 빌드 목록, OEUK 전환·버전 기록, 산출물 폴더 이름). 바이트·줄바꿈 보존 |

APP·FBL이 **같은 파일 한 벌**을 쓴다. 차이는 `PJ_Define.h`의 버전 배치뿐이고 스크립트가 알아서 읽는다.

> 🎯 **빌드 대상 설정 — `PJ_Define.h`의 `JENKINS_BUILD_TARGET`**
>
> 기준 OEUK 블록(예: `OEUK_HE1I`)의 버전 define 근처에 둔다. bat만 읽고 C 코드는 쓰지 않는다(쓰지 않는 매크로라 MISRA 2.5 권고 경고가 날 수 있다).
>
> ```c
> #define JENKINS_BUILD_TARGET CURRENT   /* CURRENT | ALL */
> ```
>
> | 값 | APP (`26810`) | FBL (`HE130I02`) |
> | --- | --- | --- |
> | `CURRENT` 또는 define 없음 (기본값) | 켜진 OEUK 하나만. HE1I → `26810\`, TEST → `26810_test\` | 켜진 OEUK 하나만. HE1I → `OEUK_HE1I\`, TEST → `OEUK_HE1I_TEST\` |
> | `ALL` | 4개: `26810\`, `26810_test\`, `26820\`, `26820_test\` | 2개: `OEUK_HE1I\`, `OEUK_HE1I_TEST\` |
>
> 값은 **`CURRENT`와 `ALL` 둘뿐**이다. `ALL`은 "그 프로젝트에서 가능한 조합 전부"이고, 다음 버전(올림)이 가능한지 스크립트가 판단한다. TEST 하나만 빌드하려면 `CURRENT`로 두고 OEUK 선택 줄을 `OEUK_TEST`로 바꾼다. 그 밖의 값(옛 `TEST` 등)은 알 수 없는 값으로 보고 단일 빌드한다.
>
> - 조합마다 **켤 OEUK 하나만 살리고 나머지는 주석** 처리한다(`#if OEUK_HE1I`가 먼저라 둘 다 살면 TEST가 빌드되지 않는다).
> - **버전 읽기**: `SOFTWARE_VERSION_<n>`을 OEUK 블록에서 먼저, 블록에 없는 자리는 모든 OEUK 블록 밖의 공통 영역에서 읽어 자리 순으로 붙인다. APP `0~4` 블록 안 → `26810`, FBL `0~2` 블록 안 + `3~7` 공통 → `HE130I02`.
> - **test 폴더 이름**: APP는 기준 버전 + `_test`(`26810_test\`). FBL은 기준 OEUK + `_TEST`(`Debug\OEUK_HE1I_TEST\`)이고 콘솔에는 TEST 블록의 실제 버전(`DEV30I02`)이 찍힌다.
> - **버전 올림 가능**(버전이 전부 숫자이고 **전부 OEUK 블록 안**, APP) → 4개. test 조합은 TEST 블록 버전 칸에 기준 버전을 적어 빌드한다. 다음 버전은 **끝에서 두 번째 자리 +1, 받아올림, 마지막 자리 유지**(26810 → 26820, 26815 → 26825, 26890 → 26900) — 2026-10 사양 변경, 그전에는 마지막 자리 +1(26810 → 26811)이었다. 버전 칸은 한 글자씩이라 `10`은 넣을 수 없다. 자리가 넘치면(99990) 올림 불가로 보고 기준·test 2개만 빌드한다.
> - **업 버전을 만들지 않는 경우**(FBL) → 기준과 test 2개. **FBL 은 업 버전을 따로 낼 일이 없어서 현재 버전과 `OEUK_TEST` 둘만 둔다**(2026-11-10 사용자 확인). 스크립트는 이것을 "버전 올림 불가"로 판정해 같은 결과를 내는데, 판정 근거는 **버전 자리가 블록 밖에 있거나 글자가 섞여 있다**는 기술적 조건이다. 둘이 우연히 일치하므로 **다른 과제에 그대로 적용하지 말 것** — 업 버전이 필요한데 버전에 글자가 섞여 있으면(TPMS APP `26B100`) 스크립트는 FBL 과 똑같이 2개만 내고 **필요한 업 버전 2개를 조용히 빠뜨린다.** 버전은 건드리지 않으므로 TEST 블록의 원래 버전(FBL `DEV…`) 그대로 빌드한다. 콘솔에 `next version not possible (...) - base + test only` 로 이유를 남긴다.
> - 올린 버전과 OEUK 전환은 **임시**다. 빌드가 끝나면 `PJ_Define.h`를 원본으로 되돌려 커밋에 들어가지 않는다. 기준 버전은 사람이 정한다.
> - 한 조합이 실패해도 나머지를 빌드하고, 만들어진 폴더는 push한다. 빌드 결과는 실패로 표시된다(`[VARIANTS] [FAIL] …`).
> - 기준 블록과 TEST 블록의 FOTA(`FOTA_OTA_0x`)·HSM(`HAE_HSM_x`) 설정이 다르면 아무것도 빌드하지 않고 멈춘다 — ARXML 재생성이 필요한 경우라 로컬 `build_all.bat`을 쓴다.
> - 첫 조합은 **요청한 BuildType 그대로** 빌드한다. push 자동 빌드(Hook)는 보통 `Build`이고, `Rebuild`는 수동으로 요청했을 때만 첫 조합에 한 번 적용된다. 나머지 조합은 증분 `Build`다(`Rebuild` 요청 시 `Build`로 바뀜, `BuildVariants.bat` `FIRST_ACT`/`NEXT_ACT`). 증분 `Build`도 Generate 단계는 매번 돌고(조합당 약 1분), 컴파일은 `PJ_Define.h`에 의존하는 파일만 한다 — NQ6E APP 실측: Rebuild 602개, 나머지 조합 각 18개.
> - 시간은 조합 수만큼이다. HE1I APP 실측: ALL 4개 20.7분(첫 조합 Rebuild). NQ6E APP 실측: 첫 조합 Rebuild 26분, 전부 증분 Build 8분.
> - 처음 빌드하는 브랜치나, 저장소에 커밋된 옛 생성물(`Generated\`)이 남아 있을 수 있는 경우에는 첫 빌드를 `BuildType=Rebuild`로 수동 실행하도록 안내한다. NQ6E APP 첫 Hook 빌드는 옛 `os_ioc.arxml` 때문에 `MemMap.h` `#error`로 실패했고, Rebuild로 해결됐다.
> - **`PJ_Define.h`는 공유 소스라 skill이 넣지 않는다.** `add-bat` 결과의 `build_target.define`이 `null`이면 CURRENT로 동작하며, ALL이 필요하면 위 줄을 사용자가 넣도록 안내한다. `has_oeuk_test`가 false면 ALL은 쓸 수 없다고 함께 알린다.
> - 평소에는 `CURRENT`로 두고, 필요할 때만 `ALL`로 바꿔 커밋한 뒤 결과를 받고 되돌리도록 안내한다(매 push마다 여러 번 빌드하지 않도록).
> - 실측(HE1I): APP ALL 4개 약 21~23분, FBL ALL 2개 약 0.5분.

> 📐 **규정 — `PJ_Define.h` 위치와 FBL 산출물 폴더 이름 (저장소가 이 규정을 따른다)**
>
> | 항목 | 규정 |
> | --- | --- |
> | `PJ_Define.h` 위치 | `<프로젝트 폴더>\Application\app_code\a_app_service\src\PJ_Define.h` — APP·FBL 공통 |
> | FBL 산출물 폴더 | `<프로젝트 폴더>\Debug\OEUK_<차종>\` 과 `\Debug\OEUK_<차종>_TEST\` |
>
> 확인된 기준 저장소: `psu_master`(PSU APP) `psu_app/Application/app_code/a_app_service/src/PJ_Define.h`, `psu_fbl_master`(NQ6E FBL) `psu_fbl/Application/app_code/a_app_service/src/PJ_Define.h` + `psu_fbl/Debug/OEUK_NQ6E/`·`OEUK_NQ6E_TEST/`. `assets\PostPackage.bat` 의 `VEHICLE_OPTION_FILE` 이 이 규정 경로다.
>
> **스크립트를 저장소에 맞추지 않는다** — 경로 후보를 늘리거나 과제별 분기를 넣으면 과제마다 갈라져 규정이 사라진다. 어긋난 것을 발견하면 **고치지 말고 사용자에게 보고**한다(공유 소스 이동은 `#include` 에 영향이 있어 저장소 소유자 판단이다).
>
> ⚠️ **다만 "저장소를 규정에 맞춘다" 가 늘 가능한 것은 아니다 — `OEUK_TEST` 의 유무는 뱅크 구조가 가른다.** `OEUK_TEST` 는 **서명검증 공개키(`Dcm_GaaPublicKeyData`)를 품은 빌드에만** 있다. 듀얼뱅크는 돌고 있는 APP 이 반대 뱅크 이미지를 검증하므로 APP 도 키를 갖고, 그래서 test 키 변종이 필요하다. 싱글뱅크는 FBL 만 검증하므로 **APP 에는 키도 변종도 없는 것이 설계**다 — 메울 공백이 아니다. 2026-11-10 네 저장소 실측:
>
> | 뱅크 | 과제 | 공개키 | 변종 선택 | 버전 define | 위치 |
> | --- | --- | --- | --- | --- | --- |
> | 듀얼 (규정) | PSU APP·FBL (HE1i, NQ6e) | **APP·FBL 둘 다** | `PJ_Define.h` 의 `OEUK_*` 하나만 주석 해제 | OEUK 블록 안 `SOFTWARE_VERSION_0~n`, `(u8)'2'` 한 글자씩 | 규정 경로 |
> | 싱글 | TPMS **FBL** | 있음 (`Static_Code/Reference_Code/src/App_DiagnosticService.c`) | `OEUK_*` 있음 (`//OEUK_TEST 0u` / `//OEUK_BJ1 1u` / `OEUK_LT2 2u`) | **없음** | `Application\app_code\type\PJ_Define.h` (규정 밖) |
> | 싱글 | TPMS **APP** | **없음** | **없음** (정상) — 두 차종을 한 바이너리에 담고 런타임에 고름(`CONFIG_TABLE[e_VEHICLE_MODEL_MAX]`) | 없음. `configuration.h` 에 문자열·문자로 흩어짐 | `Application\Implementation_TPMS\DataTypes\configuration.h` |
>
> 같은 제품군 안에서도 FBL 은 OEUK 가 있고 APP 은 없다. 그래서 **뱅크 구조를 먼저 가린다.**
>
> ⚠️ **FBL 은 원래 업 버전이 없다.** 현재 버전과 `OEUK_TEST` 둘만 둔다 — 2벌이 정상이고 모자란 것이 아니다.
>
> | 어떤 저장소인가 | 할 일 |
> | --- | --- |
> | 규정과 같다 | 그대로 진행 |
> | 변종 체계는 있는데 **위치·이름만** 다르다 (TPMS FBL) | 파일 경로는 이미 매개변수다 — `PJ_Variant.ps1` 은 `-File`, 전용 훅 `Build_Hook_<차종>.bat` 은 `PJ_FILE` 을 set 한다. **전용 훅에서 `PJ_FILE` 을 그 저장소의 실제 파일로 돌린다**(수정 허용 파일). 저장소를 옮기지 않는다 |
> | 변종 체계 자체가 **없다** (TPMS APP, 싱글뱅크) | **맞출 것이 없다 — 변종 빌드 대상이 아니다.** 싱글뱅크 APP 은 공개키를 품지 않으므로 `OEUK_TEST` 가 필요 없다. 전용 훅이 `PJ_FILE` 부재를 보고 **단일 빌드로 내려가는 것이 정상 동작**이다(`Build_Hook_<차종>.bat` 의 `if not exist "%PJ_FILE%" goto :single_build`). `PJ_Define.h` 를 새로 넣지 않는다 |
>
> ⚠️ **asset 에 과제 고정값이 박혀 있는 곳이 있다 (스킬 결함, 2026-11-10 확인).** 이것은 저장소 탓이 아니므로 저장소를 고쳐도 해결되지 않는다.
>
> | asset | 하드코딩 | 영향 |
> | --- | --- | --- |
> | `PostPackage.bat:35` | `VEHICLE_OPTION_FILE` = 규정 경로의 `PJ_Define.h` | 규정 밖에 둔 저장소(TPMS FBL)에서 1단계 OEUK 탐색부터 못 간다. 싱글뱅크 APP 은 애초에 대상이 아니라 무해하다 |
> | ~~`PostPackage.bat:36`~~ | `SECUREFLASH_INI` 에 PSU 전용 경로·파일명이 박혀 있었다 | ✅ **고쳤다 (2026-11-10).** 경로를 박지 않고 **훅이 `SECUREFLASH_INI` 를 넘기면 그것을, 없으면 `References\*Signed_Firmware*\*.ini` 를 찾는다.** 폴더명(`Doc_MB`/`Doc_MobaseElec`)·번호(`02_`/`03_`)·파일명이 과제마다 다르다. ini 가 없는 과제(FBL)는 전처럼 WARNING 만 남는다 — `if exist` 로 감싸여 있어 **rom zip 자체는 만들어진다** |
> | `BuildVariants.bat:29` | `PJ_FILE` = 규정 경로 | 훅이 돌려도 여기서 되돌아간다 |
> | `PJ_Variant.ps1` `Get-NextVersion` | `[long]$v + 10` — **전부 숫자여야 한다** | 문자가 섞인 버전은 예외 → plan 이 KEEP 2줄만 내고 **필요한 업 버전 2개가 조용히 빠진다.** ⚠ 2026-11-10 실측 — **현재 TPMS APP 에는 해당하지 않는다**(`PJ_FILE` 이 없어 변종 경로에 진입조차 하지 않는다). OEUK 를 쓰면서 버전에 문자가 섞인 과제가 생길 때의 잠재 위험이다. ⚠ 그런데 **이 제약이 FBL 을 2개로 묶어 두는 장치이기도 하다** — 단순히 일반화하면 FBL(`HE130I02`·`DEV30I02`)이 갑자기 4개를 빌드한다. 고칠 때는 증가 규칙만 일반화하지 말고 **"업 버전을 만들 것인가"를 선언으로 분리**한다(예: 기준 블록에 `JENKINS_BUILD_NEXT_VERSION` 같은 명시 define). 의도를 버전 문자열의 생김새에 기대지 않는다 |
>
> ⚠ **사본이 과제마다 같지 않다 — 같다고 단정하지 말고 세어 본다.** 2026-11-10 실측 `PostPackage.bat` 은 **세 갈래**였다: 스킬 asset = TPMS APP, PSU APP = PSU FBL, TPMS FBL 은 혼자 다름. asset 을 고쳐도 과제 저장소에 자동으로 퍼지지 않으므로, **고친 뒤 과제별로 반영 여부를 따로 확인한다.** 고칠 때는 **과제별 분기를 넣지 말고 전용 훅이 넘기는 환경변수로 빼낸다**(위 `SECUREFLASH_INI` 가 그 방식이다).
>
> ⚠️ **첫 빌드 뒤 산출물 폴더를 반드시 눈으로 확인한다.** `PJ_Define.h` 를 못 찾으면 `PostPackage` 가 콘솔에 한 줄만 남기고 건너뛰는데, **빌드는 `SUCCESS` 로 끝나므로 로그 결과만 보면 알 수 없다.**
>
> ```
> [PostPackage] No enabled OEUK option found. Skipping.
> ```
>
> 이 줄이 있거나 산출물이 `Debug\OEUK_<차종>\` 이 아니라 `Debug\` 바로 아래 평면으로 생겼으면 패키징이 빠진 것이다. 실제 사례 — `Kahuz/tpms_rf_receiver_bj_fbl`(TPMS FBL)은 `PJ_Define.h` 가 규정에서 벗어난 `Application\app_code\type\` 에 있어 2026-11-09 Jenkins #1(SUCCESS, 163초)에서 패키징이 건너뛰어지고 산출물이 `Debug\e_bj_tpms_asr_swp_fbl_v219.*` 로 평면 생성됐다. 같은 저장소의 다른 차이(OEUK 선언에 `1u` 값이 붙음, `SOFTWARE_VERSION_*` 없음, TEST 폴더가 차종별이 아닌 `OEUK_TEST` 공용)는 그 자체로는 막지 않는다 — `PJ_Variant.ps1` 의 정규식이 값 붙은 `#define` 을 읽고, FBL 평면 구조는 폴더명에 버전을 쓰지 않는다.
>
> 📁 **산출물 폴더 — APP는 버전별로 쌓이고, FBL은 OEUK별 평면 폴더**
>
> 어느 쪽인지는 `PJ_Variant.ps1 -Action folder`가 정한다(출력 `<폴더> <버전폴더> <버전>`). 다음 버전(올림)이 불가능한 프로젝트(FBL)는 버전폴더 자리에 `.`을 내고 평면 구조가 된다.
>
> - **FBL**: `Debug\OEUK_HE1I\`(기준), `Debug\OEUK_HE1I_TEST\`(TEST). APP 저장소 `psu_app\References\02_Fbl_Binary\`의 폴더 이름과 같아서 **같은 이름 폴더로 그대로 복사**하면 된다(`.sre/.hex/.elf/.map` 4개, `BuildWarning.xlsx` 제외). 빌드마다 그 OEUK 폴더를 통째로 다시 만들며 옛 `HE130I02\`·`HE130I02_test\`도 이때 정리된다. 파일 접두어는 TEST도 기준 차종(`he1i_psu_fbl_…`)이라 폴더로 구분한다. HE1i 실측 2026-10-05 FBL Jenkins #12(ALL)로 확인. 복사·커밋은 사람이 한다(넣을 APP 브랜치를 정해야 해서 Jenkins가 하지 않는다).
>
> 아래는 **APP** 버전 폴더 설명이다.
>
> `<버전>`은 `PJ_Define.h`의 `SOFTWARE_VERSION_*`를 위 규칙으로 읽은 문자열이다(APP `26810`). 같은 버전으로 다시 빌드하면 그 버전 폴더만 지우고 새로 만들고, 다른 버전 폴더는 그대로 둔다. `OEUK_xxxx\` 바로 아래의 파일·`rom_*` 폴더(옛 평면 구조)는 정리한다. 버전을 읽지 못하면 `UNKNOWN\`에 넣고 `rom` 패키징은 건너뛴다.
>
> - **rom 패키지 이름은 버전 폴더 이름을 따른다**: `26810\rom_26810\`·`rom_26810.zip`, `26810_test\rom_26810_test\`·`rom_26810_test.zip`. 예전에는 test 폴더 안에도 `rom_26810`이 생겨 기준 빌드와 구분되지 않았다(2026-10 수정). 콘솔의 `Software version`과 `Finished … v<버전>`에는 `_test`를 뺀 실제 버전이 찍힌다.
>
> - CVD 등 디버거 다운로드 경로가 `Debug\OEUK_xxxx\<버전>\<차종>_psu_app_vX_Y_Z_Writing.s19`가 되므로 버전을 올리면 디버거 설정 경로도 바꿔야 한다.
> - 로컬 `Build_all.bat`은 수정하지 않으므로 여전히 `OEUK_xxxx\` 전체를 지우고 평면 구조로 만든다. Jenkins 결과는 `git pull`로 받도록 안내한다.

> 🧩 **서브모듈 — Job 이 받아 주지 않으므로 전용 훅이 받는다**
>
> Job 템플릿은 서브모듈을 체크아웃하지 않는다(`SubmoduleOption` 을 넣지 않는다). 그래서 서브모듈을 쓰는 프로젝트는 **그 안의 헤더를 못 찾아 컴파일이 깨진다** — 실측 2026-11-09 `tpms_rf_receiver_bj`(APP) 빌드 #1: `CanInOut.c:8: cannot open source file "PDCReset.h"` (서브모듈 `git/common_pdc_reset`). FBL 은 서브모듈이 없어 겪지 않는다.
>
> 그래서 전용 훅 `Build_Hook_<차종>.bat` 의 **0) 단계**가 빌드 전에 받아 온다. `.gitmodules` 가 있을 때만 돌고, 이미 받아져 있으면 아무것도 하지 않는다.
>
> ```bat
> if exist "%PROJ_DIR%\.gitmodules" (
>     git submodule sync --recursive
>     git submodule update --init --recursive
> )
> ```
>
> 실패해도 **빌드를 멈추지 않고 경고만 남긴다.** 권한 문제인지 다른 문제인지 콘솔만 보고 가릴 수 있어야 하기 때문이다.
>
> ⚠️ **개발자 계정의 404 를 근거로 "권한이 없어 불가능"이라고 결론내지 말 것.** `build` 계정은 개발자와 다른 계정이고, 사내 조직(`git`) 저장소를 읽을 수 있다. 실측 — 같은 서브모듈 저장소가 `jdlee` 토큰으로는 `Repository not found`(404)였는데 `build` 계정은 clone 에 성공해 빌드가 통과했다(APP 빌드 #2, SUCCESS). 읽을 수 없다고 미리 단정하지 말고 **훅을 넣고 한 번 돌려서 확인한다.**
>
> Job 설정으로 켜는 방법(SCM → Additional Behaviours → `Advanced sub-modules behaviours` → recursive + parent credentials)도 있지만, **이 스킬은 기존 Job 을 수정하지 않는다.** 덧붙여 `config.xml` POST 는 수정하지 않은 원본을 그대로 올려도 HTTP 500 이 난다(2026-11-09 실측) — 일반 계정은 Job 설정 쓰기가 막혀 있다. 사용자가 직접 화면에서 켜야 한다.
>
> 결과물 커밋에는 서브모듈 소스가 들어가지 않는다(저장소에는 포인터만 기록된다). `Debug\` 아래에 생기는 서브모듈 오브젝트 파일(`.o`·`.dbo`)은 중간 산출물이라 모드 D 가 PR 에서 걸러낸다.

> 💡 **왜 표준 훅을 고치지 않고 전용 훅을 따로 두는가**
>
> Jenkins 훅은 `Build.bat`을 직접 부르므로 `Build_all.bat`의 Post-build 단계를 거치지 않는다. 그래서 `rom_<버전>` 패키지(aSIMS 전자서명 입력)와 차종명 산출물이 생성되지 않는다. 이걸 메우려면 훅에 한 블록을 넣어야 하는데, **이름이 `Build_Hook_GIT_ASEC.bat`인 채로 내용만 고치면 다음 사람이 표준인 줄 알고 그냥 둔다.** 차종 이름을 달아 두면 "이 과제 전용이니 고쳐도 된다"가 파일명만으로 전달된다. 전용 훅 머리말에도 `Edit : ALLOWED`로 명시된다.
>
> 표준 훅을 함께 남기는 이유는 Branch Specifier가 `*/devel_<차종>_<ID>_*` **와일드카드**이기 때문이다. 전용 훅이 없는 브랜치가 같은 Job에 걸려도 빌드 명령의 `if exist` 분기가 표준 훅으로 넘겨 **빌드가 깨지지 않는다**(패키징만 빠진다).

- 기존 `Build.bat`, `Build_Hook.bat`, `Build_all.bat`, `PJ_Define.h`는 건드리지 않는다. 다른 개발자와 공유하는 파일이라 PR로 원본에 들어가면 남의 빌드가 바뀌기 때문이다.
- **위 6개는 공유 소스가 아니다.** 이 스킬이 만들어 넣는 Jenkins 전용 파일이고 모드 D 가 PR 에서 걸러낸다. `devel_*` 작업 브랜치에서 같은 이름의 파일이 있고 내용이 다르면 **표준본으로 교체**하고 `replaced` 에 담아 보고한다. 단 git 이 추적하는 파일일 때만 — 추적되지 않으면 원본을 되돌릴 수 없으므로 `conflict` 로 멈춘다.
- `conflict` 가 나면 **디스크를 원래대로 되돌린 뒤** 멈춘다(`rolled_back`). 그리고 `details` 의 `diff`·`risk`·`reason` 을 **사용자에게 그대로 보여주고** 교체 여부를 한 줄로 묻는다.

  > 실제 사례 — `tpms_rf_receiver_bj_fbl` 의 기존 `GitPush.bat` 은 `git push ... HEAD:devel_jslim_GT` 로 **남의 브랜치에 결과물을 밀어넣고**, 커밋 메시지가 `Main Build Server Build Result` 라서 Job 의 제외 필터(`Auto commit from Jenkins`)에 걸리지 않아 **연속 빌드**를 일으킨다. `risk` 가 이 두 가지를 자동으로 찾아 낸다. 2026-11 이전 버전은 "내용이 다름" 한 줄만 내고 멈춰서, 5개를 디스크에 풀어놓은 채 커밋 없이 방치되고 **Job 은 만들어졌는데 부를 훅이 없는** 반쪽 환경이 남았다.

- bat 파일을 직접 편집하지 않는다. `sed` 등은 CRLF를 LF로 바꿔 bat 동작이 깨질 수 있다. 교체도 스크립트가 바이트 단위로 한다.

## 5. Jenkins Job — 먼저 확인하고, 없을 때만 생성

```
python gjsetup.py job-match --repo-url <GITEA_URL>/<소유자>/<repo>.git --branch <작업 브랜치>
```

Job은 브랜치 단위가 아니라 **(저장소 × Branch Specifier)** 단위다. Branch Specifier가 `*/devel_<차종>_<ID>_*`라 같은 저장소·같은 차종·같은 사람의 브랜치는 **기존 Job이 이미 받는다.**

| 결과 | 처리 |
| --- | --- |
| `matched` | **Job을 만들지 않는다.** `matched[].name`을 재사용한다고 보고하고 6단계로 간다. `disabled: true`면 활성화가 필요하다고 알린다 |
| `no_match` | 아래 `render-job` → `job-create`로 새로 만든다. `same_repo_jobs`에 같은 저장소의 다른 Job이 있으면 참고로 함께 보여준다 |

**같은 저장소에 Branch Specifier가 겹치는 Job을 또 만들면 안 된다.** 한 브랜치를 두 Job이 각각 빌드해 결과물을 같은 브랜치에 push하므로 중복 빌드와 push 경쟁이 생긴다. `job-match`는 그것을 막기 위한 확인이다.

이 확인은 모드 A에서도 한다 — 모드 A는 대개 `no_match`가 나온다.

```
python gjsetup.py render-job --name <Job> --repo-url <GITEA_URL>/<소유자>/<repo>.git --branch-spec "*/devel_<차종>_<로그인ID>_*" --project <프로젝트 폴더> --model <차종> --user <Jenkins ID> --cred-id <인증정보 ID> --description "<설명>" --out <임시폴더>\<Job>.xml
python gjsetup.py job-create --name <Job> --xml <임시폴더>\<Job>.xml [--view <뷰>]
```

템플릿이 넣는 값 (모두 HE1I PSU 첫 적용에서 동작 확인):

| 항목 | 값 | 이유 |
| --- | --- | --- |
| 상태 | **비활성** | 생성 즉시 Poll SCM이 첫 빌드를 시작하지 않도록 |
| 권한 | 본인: Job Build·Cancel·Configure·Read·Workspace, Run Delete·Update | 본인이 빌드·설정 가능 |
| 매개변수 `BuildType` | Hook(기본)·Build·Compile·GenerateAll·Rebuild·Clean | 첫 줄이 기본값, 자동 빌드는 커밋 메시지로 동작 결정 |
| Repository URL · Credentials | Fork 주소 · `build` 인증정보 | |
| Branch Specifier | `*/devel_<차종>_<ID>_*` | 같은 사람의 작업 브랜치를 한 Job으로. `GitPush.bat`이 브랜치를 자동으로 따라감 |
| 제외 메시지 필터 | `(?s).*Auto commit from Jenkins.*` | 결과물 커밋에 반응한 연속 빌드 방지. `(?s)`는 메시지 끝 줄바꿈 대응 |
| Poll SCM | `* * * * *` | push 후 1분 안에 빌드 |
| 빌드 명령 | `if exist` 분기 — 전용 훅 `<프로젝트 폴더>\Build\Build_Hook_<차종>.bat`이 있으면 그것을, 없으면 표준 훅을 호출 | 전용 훅이 없는 브랜치가 같은 Job에 걸려도 빌드가 깨지지 않게 |
| 서브모듈 · 빌드 후 조치 · 동시 빌드 | 없음 · 없음 · 끔 | |

`job-create` 결과가 `conflict`면 기존 Job은 수정하지 않고 중단한다. HTTP 오류는 `detail`을 보여주고 `troubleshooting.md` Jenkins 표를 따른다.

## 6. 검증 · 보고

```
python gjsetup.py repo-info --repo <원본 owner/repo>          # my_repo_same_name이 Fork로 보이는지
python gjsetup.py collab --repo <소유자>/<repo> --user build   # exists / write
python gjsetup.py job-verify --name <Job> --repo-url <…> --branch-spec "<…>" --project <…> --model <차종> --user <Jenkins ID>
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
| 4. 표준 bat | … | <프로젝트>\Build\ 6개, 커밋 <해시>, 빌드 대상 <CURRENT/ALL/define 없음> |
| 5. Job | ✅ 생성 / ♻️ 재사용 | <Job> (뷰 <뷰>, 비활성) 또는 <Job> 재사용 — 만들지 않음 |
| 6. 검증 | ✅ 8/8 | 필터·URL·브랜치·명령·권한·매개변수 |

경고: <서브모듈 실패 등>
Jenkins: <JENKINS_URL>/job/<Job>/
```

## 활성화 (마지막 질문)

보고 후 한 번 묻는다: "Job을 활성화할까요? 활성화하면 1분 안에 첫 빌드가 자동으로 시작되고 약 10~15분 걸립니다."

- 예 → `python gjsetup.py job-enable --name <Job>` 후, 첫 빌드 확인 방법만 안내한다(이 skill은 빌드 결과 판정을 하지 않는다):
  - Console Output에서 `[HOOK] Build/Git Push/Final ERROR LEVEL : 0` → `Finished: SUCCESS`
  - 빌드 종료 후 2~3분 동안 결과물 커밋에 반응한 추가 빌드가 **생기지 않는지**
  - **산출물이 규정 폴더에 생겼는지** — FBL은 `Debug\OEUK_<차종>\`. `Debug\` 바로 아래 평면으로 생겼거나 콘솔에 `[PostPackage] ... Skipping.` 이 있으면 패키징이 빠진 것이다(빌드는 `SUCCESS` 로 뜨므로 결과만 보면 모른다). 위 📐 규정 항목으로 돌아가 `PJ_Define.h` 위치를 확인하고 **사용자에게 보고**한다
  - 결과물 받기: 로컬에서 `git pull`
- 아니오 → Job 화면의 `프로젝트 활성화` 버튼으로 나중에 켤 수 있다고 안내한다.

## 범위 밖

첫 빌드 결과 판정, 패치 작업·커밋, 원본 동기화(upstream merge), PR 리뷰·머지, Redmine 기록, 기존 Job·저장소 설정 변경은 하지 않는다(사용자가 요청한 이전 절차 `references/migrate_to_shared_fork.md`만 예외). 작업 브랜치를 공유 브랜치에 그대로 머지하지 않는다 — `GitPush.bat`이 `git add -f .`로 중간 산출물까지 담기 때문이다. 공유 브랜치로 올리는 것은 모드 D(PR 구성)로 한다. 요청받으면 이 skill의 범위가 아님을 알리고 필요한 절차만 안내한다.
