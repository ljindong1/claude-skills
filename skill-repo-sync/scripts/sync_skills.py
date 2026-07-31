#!/usr/bin/env python3
"""
sync_skills.py — 계정에 등록된 Claude 스킬을 git 저장소로 미러링하고 커밋한다.

원본(계정 스킬 폴더)과 저장소가 같은 파일시스템에서 모두 보일 때 쓴다.

원본은 항상 계정 쪽이다. 저장소 쪽 내용은 덮어쓴다. 그래서 커밋되지 않은
로컬 수정이 있으면 시작 전에 멈춘다 — 덮어쓰면 되돌릴 방법이 없기 때문이다.

manifest.json 이 있으면 그걸 쓰고, 없으면 원본 폴더를 훑어 SKILL.md 를 가진
폴더를 스킬로 인식한다. Cowork 세션에 마운트되는 원본에는 manifest.json 이
없는 경우가 있어서, 그것 하나 때문에 전체가 멈추지 않도록 한 것이다.

사용 예 (Cowork 샌드박스에서는 --source 를 반드시 지정):
    python3 sync_skills.py --repo /sessions/<세션>/mnt/skills-repo \
        --source /sessions/<세션>/mnt/.claude/skills --dry-run
    python3 sync_skills.py --repo /sessions/<세션>/mnt/skills-repo \
        --source /sessions/<세션>/mnt/.claude/skills --skills svg-creation --no-commit

커밋·푸시는 보통 사용자가 PowerShell 에서 한다 (샌드박스는 .git/index.lock 을
지우지 못하고 푸시 인증도 없다). 그래서 --no-commit 이 기본 권장이다.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SOURCE = Path.home() / ".claude" / "skills"
# 저장소 최상위에 있어도 스킬 폴더로 오해하면 안 되는 것들
NON_SKILL_ENTRIES = {".git", ".github", ".vscode", "node_modules", "_removed", "__pycache__"}


# ---------------------------------------------------------------- git helpers


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패:\n{proc.stderr.strip()}")
    return proc.stdout


def is_git_repo(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def has_remote(repo: Path) -> str | None:
    out = git(repo, "remote", check=False).strip()
    return out.splitlines()[0] if out else None


# ------------------------------------------------------------------ manifest


BUILTIN_SKILLS = {
    "docx", "pdf", "pptx", "xlsx", "skill-creator", "morning", "schedule",
    "setup-cowork", "consolidate-memory", "artifacts-builder", "canvas-design",
    "mcp-builder", "webapp-testing", "internal-comms", "slack-gif-creator",
}


def scan_manifest(source: Path) -> dict:
    """manifest.json 이 없을 때 폴더를 훑어 같은 모양의 정보를 만든다.

    SKILL.md 를 가진 최상위 폴더 하나가 스킬 하나다. 계정이 알려주는 source
    구분이 없으므로 이름으로 Anthropic 기본 스킬을 걸러낸다. 완벽하진 않지만,
    manifest 하나가 없다고 작업 전체를 막는 것보다 낫다.
    """
    skills = []
    newest = 0.0
    for entry in sorted(source.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "SKILL.md").is_file():
            continue
        mtime = max(
            (f.stat().st_mtime for f in entry.rglob("*") if f.is_file()),
            default=entry.stat().st_mtime,
        )
        newest = max(newest, mtime)
        skills.append({
            "name": entry.name,
            "source": "builtin" if entry.name in BUILTIN_SKILLS else "custom",
            "updatedAt": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
        })
    return {
        "skills": skills,
        "lastUpdated": int(newest * 1000) if newest else None,
        "_scanned": True,
    }


def load_manifest(source: Path) -> dict:
    path = source / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    manifest = scan_manifest(source)
    if not manifest["skills"]:
        raise SystemExit(
            f"원본에서 스킬을 찾지 못했습니다: {source}\n"
            "--source 로 계정 스킬 폴더 경로를 지정하세요."
        )
    print(f"[안내] manifest.json 이 없어 폴더 스캔으로 대체합니다 "
          f"(스킬 {len(manifest['skills'])}개 인식).")
    return manifest


def snapshot_time(manifest: dict) -> datetime | None:
    ms = manifest.get("lastUpdated")
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def select_skills(manifest: dict, names: list[str], include_builtin: bool) -> list[dict]:
    entries = manifest.get("skills", [])
    if names:
        wanted = {n.strip().lower() for n in names}
        chosen = [s for s in entries if s["name"].lower() in wanted]
        missing = wanted - {s["name"].lower() for s in chosen}
        if missing:
            available = ", ".join(sorted(s["name"] for s in entries))
            raise SystemExit(
                f"다음 스킬을 계정에서 찾을 수 없습니다: {', '.join(sorted(missing))}\n"
                f"사용 가능: {available}"
            )
        return sorted(chosen, key=lambda s: s["name"])
    if include_builtin:
        chosen = entries
    else:
        chosen = [s for s in entries if s.get("source") == "custom"]
    return sorted(chosen, key=lambda s: s["name"])


# -------------------------------------------------------------------- mirror


def same_content(a: Path, b: Path) -> bool:
    """줄바꿈(CRLF/LF) 차이만 있는 경우는 같은 것으로 본다.

    Windows git 은 체크아웃 시 파일을 CRLF 로 저장하는데 계정 원본은 LF 다.
    바이트로만 비교하면 매 실행마다 전 파일이 '변경'으로 잡혀서, 정작 진짜
    변경이 그 안에 묻힌다. 내용이 같으면 굳이 덮어쓸 이유도 없다.
    """
    if filecmp.cmp(a, b, shallow=False):
        return True
    try:
        ta = a.read_text(encoding="utf-8")
        tb = b.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError):
        return False  # 바이너리는 바이트 비교가 정답
    return ta.replace("\r\n", "\n") == tb.replace("\r\n", "\n")


def mirror(src: Path, dst: Path, dry_run: bool) -> dict:
    """src 폴더 내용을 dst 에 그대로 반영한다. 변경된 파일 목록을 돌려준다."""
    added: list[str] = []
    modified: list[str] = []
    removed: list[str] = []

    src_files: set[str] = set()
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for name in files:
            abs_src = Path(root) / name
            rel = abs_src.relative_to(src).as_posix()
            src_files.add(rel)
            abs_dst = dst / rel
            if not abs_dst.exists():
                added.append(rel)
                if not dry_run:
                    abs_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(abs_src, abs_dst)
            elif not same_content(abs_src, abs_dst):
                modified.append(rel)
                if not dry_run:
                    shutil.copy2(abs_src, abs_dst)

    # 계정에서 사라진 파일은 스킬 폴더 안에서만 정리한다.
    # (저장소 최상위의 다른 파일이나 다른 스킬 폴더는 건드리지 않는다)
    if dst.exists():
        for root, dirs, files in os.walk(dst):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
            for name in files:
                abs_dst = Path(root) / name
                rel = abs_dst.relative_to(dst).as_posix()
                if rel not in src_files:
                    removed.append(rel)
                    if not dry_run:
                        abs_dst.unlink()
        if not dry_run:
            for root, dirs, files in os.walk(dst, topdown=False):
                p = Path(root)
                if p != dst and not any(p.iterdir()):
                    p.rmdir()

    return {"added": added, "modified": modified, "removed": removed}


def find_orphans(repo: Path, manifest: dict) -> list[str]:
    known = {s["name"] for s in manifest.get("skills", [])}
    orphans = []
    for entry in sorted(repo.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in NON_SKILL_ENTRIES or entry.name.startswith("."):
            continue
        if entry.name not in known:
            orphans.append(entry.name)
    return orphans


# ---------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description="계정 스킬을 git 저장소로 동기화하고 커밋한다.")
    ap.add_argument("--repo", required=True, help="스킬 저장소(git) 경로")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="계정 스킬 폴더 (기본: ~/.claude/skills)")
    ap.add_argument("--skills", nargs="*", default=[], help="특정 스킬만. 생략하면 내가 만든 스킬 전체")
    ap.add_argument("--include-builtin", action="store_true", help="Anthropic 기본 스킬도 포함")
    ap.add_argument("--dry-run", action="store_true", help="변경 내용만 보고 실제로는 쓰지 않는다")
    ap.add_argument("--allow-dirty", action="store_true", help="커밋 안 된 로컬 변경이 있어도 진행")
    ap.add_argument("--no-commit", action="store_true", help="복사만 하고 커밋하지 않는다")
    ap.add_argument("--push", action="store_true", help="커밋 후 원격에 푸시")
    ap.add_argument("--message", help="커밋 메시지 직접 지정")
    ap.add_argument("--json", action="store_true", help="마지막에 JSON 요약 출력")
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    source = Path(args.source).expanduser().resolve()

    if not source.is_dir():
        raise SystemExit(f"계정 스킬 폴더가 없습니다: {source}")
    if not repo.is_dir():
        raise SystemExit(f"저장소 폴더가 없습니다: {repo}")
    if not is_git_repo(repo):
        raise SystemExit(f"git 저장소가 아닙니다: {repo}\n먼저 `git init` 하거나 올바른 경로를 지정하세요.")

    # Windows git 은 체크아웃 시 파일을 CRLF 로 저장한다. 파일 비교는
    # same_content() 가 줄바꿈 차이를 무시하므로 여기서는 상황만 알린다.
    # 다만 샌드박스 git 의 설정이 다르면 git status 가 전 파일을 변경으로
    # 표시할 수 있어서, 그 경우의 대처를 함께 안내한다.
    autocrlf = git(repo, "config", "--get", "core.autocrlf", check=False).strip().lower()
    if autocrlf not in {"true", "input"}:
        print(
            "[안내] 이 저장소의 core.autocrlf 가 설정돼 있지 않습니다.\n"
            "       git status 가 실제 변경이 없는데도 전 파일을 변경으로 표시하면\n"
            "       `git -C <repo> config core.autocrlf true` 로 맞추세요.\n"
        )

    manifest = load_manifest(source)
    snap = snapshot_time(manifest)
    targets = select_skills(manifest, args.skills, args.include_builtin)

    print("=" * 68)
    print("원본 (계정 스킬):", source)
    print("저장소          :", repo)
    if snap:
        local = snap.astimezone()
        print(f"원본 스냅샷 시각: {snap:%Y-%m-%d %H:%M:%S} UTC  ({local:%Y-%m-%d %H:%M} 현지)")
        print("  ↑ 이 시각 이후 앱에서 스킬을 수정했다면 그 변경은 아직 여기 없습니다.")
        print("    수정 직후라면 새 세션에서 다시 실행하세요.")
    print("=" * 68)
    print(f"\n대상 스킬 {len(targets)}개:")
    for s in targets:
        print(f"  - {s['name']:<32s} 계정 최종수정 {s.get('updatedAt', '?')[:19]}")

    # 덮어쓰기 전에 작업 트리가 깨끗한지 확인한다.
    dirty = git(repo, "status", "--porcelain").strip()
    if dirty and args.dry_run:
        # dry-run 은 중단하지 않지만, 실제 실행 때 걸릴 문제를 미리 알려야 한다.
        # 여기서 침묵하면 "dry-run 은 잘 됐는데 왜 본실행이 멈추지?" 가 된다.
        print("\n[예고] 저장소에 커밋되지 않은 변경이 있습니다. 실제 실행은 여기서 멈춥니다:")
        print("\n".join("  " + line for line in dirty.splitlines()[:40]))
        print("  → 아래 변경 목록에 이 파일들이 섞여 있다면 로컬 수정분이 덮이는 것입니다.")
    if dirty and not (args.allow_dirty or args.dry_run):
        print("\n[중단] 저장소에 커밋되지 않은 변경이 있습니다:")
        print("\n".join("  " + line for line in dirty.splitlines()[:40]))
        print(
            "\n동기화는 저장소 내용을 계정 버전으로 덮어씁니다. 위 변경이 사라지면 복구할 수 없습니다."
            "\n먼저 커밋하거나 되돌린 뒤 다시 실행하세요. (의도적이면 --allow-dirty)"
        )
        return 2

    results: dict[str, dict] = {}
    for s in targets:
        name = s["name"]
        src_dir = source / name
        if not src_dir.is_dir():
            print(f"\n[건너뜀] {name}: 원본 폴더가 없습니다 ({src_dir})")
            continue
        results[name] = mirror(src_dir, repo / name, args.dry_run)

    changed = {n: r for n, r in results.items() if any(r.values())}

    print("\n" + "-" * 68)
    if not changed:
        print("변경 사항 없음 — 저장소가 이미 계정과 같습니다.")
    else:
        for name, r in changed.items():
            bits = []
            for label, key in (("추가", "added"), ("변경", "modified"), ("삭제", "removed")):
                if r[key]:
                    bits.append(f"{label} {len(r[key])}")
            print(f"  {name:<32s} {', '.join(bits)}")
            for key, mark in (("added", "+"), ("modified", "~"), ("removed", "-")):
                for rel in r[key][:20]:
                    print(f"      {mark} {rel}")
                if len(r[key]) > 20:
                    print(f"      … 외 {len(r[key]) - 20}개")

    orphans = find_orphans(repo, manifest)
    if orphans:
        print(f"\n저장소에만 있는 폴더 {len(orphans)}개 (계정에 없음, 건드리지 않음):")
        for name in orphans:
            print(f"  · {name}")

    summary = {
        "repo": str(repo),
        "source": str(source),
        "snapshot_utc": snap.isoformat() if snap else None,
        "targets": [s["name"] for s in targets],
        "changed": changed,
        "orphans": orphans,
        "committed": False,
        "pushed": False,
        "commit": None,
    }

    if args.dry_run:
        print("\n[dry-run] 실제로 쓰지 않았습니다.")
    elif changed and not args.no_commit:
        git(repo, "add", "--all", "--", *[n for n in changed])
        staged = git(repo, "diff", "--cached", "--stat").strip()
        if staged:
            print("\n스테이징된 변경:")
            print("\n".join("  " + line for line in staged.splitlines()))
            if args.message:
                message = args.message
            else:
                names = ", ".join(sorted(changed))
                lines = [f"sync: update {len(changed)} skill(s) from account", "", f"skills: {names}"]
                if snap:
                    lines.append(f"source snapshot: {snap:%Y-%m-%dT%H:%M:%SZ}")
                message = "\n".join(lines)
            git(repo, "commit", "-m", message)
            head = git(repo, "rev-parse", "--short", "HEAD").strip()
            summary["committed"] = True
            summary["commit"] = head
            print(f"\n커밋 완료: {head}")

            if args.push:
                remote = has_remote(repo)
                if not remote:
                    print("원격이 설정돼 있지 않아 푸시를 건너뜁니다.")
                else:
                    proc = subprocess.run(
                        ["git", "-C", str(repo), "push"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                    )
                    if proc.returncode == 0:
                        summary["pushed"] = True
                        print(f"푸시 완료 → {remote}")
                    else:
                        print(f"푸시 실패 ({remote}):\n{proc.stderr.strip()}")
                        print("네트워크나 인증 문제일 수 있습니다. 커밋은 이미 남아 있으니 직접 푸시하셔도 됩니다.")

    if args.json:
        print("\n---JSON---")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
