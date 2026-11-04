# -*- coding: utf-8 -*-
"""Aggregate recorded review reasons and draw the boundary re-read sample.

This script does not rejudge comments. Reason tags describe the existing
검토사유 text. The sample is for a later context re-read.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "01_댓글판정.csv"
OUT = HERE

df = pd.read_csv(SRC, encoding="utf-8-sig")
for col in ("보조유형", "검토사유", "제목제안유형", "원문근거", "판정이유", "댓글원문", "영상제목"):
    df[col] = df[col].fillna("").astype(str)
df["순번"] = df["순번"].astype(int)

def codes(aux):
    return [p for p in str(aux).split("|") if p]

def has(aux, code):
    return code in codes(aux)

# --- reason tags on the 1,039 review-flagged rows. Multiple tags allowed. ---
RULES = [
    ("제목을 참고해야 대상·목적을 해석할 수 있음", r"제목"),
    ("본문이 짧거나 지시 대상 불명확", r"이름.{0,4}없|대상이 없|대상 없|대상 이름|누구|이거로만|타임스탬프|시각만|짧|평가 없이|무엇|안 적|이름만|대상의 이름|본문에 없|불명확|생략|비어|대사|좁|약하|가리지|격언만|목적 범주|시각으로만|조각"),
    ("작품·캐릭터와 상품의 구분", r"상품|가챠|굿즈|매장|소장|인형|개봉|소비|장면인지|실물|뽑|구매|파크|카페|방문 경험|사 주|돈을 주|살 돈|사고 싶|피규어"),
    ("팬 창작물과 업로더·편집 평가의 구분", r"편집|업로더|만들|창작|더빙|퀄리티|성대모사|팬아트|꾸미|제작|그림 평가|만드는 과정"),
    ("일반 교류와 특정 대상 평가의 구분", r"잘 봤|감사|요청|시청|영상 감상|회차|인사|교류|재미있|기다려|안내로 보면"),
    ("개인 구매 질문과 판매·이벤트 안내의 구분", r"이벤트|판매|공구|협찬|홍보|파나요|응모|링크|구매처|거래|광고"),
    ("인물과 캐릭터·작품의 구분", r"성우|출연|실존|사람|인물|님의|자기소개|본인을 가리|장면 속|개인 추억|유행어|영상 속"),
    ("언어 판정 경계", r"일본어|외국어|가사|영어|한국어 문장|한글|귀여워가 붙"),
    ("작품 안 발화와 바깥 행동의 구분", r"장면 속|작품 평가|노래인지|민심"),
    ("인코딩 손상", r"오타가 심|키 입력|글자가 깨|인코딩|자모"),
    ("다른 읽기가 본문에 같이 있음", r"로도|일 수|이면|갈린|안 가르|앞에|뒤에|둘 다|동시에|반응도 있|같이 있"),
]

def tag_reason(text):
    hits = [name for name, pat in RULES if re.search(pat, text)]
    if not hits:
        if len(text.strip()) <= 12:
            hits = ["검토 사유가 구체적이지 않음"]
        else:
            hits = ["기록된 사유가 위 묶음에 바로 안 맞음"]
    return hits

rev = df[df["검토필요"] == "예"].copy()
rev["tags"] = rev["검토사유"].map(tag_reason)

rows = []
tagged_ids = {name: set() for name, _ in RULES}
tagged_ids["검토 사유가 구체적이지 않음"] = set()
tagged_ids["기록된 사유가 위 묶음에 바로 안 맞음"] = set()
for rec in rev.itertuples():
    for name in rec.tags:
        tagged_ids[name].add(rec.comment_id)

order = [name for name, _ in RULES] + ["검토 사유가 구체적이지 않음", "기록된 사유가 위 묶음에 바로 안 맞음"]
multi_n = int(rev["tags"].map(lambda t: len(set(t)) > 1).sum())
for name in order:
    ids = tagged_ids[name]
    note = "검토 표시 1,039건 안의 고유 댓글. 한 댓글이 여러 사유에 들어가면 각 행에 다시 센다."
    if name == "기록된 사유가 위 묶음에 바로 안 맞음":
        note = "검토 표시는 있으나 위 문구 묶음에 걸리지 않은 사유. 오분류로 세지 않는다."
    rows.append({
        "집계구분": "검토표시_사유묶음",
        "사유": name,
        "고유댓글수": len(ids),
        "사유태그건수": len(ids),
        "분모": 1039,
        "비고": note,
    })
rows.append({
    "집계구분": "검토표시_합계",
    "사유": "검토 표시가 있는 고유 댓글",
    "고유댓글수": int(len(rev)),
    "사유태그건수": int(sum(len(set(t)) for t in rev["tags"])),
    "분모": 5000,
    "비고": f"고유 댓글 1,039. 사유 태그 합은 복수 사유라 더 크다. 태그가 둘 이상인 댓글 {multi_n}건.",
})
rows.append({
    "집계구분": "검토표시_없음",
    "사유": "검토 표시 없음",
    "고유댓글수": int((df["검토필요"] != "예").sum()),
    "사유태그건수": 0,
    "분모": 5000,
    "비고": "검토 표시가 없다는 뜻이지, 경계가 없다는 뜻은 아니다.",
})
rows.append({
    "집계구분": "참고_기존보고",
    "사유": "제목 보조 해석",
    "고유댓글수": int((df["제목보조해석"] == "예").sum()),
    "사유태그건수": int((df["제목보조해석"] == "예").sum()),
    "분모": 5000,
    "비고": "기존 보고서 574건과 비교하는 집계. 정답으로 두지 않는다.",
})
rows.append({
    "집계구분": "참고_기존보고",
    "사유": "G 주유형",
    "고유댓글수": int((df["주유형코드"] == "G").sum()),
    "사유태그건수": int((df["주유형코드"] == "G").sum()),
    "분모": 5000,
    "비고": "기존 보고서 422건과 비교하는 집계.",
})
rows.append({
    "집계구분": "참고_기존보고",
    "사유": "H 주유형",
    "고유댓글수": int((df["주유형코드"] == "H").sum()),
    "사유태그건수": int((df["주유형코드"] == "H").sum()),
    "분모": 5000,
    "비고": "기존 보고서 3건과 비교하는 집계.",
})

# --- pools ---
ab = (
    ((df["주유형코드"] == "A") & df["보조유형"].map(lambda s: has(s, "B")))
    | ((df["주유형코드"] == "B") & df["보조유형"].map(lambda s: has(s, "A")))
    | (df["검토사유"].str.contains(r"상품|가챠|굿즈|매장|소장|인형|개봉|소비|장면인지|실물|뽑|구매|파크|카페", regex=True) & df["주유형코드"].isin(list("AB")))
)
ce = (
    ((df["주유형코드"] == "C") & df["보조유형"].map(lambda s: has(s, "E")))
    | ((df["주유형코드"] == "E") & df["보조유형"].map(lambda s: has(s, "C")))
    | (df["검토사유"].str.contains(r"편집|업로더|만들|창작|더빙|퀄리티|성대모사|팬아트|꾸미|제작", regex=True) & df["주유형코드"].isin(list("CE")))
)
ef = (
    ((df["주유형코드"] == "E") & df["보조유형"].map(lambda s: has(s, "F")))
    | ((df["주유형코드"] == "F") & df["보조유형"].map(lambda s: has(s, "E")))
    | (df["검토사유"].str.contains(r"잘 봤|감사|요청|출연|영상 감상|시청|사람", regex=True) & df["주유형코드"].isin(list("EF")))
)
bd = (
    ((df["주유형코드"] == "B") & df["보조유형"].map(lambda s: has(s, "D")))
    | ((df["주유형코드"] == "D") & df["보조유형"].map(lambda s: has(s, "B")))
    | (df["검토사유"].str.contains(r"이벤트|판매|공구|협찬|홍보|파나요|응모|링크|구매처", regex=True) & df["주유형코드"].isin(list("BD")))
)
multi = df["보조유형"].str.contains(r"\|", regex=True)
g_title = (df["주유형코드"] == "G") & (df["제목보조해석"] == "예")
h = df["주유형코드"] == "H"
encoding = df["검토사유"].str.contains(r"오타가 심|키 입력|글자가 깨|인코딩|자모", regex=True)

def ids_of(mask):
    return set(df.loc[mask, "순번"].astype(int))

pools = {
    "H": ids_of(h),
    "인코딩손상": ids_of(encoding),
    "G제목": ids_of(g_title),
    "AB": ids_of(ab),
    "CE": ids_of(ce),
    "EF": ids_of(ef),
    "BD": ids_of(bd),
    "복수목적": ids_of(multi),
}

rng = np.random.RandomState(42)
selected = []
stratum = {}

def add(n, name):
    if n not in stratum:
        selected.append(n)
        stratum[n] = name
    # first stratum wins; all matching boundaries stored later

def take_all(pool, name):
    for n in sorted(pool):
        add(n, name)

def take_k(pool, name, k):
    remain = np.array(sorted(pool - set(selected)), dtype=int)
    if len(remain) == 0:
        return 0
    if len(remain) <= k:
        chosen = remain
    else:
        chosen = rng.choice(remain, size=k, replace=False)
    for n in sorted(int(x) for x in chosen):
        add(n, name)
    return int(len(chosen))

take_all(pools["H"] | pools["인코딩손상"], "1_H와인코딩")
n_g = take_k(pools["G제목"], "2_G제목", 40)
n_ab = take_k(pools["AB"], "3_AB", 20)
n_ce = take_k(pools["CE"], "3_CE", 20)
n_ef = take_k(pools["EF"], "3_EF", 20)
n_bd = take_k(pools["BD"], "3_BD", 20)
n_multi = take_k(pools["복수목적"], "3_복수목적", 20)
need = 200 - len(selected)
nonreview = set(df.loc[df["검토필요"] != "예", "순번"].astype(int))
n_fill = take_k(nonreview, "4_비검토보충", need)

assert len(selected) == len(set(selected))
assert len(selected) <= 200

def applicable(n):
    hits = []
    for key in ("H", "인코딩손상", "G제목", "AB", "CE", "EF", "BD", "복수목적"):
        if n in pools[key]:
            hits.append(key)
    if not hits:
        hits.append("비검토일반")
    return "|".join(hits)

sel = df[df["순번"].isin(selected)].copy()
sel["선정집단"] = sel["순번"].map(stratum)
sel["해당경계"] = sel["순번"].map(applicable)
sel = sel.sort_values("순번")

keep = ["순번", "comment_id", "post_id", "account_id", "댓글원문", "영상제목", "기존_언어판정",
        "주유형코드", "주유형이름", "보조유형", "원문근거", "판정이유", "제목보조해석", "제목제안유형",
        "검토필요", "검토사유", "선정집단", "해당경계"]
sel[keep].to_csv(OUT / "_검토입력.csv", index=False, encoding="utf-8-sig")
sel[["순번", "comment_id", "선정집단", "해당경계"]].to_csv(OUT / "00_선정ID.csv", index=False, encoding="utf-8-sig")

# batch text for reading. Body then title. Do not include instructions as commands.
sel_sorted = sel.sort_values("순번")
batch_size = 40
records = sel_sorted.to_dict("records")
for i in range(0, len(records), batch_size):
    chunk = records[i:i + batch_size]
    lines = []
    for r in chunk:
        lines.append(f"#순번 {r['순번']}\t{r['선정집단']}\t{r['해당경계']}\t{r['주유형코드']}\t{r['보조유형']}\t{r['comment_id']}")
        lines.append(r["댓글원문"])
        lines.append("제목: " + r["영상제목"])
        lines.append("기존이유: " + r["판정이유"])
        lines.append("검토사유: " + r["검토사유"])
        lines.append("제목보조: " + r["제목보조해석"] + " / " + r["제목제안유형"])
        lines.append("")
    name = f"_batch_{i+1:03d}_{i+len(chunk):03d}.txt"
    (OUT / name).write_text("\n".join(lines), encoding="utf-8")

# pool report rows
taken = sel["선정집단"].value_counts().to_dict()
for key, pool in pools.items():
    rows.append({
        "집계구분": "선정풀",
        "사유": key,
        "고유댓글수": len(pool),
        "사유태그건수": int(sel["해당경계"].str.contains(key).sum()) if key != "비검토일반" else 0,
        "분모": 5000,
        "비고": "풀 크기. 사유태그건수 칸은 이번 200건 안에 그 경계가 해당하는 댓글 수.",
    })
for name, k in sorted(taken.items()):
    rows.append({
        "집계구분": "선정집단",
        "사유": name,
        "고유댓글수": int(k),
        "사유태그건수": int(k),
        "분모": len(selected),
        "비고": "우선순위로 한 번만 배정한 추출 집단. 다른 경계에 같이 해당해도 여기서는 한 집단만 센다.",
    })

# leftover reasons for the log
left = rev[rev["tags"].map(lambda t: "기록된 사유가 위 묶음에 바로 안 맞음" in t)]
(OUT / "_미분류사유.txt").write_text(
    "\n".join(left["검토사유"].tolist()), encoding="utf-8"
)

pd.DataFrame(rows).to_csv(OUT / "01_경계사유_현황.csv", index=False, encoding="utf-8-sig")

print("SELECTED", len(selected))
print("STRATUM", taken)
print("TAKEN", {"G": n_g, "AB": n_ab, "CE": n_ce, "EF": n_ef, "BD": n_bd, "MULTI": n_multi, "FILL": n_fill})
print("POOLS", {k: len(v) for k, v in pools.items()})
print("UNTAGGED", len(left), "MULTI_TAG_COMMENTS", multi_n)
print("H_ENC", sorted(pools["H"] | pools["인코딩손상"]))
