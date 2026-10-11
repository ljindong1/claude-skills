#!/usr/bin/env python3
"""당사 보호 설정이 바뀌었는지, 값이 비어 있던 파라미터(생성기 기본값 의존)가 생기거나 사라졌는지 검사한다.

누가 바꿨는지(C Studio Harmonize, mobilgene CLI, 사람의 수동 편집, 이 스킬의 반영)와 상관없이
"결과"만 본다. 그래서 S8 적용 직후, Harmonize 직후, S9 정적 검수, S10 빌드 검수에서 똑같이 쓴다.

1) 보호 설정 검사
   프로젝트 프로필(references/projects/<프로젝트>.md)의 '## 보호 설정' 표를 읽어
   각 키의 현재 값이 '당사 값'과 같은지 본다. 표 형식:
     | 구분 | 파일 | 키 | 당사 값 | 이유·근거 |
   - 구분: FBL / APP (--part 로 거른다)
   - 키: three_way.py 와 같은 '컨테이너 경로#파라미터 정의명' (예: /CanIf/CanIfPublicCfg#CanIfMetaDataSupport)
   - 당사 값: 값 그대로. '(없음)' 은 그 파라미터가 설정 파일에 없어야 한다는 뜻(생성기 기본값을 쓰는 상태)
   키의 컨테이너 이름이 바뀌면 '키 없음'으로 나온다 — 이름 변경인지 삭제인지 사람이 확인한다.

2) 기본값 의존 변화 (--before 를 줄 때)
   변경 전 형상과 비교해, 양쪽에 다 있는 컨테이너 안에서 파라미터가 새로 생기거나 사라진 것을 모은다.
   설정 파일에는 '값 추가'로만 보이지만 생성 코드에서는 기본값 → 명시값으로 바뀌는 지점이다
   (예: CanFdPaddingValue 없음 = 생성 255 → Harmonize 가 0 을 명시).

사용:
  python protected_check.py --profile <프로필.md> --root <앱 폴더> --part FBL
  python protected_check.py --profile <프로필.md> --root <앱 폴더> --part FBL --before <변경 전 앱 폴더>
  python protected_check.py --profile <프로필.md> --root <앱 폴더> --part FBL --before-rev HEAD   # git 커밋 기준
  [--md 결과.md]
<앱 폴더> 는 Configuration/ 이 들어 있는 폴더(예: psu_fbl). 종료 코드: 0 = 확인할 것 없음, 1 = 확인 필요 항목 있음.
결과의 '확인 필요'는 오류가 아니다. "동작 차이 없음"으로 보이더라도 사유를 판정표에 남기고 사용자 확인을 받으라는 뜻이다.
"""
import argparse, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from three_way import parse, SKIP_DIRS  # noqa: E402  (stdout UTF-8 설정도 three_way 가 한다)

NONE = "(없음)"


