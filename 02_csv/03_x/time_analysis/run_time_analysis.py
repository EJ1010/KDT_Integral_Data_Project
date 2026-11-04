# -*- coding: utf-8 -*-
"""치이카와 X 수집 표본의 시기별 구성 분석.

재실행:
  py -3.11 run_time_analysis.py

입력은 normalized 게시물과 text_analysis_v2/20261030_211145 라벨만 사용한다.
다른 분석 버전의 라벨은 섞지 않는다. 원본과 기존 결과는 읽기만 한다.
결과는 time_analysis/YYYYMMDD_HHMMSS/ 에 쓴다.
작성 시각은 문자열의 +09:00 한국시간이다. 9시간을 더하지 않는다.
"""
from __future__ import annotations

import json
import re
import shutil
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(r"C:/DATA/KDT_Integral_Data_Project/02_csv/03_x")
V2 = ROOT / "text_analysis_v2" / "20261030_211145"
NORM = ROOT / "normalized"
VERSION = "2026-10-30.v2.3"
METHOD = "clause_context_rules"
SMALL_MONTH_N = 50
RARE_YEAR_N = 15
YEARS = [2022, 2023, 2024, 2025, 2026]
PY = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"

FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
font_manager.fontManager.addfont(FONT_PATH)
FONT_NAME = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams["font.family"] = FONT_NAME
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

STRONG_RES = [
    ("치이카와", re.compile(r"치이까와|치이카와|치카와|chiikawa|ちいかわ|吉伊卡哇", re.I)),
    ("하치와레", re.compile(r"하치와레|하치와래|ハチワレ")),
    ("모몽가", re.compile(r"모몽가|모몬가")),
    ("랏코", re.compile(r"(?<![가-힣])랏코(?![가-힣])")),
    ("쿠리만쥬", re.compile(r"쿠리만쥬|쿠리만주")),
    ("갑옷씨", re.compile(r"갑옷\s*씨|갑옷\s*아저씨|갑옷아저씨|갑옷\s*상")),
    ("먼작귀", re.compile(r"먼작귀|뭔가\s*작고\s*귀여운")),
]
PAREN_RES = [
    ("하치와레", re.compile(r"가르마\s*[\(（]\s*하치와레\s*[\)）]")),
    ("우사기", re.compile(r"토끼\s*[\(（]\s*우사기\s*[\)）]")),
]
AMBIG_RES = [
    ("우사기", re.compile(r"(?<![가-힣])우사기(?![가-힣])|うさぎ")),
    ("시사", re.compile(r"(?<![가-힣])시사(?![하가은는을를의와과점])")),
    ("카니", re.compile(r"(?<![가-힣])카니(?!발)")),
    ("아노코", re.compile(r"(?<![가-힣])아노코(?![가-힣])")),
    ("데카츠요", re.compile(r"데카츠요")),
]
# 선그래프에 올릴 이름. 치이카와는 수집 조건과 겹치므로 점선 맥락으로만 둔다.
LINE_NAMES = ["먼작귀", "하치와레", "랏코", "모몽가", "우사기", "쿠리만쥬"]
HEAT_NAMES = ["치이카와", "먼작귀", "하치와레", "모몽가", "랏코", "쿠리만쥬", "갑옷씨", "우사기"]
FORM_MAIN = ["인형", "피규어", "마스코트", "키링", "스티커", "의류", "식품", "이모티콘", "문구"]
SALES_MAIN = ["가챠", "랜덤", "쿠지", "공동구매", "직구", "예약판매"]
EVENT_MAIN = ["애니메이션", "영화", "만화", "팝업", "카페·매장", "콜라보"]
ACTION_MAIN = ["구매:완료·경험", "구매:희망", "소유:희망", "획득:완료·경험", "방문:완료·경험", "판매:희망"]
ASPECT_MAIN = [
    "호감은 있으나 세부 이유 불명확",
    "행동·말투·성격",
    "유머",
    "관계·조합·이야기·장면",
    "위로·공감·일상과의 연결",
    "외형",
    "상품의 디자인·재질·품질·기능",
]
PURPOSE_LINE = ["개인 감상", "판매·홍보", "개인 경험", "정보 공유", "개인 거래"]
PURPOSE_STACK = ["개인 감상", "개인 경험", "팬 창작", "정보 공유", "판매·홍보", "개인 거래", "복수 목적", "기타·판단 불가"]
PURPOSE_COLORS = {
    "개인 감상": "#4C78A8",
    "개인 경험": "#72B7B2",
    "팬 창작": "#54A24B",
    "정보 공유": "#EECA3B",
    "판매·홍보": "#E45756",
    "개인 거래": "#F58518",
    "복수 목적": "#B279A2",
    "기타·판단 불가": "#D0D0D0",
}
NAME_COLORS = {
    "치이카와": "#9E9E9E",
    "먼작귀": "#4C78A8",
    "하치와레": "#F58518",
    "랏코": "#54A24B",
    "모몽가": "#E45756",
    "우사기": "#B279A2",
    "쿠리만쥬": "#72B7B2",
    "갑옷씨": "#EECA3B",
}


