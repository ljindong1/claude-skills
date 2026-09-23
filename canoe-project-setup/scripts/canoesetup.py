# -*- coding: utf-8 -*-
"""canoe-project-setup — CANoe 차종별 컨피그 추출 · 대조 · 점검.

.cfg 는 줄 단위 텍스트지만 utf-8 로도 cp949 로도 통째로 디코드되지 않는다
(바이너리 조각이 섞여 있다). 그래서 전 과정을 latin-1 왕복으로 처리한다 —
바이트가 그대로 보존되고 CRLF 도 건드리지 않는다. 화면에 보여줄 때만
cp949 로 풀어 본다.

명령
    survey  설치 · COM · 통폴더의 컨피그 목록 · 저장소 DB 현황
    plan    추출 대상과 변경 예정 (파일을 건드리지 않는다)
    create  추출 + 이름 정리 + DB 최신화 + 안내문 + 검증
    verify  참조 무결성 · 외부 잔재 · DB 최신 · 진단 로드 여부
    check   CANoe COM 으로 읽기 전용 확인 (버스로 송신하지 않는다)
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------
# 상수
# --------------------------------------------------------------------------

LATIN = "latin-1"

#: .cfg 안의 파일 참조. 340건쯤 나오고 그중 절반 이상이 빈 문자열이다.
#:
#: 태그 버전(V7 / V9)을 고정하면 안 된다 — CANoe 11 이 만든 컨피그는 V7,
#: 그걸 CANoe 19 에서 한 번 저장하면 V9 로 올라간다. 통폴더에는 두 세대가
#: 섞여 있다.
#:
#: QL 은 경로만, BQL 은 base= 를 달고 온다. **CDD 참조가 BQL 로 들어온다** —
#: QL 만 보면 진단 설정을 통째로 놓친다.
VFILE = re.compile(
    r'<VFileName V(\d+) (B?QL)> (\d+) (?:base=(\w+) )?"([^"]*)"')

#: 차종 코드. HE1i / SP3i / BJ1 / NQ6a / SX3e 를 모두 잡는다.
#: \b 는 못 쓴다 — 정규식에서 _ 는 단어 문자라 HE1i_PSU 의 i 뒤에 경계가 없다.
MODELTOK = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2}\d[a-z]?)(?![A-Za-z0-9])")

DRIVE = re.compile(r"^[A-Za-z]:")

#: cfg 가 참조하지 않지만 같이 다녀야 하는 파일.
#:
#: 환경변수 ini 가 여기 들어간다 — cfg 안에는 심볼트리 노드 키로만 나오고
#: 파일 참조로는 안 나와서, 이름 규칙으로 찾지 않으면 통째로 빠진다.
AUX_HINTS = ("Crc_Calculate", "HKMC_", "envvars")

#: 컨피그 본체와 붙어 다니는 파일들.
CFG_SIBLINGS = (".stcfg", ".cfg.ini")

CONFIG_EXTS = (".dbc", ".cdd", ".cddt", ".can", ".cin", ".cbf",
               ".xvp", ".vsysvar", ".ini", ".dll")


# --------------------------------------------------------------------------
# 바이트 안전 입출력
# --------------------------------------------------------------------------

def load(path):
    """파일을 latin-1 문자열로 읽는다. 바이트가 1:1 로 보존된다."""
    with open(path, "rb") as fh:
        return fh.read().decode(LATIN)


def save(path, txt):
    with open(path, "wb") as fh:
        fh.write(txt.encode(LATIN))


def dec(s):
    """latin-1 문자열을 화면에 보여줄 수 있게 푼다."""
    try:
        b = s.encode(LATIN)
    except Exception:
        return s
    for enc in ("cp949", "utf-8"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return s


def enc(s):
    """사람이 준 문자열을 cfg 안에 넣을 수 있는 latin-1 형태로."""
    try:
        s.encode(LATIN)
        return s
    except Exception:
        pass
    for e in ("cp949", "utf-8"):
        try:
            return s.encode(e).decode(LATIN)
        except Exception:
            pass
    return s


def die(msg):
    print("\n[중단] %s" % msg)
    sys.exit(1)


# --------------------------------------------------------------------------
# cfg 해석
# --------------------------------------------------------------------------

class Ref(object):
    """cfg 안의 파일 참조 하나."""

    __slots__ = ("line", "base", "raw", "shown", "kind")

    def __init__(self, line, base, raw):
        self.line = line
        self.base = base or ""
        self.raw = raw
        self.shown = dec(raw)
        self.kind = self._classify()

    def _classify(self):
        if self.base == "app":
            # CANoe 설치 폴더 기준. 우리 폴더와 무관하다.
            return "앱기준"
        if DRIVE.match(self.shown):
            return "절대경로"
        if self.shown.startswith(".."):
            return "폴더밖"
        if self.base == "cfg" or "\\" in self.shown:
            # base=cfg 면 파일명만 있어도 컨피그 폴더 기준이다.
            return "폴더안"
        return "파일명"

    def __repr__(self):
        return "<Ref L%d %s %s>" % (self.line, self.kind, self.shown)


def refs(txt):
    """파일 참조 목록. 빈 참조는 뺀다."""
    out = []
    for m in VFILE.finditer(txt):
        raw = m.group(5)
        if not raw:
            continue
        line = txt.count("\n", 0, m.start()) + 1
        out.append(Ref(line, m.group(4), raw))
    return out


def outside_root(shown):
    """폴더 밖 참조를 묶어 보여줄 이름. 드라이브 문자만으로는 쓸모가 없다."""
    parts = [x for x in shown.split("\\") if x]
    if DRIVE.match(shown):
        # C:\Users\Administrator\... -> C:\Users\Administrator
        return "\\".join(parts[:3]) if len(parts) > 2 else shown
    rest = [x for x in parts if x != ".."]
    # ..\..\..\30_Log\BJ1\... -> ..\30_Log
    return "..\\" + rest[0] if rest else shown


def cfg_generation(txt):
    """컨피그를 만든 CANoe 세대. 첫 줄의 ;CANoe Version |4|<세대>|… 에서."""
    m = re.match(r";CANoe Version \|\d+\|(\d+)\|", txt)
    return m.group(1) if m else None


#: 네트워크-채널 배정. 두 세대(V7/V9) 모두 같은 모양이다.
#:
#:     ILConfiguration::VNetwork 4 Begin_Of_Object
#:     2            블록 버전
#:     CAN          네트워크 이름
#:     1            채널 번호      <- 이것
#:     1 1 1 1      플래그
#:     Vector       드라이버
#:     HS_B2        DB 별칭
NETBLK = re.compile(
    r"ILConfiguration::VNetwork \d+ Begin_Of_Object\r?\n"
    r"\d+\r?\n"
    r"([^\r\n]*)\r?\n"
    r"(\d+)\r?\n"
    r"(?:[^\r\n]*\r?\n){5}"
    r"([^\r\n]*)\r?\n"
)


def networks(txt):
    """[(채널번호, 네트워크 이름, DB 별칭)]. 측정 결과를 채널별로 붙일 때 쓴다."""
    out = []
    for name, ch, db in NETBLK.findall(txt):
        try:
            out.append((int(ch), dec(name).strip(), dec(db).strip()))
        except ValueError:
            continue
    return out


def cdd_refs(rs):
    """컨피그가 참조하는 진단 기술(.cdd). 없으면 진단을 못 쓴다.

    VBasicDiagnosticStreamer 블록의 숫자는 이 용도로 쓸 수 없다 —
    CDD 가 물려 있는 원본에서도 0 으로 나온다.
    """
    return [r for r in rs if r.shown.lower().endswith((".cdd", ".odx", ".pdx"))]


def includes_of(path):
    """CAPL .can 이 #include 하는 파일명."""
    out = []
    try:
        txt = load(path)
    except Exception:
        return out
    for m in re.finditer(r'#include\s+"([^"]+)"', txt):
        out.append(dec(m.group(1)))
    return out


