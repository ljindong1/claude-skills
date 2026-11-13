"""'적용 판단 기준' 문장 + 품번 조건(원본 H열, 정본 'Tool 표시') → 규칙(조건식) 변환과 차종별 평가.

원본 통합 진단사양서의 H열은 머리글이 'Diag Tool Display'지만 실제로는 그 항목이 적용되는 품번·사양 조건이다
("RR Wiper 적용품번 & 5DR", "-SMK 사양", "브라질 품번" 등). I열 '적용 판단 기준'과 H열은 AND 관계다.

규칙 형태(JSON):
  {"const": "O"|"X"}                                   상수
  {"signals": [...], "signals_mode": "all"|"any",      블록도 신호 존재 조건
   "sig_variant": {"L_x": "IMMO"},                     신호별 블록도 형 (기준 문구의 '(-SMK 사양)' / '(SMK 사양)')
   "sig_unknown": {"L_x": "북미"},                     신호별 붙은 판단 불가 조건 (지역 등)
   "variant": "IMMO"|"SMK"|None,                       항목 전체의 블록도 형 (H열 '-SMK 사양' 등)
   "features": [["ESCORT","WELCOME"], ["PDW"]],        기능사양표 조건 — 바깥 AND, 안쪽 OR
   "unknown": ["지역: 브라질", "품번: RR Wiper 적용품번"],  문서로 판단할 수 없는 AND 조건
   "or_unknown": ["TIOS : …"],                         신호 조건과 OR 로 묶인 판단 불가 대안
   "buses": ["HS-B-CAN"],                              버스 옵션(아직 평가 불가)
   "evaluable": true/false}

평가 결과 (3값 논리 + 조건부):
  "O"  — 모든 조건이 참
  "X"  — 하나라도 확실히 거짓
  "O?" — 판단 가능한 조건은 모두 참이고 판단 불가 조건(지역·품번 등)만 남음 (조건부 O)
  None — 판단할 자료가 없음 (블록도·기능사양표 없음, 해당 형 블록도 없음)
"""
from __future__ import annotations

import re

SIG = re.compile(r"\b(?:L|P|A|HS|LS|C|D|B|V)_[A-Za-z0-9]+(?:(?:\([+-]\))?_[A-Za-z0-9]+)*(?:\([+-]\))?")   # V_: 안테나 구동, (+)/(-): 극성 표시
FEAT_LINE = re.compile(r"기능\s*사양표\s*[:：]?\s*(.+)")
BUS = re.compile(r"Option\(([^)]+)\)")
SPLIT_OR = re.compile(r"\s+or\s+|\s*\|\|\s*|\s+또는\s+", re.I)
SPLIT_AND = re.compile(r"\s*&&\s*|\s+&\s+|\s+and\s+", re.I)

REGIONS = ("브라질", "북미", "러시아", "유럽", "중국", "중동", "내수", "일반", "호주", "캐나다", "미국", "멕시코", "인도")
REGION_RE = re.compile("(" + "|".join(REGIONS) + ")")
NON_SMK = re.compile(r"(?:^|[\s(&/])(?:-\s*SMK|NON[\s-]*SMK)\b", re.I)
BODY_RE = re.compile(r"\b([45])\s*DR\b", re.I)
PN_RE = re.compile(r"적용\s*품번|품번|적용\s*차량|적용\s*차종|사양")


def _clean_feature(tok: str) -> str:
    t = tok.strip().strip("-:·,")
    t = re.sub(r"^차속\s*-\s*", "", t)
    t = re.sub(r"\s*(적용\s*시|적용시|적용|\(.*?\))\s*$", "", t)
    t = re.sub(r"\s+(?:or|또는)$", "", t.strip(), flags=re.I)        # 줄 끝에 걸린 'or'
    return t.strip().upper()


