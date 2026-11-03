# -*- coding: utf-8 -*-
"""A 영상 규모·시기·길이·채널·성과 1차 탐색. 원본 CSV는 읽기만 한다."""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

SRC = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
    r"\youtube_total_cleaning_classified_A.csv"
)
OUT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_1차탐색"
)
EXPECTED_N = 6462

DUR_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)
BIN_ORDER = [
    "60초 이하",
    "60초 초과–180초 이하",
    "180초 초과–600초 이하",
    "600초 초과–1,200초 이하",
    "1,200초 초과",
    "변환 불가·결측",
]
NAME_RULE = "영상 수가 가장 많은 이름. 동률이면 가장 최근 게시 영상에 쓰인 이름."


def parse_duration_seconds(value) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().upper()
    if text == "" or text == "NAN":
        return np.nan
    match = DUR_RE.fullmatch(text)
    if not match:
        return np.nan
    parts = match.groupdict()
    if not any(parts.values()):
        return np.nan
    days = int(parts["days"] or 0)
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = float(parts["seconds"] or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def duration_bin(seconds) -> str:
    if pd.isna(seconds):
        return "변환 불가·결측"
    if seconds <= 60:
        return "60초 이하"
    if seconds <= 180:
        return "60초 초과–180초 이하"
    if seconds <= 600:
        return "180초 초과–600초 이하"
    if seconds <= 1200:
        return "600초 초과–1,200초 이하"
    return "1,200초 초과"


def tz_kind(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    kind = pd.Series("결측 또는 시간대 없음", index=series.index)
    kind.loc[series.notna() & text.str.endswith("Z")] = "UTC(Z)"
    kind.loc[series.notna() & text.str.contains(r"[+-]\d{2}:\d{2}$", regex=True)] = "명시적 오프셋"
    kind.loc[series.isna()] = "결측"
    return kind


def dist_row(metric: str, series: pd.Series, with_sum: bool = True) -> dict:
    valid = series.dropna()
    row = {
        "지표": metric,
        "유효_영상수": int(valid.shape[0]),
        "결측_영상수": int(series.isna().sum()),
        "최솟값": np.nan,
        "1사분위": np.nan,
        "중앙값": np.nan,
        "3사분위": np.nan,
        "90백분위": np.nan,
        "최댓값": np.nan,
        "합계": np.nan,
    }
    if valid.empty:
        return row
    q = valid.quantile([0.25, 0.5, 0.75, 0.9])
    row.update(
        {
            "최솟값": float(valid.min()),
            "1사분위": float(q.loc[0.25]),
            "중앙값": float(q.loc[0.5]),
            "3사분위": float(q.loc[0.75]),
            "90백분위": float(q.loc[0.9]),
            "최댓값": float(valid.max()),
        }
    )
    if with_sum:
        row["합계"] = float(valid.sum())
    return row


def rate_pair(frame: pd.DataFrame, numer: str, denom: str) -> dict:
    mask = frame[numer].notna() & frame[denom].notna() & (frame[denom] > 0)
    sub = frame.loc[mask]
    per = sub[numer] / sub[denom] * 100
    out = {
        "유효_영상수": int(mask.sum()),
        "계산불가_영상수": int((~mask).sum()),
        "영상별_중앙값_pct": float(per.median()) if len(per) else np.nan,
        "영상별_1사분위_pct": float(per.quantile(0.25)) if len(per) else np.nan,
        "영상별_3사분위_pct": float(per.quantile(0.75)) if len(per) else np.nan,
        "합계비_pct": float(sub[numer].sum() / sub[denom].sum() * 100) if len(sub) else np.nan,
        "분자합": float(sub[numer].sum()) if len(sub) else np.nan,
        "분모합": float(sub[denom].sum()) if len(sub) else np.nan,
    }
    return out


def spearman(a: pd.Series, b: pd.Series) -> float:
    return float(a.rank(method="average").corr(b.rank(method="average")))


def fmt_int(value) -> str:
    if pd.isna(value):
        return "계산 불가"
    return f"{int(round(float(value))):,}"


def fmt_num(value, digits=1) -> str:
    if pd.isna(value):
        return "계산 불가"
    return f"{float(value):,.{digits}f}"


def fmt_pct(value, digits=2) -> str:
    if pd.isna(value):
        return "계산 불가"
    return f"{float(value):.{digits}f}%"


def choose_display_names(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    named = frame.dropna(subset=["account_id"])
    for account_id, group in named.groupby("account_id", sort=False):
        names = group["account_name"].fillna("(이름 결측)")
        counts = names.value_counts()
        top_count = int(counts.max())
        candidates = counts[counts == top_count].index.tolist()
        if len(candidates) == 1:
            display = candidates[0]
            rule = NAME_RULE
        else:
            latest = group.assign(_name=names).sort_values(
                ["created_kst", "post_id"], ascending=[False, True]
            )
            display = latest["_name"].iloc[0]
            rule = NAME_RULE
        rows.append(
            {
                "account_id": account_id,
                "display_name": display,
                "n_names": int(names.nunique()),
                "name_variants": " | ".join(sorted(names.unique())),
                "n_videos": int(len(group)),
                "selection_rule": rule,
            }
        )
    return pd.DataFrame(rows)


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def foot(fig, text: str, bottom: float = 0.18) -> None:
    fig.tight_layout()
    fig.subplots_adjust(bottom=bottom)
    fig.text(0.01, 0.012, text, fontsize=8, color="#444")


def style_ax(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=12, pad=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.5)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    raw = pd.read_csv(SRC, encoding="utf-8-sig")
    n_rows = int(len(raw))
    n_id = int(raw["post_id"].nunique(dropna=False))
    dup_mask = raw["post_id"].duplicated(keep=False)
    n_dup_rows = int(dup_mask.sum())
    n_dup_ids = int(raw.loc[dup_mask, "post_id"].nunique()) if n_dup_rows else 0

    conflict_notes = []
    if n_dup_ids:
        for post_id, group in raw.loc[dup_mask].groupby("post_id"):
            varying = [
                col
                for col in raw.columns
                if group[col].astype(str).nunique(dropna=False) > 1
            ]
            conflict_notes.append(
                {
                    "post_id": post_id,
                    "행수": int(len(group)),
                    "값이_다른_컬럼": ", ".join(varying),
                }
            )
        pd.DataFrame(conflict_notes).to_csv(
            OUT / "00_중복ID_충돌.csv", index=False, encoding="utf-8-sig"
        )

    work = raw.copy()
    work["created_tz_kind"] = tz_kind(work["created_at"])
    work["collected_tz_kind"] = tz_kind(work["collected_at"])
    work["created_utc"] = pd.to_datetime(work["created_at"], utc=True, errors="coerce")
    work["collected_utc"] = pd.to_datetime(work["collected_at"], utc=True, errors="coerce")
    created_explicit = work["created_tz_kind"].isin(["UTC(Z)", "명시적 오프셋"])
    collected_explicit = work["collected_tz_kind"].isin(["UTC(Z)", "명시적 오프셋"])
    work["created_kst"] = work["created_utc"].dt.tz_convert("Asia/Seoul")
    work.loc[~created_explicit, "created_kst"] = pd.NaT
    work["collected_kst"] = work["collected_utc"].dt.tz_convert("Asia/Seoul")
    work.loc[~collected_explicit, "collected_kst"] = pd.NaT
    work["year"] = work["created_kst"].dt.year
    work["year_month"] = work["created_kst"].dt.strftime("%Y-%m")
    work["elapsed_days"] = (
        work["collected_utc"] - work["created_utc"]
    ).dt.total_seconds() / 86400
    work.loc[~(created_explicit & collected_explicit), "elapsed_days"] = np.nan

    for col in ["view_count", "like_count", "comment_count"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work["duration_sec"] = work["duration"].map(parse_duration_seconds)
    work["duration_bin"] = work["duration_sec"].map(duration_bin)
    work["like_rate"] = np.where(
        work["like_count"].notna() & work["view_count"].notna() & (work["view_count"] > 0),
        work["like_count"] / work["view_count"] * 100,
        np.nan,
    )
    work["comment_rate"] = np.where(
        work["comment_count"].notna()
        & work["view_count"].notna()
        & (work["view_count"] > 0),
        work["comment_count"] / work["view_count"] * 100,
        np.nan,
    )
    positive_age = work["elapsed_days"].notna() & (work["elapsed_days"] > 0)
    work["views_per_elapsed_day"] = np.where(
        positive_age & work["view_count"].notna(),
        work["view_count"] / work["elapsed_days"],
        np.nan,
    )

    # 기간 완전성: 관측된 게시 범위가 해당 달·해를 모두 덮는지
    kst_ok = work["created_kst"].notna()
    min_kst = work.loc[kst_ok, "created_kst"].min()
    max_kst = work.loc[kst_ok, "created_kst"].max()
    month_start = min_kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (max_kst + pd.offsets.MonthEnd(0)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    all_months = pd.period_range(min_kst, max_kst, freq="M").astype(str)

    def month_coverage(label: str) -> str:
        if label == all_months[0] and min_kst > month_start:
            return "일부"
        if label == all_months[-1] and max_kst < month_end:
            return "일부"
        return "달력월 전체 구간"

    def year_coverage(year: int) -> str:
        start = pd.Timestamp(year=year, month=1, day=1, tz="Asia/Seoul")
        end = pd.Timestamp(year=year, month=12, day=31, hour=23, minute=59, tz="Asia/Seoul")
        if min_kst <= start and max_kst >= end:
            return "연 전체 구간"
        return "일부"

    # ----- 점검 -----
    numeric_flags = []
    for col in ["view_count", "like_count", "comment_count", "duration_sec"]:
        s = work[col]
        numeric_flags.append(
            {
                "컬럼": col,
                "자료형": str(raw[col].dtype) if col != "duration_sec" else "변환값",
                "결측": int(s.isna().sum()),
                "음수": int((s < 0).sum()),
                "0": int((s == 0).sum()),
                "소수값이_있는_건수": int(((s.dropna() % 1) != 0).sum()) if col != "duration_sec" else "해당 없음",
            }
        )
    pd.DataFrame(numeric_flags).to_csv(OUT / "00_수치점검.csv", index=False, encoding="utf-8-sig")

    id_missing = int(work["account_id"].isna().sum())
    name_missing = int(work["account_name"].isna().sum())
    id_only = int((work["account_id"].notna() & work["account_name"].isna()).sum())
    name_only = int((work["account_id"].isna() & work["account_name"].notna()).sum())

    names = choose_display_names(work)
    multi = names[names["n_names"] > 1].sort_values(["n_names", "n_videos"], ascending=False)
    multi.to_csv(OUT / "04_채널명_복수.csv", index=False, encoding="utf-8-sig")
    work = work.merge(
        names[["account_id", "display_name"]],
        on="account_id",
        how="left",
    )

    qc = pd.DataFrame(
        [
            {"항목": "행수", "값": n_rows},
            {"항목": "고유_post_id", "값": n_id},
            {"항목": "중복_post_id_수", "값": n_dup_ids},
            {"항목": "중복에_걸린_행수", "값": n_dup_rows},
            {"항목": "final_class_고유값", "값": " | ".join(sorted(work["final_class"].dropna().unique()))},
            {"항목": "final_class_결측", "값": int(work["final_class"].isna().sum())},
            {"항목": "A_우선포함_행수", "값": int((work["final_class"] == "A_우선포함").sum())},
            {"항목": "created_at_UTC(Z)", "값": int((work["created_tz_kind"] == "UTC(Z)").sum())},
            {"항목": "created_at_명시적오프셋", "값": int((work["created_tz_kind"] == "명시적 오프셋").sum())},
            {"항목": "created_at_시간대불명", "값": int((~created_explicit).sum())},
            {"항목": "collected_at_UTC(Z)", "값": int((work["collected_tz_kind"] == "UTC(Z)").sum())},
            {"항목": "collected_at_명시적오프셋", "값": int((work["collected_tz_kind"] == "명시적 오프셋").sum())},
            {"항목": "collected_at_시간대불명", "값": int((~collected_explicit).sum())},
            {"항목": "duration_변환성공", "값": int(work["duration_sec"].notna().sum())},
            {"항목": "duration_변환실패_또는_결측", "값": int(work["duration_sec"].isna().sum())},
            {"항목": "account_id_결측", "값": id_missing},
            {"항목": "account_name_결측", "값": name_missing},
            {"항목": "ID만_있고_이름결측", "값": id_only},
            {"항목": "이름만_있고_ID결측", "값": name_only},
            {"항목": "이름이_2개이상인_채널ID", "값": int(len(multi))},
            {"항목": "게시후_경과일이_0이하", "값": int((work["elapsed_days"].notna() & (work["elapsed_days"] <= 0)).sum())},
            {"항목": "게시후_경과일_결측", "값": int(work["elapsed_days"].isna().sum())},
            {"항목": "예상행수와_차이", "값": n_rows - EXPECTED_N},
        ]
    )
    qc.to_csv(OUT / "00_데이터점검.csv", index=False, encoding="utf-8-sig")

    # ----- 규모 -----
    scale_metrics = pd.DataFrame(
        [
            dist_row("조회수", work["view_count"]),
            dist_row("좋아요수", work["like_count"]),
            dist_row("댓글수", work["comment_count"]),
            dist_row("영상길이_초", work["duration_sec"], with_sum=False),
            dist_row("좋아요율_pct", pd.Series(work["like_rate"]), with_sum=False),
            dist_row("댓글률_pct", pd.Series(work["comment_rate"]), with_sum=False),
            dist_row("게시후_경과일", work["elapsed_days"], with_sum=False),
            dist_row("일평균_누적조회수", work["views_per_elapsed_day"], with_sum=False),
        ]
    )
    scale_metrics.to_csv(OUT / "01_분포_사분위.csv", index=False, encoding="utf-8-sig")

    view_valid_n = int(work["view_count"].notna().sum())
    like_valid_n = int(work["like_count"].notna().sum())
    comment_valid_n = int(work["comment_count"].notna().sum())
    n_channels = int(work["account_id"].nunique(dropna=True))
    scale_card = pd.DataFrame(
        [
            {"항목": "영상수", "값": n_id, "유효_영상수": n_id, "비고": "고유 post_id. 댓글 연결 여부와 무관"},
            {"항목": "채널수", "값": n_channels, "유효_영상수": n_rows - id_missing, "비고": "account_id 결측은 채널 수에서 제외. 하나의 채널로 합치지 않음"},
            {"항목": "채널ID_결측_영상수", "값": id_missing, "유효_영상수": n_rows, "비고": ""},
            {"항목": "게시_시작_KST", "값": str(min_kst), "유효_영상수": int(kst_ok.sum()), "비고": "created_at이 UTC이면 한국시간으로 변환"},
            {"항목": "게시_종료_KST", "값": str(max_kst), "유효_영상수": int(kst_ok.sum()), "비고": ""},
            {"항목": "수집_시작_KST", "값": str(work["collected_kst"].min()), "유효_영상수": int(work["collected_kst"].notna().sum()), "비고": ""},
            {"항목": "수집_종료_KST", "값": str(work["collected_kst"].max()), "유효_영상수": int(work["collected_kst"].notna().sum()), "비고": ""},
            {"항목": "조회수_합계", "값": float(work["view_count"].sum(min_count=1)), "유효_영상수": view_valid_n, "비고": "값이 있는 영상의 합. 수집 시점 누적"},
            {"항목": "좋아요_합계", "값": float(work["like_count"].sum(min_count=1)), "유효_영상수": like_valid_n, "비고": "값이 있는 영상의 합. 결측을 0으로 두지 않음"},
            {"항목": "댓글수_합계", "값": float(work["comment_count"].sum(min_count=1)), "유효_영상수": comment_valid_n, "비고": "영상 메타데이터의 comment_count 합. 수집 댓글 행 수가 아님"},
        ]
    )
    scale_card.to_csv(OUT / "01_규모_요약.csv", index=False, encoding="utf-8-sig")

    # ----- 시기 -----
    month_rows = []
    for label in all_months:
        sub = work[work["year_month"] == label]
        known_channels = sub["account_id"].nunique(dropna=True)
        month_rows.append(
            {
                "게시월_KST": label,
                "기간구분": month_coverage(label),
                "영상수": int(len(sub)),
                "활동채널수": int(known_channels),
                "채널ID결측_영상수": int(sub["account_id"].isna().sum()),
                "조회수_중앙값": float(sub["view_count"].median()) if sub["view_count"].notna().any() else np.nan,
                "조회수_유효영상수": int(sub["view_count"].notna().sum()),
                "좋아요율_중앙값_pct": float(np.nanmedian(sub["like_rate"])) if np.isfinite(sub["like_rate"]).any() else np.nan,
                "좋아요율_유효영상수": int(np.isfinite(sub["like_rate"]).sum()),
                "댓글률_중앙값_pct": float(np.nanmedian(sub["comment_rate"])) if np.isfinite(sub["comment_rate"]).any() else np.nan,
                "댓글률_유효영상수": int(np.isfinite(sub["comment_rate"]).sum()),
            }
        )
    unknown_month = work[work["year_month"].isna()]
    if len(unknown_month):
        month_rows.append(
            {
                "게시월_KST": "시간대 불명",
                "기간구분": "확인 불가",
                "영상수": int(len(unknown_month)),
                "활동채널수": int(unknown_month["account_id"].nunique(dropna=True)),
                "채널ID결측_영상수": int(unknown_month["account_id"].isna().sum()),
                "조회수_중앙값": float(unknown_month["view_count"].median()) if unknown_month["view_count"].notna().any() else np.nan,
                "조회수_유효영상수": int(unknown_month["view_count"].notna().sum()),
                "좋아요율_중앙값_pct": np.nan,
                "좋아요율_유효영상수": int(np.isfinite(unknown_month["like_rate"]).sum()),
                "댓글률_중앙값_pct": np.nan,
                "댓글률_유효영상수": int(np.isfinite(unknown_month["comment_rate"]).sum()),
            }
        )
    monthly = pd.DataFrame(month_rows)
    monthly.to_csv(OUT / "02_월별.csv", index=False, encoding="utf-8-sig")

    year_rows = []
    years = sorted(int(y) for y in work["year"].dropna().unique())
    for year in years:
        sub = work[work["year"] == year]
        year_rows.append(
            {
                "게시연도_KST": year,
                "기간구분": year_coverage(year),
                "영상수": int(len(sub)),
                "활동채널수": int(sub["account_id"].nunique(dropna=True)),
                "조회수_합계": float(sub["view_count"].sum(min_count=1)),
                "조회수_유효영상수": int(sub["view_count"].notna().sum()),
                "조회수_중앙값": float(sub["view_count"].median()) if sub["view_count"].notna().any() else np.nan,
                "좋아요율_중앙값_pct": float(np.nanmedian(sub["like_rate"])) if np.isfinite(sub["like_rate"]).any() else np.nan,
                "좋아요율_유효영상수": int(np.isfinite(sub["like_rate"]).sum()),
                "댓글률_중앙값_pct": float(np.nanmedian(sub["comment_rate"])) if np.isfinite(sub["comment_rate"]).any() else np.nan,
                "댓글률_유효영상수": int(np.isfinite(sub["comment_rate"]).sum()),
                "게시후_경과일_중앙값": float(sub["elapsed_days"].median()) if sub["elapsed_days"].notna().any() else np.nan,
                "일평균_누적조회수_중앙값": float(sub["views_per_elapsed_day"].median())
                if sub["views_per_elapsed_day"].notna().any()
                else np.nan,
                "일평균_누적조회수_유효영상수": int(sub["views_per_elapsed_day"].notna().sum()),
            }
        )
    yearly = pd.DataFrame(year_rows)
    yearly.to_csv(OUT / "02_연도별.csv", index=False, encoding="utf-8-sig")

    # ----- 길이 -----
    def duration_summary(frame: pd.DataFrame, year_label):
        rows = []
        total = len(frame)
        for label in BIN_ORDER:
            sub = frame[frame["duration_bin"] == label]
            like = rate_pair(sub, "like_count", "view_count")
            comment = rate_pair(sub, "comment_count", "view_count")
            rows.append(
                {
                    "게시연도_KST": year_label,
                    "길이구간": label,
                    "영상수": int(len(sub)),
                    "영상비중_pct": (len(sub) / total * 100) if total else np.nan,
                    "조회수_중앙값": float(sub["view_count"].median()) if sub["view_count"].notna().any() else np.nan,
                    "조회수_1사분위": float(sub["view_count"].quantile(0.25)) if sub["view_count"].notna().any() else np.nan,
                    "조회수_3사분위": float(sub["view_count"].quantile(0.75)) if sub["view_count"].notna().any() else np.nan,
                    "조회수_유효영상수": int(sub["view_count"].notna().sum()),
                    "좋아요율_중앙값_pct": like["영상별_중앙값_pct"],
                    "좋아요율_유효영상수": like["유효_영상수"],
                    "댓글률_중앙값_pct": comment["영상별_중앙값_pct"],
                    "댓글률_유효영상수": comment["유효_영상수"],
                }
            )
        return rows

    duration_rows = duration_summary(work, "전체")
    for year in years:
        duration_rows.extend(duration_summary(work[work["year"] == year], str(year)))
    duration_df = pd.DataFrame(duration_rows)
    duration_df.to_csv(OUT / "03_길이구간.csv", index=False, encoding="utf-8-sig")
    duration_all = duration_df[duration_df["게시연도_KST"] == "전체"].copy()
    duration_by_year = duration_df[duration_df["게시연도_KST"] != "전체"].copy()

    # 연도 구성이 길이 구간마다 다른지
    mix_rows = []
    for label in BIN_ORDER:
        sub = work[work["duration_bin"] == label]
        mix = {"길이구간": label, "영상수": int(len(sub))}
        for year in years:
            n = int((sub["year"] == year).sum())
            mix[f"{year}_영상수"] = n
            mix[f"{year}_비중_pct"] = (n / len(sub) * 100) if len(sub) else np.nan
        mix_rows.append(mix)
    pd.DataFrame(mix_rows).to_csv(OUT / "03_길이구간_연도구성.csv", index=False, encoding="utf-8-sig")

    # ----- 채널 -----
    known = work.dropna(subset=["account_id"])
    channel = (
        known.groupby("account_id", as_index=False)
        .agg(
            display_name=("display_name", "first"),
            영상수=("post_id", "nunique"),
            조회수_합계=("view_count", lambda s: float(s.sum(min_count=1)) if s.notna().any() else np.nan),
            조회수_유효영상수=("view_count", lambda s: int(s.notna().sum())),
            조회수_중앙값=("view_count", "median"),
            좋아요_합계=("like_count", lambda s: float(s.sum(min_count=1)) if s.notna().any() else np.nan),
            댓글수_합계=("comment_count", lambda s: float(s.sum(min_count=1)) if s.notna().any() else np.nan),
        )
    )
    video_counts = channel["영상수"]
    dist_bins = pd.cut(
        video_counts,
        bins=[0, 1, 4, 9, 29, 10**9],
        labels=["1편", "2–4편", "5–9편", "10–29편", "30편 이상"],
        right=True,
    )
    dist_rows = []
    for label in ["1편", "2–4편", "5–9편", "10–29편", "30편 이상"]:
        sub = channel[dist_bins == label]
        dist_rows.append(
            {
                "채널당_A영상수": label,
                "채널수": int(len(sub)),
                "채널비중_pct": len(sub) / len(channel) * 100 if len(channel) else np.nan,
                "영상수": int(sub["영상수"].sum()),
                "영상비중_pct": sub["영상수"].sum() / n_rows * 100,
            }
        )
    channel_dist = pd.DataFrame(dist_rows)
    channel_dist.to_csv(OUT / "04_채널당_영상수분포.csv", index=False, encoding="utf-8-sig")

    view_denom = float(work["view_count"].sum(min_count=1))
    top_videos = channel.sort_values(["영상수", "account_id"], ascending=[False, True]).head(10)
    top_views = channel.sort_values(["조회수_합계", "account_id"], ascending=[False, True]).head(10)
    top_videos.to_csv(OUT / "04_상위10_영상수.csv", index=False, encoding="utf-8-sig")
    top_views.to_csv(OUT / "04_상위10_조회수.csv", index=False, encoding="utf-8-sig")

    by_videos = channel.sort_values(["영상수", "account_id"], ascending=[False, True])
    by_views = channel.sort_values(["조회수_합계", "account_id"], ascending=[False, True])
    conc_rows = []
    for k in (1, 5, 10):
        vsub = by_videos.head(k)
        wsub = by_views.head(k)
        conc_rows.append(
            {
                "순위범위": f"상위 {k}개 채널",
                "기준": "A 영상 수",
                "영상수": int(vsub["영상수"].sum()),
                "영상_점유율_pct": vsub["영상수"].sum() / n_rows * 100,
                "조회수_합계": float(vsub["조회수_합계"].sum(min_count=1)),
                "조회수_점유율_pct": float(vsub["조회수_합계"].sum(min_count=1) / view_denom * 100),
                "분모_영상": "A 전체 영상 수. 채널 ID 결측 포함",
                "분모_조회수": "조회수가 있는 A 전체 영상의 조회수 합. 결측은 합계·분모에서 제외",
            }
        )
        conc_rows.append(
            {
                "순위범위": f"상위 {k}개 채널",
                "기준": "관측 조회수 합계",
                "영상수": int(wsub["영상수"].sum()),
                "영상_점유율_pct": wsub["영상수"].sum() / n_rows * 100,
                "조회수_합계": float(wsub["조회수_합계"].sum(min_count=1)),
                "조회수_점유율_pct": float(wsub["조회수_합계"].sum(min_count=1) / view_denom * 100),
                "분모_영상": "A 전체 영상 수. 채널 ID 결측 포함",
                "분모_조회수": "조회수가 있는 A 전체 영상의 조회수 합. 결측은 합계·분모에서 제외",
            }
        )
    missing_views = work.loc[work["account_id"].isna(), "view_count"]
    missing_view_sum = float(missing_views.sum(min_count=1)) if missing_views.notna().any() else np.nan
    conc_rows.append(
        {
            "순위범위": "채널 ID 결측",
            "기준": "채널로 합치지 않음",
            "영상수": id_missing,
            "영상_점유율_pct": id_missing / n_rows * 100 if n_rows else np.nan,
            "조회수_합계": missing_view_sum,
            "조회수_점유율_pct": (missing_view_sum / view_denom * 100) if pd.notna(missing_view_sum) else np.nan,
            "분모_영상": "A 전체 영상 수",
            "분모_조회수": "조회수가 모두 결측이면 조회수 점유율은 계산 불가. 이 영상들은 관측 조회수 분모에 들어가지 않음",
        }
    )
    conc = pd.DataFrame(conc_rows)
    conc.to_csv(OUT / "04_채널_점유율.csv", index=False, encoding="utf-8-sig")

    # ----- 성과 -----
    ranked = work.dropna(subset=["view_count"]).sort_values(
        ["view_count", "post_id"], ascending=[False, True]
    )
    n_ranked = len(ranked)
    share_rows = []
    for pct in (0.01, 0.10):
        k = max(1, int(np.ceil(n_ranked * pct)))
        top = ranked.iloc[:k]
        boundary = float(top["view_count"].iloc[-1])
        n_tie_total = int((ranked["view_count"] == boundary).sum())
        n_tie_outside = int(((ranked["view_count"] == boundary) & ~ranked.index.isin(top.index)).sum())
        share_rows.append(
            {
                "구간": f"상위 {pct:.0%}",
                "영상수": k,
                "경계_조회수": boundary,
                "경계값과_같은_영상수": n_tie_total,
                "경계_밖으로_잘린_동률": n_tie_outside,
                "조회수_합계": float(top["view_count"].sum()),
                "전체대비_점유율_pct": float(top["view_count"].sum() / view_denom * 100),
                "정렬": "조회수 내림차순, 동률이면 post_id 오름차순으로 k편만 포함",
            }
        )
    share_df = pd.DataFrame(share_rows)
    share_df.to_csv(OUT / "05_조회수_상위점유.csv", index=False, encoding="utf-8-sig")

    top20 = ranked.head(20).copy()
    top20_out = pd.DataFrame(
        {
            "순위": np.arange(1, len(top20) + 1),
            "post_id": top20["post_id"].values,
            "제목": top20["post_title"].values,
            "account_id": top20["account_id"].values,
            "채널": top20["display_name"].values,
            "게시일_KST": top20["created_kst"].dt.strftime("%Y-%m-%d").values,
            "길이_초": top20["duration_sec"].values,
            "duration": top20["duration"].values,
            "조회수": top20["view_count"].values,
            "좋아요수": top20["like_count"].values,
            "댓글수": top20["comment_count"].values,
        }
    )
    top20_out.to_csv(OUT / "05_조회수_상위20.csv", index=False, encoding="utf-8-sig")

    corr_rows = []
    for left, right, label in [
        ("view_count", "like_count", "조회수-좋아요수"),
        ("view_count", "comment_count", "조회수-댓글수"),
        ("like_count", "comment_count", "좋아요수-댓글수"),
    ]:
        mask = work[left].notna() & work[right].notna()
        corr_rows.append(
            {
                "관계": label,
                "계수": "Spearman",
                "상관계수": spearman(work.loc[mask, left], work.loc[mask, right]) if mask.any() else np.nan,
                "유효_영상수": int(mask.sum()),
                "해석범위": "함께 움직이는 정도. 원인으로 읽지 않음",
            }
        )
    corr_df = pd.DataFrame(corr_rows)
    corr_df.to_csv(OUT / "05_스피어만.csv", index=False, encoding="utf-8-sig")

    rate_rows = []
    for scope, frame in [("전체_계산가능", work), ("조회수_100이상", work[work["view_count"] >= 100])]:
        for numer, label in [("like_count", "좋아요율"), ("comment_count", "댓글률")]:
            stats = rate_pair(frame, numer, "view_count")
            rate_rows.append({"범위": scope, "지표": label, **stats})
    rate_df = pd.DataFrame(rate_rows)
    rate_df.to_csv(OUT / "05_반응률.csv", index=False, encoding="utf-8-sig")

    # 수집 시점 차이
    collected_dates = work["collected_kst"].dt.strftime("%Y-%m-%d")
    collect_summary = pd.DataFrame(
        [
            {"항목": "수집시각_고유값수", "값": int(work["collected_at"].nunique(dropna=True))},
            {"항목": "수집일_고유값수_KST", "값": int(collected_dates.nunique(dropna=True))},
            {"항목": "수집일_최솟값", "값": str(collected_dates.min())},
            {"항목": "수집일_최댓값", "값": str(collected_dates.max())},
            {"항목": "경과일_최솟값", "값": float(work["elapsed_days"].min())},
            {"항목": "경과일_중앙값", "값": float(work["elapsed_days"].median())},
            {"항목": "경과일_최댓값", "값": float(work["elapsed_days"].max())},
        ]
    )
    collect_summary.to_csv(OUT / "00_수집시점.csv", index=False, encoding="utf-8-sig")

    definitions = pd.DataFrame(
        [
            {"항목": "분석대상", "정의": "한국어 제목과 치이카와 내용 관련성 기준 A_우선포함 영상. 한국 발생 조회수나 한국인 시청자 행동이 아님."},
            {"항목": "영상수", "정의": "고유 post_id 수. 이 파일은 영상당 한 행."},
            {"항목": "채널수", "정의": "결측이 아닌 고유 account_id 수. 이름이 같아도 ID가 다르면 합치지 않음."},
            {"항목": "활동채널수", "정의": "해당 기간에 영상을 게시한, 결측이 아닌 고유 account_id 수."},
            {"항목": "영상길이", "정의": "ISO-8601 duration을 초로 변환. 실패·결측은 변환 불가·결측."},
            {"항목": "좋아요율", "정의": "like_count / view_count × 100. 조회수 결측·0 또는 좋아요 결측이면 계산 불가. 결측을 0으로 채우지 않음."},
            {"항목": "댓글률", "정의": "comment_count / view_count × 100. comment_count는 영상 메타데이터이며 수집 댓글 행 수가 아님."},
            {"항목": "게시후_경과일", "정의": "시간대가 명시된 collected_at - created_at. 둘 다 UTC로 맞춘 뒤 일 단위."},
            {"항목": "게시월연도", "정의": "created_at이 UTC(Z)이면 Asia/Seoul로 변환한 뒤 집계."},
            {"항목": "조회수_의미", "정의": "각 영상의 수집 시점 누적조회수. 해당 연도·월에 발생한 조회수가 아님."},
            {"항목": "일평균_누적조회수", "정의": "누적조회수 / 게시 후 경과일. 최근 조회 속도나 성장률이 아님."},
            {"항목": "채널_표시이름", "정의": NAME_RULE},
            {"항목": "점유율_분모", "정의": "영상 점유율은 A 전체 영상 수. 조회수 점유율은 조회수가 있는 영상 합계. 채널 ID 결측은 분모에 포함하고 한 채널로 묶지 않음."},
            {"항목": "입력파일", "정의": str(SRC)},
            {"항목": "원본수정", "정의": "하지 않음"},
        ]
    )
    definitions.to_csv(OUT / "00_지표정의.csv", index=False, encoding="utf-8-sig")

    # ----- 그래프 -----
    plot_months = monthly[monthly["게시월_KST"] != "시간대 불명"].copy()
    x = np.arange(len(plot_months))
    partial = plot_months["기간구분"].eq("일부").to_numpy()
    colors = np.where(partial, "#c47b2b", "#2f5d8c")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(x, plot_months["영상수"], color=colors, width=0.8)
    ax.set_xticks(x[::3])
    ax.set_xticklabels(plot_months["게시월_KST"].iloc[::3], rotation=90)
    style_ax(
        ax,
        "월별 A 영상 업로드 수\n"
        f"게시 시각 한국시간 · {plot_months['게시월_KST'].iloc[0]}–{plot_months['게시월_KST'].iloc[-1]} · "
        f"그래프 {int(plot_months['영상수'].sum()):,}편 · 게시 시각 결측 {int((~kst_ok).sum())}편 제외",
        "게시월 (한국시간)",
        "업로드 영상 수 (편)",
    )
    ax.bar([0], [0], color="#2f5d8c", label="달력월 전체 구간")
    ax.bar([0], [0], color="#c47b2b", label="일부 월 (첫 달·마지막 달)")
    ax.legend(frameon=False)
    foot(fig, "이 데이터 안에서 관찰된 A 영상 수. YouTube 전체 업로드 수가 아님. 일부 월과 전체 구간의 증감률은 비교하지 않음.", 0.28)
    save_fig(fig, "fig_월별_업로드수.png")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(x, plot_months["활동채널수"], color="#2f5d8c", marker="o", markersize=3, linewidth=1.4)
    ax.set_xticks(x[::3])
    ax.set_xticklabels(plot_months["게시월_KST"].iloc[::3], rotation=90)
    style_ax(
        ax,
        "월별 활동 채널 수\n"
        f"해당 월에 A 영상을 게시한 고유 account_id · 그래프 대상 게시 시각 있는 영상 {int(kst_ok.sum()):,}편 · "
        f"채널 ID 결측 {id_missing}편은 채널로 세지 않음",
        "게시월 (한국시간)",
        "활동 채널 수 (개)",
    )
    foot(
        fig,
        f"기간 {plot_months['게시월_KST'].iloc[0]}–{plot_months['게시월_KST'].iloc[-1]} 한국시간. 첫 달·마지막 달은 일부 기간.",
        0.28,
    )
    save_fig(fig, "fig_월별_활동채널수.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = duration_all["길이구간"].tolist()
    short = ["≤60초", "60–180초", "180–600초", "600–1,200초", ">1,200초", "변환 불가"]
    axes[0].barh(short[::-1], duration_all["영상비중_pct"].to_numpy()[::-1], color="#2f5d8c")
    style_ax(axes[0], f"길이 구간별 영상 비중\nn={n_rows:,}편", "영상 비중 (%)", "길이 구간")
    med = duration_all["조회수_중앙값"].to_numpy()
    axes[1].barh(short[::-1], med[::-1], color="#5b7f6a")
    style_ax(
        axes[1],
        "길이 구간별 수집 시점 누적조회수 중앙값\n길이가 조회수를 만들었다고 읽지 않음",
        "누적조회수 중앙값 (회)",
        "길이 구간",
    )
    fig.suptitle(
        f"A 영상 길이 구성과 성과 비교 · 게시 {min_kst.strftime('%Y-%m-%d')}–{max_kst.strftime('%Y-%m-%d')} 한국시간",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    fig.tight_layout()
    save_fig(fig, "fig_길이_비중과_조회수.png")

    year_labels = [str(y) for y in years]
    bin_plot = [b for b in BIN_ORDER if b != "변환 불가·결측"]
    palette = ["#2f5d8c", "#6f93b0", "#c47b2b", "#5b7f6a", "#8a6a9a"]
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(years))
    for color, label in zip(palette, bin_plot):
        vals = []
        for year in year_labels:
            row = duration_by_year[
                (duration_by_year["게시연도_KST"] == year) & (duration_by_year["길이구간"] == label)
            ]
            vals.append(float(row["영상비중_pct"].iloc[0]) if len(row) else 0.0)
        arr = np.array(vals)
        ax.bar(year_labels, arr, bottom=bottom, color=color, label=label, width=0.7)
        bottom += arr
    style_ax(
        ax,
        "게시 연도별 길이 구간 구성\n"
        f"각 연도 안에서의 비중 · 게시 시각이 있는 {int(kst_ok.sum()):,}편 · 시각 결측 {int((~kst_ok).sum())}편 제외",
        "게시 연도 (한국시간, 일부 연도는 연중 일부)",
        "해당 연도 영상 대비 비중 (%)",
    )
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
    foot(fig, "2022년과 2026년은 연중 일부만 관측됨. 구성 차이는 관찰이며 길이의 효과로 해석하지 않음.", 0.16)
    save_fig(fig, "fig_연도별_길이구성.png")

    positive_views = work.loc[work["view_count"] > 0, "view_count"]
    zero_views = int((work["view_count"] == 0).sum())
    null_views = int(work["view_count"].isna().sum())
    fig, ax = plt.subplots(figsize=(8, 4.8))
    logs = np.log10(positive_views)
    ax.hist(logs, bins=30, color="#2f5d8c", edgecolor="white")
    style_ax(
        ax,
        f"영상별 수집 시점 누적조회수 분포\nlog10(조회수) · 조회수>0 {len(positive_views):,}편 · 0값 {zero_views}편 · 결측 {null_views}편 제외",
        "log10(누적조회수)",
        "영상 수 (편)",
    )
    foot(fig, "0은 로그에 올릴 수 없어 히스토그램에서 제외하고 건수만 표시. 결측은 0으로 바꾸지 않음.", 0.16)
    save_fig(fig, "fig_조회수_분포.png")

    scatter = work[work["view_count"].notna() & work["like_count"].notna() & (work["view_count"] > 0)]
    zero_like = int((scatter["like_count"] == 0).sum())
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.scatter(
        scatter["view_count"],
        scatter["like_count"] + 1,
        s=12,
        alpha=0.35,
        c="#2f5d8c",
        linewidths=0,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    rho_like = float(corr_df.loc[corr_df["관계"] == "조회수-좋아요수", "상관계수"].iloc[0])
    style_ax(
        ax,
        f"누적조회수와 좋아요 수\nSpearman {rho_like:.2f} · 유효 {len(scatter):,}편 · 좋아요 0은 {zero_like}편이라 세로축은 좋아요+1",
        "누적조회수 (회, 로그)",
        "좋아요 수 + 1 (로그)",
    )
    foot(fig, "좋아요 결측은 제외. 같이 큰 경향이지 조회수가 좋아요를 만들었다고 읽지 않음.", 0.16)
    save_fig(fig, "fig_조회수_좋아요.png")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    show = top_views.iloc[::-1]
    ax.barh(show["display_name"].astype(str), show["조회수_합계"] / 10000, color="#2f5d8c")
    style_ax(
        ax,
        f"관측 조회수 합계 상위 10개 채널\nA 영상만의 합 · 분모는 조회수 있는 A 전체 {view_denom/10000:,.0f}만 회 · 채널 전체 성과가 아님",
        "A 영상 누적조회수 합계 (만 회)",
        "채널 표시 이름",
    )
    save_fig(fig, "fig_채널_조회수상위10.png")

    # 반응률 비교
    fig, ax = plt.subplots(figsize=(8, 4.8))
    plot_rate = rate_df.copy()
    cats = ["전체·좋아요", "전체·댓글", "100회 이상·좋아요", "100회 이상·댓글"]
    keys = [
        ("전체_계산가능", "좋아요율"),
        ("전체_계산가능", "댓글률"),
        ("조회수_100이상", "좋아요율"),
        ("조회수_100이상", "댓글률"),
    ]
    medians, aggregates, ns = [], [], []
    for scope, metric in keys:
        row = plot_rate[(plot_rate["범위"] == scope) & (plot_rate["지표"] == metric)].iloc[0]
        medians.append(row["영상별_중앙값_pct"])
        aggregates.append(row["합계비_pct"])
        ns.append(int(row["유효_영상수"]))
    xpos = np.arange(len(cats))
    ax.bar(xpos - 0.18, medians, width=0.36, color="#2f5d8c", label="영상별 중앙값")
    ax.bar(xpos + 0.18, aggregates, width=0.36, color="#c47b2b", label="합계 / 합계")
    ax.set_xticks(xpos)
    ax.set_xticklabels(
        [f"{name}\nn={n:,}" for name, n in zip(["좋아요율", "댓글률", "좋아요율", "댓글률"], ns)]
    )
    style_ax(
        ax,
        "반응률: 영상별 중앙값과 합계 비율\n왼쪽 두 쌍은 계산 가능한 전체, 오른쪽 두 쌍은 조회수 100회 이상",
        "범위",
        "비율 (%)",
    )
    ax.legend(frameon=False)
    foot(fig, "같은 색의 두 막대는 서로 다른 요약이다. 분자·분모가 모두 유효한 동일 영상만 사용. 반응률 순위를 인기 순위로 쓰지 않음.", 0.22)
    save_fig(fig, "fig_반응률_비교.png")

    # ----- 검증 -----
    checks = []

    def add_check(name, ok, detail):
        checks.append({"검증": name, "결과": "통과" if ok else "실패", "내용": detail})

    add_check("행수와_고유ID", n_rows == n_id and n_dup_ids == 0, f"행 {n_rows}, 고유 {n_id}, 중복 ID {n_dup_ids}")
    add_check("예상_6462", n_rows == EXPECTED_N, f"차이 {n_rows - EXPECTED_N}")
    add_check("final_class", set(work["final_class"].unique()) == {"A_우선포함"}, str(work["final_class"].unique().tolist()))
    add_check(
        "월별_영상수_합",
        int(monthly["영상수"].sum()) == n_rows,
        f"월별 합 {int(monthly['영상수'].sum())}",
    )
    add_check(
        "연도별_영상수_합",
        int(yearly["영상수"].sum()) == int(work["year"].notna().sum()),
        f"연도 합 {int(yearly['영상수'].sum())}, 연도값 있는 영상 {int(work['year'].notna().sum())}",
    )
    add_check(
        "길이구간_합",
        int(duration_all["영상수"].sum()) == n_rows,
        f"구간 합 {int(duration_all['영상수'].sum())}",
    )
    add_check(
        "채널분포_영상합",
        int(channel_dist["영상수"].sum()) + id_missing == n_rows,
        f"채널 분포 영상 {int(channel_dist['영상수'].sum())} + ID결측 {id_missing}",
    )
    add_check(
        "댓글행_중복합산_없음",
        n_rows == n_id,
        "입력은 영상 단위 파일이고 post_id 중복이 없으면 댓글 행으로 곱해지지 않음",
    )
    add_check(
        "반응률_동일집단",
        all(rate_df["유효_영상수"] + rate_df["계산불가_영상수"] >= rate_df["유효_영상수"]),
        "좋아요율·댓글률은 각 분자와 조회수가 모두 유효하고 조회수>0인 행만 사용",
    )
    add_check(
        "조회수_점유율_분모",
        abs(float(by_views["조회수_합계"].sum(min_count=1)) + (float(missing_views.sum(min_count=1)) if missing_views.notna().any() else 0) - view_denom)
        < 1,
        "채널별 합과 ID 결측 합이 전체 조회수 합과 일치",
    )
    pd.DataFrame(checks).to_csv(OUT / "00_검증.csv", index=False, encoding="utf-8-sig")

    summary = {
        "n_rows": n_rows,
        "n_id": n_id,
        "n_dup_ids": n_dup_ids,
        "n_channels": n_channels,
        "id_missing": id_missing,
        "name_missing": name_missing,
        "multi_name_channels": int(len(multi)),
        "min_kst": str(min_kst),
        "max_kst": str(max_kst),
        "collected_min": str(work["collected_kst"].min()),
        "collected_max": str(work["collected_kst"].max()),
        "n_collected_timestamps": int(work["collected_at"].nunique(dropna=True)),
        "n_collected_dates": int(collected_dates.nunique(dropna=True)),
        "view_sum": float(work["view_count"].sum(min_count=1)),
        "like_sum": None if work["like_count"].notna().sum() == 0 else float(work["like_count"].sum(min_count=1)),
        "comment_sum": float(work["comment_count"].sum(min_count=1)),
        "view_valid_n": view_valid_n,
        "like_valid_n": like_valid_n,
        "comment_valid_n": comment_valid_n,
        "duration_ok": int(work["duration_sec"].notna().sum()),
        "duration_bad": int(work["duration_sec"].isna().sum()),
        "elapsed_nonpositive": int((work["elapsed_days"].notna() & (work["elapsed_days"] <= 0)).sum()),
        "created_tz": work["created_tz_kind"].value_counts().to_dict(),
        "collected_tz": work["collected_tz_kind"].value_counts().to_dict(),
        "zero_views": zero_views,
        "null_views": null_views,
        "checks_failed": int((pd.DataFrame(checks)["결과"] == "실패").sum()),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    write_report(
        work=work,
        monthly=monthly,
        yearly=yearly,
        duration_all=duration_all,
        duration_by_year=duration_by_year,
        mix=pd.DataFrame(mix_rows),
        channel_dist=channel_dist,
        top_videos=top_videos,
        top_views=top_views,
        conc=conc,
        scale_metrics=scale_metrics,
        scale_card=scale_card,
        share_df=share_df,
        top20=top20_out,
        corr_df=corr_df,
        rate_df=rate_df,
        multi=multi,
        checks=pd.DataFrame(checks),
        summary=summary,
        ranked_n=n_ranked,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("FAILED", summary["checks_failed"])


def md_table(frame: pd.DataFrame, columns: list[str], formats: dict[str, str]) -> str:
    show = frame[columns].copy()
    for col, kind in formats.items():
        if kind == "int":
            show[col] = show[col].map(lambda v: fmt_int(v) if pd.notna(v) else "계산 불가")
        elif kind == "num1":
            show[col] = show[col].map(lambda v: fmt_num(v, 1) if pd.notna(v) else "계산 불가")
        elif kind == "num2":
            show[col] = show[col].map(lambda v: fmt_num(v, 2) if pd.notna(v) else "계산 불가")
        elif kind == "pct":
            show[col] = show[col].map(lambda v: fmt_pct(v) if pd.notna(v) else "계산 불가")
        else:
            show[col] = show[col].map(lambda v: "" if pd.isna(v) else str(v))
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for _, row in show.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in columns) + " |")
    return "\n".join(lines)


def write_report(**kw) -> None:
    s = kw["summary"]
    yearly = kw["yearly"]
    monthly = kw["monthly"]
    duration_all = kw["duration_all"]
    top_views = kw["top_views"]
    top_videos = kw["top_videos"]
    conc = kw["conc"]
    share_df = kw["share_df"]
    rate_df = kw["rate_df"]
    corr_df = kw["corr_df"]
    scale_metrics = kw["scale_metrics"]
    top20 = kw["top20"]
    channel_dist = kw["channel_dist"]
    checks = kw["checks"]
    multi = kw["multi"]

    def metric(name):
        return scale_metrics.loc[scale_metrics["지표"] == name].iloc[0]

    views = metric("조회수")
    likes = metric("좋아요수")
    comments = metric("댓글수")
    y2022 = yearly[yearly["게시연도_KST"] == 2022].iloc[0]
    y2023 = yearly[yearly["게시연도_KST"] == 2023].iloc[0]
    y2024 = yearly[yearly["게시연도_KST"] == 2024].iloc[0]
    y2025 = yearly[yearly["게시연도_KST"] == 2025].iloc[0]
    y2026 = yearly[yearly["게시연도_KST"] == 2026].iloc[0]
    top1_view = conc[(conc["순위범위"] == "상위 1개 채널") & (conc["기준"] == "관측 조회수 합계")].iloc[0]
    top10_view = conc[(conc["순위범위"] == "상위 10개 채널") & (conc["기준"] == "관측 조회수 합계")].iloc[0]
    top10_n = conc[(conc["순위범위"] == "상위 10개 채널") & (conc["기준"] == "A 영상 수")].iloc[0]
    share1 = share_df[share_df["구간"] == "상위 1%"].iloc[0]
    share10 = share_df[share_df["구간"] == "상위 10%"].iloc[0]
    like_all = rate_df[(rate_df["범위"] == "전체_계산가능") & (rate_df["지표"] == "좋아요율")].iloc[0]
    like_100 = rate_df[(rate_df["범위"] == "조회수_100이상") & (rate_df["지표"] == "좋아요율")].iloc[0]
    c_all = rate_df[(rate_df["범위"] == "전체_계산가능") & (rate_df["지표"] == "댓글률")].iloc[0]
    c_100 = rate_df[(rate_df["범위"] == "조회수_100이상") & (rate_df["지표"] == "댓글률")].iloc[0]
    rho_like = corr_df[corr_df["관계"] == "조회수-좋아요수"].iloc[0]
    rho_c = corr_df[corr_df["관계"] == "조회수-댓글수"].iloc[0]
    short = duration_all[duration_all["길이구간"] == "60초 이하"].iloc[0]
    long = duration_all[duration_all["길이구간"] == "1,200초 초과"].iloc[0]
    one_video_channels = channel_dist[channel_dist["채널당_A영상수"] == "1편"].iloc[0]
    partial_months = monthly.loc[monthly["기간구분"] == "일부", "게시월_KST"].tolist()
    peak = monthly.loc[monthly["영상수"].idxmax()]
    ch_peak = monthly.loc[monthly["활동채널수"].idxmax()]

    top20_show = top20.copy()
    top20_show["제목"] = top20_show["제목"].astype(str).str.replace("\n", " ", regex=False).str.slice(0, 40)
    top_views_show = top_views.copy()
    top_videos_show = top_videos.copy()

    lines = []
    a = lines.append
    a("# A 영상 1차 탐색: 규모·시기·길이·채널·성과")
    a("")
    a("분석 대상은 한국어 제목과 치이카와 내용 관련성을 기준으로 선별한 영상이다. 한국에서 발생한 조회수나 한국인 시청자의 행동을 측정한 결과가 아니다.")
    a("")
    a(f"입력은 `youtube_total_cleaning_classified_A.csv`이며 영상 {fmt_int(s['n_rows'])}편, 고유 `post_id` {fmt_int(s['n_id'])}개다. 댓글 연결 여부와 관계없이 A 전체를 영상 1행으로 집계했다. 조회수·좋아요·댓글 수는 각 영상을 수집한 시점의 누적값이다.")
    a("")
    a("## 핵심 발견")
    a("")
    a(f"1. A 영상은 {fmt_int(s['n_rows'])}편, 채널은 {fmt_int(s['n_channels'])}개다. 수집 시점 누적조회수 합계는 {fmt_int(s['view_sum'])}회이고, 영상별 중앙값은 {fmt_int(views['중앙값'])}회다. 합계와 중앙값의 차이가 커서 소수의 영상이 합계를 끌어올린다. 근거는 `01_규모_요약.csv`, `05_조회수_상위점유.csv`, `fig_조회수_분포.png`.")
    a(f"2. 조회수 상위 1%({fmt_int(share1['영상수'])}편)가 관측 조회수의 {fmt_pct(share1['전체대비_점유율_pct'])}를, 상위 10%({fmt_int(share10['영상수'])}편)가 {fmt_pct(share10['전체대비_점유율_pct'])}를 차지한다. 조회수 합계 상위 10개 채널의 점유율은 {fmt_pct(top10_view['조회수_점유율_pct'])}다. 근거는 `05_조회수_상위점유.csv`, `04_채널_점유율.csv`, `fig_채널_조회수상위10.png`.")
    a(f"3. 게시 시각이 있는 영상의 한국시간 범위는 {s['min_kst'][:10]}부터 {s['max_kst'][:10]}까지다. 업로드가 가장 많은 달은 {peak['게시월_KST']} ({fmt_int(peak['영상수'])}편, {peak['기간구분']})이고, 활동 채널이 가장 많은 달은 {ch_peak['게시월_KST']} ({fmt_int(ch_peak['활동채널수'])}개, {ch_peak['기간구분']})다. 2022년과 2026년, 그리고 {', '.join(partial_months)}은 일부 기간이라 완전한 해·달과 증감률을 비교하지 않는다. 근거는 `02_월별.csv`, `02_연도별.csv`, `fig_월별_업로드수.png`, `fig_월별_활동채널수.png`.")
    a(f"4. 60초 이하가 {fmt_int(short['영상수'])}편({fmt_pct(short['영상비중_pct'])})으로 가장 많고, 이 구간의 누적조회수 중앙값은 {fmt_int(short['조회수_중앙값'])}회다. 1,200초 초과는 {fmt_int(long['영상수'])}편({fmt_pct(long['영상비중_pct'])}), 중앙값 {fmt_int(long['조회수_중앙값'])}회다. 길이 구간의 게시 연도 구성이 다르므로 길이 차이를 성과의 원인으로 읽지 않는다. 근거는 `03_길이구간.csv`, `03_길이구간_연도구성.csv`, `fig_길이_비중과_조회수.png`.")
    a(f"5. 계산 가능한 영상에서 좋아요율의 중앙값은 {fmt_pct(like_all['영상별_중앙값_pct'])}이고, 같은 영상의 좋아요 합계/조회수 합계는 {fmt_pct(like_all['합계비_pct'])}다. 조회수 100회 이상만 보면 중앙값은 {fmt_pct(like_100['영상별_중앙값_pct'])}다. 조회수와 좋아요 수의 Spearman 계수는 {fmt_num(rho_like['상관계수'], 2)} (n={fmt_int(rho_like['유효_영상수'])})이다. 근거는 `05_반응률.csv`, `05_스피어만.csv`, `fig_반응률_비교.png`.")
    a("")
    a("## 1. 데이터 점검")
    a("")
    created_missing = int(s["created_tz"].get("결측", 0))
    a(f"행 수와 고유 `post_id`가 모두 {fmt_int(s['n_rows'])}로 예상 6,462편과 같다. 중복 ID가 없어 첫 행을 고르는 규칙은 쓰지 않았다. `final_class`는 모두 `A_우선포함`이다.")
    a("")
    a(f"게시 시각이 비어 있는 영상은 {fmt_int(created_missing)}편이다. 이 영상은 `post_id`, `full_title`, `duration`, `collected_at`은 있고, 채널·게시 시각·`post_title`·조회수·좋아요·댓글 수가 비어 있다. 영상 수에는 포함했다. 월 집계에서는 ‘시간대 불명’으로 따로 두었고, 연도 표와 조회수 합계에는 넣지 않았다.")
    a("")
    a(f"`created_at`이 있는 {fmt_int(s['n_rows'] - created_missing)}편은 모두 UTC(`Z`)다. 이 행만 한국시간으로 바꿔 월·연도를 집계했다. `collected_at`은 {fmt_int(s['n_rows'])}편 모두 `+09:00` 오프셋이다. 수집 시각 고유값은 {fmt_int(s['n_collected_timestamps'])}개, 수집일은 {s['collected_min'][:10]}부터 {s['collected_max'][:10]}까지 {fmt_int(s['n_collected_dates'])}일이다. 누적 지표의 기준 시각은 이 이틀 안에 있다.")
    a("")
    a(f"길이 문자열은 {fmt_int(s['duration_ok'])}편 변환에 성공했고, 실패·결측은 {fmt_int(s['duration_bad'])}편이다. `account_id` 결측은 {fmt_int(s['id_missing'])}편, `account_name` 결측은 {fmt_int(s['name_missing'])}편이다. 이름이 둘 이상인 채널 ID는 {fmt_int(s['multi_name_channels'])}개이며, 표시 이름은 ‘{NAME_RULE}’로 골랐다. 서로 다른 ID는 이름이 같아도 합치지 않았다.")
    a("")
    a(f"조회수 음수는 없고, 0은 {fmt_int(s['zero_views'])}편, 결측은 {fmt_int(s['null_views'])}편이다. 좋아요 결측은 {fmt_int(s['n_rows'] - s['like_valid_n'])}편이며 0으로 채우지 않았다. 게시 후 경과일이 0 이하인 영상은 {fmt_int(s['elapsed_nonpositive'])}편이다.")
    a("")
    a("세부 수치는 `00_데이터점검.csv`, `00_수치점검.csv`, `00_수집시점.csv`에 있다.")
    a("")
    a("## 2. 지표 정의와 처리 기준")
    a("")
    a("| 지표 | 정의 |")
    a("| --- | --- |")
    a("| 영상 수 | 고유 `post_id` |")
    a("| 채널 수 | 결측이 아닌 고유 `account_id` |")
    a("| 활동 채널 수 | 해당 기간에 영상을 게시한 고유 `account_id` |")
    a("| 영상 길이 | `duration`을 초로 변환 |")
    a("| 좋아요율 | `like_count / view_count × 100`. 조회수가 없거나 0이면 계산 불가 |")
    a("| 댓글률 | 영상 메타데이터의 `comment_count / view_count × 100` |")
    a("| 게시 후 경과일 | 시간대를 맞춘 `collected_at - created_at` |")
    a("| 일평균 누적조회수 | 누적조회수 / 게시 후 경과일. 최근 속도가 아님 |")
    a("")
    a("결측은 0으로 두지 않았다. 합계는 값이 있는 영상만 더했고, 유효 영상 수를 같이 적었다. 연도별 조회수는 그 해에 발생한 조회수가 아니라, 그 해에 게시된 영상의 수집 시점 누적조회수다.")
    a("")
    a("## 3. 규모")
    a("")
    a("| 항목 | 값 | 유효 영상 수 |")
    a("| --- | --- | --- |")
    a(f"| 영상 수 | {fmt_int(s['n_rows'])}편 | {fmt_int(s['n_rows'])} |")
    a(f"| 채널 수 | {fmt_int(s['n_channels'])}개 | {fmt_int(s['n_rows'] - s['id_missing'])} |")
    a(f"| 채널 ID 결측 영상 | {fmt_int(s['id_missing'])}편 | {fmt_int(s['n_rows'])} |")
    a(f"| 게시 기간 (한국시간) | {s['min_kst'][:10]} – {s['max_kst'][:10]} | {fmt_int(s['n_rows'] - int(s['created_tz'].get('결측', 0)))} |")
    a(f"| 수집 기간 (한국시간) | {s['collected_min'][:10]} – {s['collected_max'][:10]} | {fmt_int(s['n_rows'])} |")
    a(f"| 조회수 합계 | {fmt_int(s['view_sum'])}회 | {fmt_int(s['view_valid_n'])} |")
    a(f"| 좋아요 합계 | {fmt_int(s['like_sum'])} | {fmt_int(s['like_valid_n'])} |")
    a(f"| 댓글 수 합계 | {fmt_int(s['comment_sum'])} | {fmt_int(s['comment_valid_n'])} |")
    a("")
    a("합계는 값이 있는 영상의 합이다.")
    a("")
    a(md_table(
        scale_metrics[scale_metrics["지표"].isin(["조회수", "좋아요수", "댓글수"])],
        ["지표", "유효_영상수", "결측_영상수", "1사분위", "중앙값", "3사분위", "90백분위"],
        {"유효_영상수": "int", "결측_영상수": "int", "1사분위": "num1", "중앙값": "num1", "3사분위": "num1", "90백분위": "num1"},
    ))
    a("")
    a(f"조회수 중앙값 {fmt_int(views['중앙값'])}회는 합계를 영상 수로 나눈 평균과 다르다. 3사분위는 {fmt_int(views['3사분위'])}회, 90백분위는 {fmt_int(views['90백분위'])}회, 최댓값은 {fmt_int(views['최댓값'])}회다. 좋아요 중앙값은 {fmt_int(likes['중앙값'])}, 댓글 수 중앙값은 {fmt_int(comments['중앙값'])}다. 좋아요는 결측 {fmt_int(likes['결측_영상수'])}편을 제외한 분포다.")
    a("")
    a("## 4. 시기")
    a("")
    a("월별 업로드 수와 활동 채널 수는 `fig_월별_업로드수.png`, `fig_월별_활동채널수.png`에 있다. 주황 막대는 관측이 달력월을 다 덮지 않는 일부 월이다.")
    a("")
    a(md_table(
        yearly,
        ["게시연도_KST", "기간구분", "영상수", "활동채널수", "조회수_합계", "조회수_중앙값", "게시후_경과일_중앙값", "일평균_누적조회수_중앙값"],
        {
            "영상수": "int",
            "활동채널수": "int",
            "조회수_합계": "int",
            "조회수_중앙값": "num1",
            "게시후_경과일_중앙값": "num1",
            "일평균_누적조회수_중앙값": "num1",
        },
    ))
    a("")
    a(f"2023–2025년은 게시 관측 범위가 해당 연도의 1월 1일부터 12월 31일까지를 덮는다. 2022년은 {s['min_kst'][:10]}부터, 2026년은 {s['max_kst'][:10]}까지다. 그래서 2022년 {fmt_int(y2022['영상수'])}편, 2026년 {fmt_int(y2026['영상수'])}편을 2023년 {fmt_int(y2023['영상수'])}편, 2024년 {fmt_int(y2024['영상수'])}편, 2025년 {fmt_int(y2025['영상수'])}편과 증감률로 비교하지 않는다. 게시 시각이 없는 {fmt_int(int(s['created_tz'].get('결측', 0)))}편은 이 표에 없다.")
    a("")
    a(f"2026년에 게시된 영상의 수집 시점 누적조회수 합계는 {fmt_int(y2026['조회수_합계'])}회다. 이것은 2026년에 발생한 조회수가 아니라, 2026년에 게시된 영상이 수집 시점까지 모은 조회수다. 2026년 관측은 {s['max_kst'][:10]}에서 끝난다.")
    oct = monthly[(monthly["게시월_KST"] == "2026-10")]
    if len(oct):
        a(
            f"2026-10은 {s['max_kst'][:10]}까지의 일부 월이고 업로드 {fmt_int(oct.iloc[0]['영상수'])}편으로 관측 월 중 가장 많다. "
            f"이 달 영상의 수집 시점 누적조회수 중앙값은 {fmt_int(oct.iloc[0]['조회수_중앙값'])}회다. "
            "수집일이 10월 26–27일이라 이 달 영상은 게시 직후에 관측된 누적값이다. 월별 중앙값 차이를 인기 변화로 단정하지 않는다."
        )
    a("")
    a(f"연도 열의 조회수는 그 해에 게시된 영상의 수집 시점 누적조회수다. 2022년 게시 영상의 중앙 경과일은 {fmt_num(y2022['게시후_경과일_중앙값'], 0)}일, 2026년은 {fmt_num(y2026['게시후_경과일_중앙값'], 0)}일이다. 오래된 영상의 누적조회수가 더 크거나 작다고 해서 인기가 늘거나 줄었다고 단정하지 않는다. 일평균 누적조회수는 누적값을 경과일로 나눈 보조 지표이며 최근 조회 속도가 아니다.")
    a("")
    a("월별 전체 수치는 `02_월별.csv`에 있다. 수집 범위 안에서 본 업로드 수와 활동 채널 수의 변화로만 읽는다.")
    a("")
    a("## 5. 길이")
    a("")
    a("60초 이하는 Shorts로 확정하지 않았다. 길이만으로 형식을 나누지 않는다.")
    a("")
    a(md_table(
        duration_all,
        ["길이구간", "영상수", "영상비중_pct", "조회수_중앙값", "조회수_1사분위", "조회수_3사분위", "조회수_유효영상수", "좋아요율_중앙값_pct", "좋아요율_유효영상수", "댓글률_중앙값_pct", "댓글률_유효영상수"],
        {
            "영상수": "int",
            "영상비중_pct": "pct",
            "조회수_중앙값": "num1",
            "조회수_1사분위": "num1",
            "조회수_3사분위": "num1",
            "조회수_유효영상수": "int",
            "좋아요율_중앙값_pct": "pct",
            "좋아요율_유효영상수": "int",
            "댓글률_중앙값_pct": "pct",
            "댓글률_유효영상수": "int",
        },
    ))
    a("")
    short_by_year = []
    for year in [2022, 2023, 2024, 2025, 2026]:
        row = kw["duration_by_year"]
        sub = row[(row["게시연도_KST"] == str(year)) & (row["길이구간"] == "60초 이하")]
        if len(sub):
            short_by_year.append(f"{year}년 {fmt_pct(sub.iloc[0]['영상비중_pct'])}")
    a("같은 게시 연도 안에서 60초 이하가 차지하는 비중은 " + ", ".join(short_by_year) + "다. 2022년과 2026년은 일부 연도다. 전체 기간의 길이별 중앙값에는 이 구성 차이가 섞여 있으므로, 길이 차이를 성과의 원인으로 읽지 않는다. 연도별 수치는 `03_길이구간.csv`, 구성 그래프는 `fig_연도별_길이구성.png`에 있다.")
    a("")
    a("## 6. 채널")
    a("")
    a(f"집계 키는 `account_id`다. 표시 이름이 여러 개인 채널은 위 규칙으로 하나만 골랐고, 이번 파일에서는 그런 채널이 {fmt_int(s['multi_name_channels'])}개다. 채널 ID가 없는 {fmt_int(s['id_missing'])}편은 한 채널로 묶지 않았다. 이 {fmt_int(s['id_missing'])}편은 조회수도 비어 있어 조회수 합계와 조회수 점유율은 계산 불가다. 아래 성과는 데이터에 포함된 A 영상의 성과이지 채널이 올린 전체 영상의 성과가 아니다.")
    a("")
    a("채널당 A 영상 수:")
    a("")
    a(md_table(
        channel_dist,
        ["채널당_A영상수", "채널수", "채널비중_pct", "영상수", "영상비중_pct"],
        {"채널수": "int", "채널비중_pct": "pct", "영상수": "int", "영상비중_pct": "pct"},
    ))
    a("")
    a(f"채널 {fmt_int(one_video_channels['채널수'])}개({fmt_pct(one_video_channels['채널비중_pct'])})는 A 영상이 1편뿐이다.")
    a("")
    a("영상 수 상위 10개 채널:")
    a("")
    a(md_table(
        top_videos_show,
        ["display_name", "account_id", "영상수", "조회수_합계", "조회수_중앙값", "조회수_유효영상수"],
        {"영상수": "int", "조회수_합계": "int", "조회수_중앙값": "num1", "조회수_유효영상수": "int"},
    ))
    a("")
    a("관측 조회수 합계 상위 10개 채널:")
    a("")
    a(md_table(
        top_views_show,
        ["display_name", "account_id", "영상수", "조회수_합계", "조회수_중앙값", "조회수_유효영상수"],
        {"영상수": "int", "조회수_합계": "int", "조회수_중앙값": "num1", "조회수_유효영상수": "int"},
    ))
    a("")
    a("점유율의 영상 분모는 A 전체 영상 수이고, 조회수 분모는 조회수가 있는 영상의 합계다. 상위 5·10은 상위 1을 포함한다.")
    a("")
    a(md_table(
        conc,
        ["순위범위", "기준", "영상수", "영상_점유율_pct", "조회수_합계", "조회수_점유율_pct"],
        {"영상수": "int", "영상_점유율_pct": "pct", "조회수_합계": "int", "조회수_점유율_pct": "pct"},
    ))
    a("")
    a(f"영상 수 기준 상위 10개 채널은 영상의 {fmt_pct(top10_n['영상_점유율_pct'])}를 게시했다. 조회수 기준 상위 1개 채널은 관측 조회수의 {fmt_pct(top1_view['조회수_점유율_pct'])}다. 복수 채널명 목록은 `04_채널명_복수.csv` ({fmt_int(len(multi))}개 채널)에 있다.")
    a("")
    a("## 7. 성과")
    a("")
    a(f"조회수 분포는 오른쪽으로 길게 치우쳐 있다. `fig_조회수_분포.png`는 log10(조회수)이며, 조회수 0인 {fmt_int(s['zero_views'])}편과 결측 {fmt_int(s['null_views'])}편은 막대에 넣지 않고 건수만 적었다.")
    a("")
    a(md_table(
        scale_metrics[scale_metrics["지표"].isin(["조회수", "좋아요수", "댓글수", "좋아요율_pct", "댓글률_pct"])],
        ["지표", "유효_영상수", "1사분위", "중앙값", "3사분위", "90백분위", "최댓값"],
        {"유효_영상수": "int", "1사분위": "num2", "중앙값": "num2", "3사분위": "num2", "90백분위": "num2", "최댓값": "num2"},
    ))
    a("")
    a(md_table(
        share_df,
        ["구간", "영상수", "경계_조회수", "경계_밖으로_잘린_동률", "조회수_합계", "전체대비_점유율_pct"],
        {"영상수": "int", "경계_조회수": "int", "경계_밖으로_잘린_동률": "int", "조회수_합계": "int", "전체대비_점유율_pct": "pct"},
    ))
    a("")
    a("순위는 조회수 내림차순이고, 동률이면 `post_id` 오름차순으로 잘랐다. 경계 밖으로 잘린 동률이 0이면 잘린 자리에 같은 조회수가 더 없다.")
    a("")
    a("조회수 상위 20개 영상:")
    a("")
    a(md_table(
        top20_show,
        ["순위", "post_id", "제목", "채널", "게시일_KST", "길이_초", "조회수", "좋아요수", "댓글수"],
        {"순위": "int", "길이_초": "num1", "조회수": "int", "좋아요수": "int", "댓글수": "int"},
    ))
    a("")
    a("제목은 보고서에서 40자까지만 보였다. 전체 제목은 `05_조회수_상위20.csv`에 있다.")
    a("")
    a(md_table(
        corr_df,
        ["관계", "계수", "상관계수", "유효_영상수"],
        {"상관계수": "num2", "유효_영상수": "int"},
    ))
    a("")
    a(f"조회수가 큰 영상일수록 좋아요 수와 댓글 수도 큰 편이지만(Spearman {fmt_num(rho_like['상관계수'], 2)}, {fmt_num(rho_c['상관계수'], 2)}), 이것은 함께 움직이는 정도다. 한 지표가 다른 지표의 원인은 아니다. 산점도는 `fig_조회수_좋아요.png`이고, 좋아요 0을 로그 축에 올리기 위해 세로축만 좋아요+1을 썼다. 상관계수 계산에는 1을 더하지 않았다.")
    a("")
    a("반응률은 두 가지를 나눠 적는다. 영상별 중앙값은 영상 하나의 비율을 고르게 보고, 합계 비율은 같은 유효 집단의 분자 합을 분모 합으로 나눈 값이다.")
    a("")
    a(md_table(
        rate_df,
        ["범위", "지표", "유효_영상수", "계산불가_영상수", "영상별_중앙값_pct", "합계비_pct", "분자합", "분모합"],
        {
            "유효_영상수": "int",
            "계산불가_영상수": "int",
            "영상별_중앙값_pct": "pct",
            "합계비_pct": "pct",
            "분자합": "int",
            "분모합": "int",
        },
    ))
    a("")
    a(f"전체 계산 가능 영상의 댓글률 중앙값은 {fmt_pct(c_all['영상별_중앙값_pct'])}, 합계 비율은 {fmt_pct(c_all['합계비_pct'])}다. 조회수 100회 이상에서는 댓글률 중앙값이 {fmt_pct(c_100['영상별_중앙값_pct'])}다. 조회수가 적은 영상의 비율이 커질 수 있어 두 범위를 같이 본다. 반응률이 높다는 이유만으로 인기 순위를 매기지 않는다. 그래프는 `fig_반응률_비교.png`다.")
    a("")
    a("## 8. 한계")
    a("")
    a("- 선별 기준은 한국어 제목과 치이카와 내용 관련성이다. 시청 국가, 시청자 국적, 한국에서 발생한 조회수로 읽지 않는다.")
    a("- 조회수·좋아요·댓글 수는 수집 시점의 누적값이고, 수집일이 영상마다 다를 수 있다. 게시 후 노출 기간도 다르다.")
    a("- 2022년 첫 구간과 2026년 마지막 구간은 일부 기간이다. 완전한 연도·월과 증감률을 직접 비교하지 않았다.")
    a("- 이 파일에 없는 영상, 댓글이 수집되지 않은 영상, 채널의 A 밖 영상은 채널 성과에 들어 있지 않다.")
    a("- 길이 구간은 형식의 대리지표가 아니다. Shorts 여부는 확인하지 않았다.")
    a("- 콘텐츠 유형, 캐릭터, 댓글 내용은 이번 단계에서 분류하지 않았다.")
    a("")
    a("## 9. 검증")
    a("")
    a(md_table(checks, ["검증", "결과", "내용"], {}))
    a("")
    a("길이 구간 합과 월별 합은 전체 6,462편과 같다. 월별 합에는 게시 시각이 없는 8편이 ‘시간대 불명’으로 들어 있다. 연도별 합은 게시 시각이 있는 6,454편과 같다. 입력은 영상 단위 파일이고 `post_id` 중복이 없어 댓글 행 수만큼 지표가 곱해지지 않았다. 채널 ID 결측 8편은 채널 분포에 넣지 않고 점유율 표의 별도 행으로 두었다. 반응률의 분자와 분모는 둘 다 유효하고 조회수가 0보다 큰 같은 영상에서 계산했다.")
    a("")
    a("## 저장된 파일")
    a("")
    a("- 보고서: `A_1차탐색_보고서.md`")
    a("- 요약 CSV: `00_` 점검·정의·검증, `01_` 규모, `02_` 시기, `03_` 길이, `04_` 채널, `05_` 성과")
    a("- 그래프: `fig_월별_업로드수.png`, `fig_월별_활동채널수.png`, `fig_길이_비중과_조회수.png`, `fig_연도별_길이구성.png`, `fig_조회수_분포.png`, `fig_조회수_좋아요.png`, `fig_채널_조회수상위10.png`, `fig_반응률_비교.png`")
    a("")
    (OUT / "A_1차탐색_보고서.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
