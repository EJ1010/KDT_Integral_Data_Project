# -*- coding: utf-8 -*-
import pandas as pd
import re
from pathlib import Path

src = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\AH_댓글내용분류_표본5000\01_댓글판정.csv")
out = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\AH_댓글내용분류_표본5000\기준보완_v2")
out.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(src, encoding="utf-8-sig")
for c in ["댓글원문", "영상제목", "보조유형", "원문근거", "판정이유", "검토사유", "제목제안유형"]:
    df[c] = df[c].fillna("").astype(str)

priority = [246, 437, 1049, 1269, 1604, 1708, 1711, 2170, 2329, 2651, 2776, 3225, 3960, 4112, 4409]

bd = re.compile(r"이벤트|응모|당첨|교환|맞구|나눔|공구|공동구매|협찬|판매|파나|팔아|팔겠|팔립|얼마에|당근|중고|양도|구매처|어디서\s*사|살\s*수\s*있|파실|사실|팝니|삼|구매\s*가능|판매\s*가능")
# '삼' is too broad. Don't use 삼.
bd = re.compile(
    r"이벤트|응모|당첨|교환|맞구|나눔|공구|공동구매|협찬|"
    r"판매|파나요|파실|팔아|팔겠|팔립|팝니다|양도|중고|당근|"
    r"구매처|어디서\s*사|살\s*수|사실\s*건|얼마"
)
ce = re.compile(r"금손|손재주|솜씨|잘한다|잘하네|잘하심|잘하신|잘했|잘그리|잘 그리|그림체|퀄리티|성대모사|더빙|팬아트|뜨개|점토|도안")
cf = re.compile(r"해주|해 주|해달|해 달|해주세요|해 주세요|부탁|올려 ?주|올려 ?달|만들어|만들어 ?주|만들어 ?달|업로드|번역 ?해")

def hit(pat, row):
    blob = " ".join([row["댓글원문"], row["판정이유"], row["검토사유"], row["영상제목"]])
    return bool(pat.search(row["댓글원문"])) or bool(pat.search(row["판정이유"])) or bool(pat.search(row["검토사유"]))

df["pool_bd"] = df.apply(lambda r: hit(bd, r), axis=1)
df["pool_ce"] = df.apply(lambda r: hit(ce, r), axis=1)
df["pool_cf"] = df.apply(lambda r: hit(cf, r), axis=1)
# body-only keyword, stricter for reading load
df["body_bd"] = df["댓글원문"].str.contains(bd)
df["body_ce"] = df["댓글원문"].str.contains(ce)
df["body_cf"] = df["댓글원문"].str.contains(cf)

print("pool bd", int(df.pool_bd.sum()), "body", int(df.body_bd.sum()))
print("pool ce", int(df.pool_ce.sum()), "body", int(df.body_ce.sum()))
print("pool cf", int(df.pool_cf.sum()), "body", int(df.body_cf.sum()))
anyc = df.pool_bd | df.pool_ce | df.pool_cf
print("union", int(anyc.sum()))
bodyu = df.body_bd | df.body_ce | df.body_cf
print("body union", int(bodyu.sum()))
print("pri of body union")
print(df.loc[bodyu, "주유형코드"].value_counts().sort_index().to_string())

# priority full text
lines = []
for n in priority:
    r = df.loc[df.순번 == n].iloc[0]
    lines.append(f"===== {n} pri={r.주유형코드} aux={r.보조유형} title={r.제목보조해석}/{r.제목제안유형} review={r.검토필요}")
    lines.append(f"TITLE: {r.영상제목}")
    lines.append(f"WHY: {r.판정이유}")
    lines.append(f"REVIEW: {r.검토사유}")
    lines.append(f"BODY:\n{r.댓글원문}")
    lines.append("")
(out / "_priority.txt").write_text("\n".join(lines), encoding="utf-8")
print("wrote priority", len(priority))
