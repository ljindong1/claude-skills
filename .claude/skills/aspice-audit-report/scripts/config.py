"""체크리스트 양식의 시트명·컬럼 정의.

핵심 원칙 (V5.1 대응 개정):
1) 시트는 "있는 것만, 전부" 인식한다 — find_sheets()는 종류별 '리스트'를 반환.
   Target/WP 없는 Process 전용 양식, 차수별 Process 시트 여러 개가 모두 정상 입력이다.
2) 컬럼은 시트마다 다를 수 있다 — detect_cols(ws, kind)가 3행 머리글을 읽어
   시트별로 컬럼 위치를 감지한다(Applicable 열이 없는 구버전 레이아웃 대응,
   이때 cols["applicable"]는 None). 감지 실패 키는 아래 고정값 폴백.
3) 판정값 어휘에 'Conditional pass'(조건부 합격)를 포함한다. 합격 계열 비교는
   PASS_FAMILY 를 쓸 것.

주의: 머리글 행과 데이터 행이 병합 셀로 어긋나는 양식이 있으면 폴백 고정값을
쓰게 되므로, 새 양식 적용 시 make_blank_template.py의 "문항 칸" 검증 줄로 확인하라.
"""

DATA_START_ROW = 4
HEADER_ROW = 3

SHEET_PREFIX = {
    "process": "Process Checklist",
    "wp": "WP Checklist",
    "target": "Target",
}

# 판정값 어휘 — Conditional pass 포함
ALLOWED_RESULTS = ("Pass", "Fail", "Conditional pass", "확인 필요")
# 'AI 1차 의견 직접 기록' 정책: Result에 Pass/Fail/확인 필요를 기록하고 사람이 확정한다.
# '확인 필요'는 판정이 아니라 보류 표기 — 일치율 비교에서는 미판정으로 취급.
PASS_FAMILY = ("Pass", "Conditional pass")  # 합격 계열(일치율 비교 시 같은 묶음)


def is_pass(v):
    return str(v or "").strip() in PASS_FAMILY


# 데이터 행 기준 1-based 컬럼 (머리글 감지 실패 시 폴백)
PROCESS_COLS = dict(output_product=7, timing=12, recond=13, question=14, applicable=15,
                    result=16, comments=17, note=18, ncid=19)
WP_COLS = dict(product=2, question=3, applicable=4, result=5,
               comments=6, note=7, ncid=8)
TARGET_COLS = dict(product=3, file=4, bigo=5, note=6)

DEFAULT_COLS = {"process": PROCESS_COLS, "wp": WP_COLS, "target": TARGET_COLS}

# 3행 머리글 텍스트(startswith 매칭) → 컬럼 키
_HEADER_LABELS = {
    "process": [("output_product", "출력 작업 산출물"), ("timing", "실행시점"),
                ("recond", "재수행"), ("question", "Process Checklist"),
                ("applicable", "Applicable"), ("result", "Review Result"),
                ("comments", "Review Comments"), ("note", "Note"),
                ("ncid", "Non-conformances")],
    "wp": [("product", "작업 산출물"), ("question", "Work Product"),
           ("applicable", "Applicable"), ("result", "Review Result"),
           ("comments", "Review Comments"), ("note", "Note"),
           ("ncid", "Non-conformances")],
    "target": [("product", "출력 작업 산출물"), ("file", "파일 명"),
               ("bigo", "비고"), ("note", "Note")],
}

# 시트 종류별 "답 칸"(빈 양식 생성 시 비울 컬럼 키)
ANSWER_KEYS = {
    "process": ("applicable", "result", "comments", "ncid"),
    "wp": ("applicable", "result", "comments", "ncid"),
    "target": ("file", "bigo", "note"),
}


def find_sheets(wb):
    """워크북의 process/wp/target 시트명을 접두어로 전부 찾아 '리스트'로 반환.

    반환: {"process": [...], "wp": [...], "target": [...]} — 없으면 빈 리스트.
    (구버전은 첫 매치 1개만 반환했음 — 차수별 시트 여러 개를 놓치는 원인)
    """
    out = {k: [] for k in SHEET_PREFIX}
    for name in wb.sheetnames:
        for key, prefix in SHEET_PREFIX.items():
            if name.startswith(prefix):
                out[key].append(name)
                break
    return out


def sheet_kind(name):
    """시트명 → 'process'/'wp'/'target'/None."""
    for key, prefix in SHEET_PREFIX.items():
        if name.startswith(prefix):
            return key
    return None


def detect_cols(ws, kind):
    """시트 3행 머리글을 읽어 컬럼 위치를 감지. 감지 실패 키는 고정값 폴백.

    - 같은 워크북 안에서도 시트마다 레이아웃이 다를 수 있으므로(예: BJ1 V5.1의
      구버전 Process 시트는 Applicable 열 없음) 시트 단위로 호출할 것.
    - result는 감지됐는데 applicable이 머리글에 없으면 구버전 레이아웃으로 보고
      applicable=None 으로 둔다(폴백 고정값을 쓰면 엉뚱한 칸에 쓰게 됨).
    """
    labels = _HEADER_LABELS.get(kind, [])
    found = {}
    maxc = ws.max_column or 0
    for c in range(1, maxc + 1):
        v = ws.cell(HEADER_ROW, c).value
        if v is None:
            continue
        t = str(v).strip()
        for key, label in labels:
            if key not in found and t.startswith(label):
                found[key] = c
                break
    cols = dict(DEFAULT_COLS[kind])
    if found:
        # 머리글이 실제로 읽혔으면 감지값을 신뢰한다.
        cols.update(found)
        if kind in ("process", "wp") and "result" in found and "applicable" not in found:
            cols["applicable"] = None  # Applicable 열이 없는 레이아웃
    return cols


def clear_cols(cols, kind):
    """빈 양식 생성 시 비울 컬럼 번호 리스트(존재하는 컬럼만)."""
    return [cols[k] for k in ANSWER_KEYS[kind] if cols.get(k)]
