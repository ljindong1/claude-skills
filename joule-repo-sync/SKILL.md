---
name: joule-repo-sync
description: 회사 Gitea 저장소(D:\Mobase\asec_autotest_tool)의 커밋을 개인 GitHub 백업 사본(ljindong1/Joule, private)으로 덧붙여 동기화하는 스킬. 회사 커밋마다 트리를 가져와 차종 표준 DB(*.dbc)만 떨어낸 뒤 사본 브랜치에 쌓으므로 force push 없이 작성자·날짜·메시지가 보존된다. 사용자가 "저장소 동기화", "동기화해줘", "개인 저장소에 올려줘", "GitHub 사본 갱신", "joule 백업해줘", "두 저장소 맞춰줘", "개인 깃허브에 반영", "미러링", "사본 최신화", "회사에서 한 작업 개인 저장소로", "동기화 밀렸나", "사본 몇 커밋 밀렸어" 등을 말하거나 joule(asec_autotest_tool) 작업을 개인 GitHub 에 남기려는 의도를 보이면 반드시 이 스킬을 사용하라. 푸시는 언제나 사용자 확인을 받은 뒤에만 하고, 확인이 없으면 스크립트가 스스로 멈춘다. 방향은 회사 -> 개인 단방향이며 개인 쪽에서는 개발하지 않는다. 계정 스킬을 저장소에 백업하는 일은 skill-repo-sync 담당이고, 이 스킬은 joule 저장소 두 곳의 동기화만 한다.
---

# joule 저장소 동기화 (회사 Gitea -> 개인 GitHub)

## 평소 하는 일

준비는 2026-11-07 에 다 끝났다 (`setup` 은 다시 돌리지 않는다). 평소에는 이 세 단계다.

```powershell
cd D:\Ljindong\skills-repo\joule-repo-sync
python scripts\sync_mirror.py preview    # 올라갈 것 확인 (fetch 포함)
python scripts\sync_mirror.py sync       # 사본 브랜치에 쌓기 - 로컬만, 끝에 검증이 돈다
python scripts\sync_mirror.py push       # GitHub 로 보내기 - 확인 입력이 있어야 나간다
```

Bash 로 돌릴 때는 한글이 깨지지 않게 `PYTHONIOENCODING=utf-8` 을 붙인다.
밀린 커밋 수만 보려면 `status`. `sync` 까지는 로컬이라 되돌리기 쉽고, 밖으로 나가는 것은 `push` 하나다.

**Claude 가 사용자 대신 돌릴 때**는 `preview` 와 `sync` 결과(올라갈 커밋 수, 빠지는 파일,
점검에서 나온 것, 검증 통과 여부)를 사용자에게 보여 주고 **"보낼까요?" 를 물은 뒤** `push` 한다.
승인을 받았으면 `push --confirmed` 로 돌린다. 승인은 그 턴에 받은 것만 유효하다.

**주간 작업이 이미 쌓아 둔 때**(아래 "주간 자동 sync")는 `preview` 가 "덧붙일 커밋 0 개" 로
나온다. 그때는 점검 결과가 **주간 로그**에 있으니 그것을 읽어 사용자에게 보고한 뒤 `push` 한다.

```powershell
Get-Content "$env:LOCALAPPDATA\joule-repo-sync\weekly.log" -Tail 60
```

## 주간 자동 sync (2026-11-07 설치)

Windows 작업 스케줄러에 `joule-repo-sync weekly` 가 등록돼 있다. **매주 금요일 17:00**,
`scripts\weekly_sync.ps1` 이 돌아 회사 저장소의 새 커밋을 **로컬 사본 브랜치에 쌓는다.**

**푸시는 하지 않는다.** 밖으로 나가는 일은 사람이 보고 승인한다는 규칙 그대로다.
쌓을 것이 있었으면 끝에 **알림 창**이 떠서 "올릴 커밋 N 개" 를 알려 준다. 사용자가 그것을 보고
"푸시해줘" 라고 하면 Claude 가 로그의 점검 결과를 보고한 뒤 `push` 한다.