def model_tokens(names):
    """파일명 목록에서 차종 코드를 뽑는다."""
    found = []
    for n in names:
        for t in MODELTOK.findall(n):
            if t not in found:
                found.append(t)
    return found


def is_aux(name):
    """cfg 가 참조하지 않아도 같이 가져와야 하는 이름인가."""
    return any(h.lower() in name.lower() for h in AUX_HINTS)


def aux_belongs(name, target, donors):
    """그 보조 파일이 이 컨피그 것인가.

    통폴더에는 남의 차종 환경변수 ini 도 같이 있다 (PSM_envvars_RG3_EV_PE.ini).
    차종 코드가 붙어 있으면 목표 차종이나 이 컨피그가 실제로 쓰는 차종의
    것만 가져온다. 코드가 없으면 공용이라 그냥 가져온다.
    """
    toks = model_tokens([os.path.basename(name)])
    if not toks:
        return True
    allowed = {target} | set(donors)
    return any(t in allowed for t in toks)


# --------------------------------------------------------------------------
# 저장소에서 읽어내기
# --------------------------------------------------------------------------

def repo_model_ctrl(repo):
    """HSM 파일명 rel_<차종>_<제어기>_V 에서 차종과 제어기.

    CVD 스킬과 같은 근거를 쓴다. 폴더명(OEUK_HE1I)이나 .project(he1i)는
    대소문자가 달라 정식 표기가 아니다.
    """
    hsm = os.path.join(repo, "References", "01_HSM_Framework")
    if not os.path.isdir(hsm):
        return None, None
    for fn in sorted(os.listdir(hsm)):
        m = re.search(r"rel_([A-Za-z0-9]+)_([A-Za-z0-9]+)_V", fn)
        if m:
            return m.group(1), m.group(2)
    return None, None


def repo_dbs(repo):
    """References/DB 최상위의 현행 DBC. 구버전은 unused/ 로 내려가 있다."""
    d = os.path.join(repo, "References", "DB")
    if not os.path.isdir(d):
        return {}
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".dbc"):
            continue
        if not os.path.isfile(os.path.join(d, fn)):
            continue
        if re.search(r"_FD_B2[_.]", fn, re.I):
            out.setdefault("B2", []).append(fn)
        elif re.search(r"_Local[_.]", fn, re.I):
            out.setdefault("Local", []).append(fn)
        else:
            out.setdefault("기타", []).append(fn)
    # 같은 종류가 여럿이면 최신 날짜 접두사를 고른다.
    for k in list(out):
        out[k] = sorted(out[k])
    return out


def newest(lst):
    return lst[-1] if lst else None


# --------------------------------------------------------------------------
# survey
# --------------------------------------------------------------------------

def canoe_install():
    cands = []
    for root in (r"C:\Program Files", r"C:\Program Files (x86)"):
        if not os.path.isdir(root):
            continue
        for n in sorted(os.listdir(root)):
            if n.lower().startswith("vector canoe") and "report" not in n.lower():
                cands.append(os.path.join(root, n))
    return cands


def com_registered():
    try:
        out = subprocess.run(
            ["reg", "query", r"HKCR\CANoe.Application\CurVer"],
            capture_output=True, text=True, timeout=15)
        return out.returncode == 0
    except Exception:
        return False


def cmd_survey(a):
    print("== CANoe 설치 ==")
    ins = canoe_install()
    if ins:
        for p in ins:
            print("   %s" % p)
    else:
        print("   찾지 못했다")
    print("   COM(CANoe.Application) 등록: %s" % ("예" if com_registered() else "아니오"))

    if a.pool:
        print("\n== 통폴더의 컨피그 ==")
        if not os.path.isdir(a.pool):
            die("통폴더가 없다: %s" % a.pool)
        cfgs = [f for f in sorted(os.listdir(a.pool)) if f.lower().endswith(".cfg")]
        if not cfgs:
            print("   .cfg 가 없다")
        for f in cfgs:
            size = os.path.getsize(os.path.join(a.pool, f))
            toks = model_tokens([f])
            print("   %-34s %8.1f KB   차종 %s"
                  % (f, size / 1024.0, "/".join(toks) if toks else "-"))

    if a.repo:
        print("\n== 저장소 ==")
        model, ctrl = repo_model_ctrl(a.repo)
        print("   차종 / 제어기 : %s / %s" % (model or "?", ctrl or "?"))
        dbs = repo_dbs(a.repo)
        if not dbs:
            print("   References/DB 를 찾지 못했다")
        for k in ("B2", "Local", "기타"):
            for fn in dbs.get(k, []):
                mark = " <- 현행" if fn == newest(dbs[k]) else ""
                print("   %-6s %s%s" % (k, fn, mark))


# --------------------------------------------------------------------------
# 추출 계획
# --------------------------------------------------------------------------

class Plan(object):
    def __init__(self):
        self.cfg = None            # 통폴더 기준 cfg 파일명
        self.pool = None
        self.out = None
        self.target = None         # 목표 차종 코드
        self.donors = []           # 남의 차종 코드
        self.inside = []           # (상대경로, 존재여부)
        self.outside = []          # (줄번호, 표시값, 분류)
        self.extra = []            # include 로 딸려오는 것
        self.shared = []           # 공용 파일
        self.runtime = None        # .run\<cfg이름>
        self.cdds = []             # 참조하는 진단 기술
        self.gen = None            # 만든 CANoe 세대
        self.db_now = {}
        self.db_new = {}
        self.repo_model = None
        self.repo_ctrl = None
        self.orphans = []          # 폴더에 있는데 참조되지 않는 것


