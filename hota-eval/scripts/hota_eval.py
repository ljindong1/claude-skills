#!/usr/bin/env python3
"""H-OTA A·B 그룹 평가 도우미 (hota-eval 스킬).

H-OTA Studio 로 돌리는 A(OEUK_HE1I) · B(OEUK_TEST) 그룹 12개 Rules 실행의 앞뒤 일을 맡는다.
H-OTA 실행 자체(Start 클릭)는 사람이 하거나(반자동), 파일럿이 끝나면 joule-hota 가 한다.

  status    결과 폴더 상태 - 케이스별 .asc/.log/.png 유무, 이름 규칙, 판정, 다음 할 일
  identify  aSIMS 서명본 폴더를 hash xml 로 변형 4벌에 맞추고, 저장소 빌드와 같은지(재빌드 여부) 확인
  bins      서명본 .bin 을 결과 폴더로 (없으면 Hex2Binary 로 만든다)
  prepare   케이스 실행 직전 - H-OTA 설정 파일에 .asc 경로(Report Config) · OEUK 를 넣고 할 일을 보여 준다
  restore   prepare 가 바꾼 H-OTA 설정 파일을 처음 상태로 되돌린다
  collect   케이스 실행 직후 - .asc/.log 확인, 캡처 png 이름 맞춤, 판정
  judge     .log · .asc 로 업·다운그레이드 판정 (결과·SW 버전·27 13/14, 소요 시간은 표시만)
  names     결과 폴더 파일 이름 규칙 검사
  report    보드평가레포트 xlsx 의 첨부 · 그림 · 헤더 교체 (Excel COM)
  zip       Redmine 첨부용 묶음 zip
  summary   Redmine / Confluence 결과 표 초안

공통 인자: --profile he1i_psu --swp 3.0.29 --date 261008 (결과 폴더 = <result_root>/v<swp>/<date>)
쓰기는 결과 폴더 · H-OTA 설정 파일(백업 후) · 지정한 출력 위치에만 한다. 저장소 커밋·외부 등록은 하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL = Path(__file__).resolve().parent.parent
RULE_KEY = {"ExternalRules": "External-rule", "BGRules": "background-rule", "ReproRules": "reprogram-rule"}
STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "hota-eval"


# ============================================================ 프로필
class Profile:
    def __init__(self, name: str, swp: str | None, date: str | None):
        p = Path(name)
        if not p.suffix:
            p = SKILL / "references" / "projects" / f"{name}.toml"
        self.path = p
        self.raw = tomllib.loads(p.read_text(encoding="utf-8"))
        pr = self.raw["project"]
        self.repo = Path(pr["app_repo"])
        self.low, self.high = pr["low"], pr["high"]
        self.swp = swp or self._swp_from_repo()
        self.date = date or dt.date.today().strftime("%y%m%d")
        self.vars = {"low": self.low, "high": self.high, "ver": self.swp,
                     "ver_us": self.swp.replace(".", "_"), "yymmdd": self.date}
        self.result = self.repo / pr["result_root"] / f"v{self.swp}" / self.date
        self.cases = [self._case(c) for c in self.raw["case"]]
        self.variants = {v["key"]: {**v, "folder": self.f(v["folder"])} for v in self.raw["variant"]}

    def f(self, s: str, **extra) -> str:
        return s.format(**{**self.vars, **extra})

    def _swp_from_repo(self) -> str:
        proj = self.repo / self.raw["project"]["app_dir"] / ".project"
        m = re.search(r"_v(\d+)_(\d+)_(\d+)</name>", proj.read_text(encoding="utf-8", errors="ignore")) if proj.exists() else None
        if not m:
            sys.exit("SWP 버전을 알 수 없습니다 - --swp 3.0.xx 로 주세요")
        return ".".join(m.groups())

    def _case(self, c: dict) -> dict:
        c = dict(c)
        c["name"] = self.f(c["name"])
        c["target"] = self.f(c["target"])
        c["sw_after"] = self.f(c.get("sw_after", ""))
        c["files"] = [f"{c['name']}_{r}" for r in c["rules"]]
        return c

    def case(self, cid: str) -> dict:
        for c in self.cases:
            if c["id"].upper() == cid.upper():
                return c
        sys.exit(f"케이스 {cid} 없음 ({', '.join(c['id'] for c in self.cases)})")


# ============================================================ 파일 해석
def read_log(p: Path) -> str:
    b = p.read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


_TS = re.compile(r"\[(\d{4}-\d\d-\d\d [\d:.]+)\]")


def _ts(line: str) -> dt.datetime | None:
    m = _TS.search(line)
    return dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f") if m else None


def judge_log(p: Path, rule: str) -> dict:
    """Output .log 에서 마지막 실행의 결과·NRC·SW 버전·소요 시간."""
    key = RULE_KEY[rule]
    lines = read_log(p).splitlines()
    res = [l for l in lines if re.search(rf"Run active document {key} (success|fail)", l, re.I)]
    if not res:
        return {"outcome": "없음", "detail": f"'{key}' 결과 줄 없음"}
    last = res[-1]
    t_end = _ts(last)
    ok = re.search(r"success", last.split("Run active document", 1)[1], re.I) is not None
    nrc = re.search(r"NRC\(0x([0-9A-Fa-f]{2})\)", last)
    outcome = "success" if ok else (f"nrc_{nrc.group(1).lower()}" if nrc else "fail")
    if rule == "BGRules":
        starts = [l for l in lines if f"[{key} Start]".lower() in l.lower() and _ts(l) and _ts(l) <= t_end]
    else:
        starts = [l for l in lines if "Success to Run Pre-procedure" in l and _ts(l) and _ts(l) <= t_end]
    dur = (t_end - _ts(starts[-1])).total_seconds() if starts and t_end else None
    sw = [m.group(1) for l in lines for m in [re.search(r"response SW version : (\d+)", l)] if m]
    return {"outcome": outcome, "time": t_end.strftime("%H:%M") if t_end else "",
            "duration_s": dur, "sw": sw[-1] if sw else "", "line": last.strip()[:160]}


_ASC = re.compile(r"^\s*(\d+\.\d+)\s+0*([0-9A-Fa-f]+)\s+(\d+)\s+(.*)$")


def asc_frames(p: Path):
    for line in open(p, errors="ignore"):
        m = _ASC.match(line)
        if m:
            yield float(m.group(1)), m.group(2).upper(), m.group(4).split()


def _sid(d: list[str]) -> list[str]:
    """ISO-TP 첫 프레임의 서비스 바이트부터 (SF: 0L, FD SF: 00 LL, FF: 1L LL). CF·FC 는 빈 목록."""
    if not d:
        return []
    pci = d[0][0]
    if pci == "0":
        return d[2:] if d[0] == "00" else d[1:]
    if pci == "1":
        return d[2:]
    return []


def judge_asc(p: Path, oeuk_auth: bool) -> dict:
    fr = list(asc_frames(p))
    out: dict = {"frames": len(fr)}
    if oeuk_auth:
        has = lambda i, a, b: any(x == i and _sid(d)[:2] == [a, b] for _, x, d in fr)  # noqa: E731
        out["auth"] = {"27 13": has("7A3", "27", "13"), "67 13": has("7AB", "67", "13"),
                       "27 14": has("7A3", "27", "14"), "67 14": has("7AB", "67", "14")}
    return out


# ============================================================ 판정
def expect_ok(exp: str, outcome: str) -> bool:
    return {"success": outcome == "success", "f4": outcome == "nrc_f4"}.get(exp, False)


def judge_case(pf: Profile, c: dict) -> dict:
    rows = []
    for rule, exp, base in zip(c["rules"], c["expect"], c["files"]):
        log, asc = pf.result / f"{base}.log", pf.result / f"{base}.asc"
        r = {"rule": rule, "expect": exp, "log": log.exists(), "asc": asc.exists(), "png": (pf.result / f"{base}.png").exists()}
        if log.exists():
            r.update(judge_log(log, rule))
            r["ok"] = expect_ok(exp, r["outcome"])
        auth = rule in c.get("oeuk_auth", [])
        if asc.exists():
            r["asc_info"] = judge_asc(asc, auth)
            if auth and "auth" in r["asc_info"]:
                r["ok"] = r.get("ok", False) and all(r["asc_info"]["auth"].values())
        rows.append(r)
    done = all(r.get("ok") is not None for r in rows)
    ok = done and all(r.get("ok") for r in rows)
    last_sw = next((r.get("sw") for r in reversed(rows) if r.get("sw")), "")
    return {"id": c["id"], "name": c["name"], "rows": rows, "done": done, "ok": ok, "sw": last_sw}


def fmt_dur(s):
    return "" if s is None else (f"{int(s)//60}분 {int(s)%60}초" if s >= 60 else f"{int(round(s))}초")


def cmd_judge(pf: Profile, a) -> list[dict]:
    res = [judge_case(pf, c) for c in pf.cases]
    if getattr(a, "json", False):
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return res
    print(f"== 판정  {pf.result}")
    for j in res:
        c = pf.case(j["id"])
        state = "통과" if j["ok"] else ("실패" if j["done"] else "미완")
        print(f"[{state}] {j['id']} {c['name']}  SW {j['sw'] or '-'}")
        for r in j["rows"]:
            exp = {"success": "Success", "f4": "NRC 0xF4"}[r["expect"]]
            got = r.get("outcome", "(로그 없음)")
            extra = []
            if r.get("duration_s") is not None:
                extra.append(fmt_dur(r["duration_s"]))
            ai = r.get("asc_info", {})
            if "auth" in ai:
                extra.append("27 13/14 " + ("OK" if all(ai["auth"].values()) else "없음 " + str(ai["auth"])))
            mark = "OK" if r.get("ok") else ("--" if r.get("ok") is None else "NG")
            print(f"    {mark} {r['rule']:13s} 기대 {exp:8s} 결과 {got:9s} {' · '.join(extra)}")
    bad = [j["id"] for j in res if j["done"] and not j["ok"]]
    todo = [j["id"] for j in res if not j["done"]]
    print(f"\n통과 {sum(j['ok'] for j in res)}/{len(res)}" + (f"  실패 {bad}" if bad else "") + (f"  미완 {todo}" if todo else ""))
    return res


# ============================================================ 이름 규칙
def expected_names(pf: Profile) -> set[str]:
    return {f"{b}{ext}" for c in pf.cases for b in c["files"] for ext in (".asc", ".log", ".png")}


def cmd_names(pf: Profile, a) -> int:
    if not pf.result.exists():
        print(f"결과 폴더 없음: {pf.result}")
        return 1
    want = expected_names(pf)
    have = {p.name for p in pf.result.iterdir() if p.is_file() and p.suffix in (".asc", ".log", ".png")}
    bad = sorted(have - want)
    miss = sorted(want - have)
    for n in bad:
        hint = ""
        if n.count(".asc") > 1 or n.endswith(".asc.asc"):
            hint = "  <- 확장자 중복"
        elif re.search(r"Rule\.(asc|log|png)$", n):
            hint = "  <- 'Rules' 의 s 빠짐"
        print(f"  규칙 밖 이름: {n}{hint}")
    for n in miss:
        print(f"  없음: {n}")
    print(f"이름 검사: 규칙 밖 {len(bad)} / 없음 {len(miss)} / 맞음 {len(have & want)}")
    return 0 if not bad else 1


# ============================================================ status
def cmd_status(pf: Profile, a) -> int:
    print(f"== {pf.raw['project']['name']}  SWP v{pf.swp}  결과 폴더 {pf.result}")
    if not pf.result.exists():
        print("결과 폴더가 아직 없습니다 -> prepare 가 만들거나 직접 만든다")
        return 0
    bins = sorted(p.name for p in pf.result.glob("*.bin"))
    print(f"  bin {len(bins)}개" + (f" ({', '.join(bins)})" if bins else " - identify/bins 로 넣는다"))
    nxt = None
    for c in pf.cases:
        j = judge_case(pf, c)
        files = " ".join(("A" if r["asc"] else "-") + ("L" if r["log"] else "-") + ("P" if r["png"] else "-") for r in j["rows"])
        st = "통과" if j["ok"] else ("실패" if j["done"] else "미완")
        print(f"  {c['id']} [{st}] {files}  {c['name']}  ({'+'.join(c['rules'])}, OEUK {'체크' if c['oeuk'] else '해제'})")
        if not j["done"] and nxt is None:
            nxt = c["id"]
    print("  (A=.asc L=.log P=.png)")
    cmd_names(pf, a)
    if nxt:
        print(f"\n다음 : prepare {nxt}")
    return 0


# ============================================================ identify / bins
def _s19(p: Path) -> dict[int, bytes]:
    mem = {}
    for line in open(p):
        line = line.strip()
        if line[:2] in ("S1", "S2", "S3"):
            al = {"S1": 2, "S2": 3, "S3": 4}[line[:2]]
            n = int(line[2:4], 16)
            mem[int(line[4:4 + 2 * al], 16)] = bytes.fromhex(line[4 + 2 * al:4 + 2 * n - 2])
    return mem


def _digest(mem: dict[int, bytes], secs: list[tuple[int, int]]) -> str:
    h = hashlib.sha256()
    for lo, hi in secs:
        buf = bytearray(b"\xff") * (hi - lo + 1)
        for adr, d in mem.items():
            if adr + len(d) > lo and adr <= hi:
                s, e = max(adr, lo), min(adr + len(d), hi + 1)
                buf[s - lo:e - lo] = d[s - adr:e - adr]
        h.update(buf)
    return h.hexdigest()


def _signed(signed: Path) -> list[dict]:
    out = []
    for x in sorted(signed.rglob("aSIMS_hash_*.xml")):
        t = x.read_text(encoding="utf-8", errors="ignore")
        d = re.search(r'digest="(\w+)"', t)
        secs = [(int(a, 16), int(b, 16)) for a, b in re.findall(r"<section>0x([0-9A-Fa-f]+)-([0-9A-Fa-f]+)--</section>", t)]
        s19 = next(iter(x.parent.glob("aSIMS_enc_signed_*.s19")), None)
        out.append({"dir": x.parent, "xml": x, "digest": d.group(1) if d else "", "secs": secs, "s19": s19,
                    "bin": s19.with_suffix(".bin") if s19 else None})
    return out


def _repo_s19(pf: Profile, folder: str, ref: str | None) -> tuple[Path | None, str]:
    rel = Path(pf.raw["project"]["debug_dir"]) / folder / pf.f(pf.raw["project"]["rom_s19"], folder=folder)
    if not ref:
        p = pf.repo / rel
        return (p if p.exists() else None), "작업 트리"
    tmp = STATE_DIR / "ref" / ref / folder
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / rel.name
    r = subprocess.run(["git", "-C", str(pf.repo), "show", f"{ref}:{rel.as_posix()}"], capture_output=True)
    if r.returncode:
        return None, ref
    out.write_bytes(r.stdout)
    return out, ref


def cmd_identify(pf: Profile, a) -> dict:
    signed = _signed(Path(a.signed))
    if not signed:
        sys.exit(f"{a.signed} 아래에 aSIMS_hash_*.xml 이 없습니다")
    by_digest = {s["digest"]: s for s in signed}
    mapping, bad = {}, []
    print(f"== 서명본 {len(signed)}개  기준 빌드: {a.ref or '작업 트리'}")
    for key, v in pf.variants.items():
        s19, src = _repo_s19(pf, v["folder"], a.ref)
        if not s19:
            print(f"  {key:10s} {v['folder']:12s} 빌드 산출물 없음 ({src})")
            bad.append(key)
            continue
        d = _digest(_s19(s19), signed[0]["secs"])
        hit = by_digest.get(d)
        if hit:
            mapping[key] = hit
            print(f"  {key:10s} {v['folder']:12s} = {hit['dir'].name}")
        else:
            bad.append(key)
            print(f"  {key:10s} {v['folder']:12s} 일치하는 서명본 없음 (digest {d[:12]}) <- 서명 뒤 다시 빌드됐거나 다른 회차")
    extra = [s["dir"].name for s in signed if s not in mapping.values()]
    if extra:
        print(f"  짝 없는 서명본: {extra}")
    if bad:
        print("\n[멈춤] 서명본과 빌드가 맞지 않는 변형이 있습니다. 서명한 빌드 커밋을 --ref 로 주거나, 다시 서명받아야 합니다.")
    else:
        print("\n4벌 모두 서명 해시와 일치")
    return mapping if not bad else {}


def cmd_bins(pf: Profile, a) -> int:
    mapping = cmd_identify(pf, a)
    if not mapping:
        return 1
    pf.result.mkdir(parents=True, exist_ok=True)
    hex2bin = Path(pf.raw["hota"]["studio_dir"]) / "Hex2Binary" / "Hex2Binary.exe"
    for key, s in mapping.items():
        b = s["bin"]
        if not b.exists():
            print(f"  {key}: bin 없음 -> Hex2Binary")
            subprocess.run([str(hex2bin), "-Export", str(s["s19"])], cwd=str(hex2bin.parent), check=False)
            if not b.exists():
                print(f"  [실패] {b} 가 생기지 않았습니다 (FAIL_*Export.log 확인)")
                return 1
        dst = pf.result / b.name
        if dst.exists() and dst.read_bytes() == b.read_bytes():
            print(f"  {key}: {dst.name} 이미 같음")
        else:
            shutil.copy2(b, dst)
            print(f"  {key}: {dst.name} 복사")
    # 케이스별 rom 경로를 기록해 prepare 가 쓴다
    st = {k: str(pf.result / s["bin"].name) for k, s in mapping.items()}
    (pf.result / ".hota_eval_bins.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


# ============================================================ prepare / restore / collect
def _ini_path(pf: Profile, key: str) -> Path:
    return Path(pf.raw["hota"]["studio_dir"]) / pf.raw["hota"][key]


def _backup(pf: Profile) -> None:
    bk = STATE_DIR / "backup"
    bk.mkdir(parents=True, exist_ok=True)
    for k in ("editor_ini", "config_ini"):
        src = _ini_path(pf, k)
        dst = bk / src.name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"  백업 {src.name} -> {dst}")


def _set_ini(p: Path, section: str, key: str, value: str) -> None:
    raw = p.read_bytes()
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig" if raw[:3] == b"\xef\xbb\xbf" else "cp949")
    text = raw.decode(enc)
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    sec, done = None, False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if sec == section and not done:
                lines.insert(i, f"{key}={value}")
                done = True
                break
            sec = s[1:-1]
        elif sec == section and s.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            done = True
    if not done:
        if sec != section:
            lines += [f"[{section}]"]
        lines.append(f"{key}={value}")
    p.write_bytes(nl.join(lines).encode(enc))


def _writable(p: Path) -> bool:
    """Windows 는 os.access 가 ACL 을 보지 않는다 - 실제로 열어 본다 (내용은 바꾸지 않음)."""
    try:
        with open(p, "ab"):
            return True
    except OSError:
        return False


def _clip(text: str) -> None:
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"], input=text.encode("utf-8"),
                       check=False, capture_output=True)
    except OSError:
        pass


def _rom(pf: Profile, c: dict) -> str:
    st = pf.result / ".hota_eval_bins.json"
    if st.exists():
        return json.loads(st.read_text(encoding="utf-8")).get(c["rom"], "")
    return ""


def cmd_prepare(pf: Profile, a) -> int:
    c = pf.case(a.case.split(":")[0])
    rule = a.case.split(":")[1] if ":" in a.case else c["rules"][0]
    if rule not in c["rules"]:
        sys.exit(f"{c['id']} 의 Rules 는 {c['rules']}")
    base = c["files"][c["rules"].index(rule)]
    pf.result.mkdir(parents=True, exist_ok=True)
    asc = pf.result / f"{base}.asc"
    oeuk_note = "OEUK Vehicle " + ("체크" if c["oeuk"] else "해제") + " (H-OTA 화면에서 직접)"
    ini_note = "설정 파일에 넣음. H-OTA Studio 가 떠 있으면 Report Config 창을 다시 열어 반영됐는지 확인"
    if not a.manual and all(_writable(_ini_path(pf, k)) for k in ("editor_ini", "config_ini")):
        _backup(pf)
        _set_ini(_ini_path(pf, "editor_ini"), "TESTREPORT", "ReportFilePath", str(asc))
        want = pf.raw["hota"]["oeuk_on"] if c["oeuk"] else pf.raw["hota"].get("oeuk_off", "")
        if c["oeuk"] or pf.raw["hota"].get("oeuk_off"):
            _set_ini(_ini_path(pf, "config_ini"), "SETVALUE", pf.raw["hota"]["oeuk_key"], want)
            oeuk_note = f"OEUK={want or '(빈 값)'} 로 넣음 - 화면 체크 상태가 {'체크' if c['oeuk'] else '해제'} 인지 확인"
    else:
        _clip(str(asc))
        ini_note = "클립보드에 복사함 - Report Config 의 ... 칸에 붙여 넣기 (설정 파일 직접 수정은 관리자 터미널에서)"
    (STATE_DIR / "last_prepare.json").write_text(json.dumps({"case": c["id"], "rule": rule, "base": base,
        "result": str(pf.result), "t": dt.datetime.now().timestamp()}, ensure_ascii=False), encoding="utf-8")
    rom = _rom(pf, c) or f"(bins 를 먼저 - 변형 {c['rom']})"
    print(f"== {c['id']} {rule}  [{c['group']} 그룹]")
    print(f"  Report Config(.asc) : {asc}")
    print(f"                        <- {ini_note}")
    print(f"  rom                 : {rom}")
    print(f"  targetVersion       : {c['target']}")
    print(f"  {oeuk_note}")
    print(f"  기대                : {dict(zip(c['rules'], c['expect']))[rule]}")
    print(f"  끝나면 Output log 를 {base}.log 로 저장 -> collect {c['id']}:{rule}")
    return 0


def cmd_restore(pf: Profile, a) -> int:
    bk = STATE_DIR / "backup"
    for k in ("editor_ini", "config_ini"):
        dst = _ini_path(pf, k)
        src = bk / dst.name
        if src.exists():
            try:
                shutil.copy2(src, dst)
            except PermissionError:
                print(f"  [권한 없음] {dst} - 관리자 터미널에서 다시 restore")
                return 1
            src.unlink()
            print(f"  되돌림 {dst.name}")
    return 0


def cmd_collect(pf: Profile, a) -> int:
    c = pf.case(a.case.split(":")[0])
    rule = a.case.split(":")[1] if ":" in a.case else c["rules"][-1]
    base = c["files"][c["rules"].index(rule)]
    asc, log, png = (pf.result / f"{base}{e}" for e in (".asc", ".log", ".png"))
    for p in (asc, log):
        print(f"  {'있음' if p.exists() else '없음'} {p.name}")
    for p in pf.result.glob(f"{glob.escape(base)}*"):
        if p.name not in (asc.name, log.name, png.name) and p.suffix in (".asc", ".log"):
            print(f"  [이름 확인] {p.name} - 규칙과 다름 (확장자 중복·s 빠짐?)")
    shot_dir = pf.raw["hota"].get("screenshot_dir")
    if shot_dir and not png.exists():
        last = STATE_DIR / "last_prepare.json"
        t0 = json.loads(last.read_text(encoding="utf-8"))["t"] if last.exists() else 0
        shots = sorted((p for p in Path(shot_dir).glob("*.png") if p.stat().st_mtime > t0), key=lambda p: p.stat().st_mtime)
        if shots:
            shutil.move(str(shots[-1]), png)
            print(f"  캡처 {shots[-1].name} -> {png.name}")
    if log.exists():
        r = judge_log(log, rule)
        exp = dict(zip(c["rules"], c["expect"]))[rule]
        print(f"  판정: 기대 {exp} / 결과 {r['outcome']}  SW {r.get('sw')}  {fmt_dur(r.get('duration_s'))}  -> {'OK' if expect_ok(exp, r['outcome']) else 'NG'}")
    if c.get("reflash_after") and rule == c["rules"][-1]:
        g = c["group"]
        ver = pf.f(pf.raw["cvd"]["group_version"][g])
        print(f"  다음 하위그룹 전 다시 라이팅: cvd-project flash --name {pf.raw['cvd']['name']} --version {ver} --mode IMAGE --banks AB")
    return 0


# ============================================================ report
PS_REPORT = r"""$ErrorActionPreference = 'Stop'
$src = '__SRC__'
$dst = '__DST__'
$ole = @{__OLE__}
$pic = @{__PIC__}
foreach ($p in @($ole.Values + $pic.Values)) { if (-not (Test-Path -LiteralPath $p)) { throw "없음: $p" } }
$x = New-Object -ComObject Excel.Application; $x.Visible = $false; $x.DisplayAlerts = $false
try {
  $wb = $x.Workbooks.Open($src); $ws = $wb.Worksheets.Item(__SHEET__)
  foreach ($k in $ole.Keys) {
    $s = $ws.Shapes.Item($k); $L=$s.Left; $T=$s.Top; $W=$s.Width; $H=$s.Height
    $f = $ole[$k]; $label = Split-Path $f -Leaf
    $n = $ws.OLEObjects().Add([Type]::Missing, $f, $false, $true, [Type]::Missing, [Type]::Missing, $label, $L, $T)
    $n.ShapeRange.LockAspectRatio = 0; $n.Width = $W; $n.Height = $H
    $s.Delete(); $n.Name = $k
    "OLE  $k <- $label"
  }
  foreach ($k in $pic.Keys) {
    $s = $ws.Shapes.Item($k); $L=$s.Left; $T=$s.Top; $W=$s.Width; $H=$s.Height
    $n = $ws.Shapes.AddPicture($pic[$k], 0, -1, $L, $T, $W, $H)
    $s.Delete(); $n.Name = $k
    "PIC  $k <- " + (Split-Path $pic[$k] -Leaf)
  }
__CELLS__
  if ($src -eq $dst) { $wb.Save() } else { $wb.SaveAs($dst, 51) }
  $wb.Close($false)
  "저장: $dst"
} finally { $x.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($x) }
"""


def _resolve_ref(pf: Profile, ref: str, bench: Path | None) -> Path:
    where, fname = ref.split(":", 1)
    if where == "bench":
        if not bench:
            sys.exit("CAN 벤치 결과 첨부가 있어 --bench <joule runs 폴더> 가 필요합니다")
        return bench / fname
    c = pf.case(where)
    return pf.result / f"{c['name']}_{fname}"


def cmd_report(pf: Profile, a) -> int:
    rp = pf.raw["report"]
    dst = pf.result / pf.f(rp["pattern"])
    src = Path(a.template) if a.template else None
    if not src:
        pat = re.sub(r"\{yymmdd\}", "*", rp["pattern"])
        cands = [p for p in pf.result.glob(glob.escape(pat).replace(r"\*", "*")) if p != dst] + ([dst] if dst.exists() else [])
        if not cands:
            sys.exit(f"템플릿(이전 회차 보드평가레포트)이 결과 폴더에 없습니다 - 복사해 오거나 --template")
        src = cands[0]
    out = Path(a.out) if a.out else dst
    if out.exists() and out != src and not a.force:
        sys.exit(f"이미 있음: {out} (--force 로 덮어쓰기)")
    bench = Path(a.bench) if a.bench else None
    q = lambda s: str(s).replace("'", "''")  # noqa: E731
    ole = "; ".join(f"'{k}' = '{q(_resolve_ref(pf, v, bench))}'" for k, v in rp.get("ole", {}).items())
    pic = "; ".join(f"'{k}' = '{q(_resolve_ref(pf, v, bench))}'" for k, v in rp.get("picture", {}).items())
    d = dt.datetime.strptime(pf.date, "%y%m%d")
    cells = []
    if a.fbl:
        cells.append(f"  $ws.Range('{rp['fbl_cell']}').Value2 = 'v{a.fbl}'")
    cells.append(f"  $ws.Range('{rp['app_cell']}').Value2 = 'v{pf.swp}'")
    cells.append(f"  $ws.Range('{rp['date_cell']}').Value2 = [DateTime]::new({d.year},{d.month},{d.day}).ToOADate()")
    ps = (PS_REPORT.replace("__SRC__", q(src)).replace("__DST__", q(out)).replace("__OLE__", ole)
          .replace("__PIC__", pic).replace("__SHEET__", str(rp.get("sheet", 1))).replace("__CELLS__", "\n".join(cells)))
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ps1 = STATE_DIR / "update_report.ps1"
    ps1.write_bytes(b"\xef\xbb\xbf" + ps.encode("utf-8"))
    print(f"템플릿 {src.name} -> {out}")
    if a.dry_run:
        print(f"[미리보기] 스크립트만 만들었습니다: {ps1}")
        return 0
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)], capture_output=True)
    dec = lambda b: next((b.decode(e) for e in ("utf-8", "cp949") if _can(b, e)), b.decode("utf-8", "replace"))  # noqa: E731
    print(dec(r.stdout) + dec(r.stderr))
    if r.returncode:
        return r.returncode
    return verify_report(out, pf, bench)


def _can(b: bytes, enc: str) -> bool:
    try:
        b.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def verify_report(xlsx: Path, pf: Profile, bench: Path | None) -> int:
    """첨부(Ole10Native) 가 결과 파일과 바이트로 같은지. olefile 이 없으면 건너뛴다."""
    try:
        import olefile  # type: ignore
    except ImportError:
        print("검증 건너뜀 (olefile 없음)")
        return 0
    want = {Path(_resolve_ref(pf, v, bench)).name: Path(_resolve_ref(pf, v, bench)).read_bytes()
            for v in pf.raw["report"].get("ole", {}).values()}
    got = {}
    with zipfile.ZipFile(xlsx) as z:
        for n in z.namelist():
            if n.startswith("xl/embeddings/") and n.endswith(".bin"):
                ole = olefile.OleFileIO(io.BytesIO(z.read(n)))
                if ole.exists("\x01Ole10Native"):
                    d = ole.openstream("\x01Ole10Native").read()
                    label_end = d.index(b"\x00", 6)
                    label = d[6:label_end].decode("cp949", "replace")
                    p = d.index(b"\x00", label_end + 1) + 1          # 원본 경로
                    p += 4                                           # 예약 (00 00 03 00)
                    p += 4 + int.from_bytes(d[p:p + 4], "little")    # 임시 경로 길이 + 경로
                    size = int.from_bytes(d[p:p + 4], "little")
                    got[label] = d[p + 4:p + 4 + size]
    ok = sum(1 for k, v in want.items() if got.get(k) == v)
    print(f"첨부 검증: {ok}/{len(want)} 개가 결과 파일과 바이트 동일")
    return 0 if ok == len(want) else 1


# ============================================================ zip
def cmd_zip(pf: Profile, a) -> int:
    z = pf.raw["zip"]
    dest = Path(a.dest) if a.dest else Path(pf.f(z["dest"], issue=a.issue))
    dest.mkdir(parents=True, exist_ok=True)
    pre = pf.f(z["prefix"])
    top = sorted(p for p in pf.result.iterdir() if p.is_file() and not p.name.startswith("."))
    groups = {
        "HOTA_asc": [p for p in top if p.suffix == ".asc"],
        "HOTA_log": [p for p in top if p.suffix == ".log"],
        "HOTA_png": [p for p in top if p.suffix == ".png"],
        "aSIMS_bin": [p for p in top if p.suffix == ".bin"],
        "report_xlsx": [p for p in top if p.suffix == ".xlsx"],
    }
    if a.bench:
        groups["CAN_bench"] = [Path(a.bench) / n for n in ("B-CAN.asc", "Local.asc", "result.txt")]
    for sub in sorted(p for p in pf.result.iterdir() if p.is_dir()):
        groups[sub.name] = sorted(q for q in sub.iterdir() if q.is_file())
    used = {p for v in groups.values() for p in v}
    left = [p.name for p in top if p not in used]
    for g, items in groups.items():
        if not items:
            continue
        out = dest / f"{pre}{g}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in items:
                zf.write(p, p.name)
        assert zipfile.ZipFile(out).testzip() is None
        print(f"  {out.name}  {len(items)}개  {out.stat().st_size / 1e6:.1f} MB")
    print(f"빠진 파일: {left or '없음'}  -> {dest}")
    return 0


# ============================================================ summary
def cmd_summary(pf: Profile, a) -> int:
    res = [judge_case(pf, c) for c in pf.cases]
    title = {"A": "HE1I", "B": "TEST"}
    print("| # | 시나리오 | 기대 | 실제 | 소요 시간 | 비고 |")
    print("|---|---|---|---|---|---|")
    for j in res:
        c = pf.case(j["id"])
        kind = "External" if c["rules"] == ["ExternalRules"] else "BG→Repro"
        updown = "업" if c["expect"][-1] == "success" and not c["oeuk"] else ("강제 다운 (OEUK)" if c["oeuk"] else "다운")
        exp = " / ".join({"success": "Success", "f4": "NRC 0xF4"}[e] for e in c["expect"]) + (" + 27 13/14" if c.get("oeuk_auth") else "")
        got = " / ".join({"success": "Success", "nrc_f4": "NRC 0xF4"}.get(r.get("outcome", "-"), r.get("outcome", "-")) for r in j["rows"])
        auth_rows = [r for r in j["rows"] if r["rule"] in c.get("oeuk_auth", [])]
        if auth_rows and all(all(r.get("asc_info", {}).get("auth", {"x": False}).values()) for r in auth_rows):
            got += " + 27 13/14"
        durs = [fmt_dur(r.get("duration_s")) for r in j["rows"]]
        dur = durs[0] if len(durs) == 1 else f"BG {durs[0]} · Repro {durs[1]}"
        note = f"SW {j['sw']}" if j["sw"] else ""
        print(f"| {c['id']} | {title.get(c['group'], c['group'])} · {kind} · {updown} | {exp} | {got} | {dur} | {note} |")
    ok = all(j["ok"] for j in res)
    print(f"\n판정 : {'통과' if ok else '미완/실패 있음'} — A 그룹 다운그레이드는 0xF4 로 차단, B 그룹 OEUK 강제 다운그레이드 성공 (대칭성)")
    return 0


# ============================================================ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="he1i_psu")
    ap.add_argument("--swp", help="APP SWP 버전 (예 3.0.29). 없으면 저장소 .project 에서")
    ap.add_argument("--date", help="결과 폴더 YYMMDD (없으면 오늘)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status")
    p = sp.add_parser("judge"); p.add_argument("--json", action="store_true")
    sp.add_parser("names")
    for n in ("identify", "bins"):
        p = sp.add_parser(n); p.add_argument("--signed", required=True, help="aSIMS 서명본 폴더들이 있는 상위 폴더")
        p.add_argument("--ref", help="서명한 빌드 커밋 (없으면 작업 트리 Debug 폴더)")
    p = sp.add_parser("prepare"); p.add_argument("case", help="A1 / A3:BGRules 처럼")
    p.add_argument("--manual", action="store_true", help="설정 파일을 건드리지 않고 경로만 클립보드로")
    sp.add_parser("restore")
    p = sp.add_parser("collect"); p.add_argument("case")
    p = sp.add_parser("report"); p.add_argument("--template"); p.add_argument("--out"); p.add_argument("--bench")
    p.add_argument("--fbl", help="FBL 버전 (예 3.0.19) - 헤더에 넣는다"); p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p = sp.add_parser("zip"); p.add_argument("--issue", required=True); p.add_argument("--bench"); p.add_argument("--dest", help="출력 폴더 (기본: 프로필 [zip] dest)")
    sp.add_parser("summary")
    a = ap.parse_args()
    pf = Profile(a.profile, a.swp, a.date)
    fn = {"status": cmd_status, "judge": cmd_judge, "names": cmd_names, "identify": cmd_identify, "bins": cmd_bins,
          "prepare": cmd_prepare, "restore": cmd_restore, "collect": cmd_collect, "report": cmd_report,
          "zip": cmd_zip, "summary": cmd_summary}[a.cmd]
    r = fn(pf, a)
    return r if isinstance(r, int) else 0


if __name__ == "__main__":
    sys.exit(main())
