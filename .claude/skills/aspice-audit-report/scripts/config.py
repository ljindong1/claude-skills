"""체크리스트 양식의 시트명·컬럼 인덱스 정의 (1-based).

양식이 개정되어 열이 추가/삭제되면 이 파일을 먼저 갱신할 것.
시트명은 단계 접미사("_P1 소프트웨어 설계" 등)가 붙으므로 접두어로 매칭한다.
주의: 머리글 행과 데이터 행이 병합 셀로 한 칸 어긋날 수 있어, 아래 값은
실제 '데이터 행' 기준 컬럼이다(머리글의 openpyxl 인덱스와 다를 수 있음).
"""

DATA_START_ROW = 4

SHEET_PREFIX = {
    "process": "Process Checklist",
    "wp": "WP Checklist",
    "target": "Target",
}

# 데이터 행 기준 1-based 컬럼
PROCESS_COLS = dict(output_product=7, timing=12, recond=13, question=14, applicable=15,
                    result=16, comments=17, note=18, ncid=19)
WP_COLS = dict(product=2, question=3, applicable=4, result=5,
               comments=6, note=7, ncid=8)
TARGET_COLS = dict(product=3, file=4, bigo=5, note=6)

# 비울 답 칸 (빈 양식 생성용)
CLEAR_COLS = {
    "process": [PROCESS_COLS[k] for k in ("applicable", "result", "comments", "ncid")],
    "wp": [WP_COLS[k] for k in ("applicable", "result", "comments", "ncid")],
    "target": [TARGET_COLS[k] for k in ("file", "bigo", "note")],
}


def find_sheets(wb):
    """워크북에서 process/wp/target 시트명을 접두어로 찾아 반환."""
    out = {}
    for key, prefix in SHEET_PREFIX.items():
        for name in wb.sheetnames:
            if name.startswith(prefix):
                out[key] = name
                break
    return out