def build_plan(a):
    p = Plan()
    p.pool = os.path.abspath(a.pool)
    if not os.path.isdir(p.pool):
        die("통폴더가 없다: %s" % p.pool)

    cfgname = a.cfg
    if not cfgname.lower().endswith(".cfg"):
        cfgname += ".cfg"
    cfgpath = os.path.join(p.pool, cfgname)
    if not os.path.isfile(cfgpath):
        die("컨피그가 없다: %s" % cfgpath)
    p.cfg = cfgname

    txt = load(cfgpath)
    p.gen = cfg_generation(txt)
    rs = refs(txt)
    p.cdds = cdd_refs(rs)

    # 목표 차종 — cfg 파일명에서. --model 로 덮어쓸 수 있다.
    toks = model_tokens([cfgname])
    p.target = a.model or (toks[0] if toks else None)
    if not p.target:
        die("cfg 이름에서 차종 코드를 못 찾았다. --model 로 지정하라.")

    for r in rs:
        if r.kind == "폴더안":
            full = os.path.join(p.pool, r.shown)
            p.inside.append((r.shown, os.path.isfile(full)))
        elif r.kind in ("절대경로", "폴더밖"):
            p.outside.append((r.line, r.shown, r.kind))

    # 중복 제거 (같은 파일이 여러 번 참조된다)
    seen = set()
    uniq = []
    for rel, ok in p.inside:
        if rel.lower() in seen:
            continue
        seen.add(rel.lower())
        uniq.append((rel, ok))
    p.inside = uniq

    # 남의 차종 자산 찾기
    basenames = [os.path.basename(r) for r, _ in p.inside]
    for t in model_tokens(basenames):
        if t != p.target and t not in p.donors:
            p.donors.append(t)

    # CAPL include 를 따라간다
    for rel, ok in p.inside:
        if not ok or not rel.lower().endswith(".can"):
            continue
        base = os.path.dirname(rel)
        for inc in includes_of(os.path.join(p.pool, rel)):
            cand = os.path.join(base, inc) if base else inc
            if cand.lower() in seen:
                continue
            seen.add(cand.lower())
            p.extra.append((cand, os.path.isfile(os.path.join(p.pool, cand))))

    # 이름으로 알아보는 보조 파일 (cfg 가 참조하지 않아도 필요하다)
    for dirpath, dirs, files in os.walk(p.pool):
        dirs[:] = [d for d in dirs if not d.startswith(".run")]
        for fn in files:
            if not is_aux(fn):
                continue
            if not aux_belongs(fn, p.target, p.donors):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), p.pool)
            if rel.lower() in seen:
                continue
            seen.add(rel.lower())
            p.shared.append(rel)

    # 실행 상태 폴더
    runtime = os.path.join(".run", os.path.splitext(cfgname)[0])
    if os.path.isdir(os.path.join(p.pool, runtime)):
        p.runtime = runtime

    # DB 현황
    for rel, _ok in p.inside:
        if rel.lower().endswith(".dbc"):
            fn = os.path.basename(rel)
            key = "B2" if re.search(r"_FD_B2[_.]", fn, re.I) else "Local"
            p.db_now[key] = rel

    if a.repo:
        p.repo_model, p.repo_ctrl = repo_model_ctrl(a.repo)
        for k, lst in repo_dbs(a.repo).items():
            if k in ("B2", "Local"):
                p.db_new[k] = newest(lst)

    out = a.out or os.path.join(os.path.dirname(p.pool),
                                "CANoe_%s" % p.target)
    p.out = os.path.abspath(out)
    return p


def print_plan(p, a):
    print("== 추출 대상 ==")
    print("   통폴더   %s" % p.pool)
    print("   컨피그   %s" % p.cfg)
    print("   대상폴더 %s%s" % (p.out, "   <- 이미 있다" if os.path.isdir(p.out) else ""))
    print("   차종     %s" % p.target)
    print("   세대     CANoe %s 가 만든 컨피그" % (p.gen or "?"))

    if p.repo_model:
        print("\n== 저장소 대조 ==")
        print("   저장소 차종 / 제어기 : %s / %s" % (p.repo_model, p.repo_ctrl))
        if p.repo_model.lower() != p.target.lower():
            print("   [경고] cfg 차종(%s)과 저장소 차종(%s)이 다르다."
                  % (p.target, p.repo_model))

    print("\n== 가져올 파일 ==")
    for rel, ok in p.inside:
        print("   %-6s %s" % ("있음" if ok else "없음", dec(rel)))
    for rel, ok in p.extra:
        print("   %-6s %s   (CAPL include)" % ("있음" if ok else "없음", rel))
    for rel in p.shared:
        print("   있음     %s   (보조 — cfg 가 참조하지 않는다)" % rel)
    if p.runtime:
        print("   있음   %s\\   (실행 상태)" % p.runtime)

    if p.donors:
        print("\n== 남의 차종 자산 ==")
        print("   이 컨피그는 %s 자산을 쓰고 있다." % ", ".join(p.donors))
        for rel, _ok in p.inside:
            b = os.path.basename(rel)
            if any(t in b for t in p.donors):
                print("      %s" % dec(rel))
        if getattr(a, "rename", False):
            print("   --rename: %s 이름으로 정리하고 출처를 안내문에 남긴다."
                  % p.target)
        else:
            print("   이름을 그대로 둔다 (공유 사실이 눈에 보인다).")
            print("   --rename 을 주면 %s 이름으로 정리한다." % p.target)

    if p.db_new:
        print("\n== CAN DB ==")
        for k in ("B2", "Local"):
            now = os.path.basename(p.db_now.get(k, "")) or "-"
            new = p.db_new.get(k) or "-"
            same = "같음" if now == new else "갱신"
            print("   %-6s %-52s -> %-52s %s" % (k, now, new, same))

    print("\n== 진단(CDD) ==")
    if p.cdds:
        for r in p.cdds:
            print("   L%-7d %s" % (r.line, r.shown))
    else:
        print("   컨피그가 참조하는 진단 기술이 없다.")
        print("   폴더에 .cdd 가 있어도 CANoe 가 쓰지 않는다 — 진단 검증 전에 물려야 한다.")

    print("\n== 폴더 밖을 가리키는 참조 %d건 ==" % len(p.outside))
    groups = {}
    for line, shown, kind in p.outside:
        groups.setdefault(outside_root(shown), []).append(line)
    for root, lines in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print("   %3d건  %s" % (len(lines), root))
    print("   로그·템플릿·테스트 보고서 경로다. 라이팅이나 측정을 막지는 않지만,")
    print("   남의 PC·남의 프로젝트 흔적이므로 보고서에 남긴다.")


def cmd_plan(a):
    p = build_plan(a)
    print_plan(p, a)
    print("\n파일은 건드리지 않았다. 진행하려면 create --yes 를 쓴다.")


# --------------------------------------------------------------------------
# create
# --------------------------------------------------------------------------

def copy_one(src, dst):
    d = os.path.dirname(dst)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    shutil.copy2(src, dst)