def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def parse_pn(text: str) -> dict:
    """원본 H열(품번·사양 조건) → {"variant", "features", "unknown", "or_unknown"}.

    '○○ 적용품번' 하나만 적힌 경우는 '그 기능이 있는 품번' = 블록도에 그 신호가 그려짐과 같은 뜻이라 추가 조건이 아니다.
    추가 조건으로 보는 한정어:
    - '-SMK 사양' / 'NON-SMK 품번' / 'Non SMK 사양' → IMMO형 블록도로 판단, 'SMK 사양'·'SMK 적용품번' → SMK형
    - '5DR' / '4DR' → 기능사양표 차체 형식
    - 지역(브라질·북미·러시아 …), '-IMMO', '차종별 상이', '확인필요', 사양별 번호 나열 → 판단 불가
    - '&' 로 붙은 둘째 품번 조건 ('FRONT WIPER & SERVICE POSITION 적용품번') → 판단 불가
    - 'or' 로 붙은 다른 대안 ('음성인식(선루프) 적용품번 or …') → 신호가 없을 때 판단 불가
    'O,X 기준' 은 'I열 기준을 따른다'는 뜻이라 조건이 아니다. 괄호 안 표출 조건('(IGN1 Off시 미 표출)')은 적용 조건이 아니다.
    """
    t = (text or "").replace("\xa0", " ").strip()
    out = {"variant": None, "features": [], "unknown": [], "or_unknown": []}
    if not t:
        return out
    body = re.sub(r"O\s*[,/]\s*X\s*기준\s*&?", "", t, flags=re.I).strip()
    if not body:
        return out
    if re.search(r"(?m)^\s*\d\.\s", body):
        # 번호 나열: 사양(SMK·지역)별 조건이면 판단 불가, 블록도·기능사양표 판단법을 적은 것이면 I열 기준의 설명이라 무시
        if re.search(r"SMK|IMMO", body, re.I) or REGION_RE.search(body):
            out["unknown"].append("사양별 조건: " + _one_line(body)[:60])
        return out
    flat = _one_line(body)
    flat = re.sub(r"\([^()]*(?:표출|기능사양표 표현)[^()]*\)", " ", flat)          # 표출 조건·해석 메모
    if re.search(r"확인\s*필요|메모\s*참조", flat):
        out["unknown"].append("확인 필요: " + flat[:60])
        return out
    if re.search(r"-\s*IMMO", flat, re.I):
        out["unknown"].append("품번: -IMMO")
    if re.search(r"차종별\s*상이", flat):
        out["unknown"].append("품번: 차종별 상이")
    if NON_SMK.search(" " + flat) and re.search(r"-\s*IMMO", flat, re.I):
        out["variant"] = "NON_SMK_NON_IMMO"                 # SMK도 IMMO도 아닌 품번 — 블록도에 그 형 쪽이 없으면 판단 불가
        out["unknown"] = [u for u in out["unknown"] if u != "품번: -IMMO"]
    elif NON_SMK.search(" " + flat):
        out["variant"] = "IMMO"
    elif re.search(r"(?<![-A-Z])\bSMK\b", flat, re.I) and re.search(r"SMK\s*(?:사양|품번|적용)", flat, re.I):
        out["variant"] = "SMK"
    m = BODY_RE.search(flat)
    if m:
        out["features"].append([f"{m.group(1)}DR"])
    for rg in dict.fromkeys(REGION_RE.findall(flat)):
        out["unknown"].append(f"지역: {rg}")
    # 'A or B 적용품번' 은 기능명을 나열한 것이라 대안 조건으로 보지 않는다 (신호 쪽 대안은 I열 '또는 …' 에서 잡는다)
    # 형·차체·지역·-IMMO 를 걷어내고 '&' 로 남는 품번 조건이 둘 이상이면 판단 불가
    rest = re.sub(r"-\s*IMMO|(?:-|NON[\s-]*)\s*SMK|\bSMK\b|\b[45]\s*DR\b|차종별\s*상이|\*", " ", flat, flags=re.I)
    rest = REGION_RE.sub(" ", rest)
    segs = [s for s in (re.sub(r"\s+", " ", x).strip(" /()") for x in re.split(r"&|\bor\b|또는", rest, flags=re.I))
            if re.sub(r"사양|지역|품번|적용|[\s/:()]", "", s)]
    if len([s for s in re.split(r"&", rest) if re.sub(r"사양|지역|품번|적용|[\s/:()]", "", s)]) >= 2:
        out["unknown"].append("품번: " + flat[:60])
    return out


