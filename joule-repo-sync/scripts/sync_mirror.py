#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""회사 Gitea 저장소를 개인 GitHub 사본으로 덧붙여 미러링한다.

회사 커밋 하나하나의 트리를 가져와 제외 패턴만 떨어낸 뒤 사본 브랜치에
commit-tree 로 쌓는다. 이미 올라간 커밋은 건드리지 않으므로 force push 가
필요 없고, 작성자·커밋터·날짜·메시지가 그대로 보존된다.
각 사본 커밋 끝의 Mirror-Of trailer 가 다음 동기화의 기준점이 된다.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

COMPANY_DEFAULT = r"D:\Mobase\asec_autotest_tool"
WORK_DEFAULT = r"D:\Ljindong\joule"

COMPANY_REMOTE = "company"          # 작업장에서 회사 저장소를 가리키는 원격
COMPANY_BRANCH = "main"             # 작업장의 회사 사본 브랜치 (DBC 포함, 밖으로 안 나간다)
MIRROR_BRANCH = "public"            # 작업장의 걸러진 사본 브랜치
MIRROR_REMOTE = "origin"            # 개인 GitHub
MIRROR_REMOTE_BRANCH = "main"
LAST_SYNC_REF = "refs/sync/company-main"

EXCLUDE = ["*.dbc"]                 # 사본에서 빼는 것 (git pathspec)
TRAILER = "Mirror-Of"

# 사본 커밋의 작성자·커밋터를 개인 계정으로 적는다 (날짜·메시지는 회사 것 그대로).
# GitHub 는 author 메일이 계정에 등록된 것일 때만 작성자로 연결하고, 회사 메일을
# 개인 저장소에 남기지 않으려는 뜻도 있다 (사용자 결정 2026-11-07).
# None 으로 두거나 --keep-identity 를 주면 회사 저장소의 작성자를 그대로 쓴다.
MIRROR_IDENTITY = ("ljindong", "ljindong1@gmail.com")
BACKUP_REF = "refs/sync/public-before-rebuild"
BIG_FILE_BYTES = 1024 * 1024
CONTROL_REPO = "git/git"            # private 판별의 대조군 (확실히 public)

README_BLOCK = """## 이 저장소에 대하여

사내 Gitea 저장소 `asec_autotest_tool` 의 개인 백업 사본이다.
개발은 사내 저장소에서 하고, 이 사본은 커밋 단위로 덧붙이기만 한다 (회사 -> 개인 단방향).

- 빠진 것: 차종 표준 DB `*.dbc`. 고객사 자료라 사내 저장소에만 둔다.
  설정이 가리키는 `can_db/<차종>/` 에 DBC 를 채우면 검증 명령이 돈다.
- 각 커밋 끝의 `Mirror-Of:` 가 대응하는 사내 저장소 커밋이다.
"""

GITIGNORE_BLOCK = """# 개인 백업 사본에서 빼는 것 - 사내 저장소에만 둔다
*.dbc
"""

OVERLAYS = {"README.md": README_BLOCK, ".gitignore": GITIGNORE_BLOCK}

PRE_PUSH_HOOK = """#!/bin/sh
# joule-repo-sync 안전망: 개인 GitHub 로 차종 DBC 가 나가는 것을 막는다.
case "$2" in
  *github*) ;;
  *) exit 0 ;;
esac
while read -r local_ref local_sha remote_ref remote_sha; do
  case "$local_sha" in
    0000000000000000000000000000000000000000) continue ;;
  esac
  hits=$(git ls-tree -r --name-only "$local_sha" | grep -i "\\.dbc$" | head -5)
  if [ -n "$hits" ]; then
    echo "pre-push 거부: $local_ref 에 차종 DBC 가 들어 있다." >&2
    echo "$hits" >&2
    exit 1
  fi
done
exit 0
"""


class GitError(RuntimeError):
    pass


