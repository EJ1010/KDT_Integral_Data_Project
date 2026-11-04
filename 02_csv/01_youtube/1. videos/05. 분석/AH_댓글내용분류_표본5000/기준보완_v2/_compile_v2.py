# -*- coding: utf-8 -*-
import json
from pathlib import Path
import pandas as pd

root = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\AH_댓글내용분류_표본5000")
here = root / "기준보완_v2"
src = pd.read_csv(root / "01_댓글판정.csv", encoding="utf-8-sig")
for c in ["보조유형", "원문근거", "판정이유", "검토사유", "제목제안유형", "댓글원문", "영상제목"]:
    src[c] = src[c].fillna("").astype(str)
src["순번"] = src["순번"].astype(int)

names = {
    "A": "작품·캐릭터 감상·장면 공유",
    "B": "개인 상품 관심·소비·소유·사용",
    "C": "팬 창작·꾸미기·제작물 공유",
    "D": "상품·거래·협찬·이벤트 안내",
    "E": "다른 인물·대상·팬덤 관련",
    "F": "콘텐츠 정보·번역·독자 교류",
    "G": "본문만으로 목적 판단 어려움",
    "H": "비한국어 본문",
}

rows = []
for name in ["_locked.jsonl", "_chg_a.jsonl", "_chg_b.jsonl", "_chg_c.jsonl", "_chg_d.jsonl", "_chg_e.jsonl", "_chg_f.jsonl"]:
    for line in (here / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

by_n = {}
for r in rows:
    n = int(r["n"])
    if n in by_n:
        raise SystemExit(f"duplicate {n}")
    by_n[n] = r

def norm_aux(s):
    s = (s or "").strip()
    if not s or s.lower() == "nan":
        return ""
    parts = [p for p in s.split("|") if p]
    return "|".join(parts)

out = src.copy()
log = []
for n, ch in sorted(by_n.items()):
    hit = out.index[out["순번"] == n]
    if len(hit) != 1:
        raise SystemExit(f"missing {n}")
    i = hit[0]
    body = out.at[i, "댓글원문"]
    quote = ch.get("quote") or ""
    if quote and quote not in body:
        raise SystemExit(f"bad quote {n}: {quote}")
    pri = ch["pri"]
    aux = norm_aux(ch.get("aux") or "")
    if pri in aux.split("|"):
        raise SystemExit(f"aux duplicates pri {n}")
    if pri not in names:
        raise SystemExit(f"bad pri {n} {pri}")
    hold = str(ch.get("hold")) in {"예", "True", "true"}
    old_pri = out.at[i, "주유형코드"]
    old_aux = norm_aux(out.at[i, "보조유형"])
    if hold and (pri != old_pri or aux != old_aux):
        raise SystemExit(f"hold changed label {n} {old_pri}/{old_aux} -> {pri}/{aux}")
    title_use = ch.get("title_use") or "아니오"
    title_sug = ch.get("title_sug") or ""
    if title_use != "예":
        title_sug = ""
    if title_sug == pri:
        raise SystemExit(f"title equals pri {n}")
    review = ch.get("review") or "아니오"
    old_title_use = out.at[i, "제목보조해석"]
    old_title = norm_aux(out.at[i, "제목제안유형"]) if False else (out.at[i, "제목제안유형"] or "")
    old_review = out.at[i, "검토필요"]
    if pri != old_pri:
        kind = "주유형 변경"
    elif aux != old_aux:
        kind = "보조유형만 변경"
    elif hold:
        kind = "사용자 확인 보류"
    elif title_use != old_title_use or title_sug != (out.at[i, "제목제안유형"] or "") or review != old_review:
        kind = "제목·검토만 변경"
    else:
        kind = "변경 없음"
    if hold:
        kind = "사용자 확인 보류"
    out.at[i, "주유형코드"] = pri
    out.at[i, "주유형이름"] = names[pri]
    out.at[i, "보조유형"] = aux
    out.at[i, "원문근거"] = quote
    out.at[i, "판정이유"] = ch.get("why") or ""
    out.at[i, "제목보조해석"] = title_use
    out.at[i, "제목제안유형"] = title_sug
    out.at[i, "검토필요"] = review
    out.at[i, "검토사유"] = ch.get("review_why") or ""
    out.at[i, "판정모델"] = "Grok 4.7"
    out.at[i, "프롬프트버전"] = "ah-context-v2"
    log.append({
        "comment_id": out.at[i, "comment_id"],
        "순번": n,
        "댓글원문": body,
        "영상제목": out.at[i, "영상제목"],
        "기존_주유형": old_pri,
        "기존_보조유형": old_aux,
        "수정_주유형": pri,
        "수정_보조유형": aux,
        "원문근거": quote,
        "변경이유": ch.get("why") or "",
        "적용기준ID": ch.get("rule") or "",
        "제목보조해석": title_use,
        "제목제안유형": title_sug,
        "검토필요": review,
        "검토사유": ch.get("review_why") or "",
        "변경구분": kind,
        "판정모델": "Grok 4.7",
        "기준버전": "ah-context-v2",
        "사용자_확인": "",
        "사용자_의견": "",
    })

# checks
if len(out) != 5000:
    raise SystemExit("row count")
if out["comment_id"].nunique() != 5000:
    raise SystemExit("unique")
if set(out["comment_id"]) != set(src["comment_id"]):
    raise SystemExit("id set")
if out["순번"].nunique() != 5000:
    raise SystemExit("seq")
if (out["댓글원문"] != src["댓글원문"]).any() or (out["post_id"] != src["post_id"]).any():
    raise SystemExit("body or post changed")
if not out["주유형코드"].isin(list(names)).all():
    raise SystemExit("pri missing")
bad_aux = 0
for pri, aux in zip(out["주유형코드"], out["보조유형"].fillna("")):
    if pri in str(aux).split("|"):
        bad_aux += 1
if bad_aux:
    raise SystemExit(f"aux dup {bad_aux}")

order = list("ABCDEFGH")
before = src["주유형코드"].value_counts()
after = out["주유형코드"].value_counts()
comp = []
for code in order:
    b = int(before.get(code, 0))
    a = int(after.get(code, 0))
    comp.append({
        "코드": code,
        "이름": names[code],
        "수정전": b,
        "수정전비율": round(b / 5000, 4),
        "수정후": a,
        "수정후비율": round(a / 5000, 4),
        "증감": a - b,
    })

log_df = pd.DataFrame(log)
kind_counts = log_df["변경구분"].value_counts().to_dict()
print("changes", len(log_df))
print(kind_counts)
print("primary", int((log_df["기존_주유형"] != log_df["수정_주유형"]).sum()))
print("aux only", int(((log_df["기존_주유형"] == log_df["수정_주유형"]) & (log_df["기존_보조유형"] != log_df["수정_보조유형"]) & (log_df["변경구분"] != "사용자 확인 보류")).sum()))
print("hold", int((log_df["변경구분"] == "사용자 확인 보류").sum()))
print(pd.DataFrame(comp).to_string(index=False))

out.to_csv(here / "01_댓글판정_5000_v2.csv", index=False, encoding="utf-8-sig")
log_df.to_csv(here / "02_변경기록.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(comp).to_csv(here / "03_유형별_전후비교.csv", index=False, encoding="utf-8-sig")
print("wrote")