def rename_for(rel, donors, target):
    """남의 차종 이름을 목표 차종으로.

    공용 파일을 따로 거르지 않는다 — 공용이면 차종 코드가 애초에 없어서
    치환 대상이 되지 않는다. 반대로 PSM_envvars_SP3i.ini 처럼 보조 파일이어도
    차종 코드가 붙어 있으면 바꿔야 한다.
    """
    head, base = os.path.split(rel)
    new = base
    for t in donors:
        new = re.sub(re.escape(t), target, new)
    if new == base:
        return rel, False
    return (os.path.join(head, new) if head else new), True


def cmd_create(a):
    p = build_plan(a)
    print_plan(p, a)

    if not a.yes:
        die("확인이 필요하다. 위 내용이 맞으면 --yes 를 붙여 다시 실행하라.")
    if os.path.isdir(p.out) and os.listdir(p.out):
        die("대상 폴더가 이미 있고 비어 있지 않다: %s" % p.out)

    donors = p.donors if a.rename else []
    os.makedirs(p.out, exist_ok=True)

    provenance = []   # (새 경로, 원래 경로, 비고)

    # 1) 컨피그 본체와 형제 파일
    stem = os.path.splitext(p.cfg)[0]
    for ext in ("",) + CFG_SIBLINGS:
        src_name = stem + ext if ext else p.cfg
        if ext == ".cfg.ini":
            src_name = p.cfg + ".ini"
        src = os.path.join(p.pool, src_name)
        if not os.path.isfile(src):
            continue
        copy_one(src, os.path.join(p.out, src_name))
        provenance.append((src_name, src_name, "원본 그대로"))

    # 2) 참조 파일 + include + 공용
    rename_map = {}
    for rel, ok in p.inside + p.extra:
        if not ok:
            continue
        if rel.lower().startswith(".run"):
            continue
        newrel, changed = rename_for(rel, donors, p.target)
        copy_one(os.path.join(p.pool, rel), os.path.join(p.out, newrel))
        if changed:
            rename_map[os.path.basename(rel)] = os.path.basename(newrel)
            provenance.append((dec(newrel), dec(rel), "다른 차종 자산 — 이름만 바꿈"))
        else:
            provenance.append((dec(newrel), dec(rel), "원본 그대로"))

    for rel in p.shared:
        newrel, changed = rename_for(rel, donors, p.target)
        copy_one(os.path.join(p.pool, rel), os.path.join(p.out, newrel))
        if changed:
            provenance.append((newrel, rel, "보조 — 다른 차종 이름이었다"))
        else:
            provenance.append((newrel, rel, "공용 — 이름 유지"))

    # 3) 실행 상태 폴더
    if p.runtime:
        shutil.copytree(os.path.join(p.pool, p.runtime),
                        os.path.join(p.out, p.runtime), dirs_exist_ok=True)
        provenance.append((p.runtime + "\\", p.runtime + "\\", "실행 상태"))

    # 4) CAN DB 최신화
    db_changes = []
    for k, newfn in p.db_new.items():
        oldrel = p.db_now.get(k)
        if not oldrel or not newfn:
            continue
        if os.path.basename(oldrel) == newfn:
            continue
        newrel = os.path.join(os.path.dirname(oldrel), newfn)
        src = os.path.join(a.repo, "References", "DB", newfn)
        if not os.path.isfile(src):
            continue
        copy_one(src, os.path.join(p.out, newrel))
        old_full = os.path.join(p.out, oldrel)
        if os.path.isfile(old_full):
            os.remove(old_full)
        db_changes.append((oldrel, newrel))
        # 교체로 지워진 구버전 행을 출처표에서 뺀다. 남겨 두면 폴더에 없는
        # 파일이 목록에 있는 꼴이 된다.
        provenance[:] = [row for row in provenance
                         if os.path.normcase(row[0]) != os.path.normcase(dec(oldrel))]
        provenance.append((dec(newrel), "psu_app/References/DB/" + newfn,
                           "저장소 현행 DB"))

    # 5) cfg 안의 참조 고치기 — 이름 변경 + DB 교체
    cfgdst = os.path.join(p.out, p.cfg)
    txt = load(cfgdst)
    subs = 0

    def swap(text, old, new):
        """치환. 바꿔 넣을 값은 반드시 함수로 준다.

        경로에는 역슬래시가 들어 있고, re.sub 의 치환 문자열에서 \\2 는
        그룹 참조로 해석된다. 'CAN DB\\20260529_...' 를 문자열로 주면
        \\2 가 2번 그룹으로 바뀌어 'CAN DB60529_...' 가 된다.
        """
        return re.subn(re.escape(enc(old)), lambda _m: enc(new), text)

    for old, new in rename_map.items():
        txt, n = swap(txt, old, new)
        subs += n
    for oldrel, newrel in db_changes:
        txt, n = swap(txt, oldrel, newrel)
        subs += n
    save(cfgdst, txt)

    # 6) 안내문
    write_readme(p, provenance, donors, db_changes, a)

    print("\n== 생성 완료 ==")
    print("   폴더      %s" % p.out)
    print("   치환      %d곳" % subs)
    print("   안내문    읽어보세요.txt")

    print()
    ok = run_verify(p.out, a.repo, target=p.target)
    return p.out, p.target, ok


