# -*- coding: utf-8 -*-
"""
cvdsetup.py - CVD(CodeViser) 프로젝트 설정 생성기

저장소(psu_app)에서 차종/바이너리/MCU 를 자동 인식하고,
검증된 템플릿을 복제해 차종별 CVD 설정을 만든다.

  survey   설치/도너/등록 현황
  plan     저장소 인식 결과와 변경 예정 내역 (파일 변경 없음)
  create   설정 생성 + loadfile.cmm 등록
  verify   생성 결과 검증
  images   loadimage.txt / Path.cmm ELF 경로만 갱신
"""
import argparse
import glob
import os
import re
import shutil
import sys
import time

# 기본은 이 PC 의 CVD 설정 폴더. 시험용으로만 CVD_S32_CONFIG 로 덮어쓴다.
S32 = os.environ.get("CVD_S32_CONFIG", r"C:\JnDTech\CVI\CVD\S32_Config")
LOADFILE = "loadfile.cmm"
BASE_DONOR = "_BASE_CYT2BL_Dual"
REF_BLOCK = "HE1i_PSU_DUAL"          # loadfile.cmm 블록 구조 참조용
REF_FOLDER = "HE1i_PSU_Dual"
TEXT_EXT = ('.cmm', '.csf', '.txt')
SEP = b';' + b'#' * 128
GRID = [(2.0, 14.0), (17.0, 14.0), (32.0, 18.0), (51.0, 18.0)]
ROWS = [1.0, 2.0, 3.0, 4.0, 5.0]
TOKENS = ("@@APP_ELF@@", "@@SRC_PATH@@", "@@FBL@@", "@@APP_WRITING@@", "@@HSM@@")
README_NAME = "읽어보세요.txt"


def label(project):
    """Project Select 에 찍힐 이름. 차종 표기는 그대로 두고 마지막 칸만 대문자.

    HE1i_PSU_Dual -> HE1i_PSU_DUAL   (HE1I_PSU_DUAL 이 아니다)
    """
    if "_" in project:
        head, tail = project.rsplit("_", 1)
        return head + "_" + tail.upper()
    return project.upper()


def die(msg):
    print("[중단] " + msg)
    sys.exit(1)


def rb(p):
    with open(p, 'rb') as f:
        return f.read()


def wb(p, d):
    with open(p, 'wb') as f:
        f.write(d)


# ---------------------------------------------------------------- 저장소 인식
def discover(repo):
    repo = os.path.abspath(repo)
    if os.path.basename(repo).lower() != "psu_app":
        cand = os.path.join(repo, "psu_app")
        if os.path.isdir(cand):
            repo = cand
    if not os.path.isdir(repo):
        die("저장소 경로가 없습니다: " + repo)

    d = {"repo": repo}

    hsm = sorted(glob.glob(os.path.join(repo, "References", "01_HSM_Framework", "*.sre")))
    if not hsm:
        die("HSM 이미지를 찾지 못했습니다: References\\01_HSM_Framework\\*.sre")
    d["hsm"] = hsm[0]
    m = re.search(r'rel_([A-Za-z0-9]+)_([A-Za-z0-9]+)_V', os.path.basename(hsm[0]))
    if not m:
        die("HSM 파일명에서 차종을 읽지 못했습니다: " + os.path.basename(hsm[0]))
    d["model"], d["ctrl"] = m.group(1), m.group(2)      # HE1i, PSU  (정식 표기)

    specs = sorted(os.path.basename(x)
                   for x in glob.glob(os.path.join(repo, "Debug", "OEUK_*"))
                   if os.path.isdir(x))
    if not specs:
        die("Debug\\OEUK_* 폴더가 없습니다. 빌드 산출물을 먼저 받으세요 (git pull).")
    d["spec"] = specs[0]
    d["spec_all"] = specs

    dbg = os.path.join(repo, "Debug", d["spec"])
    w = sorted(glob.glob(os.path.join(dbg, "*_Writing.s19")))
    e = sorted(glob.glob(os.path.join(dbg, "*.elf")))
    if not w:
        die("APP 라이팅 이미지가 없습니다: %s\\*_Writing.s19" % dbg)
    if not e:
        die("APP ELF 가 없습니다: %s\\*.elf" % dbg)
    d["app_writing"], d["app_elf"] = w[0], e[0]

    f = sorted(glob.glob(os.path.join(repo, "References", "02_Fbl_Binary", d["spec"], "*.sre")))
    if not f:
        f = sorted(glob.glob(os.path.join(repo, "References", "02_Fbl_Binary", "*", "*.sre")))
    if not f:
        die("FBL 이미지를 찾지 못했습니다: References\\02_Fbl_Binary\\...\\*.sre")
    d["fbl"] = f[0]

    d["mcu"] = detect_mcu(repo, hsm[0])
    d["project"] = "%s_%s_Dual" % (d["model"], d["ctrl"])
    return d


