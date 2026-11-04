# -*- coding: utf-8 -*-
"""Mine character surfaces, language, and a rule-development sample. Does not modify source files."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
NORM = ROOT / "normalized"
OUT = ROOT / "character_reaction" / "20261103_1635" / "working"

posts = pd.read_csv(
    NORM / "x_posts.csv",
    dtype=str,
    keep_default_na=False,
)
kw = pd.read_csv(NORM / "x_post_keywords.csv", dtype=str, keep_default_na=False)
src = pd.read_csv(NORM / "x_post_sources.csv", dtype=str, keep_default_na=False)

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
HASHTAG_RE = re.compile(r"#([^\s#]+)")
HANGUL_RE = re.compile(r"[가-힣]")
KANA_RE = re.compile(r"[ぁ-んァ-ン]")
CJK_RE = re.compile(r"[一-龯]")
LATIN_RE = re.compile(r"[A-Za-z]")


def analysis_text(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = t.replace("#", " ")
    return t


def script_counts(s: str):
    return {
        "hangul": len(HANGUL_RE.findall(s)),
        "kana": len(KANA_RE.findall(s)),
        "cjk": len(CJK_RE.findall(s)),
        "latin": len(LATIN_RE.findall(s)),
    }


def language_label(raw: str) -> str:
    """Korean-primary, Korean-primary mixed, other-primary, or undetermined.

    Hashtag-only Japanese names do not create a mixed label.
    """
    body = URL_RE.sub(" ", raw)
    body = MENTION_RE.sub(" ", body)
    tags = HASHTAG_RE.findall(body)
    body_wo_tags = HASHTAG_RE.sub(" ", body)
    c_body = script_counts(body_wo_tags)
    letters = c_body["hangul"] + c_body["kana"] + c_body["cjk"] + c_body["latin"]
    if letters < 2 and script_counts(" ".join(tags))["hangul"] + script_counts(" ".join(tags))["kana"] < 2:
        return "판단 불가"
    # sentence-like chunks outside hashtags
    chunks = re.split(r"[\n.!?。！？]+", body_wo_tags)
    ko_sent = 0
    ot_sent = 0
    for ch in chunks:
        sc = script_counts(ch)
        if sc["hangul"] >= 2 and sc["hangul"] >= sc["kana"] + sc["cjk"]:
            ko_sent += 1
        elif sc["kana"] + sc["cjk"] >= 2 and sc["hangul"] == 0:
            ot_sent += 1
        elif sc["latin"] >= 12 and sc["hangul"] == 0 and sc["kana"] == 0:
            ot_sent += 1
    ko = c_body["hangul"]
    other = c_body["kana"] + c_body["cjk"] + (c_body["latin"] if c_body["latin"] >= 12 else 0)
    if ko >= 2 and ko >= other and ot_sent >= 1 and ko_sent >= 1:
        return "한국어 중심 혼합"
    if ko >= 2 and ko >= other:
        return "한국어 중심"
    if other >= 2 and other > ko:
        return "다른 언어 중심"
    if ko >= 1:
        return "한국어 중심"
    return "판단 불가"


posts["analysis_text"] = posts["text"].map(analysis_text)
posts["language"] = posts["text"].map(language_label)
posts["year"] = posts["created_at"].str.slice(0, 4)
posts["view_missing"] = posts["view_count"].eq("")

# Patterns. Ambiguous ones are flagged and not auto-merged.
PATTERNS = [
    ("치이카와계", r"치이카와|치이까와|치카와|치까와|ちいかわ|チイカワ|chiikawa|Chiikawa|CHIIKAWA|吉伊卡哇|吉伊"),
    ("먼작귀", r"먼작귀"),
    ("하치와레", r"하치와레|하치와래|하찌와레|하찌와래|ハチワレ|はちわれ|hachiware|Hachiware"),
    ("가르마", r"가르마"),
    ("우사기", r"우사기|うさぎ|ウサギ|usagi|Usagi"),
    ("토끼단독", r"(?<![가-힣])토끼(?![가-힣])"),
    ("모몽가", r"모몽가|모몬가|モモンガ"),
    ("랏코", r"랏코|ラッコ|らっこ"),
    ("라코", r"(?<![가-힣])라코(?![가-힣])"),
    ("쿠리만쥬", r"쿠리만쥬|쿠리만주|くりまんじゅう|クリマンジュウ"),
    ("만쥬단독", r"(?<![가-힣])만쥬(?![가-힣])|(?<![가-힣])만주(?![가-힣])"),
    ("시사", r"시사|シーサー|シーサ"),
    ("카니", r"카니|カニ"),
    ("갑옷씨계", r"갑옷\s*씨|갑옷\s*아저씨|갑옷상|鎧さん|ヨロイさん"),
    ("갑옷단독", r"갑옷"),
    ("아노코", r"아노코|あのこ|あの子|アノコ"),
    ("데카츠요", r"데카츠요|デカツヨ"),
    ("파자마파티즈", r"파자마\s*파티즈"),
    ("빤쮸", r"빤쮸|팬티토끼|ぽしゃっと"),
    ("치이카와즈", r"치이카와즈|치카와즈"),
    ("하치단독", r"(?<![가-힣])하치(?!와)"),
    ("치이단독", r"(?<![가-힣])치이(?!카|까)"),
    ("우사깅", r"우사깅"),
    ("야하", r"야하"),
    ("우라", r"(?<![가-힣])우라(?![가-힣])"),
    ("후루하냐", r"후루하냐|フリューリャ|古本屋"),
    ("노동요정", r"노동요정|요정"),
    ("비버", r"비버|ビーバー"),
    ("그리핀", r"그리핀|グリフィン"),
    ("스핑크스", r"스핑크스"),
    ("풍뎅이", r"풍뎅이|카부토|カブトムシ"),
    ("오징어옷", r"오징어"),
    ("버섯", r"(?<![가-힣])버섯(?![가-힣])"),
    ("라이온", r"라이온"),
    ("호랑이", r"호랑이"),
    ("꿀벌", r"꿀벌"),
    ("인어", r"인어"),
    ("도깨비", r"도깨비"),
    ("먹보", r"먹보"),
    ("채찍", r"채찍"),
    ("마법", r"마법소녀|마법"),
    ("나가노", r"나가노"),
    ("농담곰", r"농담곰"),
    ("산리오", r"산리오"),
]

rows = []
examples = []
for name, pat in PATTERNS:
    rx = re.compile(pat)
    hit = posts["analysis_text"].str.contains(rx)
    rows.append({"surface": name, "posts": int(hit.sum()), "pattern": pat})
    for _, r in posts.loc[hit].head(3).iterrows():
        text = r["analysis_text"].replace("\n", " / ")
        m = rx.search(r["analysis_text"])
        start = max(0, m.start() - 24) if m else 0
        end = min(len(r["analysis_text"]), (m.end() + 24) if m else 80)
        examples.append(
            {
                "surface": name,
                "post_id": r["post_id"],
                "year": r["year"],
                "language": r["language"],
                "snippet": r["analysis_text"][start:end].replace("\n", " / "),
                "full_short": text[:240],
            }
        )

pd.DataFrame(rows).sort_values("posts", ascending=False).to_csv(
    OUT / "surface_counts.csv", index=False, encoding="utf-8-sig"
)
pd.DataFrame(examples).to_csv(OUT / "surface_examples.csv", index=False, encoding="utf-8-sig")

# ambiguous context dumps
ambig_pats = {
    "시사": r"시사",
    "카니": r"카니",
    "라코": r"(?<![가-힣])라코(?![가-힣])",
    "우사기": r"우사기",
    "토끼단독": r"(?<![가-힣])토끼(?![가-힣])",
    "갑옷단독": r"갑옷",
    "하치단독": r"(?<![가-힣])하치(?!와)",
    "치이단독": r"(?<![가-힣])치이(?!카|까)",
    "요정": r"요정",
}
amb_rows = []
for name, pat in ambig_pats.items():
    rx = re.compile(pat)
    for _, r in posts.iterrows():
        if not rx.search(r["analysis_text"]):
            continue
        amb_rows.append(
            {
                "surface": name,
                "post_id": r["post_id"],
                "year": r["year"],
                "language": r["language"],
                "text": r["analysis_text"].replace("\n", " / "),
            }
        )
pd.DataFrame(amb_rows).to_csv(OUT / "ambiguous_posts.csv", index=False, encoding="utf-8-sig")

# RT / quote-like text markers. These are textual, not relationship IDs.
rt = posts["text"].str.match(r"^\s*RT\s+@", flags=re.I)
qt = posts["text"].str.contains(r"인용|인용트|QT", regex=True)
reply_at = posts["text"].str.match(r"^\s*@")
print("language")
print(posts.language.value_counts().to_string())
print("RT prefix", int(rt.sum()), "quote word", int(qt.sum()), "starts with @", int(reply_at.sum()))
print("view missing", int(posts.view_missing.sum()), "by year")
print(posts.groupby("year").view_missing.sum().to_string())
print("accounts", posts.account_id.nunique(), "kw rows", len(kw), "kw posts", kw.post_id.nunique())
print("src rows", len(src), "src posts", src.post_id.nunique())

# keyword vs body
kw_map = {
    "치이카와": r"치이카와|치이까와|치카와|치까와|ちいかわ|チイカワ|chiikawa|吉伊",
    "하치와레": r"하치와레|하치와래|ハチワレ|hachiware",
    "먼작귀": r"먼작귀",
    "랏코": r"랏코|ラッコ",
    "우사기": r"우사기|うさぎ|ウサギ",
    "모몽가": r"모몽가|모몬가|モモンガ",
    "쿠리만쥬": r"쿠리만쥬|쿠리만주|くりまんじゅう",
    "시사": r"시사|シーサー",
    "갑옷씨": r"갑옷\s*씨|갑옷\s*아저씨|갑옷상",
    "카니": r"카니|カニ",
    "데카츠요": r"데카츠요|デカツヨ",
    "아노코": r"아노코|あのこ|あの子",
    "파자마 파티즈": r"파자마\s*파티즈",
}
merged = posts.merge(kw, on="post_id", how="left")
cmp_rows = []
for keyword, pat in kw_map.items():
    sub = merged[merged.keyword == keyword]
    body = sub.analysis_text.str.contains(pat, regex=True)
    cmp_rows.append(
        {
            "keyword": keyword,
            "keyword_links": int(len(sub)),
            "unique_posts": int(sub.post_id.nunique()),
            "body_has_same_surface": int(body.sum()),
            "body_missing_surface": int((~body).sum()),
        }
    )
pd.DataFrame(cmp_rows).to_csv(OUT / "keyword_vs_body.csv", index=False, encoding="utf-8-sig")

# stratified development sample: not the holdout
# buckets
posts = posts.copy()
posts["n_chars_flag"] = (
    posts.analysis_text.str.contains("하치와레|우사기|모몽가|랏코|쿠리만")
    & posts.analysis_text.str.contains("치이카와|먼작귀")
)
posts["eval_flag"] = posts.analysis_text.str.contains(
    r"귀엽|기여|좋|웃|힐링|사랑|싫어|별로|사고 ?싶|갖고 ?싶|샀|겟|양도|판매|번역|그렸"
)
posts["neg_flag"] = posts.analysis_text.str.contains(r"안 귀엽|별로|싫|못|아니")
posts["seller_flag"] = posts.analysis_text.str.contains(r"판매|양도|공구|입고|예약|증정|폼 ")
posts["amb_flag"] = posts.analysis_text.str.contains(r"시사|카니|(?<![가-힣])라코(?![가-힣])|갑옷")

rng = posts.sample(frac=1, random_state=20261103)
picked = []
seen = set()

def take(mask, n, bucket):
    sub = rng[mask & ~rng.post_id.isin(seen)]
    for _, r in sub.head(n).iterrows():
        picked.append((bucket, r))
        seen.add(r.post_id)

for year in ["2022", "2023", "2024", "2025", "2026"]:
    take((rng.year == year) & rng.eval_flag & (rng.language == "한국어 중심"), 8, f"eval_{year}")
    take((rng.year == year) & rng.seller_flag & (rng.language.str.startswith("한국어")), 3, f"seller_{year}")
    take((rng.year == year) & ~rng.eval_flag & (rng.language == "한국어 중심"), 4, f"plain_{year}")
take(rng.language == "한국어 중심 혼합", 12, "mixed_ko")
take(rng.language == "다른 언어 중심", 8, "other_lang")
take(rng.amb_flag, 15, "ambiguous_name")
take(rng.neg_flag & rng.language.str.startswith("한국어"), 12, "negation")
take(rng.n_chars_flag & rng.language.str.startswith("한국어"), 12, "multi_char")
take(rng.language == "판단 불가", 8, "lang_unknown")

lines = ["# 규칙 작성용 표본", "", f"건수 {len(picked)}", ""]
for bucket, r in picked:
    lines.append(f"## {bucket} | {r.post_id} | {r.year} | {r.language} | {r.account_id}")
    lines.append(r["text"].replace("\r\n", "\n"))
    lines.append("")
(OUT / "dev_sample.md").write_text("\n".join(lines), encoding="utf-8")
print("dev sample", len(picked))
print("lang x year")
print(pd.crosstab(posts.year, posts.language).to_string())
