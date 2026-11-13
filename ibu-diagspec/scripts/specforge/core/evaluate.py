"""파이프라인: 세 파일 파싱 → 공통 모델 → 규칙 평가 → 불일치 목록 → out/. (진입점은 specforge/cli.py)

진단사양서 입력은 정본 워크북(.xlsx, master/diagspec_IBU_BCM_Master.xlsx)이 기본이다. 예전 통합 진단사양서(.xls)를 주면 xls 파서로 읽는다.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from ..parsers.diagspec import parse_diagspec
from ..parsers.rawbook import parse_rawbook
from .projects import ProjectRegistry
from .refdata import load_sources
from .rules import evaluate, parse_rule


def build(funcspec, diagspec: Path, blockdiag, out: Path, aliases: Path | None, reg: ProjectRegistry | None = None) -> dict:
    """funcspec·blockdiag 은 경로 하나 또는 목록 (.xlsx/.pdf 또는 참조 데이터 스냅숏 .json — core/refdata.py)."""
    out.mkdir(parents=True, exist_ok=True)
    reg = reg or ProjectRegistry.load(aliases)
    fs, bd = load_sources(funcspec, blockdiag, reg)
    ds = parse_rawbook(diagspec, reg) if Path(diagspec).suffix.lower() == ".xlsx" else parse_diagspec(diagspec, reg)

    # 평가 컨텍스트
    signals_by_project = {e["project"]: set(e["signals"]) for e in bd["by_project"]}
    variants_by_project = {e["project"]: {k: set(v) for k, v in e["variants"].items()} for e in bd["by_project"]}
    features_by_project: dict[str, dict[str, bool]] = {}
    for f in fs["features"]:
        for proj, regions in f["applicability"].items():
            applied = any(v["state"] in ("STD", "OPT", "VAL") for v in regions.values())
            features_by_project.setdefault(proj, {})[f["name"].upper()] = applied

    # 규칙 변환 + 평가
    evals, stats = [], Counter()
    for it in ds["items"]:
        it["rule"] = parse_rule(it["criteria_text"], it.get("pn_text", it.get("tool_display", "")),   # BCM: Tool 표시 = 원본 H열(품번 조건)
                                it.get("hint_signals"))
        confirmed = it.get("confirmed_exceptions", {})
        stats["items"] += 1
        stats["items_with_rule"] += int(it["rule"].get("evaluable", False))
        it["evaluation"] = {}
        for proj, rec in it["recorded"].items():
            res, why = evaluate(it["rule"], proj, signals_by_project, features_by_project, variants_by_project)
            if res is None:
                status = "not_evaluable"
            elif rec not in ("O", "X"):
                status = "recorded_other"
            elif res == "O?":
                status = "conditional"          # 판단 불가 조건(지역·품번 등)이 남아 O/X 어느 쪽도 규칙과 모순되지 않음
            else:
                status = "match" if res == rec else "mismatch"
            if status == "mismatch" and proj in confirmed:
                status = "exception_ok"         # 담당자가 확인해 적용예외에 사유를 남긴 칸
                why += ";예외 확인:" + confirmed[proj]
            it["evaluation"][proj] = {"rule": res, "recorded": rec, "status": status, "why": why}
            stats["cells"] += 1
            stats[status] += 1
            if status == "mismatch":
                evals.append({"item": it["id"], "sheet": it["sheet"], "code": it["code"], "name": it["name"],
                              "project": proj, "recorded": rec, "rule": res, "why": why,
                              "criteria": it["criteria_text"].replace("\n", " / ")})

    # 산출물
    model = {
        "generated_from": {"funcspec": fs["file"], "diagspec": ds["file"], "blockdiag": bd["file"]},
        "projects": reg.export(),
        "funcspec": fs, "diagspec": {k: v for k, v in ds.items() if k != "items"},
        "diag_items": ds["items"],
        "blockdiag": {"pages": bd["pages"], "by_project": bd["by_project"], "signals": bd["signals"]},
        "stats": dict(stats),
    }
    (out / "model.json").write_text(json.dumps(model, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "mismatch.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sheet", "code", "name", "project", "recorded", "rule", "why", "criteria", "item"])
        w.writeheader(); w.writerows(evals)
    evaluable_cells = stats["match"] + stats["mismatch"]
    summary = {
        **dict(stats),
        "match_rate": round(stats["match"] / evaluable_cells, 4) if evaluable_cells else None,
        "projects_total": len(model["projects"]),
        "projects_with_blockdiag": len(signals_by_project),
        "projects_with_funcspec": len(features_by_project),
        "signals_total": len(bd["signals"]),
        "history_rows": len(ds["history"]),
        "history_kinds": dict(Counter(h["kind"] for h in ds["history"])),
        "sheets": ds["sheets"],
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary
