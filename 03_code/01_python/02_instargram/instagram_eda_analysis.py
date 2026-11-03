from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATASET_LABELS = {
    "all_posts": "전체 게시물",
    "chiikawa_filtered": "치이카와 필터",
}


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def safe_int(value):
    if pd.isna(value):
        return None
    return int(value)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def configure_plotting() -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 130
    plt.rcParams["savefig.dpi"] = 180
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def load_posts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"post_id": "string", "media_type_id": "Int64"})
    df["created_at_parsed"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    for col in ["like_count", "comment_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def profile_dataset(key: str, df: pd.DataFrame, media: pd.DataFrame):
    rows = len(df)
    missing_rows = []
    for col in [c for c in df.columns if c != "created_at_parsed"]:
        count = int(df[col].isna().sum())
        missing_rows.append(
            {
                "dataset": DATASET_LABELS[key],
                "column": col,
                "missing_count": count,
                "missing_pct": count / rows if rows else np.nan,
            }
        )

    duplicate_rows = []
    checks = {
        "완전 동일 행": int(df.drop(columns=["created_at_parsed"]).duplicated().sum()),
        "post_id 추가 중복": int(df["post_id"].duplicated().sum()),
        "post_url 추가 중복": int(df["post_url"].duplicated().sum()),
        "description 추가 중복(결측 제외)": int(df.loc[df["description"].notna(), "description"].duplicated().sum()),
    }
    for check, count in checks.items():
        duplicate_rows.append(
            {
                "dataset": DATASET_LABELS[key],
                "check": check,
                "duplicate_count": count,
                "duplicate_pct": count / rows if rows else np.nan,
            }
        )

    valid_media_ids = set(media["media_type_id"].dropna().astype(int))
    media_fk_invalid = int((~df["media_type_id"].isin(valid_media_ids) & df["media_type_id"].notna()).sum())
    url_invalid = int((~df["post_url"].fillna("").str.match(r"^https://www\.instagram\.com/", na=False)).sum())
    invalid_dates = int(df["created_at_parsed"].isna().sum())
    negative_likes = int((df["like_count"] < 0).fillna(False).sum())
    negative_comments = int((df["comment_count"] < 0).fillna(False).sum())

    quality = {
        "dataset": DATASET_LABELS[key],
        "rows": rows,
        "columns": len([c for c in df.columns if c != "created_at_parsed"]),
        "unique_post_ids": int(df["post_id"].nunique(dropna=True)),
        "full_duplicate_rows": checks["완전 동일 행"],
        "duplicate_post_ids": checks["post_id 추가 중복"],
        "invalid_dates": invalid_dates,
        "invalid_instagram_urls": url_invalid,
        "invalid_media_type_fk": media_fk_invalid,
        "negative_likes": negative_likes,
        "negative_comments": negative_comments,
        "date_min_utc": df["created_at_parsed"].min().isoformat() if df["created_at_parsed"].notna().any() else None,
        "date_max_utc": df["created_at_parsed"].max().isoformat() if df["created_at_parsed"].notna().any() else None,
    }

    dtype_rows = []
    expected = {
        "post_id": "문자열 식별자",
        "description": "문자열",
        "media_type_id": "정수 외래키",
        "post_url": "문자열 URL",
        "created_at": "시간대 포함 일시",
        "like_count": "0 이상 수치",
        "comment_count": "0 이상 정수",
    }
    for col in expected:
        dtype_rows.append(
            {
                "dataset": DATASET_LABELS[key],
                "column": col,
                "loaded_dtype": str(df[col].dtype),
                "expected_role": expected[col],
            }
        )
    return quality, pd.DataFrame(missing_rows), pd.DataFrame(duplicate_rows), pd.DataFrame(dtype_rows)


def engagement_summary(key: str, df: pd.DataFrame):
    rows = []
    outlier_info = {}
    for col, label in [("like_count", "좋아요"), ("comment_count", "댓글")]:
        s = df[col].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        lower = max(0.0, q1 - 1.5 * iqr)
        outlier_mask = (df[col] < lower) | (df[col] > upper)
        outlier_info[col] = {
            "lower": float(lower),
            "upper": float(upper),
            "count": int(outlier_mask.fillna(False).sum()),
        }
        rows.append(
            {
                "dataset": DATASET_LABELS[key],
                "metric": label,
                "valid_count": int(s.count()),
                "missing_count": int(df[col].isna().sum()),
                "mean": safe_float(s.mean()),
                "std": safe_float(s.std()),
                "min": safe_float(s.min()),
                "p25": safe_float(s.quantile(0.25)),
                "median": safe_float(s.median()),
                "p75": safe_float(s.quantile(0.75)),
                "p90": safe_float(s.quantile(0.90)),
                "p95": safe_float(s.quantile(0.95)),
                "p99": safe_float(s.quantile(0.99)),
                "max": safe_float(s.max()),
                "zero_count": int((s == 0).sum()),
                "zero_pct": float((s == 0).mean()),
                "iqr_lower": float(lower),
                "iqr_upper": float(upper),
                "iqr_outlier_count": int(outlier_mask.fillna(False).sum()),
                "iqr_outlier_pct": float(outlier_mask.fillna(False).mean()),
            }
        )
    complete = df[["like_count", "comment_count"]].dropna()
    corr = {
        "dataset": DATASET_LABELS[key],
        "complete_pairs": len(complete),
        "pearson": safe_float(complete.corr(method="pearson").iloc[0, 1]) if len(complete) > 1 else None,
        "spearman": safe_float(complete.corr(method="spearman").iloc[0, 1]) if len(complete) > 1 else None,
    }
    return pd.DataFrame(rows), outlier_info, corr


def outlier_table(key: str, df: pd.DataFrame, outlier_info: dict, media_map: dict) -> pd.DataFrame:
    mask_like = df["like_count"] > outlier_info["like_count"]["upper"]
    mask_comment = df["comment_count"] > outlier_info["comment_count"]["upper"]
    out = df.loc[mask_like.fillna(False) | mask_comment.fillna(False)].copy()
    out["dataset"] = DATASET_LABELS[key]
    out["media_type"] = out["media_type_id"].map(media_map)
    out["like_outlier"] = mask_like.loc[out.index].values
    out["comment_outlier"] = mask_comment.loc[out.index].values
    out["description_preview"] = out["description"].fillna("").str.replace(r"\s+", " ", regex=True).str.slice(0, 120)
    out["engagement_total"] = out["like_count"].fillna(0) + out["comment_count"].fillna(0)
    cols = [
        "dataset", "post_id", "created_at", "media_type", "like_count", "comment_count",
        "engagement_total", "like_outlier", "comment_outlier", "post_url", "description_preview",
    ]
    return out[cols].sort_values(["engagement_total", "like_count"], ascending=False)


def build_time_tables(frames: dict[str, pd.DataFrame]):
    monthly = []
    yearly = []
    hours = []
    for key, df in frames.items():
        temp = df.loc[df["created_at_parsed"].notna()].copy()
        temp["month"] = temp["created_at_parsed"].dt.strftime("%Y-%m")
        temp["year"] = temp["created_at_parsed"].dt.year
        temp["hour_kst"] = temp["created_at_parsed"].dt.tz_convert("Asia/Seoul").dt.hour
        m = temp.groupby("month", as_index=False).agg(
            post_count=("post_id", "count"),
            like_median=("like_count", "median"),
            comment_median=("comment_count", "median"),
        )
        m.insert(0, "dataset", DATASET_LABELS[key])
        monthly.append(m)
        y = temp.groupby("year", as_index=False).agg(post_count=("post_id", "count"))
        y.insert(0, "dataset", DATASET_LABELS[key])
        yearly.append(y)
        h = temp.groupby("hour_kst", as_index=False).agg(post_count=("post_id", "count"))
        h.insert(0, "dataset", DATASET_LABELS[key])
        hours.append(h)
    return pd.concat(monthly, ignore_index=True), pd.concat(yearly, ignore_index=True), pd.concat(hours, ignore_index=True)


def media_distribution(frames: dict[str, pd.DataFrame], media: pd.DataFrame) -> pd.DataFrame:
    media_map = dict(zip(media["media_type_id"].astype(int), media["media_type"]))
    parts = []
    for key, df in frames.items():
        counts = df["media_type_id"].map(media_map).fillna("UNKNOWN").value_counts(dropna=False)
        part = counts.rename_axis("media_type").reset_index(name="post_count")
        part.insert(0, "dataset", DATASET_LABELS[key])
        part["share"] = part["post_count"] / len(df)
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def keyword_tables(posts: pd.DataFrame, filtered: pd.DataFrame, post_keywords_path: Path, keywords_path: Path):
    post_keywords = pd.read_csv(post_keywords_path, dtype={"post_id": "string", "keyword_id": "Int64"})
    keywords = pd.read_csv(keywords_path, dtype={"keyword_id": "Int64"})
    linked = post_keywords.merge(keywords, on="keyword_id", how="left", validate="many_to_one")
    filtered_ids = set(filtered["post_id"].dropna())
    linked["in_chiikawa_filter"] = linked["post_id"].isin(filtered_ids)
    source = (
        linked.groupby("keyword", dropna=False)
        .agg(tagged_posts=("post_id", "nunique"), filtered_posts=("in_chiikawa_filter", "sum"))
        .reset_index()
        .sort_values("tagged_posts", ascending=False)
    )
    source["share_of_all_posts"] = source["tagged_posts"] / len(posts)
    source["filtered_retention"] = source["filtered_posts"] / source["tagged_posts"]

    hashtag_rows = []
    pattern = re.compile(r"#([0-9A-Za-z가-힣_]+)")
    for key, df in [("all_posts", posts), ("chiikawa_filtered", filtered)]:
        occurrence = {}
        document = {}
        for text in df["description"].fillna("").astype(str):
            tags = [t.lower() for t in pattern.findall(text)]
            for tag in tags:
                occurrence[tag] = occurrence.get(tag, 0) + 1
            for tag in set(tags):
                document[tag] = document.get(tag, 0) + 1
        for tag, doc_count in sorted(document.items(), key=lambda x: (-x[1], x[0])):
            hashtag_rows.append(
                {
                    "dataset": DATASET_LABELS[key],
                    "hashtag": tag,
                    "document_count": doc_count,
                    "document_share": doc_count / len(df),
                    "occurrence_count": occurrence[tag],
                }
            )
    hashtags = pd.DataFrame(hashtag_rows)
    return source, hashtags


def make_figures(output_dir: Path, frames: dict[str, pd.DataFrame], monthly: pd.DataFrame,
                 media_dist: pd.DataFrame, source_keywords: pd.DataFrame, hashtags: pd.DataFrame,
                 correlations: pd.DataFrame):
    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    colors = {"전체 게시물": "#3B82F6", "치이카와 필터": "#F59E0B"}

    fig, ax = plt.subplots(figsize=(11, 4.8))
    for name, grp in monthly.groupby("dataset"):
        ax.plot(pd.to_datetime(grp["month"]), grp["post_count"], marker="o", ms=3, lw=1.7, label=name, color=colors[name])
    ax.set_title("월별 게시물 수")
    ax.set_ylabel("게시물 수")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(fig_dir / "01_monthly_posts.png", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, col, title in zip(axes, ["like_count", "comment_count"], ["좋아요 분포", "댓글 분포"]):
        for key, df in frames.items():
            vals = np.log1p(df[col].dropna().clip(lower=0))
            ax.hist(vals, bins=45, alpha=0.48, density=True, label=DATASET_LABELS[key], color=colors[DATASET_LABELS[key]])
        ax.set_title(title + " (log1p)")
        ax.set_xlabel("log(1 + 건수)")
        ax.set_ylabel("밀도")
        ax.grid(axis="y", alpha=0.18)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "02_engagement_distributions.png", bbox_inches="tight")
    plt.close(fig)

    pivot = media_dist.pivot(index="media_type", columns="dataset", values="post_count").fillna(0)
    pivot = pivot.sort_values("전체 게시물", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot.plot(kind="barh", ax=ax, color=[colors.get(c, "#64748B") for c in pivot.columns])
    ax.set_title("게시 유형별 게시물 수")
    ax.set_xlabel("게시물 수")
    ax.set_ylabel("")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    fig.savefig(fig_dir / "03_media_types.png", bbox_inches="tight")
    plt.close(fig)

    top = source_keywords.head(13).sort_values("tagged_posts", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.barh(top["keyword"].astype(str), top["tagged_posts"], color="#3B82F6")
    ax.set_title("수집 키워드별 게시물 수")
    ax.set_xlabel("고유 게시물 수")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    fig.savefig(fig_dir / "04_source_keywords.png", bbox_inches="tight")
    plt.close(fig)

    top_hash = hashtags[hashtags["dataset"] == "치이카와 필터"].head(20).sort_values("document_count", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh(top_hash["hashtag"], top_hash["document_count"], color="#F59E0B")
    ax.set_title("치이카와 필터 상위 해시태그")
    ax.set_xlabel("해시태그가 포함된 게시물 수")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    fig.savefig(fig_dir / "05_top_hashtags.png", bbox_inches="tight")
    plt.close(fig)

    df = frames["chiikawa_filtered"].dropna(subset=["like_count", "comment_count"])
    if len(df) > 5000:
        df = df.sample(5000, random_state=42)
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.scatter(np.log1p(df["like_count"].clip(lower=0)), np.log1p(df["comment_count"].clip(lower=0)), s=12, alpha=0.28, color="#7C3AED", edgecolors="none")
    ax.set_title("치이카와 필터 좋아요와 댓글 관계")
    ax.set_xlabel("log(1 + 좋아요)")
    ax.set_ylabel("log(1 + 댓글)")
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(fig_dir / "06_like_comment_scatter.png", bbox_inches="tight")
    plt.close(fig)


def format_table_html(df: pd.DataFrame, max_rows=30, pct_cols=None, num_cols=None):
    show = df.head(max_rows).copy()
    pct_cols = pct_cols or []
    num_cols = num_cols or []
    for c in pct_cols:
        if c in show:
            show[c] = show[c].map(lambda x: "" if pd.isna(x) else f"{x:.1%}")
    for c in num_cols:
        if c in show:
            show[c] = show[c].map(lambda x: "" if pd.isna(x) else f"{x:,.2f}" if isinstance(x, float) and not float(x).is_integer() else f"{x:,.0f}")
    return show.to_html(index=False, escape=True, border=0, classes="data")


def build_html(output_dir: Path, summary: dict, quality: pd.DataFrame, missing: pd.DataFrame,
               duplicates: pd.DataFrame, engagement: pd.DataFrame, media_dist: pd.DataFrame,
               source_keywords: pd.DataFrame, hashtags: pd.DataFrame, correlations: pd.DataFrame,
               outliers: pd.DataFrame):
    q_all = quality.loc[quality["dataset"] == "전체 게시물"].iloc[0]
    q_fil = quality.loc[quality["dataset"] == "치이카와 필터"].iloc[0]
    html_text = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Instagram EDA 보고서</title>
<style>
body{{font-family:'Malgun Gothic',Arial,sans-serif;color:#172033;background:#f5f7fb;margin:0;line-height:1.55}}
.wrap{{max-width:1180px;margin:0 auto;padding:36px 28px 64px}} h1{{font-size:30px;margin:0 0 8px}} h2{{margin-top:38px;border-bottom:2px solid #dce3ee;padding-bottom:8px}}
.sub{{color:#5b6678}} .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}} .card{{background:white;border:1px solid #e1e7ef;border-radius:10px;padding:18px}}
.k{{font-size:13px;color:#64748b}} .v{{font-size:25px;font-weight:700;margin-top:4px}} .note{{background:#fff7ed;border-left:4px solid #f59e0b;padding:14px 16px;margin:18px 0}}
.insight{{background:#eef6ff;border-left:4px solid #3b82f6;padding:14px 16px;margin:14px 0}} table.data{{border-collapse:collapse;width:100%;background:white;font-size:13px}}
table.data th{{background:#263b5a;color:white;padding:8px;text-align:center}} table.data td{{border-bottom:1px solid #e5e9f0;padding:7px 9px;text-align:right}} table.data td:nth-child(-n+2){{text-align:left}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} img{{max-width:100%;background:white;border:1px solid #e1e7ef;border-radius:8px}} code{{background:#e9eef5;padding:2px 5px;border-radius:4px}}
@media(max-width:800px){{.cards,.grid2{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>인스타그램 게시물 EDA</h1><div class="sub">대원미디어 IP 사업 다각화를 위한 국내 창작자 협업 전략 · 원본 전체와 치이카와 필터 비교</div>
<div class="cards">
<div class="card"><div class="k">전체 게시물</div><div class="v">{int(q_all['rows']):,}</div></div>
<div class="card"><div class="k">치이카와 필터</div><div class="v">{int(q_fil['rows']):,}</div></div>
<div class="card"><div class="k">필터 포함률</div><div class="v">{summary['filter_coverage']:.1%}</div></div>
<div class="card"><div class="k">분석 기간</div><div class="v" style="font-size:16px">{html.escape(summary['date_range_label'])}</div></div>
</div>
<div class="note"><b>해석 범위:</b> 해시태그 기반 수집 자료이므로 인스타그램 전체 이용자나 실제 구매 전환을 대표하지 않습니다. 좋아요 결측은 0으로 대체하지 않았고, 이상치는 오류로 삭제하지 않고 별도 표시했습니다.</div>
<h2>핵심 점검 결과</h2>
<div class="insight">{html.escape(summary['headline_quality'])}</div>
<div class="insight">{html.escape(summary['headline_engagement'])}</div>
<div class="insight">{html.escape(summary['headline_strategy'])}</div>
{format_table_html(quality, num_cols=['rows','columns','unique_post_ids','full_duplicate_rows','duplicate_post_ids','invalid_dates','invalid_instagram_urls','invalid_media_type_fk','negative_likes','negative_comments'])}
<h2>날짜와 게시물 흐름</h2><img src="figures/01_monthly_posts.png" alt="월별 게시물 수">
<h2>좋아요·댓글 분포와 이상치</h2><div class="grid2"><img src="figures/02_engagement_distributions.png"><img src="figures/06_like_comment_scatter.png"></div>
{format_table_html(engagement, pct_cols=['zero_pct','iqr_outlier_pct'], num_cols=['valid_count','missing_count','mean','std','min','p25','median','p75','p90','p95','p99','max','zero_count','iqr_lower','iqr_upper','iqr_outlier_count'])}
<p><b>상관계수:</b> {format_table_html(correlations, num_cols=['complete_pairs','pearson','spearman'])}</p>
<h2>게시 유형</h2><img src="figures/03_media_types.png">{format_table_html(media_dist, pct_cols=['share'], num_cols=['post_count'])}
<h2>키워드와 해시태그</h2><div class="grid2"><img src="figures/04_source_keywords.png"><img src="figures/05_top_hashtags.png"></div>
<h3>수집 키워드</h3>{format_table_html(source_keywords, max_rows=20, pct_cols=['share_of_all_posts','filtered_retention'], num_cols=['tagged_posts','filtered_posts'])}
<h3>치이카와 필터 상위 해시태그</h3>{format_table_html(hashtags[hashtags['dataset']=='치이카와 필터'], max_rows=30, pct_cols=['document_share'], num_cols=['document_count','occurrence_count'])}
<h2>결측과 중복</h2><div class="grid2"><div>{format_table_html(missing, pct_cols=['missing_pct'], num_cols=['missing_count'])}</div><div>{format_table_html(duplicates, pct_cols=['duplicate_pct'], num_cols=['duplicate_count'])}</div></div>
<h2>상위 반응 이상치</h2>{format_table_html(outliers, max_rows=30, num_cols=['like_count','comment_count','engagement_total'])}
<h2>재현 방법</h2><p>동봉한 <code>instagram_eda_analysis.py</code>에 원본 CSV 경로를 인수로 전달하면 동일한 CSV 요약표와 PNG 시각화를 다시 생성할 수 있습니다. 산출물의 <code>analysis_metadata.json</code>에는 입력 경로, 생성 시각과 핵심 수치가 기록되어 있습니다.</p>
</div></body></html>"""
    (output_dir / "instagram_eda_report.html").write_text(html_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Instagram 3NF 게시물 EDA")
    parser.add_argument("--posts", required=True, type=Path)
    parser.add_argument("--filtered", required=True, type=Path)
    parser.add_argument("--post-keywords", required=True, type=Path)
    parser.add_argument("--keywords", required=True, type=Path)
    parser.add_argument("--media-types", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    configure_plotting()

    posts = load_posts(args.posts)
    filtered = load_posts(args.filtered)
    media = pd.read_csv(args.media_types, dtype={"media_type_id": "Int64"})
    frames = {"all_posts": posts, "chiikawa_filtered": filtered}

    qualities, missing_parts, duplicate_parts, dtype_parts = [], [], [], []
    engagement_parts, correlations, outlier_parts = [], [], []
    outlier_infos = {}
    media_map = dict(zip(media["media_type_id"].astype(int), media["media_type"]))
    for key, df in frames.items():
        q, m, d, t = profile_dataset(key, df, media)
        qualities.append(q); missing_parts.append(m); duplicate_parts.append(d); dtype_parts.append(t)
        e, info, corr = engagement_summary(key, df)
        engagement_parts.append(e); outlier_infos[key] = info; correlations.append(corr)
        outlier_parts.append(outlier_table(key, df, info, media_map))

    quality = pd.DataFrame(qualities)
    missing = pd.concat(missing_parts, ignore_index=True)
    duplicates = pd.concat(duplicate_parts, ignore_index=True)
    dtypes = pd.concat(dtype_parts, ignore_index=True)
    engagement = pd.concat(engagement_parts, ignore_index=True)
    correlations_df = pd.DataFrame(correlations)
    outliers = pd.concat(outlier_parts, ignore_index=True)
    monthly, yearly, hourly = build_time_tables(frames)
    media_dist = media_distribution(frames, media)
    source_keywords, hashtags = keyword_tables(posts, filtered, args.post_keywords, args.keywords)

    filtered_ids = set(filtered["post_id"].dropna())
    all_ids = set(posts["post_id"].dropna())
    missing_from_all = filtered_ids - all_ids
    excluded_ids = all_ids - filtered_ids
    subset_checks = pd.DataFrame([
        {"check": "필터 post_id가 전체에 없는 건수", "count": len(missing_from_all)},
        {"check": "전체에서 필터로 제외된 post_id", "count": len(excluded_ids)},
        {"check": "필터 포함률", "count": len(filtered_ids) / len(all_ids) if all_ids else np.nan},
        {"check": "post_keywords의 고아 post_id", "count": int((~pd.read_csv(args.post_keywords, dtype={"post_id":"string"})["post_id"].isin(all_ids)).sum())},
    ])

    for name, df in {
        "data_quality_summary.csv": quality,
        "missing_values.csv": missing,
        "duplicate_checks.csv": duplicates,
        "data_types.csv": dtypes,
        "engagement_statistics.csv": engagement,
        "engagement_correlations.csv": correlations_df,
        "outlier_posts.csv": outliers,
        "monthly_distribution.csv": monthly,
        "yearly_distribution.csv": yearly,
        "hourly_distribution_kst.csv": hourly,
        "media_type_distribution.csv": media_dist,
        "source_keyword_frequency.csv": source_keywords,
        "hashtag_frequency.csv": hashtags,
        "relational_integrity_checks.csv": subset_checks,
    }.items():
        save_csv(df, args.output_dir / name)

    all_like = engagement[(engagement["dataset"] == "전체 게시물") & (engagement["metric"] == "좋아요")].iloc[0]
    fil_like = engagement[(engagement["dataset"] == "치이카와 필터") & (engagement["metric"] == "좋아요")].iloc[0]
    fil_comments = engagement[(engagement["dataset"] == "치이카와 필터") & (engagement["metric"] == "댓글")].iloc[0]
    date_min = posts["created_at_parsed"].min().tz_convert("Asia/Seoul")
    date_max = posts["created_at_parsed"].max().tz_convert("Asia/Seoul")
    coverage = len(filtered_ids) / len(all_ids)
    top_source = source_keywords.iloc[0]
    top_hash = hashtags[hashtags["dataset"] == "치이카와 필터"].iloc[0]
    summary = {
        "source_files": {k: str(v) for k, v in vars(args).items() if k != "output_dir"},
        "filter_coverage": coverage,
        "filtered_excluded_count": len(excluded_ids),
        "date_range_label": f"{date_min:%Y-%m-%d} ~ {date_max:%Y-%m-%d}",
        "headline_quality": f"전체 {len(posts):,}건 중 치이카와 필터는 {len(filtered):,}건({coverage:.1%})입니다. 필터 post_id의 전체 데이터셋 이탈은 {len(missing_from_all):,}건입니다.",
        "headline_engagement": f"치이카와 필터의 좋아요 중앙값은 {fil_like['median']:,.0f}, 99백분위는 {fil_like['p99']:,.0f}이고 댓글 중앙값은 {fil_comments['median']:,.0f}입니다. IQR 기준 좋아요 이상치는 {int(fil_like['iqr_outlier_count']):,}건으로 삭제 대신 별도 검토 대상으로 유지했습니다.",
        "headline_strategy": f"수집 키워드 상위 항목은 '{top_source['keyword']}'({int(top_source['tagged_posts']):,}건), 치이카와 필터에서 가장 널리 쓰인 해시태그는 #{top_hash['hashtag']}({int(top_hash['document_count']):,}건)입니다. 빈도는 수집 설계의 영향을 받으므로 창작자 협업 후보 평가는 반응률·콘텐츠 맥락·팬덤 자발성 분류와 결합해야 합니다.",
        "all_like_median": safe_float(all_like["median"]),
        "filtered_like_median": safe_float(fil_like["median"]),
        "filtered_comment_median": safe_float(fil_comments["median"]),
        "filtered_like_p99": safe_float(fil_like["p99"]),
        "filtered_like_outliers": safe_int(fil_like["iqr_outlier_count"]),
        "filtered_comment_outliers": safe_int(fil_comments["iqr_outlier_count"]),
        "top_source_keyword": str(top_source["keyword"]),
        "top_source_keyword_count": int(top_source["tagged_posts"]),
        "top_hashtag": str(top_hash["hashtag"]),
        "top_hashtag_count": int(top_hash["document_count"]),
    }
    (args.output_dir / "analysis_metadata.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    make_figures(args.output_dir, frames, monthly, media_dist, source_keywords, hashtags, correlations_df)
    build_html(args.output_dir, summary, quality, missing, duplicates, engagement, media_dist,
               source_keywords, hashtags, correlations_df, outliers)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
