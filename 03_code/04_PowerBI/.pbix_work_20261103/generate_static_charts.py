from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(r"C:\Users\user\Desktop\KDT_2026\프로젝트\02_데이터_프로젝트\03_code\04_PowerBI")
OUT = ROOT / ".pbix_work_20261103" / "static_charts"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "Malgun Gothic",
        "axes.unicode_minus": False,
        "font.size": 13,
        "axes.titlesize": 18,
        "axes.titleweight": "bold",
    }
)

DIST = pd.read_csv(ROOT / "analysis" / "summary_axis_distribution.csv")
CROSS = pd.read_csv(ROOT / "analysis" / "analysis_cross_pairs.csv")
BLUE = "#5B5BD6"
PINK = "#D05A6E"
NAVY = "#24245E"
GRID = "#E6E8F0"


def save_bar(axis_id: str, filename: str, color: str, title: str) -> None:
    frame = DIST.loc[DIST["axis_id"].eq(axis_id)].sort_values("share_pct")
    fig, ax = plt.subplots(figsize=(12, 7), facecolor="white")
    bars = ax.barh(frame["label"], frame["share_pct"], color=color, height=0.66)
    ax.set_title(title, color=NAVY, loc="left", pad=18)
    ax.set_xlabel("언급률 (%)", color="#555A66")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0, colors="#30343B")
    ax.tick_params(axis="x", colors="#6B7078")
    max_value = float(frame["share_pct"].max())
    ax.set_xlim(0, max_value * 1.18)
    for bar, value in zip(bars, frame["share_pct"]):
        ax.text(
            bar.get_width() + max_value * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            va="center",
            fontsize=12,
            color="#30343B",
        )
    fig.tight_layout(pad=2)
    fig.savefig(OUT / filename, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_heatmap(analysis_type: str, filename: str, title: str) -> None:
    frame = CROSS.loc[CROSS["analysis_type"].eq(analysis_type)].copy()
    matrix = frame.pivot(index="left_label", columns="right_label", values="cooccurrence_post_count").fillna(0)
    row_order = frame.groupby("left_label")["cooccurrence_post_count"].sum().sort_values(ascending=False).index
    col_order = frame.groupby("right_label")["cooccurrence_post_count"].sum().sort_values(ascending=False).index
    matrix = matrix.reindex(index=row_order, columns=col_order)

    fig, ax = plt.subplots(figsize=(14, 8), facecolor="white")
    image = ax.imshow(matrix.values, cmap="Purples", aspect="auto")
    ax.set_title(title, color=NAVY, loc="left", pad=18)
    ax.set_xticks(np.arange(matrix.shape[1]), labels=matrix.columns, rotation=38, ha="right")
    ax.set_yticks(np.arange(matrix.shape[0]), labels=matrix.index)
    ax.tick_params(length=0, labelsize=11)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = int(matrix.iloc[i, j])
            if value:
                threshold = matrix.values.max() * 0.55
                ax.text(j, i, f"{value:,}", ha="center", va="center", fontsize=9, color="white" if value > threshold else "#24245E")
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("동시출현 게시물 수")
    fig.tight_layout(pad=2)
    fig.savefig(OUT / filename, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


save_bar("project_category", "project_category.png", BLUE, "프로젝트 평가영역별 게시물 언급률")
save_bar("goods_type", "goods_type.png", BLUE, "굿즈 유형 분포")
save_bar("consumption_behavior", "consumption_behavior.png", PINK, "소비·소장 행동 분포")
save_heatmap("goods_type_x_behavior", "goods_behavior_heatmap.png", "굿즈 유형 × 소비·소장 행동")
save_bar("visual_element", "visual_element.png", BLUE, "시각적 매력 요소")
save_bar("visual_reaction", "visual_reaction.png", PINK, "시각적 매력에 연결된 반응")
save_heatmap("visual_element_x_reaction", "visual_reaction_heatmap.png", "시각 요소 × 반응")

print(f"Generated 7 chart images in {OUT}")