def _signal_annotations(t: str, sigs: list[str]) -> tuple[dict, dict]:
    """기준 문구 줄마다 붙은 '(-SMK 사양)', '(SMK 사양) - 북미' 표시 → 신호별 형·지역."""
    var, unk = {}, {}
    for line in t.split("\n"):
        found = [s for s in sigs if s in line]
        if not found:
            continue
        rest = line
        for s in found:
            rest = rest.replace(s, " ")
        v = "IMMO" if NON_SMK.search(" " + rest) else "SMK" if re.search(r"\bSMK\b", rest) else None
        rg = REGION_RE.findall(rest)
        for s in found:
            if v:
                var[s] = v
            if rg:
                unk[s] = "지역: " + "/".join(dict.fromkeys(rg))
    return var, unk


def _criteria_extras(t: str, has_signals: bool, feature_lines: set[int]) -> tuple[list[str], list[str]]:
    """기준 문구에서 신호·기능사양표가 아닌 조건 조각 → (AND 판단 불가, OR 판단 불가)."""
    unknown, or_unknown = [], []
    lines = t.split("\n")
    flat_lines = []
    for i, line in enumerate(lines):
        if i in feature_lines:
            continue
        flat_lines.append(line)
    text = "\n".join(flat_lines)
    # 괄호 안 '(○○ 적용 품번)' 은 신호 존재와 같은 뜻이라 조건이 아니다
    text = re.sub(r"\([^()]*적용\s*품번[^()]*\)", " ", text)
    # '&' 로 이어진 조각 중 신호·블록도·기능사양표가 없는 것 → AND 판단 불가 ('& 직구동 타입(접점 타입)', '브라질 품번 &')
    for seg in re.split(r"&&|&", text):
        s = _one_line(re.sub(r"\([^)]*\)", " ", seg))
        if not s or SIG.search(seg) or "블록도" in s or "기능" in s:
            continue
        if REGION_RE.search(s):
            unknown += [f"지역: {r}" for r in dict.fromkeys(REGION_RE.findall(s))]
        elif len(s) >= 2 and not re.fullmatch(r"[-*/.\s]*", s):
            unknown.append("조건: " + s[:40])
    # 신호 조건과 '또는'/'or' 로 묶인, 신호가 없는 대안 ('또는 TIOS : Sunroof Open State Transfer Function')
    if has_signals:
        for m in re.finditer(r"(?:또는|\bor\b)\s*\n?\s*([^\n]+)", text, re.I):
            alt = m.group(1)
            if not SIG.search(alt) and "기능" not in alt and alt.strip():
                or_unknown.append(_one_line(alt)[:60])
    return list(dict.fromkeys(unknown)), or_unknown