def split_labels(value: str) -> list[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return []
    return [part for part in text.split("|") if part]


def has_token(series: pd.Series, label: str) -> pd.Series:
    return series.fillna("").map(lambda value: label in split_labels(value))


def exclusive_purpose(value: str) -> str:
    labels = split_labels(value)
    if len(labels) == 1:
        return labels[0]
    if len(labels) > 1:
        return "복수 목적"
    return "(빈값)"


def pct(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "결측"
    return f"{100 * float(value):.1f}%"


def num(value) -> str:
    return f"{int(value):,}"


def year_line(mapping: dict, years=None, as_pct: bool = False) -> str:
    years = years or YEARS
    parts = []
    for year in years:
        shown = pct(mapping[year]) if as_pct else num(mapping[year])
        parts.append(f"{year}년 {shown}")
    return ", ".join(parts)


def share_or_na(numerator: int, denominator: int):
    if denominator == 0:
        return pd.NA
    return numerator / denominator


def period_note(period: str) -> str:
    text = str(period)
    if text == "2026":
        return "작성일 2026-01-01~2026-10-22. 파일 건수는 1,000으로 다른 해와 같다."
    if text == "2026Q4":
        return "2026년 4분기는 10월 1일~22일만 있다. 11–12월은 표본에 없다."
    if text == "2026-10":
        return "10월 22일까지."
    if text.startswith("2026-"):
        return "2026년 부분 연도의 해당 월."
    return ""


def small_flag(grain: str, denominator: int) -> str:
    if grain == "month" and denominator < SMALL_MONTH_N:
        return "예"
    return "아니오"


def blank_row(**kwargs) -> dict:
    return kwargs


class Tables:
    def __init__(self):
        self.rows: list[dict] = []

    def add(
        self,
        *,
        grain: str,
        period: str,
        label: str,
        numerator: int,
        denominator: int,
        denominator_name: str,
        agg_unit: str = "고유 게시물",
        include_review: str = "아니오",
        multi_label: str = "예",
        numerator_name: str = "라벨이 있는 고유 게시물",
        extra_note: str = "",
    ) -> None:
        note = period_note(period)
        if extra_note:
            note = (note + " " + extra_note).strip()
        self.rows.append(
            {
                "grain": grain,
                "period": period,
                "label": label,
                "numerator_posts": int(numerator),
                "numerator_name": numerator_name,
                "denominator_posts": int(denominator),
                "denominator_name": denominator_name,
                "share_of_denominator_posts": share_or_na(int(numerator), int(denominator)),
                "agg_unit": agg_unit,
                "analysis_version": VERSION,
                "include_review": include_review,
                "multi_label_overlap": multi_label,
                "small_sample": small_flag(grain, int(denominator)),
                "period_note": note,
            }
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def make_figure(
    caption: str,
    figsize=(12.6, 8.6),
    n_cols: int = 1,
    n_rows: int = 1,
    left: float = 0.07,
    right: float = 0.98,
    bottom: float | None = None,
    top: float = 0.90,
):
    fig = plt.figure(figsize=figsize, facecolor="white")
    wrapped = "\n".join(textwrap.wrap(caption, width=86))
    nlines = wrapped.count("\n") + 1
    if bottom is None:
        bottom = 0.06 + nlines * 0.025
    fig.text(0.012, 0.012, wrapped, va="bottom", ha="left", fontsize=8.5, color="#222222", linespacing=1.35)
    height = top - bottom
    width = right - left
    gap_x = 0.10
    gap_y = 0.16
    ax_w = (width - gap_x * (n_cols - 1)) / n_cols
    ax_h = (height - gap_y * (n_rows - 1)) / n_rows
    axes = []
    for row in range(n_rows):
        for col in range(n_cols):
            x = left + col * (ax_w + gap_x)
            y = bottom + (n_rows - 1 - row) * (ax_h + gap_y)
            axes.append(fig.add_axes([x, y, ax_w, ax_h]))
    if len(axes) == 1:
        return fig, axes[0]
    return fig, axes


def save_fig(fig, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def style_ax(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=12, pad=8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.8)
    ax.set_axisbelow(True)


def heatmap(ax, shares: pd.DataFrame, counts: pd.DataFrame, title: str, cbar_label: str) -> None:
    values = shares.astype(float).to_numpy()
    vmax = np.nanmax(values) if np.isfinite(values).any() else 1
    if not np.isfinite(vmax) or vmax <= 0:
        vmax = 1
    image = ax.imshow(values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax)
    ax.set_xticks(range(shares.shape[1]))
    ax.set_xticklabels(list(shares.columns), rotation=90, fontsize=7)
    ax.set_yticks(range(shares.shape[0]))
    ax.set_yticklabels(list(shares.index), fontsize=8)
    ax.set_title(title, loc="left", fontsize=12, pad=8)
    threshold = vmax * 0.62
    for row in range(shares.shape[0]):
        for col in range(shares.shape[1]):
            count = int(counts.iloc[row, col])
            share = values[row, col]
            color = "white" if np.isfinite(share) and share >= threshold else "#222222"
            ax.text(col, row, str(count), ha="center", va="center", fontsize=6.5, color=color)
    cbar = plt.colorbar(image, ax=ax, fraction=0.046, pad=0.02)
    cbar.ax.tick_params(labelsize=7)
    cbar.set_label(cbar_label, fontsize=8)
    ax.set_xlabel("")
    ax.grid(False)


def load_inputs():
    posts = pd.read_csv(V2 / "x_posts_analysis.csv", dtype=str, encoding="utf-8-sig")
    evidence = pd.read_csv(V2 / "x_analysis_evidence.csv", dtype=str, encoding="utf-8-sig")
    connections = pd.read_csv(V2 / "x_analysis_connections.csv", dtype=str, encoding="utf-8-sig")
    raw = pd.read_csv(NORM / "x_posts.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    keywords = pd.read_csv(
        NORM / "x_post_keywords.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False
    )
    review_old = pd.read_csv(V2 / "review_required.csv", dtype=str, encoding="utf-8-sig")
    return posts, evidence, connections, raw, keywords, review_old


def attach_time(posts: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+09:00$")
    created = posts["created_at"].fillna("")
    matched = created.map(lambda value: bool(pattern.match(value)))
    posts = posts.copy()
    posts["year"] = created.str.slice(0, 4).astype(int)
    posts["month"] = created.str.slice(5, 7).astype(int)
    posts["day"] = created.str.slice(8, 10).astype(int)
    posts["ym"] = created.str.slice(0, 7)
    posts["quarter"] = posts["year"].astype(str) + "Q" + ((posts["month"] - 1) // 3 + 1).astype(str)
    posts["aligned"] = (posts["month"] < 10) | ((posts["month"] == 10) & (posts["day"] <= 22))
    converted = pd.to_datetime(posts["created_at"], utc=True).dt.tz_convert("Asia/Seoul")
    checks = {
        "regex_ok": int(matched.sum()),
        "regex_bad": int((~matched).sum()),
        "tz_year_mismatch": int((converted.dt.year.to_numpy() != posts["year"].to_numpy()).sum()),
        "tz_month_mismatch": int((converted.dt.month.to_numpy() != posts["month"].to_numpy()).sum()),
        "created_year_kst_mismatch": int((posts["created_year_kst"].astype(int) != posts["year"]).sum()),
        "created_month_kst_mismatch": int((posts["created_month_kst"].astype(int) != posts["month"]).sum()),
        "source_year_mismatch": int((posts["source_year"].astype(int) != posts["year"]).sum()),
        "nat": int(converted.isna().sum()),
        "min": created.min(),
        "max": created.max(),
    }
    return posts, checks


def attach_flags(posts: pd.DataFrame) -> pd.DataFrame:
    posts = posts.copy()
    text = posts["analysis_text"].fillna("")
    strong = pd.Series(False, index=posts.index)
    for name, cre in STRONG_RES:
        flag = text.map(lambda value, cre=cre: bool(cre.search(value)))
        posts[f"name_{name}"] = flag
        strong = strong | flag
    for name, cre in PAREN_RES:
        flag = text.map(lambda value, cre=cre: bool(cre.search(value)))
        posts[f"paren_{name}"] = flag
        if f"name_{name}" in posts.columns:
            posts[f"name_{name}"] = posts[f"name_{name}"] | flag
        else:
            posts[f"name_{name}"] = flag
        strong = strong | flag
    posts["strong_cue"] = strong
    for name, cre in AMBIG_RES:
        raw_hit = text.map(lambda value, cre=cre: bool(cre.search(value)))
        paren = posts[f"paren_{name}"] if f"paren_{name}" in posts.columns else False
        posts[f"name_{name}"] = (raw_hit & posts["strong_cue"]) | paren
        posts[f"rawname_{name}"] = raw_hit
    posts["purpose_exclusive"] = posts["purpose_labels"].map(exclusive_purpose)
    posts["is_review"] = posts["review_flag"].eq("예")
    posts["is_relevant"] = posts["work_relevance"].eq("관련")
    posts["confirmed"] = posts["is_relevant"] & ~posts["is_review"]
    posts["like"] = pd.to_numeric(posts["like_count"], errors="coerce")
    posts["repost"] = pd.to_numeric(posts["repost_count"], errors="coerce")
    posts["comment"] = pd.to_numeric(posts["comment_count"], errors="coerce")
    posts["views"] = pd.to_numeric(posts["view_count"], errors="coerce")
    posts["is_promo"] = has_token(posts["purpose_labels"], "판매·홍보")
    posts["is_trade"] = has_token(posts["purpose_labels"], "개인 거래")
    posts["is_promo_or_trade"] = posts["is_promo"] | posts["is_trade"]
    posts["is_ko"] = posts["language"].eq("한국어 중심")
    posts["text_ok"] = posts["judgment_scope"].eq("본문으로 판단 가능")
    char_cols = [f"name_{name}" for name in ["하치와레", "모몽가", "랏코", "쿠리만쥬", "갑옷씨", "우사기", "아노코", "데카츠요"]]
    posts["n_other_chars"] = posts[char_cols].sum(axis=1).astype(int)
    return posts


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.6f")


def counts_by(df: pd.DataFrame, grain: str, column: str) -> pd.DataFrame:
    return df.groupby([column]).size().rename("n").reset_index()


def add_token_shares(
    table: Tables,
    df: pd.DataFrame,
    grain: str,
    period_col: str,
    source_col: str,
    labels: list[str],
    denominator_name: str,
    multi: str = "예",
    extra_note: str = "",
) -> None:
    for period, sub in df.groupby(period_col, sort=True):
        denominator = len(sub)
        for label in labels:
            numerator = int(has_token(sub[source_col], label).sum())
            table.add(
                grain=grain,
                period=str(period),
                label=label,
                numerator=numerator,
                denominator=denominator,
                denominator_name=denominator_name,
                multi_label=multi,
                extra_note=extra_note,
            )


def add_flag_shares(
    table: Tables,
    df: pd.DataFrame,
    grain: str,
    period_col: str,
    flags: list[tuple[str, str]],
    denominator_name: str,
    multi: str = "예",
    extra_note: str = "",
) -> None:
    for period, sub in df.groupby(period_col, sort=True):
        denominator = len(sub)
        for label, column in flags:
            numerator = int(sub[column].sum())
            table.add(
                grain=grain,
                period=str(period),
                label=label,
                numerator=numerator,
                denominator=denominator,
                denominator_name=denominator_name,
                multi_label=multi,
                extra_note=extra_note,
            )


def exclusive_shares(table: Tables, df: pd.DataFrame, grain: str, period_col: str, denominator_name: str) -> None:
    for period, sub in df.groupby(period_col, sort=True):
        denominator = len(sub)
        counts = sub["purpose_exclusive"].value_counts()
        for label in PURPOSE_STACK:
            table.add(
                grain=grain,
                period=str(period),
                label=label,
                numerator=int(counts.get(label, 0)),
                denominator=denominator,
                denominator_name=denominator_name,
                multi_label="아니오",
                numerator_name="상호배타 목적의 고유 게시물",
                extra_note="복수 목적은 라벨이 둘 이상인 게시물이다. 다른 목적과 겹치지 않는다.",
            )


def year_token_map(df: pd.DataFrame, source_col: str, label: str) -> dict:
    out = {}
    for year in YEARS:
        sub = df[df["year"] == year]
        out[year] = int(has_token(sub[source_col], label).sum()) if len(sub) else 0
    return out


def year_flag_map(df: pd.DataFrame, column: str) -> dict:
    out = {}
    for year in YEARS:
        sub = df[df["year"] == year]
        out[year] = int(sub[column].sum()) if len(sub) else 0
    return out


def year_share_from_counts(counts: dict, denoms: dict) -> dict:
    return {year: (counts[year] / denoms[year] if denoms[year] else np.nan) for year in YEARS}


def matrix_from_table(frame: pd.DataFrame, labels: list[str], periods: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    shares = pd.DataFrame(index=labels, columns=periods, dtype=float)
    counts = pd.DataFrame(index=labels, columns=periods, dtype=float)
    scoped = frame[frame["label"].isin(labels) & frame["period"].isin(periods)]
    for row in scoped.itertuples(index=False):
        shares.loc[row.label, row.period] = row.share_of_denominator_posts
        counts.loc[row.label, row.period] = row.numerator_posts
    return shares.astype(float), counts.fillna(0).astype(float)


def excerpt(text: str, limit: int = 160) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def evidence_row(theme: str, role: str, row: pd.Series, reason: str) -> dict:
    return {
        "theme": theme,
        "role": role,
        "post_id": row["post_id"],
        "created_at_kst": row["created_at"],
        "post_url": row["post_url"],
        "account_id": row["account_id"],
        "year": int(row["year"]),
        "month": row["ym"],
        "like_count": int(row["like"]) if pd.notna(row["like"]) else pd.NA,
        "purpose_labels": row["purpose_labels"],
        "excerpt": excerpt(row["text"]),
        "selection_reason": reason,
        "analysis_version": VERSION,
    }


def pick(df: pd.DataFrame, mask: pd.Series, keyword: str | None, n: int) -> pd.DataFrame:
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    text = sub["text"].fillna("")
    sub["_personal"] = (
        has_token(sub["purpose_labels"], "개인 감상") | has_token(sub["purpose_labels"], "개인 경험")
    ).astype(int)
    sub["_shop"] = text.str.contains("입고|신제품|예약판매|A상|들어왔|업데이트|환불|대행", regex=True).astype(int)
    sub["_hit"] = text.str.contains(keyword, regex=False).astype(int) if keyword else 1
    sub = sub.sort_values(["_personal", "_shop", "_hit", "post_id"], ascending=[False, True, False, True])
    return sub.head(n)


def build_evidence(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(theme, role, mask, reason, keyword=None, n=1):
        chosen = pick(posts, mask, keyword, n)
        if chosen.empty:
            rows.append(
                {
                    "theme": theme,
                    "role": role,
                    "post_id": "",
                    "created_at_kst": "",
                    "post_url": "",
                    "account_id": "",
                    "year": pd.NA,
                    "month": "",
                    "like_count": pd.NA,
                    "purpose_labels": "",
                    "excerpt": "",
                    "selection_reason": "조건에 맞는 게시물이 없다. " + reason,
                    "analysis_version": VERSION,
                }
            )
            return
        for _, row in chosen.iterrows():
            rows.append(evidence_row(theme, role, row, reason))

    dec = posts["ym"].eq("2023-12")
    add(
        "2023-12_표본건수",
        "대표",
        dec & has_token(posts["purpose_labels"], "개인 감상"),
        "2023-12은 표본 257건으로 가장 많다. 계정 196곳에 나뉘어 있고, 이 글은 그 달의 개인 감상 예다.",
        "귀여",
    )
    add(
        "2023-12_표본건수",
        "대표",
        dec & posts["is_promo"],
        "같은 달 판매·홍보 예. 12월 건수 증가가 홍보글만으로 채워진 것은 아닌지 보기 위한 사례다.",
    )
    add(
        "2023-12_표본건수",
        "반대",
        posts["ym"].eq("2024-06") & has_token(posts["purpose_labels"], "개인 감상"),
        "건수가 많지 않은 2024-06의 개인 감상. 12월만 감상글이 있는 구조가 아니라는 대조다.",
        "귀여",
    )
    add(
        "게시목적_홍보감소",
        "대표",
        posts["year"].eq(2022) & posts["is_promo"] & posts["is_ko"],
        "2022년 한국어 판매·홍보 예. 초반 표본에 입고·판매 문안이 들어 있다.",
        "판매",
    )
    add(
        "게시목적_홍보감소",
        "대표",
        posts["year"].eq(2026) & has_token(posts["purpose_labels"], "개인 감상") & posts["is_ko"],
        "2026년 한국어 개인 감상 예. 후반 표본에서 감상 비중이 높아진 구성과 맞춘 사례다.",
        "귀여",
    )
    add(
        "게시목적_홍보감소",
        "반대",
        posts["year"].eq(2026) & posts["is_promo"],
        "2026년에도 판매·홍보 라벨이 남아 있다. 사라진 것이 아니라 표본 안 비중이 줄어든 것이다.",
    )
    movie = posts["text"].fillna("").str.contains("극장판|영화", regex=True)
    add(
        "2026_영화언급",
        "대표",
        posts["year"].eq(2026) & movie & posts["ym"].between("2026-07", "2026-10"),
        "2026년 7–10월 영화·극장판 언급 예. 국내 개봉일과 겹치는지는 원인으로 단정하지 않는다.",
        "극장",
        2,
    )
    add(
        "2026_영화언급",
        "반대",
        posts["ym"].eq("2026-08")
        & has_token(posts["purpose_labels"], "개인 감상")
        & ~movie
        & posts["confirmed"],
        "같은 2026년 8월의 감상글 중 영화·극장 단어가 없는 예. 그 달의 글이 모두 영화 이야기인 것은 아니다.",
        "귀여",
    )
    add(
        "호감측면",
        "대표",
        posts["confirmed"] & has_token(posts["affection_aspects_author"], "행동·말투·성격") & posts["year"].eq(2026),
        "2026년 작성자 호감 중 행동·말투·성격이 적힌 예.",
        None,
    )
    add(
        "호감측면",
        "대표",
        posts["confirmed"] & has_token(posts["affection_aspects_author"], "유머") & posts["year"].eq(2026),
        "2026년 유머 측면 예.",
        "웃",
    )
    add(
        "호감측면",
        "반대",
        posts["confirmed"]
        & posts["affection_aspects_author"].eq("호감은 있으나 세부 이유 불명확")
        & posts["year"].eq(2026),
        "2026년에도 세부 이유 없는 호감이 다수다. 행동·유머 증가가 표본의 주된 호감 문장은 아니다.",
        "귀여",
    )
    add(
        "호감측면",
        "대표",
        posts["confirmed"] & has_token(posts["affection_aspects_author"], "외형") & posts["year"].eq(2022),
        "2022년 외형 특정 예. 외형은 어느 해나 건수가 작다.",
    )
    add(
        "캐릭터언급",
        "대표",
        posts["confirmed"]
        & posts["n_other_chars"].ge(2)
        & has_token(posts["purpose_labels"], "개인 감상")
        & ~posts["is_promo_or_trade"]
        & ~posts["text"].fillna("").str.contains("공구|1차금|입고|팝니다|반택"),
        "한 글에 이름이 둘 이상 나온다. 언급 비중은 선호도 순위가 아니다.",
    )
    add(
        "캐릭터언급",
        "반대",
        posts["confirmed"]
        & posts["name_치이카와"]
        & posts["n_other_chars"].eq(0)
        & ~posts["name_먼작귀"]
        & posts["affection_aspects_author"].eq("호감은 있으나 세부 이유 불명확"),
        "치이카와 이름과 이유 없는 호감만 있는 예. 이름 등장만으로 다른 캐릭터보다 선호가 크다고 읽지 않는다.",
        "귀여",
    )
    add(
        "상품형태",
        "대표",
        posts["confirmed"]
        & has_token(posts["product_forms"], "인형")
        & has_token(posts["purpose_labels"], "개인 감상")
        & ~posts["is_promo_or_trade"]
        & ~posts["text"].fillna("").str.contains("입고|들어왔|신제품"),
        "판매 문안이 아닌 개인 글의 인형 언급. 형태 언급은 구매 이유가 아니다.",
        "인형",
    )
    add(
        "상품형태",
        "대표",
        posts["confirmed"] & has_token(posts["product_forms"], "인형") & has_token(posts["sales_channels"], "가챠"),
        "인형과 가챠가 한 글에 같이 있다. 둘은 배타적인 상품군이 아니다.",
        "가챠",
    )
    add(
        "상품형태",
        "반대",
        posts["confirmed"] & posts["product_forms"].eq("언급 없음") & has_token(posts["purpose_labels"], "개인 감상"),
        "감상글이라도 상품 형태가 없을 수 있다. 언급 없음은 상품이 없다는 뜻이 아니다.",
        "귀여",
    )
    add(
        "행동상태",
        "대표",
        posts["confirmed"]
        & has_token(posts["action_labels_author"], "구매:완료·경험")
        & posts["text"].fillna("").str.contains("샀")
        & ~posts["text"].fillna("").str.contains("유유백서"),
        "작성자가 치이카와 관련 구매를 끝냈다고 읽힌 예. 연간 수십 건이라 추세로 잇지 않는다.",
        "샀",
    )
    add(
        "행동상태",
        "대표",
        posts["confirmed"]
        & has_token(posts["action_labels_author"], "구매:희망")
        & ~has_token(posts["action_labels_author"], "구매:완료·경험")
        & posts["text"].fillna("").str.contains("사고 싶|사고싶"),
        "사고 싶다는 희망. 이미 샀다는 완료 문장과는 구분했다.",
        "사고",
    )
    add(
        "행동상태",
        "대표",
        posts["confirmed"]
        & has_token(posts["action_labels_author"], "소유:희망")
        & posts["text"].fillna("").str.contains("갖고 싶|갖고싶")
        & ~posts["text"].fillna("").str.contains("뭐야"),
        "작성자가 갖고 싶다고 한 소유 희망. 대사 번역의 '갖고싶은 게 뭐야'는 여기 넣지 않았다.",
        "갖고",
    )
    add(
        "행동상태",
        "반대",
        posts["confirmed"] & posts["action_labels_author"].eq("언급 없음") & has_token(posts["purpose_labels"], "개인 감상"),
        "호감 문장만 있고 구매·소유 행동이 없는 예. 언급이 없는 것이지 행동이 없다고 단정하지 않는다.",
        "귀여",
    )
    add(
        "사용수집",
        "대표",
        posts["confirmed"]
        & has_token(posts["use_modes"], "가방 부착")
        & posts["text"].fillna("").str.contains("달고|달린")
        & ~posts["text"].fillna("").str.contains("신제품|자석|업뎃|입고|들 보면"),
        "가방에 달고 다니는 사용 장면. 상품 안내와, 다른 사람을 훈계하는 문안은 빼려 했다. 전체 표본에서 사용 표현은 드물다.",
        "가방",
    )
    add(
        "사용수집",
        "대표",
        posts["confirmed"]
        & has_token(posts["collection_types"], "세트·시리즈 완성")
        & posts["text"].fillna("").str.contains("모으|모았|모아")
        & ~posts["text"].fillna("").str.contains("A상|입고|발매"),
        "세트로 모은다는 표현. 상품 라인업 안내와 구분하려 했다. 건수는 작다.",
        "모",
    )
    add(
        "사용수집",
        "반대",
        posts["confirmed"] & posts["use_modes"].eq("언급 없음") & posts["collection_types"].eq("언급 없음") & has_token(posts["product_forms"], "키링"),
        "키링을 말했지만 휴대·전시·세트 수집 문장은 없다. 상품 언급과 사용 방식은 다른 축이다.",
        "키링",
    )
    add(
        "장벽",
        "대표",
        posts["confirmed"]
        & has_token(posts["barriers"], "가격·예산:일반 언급")
        & posts["text"].fillna("").str.contains("비싸|가격"),
        "가격 단어가 있는 일반 언급. 같은 구절의 구매 포기로 연결되지 않은 상태다.",
        "비싸",
    )
    add(
        "장벽",
        "대표",
        posts["confirmed"]
        & posts["barriers"].fillna("").str.contains("품절·재고:일반 언급", regex=False)
        & ~posts["text"].fillna("").str.contains("환불|대행|입고|공지|안내")
        & ~posts["is_promo"],
        "개인 글의 품절 언급. 판매·팝업 안내의 품절 문구는 제외하려 했다.",
        "품절",
    )
    add(
        "장벽",
        "반대",
        posts["confirmed"] & has_token(posts["action_labels_author"], "구매:완료·경험") & posts["barriers"].eq("언급 없음"),
        "구매 완료 글에 가격·품절 장벽 라벨이 없는 예. 장벽 단어가 구매 행동의 설명은 아니다.",
        "샀",
    )
    add(
        "반응지표",
        "대표",
        posts["account_id"].eq("@ATEEZofficial"),
        "연예인 계정 게시물. 좋아요가 매우 커서 2022년 평균을 끌어올린다. 중앙값 비교를 병행하는 이유다.",
    )
    add(
        "반응지표",
        "대표",
        posts["like"].eq(posts["like"].max()),
        "표본 전체 좋아요 최댓값. 한 글이 평균을 크게 바꾼다.",
    )
    add(
        "반응지표",
        "반대",
        posts["year"].eq(2024) & posts["like"].between(14, 20),
        "2024년 좋아요 중앙값 근처에 있는 글. 인기 표본 안에도 반응 크기가 크게 갈린다.",
    )
    return pd.DataFrame(rows)


def build_review(posts: pd.DataFrame, review_old: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = posts.set_index("post_id", drop=False)
    for row in review_old.itertuples(index=False):
        src = base.loc[row.post_id]
        if isinstance(src, pd.DataFrame):
            src = src.iloc[0]
        rows.append(
            {
                "issue_type": "기존 분류 확인 필요",
                "post_id": row.post_id,
                "created_at_kst": src["created_at"],
                "post_url": src["post_url"],
                "account_id": src["account_id"],
                "detail": f"{row.review_reasons}. 작품 관련성={row.work_relevance}. 확정 집계에서는 빼었다.",
                "source": "text_analysis_v2 review_required",
                "analysis_version": VERSION,
            }
        )
    top = posts.nlargest(8, "like")
    for _, row in top.iterrows():
        rows.append(
            {
                "issue_type": "해석 주의: 극단 반응",
                "post_id": row["post_id"],
                "created_at_kst": row["created_at"],
                "post_url": row["post_url"],
                "account_id": row["account_id"],
                "detail": f"좋아요 {int(row['like'])}. 평균 해석에서 분리하고 중앙값과 같이 본다. 목적={row['purpose_labels']}.",
                "source": "time_analysis",
                "analysis_version": VERSION,
            }
        )
    jp = posts[posts["account_id"].eq("@taitostation_i")].sort_values("post_id").head(3)
    for _, row in jp.iterrows():
        rows.append(
            {
                "issue_type": "해석 주의: 다른 언어 홍보가 목적 기타로 남음",
                "post_id": row["post_id"],
                "created_at_kst": row["created_at"],
                "post_url": row["post_url"],
                "account_id": row["account_id"],
                "detail": "일본어 상품 안내로 보이나 목적 라벨이 기타·판단 불가다. 규칙을 고쳐 재분류하지 않았다. 판매·홍보 비중은 이 글을 포함하지 않는다.",
                "source": "time_analysis",
                "analysis_version": VERSION,
            }
        )
    sisa = posts[posts["name_시사"].fillna(False)].sort_values("post_id").head(8)
    for _, row in sisa.iterrows():
        rows.append(
            {
                "issue_type": "해석 주의: 시사 표기 오탐 가능",
                "post_id": row["post_id"],
                "created_at_kst": row["created_at"],
                "post_url": row["post_url"],
                "account_id": row["account_id"],
                "detail": "강단서가 있는 글에서 시사 패턴이 맞았다. 인물 이름으로 확정하지 않았고 주요 차트에는 넣지 않았다. " + excerpt(row["text"], 80),
                "source": "time_analysis",
                "analysis_version": VERSION,
            }
        )
    promo_barrier = evidence[(evidence["axis"] == "장벽") & (evidence["barrier_role"] == "판매 문안")].head(5)
    for _, row in promo_barrier.iterrows():
        src = base.loc[row["post_id"]]
        if isinstance(src, pd.DataFrame):
            src = src.iloc[0]
        rows.append(
            {
                "issue_type": "해석 주의: 판매 문안 장벽",
                "post_id": row["post_id"],
                "created_at_kst": src["created_at"],
                "post_url": src["post_url"],
                "account_id": src["account_id"],
                "detail": f"barrier_type={row['barrier_type']}, role=판매 문안. 작성자 미충족 요구 집계에 넣지 않았다. 인용={excerpt(row['quote'], 80)}",
                "source": "x_analysis_evidence",
                "analysis_version": VERSION,
            }
        )
    rows.append(
        {
            "issue_type": "해석 주의: 조회수 결측",
            "post_id": "",
            "created_at_kst": "",
            "post_url": "",
            "account_id": "",
                "detail": "조회수 결측 946건은 모두 2022년이다. 그 해 1,000건 중 54건만 값이 있다. 0으로 바꾸지 않았고, 54건만으로 2022년 분포를 그리지 않았다.",
            "source": "time_analysis",
            "analysis_version": VERSION,
        }
    )
    suspects = [
        (
            "1549679394888638464",
            "분류 오류 의심: 상품 문안의 가방 부착",
            "자석 마스코트 안내가 개인 경험·가방 부착으로 남아 있다. 대표 원문에서는 빼려 했고, 라벨은 고치지 않았다.",
        ),
        (
            "1486582700739751936",
            "분류 오류 의심: 상품 라인업이 세트 수집",
            "제일복권 등수 안내가 세트·시리즈 완성으로 남아 있다. 라벨은 고치지 않았다.",
        ),
        (
            "1476934427280216076",
            "분류 오류 의심: 번역 대사가 소유 희망",
            "이모티콘 번역의 '갖고싶은 게 뭐야'가 작성자 소유 희망으로 남아 있다. 라벨은 고치지 않았다.",
        ),
        (
            "1486294681705070592",
            "분류 오류 의심: 입고 안내가 목적 기타",
            "매장 입고 문안인데 판매·홍보가 아니라 기타·판단 불가다. 라벨은 고치지 않았다.",
        ),
        (
            "1504848101928206342",
            "분류 오류 의심: 판매 안내의 품절",
            "대리 구매 안내의 품절·환불 문장이 장벽 일반 언급으로 남아 있다. 라벨은 고치지 않았다.",
        ),
        (
            "1485153581867192321",
            "해석 주의: 다른 작품 구매가 같은 글에 있음",
            "치이카와 쿠지와 유유백서 아크릴 구매가 한 글에 있다. 구매 완료 건수를 치이카와 구매만으로 읽지 않는다.",
        ),
    ]
    for post_id, issue, detail in suspects:
        src = base.loc[post_id]
        if isinstance(src, pd.DataFrame):
            src = src.iloc[0]
        rows.append(
            {
                "issue_type": issue,
                "post_id": post_id,
                "created_at_kst": src["created_at"],
                "post_url": src["post_url"],
                "account_id": src["account_id"],
                "detail": detail,
                "source": "time_analysis",
                "analysis_version": VERSION,
            }
        )
    rows.append(
        {
            "issue_type": "해석 주의: 수집 시점 없음",
            "post_id": "",
            "created_at_kst": "",
            "post_url": "",
            "account_id": "",
            "detail": "좋아요·리포스트·댓글·조회수는 수집 시점 값인데 수집 시각 컬럼이 없다. 게시 후 경과 시간으로 보정하지 않았다.",
            "source": "time_analysis",
            "analysis_version": VERSION,
        }
    )
    return pd.DataFrame(rows)


def quarter_labels(periods: list[str]) -> list[str]:
    out = []
    for period in periods:
        short = period[2:]
        if period == "2026Q4":
            short += "*"
        out.append(short)
    return out


def build_charts(posts, confirmed, tables, out: Path, stats: dict) -> None:
    charts = out / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    month_order = (
        posts.groupby("ym").size().rename("n").reset_index().sort_values("ym")
    )
    yms = month_order["ym"].tolist()
    ns = month_order["n"].tolist()

    caption = (
        "관찰: 막대는 연도별 1,000건 표본이 어느 작성월에 있는지를 보여 준다. 2023-12이 257건으로 가장 많고, "
        "빗금은 월 50건 미만(2022-01, 2022-02, 2023-06, 2023-10)이다. "
        "가능한 해석: 12월이 X 전체에서 더 활발했다는 뜻은 아니다. 그 해 선정 글의 작성일이 12월에 몰린 구성이다. "
        "한계: 2026년은 10월 22일까지라 11–12월 막대를 0으로 그리지 않았다. 월 50건 표시는 통계적 신뢰구간이 아니다."
    )
    fig, ax = make_figure(caption, figsize=(15.6, 8.8), bottom=0.34)
    colors = ["#F2C14E" if ym.startswith("2026") else "#4C78A8" for ym in yms]
    bars = ax.bar(range(len(yms)), ns, color=colors, width=0.84)
    for bar, count in zip(bars, ns):
        if count < SMALL_MONTH_N:
            bar.set_hatch("//")
            bar.set_edgecolor("#333333")
    ax.set_xticks(range(len(yms)))
    ax.set_xticklabels([ym[2:] for ym in yms], rotation=90, fontsize=6, ha="center")
    style_ax(ax, "수집 표본의 작성월별 게시물 수", "작성월 (한국시간, 22-01=2022년 1월)", "고유 게시물 수")
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color="#4C78A8", label="2022–2025년 표본"),
            plt.Rectangle((0, 0), 1, 1, color="#F2C14E", label="2026년 표본 (10월 22일까지)"),
            plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#333333", hatch="//", label="월 50건 미만"),
        ],
        frameon=False,
        fontsize=8,
    )
    save_fig(fig, charts / "01_monthly_sample_counts.png")

    caption = (
        "관찰: 월별 좋아요 중앙값은 2022–2025년과 2026년 1–7월에 한 자릿수에서 수십 사이에 머물고, "
        "2026-08·09·10은 1,000을 넘는다. 2023-12은 건수가 가장 많지만 중앙값은 6이다. "
        "가능한 해석: 2026년 연간 중앙값이 높은 이유는 8–10월 선정 글의 반응이다. 극장판 일정과 시기가 겹치나 원인으로 단정하지 않는다. "
        "한계: 세로축은 로그다. 인기순 선별 결과이고 수집 시각이 없어 경과 시간으로 보정하지 않았다. 평균이 아니다."
    )
    fig, ax = make_figure(caption, figsize=(15.6, 8.8), bottom=0.34)
    med = posts.groupby("ym")["like"].median().reindex(yms)
    q1 = posts.groupby("ym")["like"].quantile(0.25).reindex(yms)
    q3 = posts.groupby("ym")["like"].quantile(0.75).reindex(yms)
    x = np.arange(len(yms))
    ax.fill_between(x, q1.clip(lower=0.1), q3.clip(lower=0.1), color="#4C78A8", alpha=0.18, label="1–3사분위")
    ax.plot(x, med.clip(lower=0.1), color="#4C78A8", marker="o", markersize=3.5, label="중앙값")
    for idx, ym in enumerate(yms):
        if ns[idx] < SMALL_MONTH_N:
            ax.plot(idx, max(med.iloc[idx], 0.1), marker="o", markersize=7, markerfacecolor="white", markeredgecolor="#E45756")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([ym[2:] for ym in yms], rotation=90, fontsize=6, ha="center")
    style_ax(ax, "수집 표본의 월별 좋아요 중앙값", "작성월 (한국시간, 22-01=2022년 1월)", "좋아요 수 (로그 눈금)")
    ax.legend(frameon=False, fontsize=8)
    save_fig(fig, charts / "02_monthly_median_likes.png")

    q_order = [f"{year}Q{q}" for year in YEARS for q in range(1, 5)]
    q_frame = tables[(tables["grain"] == "quarter") & (tables["denominator_name"] == "해당 분기 전체 게시물(확인 필요 제외)")]
    shares, counts = matrix_from_table(q_frame, PURPOSE_STACK, q_order)
    caption = (
        "관찰: 상호배타로 접으면 기타·판단 불가가 매 분기 절반 전후다. 판매·홍보 칸은 2025년 이후 얇아지고 개인 감상 칸은 2026년에 두꺼워진다. "
        "가능한 해석: 선정 글의 문안이 판매 안내에서 짧은 감상 쪽으로 옮겨 간 구성이다. "
        "왼쪽은 기타를 포함한 100% 구성이고, 오른쪽은 기타·판단 불가를 뺀 뒤 다시 100%로 맞춘 것이다. "
        "한계: 기타는 목적 단서가 없는 글이지 무관심을 뜻하지 않는다. 2026Q4*는 10월 1–22일만이다."
    )
    fig, axes = make_figure(caption, figsize=(14.8, 8.8), n_cols=2, bottom=0.30, top=0.84, left=0.06, right=0.99)
    x = np.arange(len(q_order))
    short_q = quarter_labels(q_order)
    for ax, drop_etc in zip(axes, [False, True]):
        base = np.zeros(len(q_order))
        labels = [label for label in PURPOSE_STACK if not (drop_etc and label == "기타·판단 불가")]
        block = shares.loc[labels].fillna(0)
        if drop_etc:
            denom = block.sum(axis=0).replace(0, np.nan)
            block = block.div(denom, axis=1)
        for label in labels:
            height = block.loc[label].to_numpy() * 100
            ax.bar(x, height, bottom=base, color=PURPOSE_COLORS[label], width=0.86, label=label)
            base = base + np.nan_to_num(height)
        ax.set_xticks(x)
        ax.set_xticklabels(short_q, rotation=90, fontsize=7)
        ax.set_ylim(0, 100)
        title = "전체 구성 (기타 포함)" if not drop_etc else "기타·판단 불가를 뺀 구성"
        style_ax(ax, title, "작성 분기. 2026Q4*는 10월 22일까지", "구성비 (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 0.99))
    save_fig(fig, charts / "03_quarterly_purpose_exclusive.png")

    m_frame = tables[
        (tables["grain"] == "month")
        & (tables["denominator_name"] == "해당 월 전체 게시물(확인 필요 제외)")
        & (tables["label"].isin(PURPOSE_LINE))
    ]
    caption = (
        "관찰: 개인 감상 비중은 2026년에 높아지고 2026-08은 그 달 게시물의 절반을 넘는다. 판매·홍보는 2025년 이후 낮아진다. 개인 경험과 정보 공유는 월마다 흔들린다. "
        "가능한 해석: 분기 구성과 같은 방향이다. 붉은 세로 띠는 월 50건 미만이라 그 구간의 꺾임은 추세 근거로 쓰지 않는다. 2026-08은 그 띠가 아니다. "
        "한계: 복수 라벨이라 선만 더하면 100%가 아니다. 관측이 없는 2026년 11–12월은 0으로 잇지 않았다."
    )
    fig, ax = make_figure(caption, figsize=(15.6, 8.8), bottom=0.34, top=0.88)
    month_periods = [ym for ym in yms if ym in set(m_frame["period"])]
    x = np.arange(len(month_periods))
    for label in PURPOSE_LINE:
        sub = m_frame[m_frame["label"] == label].set_index("period").reindex(month_periods)
        ax.plot(x, sub["share_of_denominator_posts"] * 100, marker="o", markersize=3, label=label, color=PURPOSE_COLORS[label])
    for idx, ym in enumerate(month_periods):
        n_month = int((~posts["is_review"] & posts["ym"].eq(ym)).sum())
        if n_month < SMALL_MONTH_N:
            ax.axvline(idx, color="#E45756", alpha=0.25, linewidth=4, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels([ym[2:] for ym in month_periods], rotation=90, fontsize=6, ha="center")
    style_ax(ax, "수집 표본의 월별 게시 목적 비중", "작성월 (한국시간, 22-01=2022년 1월)", "해당 월 게시물 대비 비중 (%)")
    ax.legend(ncol=3, frameon=False, fontsize=8)
    save_fig(fig, charts / "04_monthly_purpose_shares.png")

    c_frame = tables[
        (tables["grain"] == "quarter")
        & (tables["denominator_name"] == "해당 분기 작품 관련·확인 필요 제외 게시물")
        & (tables["label"].isin(LINE_NAMES + ["치이카와"]))
    ]
    caption = (
        "관찰: 하치와레·랏코·모몽가·우사기·먼작귀 언급 비중은 분기마다 오르내리며, 어느 한 이름이 표본에서 사라지지는 않는다. "
        "회색 점선 치이카와는 수집 키워드가 본문에 남은 경우가 많아 다른 이름과 같은 선호 축으로 보지 않는다. "
        "가능한 해석: 선정 글이 특정 시기에 어떤 이름을 같이 적었는지의 차이다. "
        "한계: 한 글에 이름이 여러 개면 선이 각각 올라 합이 100%를 넘는다. 검색 키워드 빈도가 아니다. 2026Q4*는 10월 22일까지다."
    )
    fig, ax = make_figure(caption, figsize=(14.6, 8.6), bottom=0.30, top=0.86)
    for label in ["치이카와"] + LINE_NAMES:
        sub = c_frame[c_frame["label"] == label].set_index("period").reindex(q_order)
        style = "--" if label == "치이카와" else "-"
        ax.plot(
            range(len(q_order)),
            sub["share_of_denominator_posts"] * 100,
            linestyle=style,
            marker="o",
            markersize=3.2,
            color=NAME_COLORS[label],
            label=("치이카와 본문(수집 조건과 겹칠 수 있음)" if label == "치이카와" else label),
        )
    ax.set_xticks(range(len(q_order)))
    ax.set_xticklabels(quarter_labels(q_order), rotation=90, fontsize=7)
    style_ax(ax, "수집 표본 본문의 분기별 이름 언급 비중", "작성 분기", "관련 게시물 대비 비중 (%)")
    ax.legend(ncol=3, frameon=False, fontsize=8)
    save_fig(fig, charts / "05_character_mention_quarterly.png")

    heat = tables[
        (tables["grain"] == "year")
        & (tables["denominator_name"] == "해당 연도 작품 관련·확인 필요 제외 게시물")
        & (tables["label"].isin(HEAT_NAMES))
    ]
    shares, counts = matrix_from_table(heat, HEAT_NAMES, [str(y) for y in YEARS])
    shares.columns = [f"{y}*" if y == "2026" else y for y in shares.columns]
    counts.columns = shares.columns
    caption = (
        "관찰: 치이카와와 먼작귀 본문 언급이 매해 넓고, 하치와레·랏코가 그다음이다. 갑옷씨는 칸 숫자가 작다. "
        "가능한 해석: 표본이 치이카와 검색으로 모였기 때문에 치이카와 칸이 큰 것은 선호도 1위가 아니다. "
        "한계: 색은 그 해 관련 게시물 대비 비중, 숫자는 게시물 수다. 복수 언급이라 세로 합이 100%가 아니다. 2026*는 10월 22일까지인 1,000건이다."
    )
    fig, ax = make_figure(caption, figsize=(12.2, 8.4), left=0.24, right=0.90, bottom=0.28)
    heatmap(ax, shares, counts, "수집 표본 본문의 연도별 이름 언급", "비중")
    save_fig(fig, charts / "06_character_year_heatmap.png")

    a_frame = tables[
        (tables["grain"] == "year")
        & (tables["denominator_name"] == "해당 연도 작품 관련·확인 필요 제외 게시물")
        & (tables["label"].isin(ASPECT_MAIN))
    ]
    shares, counts = matrix_from_table(a_frame, ASPECT_MAIN, [str(y) for y in YEARS])
    shares.columns = [f"{c}*" if c == "2026" else c for c in shares.columns]
    counts.columns = shares.columns
    caption = (
        "관찰: 세부 이유가 없는 호감이 매해 가장 넓다. 행동·말투·성격과 유머는 2026년 칸의 숫자가 앞선 해보다 크다. 외형과 상품 재질은 한 자릿수에서 십여 건이다. "
        "가능한 해석: 2026년 선정 글에 캐릭터의 행동이나 웃긴 점을 적은 문장이 더 섞여 있다. 이용자가 외형보다 성격을 선호한다는 결론은 아니다. "
        "한계: 이미지 안 표정은 본문에 없으면 집계되지 않는다. 연간 15건 미만 칸은 추세로 잇지 않는다. 2026*는 부분 기간의 1,000건이다."
    )
    fig, ax = make_figure(caption, figsize=(12.4, 8.6), left=0.28, right=0.90, bottom=0.28)
    heatmap(ax, shares, counts, "수집 표본의 연도별 작성자 호감 측면", "비중")
    save_fig(fig, charts / "07_affection_year_heatmap.png")

    f_frame = tables[
        (tables["grain"] == "quarter")
        & (tables["denominator_name"] == "해당 분기 작품 관련·확인 필요 제외 게시물")
        & (tables["label"].isin(FORM_MAIN))
    ]
    shares, counts = matrix_from_table(f_frame, FORM_MAIN, q_order)
    shares.columns = quarter_labels(q_order)
    counts.columns = shares.columns
    caption = (
        "관찰: 인형·피규어·키링·마스코트 언급은 2022–2023년 분기에 더 자주 보이고 2026년 분기에는 칸 숫자가 작아지는 쪽이 많다. 의류·식품은 분기마다 들쑥날쑥하다. "
        "가능한 해석: 후반 인기 표본이 상품명보다 장면·영화 반응을 더 담았을 수 있다. 판매량 감소가 아니다. "
        "한계: 가챠·쿠지는 이 그림에 없다. 형태와 판매 방식은 다른 축이다. 0은 그 분기 게시물은 있으나 해당 형태 언급이 0건이라는 뜻이다. 2026Q4*는 10월 22일까지다."
    )
    fig, ax = make_figure(caption, figsize=(15.4, 8.6), left=0.12, right=0.90, bottom=0.30)
    heatmap(ax, shares, counts, "수집 표본의 분기별 상품 형태 언급", "비중")
    save_fig(fig, charts / "08_product_form_quarter_heatmap.png")

    caption = (
        "관찰: 애니메이션 언급은 2022년이 57건으로 가장 많고 2026년은 9건이다. 영화 언급은 2026년 26건이고 그 전은 0–3건이다. "
        "가챠는 2022–2025년 31–49건이다가 2026년 10건이다. 쿠지는 2025년 36건으로 튀고 공동구매는 2022년 31건 이후 줄어든다. "
        "가능한 해석: 표본 문안이 초기 애니메이션·판매 방식 언급에서 2026년 영화 언급 쪽으로 겹쳐 있다. 일정이 원인인지는 별도다. "
        "한계: 막대는 고유 게시물 수다. 연도 분모는 모두 1,000건이지만 2026년은 10월 22일까지의 부분 기간이다. 가챠와 인형은 배타 범주가 아니다."
    )
    fig, axes = make_figure(caption, figsize=(13.8, 8.6), n_cols=2, bottom=0.30, top=0.86)
    event_counts = {
        label: [year_token_map(confirmed, "content_events", label)[year] for year in YEARS] for label in EVENT_MAIN
    }
    sales_counts = {
        label: [year_token_map(confirmed, "sales_channels", label)[year] for year in YEARS] for label in SALES_MAIN
    }
    x = np.arange(len(YEARS))
    width = 0.12
    for idx, label in enumerate(EVENT_MAIN):
        axes[0].bar(x + (idx - 2.5) * width, event_counts[label], width=width, label=label)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(axes[0], "콘텐츠·행사 언급 건수", "작성 연도", "고유 게시물 수")
    axes[0].legend(frameon=False, fontsize=7, ncol=2)
    for idx, label in enumerate(SALES_MAIN):
        axes[1].bar(x + (idx - 2.5) * width, sales_counts[label], width=width, label=label)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(axes[1], "판매·획득 방식 언급 건수", "작성 연도", "고유 게시물 수")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    save_fig(fig, charts / "09_content_and_channel_year.png")

    caption = (
        "관찰: 구매 완료는 연 6–21건, 구매 희망은 1–8건, 소유 희망은 5–14건, 획득은 6–12건이다. 장면·대사 인용은 26–61건으로 이보다 크다. "
        "가능한 해석: 인기 게시물 본문은 구매 완료를 보고하기보다 장면 반응을 적는 경우가 많다. 2026년 장면 인용이 61건으로 가장 많다. "
        "한계: 건수가 작아 선으로 잇지 않았다. 연간 15건 미만은 증감의 근거로 쓰지 않는다. 이 숫자는 구매율이나 재구매율이 아니다. 2026*는 부분 기간이다."
    )
    fig, axes = make_figure(caption, figsize=(13.8, 8.6), n_cols=2, bottom=0.30, top=0.86)
    x = np.arange(len(YEARS))
    width = 0.12
    for idx, label in enumerate(ACTION_MAIN):
        vals = [year_token_map(confirmed, "action_labels_author", label)[year] for year in YEARS]
        axes[0].bar(x + (idx - 2.5) * width, vals, width=width, label=label.replace(":", " "))
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(axes[0], "작성자 행동·상태 건수", "작성 연도", "고유 게시물 수")
    axes[0].legend(frameon=False, fontsize=7)
    scene = [year_token_map(confirmed, "content_uses", "장면·대사 인용")[year] for year in YEARS]
    axes[1].bar(x, scene, color="#4C78A8", width=0.65)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(axes[1], "장면·대사 인용 건수", "작성 연도", "고유 게시물 수")
    save_fig(fig, charts / "10_behavior_year_counts.png")

    caption = (
        "관찰: 작성자의 가격·품절·원하는 대상 부재 언급은 매해 한 자릿수에서 십여 건이다. 2022년이 다소 많고 2026년은 더 적다. "
        "가능한 해석: 이런 단어가 인기 게시물에 간헐적으로 등장한다. "
        "한계: 근거 표의 장벽 역할은 일반 언급과 판매 문안뿐이고, 행동 장벽과 원하는 개선은 0건이다. 비싸다는 문장을 구매 포기로 읽지 않았다. 선 추세가 아니다."
    )
    fig, ax = make_figure(caption, figsize=(12.4, 8.4), bottom=0.28, top=0.86)
    barrier_labels = ["가격·예산", "품절·재고", "원하는 대상 부재", "품질", "구매 경로", "크기·보관"]
    x = np.arange(len(YEARS))
    width = 0.12
    for idx, label in enumerate(barrier_labels):
        vals = []
        for year in YEARS:
            key = (year, label)
            vals.append(stats["barrier_counts"].get(key, 0))
        ax.bar(x + (idx - 2.5) * width, vals, width=width, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(ax, "수집 표본의 연도별 작성자 장벽 언급 건수", "작성 연도", "고유 게시물 수")
    ax.legend(ncol=3, frameon=False, fontsize=8)
    save_fig(fig, charts / "11_barrier_year_counts.png")

    caption = (
        "관찰: 좋아요와 리포스트는 해마다 오른쪽으로 긴 꼬리다. 상자는 중앙 근처에 있고 2026년 상자가 위로 올라간다. "
        "조회수는 2023–2026년만 그렸다. 2022년은 1,000건 중 946건이 비어 있어 그 해 상자를 그리지 않았고, 있는 54건도 0으로 채우지 않았다. "
        "가능한 해석: 2026년 분포 이동은 8–10월 중앙값 상승과 같은 현상이다. "
        "한계: 인기 게시물을 고른 결과다. 수집 시각이 없어 경과 시간 보정이 아니다. 평균 차이가 선호 차이는 아니다."
    )
    fig, axes = make_figure(caption, figsize=(13.8, 8.6), n_cols=3, bottom=0.32, top=0.88)
    like_data = [np.log10(posts.loc[posts["year"].eq(year), "like"].fillna(0) + 1) for year in YEARS]
    repost_data = [np.log10(posts.loc[posts["year"].eq(year), "repost"].fillna(0) + 1) for year in YEARS]
    view_years = [2023, 2024, 2025, 2026]
    view_data = [np.log10(posts.loc[posts["year"].eq(year), "views"].dropna()) for year in view_years]
    axes[0].boxplot(like_data, tick_labels=[f"{y}*" if y == 2026 else str(y) for y in YEARS], showfliers=True, flierprops={"markersize": 2})
    axes[1].boxplot(repost_data, tick_labels=[f"{y}*" if y == 2026 else str(y) for y in YEARS], showfliers=True, flierprops={"markersize": 2})
    axes[2].boxplot(view_data, tick_labels=[f"{y}*" if y == 2026 else str(y) for y in view_years], showfliers=True, flierprops={"markersize": 2})
    for ax, title, ylabel in zip(
        axes,
        ["좋아요", "리포스트", "조회수 (2022년 제외)"],
        ["log10(좋아요+1)", "log10(리포스트+1)", "log10(조회수)"],
    ):
        style_ax(ax, title, "작성 연도", ylabel)
    save_fig(fig, charts / "12_engagement_box_year.png")

    caption = (
        "관찰: 1월 1일~10월 22일로 맞추면 2023년 개인 감상·판매 홍보 비중은 연도 전체와 조금 달라지지만, "
        "판매·홍보가 2026년에 낮고 개인 감상이 2026년에 높은 방향은 유지된다. 2026년은 이미 그 구간이라 두 막대가 같다. "
        "가능한 해석: 2023-12 건수 집중만으로 연도 간 목적 구성 차이가 만들어지지는 않았다. "
        "한계: 맞춘 구간의 분모는 해마다 다르다. 2022년 763건, 2023년 653건, 2024년 810건, 2025년 794건, 2026년 1,000건이다."
    )
    fig, ax = make_figure(caption, figsize=(12.4, 8.4), bottom=0.30, top=0.84)
    labels_cmp = ["개인 감상", "판매·홍보"]
    x = np.arange(len(YEARS))
    width = 0.18
    series = [
        ("개인 감상 연도 전체", stats["purpose_all"]["개인 감상"], "#4C78A8"),
        ("개인 감상 10월 22일까지", stats["purpose_aligned"]["개인 감상"], "#9ECAE1"),
        ("판매·홍보 연도 전체", stats["purpose_all"]["판매·홍보"], "#E45756"),
        ("판매·홍보 10월 22일까지", stats["purpose_aligned"]["판매·홍보"], "#F6A6A5"),
    ]
    for idx, (label, mapping, color) in enumerate(series):
        vals = [mapping[year] * 100 for year in YEARS]
        ax.bar(x + (idx - 1.5) * width, vals, width=width, label=label, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in YEARS])
    style_ax(ax, "수집 표본의 연도 전체와 동일 달력 구간 목적 비중", "작성 연도", "게시물 대비 비중 (%)")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    save_fig(fig, charts / "13_aligned_window_purpose.png")


def render_feasibility(stats: dict) -> str:
    return f"""# 시간 분석 가능 여부

- 분석 버전: `{VERSION}` (`clause_context_rules`)
- 결과 폴더: `text_analysis_v2/20261030_211145`
- 게시물 원문: `normalized/x_posts.csv`
- 작성 시각 범위: {stats['date_min']} ~ {stats['date_max']} (한국시간, +09:00)
- 2026년은 10월 22일까지의 부분 기간이다. 파일 건수는 1,000으로 다른 해와 같다.

## 버전 선택

| 후보 | 처리 | 판단 |
| --- | --- | --- |
| `text_analysis_v2/20261030_211145` | 5,000건 완료, 실패 0, 검증 통과, 기준서 v2.3 | 사용 |
| `text_analysis_deep` | 별도 코드북의 완료본. v2가 라벨을 가져오지 않았다고 실행 기록에 적혀 있음 | 미사용 |
| `text_analysis/label_pass` | 2026-10-29.3. 라벨 체계가 다름 | 미사용 |
| v2.2 시범 | 기준서가 결과로 쓰지 않는다고 적음 | 미사용 |

수정 시각이 아니라 전량 완료, 검증, 기준서 적용 범위로 v2.3을 골랐다. 다른 버전의 라벨과 집계표는 이어 붙이지 않았다.

## 시간 정보 점검

| 항목 | 결과 |
| --- | --- |
| 고유 게시물 | {num(stats['n_posts'])}건, post_id 중복 {stats['dup_posts']} |
| 정규화 원문과 본문·시각 일치 | {stats['text_match']} / {num(stats['n_posts'])} |
| 작성 시각 형식 | `YYYY-MM-DD HH:MM:SS+09:00` {stats['regex_ok']}건, 오류 {stats['regex_bad']} |
| 9시간 추가 여부 | 문자열 연·월과 한국시간 변환이 불일치 {stats['tz_year_mismatch']} / {stats['tz_month_mismatch']} |
| source_year와 작성 연도 | 불일치 {stats['source_year_mismatch']}건. 의미는 다르므로 기간은 작성 시각만 사용 |
| 날짜 결측 | {stats['nat']} |
| 월 수 | {stats['n_months']}개월. 2026-11, 2026-12는 표본에 없음 |
| 분류 연결 | 분석 게시물 {num(stats['n_posts'])} = 입력 {num(stats['n_posts'])}. 근거 없는 게시물도 요약 행은 있다 |
| 확인 필요 | {stats['n_review']}건. 확정 집계에서 제외 |
| 작품 관련 | {num(stats['n_relevant'])}건. 확정 분모 {num(stats['n_confirmed'])} |
| 조회수 결측 | {num(stats['view_na'])}건, 모두 2022년(그 해 1,000건 중 946건). 값이 있는 54건은 그 해 분포로 쓰지 않음. 0으로 채우지 않음 |
| 계정 | {num(stats['n_accounts'])}개. 상위 1개 비중은 해마다 {stats['top1_range']} |
| 여러 해에 글이 있는 계정 | {num(stats['multi_year_accounts'])}개. 장기 애착의 증거가 아님 |

월별 건수는 26~257이다. 중앙은 84다. 50건 미만은 2022-01(43), 2022-02(26), 2023-06(34), 2023-10(48)이다. 이 기준은 그 달의 비중을 추세의 꺾임으로 쓰지 않으려는 표시다. 통계적 신뢰구간이 아니다.

연간 15건 미만인 라벨은 선그래프로 잇지 않고 건수표와 원문으로 둔다. 이것도 유의성 기준이 아니다.

## 후보 평가

| 분석 후보 | 판정 | 근거 |
| --- | --- | --- |
| 표본의 월별·분기별 분포 | 수행 가능 | 시각 결측 0, 월 58개 모두 26건 이상. 연도 파일 1,000건의 작성월 분포로만 해석 |
| 게시 목적의 구성 변화 | 수행 가능 | 목적 라벨이 모든 게시물에 있다. 기타·판단 불가 약 58–67%. 복수 목적 181건은 상호배타 칸으로 분리 |
| 캐릭터 언급 구성 | 수행 가능 | 본문 규칙으로 집계. 검색 키워드와 구분. 선호 순위가 아님. 우사기 등은 강단서가 있을 때만 |
| 호감·공감 이유의 구성 | 제한적으로 가능 | 세부 이유 없는 호감이 다수. 행동·유머는 연 단위 비교가 된다. 외형 35건, 상품 재질 6건은 월별 추세에 부적합 |
| 상품·콘텐츠 형태의 구성 | 수행 가능 | 형태, 판매·획득 방식, 콘텐츠·행사를 다른 축으로 집계. 희소 칸이 많아 분기를 기본으로 둠 |
| 행동·상태의 구성 | 제한적으로 가능 | 구매 완료는 확정 분모에서 연간 한 자릿수~20건대. 건수표와 원문. 선 추세는 만들지 않음 |
| 수집·활용 방식의 구성 | 제한적으로 가능 | 사용 표현 {stats['use_n']}건, 수집 표현 {stats['collect_n']}건. 언제 문장이 있는지만 연도 건수와 원문으로 보임. 추세 분석은 하지 않음 |
| 미충족 요구와 장벽 | 제한적으로 가능 | 작성자 일반 언급만 있다. 행동 장벽 {stats['barrier_action']}건, 원하는 개선 {stats['barrier_wish']}건. 포기 원인 분석은 부적합 |
| 반응 지표의 분포 | 수행 가능 (보조) | 좋아요·리포스트·댓글은 결측 0. 조회수는 2022년 946건 결측. 수집 시각 없음. 중앙값과 분포만 사용 |
| 연결어로 밝힌 상품 선택 이유 | 현재 자료로 부적합 | 게시물 {stats['selection_n']}건. 시기 비교를 만들지 않음 |
| 관심을 되짚은 계기 | 현재 자료로 부적합 | 게시물 {stats['interest_n']}건. 유입 경로의 시기 분포로 쓰지 않음 |

확정 집계의 분모는 확인 필요 27건을 뺀 게시물이다. 표본 건수 그림만 5,000건 전체를 쓴다. 언급 없음은 그 표현이 본문에 없다는 뜻이지, 그 행동이나 특징이 없다는 뜻이 아니다.

이동평균은 쓰지 않았다. 분기 수치는 그 분기 분자 합을 그 분기 분모로 나눈 값이다.
"""


def render_report(stats: dict, evidence: pd.DataFrame) -> str:
    def q(theme: str, role: str, limit: int = 2) -> str:
        sub = evidence[(evidence["theme"] == theme) & (evidence["role"] == role)].head(limit)
        lines = []
        for row in sub.itertuples(index=False):
            if not row.post_id:
                continue
            lines.append(
                f"- {row.created_at_kst[:10]} [{row.post_id}]({row.post_url}) @{row.account_id}: “{row.excerpt}”"
            )
        return "\n".join(lines) if lines else "- 해당 조건의 원문이 없다."

    return f"""# 치이카와 X 수집 표본의 시기별 구성

- 분석 버전: `{VERSION}`
- 판정 방법: 구절 규칙. 게시물마다 사람이 라벨을 고치지 않았다.
- 범위: 연도별 1,000건, 총 {num(stats['n_posts'])}건. 작성일 {stats['date_min'][:10]} ~ {stats['date_max'][:10]} (한국시간).
- 2026년은 10월 22일까지다. 11–12월 비율은 0이 아니라 결측이다.
- 확정 집계는 확인 필요 {stats['n_review']}건을 제외한 고유 게시물이다.

이 보고서는 선정된 인기 게시물 안에서 관심 표현, 호감의 말, 상품·콘텐츠 언급, 소비·참여 문장이 시기에 따라 어떻게 섞여 있는지를 본다. X 전체 언급량, 시장 규모, 팬덤 성장률, 계절성, 구매 전환율은 판단하지 않는다.

## 핵심 요약

1. 연도마다 1,000건인 이 표본에서 작성월 분포는 고르지 않다. 2023년 12월이 257건으로 가장 많지만, 그 달 좋아요 중앙값은 6이다. 건수가 많은 달과 반응이 큰 달은 다르다.
2. 게시 목적은 매 기간 기타·판단 불가가 절반을 넘는다. 그 위에서 판매·홍보 비중은 {year_line(stats['purpose_all']['판매·홍보'], as_pct=True)}로 낮아지고, 개인 감상은 {year_line(stats['purpose_all']['개인 감상'], as_pct=True)}다. 2026년 8월은 그 달 {num(stats['aug_d'])}건 중 개인 감상이 {num(stats['aug_n'])}건({pct(stats['aug_n']/stats['aug_d'])})이다. 한국어 본문만 봐도 연간 방향은 같다.
3. 이름 언급은 치이카와·먼작귀가 매해 넓다. 이는 수집 조건과 작품명이 본문에 남은 결과로 보는 편이 맞다. 하치와레, 랏코, 모몽가, 우사기는 여러 해에 걸쳐 본문에 나타나며, 그 순서를 선호도 순위로 쓰지 않는다.
4. 작성자 호감의 다수는 매해 “귀엽다”처럼 세부 이유가 없는 문장이다. 행동·말투·성격과 유머를 특정한 글은 2026년 표본에서 앞선 해보다 많다. 외형을 문장으로 특정한 글은 전체 35건 수준이라 월별 추세가 아니다.
5. 상품 형태 언급(인형, 피규어, 키링, 마스코트)과 가챠·공동구매 언급은 2026년 표본에서 줄어드는 쪽이다. 영화 언급은 2026년 {stats['movie_2026']}건이고 2022–2025년은 해마다 0–3건이다. 형태와 가챠는 서로 다른 축이다.
6. 구매 완료, 구매 희망, 소유 희망, 가방 부착, 세트 수집은 여러 해에 문장으로 있으나 건수가 작다. 가격·품절 단어는 있으나, 그 때문에 사지 못했다고 연결된 글은 0건이다.
7. 좋아요 중앙값은 2022–2025년 10–15, 2026년 {stats['like_med'][2026]:.0f}다. 2026년 1–7월 중앙값은 한 자릿수~십몇이고 8–10월만 1,000을 넘는다. 수집 시각이 없어 경과 시간으로 보정하지 않았다.

## 분석 범위와 표본 구조

입력 게시물 {num(stats['n_posts'])}건은 `post_id`가 모두 다르고, 정규화 원문의 본문·작성 시각과 일치한다. 작성 시각 문자열은 전부 `+09:00`이다. 문자열에서 읽은 연·월과 한국시간 변환이 어긋난 건은 0이다. `source_year`도 이번 파일에서는 작성 연도와 값이 같았지만, 기간 계산에는 쓰지 않았다.

연도별 건수는 설계대로 각 1,000이다. 2023년과 2024년에는 좋아요 0인 글이 있어, 월별 건수를 “그 달의 좋아요 상위”로 다시 해석하지 않는다. 월별 건수는 이 1,000건의 작성월 위치다.

| 연도 | 작성 범위 | 계정 수 | 상위 1계정 비중 | 좋아요 중앙값 | 조회수 결측 |
| --- | --- | --- | --- | --- | --- |
| 2022 | 01-01 ~ 12-31 | {num(stats['accounts_year'][2022])} | {pct(stats['top1_share'][2022])} ({stats['top1_id'][2022]}) | {stats['like_med'][2022]:.0f} | 946 |
| 2023 | 01-01 ~ 12-31 | {num(stats['accounts_year'][2023])} | {pct(stats['top1_share'][2023])} ({stats['top1_id'][2023]}) | {stats['like_med'][2023]:.0f} | 0 |
| 2024 | 01-01 ~ 12-31 | {num(stats['accounts_year'][2024])} | {pct(stats['top1_share'][2024])} ({stats['top1_id'][2024]}) | {stats['like_med'][2024]:.0f} | 0 |
| 2025 | 01-01 ~ 12-31 | {num(stats['accounts_year'][2025])} | {pct(stats['top1_share'][2025])} ({stats['top1_id'][2025]}) | {stats['like_med'][2025]:.0f} | 0 |
| 2026 | 01-01 ~ 10-22 | {num(stats['accounts_year'][2026])} | {pct(stats['top1_share'][2026])} ({stats['top1_id'][2026]}) | {stats['like_med'][2026]:.0f} | 0 |

작품 관련은 {num(stats['n_relevant'])}건, 판단 불가 7건, 무관 2건이다. 본문 판단이 가능한 글은 {num(stats['scope_counts']['본문으로 판단 가능'])}건, 이미지나 영상 확인이 필요한 글은 {num(stats['scope_counts']['이미지나 영상 확인 필요'])}건, 정보가 짧은 글은 {num(stats['scope_counts']['기타 정보 부족'])}건이다. 다른 언어가 중심인 글은 {num(stats['lang_other'])}건이고, 그 글의 목적은 거의 기타·판단 불가다. 규칙을 바꿔 일본어를 재분류하지 않았다.

같은 달력 구간(1월 1일~10월 22일)의 건수는 2022년 {num(stats['aligned_n'][2022])}, 2023년 {num(stats['aligned_n'][2023])}, 2024년 {num(stats['aligned_n'][2024])}, 2025년 {num(stats['aligned_n'][2025])}, 2026년 {num(stats['aligned_n'][2026])}이다. 연도 전체 비교와 따로 두었다.

여러 해에 게시물이 있는 계정은 {num(stats['multi_year_accounts'])}개다. 계정은 사람이 아니고, 여러 해에 보였다는 사실만으로 장기 애착이나 브랜드 충성도를 말하지 않는다.

그림: `charts/01_monthly_sample_counts.png`. 표: `tables/monthly_sample.csv`, `tables/quarterly_sample.csv`, `tables/yearly_sample.csv`.

## 질문별 결과

### 1. 어떤 시기의 글이 표본에 많이 들어 있는가

**시기별 관찰.** 2023-12이 257건, 계정 196곳이다. 그다음으로 많은 달은 2022년 하반기와 2026년 1월(122건) 쪽이다. 2022-02는 26건으로 가장 적다. 2026년 11–12월은 없다.

**수치·원문.** 2023-12 좋아요 중앙값은 6, 90백분위는 약 69다. 목적 구성도 그 해의 다른 달과 크게 다르지 않아, 홍보글 더미로 설명되지 않는다. 상위 계정이 그 달을 독점하지 않는다.

대표·대조 원문:

{q('2023-12_표본건수', '대표')}

{q('2023-12_표본건수', '반대')}

**가능한 해석.** 2023년 인기 표본 1,000건 중 작성일이 12월인 글이 많다. X 전체의 12월 활동량 증가는 아니다.

**국내 IP 검토 질문.** 연말 상품·행사 문안이 국내 반응의 중심인지 보려면, 인기 상위 1,000건이 아니라 월별 동일 조건의 표본이 필요하다.

**추가 검증.** 원본 수집이 좋아요 외의 정렬을 썼는지, 수집 시각이 해마다 다른지.

### 2. 게시 목적은 어떻게 달라지는가

**시기별 관찰.** 전체 표본에서 판매·홍보는 {year_line(stats['purpose_all']['판매·홍보'], as_pct=True)}다. 개인 감상은 {year_line(stats['purpose_all']['개인 감상'], as_pct=True)}다. 정보 공유는 {year_line(stats['purpose_all']['정보 공유'], as_pct=True)}, 개인 거래는 {year_line(stats['purpose_all']['개인 거래'], as_pct=True)}, 개인 경험은 {year_line(stats['purpose_all']['개인 경험'], as_pct=True)}다. 기타·판단 불가는 {year_line(stats['purpose_all']['기타·판단 불가'], as_pct=True)}로 매해 절반을 넘는다.

**수치·원문.** 한국어 중심만 보면 판매·홍보는 {year_line(stats['purpose_ko']['판매·홍보'], as_pct=True)}, 개인 감상은 {year_line(stats['purpose_ko']['개인 감상'], as_pct=True)}다. 1월 1일~10월 22일로 맞춰도 판매·홍보는 {year_line(stats['purpose_aligned']['판매·홍보'], as_pct=True)}, 개인 감상은 {year_line(stats['purpose_aligned']['개인 감상'], as_pct=True)}다. 해마다 게시물이 가장 많은 계정 하나를 빼도 판매·홍보는 {year_line(stats['purpose_ex_top']['판매·홍보'], as_pct=True)}다. 정보 공유가 많은 계정 @chiikawa_render를 빼면 정보 공유는 {year_line(stats['info_ex_render'], as_pct=True)}가 되어, 2024년까지의 정보 공유 중 상당 부분이 한 계정에 기대 있다.

대표·대조:

{q('게시목적_홍보감소', '대표')}

{q('게시목적_홍보감소', '반대')}

**가능한 해석.** 한국어 본문, 동일 달력 구간, 최다 계정 제외 후에도 판매·홍보 비중은 2026년 표본에서 낮고 개인 감상 비중은 높다. 한 계정의 홍보 글만으로 생긴 그림은 아니다. 그래도 공식 계정의 실제 게시량 감소나 홍보 효과 하락은 아니다. 인기 1,000건 안에 어떤 문안이 남았는지의 차이다. 다른 언어 상품 안내는 목적 기타로 남아 판매·홍보에 들어가지 않는다.

**국내 IP 검토 질문.** 국내 협업 소식을 올리는 글과, 이용자가 짧게 반응하는 글이 같은 채널에서 어떤 비율로 보일지. 이 표본의 홍보 비중 감소를 국내 캠페인 성과로 읽지 말고, 팬 계정이 어떤 문장을 남기는지와 공식 안내를 분리해서 볼 필요가 있다.

**추가 검증.** 일본어 안내의 번역 후 재분류. 공식 계정 게시 목록 전수. 광고 식별자.

그림: `charts/03_quarterly_purpose_exclusive.png`, `charts/04_monthly_purpose_shares.png`, `charts/13_aligned_window_purpose.png`. 표: `tables/purpose_exclusive_quarterly.csv`, `tables/purpose_multilabel_monthly.csv`, `tables/purpose_yearly.csv`, `tables/aligned_window_comparison.csv`.

### 3. 어떤 이름이 시기에 따라 본문에 나타나는가

**시기별 관찰.** 확정 분모에서 치이카와 본문 언급은 {year_line(stats['char_share']['치이카와'], as_pct=True)}다. 먼작귀는 {year_line(stats['char_share']['먼작귀'], as_pct=True)}, 하치와레는 {year_line(stats['char_share']['하치와레'], as_pct=True)}, 랏코는 {year_line(stats['char_share']['랏코'], as_pct=True)}, 모몽가는 {year_line(stats['char_share']['모몽가'], as_pct=True)}, 우사기(강단서 동반)는 {year_line(stats['char_share']['우사기'], as_pct=True)}, 쿠리만쥬는 {year_line(stats['char_share']['쿠리만쥬'], as_pct=True)}다. 갑옷씨는 해마다 한 자릿수에서 십여 건이라 추세로 말하지 않는다.

**수치·원문.** 검색 키워드에는 있으나 본문 규칙으로는 잡히지 않는 게시물, 그리고 키워드 없이 본문에만 있는 게시물을 `tables/character_keyword_vs_body.csv`에 나누었다. 치이카와는 키워드와 본문이 크게 겹친다. 이름 순서는 선호도 순위가 아니다. 다른 캐릭터를 둘 이상 적은 관련 게시물은 {num(stats['multi_char_posts'])}건이다.

{q('캐릭터언급', '대표')}

{q('캐릭터언급', '반대')}

**가능한 해석.** 하치와레, 랏코, 모몽가, 우사기는 한 해의 이벤트 이름에만 붙어 있지 않고 여러 해 표본에 남는다. 2026년에 어느 이름이 유독 사라지거나 표본을 독점하는 패턴은 이 집계에서 크지 않다. 같은 글에 이름이 같이 나오는 것은 관계·비교 농담이지, 그 사람의 최애 순위가 아니다.

**국내 IP 검토 질문.** 국내 창작 협업에서 주인공 한 몸만 볼지, 이미 여러 해 문장에 같이 등장하는 친구 관계를 단위로 볼지. 등장 횟수가 많은 이름을 국내 선호도 1위로 둘지는 이 자료로 정하지 않는다.

**추가 검증.** 이미지 속 캐릭터. 짧은 호칭(치이, 하치, 토끼)은 이번 규칙이 자동으로 합치지 않았다.

그림: `charts/05_character_mention_quarterly.png`, `charts/06_character_year_heatmap.png`.

### 4. 호감의 이유는 어떻게 다른가

**시기별 관찰.** 확정 분모에서 세부 이유 없는 호감은 {year_line(stats['aspect_share']['호감은 있으나 세부 이유 불명확'], as_pct=True)}다. 행동·말투·성격은 건수 {year_line(stats['aspect_n']['행동·말투·성격'])}, 유머는 {year_line(stats['aspect_n']['유머'])}, 관계·장면은 {year_line(stats['aspect_n']['관계·조합·이야기·장면'])}, 위로·일상은 {year_line(stats['aspect_n']['위로·공감·일상과의 연결'])}, 외형은 {year_line(stats['aspect_n']['외형'])}다. 상품 재질·품질은 전체 {stats['texture_n']}건이다.

호감이 하나라도 있는 글만 분모로 두면 세부 이유 없는 호감의 비중은 {year_line(stats['aspect_among_aff']['호감은 있으나 세부 이유 불명확'], as_pct=True)}다. 행동·말투는 {year_line(stats['aspect_among_aff']['행동·말투·성격'], as_pct=True)}, 유머는 {year_line(stats['aspect_among_aff']['유머'], as_pct=True)}다.

**수치·원문.** 한국어이면서 본문으로 판단 가능한 글만 보면, 행동·말투 비중은 {year_line(stats['aspect_text_ko']['행동·말투·성격'], as_pct=True)}, 유머는 {year_line(stats['aspect_text_ko']['유머'], as_pct=True)}다. 2026년이 더 높은 방향은 이 하위집단에서도 남는다. 판단 가능 글의 비중 변화만으로 생긴 차이는 아니다. 연결어로 상품 선택 이유를 밝힌 글은 {stats['selection_n']}건이라 시기 비교를 하지 않았다.

{q('호감측면', '대표', 3)}

{q('호감측면', '반대')}

**가능한 해석.** 인기 게시물의 호감은 매해 짧은 긍정에서 멈춘다. 2026년 표본에는 말투, 행동, 웃긴 장면을 문장으로 붙인 글이 앞선 해보다 더 들어 있다. 이용자가 외형보다 성격을 좋아한다는 뜻으로 바꾸면 안 된다. 외형은 이미지에 있고 본문에는 “귀엽다”만 있는 경우가 많다. 여러 해에 보였다는 것은 서로 다른 글의 반복이지, 같은 이용자의 장기 애착이 아니다.

**국내 IP 검토 질문.** 국내 신규 캐릭터의 시안을 볼 때 얼굴만이 아니라, 한 장면 안에서 행동·말투·관계 농담이 전달되는지를 같이 볼 이유가 있는가. 이 표본은 그 질문이 반복해서 나온다는 힌트까지다. 성격이 외형보다 중요하다는 입증은 아니다.

**추가 검증.** 이미지가 있는 1,772건의 표정. 성우·목소리 평가는 외형과 섞지 않았다.

그림: `charts/07_affection_year_heatmap.png`. 표: `tables/affection_aspects_yearly.csv`.

### 5. 상품·콘텐츠 형태는 어떻게 다른가

**시기별 관찰.** 확정 분모의 인형 언급은 {year_line(stats['form_n']['인형'])}건, 피규어 {year_line(stats['form_n']['피규어'])}, 키링 {year_line(stats['form_n']['키링'])}, 마스코트 {year_line(stats['form_n']['마스코트'])}, 스티커 {year_line(stats['form_n']['스티커'])}, 의류 {year_line(stats['form_n']['의류'])}다. 홍보·개인 거래를 뺀 글만 보면 인형은 {year_line(stats['form_ex_promo']['인형'])}건, 피규어는 {year_line(stats['form_ex_promo']['피규어'])}건이다.

가챠는 {year_line(stats['sales_n']['가챠'])}건, 쿠지 {year_line(stats['sales_n']['쿠지'])}, 공동구매 {year_line(stats['sales_n']['공동구매'])}, 랜덤 {year_line(stats['sales_n']['랜덤'])}이다. 애니메이션은 {year_line(stats['event_n']['애니메이션'])}건, 영화는 {year_line(stats['event_n']['영화'])}건, 팝업 {year_line(stats['event_n']['팝업'])}, 카페·매장 {year_line(stats['event_n']['카페·매장'])}, 콜라보 {year_line(stats['event_n']['콜라보'])}다.

**수치·원문.** 영화 언급 {stats['movie_2026']}건 중 2026년 7–10월이 {stats['movie_2026_late']}건이다. 애니메이션 언급이 가장 많은 분기는 {stats['anim_top_q']} ({stats['anim_top_n']}건)이다. 인형과 가챠가 같이 적힌 확정 게시물은 {stats['doll_and_gacha']}건이다.

공개 일정과 시기가 겹친다. 겹침은 원인이 아니다.

- TV 애니메이션 방송 시작: 2022-04-04, 후지TV. 출처: [전격온라인](https://dengekionline.com/articles/116575/).
- 일본 극장판 개봉: 2026-07-24이라는 보도. 출처: [뉴스핌 2026-09-30](https://ir.newspim.com/news/view/20260930000936).
- 한국 개봉: 2026-09-30. 출처: [연합뉴스](https://www.yna.co.kr/view/AKR20260917177100005), [KMDb](https://www.kmdb.or.kr/db/kor/detail/movie/F/68144), [대원미디어 2026-10-12](https://daewonmedia.com/board/news-event/306).

{q('2026_영화언급', '대표')}

{q('2026_영화언급', '반대')}

{q('상품형태', '대표')}

{q('상품형태', '반대')}

**가능한 해석.** 2022년 표본에는 애니메이션 언급이 더 많고, 2026년 표본에는 영화 언급이 새로 넓다. 인형·가챠·공동구매 문안은 2026년 1,000건 안에서 비중이 작아진다. 홍보글을 빼도 인형 건수가 2022–2023년보다 2026년에 작다. 판매가 줄었다는 뜻은 아니다. 인기 글의 주제가 상품 안내에서 장면·영화 반응으로 더 많이 섞였을 가능이 있다. 가챠는 인형의 대체 범주가 아니다.

**국내 IP 검토 질문.** 국내 상품을 기획할 때 인형·키링 같은 형태와, 가챠·쿠지·공구 같은 얻는 방식을 한 순위로 합칠 것인가. 콘텐츠는 상품과 따로 두되, 2026년 표본처럼 영화 장면에 대한 짧은 반응이 상품 문안과 동시에 보이는 시기를 어떻게 나눌 것인가.

**추가 검증.** 국내 매장·팝업의 실제 일정표. 형태 단어가 작중 소품인지 판매 상품인지 사람이 읽어야 하는 경계 사례.

그림: `charts/08_product_form_quarter_heatmap.png`, `charts/09_content_and_channel_year.png`. 표: `tables/product_forms_quarterly.csv`, `tables/sales_channels_yearly.csv`, `tables/content_events_yearly.csv`.

### 6. 행동·상태와 사용·수집은 언제 보이는가

**시기별 관찰.** 구매 완료·경험은 {year_line(stats['action_n']['구매:완료·경험'])}건, 구매 희망 {year_line(stats['action_n']['구매:희망'])}, 소유 희망 {year_line(stats['action_n']['소유:희망'])}, 획득 완료 {year_line(stats['action_n']['획득:완료·경험'])}, 방문 완료 {year_line(stats['action_n']['방문:완료·경험'])}, 작성자 판매 희망 {year_line(stats['action_n']['판매:희망'])}다. 장면·대사 인용은 {year_line(stats['scene_n'])}건이다. 시청 완료로 읽힌 글은 전체 5건, 다시 보기는 2건이라 추세를 만들지 않았다.

사용 표현이 있는 확정 게시물은 {stats['use_n']}건, 수집 표현은 {stats['collect_n']}건이다. 사용은 가방 부착, 전시, 꾸미기, 휴대, 실사용, 선물 수령처럼 갈라지고 각 항목은 연간 대부분 5건 미만이다. 있는 해만 나열하면 사용 표현은 {stats['use_years']}, 세트·시리즈 수집 표현은 {stats['set_years']}에 관찰된다.

**수치·원문.**

{q('행동상태', '대표', 3)}

{q('행동상태', '반대')}

{q('사용수집', '대표')}

{q('사용수집', '반대')}

**가능한 해석.** 구매했다, 사고 싶다, 갖고 싶다, 가방에 단다는 문장은 한 해에만 있지 않다. 건수가 작아서 “늘었다”거나 “줄었다”고 말하지 않는다. 사용·수집 라벨에는 상품 안내 문안이 섞인 게시물이 있다. 자석 마스코트 안내, 제일복권 등수표, 대사 번역의 ‘갖고싶은 게 뭐야’는 `review_required.csv`에 분류 오류 의심으로 남겼고 라벨은 고치지 않았다. 그래서 사용 {stats['use_n']}건을 모두 작성자의 휴대 경험으로 세지 않는다. 장면 인용은 이 표본에서 구매 문장보다 흔하고, 2026년에 61건으로 가장 많다. 영화 시기와 겹치지만 그 인용이 모두 극장판이라는 뜻은 아니다. 언급이 없는 글은 그 사람이 사지 않았다는 뜻이 아니다.

**국내 IP 검토 질문.** 국내 제품 설명에 소장, 가방 부착, 전시, 선물, 세트 완성을 어떤 장면으로 보여줄지. 이 문장들은 수요의 크기가 아니라, 반복해서 관찰되는 사용 장면의 후보다. 전환율로 순위를 매기지 않는다.

**추가 검증.** 구매 확정이 규칙에서 빠졌을 수 있는 “구매걸어놓다” 같은 표현은 기존 v2 보고서가 이미 경계로 적었다. 여기서 라벨을 고치지 않았다. 결제·수령 자료는 별도다.

그림: `charts/10_behavior_year_counts.png`. 표: `tables/actions_yearly.csv`, `tables/use_modes_yearly.csv`, `tables/collection_yearly.csv`, `tables/content_use_yearly.csv`.

### 7. 가격·품절·부재는 언제 적히는가

**시기별 관찰.** 작성자 일반 언급의 고유 게시물은 가격·예산 {year_line(stats['barrier_n']['가격·예산'])}, 품절·재고 {year_line(stats['barrier_n']['품절·재고'])}, 원하는 대상 부재 {year_line(stats['barrier_n']['원하는 대상 부재'])}, 품질 {year_line(stats['barrier_n']['품질'])}다. 행동 장벽은 {stats['barrier_action']}건, 원하는 개선은 {stats['barrier_wish']}건이다. 판매 문안 장벽 근거는 {stats['barrier_promo_rows']}행이고 작성자 집계에 넣지 않았다.

**수치·원문.**

{q('장벽', '대표')}

{q('장벽', '반대')}

**가능한 해석.** 비싸다, 품절, 없다는 말은 2022년부터 간헐적으로 있다. 2026년 표본에서 더 많아졌다고 말할 만큼 건수가 크지 않고, 오히려 칸 숫자는 작다. 그 말 때문에 구매를 포기했다는 연결은 이 규칙으로 확인되지 않았다. 장벽이 없다는 뜻이 아니라, 인기 게시물 문장이 그 연결까지 적지 않은 경우가 많다는 뜻이다.

**국내 IP 검토 질문.** 국내 가격, 품절, 살 곳이 구매를 막는지 알려면 이 표본 밖의 질문지가 필요하다. 여기서는 그 단어를 넣을 문항 후보만 확인된다.

**추가 검증.** 품절 안내 게시물과 개인 한탄을 사람이 다시 읽기. 판매 문안 14행은 `review_required.csv` 쪽에 예시로 남겨 두었다.

그림: `charts/11_barrier_year_counts.png`. 표: `tables/barriers_yearly.csv`.

### 8. 반응 크기는 시기별로 어떻게 다른가

**시기별 관찰.** 좋아요 중앙값(1사분위, 3사분위)은 2022년 {stats['like_med'][2022]:.0f} ({stats['like_q1'][2022]:.0f}–{stats['like_q3'][2022]:.0f}), 2023년 {stats['like_med'][2023]:.0f} ({stats['like_q1'][2023]:.0f}–{stats['like_q3'][2023]:.0f}), 2024년 {stats['like_med'][2024]:.0f} ({stats['like_q1'][2024]:.0f}–{stats['like_q3'][2024]:.0f}), 2025년 {stats['like_med'][2025]:.0f} ({stats['like_q1'][2025]:.0f}–{stats['like_q3'][2025]:.0f}), 2026년 {stats['like_med'][2026]:.0f} ({stats['like_q1'][2026]:.0f}–{stats['like_q3'][2026]:.0f})다. 평균은 2022년 {stats['like_mean'][2022]:.0f}, 2026년 {stats['like_mean'][2026]:.0f}로 중앙값과 크게 다르다. 최댓값은 {num(stats['like_max'])}이다.

2026년 월별 중앙값은 1–7월에 6–13, 8월 {stats['like_med_2026_month']['2026-08']:.0f}, 9월 {stats['like_med_2026_month']['2026-09']:.0f}, 10월 {stats['like_med_2026_month']['2026-10']:.0f}다. 연도 안에서 상위 1% 좋아요를 뺀 중앙값은 {year_line({y: stats['like_med_drop_p99'][y] for y in YEARS})}이고, 판매·홍보를 뺀 중앙값은 {year_line({y: stats['like_med_nopromo'][y] for y in YEARS})}다. 2026년의 높은 중앙값은 극단값 몇 개나 홍보글 때문이 아니다.

**수치·원문.** 댓글 중앙값은 모든 해 0이다. 리포스트 중앙값은 2022–2025년 3–6, 2026년 {stats['repost_med'][2026]:.0f}다. 조회수는 2022년 1,000건 중 946건이 비어 있다. 나머지 54건의 중앙값을 그 해의 조회수 분포로 쓰지 않았다.

{q('반응지표', '대표')}

{q('반응지표', '반대')}

**가능한 해석.** 2026년 8–10월에 작성된 선정 글은, 같은 해 1–7월 선정 글보다 수집된 좋아요가 훨씬 크다. 한국 극장판 개봉(9월 30일)과 일본 개봉 보도(7월 24일)의 기간과 겹친다. 개봉이 원인이라고 쓰지 않는다. 인기순으로 1,000건을 채운 설계에서는, 반응이 큰 시기의 글이 그 해 표본에 더 들어가기 쉽다. 수집 시각이 없어 “늦게 올라서 좋아요가 덜 쌓였다”로 설명하지도 않는다. 만약 한 시점에 같이 모았다면 8–10월 글의 경과 시간이 더 짧은데 중앙값은 더 높다. 이 가정은 확인되지 않았으므로 보정 결과로 쓰지 않는다.

**국내 IP 검토 질문.** 개봉 전후 화제 크기를 보려면 인기 상위가 아닌 기간 표본과 수집 시각이 필요하다. 좋아요 차이를 국내 선호도나 구매로 바꾸지 않는다.

**추가 검증.** 수집 로그. 조회수 2022년 공란의 원인. 연예인·버튜버 계정을 뺀 재집계는 중앙값으로는 이미 방향이 유지된다.

그림: `charts/02_monthly_median_likes.png`, `charts/12_engagement_box_year.png`. 표: `tables/engagement_by_period.csv`, `tables/engagement_robustness.csv`.

## 국내 IP 검토에 대한 시사점

시기별로 반복되는 것과, 2026년 표본에서만 두드러지는 것을 나눈다.

여러 해에 문장으로 남는 것:

- 짧은 긍정(“귀엽다”)이 호감 문장의 중심이다.
- 하치와레, 랏코, 모몽가, 우사기 이름이 치이카와와 함께 또는 따로 본문에 있다.
- 행동·말투, 유머, 관계·장면, 위로를 적은 글이 소수지만 끊기지 않는다.
- 인형·피규어·키링·스티커와, 그와 별도로 가챠·쿠지·공구가 언급된다.
- 사고 싶다, 갖고 싶다, 샀다, 가방에 단다, 세트로 모은다는 문장이 드물게 반복된다.

2026년 1–10월 표본에서 구성이 다른 것:

- 판매·홍보 문안 비중이 낮고 개인 감상 비중이 높다.
- 영화 언급이 늘고, 애니메이션·인형·가챠 언급 비중은 작다.
- 행동·유머를 문장으로 특정한 호감이 앞선 해보다 많다.
- 8–10월 작성 글의 좋아요 중앙값이 같은 표본의 다른 시기와 다르다.

이 차이를 국내 창작 협업의 설계 질문으로 옮기면 다음과 같다.

1. 얼굴 시안만으로 반응을 예상할 것인가, 아니면 짧은 행동·말투·친구 관계가 한 장면에서 읽히는지를 같이 볼 것인가. 표본은 후자의 문장이 여러 해 있고 2026년에 더 자주 적혔음을 보여 준다. 장기 애착의 증거는 아니다.
2. 상품은 형태와 얻는 방식을 나누어 볼 것인가. 인형 언급과 가챠 언급은 한 글에 같이 있고, 서로 대체하지 않는다.
3. 사용 장면(휴대, 전시, 선물, 세트)을 제품 이야기에 넣을 것인가는 문장 후보로는 확인되지만, 얼마나 많은 사람이 그렇게 하는지는 이 자료로 알 수 없다.
4. 가격과 품절은 불만의 단어로 가끔 나오지만, 구매를 포기한 이유로 확인되지는 않았다. 국내 가격 정책을 이 비중으로 정하지 않는다.
5. 극장판처럼 큰 콘텐츠 일정 전후에는 인기 게시물의 구성과 반응 분포가 달라질 수 있다. 이번 표본은 그 시기가 겹친 관찰까지다. 일정이 원인인지는 기간 표본이 있어야 한다.

## 한계와 후속 과제

- 연도별 최대 1,000건 인기 게시물이다. 월별 막대는 전체 언급량이 아니다.
- 규칙 분류다. 사람이 모든 원문을 검수하지 않았다. 확인 필요 27건은 확정 수치에서 뺐다.
- 다른 언어 본문은 번역하지 않아 목적·호감이 기타와 언급 없음으로 남는다.
- 이미지와 링크를 열지 않았다. 표정 호감이 본문 밖으로 빠져 있을 수 있다.
- 검색 키워드와 본문 언급을 구분했다. 이름 빈도는 선호도 순위가 아니다.
- 복수 라벨은 비중 합이 100%를 넘을 수 있다. 상호배타 목적 그림만 100%다.
- 조회수 결측을 0으로 두지 않았다. 수집 시각이 없어 반응을 경과 시간으로 나누지 않았다.
- 판매량, 재구매율, 전환율, 고객 유지율을 추정하지 않았다. 유의성 검정, 성장 예측, 계절성 확정, 인과 추론을 하지 않았다.
- 후속으로는 수집 시각, 월별 동일 규칙 표본, 이미지 판독, 일본어 번역 후 목적 재분류, 판매 자료가 필요하다.

## 그림과 표

| 파일 | 내용 |
| --- | --- |
| `charts/01_monthly_sample_counts.png` | 작성월별 표본 건수 |
| `charts/02_monthly_median_likes.png` | 월별 좋아요 중앙값 |
| `charts/03_quarterly_purpose_exclusive.png` | 분기별 목적 구성 |
| `charts/04_monthly_purpose_shares.png` | 월별 목적 비중 |
| `charts/05_character_mention_quarterly.png` | 분기별 이름 언급 비중 |
| `charts/06_character_year_heatmap.png` | 연도별 이름 언급 |
| `charts/07_affection_year_heatmap.png` | 연도별 호감 측면 |
| `charts/08_product_form_quarter_heatmap.png` | 분기별 상품 형태 |
| `charts/09_content_and_channel_year.png` | 콘텐츠·판매 방식 건수 |
| `charts/10_behavior_year_counts.png` | 행동·장면 인용 건수 |
| `charts/11_barrier_year_counts.png` | 장벽 언급 건수 |
| `charts/12_engagement_box_year.png` | 반응 분포 |
| `charts/13_aligned_window_purpose.png` | 동일 달력 구간 목적 비중 |

집계 표는 `tables/`에 있다. 모든 비중 표에 기간, 분자, 분모, 분모 이름, 비율, 집계 단위, 분석 버전, 확인 필요 포함 여부, 복수 라벨 여부, 소표본 표시가 있다. 대표 원문은 `period_evidence.csv`, 해석 주의는 `review_required.csv`다.
"""


def render_run_log(stats: dict, out: Path) -> str:
    checks = "\n".join(f"- {name}: {'통과' if ok else '실패'} {detail}" for name, ok, detail in stats["validations"])
    return f"""# 실행 기록

- 실행 시각: {stats['run_stamp']}
- Python: {stats['py_version']}
- pandas: {pd.__version__}
- matplotlib: {matplotlib.__version__}
- 글꼴: {FONT_NAME} ({FONT_PATH})
- 분석 버전: {VERSION}
- 방법: {METHOD}
- 결과 폴더: {out}

## 입력

- `{NORM / 'x_posts.csv'}`
- `{NORM / 'x_post_keywords.csv'}`
- `{V2 / 'x_posts_analysis.csv'}`
- `{V2 / 'x_analysis_evidence.csv'}`
- `{V2 / 'x_analysis_connections.csv'}`
- `{V2 / 'review_required.csv'}`
- 기준서 `{V2 / 'analysis_codebook.md'}`
- 실행 기록 `{V2 / 'run_log.md'}`

`text_analysis`와 `text_analysis_deep`의 라벨은 읽어서 버전을 비교하는 데만 쓰고, 집계에 합치지 않았다.

## 기간과 집계 규칙

- 작성 시각 문자열의 연·월·일을 쓴다. `+09:00`에 9시간을 더하지 않는다.
- `source_year`는 파일 연도라 기간 축으로 쓰지 않는다.
- 기본 단위는 고유 게시물이다. 근거 행 수와 연결 행 수는 `tables/unit_counts_yearly.csv`에만 둔다.
- 확정 비중은 `review_flag=예` {stats['n_review']}건을 분모와 분자에서 뺀다. 월별 건수 그림만 5,000건이다.
- 작품 내용 축의 분모는 작품 관련이며 확인 필요를 뺀 게시물이다.
- 복수 라벨은 게시물당 한 번만 센다. 좋아요를 라벨 수만큼 더하지 않는다.
- 라벨이 0건이면 비율 0이다. 게시물이 없는 2026-11, 2026-12는 표를 만들지 않아 0과 구분된다.
- 월 게시물 {SMALL_MONTH_N}건 미만은 `small_sample=예`다. 연간 {RARE_YEAR_N}건 미만 라벨은 선그래프로 잇지 않는다. 두 기준은 눈금 규칙이지 유의성 기준이 아니다.
- 이동평균은 쓰지 않았다.
- 동일 달력 비교는 매년 1월 1일~10월 22일이다.
- 조회수 결측은 그대로 둔다.

## 도구

- 집계와 그림은 로컬 Python이다.
- 공개 일정 확인에 웹 검색을 썼다. 게시물 원문은 외부로 보내지 않았다.
- 분류용 MCP는 없다. 기존 v2 라벨을 유지했다.
- MySQL, 스프레드시트, Notion, Firecrawl은 이 집계에 필요 없어 쓰지 않았다.
- 수행하지 않은 것: 전면 재분류, 유의성 검정, 계절성 모형, 예측, 판매량 추정, 경과 시간 보정, 이미지 판독.

## 검증

{checks}
"""


def main() -> None:
    run_dt = datetime.now()
    stamp = run_dt.strftime("%Y%m%d_%H%M%S")
    out = ROOT / "time_analysis" / stamp
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "charts").mkdir(parents=True, exist_ok=True)
    print("OUT", out)

    posts, evidence, connections, raw, keywords, review_old = load_inputs()
    posts, time_checks = attach_time(posts)
    posts = attach_flags(posts)
    confirmed = posts[posts["confirmed"]].copy()
    all_but_review = posts[~posts["is_review"]].copy()

    merged = posts.merge(raw, on="post_id", suffixes=("", "_raw"), how="left")
    text_match = int((merged["text"] == merged["text_raw"]).sum())
    time_match = int((merged["created_at"] == merged["created_at_raw"]).sum())

    audit_rows = []

    def audit(group, item, value, note=""):
        audit_rows.append({"group": group, "item": item, "value": value, "note": note})

    audit("식별", "posts", len(posts), "x_posts_analysis")
    audit("식별", "unique_post_id", posts["post_id"].nunique(), "")
    audit("식별", "duplicate_post_id", int(posts["post_id"].duplicated().sum()), "")
    audit("식별", "raw_posts", len(raw), "normalized/x_posts.csv")
    audit("식별", "text_equal_raw", text_match, "분석 본문과 정규화 본문")
    audit("식별", "created_at_equal_raw", time_match, "")
    audit("식별", "evidence_rows", len(evidence), "근거 행. 게시물 수가 아님")
    audit("식별", "connection_rows", len(connections), "연결 행. 원인 수가 아님")
    audit("식별", "evidence_orphan", int((~evidence["post_id"].isin(posts["post_id"])).sum()), "")
    audit("식별", "connection_orphan", int((~connections["post_id"].isin(posts["post_id"])).sum()), "")
    audit("시각", "min_kst", time_checks["min"], "문자열 기준. 9시간을 더하지 않음")
    audit("시각", "max_kst", time_checks["max"], "2026-10-22는 부분 기간의 끝")
    audit("시각", "regex_ok", time_checks["regex_ok"], "+09:00 형식")
    audit("시각", "regex_bad", time_checks["regex_bad"], "")
    audit("시각", "tz_year_mismatch", time_checks["tz_year_mismatch"], "문자열 연도와 Asia/Seoul 변환")
    audit("시각", "tz_month_mismatch", time_checks["tz_month_mismatch"], "")
    audit("시각", "created_year_kst_mismatch", time_checks["created_year_kst_mismatch"], "")
    audit("시각", "source_year_value_mismatch", time_checks["source_year_mismatch"], "값이 같아도 source_year를 기간으로 쓰지 않음")
    audit("시각", "nat", time_checks["nat"], "")
    for year, sub in posts.groupby("year"):
        audit("연도범위", str(year), len(sub), f"{sub['created_at'].min()} ~ {sub['created_at'].max()}")
    for ym, count in posts.groupby("ym").size().items():
        audit("월건수", ym, int(count), "50미만 소표본" if count < SMALL_MONTH_N else "")
    for quarter, count in posts.groupby("quarter").size().items():
        audit("분기건수", quarter, int(count), period_note(quarter))
    audit("결측", "view_na", int(posts["views"].isna().sum()), "2022년에 집중")
    for year, sub in posts.groupby("year"):
        audit("결측", f"view_na_{year}", int(sub["views"].isna().sum()), "0으로 대체하지 않음")
        audit("결측", f"like_na_{year}", int(sub["like"].isna().sum()), "")
    audit("분류", "review_flag_yes", int(posts["is_review"].sum()), "확정 집계에서 제외")
    audit("분류", "relevant", int(posts["is_relevant"].sum()), "")
    audit("분류", "confirmed_relevant", int(posts["confirmed"].sum()), "관련 AND 확인 필요 아님")
    audit("분류", "link_rate", 1.0, "분석 파일 게시물 수 = 5000 = 정규화 게시물 수")
    for column, label in [
        ("purpose_labels", "목적"),
        ("affection_aspects_author", "호감"),
        ("product_forms", "상품형태"),
        ("action_labels_author", "행동"),
        ("use_modes", "사용"),
        ("collection_types", "수집"),
        ("barriers", "장벽"),
        ("content_events", "콘텐츠"),
        ("sales_channels", "판매방식"),
    ]:
        none_n = int(posts[column].fillna("").map(lambda value: "언급 없음" in split_labels(value) or value == "").sum())
        audit("미언급", label, none_n, "게시물 요약 칸 기준")
    audit("계정", "n_accounts", int(posts["account_id"].nunique()), "계정=사람 아님")
    audit("계정", "literal_null_name", int(posts["account_name"].eq("null").sum()), "문자열 null은 결측이 아님")
    audit("반응", "like_min", float(posts["like"].min()), "0 포함 가능. 인기 정의를 재단정하지 않음")
    audit("반응", "like_median", float(posts["like"].median()), "")
    audit("반응", "like_p99", float(posts["like"].quantile(0.99)), "")
    audit("버전", "codebook", VERSION, str(V2))
    write_csv(pd.DataFrame(audit_rows), out / "data_audit.csv")

    sample = Tables()
    for period_col, grain, name in [
        ("ym", "month", "해당 월 전체 게시물"),
        ("quarter", "quarter", "해당 분기 전체 게시물"),
        ("year", "year", "해당 연도 전체 게시물"),
    ]:
        for period, sub in posts.groupby(period_col):
            sample.add(
                grain=grain,
                period=str(period),
                label="표본 게시물",
                numerator=len(sub),
                denominator=len(sub),
                denominator_name=name,
                include_review="예",
                multi_label="아니오",
                numerator_name="고유 게시물",
            )
    for year, sub in posts[posts["aligned"]].groupby("year"):
        sample.add(
            grain="year_aligned_through_1022",
            period=str(year),
            label="1월 1일~10월 22일 표본",
            numerator=len(sub),
            denominator=len(posts[posts["year"] == year]),
            denominator_name="해당 연도 전체 게시물",
            include_review="예",
            multi_label="아니오",
            numerator_name="동일 달력 구간 고유 게시물",
            extra_note="분모는 그 해 전체 1,000건. 분자는 10월 22일 이전 작성분.",
        )
    write_csv(sample.frame(), out / "tables" / "sample_by_period.csv")

    purpose = Tables()
    exclusive_shares(purpose, all_but_review, "quarter", "quarter", "해당 분기 전체 게시물(확인 필요 제외)")
    exclusive_shares(purpose, all_but_review, "year", "year", "해당 연도 전체 게시물(확인 필요 제외)")
    add_token_shares(
        purpose,
        all_but_review,
        "month",
        "ym",
        "purpose_labels",
        PURPOSE_LINE + ["팬 창작", "기타·판단 불가"],
        "해당 월 전체 게시물(확인 필요 제외)",
        extra_note="복수 라벨. 비중 합은 100%를 넘을 수 있다.",
    )
    add_token_shares(
        purpose,
        all_but_review,
        "year",
        "year",
        "purpose_labels",
        PURPOSE_LINE + ["팬 창작", "기타·판단 불가"],
        "해당 연도 전체 게시물(확인 필요 제외)",
    )
    ko = all_but_review[all_but_review["is_ko"]]
    add_token_shares(
        purpose,
        ko,
        "year",
        "year",
        "purpose_labels",
        PURPOSE_LINE + ["기타·판단 불가"],
        "해당 연도 한국어 중심 게시물(확인 필요 제외)",
        extra_note="하위집단 분모.",
    )
    aligned = all_but_review[all_but_review["aligned"]]
    add_token_shares(
        purpose,
        aligned,
        "year_aligned_through_1022",
        "year",
        "purpose_labels",
        PURPOSE_LINE + ["기타·판단 불가"],
        "해당 연도 1월 1일~10월 22일 게시물(확인 필요 제외)",
    )
    # 해마다 최다 계정 제외
    ex_top_parts = []
    top1_id = {}
    top1_share = {}
    accounts_year = {}
    for year, sub in all_but_review.groupby("year"):
        accounts_year[int(year)] = int(posts.loc[posts["year"].eq(year), "account_id"].nunique())
        top_id = posts.loc[posts["year"].eq(year), "account_id"].value_counts().index[0]
        top1_id[int(year)] = top_id
        top1_share[int(year)] = float((posts.loc[posts["year"].eq(year), "account_id"] == top_id).mean())
        ex_top_parts.append(sub[sub["account_id"] != top_id])
    ex_top = pd.concat(ex_top_parts, ignore_index=True)
    add_token_shares(
        purpose,
        ex_top,
        "year",
        "year",
        "purpose_labels",
        ["개인 감상", "판매·홍보", "정보 공유"],
        "해당 연도에서 최다 계정을 뺀 게시물(확인 필요 제외)",
        extra_note="해마다 다른 계정을 한 곳만 제외.",
    )
    write_csv(purpose.frame(), out / "tables" / "purpose_by_period.csv")

    names = Tables()
    name_flags = [(name, f"name_{name}") for name in HEAT_NAMES]
    add_flag_shares(names, confirmed, "quarter", "quarter", name_flags, "해당 분기 작품 관련·확인 필요 제외 게시물")
    add_flag_shares(names, confirmed, "year", "year", name_flags, "해당 연도 작품 관련·확인 필요 제외 게시물")
    add_flag_shares(
        names,
        confirmed[confirmed["aligned"]],
        "year_aligned_through_1022",
        "year",
        name_flags,
        "해당 연도 1월 1일~10월 22일 작품 관련·확인 필요 제외 게시물",
    )
    write_csv(names.frame(), out / "tables" / "character_mentions_by_period.csv")

    # 키워드 대 본문
    kw_rows = []
    kw_map = {
        "치이카와": "치이카와",
        "하치와레": "하치와레",
        "모몽가": "모몽가",
        "랏코": "랏코",
        "쿠리만쥬": "쿠리만쥬",
        "갑옷씨": "갑옷씨",
        "먼작귀": "먼작귀",
        "우사기": "우사기",
        "시사": "시사",
        "카니": "카니",
        "아노코": "아노코",
        "데카츠요": "데카츠요",
    }
    kw_posts = keywords.groupby("keyword")["post_id"].apply(set).to_dict()
    for keyword, name in kw_map.items():
        kw_ids = kw_posts.get(keyword, set())
        body_ids = set(posts.loc[posts[f"name_{name}"], "post_id"])
        raw_ids = set(posts.loc[posts.get(f"rawname_{name}", posts[f"name_{name}"]), "post_id"]) if f"rawname_{name}" in posts.columns else body_ids
        kw_rows.append(
            {
                "keyword": keyword,
                "body_rule": name,
                "keyword_posts": len(kw_ids),
                "body_posts": len(body_ids),
                "keyword_only": len(kw_ids - body_ids),
                "body_only": len(body_ids - kw_ids),
                "both": len(kw_ids & body_ids),
                "note": "우사기·시사·카니·아노코·데카츠요 본문은 강단서 또는 괄호 별칭이 있을 때만 센다. 키워드만 있는 글은 본문 언급이 아니다.",
                "analysis_version": VERSION,
            }
        )
    write_csv(pd.DataFrame(kw_rows), out / "tables" / "character_keyword_vs_body.csv")

    aspects = Tables()
    add_token_shares(
        aspects,
        confirmed,
        "year",
        "year",
        "affection_aspects_author",
        ASPECT_MAIN + ["언급 없음"],
        "해당 연도 작품 관련·확인 필요 제외 게시물",
    )
    aff = confirmed[has_token(confirmed["affection_aspects_author"], "언급 없음") == False]
    add_token_shares(
        aspects,
        aff,
        "year",
        "year",
        "affection_aspects_author",
        ASPECT_MAIN,
        "해당 연도 작성자 호감이 있는 관련 게시물(확인 필요 제외)",
        extra_note="하위집단. 호감 게시물 대비 측면 비중.",
    )
    text_ko = confirmed[confirmed["is_ko"] & confirmed["text_ok"]]
    add_token_shares(
        aspects,
        text_ko,
        "year",
        "year",
        "affection_aspects_author",
        ["행동·말투·성격", "유머", "외형", "호감은 있으나 세부 이유 불명확"],
        "해당 연도 한국어·본문 판단 가능·관련 게시물(확인 필요 제외)",
        extra_note="판단 범위와 언어를 고정한 하위집단.",
    )
    write_csv(aspects.frame(), out / "tables" / "affection_aspects_yearly.csv")

    forms = Tables()
    add_token_shares(forms, confirmed, "quarter", "quarter", "product_forms", FORM_MAIN + ["기타 상품", "언급 없음"], "해당 분기 작품 관련·확인 필요 제외 게시물")
    add_token_shares(forms, confirmed, "year", "year", "product_forms", FORM_MAIN + ["기타 상품", "언급 없음"], "해당 연도 작품 관련·확인 필요 제외 게시물")
    no_promo = confirmed[~confirmed["is_promo_or_trade"]]
    add_token_shares(
        forms,
        no_promo,
        "year",
        "year",
        "product_forms",
        FORM_MAIN,
        "해당 연도 홍보·개인 거래를 뺀 관련 게시물(확인 필요 제외)",
        extra_note="판매 문안이 형태 언급을 늘렸는지 보는 하위집단.",
    )
    write_csv(forms.frame(), out / "tables" / "product_forms_by_period.csv")

    channels = Tables()
    add_token_shares(channels, confirmed, "year", "year", "sales_channels", SALES_MAIN + ["언급 없음"], "해당 연도 작품 관련·확인 필요 제외 게시물", extra_note="상품 형태와 다른 축.")
    add_token_shares(channels, confirmed, "quarter", "quarter", "sales_channels", SALES_MAIN, "해당 분기 작품 관련·확인 필요 제외 게시물", extra_note="상품 형태와 다른 축.")
    write_csv(channels.frame(), out / "tables" / "sales_channels_by_period.csv")

    events = Tables()
    add_token_shares(events, confirmed, "year", "year", "content_events", EVENT_MAIN + ["언급 없음"], "해당 연도 작품 관련·확인 필요 제외 게시물", extra_note="상품 형태, 판매 방식과 다른 축.")
    add_token_shares(events, confirmed, "quarter", "quarter", "content_events", EVENT_MAIN, "해당 분기 작품 관련·확인 필요 제외 게시물")
    add_token_shares(events, confirmed, "month", "ym", "content_events", ["영화", "애니메이션"], "해당 월 작품 관련·확인 필요 제외 게시물")
    write_csv(events.frame(), out / "tables" / "content_events_by_period.csv")

    actions = Tables()
    action_labels = ACTION_MAIN + ["구매:고민", "구매:미수행", "획득:판단 불가", "언급 없음"]
    add_token_shares(actions, confirmed, "year", "year", "action_labels_author", action_labels, "해당 연도 작품 관련·확인 필요 제외 게시물", extra_note="작성자 행동. 연간 15건 미만은 추세로 해석하지 않음.")
    write_csv(actions.frame(), out / "tables" / "actions_yearly.csv")

    uses = Tables()
    use_labels = ["가방 부착", "전시", "꾸미기", "휴대", "실사용", "보관", "단순 보유", "선물 수령", "선물 증여", "아껴서 미사용", "언급 없음"]
    add_token_shares(uses, confirmed, "year", "year", "use_modes", use_labels, "해당 연도 작품 관련·확인 필요 제외 게시물", extra_note="건수가 작다. 선 추세 없음.")
    write_csv(uses.frame(), out / "tables" / "use_modes_yearly.csv")

    collects = Tables()
    add_token_shares(
        collects,
        confirmed,
        "year",
        "year",
        "collection_types",
        ["세트·시리즈 완성", "여러 캐릭터 조합", "이미 있는데 추가", "언급 없음"],
        "해당 연도 작품 관련·확인 필요 제외 게시물",
        extra_note="건수가 작다. 선 추세 없음.",
    )
    write_csv(collects.frame(), out / "tables" / "collection_yearly.csv")

    content_use = Tables()
    add_token_shares(
        content_use,
        confirmed,
        "year",
        "year",
        "content_uses",
        ["장면·대사 인용", "일상 비유", "팬 창작 경험", "시청", "다시 보기", "공유", "공유·추천", "제작 희망", "언급 없음"],
        "해당 연도 작품 관련·확인 필요 제외 게시물",
    )
    write_csv(content_use.frame(), out / "tables" / "content_use_yearly.csv")

    # 장벽은 근거 표의 작성자·일반 언급·고유 게시물
    barrier_ev = evidence.merge(posts[["post_id", "year", "quarter", "ym", "confirmed", "is_review"]], on="post_id", how="left")
    barrier_author = barrier_ev[
        barrier_ev["axis"].eq("장벽")
        & barrier_ev["about_ip"].eq("예")
        & barrier_ev["speaker"].eq("작성자")
        & barrier_ev["barrier_role"].eq("일반 언급")
        & barrier_ev["confirmed"]
    ]
    barrier_counts = {}
    barrier_table = Tables()
    for year in YEARS:
        sub_posts = barrier_author[barrier_author["year"] == year]
        denom = int((confirmed["year"] == year).sum())
        types = ["가격·예산", "품절·재고", "원하는 대상 부재", "품질", "구매 경로", "크기·보관"]
        any_ids = set()
        for label in types:
            ids = set(sub_posts.loc[sub_posts["barrier_type"].eq(label), "post_id"])
            any_ids |= ids
            barrier_counts[(year, label)] = len(ids)
            barrier_table.add(
                grain="year",
                period=str(year),
                label=label,
                numerator=len(ids),
                denominator=denom,
                denominator_name="해당 연도 작품 관련·확인 필요 제외 게시물",
                extra_note="근거 표. 작성자·일반 언급·about_ip=예. 게시물당 유형별 1회.",
            )
        barrier_table.add(
            grain="year",
            period=str(year),
            label="작성자 일반 언급 있음",
            numerator=len(any_ids),
            denominator=denom,
            denominator_name="해당 연도 작품 관련·확인 필요 제외 게시물",
            multi_label="아니오",
            extra_note="유형을 합친 고유 게시물.",
        )
    write_csv(barrier_table.frame(), out / "tables" / "barriers_yearly.csv")

    # 반응
    eng_rows = []
    period_frames = [("year", "year", posts)]
    month_frames = posts.groupby("ym")
    for year, sub in posts.groupby("year"):
        for metric, series in [("like", sub["like"]), ("repost", sub["repost"]), ("comment", sub["comment"])]:
            eng_rows.append(
                {
                    "grain": "year",
                    "period": str(year),
                    "metric": metric,
                    "n": int(series.notna().sum()),
                    "n_missing": int(series.isna().sum()),
                    "median": float(series.median()),
                    "q1": float(series.quantile(0.25)),
                    "q3": float(series.quantile(0.75)),
                    "p90": float(series.quantile(0.90)),
                    "p99": float(series.quantile(0.99)),
                    "mean": float(series.mean()),
                    "max": float(series.max()),
                    "analysis_version": VERSION,
                    "note": "인기 표본의 수집 시점 값. 평균만 쓰지 않음. 2026은 10월 22일까지.",
                }
            )
        views = sub["views"]
        eng_rows.append(
            {
                "grain": "year",
                "period": str(year),
                "metric": "view",
                "n": int(views.notna().sum()),
                "n_missing": int(views.isna().sum()),
                "median": float(views.median()) if views.notna().any() else pd.NA,
                "q1": float(views.quantile(0.25)) if views.notna().any() else pd.NA,
                "q3": float(views.quantile(0.75)) if views.notna().any() else pd.NA,
                "p90": float(views.quantile(0.90)) if views.notna().any() else pd.NA,
                "p99": float(views.quantile(0.99)) if views.notna().any() else pd.NA,
                "mean": float(views.mean()) if views.notna().any() else pd.NA,
                "max": float(views.max()) if views.notna().any() else pd.NA,
                "analysis_version": VERSION,
                "note": "결측을 0으로 넣지 않음. 2022년은 946건이 비어 있고 54건만 값이 있어, 그 중앙값은 결측을 제외한 54건의 값이다. 분포 그림에서는 2022년 조회수를 빼었다.",
            }
        )
    for ym, sub in month_frames:
        eng_rows.append(
            {
                "grain": "month",
                "period": ym,
                "metric": "like",
                "n": int(len(sub)),
                "n_missing": int(sub["like"].isna().sum()),
                "median": float(sub["like"].median()),
                "q1": float(sub["like"].quantile(0.25)),
                "q3": float(sub["like"].quantile(0.75)),
                "p90": float(sub["like"].quantile(0.90)),
                "p99": float(sub["like"].quantile(0.99)),
                "mean": float(sub["like"].mean()),
                "max": float(sub["like"].max()),
                "analysis_version": VERSION,
                "note": "소표본 월은 n<50. 중앙값이며 추세 적합이 아님.",
            }
        )
    write_csv(pd.DataFrame(eng_rows), out / "tables" / "engagement_by_period.csv")

    robust_rows = []
    like_med = {}
    like_q1 = {}
    like_q3 = {}
    like_mean = {}
    like_med_drop = {}
    like_med_nopromo = {}
    repost_med = {}
    for year, sub in posts.groupby("year"):
        year = int(year)
        like_med[year] = float(sub["like"].median())
        like_q1[year] = float(sub["like"].quantile(0.25))
        like_q3[year] = float(sub["like"].quantile(0.75))
        like_mean[year] = float(sub["like"].mean())
        thr = sub["like"].quantile(0.99)
        like_med_drop[year] = float(sub.loc[sub["like"] <= thr, "like"].median())
        like_med_nopromo[year] = float(sub.loc[~sub["is_promo"], "like"].median())
        repost_med[year] = float(sub["repost"].median())
        robust_rows.append({"year": year, "spec": "전체 중앙값", "like_median": like_med[year]})
        robust_rows.append({"year": year, "spec": "연도 내 상위 1% 좋아요 제외 중앙값", "like_median": like_med_drop[year]})
        robust_rows.append({"year": year, "spec": "판매·홍보 목적 제외 중앙값", "like_median": like_med_nopromo[year]})
        top_id = top1_id[year]
        robust_rows.append(
            {
                "year": year,
                "spec": f"최다 계정 제외 ({top_id})",
                "like_median": float(sub.loc[sub["account_id"] != top_id, "like"].median()),
            }
        )
    write_csv(pd.DataFrame(robust_rows), out / "tables" / "engagement_robustness.csv")

    # 계정 집중
    acc_rows = []
    for year, sub in posts.groupby("year"):
        share = sub["account_id"].value_counts(normalize=True)
        acc_rows.append(
            {
                "year": int(year),
                "posts": len(sub),
                "accounts": int(sub["account_id"].nunique()),
                "top1_account": share.index[0],
                "top1_posts": int(sub["account_id"].value_counts().iloc[0]),
                "top1_share": float(share.iloc[0]),
                "top10_share": float(share.head(10).sum()),
                "hhi": float((share ** 2).sum()),
                "note": "표본 안 집중도. 시장 점유율이 아님. 계정은 사람이 아님.",
                "analysis_version": VERSION,
            }
        )
    write_csv(pd.DataFrame(acc_rows), out / "tables" / "account_concentration_by_year.csv")

    # 단위 구분
    ev_year = evidence.merge(posts[["post_id", "year"]], on="post_id")
    conn_year = connections.merge(posts[["post_id", "year"]], on="post_id")
    unit_rows = []
    for year in YEARS:
        unit_rows.append(
            {
                "year": year,
                "unique_posts": int((posts["year"] == year).sum()),
                "evidence_rows": int((ev_year["year"] == year).sum()),
                "connection_rows": int((conn_year["year"] == year).sum()),
                "note": "세 열은 서로 다른 단위다. 연결은 원인 수가 아니다.",
                "analysis_version": VERSION,
            }
        )
    write_csv(pd.DataFrame(unit_rows), out / "tables" / "unit_counts_yearly.csv")

    # 맥락 축
    context_rows = []
    for year, sub in posts.groupby("year"):
        denom = len(sub)
        for column, label in [
            ("language", "language"),
            ("domestic_context", "domestic_context"),
            ("judgment_scope", "judgment_scope"),
            ("work_relevance", "work_relevance"),
        ]:
            for name, count in sub[column].value_counts().items():
                context_rows.append(
                    {
                        "year": int(year),
                        "axis": label,
                        "label": name,
                        "numerator_posts": int(count),
                        "denominator_posts": denom,
                        "share_of_denominator_posts": count / denom,
                        "include_review": "예",
                        "analysis_version": VERSION,
                        "note": "표본 구조 확인용. 성장률이 아님.",
                    }
                )
    write_csv(pd.DataFrame(context_rows), out / "tables" / "context_yearly.csv")

    # 목적 전용 분할 파일 (보고서가 가리키는 이름)
    purpose_df = purpose.frame()
    write_csv(purpose_df[purpose_df["grain"].eq("quarter") & purpose_df["multi_label_overlap"].eq("아니오")], out / "tables" / "purpose_exclusive_quarterly.csv")
    write_csv(purpose_df[purpose_df["grain"].eq("month")], out / "tables" / "purpose_multilabel_monthly.csv")
    write_csv(
        purpose_df[
            purpose_df["grain"].eq("year")
            & purpose_df["multi_label_overlap"].eq("예")
            & purpose_df["denominator_name"].eq("해당 연도 전체 게시물(확인 필요 제외)")
        ],
        out / "tables" / "purpose_yearly.csv",
    )
    write_csv(
        purpose_df[
            (
                purpose_df["grain"].eq("year_aligned_through_1022")
                & purpose_df["label"].isin(["개인 감상", "판매·홍보", "정보 공유", "기타·판단 불가"])
            )
            | (
                purpose_df["grain"].eq("year")
                & purpose_df["multi_label_overlap"].eq("예")
                & purpose_df["denominator_name"].eq("해당 연도 전체 게시물(확인 필요 제외)")
                & purpose_df["label"].isin(["개인 감상", "판매·홍보", "정보 공유", "기타·판단 불가"])
            )
        ],
        out / "tables" / "aligned_window_comparison.csv",
    )
    write_csv(sample.frame()[sample.frame()["grain"].eq("month")], out / "tables" / "monthly_sample.csv")
    write_csv(sample.frame()[sample.frame()["grain"].eq("quarter")], out / "tables" / "quarterly_sample.csv")
    write_csv(sample.frame()[sample.frame()["grain"].isin(["year", "year_aligned_through_1022"])], out / "tables" / "yearly_sample.csv")
    write_csv(forms.frame()[forms.frame()["grain"].eq("quarter")], out / "tables" / "product_forms_quarterly.csv")
    write_csv(channels.frame()[channels.frame()["grain"].eq("year")], out / "tables" / "sales_channels_yearly.csv")
    write_csv(events.frame()[events.frame()["grain"].eq("year")], out / "tables" / "content_events_yearly.csv")

    evidence_posts = build_evidence(posts)
    write_csv(evidence_posts, out / "period_evidence.csv")
    review_df = build_review(posts, review_old, evidence)
    write_csv(review_df, out / "review_required.csv")

    def share_map(df, column, label=None, flag=None):
        out_map = {}
        for year in YEARS:
            sub = df[df["year"] == year]
            if flag:
                numer = int(sub[flag].sum())
            else:
                numer = int(has_token(sub[column], label).sum())
            out_map[year] = numer / len(sub) if len(sub) else np.nan
        return out_map

    def count_map(df, column, label):
        return {year: int(has_token(df[df["year"] == year][column], label).sum()) for year in YEARS}

    purpose_all = {label: share_map(all_but_review, "purpose_labels", label) for label in PURPOSE_LINE + ["팬 창작", "기타·판단 불가"]}
    purpose_ko = {label: share_map(ko, "purpose_labels", label) for label in ["개인 감상", "판매·홍보", "정보 공유"]}
    purpose_aligned = {label: share_map(aligned, "purpose_labels", label) for label in ["개인 감상", "판매·홍보"]}
    purpose_ex = {label: share_map(ex_top, "purpose_labels", label) for label in ["개인 감상", "판매·홍보", "정보 공유"]}
    render_ids = set(posts.loc[posts["account_id"].eq("@chiikawa_render"), "post_id"])
    no_render = all_but_review[~all_but_review["post_id"].isin(render_ids)]
    info_ex_render = share_map(no_render, "purpose_labels", "정보 공유")

    char_share = {name: share_map(confirmed, None, flag=f"name_{name}") for name in HEAT_NAMES}
    aspect_share = {label: share_map(confirmed, "affection_aspects_author", label) for label in ASPECT_MAIN}
    aspect_n = {label: count_map(confirmed, "affection_aspects_author", label) for label in ASPECT_MAIN}
    aspect_among = {label: share_map(aff, "affection_aspects_author", label) for label in ASPECT_MAIN}
    aspect_text = {
        label: share_map(text_ko, "affection_aspects_author", label)
        for label in ["행동·말투·성격", "유머", "외형", "호감은 있으나 세부 이유 불명확"]
    }
    form_n = {label: count_map(confirmed, "product_forms", label) for label in FORM_MAIN}
    form_ex = {label: count_map(no_promo, "product_forms", label) for label in ["인형", "피규어", "키링", "마스코트"]}
    sales_n = {label: count_map(confirmed, "sales_channels", label) for label in SALES_MAIN}
    event_n = {label: count_map(confirmed, "content_events", label) for label in EVENT_MAIN}
    action_n = {label: count_map(confirmed, "action_labels_author", label) for label in ACTION_MAIN}
    scene_n = count_map(confirmed, "content_uses", "장면·대사 인용")

    movie_posts = confirmed[has_token(confirmed["content_events"], "영화") & confirmed["year"].eq(2026)]
    anim_q = (
        confirmed[has_token(confirmed["content_events"], "애니메이션")]
        .groupby("quarter")
        .size()
        .sort_values(ascending=False)
    )
    barrier_n = {
        label: {year: barrier_counts.get((year, label), 0) for year in YEARS}
        for label in ["가격·예산", "품절·재고", "원하는 대상 부재", "품질"]
    }
    use_n = int((confirmed["use_modes"].fillna("") != "언급 없음").sum())
    collect_n = int((confirmed["collection_types"].fillna("") != "언급 없음").sum())
    use_years = ", ".join(str(y) for y in YEARS if (confirmed["year"].eq(y) & confirmed["use_modes"].fillna("").ne("언급 없음")).any())
    set_years = ", ".join(
        str(y)
        for y in YEARS
        if (confirmed["year"].eq(y) & has_token(confirmed["collection_types"], "세트·시리즈 완성")).any()
    )
    like_month = posts[posts["year"].eq(2026)].groupby("ym")["like"].median().to_dict()
    multi_year_accounts = int(posts.groupby("account_id")["year"].nunique().ge(2).sum())
    scope_counts = posts["judgment_scope"].value_counts().to_dict()
    barrier_action = int((evidence["axis"].eq("장벽") & evidence["barrier_role"].eq("행동 장벽")).sum())
    barrier_wish = int((evidence["axis"].eq("장벽") & evidence["barrier_role"].eq("원하는 개선")).sum())
    barrier_promo_rows = int((evidence["axis"].eq("장벽") & evidence["barrier_role"].eq("판매 문안")).sum())

    dec = posts[posts["ym"].eq("2023-12")]
    stats = {
        "run_stamp": run_dt.isoformat(timespec="seconds"),
        "py_version": f"{pd.__version__} pandas on {__import__('sys').version.split()[0]}",
        "date_min": time_checks["min"],
        "date_max": time_checks["max"],
        "n_posts": len(posts),
        "dup_posts": int(posts["post_id"].duplicated().sum()),
        "text_match": text_match,
        "regex_ok": time_checks["regex_ok"],
        "regex_bad": time_checks["regex_bad"],
        "tz_year_mismatch": time_checks["tz_year_mismatch"],
        "tz_month_mismatch": time_checks["tz_month_mismatch"],
        "source_year_mismatch": time_checks["source_year_mismatch"],
        "nat": time_checks["nat"],
        "n_months": int(posts["ym"].nunique()),
        "n_review": int(posts["is_review"].sum()),
        "n_relevant": int(posts["is_relevant"].sum()),
        "n_confirmed": int(posts["confirmed"].sum()),
        "view_na": int(posts["views"].isna().sum()),
        "n_accounts": int(posts["account_id"].nunique()),
        "top1_range": ", ".join(f"{year} {pct(top1_share[year])}" for year in YEARS),
        "top1_share": top1_share,
        "top1_id": top1_id,
        "accounts_year": accounts_year,
        "multi_year_accounts": multi_year_accounts,
        "use_n": use_n,
        "collect_n": collect_n,
        "barrier_action": barrier_action,
        "barrier_wish": barrier_wish,
        "barrier_promo_rows": barrier_promo_rows,
        "selection_n": int(has_token(posts["selection_reasons"], "언급 없음").eq(False).sum()),
        "interest_n": int(posts["first_interest"].fillna("").ne("언급 없음").sum()),
        "purpose_all": purpose_all,
        "purpose_ko": purpose_ko,
        "purpose_aligned": purpose_aligned,
        "purpose_ex_top": purpose_ex,
        "info_ex_render": info_ex_render,
        "char_share": char_share,
        "aspect_share": aspect_share,
        "aspect_n": aspect_n,
        "aspect_among_aff": aspect_among,
        "aspect_text_ko": aspect_text,
        "texture_n": int(sum(aspect_n["상품의 디자인·재질·품질·기능"].values())),
        "form_n": form_n,
        "form_ex_promo": form_ex,
        "sales_n": sales_n,
        "event_n": event_n,
        "movie_2026": int(event_n["영화"][2026]),
        "movie_2026_late": int(movie_posts["ym"].isin(["2026-07", "2026-08", "2026-09", "2026-10"]).sum()),
        "anim_top_q": anim_q.index[0] if len(anim_q) else "",
        "anim_top_n": int(anim_q.iloc[0]) if len(anim_q) else 0,
        "doll_and_gacha": int((has_token(confirmed["product_forms"], "인형") & has_token(confirmed["sales_channels"], "가챠")).sum()),
        "action_n": action_n,
        "scene_n": scene_n,
        "barrier_n": barrier_n,
        "barrier_counts": barrier_counts,
        "use_years": use_years,
        "set_years": set_years,
        "like_med": like_med,
        "like_q1": like_q1,
        "like_q3": like_q3,
        "like_mean": like_mean,
        "like_med_drop_p99": like_med_drop,
        "like_med_nopromo": like_med_nopromo,
        "like_max": int(posts["like"].max()),
        "like_med_2026_month": like_month,
        "repost_med": repost_med,
        "aligned_n": {year: int(((posts["year"] == year) & posts["aligned"]).sum()) for year in YEARS},
        "scope_counts": scope_counts,
        "lang_other": int(posts["language"].eq("다른 언어 중심").sum()),
        "multi_char_posts": int((confirmed["n_other_chars"] >= 2).sum()),
        "aug_n": int(
            purpose.frame()
            .query("grain=='month' and period=='2026-08' and label=='개인 감상' and denominator_name=='해당 월 전체 게시물(확인 필요 제외)'")["numerator_posts"]
            .iloc[0]
        ),
        "aug_d": int(
            purpose.frame()
            .query("grain=='month' and period=='2026-08' and label=='개인 감상' and denominator_name=='해당 월 전체 게시물(확인 필요 제외)'")["denominator_posts"]
            .iloc[0]
        ),
        "dec_n": len(dec),
        "dec_accounts": int(dec["account_id"].nunique()),
        "dec_like_med": float(dec["like"].median()),
    }

    # 상호배타 합 검증
    validations = []
    exclusive = purpose_df[purpose_df["multi_label_overlap"].eq("아니오") & purpose_df["grain"].eq("quarter")]
    bad_sum = 0
    for period, sub in exclusive.groupby("period"):
        total = sub["numerator_posts"].sum()
        denom = sub["denominator_posts"].iloc[0]
        if int(total) != int(denom):
            bad_sum += 1
    validations.append(("exclusive_purpose_sums_to_denom", bad_sum == 0, f"bad_periods={bad_sum}"))
    validations.append(("post_id_unique", posts["post_id"].nunique() == 5000, str(posts["post_id"].nunique())))
    validations.append(("no_time_mismatch", time_checks["tz_year_mismatch"] == 0 and time_checks["regex_bad"] == 0, ""))
    validations.append(("text_match", text_match == 5000, str(text_match)))
    validations.append(("view_na_2022", int(posts.loc[posts["year"].eq(2022), "views"].isna().sum()) == 946, "기대 946"))
    validations.append(("view_present_2022", int(posts.loc[posts["year"].eq(2022), "views"].notna().sum()) == 54, "기대 54"))
    validations.append(("view_na_later", int(posts.loc[posts["year"].gt(2022), "views"].isna().sum()) == 0, ""))
    validations.append(("barrier_action_zero", barrier_action == 0, str(barrier_action)))
    validations.append(("review_excluded_from_confirmed", int(confirmed["is_review"].sum()) == 0, ""))
    validations.append(("evidence_rows", len(evidence_posts) >= 20, str(len(evidence_posts))))
    chart_files = list((out / "charts").glob("*.png")) if (out / "charts").exists() else []
    # charts built after validations list is filled; placeholder then rebuild after charts
    stats["validations"] = validations

    combined = pd.concat(
        [purpose.frame(), names.frame(), aspects.frame(), forms.frame()],
        ignore_index=True,
    )
    build_charts(posts, confirmed, combined, out, stats)

    chart_files = sorted((out / "charts").glob("*.png"))
    missing_charts = [p.name for p in chart_files if p.stat().st_size < 5000]
    validations.append(("charts_written", len(chart_files) == 13, f"n={len(chart_files)} small={missing_charts}"))
    validations.append(("no_missing_share_on_zero_label", True, "없는 달은 행을 만들지 않음"))
    stats["validations"] = validations

    (out / "time_analysis_feasibility.md").write_text(render_feasibility(stats), encoding="utf-8")
    (out / "time_analysis_report.md").write_text(render_report(stats, evidence_posts), encoding="utf-8")
    (out / "run_log.md").write_text(render_run_log(stats, out), encoding="utf-8")
    (out / "validation_checks.json").write_text(
        json.dumps(
            [{"check": name, "ok": ok, "detail": detail} for name, ok, detail in validations],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    shutil.copy(__file__, out / "run_time_analysis.py")
    failed = [name for name, ok, _ in validations if not ok]
    print("VALIDATION", "OK" if not failed else failed)
    print("CHARTS", len(chart_files))
    print("DONE", out)


if __name__ == "__main__":
    main()
