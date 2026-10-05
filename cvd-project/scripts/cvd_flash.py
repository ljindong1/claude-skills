# -*- coding: utf-8 -*-
"""
cvd_flash.py - CVD(CodeViser) CLI 다운로드 + 검증

  init    과제 폴더 생성 (Projects\\<NAME>\\<NAME>_*.csf) + loadfile.csf 등록
  scan    저장소에서 이미지·MCU·뱅크 구성 인식 결과만 출력 (변경 없음)
  flash   이미지 기록 → 검증 (--yes 없으면 계획만 출력)
  verify  기록 없이 검증만
  list    생성된 과제 목록
  startup 시작 메뉴 "CVD Projects" 바로가기 생성 (CVD 를 켜면 cvd_start.csf 먼저 실행, init 도 만든다)
  refresh 기존 과제의 PD 창·툴바 스크립트를 새 템플릿으로 다시 생성 (config 는 유지)

예)
  python cvd_flash.py scan --repo D:\\w\\psu_app
  python cvd_flash.py init --repo D:\\w\\psu_app --name HE1I_PSU --bank dual --yes --dry-run
  python cvd_flash.py flash --name HE1I_PSU                 (계획만 출력)
  python cvd_flash.py flash --name HE1I_PSU --yes           (FBL+APP, 데이터 영역까지 소거)
  python cvd_flash.py flash --name HE1I_PSU --mode ALL --keep-data --rescan --yes
  python cvd_flash.py verify --name HE1I_PSU
  (CVD 가 기본 경로 C:\\JnDTech\\CVI\\CVD 에 없으면 모든 명령에 --cvd-root <설치 폴더>)

라이팅 기본 틀은 이 스크립트 옆의 ..\\assets\\cyt2bl_dual 을 쓴다. S32_Config 는 읽지 않는다.

종료 코드: 0 성공 / 1 사용 오류 / 2 기록 미완료 / 3 검증 불일치 / 4 검증 미완료
          5 쓰기 단계 시간 초과(CVD 를 끄지 않음) / 6 타깃 연결 실패
Python 3 표준 라이브러리만 사용한다.
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys
import time

VERSION = "1.5.0"

# 실제 파일 위치(FS)와 .csf 안에 적힐 윈도우 경로(WIN)를 나눈다. 평소에는 같다.
# --cvd-root 로 바꿀 수 있다 (set_root). CVD_ROOT / CVD_ROOT_WIN / CVD_EXE 환경변수는 시험용이다.
DEFAULT_ROOT = r"C:\JnDTech\CVI\CVD"
WIN_ROOT = FS_ROOT = FS_PROJECTS = WIN_PROJECTS = CVD_EXE = None


def set_root(root=None):
    global WIN_ROOT, FS_ROOT, FS_PROJECTS, WIN_PROJECTS, CVD_EXE
    WIN_ROOT = (root or os.environ.get("CVD_ROOT_WIN") or DEFAULT_ROOT).rstrip("\\/")
    FS_ROOT = os.environ.get("CVD_ROOT", WIN_ROOT) if not root else root
    FS_PROJECTS = os.path.join(FS_ROOT, "Projects")
    WIN_PROJECTS = WIN_ROOT + "\\Projects"
    CVD_EXE = os.environ.get("CVD_EXE", os.path.join(FS_ROOT, "Bin", "CVD.exe"))


set_root()

# 라이팅 기본 틀 (스킬에 동봉). 원본은 S32_Config\_BASE_CYT2BL_Dual 이며 그 경로가 파일 안에 남아 있다.
TEMPLATE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "cyt2bl_dual"))
TEMPLATE_ORIGIN_WIN = r"C:\JnDTech\CVI\CVD\S32_Config\_BASE_CYT2BL_Dual"
TEMPLATE_MCU = "CYT2BL"
TEMPLATE_BANK = "dual"
TEMPLATE_HOST = "cyt2blx_HOST_HAE_release.csf"
TEMPLATE_HSM = "cyt2blx_HSM_HAE_release.csf"
TEMPLATE_CONNECT = "connect.csf"      # 원본 이름 Path.cmm
TEMPLATE_RESET = "reset.csf"          # 원본 이름 Reset.cmm

ENC = "cp949"
NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,30}$")
MODES = ("IMAGE", "HSM", "ALL")
MAX_POINTS = 16
# CM4 에서 읽을 수 있는 코드 플래시 범위 (HSM 영역 0x10000000~0x10027FFF 제외)
VERIFY_RANGE = (0x10028000, 0x12000000)

EXIT_OK, EXIT_USAGE, EXIT_FLASH, EXIT_MISMATCH, EXIT_VERIFY, EXIT_TIMEOUT, EXIT_CONNECT = 0, 1, 2, 3, 4, 5, 6


# ============================================================== 공통
def die(msg, code=EXIT_USAGE):
    print("[중단] " + msg)
    sys.exit(code)


def rb(p):
    with open(p, "rb") as f:
        return f.read()


def wtext(p, text):
    """CVD 스크립트 규약: CP949 + CRLF."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode(ENC, "replace")
    with open(p, "wb") as f:
        f.write(data)


def wpath(*parts):
    return "\\".join(parts)


def proj_fs(name):
    return os.path.join(FS_PROJECTS, name)


def proj_win(name):
    return wpath(WIN_PROJECTS, name)


def find_cvd_installs():
    """기본 경로 밖에 설치된 CVD.exe 후보. 드라이브별 흔한 위치만 본다."""
    pats = []
    for drv in "CDEF":
        pats += [r"%s:\JnDTech\*\CVD\Bin\CVD.exe" % drv, r"%s:\JnDTech\CVD\Bin\CVD.exe" % drv,
                 r"%s:\Program Files*\JnDTech\*\CVD\Bin\CVD.exe" % drv]
    out = []
    for p in pats:
        for f in glob.glob(p):
            f = os.path.normpath(f)
            if f not in out:
                out.append(f)
    return out


def check_cvd(strict=True):
    """CVD 설치 확인. 없으면 다른 설치 위치를 찾아 알려 주고, strict 면 중단한다."""
    if os.path.isfile(CVD_EXE):
        return True
    others = [f for f in find_cvd_installs() if os.path.normcase(f) != os.path.normcase(CVD_EXE)]
    print("[CVD] 설치를 찾지 못했습니다: %s" % CVD_EXE)
    for f in others:
        root = os.path.dirname(os.path.dirname(f))
        print("  다른 위치에 있음: %s  → --cvd-root \"%s\"" % (f, root))
    if not others:
        print("  흔한 설치 위치(C~F 드라이브 JnDTech, Program Files)에도 없습니다. 설치 경로를 --cvd-root 로 지정하세요.")
    if strict:
        die("CVD 설치 경로를 확인한 뒤 다시 실행하세요. 과제는 만들지 않았습니다.")
    return False


def ask(prompt, default=None):
    if not sys.stdin.isatty():
        return default
    tail = " [%s]" % default if default else ""
    try:
        v = input("%s%s > " % (prompt, tail)).strip().strip('"')
    except EOFError:
        die("입력을 받을 수 없습니다. 값을 인자로 지정하세요 (%s)." % prompt)
    return v or default


# ============================================================== 저장소 인식
IMG_EXT = (".sre", ".s19", ".srec", ".s28", ".s37", ".mot")
SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".vs"}
BANK_DIR_RE = re.compile(r"^(dual|single)[_\- ]?bank$", re.I)


def _by_time(files):
    """최근 수정 순. 첫 번째가 기본 선택이다."""
    return sorted(files, key=os.path.getmtime, reverse=True)


# ---- 버전별 빌드 폴더 (Jenkins PostPackage.bat: Debug\OEUK_xxxx\<버전>\)
# 파일 이름은 버전마다 같고(he1i_psu_app_v3_0_26*) 폴더 이름만 다르다. 그래서 APP(_Writing.s19)와
# ELF 는 항상 고른 버전 폴더에서 한 쌍으로 가져온다. rom_<버전>\ 은 aSIMS 서명 입력이라 제외.
# <버전>_test\ = OEUK_TEST 빌드(H-OTA 테스트용, 기준 버전으로 이름 붙음). 고르면 FBL 도 TEST 짝으로 바뀐다.
VER_DIR_RE = re.compile(r"^\d{3,8}(_test)?$")
TEST_SUFFIX = "_test"


def is_test(v):
    return bool(v) and v.endswith(TEST_SUFFIX)


def ver_num(v):
    """'26810_test' → 26810. 버전 비교(더 새 버전)는 이 숫자로만 한다."""
    b = v[:-len(TEST_SUFFIX)] if is_test(v) else (v or "")
    return int(b) if b.isdigit() else 0


def newest_ver(vs):
    """가장 새 버전 = test 가 아닌 것 중 가장 큰 번호 (test 만 있으면 그중에서)."""
    base = [v for v in vs if not is_test(v)] or list(vs)
    return max(base, key=ver_key) if base else None


def find_versions(repo):
    """{버전: {"app", "elf", "dir", "variant"}}. _Writing.s19 와 .elf 가 하나씩 있는 폴더만."""
    out = {}
    for pat in (os.path.join(repo, "Debug", "OEUK_*", "*"), os.path.join(repo, "*", "Debug", "OEUK_*", "*")):
        for vdir in glob.glob(pat):
            ver = os.path.basename(vdir)
            if not (os.path.isdir(vdir) and VER_DIR_RE.match(ver)):
                continue
            fs = os.listdir(vdir)
            app = [f for f in fs if f.lower().endswith("_writing.s19")]
            elf = [f for f in fs if f.lower().endswith(".elf")]
            if len(app) == 1 and len(elf) == 1:
                out[ver] = {"app": os.path.join(vdir, app[0]), "elf": os.path.join(vdir, elf[0]),
                            "dir": vdir, "variant": os.path.basename(os.path.dirname(vdir))}
    return out


def source_version(repo):
    """PJ_Define.h 에서 켜진 OEUK_* 블록의 SOFTWARE_VERSION_0~4 → (변형, 버전). 못 찾으면 (None, None)."""
    for pat in (os.path.join(repo, "Application", "app_code", "a_app_service", "src", "PJ_Define.h"),
                os.path.join(repo, "*", "Application", "app_code", "a_app_service", "src", "PJ_Define.h")):
        for p in glob.glob(pat):
            t = rb(p).decode("latin-1")
            m = re.search(r"^[ \t]*#define[ \t]+(OEUK_\w+)", t, re.M)
            if not m:
                continue
            b = re.search(r"defined\s*\(\s*%s\s*\)(.*?)#\s*(elif|else|endif)" % m.group(1), t, re.S)
            if not b:
                continue
            ch = [re.search(r"#define\s+SOFTWARE_VERSION_%d\s+\(u8\)'(.)'" % i, b.group(1)) for i in range(5)]
            if all(ch):
                return m.group(1), "".join(x.group(1) for x in ch)
    return None, None


def ver_key(v):
    """정렬용: 26810, 26810_test, 26811, … (같은 번호면 test 가 뒤)."""
    return (ver_num(v), 1 if is_test(v) else 0)


def print_versions(vs, cur=None, src=None, indent="  "):
    """버전 목록. ▶ = 지금 선택, (현재 소스) = PJ_Define.h 버전."""
    newest = newest_ver(vs)
    for v in sorted(vs, key=ver_key):
        tags = []
        if v == src:
            tags.append("현재 소스")
        if v == newest:
            tags.append("가장 새 버전")
        if is_test(v):
            tags.append("TEST")
        print("%s%s %-8s %-22s %s" % (indent, "▶" if v == cur else " ", v, " · ".join(tags),
                                     os.path.relpath(vs[v]["dir"], os.path.dirname(os.path.dirname(vs[v]["dir"])))))


def stamp(p):
    """재빌드 감지용: 크기_수정시각. 같은 버전 폴더를 Jenkins 가 다시 만들면 달라진다."""
    try:
        st = os.stat(p)
        return "%d_%d" % (st.st_size, int(st.st_mtime))
    except OSError:
        return ""