def detect_mcu(repo, hsmfile):
    cnt = {}
    for root, _, files in os.walk(os.path.join(repo, "Configuration")):
        for fn in files:
            if not fn.lower().endswith(('.arxml', '.h')):
                continue
            try:
                t = rb(os.path.join(root, fn)).decode('latin-1')
            except Exception:
                continue
            for mm in re.findall(r'CYT[0-9][A-Z0-9]{3,8}', t):
                cnt[mm] = cnt.get(mm, 0) + 1
    if cnt:
        # 가장 구체적인 것(긴 것) 우선, 같으면 많이 나온 것
        return sorted(cnt.items(), key=lambda kv: (len(kv[0]), kv[1]), reverse=True)[0][0]
    m = re.search(r'(CYT2[A-Z0-9]+)', os.path.basename(hsmfile))
    return m.group(1) if m else "UNKNOWN"


# ---------------------------------------------------------------- 도너
def donor_candidates():
    out = []
    for name in sorted(os.listdir(S32)):
        p = os.path.join(S32, name)
        if not os.path.isdir(p) or name.startswith("S32_Config"):
            continue
        csf = len({x.lower() for x in glob.glob(os.path.join(p, "*.csf"))}
                  | {x.lower() for x in glob.glob(os.path.join(p, "*.CSF"))})
        loaders = len(glob.glob(os.path.join(p, "TVII-B-*.out")))
        if csf:
            out.append((name, csf, loaders))
    return out


def pick_donor(mcu, bank):
    if (bank == "dual" and mcu.upper().startswith("CYT2BL")
            and os.path.isdir(os.path.join(S32, BASE_DONOR))):
        return BASE_DONOR
    return None


# ---------------------------------------------------------------- loadfile
def loadfile_path():
    return os.path.join(S32, LOADFILE)


def registered_projects(raw=None):
    raw = raw if raw is not None else rb(loadfile_path())
    return [m.decode('latin-1') for m in re.findall(rb'CHOOSEBOX\s+"([^"]+)"', raw)]


def used_slots(raw):
    t = raw.decode('latin-1')
    s = set()
    for m in re.finditer(r'POS\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\n\s*LN\.\w+:\s+CHOOSEBOX', t):
        s.add((float(m.group(1)), float(m.group(2))))
    return s


def free_slot(raw):
    used = used_slots(raw)
    for y in ROWS:
        for x, w in reversed(GRID):          # 넓은 열(w=18) 우선
            if (x, y) not in used:
                return x, y, w
    return None


# ---------------------------------------------------------------- 출력
def show_discovery(d, donor, slot):
    def rel(p):
        return os.path.relpath(p, d["repo"])
    extra = "   (후보 %s)" % d["spec_all"] if len(d["spec_all"]) > 1 else ""
    print("### 저장소 인식 결과")
    print("  저장소        %s" % d["repo"])
    print("  차종 / 제어기 %s / %s        (HSM 파일명 기준 정식 표기)" % (d["model"], d["ctrl"]))
    print("  사양 폴더     %s%s" % (d["spec"], extra))
    print("  MCU           %s" % d["mcu"])
    print()
    print("  FBL           %s" % rel(d["fbl"]))
    print("  APP(라이팅)   %s" % rel(d["app_writing"]))
    print("  APP(심볼)     %s" % rel(d["app_elf"]))
    print("  HSM           %s" % rel(d["hsm"]))
    print()
    print("### 생성 대상")
    print("  프로젝트      %s" % d["project"])
    print("  폴더          %s" % os.path.join(S32, d["project"]))
    print("  도너          %s" % (donor or "<없음 - 지정 필요>"))
    if slot:
        print("  Project Select 배치   POS %s %s %s 1." % (slot[0], slot[1], slot[2]))


