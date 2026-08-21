"""③′ 매칭 파일 무결성 검사 (설계서 v0.3 신규 — 결정론).

build_mapping.py 가 import 해 사용하며 단독 실행도 지원한다:
  python verify_matched_files.py <파일...>   # 파일별 무결성 코드 출력

판별: OK / FILE_EMPTY / FILE_CORRUPT / FORMAT_MISMATCH / PASSWORD_PROTECTED /
NOT_CHECKED(파일 미접근 — listing 모드).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from config import (
    INTEGRITY_CORRUPT,
    INTEGRITY_EMPTY,
    INTEGRITY_FORMAT,
    INTEGRITY_NOT_CHECKED,
    INTEGRITY_OK,
    INTEGRITY_PASSWORD,
)

# 확장자 → 기대 매직 바이트 (선두)
ZIP_MAGIC = b"PK\x03\x04"
OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
PDF_MAGIC = b"%PDF"
MAGIC_BY_EXTENSION: dict[str, tuple[bytes, ...]] = {
    ".xlsx": (ZIP_MAGIC,), ".xlsm": (ZIP_MAGIC,), ".docx": (ZIP_MAGIC,),
    ".pptx": (ZIP_MAGIC,), ".zip": (ZIP_MAGIC,),
    ".xls": (OLE2_MAGIC,), ".doc": (OLE2_MAGIC,), ".ppt": (OLE2_MAGIC,),
    ".pdf": (PDF_MAGIC,),
}
# OLE2 암호화·OOXML 암호화(둘 다 OLE2 컨테이너에 EncryptionInfo 스트림) 탐지용
ENCRYPTION_HINTS = (b"EncryptionInfo", b"EncryptedPackage")


def check_integrity(path: Path | None) -> str:
    """파일 1개의 무결성 코드를 돌려준다. path=None이면 NOT_CHECKED."""
    if path is None:
        return INTEGRITY_NOT_CHECKED
    try:
        if not path.is_file():
            return INTEGRITY_NOT_CHECKED
        size = path.stat().st_size
        if size == 0:
            return INTEGRITY_EMPTY
        with path.open("rb") as handle:
            head = handle.read(8)
        extension = path.suffix.lower()
        expected = MAGIC_BY_EXTENSION.get(extension)
        if expected is not None and not any(head.startswith(m) for m in expected):
            # OOXML 확장자인데 OLE2 서명이면 암호화 컨테이너 가능성 우선 확인
            if head.startswith(OLE2_MAGIC):
                data = path.read_bytes()
                if any(hint in data for hint in ENCRYPTION_HINTS):
                    return INTEGRITY_PASSWORD
            return INTEGRITY_FORMAT
        if expected == (ZIP_MAGIC,):
            try:
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        return INTEGRITY_CORRUPT
                    names = archive.namelist()
                    if not names:
                        return INTEGRITY_EMPTY
                    # OOXML 내부 구조로 실제 포맷 판별 (docx↔xlsx 위장 검출)
                    ooxml_root = {".xlsx": "xl/", ".xlsm": "xl/",
                                  ".docx": "word/", ".pptx": "ppt/"}.get(extension)
                    if ooxml_root is not None and not any(n.startswith(ooxml_root) for n in names):
                        return INTEGRITY_FORMAT
            except zipfile.BadZipFile:
                return INTEGRITY_CORRUPT
        if expected == (OLE2_MAGIC,):
            data = path.read_bytes()
            if any(hint in data for hint in ENCRYPTION_HINTS):
                return INTEGRITY_PASSWORD
        return INTEGRITY_OK
    except OSError:
        return INTEGRITY_CORRUPT


def main(argv: list[str] | None = None) -> int:
    paths = argv if argv is not None else sys.argv[1:]
    for raw in paths:
        print(f"{check_integrity(Path(raw))}\t{raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
