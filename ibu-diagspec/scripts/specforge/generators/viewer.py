"""out/model.json → 단일 HTML 뷰어(out/ibu_diagspec_viewer.html). 데이터는 페이지 안에 JSON으로 내장한다. (진입점: specforge viewer)"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "viewer" / "template.html"


def slim(model: dict, summary: dict) -> dict:
    items = []
    for it in model["diag_items"]:
        items.append({k: it[k] for k in ("id", "kind", "sheet", "gen", "did", "code", "name", "attrs", "sw_variable",
                                          "tool_display", "criteria_text", "values", "recorded", "rule")}
                     | {"eval": {p: [e["rule"], e["status"]] for p, e in it["evaluation"].items()}})
    return {
        "projects": model["projects"], "items": items,
        "signals_by_project": {e["project"]: e["signals"] for e in model["blockdiag"]["by_project"]},
        "security": model["diagspec"].get("security", {}),
        "owners": model["diagspec"].get("owners", {}),
        "signal_variants": {e["project"]: e["variants"] for e in model["blockdiag"]["by_project"]},   # SMK/IMMO 페이지별
        "bd_pages": [{k: p[k] for k in ("page", "title", "project", "variant")} for p in model["blockdiag"]["pages"]],
        "features": [{k: f[k] for k in ("id", "group", "name", "oem_code", "control", "applicability")} for f in model["funcspec"]["features"]],
        "history": model["diagspec"]["history"],
        "stats": {**summary, "sources": model["generated_from"], "rev": model["diagspec"].get("rev", ""),
                  "module": (re.match(r"diagspec_(?:IBU_)?([A-Za-z0-9]+)", model["diagspec"].get("file", ""), re.I) or [None, ""])[1].upper(),
                  "built_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")},   # 한국 시각
    }



def build_viewer(model_path: Path, summary_path: Path, out_path: Path, template: Path | None = None) -> int:
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    data = json.dumps(slim(model, summary), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = Path(template or TEMPLATE).read_text(encoding="utf-8").replace("__DATA__", data)
    Path(out_path).write_text(html, encoding="utf-8")
    return len(html.encode())
