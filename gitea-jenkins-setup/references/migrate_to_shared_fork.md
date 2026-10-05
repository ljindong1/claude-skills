# 개인 Fork → 공유 Fork 이전 절차

`원본 → tglee(공유 Fork) → jdlee(개인 Fork) → clone` 구조를 **`원본 → tglee → clone`** 으로 줄이는 절차다. 개인 Fork 층을 없애 작업 브랜치·Jenkins 결과물이 공유 Fork 에 바로 쌓이게 한다. HE1i PSU APP·FBL(2026-10-05)에 실제로 적용한 순서다.

> ⚠️ **이 절차만 기존 자원을 수정·삭제한다.** 사용자가 "jdlee fork 를 없애 달라", "tglee 로 옮겨 달라"처럼 **명시적으로 요청했을 때만** 쓴다. 계획을 먼저 보여 주고 승인받은 뒤 진행하며, 마지막 Fork 삭제는 **실행 직전에 한 번 더** 묻는다.

## 0. 먼저 확인할 것 (읽기만)

| 확인 | 명령 | 통과 조건 |
| --- | --- | --- |
| 공유 Fork 에 내가 쓸 수 있는가 | `repo-info --repo tglee/<repo>` | `mode: C`, `can_push: true` |
| build 계정 권한 | `collab --repo tglee/<repo> --user build --check-only` | `exists` (write 이상). `missing` 이면 **중단** — 소유자에게 요청 |
| 지금 Job | `job-match --repo-url <개인 Fork URL> --branch <작업 브랜치>` | 옮길 Job 이름 확인 |
| 공유 Fork 에 같은 Branch Specifier 를 받는 Job 이 이미 있는가 | `job-match --repo-url <공유 Fork URL> --branch <새 브랜치>` | `no_match` 여야 한다. `matched` 면 그 Job 을 쓰고 기존 Job 은 옮기지 않는다 (중복 빌드 방지) |

계획을 보여 줄 때 정해 받을 것:

- **브랜치 이름**: 2번째 칸이 개발 단계(`LP2`)면 차종 코드로 바꾸기를 권한다. 예: `devel_LP2_jdlee_FBL_patch_Update` → `devel_HE1i_jdlee_FBL_patch_Update`
- **Job**: 기존 Job 을 고쳐 쓰기(**권장** — 빌드 이력·빌드 명령·인증정보·권한이 그대로) / 새로 만들고 기존 Job 삭제

## 1. 작업 브랜치를 공유 Fork 로

```
git -C <clone> push <공유 Fork URL> <옛 브랜치>:refs/heads/<새 브랜치>
```

- 인증은 `gjsetup.git_auth_args()` 헤더로 한다 (토큰 출력 금지). 일반 `git push` 는 `Failed to authenticate user` 가 날 수 있다.
- Jenkins 자동 커밋(빌드 산출물)도 같이 올라간다. 원래 그런 브랜치다.

## 2. 로컬 clone 전환 (작업 폴더는 그대로)

```
git remote set-url origin <공유 Fork URL>
git fetch --prune origin                       # 토큰 헤더 사용
git branch -m <옛 브랜치> <새 브랜치>           # 이름을 바꾼 경우
git branch -u origin/<새 브랜치>
```

`git status -sb` 가 `<새 브랜치>...origin/<새 브랜치>` 이고 `HEAD` 와 원격이 같은 커밋이면 된다. 커밋 안 한 파일은 그대로 남는다.

## 3. Jenkins Job 전환

기존 Job 을 고쳐 쓰는 경우:

```
python gjsetup.py job-retarget --name <Job> --repo-url <공유 Fork URL> --branch-spec "*/devel_<차종>_<ID>_*" --description "<설명>" --backup <임시폴더>
python gjsetup.py job-rename   --name <Job> --new-name <새 Job 이름>
```

- `job-retarget` 은 저장소 URL·Branch Specifier·설명만 바꾸고, 바꾸기 전 `config.xml` 을 `--backup` 폴더에 남긴다. `checks.other_unchanged` 가 true 여야 한다 (빌드 명령·필터·권한 등 나머지가 그대로).
- **이름이 대소문자만 다르면**(`HE1I_PSU_FBL_jdlee` → `HE1i_PSU_FBL_jdlee`) Jenkins 가 "이미 사용 중"으로 거절한다(Windows 서버라 이름을 대소문자 구분 없이 본다). `job-rename` 이 `<새 이름>_renaming` 을 거쳐 두 번에 바꾼다. 워크스페이스 폴더는 같은 폴더로 이어서 쓴다.
- 빌드 명령이 옛 형태(표준 훅 직접 호출)면 `if exist` 분기로 바꿔야 전용 훅이 돈다 — `build_command()` 와 같은 내용. 사용자 승인 후 같은 방식(백업 → POST → 다시 읽어 확인)으로 바꾼다.

## 4. 동작 확인

```
git commit --allow-empty -m "[<제어기>][<차종>] Jenkins 빌드 테스트 (<공유 Fork> 저장소 전환 확인)"
git push origin <새 브랜치>
```

Console Output 에서 확인:

- `Checking out Revision <방금 커밋> (origin/<새 브랜치>)`
- `[GitPush] branch : <새 브랜치>` → `Finished: SUCCESS`
- 자동 커밋이 공유 Fork 에 올라오면 `git pull` 로 받는다

## 5. 개인 Fork 삭제

```
python gjsetup.py fork-retire --fork jdlee/<repo> --target tglee/<repo> --path <clone> --map <옛 브랜치>=<새 브랜치>
python gjsetup.py fork-retire ... --delete        # 위가 contained 이고 사용자가 승인한 뒤에만
```

- 개인 Fork 의 **모든 브랜치**를 임시 참조로 받아, 공유 Fork 쪽 브랜치에 없는 커밋이 있는지 센다. 이름을 바꾼 브랜치는 `--map` 으로 짝을 지어 준다. 임시 참조는 끝나면 지운다.
- 하나라도 `fork_only_commits` 가 0 이 아니거나 짝이 없는 브랜치가 있으면 `not_contained` 로 멈추고 **삭제하지 않는다**. 그 브랜치를 어떻게 할지 사용자와 정한다.
- 삭제는 되돌릴 수 없다. 단, 모든 내용이 공유 Fork 에 있으므로 필요하면 다시 Fork 할 수 있다는 점을 함께 알린다.
- 삭제 후 `after: 404` 를 확인하고, 그 Fork 를 보던 Job 이 남지 않았는지 `job-match` 로 본다.

## 결과 보고 형식

```
| 단계 | 결과 |
| 1. 브랜치 이동 | <새 브랜치> 로 tglee/<repo> 에 push |
| 2. 로컬 clone | origin → tglee/<repo>, 추적 연결 |
| 3. Jenkins Job | URL·Branch Specifier·설명 변경, 이름 <새 이름> (이력 유지) |
| 4. 동작 확인 | #N SUCCESS, 자동 커밋 tglee 에 push, pull 완료 |
| 5. Fork 삭제 | 비교 결과 Fork 에만 있는 커밋 0 → 삭제 (404 확인) |
```
