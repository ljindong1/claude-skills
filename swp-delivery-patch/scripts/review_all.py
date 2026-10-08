#!/usr/bin/env python3
"""패치 적용 후 검수를 한 번에 돌리고 검수 보고서(markdown) 한 장을 만든다.

같은 폴더의 검수 스크립트를 순서대로 부르고 결과를 모아, 맨 위에 항목별 판정 요약표,
아래에 상세 출력, 마지막에 '정적 검수로 확인 못 한 것'을 붙인다. 아무것도 수정하지 않는다.

정적 검수 (빌드 전에도 가능)
  1. 설정 재대조      three_way.py --check  — HAE 변경 중 아직 Cur 와 다른 항목 (판정표 사유와 1:1 이어야 함)
  2. 모듈 일치        교체한 모듈 폴더 vs HAE Cur 바이트 비교 — 다른 파일 = 병합한 당사 수정(의도) 또는 누락
  3. 당사 코드 영향   symbol_crosscheck.py — 심볼 삭제·선언 변화, 구조체 멤버 변화, 새 #if 매크로
  4. 버전 잔존        version_bump_check.py
  5. 의존 버전 목록   Static_Code 의 .ver 목록 (IM 의존성 요구와 대조용)
빌드 검수 (인자를 주면)
  6. 빌드 비교        jenkins_wait.py --compare
  7. 생성물 diff      gen_diff_review.py
  8. 메모리           map_mem.py

사용 예 (HE1i APP V3.0.29):
  python review_all.py --prev <배포본>/VersionComparison/PreviousVersion --cur <배포본>/VersionComparison/CurrentVersion \
      --app D:/Mobase/psu_master/psu_app --old-token v3_0_28 --new-token v3_0_29 \
      --expect .project References/Doc_MB/01_CRT_UTIP_CFG/aSIMs_sample_ini.ini \
      --job HE1i_PSU_AUTOSAR_jdlee --build 31 --compare 28 \
      --gen-old 7ccc547ff --gen-new 77acb016b \
      --map-old 7ccc547ff:psu_app/Debug/OEUK_HE1I/26810/he1i_psu_app_v3_0_28.map \
      --map-new psu_app/Debug/OEUK_HE1I/26810/he1i_psu_app_v3_0_29.map \
      --out 검수보고서.md
--modules 를 생략하면 Cur 의 Static_Code/Modules 아래 폴더를 모두 대상으로 한다.
모듈별 심볼 접두는 폴더명에서 만든다(Dcm_R44 → Dcm_ / DCM_). 다르면 --modules Dcm_R44:Dcm_:DCM_ 처럼 준다.
"""
import argparse, datetime, io, os, re, subprocess, sys, tempfile, zlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *map(str, args)], capture_output=True, env=env)
    out = r.stdout.decode("utf-8", "replace") + (("\n[stderr]\n" + r.stderr.decode("utf-8", "replace")) if r.returncode and r.stderr else "")
    return r.returncode, out.strip()


def git(root, *args, binary=False):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()


def files(root):
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def crc(p):
    return zlib.crc32(open(p, "rb").read()) & 0xFFFFFFFF


def module_specs(a):
    mods = []
    if a.modules:
        for m in a.modules:
            parts = m.split(":")
            name = parts[0]
            base = re.sub(r"_R4[0-9X]$", "", name)
            pre = parts[1] if len(parts) > 1 else base + "_"
            mac = parts[2] if len(parts) > 2 else pre.upper()
            mods.append((name, pre, mac))
    else:
        d = os.path.join(a.cur, "Static_Code", "Modules")
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if os.path.isdir(os.path.join(d, name)):
                    base = re.sub(r"_R4[0-9X]$", "", name)
                    mods.append((name, base + "_", (base + "_").upper()))
    return mods


def map_path(spec, repo, tmpdir):
    """'REV:path' 이면 git show 로 꺼내고, 아니면 파일 경로(상대면 repo 기준)."""
    if spec and ":" in spec and not re.match(r"^[A-Za-z]:[\\/]", spec):
        rev, path = spec.split(":", 1)
        data = git(repo, "show", f"{rev}:{path}", binary=True)
        p = os.path.join(tmpdir, rev + "_" + os.path.basename(path))
        open(p, "wb").write(data)
        return p
    if spec and not os.path.isabs(spec):
        return os.path.join(repo, spec)
    return spec


