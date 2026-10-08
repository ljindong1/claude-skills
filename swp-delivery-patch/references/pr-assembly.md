# PR 브랜치 구성 (S13)

작업 브랜치(Jenkins 자동 커밋·중간 산출물·빌드 로그가 섞임)에서 필요한 변경만 골라 PR 브랜치를 만든다. 작업 트리를 건드리지 않도록 **임시 인덱스(GIT_INDEX_FILE) + commit-tree** 로 만든다. 2026-10-08 HE1i V3.0.29 APP PR #4 · FBL PR #2 에서 쓴 방법이다.

## APP — 버전별 feature 에 커밋을 쌓는다

기준: 앞 버전 feature 브랜치 끝 (앞 PR 이 머지 전이면 그 브랜치를 PR 대상으로, 머지 후 develop_he1i 로 변경)

| 순서 | 커밋 | 출처 |
|---|---|---|
| 1 | SWP 모듈 패치 적용 | 작업 브랜치 패치 커밋 cherry-pick (diff 를 임시 인덱스에 apply) |
| 2 | FBL Binary Commit (있으면) | cherry-pick |
| 3 | Generated 갱신 | **서명·평가한 빌드**의 `Generated/Bsw_Output`, `.cproject`, `.scons_arxml_cache`, `Build/input_files.yml` |
| 4 | H-OTA 평가 결과 | 결과 폴더 (추가 시험 하위 폴더 제외) |
| 5 | 빌드 산출물 | 서명·평가한 빌드의 `Debug/OEUK_xxx/` 4벌 (폴더 통째 교체) |
| 6 | 추가 확인 결과 (있으면) | 결과 폴더의 하위 폴더 |

넣지 않는 것: `PJ_Define.h` 의 `JENKINS_BUILD_TARGET`, Jenkins 빌드 스크립트, `.log/`, `.sconsign.dblite`, `workspace/.metadata`, 개인 H-OTA 설정(`*_lee.hcfg-r`) — 사용자가 정한 경우.

## FBL — 앞 버전 feature 위에 squash 1개

변경 경로 = `git diff --name-only <앞 PR 완료 기준 커밋> HEAD` 에서 `.log/`, `workspace/`, `Debug/Generated/`, `Debug/Static_Code/` 를 뺀 것. 각 경로를 작업 브랜치 HEAD 값으로 맞춘다(없으면 삭제). 앞 feature 에 남은 옛 BuildWarning 같은 파일도 정리한다.

## 명령 골격 (Git Bash)

```bash
export GIT_INDEX_FILE=<scratch>/pr.index; rm -f "$GIT_INDEX_FILE"
git read-tree <기준>; HEADC=<기준>
# cherry-pick : 외부 diff·textconv 를 꺼야 PDF 등에서 끊기지 않는다
git diff --binary --no-ext-diff --no-textconv C~1 C > p.diff && git apply --cached --whitespace=nowarn p.diff
# 경로를 다른 커밋 값으로 : 먼저 지우고(--force-remove) 다시 채운다
git ls-files -s -- P | awk '{print $4}' | git update-index --force-remove --stdin
git ls-tree -r SRC -- P | git update-index --index-info
# 커밋 : 메시지는 파일로 (파이프로 함수에 넘기면 서브셸이라 HEADC 가 이어지지 않는다). 제목 뒤 빈 줄 필수
HEADC=$(git commit-tree $(git write-tree) -p $HEADC -F msg.txt)
git branch -f <PR 브랜치> $HEADC; unset GIT_INDEX_FILE
```

## 검증 (push 전)

- 경로별로 서명·평가 빌드와 diff 0 인지: Static_Code, Configuration, SCons, Generated, 02_Fbl_Binary, Debug/OEUK_xxx, 결과 폴더
- 남는 차이는 의도한 것뿐인지 (예: `JENKINS_BUILD_TARGET` 두 줄)
- `git log --oneline` 으로 체인·제목 확인

PR 은 Gitea API(`GITEA_URL`, `GITEA_TOKEN`)로 만들고 본문은 이전 PR 형식(개요 · 커밋 표 · 평가 · 의도적으로 넣지 않은 것 · 참고)을 따른다. 본문은 미리 보여 주고 승인 후 생성.
