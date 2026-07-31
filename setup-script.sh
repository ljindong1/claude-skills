#!/bin/bash
# ── JIns 클라우드 환경 설정 스크립트 ──
# 목적: 세션 시작 시 저장소의 스킬 전부를 Claude Code 로드 경로(~/.claude/skills/)에 설치.
#
# 전제 저장소 구조 (스킬 폴더가 저장소 최상위에 바로 놓임):
#   repo/
#   ├── slack-morning-briefing/SKILL.md
#   ├── slack-to-calendar/SKILL.md
#   └── arxml-analyzer/SKILL.md   (몇 개든 폴더로 추가 가능)
#
# 사용법: 이 파일 내용을 클라우드 환경 설정의 "설정 스크립트" 칸에 붙여넣으면 끝.
#         스킬을 추가해도 이 스크립트는 고칠 필요 없음 (SKILL.md 를 가진 폴더를 자동으로 찾는다).
#
# 참고: SSH 별칭(git@github.com-ljindong:...) 이 아니라 HTTPS 주소를 쓴다.
#       클라우드 컨테이너에는 SSH 키가 없어서 공개 저장소를 HTTPS 로 받아야 한다.
set -euo pipefail

REPO_URL="https://github.com/ljindong1/claude-skills.git"
TMP_DIR="$(mktemp -d)"
SKILLS_ROOT="$HOME/.claude/skills"

# 1) 저장소 clone (최신만 얕게)
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

# 2) 저장소 최상위의 스킬 폴더(SKILL.md 를 가진 폴더)만 골라 로드 경로에 복사
#    README.md, setup-script.sh, .git 등 스킬이 아닌 항목은 제외된다.
mkdir -p "$SKILLS_ROOT"
FOUND=0
while IFS= read -r dir; do
  cp -a "$dir" "$SKILLS_ROOT"/
  FOUND=$((FOUND + 1))
done < <(find "$TMP_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md -printf '%h\n' | sort)
test "$FOUND" -ge 1 || { echo "[설치 실패] 저장소 최상위에 스킬 폴더가 없음"; exit 1; }
rm -rf "$TMP_DIR"

# 3) 설치 검증(assert): SKILL.md를 가진 스킬 폴더가 하나 이상인지 + 목록 출력
INSTALLED=$(find "$SKILLS_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)
test "$INSTALLED" -ge 1 || { echo "[설치 실패] 설치된 스킬 없음"; exit 1; }
echo "[설치 완료] 스킬 $INSTALLED개:"
find "$SKILLS_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md -printf "  - %h\n" | sed "s#$SKILLS_ROOT/##"