def parse_rule(text: str, pn_text: str = "", hint_signals: list[str] | None = None) -> dict:
    """hint_signals: 기준에 '블록도'만 적고 신호명이 없을 때 쓸 신호 (SMK: 항목 이름·Actuator Name 열의 신호)."""
    t = (text or "").replace("\xa0", " ").strip()
    pn = parse_pn(pn_text)
    if not t:
        return {"evaluable": False, "reason": "no_criteria"}
    head = t.split("\n")[0].strip()
    if re.match(r"^\*?\s*미\s*사용", head) or re.match(r"^미\s*적용\s*$", head):
        return {"const": "X", "evaluable": True, "reason": "unused"}
    if head.upper() in ("O", "X"):                          # SMK '검토 방법'에 값 자체가 적힌 경우
        return {"const": head.upper(), "evaluable": True, "reason": "const"}
    if head.upper() in ("STD", "기본적용", "기본 적용"):
        return {"const": "O", "evaluable": True, "reason": "standard"}

    rule: dict = {"signals": [], "signals_mode": "all", "sig_variant": {}, "sig_unknown": {}, "variant": pn["variant"],
                  "features": [], "unknown": [], "or_unknown": [], "buses": [], "evaluable": False}
    if "블록도" in t or SIG.search(t):
        sigs = []
        for s in SIG.findall(t):
            if len(s) > 5 and s not in sigs:
                sigs.append(s)
        if not sigs and hint_signals and "블록도" in t:     # '블록도'만 적힌 기준 → 항목 이름의 신호
            sigs = [s for s in hint_signals if len(s) > 5]
        rule["signals"] = sigs
        # 신호가 여럿이면 기본은 '하나라도 있으면'(변형별 대체 신호를 나열하는 관행). '&'로 묶인 경우만 '모두'.
        rule["signals_mode"] = "all" if (len(sigs) > 1 and re.search(r"_(?:IN|OUT)\S*\s*(?:&|&&|and)\s*", t, re.I)
                                         and not re.search(r"\s+(?:or|또는)\s+", t, re.I)) else "any"
        rule["sig_variant"], rule["sig_unknown"] = _signal_annotations(t, sigs)
    feature_lines: set[int] = set()
    for m in FEAT_LINE.finditer(t):                      # (기존 동작 유지) '기능사양표 :' 뒤 첫 줄의 기능명
        line = m.group(1).split("\n")[0]
        first = t.count("\n", 0, m.start())
        last = t.count("\n", 0, m.start(1) + len(line))
        feature_lines.update(range(first, last + 1))
        line = re.split(r"\s*(?:&\s*블록도|블록도)", line)[0]
        for grp in SPLIT_AND.split(line):
            alts = [_clean_feature(a) for a in SPLIT_OR.split(grp)]
            alts = [a for a in alts if a and a not in ("O", "X")]
            if alts:
                rule["features"].append(alts)
    lines = t.split("\n")                               # 기능사양표 줄에 'or' 로 이어지는 줄도 기능사양표 조건의 일부
    for i in sorted(feature_lines):
        j = i
        while j + 1 < len(lines) and (re.search(r"\b(?:or|또는)\s*$", lines[j], re.I)
                                      or re.match(r"\s*(?:or|또는)\b", lines[j + 1], re.I)):
            j += 1
            feature_lines.add(j)
    for m in BUS.finditer(t):
        rule["buses"] += [b.strip().upper() for b in SPLIT_OR.split(m.group(1))]
    unk, or_unk = _criteria_extras(t, bool(rule["signals"]), feature_lines)
    rule["unknown"] = list(dict.fromkeys(unk + pn["unknown"]))
    if rule["sig_variant"] or rule["sig_unknown"]:          # 신호마다 형·지역이 적혀 있으면 H열 사양별 나열은 같은 내용
        rule["unknown"] = [u for u in rule["unknown"] if not u.startswith("사양별 조건")]
    rule["or_unknown"] = or_unk + pn["or_unknown"]
    rule["features"] += [f for f in pn["features"] if f not in rule["features"]]
    # 기능사양표 조건이 이미 있으면 H열의 '… 적용품번'은 그 기능사양표(=품번사양표) 조건과 같은 뜻으로 본다
    if any(not set(f) <= {"4DR", "5DR"} for f in rule["features"]):
        rule["unknown"] = [u for u in rule["unknown"] if not u.startswith("품번:") or "IMMO" in u or "상이" in u]
        rule["or_unknown"] = []
    rule["evaluable"] = bool(rule["signals"] or rule["features"])
    if not rule["evaluable"]:
        rule["reason"] = "bus_only" if rule["buses"] else "free_text"
    return rule


# 판단 기준과 블록도가 같은 신호를 다르게 적은 경우 (이름 앞부분 바꿈). 근거를 같이 적는다.
SIG_ALIASES = {
    # SMK IOCBI 0xF04C: 판단 기준 V_FrontBumperANT, 블록도 V_FRTBumperANT — 블록도에 있는 차종(SP2 PE)만 O, 나머지 X로 정확히 일치 (2026-11-03)
    "V_FrontBumperANT": "V_FRTBumperANT",
}