# ---------------------------------------------------------------- create
def substitute(dst, donor, project):
    n = 0
    for fn in sorted(os.listdir(dst)):
        if not fn.lower().endswith(TEXT_EXT):
            continue
        p = os.path.join(dst, fn)
        d = rb(p)
        c = d.count(donor.encode('latin-1'))
        if c:
            wb(p, d.replace(donor.encode('latin-1'), project.encode('latin-1')))
            n += c
    return n


def fix_loader_paths(dst):
    """&FLASH_LOADER 경로를 모두 대상 폴더 기준 절대경로로 다시 쓴다.

    .csf 에는 S32 루트까지 포함한 절대경로가 박혀 있어 폴더명만 치환하면
    도너가 만들어진 당시의 루트가 남는다. 상대 파일명도 CVD 작업 디렉터리에
    따라 해석이 달라진다. 둘 다 여기서 없앤다.
    """
    n = 0
    for fn in sorted(os.listdir(dst)):
        if not fn.lower().endswith('.csf'):
            continue
        p = os.path.join(dst, fn)
        d = rb(p)

        def sub(m):
            name = os.path.basename(m.group(1).replace("\\", "/"))
            if not os.path.isfile(os.path.join(dst, name)):
                return m.group(0)          # 폴더에 없는 로더는 건드리지 않는다
            return '&FLASH_LOADER="%s"' % os.path.join(dst, name)

        t = d.decode('cp949', 'replace')
        t2, k = re.subn(r'&FLASH_LOADER="([^"]+)"', sub, t)
        if k:
            wb(p, t2.encode('cp949', 'replace'))
            n += k
    return n


def fill_tokens(dst, info):
    rep = {
        "@@APP_ELF@@":     info["app_elf"],
        "@@SRC_PATH@@":    info["repo"],
        "@@FBL@@":         info["fbl"],
        "@@APP_WRITING@@": info["app_writing"],
        "@@HSM@@":         info["hsm"],
    }
    for fn in sorted(os.listdir(dst)):
        if not fn.lower().endswith(TEXT_EXT):
            continue
        p = os.path.join(dst, fn)
        d = rb(p)
        for k, v in rep.items():
            d = d.replace(k.encode('latin-1'), v.encode('cp949', 'replace'))
        wb(p, d)
    left = []
    for fn in os.listdir(dst):
        if fn.lower().endswith(TEXT_EXT):
            d = rb(os.path.join(dst, fn))
            for t in TOKENS:
                if t.encode('latin-1') in d:
                    left.append("%s : %s" % (fn, t))
    return left


def find_ref_block(parts, cpu_prefix):
    """구조가 온전하고 CPU 계열이 맞는 블록을 참조로 고른다.

    이름으로 찾으면 그 프로젝트가 지워졌을 때 스킬이 멈춘다. 그래서 조건으로
    찾는다.

      - Path Set / Program DownLoad 툴버튼이 있을 것
        (Path Set 이 빠진 블록을 복제하면 Path.cmm 을 호출할 수 없다)
      - sys.CPU 가 대상 MCU 계열과 같을 것
        (CYT2B9 블록을 복제하면 CPU 가 엉뚱하게 잡힌다)

    반환: (인덱스, 블록내용, 그 블록이 쓰는 폴더명, 그 블록의 라벨)
    """
    pref = ('"%s"' % REF_BLOCK).encode('latin-1')
    cands = []
    for i, c in enumerate(parts):
        if b'"Path Set"' not in c or b'"Program DownLoad"' not in c:
            continue
        cpu = re.search(rb'sys\.CPU\s+([A-Za-z0-9_+-]+)', c)
        if not cpu or not cpu.group(1).decode('latin-1').upper().startswith(cpu_prefix.upper()):
            continue
        m = re.search(rb'S32_Config\\([^\\"]+)\\loadimage\.cmm', c)
        n = re.search(rb'CHOOSEBOX\s+"([^"]+)"', c)
        if m and n:
            cands.append((i, c, m.group(1).decode('latin-1'), n.group(1).decode('latin-1')))
    if not cands:
        die("loadfile.cmm 에서 %s 계열이고 Path Set 툴버튼을 갖춘 참조 블록을 "
            "찾지 못했습니다. --donor 로 쓸 만한 설정이 등록되어 있어야 합니다." % cpu_prefix)
    for cand in cands:
        if pref in cand[1]:
            return cand
    return cands[0]


