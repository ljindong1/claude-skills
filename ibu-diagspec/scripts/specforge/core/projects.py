"""차종(프로젝트) 이름 정규화.

세 문서(기능사양표·진단사양서·블록도)가 같은 차종을 서로 다른 표기로 적으므로
표기 → 마스터 코드로 모으는 규칙을 한 곳에 둔다. 규칙으로 안 잡히는 경우는
aliases.yaml(수동 별칭표)에서 덮어쓴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_WS = re.compile(r"\s+")
_PAREN = re.compile(r"\([^)]*\)")  # (C2, C9) 같은 괄호 주석 제거
_IBU_SUFFIX = re.compile(r"\s*IBU\s*\(.*$", re.I)  # 블록도 제목의 'IBU(BCM+TPMS+SMK)_ ...' 꼬리
_FUNC_PREFIX = re.compile(r"^IBU_(HW|EOL)\s*품번사양표_?", re.I)  # 기능사양표 시트명 머리


def _basic(name: str) -> str:
    s = name.replace("\xa0", " ").replace("\n", " ")
    s = _IBU_SUFFIX.sub("", s)
    s = _FUNC_PREFIX.sub("", s)
    s = _PAREN.sub("", s)
    s = s.replace("F/L", "FL").replace("N/LINE", "NLINE").replace("N-LINE", "NLINE").replace("N LINE", "NLINE")
    s = s.replace("/", " ").replace("-", "_")
    s = _WS.sub(" ", s).strip()
    s = s.replace(" ", "_")
    return s.upper()


def variant_of(title: str) -> str | None:
    """블록도 제목에서 SMK/IMMO 형을 뽑는다."""
    m = re.search(r"\((BCM\+TPMS\+(SMK|IMMO))\)", title)
    return m.group(2) if m else None


@dataclass
class ProjectRegistry:
    """표기 → 코드 매핑과, 코드별로 어느 문서에서 보였는지 기록."""

    aliases: dict[str, str] = field(default_factory=dict)  # 수동 별칭(정규화 전 표기 → 코드)
    codes: dict[str, dict] = field(default_factory=dict)  # code → {aliases:set, sources:set}

    @classmethod
    def load(cls, alias_file: Path | None) -> "ProjectRegistry":
        reg = cls()
        if alias_file and alias_file.exists():
            data = yaml.safe_load(alias_file.read_text(encoding="utf-8")) or {}
            for code, names in (data.get("aliases") or {}).items():
                for n in names:
                    reg.aliases[_basic(n)] = code
        return reg

    def code_for(self, raw: str, source: str) -> str:
        b = _basic(raw)
        code = self.aliases.get(b, b)
        ent = self.codes.setdefault(code, {"aliases": set(), "sources": set()})
        ent["aliases"].add(raw.replace("\n", " ").strip())
        ent["sources"].add(source)
        return code

    def export(self) -> list[dict]:
        return [
            {"code": c, "aliases": sorted(v["aliases"]), "sources": sorted(v["sources"])}
            for c, v in sorted(self.codes.items())
        ]
