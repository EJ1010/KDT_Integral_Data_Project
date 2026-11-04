# -*- coding: utf-8 -*-
"""Join batch judgments to the seed-42 sample and write the deliverable CSVs."""
import json
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
NAMES = {
    "A": "작품·캐릭터 감상·장면 공유",
    "B": "개인 상품 관심·소비·소유·사용",
    "C": "팬 창작·꾸미기·제작물 공유",
    "D": "상품·거래·협찬·이벤트 안내",
    "E": "다른 인물·대상·팬덤 관련",
    "F": "콘텐츠 정보·번역·독자 교류",
    "G": "본문만으로 목적 판단 어려움",
    "H": "비한국어 본문",
}

src = pd.read_csv(HERE / "_입력5000.csv", encoding="utf-8-sig")
src["순번"] = src["순번"].astype(int)
src["comment_id"] = src["comment_id"].astype(str)
expect = dict(zip(src["순번"], src["comment_id"]))
text = dict(zip(src["comment_id"], src["댓글원문"].fillna("").astype(str)))

rows = []
for path in sorted(HERE.glob("_j_*.jsonl")):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

assert len(rows) == 5000, len(rows)
ns = [r["n"] for r in rows]
assert sorted(ns) == list(range(1, 5001))
assert len({r["id"] for r in rows}) == 5000

bad = []
for r in rows:
    if expect[r["n"]] != str(r["id"]):
        bad.append(("id", r["n"]))
    q = r.get("quote") or ""
    if q and q not in text[str(r["id"])]:
        bad.append(("quote", r["n"], q))
    if r["pri"] not in NAMES:
        bad.append(("pri", r["n"]))
    parts = [p for p in (r.get("aux") or "").split("|") if p]
    if r["pri"] in parts or len(parts) != len(set(parts)) or any(p not in NAMES for p in parts):
        bad.append(("aux", r["n"], r.get("aux")))
    if r["title_use"] not in ("예", "아니오") or r["review"] not in ("예", "아니오"):
        bad.append(("flag", r["n"]))
    if r["title_use"] == "예" and r.get("title_sug") not in NAMES:
        bad.append(("title_sug", r["n"], r.get("title_sug")))
    if r["title_use"] == "아니오" and (r.get("title_sug") or ""):
        bad.append(("title_sug_extra", r["n"]))
assert not bad, bad[:20]

jud = pd.DataFrame(rows)
jud["n"] = jud["n"].astype(int)
jud["id"] = jud["id"].astype(str)
out = src.merge(jud, left_on=["순번", "comment_id"], right_on=["n", "id"], how="outer", indicator=True)
assert (out["_merge"] == "both").all()
assert out["댓글원문"].fillna("").eq(src.set_index("comment_id").loc[out["comment_id"], "댓글원문"].fillna("").to_numpy()).all()

final = pd.DataFrame({
    "순번": out["순번"],
    "comment_id": out["comment_id"],
    "post_id": out["post_id"],
    "account_id": out["account_id"],
    "댓글원문": out["댓글원문"],
    "영상제목": out["영상제목"],
    "기존_언어판정": out["기존_언어판정"],
    "주유형코드": out["pri"],
    "주유형이름": out["pri"].map(NAMES),
    "보조유형": out["aux"].fillna(""),
    "원문근거": out["quote"].fillna(""),
    "판정이유": out["why"],
    "제목보조해석": out["title_use"],
    "제목제안유형": out["title_sug"].fillna(""),
    "검토필요": out["review"],
    "검토사유": out["review_why"].fillna(""),
    "판정모델": "Grok 4.7",
    "판정방식": "LLM 문맥 판정",
    "프롬프트버전": "ah-context-v1",
    "처리상태": "완료",
}).sort_values("순번")

assert final["comment_id"].nunique() == 5000
assert set(final["comment_id"]) == set(src["comment_id"])
assert final["주유형코드"].isin(list(NAMES)).all()
assert (final["주유형코드"].map(NAMES) == final["주유형이름"]).all()
assert final["댓글원문"].isna().sum() == 0
assert (final["처리상태"] == "완료").all()

final.to_csv(HERE / "01_댓글판정.csv", index=False, encoding="utf-8-sig")