- 로그: `%LOCALAPPDATA%\joule-repo-sync\weekly.log` - `preview`(점검 포함)와 `sync` 를 함께 남긴다.
  `preview` 를 먼저 돌리는 까닭은, `sync` 뒤에는 "덧붙일 커밋 0 개" 가 되어
  "사본에 처음 들어가는 확장자·폴더" 점검을 아무도 볼 수 없기 때문이다.
- 알림이 뜨는 때: 올릴 것이 생겼을 때, 또는 `sync` 가 끝내지 못했을 때(그때는 로그를 보라고 한다).
- 노트북이라 그 시각에 꺼져 있을 수 있어 `-StartWhenAvailable` 로 등록했다. 놓치면 다음에 켤 때 돈다.
- 시간 바꾸기: `.\install_weekly_task.ps1 -At 18:30 -Day Thursday` / 끄기: `-Remove`

`.ps1` 을 고칠 때는 **UTF-8 BOM 으로 저장한다.** Windows PowerShell 5.1 은 BOM 없는 UTF-8 을
cp949 로 읽어 한글 주석에서 파싱이 깨진다.

```powershell
$p = '...\weekly_sync.ps1'
$c = Get-Content -Raw -Encoding UTF8 $p
[System.IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding $true))
```

## 구조

joule 은 원래 개인 저장소에서 개발했는데 회사 업무에 필요해져 사본을 회사 Gitea 로 옮겼다.
개인 계정으로는 회사 Gitea 에 접근할 수 없어 저장소가 둘로 갈렸고, 지금은 **회사 저장소에서만 개발한다.**

```
[회사 저장소]                      [동기화 작업장]              [개인 GitHub]
D:\Mobase\asec_autotest_tool  ->  D:\Ljindong\joule       ->   ljindong1/Joule
개발은 여기서만                     *.dbc 를 걸러낸다              백업 (private)
                                                                    |
                                                                    v  (pull 만)
                                                        [개인 PC - 보기 전용]
                                                        D:\Python_Program\Joule
```

개인 PC 의 `D:\Python_Program\Joule` 은 joule 을 처음 개발하던 원조 폴더이고, 지금은
**받아서 보기만 한다** (사용자 결정 2026-11-07). 거기서 작업하지 않으므로 개인 -> 회사 방향은
여전히 없다. 그 PC 가 있다는 것은 **이력을 다시 쓸 때만** 문제가 된다 (아래 `rebuild`).

가운데를 거치는 까닭은 회사 저장소에서 바로 보내면 DBC 가 함께 올라가기 때문이다.
작업장의 브랜치 두 개가 역할이 다르다. 헷갈리면 사고가 난다.

- `main` = 회사 저장소를 그대로 받아 둔 것. **DBC 가 들어 있어 GitHub 로 나가면 안 된다.**
- `public` = `*.dbc` 를 떨어낸 것. 이것만 GitHub 로 간다.

## 정해진 규칙 (사용자 결정 2026-11-07)

1. **제외는 `*.dbc` 하나다.** 차종 표준 DB 는 고객사 자료라 사내 저장소에만 둔다.
   `src/joule/flash/assets/`(CVD·HAE 벤더 스크립트와 플래시 알고리즘 ELF)와
   `tests/golden/flash/` 는 **올린다** - 그 안에 암호 열쇠가 없고(HSM 열쇠는 `.bin` 안에 있고
   저장소에 없다) 사본이 private 이라, 백업으로서 코드가 돌아가는 쪽을 택했다.
2. **덧붙이기 전용.** 이미 올라간 커밋은 고치지 않고 force push 를 쓰지 않는다.
3. **회사 -> 개인 단방향.** 개인 쪽에서 작업하지 않으므로 역방향은 다루지 않는다.
4. **푸시는 반드시 사용자 확인 뒤에.**
5. **사본 커밋의 작성자·커밋터는 `ljindong <ljindong1@gmail.com>`** 으로 적는다
   (날짜·메시지·순서는 회사 것 그대로). 회사 저장소는 `jdlee@mobaseasec.com` 으로 커밋되는데,
   GitHub 는 author 메일이 계정에 등록된 것일 때만 작성자로 연결하고, 개인 저장소에 회사 메일을
   남기지 않으려는 뜻도 있다.

