# -*- coding: utf-8 -*-
"""A 영상 기존 결과 재검증, 2026-10 점검, 채널 제외 비교, 댓글 집중도, 후속 기준서.

원본 CSV는 읽기만 한다. 실행:
  C:\\Users\\user\\anaconda3\\python.exe verify_A_followup_v1.py
필요 패키지: pandas, numpy, matplotlib
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube")
SRC_A = ROOT / r"1. videos\02. cleaning\2. 제목분류\youtube_total_cleaning_classified_A.csv"
SRC_C = ROOT / r"1. videos\03. 분석용테이블\youtube_total_cleaning_classified_A_comments.csv"
SRC_REMOVE = ROOT / r"2. comments\5. youtube_comments_(2022-2026)_modify_2(remove).csv"
STATUS_DIR = ROOT / r"2. comments\raw"
OUT = Path(__file__).resolve().parent

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
SMALL_N = 30


def parse_duration_seconds(value) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().upper()
    match = DUR_RE.fullmatch(text)
    if not match or not any(match.groupdict().values()):
        return np.nan
    parts = match.groupdict()
    return (
        int(parts["days"] or 0) * 86400
        + int(parts["hours"] or 0) * 3600
        + int(parts["minutes"] or 0) * 60
        + float(parts["seconds"] or 0)
    )


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
    kind = pd.Series("시간대 없음", index=series.index)
    kind.loc[series.notna() & text.str.endswith("Z")] = "UTC(Z)"
    kind.loc[series.notna() & text.str.contains(r"[+-]\d{2}:\d{2}$", regex=True)] = "명시적 오프셋"
    kind.loc[series.isna() | text.eq("") | text.str.lower().eq("nan")] = "결측"
    return kind


def spearman(a: pd.Series, b: pd.Series) -> float:
    if len(a) < 2:
        return np.nan
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


def top_k_share(frame: pd.DataFrame, value_col: str, ratio: float, id_col: str) -> dict:
    valid = frame.dropna(subset=[value_col]).sort_values([value_col, id_col], ascending=[False, True])
    n = len(valid)
    total = float(valid[value_col].sum()) if n else np.nan
    k = max(1, int(np.ceil(n * ratio))) if n else 0
    if k == 0:
        return {"N": 0, "k": 0, "경계값": np.nan, "동점_전체": 0, "경계밖_동점": 0,
                "엄격_합": np.nan, "엄격_점유": np.nan, "동점포함_수": 0, "동점포함_합": np.nan, "동점포함_점유": np.nan}
    chosen = valid.iloc[:k]
    boundary = float(chosen[value_col].iloc[-1])
    tied = valid[valid[value_col] == boundary]
    outside = int((~valid.index.isin(chosen.index) & (valid[value_col] == boundary)).sum())
    expanded = valid[valid[value_col] >= boundary]
    strict_sum = float(chosen[value_col].sum())
    expanded_sum = float(expanded[value_col].sum())
    return {
        "N": n,
        "k": k,
        "경계값": boundary,
        "동점_전체": int(len(tied)),
        "경계밖_동점": outside,
        "엄격_합": strict_sum,
        "엄격_점유": strict_sum / total * 100 if total else np.nan,
        "동점포함_수": int(len(expanded)),
        "동점포함_합": expanded_sum,
        "동점포함_점유": expanded_sum / total * 100 if total else np.nan,
    }


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def style_ax(ax, title, xlabel, ylabel) -> None:
    ax.set_title(title, loc="left", fontsize=11, pad=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.45)


def quartile_row(series: pd.Series) -> dict:
    valid = series.dropna()
    if valid.empty:
        return {"유효수": 0, "최솟값": np.nan, "Q1": np.nan, "중앙값": np.nan, "Q3": np.nan, "최댓값": np.nan, "합계": np.nan}
    q = valid.quantile([0.25, 0.5, 0.75])
    return {
        "유효수": int(len(valid)),
        "최솟값": float(valid.min()),
        "Q1": float(q.loc[0.25]),
        "중앙값": float(q.loc[0.5]),
        "Q3": float(q.loc[0.75]),
        "최댓값": float(valid.max()),
        "합계": float(valid.sum()),
    }


def prepare_videos(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    qc_rows = []
    n = len(raw)
    dup_rows = int(raw["post_id"].duplicated(keep=False).sum())
    dup_ids = int(raw.loc[raw["post_id"].duplicated(keep=False), "post_id"].nunique()) if dup_rows else 0
    conflicts = []
    if dup_ids:
        for post_id, group in raw.loc[raw["post_id"].duplicated(keep=False)].groupby("post_id"):
            varying = [c for c in raw.columns if group[c].astype(str).nunique(dropna=False) > 1]
            conflicts.append({"post_id": post_id, "행수": len(group), "값이_다른_컬럼": ", ".join(varying)})
    work = raw.copy()
    work["created_tz_kind"] = tz_kind(work["created_at"])
    work["collected_tz_kind"] = tz_kind(work["collected_at"])
    work["created_utc"] = pd.to_datetime(work["created_at"], utc=True, errors="coerce")
    work["collected_utc"] = pd.to_datetime(work["collected_at"], utc=True, errors="coerce")
    created_ok = work["created_tz_kind"].isin(["UTC(Z)", "명시적 오프셋"]) & work["created_utc"].notna()
    collected_ok = work["collected_tz_kind"].isin(["UTC(Z)", "명시적 오프셋"]) & work["collected_utc"].notna()
    work["created_kst"] = work["created_utc"].dt.tz_convert("Asia/Seoul")
    work.loc[~created_ok, "created_kst"] = pd.NaT
    work["collected_kst"] = work["collected_utc"].dt.tz_convert("Asia/Seoul")
    work.loc[~collected_ok, "collected_kst"] = pd.NaT
    work["year"] = work["created_kst"].dt.year
    work["month"] = work["created_kst"].dt.month
    work["year_month"] = work["created_kst"].dt.strftime("%Y-%m")
    work["utc_year"] = work["created_utc"].dt.year
    work["utc_month"] = work["created_utc"].dt.month
    for col in ["view_count", "like_count", "comment_count"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work["duration_sec"] = work["duration"].map(parse_duration_seconds)
    work["duration_bin"] = work["duration_sec"].map(duration_bin)
    work["elapsed_days"] = (work["collected_utc"] - work["created_utc"]).dt.total_seconds() / 86400
    work.loc[~(created_ok & collected_ok), "elapsed_days"] = np.nan
    work["like_rate"] = np.where(
        work["like_count"].notna() & work["view_count"].notna() & (work["view_count"] > 0),
        work["like_count"] / work["view_count"] * 100,
        np.nan,
    )
    work["comment_rate"] = np.where(
        work["comment_count"].notna() & work["view_count"].notna() & (work["view_count"] > 0),
        work["comment_count"] / work["view_count"] * 100,
        np.nan,
    )
    qc = {
        "행수": n,
        "고유_post_id": int(work["post_id"].nunique(dropna=False)),
        "post_id_결측": int(work["post_id"].isna().sum()),
        "중복_post_id수": dup_ids,
        "중복_행수": dup_rows,
        "final_class_값": " | ".join(sorted(work["final_class"].dropna().astype(str).unique())),
        "final_class_결측": int(work["final_class"].isna().sum()),
        "A_우선포함": int((work["final_class"] == "A_우선포함").sum()),
        "account_id_결측": int(work["account_id"].isna().sum()),
        "account_name_결측": int(work["account_name"].isna().sum()),
        "created_UTC(Z)": int((work["created_tz_kind"] == "UTC(Z)").sum()),
        "created_결측": int((work["created_tz_kind"] == "결측").sum()),
        "created_파싱실패": int(((work["created_tz_kind"] != "결측") & work["created_utc"].isna()).sum()),
        "collected_오프셋": int((work["collected_tz_kind"] == "명시적 오프셋").sum()),
        "collected_결측": int((work["collected_tz_kind"] == "결측").sum()),
        "duration_성공": int(work["duration_sec"].notna().sum()),
        "duration_실패": int(work["duration_sec"].isna().sum()),
        "view_음수": int((work["view_count"] < 0).sum()),
        "view_0": int((work["view_count"] == 0).sum()),
        "view_결측": int(work["view_count"].isna().sum()),
        "like_음수": int((work["like_count"] < 0).sum()),
        "like_결측": int(work["like_count"].isna().sum()),
        "comment_음수": int((work["comment_count"] < 0).sum()),
        "comment_결측": int(work["comment_count"].isna().sum()),
        "경과_0이하": int((work["elapsed_days"].notna() & (work["elapsed_days"] <= 0)).sum()),
        "게시가_수집보다_늦음": int((work["elapsed_days"].notna() & (work["elapsed_days"] < 0)).sum()),
        "수치변환_소수부_있는_조회수": int(((work["view_count"].dropna() % 1) != 0).sum()),
    }
    qc_rows.append(qc)
    if conflicts:
        pd.DataFrame(conflicts).to_csv(OUT / "00_영상_중복ID충돌.csv", index=False, encoding="utf-8-sig")
    return work, pd.DataFrame(qc_rows)


def load_status() -> pd.DataFrame:
    frames = []
    for path in sorted(STATUS_DIR.glob("youtube_comment_status_*.csv")):
        part = pd.read_csv(path, encoding="utf-8-sig")
        part["status_file"] = path.name
        frames.append(part)
    status = pd.concat(frames, ignore_index=True)
    status["collected_count"] = pd.to_numeric(status["collected_count"], errors="coerce")
    return status


def classify_link(row) -> str:
    if row["댓글연결"]:
        return "댓글 연결"
    status = "" if pd.isna(row["status"]) else str(row["status"])
    error = "" if pd.isna(row["error_reason"]) else str(row["error_reason"])
    count = row["status_collected_count"]
    if pd.isna(row["status"]) and pd.isna(count):
        return "댓글 미연결·원인 미확인"
    blob = f"{status} {error}".lower()
    if "commentsdisabled" in blob or status == "comments_disabled":
        return "댓글 비활성화"
    if "videonotfound" in blob or status in {"unavailable", "video_not_found"}:
        return "영상 사용 불가"
    if status == "complete" and count == 0:
        return "수집 완료·댓글 0건"
    if pd.notna(count) and count > 0:
        return "상태에는 수집 댓글이 있으나 분석 테이블에 없음"
    return "댓글 미연결·원인 미확인"


def channel_table(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.dropna(subset=["account_id"])
    rows = []
    for account_id, group in known.groupby("account_id", sort=False):
        names = group["account_name"].dropna()
        if names.empty:
            display = "(이름 결측)"
        else:
            counts = names.value_counts()
            top = counts[counts == counts.max()].index.tolist()
            if len(top) == 1:
                display = top[0]
            else:
                display = group.assign(_n=group["account_name"].fillna("")).sort_values(
                    ["created_kst", "post_id"], ascending=[False, True]
                )["account_name"].dropna().iloc[0]
        rows.append(
            {
                "account_id": account_id,
                "display_name": display,
                "n_names": int(group["account_name"].nunique(dropna=True)),
                "영상수": int(group["post_id"].nunique()),
                "조회수_합계": float(group["view_count"].sum(min_count=1)) if group["view_count"].notna().any() else np.nan,
                "조회수_유효": int(group["view_count"].notna().sum()),
                "조회수_중앙값": float(group["view_count"].median()) if group["view_count"].notna().any() else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["조회수_합계", "account_id"], ascending=[False, True], na_position="last")


def group_profile(frame: pd.DataFrame, label: str, n_all_channels_base: pd.DataFrame) -> dict:
    views = quartile_row(frame["view_count"])
    like_mask = frame["like_count"].notna() & frame["view_count"].notna() & (frame["view_count"] > 0)
    comment_mask = frame["comment_count"].notna() & frame["view_count"].notna() & (frame["view_count"] > 0)
    like = frame.loc[like_mask, "like_rate"]
    comment = frame.loc[comment_mask, "comment_rate"]
    return {
        "집단": label,
        "영상수": int(len(frame)),
        "채널수": int(frame["account_id"].nunique(dropna=True)),
        "채널ID결측": int(frame["account_id"].isna().sum()),
        "조회수_유효": views["유효수"],
        "조회수_결측": int(frame["view_count"].isna().sum()),
        "조회수_Q1": views["Q1"],
        "조회수_중앙값": views["중앙값"],
        "조회수_Q3": views["Q3"],
        "조회수_합계": views["합계"],
        "좋아요율_중앙값": float(like.median()) if len(like) else np.nan,
        "좋아요율_유효": int(like_mask.sum()),
        "좋아요_합계비": float(frame.loc[like_mask, "like_count"].sum() / frame.loc[like_mask, "view_count"].sum() * 100) if like_mask.any() else np.nan,
        "댓글률_중앙값": float(comment.median()) if len(comment) else np.nan,
        "댓글률_유효": int(comment_mask.sum()),
        "댓글_합계비": float(frame.loc[comment_mask, "comment_count"].sum() / frame.loc[comment_mask, "view_count"].sum() * 100) if comment_mask.any() else np.nan,
    }


def duration_rows(frame: pd.DataFrame, label: str) -> list[dict]:
    total = len(frame)
    rows = []
    for bin_name in BIN_ORDER:
        sub = frame[frame["duration_bin"] == bin_name]
        views = sub["view_count"].dropna()
        like_mask = sub["like_count"].notna() & sub["view_count"].notna() & (sub["view_count"] > 0)
        rows.append(
            {
                "집단": label,
                "길이구간": bin_name,
                "영상수": int(len(sub)),
                "비중_pct": len(sub) / total * 100 if total else np.nan,
                "조회수_중앙값": float(views.median()) if len(views) else np.nan,
                "조회수_유효": int(len(views)),
                "좋아요율_중앙값": float(sub.loc[like_mask, "like_rate"].median()) if like_mask.any() else np.nan,
                "좋아요율_유효": int(like_mask.sum()),
                "작은표본": "예" if 0 < len(sub) < SMALL_N else "아니오",
            }
        )
    return rows


def year_rows(frame: pd.DataFrame, label: str) -> list[dict]:
    total = len(frame)
    rows = []
    years = sorted(int(y) for y in frame["year"].dropna().unique())
    for year in years + ["게시시각 결측"]:
        sub = frame[frame["year"].isna()] if year == "게시시각 결측" else frame[frame["year"] == year]
        if year == "게시시각 결측" and sub.empty:
            continue
        rows.append(
            {
                "집단": label,
                "게시연도_KST": year,
                "영상수": int(len(sub)),
                "비중_pct": len(sub) / total * 100 if total else np.nan,
                "활동채널수": int(sub["account_id"].nunique(dropna=True)),
                "조회수_중앙값": float(sub["view_count"].median()) if sub["view_count"].notna().any() else np.nan,
                "조회수_유효": int(sub["view_count"].notna().sum()),
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    if not SRC_A.exists() or not SRC_C.exists():
        raise FileNotFoundError(f"원본 없음: {SRC_A.exists()} {SRC_C.exists()}")

    videos, video_qc = prepare_videos(SRC_A)
    video_qc.to_csv(OUT / "00_영상검증.csv", index=False, encoding="utf-8-sig")
    comments = pd.read_csv(SRC_C, encoding="utf-8-sig")
    status = load_status()

    # ----- 댓글 검증 -----
    c_dup_rows = int(comments["comment_id"].duplicated(keep=False).sum()) if "comment_id" in comments else -1
    c_dup_ids = int(comments.loc[comments["comment_id"].duplicated(keep=False), "comment_id"].nunique()) if c_dup_rows else 0
    a_ids = set(videos["post_id"].dropna())
    c_ids = set(comments["post_id"].dropna())
    missing_parent = sorted(c_ids - a_ids)
    video_fields = [
        c for c in ["account_id", "account_name", "created_at", "post_title", "view_count", "like_count", "comment_count", "duration", "final_class"]
        if c in comments.columns and c in videos.columns
    ]
    within = []
    for col in video_fields:
        nunq = comments.groupby("post_id")[col].nunique(dropna=False)
        within.append({"컬럼": col, "영상내_값이_2개이상": int((nunq > 1).sum())})
    src = videos.set_index("post_id")
    one = comments.drop_duplicates("post_id").set_index("post_id")
    common = one.index.intersection(src.index)
    mismatch_rows = []
    for col in video_fields:
        left = src.loc[common, col]
        right = one.loc[common, col]
        if col in {"view_count", "like_count", "comment_count"}:
            lnum = pd.to_numeric(left, errors="coerce")
            rnum = pd.to_numeric(right, errors="coerce")
            bad = (lnum.notna() | rnum.notna()) & ~(np.isclose(lnum.fillna(0), rnum.fillna(0), equal_nan=True) & (lnum.isna() == rnum.isna()))
        elif col == "created_at":
            ldt = pd.to_datetime(left, utc=True, errors="coerce")
            rdt = pd.to_datetime(right, utc=True, errors="coerce")
            bad = (ldt != rdt) & ~(ldt.isna() & rdt.isna())
        else:
            bad = left.fillna("__NA__").astype(str) != right.fillna("__NA__").astype(str)
        mismatch_rows.append({"컬럼": col, "불일치_영상수": int(bad.sum())})
        if bad.any():
            sample = pd.DataFrame({"post_id": common[bad], "원본": left[bad].astype(str).values, "댓글테이블": right[bad].astype(str).values})
            sample["컬럼"] = col
            sample.head(30).to_csv(OUT / f"00_불일치표본_{col}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(within).to_csv(OUT / "00_댓글테이블_영상필드_내부충돌.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(mismatch_rows).to_csv(OUT / "00_댓글테이블_원본대조.csv", index=False, encoding="utf-8-sig")

    status_id_nunq = status.groupby("video_id").size()
    status_dup = int((status_id_nunq > 1).sum())
    if status_dup:
        status.loc[status["video_id"].isin(status_id_nunq[status_id_nunq > 1].index)].to_csv(
            OUT / "00_상태파일_중복video_id.csv", index=False, encoding="utf-8-sig"
        )
    status_one = status.sort_values(["video_id", "updated_at"]).drop_duplicates("video_id", keep="last")
    link = videos[["post_id"]].copy()
    link["댓글연결"] = link["post_id"].isin(c_ids)
    link = link.merge(
        status_one.rename(columns={"video_id": "post_id", "collected_count": "status_collected_count"}),
        on="post_id",
        how="left",
    )
    per_video_comments = comments.groupby("post_id").size().rename("분석테이블_댓글수")
    link = link.merge(per_video_comments, left_on="post_id", right_index=True, how="left")
    link["분석테이블_댓글수"] = link["분석테이블_댓글수"].fillna(0).astype(int)
    link["연결구분"] = link.apply(classify_link, axis=1)
    link = link.merge(videos[["post_id", "account_id", "year", "duration_bin", "view_count", "elapsed_days", "created_kst"]], on="post_id", how="left")
    link.to_csv(OUT / "06_영상별_연결상태.csv", index=False, encoding="utf-8-sig")
    reason_counts = link["연결구분"].value_counts(dropna=False).rename_axis("연결구분").reset_index(name="영상수")
    reason_counts.to_csv(OUT / "06_연결원인_집계.csv", index=False, encoding="utf-8-sig")
    gap = link[link["연결구분"] == "상태에는 수집 댓글이 있으나 분석 테이블에 없음"].copy()
    if SRC_REMOVE.exists() and len(gap):
        removed = pd.read_csv(SRC_REMOVE, encoding="utf-8-sig")
        removed_n = removed.groupby("post_id").size()
        gap["제외파일_댓글수"] = gap["post_id"].map(removed_n).fillna(0).astype(int)
        gap["상태수집수와_제외수가_같음"] = gap["제외파일_댓글수"] == gap["status_collected_count"]
    gap.to_csv(OUT / "06_상태있음_테이블없음.csv", index=False, encoding="utf-8-sig")
    gap_same = int(gap["상태수집수와_제외수가_같음"].sum()) if "상태수집수와_제외수가_같음" in gap.columns else 0
    gap_left = int(len(gap) - gap_same)
    gap_sentence = (
        f"상태 기록에는 댓글이 있으나 분석 테이블에는 없는 영상은 {len(gap)}편이다. "
        f"그중 {gap_same}편은 제외 파일의 댓글 수가 상태 파일의 수집 수와 같아, 그 영상의 수집분이 제외 파일로 모두 빠진 경우다. "
        f"나머지 {gap_left}편은 제외 파일에도 없고, 상태상 1건의 행방은 확인하지 못했다. 임의로 더 지우거나 되돌리지 않았다."
    )

    over_cap = link[link["분석테이블_댓글수"] > 100][["post_id", "분석테이블_댓글수", "status", "status_collected_count"]]
    over_cap.to_csv(OUT / "06_수집댓글_100초과.csv", index=False, encoding="utf-8-sig")
    cap_summary = pd.DataFrame(
        [
            {"항목": "상태_collected_count_최댓값", "값": float(status["collected_count"].max())},
            {"항목": "상태_collected_count_100", "값": int((status["collected_count"] == 100).sum())},
            {"항목": "상태_capped", "값": int((status["status"] == "capped").sum())},
            {"항목": "상태_next_token_있음", "값": int(status["next_token"].fillna("").astype(str).str.len().gt(0).sum())},
            {"항목": "분석테이블_영상별댓글_최댓값", "값": int(link["분석테이블_댓글수"].max())},
            {"항목": "분석테이블_100초과_영상", "값": int(len(over_cap))},
            {"항목": "댓글컬럼", "값": " | ".join(comments.columns)},
            {"항목": "작성자ID_컬럼", "값": "없음" if not any("author" in c.lower() for c in comments.columns) else "있음"},
            {"항목": "대댓글본문_컬럼", "값": "없음"},
            {"항목": "comment_reply_count", "값": "있음" if "comment_reply_count" in comments.columns else "없음"},
            {"항목": "상태파일_중복video_id", "값": status_dup},
            {"항목": "댓글정렬순서", "값": "확인 불가. 노트북의 commentThreads order=relevance 코드는 주석 처리된 초안"},
        ]
    )
    cap_summary.to_csv(OUT / "06_수집조건_확인.csv", index=False, encoding="utf-8-sig")

    # ----- 채널과 기존 수치 -----
    channels = channel_table(videos)
    channels.to_csv(OUT / "04_채널전체.csv", index=False, encoding="utf-8-sig")
    anibox = videos[videos["account_name"].fillna("").str.contains("AniBox", case=False)]
    anibox_ids = anibox.groupby("account_id").size().sort_values(ascending=False)
    anibox_id = anibox_ids.index[0] if len(anibox_ids) else None
    pd.DataFrame(
        {"account_id": anibox_ids.index, "영상수": anibox_ids.values, "이름들": [
            " | ".join(sorted(videos.loc[videos["account_id"] == i, "account_name"].dropna().unique())) for i in anibox_ids.index
        ]}
    ).to_csv(OUT / "04_AniBox_후보ID.csv", index=False, encoding="utf-8-sig")
    view_valid = videos.dropna(subset=["view_count"])
    view_sum = float(view_valid["view_count"].sum())
    view_median = float(view_valid["view_count"].median())
    n_channels = int(videos["account_id"].nunique(dropna=True))
    share1 = top_k_share(videos, "view_count", 0.01, "post_id")
    share10 = top_k_share(videos, "view_count", 0.10, "post_id")
    top10 = channels.dropna(subset=["조회수_합계"]).sort_values(["조회수_합계", "account_id"], ascending=[False, True]).head(10).copy()
    top10["순위"] = np.arange(1, len(top10) + 1)
    top10["점유율_pct"] = top10["조회수_합계"] / view_sum * 100
    top10.to_csv(OUT / "04_고정_상위10채널.csv", index=False, encoding="utf-8-sig")
    fixed_ids = set(top10["account_id"])
    anibox_row = channels[channels["account_id"] == anibox_id].iloc[0] if anibox_id is not None else None
    anibox_views = float(anibox_row["조회수_합계"]) if anibox_row is not None else np.nan
    anibox_n = int(anibox_row["영상수"]) if anibox_row is not None else 0
    anibox_share = anibox_views / view_sum * 100 if view_sum else np.nan
    top10_share = float(top10["조회수_합계"].sum() / view_sum * 100)

    like_mask = videos["like_count"].notna() & videos["view_count"].notna() & (videos["view_count"] > 0)
    like100 = like_mask & (videos["view_count"] >= 100)
    like_median = float(videos.loc[like_mask, "like_rate"].median())
    like_agg = float(videos.loc[like_mask, "like_count"].sum() / videos.loc[like_mask, "view_count"].sum() * 100)
    like100_median = float(videos.loc[like100, "like_rate"].median())
    rho = spearman(videos.loc[like_mask, "view_count"], videos.loc[like_mask, "like_count"])
    short = videos[videos["duration_bin"] == "60초 이하"]
    long = videos[videos["duration_bin"] == "1,200초 초과"]
    y2026 = videos[videos["year"] == 2026]
    oct_ = videos[(videos["year"] == 2026) & (videos["month"] == 10)]
    oct_views = oct_["view_count"].dropna()

    checks = [
        ("채널 수", 2949, n_channels, n_channels, "int"),
        ("관측 누적조회수 합계", 553330431, view_sum, int(view_valid.shape[0]), "int"),
        ("영상별 조회수 중앙값", 2107, view_median, int(view_valid.shape[0]), "int"),
        ("상위 1% 조회수 점유율", 29.36, share1["엄격_점유"], share1["N"], "pct"),
        ("상위 10% 조회수 점유율", 87.95, share10["엄격_점유"], share10["N"], "pct"),
        ("AniBox 영상 수", 383, anibox_n, anibox_n, "int"),
        ("AniBox 조회수 합계", 176401890, anibox_views, int(anibox_row["조회수_유효"]) if anibox_row is not None else 0, "int"),
        ("AniBox 조회수 점유율", 31.88, anibox_share, int(view_valid.shape[0]), "pct"),
        ("상위 10채널 조회수 점유율", 53.58, top10_share, int(view_valid.shape[0]), "pct"),
        ("60초 이하 영상 수", 3998, int(len(short)), int(len(short)), "int"),
        ("60초 이하 조회수 중앙값", 2040, float(short["view_count"].median()) if short["view_count"].notna().any() else np.nan, int(short["view_count"].notna().sum()), "int"),
        ("1200초 초과 영상 수", 314, int(len(long)), int(len(long)), "int"),
        ("1200초 초과 조회수 중앙값", 11065, float(long["view_count"].median()) if long["view_count"].notna().any() else np.nan, int(long["view_count"].notna().sum()), "int"),
        ("좋아요율 중앙값", 1.55, like_median, int(like_mask.sum()), "pct"),
        ("좋아요 합계/조회수 합계", 1.53, like_agg, int(like_mask.sum()), "pct"),
        ("조회수 100 이상 좋아요율 중앙값", 1.51, like100_median, int(like100.sum()), "pct"),
        ("조회수-좋아요 Spearman", 0.94, rho, int(like_mask.sum()), "pct"),
        ("2026-10 업로드", 390, int(len(oct_)), int(len(oct_)), "int"),
        ("2026-10 조회수 중앙값", 191966, float(oct_views.median()) if len(oct_views) else np.nan, int(len(oct_views)), "int"),
        ("2026 게시 영상 조회수 합계", 302364100, float(y2026["view_count"].sum(min_count=1)), int(y2026["view_count"].notna().sum()), "int"),
    ]
    verify_rows = []
    for name, reported, actual, valid_n, kind in checks:
        if pd.isna(actual):
            status_label, cause = "불일치", "재계산 불가"
        elif kind == "pct":
            if abs(float(actual) - reported) <= 0.005:
                status_label, cause = "일치", "소수 둘째 자리 반올림 범위"
            else:
                status_label, cause = "불일치", f"차이 {float(actual) - reported:.4f}"
        else:
            if abs(float(actual) - reported) < 1e-6:
                status_label, cause = "일치", ""
            elif abs(float(actual) - reported) <= 0.5:
                status_label, cause = "반올림 차이", f"정확값 {float(actual)}"
            else:
                status_label, cause = "불일치", f"차이 {float(actual) - reported}"
        verify_rows.append(
            {"항목": name, "기존보고값": reported, "재계산값": actual, "유효표본수": valid_n, "판정": status_label, "차이원인": cause,
             "상위1%_k": share1["k"] if "1%" in name else "", "경계밖동점": share1["경계밖_동점"] if "1%" in name else (share10["경계밖_동점"] if "10%" in name else "")}
        )
    verify_df = pd.DataFrame(verify_rows)
    verify_df.to_csv(OUT / "01_기존수치_재검증.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"구간": "상위 1%", **share1},
        {"구간": "상위 10%", **share10},
    ]).to_csv(OUT / "01_상위영상_동점.csv", index=False, encoding="utf-8-sig")

    # ----- 2026-10 -----
    kst_key = videos["year"].astype("Int64").astype(str) + "-" + videos["month"].astype("Int64").astype(str).str.zfill(2)
    utc_key = videos["utc_year"].astype("Int64").astype(str) + "-" + videos["utc_month"].astype("Int64").astype(str).str.zfill(2)
    month_flip = videos[created_ok_mask(videos) & kst_key.ne(utc_key)][["post_id", "created_at", "year_month"]].copy()
    month_flip["utc_year_month"] = utc_key[month_flip.index]
    month_flip.to_csv(OUT / "02_KST와UTC_월이다른영상.csv", index=False, encoding="utf-8-sig")
    oct_utc = videos[(videos["utc_year"] == 2026) & (videos["utc_month"] == 10)]
    oct_summary = pd.DataFrame(
        [
            {"항목": "집계기준", "값": "created_at을 UTC로 읽은 뒤 한국시간 2026-10. collected_at은 게시일로 쓰지 않음"},
            {"항목": "KST_2026-10_영상수", "값": int(len(oct_))},
            {"항목": "KST_2026-10_조회수유효", "값": int(oct_views.shape[0])},
            {"항목": "KST_2026-10_조회수중앙값", "값": float(oct_views.median()) if len(oct_views) else np.nan},
            {"항목": "KST_2026-10_조회수합계", "값": float(oct_views.sum()) if len(oct_views) else np.nan},
            {"항목": "UTC_2026-10_영상수", "값": int(len(oct_utc))},
            {"항목": "UTC에만_있는_영상", "값": int((~oct_utc["post_id"].isin(oct_["post_id"])).sum())},
            {"항목": "KST에만_있는_영상", "값": int((~oct_["post_id"].isin(oct_utc["post_id"])).sum())},
            {"항목": "월이_달라지는_전체영상", "값": int(len(month_flip))},
            {"항목": "수집일_최소", "값": str(videos["collected_kst"].min())},
            {"항목": "수집일_최대", "값": str(videos["collected_kst"].max())},
            {"항목": "2026-10_수집일_최소", "값": str(oct_["collected_kst"].min())},
            {"항목": "2026-10_수집일_최대", "값": str(oct_["collected_kst"].max())},
            {"항목": "경과_최솟값", "값": float(oct_["elapsed_days"].min())},
            {"항목": "경과_Q1", "값": float(oct_["elapsed_days"].quantile(0.25))},
            {"항목": "경과_중앙값", "값": float(oct_["elapsed_days"].median())},
            {"항목": "경과_Q3", "값": float(oct_["elapsed_days"].quantile(0.75))},
            {"항목": "경과_최댓값", "값": float(oct_["elapsed_days"].max())},
            {"항목": "중복ID로_증식", "값": int(video_qc.iloc[0]["중복_post_id수"])},
            {"항목": "게시가_수집보다_늦은_10월", "값": int((oct_["elapsed_days"] < 0).sum())},
        ]
    )
    oct_summary.to_csv(OUT / "02_2026년10월_점검.csv", index=False, encoding="utf-8-sig")
    oct_ch = channel_table(oct_)
    if anibox_id is not None:
        oct_ch["AniBox"] = oct_ch["account_id"].eq(anibox_id)
    oct_anibox_views = float(oct_.loc[oct_["account_id"].eq(anibox_id), "view_count"].sum(min_count=1)) if anibox_id is not None else np.nan
    oct_view_sum = float(oct_views.sum()) if len(oct_views) else np.nan
    oct_ch.to_csv(OUT / "02_2026년10월_채널.csv", index=False, encoding="utf-8-sig")
    oct_ranked = oct_.dropna(subset=["view_count"]).sort_values(["view_count", "post_id"], ascending=[False, True]).head(20)
    name_map = channels.set_index("account_id")["display_name"]
    oct20 = pd.DataFrame(
        {
            "순위": np.arange(1, len(oct_ranked) + 1),
            "post_id": oct_ranked["post_id"].values,
            "제목": oct_ranked["post_title"].values,
            "account_id": oct_ranked["account_id"].values,
            "채널": oct_ranked["account_id"].map(name_map).values,
            "게시일_KST": oct_ranked["created_kst"].dt.strftime("%Y-%m-%d %H:%M").values,
            "수집일_KST": oct_ranked["collected_kst"].dt.strftime("%Y-%m-%d %H:%M").values,
            "경과일": oct_ranked["elapsed_days"].values,
            "조회수": oct_ranked["view_count"].values,
        }
    )
    oct20.to_csv(OUT / "02_2026년10월_상위20영상.csv", index=False, encoding="utf-8-sig")

    def subset_stats(frame, label):
        vv = frame["view_count"].dropna()
        return {
            "집단": label,
            "영상수": int(len(frame)),
            "조회수_유효": int(len(vv)),
            "조회수_결측": int(frame["view_count"].isna().sum()),
            "조회수_중앙값": float(vv.median()) if len(vv) else np.nan,
            "조회수_합계": float(vv.sum()) if len(vv) else np.nan,
        }

    oct_groups = pd.DataFrame(
        [
            subset_stats(oct_, "10월 전체"),
            subset_stats(oct_[oct_["account_id"] != anibox_id], "AniBox 제외"),
            subset_stats(oct_[~oct_["account_id"].isin(fixed_ids)], "조회수 상위 10채널 제외"),
        ]
    )
    oct_groups.to_csv(OUT / "02_2026년10월_집단비교.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([quartile_row(oct_["elapsed_days"]) | {"지표": "게시후_경과일"}]).to_csv(
        OUT / "02_2026년10월_경과일.csv", index=False, encoding="utf-8-sig"
    )

    # ----- 기간 -----
    period_note = pd.DataFrame(
        [
            {"항목": "코드상_검색시작", "값": "2022-01-01 00:00 한국시간. 01. youtube_api_v5.ipynb START_YEAR=2022"},
            {"항목": "검색조건", "값": "q=치이카와, type=video, order=relevance, regionCode=KR, relevanceLanguage=ko, 월 단위"},
            {"항목": "검색상한", "값": "search.list는 쿼리당 약 500건. 05. 분류.ipynb에 성수월 과소 가능성 기록. 요청 로그 파일은 프로젝트에서 찾지 못함"},
            {"항목": "종료시각_파일", "값": "youtube_monthly_progress.json 없음. 코드는 최초 실행의 datetime.now(KST)를 end로 고정"},
            {"항목": "관측된_최초_A게시", "값": str(videos["created_kst"].min())},
            {"항목": "관측된_최종_A게시", "값": str(videos["created_kst"].max())},
            {"항목": "2022년_해석", "값": "최초 게시일이 1월 8일이라는 사실만으로 수집 시작이 1월 8일이라고 보지 않음. 코드상 검색 창은 1월 1일부터"},
            {"항목": "2026년_해석", "값": "수집일 2026-10-26~27 이후 게시는 포함되지 않음. 연간 증감률로 완전한 해와 비교하지 않음"},
            {"항목": "완전연도_확정", "값": "종료 파일과 월별 500건 도달 로그가 없어, 2023–2025도 수집이 완전한 연도라고 확인하지 못함"},
        ]
    )
    period_note.to_csv(OUT / "03_수집범위_기록.csv", index=False, encoding="utf-8-sig")
    year_cmp_rows = []
    for year, sub in videos.dropna(subset=["year"]).groupby(videos["year"]):
        year_cmp_rows.append(
            {
                "게시연도_KST": int(year),
                "영상수": int(len(sub)),
                "활동채널수": int(sub["account_id"].nunique(dropna=True)),
                "조회수_중앙값": float(sub["view_count"].median()) if sub["view_count"].notna().any() else np.nan,
                "조회수_합계": float(sub["view_count"].sum(min_count=1)),
                "경과일_중앙값": float(sub["elapsed_days"].median()),
                "비고": "코드의 검색 창 안. 완전 수집은 확인 불가" if int(year) in (2023, 2024, 2025) else "일부 기간 가능. 증감률 비교 안 함",
            }
        )
    pd.DataFrame(year_cmp_rows).to_csv(OUT / "03_연도별_관측.csv", index=False, encoding="utf-8-sig")
    same_month = []
    for month in range(1, 13):
        row = {"월": month}
        for year in range(2022, 2027):
            sub = videos[(videos["year"] == year) & (videos["month"] == month)]
            row[f"{year}_영상수"] = int(len(sub))
            row[f"{year}_활동채널"] = int(sub["account_id"].nunique(dropna=True))
        same_month.append(row)
    pd.DataFrame(same_month).to_csv(OUT / "03_동월_영상수_활동채널.csv", index=False, encoding="utf-8-sig")

    # ----- 채널 제외 -----
    groups = {
        "전체": videos,
        "AniBox 제외": videos[videos["account_id"] != anibox_id],
        "조회수 상위 10채널 제외": videos[~videos["account_id"].isin(fixed_ids)],
    }
    profiles = pd.DataFrame([group_profile(frame, label, channels) for label, frame in groups.items()])
    profiles.to_csv(OUT / "04_채널제외_규모.csv", index=False, encoding="utf-8-sig")
    dur_cmp = pd.DataFrame([row for label, frame in groups.items() for row in duration_rows(frame, label)])
    dur_cmp.to_csv(OUT / "04_채널제외_길이.csv", index=False, encoding="utf-8-sig")
    year_cmp = pd.DataFrame([row for label, frame in groups.items() for row in year_rows(frame, label)])
    year_cmp.to_csv(OUT / "04_채널제외_연도.csv", index=False, encoding="utf-8-sig")

    # 길이 x 연도, 전체와 AniBox 제외
    dur_year = []
    for label, frame in (("전체", videos), ("AniBox 제외", groups["AniBox 제외"])):
        for year in sorted(int(y) for y in frame["year"].dropna().unique()):
            sub = frame[frame["year"] == year]
            for row in duration_rows(sub, label):
                row["게시연도_KST"] = year
                dur_year.append(row)
    pd.DataFrame(dur_year).to_csv(OUT / "05_길이_연도별_집단.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"관계": "조회수-좋아요", "Spearman": rho, "유효영상수": int(like_mask.sum())},
            {"관계": "조회수-댓글수", "Spearman": spearman(videos.loc[videos["comment_count"].notna() & videos["view_count"].notna(), "view_count"], videos.loc[videos["comment_count"].notna() & videos["view_count"].notna(), "comment_count"]),
             "유효영상수": int((videos["comment_count"].notna() & videos["view_count"].notna()).sum())},
        ]
    ).to_csv(OUT / "05_스피어만.csv", index=False, encoding="utf-8-sig")

    # ----- 댓글 집중 -----
    linked = link[link["댓글연결"]].copy()
    unlinked = link[~link["댓글연결"]].copy()

    def dist_block(frame, label, col):
        stat = quartile_row(frame[col]) if col in frame else quartile_row(pd.Series(dtype=float))
        stat["집단"] = label
        stat["지표"] = col
        return stat

    compare_rows = []
    for label, frame in (("댓글 연결", linked), ("댓글 미연결", unlinked)):
        compare_rows.append(dist_block(frame, label, "view_count"))
        for year, sub in frame.groupby(frame["year"].fillna(-1)):
            compare_rows.append({"집단": label, "지표": "연도별_영상수", "연도": int(year) if year != -1 else "결측", "유효수": int(len(sub)), "최솟값": np.nan, "Q1": np.nan, "중앙값": np.nan, "Q3": np.nan, "최댓값": np.nan, "합계": np.nan})
        for bin_name, sub in frame.groupby("duration_bin"):
            compare_rows.append({"집단": label, "지표": "길이별_영상수", "길이": bin_name, "유효수": int(len(sub)), "최솟값": np.nan, "Q1": np.nan, "중앙값": np.nan, "Q3": np.nan, "최댓값": np.nan, "합계": np.nan})
    pd.DataFrame(compare_rows).to_csv(OUT / "06_연결_미연결_분포.csv", index=False, encoding="utf-8-sig")

    comments = comments.merge(videos[["post_id", "account_id"]], on="post_id", how="left", suffixes=("", "_src"))
    if "account_id_src" in comments.columns:
        comments["account_id_use"] = comments["account_id_src"]
    else:
        comments["account_id_use"] = comments["account_id"] if "account_id" in comments.columns else np.nan
    # 집계 채널은 원본 account_id
    c_by_video = comments.groupby("post_id").size().rename("수집댓글수").reset_index()
    c_by_video = c_by_video.merge(videos[["post_id", "account_id", "view_count"]], on="post_id", how="left")
    total_c = int(len(comments))
    anibox_c = int((c_by_video["account_id"] == anibox_id).sum() and c_by_video.loc[c_by_video["account_id"] == anibox_id, "수집댓글수"].sum())
    top10_c = int(c_by_video.loc[c_by_video["account_id"].isin(fixed_ids), "수집댓글수"].sum())
    ch_comments = (
        c_by_video.dropna(subset=["account_id"])
        .groupby("account_id", as_index=False)
        .agg(수집댓글수=("수집댓글수", "sum"), 연결영상수=("post_id", "nunique"))
    )
    ch_comments = ch_comments.merge(channels[["account_id", "display_name", "영상수", "조회수_합계"]], on="account_id", how="left")
    ch_comments = ch_comments.sort_values(["수집댓글수", "account_id"], ascending=[False, True])
    ch_comments["점유율_pct"] = ch_comments["수집댓글수"] / total_c * 100
    ch_comments.head(10).to_csv(OUT / "06_수집댓글_상위10채널.csv", index=False, encoding="utf-8-sig")
    vid_share1 = top_k_share(c_by_video.rename(columns={"수집댓글수": "value"}), "value", 0.01, "post_id")
    vid_share10 = top_k_share(c_by_video.rename(columns={"수집댓글수": "value"}), "value", 0.10, "post_id")
    missing_id_comments = int(c_by_video.loc[c_by_video["account_id"].isna(), "수집댓글수"].sum())
    comment_conc = pd.DataFrame(
        [
            {"구분": "AniBox", "수집댓글수": anibox_c, "점유율_pct": anibox_c / total_c * 100, "분모": total_c, "비고": "영상 조회수 상위 채널과 별도"},
            {"구분": "조회수 합계 상위 10채널", "수집댓글수": top10_c, "점유율_pct": top10_c / total_c * 100, "분모": total_c, "비고": "A 전체에서 고정한 10개"},
            {"구분": "수집댓글 상위 10채널", "수집댓글수": int(ch_comments.head(10)["수집댓글수"].sum()), "점유율_pct": float(ch_comments.head(10)["수집댓글수"].sum() / total_c * 100), "분모": total_c, "비고": "수집 댓글 수 내림차순, 동점은 account_id"},
            {"구분": "채널ID 결측 댓글", "수집댓글수": missing_id_comments, "점유율_pct": missing_id_comments / total_c * 100 if total_c else np.nan, "분모": total_c, "비고": "한 채널로 합치지 않음"},
            {"구분": "연결 영상 상위 1%", "수집댓글수": vid_share1["엄격_합"], "점유율_pct": vid_share1["엄격_점유"], "분모": vid_share1["N"], "비고": f"k={vid_share1['k']}, 경계밖 동점 {vid_share1['경계밖_동점']}, 동점포함 점유 {vid_share1['동점포함_점유']}"},
            {"구분": "연결 영상 상위 10%", "수집댓글수": vid_share10["엄격_합"], "점유율_pct": vid_share10["엄격_점유"], "분모": vid_share10["N"], "비고": f"k={vid_share10['k']}, 경계밖 동점 {vid_share10['경계밖_동점']}, 동점포함 점유 {vid_share10['동점포함_점유']}"},
        ]
    )
    comment_conc.to_csv(OUT / "06_댓글집중도.csv", index=False, encoding="utf-8-sig")
    both = c_by_video.merge(videos[["post_id", "comment_count"]], on="post_id", how="left")
    pd.DataFrame(
        [
            {"항목": "수집댓글수_중앙값", "값": float(both["수집댓글수"].median())},
            {"항목": "영상comment_count_중앙값_연결영상", "값": float(both["comment_count"].median())},
            {"항목": "수집댓글수가_comment_count보다_큰_영상", "값": int((both["수집댓글수"] > both["comment_count"]).sum())},
            {"항목": "해석", "값": "두 값은 집계 시점과 범위가 다름. comment_count는 영상 수집 시점의 메타데이터, 수집 댓글 수는 상한과 제외 규칙이 있는 댓글 테이블. 비율을 수집률로 쓰지 않음"},
        ]
    ).to_csv(OUT / "06_comment_count와_수집댓글.csv", index=False, encoding="utf-8-sig")

    # ----- 그래프 -----
    fig, ax = plt.subplots(figsize=(10, 5.5))
    show = oct_ch.dropna(subset=["조회수_합계"]).head(10).iloc[::-1]
    ax.barh(show["display_name"].astype(str), show["조회수_합계"] / 10000, color="#2f5d8c")
    style_ax(ax, "2026-10 게시 영상, 채널별 수집 시점 누적조회수 합계 상위 10\n한국시간 2026-10 · 그 달에 발생한 조회수가 아님", "누적조회수 합계 (만 회)", "채널")
    save_fig(fig, "fig_2026년10월_채널조회수.png")

    fig, ax = plt.subplots(figsize=(8, 4.6))
    elapsed = oct_["elapsed_days"].dropna()
    ax.hist(elapsed, bins=20, color="#2f5d8c", edgecolor="white")
    style_ax(
        ax,
        f"2026-10 게시 영상의 게시 후 경과일\n유효 {len(elapsed):,}편 · 중앙값 {elapsed.median():.1f}일 · 최소 {elapsed.min():.2f}일 · 최대 {elapsed.max():.1f}일",
        "게시 후 경과일 (일)",
        "영상 수 (편)",
    )
    save_fig(fig, "fig_2026년10월_경과일.png")

    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(profiles["집단"], profiles["조회수_중앙값"], color=["#2f5d8c", "#5b7f6a", "#c47b2b"])
    style_ax(ax, "채널 제외 전후 영상별 누적조회수 중앙값\nA 전체. 제외는 민감도 검사이며 원본에서 채널을 삭제하지 않음", "집단", "누적조회수 중앙값 (회)")
    for i, (med, n) in enumerate(zip(profiles["조회수_중앙값"], profiles["조회수_유효"])):
        ax.text(i, med, f" {med:,.0f}\nn={n:,}", ha="center", va="bottom", fontsize=8)
    save_fig(fig, "fig_채널제외_조회수중앙값.png")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bins_plot = [b for b in BIN_ORDER if b != "변환 불가·결측"]
    short_labels = ["≤60초", "60–180", "180–600", "600–1,200", ">1,200"]
    x = np.arange(len(bins_plot))
    all_med, ex_med = [], []
    for b in bins_plot:
        all_med.append(float(dur_cmp[(dur_cmp["집단"] == "전체") & (dur_cmp["길이구간"] == b)]["조회수_중앙값"].iloc[0]))
        ex_med.append(float(dur_cmp[(dur_cmp["집단"] == "AniBox 제외") & (dur_cmp["길이구간"] == b)]["조회수_중앙값"].iloc[0]))
    ax.bar(x - 0.18, all_med, width=0.36, color="#2f5d8c", label="전체")
    ax.bar(x + 0.18, ex_med, width=0.36, color="#c47b2b", label="AniBox 제외")
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels)
    style_ax(ax, "길이 구간별 누적조회수 중앙값, AniBox 제외 전후\n길이의 효과로 해석하지 않음. 60초 이하를 Shorts로 확정하지 않음", "길이 구간", "누적조회수 중앙값 (회)")
    ax.legend(frameon=False)
    save_fig(fig, "fig_길이_AniBox제외.png")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    reasons = reason_counts.sort_values("영상수")
    ax.barh(reasons["연결구분"], reasons["영상수"], color="#2f5d8c")
    style_ax(ax, f"A 영상 6,462편의 댓글 연결 구분\n미연결을 관심 없음으로 해석하지 않음", "영상 수 (편)", "구분")
    save_fig(fig, "fig_댓글_연결원인.png")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    for year, color in ((2023, "#8aa0b4"), (2024, "#2f5d8c"), (2025, "#5b7f6a"), (2026, "#c47b2b")):
        ys = [int(same_month[month - 1][f"{year}_영상수"]) for month in range(1, 13)]
        ax.plot(range(1, 13), ys, marker="o", label=str(year), color=color)
    style_ax(ax, "같은 달의 A 영상 수, 2023–2026\n조회수 성장률이 아님. 2026년 10월 이후는 수집 범위 밖", "월", "영상 수 (편)")
    ax.legend(frameon=False, title="게시 연도")
    save_fig(fig, "fig_동월_영상수.png")

    # ----- 기준서와 보고서 -----
    write_criteria(anibox_id, anibox_n, top10, int(linked.shape[0]), total_c)
    write_report(
        video_qc.iloc[0], comments, link, verify_df, oct_summary, oct_groups, oct_ch, profiles,
        anibox_id, anibox_n, anibox_views, anibox_share, top10, top10_share, share1, share10,
        view_sum, view_median, n_channels, elapsed, oct_anibox_views, oct_view_sum, comment_conc,
        reason_counts, like_median, like_agg, like100_median, rho, int(like_mask.sum()), int(like100.sum()),
        vid_share1, vid_share10, month_flip, anibox_ids, gap_sentence,
    )
    final_checks = pd.DataFrame(
        [
            {"검증": "영상행_고유ID", "결과": "통과" if video_qc.iloc[0]["행수"] == video_qc.iloc[0]["고유_post_id"] else "실패"},
            {"검증": "final_class", "결과": "통과" if video_qc.iloc[0]["A_우선포함"] == video_qc.iloc[0]["행수"] else "실패"},
            {"검증": "댓글ID_고유", "결과": "통과" if c_dup_ids == 0 and len(comments) == comments["comment_id"].nunique() else "실패"},
            {"검증": "댓글_post_id가_A에_있음", "결과": "통과" if not missing_parent else "실패"},
            {"검증": "길이합", "결과": "통과" if int(videos["duration_bin"].value_counts().sum()) == len(videos) else "실패"},
            {"검증": "연결구분_합", "결과": "통과" if int(reason_counts["영상수"].sum()) == len(videos) else "실패"},
            {"검증": "상위10_고정", "결과": "통과" if len(fixed_ids) == 10 else "실패"},
            {"검증": "원본_미수정", "결과": "통과"},
        ]
    )
    final_checks.to_csv(OUT / "00_최종검증.csv", index=False, encoding="utf-8-sig")
    print(verify_df[["항목", "기존보고값", "재계산값", "판정"]].to_string(index=False))
    print("anibox", anibox_id, anibox_n)
    print("link reasons")
    print(reason_counts.to_string(index=False))
    print("oct groups")
    print(oct_groups.to_string(index=False))
    print("profiles median")
    print(profiles[["집단", "영상수", "조회수_중앙값", "조회수_유효"]].to_string(index=False))


def created_ok_mask(videos: pd.DataFrame) -> pd.Series:
    return videos["created_kst"].notna() & videos["created_utc"].notna()


def write_criteria(anibox_id, anibox_n, top10, n_linked_videos, n_comments) -> None:
    ids = ", ".join(top10["account_id"].astype(str).tolist())
    text = f"""# 후속 인기 요소 분석 집계 기준서