def register(project, slot, cpu_prefix):
    p = loadfile_path()
    raw = rb(p)
    upper = label(project)
    if ('"%s"' % upper).encode('latin-1') in raw:
        die("loadfile.cmm 에 %s 가 이미 등록되어 있습니다." % upper)

    parts = raw.split(SEP)
    i, src, ref_folder, ref_label = find_ref_block(parts, cpu_prefix)
    idx = [i]

    # 라벨을 먼저 바꾼다. 라벨과 폴더명이 같은 블록(SX2_MKBD_Dual 등)에서
    # 폴더를 먼저 치환하면 라벨까지 덩달아 바뀌어 대소문자가 어긋난다.
    new = src.replace(('"%s"' % ref_label).encode('latin-1'),
                      ('"%s"' % upper).encode('latin-1'))
    new = new.replace(ref_folder.encode('latin-1'), project.encode('latin-1'))
    # 파일의 기존 표기와 같은 형식으로 쓴다.  51.0 이 아니라 51.
    fmt = lambda v: ("%d." % v) if float(v).is_integer() else ("%s" % v)
    new = re.sub(rb'POS\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+1\.',
                 ("POS %s %s %s 1." % (fmt(slot[0]), fmt(slot[1]), fmt(slot[2]))).encode('latin-1'),
                 new, count=1)

    bak = p + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copyfile(p, bak)
    parts.insert(idx[0] + 1, new)
    wb(p, SEP.join(parts))
    return bak


def write_readme(dst, info, donor, assets):
    tpl = os.path.join(assets, "readme_template.txt")
    if not os.path.isfile(tpl):
        return None
    with open(tpl, encoding='utf-8') as f:
        t = f.read()

    def rel(p):
        return os.path.relpath(p, info["repo"])
    pairs = {
        "{PROJECT}": info["project"], "{UPPER}": label(info["project"]),
        "{MODEL}": info["model"], "{CTRL}": info["ctrl"], "{MCU}": info["mcu"],
        "{DONOR}": donor, "{FOLDER}": os.path.join(S32, info["project"]),
        "{REPO}": info["repo"], "{DATE}": time.strftime("%Y-%m-%d"),
        "{FBL}": rel(info["fbl"]), "{APPW}": rel(info["app_writing"]),
        "{APPE}": rel(info["app_elf"]), "{HSM}": rel(info["hsm"]),
    }
    for k, v in pairs.items():
        t = t.replace(k, v)
    out = os.path.join(dst, README_NAME)
    with open(out, "w", encoding="cp949", errors="replace", newline="") as f:
        f.write(t.replace("\n", "\r\n"))
    return out


