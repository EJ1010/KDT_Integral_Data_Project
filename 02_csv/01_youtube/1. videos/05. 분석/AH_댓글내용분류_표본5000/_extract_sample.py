# -*- coding: utf-8 -*-
"""67,891건에서 시드 42로 5,000건을 비복원 추출한다. 원본은 읽기만 한다."""
import sys
from pathlib import Path
import pandas as pd

here = Path(__file__).resolve().parent
goods = here.parent / "A_상품소비_1차분류"
sys.path.insert(0, str(goods))
import classify_A_goods_screen_v1 as g  # noqa: E402

pop, info = g.population()
print("population_info", info)
assert len(pop) == 67891
assert pop.comment_id.is_unique
assert pop.post_id.notna().all()
assert pop.comment_id.notna().all()

# 파일 순서에 덜 의존하도록 comment_id로 정렬한 뒤 뽑는다.
pop = pop.sort_values("comment_id").reset_index(drop=True)
sample = pop.sample(n=5000, random_state=42)
sample = sample.sort_values("comment_id").reset_index(drop=True)
sample.insert(0, "순번", range(1, len(sample) + 1))

out = pd.DataFrame({
    "순번": sample["순번"],
    "comment_id": sample["comment_id"],
    "post_id": sample["post_id"],
    "account_id": sample["account_id"],
    "댓글원문": sample["comment_description"],
    "영상제목": sample["title_without_hashtags"],
    "기존_언어판정": sample["language_class"],
    "언어재계산": sample["lang_re"],
    "기존_반응대상": sample["reaction_target"],
})
assert out.comment_id.is_unique and len(out) == 5000
assert set(out.comment_id).issubset(set(pop.comment_id))
out.to_csv(here / "_입력5000.csv", index=False, encoding="utf-8-sig")
out[["순번", "comment_id"]].to_csv(here / "00_표본ID.csv", index=False, encoding="utf-8-sig")

lens = out.댓글원문.fillna("").map(len)
print("chars", int(lens.sum()), "mean", round(float(lens.mean()), 1), "median", int(lens.median()), "max", int(lens.max()))
print("lang_re", out.언어재계산.value_counts().to_dict())
print("language_class", out.기존_언어판정.value_counts().to_dict())
print("empty", int((out.댓글원문.fillna("").str.strip() == "").sum()))
print("videos", out.post_id.nunique(), "channels", out.account_id.nunique())
