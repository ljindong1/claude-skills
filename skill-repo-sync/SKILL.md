---
name: skill-repo-sync
description: 계정에 등록된 Claude 스킬을 로컬 git 저장소(기본 D:\Ljindong\skills-repo)에 그대로 반영하고 변경 요약을 보여준 뒤 커밋·푸시까지 안내하는 스킬. 사용자가 "스킬 백업", "스킬 커밋해줘", "스킬 저장소에 반영", "스킬 동기화", "수정한 스킬 올려줘", "저장소에 반영", "스킬 git에 넣어줘", "스킬 저장소 최신화", "스킬 형상관리" 등을 언급하거나, 앱에서 스킬을 고친 뒤 그 변경을 저장소에 남기려는 의도를 보이면 반드시 이 스킬을 사용하라. 특정 스킬 이름을 지정하면 그것만, 아무 말이 없으면 사용자가 직접 만든 스킬 전체가 대상이다. 저장소에 없으면 추가하고 있으면 계정 버전으로 덮어쓴다. 스킬을 새로 만들거나 내용을 편집·개선하는 일은 skill-creator 담당이며, 이 스킬은 이미 계정에 있는 스킬을 저장소로 옮겨 기록하는 일만 한다.
---

# 스킬 저장소 동기화

계정에 등록된 스킬을 git 저장소에 반영한다. 방향은 **항상 계정 → 저장소** 한 방향이다.

실제로 쓰이는 스킬은 계정에 등록된 것이고, 저장소는 그 이력을 남기는 사본이다. 저장소에서 파일을 고쳐도 계정 스킬은 바뀌지 않는다. 그래서 저장소 쪽 내용은 주저 없이 덮어써도 되지만, **커밋되지 않은 로컬 수정만은 예외**다 — 그건 덮어쓰면 복구할 방법이 없으므로 반드시 먼저 멈추고 물어본다.

## 기본값

| 항목 | 값 |
| --- | --- |
| 저장소 | `D:\Ljindong\skills-repo` (사용자가 다른 경로를 말하면 그쪽) |
| 원본 | 세션에 마운트된 계정 스킬 폴더 (`/sessions/<세션>/mnt/.claude/skills`, 읽기 전용) |
| 저장소 구조 | 스킬 폴더가 **저장소 최상위**에 바로 놓인다 (`skills-repo/svg-creation/SKILL.md`) |
| 대상 | 이름을 지정하면 그 스킬만, 없으면 사용자가 만든 스킬 전체 |
| 커밋 | Claude 가 한다 (세션당 한 번 삭제 권한 필요 — 아래 참조) |
| 푸시 | **사용자가 PowerShell 한 줄** (샌드박스에 네트워크 경로 없음) |

