# -*- coding: utf-8 -*-
"""
cvd_flash.py - CVD(CodeViser) CLI 다운로드 + 검증

  init    과제 폴더 생성 (Projects\\<NAME>\\<NAME>_*.csf) + loadfile.csf 등록
  scan    저장소에서 이미지·MCU·뱅크 구성 인식 결과만 출력 (변경 없음)
  flash   이미지 기록 → 검증 (--yes 없으면 계획만 출력)
  verify  기록 없이 검증만
  list    생성된 과제 목록

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

VERSION = "1.2.0"

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


def discover(repo):
    repo = os.path.abspath(repo)
    if not os.path.isdir(repo):
        die("프로젝트 폴더가 없습니다: " + repo)
    imgs, elfs, bank_dirs = [], [], []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
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
    hsm = [p for p in imgs if "hsm" in low(p)]
    fbl = [p for p in imgs if "fbl" in low(p) or "boot" in low(p)]
    rest = [p for p in imgs if p not in hsm and p not in fbl]
    app_w = [p for p in rest if "_writing" in low(p)] or [p for p in rest if "app" in low(p)] or rest
    elf = [p for p in elfs if "fbl" not in low(p) and "hsm" not in low(p)]
    elf = [p for p in elf if "app" in low(p)] or elf
    cands = {"fbl": _by_time(fbl), "hsm": _by_time(hsm), "elf": _by_time(elf), "app": _by_time(app_w)}
    d = {"repo": repo, "cands": cands}
    for k in ("fbl", "hsm", "elf"):
        d[k] = cands[k][0] if cands[k] else None
    d["app"] = cands["app"][0] if cands["app"] else d["elf"]      # 기록용 APP (없으면 ELF 로 기록)
    d["mcu"] = detect_mcu(repo)
    d["name"] = suggest_name(repo, d["hsm"])
    d["bank"], d["bank_why"] = detect_bank(repo, bank_dirs)
    return d


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


# ============================================================== config.csf 읽고 쓰기
CFG_KEYS = ("name", "dir", "cpu", "bank", "mode", "erase", "repo", "fbl", "app", "elf", "hsm", "src", "log", "template")


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
    pts = verify_points([c.get("fbl"), c.get("app")])
    names = " ".join("&cfg_%s" % k for k in CFG_KEYS)
    vnames = " ".join("&cfg_va%d &cfg_ve%d" % (i, i) for i in range(1, MAX_POINTS + 1))
    L = [
        "; %s_config.csf - cvd_flash.py %s 가 생성. 경로는 cvd_flash.py 로 갱신한다." % (name, VERSION),
        "; 갱신: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "; cfg_erase: YES = 데이터 영역(DTC·NvM)까지 소거 / NO = 유지. CLI 에서 인자가 없을 때만 쓴다.",
        "GLOBAL %s" % names,
        "GLOBAL %s" % vnames,
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
    L.append("ENDDO")
    wtext(cfg_path(name), "\n".join(L) + "\n")
    return pts


# ============================================================== 템플릿
def tpl_flash(name, d):
    return """; {n}_flash.csf - FL: 소거 + 기록