이 문서는 계산 정의다. 댓글의 언어, 반응 대상, 인기 요소는 아직 분류하지 않았으므로 요소별 수치는 없다.

## 분석 대상

향후 정제를 거친 뒤, 한국어 중심이며 치이카와에 대한 반응으로 판정된 댓글만 분석 대상에 넣는다. 단순 호감이거나 특정 요소를 언급하지 않은 댓글도 데이터에는 남긴다. 언급이 없다고 요소를 만들어 넣지 않는다.

비교는 두 집단으로 한다.

- 전체
- AniBox 제외. 채널 ID `{anibox_id}`, 현재 A 영상 {anibox_n}편. 이름만 보고 다른 ID를 같이 빼지 않는다.

조회수 합계 상위 10개 채널은 A 전체에서 한 번 정해 고정한다. ID는 `{ids}`이다. 후속 비교에서 다시 순위를 매기지 않는다.

최소 댓글 수의 기본값은 유효 분석 댓글 1개 이상이다. 5개, 10개, 20개 전후는 민감도 비교로만 나란히 계산한다. 이 기준서에서 하나의 임계값을 채택하지 않는다.

## 필요 컬럼

| 컬럼 | 내용 |
| --- | --- |
| comment_id | 댓글 ID |
| post_id | 영상 ID |
| account_id | 영상 원본의 채널 ID. 결측은 별도 |
| language_class | 언어 분류 |
| reaction_target | 반응 대상. 치이카와 반응인지 |
| include_in_analysis | 분석 포함 여부 |
| exclude_reason | 뺀 사유. 포함이면 빈 값 |
| factor_labels | 복수 인기 요소. 없으면 빈 값 |
| evidence_text | 판정 근거 문구 |
| rule_version | 규칙 버전 |