def write_readme(p, provenance, donors, db_changes, a):
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "assets", "readme_template.txt")
    rows = []
    width = max([len(x[0]) for x in provenance] + [24])
    for new, old, note in provenance:
        if new == old:
            rows.append("  %-*s  %s" % (width, new, note))
        else:
            rows.append("  %-*s  %s  <- %s" % (width, new, note, old))

    donor_note = ""
    if donors:
        donor_note = (
            "이 컨피그는 %s 의 자산(CDD / PANEL / CAPL)을 쓴다.\n"
            "%s 이름으로 바꿔 두었지만 내용은 %s 것이다 — 특히 .cdd 는\n"
            "%s 진단 사양서다. 이 차종에만 있는 DTC / DID 는 들어 있지 않다.\n"
            % (", ".join(donors), p.target, ", ".join(donors), ", ".join(donors))
        )
    else:
        donor_note = "남의 차종 자산을 쓰지 않는다.\n"

    if p.cdds:
        diag_note = ("컨피그가 참조하는 진단 기술:\n"
                     + "\n".join("  %s" % r.shown for r in p.cdds))
    else:
        diag_note = ("컨피그가 참조하는 진단 기술이 없다. 폴더에 .cdd 가 있어도\n"
                     "CANoe 가 쓰지 않는다 — 진단 검증 전에 물려야 한다.")

    db_note = "\n".join("  %s\n    -> %s" % (dec(o), dec(n)) for o, n in db_changes) \
        or "  변경 없음"

    # 템플릿은 우리가 쓴 UTF-8 파일이다. cfg 와 달리 latin-1 왕복이 필요 없다.
    if os.path.isfile(tpl_path):
        with open(tpl_path, encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = "{PROJECT} CANoe 컨피그\n\n[파일 출처]\n{PROVENANCE}\n"

    body = (body
            .replace("{PROJECT}", p.target)
            .replace("{CFG}", p.cfg)
            .replace("{DATE}", datetime.date.today().isoformat())
            .replace("{POOL}", p.pool)
            .replace("{REPO}", a.repo or "-")
            .replace("{PROVENANCE}", "\n".join(rows))
            .replace("{DONOR_NOTE}", donor_note.rstrip())
            .replace("{DIAG_NOTE}", diag_note.rstrip())
            .replace("{DB_NOTE}", db_note)
            .replace("{OUTSIDE}", str(len(p.outside))))

    out = os.path.join(p.out, "읽어보세요.txt")
    with open(out, "wb") as fh:
        fh.write(body.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

def run_verify(folder, repo=None, target=None):
    print("== 검증 ==")
    cfgs = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(".cfg")]
    if len(cfgs) != 1:
        print("   [실패] .cfg 가 %d개다 (1개여야 한다)" % len(cfgs))
        return False
    cfg = cfgs[0]
    txt = load(os.path.join(folder, cfg))
    rs = refs(txt)
    ok = True

    gen = cfg_generation(txt)
    if gen:
        print("   [정보] CANoe %s 세대 컨피그" % gen)

    # 1. 폴더 안 참조가 전부 실재하나
    missing = []
    present = 0
    for r in rs:
        if r.kind != "폴더안":
            continue
        if os.path.isfile(os.path.join(folder, r.shown)):
            present += 1
        else:
            missing.append(r.shown)
    missing = sorted(set(missing))
    if missing:
        ok = False
        print("   [실패] 참조하는데 없는 파일 %d건" % len(missing))
        for m in missing:
            print("          %s" % m)
    else:
        print("   [통과] 폴더 안 참조 %d건 전부 실재" % present)

    # 2. 남의 차종 이름이 남아 있나
    if target:
        names = [os.path.basename(r.shown) for r in rs if r.kind == "폴더안"]
        left = [t for t in model_tokens(names) if t != target]
        if left:
            print("   [주의] 다른 차종 이름이 남아 있다: %s" % ", ".join(left))
        else:
            print("   [통과] 파일 이름은 %s 로 통일" % target)

    # 3. 진단 기술 참조
    refd = cdd_refs(rs)
    ondisk = [f for f in os.listdir(folder) if f.lower().endswith(".cdd")]
    if refd:
        print("   [통과] 진단 기술 참조 %d건" % len(refd))
    elif ondisk:
        ok = False
        print("   [실패] .cdd 가 폴더에 있는데 컨피그가 참조하지 않는다")
        for f in ondisk:
            print("          %s" % f)
        print("          CANoe 에서 Diagnostics/ISO TP 에 물린 뒤 저장해야 한다")
    else:
        print("   [주의] 진단 기술이 없다 (진단 검증을 하려면 필요하다)")

    # 4. DB 가 저장소 현행인가
    if repo:
        cur = repo_dbs(repo)
        for r in rs:
            shown = r.shown
            if not shown.lower().endswith(".dbc"):
                continue
            fn = os.path.basename(shown)
            key = "B2" if re.search(r"_FD_B2[_.]", fn, re.I) else "Local"
            want = newest(cur.get(key, []))
            if want and want != fn:
                ok = False
                print("   [실패] %s DB 가 저장소 현행과 다르다" % key)
                print("          지금   %s" % fn)
                print("          저장소 %s" % want)
            elif want:
                print("   [통과] %s DB 가 저장소 현행과 같다" % key)

    # 5. 폴더 밖 참조
    out = [r for r in rs if r.kind in ("절대경로", "폴더밖")]
    if out:
        print("   [정보] 폴더 밖을 가리키는 참조 %d건 (로그·템플릿·보고서)" % len(out))
        roots = {}
        for r in out:
            root = outside_root(r.shown)
            roots[root] = roots.get(root, 0) + 1
        for root, n in sorted(roots.items(), key=lambda kv: -kv[1])[:6]:
            print("          %3d건  %s" % (n, root))

    # 6. VFileName 밖의 맨 절대경로
    #    CAPL 컴파일 출력(.cbf) 경로가 원작성자 PC 를 가리킨 채로 남는다.
    #    CANoe 가 다시 컴파일하면 덮어쓰므로 막지는 않지만 흔적이다.
    bare = sorted(set(
        m.group(0) for m in re.finditer(
            r"(?m)^[A-Za-z]:\\[^\r\n]*\.(?:cbf|dll|exe)$", txt)))
    if bare:
        print("   [정보] 참조 태그 밖의 절대경로 %d건 (CAPL 컴파일 출력 등)" % len(bare))
        for b in bare[:4]:
            print("          %s" % dec(b))

    # 7. 참조되지 않는 파일
    #    cfg 참조 + CAPL include + 이름으로 아는 공용 파일까지가 "쓰이는 것"이다.
    #    .cin 은 cfg 가 아니라 .can 의 #include 로만 등장한다.
    used = set()
    for r in rs:
        if r.kind == "폴더안":
            used.add(os.path.normcase(r.shown))
    for r in list(rs):
        if r.kind != "폴더안" or not r.shown.lower().endswith(".can"):
            continue
        head = os.path.dirname(r.shown)
        for inc in includes_of(os.path.join(folder, r.shown)):
            used.add(os.path.normcase(os.path.join(head, inc) if head else inc))
    orphan = []
    for dirpath, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".run")]
        for fn in files:
            rel = os.path.relpath(os.path.join(dirpath, fn), folder)
            if os.path.normcase(rel) in used:
                continue
            if fn == cfg or fn.startswith(os.path.splitext(cfg)[0]):
                continue
            if fn == "읽어보세요.txt":
                continue
            if is_aux(fn):
                continue
            if os.path.splitext(fn)[1].lower() in CONFIG_EXTS:
                orphan.append(rel)
    if orphan:
        print("   [정보] 컨피그가 참조하지 않는 파일 %d건" % len(orphan))
        for o in sorted(orphan):
            print("          %s" % o)

    print("\n   => %s" % ("검증 통과" if ok else "검증 실패 — 위 [실패] 항목을 보라"))
    return ok


def cmd_verify(a):
    if not os.path.isdir(a.dir):
        die("폴더가 없다: %s" % a.dir)
    ok = run_verify(a.dir, a.repo, a.model)
    sys.exit(0 if ok else 2)


# --------------------------------------------------------------------------
# check — CANoe COM, 읽기 전용
# --------------------------------------------------------------------------

