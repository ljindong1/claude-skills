#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""패치 첨부 폴더를 재귀로 수확한다 — 첨부 안쪽의 첨부까지.

규칙은 ../references/tracing.md 2절이 정본이다. 여기서 바뀌면 그 파일도 고쳐라.

넘겨받은 폴더는 외부 자료다. 안의 코드는 읽기만 하고 실행하지 않는다.
그래서 이 스크립트는 폴더 밖에 두고 경로를 인자로 받으며, python -I 로 돌린다
(폴더 안에 json.py 가 있으면 import json 이 그것을 집는다).

    python -I harvest_attach.py "<첨부 폴더>" --out attach.json
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ARCHIVE = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".z01", ".z02", ".cab")
LIST_ONLY = (".c", ".h", ".jar", ".epd", ".pdf", ".a", ".s", ".o", ".obj", ".lib")
OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
CAP = 40  # 표본 상한 - 일감에 들어갈 분량만 본다


def rel(root, p):
    return os.path.relpath(p, root).replace("\\", "/")


def read_text(p, limit=4000000):
    for enc in ("utf-8", "cp949", "latin-1"):
        try:
            with io.open(p, encoding=enc, errors="strict") as f:
                return f.read(limit)
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return ""
    try:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def walk(root):
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            out.append(os.path.join(dirpath, fn))
    return out


def harvest_manifest(paths, root):
    for p in paths:
        if os.path.basename(p) == "patch_manifest.json":
            try:
                m = json.loads(read_text(p))
            except Exception as e:
                return {"path": rel(root, p), "error": "파싱 실패: %s" % e}
            m["_path"] = rel(root, p)
            return m
    return None


def harvest_docx(p):
    """릴리즈 노트 등. python-docx 가 없으면 docx 는 zip+xml 이므로 직접 긁는다."""
    try:
        import docx
    except ImportError:
        docx = None
    except Exception:
        docx = None
    if docx is not None:
        try:
            d = docx.Document(p)
            lines = [t.text.strip() for t in d.paragraphs if t.text.strip()]
            for tb in d.tables:
                for r in tb.rows:
                    cells = [c.text.strip() for c in r.cells if c.text.strip()]
                    if cells:
                        lines.append(" | ".join(cells))
            return {"reader": "python-docx", "lines": lines[:CAP],
                    "line_count": len(lines)}
        except Exception as e:
            return {"error": "docx 읽기 실패: %s" % e}
    try:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        txt = re.sub(r"<[^>]+>", "\n", xml)
        lines = [s.strip() for s in txt.split("\n") if s.strip()]
        return {"reader": "zip+regex", "lines": lines[:CAP], "line_count": len(lines)}
    except Exception as e:
        return {"error": "docx 읽기 실패: %s" % e}


POSIX_DRIVE = re.compile(r"^/([A-Za-z])/")


def win_path(p):
    """Git Bash 식 /c/Users/... 를 C:\\Users\\... 로 바꾼다."""
    m = POSIX_DRIVE.match(p)
    if m:
        p = "%s:\\%s" % (m.group(1).upper(), p[3:])
    return os.path.normpath(os.path.abspath(p))


def convert_xls(p, workdir):
    """구형 .xls(OLE2/BIFF)를 엑셀을 시켜 .xlsx 로 바꾼다.

    openpyxl 은 .xlsx(ZIP+XML)만 읽고 .xls 는 전혀 다른 포맷이다. xlrd 가 없어도
    윈도우에 엑셀이 깔려 있으면 COM 으로 변환해 읽을 수 있다.

    "읽을 수단이 없다"고 넘기기 전에 이것을 먼저 해 본다. 한 번 그냥 넘겼던 .xls 가
    Harmonize 대조표였고, 그 안에 일감을 바꿀 내용이 있었다 - 설정 변경 안내와
    Harmonize 가 서로 반대로 작용하는 자리가 거기서 드러났다. 포기는 마지막에 한다."""
    if os.name != "nt":
        return None, "윈도우가 아니다"
    # 엑셀 COM 은 윈도우 절대 경로만 받는다. Git Bash 식 /c/Users/... 를 그대로
    # 넘기면 "경로를 찾을 수 없습니다" 로 실패한다.
    workdir = win_path(workdir)
    p = win_path(p)
    try:
        if not os.path.isdir(workdir):
            os.makedirs(workdir)
    except OSError as e:
        return None, "작업 폴더 생성 실패: %s" % e
    dst = os.path.join(workdir, os.path.splitext(os.path.basename(p))[0] + ".xlsx")
    ps = (
        "try{$xl=New-Object -ComObject Excel.Application}"
        "catch{Write-Output 'NOEXCEL'; exit 0};"
        "$xl.Visible=$false; $xl.DisplayAlerts=$false;"
        "try{$wb=$xl.Workbooks.Open('%s',0,$true); $wb.SaveAs('%s',51);"
        " $wb.Close($false); Write-Output 'OK'}"
        "catch{Write-Output ('ERR ' + $_.Exception.Message)}"
        "finally{$xl.Quit()}"
    ) % (p.replace("'", "''"), dst.replace("'", "''"))
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, timeout=300)
    except Exception as e:
        return None, "엑셀 변환 호출 실패: %s" % e
    out = (r.stdout or b"").decode("utf-8", "replace").strip()
    if "OK" in out and os.path.exists(dst):
        return dst, None
    if "NOEXCEL" in out:
        return None, "이 PC 에 엑셀이 없다"
    return None, "엑셀 변환 실패: %s" % (out[:200] or "출력 없음")


