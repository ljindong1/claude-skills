#!/usr/bin/env python3
"""HAE 배포본의 patch_tool 을 실행하지 않고 읽어서, 이번 패치에서 돌 스크립트와 그 내용을 계획서로 만든다 (P 단계).

  python patch_tool_plan.py --pkg <배포본 루트(patch_tool 이 있는 폴더)> [--app <당사 앱 루트>] [--part FBL|APP] [--out 계획.md]

무엇을 보여 주나
  1. 패치 대상 모듈과 버전 — patch_manifest.json 의 current→target 과 당사 .ver 의 현재 버전을 대조
     (당사 버전이 HAE 기준 프로젝트와 다르면 버전 스크립트 범위가 달라진다)
  2. 실제 실행 순서 — script_collector.py 규칙 그대로 (manifest 의 scripts 목록은 쓰이지 않고 순서도 다르다)
       clear_harmonize → Os_* → Integrator common → 모듈(common + 버전 스크립트 current < v <= target)
       → integration_MemMap → Fota → EcucValueCollection common → SCons common → ValidationChecker common → SCons 버전
  3. 스크립트마다 — docstring 의 Changes / Checklist(☑ 항목) / IM 링크, requestHarmonize·GenPatch·PostPatch 호출,
     report_action 의 대상·사유(실행 때 실제로 바뀔 수 있는 위치)
  4. 공통 스크립트 항목 — [FBL only] / APP only / MCU 표시를 붙여 당사 해당 여부 판단을 돕는다
  5. 툴이 하는데 Jenkins 빌드는 하지 않는 일 — GenerateAll 전 Generated/Debug 삭제, Harmonize 앞뒤 보정, orphan 파라미터 삭제

이 결과는 "HAE 가 이번에 무엇을 자동으로 바꾸려 하는지"의 목록이다. 그대로 적용하지 않는다 — 판정표 행으로 올려 3-way 판정을 거친다.
"""
import argparse, ast, io, json, os, re, sys, warnings

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
warnings.filterwarnings("ignore")

OTHER_MCU = {"CYT": ("S32K", "S32G", "TC3", "TC2", "U2A", "U5L", "RH850", "TCC"),
             "S32K": ("CYT", "TC3", "U2A", "U5L", "RH850", "TCC"),
             "TC3": ("CYT", "S32K", "S32G", "U2A", "U5L", "RH850", "TCC")}


def vkey(s):
    """'2.1.1.0_HF4' -> ((2,1,1,0), 4). HF 없으면 0."""
    if not s:
        return None
    m = re.match(r"(\d+(?:\.\d+)*)(?:[._-]?HF(\d+))?", s, re.I)
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split(".")), int(m.group(2) or 0)


def ver_from_name(fname, prefix):
    m = re.match(rf"patch_{re.escape(prefix)}_[vV](.+)\.py$", fname)
    if not m:
        return None
    s = m.group(1)
    hf = re.search(r"_HF(\d+)$", s, re.I)
    base = s[:hf.start()] if hf else s
    return base.replace("_", ".") + (f"_HF{hf.group(1)}" if hf else "")


def find_mod_dir(mp, name):
    cands = [name, name + "_Common", re.sub(r"_R\d+$", "", name)]
    low = {d.lower(): d for d in os.listdir(mp)}
    for c in cands:
        if c.lower() in low:
            return os.path.join(mp, low[c.lower()])
    return None


def our_version(app, target_path, name):
    if not app or not target_path:
        return None
    d = os.path.join(app, *target_path.split("/"))
    if not os.path.isdir(d):
        return None
    for f in os.listdir(d):
        m = re.match(rf"{re.escape(os.path.basename(d))}-(.+)\.ver$", f)
        if m:
            return m.group(1)
    return None