def read_rules(profile, part):
    rules, in_sec, header = [], False, None
    with open(profile, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("## "):
                in_sec = s[3:].strip().startswith("보호 설정")
                header = None
                continue
            if not in_sec or not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header = cells
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            row = dict(zip(header, cells))
            if part and row.get("구분", "").upper() not in (part.upper(), "공통"):
                continue
            key = row.get("키", "").strip("`")
            if key:
                rules.append({"part": row.get("구분", ""), "file": row.get("파일", "").strip("`"), "key": key,
                              "value": row.get("당사 값", "").strip("`"), "why": row.get("이유·근거", "")})
    return rules


def ecud_files(root):
    base = os.path.join(root, "Configuration")
    for d, dirs, fs in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in fs:
            if f.endswith(".arxml"):
                p = os.path.join(d, f)
                yield os.path.relpath(p, root).replace("\\", "/"), p


def load(root):
    """{상대경로: {key: values}}"""
    out = {}
    for rel, p in ecud_files(root):
        try:
            out[rel] = parse(p)
        except Exception as e:  # 깨진 파일은 따로 보고
            out[rel] = {"#<파싱 실패>": (str(e),)}
    return out


def load_rev(root, rev):
    top = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    prefix = os.path.relpath(os.path.abspath(root), top).replace("\\", "/")
    prefix = "" if prefix == "." else prefix + "/"
    names = subprocess.run(["git", "-C", top, "ls-tree", "-r", "--name-only", rev, prefix + "Configuration"],
                           capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for n in names:
            if not n.endswith(".arxml") or any(("/" + s + "/") in ("/" + n) for s in SKIP_DIRS):
                continue
            data = subprocess.run(["git", "-C", top, "show", f"{rev}:{n}"], capture_output=True).stdout
            p = os.path.join(tmp, "f.arxml")
            with open(p, "wb") as f:
                f.write(data)
            try:
                out[n[len(prefix):]] = parse(p)
            except Exception as e:
                out[n[len(prefix):]] = {"#<파싱 실패>": (str(e),)}
    return out


def merged(files):
    m = {}
    for rel, d in files.items():
        for k, v in d.items():
            m[k] = (v, rel)
    return m


def check_rules(rules, cur):
    rows = []
    for r in rules:
        hit = cur.get(r["key"])
        container = r["key"].split("#", 1)[0] + "#<존재>"
        if r["value"] == NONE:
            if hit is None:
                state = "유지" if container in cur else "키 없음(컨테이너 이름 변경·삭제 의심)"
                now = NONE
            else:
                state, now = "바뀜 — 값이 새로 명시됨(기본값 의존 해제)", ", ".join(hit[0])
        elif hit is None:
            state = "바뀜 — 파라미터 사라짐(기본값으로 돌아감)" if container in cur else "키 없음(컨테이너 이름 변경·삭제 의심)"
            now = NONE
        else:
            now = ", ".join(hit[0])
            state = "유지" if now == r["value"] else "바뀜"
        rows.append((r, now, state))
    return rows


def default_dependent(before, after):
    """양쪽에 다 있는 컨테이너 안에서 파라미터가 생기거나 사라진 것."""
    out = []
    for rel in sorted(set(before) | set(after)):
        b, a = before.get(rel, {}), after.get(rel, {})
        if b == a:
            continue
        for k in sorted(set(b) ^ set(a)):
            if k.endswith("#<존재>"):
                continue
            c = k.split("#", 1)[0] + "#<존재>"
            if c in b and c in a:
                out.append((rel, k, "생김" if k in a else "사라짐", ", ".join(a.get(k, b.get(k, ())))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--part", default="")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--before")
    g.add_argument("--before-rev")
    ap.add_argument("--md")
    o = ap.parse_args()

    rules = read_rules(o.profile, o.part)
    cur_files = load(o.root)
    cur = merged(cur_files)
    lines, need = [], 0

    lines.append(f"# 보호 설정 검사 ({o.part or '전체'}) — {os.path.abspath(o.root)}\n")
    if not rules:
        lines.append("> 프로필에 '## 보호 설정' 표가 없거나 해당 구분의 행이 없다. 프로필에 먼저 채운다.\n")
    else:
        lines.append("## 1. 보호 설정\n")
        lines.append("| 상태 | 파일 | 키 | 당사 값 | 현재 | 이유·근거 |")
        lines.append("|---|---|---|---|---|---|")
        for r, now, state in check_rules(rules, cur):
            mark = "✅" if state == "유지" else "⚠️ 확인 필요"
            need += state != "유지"
            lines.append(f"| {mark} {state} | {r['file']} | `{r['key']}` | {r['value']} | {now} | {r['why']} |")
        lines.append("")

    if o.before or o.before_rev:
        before = load(o.before) if o.before else load_rev(o.root, o.before_rev)
        dd = default_dependent(before, cur_files)
        lines.append("## 2. 기본값 의존 변화 (파라미터가 생기거나 사라짐)\n")
        if dd:
            lines.append("| 파일 | 키 | 변화 | 값 |")
            lines.append("|---|---|---|---|")
            for rel, k, how, v in dd:
                lines.append(f"| {rel} | `{k}` | ⚠️ {how} | {v} |")
            need += len(dd)
        else:
            lines.append("없음")
        lines.append("")
        broken = [rel for rel, d in cur_files.items() if "#<파싱 실패>" in d]
        if broken:
            lines.append("파싱 실패: " + ", ".join(broken))

    lines.append(f"\n확인 필요 {need}건. '동작 차이 없음'이어도 판정표에 사유를 쓰고 사용자 확인을 받는다.")
    text = "\n".join(lines)
    print(text)
    if o.md:
        with open(o.md, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(1 if need else 0)


if __name__ == "__main__":
    main()
