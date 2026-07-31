"""Intent 지식베이스(intent_map.json) 로더·유틸 — Phase B.

[evidence 브리핑 재정의, references/roadmap.md]
ASPICE PAM 4.0 문항은 매우 general하게 기술되어 조직이 사내 프로세스로 adapt한다.
그래서 문항 문구가 아니라 그 문항이 확인하려는 '목적(Intent)'을 중심으로 점검해야 한다.
이 파일은 문항별 Intent 정의(intent_map.json)를 읽어, 코멘트 머리에 붙일
`[의도]` 라인을 만들고, 대체 근거 후보 키워드를 제공한다.

intent_map.json 구조(assets/intent_map.schema.json 참고):
{
  "_meta": {...},
  "entries": [
    {"sheet":"wp"|"process", "no":2, "product":"프로젝트 계획서",
     "question_excerpt":"...", "intent":"...", "pam_ref":"MAN.5 / SUP.1",
     "focus":"...", "depth":"존재성|내용|시스템",
     "primary_location":"...", "alt_evidence":["...","..."]}
  ]
}

키: (sheet, no, product). WP는 No가 산출물마다 중복되므로 product가 필수 구분자다.
Process는 product에 출력 산출물/활동명을 넣는다(없으면 no만으로 매칭).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def _norm(s: Any) -> str:
    return str(s or "").strip().splitlines()[0][:40] if s is not None else ""


class IntentMap:
    """intent_map.json 을 로드해 (sheet,no,product) 로 조회한다."""

    def __init__(self, entries: List[Dict[str, Any]], meta: Optional[Dict] = None):
        self.meta = meta or {}
        self._by_key: Dict[tuple, Dict[str, Any]] = {}
        self._by_no: Dict[tuple, Dict[str, Any]] = {}
        for e in entries:
            sheet = str(e.get("sheet", "")).strip().lower()
            no = e.get("no")
            prod = _norm(e.get("product"))
            self._by_key[(sheet, no, prod)] = e
            self._by_no.setdefault((sheet, no), e)  # product 미지정 fallback

    @classmethod
    def load(cls, path: str) -> "IntentMap":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):            # entries 배열만 준 경우 허용
            return cls(data)
        return cls(data.get("entries", []), data.get("_meta"))

    def get_exact(self, sheet: str, no: Any, product: Any = None) -> Optional[Dict[str, Any]]:
        """정확히 (sheet,no,product)로만 조회 — WP No 중복 시 오매칭 방지."""
        return self._by_key.get((str(sheet or "").strip().lower(), no, _norm(product)))

    def get(self, sheet: str, no: Any, product: Any = None) -> Optional[Dict[str, Any]]:
        sheet = str(sheet or "").strip().lower()
        exact = self._by_key.get((sheet, no, _norm(product)))
        if exact is not None:
            return exact
        # product 미지정 fallback은 Process에만 허용(WP는 No가 산출물마다 중복되므로 위험)
        if sheet == "process":
            return self._by_no.get((sheet, no))
        return None

    def intent_line(self, sheet: str, no: Any, product: Any = None) -> str:
        """코멘트 머리에 붙일 `[의도]` 한 줄. 항목이 없으면 안내 문구."""
        e = self.get(sheet, no, product)
        if not e or not str(e.get("intent", "")).strip():
            return "[의도] (미정의 — intent_map.json에 정의 후 사용, 없으면 감사자 확인 권장)"
        parts = [str(e["intent"]).strip()]
        extra = []
        if e.get("focus"):
            extra.append("초점: " + str(e["focus"]).strip())
        if e.get("depth"):
            extra.append("깊이: " + str(e["depth"]).strip())
        if e.get("pam_ref"):
            extra.append("PAM: " + str(e["pam_ref"]).strip())
        tail = (" (" + ", ".join(extra) + ")") if extra else ""
        return "[의도] " + parts[0] + tail

    def alt_keywords(self, sheet: str, no: Any, product: Any = None) -> List[str]:
        """이 문항의 Intent를 충족할 수 있는 대체 근거 키워드(evidence_search용)."""
        e = self.get(sheet, no, product)
        if not e:
            return []
        kws: List[str] = []
        if e.get("primary_location"):
            kws.append(str(e["primary_location"]))
        for a in e.get("alt_evidence", []) or []:
            kws.append(str(a))
        return kws

    def is_filled(self, sheet: str, no: Any, product: Any = None) -> bool:
        e = self.get(sheet, no, product)
        return bool(e and str(e.get("intent", "")).strip())

    def unfilled(self) -> List[Dict[str, Any]]:
        """intent가 비어 있는 항목 목록(작성 진행률 추적용)."""
        return [e for e in self._by_key.values() if not str(e.get("intent", "")).strip()]

    def __len__(self) -> int:
        return len(self._by_key)


def try_load(path: Optional[str]) -> Optional[IntentMap]:
    """경로가 없거나 로드 실패해도 예외 없이 None 반환(선택적 통합용)."""
    if not path or not os.path.exists(path):
        return None
    try:
        return IntentMap.load(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