n = 5000
pri = final["주유형코드"].value_counts()
summary_rows = []
for code in "ABCDEFGH":
    k = int(pri.get(code, 0))
    summary_rows.append({
        "집계구분": "주유형",
        "코드": code,
        "이름": NAMES[code],
        "건수": k,
        "비율": round(k / n, 6),
        "비고": "주유형은 댓글당 하나. 비율의 분모는 표본 5,000건.",
    })
aux_counter = Counter()
aux_comments = 0
for aux in final["보조유형"]:
    parts = [p for p in str(aux).split("|") if p]
    if parts:
        aux_comments += 1
    for p in parts:
        aux_counter[p] += 1
for code in "ABCDEFGH":
    k = int(aux_counter.get(code, 0))
    summary_rows.append({
        "집계구분": "보조유형_중복",
        "코드": code,
        "이름": NAMES[code],
        "건수": k,
        "비율": round(k / n, 6),
        "비고": "한 댓글에 보조유형이 여러 개일 수 있다. 코드별 건수를 더하면 댓글 수를 넘을 수 있다.",
    })
summary_rows.append({
    "집계구분": "보조유형_댓글",
    "코드": "",
    "이름": "보조유형이 하나 이상인 댓글",
    "건수": aux_comments,
    "비율": round(aux_comments / n, 6),
    "비고": "댓글 단위. 보조유형 코드 건수의 합과 다르다.",
})
title_n = int((final["제목보조해석"] == "예").sum())
review_n = int((final["검토필요"] == "예").sum())
empty_q = int((final["원문근거"].fillna("") == "").sum())
summary_rows.extend([
    {"집계구분": "제목보조해석", "코드": "예", "이름": "제목을 보면 해석이 달라짐", "건수": title_n, "비율": round(title_n / n, 6), "비고": "주유형은 본문 기준. 제안 유형은 보조 정보."},
    {"집계구분": "검토필요", "코드": "예", "이름": "추가 검토 표시", "건수": review_n, "비율": round(review_n / n, 6), "비고": "자동 점검이 아니라 판정 시 남긴 검토 표시."},
    {"집계구분": "처리상태", "코드": "완료", "이름": "문맥 판정 완료", "건수": 5000, "비율": 1.0, "비고": "G와 H도 완료. 실패 0, 미처리 0."},
    {"집계구분": "처리상태", "코드": "실패", "이름": "판정 실패", "건수": 0, "비율": 0.0, "비고": ""},
    {"집계구분": "처리상태", "코드": "미처리", "이름": "아직 읽지 않음", "건수": 0, "비율": 0.0, "비고": "표본 밖 62,891건은 이 파일에 없다."},
    {"집계구분": "원문근거", "코드": "빈근거", "이름": "발췌를 비워 둔 댓글", "건수": empty_q, "비율": round(empty_q / n, 6), "비고": "문구를 만들지 않고 비운 경우."},
])
pd.DataFrame(summary_rows).to_csv(HERE / "02_유형요약.csv", index=False, encoding="utf-8-sig")

print("PRI")
for code in "ABCDEFGH":
    k = int(pri.get(code, 0))
    print(f"{code} {k} {k/n:.4%}")
print("AUX_COMMENTS", aux_comments)
print("AUX", dict(aux_counter))
print("TITLE", title_n, "REVIEW", review_n, "EMPTY_Q", empty_q)
print("LANG", final["기존_언어판정"].value_counts().to_dict())
print("H")
h = final[final["주유형코드"] == "H"][["순번", "기존_언어판정", "댓글원문", "판정이유"]]
for rec in h.to_dict("records"):
    print(rec["순번"], rec["기존_언어판정"], rec["판정이유"], "|", rec["댓글원문"][:120].replace("\n", " "))
print("TITLE_SUG")
print(final.loc[final["제목보조해석"] == "예", "제목제안유형"].value_counts().to_dict())
print("PAIRS")
for a, b in [("A", "B"), ("B", "D"), ("C", "E"), ("E", "F"), ("G", "H")]:
    ab = ((final["주유형코드"] == a) & final["보조유형"].str.contains(b)).sum()
    ba = ((final["주유형코드"] == b) & final["보조유형"].str.contains(a)).sum()
    print(a, b, int(ab), int(ba))