# ---------------------------------------------------------------- verify
def verify(project, donor=None):
    dst = os.path.join(S32, project)
    ok = True
    print("### 검증 : %s" % project)
    if not os.path.isdir(dst):
        die("폴더가 없습니다: " + dst)

    if donor:
        # 안내문은 도너 이름을 일부러 기록하므로 제외한다.
        left = 0
        for fn in os.listdir(dst):
            if fn == README_NAME or not fn.lower().endswith(TEXT_EXT):
                continue
            left += rb(os.path.join(dst, fn)).count(donor.encode('latin-1'))
        print("  %-40s %s" % ("도너명 잔여 참조", "0건" if left == 0 else "%d건  <-- 문제" % left))
        ok = ok and (left == 0)

    left = []
    for fn in os.listdir(dst):
        if fn.lower().endswith(TEXT_EXT):
            d = rb(os.path.join(dst, fn))
            for t in TOKENS:
                if t.encode('latin-1') in d:
                    left.append("%s:%s" % (fn, t))
    print("  %-40s %s" % ("치환 토큰 잔여",
                          "없음" if not left else ", ".join(left) + "  <-- 문제"))
    ok = ok and not left

    li = os.path.join(dst, "loadimage.txt")
    lines = []
    if os.path.isfile(li):
        with open(li, encoding='cp949', errors='replace') as f:
            lines = f.read().splitlines()
    for name, i in (("FBL", 1), ("APP(_Writing.s19)", 2), ("HSM", 3)):
        pth = lines[i].strip() if len(lines) > i else ""
        good = bool(pth) and os.path.isfile(pth)
        print("  %-40s %s" % ("이미지 " + name, "OK" if good else "없음  <-- 문제"))
        print("      %s" % (pth or "-"))
        ok = ok and good

    pc = rb(os.path.join(dst, "Path.cmm")).decode('cp949', 'replace')
    m = re.search(r'Data\.LOAD\.auto\s+"([^"]+)"', pc)
    good = bool(m) and m.group(1).lower().endswith(".elf") and os.path.isfile(m.group(1))
    print("  %-40s %s" % ("Path.cmm 심볼 ELF", "OK" if good else "확인 필요  <-- 문제"))
    print("      %s" % (m.group(1) if m else "-"))
    ok = ok and good

    bad = []
    for fn in os.listdir(dst):
        if fn.lower().endswith('.csf'):
            t = rb(os.path.join(dst, fn)).decode('cp949', 'replace')
            for mm in re.findall(r'&FLASH_LOADER="([^"]+)"', t):
                if os.path.isabs(mm) and os.path.normcase(os.path.dirname(mm)) != os.path.normcase(dst):
                    bad.append("%s -> %s" % (fn, mm))
    loaders = glob.glob(os.path.join(dst, "TVII-B-*.out"))
    print("  %-40s %s" % ("플래시 로더 파일",
                          "%d개" % len(loaders) if loaders else "없음  <-- 문제"))
    print("  %-40s %s" % ("로더 외부 폴더 참조",
                          "없음" if not bad else "%d건  <-- 문제" % len(bad)))
    for b in bad:
        print("      " + b)
    ok = ok and bool(loaders) and not bad

    n = registered_projects().count(label(project))
    print("  %-40s %s" % ("loadfile.cmm 등록", "1건" if n == 1 else "%d건  <-- 문제" % n))
    ok = ok and (n == 1)

    print()
    print("  => %s" % ("전체 통과" if ok else "문제 있음 - 위 항목 확인"))
    return ok


# ---------------------------------------------------------------- commands
def cmd_survey(a):
    print("### CVD 설치")
    print("  S32_Config   %s   %s" % (S32, "있음" if os.path.isdir(S32) else "없음"))
    exe = r"C:\JnDTech\CVI\CVD\Bin\CVD.exe"
    print("  CVD.exe      %s   %s" % (exe, "있음" if os.path.isfile(exe) else "없음"))
    print()
    print("### 도너 후보 (csf 보유 폴더)")
    for name, csf, loaders in donor_candidates():
        tag = "  <- 기본 템플릿" if name == BASE_DONOR else ""
        print("  %-20s csf %d  로더 %d%s" % (name, csf, loaders, tag))
    print()
    print("### loadfile.cmm 등록 프로젝트")
    for i, p in enumerate(registered_projects(), 1):
        print("  %2d  %s" % (i, p))
    s = free_slot(rb(loadfile_path()))
    print()
    print("  다음 빈 배치 슬롯 : %s" % ("POS %s %s %s 1." % s if s else "없음 (격자 가득참)"))


def cmd_plan(a):
    d = discover(a.repo)
    if a.name:
        d["project"] = a.name
    donor = a.donor or pick_donor(d["mcu"], a.bank)
    slot = free_slot(rb(loadfile_path()))
    show_discovery(d, donor, slot)
    print()
    if not donor:
        print("### 도너를 정해야 합니다")
        print("  MCU %s / %s뱅크 에 맞는 기본 템플릿이 없습니다." % (d["mcu"], a.bank))
        print("  --donor 로 직접 지정하세요. 후보:")
        for name, _c, _l in donor_candidates():
            print("    %s" % name)
        return
    dst = os.path.join(S32, d["project"])
    print("### 수행 예정")
    print("  1. %s  ->  %s   복제" % (donor, d["project"]))
    print("  2. 폴더명 치환 (.cmm/.csf/.txt)")
    print("  3. 토큰 5종 채움 (ELF/소스경로/FBL/APP/HSM)")
    print("  4. loadfile.cmm 에 %s 블록 추가 (백업 후, 추가만)" % label(d["project"]))
    print("  5. 읽어보세요.txt 생성")
    print()
    print("  기존 폴더 존재 : %s" % ("예  <-- create 는 중단됩니다"
                                     if os.path.isdir(dst) else "아니오"))
    print("  파일은 변경하지 않았습니다. 진행하려면 create 를 쓰세요.")


