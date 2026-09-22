# -*- coding: utf-8 -*-
"""정정 이력 대조기 - 여러 차례 정정된 증권신고서를 원본부터 최종 확정까지 이어 붙여 보여준다.

데이터는 build_data.py 가 만든 data/cases.json 만 읽는다. 앱에서 원문을 다시 파싱하지 않는다.
"""
from __future__ import annotations

import difflib
import json
import re
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "cases.json"

st.set_page_config(page_title="정정 이력 대조기", page_icon="📄", layout="wide")

CSS = """
<style>
  .stApp { background: #eef2f7; }
  html, body, [class*="css"] { font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; }
  .num { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
  .lead { color:#4a5a6a; font-size:0.95rem; line-height:1.6; margin:-8px 0 18px; }
  .card { background:#fff; border:1px solid #d9e1ea; border-radius:10px;
          padding:18px 20px; margin-bottom:16px; }
  .card h3 { margin:0 0 12px; font-size:1.0rem; color:#2c3e50; letter-spacing:-0.01em; }
  .path { display:flex; flex-wrap:wrap; align-items:center; gap:10px; }
  .step { display:flex; flex-direction:column; gap:2px; }
  .val { font-size:1.45rem; font-variant-numeric: tabular-nums; color:#8a97a5;
         text-decoration: line-through; text-decoration-thickness:1.5px; }
  .val.final { color:#16324f; font-weight:700; text-decoration:none; }
  .rnd { font-size:0.74rem; color:#77869a; }
  .arrow { color:#9fb0c2; font-size:1.2rem; padding:0 2px; }
  .badge { display:inline-block; background:#16324f; color:#fff; border-radius:4px;
           padding:1px 6px; font-size:0.68rem; margin-left:6px; vertical-align:2px; }
  .summary { margin-top:12px; color:#41556b; font-size:0.9rem; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }
  .scroll { overflow-x:auto; }
  table.grid { border-collapse:collapse; width:100%; font-size:0.86rem; min-width:620px; }
  table.grid th, table.grid td { border:1px solid #dde4ec; padding:7px 10px; text-align:right;
                                 font-variant-numeric: tabular-nums; white-space:nowrap; }
  table.grid th { background:#f2f6fa; color:#3a4a5c; font-weight:600; text-align:center; }
  table.grid td.k { text-align:left; background:#f8fafc; color:#3a4a5c; white-space:normal; }
  table.grid td.same { color:#9aa7b5; }
  table.grid td.none { color:#c2ccd6; }
  .chg { font-weight:700; }
  .moved { color:#6b7f95; font-size:0.8rem; }
  .warn { background:#fdf3f2; border:1px solid #e8bdb8; color:#8d2b20;
          border-radius:8px; padding:12px 14px; margin-bottom:10px; font-size:0.88rem; }
  .info { background:#f2f6fa; border:1px solid #d9e1ea; color:#41556b;
          border-radius:8px; padding:12px 14px; font-size:0.88rem; }
  .blk { background:#f8fafc; border:1px solid #e3eaf1; border-radius:6px; padding:10px 12px;
         font-size:0.8rem; color:#3f5168; line-height:1.55; white-space:pre-wrap;
         max-height:240px; overflow:auto; }
  .foot { color:#7d8b9b; font-size:0.8rem; border-top:1px solid #d9e1ea;
          padding-top:12px; margin-top:22px; }
  /* --- 정정 전/후 차이 표시 --- */
  del.d { background:#fdeaea; color:#9b2c20; text-decoration:line-through;
          text-decoration-thickness:1.5px; border-radius:3px; padding:0 2px; }
  ins.i { background:#e6f4ea; color:#14622f; text-decoration:none;
          border-radius:3px; padding:0 2px; font-weight:600; }
  .gap { color:#b6c2ce; padding:0 4px; }
  .note { background:#fff; border:1px solid #d9e1ea; border-left:4px solid #16324f;
          border-radius:8px; padding:14px 16px; margin:10px 0; scroll-margin-top:70px; }
  .note h4 { margin:0 0 4px; font-size:0.92rem; color:#16324f; }
  .note .meta { color:#77869a; font-size:0.78rem; margin-bottom:10px; }
  .chip { display:inline-block; background:#f2f6fa; border:1px solid #d9e1ea;
          border-radius:14px; padding:3px 10px; margin:0 6px 6px 0; font-size:0.82rem;
          font-variant-numeric: tabular-nums; }
  .chip b { color:#14622f; }
  .chip s { color:#9b2c20; }
  .difftext { font-size:0.82rem; line-height:1.75; color:#3f5168;
              background:#fbfcfe; border:1px solid #e3eaf1; border-radius:6px;
              padding:10px 12px; max-height:300px; overflow:auto; }
  .split { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  @media (max-width:820px) { .split { grid-template-columns:1fr; } }
  .side { border:1px solid #e3eaf1; border-radius:6px; background:#fbfcfe;
          max-height:340px; overflow:auto; }
  .side .hd { position:sticky; top:0; background:#f2f6fa; border-bottom:1px solid #e3eaf1;
              padding:6px 10px; font-size:0.76rem; font-weight:600; color:#5a6b7d; }
  .side.before .hd { color:#9b2c20; }
  .side.after  .hd { color:#14622f; }
  .drow { display:flex; gap:8px; padding:6px 10px; border-top:1px solid #edf1f6;
          font-size:0.82rem; line-height:1.65; color:#3f5168; }
  .drow:first-of-type { border-top:none; }
  .rn { color:#b6c2ce; min-width:20px; text-align:right; font-variant-numeric:tabular-nums; }
  .ctx { color:#a7b3c0; }
  .empty { color:#b6c2ce; font-style:italic; }
  .full { padding:10px 12px; font-size:0.82rem; line-height:1.7; color:#3f5168;
          white-space:pre-wrap; }
  a.jump { color:#16324f; font-weight:600; text-decoration:none;
           border-bottom:1px dashed #9fb0c2; }
  a.jump:hover { background:#eaf1f8; }
  .nodiff { color:#8a97a5; font-size:0.82rem; }
  .stButton > button { width:100%; border:1px solid #cfdae5; background:#fff; color:#33485e;
                       font-size:0.82rem; padding:6px 4px; border-radius:7px; }
  .stButton > button:hover { border-color:#16324f; color:#16324f; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------------------ 데이터
@st.cache_data
def load_cases():
    if not DATA.exists():
        st.error("data/cases.json 이 없습니다. 먼저 `python build_data.py` 를 실행하세요.")
        st.stop()
    return json.loads(DATA.read_text(encoding="utf-8"))


CASES = load_cases()


def to_int(text):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None


def pick(values, *keys):
    for key in keys:
        if key in values:
            return values[key]
    return None


def won(n):
    return "-" if n is None else format(n, ",") + "원"


def short_won(n):
    """대표 경로용. 조/억 단위로 줄인다."""
    if n is None:
        return "-"
    if n >= 10 ** 12:
        return format(n / 10 ** 12, ",.2f").rstrip("0").rstrip(".") + "조원"
    if n >= 10 ** 8:
        return format(n / 10 ** 8, ",.0f") + "억원"
    return format(n, ",") + "원"


# 사례 종류별 '주요 항목' 정의: (표시명, values 키 후보, 단위)
EQUITY_ROWS = [
    ("모집주식수", ("shares",), "주"),
    ("1주당 가액", ("price_fixed", "price_plan"), "원"),
    ("모집총액", ("total_fixed", "total_plan"), "원"),
]
DEBT_ROWS = [
    ("118-1 모집금액 (2년물)", ("amt_118-1",), "원"),
    ("118-2 모집금액 (3년물)", ("amt_118-2",), "원"),
    ("발행금액 합계", ("total_fixed", "total_plan"), "원"),
    ("희망금리밴드", ("band",), ""),
    ("118-1 가산금리", ("spread_118-1",), ""),
    ("118-2 가산금리", ("spread_118-2",), ""),
    ("118-1 확정금리", ("rate_118-1",), ""),
    ("118-2 확정금리", ("rate_118-2",), ""),
    ("발행일", ("issue_date",), ""),
]


def rows_of(case):
    return DEBT_ROWS if case["kind"] == "debt" else EQUITY_ROWS


# ------------------------------------------------------- 정정 전/후 차이 (블록 비교)
TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[가-힣]+|[A-Za-z]+|\s+|[^\s]")
NUMTOK = re.compile(r"^\d[\d,]*(?:\.\d+)?$")


def tokenize(text):
    return TOKEN.findall(text or "")


def opcodes(before, after):
    a, b = tokenize(before), tokenize(after)
    return a, b, difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()


def merge_ops(ops, gap=4):
    """변경 - 짧은 동일구간 - 변경 을 하나로 합친다.

    difflib 은 '2,300' 처럼 쉼표가 낀 숫자를 여러 조각으로 쪼개 놓는데,
    그대로 두면 한 군데 수정이 대여섯 줄로 흩어져 오히려 읽기 나쁘다.
    """
    out, i = [], 0
    while i < len(ops):
        tag, i1, i2, j1, j2 = ops[i]
        if tag == "equal":
            out.append(ops[i])
            i += 1
            continue
        end_i, end_j = i2, j2
        i += 1
        while (i + 1 < len(ops) and ops[i][0] == "equal"
               and (ops[i][2] - ops[i][1]) <= gap and ops[i + 1][0] != "equal"):
            end_i, end_j = ops[i + 1][2], ops[i + 1][4]
            i += 2
        out.append(("change", i1, end_i, j1, end_j))
    return out


def change_rows(before, after, ctx=5, limit=40):
    """바뀐 곳만 골라 (정정 전 조각, 정정 후 조각) 쌍의 목록으로 만든다.

    각 조각 앞뒤로 짧은 문맥을 붙여 어디가 바뀐 것인지 알 수 있게 한다.
    좌우 목록의 N번째 줄끼리 서로 대응한다.
    """
    a, b, ops = opcodes(before, after)
    rows = []
    for tag, i1, i2, j1, j2 in merge_ops(ops):
        if tag == "equal":
            continue
        old, new = "".join(a[i1:i2]), "".join(b[j1:j2])
        # 띄어쓰기만 다른 곳은 읽는 사람에게 의미가 없다. 버린다.
        if re.sub(r"\s+", "", old) == re.sub(r"\s+", "", new):
            continue
        rows.append({
            "old": old,
            "new": new,
            "old_l": "".join(a[max(0, i1 - ctx):i1]),
            "old_r": "".join(a[i2:i2 + ctx]),
            "new_l": "".join(b[max(0, j1 - ctx):j1]),
            "new_r": "".join(b[j2:j2 + ctx]),
        })
    return rows[:limit], max(0, len(rows) - limit)


def side_html(rows, which, omitted):
    """한쪽(정정 전 또는 정정 후) 칸을 그린다. 바뀐 줄만 들어간다."""
    is_before = which == "before"
    head = "정정 전 — 삭제·수정된 부분" if is_before else "정정 후 — 추가·수정된 부분"
    body = ""
    for n, row in enumerate(rows, 1):
        piece = row["old"] if is_before else row["new"]
        left = row["old_l"] if is_before else row["new_l"]
        right = row["old_r"] if is_before else row["new_r"]
        if piece.strip():
            mark = ('<del class="d">' if is_before else '<ins class="i">') \
                + escape(piece) + ("</del>" if is_before else "</ins>")
        else:
            mark = ('<span class="empty">(이 자리에 없던 내용)</span>' if is_before
                    else '<span class="empty">(삭제됨)</span>')
        body += ('<div class="drow"><span class="rn">' + str(n) + "</span><span>"
                 + '<span class="ctx">' + escape(left) + "</span>" + mark
                 + '<span class="ctx">' + escape(right) + "</span></span></div>")
    if omitted:
        body += ('<div class="drow"><span class="rn"></span>'
                 '<span class="ctx">그 외 ' + str(omitted) + "군데 더 (생략)</span></div>")
    return ('<div class="side ' + which + '"><div class="hd">' + head + "</div>"
            + body + "</div>")


def number_changes(before, after):
    """바뀐 숫자만 (정정 전, 정정 후) 쌍으로 뽑는다. 화면 맨 위 요약용."""
    a, b, ops = opcodes(before, after)
    pairs, seen = [], set()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        olds = [t for t in a[i1:i2] if NUMTOK.match(t) and len(t) >= 3]
        news = [t for t in b[j1:j2] if NUMTOK.match(t) and len(t) >= 3]
        for k in range(max(len(olds), len(news))):
            pair = (olds[k] if k < len(olds) else None,
                    news[k] if k < len(news) else None)
            if pair[0] == pair[1] or pair in seen:
                continue
            seen.add(pair)
            pairs.append(pair)
    return pairs


POINTER = re.compile(r"\(주\s*(\d+)\)")


def note_id(rnd, item, idx, prefix=""):
    """앵커 id. 같은 회차를 두 곳에서 그릴 수 있어 접두사로 구분한다."""
    m = POINTER.match(item["before"] or "") or POINTER.match(item["after"] or "")
    if m:
        return prefix + "note-" + rnd["rcept_no"] + "-" + m.group(1)
    return prefix + "row-" + rnd["rcept_no"] + "-" + str(idx)


def detail_texts(item):
    """비교할 정정 전/후 텍스트.

    총괄표가 (주N) 을 가리키면 블록 본문을, 값을 표 안에 직접 적었으면
    그 셀 자체를 비교한다. 직접 기재 행에 핵심 값이 들어있는 경우가 많다
    (대한항공 확정2의 확정금리, 아이진 확정1·2의 모집가액).
    """
    if item["block_before"] or item["block_after"]:
        return item["block_before"], item["block_after"], "(주N) 블록"
    return item["before"], item["after"], "표 셀 직접 기재"


def has_detail(item):
    if item["kind"] != "row":
        return False
    before, after, _ = detail_texts(item)
    if POINTER.match(before or "") or POINTER.match(after or ""):
        return False            # 포인터인데 블록을 못 찾은 행
    return bool((before or after) and before != after)


def sort_chips(pairs):
    """큰 금액이 먼저 오게. 양쪽 다 있는 쌍을 한쪽만 있는 쌍보다 앞에 둔다."""
    def weight(p):
        both = 0 if (p[0] and p[1]) else 1
        size = max(len(re.sub(r"\D", "", x or "")) for x in p)
        return (both, -size)
    return sorted(pairs, key=weight)


def note_panel(rnd, item, idx, only_changes=True, prefix=""):
    """정정 전/후 한 덩어리를 차이 표시와 함께 렌더링한다."""
    before, after, origin = detail_texts(item)
    anchor = note_id(rnd, item, idx, prefix)
    tag = POINTER.match(item["before"] or "") or POINTER.match(item["after"] or "")
    title = ("(주" + tag.group(1) + ") " if tag else "") + (item["item"][:80] or "(항목명 없음)")
    chips = ""
    for old, new in sort_chips(number_changes(before, after))[:8]:
        chips += ('<span class="chip"><s>' + escape(old or "(없음)") + "</s> → <b>"
                  + escape(new or "(삭제)") + "</b></span>")
    if only_changes:
        rows, omitted = change_rows(before, after)
        if not rows:
            body = ('<div class="nodiff">텍스트는 같습니다. 표 구조나 서식만 바뀌었을 수 '
                    "있습니다.</div>")
        else:
            body = ('<div class="split">' + side_html(rows, "before", omitted)
                    + side_html(rows, "after", omitted) + "</div>")
    else:
        body = ('<div class="split">'
                '<div class="side before"><div class="hd">정정 전 (전체)</div>'
                '<div class="full">' + escape(before or "(없음)") + "</div></div>"
                '<div class="side after"><div class="hd">정정 후 (전체)</div>'
                '<div class="full">' + escape(after or "(없음)") + "</div></div></div>")
    meta = rnd["label"] + " · " + rnd["date"] + " · " + origin
    if item["reason"]:
        meta += " · 사유: " + item["reason"]
    return ('<div class="note" id="' + anchor + '"><h4>' + escape(title) + "</h4>"
            '<div class="meta">' + escape(meta) + "</div>"
            + (chips + "<br>" if chips else "") + body + "</div>")


def linkify_pointer(text, rnd, anchor):
    """총괄표 셀을 아래 상세 패널로 가는 링크로 바꾼다.

    (주N) 포인터는 물론, 값을 직접 적은 셀도 같은 행의 상세로 이어준다.
    """
    if not anchor or not (text or "").strip():
        return escape(text or "")
    return ('<a class="jump" href="#' + anchor + '">' + escape(text) + " ↓</a>")


def headline_key(case):
    """대표 경로에 쓸 항목."""
    return ("발행금액 합계" if case["kind"] == "debt" else "모집총액")


def cell_of(rnd, keys):
    return pick(rnd["values"], *keys)


def check_round(case, rnd):
    """검산. 지분증권은 주식수 x 1주당 가액 = 모집총액, 채무증권은 트랜치 합 = 합계."""
    values = rnd["values"]
    if case["kind"] == "debt":
        a = to_int((values.get("amt_118-1") or {}).get("value"))
        b = to_int((values.get("amt_118-2") or {}).get("value"))
        total = to_int((pick(values, "total_fixed", "total_plan") or {}).get("value"))
        if None in (a, b, total):
            return None
        return {"ok": a + b == total, "lhs": "118-1 + 118-2",
                "expect": a + b, "actual": total}
    shares = to_int((values.get("shares") or {}).get("value"))
    price = to_int((pick(values, "price_fixed", "price_plan") or {}).get("value"))
    total = to_int((pick(values, "total_fixed", "total_plan") or {}).get("value"))
    if None in (shares, price, total):
        return None
    return {"ok": shares * price == total, "lhs": "모집주식수 x 1주당 가액",
            "expect": shares * price, "actual": total}


def diff_kind(prev, cur, idx):
    """직전 회차와 비교한 변화 종류.

    added  : 앞 회차에는 아예 없던 항목이 이 회차에서 처음 기재됨
             (대한항공 확정금리가 여기 해당. '변경 없음'으로 묻히면 안 된다)
    moved  : 금액은 그대로고 예정/확정 칸만 이동. 값 변경으로 세지 않는다.
    """
    if cur is None:
        return "none"
    if idx == 0:
        return "first"
    if prev is None:
        return "added"
    pv, cv = to_int(prev["value"]), to_int(cur["value"])
    same_value = (pv == cv) if (pv is not None and cv is not None) \
        else (prev["value"] == cur["value"])
    if same_value and prev.get("kind") != cur.get("kind"):
        return "moved"
    return "same" if same_value else "changed"


def move_label(prev, cur):
    """예정/확정 칸 이동의 실제 방향을 그대로 쓴다(되돌아가는 경우도 있다)."""
    return ((prev.get("kind") or "미구분") + "→" + (cur.get("kind") or "미구분")
            + " 표기 이동")


def path_for(case, keys):
    """회차별 값과 변화 종류를 이어 붙인다."""
    out, prev = [], None
    for idx, rnd in enumerate(case["rounds"]):
        cur = cell_of(rnd, keys)
        out.append({"round": rnd, "cell": cur, "prev": prev,
                    "kind": diff_kind(prev, cur, idx)})
        if cur is not None:
            prev = cur
    return out


# --------------------------------------------------------------------------------- 화면
st.markdown("## 정정 이력 대조기")
st.markdown(
    '<div class="lead">정정신고서는 직전 회차와의 차이만 보여줍니다. '
    "원본부터 최종 확정까지 같은 항목이 어떻게 바뀌었는지 한 화면에 모았습니다.</div>",
    unsafe_allow_html=True)

names = [c["name"] + " · " + c["subtitle"] for c in CASES]
choice = st.radio("사례", names, horizontal=True, label_visibility="collapsed")
case = CASES[names.index(choice)]

if st.session_state.get("case_id") != case["id"]:
    st.session_state["case_id"] = case["id"]
    st.session_state["round_idx"] = len(case["rounds"]) - 1

rounds = case["rounds"]
checks = [check_round(case, r) for r in rounds]

# ---------------------------------------------------------------------- 3. 대표 경로
head_name = headline_key(case)
head_keys = dict((n, k) for n, k, _ in rows_of(case))[head_name]
head_path = path_for(case, head_keys)
steps = []
for i, node in enumerate(head_path):
    if node["cell"] is None:
        continue
    is_last = all(n["cell"] is None for n in head_path[i + 1:])
    mark = " ⚠" if (checks[i] and not checks[i]["ok"]) else ""
    badge = '<span class="badge">확정</span>' if (is_last and node["cell"].get("kind") == "확정") \
        else ('<span class="badge">최종</span>' if is_last else "")
    steps.append(
        '<div class="step"><div class="val' + (" final" if is_last else "") + '">'
        + escape(short_won(to_int(node["cell"]["value"])) if head_keys[0] != "band"
                 else node["cell"]["value"]) + escape(mark) + badge
        + '</div><div class="rnd">' + escape(node["round"]["label"] + " · "
                                             + node["round"]["date"]) + "</div></div>")

first_val = to_int(head_path[0]["cell"]["value"]) if head_path[0]["cell"] else None
last_cell = next((n["cell"] for n in reversed(head_path) if n["cell"]), None)
last_val = to_int(last_cell["value"]) if last_cell else None
n_changed = sum(1 for n in head_path if n["kind"] == "changed")
pct = ("" if not first_val or not last_val else
       format((last_val - first_val) / first_val * 100, "+.1f") + "%")

st.markdown(
    '<div class="card"><h3>' + escape(head_name) + " 값 경로</h3>"
    + '<div class="path">' + '<span class="arrow">→</span>'.join(steps) + "</div>"
    + '<div class="summary num">원본 대비 최종 ' + escape(pct)
    + " &nbsp;·&nbsp; 값 변경 " + str(n_changed) + "회 &nbsp;·&nbsp; 공시 "
    + str(len(rounds)) + "건 (원본 1 + 정정 " + str(len(rounds) - 1) + ")</div></div>",
    unsafe_allow_html=True)

# ------------------------------------------------------------------------- 4. 회차 띠
st.markdown("###### 회차")
cols = st.columns(len(rounds))
for i, (col, rnd) in enumerate(zip(cols, rounds)):
    with col:
        dot = "●" if rnd["color"] else "○"
        if st.button(dot + " " + rnd["label"] + "\n" + rnd["date"], key="rb" + str(i)):
            st.session_state["round_idx"] = i
        st.markdown(
            '<div class="rnd" style="text-align:center;margin-top:-6px">'
            '<span class="dot" style="background:' + rnd["color_hex"] + '"></span>'
            + escape(rnd["color"] or "원본") + "</div>", unsafe_allow_html=True)

sel = min(st.session_state.get("round_idx", len(rounds) - 1), len(rounds) - 1)

# --------------------------------------------------------------------- 5. 보기 전환
view = st.radio("보기", ["누적 경로", "정정표 방식(직전 대비)"],
                horizontal=True, label_visibility="collapsed")

if view == "누적 경로":
    head_cells = "".join(
        '<th>' + escape(r["label"]) + "<br><span style='font-weight:400;font-size:0.76rem'>"
        + escape(r["date"]) + "</span></th>" for r in rounds)
    body = ""
    for name, keys, unit in rows_of(case):
        path = path_for(case, keys)
        tds = ""
        for node in path:
            cell = node["cell"]
            if cell is None:
                tds += '<td class="none">—</td>'
                continue
            raw = cell["value"]
            text = won(to_int(raw)) if unit == "원" else (
                format(to_int(raw), ",") + "주" if unit == "주" else raw)
            prefix = (cell.get("kind") + " ") if cell.get("kind") else ""
            if node["kind"] in ("changed", "added"):
                tag = '<br><span class="moved">신규 기재</span>' \
                    if node["kind"] == "added" else ""
                tds += ('<td class="chg" style="color:' + node["round"]["color_hex"]
                        + '">' + escape(prefix + text) + tag + "</td>")
            elif node["kind"] == "moved":
                tds += ('<td class="same">' + escape(text) + '<br><span class="moved">'
                        + escape(move_label(node["prev"], cell)) + "</span></td>")
            else:
                tds += '<td class="same">' + escape(prefix + text) + "</td>"
        first = next((n["cell"] for n in path if n["cell"]), None)
        last = next((n["cell"] for n in reversed(path) if n["cell"]), None)
        if first and last and first["value"] != last["value"]:
            final = ('<td class="chg">' + escape(first["value"] + " → " + last["value"])
                     + "</td>")
        else:
            final = '<td class="same">변동 없음</td>'
        body += ('<tr><td class="k">' + escape(name) + "</td>" + tds + final + "</tr>")
    st.markdown(
        '<div class="card"><h3>누적 경로 — 원본부터 최종까지</h3><div class="scroll">'
        '<table class="grid"><tr><th>항목</th>' + head_cells
        + "<th>원본 대비 최종</th></tr>" + body + "</table></div>"
        '<div class="rnd" style="margin-top:8px">'
        "값이 바뀐 칸은 그 회차의 선언 색으로 표시했습니다. "
        "— 는 그 회차 문서에 해당 항목이 없다는 뜻입니다(발행조건확정은 부분 문서).</div></div>",
        unsafe_allow_html=True)
else:
    rnd = rounds[sel]
    if sel == 0:
        st.markdown('<div class="info">원본 신고서입니다. 정정사항 표가 없습니다.</div>',
                    unsafe_allow_html=True)
    else:
        only_changes = st.toggle("바뀐 부분만 보기 (끄면 정정 전/후 전체 원문)",
                                 value=True, key="oc" + str(sel))
        body = ""
        for idx, item in enumerate(rnd["detail"]):
            if item["kind"] == "heading":
                body += ('<tr><td class="k" colspan="4"><b>' + escape(item["item"])
                         + "</b></td></tr>")
                continue
            anchor = note_id(rnd, item, idx) if has_detail(item) else None
            body += ('<tr><td class="k">' + escape(item["item"][:70])
                     + '</td><td class="k">' + escape(item["reason"])
                     + '</td><td class="k">'
                     + linkify_pointer(item["before"][:90], rnd, anchor)
                     + '</td><td class="k">'
                     + linkify_pointer(item["after"][:90], rnd, anchor)
                     + "</td></tr>")
        st.markdown(
            '<div class="card"><h3>' + escape(rnd["label"] + " 정정사항 표 — 직전 회차 대비")
            + '</h3><div class="scroll"><table class="grid">'
            "<tr><th>항목</th><th>정정사유</th><th>정정 전</th><th>정정 후</th></tr>"
            + body + '</table></div><div class="rnd" style="margin-top:8px">'
            "(주N) 을 누르면 아래 해당 블록으로 이동합니다. "
            "총괄표에는 값이 없고, 실제 내용은 그 블록에 있습니다.</div></div>",
            unsafe_allow_html=True)

        notes = [(idx, i) for idx, i in enumerate(rnd["detail"]) if has_detail(i)]
        if notes:
            st.markdown("###### 정정 전/후 차이 (" + str(len(notes)) + "건)")
            st.markdown(
                '<div class="rnd">왼쪽 칸은 정정 전에서 사라지거나 바뀐 부분, '
                "오른쪽 칸은 정정 후에 들어온 부분만 모았습니다. 좌우의 같은 번호끼리 "
                "짝입니다. 위 표의 칸을 누르면 해당 항목으로 이동합니다.</div>",
                unsafe_allow_html=True)
            st.markdown("".join(note_panel(rnd, i, idx, only_changes)
                                for idx, i in notes), unsafe_allow_html=True)
        else:
            st.markdown('<div class="info">이 회차에서는 비교할 정정 전/후 본문을 '
                        "찾지 못했습니다.</div>", unsafe_allow_html=True)

        origin_cell = cell_of(rounds[0], head_keys)
        if origin_cell:
            blob = " ".join([i["before"] + i["after"] + i["block_before"] + i["block_after"]
                             for i in rnd["detail"]])
            if origin_cell["value"] not in blob:
                st.markdown(
                    '<div class="warn">이 화면에는 원본 ' + escape(head_name) + " "
                    + escape(won(to_int(origin_cell["value"])))
                    + " 값이 없습니다. 원본 값을 알려면 이전 공시를 따로 열어야 합니다.</div>",
                    unsafe_allow_html=True)

# ------------------------------------------------------------------------- 6. 검산 경고
bad = [(r, c) for r, c in zip(rounds, checks) if c and not c["ok"]]
if bad:
    for rnd, chk in bad:
        st.markdown(
            '<div class="warn"><b>⚠ 검산 불일치 — ' + escape(rnd["label"]) + " ("
            + escape(rnd["date"]) + ")</b><br>" + escape(chk["lhs"]) + " = "
            + escape(won(chk["expect"])) + " 인데, 문서에 적힌 값은 "
            + escape(won(chk["actual"])) + " 입니다. 차이 "
            + escape(won(abs(chk["expect"] - chk["actual"]))) + ".</div>",
            unsafe_allow_html=True)
else:
    st.markdown('<div class="info">검산 결과: 모든 회차에서 값이 맞습니다.</div>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------------- 7. 회차별 상세
st.markdown("###### 회차별 상세")
for i, rnd in enumerate(rounds):
    changes = []
    for name, keys, unit in rows_of(case):
        path = path_for(case, keys)
        node = path[i]
        if node["kind"] == "changed":
            prev = node["prev"]
            before = short_won(to_int(prev["value"])) if (prev and unit == "원") else (
                prev["value"] if prev else "-")
            after = short_won(to_int(node["cell"]["value"])) if unit == "원" \
                else node["cell"]["value"]
            changes.append(name + " " + before + " → " + after)
        elif node["kind"] == "added":
            value = short_won(to_int(node["cell"]["value"])) if unit == "원" \
                else node["cell"]["value"]
            changes.append(name + " 신규 기재 " + value)
        elif node["kind"] == "moved":
            changes.append(name + " " + move_label(node["prev"], node["cell"])
                           + " (값 동일)")
    if i == 0:
        line = "원본 신고서"
    elif changes:
        line = " / ".join(changes)
    else:
        line = "도출된 주요 사항의 변경 사항은 없습니다."
    flag = " ⚠" if (checks[i] and not checks[i]["ok"]) else ""

    st.markdown(
        '<div class="rnd" style="margin-bottom:-6px">'
        '<span class="dot" style="background:' + rnd["color_hex"] + '"></span>'
        + "<b style='color:#33485e'>" + escape(rnd["label"]) + "</b> · "
        + escape(rnd["date"]) + " · " + escape(rnd["doc_name"]) + escape(flag)
        + " — " + escape(line) + "</div>", unsafe_allow_html=True)
    with st.expander("자세히 보기 — " + rnd["label"]):
        st.markdown("**정정사유 원문**: "
                    + (" / ".join(rnd["reasons"]) if rnd["reasons"] else "(원본 신고서)"))
        if rnd["notice"]:
            st.markdown('<div class="blk">' + escape(rnd["notice"][:900]) + "</div>",
                        unsafe_allow_html=True)
        if rnd["detail"]:
            st.markdown("**정정사항 표 전체 (" + str(len(rnd["detail"])) + "행)**")
            for idx, item in enumerate(rnd["detail"]):
                if item["kind"] == "heading":
                    st.markdown("**" + item["item"] + "**")
                    continue
                if has_detail(item):
                    st.markdown(note_panel(rnd, item, idx, True, "d-"),
                                unsafe_allow_html=True)
                else:
                    st.markdown("- `" + (item["item"][:80] or "-") + "` · 사유: "
                                + (item["reason"] or "-") + " · 정정 전: "
                                + (item["before"][:60] or "-") + " · 정정 후: "
                                + (item["after"][:60] or "-"))
        else:
            st.markdown("정정사항 표가 없는 문서입니다(원본).")
        st.markdown("[DART 원문 열기](" + rnd["dart_url"] + ")  ·  접수번호 "
                    + rnd["rcept_no"])

# ------------------------------------------------------------- 8. 정정사유 / 관련 보도
left, right = st.columns(2)
with left:
    rows = "".join(
        '<tr><td class="k">' + escape(r["label"] + " · " + r["date"]) + '</td><td class="k">'
        + escape(" / ".join(r["reasons"]) if r["reasons"] else "(원본)") + "</td></tr>"
        for r in rounds)
    st.markdown('<div class="card"><h3>회차별 정정사유 원문</h3><div class="scroll">'
                '<table class="grid" style="min-width:0">'
                "<tr><th>회차</th><th>정정사유</th></tr>" + rows + "</table></div></div>",
                unsafe_allow_html=True)
with right:
    if case["news"]:
        items = "".join(
            '<tr><td class="k">' + escape(n["date"]) + '</td><td class="k">'
            '<a href="' + n["url"] + '" target="_blank">' + escape(n["title"])
            + "</a></td><td class=\"k\">" + escape(n["media"]) + "</td></tr>"
            for n in case["news"])
        st.markdown('<div class="card"><h3>관련 보도 (맥락 참고용)</h3><div class="scroll">'
                    '<table class="grid" style="min-width:0">'
                    "<tr><th>날짜</th><th>제목</th><th>매체</th></tr>" + items
                    + "</table></div></div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><h3>관련 보도 (맥락 참고용)</h3>'
                    '<div class="info">이 사례는 수집된 보도가 없습니다. '
                    "값은 모두 공시 원문에서 나왔습니다.</div></div>",
                    unsafe_allow_html=True)

st.markdown('<div class="foot">모든 값은 DART 공시 원문에서 추출했습니다. '
            "보도는 맥락 참고용이며 값의 출처가 아닙니다.</div>", unsafe_allow_html=True)
