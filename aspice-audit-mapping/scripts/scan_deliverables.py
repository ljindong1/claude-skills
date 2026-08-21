"""산출물 폴더를 스캔해 파일 인벤토리(JSON)를 만든다.

사용:
  python scan_deliverables.py --root <폴더> -o inventory.json
  python scan_deliverables.py --from-listing <listing.json> --root-label "<원본 경로>" -o inventory.json

--from-listing 은 Cowork device_list_dir(recursive) 결과 JSON을 입력으로 받는다.
스캔 시각(scanned_at)이 점검의 스냅샷 기준 시각이다.

v0.4 인벤토리 제외 규칙 (설계서 §4.2 ②):
- 입력 체크리스트 파일 자신 (`--exclude-checklist <파일명>`) — 자기 자신이
  UNCLAIMED로 잡히는 노이즈 방지
- `_ai_draft_meta` 마커 보유 .xlsx (모드 B 초안 — filesystem 스캔에서만 검출 가능)
- 임시파일(`~$` 등, 기존 규칙)
제외 내역은 inventory의 `excluded_from_scan`에 기록되어 mapping.json source로 전달된다.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import (
    DOCUMENT_EXTENSIONS,
    DRAFT_META_SHEET,
    EXCLUDED_DIR_PREFIXES,
    EXCLUDED_FILE_PATTERNS,
    EXCLUDED_FILE_SUFFIXES,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FileRecord:
    """인벤토리 파일 레코드 1건."""

    relpath: str
    name: str
    kind: str  # "file" | "dir"
    size: int | None
    mtime: str | None
    document: bool = False  # v0.3: 문서/비문서 분류 (모드 B 추론 대상 판별)


def is_document(name: str) -> bool:
    return name.lower().endswith(DOCUMENT_EXTENSIONS)


def is_excluded(name: str, is_dir: bool) -> bool:
    """스캔 제외 대상인지 판별한다 (references/matching_rules.md)."""
    if is_dir:
        return name.startswith(EXCLUDED_DIR_PREFIXES)
    if any(name.startswith(p) or p in name for p in EXCLUDED_FILE_PATTERNS):
        return True
    return name.lower().endswith(EXCLUDED_FILE_SUFFIXES)


def iso_from_ms(mtime_ms: float | None) -> str | None:
    """epoch ms → ISO 문자열 (로컬 타임존 미상이므로 UTC 표기)."""
    if mtime_ms is None:
        return None
    return datetime.fromtimestamp(mtime_ms / 1000, tz=timezone.utc).isoformat()


def has_draft_marker(path: Path) -> bool:
    """`.xlsx`가 모드 B 초안 마커(_ai_draft_meta 시트)를 갖는지 검사한다."""
    if path.suffix.lower() not in (".xlsx", ".xlsm"):
        return False
    try:
        import openpyxl  # 지연 import — listing 모드에서는 불필요

        workbook = openpyxl.load_workbook(path, read_only=True)
        found = DRAFT_META_SHEET in workbook.sheetnames
        workbook.close()
        return found
    except Exception:  # noqa: BLE001 — 열기 실패는 마커 아님 (무결성은 ③′ 소관)
        return False


def scan_filesystem(root: Path, exclude_checklist: str | None,
                    excluded: list[dict[str, str]]) -> list[FileRecord]:
    """로컬 폴더를 재귀 스캔한다. 제외 내역은 excluded에 기록한다."""
    records: list[FileRecord] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part.startswith(EXCLUDED_DIR_PREFIXES) for part in relative.parts[:-1]):
            continue
        if is_excluded(path.name, path.is_dir()):
            continue
        if path.is_file():
            if exclude_checklist and path.name == exclude_checklist:
                excluded.append({"path": str(relative), "reason": "INPUT_CHECKLIST"})
                continue
            if has_draft_marker(path):
                excluded.append({"path": str(relative), "reason": "AI_DRAFT_MARKER"})
                continue
        if path.is_dir():
            records.append(FileRecord(str(relative), path.name, "dir", None, None))
        else:
            stat = path.stat()
            records.append(
                FileRecord(
                    str(relative), path.name, "file", stat.st_size,
                    datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    document=is_document(path.name),
                )
            )
    return records


def scan_listing(listing_path: Path, exclude_checklist: str | None,
                 excluded: list[dict[str, str]]) -> list[FileRecord]:
    """device_list_dir(recursive) 결과 JSON을 인벤토리로 변환한다.

    listing 모드에서는 파일을 열 수 없어 초안 마커(_ai_draft_meta) 검출은
    생략된다 — stage 후 filesystem 재스캔 시 검출된다.
    """
    raw = json.loads(listing_path.read_text(encoding="utf-8"))
    entries = raw.get("entries", raw if isinstance(raw, list) else [])
    records: list[FileRecord] = []
    for entry in entries:
        relpath = str(entry.get("name", ""))
        kind = str(entry.get("type", "file"))
        if kind not in ("file", "dir"):
            continue
        name = relpath.replace("\\", "/").rsplit("/", 1)[-1]
        parts = relpath.replace("\\", "/").split("/")
        if any(part.startswith(EXCLUDED_DIR_PREFIXES) for part in parts[:-1]):
            continue
        if is_excluded(name, kind == "dir"):
            continue
        if kind == "file" and exclude_checklist and name == exclude_checklist:
            excluded.append({"path": relpath.replace("\\", "/"), "reason": "INPUT_CHECKLIST"})
            continue
        records.append(
            FileRecord(
                relpath=relpath.replace("\\", "/"),
                name=name,
                kind=kind,
                size=entry.get("size"),
                mtime=iso_from_ms(entry.get("mtimeMs")),
                document=(kind == "file" and is_document(name)),
            )
        )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="산출물 폴더 스캔")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", help="산출물 폴더 경로 (로컬 스캔)")
    source.add_argument("--from-listing", help="device_list_dir 결과 JSON 경로")
    parser.add_argument("--root-label", default=None, help="listing 모드에서 원본 폴더 경로 표기")
    parser.add_argument("--exclude-checklist", default=None,
                        help="입력 체크리스트 파일명 — 인벤토리에서 제외 (v0.4 §4.2 ②)")
    parser.add_argument("-o", "--output", required=True, help="inventory.json 출력 경로")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    excluded: list[dict[str, str]] = []
    if args.root:
        root = Path(args.root)
        if not root.is_dir():
            logger.error("폴더 없음: %s", root)
            return 1
        records = scan_filesystem(root, args.exclude_checklist, excluded)
        root_label = str(root)
        mode = "filesystem"
    else:
        listing_path = Path(args.from_listing)
        if not listing_path.is_file():
            logger.error("listing 파일 없음: %s", listing_path)
            return 1
        records = scan_listing(listing_path, args.exclude_checklist, excluded)
        root_label = args.root_label or str(listing_path)
        mode = "listing"

    result = {
        "root": root_label,
        "mode": mode,
        "scanned_at": datetime.now(tz=timezone.utc).astimezone().isoformat(),
        "excluded_from_scan": excluded,
        "files": [asdict(record) for record in records],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    file_count = sum(1 for r in records if r.kind == "file")
    logger.info("스캔 완료: 파일 %d건, 폴더 %d건 → %s", file_count, len(records) - file_count, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
