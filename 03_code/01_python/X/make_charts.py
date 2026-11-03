# -*- coding: utf-8 -*-
"""Charts for the v2.3 team report. Does not reclassify posts."""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

BASE = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145")
OUT = BASE / "team_report"
CHART = OUT / "charts"
CHART.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#1F4E79"
BLUE = "#2F6F8F"
AMBER = "#C47B2B"
TEAL = "#3D7A6A"
GRAY = "#5C6B73"
PALE = "#F4F7F8"
RED = "#8C4A3A"


def hbar(labels, values, title, xlabel, path, note, color=BLUE):
    fig, ax = plt.subplots(figsize=(10.2, 5.6), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    y = list(range(len(labels)))[::-1]
    ax.barh(y, values, color=color, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_title(title, fontsize=14, loc="left", pad=12, color="#1A1A1A")
    xmax = max(values) * 1.18
    ax.set_xlim(0, xmax)
    for yi, v in zip(y, values):
        ax.text(v + xmax * 0.01, yi, f"{v:,}", va="center", fontsize=11, color="#1A1A1A")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.text(0.01, 0.01, note, fontsize=9, color=GRAY, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


aspect_labels = [
    "세부 이유 없는 평가\n(귀엽다·좋다 등)",
    "행동·말투·성격",
    "유머",
    "관계·장면",
    "위로·일상 연결",
    "외형",
    "상품 재질·품질",
]
aspect_values = [987, 117, 101, 48, 46, 35, 6]
hbar(
    aspect_labels,
    aspect_values,
    "호감 문장에 같이 적힌 측면  (작성자 호감 1,228건 중)",
    "고유 게시물 수. 한 글이 여러 측면에 들어갈 수 있어 합이 1,228을 넘습니다.",
    CHART / "01_affection_aspects.png",
    "출처: x_analysis_evidence.csv · 작성자 · 작품 관련 · 확정 · 기준 2026-10-30.v2.3  |  분모: 작성자 호감 게시물 1,228  |  관련 게시물 4,991",
)

behavior_labels = [
    "구매 완료",
    "판매 희망\n(본인이 팔고 싶다)",
    "획득 완료\n(겟·뽑기 등)",
    "소유 희망\n(갖고 싶다)",
    "구매 희망\n(사고 싶다)",
    "방문 경험",
    "구매 고민",
    "구매하지 않음",
]
behavior_values = [55, 50, 43, 39, 25, 18, 9, 4]
hbar(
    behavior_labels,
    behavior_values,
    "작성자가 말한 행동  (서로 다른 말입니다)",
    "고유 게시물 수. 한 글에 행동이 둘이면 각 칸에 다시 셉니다.",
    CHART / "02_behaviors.png",
    "출처: x_analysis_evidence.csv · 작성자 · 작품 관련 · 확정 · 기준 2026-10-30.v2.3  |  분모: 전체 게시물 5,000 (관련 4,991)",
    color=TEAL,
)

form_labels = ["인형", "피규어", "마스코트", "의류", "식품", "키링", "스티커"]
form_values = [289, 224, 188, 180, 145, 131, 111]
hbar(
    form_labels,
    form_values,
    "상품 형태가 본문에 나온 글  (선택 이유가 아닙니다)",
    "고유 게시물 수. 언급입니다. 고른 이유를 적은 글은 별도 8건입니다.",
    CHART / "03_product_mentions.png",
    "출처: x_analysis_evidence.csv · 상품형태 · 작품 관련 · 기준 2026-10-30.v2.3  |  의류에는 작중 차림이 섞일 수 있음  |  분모: 관련 게시물 4,991",
    color=AMBER,
)

# Year purpose shares. Review posts excluded. Denominators differ by year.
years = [2022, 2023, 2024, 2025, 2026]
denoms = [997, 984, 995, 998, 999]
personal_n = [245, 203, 219, 249, 313]
sales_n = [128, 123, 104, 56, 15]
personal = [n / d * 100 for n, d in zip(personal_n, denoms)]
sales = [n / d * 100 for n, d in zip(sales_n, denoms)]

fig, ax = plt.subplots(figsize=(10.2, 5.4), dpi=140)
fig.patch.set_facecolor("white")
ax.plot(years, personal, marker="o", color=BLUE, linewidth=2.2, label="개인 감상")
ax.plot(years, sales, marker="o", color=AMBER, linewidth=2.2, label="판매·홍보")
for x, y, n in zip(years, personal, personal_n):
    ax.text(x, y + 1.3, f"{n}", ha="center", fontsize=10, color=BLUE)
for x, y, n in zip(years, sales, sales_n):
    ax.text(x, y + 1.3, f"{n}", ha="center", fontsize=10, color=AMBER)
ax.set_xticks(years)
ax.set_ylim(0, 42)
ax.set_ylabel("그 해 표본 대비 비중 (%)", fontsize=11)
ax.set_title("인기 게시물 표본 안의 목적 구성  (시장 성장률이 아닙니다)", fontsize=14, loc="left", pad=12)
ax.legend(frameon=False, fontsize=11)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.text(
    0.01,
    0.01,
    "출처: time_analysis/tables/purpose_yearly.csv · 같은 기준 2026-10-30.v2.3  |  확인 필요 27건 제외  |  분모: 2022년 997, 2023년 984, 2024년 995, 2025년 998, 2026년 999\n"
    "한 글이 두 목적에 들어갈 수 있습니다. 2026년은 10월 22일까지입니다. 점 옆 숫자는 게시물 수입니다.",
    fontsize=9,
    color=GRAY,
)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(CHART / "04_purpose_by_year.png", bbox_inches="tight", facecolor="white")
plt.close()

# Side-by-side reading diagram. No causal arrows.
fig, ax = plt.subplots(figsize=(11.2, 6.2), dpi=140)
fig.patch.set_facecolor("white")
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
ax.set_title("문장에서 확인한 것과, 이 자료로 정하지 않는 것", fontsize=15, loc="left", color="#1A1A1A", pad=8)

left = patches.FancyBboxPatch((3, 8), 44, 82, boxstyle="round,pad=0.4,rounding_size=1.2",
                               facecolor="#E7F0F6", edgecolor=NAVY, linewidth=1.2)
right = patches.FancyBboxPatch((53, 8), 44, 82, boxstyle="round,pad=0.4,rounding_size=1.2",
                                facecolor="#F8F1E7", edgecolor=AMBER, linewidth=1.2)
ax.add_patch(left)
ax.add_patch(right)
ax.text(25, 84, "이 표본의 문장에서 확인", ha="center", va="center", fontsize=13, color=NAVY, fontweight="bold")
ax.text(75, 84, "이 자료만으로 정하지 않음", ha="center", va="center", fontsize=13, color=AMBER, fontweight="bold")

left_lines = [
    "짧은 칭찬이 호감 글의 다수",
    "938 / 1,228건은 귀엽다·좋다뿐",
    "",
    "이유가 적히면 행동·유머·장면",
    "외형을 문장으로 특정한 글 35건",
    "",
    "상품 이름은 자주 등장",
    "고른 이유를 연결한 글은 8건",
    "",
    "구매 완료 55, 사고 싶다 25,",
    "갖고 싶다 39는 다른 말",
]
right_lines = [
    "이용자가 외형을 안 좋아한다",
    "이미지가 필요한 글 1,772건",
    "",
    "언급이 많은 상품이 더 잘 팔린다",
    "매출·재구매 자료가 없음",
    "",
    "가격·품절 때문에 포기했다",
    "이유 연결로 확인된 글 0건",
    "",
    "2026년 감상 비중이 더 높다",
    "이것을 시장 성장으로 읽지 않음",
]
ax.text(6, 74, "\n".join(left_lines), ha="left", va="top", fontsize=11.5, color="#1A1A1A", linespacing=1.35)
ax.text(56, 74, "\n".join(right_lines), ha="left", va="top", fontsize=11.5, color="#1A1A1A", linespacing=1.35)
ax.text(50, 4, "나란히 둔 구분입니다. 화살표는 원인과 결과가 아닙니다.", ha="center", fontsize=10, color=GRAY)
fig.savefig(CHART / "05_what_the_text_shows.png", bbox_inches="tight", facecolor="white")
plt.close()

rows = []
for lab, val in zip(
    ["세부 이유 없는 평가", "행동·말투·성격", "유머", "관계·장면", "위로·일상 연결", "외형", "상품 재질·품질"],
    aspect_values,
):
    rows.append({
        "표": "호감 측면",
        "항목": lab,
        "고유 게시물": val,
        "분모 이름": "작성자 호감 게시물",
        "분모": 1228,
        "비중": round(val / 1228, 4),
        "겹침": "예. 한 글이 여러 측면에 들어갈 수 있음",
        "기준": "2026-10-30.v2.3",
        "출처": "x_analysis_evidence.csv 작성자·작품관련·확정",
    })
for lab, val in [
    ("세부 이유 없는 평가만", 938),
    ("세부 이유 없는 평가와 다른 측면", 49),
    ("다른 측면만", 241),
]:
    rows.append({
        "표": "호감 구성(겹치지 않음)",
        "항목": lab,
        "고유 게시물": val,
        "분모 이름": "작성자 호감 게시물",
        "분모": 1228,
        "비중": round(val / 1228, 4),
        "겹침": "아니오. 세 칸의 합은 1,228",
        "기준": "2026-10-30.v2.3",
        "출처": "x_analysis_evidence.csv",
    })
for lab, val in zip(
    ["구매 완료", "판매 희망", "획득 완료", "소유 희망", "구매 희망", "방문 경험", "구매 고민", "구매하지 않음"],
    behavior_values,
):
    rows.append({
        "표": "작성자 행동",
        "항목": lab,
        "고유 게시물": val,
        "분모 이름": "전체 게시물",
        "분모": 5000,
        "비중": round(val / 5000, 4),
        "겹침": "행동은 글마다 다시 셀 수 있음",
        "기준": "2026-10-30.v2.3",
        "출처": "x_analysis_evidence.csv 작성자·작품관련·확정",
    })
for lab, val in zip(form_labels, form_values):
    rows.append({
        "표": "상품 형태 언급",
        "항목": lab,
        "고유 게시물": val,
        "분모 이름": "작품 관련 게시물",
        "분모": 4991,
        "비중": round(val / 4991, 4),
        "겹침": "언급. 선택 이유 아님",
        "기준": "2026-10-30.v2.3",
        "출처": "x_analysis_evidence.csv 상품형태·작품관련",
    })
for y, d, pn, sn in zip(years, denoms, personal_n, sales_n):
    rows.append({
        "표": "연도별 목적",
        "항목": f"{y} 개인 감상",
        "고유 게시물": pn,
        "분모 이름": f"{y}년 확인필요 제외",
        "분모": d,
        "비중": round(pn / d, 4),
        "겹침": "목적 복수 가능",
        "기준": "2026-10-30.v2.3",
        "출처": "time_analysis/tables/purpose_yearly.csv",
    })
    rows.append({
        "표": "연도별 목적",
        "항목": f"{y} 판매·홍보",
        "고유 게시물": sn,
        "분모 이름": f"{y}년 확인필요 제외",
        "분모": d,
        "비중": round(sn / d, 4),
        "겹침": "목적 복수 가능",
        "기준": "2026-10-30.v2.3",
        "출처": "time_analysis/tables/purpose_yearly.csv",
    })

pd.DataFrame(rows).to_csv(OUT / "report_counts.csv", index=False, encoding="utf-8-sig")
print("charts ok", list(CHART.glob('*.png')))