CHECK_PS1 = r"""
# canoe-project-setup — 읽기 전용 확인.
# 컨피그를 열어 구성만 읽고 닫는다. 측정을 시작하지 않으므로
# 버스로 아무것도 내보내지 않는다.
$ErrorActionPreference = "Stop"
$cfg = "__CFG__"
$log = "__LOG__"

function W($s) { Add-Content -Path $log -Value $s -Encoding utf8 }

Set-Content -Path $log -Value ("STEP=start  " + (Get-Date -Format "s")) -Encoding utf8
$app = $null
try {
    $app = New-Object -ComObject CANoe.Application
    # 창을 띄우지 않는다. 사람이 쓰던 화면을 가리지 않고, 원격/무인 실행에서도
    # 뜨는 창이 없다. 실패해도 finally 에서 Quit 하므로 유령 프로세스가 남지 않는다.
    try { $app.Visible = $false } catch { W ("VISIBLE_ERR=" + $_.Exception.Message) }
    W ("CANoe=" + $app.Version.major + "." + $app.Version.minor + "." + $app.Version.Build)
    W "STEP=com_ok"

    $app.Open($cfg, $false, $false)
    W "STEP=opened"
    W ("CFG=" + $app.Configuration.FullName)
    W ("MODIFIED=" + $app.Configuration.Modified)

    $dbs = $app.Configuration.GeneralSetup.DatabaseSetup.Databases
    W ("DB_COUNT=" + $dbs.Count)
    for ($i = 1; $i -le $dbs.Count; $i++) {
        $d = $dbs.Item($i)
        W ("DB=" + $d.Name + " | " + $d.FullName)
    }
    W "STEP=db_ok"

    try {
        $nodes = $app.Configuration.SimulationSetup.Nodes
        W ("NODE_COUNT=" + $nodes.Count)
        for ($i = 1; $i -le $nodes.Count; $i++) {
            W ("NODE=" + $nodes.Item($i).Name)
        }
    } catch { W ("NODE_ERR=" + $_.Exception.Message) }

    W "STEP=done"
}
catch {
    W ("ERROR=" + $_.Exception.Message)
}
finally {
    if ($app -ne $null) {
        try { $app.Quit() } catch { W ("QUIT_ERR=" + $_.Exception.Message) }
    }
}
"""


RUN_PS1 = r"""
# canoe-project-setup — 연결 + 측정 + 채널별 통신 통계.
#
# check 와 달리 측정을 시작한다. 시뮬레이션 노드가 버스로 송신한다.
# 정해진 시간만 돌리고 반드시 Stop / Quit 한다.
$ErrorActionPreference = "Stop"
$cfg     = "__CFG__"
$log     = "__LOG__"
$seconds = __SECONDS__
$chans   = @(__CHANS__)

function W($s) { Add-Content -Path $log -Value $s -Encoding utf8 }
function P($o, $n) { try { return $o.$n } catch { return "?" } }

Set-Content -Path $log -Value ("STEP=start  " + (Get-Date -Format "s")) -Encoding utf8
$app = $null
try {
    $app = New-Object -ComObject CANoe.Application
    try { $app.Visible = $false } catch {}
    W ("CANoe=" + $app.Version.major + "." + $app.Version.minor + "." + $app.Version.Build)
    W "STEP=com_ok"

    $app.Open($cfg, $false, $false)
    W ("CFG=" + $app.Configuration.FullName)

    # 실버스인가 시뮬레이션인가. 시뮬레이션이면 장비로 아무것도 안 나가므로
    # 통계가 전부 0 이 되는데, 그것은 "버스가 조용한 것"과 전혀 다른 상황이다.
    try { W ("MODE=" + $app.Configuration.mode) } catch {}
    try { W ("WORKMODE=" + $app.Configuration.OnlineSetup.WorkingMode) } catch {}
    try { W ("CHMAP=" + $app.ChannelMappingName) } catch {}

    $dbs = $app.Configuration.GeneralSetup.DatabaseSetup.Databases
    W ("DB_COUNT=" + $dbs.Count)
    for ($i = 1; $i -le $dbs.Count; $i++) {
        W ("DB=" + $dbs.Item($i).Name + " | " + $dbs.Item($i).FullName)
    }
    W "STEP=opened"

    $m = $app.Measurement
    $m.Start()
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while (-not $m.Running -and $sw.Elapsed.TotalSeconds -lt 30) {
        Start-Sleep -Milliseconds 200
    }
    if (-not $m.Running) { throw "측정이 시작되지 않았다 (30초 대기)" }
    W "STEP=measuring"

    Start-Sleep -Seconds $seconds
    W ("ELAPSED=" + [math]::Round($sw.Elapsed.TotalSeconds, 1))

    # 통계는 Bus("CAN").Statistics() 가 아니다 — 그런 멤버는 없다.
    # Configuration.OnlineSetup.BusStatistics.BusStatistic(버스종류, 채널) 이고,
    # 버스 종류는 문자열 "CAN" 이 아니라 정수 1 을 받는다.
    $stats = $app.Configuration.OnlineSetup.BusStatistics
    foreach ($ch in $chans) {
        try {
            $st = $stats.BusStatistic(1, $ch)
            W ("CH" + $ch + "_STD="   + (P $st "Standard"))
            W ("CH" + $ch + "_EXT="   + (P $st "Extended"))
            W ("CH" + $ch + "_ERR="   + (P $st "Error"))
            W ("CH" + $ch + "_LOAD="  + (P $st "BusLoad"))
            W ("CH" + $ch + "_PEAK="  + (P $st "PeakLoad"))
            W ("CH" + $ch + "_CHIP="  + (P $st "ChipState"))
            W ("CH" + $ch + "_RXERR=" + (P $st "RxErrorCount"))
            W ("CH" + $ch + "_TXERR=" + (P $st "TxErrorCount"))
        } catch {
            W ("CH" + $ch + "_STATERR=" + $_.Exception.Message)
        }
    }
    W "STEP=stats_ok"

    $m.Stop()
    $sw2 = [Diagnostics.Stopwatch]::StartNew()
    while ($m.Running -and $sw2.Elapsed.TotalSeconds -lt 30) {
        Start-Sleep -Milliseconds 200
    }
    W "STEP=done"
}
catch {
    W ("ERROR=" + $_.Exception.Message)
}
finally {
    if ($app -ne $null) {
        try { if ($app.Measurement.Running) { $app.Measurement.Stop() } } catch {}
        try { $app.Quit() } catch { W ("QUIT_ERR=" + $_.Exception.Message) }
    }
}
"""

#: CANoe 칩 상태 코드. BusOff 면 배선 / 종단 / 보율을 본다.
CHIPSTATE = {"0": "ErrorActive", "1": "ErrorPassive", "2": "BusOff", "3": "Unknown"}


def one_cfg(folder):
    cfgs = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(".cfg")]
    if len(cfgs) != 1:
        die(".cfg 가 %d개다. 1개여야 한다: %s" % (len(cfgs), folder))
    return cfgs[0]


