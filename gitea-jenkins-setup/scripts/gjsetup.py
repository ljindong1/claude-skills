#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gjsetup.py - gitea-jenkins-setup skill helper (Claude Code CLI, Windows)

Rules enforced in code:
  * CREATE ONLY. Never modify or delete anything that already exists.
    Existing resource that matches      -> reuse (status "exists")
    Existing resource that differs      -> leave untouched (status "conflict")
  * Tokens are read from environment variables and never printed.
  * Standard library only.

Every command prints one JSON object to stdout:
  {"ok": true|false, "status": "...", "message": "...", ...}

Commands
  preflight                         check env vars, API access, git
  repo-info   --repo O/R            default branch, branches, submodules, my fork
  fork        --repo O/R [--org ORG]
  collab      --repo O/R --user U [--perm write]
  resolve-path --repo O/R [--path DIR]  parent/repo folder from input or current dir
  clone       --repo O/R [--dest DIR]   DIR = parent or repo folder (default: current dir)
  detect-project --path DIR         find <project>/Build/Build.bat
  branch      --path DIR --base B --name N
  add-bat     --path DIR --project P --name N --email E
  job-info    --name J [--view V]   exists? view list, credential id candidates
  render-job  --name J --repo-url URL --branch-spec S --project P --user U
              --cred-id ID [--description D] --out FILE
  job-create  --name J --xml FILE [--view V]
  job-verify  --name J --repo-url URL --branch-spec S --project P --user U
  job-enable  --name J