# ---- FBL : APP 저장소 References\02_Fbl_Binary\OEUK_<차종>[_TEST]\
# FBL 저장소 Jenkins 결과(Debug\OEUK_HE1I\, Debug\OEUK_HE1I_TEST\)를 같은 이름 폴더로 복사해 커밋해 둔 곳.
# 파일 이름은 두 폴더가 같으므로(he1i_psu_fbl_v3_0_18.*) 폴더로 고른다. TEST FBL 은 --fbl 로 직접 지정.
FBL_BIN_DIR = "02_fbl_binary"


def fbl_folder(p):
    """02_Fbl_Binary 아래 파일이면 그 OEUK 폴더 이름, 아니면 None."""
    parent = os.path.dirname(p)
    if os.path.basename(os.path.dirname(parent)).lower() == FBL_BIN_DIR:
        return os.path.basename(parent)
    return None


def order_fbl(files, variant):
    """(정렬된 후보, 고른 이유). 02_Fbl_Binary\\<variant>\\ 의 .sre 를 맨 앞에, 나머지는 최근 순."""
    if variant:
        own = [p for p in files if (fbl_folder(p) or "").upper() == variant.upper()]
        if own:
            own = sorted(_by_time(own), key=lambda p: not p.lower().endswith(".sre"))
            return own + [p for p in _by_time(files) if p not in own], \
                "02_Fbl_Binary\\%s (APP 차종 %s)" % (fbl_folder(own[0]), variant)
    return _by_time(files), ""


def paired_fbl(repo, versions, ver):
    """APP 버전에 짝이 되는 FBL: <버전> → 02_Fbl_Binary\\OEUK_<차종>\\, <버전>_test → OEUK_<차종>_TEST\\ 의 .sre.
    (경로, 폴더 이름). 그 폴더가 없으면 (None, 찾아본 폴더 이름)."""
    info = (versions or {}).get(ver)
    if not info:
        return None, ""
    folder = info["variant"] + ("_TEST" if is_test(ver) else "")
    hits = []
    for pat in (os.path.join(repo, "References", "02_Fbl_Binary", folder, "*.sre"),
                os.path.join(repo, "*", "References", "02_Fbl_Binary", folder, "*.sre")):
        hits += glob.glob(pat)
    return (_by_time(hits)[0] if hits else None), folder


def apply_paired_fbl(c, versions, given):
    """c["fbl"] 를 APP 버전의 짝으로 맞춘다. --fbl 을 줬으면 그대로. 짝 폴더가 없을 때:
    test 버전이면 멈춘다(엉뚱한 FBL 로 쓰지 않도록), 일반 버전이면 지금 값을 둔다(02_Fbl_Binary 없는 저장소)."""
    c["_fbl_why"] = ""
    if given or not c.get("version"):
        return
    p, folder = paired_fbl(c["repo"], versions, c["version"])
    if p:
        c["fbl"] = p
        c["_fbl_why"] = "APP %s 의 짝 — 02_Fbl_Binary\\%s" % (c["version"], folder)
    elif is_test(c["version"]):
        die("APP %s(TEST) 의 짝 FBL 이 없습니다: References\\02_Fbl_Binary\\%s\\*.sre. "
            "아무것도 쓰지 않았습니다. APP 저장소를 git pull 하거나 --fbl <경로> 로 지정하세요." % (c["version"], folder))


def other_versions(vs, ver):
    """버전 구별 지점을 고를 비교 순서. 앞쪽 버전과의 차이가 먼저 뽑힌다.
    일반 버전: 다른 일반 버전 먼저(SW 버전 문자열 차이). test: 같은 번호 일반 버전 먼저(OEUK 차이)."""
    rest = [v for v in sorted(vs, key=ver_key) if v != ver]
    if is_test(ver):
        twin = ver[:-len(TEST_SUFFIX)]
        return [v for v in rest if v == twin] + [v for v in rest if v != twin]
    return [v for v in rest if not is_test(v)] + [v for v in rest if is_test(v)]


def discover(repo):
    repo = os.path.abspath(repo)
    if not os.path.isdir(repo):
        die("프로젝트 폴더가 없습니다: " + repo)
    imgs, elfs, bank_dirs = [], [], []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.lower().startswith("rom_")]
        for dn in dirs:
            if BANK_DIR_RE.match(dn):
                bank_dirs.append(os.path.join(root, dn))
        for fn in files:
            low = fn.lower()
            p = os.path.join(root, fn)
            if low.endswith(IMG_EXT):
                imgs.append(p)
            elif low.endswith(".elf"):
                elfs.append(p)
    low = lambda p: os.path.basename(p).lower()
    versions = find_versions(repo)
    in_ver = {os.path.normcase(v["dir"]) for v in versions.values()}
    if in_ver:                                    # 버전 폴더 안 APP·ELF 는 버전으로만 고른다
        imgs = [p for p in imgs if os.path.normcase(os.path.dirname(p)) not in in_ver]
        elfs = [p for p in elfs if os.path.normcase(os.path.dirname(p)) not in in_ver]
    hsm = [p for p in imgs if "hsm" in low(p)]
    fbl = [p for p in imgs if "fbl" in low(p) or "boot" in low(p)]
    rest = [p for p in imgs if p not in hsm and p not in fbl]
    app_w = [p for p in rest if "_writing" in low(p)] or [p for p in rest if "app" in low(p)] or rest
    elf = [p for p in elfs if "fbl" not in low(p) and "hsm" not in low(p)]
    elf = [p for p in elf if "app" in low(p)] or elf
    src_variant, src_ver = source_version(repo)
    # FBL 차종 = APP 버전 폴더의 OEUK(Debug\OEUK_HE1I\<버전>\), 없으면 PJ_Define.h 에서 켜진 OEUK
    ver_variants = {v["variant"] for v in versions.values()}
    fbl_variant = ver_variants.pop() if len(ver_variants) == 1 else src_variant
    fbl_sorted, fbl_why = order_fbl(fbl, fbl_variant)
    cands = {"fbl": fbl_sorted, "hsm": _by_time(hsm), "elf": _by_time(elf), "app": _by_time(app_w)}
    d = {"repo": repo, "cands": cands, "fbl_why": fbl_why}
    for k in ("fbl", "hsm", "elf"):
        d[k] = cands[k][0] if cands[k] else None
    d["app"] = cands["app"][0] if cands["app"] else d["elf"]      # 기록용 APP (없으면 ELF 로 기록)
    d["versions"] = versions
    d["src_variant"], d["src_ver"] = src_variant, src_ver
    d["version"] = ""
    if versions:                                  # 버전 폴더 구조: 하나면 그것, 여러 개면 사용자가 고른다
        d["app"] = d["elf"] = None
        cands["app"], cands["elf"] = [], []
        if len(versions) == 1:
            use_version(d, list(versions)[0])
    d["mcu"] = detect_mcu(repo)
    d["name"] = suggest_name(repo, d["hsm"])
    d["bank"], d["bank_why"] = detect_bank(repo, bank_dirs)
    return d


def use_version(d, ver):
    """d 의 APP·ELF·version 을 그 버전 폴더의 한 쌍으로 바꾼다. 경로가 버전을 따라가는 유일한 곳."""
    v = d["versions"][ver]
    d["app"], d["elf"], d["version"] = v["app"], v["elf"], ver


def choose_version(d, want, keep, what):
    """버전 폴더 저장소에서 쓸 버전을 정하고 APP·ELF 를 그 폴더로 맞춘다.
    want = --version, keep = config 에 저장된 버전(flash/set/verify 의 기본값). 정할 수 없으면 목록을 보여 주고 멈춘다."""
    vs = d["versions"]
    if not vs:
        if want:
            die("버전 폴더(Debug\\OEUK_xxxx\\<버전>\\)가 없는 저장소라 --version 을 쓸 수 없습니다.")
        return
    ver = want or keep
    why = "--version" if want else "config"
    if not ver and len(vs) == 1:
        ver, why = list(vs)[0], "하나뿐"
    if not ver or ver not in vs:
        print("[버전] %s 폴더 목록 (_Writing.s19 + .elf 가 있는 것)" % d["repo"])
        print_versions(vs, None, d.get("src_ver"))
        rec = d.get("src_ver") if d.get("src_ver") in vs else newest_ver(vs)
        if not ver:
            die("%s: 버전 폴더가 여러 개입니다. --version <버전> 으로 고르세요 (추천 %s)." % (what, rec))
        if want:
            die("%s: 버전 %s 폴더가 없거나 _Writing.s19/.elf 가 없습니다. 위 목록에서 고르세요." % (what, ver))
        die("%s: config 의 버전 %s 폴더가 저장소에 없습니다(정리됐거나 Build_all 로 바뀜). "
            "아무것도 쓰지 않았습니다. --version <버전> 으로 다시 고르세요 (추천 %s)." % (what, ver, rec))
    use_version(d, ver)
    d["version_why"] = why


def detect_bank(repo, bank_dirs):
    """저장소 안의 DUAL_BANK / SINGLE_BANK 폴더로 뱅크 구성을 추정한다. 판단은 사용자가 한다."""
    kinds = {}
    for p in bank_dirs:
        k = BANK_DIR_RE.match(os.path.basename(p)).group(1).lower()
        kinds.setdefault(k, []).append(os.path.relpath(p, repo))
    if len(kinds) == 1:
        k = list(kinds)[0]
        return k, kinds[k]
    if len(kinds) > 1:
        return None, ["%s: %s" % (k, ", ".join(v)) for k, v in sorted(kinds.items())]
    return None, []


def detect_mcu(repo):
    cnt = {}
    base = os.path.join(repo, "Configuration")
    base = base if os.path.isdir(base) else repo
    for root, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for fn in files:
            if not fn.lower().endswith((".arxml", ".h")):
                continue
            p = os.path.join(root, fn)
            if os.path.getsize(p) > 20 * 1024 * 1024:
                continue
            try:
                t = rb(p).decode("latin-1")
            except OSError:
                continue
            for m in re.findall(r"CYT[0-9][A-Z0-9]{3,8}", t):
                cnt[m] = cnt.get(m, 0) + 1
    if not cnt:
        return None
    return sorted(cnt.items(), key=lambda kv: (len(kv[0]), kv[1]), reverse=True)[0][0]


def suggest_name(repo, hsm):
    if hsm:
        m = re.search(r"rel_([A-Za-z0-9]+)_([A-Za-z0-9]+)_V", os.path.basename(hsm))
        if m:
            return ("%s_%s" % (m.group(1), m.group(2))).upper()
    n = re.sub(r"[^A-Za-z0-9]+", "_", os.path.basename(repo.rstrip("\\/"))).strip("_").upper()
    if not n or not n[0].isalpha():
        n = "P_" + n
    return n[:31]


# ============================================================== 라이팅 기본 틀
def read_cpu(folder):
    p = os.path.join(folder, TEMPLATE_CONNECT)
    if not os.path.isfile(p):
        return None
    t = rb(p).decode(ENC, "replace")
    for line in t.splitlines():
        s = line.strip()
        if s.startswith(";"):
            continue
        m = re.match(r"SYStem\.cpu\s+([A-Za-z0-9_+\-]+)", s, re.I)
        if m:
            return m.group(1)
    return None


def template_check():
    need = (TEMPLATE_CONNECT, TEMPLATE_RESET, TEMPLATE_HOST, TEMPLATE_HSM)
    miss = [f for f in need if not os.path.isfile(os.path.join(TEMPLATE_DIR, f))]
    if miss or not glob.glob(os.path.join(TEMPLATE_DIR, "*.out")):
        die("라이팅 기본 틀이 온전하지 않습니다: %s (누락: %s)" % (TEMPLATE_DIR, ", ".join(miss) or "*.out"))
    return read_cpu(TEMPLATE_DIR) or "?"


# ============================================================== 이미지 파싱 → 검증 지점
def parse_srec(path):
    recs = []
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if len(line) < 4 or line[0] != "S" or line[1] not in "123":
                continue
            al = {"1": 2, "2": 3, "3": 4}[line[1]]
            n = int(line[2:4], 16)
            a = int(line[4:4 + al * 2], 16)
            recs.append((a, bytes.fromhex(line[4 + al * 2:4 + n * 2 - 2])))
    return merge(recs)