def ps_run(folder, ps1_name, body, timeout):
    """PowerShell 스크립트를 만들어 돌리고 로그 줄을 돌려준다."""
    work = os.path.join(folder, "_autorun")
    if not os.path.isdir(work):
        os.makedirs(work)
    ps1 = os.path.join(work, ps1_name)
    log = os.path.join(work, os.path.splitext(ps1_name)[0] + "_log.txt")
    if os.path.isfile(log):
        os.remove(log)
    with open(ps1, "wb") as fh:
        fh.write(body.encode("utf-8-sig"))
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1],
            timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("   [시간초과] %d초 안에 안 끝났다." % timeout)
    if not os.path.isfile(log):
        return None, log
    with open(log, encoding="utf-8-sig") as fh:
        return [l.rstrip() for l in fh.read().splitlines() if l.strip()], log


def kv(lines):
    out = {}
    for l in lines:
        if "=" in l:
            k, v = l.split("=", 1)
            out.setdefault(k.strip(), v.strip())
    return out


def num(s, default=None):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return default


def report_traffic(lines, nets):
    """채널별 통계를 표로 내고 판정한다.

    판정 규칙은 HE1i 작업에서 실제로 겪은 것을 그대로 옮겼다.
    """
    d = kv(lines)
    steps = [l.split("=", 1)[1] for l in lines if l.startswith("STEP=")]
    last = steps[-1] if steps else None

    print("   --- 측정 ---")
    print("   CANoe %s, %s초" % (d.get("CANoe", "?"), d.get("ELAPSED", "?")))
    for l in lines:
        if l.startswith("DB="):
            print("   DB  %s" % l[3:].split(" | ")[0])
    chmap = d.get("CHMAP")
    if chmap:
        # Vector 는 채널 배정을 애플리케이션 단위로 한다. 이 이름의 항목에
        # 채널이 안 물려 있으면 측정은 돌아도 장비로 아무것도 안 나간다.
        print("   하드웨어 애플리케이션 이름  [%s]" % chmap)

    if last not in ("stats_ok", "done"):
        print("\n   --- 판정 ---")
        meaning = {
            None: "로그가 없다. PowerShell 이 스크립트를 실행하지 못했다.",
            "start": "COM 객체를 못 만들었다. CANoe 설치 / 라이선스를 본다.",
            "com_ok": "컨피그를 못 열었다. 경로 / 다른 CANoe 인스턴스를 본다.",
            "opened": "측정이 시작되지 않았다. 하드웨어 배정(Hardware Manager)을 본다.",
            "measuring": "통계를 못 읽었다.",
        }
        print("   %s" % meaning.get(last, "로그를 직접 보라 (마지막 STEP=%s)" % last))
        for e in [l for l in lines if l.startswith("ERROR=")]:
            print("   %s" % e)
        return False

    netmap = {ch: (nm, db) for ch, nm, db in nets}
    chans = sorted(netmap) or [1, 2]

    print()
    print("   채널  네트워크      수신프레임   에러프레임   버스로드   칩상태")
    rows = []

    def fmt(v):
        return "{:,}".format(int(v)) if v is not None else "못읽음"

    for ch in chans:
        std = num(d.get("CH%d_STD" % ch))
        ext = num(d.get("CH%d_EXT" % ch))
        err = num(d.get("CH%d_ERR" % ch))
        load = num(d.get("CH%d_LOAD" % ch))
        raw = str(d.get("CH%d_CHIP" % ch, "")).strip()
        chip = CHIPSTATE.get(raw, raw or "?")
        nm = netmap.get(ch, ("?", "?"))[0]
        # 셋 다 못 읽었으면 "0" 이 아니라 "못 읽음"이다. 이걸 0 으로 보고하면
        # 멀쩡한 버스를 "아무도 없다"고 단정하게 된다.
        rx = None if (std is None and ext is None) else (std or 0) + (ext or 0)
        rows.append((ch, nm, rx, err, load, chip))
        print("   %-5d %-13s %10s   %10s   %7s   %s"
              % (ch, nm[:13], fmt(rx), fmt(err),
                 ("%.1f%%" % load) if load is not None else "?", chip))

    staterr = [l for l in lines if "_STATERR=" in l]
    print("\n   --- 판정 ---")
    ok = True
    for ch, nm, rx, err, load, chip in rows:
        if rx is None and err is None:
            ok = False
            print("   채널 %d (%s)  [판정 불가] 통계를 읽지 못했다." % (ch, nm))
            print("      => 버스 상태를 알 수 없다. 수신 0 이라는 뜻이 아니다.")
            for e in staterr[:1]:
                print("      %s" % e.split("=", 1)[1][:110])
        elif chip == "BusOff":
            ok = False
            print("   채널 %d (%s)  [BusOff] 배선 / 종단저항 / 보율을 본다." % (ch, nm))
        elif rx is None or err is None:
            # 한쪽만 읽힌 경우. 있는 값만 말하고 단정하지 않는다.
            print("   채널 %d (%s)  [부분] 수신 %s / 에러 %s — 한쪽을 못 읽었다."
                  % (ch, nm, fmt(rx), fmt(err)))
        elif err > 0 and rx == 0:
            ok = False
            print("   채널 %d (%s)  [이상] 에러 프레임만 쏟아진다." % (ch, nm))
            print("      => 채널이 CAN FD 가 아니라 Classic CAN 으로 잡혀 있을 확률이 높다.")
            print("         Vector Hardware Manager 에서 해당 채널을 CAN FD 로 바꾼다.")
            print("         이 설정은 .cfg 안에 없어서 파일 검사로는 안 잡힌다.")
        elif err > 0:
            print("   채널 %d (%s)  [주의] 수신은 되는데 에러 프레임 %d건." % (ch, nm, int(err)))
            print("      => 종단저항 / 배선 / 다른 노드의 보율을 본다.")
        elif rx == 0:
            ok = False
            print("   채널 %d (%s)  [이상] 프레임 0, 에러 0, 버스로드 0 — 버스가 조용하다."
                  % (ch, nm))
            app = d.get("CHMAP") or "CANoe"
            print("      => 1. Vector Hardware Manager 에서 애플리케이션 [%s] 의" % app)
            print("            채널 %d 가 실제 장비(VN1640A 등)에 배정돼 있나." % ch)
            print("            **채널 배정은 애플리케이션 단위다.** 파이썬(XL API)이나")
            print("            다른 도구로 같은 장비를 쓴 적이 있으면 그쪽 이름에만")
            print("            물려 있고 [%s] 는 비어 있을 수 있다. 그래도 측정은" % app)
            print("            정상으로 돌기 때문에 이렇게 전부 0 으로만 보인다.")
            print("         2. 보드 전원과 IGN — B+ 만으로는 슬립에 머문다.")
            print("         3. 디버거로 main 에 세워 둔 상태는 아닌가 (CPU 정지 = 송신 없음).")
            print("         4. 결선과 종단저항.")
        else:
            print("   채널 %d (%s)  정상 — 수신 %s프레임, 에러 0."
                  % (ch, nm, "{:,}".format(int(rx))))
    return ok