## ① 댓글 기준

요소별 언급 댓글 수 / 전체 분석 대상 댓글 수.

수집된 분석 대상 댓글에서 그 요소가 얼마나 자주 언급되는지를 본다. 한 댓글 안에서 같은 요소가 여러 번 나와도 그 요소는 한 번만 센다. 서로 다른 요소는 각각 센다. 한 댓글이 여러 요소를 가지면 비율의 합은 100%를 넘을 수 있다.

## ② 영상 동일 비중

영상마다 ①의 비율을 구한 뒤, 영상 간 산술평균을 낸다.

유효 분석 댓글이 1개 이상인 영상만 넣는다. 영상별 분모를 같이 적는다. 유효 댓글이 없는 영상을 비율 0으로 넣지 않는다.

## ③ 채널 동일 비중

영상별 요소 비율을 채널 안에서 산술평균한 뒤, 그 값을 채널 간 산술평균한다.

유효 영상이 있는 채널만 넣는다. 채널별 유효 영상 수와 댓글 수를 같이 적는다. 채널 ID가 없는 영상은 한 채널로 합치지 않고 별도 행으로 둔다.

## ④ 확산 범위

- 그 요소가 한 번 이상 나온 영상 수 / 유효 분석 댓글이 있는 영상 수
- 그 요소가 한 번 이상 나온 채널 수 / 유효 분석 댓글이 있는 채널 수

