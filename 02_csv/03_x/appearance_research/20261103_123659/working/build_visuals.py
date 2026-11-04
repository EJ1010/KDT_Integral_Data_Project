# -*- coding: utf-8 -*-
"""Contact sheet and count chart. Schematic is written separately as SVG."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

base = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659")
crops = base / "visuals" / "reference_images" / "crops"
out = base / "visuals"

order = [
    ("char_01_323x359.png", "치이카와"),
    ("char_02_326x370.png", "하치와레"),
    ("char_03_310x457.png", "우사기"),
    ("char_04_406x388.png", "모몽가"),
    ("char_05_307x352.png", "쿠리만쥬"),
    ("char_09_337x360.png", "랏코"),
    ("char_10_398x355.png", "시사"),
    ("char_12_303x409.png", "고혼야"),
    ("char_06_161x426.png", "갑옷씨"),
    ("char_11_415x333.png", "파자마"),
]
font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 14)
cell_w, cell_h = 220, 280
cols = 5
rows = 2
sheet = Image.new("RGB", (cols * cell_w, rows * cell_h + 70), (255, 255, 255))
draw = ImageDraw.Draw(sheet)
title = "공식 애니메이션 라인업 잘라낸 그림. 출처 anime-chiikawa.jp img_charapage.png. 확인 2026-11-03. 공식 설정값이 아님."
draw.text((12, 6), title, fill=(20, 20, 20), font=font)
draw.text((12, 26), "같은 그림의 정면 선 자세. 귀·꼬리·발이 상자에 포함된다. 갑옷씨는 키 대비를 보여 준다.", fill=(60, 60, 60), font=font)
for i, (name, label) in enumerate(order):
    im = Image.open(crops / name).convert("RGBA")
    r, c = divmod(i, cols)
    # fit
    max_w, max_h = cell_w - 24, cell_h - 36
    scale = min(max_w / im.width, max_h / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    im2 = im.resize((nw, nh), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", (cell_w - 16, cell_h - 28), (255, 255, 255))
    bg.paste(im2, ((bg.width - nw) // 2, (bg.height - nh) // 2), im2)
    x = c * cell_w + 8
    y = 52 + r * cell_h
    sheet.paste(bg, (x, y))
    draw.text((x, y + cell_h - 26), label, fill=(20, 20, 20), font=font)
sheet.save(out / "01_official_lineup_contact.png")

# Core unique-post counts. A post in two features is counted in each bar.
# Denominator for the note is 5000 posts. These bars are not shares of popularity.
counts = [
    ("표정", 20),
    ("상품 촉감", 5),
    ("볼·볼터치", 5),
    ("둥글다고 지목", 5),
    ("앞머리 변형", 5),
    ("옆모습", 2),
    ("주둥이", 2),
    ("짧은 팔다리", 1),
    ("뒷모습", 1),
    ("머리 색", 1),
    ("눈 긍정", 1),
    ("눈 부정", 1),
    ("상품 머리 크기 불만", 1),
    ("눈 조립 불만", 1),
    ("작중 옷", 2),
]
bar_w, row_h = 640, 28
h = 70 + row_h * len(counts) + 40
chart = Image.new("RGB", (820, h), (255, 255, 255))
d = ImageDraw.Draw(chart)
d.text((16, 8), "기존 5,000건 안에서 수준 1·2로 본 고유 게시물 수. 인기 순위가 아니다.", fill=(20, 20, 20), font=font)
d.text((16, 28), "분모 5,000게시물. 한 글이 여러 막대에 들어갈 수 있다. 판매 문안은 빠졌다.", fill=(60, 60, 60), font=font)
max_n = max(n for _, n in counts)
for i, (label, n) in enumerate(counts):
    y = 58 + i * row_h
    d.text((16, y + 4), label, fill=(20, 20, 20), font=font)
    bw = int(360 * n / max_n)
    d.rectangle((200, y + 4, 200 + bw, y + 20), fill=(70, 110, 160))
    d.text((210 + bw, y + 4), str(n), fill=(20, 20, 20), font=font)
chart.save(out / "03_core_mention_counts.png")
print("wrote visuals")
