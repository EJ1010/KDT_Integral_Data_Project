# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

base = Path(r"c:\DATA\KDT_Integral_Data_Project\02_csv\03_x\character_reaction\20261103_1635")
ev = pd.read_csv(base / "reaction_evidence.csv", dtype=str, keep_default_na=False)
posts = pd.read_csv(base / "post_reaction_analysis.csv", dtype=str, keep_default_na=False)
acc = dict(zip(posts.post_id, posts.account_id))
a = ev[(ev.speaker == "작성자") & (ev.analysis_target == "예")].copy()
a["account"] = a.post_id.map(acc)
mask = a.evidence_level.eq("직접 이유") | a.evidence_level.str.startswith("특징")
sub = a[mask & a.reaction_target.isin(["특정 캐릭터", "캐릭터 간 관계", "굿즈", "작품·스토리·세계관"])]
lines = [f"rows {len(sub)} posts {sub.post_id.nunique()}", ""]
for _, r in sub.sort_values(["reaction_target", "character", "evidence_level", "post_id"]).iterrows():
    lines.append(
        " | ".join(
            [
                r.reaction_target,
                r.character,
                r.account,
                r.post_id,
                r.appeal,
                r.emotion,
                r.behavior,
                r.evidence_level,
                r.reason_explains,
            ]
        )
    )
    lines.append(r.evidence_quote)
    lines.append("")
(base / "working" / "model_review_queue.md").write_text("\n".join(lines), encoding="utf-8")
print(len(sub))
