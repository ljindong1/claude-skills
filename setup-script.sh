#!/bin/bash
# ── JIns 클라우드 환경 설정 스크립트 ──
# 목적: 세션 시작 시 저장소의 스킬 전부를 Claude Code 로드 경로(~/.claude/skills/)에 설치.
#
# 전제 저장소 구조:
#   repo/
#   └── .claude/skills/
#       ├── slack-morning-briefing/SKILL.md
#       ├── slack-to-calendar/SKILL.md
#       └── arxml-analyzer/SKILL.md   (몇 개든 폴더로 추가 가능)
#
# 사용법: 아래 REPO_URL만 본인 저장소로 바꾸면 끝. 스킬을 추가해도 이 스크립트는 고칠 필요 없음.
set -euo pipefail

REPO_URL="https://github.com/<사용자명>/<저장소명>.git"
TMP_DIR="$(mktemp -d)"
SKILLS_ROOT="$HOME/.claude/skills"

# 1) 저장소 clone (최신만 얕게)
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

# 2) 저장소 안 .claude/skills 아래 스킬 폴더를 통째로 로드 경로에 복사
SRC="$TMP_DIR/.claude/skills"
test -d "$SRC" || { echo "[설치 실패] 저장소에 .claude/skills 폴더가 없음"; exit 1; }
mkdir -p "$SKILLS_ROOT"
cp -a "$SRC"/. "$SKILLS_ROOT"/
rm -rf "$TMP_DIR"

# 3) 설치 검증(assert): SKILL.md를 가진 스킬 폴더가 하나 이상인지 + 목록 출력
INSTALLED=$(find "$SKILLS_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)
test "$INSTALLED" -ge 1 || { echo "[설치 실패] 설치된 스킬 없음"; exit 1; }
echo "[설치 완료] 스킬 $INSTALLED개:"
find "$SKILLS_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md -printf "  - %h\n" | sed "s#$SKILLS_ROOT/##"