Anthropic 기본 스킬(`docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `morning` 등)은 사용자가 만든 것이 아니고 플랫폼 업데이트마다 바뀌어 커밋 노이즈가 되므로 기본 대상에서 뺀다. 사용자가 "전부", "기본 스킬까지"라고 하면 `--include-builtin` 을 붙인다.

## 이 환경의 구조

세 곳을 구분해야 헷갈리지 않는다.

```
계정 스킬 (앱에서 편집하는 정본)
    │  세션 시작 시 한 번 복사
    ▼
/sessions/<세션>/mnt/.claude/skills/     ← 원본. 읽기 전용 스냅샷
    │  이 스킬이 복사
    ▼
D:\Ljindong\skills-repo/                 ← 저장소. git 이력
    ▲
    │  디렉터리 정션(바로가기)
C:\Users\ljindong\.claude\skills/        ← VS Code(Claude Code)가 읽는 곳
```

마지막 정션 덕분에 **저장소를 갱신하면 VS Code 쪽도 자동으로 같이 바뀐다.** 따로 복사할 필요가 없다. 사용자가 "VS Code에도 반영해야 하나?"라고 물으면 이 점을 알려주면 된다.

정션이 걸려 있는지 확인하려면 사용자에게 이걸 부탁한다.

```powershell
(Get-Item C:\Users\ljindong\.claude\skills).LinkType
```

`Junction` 이 나오면 연결된 상태다. 아무것도 안 나오면 그냥 폴더이므로, 저장소 갱신 후 그쪽도 따로 맞춰야 한다.

## 시작 전 — 폴더 연결부터 시도한다

추측하지 말고 `mcp__cowork__request_cowork_directory` 로 저장소 경로를 요청해 본다. 결과가 곧 진단이다.

**성공하면** 그대로 진행한다. Read/Write/Edit 는 Windows 경로(`D:\Ljindong\skills-repo\...`)를 쓰고, bash 는 마운트 경로(`/sessions/<세션>/mnt/skills-repo/...`)를 쓴다.

**`overlaps a protected host location (…\.claude\skills)` 로 거부되면** — 이게 이 스킬에서 가장 많이 밟는 함정이다. 요청한 경로 안에 `.claude\skills` 가 있으면 앱이 그 경로를 보호 대상으로 보고 **저장소도 상위 폴더도 전부 잠근다.** 폴더를 지워도 등록이 남아 계속 거부될 수 있다.

이때 답은 하나다. **저장소를 `.claude` 를 품지 않는 새 경로로 clone 하고, 스킬 폴더를 최상위에 둔다.**

```powershell
git clone <원격 URL> D:\Ljindong\skills-repo
```

옛 저장소가 `.claude/skills/` 안에 스킬을 두고 있었다면 최상위로 올린다.

```powershell
cd <옛 저장소>
Get-ChildItem .claude\skills -Directory | ForEach-Object { git mv ".claude/skills/$($_.Name)" $_.Name }
Remove-Item -Recurse -Force .claude
git add -A; git commit -m "chore: move skills to repo root"; git push
```

### 흔한 오진 두 가지

**bash 샌드박스에 `D:` 가 안 보이는 것은 정상이다.** bash 는 항상 격리된 리눅스에서 돌고 Windows 드라이브가 그대로 보이지 않는다. 이걸 근거로 "클라우드 세션이라 안 된다"고 판단하면 틀린다. 로컬 실행 여부는 bash 로 판별할 수 없다 — 폴더 연결을 시도해서 확인하라.

**사용자에게 "새 세션에서 다시 하세요"라고 먼저 말하지 않는다.** 대부분의 거부는 위 보호 경로 문제이고, 세션을 바꿔도 그대로다. 오류 메시지를 읽고 원인을 말해 주는 편이 훨씬 빠르다.

## 원본은 세션 시작 시점의 스냅샷이다

마운트된 원본은 계정 스킬의 **사본**이고, 세션이 시작될 때 한 번 내려온다. 앱에서 스킬을 고친 직후 같은 세션에서 동기화를 요청하면 **수정 전 버전이 반영될 수 있다.**

파일 수정 시각을 확인해 사용자에게 알린다.

```bash
find /sessions/<세션>/mnt/.claude/skills/<스킬> -type f -printf '%TY-%Tm-%Td %TH:%TM  %P\n' | sort
```

방금 앱에서 고친 내용이라면 그 시각이 여기 반영돼 있는지 확인하고, 안 되어 있으면 새 세션에서 다시 실행해야 한다고 알린다. 잘못된 버전을 커밋하는 것보다 한 번 더 묻는 편이 낫다.

## 누가 무엇을 하는가

| 단계 | 담당 |
| --- | --- |
| 파일 비교·복사 | Claude |
| `git add` · `git commit` | Claude |
| `git push` | **사용자 (PowerShell 한 줄)** |

푸시만 넘기는 이유는 샌드박스에 원격까지 가는 길이 없기 때문이다. DNS 가 해석되지 않고(`Could not resolve hostname github.com`), SSH 22번 포트가 프록시에서 차단되며(`E CONNECT …:22: Forbidden`), 키도 없다. 권한이나 설정 문제가 아니라 경로 자체가 없는 것이므로 **재시도하지 말고 바로 사용자에게 넘긴다.**

```powershell
git -C D:\Ljindong\skills-repo push
```

### 커밋 전에 — 삭제 권한을 먼저 받는다

마운트는 기본적으로 파일 생성과 이름변경만 허용하고 **삭제를 막는다.** git 은 `index.lock`, `HEAD.lock`, `objects/tmp_obj_*` 같은 임시 파일을 만들었다 지우며 동작하므로, 삭제가 막히면 잠금 파일이 그대로 남는다. 그러면 샌드박스는 물론 **Windows 쪽 git 까지 전부 막혀서** 사용자가 손으로 지워야 풀린다. 가장 성가신 사고이니 커밋 전에 권한부터 받는다.

```
mcp__cowork__allow_cowork_file_delete(file_path="/sessions/<세션>/mnt/skills-repo/.git/index.lock")
```

승인은 파일 단위가 아니라 **폴더 단위**로 적용되므로 세션당 한 번이면 된다. 이후에는 평범하게 커밋하면 된다.

```bash
R=/sessions/<세션>/mnt/skills-repo
git -C $R add -A
git -C $R status --short          # 무엇이 커밋되는지 사용자에게 보여준다
git -C $R -c user.name="ljindong" -c user.email="ljindong1@gmail.com" commit -m "<메시지>"
git -C $R rev-parse --short HEAD
```

커밋 뒤에는 찌꺼기가 남지 않았는지 확인하고, 남았으면 지운다.

```bash
find $R/.git -name "*.lock" -o -name "tmp_obj*"
```

**사용자가 삭제 권한을 거부하면** 커밋도 사용자에게 넘긴다. 억지로 진행하면 잠금 파일만 남기고 상황을 악화시킨다.

```powershell
cd D:\Ljindong\skills-repo
Remove-Item .git\index.lock -Force -ErrorAction SilentlyContinue
git add -A; git commit -m "..."; git push
```

### 줄바꿈(CRLF) 오탐

Windows git 이 체크아웃하면 파일이 CRLF 로 저장된다. 샌드박스 git 의 설정이 다르면 **모든 파일이 수정된 것처럼 보인다.** 갓 clone 한 저장소에서 수십 개가 ` M` 으로 뜨면 이 경우다. 실제 변경이 아니므로 설정만 맞춘다.

```bash
git -C /sessions/<세션>/mnt/skills-repo config core.autocrlf true
git -C /sessions/<세션>/mnt/skills-repo status --porcelain | wc -l   # 0 이면 정상
```

파일 비교 자체는 스크립트가 줄바꿈 차이를 무시하므로 영향받지 않는다.

## 절차

### 1. 무엇이 바뀌는지 먼저 보여준다

```bash
python3 <skill>/scripts/sync_skills.py \
  --repo /sessions/<세션>/mnt/skills-repo \
  --source /sessions/<세션>/mnt/.claude/skills \
  --skills slack-morning-briefing --dry-run
```

`--source` 는 생략하지 않는다. 스크립트 기본값은 `~/.claude/skills` 인데 샌드박스의 홈은 그 경로가 아니다.

출력에는 대상 스킬, 파일 단위 추가/변경/삭제, 저장소에만 있는 폴더가 들어 있다. 이걸 요약해서 보여준다.

### 2. 확인 후 실제 복사

변경이 사소하고 명백하면 바로 진행해도 된다. 규모가 크거나 예상 밖의 삭제가 섞여 있으면 먼저 확인을 받는다.

```bash
python3 <skill>/scripts/sync_skills.py \
  --repo /sessions/<세션>/mnt/skills-repo \
  --source /sessions/<세션>/mnt/.claude/skills \
  --skills slack-morning-briefing --no-commit --json
```

복사는 스크립트에 맡기고 커밋은 `--no-commit` 으로 떼어내 직접 한다. 무엇이 커밋되는지 `git status` 로 확인해 사용자에게 보여준 뒤 커밋하는 편이, 스크립트에 통째로 맡기는 것보다 사고가 적다.

스크립트가 어떤 이유로든 막히면 손으로 복사해도 결과는 같다. 스크립트는 편의 도구이지 필수가 아니다.

```bash
cp -rf /sessions/<세션>/mnt/.claude/skills/<스킬>/. /sessions/<세션>/mnt/skills-repo/<스킬>/
```

### 3. 스크립트가 멈추면

- **exit code 2 — 커밋 안 된 로컬 변경**: 어떤 파일인지 출력에 나온다. 그대로 보여주고 `먼저 커밋 / 되돌리기 / 무시하고 덮어쓰기(--allow-dirty)` 중 무엇을 원하는지 묻는다. **임의로 `--allow-dirty` 를 붙이지 않는다.** 단, 위 CRLF 오탐인지부터 확인한다.
- **`git 저장소가 아닙니다`**: 경로를 먼저 확인하고, 맞다면 `git init` 을 해도 되는지 묻는다.
- **`manifest.json 이 없어 폴더 스캔으로 대체합니다`**: 오류가 아니라 정상 동작이다. 마운트된 원본에는 manifest 가 없어서 스크립트가 폴더를 훑어 스킬을 인식한다. 다만 이때는 기본 스킬 판별을 이름 목록에 의존하므로, 목록에 없는 신규 기본 스킬이 대상에 섞일 수 있다. 대상 목록을 사용자에게 보여줄 때 눈으로 확인한다.

### 주요 옵션

| 옵션 | 용도 |
| --- | --- |
| `--source` | 원본 경로 (샌드박스에서는 항상 지정) |
| `--skills A B` | 특정 스킬만 |
| `--include-builtin` | Anthropic 기본 스킬도 포함 |
| `--dry-run` | 쓰지 않고 변경 내용만 |
| `--allow-dirty` | 커밋 안 된 변경이 있어도 진행 (사용자 승인 후에만) |
| `--no-commit` | 복사만 (커밋을 따로 하고 싶을 때) |
| `--message "..."` | 커밋 메시지 지정 |
| `--json` | JSON 요약 출력 |

## 저장소 문서도 함께 맞춘다

스킬 폴더가 **새로 추가되거나 없어지면** 저장소의 `README.md` 도 같은 커밋에서 고친다. 문서와 실제 내용이 어긋나면 나중에 저장소만 보고는 무엇이 들어 있는지 알 수 없게 되고, 그 어긋남은 시간이 지날수록 커진다.

고칠 곳은 두 군데다.

- **저장소 구조 트리** — 새 폴더와 그 하위 디렉터리(`references/`, `scripts/`, `assets/`)를 알파벳 순 위치에 넣는다. 각 항목 옆 주석은 그 폴더에 무엇이 들었는지 한 마디로 적는다.
- **스킬 목록 표** — 스킬 이름과 용도 한 줄. 용도는 해당 `SKILL.md` 의 description 을 그대로 붙이지 말고, 표에서 읽기 좋게 한 줄로 줄여 쓴다.

저장소에 일부러 두지 않은 스킬이 있다면 README 맨 아래 그 목록도 함께 갱신한다.

기존 스킬의 **내용만 바뀐 경우에는 README 를 건드리지 않는다.** 목록과 트리는 그대로이므로 고칠 것이 없고, 불필요한 diff 만 남는다.

## 결과 보고

장황한 로그를 붙이지 말고 이 정도로 정리한다. 사용자가 알고 싶은 건 "무엇이 바뀌었고 다음에 뭘 하면 되는가" 뿐이다.

```
저장소 갱신 완료 — 스킬 2개

  svg-creation           SKILL.md, references/patterns.md 갱신
  confluence-writing     신규 추가 (5개 파일)

  커밋 a1b2c3d (신규 추가 시 README.md 갱신 포함)
  원본 스냅샷: 2026-07-31 10:37 (이 시각 이후 수정분은 미포함)

푸시만 실행해 주세요:
  git -C D:\Ljindong\skills-repo push
```

변경이 없으면 한 줄로 끝낸다: `저장소가 이미 계정과 같습니다 — 반영할 변경 없음.`

정션이 걸려 있으면 마지막에 한 줄 덧붙인다: `VS Code 쪽은 정션으로 연결돼 있어 자동 반영됩니다.`

저장소에만 있는 폴더가 있으면 목록만 알리고 지우자고 먼저 제안하지 않는다. 이름을 바꾼 스킬의 옛 폴더일 수도, 의도적으로 보관 중일 수도 있어 판단은 사용자 몫이다.

## 이 스킬이 하지 않는 것

- **저장소 → 계정 방향 반영.** 저장소에서 고친 내용을 계정 스킬에 넣으려면 `.skill` 로 패키징해 저장해야 하며 그건 skill-creator 의 일이다. 사용자가 그걸 원하는 것 같으면 방향을 착각한 게 아닌지 먼저 확인한다.
- **스킬 내용 편집·개선.** 동기화 중에 오타나 문제가 눈에 띄어도 고치지 않는다. 저장소에 고쳐 넣어봐야 계정에는 반영되지 않아 두 쪽이 어긋나기만 한다. 발견한 사실만 알리고 skill-creator 로 넘긴다.
- **계정에서 사라진 스킬의 저장소 폴더 삭제.**
