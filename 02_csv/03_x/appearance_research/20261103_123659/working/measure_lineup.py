# -*- coding: utf-8 -*-
"""Measure the official anime lineup image. Values belong to this image only."""
from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path

crops = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659\visuals\reference_images\crops")
ann = crops.parent / "annotated"
ann.mkdir(exist_ok=True)
names = {
    1: "chiikawa",
    2: "hachiware",
    3: "usagi",
    4: "momonga",
    5: "kurimanju",
    6: "yoroi_pochette",
    7: "yoroi_2",
    8: "yoroi_3",
    9: "rakko",
    10: "shisa",
    11: "pajamas",
    12: "furuhonya",
}


def erode(mask, times):
    m = mask.copy()
    for _ in range(times):
        up = np.pad(m, 1, constant_values=False)[:-2, 1:-1]
        down = np.pad(m, 1, constant_values=False)[2:, 1:-1]
        left = np.pad(m, 1, constant_values=False)[1:-1, :-2]
        right = np.pad(m, 1, constant_values=False)[1:-1, 2:]
        m = m & up & down & left & right
    return m


def label(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    current = 0
    # iterative flood via stack
    ys, xs = np.where(mask)
    seen = np.zeros_like(mask, dtype=bool)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        current += 1
        stack = [(y0, x0)]
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            lab[y, x] = current
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
    return lab, current


lines = []
for fp in sorted(crops.glob("char_*.png")):
    n = int(fp.name.split("_")[1])
    im = Image.open(fp).convert("RGBA")
    arr = np.array(im)
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    body = alpha > 40
    er = erode(body, 7)
    lum = rgb.mean(axis=2)
    dark = er & (lum < 90)
    lab, num = label(dark)
    ys, xs = np.where(body)
    top, bot = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    bh = bot - top + 1
    bw = right - left + 1
    mid = (top + bot) // 2
    row = body[mid]
    rx = np.where(row)[0]
    mid_w = int(rx.max() - rx.min() + 1) if len(rx) else 0
    # width of the central mass excluding thin side protrusions: median row width of middle 40%
    widths = []
    for y in range(top + int(bh * 0.25), top + int(bh * 0.75)):
        rr = np.where(body[y])[0]
        if len(rr):
            widths.append(rr.max() - rr.min() + 1)
    med_w = int(np.median(widths)) if widths else 0
    header = (
        f"== {n} {names.get(n)} px={im.size[0]}x{im.size[1]} "
        f"content_bbox={bw}x{bh} w/h={bw/bh:.3f} "
        f"mid_w/h={mid_w/bh:.3f} mid40_median_w/h={med_w/bh:.3f}"
    )
    print(header)
    lines.append(header)
    comps = []
    for i in range(1, num + 1):
        yy, xx = np.where(lab == i)
        if len(xx) < 12:
            continue
        comps.append((len(xx), float(xx.mean()), float(yy.mean()), int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())))
    comps.sort(reverse=True)
    im2 = im.copy()
    dr = ImageDraw.Draw(im2)
    for area, cx, cy, x0, y0, x1, y1 in comps[:10]:
        rel_y = (cy - top) / bh
        rel_x = (cx - left) / bw
        rowt = f"  dark area={area:4d} relx={rel_x:.3f} rely={rel_y:.3f} box={x1-x0+1}x{y1-y0+1}"
        print(rowt)
        lines.append(rowt)
        dr.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=(255, 0, 0, 255), width=2)
    # mark 50% height
    dr.line((0, mid, im.width, mid), fill=(0, 180, 255, 255), width=1)
    im2.save(ann / f"{n:02d}_{names.get(n)}.png")

outp = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659\working\lineup_measures.txt")
outp.write_text("\n".join(lines), encoding="utf-8")
