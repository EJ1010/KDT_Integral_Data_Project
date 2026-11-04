# -*- coding: utf-8 -*-
"""판정용으로 순번 구간을 원문 그대로 출력한다. 원본 파일은 읽기만 한다."""
import sys
from pathlib import Path
import pandas as pd

here = Path(__file__).resolve().parent
start, end = int(sys.argv[1]), int(sys.argv[2])
df = pd.read_csv(here / "_입력5000.csv", encoding="utf-8-sig")
part = df[(df.순번 >= start) & (df.순번 <= end)]
lines = []
for r in part.itertuples(index=False):
    text = "" if pd.isna(r.댓글원문) else str(r.댓글원문).replace("\r\n", "\n")
    title = "" if pd.isna(r.영상제목) else str(r.영상제목).replace("\n", " ")
    lines.append(f"#{r.순번}\t{r.언어재계산}\t{r.comment_id}")
    lines.append(text)
    lines.append(f"제목: {title}")
    lines.append("")
out = here / f"_batch_{start}_{end}.txt"
out.write_text("\n".join(lines), encoding="utf-8")
print("rows", len(part), "chars", out.stat().st_size)
