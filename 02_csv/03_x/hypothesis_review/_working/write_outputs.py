# -*- coding: utf-8 -*-
"""Write corrected evidence, summary, and SVG charts. Markdown is written separately from these counts."""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

base = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
work = base / "hypothesis_review" / "_working"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out = base / "hypothesis_review" / stamp
(out / "charts").mkdir(parents=True, exist_ok=True)

rows = json.loads((work / "corrected_rows.json").read_text(encoding="utf-8"))

# Last corrections after reading full text.
LAST = {
    ("H3", "1940757722640904461"): {
        "relation": "중립·관련 언급",
        "judgment_reason": "인형이 밤에 돌아다닌다는 농담으로 전시 이유를 말했다. 휴대를 거부한 경험으로 세지 않는다.",
    },
    ("H3", "2054216971521335437"): {
        "relation": "중립·관련 언급",
        "judgment_reason": "장식장에 하치와레 구역을 만들었다. 휴대보다 전시를 택했다는 비교는 없다.",
    },
    ("H3", "1741485728088146180"): {
        "relation": "중립·관련 언급",
        "judgment_reason": "그해 목표를 장식 공간을 만드는 쪽으로 적었다. 휴대 포기는 아니다.",
    },
}
for r in rows:
    upd = LAST.get((r["hypothesis"], r["post_id"]))
    if upd and r["facet"] == "전시·보관 선호":
        r.update(upd)

HNAME = {
    "H1": "가설1 이야기·공감과 호감",
    "H2": "가설2 동물적 외형과 호감",
    "H3": "가설3 휴대·일상 활용",
}

def raw_span(quote, text):
    """Return a verbatim substring of text. Source tweets store &lt; &gt; literally."""
    if not quote:
        return ""
    cands = [quote, quote.replace("<", "&lt;").replace(">", "&gt;")]
    for c in cands:
        if c and c in text:
            return c
    parts = [p.strip() for p in re.split(r"\s*/\s*", quote) if p.strip()]
    spans = []
    cursor = 0
    for p in parts:
        opts = [p, p.replace("<", "&lt;").replace(">", "&gt;")]
        found = None
        for opt in opts:
            i = text.find(opt, cursor)
            if i < 0:
                i = text.find(opt)
            if i >= 0:
                found = (i, i + len(opt))
                break
        if not found:
            return ""
        spans.append(found)
        cursor = found[1]
    return text[min(s[0] for s in spans):max(s[1] for s in spans)]

bad = 0
for r in rows:
    span = raw_span(r.get("quote_restored") or r.get("quote") or "", r["text"])
    if not span:
        span = raw_span(r.get("quote") or "", r["text"])
    if not span or span not in r["text"]:
        bad += 1
        print("QUOTE FAIL", r["hypothesis"], r["post_id"])
        span = r["text"]
    r["quote_final"] = span
print("quote_fail", bad)

