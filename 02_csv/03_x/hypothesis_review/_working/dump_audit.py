# -*- coding: utf-8 -*-
import csv
from pathlib import Path

base = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
posts = {
    r["post_id"]: r
    for r in csv.DictReader(open(base / "normalized" / "x_posts.csv", encoding="utf-8-sig", newline=""))
}
work = base / "hypothesis_review" / "_working"


def load(names):
    rows = []
    for fn in names:
        for r in csv.DictReader(open(work / fn, encoding="utf-8", newline="")):
            r["src"] = fn
            rows.append(r)
    return rows


def dump(path, rows, pred):
    kept = [r for r in rows if pred(r)]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"n={len(kept)}\n")
        for r in kept:
            text = posts[r["post_id"]]["text"].replace("\r", "")
            f.write("\n" + "=" * 60 + "\n")
            f.write(
                f"{r['post_id']} | {r['facet']} | {r['relation']} | {r['evidence_level']} | {r['speaker']}\n"
            )
            f.write("REASON " + r["judgment_reason"] + "\n")
            f.write("QUOTE " + r["quote"] + "\n")
            f.write("TEXT\n" + text + "\n")
    print(path.name, len(kept))


h1 = load(["judgments_h1_p1.csv", "judgments_h1_p2.csv"])
dump(
    work / "audit_h1_core.txt",
    h1,
    lambda r: r["evidence_level"] == "직접적인 이유·비교"
    or r["relation"] in ("반대", "혼합")
    or (r["relation"] == "지지" and r["facet"] != "성격·말투 호감"),
)
dump(
    work / "audit_h1_personality.txt",
    h1,
    lambda r: r["relation"] == "지지" and r["facet"] == "성격·말투 호감",
)
h2 = load(["judgments_h2_p1.csv"])
dump(
    work / "audit_h2_support.txt",
    h2,
    lambda r: r["relation"] in ("지지", "반대", "혼합") or r["facet"] in ("인간형 대비 동물형 선호", "동물형 대비 인간형 선호", "동물 특징 부정"),
)
h3 = load(["judgments_h3_p1.csv", "judgments_h3_p2.csv"])
dump(work / "audit_h3_all.txt", h3, lambda r: True)
