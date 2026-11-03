from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9._]+")
HASHTAG_RE = re.compile(r"(?<!\w)#([^#\s]+)")
TOKEN_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}|\d{2,}")

# 프로젝트 성격에 맞게 계속 보완하는 사용자 사전입니다.
STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "정말", "너무", "진짜", "오늘", "이번",
    "에서", "으로", "에게", "까지", "부터", "보다", "같이", "대한", "위해", "있는",
    "합니다", "했습니다", "입니다", "있습니다", "해주세요", "드립니다", "통해", "관련",
    "the", "and", "for", "with", "this", "that", "from", "you", "your", "are", "was",
}


def clean_hashtag(tag: str) -> str:
    return tag.lower().strip(".,!?()[]{}:;\"'“”‘’~·")


def body_tokens(text: str) -> list[str]:
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = HASHTAG_RE.sub(" ", text)
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]


def value_counts_dict(series: pd.Series, limit: int = 30) -> list[list[object]]:
    return [[str(k), int(v)] for k, v in series.value_counts(dropna=False).head(limit).items()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram CSV 품질 및 description 키워드 분석")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path, low_memory=False)
    required = {"post_id", "description", "media_type_id", "post_url", "created_at", "like_count", "comment_count"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"필수 컬럼 없음: {missing}")

    desc = df["description"].fillna("").astype(str)
    dt = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    likes = pd.to_numeric(df["like_count"], errors="coerce")
    comments = pd.to_numeric(df["comment_count"], errors="coerce")

    hashtags_by_post = [[clean_hashtag(t) for t in HASHTAG_RE.findall(x) if clean_hashtag(t)] for x in desc]
    tokens_by_post = [body_tokens(x) for x in desc]
    hashtag_tf = Counter(t for row in hashtags_by_post for t in row)
    hashtag_df = Counter(t for row in hashtags_by_post for t in set(row))
    token_tf = Counter(t for row in tokens_by_post for t in row)
    token_df = Counter(t for row in tokens_by_post for t in set(row))

    keyword_rows: dict[str, list[int]] = defaultdict(list)
    for i, tokens in enumerate(tokens_by_post):
        for token in set(tokens):
            keyword_rows[token].append(i)
    keyword_engagement = []
    for token, rows in keyword_rows.items():
        if len(rows) < 20:
            continue
        sub_likes = likes.iloc[rows]
        sub_comments = comments.iloc[rows]
        keyword_engagement.append({
            "keyword": token,
            "posts": len(rows),
            "median_likes": round(float(sub_likes.median()), 2),
            "mean_likes": round(float(sub_likes.mean()), 2),
            "median_comments": round(float(sub_comments.median()), 2),
        })
    keyword_engagement.sort(key=lambda x: (x["median_likes"], x["posts"]), reverse=True)

    hashtag_rows: dict[str, list[int]] = defaultdict(list)
    for i, tags in enumerate(hashtags_by_post):
        for tag in set(tags):
            hashtag_rows[tag].append(i)
    hashtag_engagement = []
    for tag, rows in hashtag_rows.items():
        if len(rows) < 100:
            continue
        sub_likes = likes.iloc[rows]
        sub_comments = comments.iloc[rows]
        hashtag_engagement.append({
            "hashtag": tag,
            "posts": len(rows),
            "like_available": int(sub_likes.notna().sum()),
            "median_likes": round(float(sub_likes.median()), 2),
            "mean_likes": round(float(sub_likes.mean()), 2),
            "median_comments": round(float(sub_comments.median()), 2),
        })
    hashtag_engagement.sort(key=lambda x: (x["median_likes"], x["posts"]), reverse=True)

    valid = pd.DataFrame({"likes": likes, "comments": comments}).dropna()
    local = dt.dt.tz_convert("Asia/Seoul")
    out = {
        "file": str(args.csv_path.resolve()),
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "columns": [
            {
                "name": c,
                "dtype": str(df[c].dtype),
                "nulls": int(df[c].isna().sum()),
                "null_pct": round(float(df[c].isna().mean() * 100), 3),
                "unique": int(df[c].nunique(dropna=True)),
            }
            for c in df.columns
        ],
        "quality": {
            "duplicate_full_rows": int(df.duplicated().sum()),
            "duplicate_post_id": int(df["post_id"].duplicated().sum()),
            "duplicate_post_url": int(df["post_url"].duplicated().sum()),
            "invalid_created_at": int(dt.isna().sum()),
            "negative_likes": int((likes < 0).sum()),
            "negative_comments": int((comments < 0).sum()),
        },
        "period": {"min": str(local.min()), "max": str(local.max())},
        "description": {
            "nonempty": int(desc.str.strip().ne("").sum()),
            "empty_or_null": int(desc.str.strip().eq("").sum()),
            "length_median": round(float(desc.str.len().median()), 1),
            "length_mean": round(float(desc.str.len().mean()), 1),
            "length_p90": round(float(desc.str.len().quantile(0.9)), 1),
            "length_max": int(desc.str.len().max()),
            "posts_with_hashtag": int(pd.Series(hashtags_by_post).map(bool).sum()),
            "posts_with_mention": int(desc.str.contains(MENTION_RE).sum()),
            "posts_with_url": int(desc.str.contains(URL_RE).sum()),
        },
        "media_type_counts": value_counts_dict(df["media_type_id"]),
        "media_type_engagement": [
            {
                "media_type_id": str(k),
                "posts": int(len(g)),
                "like_missing": int(pd.to_numeric(g["like_count"], errors="coerce").isna().sum()),
                "median_likes": round(float(pd.to_numeric(g["like_count"], errors="coerce").median()), 2),
                "median_comments": round(float(pd.to_numeric(g["comment_count"], errors="coerce").median()), 2),
            }
            for k, g in df.groupby("media_type_id", dropna=False)
        ],
        "engagement": {
            c: {
                "min": float(s.min()),
                "q25": float(s.quantile(0.25)),
                "median": float(s.median()),
                "mean": round(float(s.mean()), 2),
                "q75": float(s.quantile(0.75)),
                "q90": float(s.quantile(0.90)),
                "q99": float(s.quantile(0.99)),
                "max": float(s.max()),
                "zeros": int((s == 0).sum()),
            }
            for c, s in {"like_count": likes, "comment_count": comments}.items()
        },
        "spearman_like_comment": round(float(valid.corr(method="spearman").iloc[0, 1]), 4),
        "created_weekday_counts": value_counts_dict(local.dt.day_name()),
        "created_hour_counts": value_counts_dict(local.dt.hour, 24),
        "hashtag_total_occurrences": int(sum(hashtag_tf.values())),
        "hashtag_unique": int(len(hashtag_tf)),
        "top_hashtags_tf": [[k, int(v)] for k, v in hashtag_tf.most_common(args.top)],
        "top_hashtags_df": [[k, int(v)] for k, v in hashtag_df.most_common(args.top)],
        "top_body_tokens_tf": [[k, int(v)] for k, v in token_tf.most_common(args.top)],
        "top_body_tokens_df": [[k, int(v)] for k, v in token_df.most_common(args.top)],
        "top_keyword_engagement_min20": keyword_engagement[: args.top],
        "top_hashtag_engagement_min100": hashtag_engagement[: args.top],
        "yearly": [
            {
                "year": int(year),
                "posts": int(len(g)),
                "like_missing": int(g["likes"].isna().sum()),
                "median_likes": round(float(g["likes"].median()), 2),
                "median_comments": round(float(g["comments"].median()), 2),
            }
            for year, g in pd.DataFrame({"year": local.dt.year, "likes": likes, "comments": comments}).groupby("year")
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