def _sig_present(sig: str, present: set[str]) -> bool:
    for a, b in SIG_ALIASES.items():
        if sig.startswith(a) and _sig_present(b + sig[len(a):], present):
            return True
    if sig in present:
        return True
    # 도면 텍스트 잘림 보정: 접두사 관계면 같은 신호로 본다
    return any(p.startswith(sig) or sig.startswith(p) for p in present if min(len(p), len(sig)) >= 10)


def _feature_applied(token: str, feats: dict[str, bool]) -> bool | None:
    """feats: 기능명(대문자) → 적용 여부. 토큰의 단어가 모두 들어 있는 기능명을 찾는다."""
    words = [w for w in re.split(r"[^A-Z0-9]+", token) if len(w) > 1]
    if not words:
        return None
    hits = [v for name, v in feats.items() if all(w in re.split(r"[^A-Z0-9]+", name) or w in name for w in words)]
    if not hits:
        return None
    return any(hits)


COND = "cond"   # 판단 불가 조건(지역·품번·대안)이 걸려 O일 수도 X일 수도 있음 — 자료 없음(None)과 구분한다


def _or3(vals: list) -> object:
    for want in (True, COND, None):
        if any(v is want for v in vals):
            return want
    return False


def _and3(vals: list) -> object:
    for want in (False, None, COND):
        if any(v is want for v in vals):
            return want
    return True


def evaluate(rule: dict, project: str, signals_by_project: dict[str, set[str]],
             features_by_project: dict[str, dict[str, bool]],
             variants_by_project: dict[str, dict[str, set[str]]] | None = None) -> tuple[str | None, str]:
    """반환: (결과 'O'/'X'/'O?'/None, 사유)"""
    if not rule.get("evaluable"):
        return None, rule.get("reason", "not_evaluable")
    if "const" in rule:
        return rule["const"], rule.get("reason", "const")
    variants = (variants_by_project or {}).get(project, {})
    parts: list[bool | None] = []      # 판단 가능한 조건
    why = []
    if rule["signals"]:
        present_all = signals_by_project.get(project)
        if present_all is None:
            parts.append(None); why.append("no_blockdiag")
        else:
            checks, marks = [], []
            for s in rule["signals"]:
                v = rule.get("sig_variant", {}).get(s) or rule.get("variant")
                if v:
                    pool = variants.get(v)
                    if pool is None:                      # 그 형의 블록도 쪽이 없다
                        checks.append(None); marks.append(f"no_{v}")
                        continue
                    ok = _sig_present(s, set(pool))
                else:
                    ok = _sig_present(s, present_all)
                if ok and s in rule.get("sig_unknown", {}):
                    checks.append(COND); marks.append("1?")    # 신호는 있으나 지역 조건을 알 수 없음
                else:
                    checks.append(ok); marks.append("1" if ok else "0")
            res = _or3(checks) if rule["signals_mode"] == "any" else _and3(checks)
            if res is False and rule.get("or_unknown"):
                res = COND; marks.append("or?")              # 신호는 없지만 판단 불가 대안이 있음
            parts.append(res); why.append(("signals" + (f"[{rule['variant']}]" if rule.get("variant") else "") + ":")
                                          + ",".join(marks))
    for alts in rule["features"]:
        feats = features_by_project.get(project)
        if feats is None:
            parts.append(None); why.append("no_funcspec")
            continue
        res = [_feature_applied(a, feats) for a in alts]
        if all(r is None for r in res):
            parts.append(None); why.append("feature_unmatched:" + "|".join(alts))
        else:
            parts.append(any(r for r in res if r)); why.append("features:" + ",".join(str(r) for r in res))
    unknown = rule.get("unknown") or []
    if unknown:
        why.append("조건부:" + " / ".join(unknown))
    r = _and3(parts)
    if r is False:
        return "X", ";".join(why)
    if r is None:
        # 판단 가능한 조건 중 참이 하나라도 있고 나머지가 자료 없음(해당 차종 기능사양표 없음 등)이면 조건부 O
        if any(p is True for p in parts) and not any(p is None and w.startswith("signals") for p, w in zip(parts, why)):
            return "O?", ";".join(why)
        return None, ";".join(why)
    return ("O?" if (unknown or r is COND) else "O"), ";".join(why)