def cmd_create(a):
    d = discover(a.repo)
    if a.name:
        d["project"] = a.name
    donor = a.donor or pick_donor(d["mcu"], a.bank)
    if not donor:
        die("도너를 --donor 로 지정하세요. (plan 으로 후보 확인)")
    src = os.path.join(S32, donor)
    dst = os.path.join(S32, d["project"])
    if not os.path.isdir(src):
        die("도너 폴더가 없습니다: " + src)
    if os.path.isdir(dst):
        die("대상 폴더가 이미 있습니다: " + dst)
    slot = free_slot(rb(loadfile_path()))
    if not slot:
        die("Project Select 격자에 빈 자리가 없습니다. loadfile.cmm 을 손봐야 합니다.")

    show_discovery(d, donor, slot)
    print()
    if not a.yes:
        die("확인 후 --yes 를 붙여 다시 실행하세요.")

    shutil.copytree(src, dst)
    rm = os.path.join(dst, "README_TEMPLATE.txt")
    if os.path.isfile(rm):
        os.remove(rm)
    n = substitute(dst, donor, d["project"])
    ln = fix_loader_paths(dst)
    left = fill_tokens(dst, d)
    if left:
        die("채우지 못한 토큰: " + ", ".join(left))
    bak = register(d["project"], slot, d["mcu"][:6])
    rd = write_readme(dst, d, donor, a.assets)

    print("### 생성 완료")
    print("  폴더          %s" % dst)
    print("  폴더명 치환   %d곳" % n)
    print("  로더 경로     %d곳을 이 폴더 기준으로 재지정" % ln)
    print("  loadfile.cmm  %s 등록 / 백업 %s" % (label(d["project"]), os.path.basename(bak)))
    if rd:
        print("  안내문        %s" % os.path.basename(rd))
    print()
    verify(d["project"], donor)


def cmd_verify(a):
    verify(a.name, a.donor)


def cmd_images(a):
    d = discover(a.repo)
    project = a.name or d["project"]
    dst = os.path.join(S32, project)
    if not os.path.isdir(dst):
        die("폴더가 없습니다: " + dst)
    li = os.path.join(dst, "loadimage.txt")
    state = "4"
    if os.path.isfile(li):
        with open(li, encoding='cp949', errors='replace') as f:
            old = f.read().splitlines()
        if old:
            state = old[0]
    with open(li, "w", encoding="cp949", errors="replace", newline="") as f:
        f.write("\r\n".join([state, d["fbl"], d["app_writing"], d["hsm"]]) + "\r\n")
    p = os.path.join(dst, "Path.cmm")
    t = rb(p)
    t = re.sub(rb'Data\.LOAD\.auto\s+"[^"]+"\s*/\s*nocode',
               ('Data.LOAD.auto "%s" / nocode' % d["app_elf"]).encode('cp949', 'replace'),
               t, count=1)
    wb(p, t)
    print("### 이미지 목록 갱신 : %s" % project)
    for k in ("fbl", "app_writing", "hsm", "app_elf"):
        print("  %-12s %s" % (k, d[k]))
    print()
    verify(project)


# ---------------------------------------------------------------- run
CVD_EXE = os.environ.get("CVD_EXE", r"C:\JnDTech\CVI\CVD\Bin\CVD.exe")

GUIDE_STEPS = [
    ("0", "전원 · IGN 인가",
     "B+ 만으로는 슬립에 머문다. CVD 포드는 타겟에 전원을 주지 않는다"),
    ("1", "툴바 빨간 PS → 프로젝트 선택",
     "버튼에는 2글자만 찍힌다. 툴바가 없으면 명령창에 CD.DO <S32>\\loadfile.cmm"),
    ("2", "빨간 PD → Image&Hsm → file load start",
     "Image&Hsm 을 눌러야 세 칸이 산다. APP 이 _Writing.s19 인지 확인"),
    ("3", "Erase flash memory? 확인창",
     "두 번 뜬다. 보드 이력을 모르면 둘 다 Yes (DTC·학습값 초기화)"),
    ("4", "결과 확인",
     "Reset Target 이 두 번. SYSDOWN 은 정상 종료이지 실패가 아니다"),
    ("5", "PA → RE 순서로 동작 확인",
     "순서를 바꾸면 심볼이 없어 실패한다. main 에서 멈추면 정상"),
    ("6", "디버거를 떼고 전원만으로 확인",
     "RE 로 멈춘 상태는 CPU 정지 상태라 CAN 이 나가지 않는다"),
]