## preview 에서 사용자에게 보고할 것

`preview` 가 "사본에 새로 올라가는 것 점검" 을 찍는다. 기준은 회사 트리가 아니라 **지금 사본**이라,
회사 저장소에 오래 있었지만 사본에 처음 들어가는 파일도 여기서 드러난다.
이 세 줄은 그냥 흘리지 말고 사용자에게 옮긴다.

- **사본에 처음 들어가는 확장자** - 새 종류의 자료가 섞여 들어오는 신호다.
  `.xls` `.pdf` `.dbc` `.arxml` `.bin` 같은 것이 뜨면 올려도 되는지 먼저 묻는다.
- **사본에 처음 들어가는 최상위 폴더** - 새 자료 묶음이 생겼다는 뜻이다.
- **1MB 넘는 파일** - 백업에 큰 바이너리가 들어오는지 본다.

이 점검이 있는 까닭: 2026-10-27 에 정한 제외 규칙만 믿고 돌렸다면, 그 뒤 `tests/golden/flash/` 로
새로 들어온 벤더 스크립트 본문이 점검 없이 올라갔을 것이다. **제외 규칙은 시간이 지나면 낡는다.**

## 푸시 규약 (사용자 요구)

푸시는 되돌리기 어렵고 밖으로 나가는 일이라, **사용자가 그 자리에서 승인한 뒤에만** 한다.

- `push` 를 묻지 않고 실행하지 않는다. 승인은 그 턴에 받은 것만 유효하다.
- 스크립트도 스스로 막는다: 확인 입력(`push` 라고 타이핑)이 없거나 비대화형이면 멈춘다.
  사용자 승인을 받은 뒤에만 `--confirmed` 를 붙인다.
- `push` 는 보내기 전에 **무엇이 나가는지** 찍는다 (대상 저장소, 커밋 수, fast-forward 여부,
  빠지는 패턴, 사본 작성자). private 이 아니면, 검증이 통과하지 못하면,
  fast-forward 가 아닌데 `--force` 가 없으면 멈춘다.

## 안전망 (실기 확인됨)

- `pre-push` 훅: GitHub 로 가는 ref 안에 `.dbc` 가 있으면 거부한다.
  `main` 을 실수로 밀면 막힌다 - 2026-11-07 에 실제로 막히는 것을 확인했다.
- `remote.origin.push = refs/heads/public:refs/heads/main`: `git push origin` 만 쳐도 사본만 나간다.
- `branch.main.remote = company`: 작업장 `main` 의 기본 상대가 회사 저장소다.
- `verify`(`sync` 끝에 자동): 사본과 회사 트리의 차이가 **빠진 DBC + 안내를 덧붙인 두 파일**뿐인지
  본다. 설명되지 않는 차이가 하나라도 있으면 푸시하지 않는다.
- private 확인: 토큰 없이 `api.github.com` 을 두 번 읽는다. 확실히 public 인 저장소를 대조군으로
  먼저 읽어, 404 가 "private" 때문인지 "네트워크 차단" 때문인지 가린다. 판정이 안 되면 푸시하지 않는다.

## 사내망 밖(집)에서도 돈다

사내 Gitea 는 사내에서만 닿지만 동기화는 집에서도 된다. 이 스킬이 **회사 저장소를 로컬 폴더로
읽기** 때문이다 - 작업장의 `company` 원격은 네트워크 URL 이 아니라 경로
`D:/Mobase/asec_autotest_tool` 이고, 회사 폴더에 보내는 git 명령은 `status` 와
`remote get-url`(설정 읽기)뿐이다. **Gitea 에는 접속하지 않는다.** 네트워크가 필요한 곳은
GitHub 하나다 (사본 fetch·push, private 판정).