def git(repo, *args, data=None, env=None, check=True):
    cmd = ["git", "-C", str(repo), *args]
    e = os.environ.copy()
    e["LC_ALL"] = "C"
    if env:
        e.update(env)
    p = subprocess.run(cmd, input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=e)
    if check and p.returncode != 0:
        raise GitError("git %s\n%s" % (" ".join(args),
                                       p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout


def gits(repo, *args, **kw):
    return git(repo, *args, **kw).decode("utf-8", "replace").strip()


def rev(repo, name):
    return git(repo, "rev-parse", "--verify", "--quiet", str(name),
               check=False).decode().strip()


def short(repo, sha):
    return gits(repo, "rev-parse", "--short", sha) if sha else "-"


def subject(repo, sha):
    return gits(repo, "log", "-1", "--format=%s", sha) if sha else ""


def is_ancestor(repo, a, b):
    p = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", a, b],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.returncode == 0


# ---------------------------------------------------------------- 트리 만들기

def temp_index(work, commit):
    """commit 의 트리를 임시 인덱스에 읽어 (임시폴더, env) 를 돌려준다."""
    td = tempfile.TemporaryDirectory()
    env = {"GIT_INDEX_FILE": os.path.join(td.name, "index")}
    git(work, "read-tree", commit, env=env)
    return td, env


def excluded_files(work, commit, excludes):
    if not excludes:
        return []
    td, env = temp_index(work, commit)
    try:
        raw = git(work, "ls-files", "-z", "--", *excludes, env=env)
        return [n.decode("utf-8", "replace") for n in raw.split(b"\0") if n]
    finally:
        td.cleanup()


def build_tree(work, commit, excludes, overlays):
    """commit 의 트리에서 제외 패턴을 빼고 오버레이를 덧붙인 트리 sha."""
    td, env = temp_index(work, commit)
    try:
        if excludes:
            raw = git(work, "ls-files", "-z", "--", *excludes, env=env)
            for name in [n for n in raw.split(b"\0") if n]:
                git(work, "update-index", "--force-remove", "--",
                    name.decode("utf-8", "replace"), env=env)
        for path, block in overlays.items():
            base = git(work, "cat-file", "blob", "%s:%s" % (commit, path), check=False)
            body = base.rstrip(b"\n")
            new = (body + b"\n\n" if body else b"") + block.encode("utf-8")
            blob = gits(work, "hash-object", "-w", "--stdin", data=new)
            git(work, "update-index", "--add", "--cacheinfo",
                "100644,%s,%s" % (blob, path), env=env)
        return gits(work, "write-tree", env=env)
    finally:
        td.cleanup()


def add_trailer(msg_bytes, full_sha):
    text = msg_bytes.decode("utf-8", "replace").rstrip("\n")
    tail = text.rsplit("\n\n", 1)[-1].splitlines()
    looks_like_trailers = bool(tail) and all(
        (":" in ln and not ln.startswith((" ", "\t", "-", "*"))) for ln in tail)
    sep = "\n" if looks_like_trailers else "\n\n"
    return (text + sep + "%s: %s\n" % (TRAILER, full_sha)).encode("utf-8")


def mirror_commit(work, commit, tree, parent, identity=None):
    fmt = "%an%x1f%ae%x1f%aI%x1f%cn%x1f%ce%x1f%cI"
    an, ae, ad, cn, ce, cd = gits(work, "show", "-s", "--format=" + fmt,
                                  commit).split("\x1f")
    if identity:
        an = cn = identity[0]
        ae = ce = identity[1]
    msg = add_trailer(git(work, "show", "-s", "--format=%B", commit), commit)
    env = {"GIT_AUTHOR_NAME": an, "GIT_AUTHOR_EMAIL": ae, "GIT_AUTHOR_DATE": ad,
           "GIT_COMMITTER_NAME": cn, "GIT_COMMITTER_EMAIL": ce, "GIT_COMMITTER_DATE": cd}
    args = ["commit-tree", tree]
    if parent:
        args += ["-p", parent]
    return gits(work, *args, data=msg, env=env)


# ------------------------------------------------------------------- 기준점

def find_base(work, company_tip, override=""):
    if override:
        sha = rev(work, override)
        if not sha:
            raise SystemExit("[중단] --from 으로 준 %s 를 찾을 수 없다." % override)
        return sha, "--from 으로 지정"
    tip = rev(work, MIRROR_BRANCH)
    if tip:
        msg = git(work, "show", "-s", "--format=%B", tip).decode("utf-8", "replace")
        for ln in reversed(msg.splitlines()):
            s = ln.strip()
            if s.startswith(TRAILER + ":"):
                sha = rev(work, s.split(":", 1)[1].strip())
                if sha:
                    return sha, "사본 tip 의 %s trailer" % TRAILER
    sha = rev(work, LAST_SYNC_REF)
    if sha:
        return sha, LAST_SYNC_REF
    sha = rev(work, COMPANY_BRANCH)
    if sha and company_tip and is_ancestor(work, sha, company_tip):
        return sha, "작업장 %s 브랜치 (추정 - 맞는지 확인할 것)" % COMPANY_BRANCH
    return "", ""


# ------------------------------------------------------------------- 점검

def repo_visibility(work):
    url = gits(work, "remote", "get-url", MIRROR_REMOTE, check=False)
    slug = ""
    if ":" in url and "//" not in url:
        slug = url.rsplit(":", 1)[1]
    elif "github.com/" in url:
        slug = url.split("github.com/", 1)[1]
    if slug.endswith(".git"):
        slug = slug[:-4]
    if not slug:
        return "unknown", url, "원격 URL 에서 owner/repo 를 못 읽었다"

    def code(path):
        req = urllib.request.Request("https://api.github.com/repos/" + path,
                                     headers={"User-Agent": "joule-repo-sync"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return 0

    if code(CONTROL_REPO) != 200:
        return "unknown", slug, "GitHub API 에 닿지 않는다 (대조군 %s 도 실패)" % CONTROL_REPO
    c = code(slug)
    if c == 404:
        return "private", slug, "비인증 조회가 404 - 공개되어 있지 않다"
    if c == 200:
        return "public", slug, "비인증 조회가 200 - 누구나 볼 수 있다"
    return "unknown", slug, "비인증 조회 HTTP %s" % c


def inspect_range(work, base, tip, mirror_tip, excluded):
    """사본에 새로 올라가는 것들 가운데 사람이 봐야 할 것을 모은다.

    '처음 보는' 의 기준은 회사 트리가 아니라 지금 사본(mirror_tip)이다.
    회사 저장소에 오래 있었던 파일도, 사본에 처음 들어가면 거기서 보여야 한다.
    """
    rows = gits(work, "-c", "core.quotepath=false", "diff", "--name-status",
                base, tip).splitlines()
    changed = []
    for ln in rows:
        parts = ln.split("\t")
        if len(parts) >= 2:
            changed.append((parts[0], parts[-1]))

    # '사본에 새로 올라가는 파일' = 회사 tip 에 있고(제외분 빼고) 지금 사본에 없는 것.
    # 이번 범위에서 바뀌지 않았어도, 제외 규칙이 느슨해져 되살아나는 파일이 여기 잡힌다.
    skip = set(excluded)
    seen = set(gits(work, "ls-tree", "-r", "--name-only", mirror_tip).splitlines()) \
        if mirror_tip else set()
    seen_ext = {os.path.splitext(n)[1].lower() for n in seen}
    seen_top = {n.split("/")[0] for n in seen if "/" in n}
    target = [n for n in gits(work, "ls-tree", "-r", "--name-only", tip).splitlines()
              if n not in skip]

    new_ext, new_top, new_paths = {}, set(), []
    for path in target:
        if path in seen:
            continue
        new_paths.append(path)
        ext = os.path.splitext(path)[1].lower()
        if ext and ext not in seen_ext:
            new_ext[ext] = new_ext.get(ext, 0) + 1
        top = path.split("/")[0] if "/" in path else ""
        if top and top not in seen_top:
            new_top.add(top)

    big = []
    for ln in gits(work, "ls-tree", "-r", "-l", tip).splitlines():
        head, _, name = ln.partition("\t")
        cols = head.split()
        if name in skip:
            continue
        if len(cols) >= 4 and cols[3].isdigit() and int(cols[3]) >= BIG_FILE_BYTES:
            big.append((int(cols[3]), name))
    big.sort(reverse=True)
    return changed, new_ext, sorted(new_top), big[:10], new_paths


# ------------------------------------------------------------------- 공통 절차

def preflight(company, work, fetch=True):
    problems = []
    for path, label in ((company, "회사 저장소"), (work, "작업장")):
        if not os.path.isdir(os.path.join(path, ".git")):
            problems.append("%s 가 git 저장소가 아니다: %s" % (label, path))
    if problems:
        raise SystemExit("[중단] " + "\n[중단] ".join(problems))

    dirty = gits(work, "status", "--porcelain")
    if dirty:
        raise SystemExit("[중단] 작업장에 커밋 안 된 변경이 있다. 정리한 뒤 다시 돌린다:\n" + dirty)

    url = gits(work, "remote", "get-url", COMPANY_REMOTE, check=False)
    if not url:
        raise SystemExit("[중단] 작업장에 원격 %s 가 없다. setup 을 먼저 돌린다." % COMPANY_REMOTE)
    if os.path.normcase(os.path.abspath(url.replace("/", os.sep))) != \
            os.path.normcase(os.path.abspath(company)):
        print("[주의] 원격 %s 가 %s 를 가리킨다 (회사 저장소로 준 경로는 %s)" %
              (COMPANY_REMOTE, url, company))

    co_dirty = gits(company, "status", "--porcelain")
    if co_dirty:
        print("[알림] 회사 저장소에 커밋 안 된 변경이 있다. 동기화는 커밋된 것만 다룬다:")
        for ln in co_dirty.splitlines()[:10]:
            print("       " + ln)

    if fetch:
        git(work, "fetch", COMPANY_REMOTE, "--prune")
        git(work, "fetch", MIRROR_REMOTE, "--prune", check=False)


def header(company, work):
    print("회사 저장소 : %s" % company)
    print("              origin = %s" % gits(company, "remote", "get-url", "origin", check=False))
    print("사본 작업장 : %s" % work)
    print("사본 원격   : %s -> %s" % (
        gits(work, "remote", "get-url", MIRROR_REMOTE, check=False), MIRROR_REMOTE_BRANCH))


def company_tip(work):
    return rev(work, "%s/%s" % (COMPANY_REMOTE, COMPANY_BRANCH))


def identity(a):
    return None if a.keep_identity else MIRROR_IDENTITY


def one_to_one(work, mirror_tip, company_ref):
    """사본 커밋이 회사 커밋과 1:1 로 대응하는지 (수·날짜·제목·Mirror-Of)."""
    co = gits(work, "log", "--format=%H%x1f%aI%x1f%s", company_ref).splitlines()
    mi = gits(work, "log", "--format=%H%x1f%aI%x1f%s", mirror_tip).splitlines()
    if len(co) != len(mi):
        return False, "커밋 수가 다르다 (회사 %d, 사본 %d)" % (len(co), len(mi))
    for (c, m) in zip(co, mi):
        csha, cdate, csubj = c.split("\x1f")
        _, mdate, msubj = m.split("\x1f")
        if cdate != mdate or csubj != msubj:
            return False, "날짜·제목이 어긋난다: 회사 %s / 사본 %s" % (csubj, msubj)
        msg = git(work, "show", "-s", "--format=%B", m.split("\x1f")[0])
        if ("%s: %s" % (TRAILER, csha)) not in msg.decode("utf-8", "replace"):
            return False, "%s 가 %s 를 가리키지 않는다" % (TRAILER, csha[:7])
    return True, "커밋 %d 개가 날짜·제목·%s 까지 1:1 로 맞는다" % (len(co), TRAILER)


# ------------------------------------------------------------------- 명령

def cmd_status(a):
    preflight(a.company, a.work, fetch=not a.no_fetch)
    tip = company_tip(a.work)
    base, how = find_base(a.work, tip, a.frm)
    header(a.company, a.work)
    print("")
    print("회사 tip    : %s %s" % (short(a.work, tip), subject(a.work, tip)))
    print("기준점      : %s %s" % (short(a.work, base), subject(a.work, base)))
    print("              (%s)" % (how or "찾지 못했다 - --from 으로 줄 것"))
    if base:
        n = gits(a.work, "rev-list", "--count", "%s..%s" % (base, tip))
        print("덧붙일 커밋 : %s 개" % n)
    vis, slug, why = repo_visibility(a.work)
    print("사본 공개   : %s (%s) - %s" % (vis, slug, why))
    mtip = rev(a.work, MIRROR_BRANCH)
    print("사본 tip    : %s %s" % (short(a.work, mtip), subject(a.work, mtip)))
    rtip = rev(a.work, "%s/%s" % (MIRROR_REMOTE, MIRROR_REMOTE_BRANCH))
    print("GitHub tip  : %s %s" % (short(a.work, rtip), subject(a.work, rtip)))
    if mtip and rtip and mtip != rtip:
        print("[알림] 로컬 사본과 GitHub 가 다르다 - push 가 남았거나 밖에서 바뀌었다.")
    return 0


def cmd_preview(a):
    preflight(a.company, a.work, fetch=not a.no_fetch)
    tip = company_tip(a.work)
    base, how = find_base(a.work, tip, a.frm)
    header(a.company, a.work)
    if not base:
        raise SystemExit("[중단] 기준점을 찾지 못했다. --from <회사 커밋> 으로 준다.")
    if not is_ancestor(a.work, base, tip):
        raise SystemExit("[중단] 기준점 %s 가 회사 tip 의 조상이 아니다 (이력이 갈렸다)."
                         % short(a.work, base))
    print("")
    print("기준점  : %s %s   (%s)" % (short(a.work, base), subject(a.work, base), how))
    print("회사 tip: %s %s" % (short(a.work, tip), subject(a.work, tip)))
    commits = gits(a.work, "rev-list", "--reverse", "%s..%s" % (base, tip)).split()
    print("")
    print("덧붙일 커밋 %d 개:" % len(commits))
    for c in commits:
        print("  %s %s" % (short(a.work, c), subject(a.work, c)))

    ex = excluded_files(a.work, tip, EXCLUDE)
    print("")
    print("빼는 파일 (패턴 %s) %d 개:" % (" ".join(EXCLUDE), len(ex)))
    for p in ex:
        print("  %s" % p)

    changed, new_ext, new_top, big, new_paths = inspect_range(
        a.work, base, tip, rev(a.work, MIRROR_BRANCH), ex)
    print("")
    print("사본에 새로 올라가는 것 점검 (빼는 파일은 셈에서 제외했다):")
    print("  변경 파일 %d 개, 그 가운데 사본에 없던 파일 %d 개" % (len(changed), len(new_paths)))
    print("  사본에 처음 들어가는 확장자: %s"
          % (", ".join("%s(%d개)" % (k, v) for k, v in sorted(new_ext.items())) or "없음"))
    print("  사본에 처음 들어가는 최상위 폴더: %s" % (", ".join(new_top) or "없음"))
    if new_ext or new_top:
        print("  (해당 파일 - 올려도 되는 내용인지 본다)")
        hot = [p for p in new_paths
               if os.path.splitext(p)[1].lower() in new_ext
               or (p.split("/")[0] if "/" in p else "") in new_top]
        for p in hot[:25]:
            print("    %s" % p)
        if len(hot) > 25:
            print("    ... %d 개 더" % (len(hot) - 25))
    if big:
        print("  1MB 넘는 파일:")
        for size, name in big:
            print("    %7.1f MB  %s" % (size / 1048576.0, name))
    else:
        print("  1MB 넘는 파일: 없음")
    vis, slug, why = repo_visibility(a.work)
    print("")
    print("사본 공개 상태: %s (%s) - %s" % (vis, slug, why))
    print("")
    print("이대로 쌓으려면: sync_mirror.py sync")
    return 0


def cmd_sync(a):
    preflight(a.company, a.work, fetch=not a.no_fetch)
    tip = company_tip(a.work)
    base, how = find_base(a.work, tip, a.frm)
    if not base:
        raise SystemExit("[중단] 기준점을 찾지 못했다. --from <회사 커밋> 으로 준다.")
    if not is_ancestor(a.work, base, tip):
        raise SystemExit("[중단] 기준점이 회사 tip 의 조상이 아니다 (이력이 갈렸다).")
    commits = gits(a.work, "rev-list", "--reverse", "%s..%s" % (base, tip)).split()
    if not commits:
        print("덧붙일 커밋이 없다. 이미 최신이다.")
        return 0

    parent = rev(a.work, MIRROR_BRANCH)
    if not parent:
        raise SystemExit("[중단] 사본 브랜치 %s 가 없다. setup 을 먼저 돌린다." % MIRROR_BRANCH)
    start = parent
    print("기준점 %s (%s) 위에 %d 개를 쌓는다." % (short(a.work, base), how, len(commits)))
    empty = 0
    for i, c in enumerate(commits, 1):
        tree = build_tree(a.work, c, EXCLUDE, OVERLAYS)
        ptree = gits(a.work, "rev-parse", "%s^{tree}" % parent)
        new = mirror_commit(a.work, c, tree, parent, identity(a))
        mark = "  (내용 변경 없음)" if tree == ptree else ""
        if mark:
            empty += 1
        print("  [%d/%d] %s -> %s %s%s" % (i, len(commits), short(a.work, c),
                                           short(a.work, new), subject(a.work, c), mark))
        parent = new
    git(a.work, "update-ref", "refs/heads/" + MIRROR_BRANCH, parent, start)
    git(a.work, "update-ref", LAST_SYNC_REF, tip)
    print("")
    print("사본 %s : %s -> %s" % (MIRROR_BRANCH, short(a.work, start), short(a.work, parent)))
    if empty:
        print("(제외 파일만 바꾼 커밋 %d 개는 내용 변경이 없다 - 이력을 맞추려 그대로 남겼다)" % empty)
    print("")
    return cmd_verify(a)


def cmd_rebuild(a):
    """사본 이력을 루트부터 다시 만든다. 푸시할 때 force 가 필요하다."""
    preflight(a.company, a.work, fetch=not a.no_fetch)
    tip = company_tip(a.work)
    if not tip:
        raise SystemExit("[중단] 회사 브랜치를 찾지 못했다.")
    if gits(a.work, "rev-list", "--merges", tip):
        raise SystemExit("[중단] 회사 이력에 merge 커밋이 있다. 선형 재생성으로는 안 된다 - "
                         "부모 매핑을 넣어야 하므로 사용자와 의논한다.")
    commits = gits(a.work, "rev-list", "--reverse", tip).split()
    before = rev(a.work, MIRROR_BRANCH)
    who = identity(a)
    print("회사 이력 %d 개를 루트부터 다시 만든다." % len(commits))
    print("  작성자: %s" % ("%s <%s>" % who if who else "회사 저장소 그대로"))
    print("  빼는 것: %s" % " ".join(EXCLUDE))
    if before:
        git(a.work, "update-ref", BACKUP_REF, before)
        print("  전 사본 %s 를 %s 에 받아 뒀다." % (short(a.work, before), BACKUP_REF))
    parent = ""
    for i, c in enumerate(commits, 1):
        tree = build_tree(a.work, c, EXCLUDE, OVERLAYS)
        parent = mirror_commit(a.work, c, tree, parent, who)
        if i % 25 == 0 or i == len(commits):
            print("  [%d/%d] %s -> %s" % (i, len(commits), short(a.work, c),
                                          short(a.work, parent)))
    git(a.work, "update-ref", "refs/heads/" + MIRROR_BRANCH, parent)
    git(a.work, "update-ref", LAST_SYNC_REF, tip)
    print("")
    print("사본 %s : %s -> %s" % (MIRROR_BRANCH, short(a.work, before), short(a.work, parent)))
    if before:
        same = gits(a.work, "rev-parse", "%s^{tree}" % before) == \
            gits(a.work, "rev-parse", "%s^{tree}" % parent)
        print("최신 내용(트리)이 전 사본과 %s" % ("같다" if same else "다르다 - 제외 규칙이 바뀌었기 때문"))
        if not is_ancestor(a.work, before, parent):
            print("이력을 다시 썼으므로 푸시에 --force 가 필요하다.")
    ok, why = one_to_one(a.work, parent, tip)
    print("1:1 대조: %s (%s)" % ("통과" if ok else "실패", why))
    print("")
    rc = cmd_verify(a)
    return rc if ok else 1


def cmd_verify(a):
    tip = company_tip(a.work)
    mtip = rev(a.work, MIRROR_BRANCH)
    if not (tip and mtip):
        raise SystemExit("[중단] 비교할 브랜치가 없다.")
    msg = git(a.work, "show", "-s", "--format=%B", mtip).decode("utf-8", "replace")
    mirrored = ""
    for ln in reversed(msg.splitlines()):
        if ln.strip().startswith(TRAILER + ":"):
            mirrored = rev(a.work, ln.split(":", 1)[1].strip())
            break
    ref = mirrored or tip
    print("검증: 사본 %s 를 회사 %s 와 맞춰 본다." % (short(a.work, mtip), short(a.work, ref)))
    ex = set(excluded_files(a.work, ref, EXCLUDE))
    rows = gits(a.work, "-c", "core.quotepath=false", "diff", "--name-status",
                mtip, ref).splitlines()
    unexpected = [ln for ln in rows
                  if ln.split("\t")[-1] not in OVERLAYS and ln.split("\t")[-1] not in ex]
    print("  빠진 DBC %d 개, 안내를 덧붙인 파일 %d 개" % (len(ex), len(OVERLAYS)))
    rc = 0
    if unexpected:
        print("  [경고] 설명되지 않는 차이 %d 건:" % len(unexpected))
        for ln in unexpected[:20]:
            print("    " + ln)
        rc = 1
    else:
        print("  그 밖의 차이 없음 - 사본 내용이 회사 저장소와 같다.")
    bad = [n for n in gits(a.work, "ls-tree", "-r", "--name-only", mtip).splitlines()
           if n.lower().endswith(".dbc")]
    if bad:
        print("  [경고] 사본에 DBC 가 남아 있다: %s" % ", ".join(bad))
        rc = 1
    else:
        print("  사본에 .dbc 없음 확인.")
    return rc


def cmd_push(a):
    mtip = rev(a.work, MIRROR_BRANCH)
    if not mtip:
        raise SystemExit("[중단] 사본 브랜치 %s 가 없다." % MIRROR_BRANCH)
    vis, slug, why = repo_visibility(a.work)
    print("사본 공개 상태: %s (%s) - %s" % (vis, slug, why))
    if vis != "private" and not a.allow_public:
        raise SystemExit("[중단] private 임을 확인하지 못했다. 확인한 뒤 --allow-public 으로 다시 돌린다.")
    if cmd_verify(a):
        raise SystemExit("[중단] 검증이 통과하지 못했다. 푸시하지 않는다.")

    # 밖으로 내보내는 일이라 확인 없이는 돌지 않는다.
    rtip = rev(a.work, "%s/%s" % (MIRROR_REMOTE, MIRROR_REMOTE_BRANCH))
    ahead = gits(a.work, "rev-list", "--count",
                 "%s..%s" % (rtip, MIRROR_BRANCH)) if rtip else "?"
    ff = (not rtip) or is_ancestor(a.work, rtip, mtip)
    print("")
    print("보낼 내용:")
    print("  %s  ->  %s:%s" % (slug, MIRROR_REMOTE, MIRROR_REMOTE_BRANCH))
    print("  %s -> %s (커밋 %s 개)" % (short(a.work, rtip), short(a.work, mtip), ahead))
    print("  fast-forward: %s" % ("예 (이력을 덮어쓰지 않는다)" if ff else "아니다 - force 가 필요하다"))
    print("  빠지는 파일: 패턴 %s" % " ".join(EXCLUDE))
    who = identity(a)
    print("  사본 작성자: %s" % ("%s <%s>" % who if who else "회사 저장소 그대로"))
    if not ff and not a.force:
        raise SystemExit("[중단] fast-forward 가 아니다. 덧붙이기만 했다면 이럴 일이 없다 - "
                         "rebuild 로 이력을 다시 썼다면 --force 를, 아니면 GitHub 쪽이 "
                         "밖에서 바뀐 것인지 확인한다.")
    if not ff:
        print("")
        print("  [주의] --force 다. GitHub 의 지금 이력 %s 를 버리고 덮어쓴다."
              % short(a.work, rtip))
        print("         전 사본은 %s 에 받아 뒀다 (rebuild 가 남긴다)." % BACKUP_REF)
    if a.confirmed:
        print("")
        print("확인을 받았다고 지정됐다 (--confirmed).")
    elif not sys.stdin.isatty():
        raise SystemExit(
            "[중단] 확인 없이는 푸시하지 않는다.\n"
            "       터미널에서 직접 돌리거나, 사용자 승인을 받은 뒤 --confirmed 를 붙인다.")
    else:
        try:
            ans = input("\n이대로 GitHub 로 보낼까? 보내려면 push 라고 입력: ")
        except EOFError:
            ans = ""
        if ans.strip() != "push":
            raise SystemExit(
                "\n[중단] 확인되지 않아 푸시하지 않았다.\n"
                "       터미널에서 다시 돌려 push 라고 입력하거나, "
                "사용자 승인을 받은 뒤 --confirmed 를 붙인다.")
    print("")
    cmd = ["git", "-C", a.work, "push"]
    if not ff:
        cmd.append("--force-with-lease=%s:%s" % (MIRROR_REMOTE_BRANCH, rtip))
    cmd += [MIRROR_REMOTE, "%s:%s" % (MIRROR_BRANCH, MIRROR_REMOTE_BRANCH)]
    print(" ".join(cmd[3:]))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace").strip())
    if p.returncode != 0:
        raise SystemExit("[중단] 푸시가 실패했다.")
    git(a.work, "fetch", MIRROR_REMOTE, "--prune", check=False)
    tip = company_tip(a.work)
    cur = gits(a.work, "rev-parse", "--abbrev-ref", "HEAD")
    if cur == COMPANY_BRANCH and tip and is_ancestor(a.work, rev(a.work, "HEAD"), tip):
        git(a.work, "merge", "--ff-only", tip, check=False)
        print("작업장 %s 브랜치도 회사 tip 으로 맞췄다." % COMPANY_BRANCH)
    print("")
    print("끝. GitHub tip = %s" %
          short(a.work, rev(a.work, "%s/%s" % (MIRROR_REMOTE, MIRROR_REMOTE_BRANCH))))
    return 0


def cmd_setup(a):
    if not os.path.isdir(os.path.join(a.work, ".git")):
        raise SystemExit("[중단] 작업장이 git 저장소가 아니다: %s" % a.work)
    if not gits(a.work, "remote", "get-url", COMPANY_REMOTE, check=False):
        git(a.work, "remote", "add", COMPANY_REMOTE, a.company.replace("\\", "/"))
        print("원격 %s 를 %s 로 추가했다." % (COMPANY_REMOTE, a.company))
    git(a.work, "config", "remote.%s.push" % MIRROR_REMOTE,
        "refs/heads/%s:refs/heads/%s" % (MIRROR_BRANCH, MIRROR_REMOTE_BRANCH))
    git(a.work, "config", "branch.%s.remote" % COMPANY_BRANCH, COMPANY_REMOTE)
    git(a.work, "config", "branch.%s.merge" % COMPANY_BRANCH, "refs/heads/" + COMPANY_BRANCH)
    hook = os.path.join(a.work, ".git", "hooks", "pre-push")
    with open(hook, "w", encoding="utf-8", newline="\n") as f:
        f.write(PRE_PUSH_HOOK)
    os.chmod(hook, 0o755)
    print("설정을 마쳤다:")
    print("  remote.%s.push = refs/heads/%s:refs/heads/%s  (origin 으로는 사본만 나간다)"
          % (MIRROR_REMOTE, MIRROR_BRANCH, MIRROR_REMOTE_BRANCH))
    print("  branch.%s.remote = %s  (회사 사본 브랜치가 실수로 GitHub 로 가지 않게)"
          % (COMPANY_BRANCH, COMPANY_REMOTE))
    print("  pre-push 훅 설치: %s" % hook)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command",
                    choices=["setup", "status", "preview", "sync", "rebuild",
                             "push", "verify"])
    ap.add_argument("--company", default=COMPANY_DEFAULT, help="회사 저장소 폴더")
    ap.add_argument("--work", default=WORK_DEFAULT, help="동기화 작업장 (개인 폴더)")
    ap.add_argument("--from", dest="frm", default="", help="기준점 회사 커밋 (처음 한 번)")
    ap.add_argument("--no-fetch", action="store_true", help="fetch 를 건너뛴다")
    ap.add_argument("--allow-public", action="store_true",
                    help="사본이 private 임을 확인하지 못해도 푸시한다")
    ap.add_argument("--confirmed", action="store_true",
                    help="push: 사용자 확인을 이미 받았다 (대화형 입력을 건너뛴다). "
                         "사용자가 그 자리에서 승인한 때만 쓴다")
    ap.add_argument("--force", action="store_true",
                    help="push: rebuild 로 이력을 다시 쓴 뒤 덮어쓴다 (force-with-lease)")
    ap.add_argument("--keep-identity", action="store_true",
                    help="사본 작성자를 개인 계정으로 바꾸지 않고 회사 저장소 그대로 둔다")
    a = ap.parse_args(argv)
    fn = {"setup": cmd_setup, "status": cmd_status, "preview": cmd_preview,
          "sync": cmd_sync, "rebuild": cmd_rebuild, "push": cmd_push,
          "verify": cmd_verify}[a.command]
    try:
        return fn(a)
    except GitError as e:
        print("[git 오류] %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