# evidence csv
ev_fields = [
    "가설", "게시물ID", "게시물링크", "계정ID", "원문", "인용문", "평가대상",
    "세부면", "근거수준", "판정", "화자", "판단이유", "이미지확인", "이미지비고", "수집시점_좋아요",
]
with open(out / "hypothesis_evidence.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=ev_fields)
    w.writeheader()
    for r in rows:
        w.writerow({
            "가설": HNAME[r["hypothesis"]],
            "게시물ID": r["post_id"],
            "게시물링크": r["post_url"],
            "계정ID": r["account_id"],
            "원문": r["text"],
            "인용문": r["quote_final"],
            "평가대상": r.get("target", ""),
            "세부면": r["facet"],
            "근거수준": r["evidence_level"],
            "판정": r["relation"],
            "화자": r["speaker"],
            "판단이유": r["judgment_reason"],
            "이미지확인": "아니오",
            "이미지비고": "이번 검토는 본문으로 판단했다. 이미지를 새로 열지 않았다.",
            "수집시점_좋아요": r.get("like_count", ""),
        })

CAND = {"H1": 570, "H2": 218, "H3": 491}
NOISE = {"H1": 260, "H2": 111, "H3": 209}
PROMO = {"H1": 64, "H2": 39, "H3": 203}
INPUT_N = 5000

def posts_where(sub, pred):
    return {r["post_id"] for r in sub if pred(r)}

def primary(sub_post_rows):
    rels = {r["relation"] for r in sub_post_rows}
    directs = any(r["relation"] == "지지" and r["evidence_level"] == "직접적인 이유·비교" and r["speaker"] == "작성자 개인" for r in sub_post_rows)
    if "지지" in rels and "반대" in rels:
        return "지지와 반대가 함께 있음"
    if directs:
        return "작성자의 직접 이유·지지"
    if any(r["relation"] == "지지" and r["speaker"] == "작성자 개인" for r in sub_post_rows):
        return "작성자의 명시적 평가·지지"
    if any(r["relation"] == "지지" for r in sub_post_rows):
        return "작성자 외 화자의 지지"
    if "반대" in rels:
        return "반대"
    if "혼합" in rels:
        return "혼합"
    if "중립·관련 언급" in rels:
        return "중립·관련 언급"
    return "판단 불가"

summary_rows = []
stats = {}
for hyp in ("H1", "H2", "H3"):
    sub = [r for r in rows if r["hypothesis"] == hyp]
    by_post = defaultdict(list)
    for r in sub:
        by_post[r["post_id"]].append(r)
    prim = Counter(primary(v) for v in by_post.values())
    author_sup = [r for r in sub if r["relation"] == "지지" and r["speaker"] == "작성자 개인"]
    author_posts = {r["post_id"] for r in author_sup}
    acc_posts = defaultdict(set)
    for r in author_sup:
        acc_posts[r["account_id"]].add(r["post_id"])
    top = sorted(acc_posts.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    top_id, top_n = (top[0][0], len(top[0][1])) if top else ("", 0)
    direct_posts = posts_where(sub, lambda r: r["evidence_level"] == "직접적인 이유·비교" and r["relation"] == "지지" and r["speaker"] == "작성자 개인")
    explicit_posts = posts_where(sub, lambda r: r["evidence_level"] == "명시적 평가·경험")
    coexist_posts = posts_where(sub, lambda r: r["evidence_level"] == "단순 공존")
    fac_posts = defaultdict(set)
    for r in author_sup:
        fac_posts[r["facet"]].add(r["post_id"])
    stats[hyp] = {
        "evidence_rows": len(sub),
        "evidence_posts": len(by_post),
        "support_rows": sum(1 for r in sub if r["relation"] == "지지"),
        "support_posts": len(posts_where(sub, lambda r: r["relation"] == "지지")),
        "author_support_posts": len(author_posts),
        "author_support_accounts": len(acc_posts),
        "direct_author_posts": len(direct_posts),
        "direct_author_accounts": len({r["account_id"] for r in sub if r["post_id"] in direct_posts}),
        "explicit_posts": len(explicit_posts),
        "coexist_posts": len(coexist_posts),
        "oppose_posts": len(posts_where(sub, lambda r: r["relation"] == "반대")),
        "mixed_posts": len(posts_where(sub, lambda r: r["relation"] == "혼합")),
        "neutral_posts": len(posts_where(sub, lambda r: r["relation"] == "중립·관련 언급")),
        "unclear_posts": len(posts_where(sub, lambda r: r["relation"] == "판단 불가")),
        "top_account": top_id,
        "top_posts": top_n,
        "primary": dict(prim),
        "facets": {k: len(v) for k, v in fac_posts.items()},
        "direct_ids": sorted(direct_posts),
    }
    metrics = [
        ("입력 게시물", INPUT_N, "게시물", "전체 x_posts"),
        ("관련 후보이자 문맥 검토", CAND[hyp], "게시물", "키워드·기존 라벨 합집합. 후보 전량을 읽음"),
        ("노이즈로 제외", NOISE[hyp], "게시물", "검색어만 있고 가설과 무관"),
        ("홍보·판매로 제외", PROMO[hyp], "게시물", "작성자 호감으로 세지 않음"),
        ("근거 행", len(sub), "행", "한 게시물에 행이 여러 개일 수 있음"),
        ("근거 게시물", len(by_post), "게시물", "근거 행이 있는 고유 게시물"),
        ("지지 행", sum(1 for r in sub if r["relation"] == "지지"), "행", "화자 제한 없음"),
        ("지지 게시물", len(posts_where(sub, lambda r: r["relation"] == "지지")), "게시물", "화자 제한 없음. 다른 판정과 겹칠 수 있음"),
        ("작성자 지지 게시물", len(author_posts), "게시물", "화자가 작성자 개인"),
        ("작성자 지지 계정", len(acc_posts), "계정", "계정은 사람 수가 아님"),
        ("작성자 직접 이유 지지 게시물", len(direct_posts), "게시물", "근거수준이 직접적인 이유·비교이고 판정이 지지"),
        ("작성자 직접 이유 지지 계정", len({r["account_id"] for r in sub if r["post_id"] in direct_posts}), "계정", "위 게시물의 계정"),
        ("명시적 평가·경험 게시물", len(explicit_posts), "게시물", "판정과 무관. 직접 이유 게시물과 겹칠 수 있음"),
        ("단순 공존 게시물", len(coexist_posts), "게시물", "지지 합계에 넣지 않음"),
        ("반대 게시물", len(posts_where(sub, lambda r: r["relation"] == "반대")), "게시물", "다른 판정과 겹칠 수 있음"),
        ("혼합 게시물", len(posts_where(sub, lambda r: r["relation"] == "혼합")), "게시물", "다른 판정과 겹칠 수 있음"),
        ("중립·관련 언급 게시물", len(posts_where(sub, lambda r: r["relation"] == "중립·관련 언급")), "게시물", "다른 판정과 겹칠 수 있음"),
        ("판단 불가 게시물", len(posts_where(sub, lambda r: r["relation"] == "판단 불가")), "게시물", "다른 판정과 겹칠 수 있음"),
        ("작성자 지지 최다 계정 게시물", top_n, "게시물", top_id),
    ]
    for name, count, unit, note in metrics:
        summary_rows.append({
            "가설": HNAME[hyp],
            "지표": name,
            "값": count,
            "단위": unit,
            "집계기준": note,
            "분모": f"문맥 검토 {CAND[hyp]}게시물 / 입력 {INPUT_N}게시물",
        })
    for label, n in prim.items():
        summary_rows.append({
            "가설": HNAME[hyp],
            "지표": "게시물당 하나 " + label,
            "값": n,
            "단위": "게시물",
            "집계기준": "한 게시물에 하나의 우선 판정. 합은 근거 게시물 수와 같음",
            "분모": f"근거 게시물 {len(by_post)}",
        })
    for fac, n in sorted(fac_posts.items(), key=lambda kv: -len(kv[1])):
        summary_rows.append({
            "가설": HNAME[hyp],
            "지표": "작성자 지지 세부면 " + fac,
            "값": n,
            "단위": "게시물",
            "집계기준": "작성자 개인 지지. 한 게시물이 여러 세부면에 들어갈 수 있음",
            "분모": f"작성자 지지 게시물 {len(author_posts)}",
        })

with open(out / "hypothesis_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["가설", "지표", "값", "단위", "집계기준", "분모"])
    w.writeheader()
    w.writerows(summary_rows)

(out / "charts" / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

def svg_bars(title, groups, series, path, note):
    """groups: list of category labels. series: list of (name, [values aligned to groups], color)."""
    width, height = 920, 420
    left, top, chart_w, chart_h = 180, 50, 700, 280
    max_v = max(max(vals) for _, vals, _ in series) or 1
    n = len(groups)
    band = chart_w / n
    bar_w = band / (len(series) + 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Malgun Gothic, Apple SD Gothic Neo, sans-serif">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="28" font-size="16" font-weight="700">{title}</text>',
        f'<text x="24" y="{height-18}" font-size="12" fill="#444">{note}</text>',
    ]
    for i in range(4):
        y = top + chart_h - (chart_h * i / 3)
        val = round(max_v * i / 3)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#e5e5e5"/>')
        parts.append(f'<text x="{left-8}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="#555">{val}</text>')
    for gi, g in enumerate(groups):
        for si, (name, vals, color) in enumerate(series):
            v = vals[gi]
            h = chart_h * v / max_v
            x = left + gi * band + bar_w * (si + 0.5)
            y = top + chart_h - h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.8:.1f}" height="{h:.1f}" fill="{color}"/>')
            parts.append(f'<text x="{x+bar_w*0.4:.1f}" y="{y-4:.1f}" font-size="11" text-anchor="middle">{v}</text>')
        parts.append(f'<text x="{left+gi*band+band/2:.1f}" y="{top+chart_h+18}" font-size="12" text-anchor="middle">{g}</text>')
    lx = left
    for name, _, color in series:
        parts.append(f'<rect x="{lx}" y="{height-48}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{lx+16}" y="{height-38}" font-size="12">{name}</text>')
        lx += 160
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")

order = ["H1", "H2", "H3"]
labels = ["가설1 이야기", "가설2 동물 외형", "가설3 휴대·일상"]
keys = ["작성자의 직접 이유·지지", "작성자의 명시적 평가·지지", "반대", "혼합", "중립·관련 언급", "판단 불가"]
colors = ["#1d4e89", "#5b8fb8", "#b85c38", "#c4a35a", "#8d8d8d", "#cfcfcf"]
series = []
for k, c in zip(keys, colors):
    series.append((k, [stats[h]["primary"].get(k, 0) for h in order], c))
svg_bars(
    "게시물당 하나인 판정",
    labels,
    series,
    out / "charts" / "01_primary_judgment.svg",
    "한 게시물당 하나의 우선 판정. 분모는 근거 행이 있는 게시물(가설1 246, 가설2 68, 가설3 79)이며 입력 5,000이 아니다.",
)

# H1 facet chart
fac = stats["H1"]["facets"]
fac_items = sorted(fac.items(), key=lambda kv: -kv[1])
svg_bars(
    "가설1 작성자 지지 게시물, 세부면",
    [k.replace(" 호감", "").replace(" 반응", "")[:8] for k, _ in fac_items],
    [("게시물", [v for _, v in fac_items], "#1d4e89")],
    out / "charts" / "02_h1_facet_posts.svg",
    f"작성자 지지 {stats['H1']['author_support_posts']}게시물 기준. 한 글이 여러 면에 들어가 합이 더 클 수 있다. 최다 계정 {stats['H1']['top_account']} {stats['H1']['top_posts']}게시물.",
)
print("OUT", out)
print(json.dumps(stats, ensure_ascii=False, indent=2))
