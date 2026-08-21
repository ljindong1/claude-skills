"""mapping.json → self-contained dashboard.html 생성.

사용: python build_dashboard.py mapping.json -o dashboard.html
템플릿(assets/dashboard_template.html)의 __MAPPING_JSON__ 자리에 데이터를 인라인한다.
생성 전 validate_mapping 검사를 통과해야 한다 — 검증 실패 상태의 대시보드는
잘못된 판정 현황을 사용자에게 보여줄 수 있으므로 거부한다 (게이트4 결함 #3 조치).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from validate_mapping import validate

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PLACEHOLDER = "__MAPPING_JSON__"


def inline_json(mapping: dict[str, object]) -> str:
    """<script> 안에 안전하게 넣을 수 있도록 직렬화한다."""
    text = json.dumps(mapping, ensure_ascii=False)
    return text.replace("</", "<\\/")  # </script> 조기 종료 방지


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="매핑 대시보드 생성")
    parser.add_argument("mapping", help="mapping.json 경로")
    parser.add_argument("--template", default=str(ASSETS_DIR / "dashboard_template.html"))
    parser.add_argument("-o", "--output", required=True, help="dashboard.html 출력 경로")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    errors = validate(mapping, inventory_paths=None)
    if errors:
        logger.error("검증 미통과 상태 — 대시보드 생성 거부 (%d건). validate_mapping.py로 확인 후 수정하세요.", len(errors))
        for error in errors[:5]:
            logger.error("  - %s", error)
        return 1

    template = Path(args.template).read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        logger.error("템플릿에 %s 자리표시자가 없음: %s", PLACEHOLDER, args.template)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.replace(PLACEHOLDER, inline_json(mapping)), encoding="utf-8")
    logger.info("대시보드 생성 → %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
