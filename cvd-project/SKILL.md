---
name: "cvd-project"
description: "CVD(CodeViser) 과제 단위로 빌드 결과를 CLI로 MCU에 기록하고 검증하는 스킬(Claude Code CLI 전용). 과제 최초 1회 init, 이후 flash/verify. \"CVD로 다운로드\", \"보드에 구워줘\", \"라이팅\", \"CVD init\", \"CVD 설정 만들어줘\" 등에 사용."
---

# cvd-project

빌드 결과(FBL/APP/HSM)를 CVD CLI로 타깃에 기록하고, 플래시 내용을 이미지 파일과 대조해 성공/실패를 종료 코드로 알려 준다. 같은 .csf 파일을 CVD 화면 버튼으로도 쓴다. 이전 스킬 `cvd-project-setup`을 대체한다.

## 0단계 — 도구 설치 확인 (매번 먼저)

- 실행 환경: Claude Code CLI, CVD가 설치된 Windows PC (`C:\JnDTech\CVI\CVD`).
- 도구 위치: `C:\JnDTech\CVI\CVD\Projects\cvd_flash.py`
- 파일이 없거나 파일 안 `VERSION = "..."` 가 아래 부록의 버전(1.0.0)과 다르면, **부록의 스크립트를 그대로 그 경로에 쓴다**(Projects 폴더가 없으면 만든다). 한 글자도 바꾸지 않는다. 설치했으면 사용자에게 한 줄로 알린다.
- 이후 모든 명령은 `python C:\JnDTech\CVI\CVD\Projects\cvd_flash.py <명령>`.

## 폴더 구조 (도구가 만든다)

```
C:\JnDTech\CVI\CVD\
├── S32_Config\            기존 자산 — 읽기만 (복제 원본)
└── Projects\
     ├── cvd_flash.py        도구 (0단계에서 자동 설치)
     ├── cvd_start.csf       없을 때 1회만 생성, 이후 고정 — 툴바 ED/PS
     ├── loadfile.csf        과제 목록. init으로 과제가 추가될 때만 재생성(백업 후)
     └── <과제명>\
          <과제명>_config.csf      경로·검증 지점 (flash 때 도구가 갱신)
          <과제명>_connect.csf     CN  연결+워치독 해제+심볼+소스경로
          <과제명>_flash.csf       FL  소거+기록 (IMAGE/HSM/ALL)
          <과제명>_flash_host.csf  원본 HOST .csf 변환본
          <과제명>_flash_hsm.csf   원본 HSM .csf 변환본
          <과제명>_verify.csf      VF  검증 지점 읽기 → 로그
          <과제명>_reset.csf       RE  리셋 → main
          <과제명>_run.csf         CLI: flash → verify → QUIT
          <과제명>_check.csf       CLI: verify → QUIT
          <과제명>_result.log      결과 로그
          *.out                    플래시 로더
```

## 흐름 A — init (과제당 1회)

사용자가 CVD 설정·초기화·새 과제를 요청하거나, flash 대상 과제가 없을 때.

1. **프로젝트 폴더를 먼저 묻는다.** 기본값은 현재 작업 폴더. AskUserQuestion으로 "현재 폴더 `<cwd>` 사용"을 첫 옵션으로 보여 주고, 다른 경로는 직접 입력받는다.
2. `scan --repo <폴더>` 실행 → 인식 결과(FBL / APP 기록용 / ELF 심볼용 / HSM / MCU / 과제명 제안 / 복제 원본 후보)를 표로 보여 준다. 못 찾은 이미지는 경로를 묻는다(`--fbl --app --elf --hsm`).
3. 과제명과 복제 원본을 묻는다.
   - 과제명: 제안값 기본. 영문 대문자·숫자·`_`.
   - 복제 원본: MCU 계열이 같은 후보만. CYT2BL 듀얼뱅크는 실기 검증된 `HE1i_PSU_Dual`을 첫 옵션(권장)으로. 계열이 다른 원본은 제시하지 않는다.
4. `init --repo <폴더> --name <과제명> --from <원본> --yes --dry-run` 으로 계획을 보여 주고 확인받는다.
5. 확인되면 `--dry-run` 없이 실행하고 결과(변환 내역, 검증 지점 수)를 보고한다.

## 흐름 B — flash (빌드마다)

```
flash --name <과제명> [--mode IMAGE|HSM|ALL] [--rescan] [--fbl ..] [--app ..] [--elf ..] [--hsm ..]
```

- 기본 IMAGE(FBL+APP). HSM은 사용자가 요청할 때만 `--mode HSM|ALL`.
- 새 빌드가 나왔으면 `--rescan`(저장소에서 최신 이미지 재탐색) 또는 경로 직접 지정.
- 실행 전 한 줄로 알린다: 과제·모드·이미지. 기록은 확인 창 없이 코드·워크 플래시를 소거한다.
- CVD 화면이 켜져 있으면 포트가 겹치므로 닫고 실행하도록 안내한다.

검증만: `verify --name <과제명>` / 목록: `list`

## 결과 해석

| 종료 코드 | 뜻 | 안내 |
|---|---|---|
| 0 | 기록·검증 성공 | 필요하면 CN → RE 또는 전원 재투입으로 동작 확인 |
| 2 | 기록 미완료 | CVD 메시지 창 오류 줄, 전원·IGN·SWD 케이블 |
| 3 | 검증 불일치 | 불일치 주소와 이미지 확인, 다시 기록 |
| 4 | 검증 미완료 | 연결(전원·IGN·케이블), `<과제명>_connect.csf` |
| 5 | 시간 초과 | CVD가 멈춘 위치 확인, `--timeout` 조정 |
| 1 | 사용 오류 | 메시지대로 인자 보완 |

로그 마지막 `STEP=`(start → flashed → done)로 멈춘 단계를 말한다. HSM 영역은 CM4에서 읽을 수 없어 검증은 FBL·APP 지점으로 한다.

## CVD 화면에서 쓰기

`Program → Run Script File → Projects\cvd_start.csf` → **PS** → 과제 → **FL**(기록) / **VF**(검증) / **CN**(연결·심볼) / **RE**(리셋→main) / **CF**(config 편집). CLI와 같은 파일을 쓴다.

## 규칙

- `S32_Config`와 기존 `loadfile.cmm`은 읽기만 한다.
- 이미 있는 과제는 덮어쓰지 않는다(도구가 중단). 다시 만들려면 사용자가 폴더를 지운 뒤 init.
- 생성된 .csf는 손으로 고치지 않는다. 경로는 flash 인자나 `--rescan`으로 갱신한다.
- Erase All(`flash_erase_all`)은 쓰지 않는다 — SFlash까지 지운다.
- 복제 원본의 MCU 계열이 다르면 진행하지 않는다(`--force-mcu`는 사용자가 명시적으로 요구할 때만).

## 첫 실기 사용 시 확인

1. `CVD.exe <파일>.csf` 로 CLI 실행되는지. 안 되면 `--entry cmm` 으로 재실행(진입 파일만 .cmm 사본).
2. 로그가 STEP=done까지 가고 검증 지점이 모두 일치하는지.
3. 기존 PD로 기록한 결과와 동작이 같은지(CN → RE로 main 도달).

## 부록 — cvd_flash.py (VERSION 1.0.0, 0단계에서 이 내용 그대로 설치)

