# -*- coding: utf-8 -*-
"""Charts for the character-reaction report. Counts come from the v3 tables."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(r"c:\DATA\KDT_Integral_Data_Project\02_csv\03_x\character_reaction\20261103_1635")
TABLES = BASE / "tables"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)

men = pd.read_csv(TABLES / "05_character_mentions.csv")
appeal = pd.read_csv(TABLES / "06_character_appeal.csv")

# Panel: other characters' body mentions, and Chiikawa name roles.
order = ["하치와레", "랏코", "우사기", "모몽가", "쿠리만쥬", "시사", "갑옷씨", "카니", "아노코", "데카츠요", "오데"]
m = men.set_index("character")
fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.35, 1]})

vals = [int(m.loc[c, "posts"]) for c in order]
axes[0].barh(order[::-1], vals[::-1], color="#4C78A8")
axes[0].set_xlabel("고유 게시물 수")
axes[0].set_title("캐릭터 이름이 본문에 있는 글")
for y, v in enumerate(vals[::-1]):
    axes[0].text(v + 8, y, str(v), va="center", fontsize=8)

roles = ["치이카와·이름출현", "치이카와·불명확", "치이카와·작품", "치이카와·주인공"]
role_labels = ["이름 출현", "역할 불명확", "작품·상품 맥락", "주인공 문법"]
rvals = [int(m.loc[c, "posts"]) for c in roles]
axes[1].barh(role_labels[::-1], rvals[::-1], color="#F2A2A2")
axes[1].set_xlabel("고유 게시물 수")
axes[1].set_title("치이카와 이름의 역할")
for y, v in enumerate(rvals[::-1]):
    axes[1].text(v + 20, y, str(v), va="center", fontsize=8)

fig.suptitle(
    "한국어 중심·한국어 중심 혼합 4,773게시물 안의 본문 언급\n"
    "같은 글에서 같은 이름은 1번. 여러 캐릭터는 각각 포함. 검색어만 있는 글은 제외.\n"
    "치이카와 역할은 한 글이 둘 이상에 들어갈 수 있어 막대 합이 이름 출현 2,785가 아니다.",
    fontsize=10,
)
fig.tight_layout(rect=(0, 0, 1, 0.86))
fig.savefig(CHARTS / "01_character_mentions.png", dpi=140)
plt.close()

# Heatmap: directed evaluations. Generic affection stays in the table.
cols = ["외형·표정", "목소리·말투", "성격", "행동·움직임", "이야기·설정", "구체적 이유 없는 호감"]
heat_chars = appeal[appeal.eval_posts >= 6].copy()
heat_chars = heat_chars.sort_values("eval_posts", ascending=False)
mat = heat_chars[cols].to_numpy()
fig, ax = plt.subplots(figsize=(11.2, 5.2))
im = ax.imshow(mat, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(cols)))
ax.set_xticklabels(cols, rotation=30, ha="right")
ylabels = [f"{r.character}  (평가 {int(r.eval_posts)}건)" for r in heat_chars.itertuples()]
ax.set_yticks(range(len(ylabels)))
ax.set_yticklabels(ylabels)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, int(mat[i, j]), ha="center", va="center", fontsize=8, color="black")
ax.set_title(
    "캐릭터를 작성자가 평가한 글에서 짚은 요소\n"
    "칸은 고유 게시물 수. 한 글이 여러 칸에 들어갈 수 있다.\n"
    "괄호가 분모이고, 특징을 말하지 않은 호감도 분모에 있다. 계정 수가 아니다.",
    fontsize=10,
)
fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="고유 게시물")
fig.tight_layout()
fig.savefig(CHARTS / "02_character_appeal_heatmap.png", dpi=140)
plt.close()

# Reaction targets. Counts are unique posts and can overlap.
tgt = pd.read_csv(TABLES / "08_reaction_targets.csv")
order_t = ["특정 캐릭터", "불명확", "굿즈", "작품·스토리·세계관", "캐릭터 간 관계", "팬아트·번역·편집·창작자"]
tgt = tgt.set_index("reaction_target").loc[order_t]
fig, ax = plt.subplots(figsize=(10.5, 4.6))
vals = tgt["posts"].astype(int).tolist()
ax.barh(order_t[::-1], vals[::-1], color="#59A14F")
ax.set_xlabel("고유 게시물 수")
for y, v in enumerate(vals[::-1]):
    ax.text(v + 8, y, str(v), va="center", fontsize=9)
ax.set_xlim(0, max(vals) * 1.18)
ax.set_title(
    "작성자가 반응한 대상\n"
    "분석 대상 중 작성자 근거가 있는 게시물 1,467건. 한 글이 둘 이상이면 각각 포함.\n"
    "여섯 막대의 합 1,567은 게시물 수가 아니다.",
    fontsize=10,
)
fig.tight_layout()
fig.savefig(CHARTS / "04_reaction_targets.png", dpi=140)
plt.close()

# Evidence card
fig = plt.figure(figsize=(10.5, 4.6))
ax = fig.add_axes((0.04, 0.06, 0.92, 0.88))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, linewidth=1.2, edgecolor="#222222"))
ax.text(
    0.04,
    0.90,
    "이유를 문장으로 남긴 랏코 반응은 적고, 그중 반복된 소재는 목소리다.",
    fontsize=12,
    fontweight="bold",
    va="top",
)
ax.text(
    0.04,
    0.74,
    "랏코를 작성자가 평가한 122건 중, 같은 문장에 이름과 목소리가 함께 있는 글은 8건·계정 5개.\n"
    "한 계정(@EnmuS2_)이 4건이다. 그 계정을 빼면 4건·계정 4개.\n"
    "규칙이 앞 문장까지 이어 센 목소리는 11건·8계정. 특징 없는 호감은 103/122다.",
    fontsize=10,
    va="top",
)
ax.text(
    0.04,
    0.46,
    "사례  @EnmuS2_  ·  게시물 2083380528032735262\n"
    "“보송보송 귀엽게 생겨서 … 귀여운 목소리 나올 거라고 생각하는데,\n"
    "부드러운 미남목소리가 나오는 게 … 캐릭터답다고 느껴져서”\n"
    "생김과 어긋난 목소리까지 설명한 반복은 이 계정에 있다. 다른 계정은 ‘목소리가 좋다’에 가깝다.",
    fontsize=9.5,
    va="top",
)
ax.text(
    0.04,
    0.16,
    "국내 후보에게 물을 질문\n"
    "그림만 보여주고 나온 ‘귀엽다’를 외형 이유로 받지 말고, 목소리를 같이 들려 준 뒤\n"
    "어느 결을 이유로 말하는지 확인할 수 있는가.",
    fontsize=10,
    va="top",
)
fig.savefig(CHARTS / "03_x_evidence_card.png", dpi=140)
plt.close()
print("charts ok")