그래서 동기화 기준은 **회사 폴더의 로컬 `main` 브랜치**다. 사내에서 한 커밋이 그 폴더에
들어 있어야 사본에 올라간다. "사내에서 커밋했는데 사본에 없다" 면 그 폴더가 아직 그 커밋을
받지 못한 것이다 (사내망에서 `git pull` 한 뒤 다시 돌린다).

## 어떻게 쌓는가 (원리)

`git filter-repo` 는 이 PC 에 없고, 매번 전체를 다시 쓰면 공개 커밋 해시가 계속 바뀐다.
그래서 **회사 커밋 하나하나의 트리를 가져와 `*.dbc` 만 빼고 `public` 에 `commit-tree` 로 쌓는다.**

- 트리를 통째로 가져오므로 충돌이 없고, 날짜·본문·순서가 그대로 남는다.
- 각 사본 커밋 끝에 `Mirror-Of: <회사 커밋 sha>` 를 붙인다. 이것이 **다음 동기화의 기준점**이라,
  로컬 파일이나 ref 가 사라져도 사본 자체에서 "어디까지 반영했나" 를 알 수 있다.
- 제외 파일만 바꾼 커밋은 내용이 비지만 그대로 쌓는다 - 커밋이 1:1 로 대응해야 추적이 끊기지 않는다.

README 와 `.gitignore` 에는 **파일 끝에 안내를 덧붙인다** (매 커밋 트리에 다시 적용한다).
사본이 사내 저장소의 백업이라는 것, `*.dbc` 가 빠졌다는 것, `Mirror-Of` 가 무엇인지를 적는다.
끝에 덧붙이는 까닭: 2026-10-27 에는 README 본문 중간에 끼워 넣었는데, 그 문단이 그대로 굳어
명령 이름이 바뀐 뒤에도 옛 이름(`joule-bench`, `joule-project`)을 설명하고 있었다.

## 되돌리기

`sync` 가 쌓은 것이 잘못됐으면 (아직 푸시 전이라면) 사본 브랜치를 전으로 돌린다.
기준점은 그 커밋의 `Mirror-Of` 로 자동으로 함께 돌아간다.

```powershell
cd D:\Ljindong\joule
git reflog public                        # 전 위치를 찾는다
git update-ref refs/heads/public <전 sha>
```

푸시한 뒤에 잘못을 발견했다면 되돌리지 말고 **회사 저장소에서 고쳐 커밋하고 다시 동기화한다**
(덧붙이기 전용이라 그게 자연스럽다).

## 흔한 문제

| 증상 | 까닭과 조치 |
|---|---|
| `[중단] 작업장에 커밋 안 된 변경이 있다` | 작업장은 동기화 전용이다. 거기서 파일을 고치지 않는다. `git -C D:\Ljindong\joule checkout .` 로 되돌린다 |
| `[중단] 기준점이 회사 tip 의 조상이 아니다` | 회사 저장소 이력이 갈렸다(rebase·force push). 사용자에게 알리고 어떻게 맞출지 정한다 |
| `[중단] private 임을 확인하지 못했다` | 네트워크가 막혔거나 저장소가 public 이 됐다. 공개 상태를 확인한 뒤에만 `--allow-public` |
| `[경고] 설명되지 않는 차이` | 사본과 회사 트리가 제외·안내 밖에서 다르다. 푸시하지 말고 원인을 찾는다 |
| 회사 저장소에 커밋 안 된 변경이 있다는 알림 | 동기화는 커밋된 것만 다룬다. 먼저 커밋할지 사용자에게 묻는다 |
| `[중단] 기준점을 찾지 못했다` | 사본 tip 에 `Mirror-Of` 가 없다. 지금은 모든 사본 커밋에 박혀 있어 날 일이 없다 - 났다면 사본을 밖에서 손댄 것이다. `--from <회사 커밋>` 으로 한 번 준다 |
| 받아 보는 PC 에서 `fatal: refusing to merge unrelated histories` | `rebuild` 로 이력을 다시 쓴 뒤 그 PC 가 처음 pull 한 것이다. 아래 절차로 맞춘다 |