```python
# -*- coding: utf-8 -*-
"""
cvd_flash.py - CVD(CodeViser) CLI 다운로드 + 검증

  init    과제 폴더 생성 (Projects\\<NAME>\\<NAME>_*.csf) + loadfile.csf 등록
  scan    저장소에서 이미지·MCU 인식 결과와 복제 후보만 출력 (변경 없음)
  flash   이미지 기록 → 검증 (기본 명령)
  verify  기록 없이 검증만
  list    생성된 과제 목록

예)
  python cvd_flash.py init                         (대화형: 프로젝트 폴더부터 질문)
  python cvd_flash.py init --repo D:\\w\\jg_wpc --name JG_WPC --from WPC_JG_Dual --yes
  python cvd_flash.py flash --name JG_WPC          (저장된 경로로 FBL+APP 기록 → 검증)
  python cvd_flash.py flash --name JG_WPC --mode ALL --rescan
  python cvd_flash.py verify --name JG_WPC

종료 코드: 0 성공 / 1 사용 오류 / 2 기록 미완료 / 3 검증 불일치 / 4 검증 미완료 / 5 시간 초과
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

VERSION = "1.0.0"

# 실제 파일 위치(FS)와 .csf 안에 적힐 윈도우 경로(WIN)를 나눈다. 평소에는 같다.
WIN_ROOT = os.environ.get("CVD_ROOT_WIN", r"C:\JnDTech\CVI\CVD")
FS_ROOT = os.environ.get("CVD_ROOT", WIN_ROOT)
FS_PROJECTS = os.path.join(FS_ROOT, "Projects")
FS_LEGACY = os.path.join(FS_ROOT, "S32_Config")
WIN_PROJECTS = WIN_ROOT + "\\Projects"
CVD_EXE = os.environ.get("CVD_EXE", os.path.join(FS_ROOT, "Bin", "CVD.exe"))

ENC = "cp949"
NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,30}$")
MODES = ("IMAGE", "HSM", "ALL")
MAX_POINTS = 16
# CM4 에서 읽을 수 있는 코드 플래시 범위 (HSM 영역 0x10000000~0x10027FFF 제외)
VERIFY_RANGE = (0x10028000, 0x12000000)

EXIT_OK, EXIT_USAGE, EXIT_FLASH, EXIT_MISMATCH, EXIT_VERIFY, EXIT_TIMEOUT = 0, 1, 2, 3, 4, 5


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


def ask(prompt, default=None):
    if not sys.stdin.isatty():
        return default
    tail = " [%s]" % default if default else ""
    v = input("%s%s > " % (prompt, tail)).strip().strip('"')
    return v or default


# ============================================================== 저장소 인식
IMG_EXT = (".sre", ".s19", ".srec", ".s28", ".s37", ".mot")
SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".vs"}


def _newest(files):
    return max(files, key=os.path.getmtime) if files else None


def discover(repo):
    repo = os.path.abspath(repo)
    if not os.path.isdir(repo):
        die("프로젝트 폴더가 없습니다: " + repo)
    imgs, elfs = [], []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
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
    d = {
        "repo": repo,
        "fbl": _newest(fbl),
        "hsm": _newest(hsm),
        "elf": _newest(elf),
    }
    d["app"] = _newest(app_w) or d["elf"]          # 기록용 APP (없으면 ELF 로 기록)
    d["mcu"] = detect_mcu(repo)
    d["name"] = suggest_name(repo, d["hsm"])
    return d


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


# ============================================================== 복제 원본 (기존 S32_Config)
def read_cpu(folder):
    p = os.path.join(folder, "Path.cmm")
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


def source_candidates(mcu=None):
    out = []
    if not os.path.isdir(FS_LEGACY):
        return out
    for n in sorted(os.listdir(FS_LEGACY)):
        f = os.path.join(FS_LEGACY, n)
        if not os.path.isdir(f) or n.startswith("_"):
            continue
        host = glob.glob(os.path.join(f, "*HOST*.csf"))
        if not host or not os.path.isfile(os.path.join(f, "Path.cmm")):
            continue
        cpu = read_cpu(f) or "?"
        ok = True
        if mcu:
            ok = cpu.upper().startswith(mcu[:6].upper())
        out.append({"name": n, "cpu": cpu, "match": ok})
    return out


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
CFG_KEYS = ("name", "dir", "cpu", "mode", "repo", "fbl", "app", "elf", "hsm", "src", "log", "source")


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
    return """; {n}_flash.csf - FL: 소거 + 기록 (확인 창 없음)
; 인자: IMAGE (FBL+APP, 기본) / HSM / ALL
LOCAL &m &filename1 &filename2 &filename3
ENTRY &m
do {d}\\{n}_config.csf
IF "&m"==""
(
	&m="&cfg_mode"
)
; 원본 .csf 가 이 세 LOCAL 변수를 읽는다
&filename1="&cfg_fbl"
&filename2="&cfg_app"
&filename3="&cfg_hsm"
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
ENDDO
""".format(n=name, d=d)


def tpl_verify(name, d):
    L = ["; %s_verify.csf - VF: 연결 후 검증 지점을 읽어 로그에 남긴다" % name,
         "LOCAL &v",
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
              ")"]
    L += ['WRITE #1 "VERIFY=end"', "CLOSE #1", "ENDDO"]
    return "\n".join(L) + "\n"


def tpl_entry(name, d, with_flash):
    L = ["; %s_%s.csf - CLI 진입 (CVD.exe 인자로 실행, 끝나면 QUIT)" % (name, "run" if with_flash else "check"),
         "do %s\\%s_config.csf" % (d, name),
         "OPEN #1 &cfg_log /CREATE",
         'WRITE #1 "STEP=start"',
         'WRITE #1 "PROJECT=&cfg_name"',
         'WRITE #1 "MODE=&cfg_mode"',
         "CLOSE #1"]
    if with_flash:
        L += ["do %s\\%s_flash.csf &cfg_mode" % (d, name),
              "OPEN #1 &cfg_log /APPEND",
              'WRITE #1 "STEP=flashed"',
              "CLOSE #1"]
    L += ["do %s\\%s_verify.csf" % (d, name),
          "OPEN #1 &cfg_log /APPEND",
          'WRITE #1 "STEP=done"',
          "CLOSE #1",
          "QUIT"]
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
    pat = re.compile(r'DIALOG\.YESNO "Erase flash memory\?"[^\n]*\n([ \t]*)LOCAL &progflash[^\n]*\n[ \t]*ENTRY &progflash', re.I)
    t, n = pat.subn(lambda m: "; [cvd_flash] 소거 확인 창 제거 (CLI 무인 실행)\n%sLOCAL &progflash\n%s&progflash=TRUE()" % (m.group(1), m.group(1)), t)
    if n != 1:
        die("%s: 소거 확인 창 패턴을 찾지 못했습니다(%d). 원본 구조가 다릅니다." % (os.path.basename(src_file), n))
    notes.append("소거 확인 창 제거")
    t, n = re.subn(r"(OPTION\.JTAGCLOCK)\s+5\.MHz", r"\1 10.MHz   ; [cvd_flash] 5.MHz -> 10.MHz (HE1i 실기 검증본 값)", t)
    if n:
        notes.append("JTAGCLOCK 5.MHz -> 10.MHz")
    return t, notes


def convert_path_cmm(src_file, src_folder_win, dst_win, name):
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
        die("Path.cmm 구조가 예상과 다릅니다 (심볼 로드 %d곳, 소스 경로 삽입 %s)." % (n1, inserted))
    head = "; %s_connect.csf - CN: 연결 + 워치독 해제 + 심볼 + 소스 경로 (원본: Path.cmm)\ndo %s\\%s_config.csf\n" % (name, dst_win, name)
    return head + "\n".join(out)


# ============================================================== 명령: scan / init
def print_scan(d, cands):
    print("[프로젝트 폴더] %s" % d["repo"])
    for k, lab in (("fbl", "FBL"), ("app", "APP(기록)"), ("elf", "ELF(심볼)"), ("hsm", "HSM")):
        print("  %-10s %s" % (lab, d[k] or "없음"))
    print("  %-10s %s" % ("MCU", d["mcu"] or "인식 못함"))
    print("  %-10s %s" % ("과제명 제안", d["name"]))
    print("[복제 원본 후보] %s" % FS_LEGACY)
    for i, c in enumerate(cands, 1):
        print("  %d) %-18s %-16s %s" % (i, c["name"], c["cpu"], "" if c["match"] else "(MCU 계열 다름)"))


def cmd_scan(a):
    d = discover(a.repo or os.getcwd())
    print_scan(d, source_candidates(d["mcu"]))


def cmd_init(a):
    # 1) 프로젝트 폴더: 기본값 = 현재 폴더
    repo = a.repo or ask("[1/4] 프로젝트 폴더 (빌드 저장소)  Enter=기본값", os.getcwd())
    d = discover(repo)
    for k in ("fbl", "app", "elf", "hsm"):
        v = getattr(a, k)
        if v:
            d[k] = os.path.abspath(v)
    cands = source_candidates(d["mcu"])
    print_scan(d, cands)
    missing = [k for k in ("fbl", "app", "elf") if not d[k]]
    if missing:
        die("찾지 못한 이미지: %s  → --%s <경로> 로 지정하세요." % (", ".join(missing), missing[0]))

    # 2) 과제명
    if not sys.stdin.isatty() and not (a.name and a.src):
        die("대화형이 아닌 실행에서는 --name 과 --from 을 지정해야 합니다 (위 인식 결과·후보 참고).")
    name = (a.name or ask("[2/4] 과제명 (영문 대문자·숫자·_)", d["name"]) or "").upper()
    if not NAME_RE.match(name):
        die("과제명 형식이 맞지 않습니다: %s" % name)
    if os.path.exists(proj_fs(name)):
        die("이미 있는 과제입니다: %s (덮어쓰지 않음)" % proj_fs(name))

    # 3) 복제 원본
    src = a.src
    if not src:
        ok = [c for c in cands if c["match"]]
        if not ok:
            die("MCU 계열이 같은 복제 원본이 없습니다. --from 으로 지정하세요.")
        sel = ask("[3/4] 복제 원본 번호 또는 이름", ok[0]["name"])
        if sel and sel.isdigit() and 1 <= int(sel) <= len(cands):
            sel = cands[int(sel) - 1]["name"]
        src = sel
    c = next((x for x in cands if x["name"].lower() == (src or "").lower()), None)
    if not c:
        die("복제 원본이 없습니다: %s" % src)
    if not c["match"] and not a.force_mcu:
        die("복제 원본 CPU(%s)와 저장소 MCU(%s) 계열이 다릅니다. 플래시 주소가 달라질 수 있어 중단합니다." % (c["cpu"], d["mcu"]))
    src_fs = os.path.join(FS_LEGACY, c["name"])
    src_win = wpath(WIN_ROOT, "S32_Config", c["name"])
    host = glob.glob(os.path.join(src_fs, "*HOST*.csf"))
    hsm = glob.glob(os.path.join(src_fs, "*HSM*.csf"))
    if len(host) != 1 or len(hsm) != 1:
        die("원본의 HOST/HSM .csf 가 1개씩이 아닙니다: %s" % src_fs)

    # 4) 확인
    dst_fs, dst_win = proj_fs(name), proj_win(name)
    print("[4/4] 생성 예정")
    print("  폴더   %s" % dst_fs)
    print("  파일   %s_{config,connect,flash,flash_host,flash_hsm,verify,reset,run,check}.csf + 로더" % name)
    print("  원본   %s (CPU %s) — 읽기만 함" % (src_fs, c["cpu"]))
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
    for f in glob.glob(os.path.join(src_fs, "*.out")):
        shutil.copy2(f, dst_fs)
    t, n = convert_flash_csf(host[0], src_win, dst_win)
    wtext(os.path.join(dst_fs, "%s_flash_host.csf" % name), t); notes += ["host: " + x for x in n]
    t, n = convert_flash_csf(hsm[0], src_win, dst_win)
    wtext(os.path.join(dst_fs, "%s_flash_hsm.csf" % name), t); notes += ["hsm: " + x for x in n]
    wtext(os.path.join(dst_fs, "%s_connect.csf" % name),
          convert_path_cmm(os.path.join(src_fs, "Path.cmm"), src_win, dst_win, name))
    rs = os.path.join(src_fs, "Reset.cmm")
    reset = rb(rs).decode(ENC, "replace") if os.path.isfile(rs) else "sys.down\nsys.up\ngo main\nENDDO\n"
    wtext(os.path.join(dst_fs, "%s_reset.csf" % name), "; %s_reset.csf - RE: 리셋 후 main 까지 (원본: Reset.cmm)\n" % name + reset)
    wtext(os.path.join(dst_fs, "%s_flash.csf" % name), tpl_flash(name, dst_win))
    wtext(os.path.join(dst_fs, "%s_verify.csf" % name), tpl_verify(name, dst_win))
    wtext(os.path.join(dst_fs, "%s_run.csf" % name), tpl_entry(name, dst_win, True))
    wtext(os.path.join(dst_fs, "%s_check.csf" % name), tpl_entry(name, dst_win, False))
    cfg = {"name": name, "dir": dst_win, "cpu": c["cpu"], "mode": "IMAGE", "repo": d["repo"],
           "fbl": d["fbl"], "app": d["app"], "elf": d["elf"], "hsm": d["hsm"] or "",
           "src": d["repo"], "log": wpath(dst_win, "%s_result.log" % name), "source": c["name"]}
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
def update_cfg(a):
    c = read_cfg(a.name)
    if a.rescan:
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
    need = {"IMAGE": ("fbl", "app"), "HSM": ("hsm",), "ALL": ("fbl", "app", "hsm")}.get(c["mode"], ("fbl", "app"))
    for k in need + ("elf",):
        if not c[k] or not os.path.isfile(c[k]):
            die("%s 파일이 없습니다: %s" % (k.upper(), c[k] or "(미지정)"))
    pts = write_cfg(c)
    return c, pts


def run_cvd(entry_fs, log_fs, timeout, entry_ext):
    if not os.path.isfile(CVD_EXE):
        die("CVD 실행 파일이 없습니다: %s" % CVD_EXE)
    if entry_ext == "cmm":                      # .csf 를 인자로 못 받는 경우 대비
        alt = entry_fs[:-4] + ".cmm"
        shutil.copyfile(entry_fs, alt)
        entry_fs = alt
    if os.path.isfile(log_fs):
        os.remove(log_fs)
    proc = subprocess.Popen([CVD_EXE, entry_fs], cwd=os.path.dirname(CVD_EXE))
    t0, why = time.time(), "timeout"
    while time.time() - t0 < timeout:
        if os.path.isfile(log_fs) and "STEP=done" in rb(log_fs).decode(ENC, "replace"):
            why = "done"
            break
        if proc.poll() is not None:
            why = "exited"
            break
        time.sleep(1.0)
    time.sleep(1.0)
    if proc.poll() is None:
        try:
            proc.terminate()
        except OSError:
            pass
    return why, int(time.time() - t0)


def judge(log_fs, with_flash):
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
    if with_flash and "flashed" not in steps:
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
    c, pts = update_cfg(a)
    d = proj_fs(a.name)
    print("[%s] 모드 %s" % (a.name, c["mode"]) if with_flash else "[%s] 검증만" % a.name)
    for k in ("fbl", "app", "hsm"):
        if with_flash and (k != "hsm" or c["mode"] in ("HSM", "ALL")) and (k == "hsm" or c["mode"] in ("IMAGE", "ALL")):
            print("  %-4s %s" % (k.upper(), c[k]))
    if with_flash and c["mode"] in ("HSM", "ALL"):
        print("  (HSM 영역은 CM4 에서 읽을 수 없어 검증은 FBL·APP 지점으로 한다)")
    entry = os.path.join(d, "%s_%s.csf" % (a.name, "run" if with_flash else "check"))
    log_fs = os.path.join(d, "%s_result.log" % a.name)
    why, sec = run_cvd(entry, log_fs, a.timeout, a.entry)
    print("  CVD 종료: %s, %d초" % (why, sec))
    code = judge(log_fs, with_flash)
    if why == "timeout" and code != EXIT_OK:
        code = EXIT_TIMEOUT
    sys.exit(code)


def cmd_list(a):
    ps = list_projects()
    if not ps:
        print("생성된 과제가 없습니다: %s" % FS_PROJECTS)
    for n, cpu in ps:
        c = read_cfg(n)
        print("%-16s %-14s 원본 %-16s 저장소 %s" % (n, cpu, c["source"], c["repo"]))


# ============================================================== main
def main():
    ap = argparse.ArgumentParser(description="CVD CLI 다운로드 + 검증 (v%s)" % VERSION)
    sp = ap.add_subparsers(dest="cmd")

    p = sp.add_parser("init", help="과제 폴더 생성 + loadfile.csf 등록")
    p.add_argument("--repo", help="프로젝트 폴더 (기본: 현재 폴더)")
    p.add_argument("--name", help="과제명 (예: JG_WPC)")
    p.add_argument("--from", dest="src", help="복제 원본 (S32_Config 아래 폴더명)")
    for k in ("fbl", "app", "elf", "hsm"):
        p.add_argument("--" + k, help="%s 경로 직접 지정" % k.upper())
    p.add_argument("--yes", action="store_true", help="확인 생략")
    p.add_argument("--dry-run", action="store_true", help="생성하지 않고 계획만 출력")
    p.add_argument("--force-mcu", action="store_true", help="MCU 계열 불일치 무시 (권장하지 않음)")

    p = sp.add_parser("scan", help="인식 결과·복제 후보만 출력")
    p.add_argument("--repo")

    for cmd in ("flash", "verify"):
        p = sp.add_parser(cmd)
        p.add_argument("--name", required=True)
        if cmd == "flash":
            p.add_argument("--mode", choices=MODES, help="IMAGE(기본) / HSM / ALL")
            for k in ("fbl", "app", "elf", "hsm"):
                p.add_argument("--" + k)
            p.add_argument("--rescan", action="store_true", help="저장소에서 최신 이미지를 다시 찾음")
        p.add_argument("--timeout", type=int, default=300)
        p.add_argument("--entry", choices=("csf", "cmm"), default="csf", help="CLI 진입 파일 확장자")

    sp.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "init":
        cmd_init(a)
    elif a.cmd == "scan":
        cmd_scan(a)
    elif a.cmd == "flash":
        cmd_flash(a, True)
    elif a.cmd == "verify":
        a.rescan = False
        cmd_flash(a, False)
    elif a.cmd == "list":
        cmd_list(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
```