; CLI : do {n}_flash.csf <IMAGE|HSM|ALL> <YES|NO>   (YES = 데이터 영역까지 소거)
; 화면: FL 버튼 (인자 없음) -> 무엇을 쓸지, 데이터 영역을 지울지 선택창으로 묻는다
LOCAL &m &cvd_erase &a &h &e &gui &filename1 &filename2 &filename3
ENTRY &m &cvd_erase
do {d}\\{n}_config.csf
&gui="NO"
IF "&m"==""
(
	&gui="YES"
	print "FL: FBL=&cfg_fbl"
	print "FL: APP=&cfg_app"
	print "FL: HSM=&cfg_hsm"
	DIALOG.YESNO "Write FBL + APP ?"
	ENTRY &a
	DIALOG.YESNO "Write HSM ?"
	ENTRY &h
	&m="NONE"
	IF &a
	(
		&m="IMAGE"
	)
	IF &h
	(
		IF "&m"=="IMAGE"
		(
			&m="ALL"
		)
		ELSE
		(
			&m="HSM"
		)
	)
	IF "&m"=="NONE"
	(
		print "FL: cancelled (nothing selected)"
		ENDDO
	)
	DIALOG.YESNO "Erase data flash too? (DTC / NvM / learned values)"
	ENTRY &e
	&cvd_erase="NO"
	IF &e
	(
		&cvd_erase="YES"
	)
)
IF "&cvd_erase"==""
(
	&cvd_erase="&cfg_erase"
)
; 원본 .csf 가 이 LOCAL 변수들을 읽는다
&filename1="&cfg_fbl"
&filename2="&cfg_app"
&filename3="&cfg_hsm"
print "FL: mode=&m erase_data=&cvd_erase"
IF ("&m"=="IMAGE")||("&m"=="ALL")
(
	print "FL: HOST (FBL+APP) &filename1 / &filename2"
	do {d}\\{n}_flash_host.csf
)
IF ("&m"=="HSM")||("&m"=="ALL")
(
	print "FL: HSM &filename3"
	do {d}\\{n}_flash_hsm.csf
)
print "FL: done (&m)"
; 화면에서 눌렀으면 이어서 검증하고 결과를 창으로 알린다 (CLI 는 run.csf 가 따로 검증)
IF "&gui"=="YES"
(
	do {d}\\{n}_verify.csf FL
)
ENDDO
""".format(n=name, d=d)


def tpl_verify(name, d):
    L = ["; %s_verify.csf - VF: 연결 후 검증 지점을 읽어 로그에 남긴다" % name,
         "; 인자: CLI = 결과 창 없음 / FL = FL 버튼이 부름 / 없음 = VF 버튼",
         "LOCAL &v &ctx &bad &first",
         "ENTRY &ctx",
         '&bad="NO"',
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
    L += ['WRITE #1 "VERIFY=end"', "CLOSE #1",
          'IF "&bad"=="YES"',
          "(",
          '\tprint "VF: FAILED - first mismatch at &first (log: &cfg_log)"',
          '\tIF "&ctx"!="CLI"',
          "\t(",
          '\t\tDIALOG.OK "Verify FAILED - flash does not match the image (first mismatch &first). See &cfg_log"',
          "\t)",
          ")",
          "ELSE",
          "(",
          '\tprint "VF: OK - all check points match"',
          '\tIF "&ctx"=="FL"',
          "\t(",
          '\t\tDIALOG.OK "Flash + Verify OK - all check points match the image files"',
          "\t)",
          '\tIF "&ctx"==""',
          "\t(",
          '\t\tDIALOG.OK "Verify OK - all check points match the image files"',
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
         "CLOSE #1",
         "; 쓰기 전에 타깃이 붙는지 먼저 본다 (여기서 멈추면 아무것도 쓰지 않은 상태)",
         "do %s\\%s_connect.csf" % (d, name)]
    L += _step("connected")
    if with_flash:
        L += ["sys.down"]
        L += _step("flashing")
        L += ["do %s\\%s_flash.csf &cfg_mode &cfg_erase" % (d, name)]
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
              '\t\t\t\tTOOLITEM  "%s Flash"    "FL,R"  "CD.DO %s\\%s_flash.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Verify"   "VF,G"  "CD.DO %s\\%s_verify.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Connect"  "CN,R"  "CD.DO %s\\%s_connect.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Reset"    "RE,R"  "CD.DO %s\\%s_reset.csf"' % (n, d, n),
              '\t\t\t\tTOOLITEM  "%s Config"   "CF,B"  "Pedit %s\\%s_config.csf"' % (n, d, n),
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
    for k, lab in (("fbl", "FBL"), ("app", "APP(기록)"), ("elf", "ELF(심볼)"), ("hsm", "HSM")):
        print("  %-10s %s" % (lab, d[k] or "없음"))
        others = [p for p in d["cands"].get(k, []) if p != d[k]]
        if others:
            print("  %-10s   (다른 후보 %d개 — 가장 최근 파일을 골랐음. 차종·사양이 맞는지 확인)" % ("", len(others)))
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
    for k in ("fbl", "app", "elf", "hsm"):
        v = getattr(a, k)
        if v:
            d[k] = os.path.abspath(v)
            d["cands"][k] = [d[k]]
    tcpu = template_check()
    print_scan(d)
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
    cfg = {"name": name, "dir": dst_win, "cpu": tcpu, "bank": bank, "mode": "IMAGE", "erase": "YES",
           "repo": d["repo"], "fbl": d["fbl"], "app": d["app"], "elf": d["elf"], "hsm": d["hsm"] or "",
           "src": d["repo"], "log": wpath(dst_win, "%s_result.log" % name),
           "template": "cyt2bl_dual (cvd_flash %s)" % VERSION}
    pts = write_cfg(cfg)
    bak = rebuild_loadfile()
    if not os.path.isfile(os.path.join(FS_PROJECTS, "cvd_start.csf")):
        wtext(os.path.join(FS_PROJECTS, "cvd_start.csf"), tpl_start())
    print("[완료] %s" % dst_fs)
    for x in notes:
        print("  - " + x)
    print("  - 검증 지점 %d개" % len(pts))
    if bak:
        print("  - loadfile.csf 백업: %s" % bak)
    print("다음: python cvd_flash.py flash --name %s" % name)


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
    """저장된 설정 + 이번 인자. 파일에 쓰지는 않는다 (flash 는 --yes 일 때만 쓴다)."""
    c = read_cfg(a.name)
    if getattr(a, "rescan", False):
        d = discover(c["repo"])
        for k in ("fbl", "app", "elf", "hsm"):
            if d[k]:
                c[k] = d[k]
    for k in ("fbl", "app", "elf", "hsm"):
        v = getattr(a, k, None)
        if v:
            c[k] = os.path.abspath(v)
    if hasattr(a, "mode"):                       # flash: 매번 지정값, 없으면 IMAGE (저장값을 이어 쓰지 않음)
        c["mode"] = a.mode or "IMAGE"
        c["erase"] = "NO" if a.keep_data else "YES"
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


def judge(log_fs, with_flash, why, flash_limit):
    t = rb(log_fs).decode(ENC, "replace") if os.path.isfile(log_fs) else ""
    steps = re.findall(r"STEP=(\w+)", t)
    last = steps[-1] if steps else "없음"
    rows = re.findall(r"RD\s+(0x[0-9A-Fa-f]+)\s+(\S+)\s+(0x[0-9A-Fa-f]+)", t)
    bad = []
    for addr, got, exp in rows:
        try:
            ok = int(got, 16) == int(exp, 16)
        except ValueError:
            ok = False
        if not ok:
            bad.append((addr, got, exp))
    print("[로그] %s  (마지막 단계: %s)" % (log_fs, last))
    print("  검증 지점 %d개, 불일치 %d개" % (len(rows), len(bad)))
    for addr, got, exp in bad[:8]:
        print("    %s  읽음 %s  기대 %s" % (addr, got, exp))
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


def cmd_flash(a, with_flash=True):
    check_cvd(strict=True)
    c = prepare_cfg(a)
    d = proj_fs(a.name)
    if with_flash:
        print("[%s] 모드 %s, 데이터 영역(DTC·NvM) %s" % (a.name, c["mode"], "지움" if c["erase"] == "YES" else "유지"))
        for k in ("fbl", "app", "hsm"):
            if (k != "hsm" or c["mode"] in ("HSM", "ALL")) and (k == "hsm" or c["mode"] in ("IMAGE", "ALL")):
                print("  %-4s %s" % (k.upper(), c[k]))
        if c["mode"] in ("HSM", "ALL"):
            print("  (HSM 영역은 CM4 에서 읽을 수 없어 검증은 FBL·APP 지점으로 한다)")
        if not a.yes:
            print("[확인 필요] 위 내용으로 보드를 지우고 씁니다. 맞으면 --yes 를 붙여 다시 실행하세요.")
            sys.exit(EXIT_OK)
    else:
        print("[%s] 검증만" % a.name)
    write_cfg(c)
    entry = os.path.join(d, "%s_%s.csf" % (a.name, "run" if with_flash else "check"))
    log_fs = os.path.join(d, "%s_result.log" % a.name)
    why, sec = run_cvd(entry, log_fs, a.timeout, a.flash_timeout)
    print("  CVD 종료: %s, %d초" % (why, sec))
    sys.exit(judge(log_fs, with_flash, why, a.flash_timeout))


def cmd_list(a):
    ps = list_projects()
    if not ps:
        print("생성된 과제가 없습니다: %s" % FS_PROJECTS)
    for n, cpu in ps:
        c = read_cfg(n)
        print("%-16s %-14s %-6s 저장소 %s" % (n, cpu, c["bank"], c["repo"]))


# ============================================================== main
def main():
    ap = argparse.ArgumentParser(description="CVD CLI 다운로드 + 검증 (v%s)" % VERSION)
    sp = ap.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cvd-root", help="CVD 설치 폴더 (기본: %s)" % DEFAULT_ROOT)

    p = sp.add_parser("init", parents=[common], help="과제 폴더 생성 + loadfile.csf 등록")
    p.add_argument("--repo", help="프로젝트 폴더 (기본: 현재 폴더)")
    p.add_argument("--name", help="과제명 (예: HE1I_PSU)")
    p.add_argument("--bank", choices=("dual", "single"), help="뱅크 구성 (사용자 확인값)")
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
            for k in ("fbl", "app", "elf", "hsm"):
                p.add_argument("--" + k)
            p.add_argument("--rescan", action="store_true", help="저장소에서 최신 이미지를 다시 찾음")
            p.add_argument("--yes", action="store_true", help="계획 확인 후 실제로 기록")
        p.add_argument("--timeout", type=int, default=120, help="쓰기 외 단계에서 진전이 없을 때 기다리는 초")
        p.add_argument("--flash-timeout", type=int, default=900, help="쓰기 단계 한도(초). 넘어도 CVD 를 끄지 않음")

    sp.add_parser("list", parents=[common])
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
    elif a.cmd == "list":
        cmd_list(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