def harvest_xlsx(p):
    """시트별 표본과, Difference 열이 있으면 그 차이 집계를 함께 낸다.

    Harmonize 대조표가 이 꼴이다(좌 현재 / 우 대상 / Difference). 표본 몇 줄만 보면
    Added·Deleted·Different 가 몇 건인지 알 수 없어서 전수로 센다. 어느 쪽 열이
    현재이고 어느 쪽이 대상인지는 표가 말해 주지 않으니 사람에게 확인해야 한다."""
    try:
        import openpyxl
    except ImportError:
        return {"error": "openpyxl 없음"}
    try:
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    except Exception as e:
        return {"error": "xlsx 읽기 실패: %s" % e}
    sheets = {}
    diff_summary = {}
    for ws in wb.worksheets:
        sample = []
        total = 0
        dcol = None
        tally = {}
        examples = []
        for row in ws.iter_rows(values_only=True):
            cells = [("" if c is None else str(c).strip()) for c in row]
            if not any(cells):
                continue
            total += 1
            if dcol is None:
                for i, c in enumerate(cells):
                    if c == "Difference":
                        dcol = i
                        break
            elif dcol < len(cells):
                v = cells[dcol]
                if v and v != "Same":
                    tally[v] = tally.get(v, 0) + 1
                    if len(examples) < 12:
                        examples.append([c for c in cells if c][:5])
            if len(sample) < CAP:
                nz = [c for c in cells if c]
                if nz:
                    sample.append(nz)
        sheets[ws.title] = sample
        if tally:
            diff_summary[ws.title] = {"rows": total, "counts": tally,
                                      "examples": examples}
    try:
        wb.close()
    except Exception:
        pass
    out = {"reader": "openpyxl", "sheets": sheets}
    if diff_summary:
        out["difference_summary"] = diff_summary
    return out


PATHISH = re.compile(r"""[\'\"]([A-Za-z0-9_./\\-]{6,120})[\'\"]""")


def harvest_patch_script(p, root):
    """패치 스크립트가 실제로 손대는 경로/컨테이너를 뽑는다.

    HAE 안내문과 IM 절 번호는 어긋나는 일이 잦다. 스크립트가 손대는 자리가
    설정 변경 안내를 교차검증할 1차 근거다."""
    txt = read_text(p)
    hits = []
    for m in PATHISH.finditer(txt):
        s = m.group(1)
        if ("/" in s or "\\" in s or s.endswith(".arxml")) and not s.startswith("http"):
            hits.append(s.replace("\\", "/"))
    seen = set()
    uniq = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return {"path": rel(root, p), "size": os.path.getsize(p),
            "touches": uniq[:CAP], "touch_count": len(uniq)}


ERRCODE = re.compile(r"\bERR\d{6}\b")
VALID = re.compile(r".*Validation Finished.*", re.I)
FATAL = re.compile(r"(fatal error|\berror #\d|scons: \*\*\*|\bError \d+\b|\[ERROR\])", re.I)


def harvest_log(p, root):
    txt = read_text(p)
    lines = txt.splitlines()
    codes = {}
    for c in ERRCODE.findall(txt):
        codes[c] = codes.get(c, 0) + 1
    fatal = []
    valid = []
    for i, ln in enumerate(lines, 1):
        if VALID.match(ln):
            valid.append("%s:%d %s" % (rel(root, p), i, ln.strip()[:200]))
        elif FATAL.search(ln):
            fatal.append("%s:%d %s" % (rel(root, p), i, ln.strip()[:200]))
    return {"path": rel(root, p), "lines": len(lines), "err_codes": codes,
            "fatal": fatal[:CAP], "fatal_count": len(fatal),
            "validation": valid[:CAP]}