def cmd_run(a):
    target = a.model
    if a.init:
        if not (a.pool and a.cfg):
            die("--init 에는 --pool 과 --cfg 가 필요하다.")
        print("== 1단계: 설정 생성 ==\n")
        folder, target, vok = cmd_create(a)
        if not vok:
            die("검증이 통과하지 않아 측정으로 넘어가지 않는다. 위 [실패] 항목을 보라.")
        print("\n== 2단계: 연결 + 측정 ==")
    else:
        if not a.dir:
            die("--dir 로 설정 폴더를 주거나 --init 으로 새로 만들라.")
        folder = os.path.abspath(a.dir)
        if not os.path.isdir(folder):
            die("폴더가 없다: %s" % folder)
        print("== 기존 설정으로 연결 + 측정 ==")
        print("   (설정은 그대로 쓴다. 파일을 건드리지 않는다.)\n")
        if a.repo:
            run_verify(folder, a.repo, target)
            print()

    cfg = os.path.join(folder, one_cfg(folder))
    txt = load(cfg)
    nets = networks(txt)

    print("   컨피그 %s" % cfg)
    for ch, nm, db in nets:
        print("   채널 %d  %s  (DB %s)" % (ch, nm, db))
    print("   측정 %d초 — 시뮬레이션 노드가 버스로 송신한다.\n" % a.seconds)

    chans = ",".join(str(c) for c, _n, _d in nets) or "1,2"
    body = (RUN_PS1
            .replace("__CFG__", cfg.replace('"', '`"'))
            .replace("__LOG__", os.path.join(folder, "_autorun", "run_log.txt").replace('"', '`"'))
            .replace("__SECONDS__", str(a.seconds))
            .replace("__CHANS__", chans))
    lines, log = ps_run(folder, "run.ps1", body, a.timeout)
    if lines is None:
        print("   [실패] 로그가 없다: %s" % log)
        sys.exit(2)

    ok = report_traffic(lines, nets)
    print("\n   로그 %s" % log)
    sys.exit(0 if ok else 2)


def cmd_check(a):
    folder = os.path.abspath(a.dir)
    if not os.path.isdir(folder):
        die("폴더가 없다: %s" % folder)
    cfgs = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(".cfg")]
    if len(cfgs) != 1:
        die(".cfg 가 %d개다. 1개여야 한다." % len(cfgs))
    cfg = os.path.join(folder, cfgs[0])

    work = os.path.join(folder, "_autorun")
    if not os.path.isdir(work):
        os.makedirs(work)
    ps1 = os.path.join(work, "check.ps1")
    log = os.path.join(work, "check_log.txt")
    if os.path.isfile(log):
        os.remove(log)

    body = (CHECK_PS1
            .replace("__CFG__", cfg.replace('"', '`"'))
            .replace("__LOG__", log.replace('"', '`"')))
    with open(ps1, "wb") as fh:
        fh.write(body.encode("utf-8-sig"))

    print("== CANoe 읽기 전용 확인 ==")
    print("   컨피그 %s" % cfg)
    print("   측정을 시작하지 않는다 — 버스로 송신하지 않는다.")
    print("   CANoe 를 창 없이(Visible=False) 띄웠다가 닫는다.\n")

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps1],
            timeout=a.timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("   [시간초과] %d초 안에 안 끝났다." % a.timeout)

    if not os.path.isfile(log):
        print("   [실패] 로그가 없다. PowerShell 이 스크립트를 실행하지 못했다.")
        sys.exit(2)

    # utf-8-sig — PowerShell 의 -Encoding utf8 이 BOM 을 붙인다. 그냥 utf-8 로
    # 읽으면 첫 줄 앞에 보이지 않는 문자가 달려 나온다.
    with open(log, encoding="utf-8-sig") as fh:
        lines = [l.rstrip() for l in fh.read().splitlines() if l.strip()]
    print("   --- 로그 ---")
    for l in lines:
        print("   %s" % l)

    steps = [l.split("=", 1)[1] for l in lines if l.startswith("STEP=")]
    last = steps[-1] if steps else None
    print("\n   --- 판정 ---")
    meaning = {
        "start": "COM 객체를 못 만들었다. CANoe 설치 / 라이선스를 본다.",
        "com_ok": "컨피그를 못 열었다. 경로 / 다른 CANoe 인스턴스를 본다.",
        "opened": "DB 목록을 못 읽었다.",
        "db_ok": "시뮬레이션 노드를 읽다 멈췄다.",
        "done": "전부 통과.",
    }
    print("   %s" % meaning.get(last, "로그를 직접 보라 (마지막 STEP=%s)" % last))
    err = [l for l in lines if l.startswith("ERROR=")]
    for e in err:
        print("   %s" % e)
    sys.exit(0 if last == "done" else 2)


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(prog="canoesetup")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("survey")
    s.add_argument("--pool")
    s.add_argument("--repo")
    s.set_defaults(fn=cmd_survey)

    for name in ("plan", "create"):
        s = sub.add_parser(name)
        s.add_argument("--pool", required=True)
        s.add_argument("--cfg", required=True)
        s.add_argument("--repo")
        s.add_argument("--out")
        s.add_argument("--model")
        s.add_argument("--rename", action="store_true",
                       help="남의 차종 자산을 목표 차종 이름으로 정리")
        s.add_argument("--yes", action="store_true")
        s.set_defaults(fn=cmd_plan if name == "plan" else cmd_create)

    s = sub.add_parser("verify")
    s.add_argument("--dir", required=True)
    s.add_argument("--repo")
    s.add_argument("--model")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("check")
    s.add_argument("--dir", required=True)
    s.add_argument("--timeout", type=int, default=180)
    s.set_defaults(fn=cmd_check)

    # run — 연결 + 측정 + CAN 통신 결과 리포트.
    #   --init 있으면  설정을 먼저 만들고(=초기화) 이어서 측정
    #   --init 없으면  기존 설정을 그대로 쓰고 측정만
    s = sub.add_parser("run")
    s.add_argument("--init", action="store_true",
                   help="설정을 새로 만들고(추출·갱신·검증) 이어서 측정한다")
    s.add_argument("--dir", help="--init 없이 쓸 기존 설정 폴더")
    s.add_argument("--pool", help="--init 용 원본 통폴더")
    s.add_argument("--cfg", help="--init 용 대상 컨피그 이름")
    s.add_argument("--out", help="--init 용 대상 폴더")
    s.add_argument("--repo")
    s.add_argument("--model")
    s.add_argument("--rename", action="store_true")
    s.add_argument("--seconds", type=int, default=5, help="측정 시간 (기본 5초)")
    s.add_argument("--timeout", type=int, default=300)
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_run)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