def doc_info(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"doc": "", "calls": [], "acts": []}
    doc = ast.get_docstring(tree) or ""
    calls, acts = [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func.id if isinstance(n.func, ast.Name) else (n.func.attr if isinstance(n.func, ast.Attribute) else "")
            if fn.startswith("request") and n.args:
                a0 = n.args[0]
                calls.append(f"{fn}({a0.value!r})" if isinstance(a0, ast.Constant) else f"{fn}(…)")
            if fn == "report_action":
                kw = {}
                for k in n.keywords:
                    v = k.value
                    kw[k.arg] = v.value if isinstance(v, ast.Constant) else ("f'…'" if isinstance(v, ast.JoinedStr) else "…")
                acts.append(kw)
    return {"doc": doc, "calls": sorted(set(calls)), "acts": acts}


def section(doc, title, stop=("Checklist", "References", "────", "Execution", "Background", "Note")):
    lines = doc.splitlines()
    out, on = [], False
    for l in lines:
        s = l.strip()
        if not on and s.lower().startswith(title.lower()):
            on = True
            rest = s[len(title):].strip(" :")
            if rest:
                out.append(rest)
            continue
        if on:
            if any(s.startswith(x) for x in stop):
                break
            out.append(l.rstrip())
    while out and not out[-1].strip():
        out.pop()
    return out


def relevance(text, part, mcu, head=None):
    t = text
    notes = []
    h = head if head is not None else text
    if re.search(r"FBL only", t, re.I) and part == "APP":
        notes.append("FBL 전용 → APP 해당 없음")
    if re.search(r"(APP|RTSW) only", t, re.I) and part == "FBL":
        notes.append("APP 전용 → FBL 해당 없음")
    if mcu:
        others = [m for m in OTHER_MCU.get(mcu, ()) if re.search(rf"\b{m}", h)]
        if others and not re.search(rf"\b{mcu}", h, re.I):
            notes.append(f"{'/'.join(others)} 전용 추정 → {mcu} 해당 없음")
    return notes


def detect_mcu(app):
    if not app:
        return None
    mods = " ".join(os.listdir(os.path.join(app, "Static_Code", "Modules"))) if os.path.isdir(os.path.join(app, "Static_Code", "Modules")) else ""
    for k, pat in (("CYT", "CYT"), ("S32K", "S32K"), ("TC3", "TC3")):
        if pat.lower() in mods.lower():
            return k
    return None


def main():
    ap = argparse.ArgumentParser(description="patch_tool 정적 분석 → 패치 계획서")
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--app")
    ap.add_argument("--part", choices=["FBL", "APP"])
    ap.add_argument("--mcu")
    ap.add_argument("--out")
    ap.add_argument("--changes-lines", type=int, default=25)
    ap.add_argument("--search", action="append",
                    help="전체 module_patch 에서 이 단어가 나오는 스크립트·줄을 찾는다(여러 번 가능). 패치 대상이 아닌 모듈 버전에서 온 규칙을 찾을 때")
    a = ap.parse_args()

    pt = os.path.join(a.pkg, "patch_tool") if os.path.isdir(os.path.join(a.pkg, "patch_tool")) else a.pkg
    mp = os.path.join(pt, "module_patch")
    man = json.load(open(os.path.join(pt, "patch_manifest.json"), encoding="utf-8"))
    part = a.part or ("FBL" if "_fbl" in man.get("project_name", "").lower() else "APP")
    mcu = a.mcu or detect_mcu(a.app)
    L = []
    w = L.append

    nfiles = sum(len(fs) for _, _, fs in os.walk(pt))
    w(f"# patch_tool 계획서 — {man.get('patch_version')} ({man.get('ar_version')}), HAE 기준 프로젝트 `{man.get('project_name')}`")
    w("")
    w(f"- patch_tool: `{pt}` (파일 {nfiles}개) — **배포본마다 스크립트 묶음이 다르다. 이 배포본의 것만 기준으로 삼는다**")
    w(f"- 대상: {part}" + (f", MCU {mcu}" if mcu else "") + (f", 당사 앱 `{a.app}`" if a.app else ""))
    w("- 이 목록은 HAE 툴이 **자동으로 바꾸려는 것**이다. 그대로 적용하지 말고 판정표 행으로 올려 3-way 판정한다.")
    w("")

    # 1. 모듈·버전
    w("## 1. 패치 대상 모듈과 버전")
    w("")
    w("| 모듈 | HAE 기준 현재 | 대상 | 당사 현재(.ver) | 비고 |")
    w("|---|---|---|---|---|")
    mods = []
    for m in man.get("modules", []):
        ours = our_version(a.app, m.get("target_path", ""), m["name"])
        cur = ours or m.get("current_version", "")
        note = ""
        if ours and ours != m.get("current_version"):
            note = "**당사 버전이 HAE 기준과 다름 → 버전 스크립트 범위를 당사 기준으로 계산**"
        kt0, ko0 = vkey(m.get("target_version", "")), vkey(ours or "")
        if ours and kt0 and ko0 and ko0 >= kt0:
            cur = m.get("current_version", "")
            note = "당사가 이미 대상 버전 이상 — 수작업 적용분 대조용으로 HAE 기준 범위의 스크립트를 보여 준다"
        w(f"| {m['name']} | {m.get('current_version','')} | {m.get('target_version','')} | {ours or '(확인 안 됨)'} | {note} |")
        mods.append((m["name"], cur, m.get("target_version", "")))
    w("")

    # 2. 실행 순서
    order = []  # (kind, label, path)
    def add(kind, label, rel):
        p = os.path.join(mp, *rel.split("/"))
        if os.path.exists(p):
            order.append((kind, label, p))
    add("공통", "Harmonize JSON 초기화", "_harmonize/clear_harmonize_json.py")
    mod_scripts = {}
    for name, cur, tgt in mods:
        d = find_mod_dir(mp, name)
        if not d:
            mod_scripts[name] = (None, [], [])
            continue
        pre = os.path.basename(d)
        common = os.path.join(d, f"patch_{pre}_common.py")
        sub = os.path.join(d, "R44") if os.path.isdir(os.path.join(d, "R44")) else d
        vs = []
        for f in os.listdir(sub):
            v = ver_from_name(f, pre)
            if v:
                vs.append((vkey(v), v, os.path.join(sub, f)))
        vs.sort()
        kc, kt = vkey(cur), vkey(tgt)
        sel = [x for x in vs if (kc is None or x[0] > kc) and (kt is None or x[0] <= kt)]
        extra = sorted(os.path.join(d, f) for f in os.listdir(d) if re.match(rf"(gen|post|post_genall)_{re.escape(pre)}", f))
        mod_scripts[name] = (common if os.path.exists(common) else None, sel, extra)
    def add_mod(name):
        c, sel, extra = mod_scripts.get(name, (None, [], []))
        if c:
            order.append(("모듈", f"{name} common", c))
        for _, v, p in sel:
            order.append(("모듈", f"{name} v{v}", p))
    for name, _, _ in mods:
        if name.startswith("Os_"):
            add_mod(name)
    add("공통", "Integrator common (모든 패치에서 실행)", "Integrator/patch_Integrator_common.py")
    for name, _, _ in mods:
        if not name.startswith("Os_") and name not in ("integration_MemMap", "Fota"):
            add_mod(name)
    for name in ("integration_MemMap", "Fota"):
        if any(n == name for n, _, _ in mods):
            add_mod(name)
    add("공통", "EcucValueCollection common", "EcucValueCollection/patch_EcucValueCollection_common.py")
    add("공통", "SCons common", "SCons/patch_SCons_common.py")
    add("공통", "ValidationChecker common (ECM VC 항목 자동 수정)", "ValidationChecker/patch_ValidationChecker_common.py")

    w("## 2. 실제 실행 순서 (script_collector 규칙)")
    w("")
    w("manifest 의 `scripts` 목록은 실행에 쓰이지 않는다(순서도 다르다). 아래가 툴이 실제로 도는 순서다. SCons 버전 스크립트는 toolset_scons 버전에 따라 끝에 붙는다.")
    w("")
    for i, (k, lab, p) in enumerate(order, 1):
        w(f"{i}. [{k}] {lab} — `{os.path.relpath(p, pt)}`")
    for name, (c, sel, extra) in mod_scripts.items():
        if extra:
            w(f"   - {name} 조건부 스크립트(요청이 있을 때만): " + ", ".join(f"`{os.path.basename(x)}`" for x in extra))
        if c is None and not sel and not extra:
            w(f"   - {name}: module_patch 에 스크립트 없음 — 모듈 교체만")
    w("")

    # 3. 모듈 스크립트 상세
    w("## 3. 모듈 스크립트 — 바꾸려는 것")
    w("")
    req_all = set()
    for k, lab, p in order:
        if k != "모듈":
            continue
        info = doc_info(p)
        req_all.update(info["calls"])
        w(f"### {lab} (`{os.path.basename(p)}`)")
        w("")
        ch = section(info["doc"], "Changes") or section(info["doc"], "Actions") or info["doc"].splitlines()[:8]
        if ch:
            w("```")
            w("\n".join(ch[:a.changes_lines]) + ("\n…(생략)" if len(ch) > a.changes_lines else ""))
            w("```")
        chk = [l.strip() for l in info["doc"].splitlines() if l.strip().startswith("☑")]
        if chk:
            w("- Checklist ☑: " + " / ".join(chk))
        ims = sorted(set(re.findall(r"https://ecody-ecm\.autoever\.com/\S+", info["doc"])))
        if ims:
            w("- IM: " + " ".join(ims))
        if info["calls"]:
            w("- 요청: " + ", ".join(info["calls"]))
        acts = [x for x in info["acts"] if x.get("target") not in (None, "…", "f'…'")]
        if acts:
            w("- report_action 대상(실행 때 조건에 맞으면 바뀜):")
            for x in acts[:30]:
                w(f"  - {x.get('action','?')} · `{x.get('target')}`" + (f" — {x.get('reason')}" if isinstance(x.get('reason'), str) and len(x.get('reason')) < 120 else ""))
        rel = relevance(info["doc"], part, mcu)
        if rel:
            w("- 해당 여부: " + "; ".join(rel))
        w("")

    # 4. 공통 스크립트 항목
    w("## 4. 공통 스크립트 항목 — 모든 패치에서 자동 적용되는 HAE 보정")
    w("")
    w("항목마다 당사 설정이 이미 그런지, 당사가 일부러 다르게 둔 것인지(보호 설정) 판정표에서 확인한다. 표시는 docstring 문구로만 판단한 것이라 **추정**이다.")
    w("")
    for k, lab, p in order:
        if k != "공통" or "clear_harmonize" in p:
            continue
        info = doc_info(p)
        req_all.update(info["calls"])
        w(f"### {lab}")
        w("")
        doc = info["doc"].splitlines()
        items, cur = [], None
        for l in doc:
            s = l.strip()
            if re.match(r"^(\[.+\]|\d+[a-z]?[\).]|\d+-\d+\.|VC-\d+)", s):
                if cur:
                    items.append(cur)
                cur = [s]
            elif cur is not None and s and not s.startswith(("────", "Checklist", "☐", "☑", "References", "Execution", "Background")):
                cur.append(s)
            elif s.startswith(("────", "Checklist")):
                if cur:
                    items.append(cur); cur = None
        if cur:
            items.append(cur)
        merged = []
        for it in items:
            if merged and merged[-1][0].startswith("[") and len(merged[-1]) == 1 and re.match(r"^\d+[a-z]?\)", it[0]):
                merged[-1] = [it[0] + "  " + merged[-1][0]] + it[1:]
            else:
                merged.append(it)
        chk = [l.strip() for l in doc if l.strip().startswith("☑")]
        tag = {}
        for c in chk:
            for grp, who in re.findall(r"((?:\[\d+\])+)\s*([A-Za-z/ ]*only)", c):
                for n in re.findall(r"\d+", grp):
                    tag.setdefault(n, []).append(who.strip())
        for it in merged:
            head = it[0]
            body = " ".join(it[1:])
            num = re.match(r"^(\d+)", head)
            tags = tag.get(num.group(1), []) if num else []
            rel = relevance(head + " " + body + " " + " ".join(tags), part, mcu, head=head + " " + " ".join(tags))
            vc = re.match(r"^VC-(\d+)", head)
            extra = f" (ECM IA-{vc.group(1)} 대응 추정)" if vc else ""
            w(f"- {head}{extra}" + (f"  [{', '.join(tags)}]" if tags else "") + (f"  — _{'; '.join(rel)}_" if rel else ""))
            if body:
                w(f"  - {body[:300]}{'…' if len(body) > 300 else ''}")
        if chk:
            w("- Checklist ☑: " + " / ".join(chk))
        d = os.path.dirname(p)
        cond = sorted(f for f in os.listdir(d) if re.match(r"(gen|post|post_genall)_", f))
        if cond:
            w("- 같은 폴더의 조건부 스크립트(요청 시 GenerateXml/GenerateAll 뒤에 실행): " + ", ".join(f"`{f}`" for f in cond))
        w("")

    # 5. 파이프라인 사실
    w("## 5. 툴이 하는데 당사 Jenkins 빌드는 하지 않는 일")
    w("")
    w("- **GenerateAll 직전에 `Generated/`·`Debug/` 를 통째로 지운다**(build_executor). Jenkins Build 는 지우지 않으므로, 모듈을 빼면 이전 생성물이 남아 컴파일된다 → `gen_stale_check.py`.")
    w("- **모듈 교체는 폴더 삭제 후 통째 복사**, Integration_Code 하위 폴더 통째 교체, Reference_Code 는 파일 단위 덮어쓰기 — 당사 수정 파일이 사라진다 → `owner_edits.py`, usercode 3-way.")
    w("- **orphan 파라미터 삭제**(ecud_validator): 새 PDF 에 없는 파라미터 값을 Ecud 에서 지운다 → 생성기 기본값으로 바뀔 수 있다(protected-settings (d)).")
    w("- **Harmonize 앞뒤 보정**(_harmonize): Rte 는 Harmonize 가 새로 만든 BswModuleInstance 를 지우고 BswInstance_Mcu/Spi 를 복원, FBL BswM 은 Harmonize 가 넣은 Com.h 를 되돌린다. C Studio 에서 직접 Harmonize 하면 이 보정이 없다.")
    if req_all:
        w(f"- 이번 스크립트의 요청: {', '.join(sorted(req_all))} — requestHarmonize 가 있으면 툴은 Harmonize 를 돌린다(당사는 보통 결과 이식으로 대체).")
    w("- 백업(`.patch_backup`)은 모듈 복사 뒤에 만들어지고 성공하면 지워진다 → 원복은 git.")
    w("")
    w("## 6. 다음 할 일")
    w("")
    w("1. 2·3·4 절의 항목을 판정표 초기 행으로 옮긴다(경로 A~D, 대상 FBL/APP).")
    w("2. 각 행을 3-way(`three_way.py`)와 과거 회차 이력(`history_trace.py`)으로 판정한다.")
    w("3. IM 링크는 ecody-search 로 정독한다. 툴 docstring 과 IM 이 다르면 IM 을 따르고 기록한다.")
    w("")

    if a.search:
        w("## 7. 키워드 검색 — 전체 스크립트 묶음")
        w("")
        w("패치 대상이 아닌 모듈의 버전 스크립트에도 같은 위치를 다루는 규칙이 있을 수 있다"
          "(예: Crypto_76_HaeModule v1.0.7.0 의 Crypto Init → ListOne). 당사 그 모듈 버전이 규칙 버전보다 낮으면 해당 없음이지만, "
          "배포본 참고 설정에 그 결과가 섞여 올 수 있으니 판정표 근거로 남긴다.")
        w("")
        for kw in a.search:
            w(f"### `{kw}`")
            hits = 0
            for dp, _, fs in os.walk(mp):
                for f in sorted(fs):
                    if not f.endswith(".py"):
                        continue
                    fp = os.path.join(dp, f)
                    lines = open(fp, encoding="utf-8", errors="replace").read().splitlines()
                    found = [(i + 1, x.strip()) for i, x in enumerate(lines) if kw.lower() in x.lower()]
                    if found:
                        hits += 1
                        w(f"- `{os.path.relpath(fp, mp)}` ({len(found)}줄): "
                          + " / ".join(f"L{i}: {x[:110]}" for i, x in found[:3]))
            if not hits:
                w("- 없음")
            w("")

    text = "\n".join(L) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"계획서: {os.path.abspath(a.out)}  (스크립트 {len(order)}개)")
    else:
        print(text)


if __name__ == "__main__":
    main()