def main():
    ap = argparse.ArgumentParser(description="패치 첨부 폴더 재귀 수확")
    ap.add_argument("root")
    ap.add_argument("--out", help="JSON 저장 경로")
    ap.add_argument("--work", help="변환 파일을 둘 폴더 (기본: 임시 폴더). "
                                   "넘겨받은 폴더는 건드리지 않는다")
    a = ap.parse_args()
    workdir = a.work or tempfile.mkdtemp(prefix="patch_harvest_")

    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        sys.exit("폴더가 없습니다: %s" % root)

    paths = walk(root)
    by_ext = {}
    for p in paths:
        e = os.path.splitext(p)[1].lower() or "(없음)"
        by_ext[e] = by_ext.get(e, 0) + 1

    res = {
        "root": root,
        "counts": {"total": len(paths),
                   "by_ext": dict(sorted(by_ext.items(), key=lambda kv: -kv[1]))},
        "nested_archives": [],
        "unreadable": [],
        "manifest": None,
        "docs": {},
        "patch_scripts": [],
        "build_logs": [],
        "generate_logs": [],
        "config_arxml": [],
        "listed_only": {},
    }

    # 중첩 압축 - 자동 전개하지 않는다. 사용자에게 묻는다.
    for p in paths:
        if p.lower().endswith(ARCHIVE):
            res["nested_archives"].append({"path": rel(root, p),
                                           "size": os.path.getsize(p)})

    res["manifest"] = harvest_manifest(paths, root)
    res["patch_scripts_unused"] = 0
    declared = []
    if res["manifest"] and "error" not in res["manifest"]:
        declared = [s.replace("\\", "/") for s in (res["manifest"].get("scripts") or [])]

    listed = {}
    for p in paths:
        name = os.path.basename(p)
        low = name.lower()
        ext = os.path.splitext(low)[1]
        r = rel(root, p)

        if ext == ".xls":
            head = b""
            try:
                with open(p, "rb") as f:
                    head = f.read(8)
            except OSError:
                pass
            if head != OLE2:
                res["unreadable"].append(
                    {"path": r,
                     "why": "확장자는 .xls 인데 OLE2 가 아니다 - 실제 형식 확인 필요"})
                continue
            conv, err = convert_xls(p, workdir)
            if conv:
                d = harvest_xlsx(conv)
                d["converted_from"] = r
                d["converted_to"] = conv
                d["reader"] = "%s (엑셀 COM 으로 .xlsx 변환 후)" % (d.get("reader") or "?")
                res["docs"][r] = d
            else:
                res["unreadable"].append(
                    {"path": r,
                     "why": ("구형 엑셀(OLE2). %s. xlsx 로 재저장하거나 "
                             "pip install xlrd 필요" % err)})
            continue

        if ext == ".docx":
            res["docs"][r] = harvest_docx(p)
            continue
        if ext in (".xlsx", ".xlsm"):
            res["docs"][r] = harvest_xlsx(p)
            continue

        if ext == ".py" and "module_patch" in r:
            # patch_tool 은 모든 모듈의 스크립트를 동봉한다. 이번에 실제로 도는 것은
            # manifest 의 scripts 목록뿐이고, 나머지는 잡음이다.
            if any(r.endswith(s) for s in declared):
                res["patch_scripts"].append(harvest_patch_script(p, root))
            else:
                res["patch_scripts_unused"] += 1
            continue

        if ext == ".arxml" and ("/Configuration/" in "/" + r or low.endswith("scons.arxml")):
            res["config_arxml"].append({"path": r, "size": os.path.getsize(p)})
            continue

        if ext in (".log", ".txt") and ("log" in low or "build" in low):
            h = harvest_log(p, root)
            if "/log/" in "/" + r or "Generated" in r:
                res["generate_logs"].append(h)
            else:
                res["build_logs"].append(h)
            continue

        if ext in LIST_ONLY:
            listed.setdefault(ext, []).append(r)

    res["listed_only"] = dict((k, {"count": len(v), "sample": v[:5]})
                              for k, v in sorted(listed.items()))

    # Generate 로그 종합 - 예측이 아니라 실제로 뜬 것
    agg_codes = {}
    agg_fatal = []
    agg_valid = []
    for h in res["generate_logs"]:
        for c, n in h["err_codes"].items():
            agg_codes[c] = agg_codes.get(c, 0) + n
        agg_fatal += h["fatal"]
        agg_valid += h["validation"]
    res["generate_summary"] = {
        "log_files": len(res["generate_logs"]),
        "err_codes": agg_codes,
        "errors": agg_fatal[:CAP],
        "error_count": len(agg_fatal),
        "validation": agg_valid[:CAP],
    }

    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    o = []
    o.append("첨부 폴더 : %s" % root)
    o.append("파일 %d개 - %s" % (
        res["counts"]["total"],
        ", ".join("%s %d" % (k, v)
                  for k, v in list(res["counts"]["by_ext"].items())[:10])))

    m = res["manifest"]
    o.append("")
    if m and "error" not in m:
        o.append("[manifest] %s" % m.get("_path"))
        o.append("  기존 SWP : %s   패치 버전 : %s   AR : %s"
                 % (m.get("project_name"), m.get("patch_version"), m.get("ar_version")))
        for mod in m.get("modules", []):
            o.append("  모듈 : %-28s %s -> %s%s" % (
                mod.get("name"), mod.get("current_version"), mod.get("target_version"),
                "  (의존성)" if mod.get("is_dependency") else ""))
    else:
        o.append("[manifest] 없음 - 모듈/버전의 1차 출처가 빠졌다. "
                 "페이지 값만으로 쓰면 field-map 우선순위를 어긴다")

    if res["nested_archives"]:
        o.append("")
        o.append("[중첩 압축 %d개] 자동 전개하지 않았다 - 전개할지 사용자에게 물어라"
                 % len(res["nested_archives"]))
        for x in res["nested_archives"][:10]:
            o.append("  %s (%d bytes)" % (x["path"], x["size"]))

    if res["unreadable"]:
        o.append("")
        o.append("[읽지 못한 파일] 조용히 빠뜨리지 말고 일감에 미확인으로 남겨라")
        for x in res["unreadable"]:
            o.append("  %s - %s" % (x["path"], x["why"]))

    if res["docs"]:
        o.append("")
        o.append("[문서 %d개]" % len(res["docs"]))
        for k, v in res["docs"].items():
            o.append("  %s - %s" % (k, v.get("error") or v.get("reader")))
            ds = v.get("difference_summary") or {}
            for sheet, info in ds.items():
                o.append("      [%s] %d행 - %s" % (
                    sheet, info["rows"],
                    ", ".join("%s %d건" % kv
                              for kv in sorted(info["counts"].items(),
                                               key=lambda kv: -kv[1]))))
            if ds:
                o.append("      ^ 대조표다. 좌우 중 어느 쪽이 '현재'인지는 표가 말해 주지")
                o.append("        않는다. 묻지 말고 확인하라 - tracing.md '대조표를 읽는 법':")
                o.append("        1) Summary 시트의 Removed/Created Container 목록과 Apply Done")
                o.append("        2) 당사 고유 설정(*_LCAN_* 등)이 어느 쪽에 있는지, 양쪽 arxml 대조")
                o.append("        3) 그 차이가 이후 빌드 오류를 설명하는지")

    if res["patch_scripts"]:
        o.append("")
        o.append("[패치 스크립트 %d개 - manifest 가 실제로 도는 것] "
                 "설정 변경 안내의 교차검증 근거 (미사용 동봉 %d개는 뺐다)"
                 % (len(res["patch_scripts"]), res["patch_scripts_unused"]))
        for s in sorted(res["patch_scripts"], key=lambda x: -x["size"]):
            o.append("  %s (%d bytes, 경로 문자열 %d개)"
                     % (s["path"], s["size"], s["touch_count"]))

    if res["build_logs"]:
        o.append("")
        o.append("[빌드 로그 %d개]" % len(res["build_logs"]))
        for h in res["build_logs"]:
            o.append("  %s (%d행, 치명 %d건)" % (h["path"], h["lines"], h["fatal_count"]))
            for ln in h["fatal"][:6]:
                o.append("    %s" % ln)

    gs = res["generate_summary"]
    o.append("")
    o.append("[Generate 로그 %d개] - 예측이 아니라 실제로 뜬 것" % gs["log_files"])
    o.append("  ERR 코드 : %s" % (
        ", ".join("%s x%d" % (k, v) for k, v in sorted(gs["err_codes"].items())) or "없음"))
    o.append("  에러 줄 %d건" % gs["error_count"])
    for ln in gs["errors"][:8]:
        o.append("    %s" % ln)
    for ln in gs["validation"][:6]:
        o.append("    %s" % ln)

    if res["config_arxml"]:
        o.append("")
        o.append("[설정 arxml %d개] 설정 변경 대조 근거" % len(res["config_arxml"]))

    if res["listed_only"]:
        o.append("")
        o.append("[목록만 - 필요해지면 그 파일만 읽는다]")
        for k, v in res["listed_only"].items():
            o.append("  %s %d개" % (k, v["count"]))

    print("\n".join(o))
    if a.out:
        print("")
        print("JSON : %s" % a.out)


if __name__ == "__main__":
    main()
