# -*- coding: utf-8 -*-
"""Print full texts of high-signal feature posts for manual review."""
from pathlib import Path
import re

src = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659\working\candidate_texts.md")
text = src.read_text(encoding="utf-8")
parts = text.split("\n## ")
keep = ("side_profile", "snout", "cheek", "limbs", "eyes_specific", "roundness", "head_body", "expression", "negative_cute", "worthless", "pose", "color", "bangs")
out = []
for p in parts[1:]:
    first = p.split("\n", 1)[0]
    feats = first.split("|")[1].strip() if "|" in first else ""
    if any(k in feats.split("|") for k in keep):
        out.append("## " + p)
dest = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659\working\review_core.md")
dest.write_text("\n".join(out), encoding="utf-8")
print("sections", len(out), "chars", dest.stat().st_size)
