# -*- coding: utf-8 -*-
import json
from pathlib import Path

root = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\hypothesis_review\20261103_121956\charts")
stats = json.loads((root / "stats.json").read_text(encoding="utf-8"))
order = ["H1", "H2", "H3"]
labels = ["가설1 이야기", "가설2 동물 외형", "가설3 휴대·일상"]
keys = [
    "작성자의 직접 이유·지지",
    "작성자의 명시적 평가·지지",
    "작성자 외 화자의 지지",
    "반대",
    "혼합",
    "중립·관련 언급",
    "판단 불가",
]
colors = ["#1d4e89", "#5b8fb8", "#7aa2c4", "#b85c38", "#c4a35a", "#8d8d8d", "#cfcfcf"]
short = ["직접 이유", "명시 평가", "타인 화자", "반대", "혼합", "중립", "판단 불가"]
width, height = 980, 460
left, top, chart_w, chart_h = 70, 54, 880, 300
series = [(k, [stats[h]["primary"].get(k, 0) for h in order], c) for k, c in zip(keys, colors)]
max_v = max(max(v) for _, v, _ in series)
band = chart_w / len(labels)
bar_w = band / (len(series) + 1)
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Malgun Gothic, sans-serif">',
    '<rect width="100%" height="100%" fill="#ffffff"/>',
    '<text x="24" y="28" font-size="16" font-weight="700">게시물당 하나의 판정</text>',
]
for i in range(4):
    y = top + chart_h - (chart_h * i / 3)
    val = round(max_v * i / 3)
    parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#e5e5e5"/>')
    parts.append(f'<text x="{left-6}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="#555">{val}</text>')
for gi, g in enumerate(labels):
    for si, ((name, vals, color), lab) in enumerate(zip(series, short)):
        v = vals[gi]
        h = chart_h * v / max_v if max_v else 0
        x = left + gi * band + bar_w * (si + 0.4)
        y = top + chart_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.85:.1f}" height="{h:.1f}" fill="{color}"/>')
        if v:
            parts.append(f'<text x="{x+bar_w*0.42:.1f}" y="{y-3:.1f}" font-size="10" text-anchor="middle">{v}</text>')
    parts.append(f'<text x="{left+gi*band+band/2:.1f}" y="{top+chart_h+22}" font-size="12" text-anchor="middle">{g}</text>')
lx = left
for lab, color in zip(short, colors):
    parts.append(f'<rect x="{lx}" y="{height-52}" width="12" height="12" fill="{color}"/>')
    parts.append(f'<text x="{lx+16}" y="{height-42}" font-size="12">{lab}</text>')
    lx += 125
parts.append(
    f'<text x="24" y="{height-16}" font-size="12" fill="#444">한 게시물당 하나. 합은 근거 게시물(가설1 246, 가설2 68, 가설3 79). 입력 5,000이 아니고, 노이즈로 뺀 글은 막대에 없다.</text>'
)
parts.append("</svg>")
(root / "01_primary_judgment.svg").write_text("\n".join(parts), encoding="utf-8")
print("sums", [sum(stats[h]["primary"].values()) for h in order])