CHECK_CMM = '''; 자동 생성 (cvd-project-setup) - 읽기 전용 연결 확인
; 보드에 아무것도 쓰지 않는다. 플래시를 지우지도 기록하지도 않는다.
local &log
&log="@@LOG@@"

OPEN #1 &log /CREATE
WRITE #1 "STEP=start"
WRITE #1 "PROJECT=@@PROJECT@@"
CLOSE #1

; 프로젝트의 Path.cmm 을 그대로 호출한다.
; CPU 설정 / 연결 / 심볼 로드까지 사람이 PA 로 검증한 경로다.
do @@DST@@\\Path.cmm

OPEN #1 &log /APPEND
WRITE #1 "STEP=connected"
CLOSE #1

; FBL 벡터 테이블을 읽는다. 0x10028000 = 초기 SP, 0x10028004 = 리셋 벡터.
; HSM 영역(0x10000000)은 CM4 에서 접근되지 않으므로 읽지 않는다.
local &sp &rv
&sp=Data.Long(AD:0x10028000)
&rv=Data.Long(AD:0x10028004)

OPEN #1 &log /APPEND
WRITE #1 "FBL_SP=&sp"
WRITE #1 "FBL_RESET=&rv"
WRITE #1 "STEP=done"
CLOSE #1

QUIT
'''


def _run_cvd(cmm_path, log_path, timeout):
    """CVD 를 스크립트와 함께 띄우고 로그 완성 또는 종료까지 기다린다."""
    import subprocess
    if not os.path.isfile(CVD_EXE):
        die("CVD 실행 파일이 없습니다: " + CVD_EXE)
    if os.path.isfile(log_path):
        os.remove(log_path)
    proc = subprocess.Popen([CVD_EXE, cmm_path], cwd=os.path.dirname(CVD_EXE))
    t0 = time.time()
    why = "timeout"
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            why = "exited"
            break
        if os.path.isfile(log_path):
            try:
                with open(log_path, encoding='cp949', errors='replace') as f:
                    if "STEP=done" in f.read():
                        why = "done"
                        break
            except Exception:
                pass
        time.sleep(1.0)
    if proc.poll() is None:
        try:
            proc.terminate()      # QUIT 이 늦거나 안 돌 때를 대비해 정리
        except Exception:
            pass
    return why, int(time.time() - t0)