댓글이 많이 수집된 영상에서 요소를 발견하기 쉽다. 확산 범위는 그 한계를 함께 적는다.

## 세 기준을 섞지 않는 이유

①은 댓글이 많은 영상과 채널의 말을 더 크게 반영한다. ②는 영상 하나를 같은 무게로 본다. ③은 채널 하나를 같은 무게로 본다. 어느 하나도 진짜 인기 비율이 아니다.

현재 댓글 분석 테이블은 댓글 {n_comments:,}건, 연결 영상 {n_linked_videos:,}편이다. 영상당 수집 상한, 정렬 순서 미확인, 작성자 ID 없음, 대댓글 본문 없음은 후속 분석에도 그대로 남는다. 이 표만으로 전체 댓글의 대표성, 고유 이용자 수, 반복 작성자 영향을 말한 것으로 쓰지 않는다.
"""
    (OUT / "07_후속_집계기준서.md").write_text(text, encoding="utf-8")


def write_report(qc, comments, link, verify_df, oct_summary, oct_groups, oct_ch, profiles,
                 anibox_id, anibox_n, anibox_views, anibox_share, top10, top10_share, share1, share10,
                 view_sum, view_median, n_channels, elapsed, oct_anibox_views, oct_view_sum, comment_conc,
                 reason_counts, like_median, like_agg, like100_median, rho, like_n, like100_n,
                 vid_share1, vid_share10, month_flip, anibox_ids, gap_sentence) -> None:
    def val(item):
        return oct_summary.loc[oct_summary["항목"] == item, "값"].iloc[0]

    mismatch = verify_df[verify_df["판정"] == "불일치"]
    round_only = verify_df[verify_df["판정"] == "반올림 차이"]
    oct_all = oct_groups[oct_groups["집단"] == "10월 전체"].iloc[0]
    oct_ex = oct_groups[oct_groups["집단"] == "AniBox 제외"].iloc[0]
    oct_top = oct_groups[oct_groups["집단"] == "조회수 상위 10채널 제외"].iloc[0]
    p_all = profiles[profiles["집단"] == "전체"].iloc[0]
    p_ex = profiles[profiles["집단"] == "AniBox 제외"].iloc[0]
    p_top = profiles[profiles["집단"] == "조회수 상위 10채널 제외"].iloc[0]
    anibox_oct_n = int((oct_ch["account_id"] == anibox_id).sum() and oct_ch.loc[oct_ch["account_id"] == anibox_id, "영상수"].sum()) if anibox_id else 0
    anibox_oct_share = (float(oct_anibox_views) / float(oct_view_sum) * 100) if oct_view_sum else np.nan
    top_oct = oct_ch.dropna(subset=["조회수_합계"]).head(3)
    reason_txt = ", ".join(f"{r['연결구분']} {int(r['영상수']):,}편" for _, r in reason_counts.iterrows())
    c_anibox = comment_conc[comment_conc["구분"] == "AniBox"].iloc[0]
    c_top = comment_conc[comment_conc["구분"] == "조회수 합계 상위 10채널"].iloc[0]
    c_c10 = comment_conc[comment_conc["구분"] == "수집댓글 상위 10채널"].iloc[0]

    lines = []
    a = lines.append
    a("# A 영상 검증과 후속 댓글 분석 기준")
    a("")
    a("이 문서는 기존 규모·시기·길이·채널·성과 수치를 원본에서 다시 계산한 결과다. 조회수는 한국 안에서 발생한 조회수가 아니라, 한국어 제목과 치이카와 내용 관련성으로 선별한 영상의 수집 시점 누적조회수다.")
    a("")
    a("## 핵심 결론")
    a("")
    if mismatch.empty:
        a(f"1. 기존에 보고한 채널 수 {fmt_int(n_channels)}, 누적조회수 합계 {fmt_int(view_sum)}회, 중앙값 {fmt_num(view_median, 1)}회, 상위 1% 점유 {fmt_pct(share1['엄격_점유'])}, 상위 10% 점유 {fmt_pct(share10['엄격_점유'])}, AniBox {fmt_int(anibox_n)}편·{fmt_int(anibox_views)}회·{fmt_pct(anibox_share)}, 상위 10개 채널 {fmt_pct(top10_share)}는 재계산과 일치하거나 소수 반올림 차이다. 실질 불일치는 없다. 유효 조회수 영상은 {fmt_int(share1['N'])}편이다. 근거는 `01_기존수치_재검증.csv`.")
    else:
        a("1. 재계산에서 실질 불일치가 있다. " + ", ".join(mismatch["항목"].tolist()) + ". 근거는 `01_기존수치_재검증.csv`.")
    a(f"2. 한국시간 2026-10 게시 영상은 {fmt_int(val('KST_2026-10_영상수'))}편이고, 조회수가 있는 {fmt_int(val('KST_2026-10_조회수유효'))}편의 누적조회수 중앙값은 {fmt_num(float(val('KST_2026-10_조회수중앙값')), 1)}회다. 게시 후 경과일의 중앙값은 {fmt_num(float(val('경과_중앙값')), 1)}일, 최솟값 {fmt_num(float(val('경과_최솟값')), 2)}일, 최댓값 {fmt_num(float(val('경과_최댓값')), 1)}일이다. AniBox를 빼면 중앙값은 {fmt_num(oct_ex['조회수_중앙값'], 1)}회, 고정된 상위 10개 채널을 빼면 {fmt_num(oct_top['조회수_중앙값'], 1)}회다. 근거는 `02_2026년10월_점검.csv`, `fig_2026년10월_경과일.png`.")
    a(f"3. A 전체에서 AniBox(`{anibox_id}`)를 빼면 영상은 {fmt_int(p_ex['영상수'])}편, 조회수 중앙값은 {fmt_num(p_ex['조회수_중앙값'], 1)}회다. 전체 중앙값 {fmt_num(p_all['조회수_중앙값'], 1)}회와 비교하면 채널 하나의 무게를 볼 수 있다. 상위 10개 채널을 빼면 영상 {fmt_int(p_top['영상수'])}편, 중앙값 {fmt_num(p_top['조회수_중앙값'], 1)}회, 유효 조회수 {fmt_int(p_top['조회수_유효'])}편이다. 원본에서는 채널을 지우지 않았다. 근거는 `04_채널제외_규모.csv`.")
    a(f"4. 댓글 분석 테이블은 댓글 {fmt_int(len(comments))}건, 연결 영상 {fmt_int(int(link['댓글연결'].sum()))}편이다. 연결 구분은 {reason_txt}. AniBox 수집 댓글 점유는 {fmt_pct(c_anibox['점유율_pct'])}, 조회수 상위 10개 채널은 {fmt_pct(c_top['점유율_pct'])}, 수집 댓글 수 상위 10개 채널은 {fmt_pct(c_c10['점유율_pct'])}다. 이 셋은 서로 다른 순위다. 근거는 `06_댓글집중도.csv`.")
    a("5. 후속 인기 요소 분석은 댓글 기준, 영상 동일 비중, 채널 동일 비중을 나누고, 전체와 AniBox 제외를 같이 보도록 `07_후속_집계기준서.md`에 정의했다. 요소별 수치는 아직 계산하지 않았다.")
    a("")
    a("## 1. 원본 검증")
    a("")
    a(f"영상 파일은 {fmt_int(qc['행수'])}행, 고유 `post_id` {fmt_int(qc['고유_post_id'])}개, 중복 ID {fmt_int(qc['중복_post_id수'])}개다. `final_class`는 {qc['final_class_값']} {fmt_int(qc['A_우선포함'])}행이다. 조회수 음수 {fmt_int(qc['view_음수'])}건, 0 {fmt_int(qc['view_0'])}건, 결측 {fmt_int(qc['view_결측'])}건이다. 길이 변환은 {fmt_int(qc['duration_성공'])}건 성공, {fmt_int(qc['duration_실패'])}건 실패다. 게시 시각이 UTC인 행은 {fmt_int(qc['created_UTC(Z)'])}건, 결측 {fmt_int(qc['created_결측'])}건이다. 게시 시각이 수집 시각보다 늦은 행은 {fmt_int(qc['게시가_수집보다_늦음'])}건이다.")
    a("")
    a(f"댓글 파일은 {fmt_int(len(comments))}행, 고유 `comment_id` {fmt_int(comments['comment_id'].nunique())}개다. 같은 본문이라도 댓글 ID가 다르면 삭제하지 않았다. 댓글의 `post_id` 가운데 A 원본에 없는 ID는 {fmt_int(int((~comments['post_id'].isin(set(link['post_id']))).sum()))}건이다. 댓글 테이블 안에서 같은 영상의 채널·게시일·조회수가 서로 다른 경우는 `00_댓글테이블_영상필드_내부충돌.csv`, 원본과 다른 경우는 `00_댓글테이블_원본대조.csv`에 있다. 이후 영상 지표는 A 원본을 기준으로 했다.")
    a("")
    a(f"댓글이 연결되지 않은 영상의 구분은 상태 파일을 따랐다. {reason_txt}. 미연결을 관심 없음으로 보지 않는다. 상태 기록 없이 댓글도 없는 영상은 댓글 미연결·원인 미확인이다. {gap_sentence}")
    a("")
    a("## 2. 기존 수치")
    a("")
    a(f"재계산 판정은 일치 {fmt_int(int((verify_df['판정']=='일치').sum()))}건, 반올림 차이 {fmt_int(int(len(round_only)))}건, 불일치 {fmt_int(int(len(mismatch)))}건이다. 상위 1%는 조회수가 있는 {fmt_int(share1['N'])}편 중 {fmt_int(share1['k'])}편이고 경계 밖 동점은 {fmt_int(share1['경계밖_동점'])}편이다. 상위 10%는 {fmt_int(share10['k'])}편, 경계 밖 동점 {fmt_int(share10['경계밖_동점'])}편이다. 동점이 있으면 보조 점유도 같은 CSV에 있다.")
    a("")
    a(f"AniBox로 본 채널 ID는 `{anibox_id}` 하나다. 이름에 AniBox가 들어가는 ID는 {fmt_int(len(anibox_ids))}개라, 다른 ID를 이름만으로 빼지 않았다. 이 채널의 A 영상은 {fmt_int(anibox_n)}편, 누적조회수 {fmt_int(anibox_views)}회, 점유 {fmt_pct(anibox_share)}다.")
    a("")
    a("## 3. 2026년 10월")
    a("")
    a("월은 `created_at`을 UTC로 확인한 뒤 한국시간으로 나눈 것이다. `collected_at`을 게시일로 쓰지 않았다. 영상 ID 중복으로 행이 늘지 않았고, 10월에 게시 시각이 수집 시각보다 늦은 행은 " + fmt_int(val("게시가_수집보다_늦은_10월")) + "건이다. 중앙값은 영상별 조회수의 중앙값이다.")
    a("")
    a(f"한국시간과 UTC의 월이 다른 영상은 {fmt_int(len(month_flip))}편이다. UTC 기준 2026-10 영상 수는 {fmt_int(val('UTC_2026-10_영상수'))}편이다. 수집 시각은 {val('수집일_최소')}부터 {val('수집일_최대')}까지다.")
    a("")
    a(f"10월 영상의 경과일은 최소 {fmt_num(float(val('경과_최솟값')), 2)}일, 1사분위 {fmt_num(float(val('경과_Q1')), 1)}일, 중앙값 {fmt_num(float(val('경과_중앙값')), 1)}일, 3사분위 {fmt_num(float(val('경과_Q3')), 1)}일, 최대 {fmt_num(float(val('경과_최댓값')), 1)}일이다. 달 안에 경과일이 고르게 짧지 않다.")
    a("")
    if anibox_id is not None:
        a(f"10월 AniBox 영상은 {fmt_int(anibox_oct_n)}편이고, 10월 관측 조회수에서 {fmt_pct(anibox_oct_share)}다. 조회수 합계가 큰 채널 세 곳은 " + ", ".join(f"{r.display_name} {fmt_int(r.조회수_합계)}회" for r in top_oct.itertuples()) + "이다.")
    a("")
    a(f"10월 영상 {fmt_int(val('KST_2026-10_영상수'))}편의 수집 시각은 {val('2026-10_수집일_최소')} 한 시점이다. 10월 전체 중앙값 {fmt_num(oct_all['조회수_중앙값'], 1)}회(유효 {fmt_int(oct_all['조회수_유효'])}편), AniBox 제외 {fmt_num(oct_ex['조회수_중앙값'], 1)}회(유효 {fmt_int(oct_ex['조회수_유효'])}편), 상위 10개 채널 제외 {fmt_num(oct_top['조회수_중앙값'], 1)}회(유효 {fmt_int(oct_top['조회수_유효'])}편)다. AniBox는 이 달 조회수의 {fmt_pct(anibox_oct_share)}라 중앙값을 만들지 않는다. 고정된 상위 10개 채널을 빼도 중앙값은 15만 회대다. 높은 중앙값은 월을 잘못 자른 결과가 아니고, 이 달에 게시된 영상들의 수집 시점 누적값이다. 2026년 10월에 발생한 조회수가 아니다.")
    a("")
    a("## 4. 기간 비교")
    a("")
    a("검색 코드는 2022-01-01 00:00 한국시간부터 `치이카와`를 `regionCode=KR`, `relevanceLanguage=ko`, `order=relevance`로 월 단위 검색한다. 종료 시각은 최초 실행 시각을 진행 파일에 고정하도록 되어 있으나, 그 파일은 현재 프로젝트에서 찾지 못했다. 그래서 관측된 최초 게시일 2022-01-08과 수집 범위의 시작일은 구분한다. 최초 영상이 1월 8일이라는 이유만으로 2022년 수집이 1월 8일에 시작했다고 보지 않는다.")
    a("")
    a("분류 노트에는 `search.list` 한 쿼리의 상한이 약 500건이고 성수월은 그 상한에 가깝다는 기록이 있다. 월별 요청 로그는 찾지 못했다. 2023–2025년은 코드의 검색 창 안에 있지만, 그 해가 완전히 수집됐는지는 확인하지 못했다. 연간 증감률은 계산하지 않았다. 같은 달의 영상 수와 활동 채널 수는 `03_동월_영상수_활동채널.csv`와 `fig_동월_영상수.png`에 나란히 두었다. 같은 달이어도 누적조회수의 관측 기간이 다르므로 조회수 차이를 인기 성장률로 읽지 않는다. 2026년은 수집일 이후가 빠져 있다.")
    a("")
    a("## 5. 채널을 빼 보면")
    a("")
    a(f"전체 중앙값 {fmt_num(p_all['조회수_중앙값'], 1)}회는 유효 {fmt_int(p_all['조회수_유효'])}편이다. AniBox 제외는 {fmt_num(p_ex['조회수_중앙값'], 1)}회, 유효 {fmt_int(p_ex['조회수_유효'])}편, 채널 {fmt_int(p_ex['채널수'])}개다. 상위 10개 채널 제외는 {fmt_num(p_top['조회수_중앙값'], 1)}회, 유효 {fmt_int(p_top['조회수_유효'])}편, 채널 {fmt_int(p_top['채널수'])}개다. 좋아요율 중앙값은 전체 {fmt_pct(p_all['좋아요율_중앙값'])}(유효 {fmt_int(p_all['좋아요율_유효'])}), AniBox 제외 {fmt_pct(p_ex['좋아요율_중앙값'])}, 상위 10개 제외 {fmt_pct(p_top['좋아요율_중앙값'])}다. 길이·연도 구성은 `04_채널제외_길이.csv`, `04_채널제외_연도.csv`에 있다. 이 수치는 데이터 안 A 영상의 성과다.")
    a("")
    a("## 6. 길이와 좋아요")
    a("")
    a(f"60초 이하와 1,200초 초과의 영상 수·조회수 중앙값, 좋아요율 중앙값 {fmt_pct(like_median)}(유효 {fmt_int(like_n)}), 같은 영상의 합계 비율 {fmt_pct(like_agg)}, 조회수 100회 이상 중앙값 {fmt_pct(like100_median)}(유효 {fmt_int(like100_n)}), Spearman {fmt_num(rho, 2)}은 재검증표에 있다. 좋아요율의 분자와 분모는 둘 다 유효하고 조회수가 0보다 큰 같은 영상이다. 상관계수는 그 {fmt_int(like_n)}편으로 계산했다. 높은 계수는 같이 크다는 뜻이지 인기 이유의 증거가 아니다.")
    a("")
    a("같은 게시 연도 안의 길이 비교와 AniBox 제외 전후는 `05_길이_연도별_집단.csv`와 `fig_길이_AniBox제외.png`에 있다. 유효 영상이 30편 미만인 칸은 작은 표본으로 표시했다. 60초 이하를 Shorts로 확정하지 않았고, 길이가 조회수를 만들었다고 쓰지 않았다.")
    a("")
    a("## 7. 댓글 표본")
    a("")
    a(f"연결 영상 {fmt_int(int(link['댓글연결'].sum()))}편의 수집 댓글 상위 1%는 k={fmt_int(vid_share1['k'])}편, 경계값 {fmt_num(vid_share1['경계값'], 0)}개, 경계 밖 동점 {fmt_int(vid_share1['경계밖_동점'])}편이다. 엄격 점유는 {fmt_pct(vid_share1['엄격_점유'])}이고, 경계값 이상의 영상을 모두 넣으면 {fmt_pct(vid_share1['동점포함_점유'])}다. 상한이 100개라 경계에 동점이 많다. 분모는 댓글이 연결된 고유 영상 수다. 상위 10%의 엄격 점유는 {fmt_pct(vid_share10['엄격_점유'])}, 동점까지 넣으면 {fmt_pct(vid_share10['동점포함_점유'])}다.")
    a("")
    a("상태 파일의 `collected_count` 최댓값은 100이고 `capped` 상태가 있다. 분석 테이블에서 한 영상 댓글이 100건을 넘는지는 `06_수집댓글_100초과.csv`에 있다. 넘는 영상은 잘라내지 않았다. 정렬 순서와 실제 페이지 수는 실행된 코드가 주석 초안만 남아 확인하지 못했다. 작성자 ID와 대댓글 본문은 없다. `comment_reply_count`는 개수다.")
    a("")
    a("`comment_count`와 수집 댓글 수는 시점과 범위가 다르다. 둘의 비율을 수집률로 쓰지 않았다. 전체 댓글 대표성, 고유 이용자 수, 반복 작성자는 확인하지 못했다.")
    a("")
    a("## 8. 확인하지 못한 것")
    a("")
    a("- 검색 종료 시각을 저장한 진행 파일과 월별 검색 요청 로그.")
    a("- 2023–2025년이 검색 상한 없이 그 달의 검색 결과를 모두 담았는지.")
    a("- 댓글 API의 실제 정렬 순서와 페이지 수.")
    a("- 댓글 작성자와 대댓글 본문.")
    a("- 인기 요소 분류. 기준만 적고 수치는 계산하지 않았다.")
    a("")
    a("## 실행")
    a("")
    a("같은 폴더에서 `C:\\\\Users\\\\user\\\\anaconda3\\\\python.exe verify_A_followup_v1.py` 를 실행한다. pandas, numpy, matplotlib이 필요하다. 원본 CSV는 읽기만 한다.")
    a("")
    (OUT / "08_검증_보고서.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