### 받아 보는 PC 맞추기

이력을 다시 쓴 뒤에만 필요하다. **먼저 그 PC 에만 있는 작업이 없는지 확인한다** - 있으면 맞추는 순간 사라진다.

```bash
cd /d/Python_Program/Joule
git log --oneline <전 origin/main sha>..main    # pull 화면에 찍힌 옛 sha
git status --short
```

둘 다 비어 있으면 맞춘다. 무언가 나오면 사용자에게 보이고, 그 커밋을 새 이력 위로 옮긴 뒤에 맞춘다.

```bash
git branch backup-<날짜> main      # 되돌릴 가지
git reset --hard origin/main
git log --oneline -1               # 사본 tip 과 같으면 끝
```

추적하지 않는 파일(로컬 DBC 등)은 `reset --hard` 가 건드리지 않는다.

## 하지 않는 일

- 개인 -> 회사 방향은 다루지 않는다. 개인 쪽에서 작업할 일이 생기면 설계부터 사용자와 다시 정한다.
- 회사 저장소를 고치거나 커밋하지 않는다. 읽기만 한다. 사내 Gitea 에 접속하지도 않는다.
- 회사 폴더에서 GitHub 로 직접 푸시하지 않는다 (그 폴더에 `github` 원격이 남아 있지만
  DBC 가 든 `main` 이 거기 있다). 사본으로 보내는 일은 작업장의 `public` 브랜치만 한다.
- `setup` 을 다시 돌리지 않는다 (이미 깔려 있다. `status` 가 돌면 깔린 것이다).
- `CLAUDE.md` 는 두 저장소 모두 git 제외다. 백업이 필요하면 사용자에게 물어 파일만 복사한다.

## rebuild (평소에는 쓰지 않는다)

`rebuild` 는 사본 이력을 루트부터 다시 만든다. **제외 규칙이나 작성자처럼 과거 이력까지 걸리는 것을
바꿀 때만** 쓰고, 푸시에 `--force` 가 필요하다. 평소 동기화는 `sync` 다 -
**사용자가 콕 집어 요청하지 않으면 쓰지 않는다.**

쓸 때는 `--force` 가 무엇을 버리는지(GitHub 의 지금 이력) 사용자에게 분명히 말하고 승인을 받는다.
`--force-with-lease` 로 보내므로 GitHub 쪽이 그 사이 바뀌었으면 거부된다.
전 사본은 `refs/sync/public-before-rebuild` 에 남아 푸시 전이라면 되돌릴 수 있다.

**다른 PC 의 clone 도 함께 맞춰야 한다.** 이력을 다시 쓰면 사본을 받아 둔 쪽은 공통 조상이
없어져 `git pull` 이 `fatal: refusing to merge unrelated histories` 로 멈춘다.
지금 받아 보는 곳은 개인 PC 의 `D:\Python_Program\Joule` 하나다 - force push 를 승인받을 때
**그 PC 도 맞춰야 한다는 것을 함께 말한다.** 맞추는 법은 아래 "흔한 문제" 에 있다.

`rebuild` 는 돌면서 스스로 세 가지를 확인하고, 하나라도 어긋나면 종료 코드가 0 이 아니다:
**1:1 대조**(커밋 수·날짜·제목·`Mirror-Of` 짝) · **최신 트리 비교**(전 사본과 같은지) · **verify**.
merge 커밋이 있는 이력은 선형 재생성으로 다룰 수 없어 스스로 멈춘다.

2026-11-07 에 이것으로 사본 이력 187 개를 다시 만들어 한 번 force push 했다 (작성자를 개인 계정으로
통일하고, 제외를 `*.dbc` 하나로 좁히려고). 그 전 사본은 `*.dbc` 와 `assets/` 를 함께 뺀 132 개였고
작성자가 섞여 있었다. **그 뒤로는 덧붙이기만 한다.**
