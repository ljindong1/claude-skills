# PR 브랜치 구성 · PR 생성 (모드 D)

`devel_` 작업 브랜치에는 Jenkins 자동 커밋(`Auto commit from Jenkins #N`), 빌드 스크립트, `JENKINS_BUILD_TARGET`, 중간 산출물, 빌드 로그가 섞인다(`GitPush.bat` 이 `git add -f .` 로 담는다). 그래서 작업 브랜치를 그대로 머지하지 않고, 필요한 변경만 골라 **PR 브랜치**를 새로 만든 뒤 PR 을 연다.

작업 트리를 건드리지 않도록 **임시 인덱스(GIT_INDEX_FILE) + commit-tree** 로 만든다. 사용 실적: HE1i APP PR #4·#5, FBL PR #2·#5 (2026-10-08~13), NQ6e FBL PR #6 · APP PR #6 (2026-10-20).

Redmine 기록은 이 문서 범위가 아니다(redmine-issue). 여기서는 일감 번호를 **받아서 PR 제목·본문·커밋 메시지에 쓰기만** 한다.

## 1. 먼저 정할 것

| 항목 | 정하는 법 |
|---|---|
| 기준 커밋 | 작업 브랜치가 갈라져 나온 지점. `git merge-base --is-ancestor origin/<후보> HEAD` 로 확인 |
| PR 대상 브랜치 | 기준 커밋이 있는 브랜치. 그 브랜치가 아직 develop 계열에 머지되지 않았으면 **그 feature 브랜치**가 대상(HE1i FBL PR #2, NQ6e PR #6). 머지된 뒤면 develop 계열 |
| PR 브랜치 이름 | FBL `feature/swp_patch_v<x>_<차종>`, APP `feature/<차종소문자>_swp_patch_v<x>` (기존 이름 형식을 저장소에서 먼저 확인) |
| 일감 번호 | 사용자에게 받는다. **기준 커밋의 `end #N` 을 물려받지 않는다** — 그 일감이 이 차종·제어기 일감인지 Redmine 제목으로 확인한다(#48548 은 NQ6e/**APSU** 일감인데 PSU 커밋에 들어간 사례, 2026-10-20) |
| 넣을 산출물의 빌드 | **서명·평가한 빌드 번호**(대개 ALL 빌드 #N). 아래 §4 |

## 2. 넣을 것 / 뺄 것

`git diff --name-only --no-renames <기준> HEAD` 를 아래로 나눈다. 분류되지 않은 경로가 남으면 사용자에게 묻는다.

**넣는다**

| 경로 | 비고 |
|---|---|
| 설정·소스 변경 (`Configuration/`, `Build/SCons.arxml`, `Build/input_files.yml`, `RteGen.ini`, `.cproject`, `Static_Code/`, `Application/` 등) | `PJ_Define.h` 는 아래 예외 |
| `Generated/` (Bsw_Output·Mcal_Output, `module_hash.json`, `timestamp.result`) · `.scons_arxml_cache` | 평가한 빌드 기준 |
| 산출물 `Debug/OEUK_<차종>/` (APP 버전 폴더 4벌, FBL `OEUK_<차종>`·`OEUK_<차종>_TEST`) | 그 차종 폴더만 통째로 교체 |
| `Debug/` 바로 아래 `.dla`·`.dnm`·`.elf.opt`, `Debug/exclude_list.txt` | FBL·APP PR 선례대로 |
| `BuildWarning.xlsx`, FBL `.sconsign.dblite` | FBL PR #5 선례(넣음). APP 는 `.sconsign.dblite` 뺌 |
| APP `References/02_Fbl_Binary/` | FBL 바이너리 커밋 |
| 평가 결과 폴더 `References/Doc_MB/04_Reprogramming/v<x>/<YYMMDD>/` | 대개 작업 트리에만 있다(추적 안 됨). §3 |

**뺀다**

| 경로 | 이유 |
|---|---|
| `Build/Build_Hook_GIT_ASEC.bat`, `Build_Hook_<차종>.bat`, `GitPush.bat`, `PostPackage.bat`, `BuildVariants.bat`, `PJ_Variant.ps1` | 개인 Jenkins Job 용 |
| `PJ_Define.h` 전체 | `JENKINS_BUILD_TARGET` 와, ALL 빌드를 위해 바꾼 OEUK 선택 줄(예: SX3E → NQ6E)·줄 순서. **기준 브랜치 값을 그대로 둔다** |
| `.log/`, `workspace/.metadata`, `Build/site_scons/__pycache__` | 빌드 로그·IDE·파이썬 캐시 |
| `Debug/Application/`, `Debug/Generated/`, `Debug/Static_Code/` | 컴파일 중간 산출물 |
| `References/Doc_MB/01_CRT_UTIP_CFG/aSIMs_sample_ini.ini` | 빌드가 만든 서명 도구 샘플(기준 브랜치에 없음) |
| **다른 차종 `Debug/OEUK_*` 의 삭제** | `PostPackage.bat` 이 작업 브랜치에서 지운 것. 공용 저장소라 PR 에서는 **지우지 않고 유지** |

`PJ_Define.h` 를 빼므로 PR 이 머지돼도 기준 브랜치는 원래대로 단일(CURRENT) 빌드다. 작업 브랜치의 CURRENT 원복은 PR 과 무관한 개인 정리라 PR 본문·일감에 쓰지 않아도 된다.

## 3. 커밋 구성

- **FBL**: squash 1개. 경로마다 작업 브랜치 HEAD 값으로 맞춘다(없으면 삭제).
- **APP**: 순서대로 쌓는다(HE1i APP PR #4 형식). 해당 없는 커밋은 건너뛴다.

| 순서 | 커밋 | 출처 |
|---|---|---|
| 1 | 패치·소스 변경 | 작업 브랜치 커밋 (diff 를 임시 인덱스에 apply) |
| 2 | FBL Binary Commit | `References/02_Fbl_Binary/` |
| 3 | Generated 갱신 | 평가 빌드의 `Generated/`, `.cproject`, `.scons_arxml_cache`, `input_files.yml`, `RteGen.ini` |
| 4 | 평가 결과 | 결과 폴더 (작업 트리 파일을 `update-index --add`) |
| 5 | 빌드 산출물 | 평가 빌드의 `Debug/OEUK_<차종>/` + `Debug/` 루트 파일 |

평가 결과 폴더는 사용자가 정리한 그대로 넣는다. 원본 asc·log·png·bin 을 확장자별 zip 으로 묶은 형태도 있다(NQ6e 261020, 약 83MB). **zip 파일을 다시 zip 으로 묶지 않는다.**

커밋 제목은 `end #<일감> [<차종>][<제어기>][<APP|FBL>][V<x>] <내용>`. 제목만으로 무엇이 들었는지 알게 쓴다.

## 4. 산출물은 평가한 빌드에서

ALL 로 빌드해 서명·H-OTA 평가를 마친 뒤 CURRENT 로 되돌리면 Jenkins 가 한 번 더 빌드한다. 이 빌드는 평가본과 **바이트가 다를 수 있다** — NQ6e APP 2026-10-20 #4 는 `Os_Cfg.c` 태스크 스택 8개의 배치 순서만 바뀌어(크기 같음) 26310 이미지의 주소·헤더 체크섬이 달랐다. FBL #4 는 `.sre`·`.hex` 가 같았다.

그래서 넣을 경로의 값은 **평가 빌드 커밋**(예: `Auto commit from Jenkins #3`)에서 가져오고, 원복 뒤 빌드는 쓰지 않는다. 원복 커밋 전에 PR 브랜치를 만들었다면 HEAD 가 곧 평가 빌드다.

## 5. 명령 골격 (Git Bash)

```bash
S=<scratchpad>; B=$(git rev-parse origin/<기준 브랜치>); SRC=<평가 빌드 커밋>
git diff --name-only --no-renames $B $SRC > $S/all.txt      # §2 로 나눠 g1.txt … 를 만든다
git ls-tree -r $SRC --full-tree > $S/tree.txt

export GIT_INDEX_FILE=$S/pr.index; rm -f "$GIT_INDEX_FILE"
git read-tree $B; HEADC=$B

# 경로 묶음 하나를 SRC 값으로 : 먼저 지우고(--force-remove) 다시 채운다 (SRC 에 없는 경로는 삭제로 남는다)
git update-index --force-remove --stdin < $S/g1.txt
python -c "..."   # tree.txt 에서 g1.txt 경로만 골라 idx.txt 로 — 반드시 newline='\n' 으로 쓴다
git update-index --index-info < $S/idx.txt

# 작업 트리에만 있는 결과 폴더
git -c core.quotepath=false ls-files -o --exclude-standard -- <결과 폴더> > $S/g3.txt
git update-index --add --stdin < $S/g3.txt

# 커밋 : 메시지는 파일로, 제목 뒤 빈 줄
HEADC=$(git commit-tree $(git write-tree) -p $HEADC -F $S/msg1.txt)
# … 묶음마다 반복
unset GIT_INDEX_FILE
git branch -f <PR 브랜치> $HEADC
```

패치 커밋을 그대로 옮길 때(APP 1번): `git diff --binary --no-ext-diff --no-textconv C~1 C > p.diff && git apply --cached --whitespace=nowarn p.diff` — 외부 diff·textconv 를 꺼야 PDF 등에서 끊기지 않는다.

## 6. 검증 (push 전)

- 넣은 경로가 평가 빌드와 diff 0 : `xargs -d '\n' git diff --quiet <PR 브랜치> <SRC> -- < 넣은목록`
- 결과 폴더가 작업 트리와 diff 0 : `git diff --quiet <PR 브랜치> -- <결과 폴더>`
- 작업 브랜치와 남은 차이를 폴더별로 세어(`git diff --name-only <PR> HEAD | sed … | uniq -c`) **§2 뺀다 표와 1:1** 인지
- `git log --oneline` 으로 체인·제목 확인
- 사용자에게 커밋 목록, 넣은 것·뺀 것, PR 대상·제목·본문을 보여 주고 **승인 후** push·PR 생성

## 7. push · PR 생성

```bash
G=(-c credential.helper= -c http.extraHeader="Authorization: token $GITEA_TOKEN")
git "${G[@]}" push origin <PR 브랜치>
```

- 자격 증명 관리자 저장값이 `Authentication failed` 를 낼 수 있다(2026-10-12, 10-20) — fetch·pull·push 모두 위 형식을 쓴다.
- `feature/*` 브랜치 push 는 Jenkins Job(`*/devel_<차종>_<ID>_*`)에 걸리지 않는다. 작업 브랜치 push 는 빌드가 돈다.
- PR 은 Gitea API `POST /api/v1/repos/<owner>/<repo>/pulls` (`title`, `body`, `head`, `base`). JSON 은 UTF-8 파일로 만들어 `--data-binary @file` 로 보낸다. 결과의 `number`·`mergeable` 을 보고한다.
- 본문 형식: 일감 줄 → 커밋 표(APP) 또는 변경 요약(FBL) → 평가 → 의도적으로 넣지 않은 것 → 참고(상대 저장소 PR, 작업 브랜치, 일감 번호 오기 설명). 끝에 attribution 줄.
- PR 제목·본문 수정은 `PATCH .../pulls/<번호>` (예: 일감 번호 교체). 커밋 메시지까지 고치려면 PR 브랜치 강제 push 가 필요하므로 사용자에게 따로 묻는다.

## 8. 함정

| 증상 | 원인 · 대처 |
|---|---|
| `update-index --index-info` 가 `Ignoring path …` 만 내고 아무것도 안 들어감 | 파이썬이 Windows 에서 `\r\n` 으로 써서 경로 끝에 `\r` 이 붙음. 파일로 쓰고 `newline='\n'` 지정 |
| `sed -i` 로 `PJ_Define.h` 한 줄을 바꾼 뒤 `LF will be replaced by CRLF` 경고 | 저장소 blob 이 LF 면 문제 없음. `git show HEAD:<파일> \| grep -c $'\r$'` 로 전후 줄바꿈이 같은지 확인 |
| PR diff 에 다른 차종 산출물 삭제가 잔뜩 보임 | `PostPackage.bat` 정리분이 섞인 것. §2 대로 유지 |
| 일감 번호가 다른 제어기 일감 | 기준 커밋 메시지를 물려받음. PR 본문에 "커밋 메시지의 #N 은 오기, 기준 일감 #M" 한 줄 |