def main():
    ap = argparse.ArgumentParser(description="패치 검수 일괄 실행·보고서 생성")
    ap.add_argument("--prev", required=True, help="HAE 이전 형상 루트 (VersionComparison/PreviousVersion)")
    ap.add_argument("--cur", required=True, help="HAE 현재 형상 루트 (VersionComparison/CurrentVersion)")
    ap.add_argument("--app", required=True, help="당사 앱(또는 FBL) 루트 — Build/, Configuration/ 이 있는 폴더")
    ap.add_argument("--repo", help="git 루트 (기본: --app 에서 찾음)")
    ap.add_argument("--modules", nargs="*")
    ap.add_argument("--old-token")
    ap.add_argument("--new-token")
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--job")
    ap.add_argument("--build")
    ap.add_argument("--compare")
    ap.add_argument("--gen-old")
    ap.add_argument("--gen-new")
    ap.add_argument("--gen-path", help="Generated 경로 (git 루트 기준, 기본: <app 상대>/Generated)")
    ap.add_argument("--map-old")
    ap.add_argument("--map-new")
    ap.add_argument("--out", default="검수보고서.md")
    a = ap.parse_args()

    repo = a.repo or git(a.app, "rev-parse", "--show-toplevel") or a.app
    app_rel = os.path.relpath(os.path.abspath(a.app), os.path.abspath(repo)).replace(os.sep, "/")
    rows, detail = [], []

    def add(no, name, verdict, summary, body):
        rows.append((no, name, verdict, summary))
        detail.append(f"### {no}. {name}\n\n```\n{body.strip()[:20000]}\n```\n")
        print(f"[{verdict}] {no}. {name} — {summary}")

    # 1. 설정 재대조
    _, out = run("three_way.py", "--prev", a.prev, "--cur", a.cur, "--ours", a.app, "--check", "--max", "40")
    m = re.search(r"== 요약: (.*)", out)
    s = m.group(1) if m else "?"
    seq_warn = out.count("⚠")
    left = 0 if "차이 없음" in s else sum(int(x) for x in re.findall(r"(\d+)", s))
    add(1, "설정 재대조 (HAE 변경 중 Cur 와 다른 항목)", "확인" if left else "통과",
        (f"남은 항목 {left} ({s})" + (f", 순번 경고 {seq_warn}" if seq_warn else "") + " — 판정표 제외·보류·당사 구성 사유와 1:1 인지 확인") if left else "남은 항목 없음", out)

    # 2. 모듈 일치 / 3. 당사 코드 영향
    mods = module_specs(a)
    mod_lines, sym_lines, mod_bad, sym_flags = [], [], 0, 0
    for name, pre, mac in mods:
        c = os.path.join(a.cur, "Static_Code", "Modules", name)
        o = os.path.join(a.app, "Static_Code", "Modules", name)
        p = os.path.join(a.prev, "Static_Code", "Modules", name)
        if not os.path.isdir(o):
            mod_lines.append(f"{name}: 당사 저장소에 폴더 없음")
            mod_bad += 1
            continue
        C, O = files(c), files(o)
        diff = [k for k in sorted(set(C) & set(O)) if crc(C[k]) != crc(O[k])]
        only_c, only_o = sorted(set(C) - set(O)), sorted(set(O) - set(C))
        mod_lines.append(f"{name}: Cur 와 같은 파일 {len(set(C) & set(O)) - len(diff)} / 다름 {len(diff)} / Cur 에만 {len(only_c)} / 당사에만 {len(only_o)}")
        for k in diff + [f"(Cur 에만) {x}" for x in only_c] + [f"(당사에만) {x}" for x in only_o]:
            mod_lines.append(f"    {k}")
        if diff or only_c or only_o:
            mod_bad += 1
        if os.path.isdir(p):
            _, so = run("symbol_crosscheck.py", "--prev", p, "--cur", c, "--app", a.app, "--prefix", pre, "--macro", mac)
            sym_lines.append(f"===== {name} ({pre}, {mac})\n{so}")
            g = re.search(r"삭제 (\d+) / 선언 줄 변화 (\d+)", so)
            if (g and int(g.group(1))) or "★정의 안 됨" in so or "중간 변경" in so:
                sym_flags += 1
        else:
            sym_lines.append(f"===== {name}: Prev 모듈 없음 — 신규 모듈, 심볼 대조 생략")
    add(2, "모듈 폴더 vs HAE Cur 바이트 일치", "확인" if mod_bad else "통과",
        f"대상 {len(mods)}개 모듈, 차이 있는 모듈 {mod_bad} — 다른 파일은 병합한 당사 수정인지 누락인지 확인" if mod_bad else f"대상 {len(mods)}개 모듈 모두 일치",
        "\n".join(mod_lines) or "대상 모듈 없음")
    add(3, "당사 코드 영향 (심볼·구조체·#if 매크로)", "확인" if sym_flags else "통과",
        f"주의 모듈 {sym_flags} — 삭제 심볼, 중간 변경 구조체, 정의 안 된 매크로 확인" if sym_flags else "삭제 심볼·정의 안 된 새 매크로·중간 변경 구조체 없음 (선언 줄 변화는 상세에서 확인)",
        "\n\n".join(sym_lines) or "대상 없음")

    # 4. 버전 잔존
    if a.old_token and a.new_token:
        _, out = run("version_bump_check.py", a.app, a.old_token, a.new_token, *(["--expect", *a.expect] if a.expect else []))
        ok = "== 판정: 통과" in out
        add(4, f"버전 잔존 ({a.old_token} → {a.new_token})", "통과" if ok else "확인", "이전 토큰 잔존 0, 기대 위치 누락 없음" if ok else "잔존 또는 누락 있음", out)

    # 5. 의존 버전 목록
    vers = []
    for sub in ("Static_Code/Modules", "Static_Code/Integration_Code"):
        d = os.path.join(a.app, *sub.split("/"))
        for dp, _, fs in os.walk(d):
            for f in fs:
                if f.endswith(".ver"):
                    vers.append(os.path.relpath(os.path.join(dp, f), a.app).replace(os.sep, "/"))
    add(5, "의존 모듈 버전 (.ver 목록)", "수동", f"{len(vers)}개 — IM '모듈 버전별 변경사항'의 의존성 요구와 대조", "\n".join(sorted(vers)) or "없음")

    # 6~8 빌드 검수
    if a.job and a.build:
        args = [a.job, a.build] + (["--compare", a.compare] if a.compare else [])
        _, out = run("jenkins_wait.py", *args)
        res = re.search(r"#\S+: (\S+)", out)
        bad = (not res or res.group(1) != "SUCCESS") or "Error 0 /" not in out or "SAFERTE_ERR 0" not in out.split("== 비교")[0] \
              or "Rte Validation 다름" in out or ("증감: 없음" not in out and a.compare) or "Validation 오류 코드: 없음" not in out
        add(6, f"빌드 #{a.build}" + (f" vs #{a.compare}" if a.compare else ""), "확인" if bad else "통과",
            "결과·생성기·Rte·SAFERTE 중 직전과 다른 점 있음 — 상세 확인" if bad else "SUCCESS, 생성기 Error 0, Rte Validation·SAFERTE 직전과 동일", out)
    if a.gen_old and a.gen_new:
        gp = a.gen_path or (f"{app_rel}/Generated" if app_rel not in (".", "") else "Generated")
        _, out = run("gen_diff_review.py", repo, a.gen_old, a.gen_new, "--path", gp, "--lines", "30")
        arx = out.count("★내용 변경")
        cfiles = re.findall(r"\[C/H\] (\S+): 실제 변경 (\d+)줄", out)
        add(7, "생성물 diff", "확인" if (arx or cfiles) else "통과",
            (f"내용이 바뀐 ARXML {arx}, 실제 변경 C/H {len(cfiles)}개({', '.join(os.path.basename(f) for f, _ in cfiles)}) — 판정표·모듈 업데이트로 설명되는지 확인")
            if (arx or cfiles) else "C/H·ARXML 실질 변경 없음", out)
    if a.map_old and a.map_new:
        with tempfile.TemporaryDirectory() as td:
            _, out = run("map_mem.py", map_path(a.map_old, repo, td), map_path(a.map_new, repo, td))
        add(8, "메모리 (map 섹션 합계)", "수동", " / ".join(l.strip() for l in out.splitlines()[:2]), out)

    # 보고서
    unchecked = [
        "실기 동작 — 라이팅·CAN·진단 회귀·패치 고유 시험(수평전개 재현 조건)·H-OTA (S12)",
        "모듈 신규 Validation 규칙의 사전 점검 — IM 의 신규 ERR 코드별 조건을 당사 Ecud 에 적용 (규칙별 수동/임시 스크립트)",
        "의존 모듈 버전이 IM 요구 이상인지 — 5번 목록과 IM 대조",
        "모듈 내부 동작 변경이 당사 진단·기능에 미치는 영향 — 공개 API·심볼이 같아도 동작은 실기로만 확인",
    ]
    if not (a.job and a.build):
        unchecked.insert(0, "빌드 결과 (Generate·Rte Validation·SAFERTE) — --job/--build 로 다시 실행")
    if not (a.gen_old and a.gen_new):
        unchecked.insert(1, "생성물 diff — 빌드 후 --gen-old/--gen-new 로 다시 실행")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    head = [f"# 패치 검수 보고서 ({now})", "",
            f"- 당사: `{a.app}` (git `{git(repo, 'rev-parse', '--short', 'HEAD')}`)",
            f"- HAE Prev: `{a.prev}`", f"- HAE Cur: `{a.cur}`", "",
            "## 요약", "", "| # | 검수 항목 | 판정 | 내용 |", "|---|---|---|---|"]
    head += [f"| {n} | {name} | {v} | {s.replace('|', '/')} |" for n, name, v, s in rows]
    head += ["", "판정: 통과 = 기준 충족 / 확인 = 사람이 사유를 확인해야 함(오류라는 뜻은 아님) / 수동 = 자료만 모음", "",
             "## 정적 검수로 확인하지 못한 것", ""] + [f"- {u}" for u in unchecked] + ["", "## 상세", ""]
    open(a.out, "w", encoding="utf-8").write("\n".join(head) + "\n" + "\n".join(detail))
    print(f"\n보고서: {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
