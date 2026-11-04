# -*- coding: utf-8 -*-
import pandas as pd
import re
from pathlib import Path

src = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\AH_댓글내용분류_표본5000\01_댓글판정.csv")
out = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\AH_댓글내용분류_표본5000\기준보완_v2")
df = pd.read_csv(src, encoding="utf-8-sig")
for c in ["댓글원문", "영상제목", "보조유형", "원문근거", "판정이유", "검토사유", "제목제안유형"]:
    df[c] = df[c].fillna("").astype(str)

bd = re.compile(r"이벤트|응모|당첨|교환|맞구|나눔|공구|공동구매|협찬|판매|파나요|파실|팔아|팔겠|팔립|팝니다|양도|중고|당근|구매처|어디서\s*사|살\s*수|얼마")
ce = re.compile(r"금손|손재주|솜씨|잘한다|잘하네|잘하심|잘하신|잘했|잘그리|잘 그리|그림체|퀄리티|성대모사|더빙|팬아트|뜨개|점토|도안")
cf = re.compile(r"해주|해 주|해달|해 달|해주세요|해 주세요|부탁|올려 ?주|올려 ?달|만들어|만들어 ?주|만들어 ?달|업로드|번역")

def body_hit(pat, row):
    return bool(pat.search(row["댓글원문"]))

def meta_hit(pat, row):
    return bool(pat.search(row["판정이유"])) or bool(pat.search(row["검토사유"]))

df["bd"] = df.apply(lambda r: body_hit(bd, r) or meta_hit(bd, r), axis=1)
df["ce"] = df.apply(lambda r: body_hit(ce, r) or meta_hit(ce, r), axis=1)
df["cf"] = df.apply(lambda r: body_hit(cf, r) or meta_hit(cf, r), axis=1)

def cross(pri, aux, a, b):
    aux = aux or ""
    parts = aux.split("|") if aux else []
    return (pri == a and b in parts) or (pri == b and a in parts)

df["x_bd"] = df.apply(lambda r: cross(r.주유형코드, r.보조유형, "B", "D"), axis=1)
df["x_ce"] = df.apply(lambda r: cross(r.주유형코드, r.보조유형, "C", "E"), axis=1)
df["x_cf"] = df.apply(lambda r: cross(r.주유형코드, r.보조유형, "C", "F"), axis=1)
df["cand"] = df.bd | df.ce | df.cf | df.x_bd | df.x_ce | df.x_cf

print("bd", int(df.bd.sum()), "ce", int(df.ce.sum()), "cf", int(df.cf.sum()))
print("x_bd", int(df.x_bd.sum()), "x_ce", int(df.x_ce.sum()), "x_cf", int(df.x_cf.sum()))
print("union", int(df.cand.sum()))
print("cross not in keyword", int((df.cand & ~(df.bd|df.ce|df.cf)).sum()))

cand = df.loc[df.cand].sort_values("순번")
# write compact reading files of 40
n = 0
batch = []
bi = 1
def flush(batch, bi):
    if not batch:
        return
    p = out / f"_cand_{bi:02d}.txt"
    p.write_text("\n".join(batch), encoding="utf-8")

for r in cand.itertuples(index=False):
    flags = []
    if r.bd: flags.append("BD")
    if r.ce: flags.append("CE")
    if r.cf: flags.append("CF")
    if r.x_bd: flags.append("XBD")
    if r.x_ce: flags.append("XCE")
    if r.x_cf: flags.append("XCF")
    batch.append(f"--- {r.순번} | {r.주유형코드} | {r.보조유형} | T{r.제목보조해석}:{r.제목제안유형} | R{r.검토필요} | {','.join(flags)}")
    batch.append(f"제목: {r.영상제목}")
    batch.append(f"이유: {r.판정이유}")
    batch.append(f"본문: {r.댓글원문}")
    batch.append("")
    n += 1
    if n % 40 == 0:
        flush(batch, bi)
        batch = []
        bi += 1
flush(batch, bi)
print("batches", bi, "comments", n)
# id list
cand[["순번", "comment_id"]].to_csv(out / "_cand_ids.csv", index=False, encoding="utf-8-sig")