def cmd_run(a):
    if a.mode == "guide":
        print("### 첫 라이팅 안내 (사람이 GUI 에서 수행)")
        for n, what, why in GUIDE_STEPS:
            print("  %s) %s" % (n, what))
            print("       %s" % why)
        print()
        print("  자동 연결 확인은  run --mode check  로 한다.")
        return

    d = discover(a.repo)
    project = a.name or d["project"]
    dst = os.path.join(S32, project)
    if not os.path.isdir(dst):
        die("설정 폴더가 없습니다: %s  (먼저 create 를 실행하세요)" % dst)

    if a.mode == "auto":
        print("[미구현] --mode auto 는 아직 없습니다.")
        print()
        print("  벤더 스크립트(cyt2blx_*_HAE_release.csf)의 eraseFlash 안에")
        print('  DIALOG.YESNO "Erase flash memory?" 가 있어 무인 실행이 거기서 멈춘다.')
        print("  우회하려면 벤더 스크립트의 파생본을 만들어야 하므로,")
        print("  --mode check 가 실기에서 충분히 검증된 뒤에 별도로 만든다.")
        print()
        print("  지금은  --mode check (읽기 전용)  또는  --mode guide  를 쓴다.")
        return

    work = os.path.join(dst, "_autorun")
    os.makedirs(work, exist_ok=True)
    cmm = os.path.join(work, "check.cmm")
    log = os.path.join(work, "check_log.txt")
    body = (CHECK_CMM.replace("@@LOG@@", log)
                     .replace("@@PROJECT@@", project)
                     .replace("@@DST@@", dst))
    with open(cmm, "w", encoding="cp949", errors="replace", newline="") as f:
        f.write(body.replace("\n", "\r\n"))

    print("### 읽기 전용 연결 확인 : %s" % project)
    print("  스크립트  %s" % cmm)
    print("  CVD       %s" % CVD_EXE)
    print("  보드에 아무것도 쓰지 않습니다. 기다리는 중...")
    print()
    why, secs = _run_cvd(cmm, log, a.timeout)
    tail = {"done": "", "exited": "   (CVD 가 스스로 종료)",
            "timeout": "   <-- 시간 초과로 CVD 를 강제 종료함"}[why]

    lines = []
    if os.path.isfile(log):
        with open(log, encoding='cp949', errors='replace') as f:
            lines = [x.strip() for x in f if x.strip()]
    kv = dict(x.split("=", 1) for x in lines if "=" in x)
    step = kv.get("STEP", "")

    print("  경과 %d초%s" % (secs, tail))
    print()
    print("### 로그")
    for x in lines:
        print("  " + x)
    if not lines:
        print("  (비어 있음)")
    print()
    print("### 판정")
    if not lines:
        print("  실패 — 스크립트가 실행되지 않았습니다. CVD 경로와 .cmm 문법을 확인하세요.")
    elif step == "start":
        print("  실패 — Path.cmm 에서 멈췄습니다. 타겟 연결 단계입니다.")
        print("  전원 / IGN / 포드 케이블 / JTAG 클럭 순으로 확인하세요.")
        print("  (references/troubleshooting.md 의 0xEC2 항목)")
    elif step in ("connected", "done"):
        print("  연결 성공 — CPU 설정과 심볼 로드까지 통과했습니다.")
        if step == "done":
            sp, rv = kv.get("FBL_SP", ""), kv.get("FBL_RESET", "")
            print("  FBL 벡터 테이블 (0x10028000)")
            print("    초기 SP    %s" % (sp or "-"))
            print("    리셋 벡터  %s" % (rv or "-"))
            try:
                spv = int(sp, 16)
                rvv = int(rv, 16)
            except Exception:
                spv = rvv = 0
            if spv in (0, 0xFFFFFFFF) or rvv in (0, 0xFFFFFFFF):
                print("  => 플래시가 비어 있습니다. FBL 이 올라가 있지 않습니다.")
            elif 0x08000000 <= spv < 0x09000000 and 0x10028000 <= (rvv & ~1) < 0x10200000 and (rvv & 1):
                print("  => 정상. SP 는 SRAM, 리셋 벡터는 FBL 영역을 가리키는 Thumb 주소입니다.")
            else:
                print("  => 값이 예상 범위를 벗어납니다. 라이팅 상태를 확인하세요.")
        else:
            print("  메모리 읽기 단계에서 멈췄습니다. 주소나 접근 권한을 확인하세요.")
    else:
        print("  판정 불가 — STEP=%s" % (step or "없음"))


def main():
    ap = argparse.ArgumentParser(prog="cvdsetup")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("survey").set_defaults(func=cmd_survey)

    assets_default = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

    for name, fn in (("plan", cmd_plan), ("create", cmd_create)):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True, help="psu_app 경로")
        p.add_argument("--name", help="프로젝트 폴더명 (기본: <차종>_<제어기>_Dual)")
        p.add_argument("--donor", help="도너 폴더명")
        p.add_argument("--bank", choices=["dual", "single"], default="dual")
        p.add_argument("--assets", default=assets_default)
        if name == "create":
            p.add_argument("--yes", action="store_true")
        p.set_defaults(func=fn)

    p = sub.add_parser("verify")
    p.add_argument("--name", required=True)
    p.add_argument("--donor")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("images")
    p.add_argument("--repo", required=True)
    p.add_argument("--name")
    p.set_defaults(func=cmd_images)

    p = sub.add_parser("run")
    p.add_argument("--mode", choices=["guide", "check", "auto"], default="guide",
                   help="guide=사람이 GUI 에서 / check=읽기 전용 자동 연결 확인 / auto=미구현")
    p.add_argument("--repo", help="psu_app 경로 (check/auto 에 필요)")
    p.add_argument("--name", help="프로젝트 폴더명")
    p.add_argument("--timeout", type=int, default=180)
    p.set_defaults(func=cmd_run)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