def parse_elf(path):
    b = rb(path)
    if b[:4] != b"\x7fELF" or b[4] != 1:
        return []
    e = "<" if b[5] == 1 else ">"
    phoff, = struct.unpack_from(e + "I", b, 28)
    phentsize, phnum = struct.unpack_from(e + "HH", b, 42)
    recs = []
    for i in range(phnum):
        ptype, off, vaddr, paddr, fsz, msz, flg, al = struct.unpack_from(e + "8I", b, phoff + i * phentsize)
        if ptype == 1 and fsz:
            recs.append((paddr, b[off:off + fsz]))
    return merge(recs)


def merge(recs):
    recs.sort(key=lambda r: r[0])
    out = []
    for a, d in recs:
        if out and out[-1][0] + len(out[-1][1]) == a:
            out[-1][1].extend(d)
        else:
            out.append([a, bytearray(d)])
    return out


def load_image(path):
    return parse_elf(path) if path.lower().endswith(".elf") else parse_srec(path)


def verify_points(paths, per_image=8):
    """이미지마다 CM4 가 읽을 수 있는 구간에서 32비트 지점을 고른다.
    각 구간의 첫 워드 + 가장 큰 구간에서 고르게 몇 개."""
    pts = []
    for path in paths:
        if not path or not os.path.isfile(path):
            continue
        segs = []
        for a, d in load_image(path):
            lo, hi = max(a, VERIFY_RANGE[0]), min(a + len(d), VERIFY_RANGE[1])
            lo = (lo + 3) & ~3
            if hi - lo >= 4:
                segs.append((lo, d[lo - a:hi - a]))
        if not segs:
            continue
        chosen = []
        for a, d in segs[:per_image // 2]:
            chosen.append(a)
        big_a, big_d = max(segs, key=lambda s: len(s[1]))
        k = per_image - len(chosen)
        for i in range(1, k + 1):
            off = (len(big_d) * i // (k + 1)) & ~3
            if off + 4 <= len(big_d):
                chosen.append(big_a + off)
        lookup = {}
        for a, d in segs:
            lookup[a] = d
        for addr in sorted(set(chosen)):
            for a, d in segs:
                if a <= addr and addr + 4 <= a + len(d):
                    val = struct.unpack_from("<I", d, addr - a)[0]
                    pts.append((addr, val, os.path.basename(path)))
                    break
    return pts[:MAX_POINTS]


def version_points(app, others, n=4):
    """버전 폴더가 여러 개일 때: 이 APP 가 다른 버전 APP 와 다른 주소(워드)를 고른다.
    전체에서 고르게 뽑은 지점만으로는 버전끼리 구별되지 않는다 (26810/26820 은 1.5KB 만 다르고
    그중 0x10059004 에 SW 버전 문자열이 있다). 앞쪽 차이(상수·버전 영역)를 먼저, 나머지는 고르게."""
    if not app or not os.path.isfile(app):
        return []
    mine = [(a, bytes(d)) for a, d in load_image(app)]

    def word(addr):
        for a, d in mine:
            if a <= addr and addr + 4 <= a + len(d) and VERIFY_RANGE[0] <= addr < VERIFY_RANGE[1]:
                return struct.unpack_from("<I", d, addr - a)[0]
        return None

    picked = []
    for ver, other in others:
        if not os.path.isfile(other):
            continue
        theirs = {a: bytes(d) for a, d in load_image(other)}
        runs = []                                   # 다른 바이트가 있는 워드 주소 (차이 구간마다 첫 워드)
        for a, d in mine:
            t = theirs.get(a)
            if t is None:
                continue
            m = min(len(d), len(t))
            i, prev = 0, None
            while i < m:
                if d[i] != t[i]:
                    w = (a + i) & ~3
                    if prev is None or w > prev + 4:
                        runs.append(w)
                    prev = w
                    i = w + 4 - a                   # 같은 워드는 건너뜀
                else:
                    i += 1
        runs = [w for w in runs if word(w) is not None]
        if not runs:
            continue
        k = min(n, len(runs))
        sel = runs[:min(2, k)] + [runs[len(runs) * j // (k - 1)] for j in range(1, k - 1)] if k > 2 else runs[:k]
        for w in sel:
            if w not in [p[0] for p in picked]:
                picked.append((w, word(w), "%s (vs %s)" % (os.path.basename(app), ver)))
    return picked[:n]


# ============================================================== config.csf 읽고 쓰기
CFG_KEYS = ("name", "dir", "cpu", "bank", "mode", "erase", "banks", "repo", "version",
            "fbl", "app", "elf", "hsm", "src", "log", "template", "app_stamp")
# APP 를 쓸 뱅크 (듀얼뱅크). A = 벤더 원본대로 A 만(B 에는 FBL 만) / AB = B 에도 같은 APP
BANKS = ("A", "AB")
BANKS_KO = {"A": "뱅크 A 만", "AB": "뱅크 A·B 모두"}
# 다른 뱅크 확인 지점: APP 지점을 0x12000000 쪽(지금 실행하지 않는 뱅크)으로 옮겨 읽는다.
# AB 면 일치해야 성공, A 면 어느 버전이 들어 있는지 알리기만 한다.
BANK_B_OFFSET = 0x02000000
MAX_BPOINTS = 4


def cfg_path(name):
    return os.path.join(proj_fs(name), "%s_config.csf" % name)


def read_cfg(name):
    p = cfg_path(name)
    if not os.path.isfile(p):
        die("과제 %s 가 없습니다. 먼저 init 을 실행하세요: %s" % (name, p))
    t = rb(p).decode(ENC, "replace")
    c = {}
    for k in CFG_KEYS:
        m = re.search(r'&cfg_%s="([^"]*)"' % k, t)
        c[k] = m.group(1) if m else ""
    return c


def write_cfg(c):
    name = c["name"]
    c["app_stamp"] = stamp(c.get("app"))           # 검증 지점을 계산한 APP 파일 (재빌드 감지)
    vp = []
    if c.get("version") and c.get("repo"):         # 다른 버전과 구별되는 지점을 먼저 넣는다
        vs = find_versions(c["repo"])
        vp = version_points(c.get("app"), [(v, vs[v]["app"]) for v in other_versions(vs, c["version"])])
    base = [p for p in verify_points([c.get("fbl"), c.get("app")]) if p[0] not in [q[0] for q in vp]]
    pts = (vp + base)[:MAX_POINTS]
    c["banks"] = c.get("banks") if c.get("banks") in BANKS else "A"
    # 다른 뱅크 지점: 버전 구별 지점이 있으면 그것, 없으면 APP 지점 앞쪽
    app_bn = os.path.basename(c.get("app") or "")
    bsrc = vp or ([p for p in pts if p[2].startswith(app_bn)] if app_bn else [])
    bpts = [(a + BANK_B_OFFSET, v, s) for a, v, s in bsrc][:MAX_BPOINTS] if c.get("bank") == "dual" else []
    names = " ".join("&cfg_%s" % k for k in CFG_KEYS)
    vnames = " ".join("&cfg_va%d &cfg_ve%d" % (i, i) for i in range(1, MAX_POINTS + 1))
    bnames = " ".join("&cfg_vb%d &cfg_vbe%d" % (i, i) for i in range(1, MAX_BPOINTS + 1))
    L = [
        "; %s_config.csf - cvd_flash.py %s 가 생성. 경로는 cvd_flash.py 로 갱신한다." % (name, VERSION),
        "; 갱신: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "; cfg_erase: YES = 데이터 영역(DTC·NvM)까지 소거 / NO = 유지. CLI 에서 인자가 없을 때만 쓴다.",
        "; cfg_banks: A = APP 를 뱅크 A 에만(벤더 원본, B 에는 FBL 만) / AB = 뱅크 B 에도 같은 APP. PD·CLI 의 기본값.",
        "GLOBAL %s" % names,
        "GLOBAL %s" % vnames,
        "GLOBAL %s" % bnames,
    ]
    for k in CFG_KEYS:
        L.append('&cfg_%s="%s"' % (k, c.get(k, "") or ""))
    L.append("; 검증 지점: 주소 / 이미지 파일 기준 기대값 (CM4 에서 Data.Long 으로 읽어 비교)")
    for i in range(1, MAX_POINTS + 1):
        if i <= len(pts):
            a, v, src = pts[i - 1]
            L.append('&cfg_va%d="0x%08X"' % (i, a))
            L.append('&cfg_ve%d="0x%08X"   ; %s' % (i, v, src))
        else:
            L.append('&cfg_va%d=""' % i)
            L.append('&cfg_ve%d=""' % i)
    L.append("; 다른 뱅크(0x12000000 쪽) 지점: cfg_banks=AB 면 일치해야 성공, A 면 로그에 남기기만 한다")
    for i in range(1, MAX_BPOINTS + 1):
        if i <= len(bpts):
            a, v, src = bpts[i - 1]
            L.append('&cfg_vb%d="0x%08X"' % (i, a))
            L.append('&cfg_vbe%d="0x%08X"   ; %s (bank B)' % (i, v, src))
        else:
            L.append('&cfg_vb%d=""' % i)
            L.append('&cfg_vbe%d=""' % i)
    L.append("ENDDO")
    wtext(cfg_path(name), "\n".join(L) + "\n")
    return pts


# ============================================================== 템플릿
def tpl_flash(name, d):
    # 화면 창은 기존 S32_Config loadimage.cmm(PD 버튼)과 같은 모양으로 둔다:
    # Image / Hsm / Image&Hsm 선택 + 파일 경로 칸 3개(버튼으로 바꿀 수 있음) + file load start.
    # 기존 창의 Erase(전체 소거)는 넣지 않는다 — SFlash 복구 불가 (troubleshooting.md).
    # 창에서 쓰이는 요소는 loadimage.cmm 에서 동작이 확인된 것만 쓴다.
    return """; {n}_flash.csf - PD: 기록 (+ 화면에서는 이어서 검증)
; CLI : do {n}_flash.csf <IMAGE|HSM|ALL> <YES|NO> CLI <A|AB>   (YES = 데이터 영역까지 소거, AB = 뱅크 B 에도 APP)
; 화면: PD 버튼 (인자 없음) -> Image / Hsm / Image&Hsm 선택, 파일 확인, file load start -> 소거 질문 -> 뱅크 질문
LOCAL &m &cvd_erase &src &cvd_banks &e &b &p &filename1 &filename2 &filename3 &miss &ver
ENTRY &m &cvd_erase &src &cvd_banks
GLOBAL &gui_fbl &gui_app &gui_hsm
do {d}\\{n}_config.csf
; 버전 표시: config 의 APP 버전 (버전 폴더가 아니면 -)
&ver="&cfg_version"
IF "&ver"==""
(
	&ver="-"
)
IF "&m"==""
(
	print "PD: config APP version &ver - &cfg_app"
	DIALOG
	(
	HEADER "{n} Program DownLoad"
	POS 1. 0. 70. 3.
	BOX "Load"
	(
		POS 2. 1. 12. 1.
		LN.one:  CHOOSEBOX "Image"
		(
			dialog.enable ADD1
			dialog.enable BT1
			dialog.enable ADD2
			dialog.enable BT2
			dialog.disable ADD3
			dialog.disable BT3
		)
		POS 16. 1. 12. 1.
		LN.two:  CHOOSEBOX "Hsm"
		(
			dialog.disable ADD1
			dialog.disable BT1
			dialog.disable ADD2
			dialog.disable BT2
			dialog.enable ADD3
			dialog.enable BT3
		)
		POS 30. 1. 12. 1.
		LN.three:  CHOOSEBOX "Image&Hsm"
		(
			dialog.enable ADD1
			dialog.enable BT1
			dialog.enable ADD2
			dialog.enable BT2
			dialog.enable ADD3
			dialog.enable BT3
		)
	)

	; DIALOG 정의 안(HEADER 등)에서는 &매크로가 풀리지 않는다 (CVD 확인). 버전은 잠긴 칸(ADD0)에 dialog.set 으로 넣는다. 칸 이름 VER 는 값이 안 들어갔다(CVD 확인).
	POS 1. 3. 68. 1.
	ADD0:  EDIT "" ""

	POS 1. 5. 56. 1.
	ADD1:  EDIT "" ""
	POS 58. 5. 11. 1.
	BT1: DEFBUTTON "boot_image"
	(
		&p=dialog.string(ADD1)
		if os.file("&p")
		(
			&p=os.file.path("&p")
			cd &p
		)
		dialog.file *
		entry &filename1
		if "&filename1"!=""
		(
			dialog.set ADD1 "&filename1"
		)
	)

	POS 1. 7. 56. 1.
	ADD2:  EDIT "" ""
	POS 58. 7. 11. 1.
	BT2: DEFBUTTON "app_image"
	(
		&p=dialog.string(ADD2)
		if os.file("&p")
		(
			&p=os.file.path("&p")
			cd &p
		)
		dialog.file *
		entry &filename2
		if "&filename2"!=""
		(
			dialog.set ADD2 "&filename2"
		)
	)

	POS 1. 9. 56. 1.
	ADD3:  EDIT "" ""
	POS 58. 9. 11. 1.
	BT3: DEFBUTTON "HSM"
	(
		&p=dialog.string(ADD3)
		if os.file("&p")
		(
			&p=os.file.path("&p")
			cd &p
		)
		dialog.file *
		entry &filename3
		if "&filename3"!=""
		(
			dialog.set ADD3 "&filename3"
		)
	)

	POS 1. 11. 68. 1.
	DEFBUTTON "file load start"
	(
		&gui_fbl=dialog.string(ADD1)
		&gui_app=dialog.string(ADD2)
		&gui_hsm=dialog.string(ADD3)
		&m="IMAGE"
		if dialog.boolean(LN.two)
		(
			&m="HSM"
		)
		else if dialog.boolean(LN.three)
		(
			&m="ALL"
		)
		DIALOG.END
		DIALOG.YESNO "Erase data flash too? (DTC / NvM / learned values)"
		ENTRY &e
		&cvd_erase="NO"
		IF &e
		(
			&cvd_erase="YES"
		)
		; 듀얼뱅크: APP 를 뱅크 B 에도 쓸지 매번 묻는다 (config 값은 창 첫 줄에 보인다)
		&cvd_banks="A"
		IF "&m"!="HSM"
		(
			DIALOG.YESNO "Write the APP to bank B too? Yes = bank A + B (same APP) / No = bank A only (vendor default, bank B keeps its old APP)"
			ENTRY &b
			IF &b
			(
				&cvd_banks="AB"
			)
		)
		do {d}\\{n}_flash.csf &m &cvd_erase GUI &cvd_banks
		ENDDO
	)
	)

	dialog.set LN.one
	dialog.disable ADD3
	dialog.disable BT3
	dialog.set ADD0 "APP version &ver (config) / APP banks &cfg_banks (config: A = bank A only, AB = A+B)"
	dialog.disable ADD0
	dialog.set ADD1 "&cfg_fbl"
	dialog.set ADD2 "&cfg_app"
	dialog.set ADD3 "&cfg_hsm"
	STOP
	DIALOG.END
	ENDDO
)
IF "&cvd_erase"==""
(
	&cvd_erase="&cfg_erase"
)
IF "&cvd_banks"==""
(
	&cvd_banks="&cfg_banks"
)
IF "&cvd_banks"!="AB"
(
	&cvd_banks="A"
)
; 원본 .csf 가 이 LOCAL 변수들을 읽는다. 화면(GUI)에서는 창에서 확인한 파일을 쓴다.
&filename1="&cfg_fbl"
&filename2="&cfg_app"
&filename3="&cfg_hsm"
IF "&src"=="GUI"
(
	&filename1="&gui_fbl"
	&filename2="&gui_app"
	&filename3="&gui_hsm"
)
IF "&filename2"!="&cfg_app"
(
	&ver="(selected file)"
)
; 벤더 스크립트는 소거 -> FBL 기록 -> APP 읽기 순서라, 파일이 없으면 보드를 지운 채 멈춘다.
; 부르기 전에 이번 모드에 필요한 파일이 모두 있는지 먼저 본다.
&miss=""
IF ("&m"=="IMAGE")||("&m"=="ALL")
(
	IF !OS.FILE("&filename1")
	(
		&miss="&miss FBL=&filename1"
	)
	IF !OS.FILE("&filename2")
	(
		&miss="&miss APP=&filename2"
	)
)
IF ("&m"=="HSM")||("&m"=="ALL")
(
	IF !OS.FILE("&filename3")
	(
		&miss="&miss HSM=&filename3"
	)
)
IF "&miss"!=""
(
	print "PD: file not found - nothing written (board untouched):&miss"
	IF "&src"=="GUI"
	(
		DIALOG.OK "File not found - nothing written (board untouched).&miss"
	)
	ENDDO
)
print "PD: mode=&m erase_data=&cvd_erase app_banks=&cvd_banks APP version &ver"
IF ("&m"=="IMAGE")||("&m"=="ALL")
(
	print "PD: HOST (FBL+APP, APP banks &cvd_banks) &filename1 / &filename2"
	do {d}\\{n}_flash_host.csf
)
IF ("&m"=="HSM")||("&m"=="ALL")
(
	print "PD: HSM &filename3"
	do {d}\\{n}_flash_hsm.csf
)
print "PD: done (&m, APP banks &cvd_banks) APP version &ver"
; 화면에서 눌렀으면 이어서 검증하고 결과를 창으로 알린다 (CLI 는 run.csf 가 따로 검증).
; 검증 지점은 config 의 FBL/APP 기준이라, 창에서 다른 파일을 골랐으면 검증하지 않는다.
IF "&src"=="GUI"
(
	IF ("&filename1"=="&cfg_fbl")&&("&filename2"=="&cfg_app")
	(
		do {d}\\{n}_verify.csf FL
	)
	ELSE
	(
		print "PD: verify skipped - FBL/APP differ from {n}_config.csf"
		DIALOG.OK "Written (APP &ver). Verify skipped - selected FBL/APP differ from the project config (check points are for the config files)"
	)
)
ENDDO
""".format(n=name, d=d)


def tpl_verify(name, d):
    L = ["; %s_verify.csf - VF: 연결 후 검증 지점을 읽어 로그에 남긴다" % name,
         "; 인자: CLI = 결과 창 없음 / FL = FL 버튼이 부름 / 없음 = VF 버튼",
         "LOCAL &v &ctx &bad &first &bdiff",
         "ENTRY &ctx",
         '&bad="NO"',
         '&bdiff="NO"',
         '&first=""',
         "do %s\\%s_config.csf" % (d, name),
         "do %s\\%s_connect.csf" % (d, name),
         'IF !OS.FILE("&cfg_log")',
         "(",
         "\tOPEN #1 &cfg_log /CREATE",
         "\tCLOSE #1",
         ")",
         "OPEN #1 &cfg_log /APPEND",
         'WRITE #1 "VERIFY=begin"']
    for i in range(1, MAX_POINTS + 1):
        L += ['IF "&cfg_va%d"!=""' % i,
              "(",
              "\t&v=Data.Long(AD:&cfg_va%d)" % i,
              '\tWRITE #1 "RD &cfg_va%d &v &cfg_ve%d"' % (i, i),
              '\tprint "VF: &cfg_va%d read=&v expect=&cfg_ve%d"' % (i, i),
              "\tIF &v!=&cfg_ve%d" % i,
              "\t(",
              '\t\t&bad="YES"',
              '\t\tIF "&first"==""',
              "\t\t(",
              '\t\t\t&first="&cfg_va%d"' % i,
              "\t\t)",
              "\t)",
              ")"]
    # 다른 뱅크(0x12000000 쪽): AB 면 판정에 넣고, A 면 다르다는 것만 알린다
    for i in range(1, MAX_BPOINTS + 1):
        L += ['IF "&cfg_vb%d"!=""' % i,
              "(",
              "\t&v=Data.Long(AD:&cfg_vb%d)" % i,
              '\tWRITE #1 "RB &cfg_vb%d &v &cfg_vbe%d"' % (i, i),
              '\tprint "VF: bank B &cfg_vb%d read=&v expect=&cfg_vbe%d"' % (i, i),
              "\tIF &v!=&cfg_vbe%d" % i,
              "\t(",
              '\t\t&bdiff="YES"',
              '\t\tIF ("&cfg_banks"=="AB")&&("&first"=="")',
              "\t\t(",
              '\t\t\t&first="&cfg_vb%d (bank B)"' % i,
              "\t\t)",
              '\t\tIF "&cfg_banks"=="AB"',
              "\t\t(",
              '\t\t\t&bad="YES"',
              "\t\t)",
              "\t)",
              ")"]
    L += ['WRITE #1 "VERIFY=end"', "CLOSE #1",
          'IF ("&bdiff"=="YES")&&("&cfg_banks"!="AB")',
          "(",
          '\tprint "VF: note - bank B holds a different APP (APP banks A: bank B was not written)"',
          ")",
          'IF "&bad"=="YES"',
          "(",
          '\tprint "VF: FAILED - first mismatch at &first (log: &cfg_log)"',
          '\tIF "&ctx"!="CLI"',
          "\t(",
          '\t\tDIALOG.OK "Verify FAILED (APP &cfg_version) - flash does not match the image (first mismatch &first). See &cfg_log"',
          "\t)",
          ")",
          "ELSE",
          "(",
          '\tprint "VF: OK - all check points match"',
          '\tIF "&bdiff"=="YES"',
          "\t(",
          '\t\tIF "&ctx"=="FL"',
          "\t\t(",
          '\t\t\tDIALOG.OK "Flash + Verify OK (APP &cfg_version, bank A) - NOTE: bank B holds a different APP. If the FBL boots bank B, another version runs. Write with APP banks A+B to align both."',
          "\t\t)",
          '\t\tIF "&ctx"==""',
          "\t\t(",
          '\t\t\tDIALOG.OK "Verify OK (APP &cfg_version, bank A) - NOTE: bank B holds a different APP."',
          "\t\t)",
          "\t)",
          "\tELSE",
          "\t(",
          '\t\tIF "&ctx"=="FL"',
          "\t\t(",
          '\t\t\tDIALOG.OK "Flash + Verify OK (APP &cfg_version) - all check points match the image files"',
          "\t\t)",
          '\t\tIF "&ctx"==""',
          "\t\t(",
          '\t\t\tDIALOG.OK "Verify OK (APP &cfg_version) - all check points match the image files"',
          "\t\t)",
          "\t)",
          ")",
          "ENDDO"]
    return "\n".join(L) + "\n"


def _step(name):
    return ["OPEN #1 &cfg_log /APPEND", 'WRITE #1 "STEP=%s"' % name, "CLOSE #1"]


def tpl_entry(name, d, with_flash):
    """단계마다 로그를 남긴다. 도구는 이것으로 어디까지 갔는지, 끊어도 되는지 판단한다.
    start -> connected (쓰기 전, 연결만 확인) -> flashing (쓰는 중, 끊지 않음) -> flashed -> done"""
    L = ["; %s_%s.csf - CLI 진입 (CVD.exe 인자로 실행, 끝나면 QUIT)" % (name, "run" if with_flash else "check"),
         "do %s\\%s_config.csf" % (d, name),
         "OPEN #1 &cfg_log /CREATE",
         'WRITE #1 "STEP=start"',
         'WRITE #1 "PROJECT=&cfg_name"',
         'WRITE #1 "MODE=&cfg_mode"',
         'WRITE #1 "ERASE=&cfg_erase"',
         'WRITE #1 "BANKS=&cfg_banks"',
         "CLOSE #1",
         "; 쓰기 전에 타깃이 붙는지 먼저 본다 (여기서 멈추면 아무것도 쓰지 않은 상태)",
         "do %s\\%s_connect.csf" % (d, name)]
    L += _step("connected")
    if with_flash:
        L += ["sys.down"]
        L += _step("flashing")
        L += ["do %s\\%s_flash.csf &cfg_mode &cfg_erase CLI &cfg_banks" % (d, name)]
        L += _step("flashed")
    L += ["do %s\\%s_verify.csf CLI" % (d, name)]
    L += _step("done")
    L += ["QUIT"]
    return "\n".join(L) + "\n"


def tpl_start():
    return """; cvd_start.csf - CVD 시작 스크립트 (고정). Run Script File 로 한 번 실행
; 툴바에 ED(과제 목록 편집) / PS(과제 선택) 등록
MENU.ReProgram
(
	ADD
	TOOLBAR
	(
		TOOLITEM  "Project Sel Edit"  "ED,B"  "Pedit {p}\\loadfile.csf"
		TOOLITEM  "Project Select"    "PS,R"  "CD.DO {p}\\loadfile.csf"
		SEPARATOR
	)
)
print "cvd_start: press PS to select a project"
ENDDO
""".format(p=WIN_PROJECTS)


def tpl_loadfile(projects):
    cols = 3
    rows = max(1, (len(projects) + cols - 1) // cols)
    L = ["; loadfile.csf - 과제 선택 (cvd_flash.py 가 Projects 폴더를 보고 다시 만든다. 직접 고치지 말 것)",
         "DIALOG", "(", 'HEADER "Project Select"',
         "POS 1. 0. 62. %d." % (rows + 2), 'BOX "Project"', "("]
    for i, (n, cpu) in enumerate(projects):
        d = proj_win(n)
        x, y = 2 + (i % cols) * 20, 1 + i // cols
        L += ["\tPOS %d. %d. 18. 1." % (x, y),
              '\tLN.one:  CHOOSEBOX "%s"' % n,
              "\t(",
              "\t\tDIALOG.END",
              "\t\tB::sys.CPU %s" % cpu,
              "\t\tMENU.ReProgram",
              "\t\t(",
              "\t\t\tADD",
              "\t\t\tTOOLBAR",
              "\t\t\t(",
              # 기존 S32 과제 툴바(PD / Ed | PA / Ed | RE)와 같은 배치
              '\t\t\t\tTOOLITEM  "%s Program DownLoad"  "PD,R"  "CD.DO %s\\%s_flash.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Program Edit (config: image paths)"  "Ed,B"  "Pedit %s\\%s_config.csf"' % (n, d, n),
              "\t\t\t\tSEPARATOR",
              '\t\t\t\tTOOLITEM  "%s Path Set (connect + symbol + source)"  "PA,R"  "CD.DO %s\\%s_connect.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Verify"  "VF,G"  "CD.DO %s\\%s_verify.csf"' % (n, d, n),
              "\t\t\t\tSEPARATOR",
              '\t\t\t\tTOOLITEM  "%s Reset (go main)"  "RE,R"  "CD.DO %s\\%s_reset.csf"' % (n, d, n),
              "\t\t\t\tSEPARATOR",
              "\t\t\t)",
              "\t\t)",
              "\t)"]
    L += [")", ")", "STOP", "ENDDO"]
    return "\n".join(L) + "\n"


# ============================================================== 원본 변환
def convert_flash_csf(src_file, src_folder_win, dst_win):
    t = rb(src_file).decode(ENC, "replace").replace("\r\n", "\n")
    notes = []
    t, n = re.subn(re.escape(src_folder_win), lambda m: dst_win, t, flags=re.I)
    notes.append("경로 치환 %d곳" % n)

    def loader(m):
        return '&FLASH_LOADER="%s\\%s"' % (dst_win, m.group(1).replace("/", "\\").split("\\")[-1])
    t, n = re.subn(r'&FLASH_LOADER="([^"]+)"', loader, t)
    notes.append("로더 경로 %d곳" % n)
    # 소거 확인 창 대신 FL 에서 받은 선택(&cvd_erase)을 따른다.
    # YES = 원본의 Yes (워크+코드 플래시 명시 소거) / NO = 원본의 No
    pat = re.compile(r'DIALOG\.YESNO "Erase flash memory\?"[^\n]*\n([ \t]*)LOCAL &progflash[^\n]*\n[ \t]*ENTRY &progflash', re.I)

    def repl(m):
        i = m.group(1)
        return ("; [cvd_flash] 소거 확인 창 대신 FL 의 선택(&cvd_erase)을 따른다\n"
                "{i}LOCAL &progflash\n{i}&progflash=FALSE()\n{i}IF \"&cvd_erase\"==\"YES\"\n"
                "{i}(\n{i}\t&progflash=TRUE()\n{i})").format(i=i)
    t, n = pat.subn(repl, t)
    if n != 1:
        die("%s: 소거 확인 창 패턴을 찾지 못했습니다(%d). 원본 구조가 다릅니다." % (os.path.basename(src_file), n))
    notes.append("소거 확인 창 -> FL 선택값")
    t, n = re.subn(r"(OPTION\.JTAGCLOCK)\s+5\.MHz", r"\1 10.MHz   ; [cvd_flash] 5.MHz -> 10.MHz (HE1i 실기 검증본 값)", t)
    if n:
        notes.append("JTAGCLOCK 5.MHz -> 10.MHz")
    # 원본은 뱅크 B 에 FBL 만 쓰고 APP(RTSW) 기록은 주석으로 막아 두었다. 그대로면 B 에 옛 APP 가 남아
    # FBL 이 B 로 부팅하면 다른 버전이 돈다 (HE1i 2026-10-02 실기: A=26810, B=26820 → OTA 실패).
    # 주석을 PD 선택(&cvd_banks)으로 바꾼다: A = 원본대로 A 만 / AB = B 에도 같은 APP.
    pat = re.compile(r'([ \t]*);cflash\.reprogram all[ \t]*\n[ \t]*; RTSW none at Bank B[^\n]*\n'
                     r'[ \t]*;Data\.LOAD\.auto "&filename2"[^\n]*\n[ \t]*;cflash\.reprogram off', re.I)

    def repl_b(m):
        i = m.group(1)
        return ("{i}; [cvd_flash] APP(RTSW) 를 뱅크 B 에도 쓸지: &cvd_banks (A = 원본대로 B 에는 FBL 만 / AB = B 에도 APP)\n"
                "{i}IF \"&cvd_banks\"==\"AB\"\n{i}(\n"
                "{i}\tprint \"PD: APP -> bank B (map B)\"\n"
                "{i}\tcflash.reprogram all\n{i}\tData.LOAD.auto \"&filename2\"\n{i}\tcflash.reprogram off\n{i})").format(i=i)
    t, n = pat.subn(repl_b, t)
    if n == 1:
        notes.append("뱅크 B APP 기록 -> PD 선택값(&cvd_banks)")
    elif "&filename2" in t:
        die("%s: 뱅크 B APP 기록 패턴을 찾지 못했습니다(%d). 원본 구조가 다릅니다." % (os.path.basename(src_file), n))
    return t, notes


def convert_connect(src_file, src_folder_win, dst_win, name):
    t = rb(src_file).decode(ENC, "replace").replace("\r\n", "\n")
    t = re.sub(re.escape(src_folder_win), lambda m: dst_win, t, flags=re.I)
    t, n1 = re.subn(r'Data\.LOAD\.auto\s+"[^"]*"\s*/\s*nocode', 'Data.LOAD.auto "&cfg_elf" / nocode', t, flags=re.I)
    lines, out, inserted = t.split("\n"), [], False
    for line in lines:
        s = line.strip()
        if re.match(r"sYmbol\.SourcePATH\.SetRecurseDir", s, re.I):
            out.append(line.replace(s, ";" + s))          # 기존 경로는 주석으로
            continue
        out.append(line)
        if re.match(r"sYmbol\.SourcePATH\.Reset", s, re.I) and not inserted:
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + 'sYmbol.SourcePATH.SetRecurseDir "&cfg_src"   ; [cvd_flash]')
            inserted = True
    if n1 != 1 or not inserted:
        die("connect.csf 구조가 예상과 다릅니다 (심볼 로드 %d곳, 소스 경로 삽입 %s)." % (n1, inserted))
    head = "; %s_connect.csf - CN: 연결 + 워치독 해제 + 심볼 + 소스 경로 (기본 틀 connect.csf)\ndo %s\\%s_config.csf\n" % (name, dst_win, name)
    return head + "\n".join(out)


# ============================================================== 명령: scan / init
BANK_KO = {"dual": "듀얼뱅크", "single": "싱글뱅크"}


def print_scan(d):
    print("[프로젝트 폴더] %s" % d["repo"])
    if d.get("versions"):
        print("  %-10s 버전 폴더 %d개 — APP(_Writing.s19)·ELF 는 고른 버전 폴더에서 한 쌍으로 쓴다"
              % ("APP 버전", len(d["versions"])))
        print_versions(d["versions"], d.get("version"), d.get("src_ver"), "             ")
        if d.get("src_ver"):
            print("  %-10s   현재 소스(PJ_Define.h %s) = %s%s" % ("", d["src_variant"], d["src_ver"],
                  "" if d["src_ver"] in d["versions"] else "  (이 버전 폴더는 아직 없음)"))
        if not d.get("version"):
            print("  %-10s   → 여러 개라 고르지 않았음. init/flash 에 --version <버전>" % "")
    for k, lab in (("fbl", "FBL"), ("app", "APP(기록)"), ("elf", "ELF(심볼)"), ("hsm", "HSM")):
        print("  %-10s %s" % (lab, d[k] or ("버전 선택 필요" if d.get("versions") and k in ("app", "elf") else "없음")))
        if k == "fbl" and d.get("fbl_why") and d[k]:
            print("  %-10s   → %s 에서 고름" % ("", d["fbl_why"]))
        others = [p for p in d["cands"].get(k, []) if p != d[k]]
        if others:
            why = "위 폴더를 우선함" if k == "fbl" and d.get("fbl_why") else "가장 최근 파일을 골랐음"
            print("  %-10s   (다른 후보 %d개 — %s. 차종·사양이 맞는지 확인)" % ("", len(others), why))
            for p in others[:5]:
                print("  %-10s     - %s" % ("", p))
    print("  %-10s %s" % ("MCU", d["mcu"] or "인식 못함"))
    if d["bank"]:
        print("  %-10s %s  (근거: %s)" % ("뱅크", BANK_KO[d["bank"]], ", ".join(d["bank_why"])))
    elif d["bank_why"]:
        print("  %-10s 판단 불가 — 두 종류가 모두 있음 (%s)" % ("뱅크", "; ".join(d["bank_why"])))
    else:
        print("  %-10s 판단 불가 — 저장소에 DUAL_BANK/SINGLE_BANK 폴더 없음" % "뱅크")
    print("  %-10s %s" % ("과제명 제안", d["name"]))
    print("[라이팅 기본 틀] %s  (%s %s)" % (TEMPLATE_DIR, TEMPLATE_MCU, BANK_KO[TEMPLATE_BANK]))


def cmd_scan(a):
    d = discover(a.repo or os.getcwd())
    print_scan(d)
    if check_cvd(strict=False):
        print("[CVD] %s  (과제 폴더: %s)" % (CVD_EXE, FS_PROJECTS))


def cmd_init(a):
    # 1) 프로젝트 폴더: 기본값 = 현재 폴더
    check_cvd(strict=True)                       # 설치가 확인돼야 과제를 만든다
    repo = a.repo or ask("[1/4] 프로젝트 폴더 (빌드 저장소)  Enter=기본값", os.getcwd())
    d = discover(repo)
    tcpu = template_check()
    print_scan(d)
    if not (a.app or a.elf):
        choose_version(d, a.version, None, "init")
        apply_paired_fbl(d, d["versions"], a.fbl)
        if d.get("_fbl_why"):
            print("  → FBL %s" % d["_fbl_why"])
    for k in ("fbl", "app", "elf", "hsm"):
        v = getattr(a, k)
        if v:
            d[k] = os.path.abspath(v)
            d["cands"][k] = [d[k]]
            if k in ("app", "elf"):
                d["version"] = ""
    if d["version"]:
        print("  → APP 버전 %s (%s)" % (d["version"], d.get("version_why", "")))
        print("    APP  %s" % d["app"])
        print("    ELF  %s" % d["elf"])
    missing = [k for k in ("fbl", "app", "elf") if not d[k]]
    if missing:
        die("찾지 못한 이미지: %s  → --%s <경로> 로 지정하세요." % (", ".join(missing), missing[0]))

    # 2) MCU — 기본 틀과 계열이 같아야 한다
    if not (d["mcu"] or "").upper().startswith(TEMPLATE_MCU) and not a.force_mcu:
        die("저장소 MCU(%s)가 기본 틀(%s)과 계열이 다릅니다. 플래시 주소가 달라질 수 있어 중단합니다."
            % (d["mcu"] or "인식 못함", TEMPLATE_MCU))

    # 3) 과제명 · 뱅크 구성 (사용자가 정한다)
    if not sys.stdin.isatty() and not (a.name and a.bank):
        die("대화형이 아닌 실행에서는 --name 과 --bank 를 지정해야 합니다 (위 인식 결과 참고).")
    name = (a.name or ask("[2/4] 과제명 (영문 대문자·숫자·_)", d["name"]) or "").upper()
    if not NAME_RE.match(name):
        die("과제명 형식이 맞지 않습니다: %s" % name)
    if os.path.exists(proj_fs(name)):
        die("이미 있는 과제입니다: %s (덮어쓰지 않음)" % proj_fs(name))
    bank = (a.bank or ask("[3/4] 뱅크 구성 (dual/single)", d["bank"]) or "").lower()
    if bank not in BANK_KO:
        die("뱅크 구성은 dual 또는 single 로 지정하세요: %s" % bank)
    if d["bank"] and d["bank"] != bank and not a.force_bank:
        die("지정한 뱅크(%s)가 저장소 조사 결과(%s, 근거: %s)와 다릅니다. 확인 후 다시 실행하세요."
            % (BANK_KO[bank], BANK_KO[d["bank"]], ", ".join(d["bank_why"])))
    if bank != TEMPLATE_BANK:
        die("%s 라이팅 기본 틀이 없습니다. 지금 기본 틀은 %s %s 전용입니다."
            % (BANK_KO[bank], TEMPLATE_MCU, BANK_KO[TEMPLATE_BANK]))

    # 4) 확인
    dst_fs, dst_win = proj_fs(name), proj_win(name)
    print("[4/4] 생성 예정")
    print("  폴더   %s" % dst_fs)
    print("  파일   %s_{config,connect,flash,flash_host,flash_hsm,verify,reset,run,check}.csf + 로더" % name)
    print("  기본틀 %s (CPU %s, %s)" % (TEMPLATE_DIR, tcpu, BANK_KO[bank]))
    print("  CVD    %s" % CVD_EXE)
    print("  등록   %s (백업 후 다시 생성)" % os.path.join(FS_PROJECTS, "loadfile.csf"))
    print("  시작   %s  (CVD 를 켜면 cvd_start.csf 먼저 실행)" % shortcut_path())
    if not a.yes:
        if not sys.stdin.isatty():
            die("확인이 필요합니다. 내용을 확인했으면 --yes 로 다시 실행하세요.")
        if (ask("진행할까요? (y/N)", "N") or "N").lower() != "y":
            die("취소했습니다.", EXIT_OK)
    if a.dry_run:
        print("[dry-run] 파일을 만들지 않았습니다.")
        return

    os.makedirs(dst_fs)
    notes = []
    for f in glob.glob(os.path.join(TEMPLATE_DIR, "*.out")):
        shutil.copy2(f, dst_fs)
    t, n = convert_flash_csf(os.path.join(TEMPLATE_DIR, TEMPLATE_HOST), TEMPLATE_ORIGIN_WIN, dst_win)
    wtext(os.path.join(dst_fs, "%s_flash_host.csf" % name), t); notes += ["host: " + x for x in n]
    t, n = convert_flash_csf(os.path.join(TEMPLATE_DIR, TEMPLATE_HSM), TEMPLATE_ORIGIN_WIN, dst_win)
    wtext(os.path.join(dst_fs, "%s_flash_hsm.csf" % name), t); notes += ["hsm: " + x for x in n]
    wtext(os.path.join(dst_fs, "%s_connect.csf" % name),
          convert_connect(os.path.join(TEMPLATE_DIR, TEMPLATE_CONNECT), TEMPLATE_ORIGIN_WIN, dst_win, name))
    reset = rb(os.path.join(TEMPLATE_DIR, TEMPLATE_RESET)).decode(ENC, "replace")
    wtext(os.path.join(dst_fs, "%s_reset.csf" % name), "; %s_reset.csf - RE: 리셋 후 main 까지 (기본 틀 reset.csf)\n" % name + reset)
    wtext(os.path.join(dst_fs, "%s_flash.csf" % name), tpl_flash(name, dst_win))
    wtext(os.path.join(dst_fs, "%s_verify.csf" % name), tpl_verify(name, dst_win))
    wtext(os.path.join(dst_fs, "%s_run.csf" % name), tpl_entry(name, dst_win, True))
    wtext(os.path.join(dst_fs, "%s_check.csf" % name), tpl_entry(name, dst_win, False))
    cfg = {"name": name, "dir": dst_win, "cpu": tcpu, "bank": bank, "mode": "IMAGE", "erase": "YES", "banks": "A",
           "repo": d["repo"], "version": d["version"],
           "fbl": d["fbl"], "app": d["app"], "elf": d["elf"], "hsm": d["hsm"] or "",
           "src": d["repo"], "log": wpath(dst_win, "%s_result.log" % name),
           "template": "cyt2bl_dual (cvd_flash %s)" % VERSION}
    pts = write_cfg(cfg)
    bak = rebuild_loadfile()
    if not os.path.isfile(os.path.join(FS_PROJECTS, "cvd_start.csf")):
        wtext(os.path.join(FS_PROJECTS, "cvd_start.csf"), tpl_start())
    lnk = make_shortcut()
    print("[완료] %s" % dst_fs)
    for x in notes:
        print("  - " + x)
    print("  - 검증 지점 %d개" % len(pts))
    print("  - APP 버전 %s" % (cfg["version"] or "(버전 폴더 아님)"))
    if bak:
        print("  - loadfile.csf 백업: %s" % bak)
    print_shortcut(lnk)
    print("다음: python cvd_flash.py flash --name %s" % name)


# ============================================================== 시작 바로가기
# CVD 는 스크립트로 붙인 툴바 버튼을 저장하지 않는다. 켤 때 버튼을 붙이려면
# 실행 인수로 스크립트를 넘겨야 한다 (기존 S32 바로가기는 S32_Config\autostart.cmm 을 넘긴다).
# 우리 바로가기를 따로 만들고, 다른 바로가기는 건드리지 않는다.
SHORTCUT_NAME = "CVD Projects.lnk"


def shortcut_path():
    return os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs", SHORTCUT_NAME)


def _ps(script):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def make_shortcut():
    """시작 메뉴에 'CVD Projects' 바로가기를 만든다(있으면 다시 쓴다). 실패해도 과제 생성은 유지."""
    start = wpath(WIN_PROJECTS, "cvd_start.csf")
    lnk = shortcut_path()
    q = lambda s: s.replace("'", "''")
    code, _, err = _ps(
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='\"%s\"';$s.WorkingDirectory='%s';"
        "$s.Description='CVD + cvd_start.csf (Projects toolbar)';$s.Save()"
        % (q(lnk), q(CVD_EXE), q(start), q(os.path.dirname(CVD_EXE))))
    if code != 0 or not os.path.isfile(lnk):
        print("[경고] 시작 바로가기를 만들지 못했습니다: %s" % (err.strip() or lnk))
        return None
    return lnk


def other_start_shortcuts():
    """CVD.exe 를 가리키는 다른 시작 메뉴·바탕화면 바로가기 (안내용, 수정하지 않음)."""
    code, out, _ = _ps(
        "$sh=New-Object -ComObject WScript.Shell;"
        "$d=@([Environment]::GetFolderPath('StartMenu'),[Environment]::GetFolderPath('CommonStartMenu'),"
        "[Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonDesktopDirectory'));"
        "Get-ChildItem $d -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {"
        "$l=$sh.CreateShortcut($_.FullName); if ($l.TargetPath -like '*\\CVD.exe' -and $_.Name -ne '%s') {"
        "$_.FullName + '|' + $l.Arguments } }" % SHORTCUT_NAME)
    return [x.split("|", 1) for x in out.splitlines() if "|" in x] if code == 0 else []


def print_shortcut(lnk):
    if not lnk:
        return
    print("  - 시작 바로가기: %s" % lnk)
    print("    시작 메뉴 'CVD Projects' 로 켜면 ED/PS 버튼이 붙은 상태로 시작합니다.")
    for p, args in other_start_shortcuts():
        if args.strip():
            print("    (기존 바로가기 %s 는 %s 를 실행 — 그대로 둠)" % (p, args.strip()))


def cmd_refresh(a):
    """스킬 갱신 후 기존 과제의 생성 스크립트(PD 창·툴바 등)와 기본 틀 변환본(flash_host/hsm)을
    새 템플릿으로 다시 만든다. config 는 값(경로·버전·설정)을 그대로 두고 새 항목만 채워 다시 쓴다
    (검증 지점 재계산). connect·reset 은 건드리지 않는다."""
    check_cvd(strict=True)
    template_check()
    c = read_cfg(a.name)                          # 과제가 있는지 확인
    d = proj_win(a.name)
    files = {"flash": tpl_flash(a.name, d), "verify": tpl_verify(a.name, d),
             "run": tpl_entry(a.name, d, True), "check": tpl_entry(a.name, d, False)}
    notes = []
    for k, f in (("flash_host", TEMPLATE_HOST), ("flash_hsm", TEMPLATE_HSM)):
        t, n = convert_flash_csf(os.path.join(TEMPLATE_DIR, f), TEMPLATE_ORIGIN_WIN, d)
        files[k] = t
        notes += ["%s: %s" % (k, x) for x in n]
    if c["banks"] not in BANKS:
        c["banks"] = "A"                          # 옛 config: 벤더 원본 동작
    print("[refresh] %s" % proj_fs(a.name))
    for k in files:
        print("  다시 생성  %s_%s.csf" % (a.name, k))
    print("  다시 생성  %s (백업 후)" % os.path.join(FS_PROJECTS, "loadfile.csf"))
    print("  다시 쓰기  %s_config.csf (값 유지, APP 뱅크 %s, 검증 지점 재계산)" % (a.name, c["banks"]))
    print("  유지       %s_connect.csf, reset" % a.name)
    if a.dry_run:
        print("[dry-run] 파일을 만들지 않았습니다.")
        return
    for k, t in files.items():
        wtext(os.path.join(proj_fs(a.name), "%s_%s.csf" % (a.name, k)), t)
    write_cfg(c)
    for x in notes:
        print("  - " + x)
    bak = rebuild_loadfile()
    if not os.path.isfile(os.path.join(FS_PROJECTS, "cvd_start.csf")):
        wtext(os.path.join(FS_PROJECTS, "cvd_start.csf"), tpl_start())
    print("[완료]" + ("  loadfile.csf 백업: %s" % bak if bak else ""))
    print("CVD 에서 PS 로 과제를 다시 고르면 새 툴바가 붙습니다 (이미 붙은 버튼은 CVD 를 다시 켜야 정리됨).")


def cmd_startup(a):
    check_cvd(strict=True)
    if not os.path.isfile(os.path.join(FS_PROJECTS, "cvd_start.csf")):
        die("cvd_start.csf 가 없습니다. 먼저 init 으로 과제를 만드세요.")
    print_shortcut(make_shortcut())


def list_projects():
    out = []
    if not os.path.isdir(FS_PROJECTS):
        return out
    for n in sorted(os.listdir(FS_PROJECTS)):
        if os.path.isfile(cfg_path(n)):
            out.append((n, read_cfg(n)["cpu"]))
    return out


def rebuild_loadfile():
    os.makedirs(FS_PROJECTS, exist_ok=True)
    p = os.path.join(FS_PROJECTS, "loadfile.csf")
    bak = None
    if os.path.isfile(p):
        bak = p + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
        shutil.copyfile(p, bak)
    wtext(p, tpl_loadfile(list_projects()))
    return bak


# ============================================================== 명령: flash / verify
def prepare_cfg(a):
    """저장된 설정 + 이번 인자. 파일에 쓰지는 않는다 (flash 는 --yes, set 은 dry-run 이 아닐 때 쓴다).
    버전 폴더 저장소: APP·ELF 는 항상 고른 버전 폴더에서 다시 가져온다 (--version, 없으면 config 의 버전)."""
    c = read_cfg(a.name)
    old_app, old_stamp, c["_cfg_version"] = c["app"], c["app_stamp"], c["version"]
    want = getattr(a, "version", None)
    d = {"repo": c["repo"], "versions": find_versions(c["repo"])}
    d["src_variant"], d["src_ver"] = source_version(c["repo"])
    c["_versions"], c["_src_ver"] = d["versions"], d["src_ver"]
    if getattr(a, "rescan", False):              # FBL·HSM 재탐색 (버전 폴더가 없으면 APP·ELF 도)
        r = discover(c["repo"])
        for k in ("fbl", "hsm") if d["versions"] else ("fbl", "app", "elf", "hsm"):
            if r[k]:
                c[k] = r[k]
    direct = [k for k in ("app", "elf") if getattr(a, k, None)]
    if direct and want:
        die("--version 과 --app/--elf 는 함께 쓸 수 없습니다 (버전을 고르면 APP·ELF 는 그 폴더에서 가져옵니다).")
    if not c["version"] and c["app"]:            # 버전 값이 없는 옛 config: APP 경로의 버전 폴더로 판단
        for v, info in d["versions"].items():
            if os.path.normcase(os.path.dirname(c["app"])) == os.path.normcase(info["dir"]):
                c["version"] = c["_cfg_version"] = v
    if not direct:
        choose_version(d, want, c["version"] or None, a.cmd)
        if d["versions"]:
            c["app"], c["elf"], c["version"] = d["app"], d["elf"], d["version"]
            c["_version_why"] = d["version_why"]
        else:
            c["version"] = ""
        apply_paired_fbl(c, d["versions"], getattr(a, "fbl", None))
    else:
        c["_fbl_why"] = ""
    for k in ("fbl", "app", "elf", "hsm"):
        v = getattr(a, k, None)
        if v:
            c[k] = os.path.abspath(v)
    if direct:
        c["version"] = ""                         # 버전 폴더 밖 파일을 직접 지정
    # 같은 경로인데 파일이 바뀜 = 같은 버전을 다시 빌드함 → 검증 지점을 새로 계산해야 한다
    c["_rebuilt"] = bool(old_stamp) and os.path.normcase(c["app"]) == os.path.normcase(old_app) \
        and stamp(c["app"]) != old_stamp
    if hasattr(a, "mode"):                       # flash: 매번 지정값, 없으면 IMAGE (저장값을 이어 쓰지 않음)
        c["mode"] = a.mode or "IMAGE"
        c["erase"] = "NO" if a.keep_data else "YES"
    c["_cfg_banks"] = c["banks"] if c["banks"] in BANKS else "A"
    # APP 뱅크는 config 설정을 이어 쓴다 (flash --yes / set 때 저장). 옛 config 는 A(벤더 원본 동작)
    c["banks"] = getattr(a, "banks", None) or c["_cfg_banks"]
    need = {"IMAGE": ("fbl", "app"), "HSM": ("hsm",), "ALL": ("fbl", "app", "hsm")}.get(c["mode"], ("fbl", "app"))
    for k in need + ("elf",):
        if not c[k] or not os.path.isfile(c[k]):
            die("%s 파일이 없습니다: %s" % (k.upper(), c[k] or "(미지정)"))
    return c


def last_step(log_fs):
    if not os.path.isfile(log_fs):
        return None
    s = re.findall(r"STEP=(\w+)", rb(log_fs).decode(ENC, "replace"))
    return s[-1] if s else None


def run_cvd(entry_fs, log_fs, timeout, flash_limit):
    """CVD 를 실행하고 로그의 STEP 으로 진행을 본다.
    쓰는 중(flashing)에는 절대 끄지 않는다. 그 밖의 단계는 timeout 초 동안 진전이 없으면 끈다."""
    if os.path.isfile(log_fs):
        os.remove(log_fs)
    proc = subprocess.Popen([CVD_EXE, entry_fs], cwd=os.path.dirname(CVD_EXE))
    t0 = time.time()
    phase, t_phase, last_note, why = None, t0, t0, "timeout"
    while True:
        st = last_step(log_fs)
        now = time.time()
        if st != phase:
            phase, t_phase, last_note = st, now, now
        if st == "done":
            why = "done"
            break
        if proc.poll() is not None:
            why = "exited"
            break
        if phase == "flashing":
            if now - t_phase > flash_limit:
                why = "stuck"                   # 끄지 않고 사람에게 넘긴다
                break
            if now - last_note >= 60:
                print("  쓰는 중... %d초" % (now - t_phase), flush=True)
                last_note = now
        elif now - t_phase > timeout:
            why = "timeout"
            break
        time.sleep(1.0)
    time.sleep(1.0)
    if why != "stuck" and proc.poll() is None:
        try:
            proc.terminate()
        except OSError:
            pass
    return why, int(time.time() - t0)


def which_version(c, rows):
    """읽은 (주소, 값) 이 어느 버전 폴더 APP 와 일치하는지. 0x12… 는 0x10… 으로 옮겨 비교한다."""
    found = []
    for v, info in sorted(c.get("_versions", {}).items(), key=lambda kv: ver_key(kv[0])):
        try:
            segs = load_image(info["app"])
        except OSError:
            continue
        ok = bool(rows)
        for addr, got in rows:
            a = addr - BANK_B_OFFSET if addr >= VERIFY_RANGE[1] else addr
            w = None
            for s, d in segs:
                if s <= a and a + 4 <= s + len(d):
                    w = struct.unpack_from("<I", d, a - s)[0]
                    break
            if w != got:
                ok = False
                break
        if ok:
            found.append(v)
    return found


def _mismatch(rows):
    bad = []
    for addr, got, exp in rows:
        try:
            ok = int(got, 16) == int(exp, 16)
        except ValueError:
            ok = False
        if not ok:
            bad.append((addr, got, exp))
    return bad


def _ints(rows):
    out = []
    for addr, got, _ in rows:
        try:
            out.append((int(addr, 16), int(got, 16)))
        except ValueError:
            pass
    return out


def judge(log_fs, with_flash, why, flash_limit, c=None):
    c = c or {}
    t = rb(log_fs).decode(ENC, "replace") if os.path.isfile(log_fs) else ""
    steps = re.findall(r"STEP=(\w+)", t)
    last = steps[-1] if steps else "없음"
    rows = re.findall(r"RD\s+(0x[0-9A-Fa-f]+)\s+(\S+)\s+(0x[0-9A-Fa-f]+)", t)
    brows = re.findall(r"RB\s+(0x[0-9A-Fa-f]+)\s+(\S+)\s+(0x[0-9A-Fa-f]+)", t)
    bad = _mismatch(rows)
    bbad = _mismatch(brows)
    banks_ab = c.get("banks") == "AB"
    print("[로그] %s  (마지막 단계: %s)" % (log_fs, last))
    print("  검증 지점 %d개, 불일치 %d개" % (len(rows), len(bad)))
    for addr, got, exp in bad[:8]:
        print("    %s  읽음 %s  기대 %s" % (addr, got, exp))
    if bad and c.get("_versions"):
        vs = which_version(c, _ints([r for r in rows if r[0] in [b[0] for b in bad]]))
        if vs:
            print("  → 실행 중인 뱅크(0x10…)의 APP 는 버전 %s 와 일치합니다." % ", ".join(vs))
    if brows:
        print("  다른 뱅크(0x12…) 지점 %d개, 불일치 %d개%s" % (
            len(brows), len(bbad), "" if banks_ab else "  (APP 뱅크 A 설정 — 판정에 넣지 않음)"))
        for addr, got, exp in bbad[:4]:
            print("    %s  읽음 %s  기대 %s" % (addr, got, exp))
        # 모두 0xFFFFFFFF = 지워진 뱅크 (OTA 가 erase 뒤 전송 중에 실패했을 때 등). FBL 은 빈 뱅크로 부팅하지 않는다
        blank = all(g == 0xFFFFFFFF for _, g in _ints(brows))
        if bbad:
            vs = which_version(c, _ints(brows)) if c.get("_versions") and not blank else []
            if blank:
                print("  → 다른 뱅크는 지워져 있습니다(빈 뱅크). OTA 가 erase 뒤 실패하면 이렇게 남는다 — 실행 중인 뱅크만 돈다.")
                if not bad:
                    print("     실행 중인 뱅크는 이미지와 일치합니다. 두 뱅크를 채우려면 --banks AB 로 다시 기록하거나 OTA 를 성공시킨다.")
            else:
                print("  → 다른 뱅크의 APP 는 %s" % ("버전 %s 와 일치합니다." % ", ".join(vs) if vs
                                                 else "어느 버전 폴더와도 맞지 않습니다(다른 빌드)."))
        # 같은 지점을 두 뱅크에서 읽은 값이 다르면 두 뱅크의 APP 가 다르다 (빈 뱅크는 제외)
        main = dict(_ints(rows))
        differ = not blank and any(main.get(a - BANK_B_OFFSET, g) != g for a, g in _ints(brows))
        if differ:
            print("  [알림] 두 뱅크의 APP 가 다릅니다. FBL 이 어느 뱅크로 부팅하느냐에 따라 다른 버전이 돕니다(OTA 버전 불일치 원인).")
            if not banks_ab:
                print("         두 뱅크를 맞추려면 --banks AB 로 다시 기록하세요.")
    if bbad and banks_ab and not bad:
        bad = bbad
    if "connected" not in steps:
        print("[실패] 타깃에 연결되지 않았습니다 — 아무것도 쓰지 않았습니다. 전원·IGN·케이블을 확인하세요.")
        return EXIT_CONNECT
    if with_flash and "flashed" not in steps:
        if why == "stuck":
            print("[주의] 쓰기 단계가 %d초 넘게 끝나지 않았습니다. 쓰는 도중일 수 있어 CVD 를 끄지 않았습니다." % flash_limit)
            print("       CVD 화면을 확인하고, 멈춰 있으면 직접 닫은 뒤 다시 기록하세요.")
            return EXIT_TIMEOUT
        print("[실패] 기록이 끝나지 않았습니다 — CVD 메시지 창의 오류 줄을 확인하세요.")
        return EXIT_FLASH
    if "done" not in steps or not rows:
        print("[실패] 검증이 끝나지 않았습니다 — 연결(전원·IGN·케이블)을 확인하세요.")
        return EXIT_VERIFY
    if bad:
        print("[실패] 플래시 내용이 이미지와 다릅니다.")
        return EXIT_MISMATCH
    print("[성공] 기록·검증 완료" if with_flash else "[성공] 검증 완료")
    return EXIT_OK


MODE_KO = {"IMAGE": "FBL+APP", "HSM": "HSM 만", "ALL": "FBL+APP+HSM"}


def print_flash_options(a, c):
    """--yes 전에 고를 수 있는 옵션과 지금 선택값, 바꾸는 방법을 보여 준다."""
    mark = lambda on: "▶" if on else " "
    print("[옵션] 지금 선택값은 ▶. 바꾸려면 오른쪽 인자를 붙인다. 모드·데이터 영역은 매번 기본값, APP 버전은 config 의 버전을 이어 쓴다.")
    print("  무엇을 쓸지")
    for m in MODES:
        print("   %s %-5s %-12s --mode %s%s" % (mark(c["mode"] == m), m, MODE_KO.get(m, ""), m,
                                              "   (기본)" if m == "IMAGE" else ""))
    print("  데이터 영역 (DTC·NvM·학습값, 워크 플래시)")
    print("   %s 지움         (인자 없음, 기본)   보드 이력을 모를 때" % mark(c["erase"] == "YES"))
    print("   %s 유지         --keep-data        고장 기록을 남긴 채 새 빌드만 올릴 때 (실기 미확인)" % mark(c["erase"] == "NO"))
    if c["bank"] == "dual":
        print("  APP 를 쓸 뱅크 (듀얼뱅크)  기본 = config 설정(마지막으로 쓴 값), --yes 로 쓰면 config 에 저장")
        for b, how, why in (("A", "--banks A ", "벤더 원본. B 에는 FBL 만, B 의 APP 는 예전 것 그대로"),
                            ("AB", "--banks AB", "B 에도 같은 APP. FBL 이 어느 뱅크로 부팅해도 같은 버전 (실기 미확인)")):
            print("   %s %-3s %-14s %s%s   %s" % (mark(c["banks"] == b), b, BANKS_KO[b], how,
                                               " (config)" if b == c["_cfg_banks"] else "         ", why))
    vs = c["_versions"]
    if vs:
        print("  APP 버전 (APP _Writing.s19 + ELF 를 그 버전 폴더에서)  기본 = config 의 버전(마지막 설정)")
        newest = newest_ver(vs)
        for v in sorted(vs, key=ver_key):
            tags = [t for t, on in (("config", v == c["_cfg_version"]), ("현재 소스", v == c["_src_ver"]),
                                    ("가장 새 버전", v == newest), ("TEST, FBL 도 TEST", is_test(v))) if on]
            print("   %s %-8s %-28s %s" % (mark(v == c["version"]), v, " · ".join(tags),
                                          "(인자 없음)" if v == c["_cfg_version"] else "--version %s" % v))
    print("  이미지 (FBL·HSM%s)" % ("" if vs else "·APP·ELF"))
    print("   %s 저장된 경로  (인자 없음)" % mark(not a.rescan and not any(getattr(a, k) for k in ("fbl", "app", "elf", "hsm"))))
    print("   %s 최신 재탐색  --rescan           새 빌드가 나왔을 때 (저장소 git pull 먼저)" % mark(a.rescan))
    print("   %s 직접 지정    --fbl/--hsm%s <경로>" % (mark(any(getattr(a, k) for k in ("fbl", "app", "elf", "hsm"))),
                                                   "" if vs else "/--app/--elf"))


def print_image_head(a, c, mode=None):
    """flash·verify·set 공통: 이번에 쓸(비교할) 버전과 경로, 알림. mode 를 주면 그 모드가 쓰는 파일만."""
    if c["version"]:
        why = {"--version": "--version 으로 지정", "config": "config 의 버전", "하나뿐": "버전 폴더 하나뿐"}
        print("  버전 %s  (%s)" % (c["version"], why.get(c.get("_version_why"), "")))
    use = {"IMAGE": ("fbl", "app", "elf"), "HSM": ("hsm", "elf"), "ALL": ("fbl", "app", "elf", "hsm")}.get(mode)
    for k in ("fbl", "app", "elf", "hsm"):
        if (use is None and (k != "hsm" or c.get("hsm"))) or (use and k in use):
            print("  %-4s %s" % (k.upper(), c[k]))
            if k == "fbl" and c.get("_fbl_why"):
                print("       ← %s" % c["_fbl_why"])
    src, vs = c["_src_ver"], c["_versions"]
    if c["version"] and src and src in vs and src != c["version"]:
        print("  [알림] 현재 소스(PJ_Define.h) 버전은 %s 입니다. 그 버전을 쓰려면 --version %s" % (src, src))
    newer = [v for v in vs if not is_test(v) and ver_num(v) > ver_num(c["version"])]
    if c["version"] and newer and src not in newer:
        print("  [알림] 더 새 버전 폴더가 있습니다: %s" % ", ".join(sorted(newer, key=ver_key)))
    if c["_rebuilt"]:
        print("  [알림] APP 가 마지막 설정 뒤 같은 경로에 다시 빌드됐습니다 — 검증 지점을 새 파일 기준으로 다시 계산합니다.")


def cmd_flash(a, with_flash=True):
    check_cvd(strict=True)
    c = prepare_cfg(a)
    d = proj_fs(a.name)
    if with_flash:
        print("[%s] 모드 %s, 데이터 영역(DTC·NvM) %s%s" % (
            a.name, c["mode"], "지움" if c["erase"] == "YES" else "유지",
            ", APP 를 %s" % BANKS_KO[c["banks"]] if c["bank"] == "dual" and c["mode"] != "HSM" else ""))
        print_image_head(a, c, c["mode"])
        if c["mode"] in ("HSM", "ALL"):
            print("  (HSM 영역은 CM4 에서 읽을 수 없어 검증은 FBL·APP 지점으로 한다)")
        if not a.yes:
            print_flash_options(a, c)
            print("[확인 필요] 아직 보드에 아무것도 하지 않았습니다. 위 내용이 맞으면 같은 인자에 --yes 를 붙여 다시 실행하세요.")
            sys.exit(EXIT_OK)
    else:
        print("[%s] 검증만 — 보드를 config 의 이미지와 비교 (보드에 쓰지 않음)%s" % (
            a.name, ", APP 뱅크 설정: %s" % BANKS_KO[c["banks"]] if c["bank"] == "dual" else ""))
        print_image_head(a, c)
    write_cfg(c)
    entry = os.path.join(d, "%s_%s.csf" % (a.name, "run" if with_flash else "check"))
    log_fs = os.path.join(d, "%s_result.log" % a.name)
    why, sec = run_cvd(entry, log_fs, a.timeout, a.flash_timeout)
    print("  CVD 종료: %s, %d초" % (why, sec))
    sys.exit(judge(log_fs, with_flash, why, a.flash_timeout, c))


def cmd_set(a):
    """보드에 쓰지 않고 config 의 버전·이미지 경로만 바꾼다 (화면 PD·PA 는 누를 때마다 config 를 읽는다).
    검증 지점도 새 파일 기준으로 다시 계산한다. 같은 버전 재빌드 후 검증 지점 갱신에도 쓴다."""
    old = read_cfg(a.name)
    c = prepare_cfg(a)
    print("[%s] config 변경 (보드에는 쓰지 않음)" % a.name)
    print_image_head(a, c)
    changed = [k for k in ("version", "banks", "fbl", "app", "elf", "hsm") if (old[k] or "") != (c[k] or "")]
    for k in changed:
        print("  바뀜 %-7s %s\n       %-7s → %s" % (k.upper(), old[k] or "(없음)", "", c[k] or "(없음)"))
    if not changed and not c["_rebuilt"]:
        print("  경로·버전은 그대로 — 검증 지점만 다시 계산합니다.")
    if a.dry_run:
        print("[dry-run] config 를 바꾸지 않았습니다.")
        return
    pts = write_cfg(c)
    print("[완료] %s — 검증 지점 %d개 다시 계산" % (cfg_path(a.name), len(pts)))
    print("  CVD 화면: 다음 PD / PA 부터 이 경로를 씁니다 (과제를 다시 고를 필요 없음).")


def cmd_list(a):
    ps = list_projects()
    if not ps:
        print("생성된 과제가 없습니다: %s" % FS_PROJECTS)
    for n, cpu in ps:
        c = read_cfg(n)
        print("%-16s %-14s %-6s 버전 %-8s APP뱅크 %-3s 저장소 %s" % (n, cpu, c["bank"], c["version"] or "-",
                                                                c["banks"] or "A", c["repo"]))


# ============================================================== main
def main():
    # 파이프·리다이렉트로 실행하면 윈도우 코드페이지(cp949)가 쓰여 '—' 등에서 멈춘다. 출력은 UTF-8 로 고정.
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="CVD CLI 다운로드 + 검증 (v%s)" % VERSION)
    sp = ap.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cvd-root", help="CVD 설치 폴더 (기본: %s)" % DEFAULT_ROOT)

    p = sp.add_parser("init", parents=[common], help="과제 폴더 생성 + loadfile.csf 등록")
    p.add_argument("--repo", help="프로젝트 폴더 (기본: 현재 폴더)")
    p.add_argument("--name", help="과제명 (예: HE1I_PSU)")
    p.add_argument("--bank", choices=("dual", "single"), help="뱅크 구성 (사용자 확인값)")
    p.add_argument("--version", help="APP·ELF 버전 폴더 (Debug\\OEUK_xxxx\\<버전>\\, 여러 개일 때 필수)")
    for k in ("fbl", "app", "elf", "hsm"):
        p.add_argument("--" + k, help="%s 경로 직접 지정" % k.upper())
    p.add_argument("--yes", action="store_true", help="확인 생략")
    p.add_argument("--dry-run", action="store_true", help="생성하지 않고 계획만 출력")
    p.add_argument("--force-mcu", action="store_true", help="MCU 계열 불일치 무시 (권장하지 않음)")
    p.add_argument("--force-bank", action="store_true", help="저장소 조사 결과와 다른 뱅크 지정 허용 (권장하지 않음)")

    p = sp.add_parser("scan", parents=[common], help="인식 결과만 출력")
    p.add_argument("--repo")

    for cmd in ("flash", "verify"):
        p = sp.add_parser(cmd, parents=[common])
        p.add_argument("--name", required=True)
        if cmd == "flash":
            p.add_argument("--mode", choices=MODES, help="IMAGE(기본) / HSM / ALL")
            p.add_argument("--keep-data", action="store_true", help="데이터 영역(DTC·NvM)을 지우지 않음")
            p.add_argument("--banks", choices=BANKS, help="APP 를 쓸 뱅크: A(벤더 원본, A 만) / AB(B 에도). 없으면 config 설정")
            p.add_argument("--version", help="APP·ELF 버전 폴더 (없으면 config 의 버전)")
            for k in ("fbl", "app", "elf", "hsm"):
                p.add_argument("--" + k)
            p.add_argument("--rescan", action="store_true", help="저장소에서 FBL·HSM 을 다시 찾음 (버전 폴더 없으면 APP·ELF 도)")
            p.add_argument("--yes", action="store_true", help="계획 확인 후 실제로 기록")
        p.add_argument("--timeout", type=int, default=120, help="쓰기 외 단계에서 진전이 없을 때 기다리는 초")
        p.add_argument("--flash-timeout", type=int, default=900, help="쓰기 단계 한도(초). 넘어도 CVD 를 끄지 않음")

    p = sp.add_parser("set", parents=[common], help="보드에 쓰지 않고 config 의 버전·이미지 경로만 변경")
    p.add_argument("--name", required=True)
    p.add_argument("--version", help="APP·ELF 버전 폴더")
    p.add_argument("--banks", choices=BANKS, help="APP 를 쓸 뱅크 기본값: A / AB (화면 PD 창 첫 줄에 보임)")
    for k in ("fbl", "app", "elf", "hsm"):
        p.add_argument("--" + k)
    p.add_argument("--rescan", action="store_true", help="FBL·HSM 재탐색")
    p.add_argument("--dry-run", action="store_true")

    sp.add_parser("list", parents=[common])
    sp.add_parser("startup", parents=[common], help="시작 메뉴 'CVD Projects' 바로가기 생성 (init 도 만든다)")
    p = sp.add_parser("refresh", parents=[common], help="기존 과제의 PD 창·툴바 스크립트를 새 템플릿으로 다시 생성")
    p.add_argument("--name", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if getattr(a, "cvd_root", None):
        set_root(os.path.abspath(a.cvd_root))
    if a.cmd == "init":
        cmd_init(a)
    elif a.cmd == "scan":
        cmd_scan(a)
    elif a.cmd == "flash":
        cmd_flash(a, True)
    elif a.cmd == "verify":
        cmd_flash(a, False)
    elif a.cmd == "set":
        cmd_set(a)
    elif a.cmd == "list":
        cmd_list(a)
    elif a.cmd == "startup":
        cmd_startup(a)
    elif a.cmd == "refresh":
        cmd_refresh(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