"""
import argparse
import base64
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
EXCLUSION = "(?s).*Auto commit from Jenkins.*"
JOB_PERMS = [
    "hudson.model.Item.Build", "hudson.model.Item.Cancel", "hudson.model.Item.Configure",
    "hudson.model.Item.Read", "hudson.model.Item.Workspace",
    "hudson.model.Run.Delete", "hudson.model.Run.Update",
]


# ----------------------------------------------------------------- output
def out(ok, status, message="", **kw):
    data = {"ok": ok, "status": status, "message": message}
    data.update(kw)
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    sys.exit(0 if ok else 1)


def env(name):
    v = os.environ.get(name, "").strip()
    return v or None


# ----------------------------------------------------------------- http
def _ctx(url):
    if url.startswith("https") and os.environ.get("JENKINS_INSECURE") == "1":
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        return c
    return None


def http(method, url, headers=None, body=None, timeout=60):
    """Return (status, text). Never raises for HTTP errors."""
    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx(url)) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            txt = e.read().decode("utf-8", "replace")
        except Exception:
            txt = ""
        return e.code, txt
    except Exception as e:  # network / ssl
        return -1, str(e)


# -- Gitea
def g_base():
    return (env("GITEA_URL") or "").rstrip("/")


def g_hdr(json_body=False):
    h = {"Authorization": "token " + (env("GITEA_TOKEN") or ""), "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def gitea(method, path, payload=None):
    body = json.dumps(payload) if payload is not None else None
    st, txt = http(method, g_base() + "/api/v1" + path, g_hdr(payload is not None), body)
    try:
        js = json.loads(txt) if txt else None
    except ValueError:
        js = None
    return st, js, txt


def gitea_login():
    st, js, _ = gitea("GET", "/user")
    return js.get("login") if st == 200 and js else None


# -- Jenkins
def j_base():
    return (env("JENKINS_URL") or "").rstrip("/")


def j_hdr(extra=None):
    raw = "%s:%s" % (env("JENKINS_USER") or "", env("JENKINS_TOKEN") or "")
    h = {"Authorization": "Basic " + base64.b64encode(raw.encode()).decode()}
    st, txt = http("GET", j_base() + "/crumbIssuer/api/json", dict(h))
    if st == 200:
        try:
            c = json.loads(txt)
            h[c["crumbRequestField"]] = c["crumb"]
        except Exception:
            pass
    if extra:
        h.update(extra)
    return h


def jenkins(method, path, body=None, extra=None):
    return http(method, j_base() + path, j_hdr(extra), body)


def job_path(name):
    return "/job/" + urllib.parse.quote(name)


# -- git
def git_auth_args():
    """Per-command auth header (not stored in git config)."""
    tok, login = env("GITEA_TOKEN"), gitea_login() if env("GITEA_TOKEN") else None
    if tok and login:
        b = base64.b64encode(("%s:%s" % (login, tok)).encode()).decode()
        return ["-c", "http.extraHeader=Authorization: Basic " + b]
    return []


def git(args, cwd=None, auth=False, check=True):
    cmd = ["git"] + (git_auth_args() if auth else []) + args
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    safe = " ".join(["git"] + args)  # never show auth header
    if check and p.returncode != 0:
        out(False, "git_error", "git 명령 실패: " + safe, stderr=p.stderr.strip()[-1500:])
    return p


# ----------------------------------------------------------------- commands
def c_preflight(a):
    res = {"env": {}, "gitea": None, "jenkins": None, "git": None, "python": sys.version.split()[0]}
    for n in ["GITEA_URL", "GITEA_TOKEN", "JENKINS_URL", "JENKINS_USER", "JENKINS_TOKEN"]:
        res["env"][n] = bool(env(n))
    res["git"] = shutil.which("git") is not None

    if res["env"]["GITEA_URL"] and res["env"]["GITEA_TOKEN"]:
        st, js, txt = gitea("GET", "/user")
        res["gitea"] = {"http": st, "login": js.get("login") if st == 200 and js else None}
        if st != 200:
            res["gitea"]["hint"] = "토큰 값·권한·만료 또는 GITEA_URL 확인" if st in (401, 403) else txt[:200]
    if res["env"]["JENKINS_URL"] and res["env"]["JENKINS_USER"] and res["env"]["JENKINS_TOKEN"]:
        st, txt = jenkins("GET", "/me/api/json?tree=id,fullName")
        info = {"http": st}
        if st == 200:
            try:
                info["id"] = json.loads(txt).get("id")
            except ValueError:
                pass
        else:
            info["hint"] = ("JENKINS_USER/JENKINS_TOKEN 확인" if st in (401, 403)
                            else "SSL 오류면 JENKINS_INSECURE=1 검토: " + txt[:200])
        res["jenkins"] = info

    gitea_ok = bool(res["gitea"] and res["gitea"].get("login"))
    jenkins_ok = bool(res["jenkins"] and res["jenkins"].get("id"))
    mode = {"gitea": "api" if gitea_ok else "chrome", "jenkins": "api" if jenkins_ok else "chrome"}
    ok = res["git"]
    msg = "git 없음 - 설치 필요" if not res["git"] else "점검 완료"
    out(ok, "preflight", msg, result=res, mode=mode)


def c_repo_info(a):
    owner, repo = a.repo.split("/", 1)
    st, js, txt = gitea("GET", "/repos/%s/%s" % (owner, repo))
    if st != 200:
        out(False, "not_found", "원본 저장소 조회 실패 (HTTP %s)" % st)
    info = {
        "full_name": js["full_name"], "private": js.get("private"),
        "default_branch": js.get("default_branch"), "is_fork": js.get("fork"),
        "parent": (js.get("parent") or {}).get("full_name"),
        "clone_url": js.get("clone_url"),
    }
    branches, page = [], 1
    while True:
        st, bl, _ = gitea("GET", "/repos/%s/%s/branches?limit=50&page=%d" % (owner, repo, page))
        if st != 200 or not bl:
            break
        branches += [b["name"] for b in bl]
        if len(bl) < 50:
            break
        page += 1
    info["branches"] = branches
    st, _, sm = gitea("GET", "/repos/%s/%s/raw/.gitmodules?ref=%s"
                      % (owner, repo, urllib.parse.quote(info["default_branch"] or "")))
    info["submodules"] = re.findall(r"url\s*=\s*(\S+)", sm) if st == 200 else []
    me = gitea_login()
    info["me"] = me
    if me:
        st, mine, _ = gitea("GET", "/repos/%s/%s" % (me, repo))
        info["my_repo_same_name"] = None if st != 200 else {
            "full_name": mine["full_name"], "is_fork": mine.get("fork"),
            "parent": (mine.get("parent") or {}).get("full_name")}
    out(True, "repo_info", "", info=info)


def c_fork(a):
    owner, repo = a.repo.split("/", 1)
    target_owner = a.org or gitea_login()
    if not target_owner:
        out(False, "auth", "Gitea 로그인 확인 실패")
    st, js, _ = gitea("GET", "/repos/%s/%s" % (target_owner, repo))
    if st == 200:
        parent = (js.get("parent") or {}).get("full_name")
        if js.get("fork") and parent == a.repo:
            out(True, "exists", "Fork가 이미 있어 재사용", repo=js["full_name"],
                clone_url=js.get("clone_url"))
        out(False, "conflict", "같은 이름의 저장소가 있지만 %s의 Fork가 아님 - 건드리지 않음" % a.repo,
            repo=js["full_name"], is_fork=js.get("fork"), parent=parent)
    payload = {"organization": a.org} if a.org else {}
    st, js, txt = gitea("POST", "/repos/%s/%s/forks" % (owner, repo), payload)
    if st in (200, 201, 202):
        out(True, "created", "Fork 생성", repo=js.get("full_name"), clone_url=js.get("clone_url"))
    out(False, "api_error", "Fork 생성 실패 (HTTP %s)" % st, detail=txt[:400])


def c_collab(a):
    owner, repo = a.repo.split("/", 1)
    st, js, _ = gitea("GET", "/repos/%s/%s/collaborators/%s/permission" % (owner, repo, a.user))
    is_collab_st, _, _ = gitea("GET", "/repos/%s/%s/collaborators/%s" % (owner, repo, a.user))
    if is_collab_st == 204:
        perm = (js or {}).get("permission")
        rank = {"read": 1, "write": 2, "admin": 3, "owner": 4}
        if rank.get(perm, 0) >= rank.get(a.perm, 2):
            out(True, "exists", "이미 공동작업자 (%s)" % perm, permission=perm)
        out(False, "conflict", "이미 공동작업자이나 권한이 %s - 수정하지 않음. 저장소 설정에서 직접 %s로 변경 필요"
            % (perm, a.perm), permission=perm)
    st, _, txt = gitea("PUT", "/repos/%s/%s/collaborators/%s" % (owner, repo, a.user), {"permission": a.perm})
    if st in (200, 201, 204):
        st2, js2, _ = gitea("GET", "/repos/%s/%s/collaborators/%s/permission" % (owner, repo, a.user))
        out(True, "created", "공동작업자 추가", permission=(js2 or {}).get("permission"))
    out(False, "api_error", "공동작업자 추가 실패 (HTTP %s)" % st, detail=txt[:400])


def _resolve(path, repo_name):
    """Accept either a parent folder or the repository folder itself."""
    cwd = os.getcwd()
    given = os.path.abspath(path or cwd)
    if os.path.basename(os.path.normpath(given)).lower() == repo_name.lower():
        parent, target = os.path.dirname(os.path.normpath(given)), os.path.normpath(given)
    else:
        parent, target = given, os.path.join(given, repo_name)
    return cwd, parent, target


def c_resolve_path(a):
    repo_name = a.repo.split("/", 1)[-1]
    cwd, parent, target = _resolve(a.path, repo_name)
    warn = []
    if re.search(r"[^\x00-\x7F]| ", target):
        warn.append("경로에 한글 또는 공백이 있음 - 빌드 도구 오류 가능, 다른 경로 권장")
    state = "new"
    origin = None
    if os.path.isdir(os.path.join(target, ".git")):
        origin = git(["remote", "get-url", "origin"], cwd=target, check=False).stdout.strip()
        state = "same_repo" if repo_name.lower() in origin.lower() else "other_repo"
    elif os.path.exists(target) and os.listdir(target):
        state = "not_empty"
    out(True, "resolved", "", cwd=cwd, used_cwd=not a.path, parent=parent, target=target,
        parent_exists=os.path.isdir(parent), target_state=state, origin=origin, warnings=warn)


def c_clone(a):
    repo_name = a.repo.split("/", 1)[1]
    _, dest_parent, target = _resolve(a.dest, repo_name)
    warn = []
    if re.search(r"[^\x00-\x7F]| ", target):
        warn.append("경로에 한글 또는 공백이 있음 - 빌드 도구 오류 가능")
    if os.path.isdir(os.path.join(target, ".git")):
        p = git(["remote", "get-url", "origin"], cwd=target, check=False)
        url = p.stdout.strip()
        if a.repo.lower() in url.lower():
            git(["fetch", "--prune", "origin"], cwd=target, auth=True)
            out(True, "exists", "이미 Clone되어 있어 재사용(fetch만 수행)", path=target, warnings=warn)
        out(False, "conflict", "폴더에 다른 저장소가 있음 - 건드리지 않음", path=target, origin=url)
    if os.path.exists(target) and os.listdir(target):
        out(False, "conflict", "대상 폴더가 비어 있지 않음 - 건드리지 않음", path=target)
    os.makedirs(dest_parent, exist_ok=True)
    base = (a.gitea_url or g_base()).rstrip("/")
    if not base:
        out(False, "invalid", "Gitea 주소를 알 수 없음 - --gitea-url 지정")
    url = base + "/" + a.repo + ".git"
    git(["clone", url, target], auth=True)
    sub = git(["submodule", "update", "--init", "--recursive"], cwd=target, auth=True, check=False)
    if sub.returncode != 0:
        warn.append("서브모듈 받기 실패(권한 없음 등) - 본 저장소는 정상. 빌드 필요 여부는 SKILL.md 참고")
    out(True, "created", "Clone 완료", path=target, warnings=warn)


def c_detect_project(a):
    root = os.path.abspath(a.path)
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        depth = os.path.relpath(dirpath, root).count(os.sep)
        if depth > 2:
            dirnames[:] = []
            continue
        if os.path.basename(dirpath).lower() == "build" and "Build.bat" in filenames:
            rel = os.path.relpath(os.path.dirname(dirpath), root)
            names = set(filenames)
            hits.append({"project": "." if rel == "." else rel.replace("\\", "/"),
                         "has_hook_std": "Build_Hook_GIT_ASEC.bat" in names,
                         "has_gitpush": "GitPush.bat" in names,
                         "other_hooks": sorted(n for n in names if n.lower().startswith("build_hook")
                                               and n != "Build_Hook_GIT_ASEC.bat")})
    if not hits:
        out(False, "not_found", "Build/Build.bat을 찾지 못함 - 프로젝트 폴더를 사용자에게 확인")
    out(True, "detected", "", candidates=hits)


def c_branch(a):
    root = os.path.abspath(a.path)
    git(["fetch", "--prune", "origin"], cwd=root, auth=True)
    remote = git(["ls-remote", "--heads", "origin", a.name], cwd=root, auth=True).stdout.strip()
    local = git(["rev-parse", "--verify", "--quiet", a.name], cwd=root, check=False).returncode == 0
    if remote:
        if local:
            git(["checkout", a.name], cwd=root)
        else:
            git(["checkout", "-b", a.name, "--track", "origin/" + a.name], cwd=root)
        out(True, "exists", "원격에 브랜치가 이미 있어 재사용", branch=a.name)
    if local:
        out(False, "conflict", "로컬에만 같은 이름 브랜치가 있음 - 건드리지 않음", branch=a.name)
    base = "origin/" + a.base
    if git(["rev-parse", "--verify", "--quiet", base], cwd=root, check=False).returncode != 0:
        out(False, "not_found", "기준 브랜치 없음: " + base)
    git(["checkout", "-b", a.name, base], cwd=root)
    git(["push", "-u", "origin", a.name], cwd=root, auth=True)
    head = git(["rev-parse", "--short", "HEAD"], cwd=root).stdout.strip()
    out(True, "created", "작업 브랜치 생성·push", branch=a.name, base=a.base, head=head)


def _render_gitpush(name, email):
    raw = open(os.path.join(ASSETS, "GitPush.bat"), "rb").read()
    for val in (name, email):
        if not re.fullmatch(r"[\x21-\x7E]+", val) or val.startswith("<"):
            out(False, "invalid", "COMMIT_NAME/EMAIL은 공백 없는 영문·숫자·기호만 가능: " + val)
    raw = raw.replace(b'set "COMMIT_NAME=<Gitea display name>"', ('set "COMMIT_NAME=%s"' % name).encode())
    raw = raw.replace(b'set "COMMIT_EMAIL=<company email>"', ('set "COMMIT_EMAIL=%s"' % email).encode())
    return raw


def c_add_bat(a):
    root = os.path.abspath(a.path)
    cur = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root).stdout.strip()
    if cur != a.name:
        out(False, "wrong_branch", "현재 브랜치가 %s가 아님 (현재: %s)" % (a.name, cur))
    build_dir = os.path.join(root, a.project, "Build") if a.project != "." else os.path.join(root, "Build")
    if not os.path.isfile(os.path.join(build_dir, "Build.bat")):
        out(False, "not_found", "Build.bat 없음: " + build_dir)
    files = {
        "Build_Hook_GIT_ASEC.bat": open(os.path.join(ASSETS, "Build_Hook_GIT_ASEC.bat"), "rb").read(),
        "GitPush.bat": _render_gitpush(a.commit_name, a.email),
    }
    added, same, conflict = [], [], []
    norm = lambda b: b.replace(b"\r\n", b"\n")
    for fn, data in files.items():
        dst = os.path.join(build_dir, fn)
        if os.path.exists(dst):
            (same if norm(open(dst, "rb").read()) == norm(data) else conflict).append(fn)
            continue
        with open(dst, "wb") as f:
            f.write(data)
        added.append(fn)
    if conflict:
        out(False, "conflict", "같은 이름의 bat이 이미 있고 내용이 다름 - 덮어쓰지 않음", conflict=conflict,
            added=added, same=same, build_dir=build_dir)
    if not added:
        out(True, "exists", "표준 bat이 이미 있음", same=same)
    rel = [os.path.relpath(os.path.join(build_dir, f), root).replace("\\", "/") for f in added]
    git(["add", "--"] + rel, cwd=root)
    git(["commit", "-m", "[Build] Add Jenkins build scripts (Build_Hook_GIT_ASEC.bat, GitPush.bat)"], cwd=root)
    git(["push", "origin", a.name], cwd=root, auth=True)
    head = git(["rev-parse", "--short", "HEAD"], cwd=root).stdout.strip()
    out(True, "created", "표준 bat 추가·커밋·push", added=rel, head=head)


def c_job_info(a):
    st, txt = jenkins("GET", job_path(a.name) + "/api/json?tree=name,disabled")
    exists = st == 200
    st2, vtxt = jenkins("GET", "/api/json?tree=views[name]")
    views = [v["name"] for v in json.loads(vtxt).get("views", [])] if st2 == 200 else []
    creds = []
    if a.ref_job:
        st3, cx = jenkins("GET", job_path(a.ref_job) + "/config.xml")
        if st3 == 200:
            creds = sorted(set(re.findall(r"<credentialsId>([^<]+)</credentialsId>", cx)))
    out(True, "job_info", "", exists=exists, views=views, credential_ids_from_ref=creds)


def c_render_job(a):
    tpl = open(os.path.join(ASSETS, "job_config_template.xml"), encoding="utf-8").read()
    proj = a.project.replace("/", "\\")
    cmd = ("Build\\Build_Hook_GIT_ASEC.bat" if proj == "." else proj + "\\Build\\Build_Hook_GIT_ASEC.bat") \
        + " %BuildType% -j8"
    perms = "\n".join("      <permission>USER:%s:%s</permission>" % (p, xml_escape(a.user)) for p in JOB_PERMS)
    vals = {"DESCRIPTION": a.description or "", "PERMISSIONS": perms, "REPO_URL": a.repo_url,
            "CREDENTIALS_ID": a.cred_id, "BRANCH_SPEC": a.branch_spec, "BUILD_COMMAND": cmd}
    for k, v in vals.items():
        tpl = tpl.replace("${%s}" % k, v if k == "PERMISSIONS" else xml_escape(v))
    ET.fromstring(tpl.encode("utf-8"))  # well-formed check
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(tpl)
    out(True, "rendered", "Job XML 생성", file=os.path.abspath(a.out), build_command=cmd)


def c_job_create(a):
    st, _ = jenkins("GET", job_path(a.name) + "/api/json?tree=name")
    if st == 200:
        out(False, "conflict", "같은 이름의 Job이 이미 있음 - 수정하지 않음", name=a.name)
    xml = open(a.xml, encoding="utf-8").read()
    prefix = "/view/" + urllib.parse.quote(a.view) if a.view else ""
    st, txt = jenkins("POST", prefix + "/createItem?name=" + urllib.parse.quote(a.name), xml,
                      {"Content-Type": "application/xml; charset=utf-8"})
    if st in (200, 201, 302):
        out(True, "created", "Job 생성 (비활성 상태)", name=a.name, view=a.view)
    out(False, "api_error", "Job 생성 실패 (HTTP %s)" % st, detail=re.sub(r"<[^>]+>", " ", txt)[:500])


def c_job_verify(a):
    st, cx = jenkins("GET", job_path(a.name) + "/config.xml")
    if st != 200:
        out(False, "not_found", "Job config.xml 조회 실패 (HTTP %s)" % st)
    x = ET.fromstring(cx.encode("utf-8"))
    get = lambda p: [e.text or "" for e in x.iter() if e.tag == p]
    proj = a.project.replace("/", "\\")
    exp_cmd = ("Build\\Build_Hook_GIT_ASEC.bat" if proj == "." else proj + "\\Build\\Build_Hook_GIT_ASEC.bat") \
        + " %BuildType% -j8"
    choices = [e.text for e in x.iter("string")]
    perms = get("permission")
    checks = {
        "repo_url": get("url") == [a.repo_url],
        "branch_spec": a.branch_spec in get("name"),
        "exclusion_exact": get("excludedMessage") == [EXCLUSION],
        "poll_scm": get("spec") == ["* * * * *"],
        "build_command": [c.strip() for c in get("command")] == [exp_cmd],
        "param_default_hook": bool(choices) and choices[0] == "Hook",
        "user_permissions": all(("USER:%s:%s" % (p, a.user) in perms) or (p + ":" + a.user in perms)
                                for p in ["hudson.model.Item.Build", "hudson.model.Item.Read",
                                          "hudson.model.Item.Configure"]),
        "credentials_set": any(t.strip() for t in get("credentialsId")),
    }
    disabled = (get("disabled") or ["?"])[0]
    ok = all(checks.values())
    out(ok, "verified" if ok else "mismatch", "" if ok else "불일치 항목 확인 필요 (수정하지 않음)",
        checks=checks, disabled=disabled, excluded_message_raw=get("excludedMessage"))


def c_job_enable(a):
    st, txt = jenkins("POST", job_path(a.name) + "/enable")
    if st in (200, 302):
        out(True, "enabled", "Job 활성화 - 1분 안에 Poll SCM이 첫 빌드를 시작할 수 있음")
    out(False, "api_error", "활성화 실패 (HTTP %s)" % st)


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="gitea-jenkins-setup helper")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("preflight")
    p = sp.add_parser("repo-info"); p.add_argument("--repo", required=True)
    p = sp.add_parser("fork"); p.add_argument("--repo", required=True); p.add_argument("--org")
    p = sp.add_parser("collab"); p.add_argument("--repo", required=True); p.add_argument("--user", required=True)
    p.add_argument("--perm", default="write")
    p = sp.add_parser("clone"); p.add_argument("--repo", required=True); p.add_argument("--dest")
    p.add_argument("--gitea-url")
    p = sp.add_parser("resolve-path"); p.add_argument("--repo", required=True); p.add_argument("--path")
    p = sp.add_parser("detect-project"); p.add_argument("--path", required=True)
    p = sp.add_parser("branch"); p.add_argument("--path", required=True); p.add_argument("--base", required=True)
    p.add_argument("--name", required=True)
    p = sp.add_parser("add-bat"); p.add_argument("--path", required=True); p.add_argument("--project", required=True)
    p.add_argument("--name", required=True); p.add_argument("--commit-name", required=True)
    p.add_argument("--email", required=True)
    p = sp.add_parser("job-info"); p.add_argument("--name", required=True); p.add_argument("--ref-job")
    p = sp.add_parser("render-job")
    for k in ["--name", "--repo-url", "--branch-spec", "--project", "--user", "--cred-id", "--out"]:
        p.add_argument(k, required=True)
    p.add_argument("--description", default="")
    p = sp.add_parser("job-create"); p.add_argument("--name", required=True); p.add_argument("--xml", required=True)
    p.add_argument("--view")
    p = sp.add_parser("job-verify")
    for k in ["--name", "--repo-url", "--branch-spec", "--project", "--user"]:
        p.add_argument(k, required=True)
    p = sp.add_parser("job-enable"); p.add_argument("--name", required=True)
    a = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    needs_gitea = {"repo-info", "fork", "collab"}
    needs_jenkins = {"job-info", "job-create", "job-verify", "job-enable"}
    if a.cmd in needs_gitea and not (env("GITEA_URL") and env("GITEA_TOKEN")):
        out(False, "no_api", "GITEA_URL/GITEA_TOKEN 없음 - Chrome 모드로 진행 (references/chrome_mode.md)")
    if a.cmd in needs_jenkins and not (env("JENKINS_URL") and env("JENKINS_USER") and env("JENKINS_TOKEN")):
        out(False, "no_api", "JENKINS_URL/USER/TOKEN 없음 - Chrome 모드로 진행 (references/chrome_mode.md)")
    {
        "preflight": c_preflight, "repo-info": c_repo_info, "fork": c_fork, "collab": c_collab,
        "clone": c_clone, "resolve-path": c_resolve_path, "detect-project": c_detect_project, "branch": c_branch, "add-bat": c_add_bat,
        "job-info": c_job_info, "render-job": c_render_job, "job-create": c_job_create,
        "job-verify": c_job_verify, "job-enable": c_job_enable,
    }[a.cmd](a)


if __name__ == "__main__":
    main()
