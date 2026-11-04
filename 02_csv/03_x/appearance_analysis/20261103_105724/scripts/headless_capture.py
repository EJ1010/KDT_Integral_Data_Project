# -*- coding: utf-8 -*-
"""필요한 게시물만 화면 없는 Chrome으로 연다.

사용자 요청으로 바탕화면 창은 띄우지 않는다.
이미 저장된 PNG는 다시 열지 않는다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
OUT = ROOT / "appearance_analysis" / "20261103_105724"
SHOT = OUT / "working" / "headless_shots"
LOG = OUT / "working" / "headless_capture_log.csv"
POSTS = ROOT / "normalized" / "x_posts.csv"

IDS = [
    "2108901582838661630",
    "1759765157285404916",
    "1651983324230090753",
    "2037759934197387522",
    "1571131866656407554",
    "1593857972157165568",
    "1951140824043098584",
    "1535067039521738753",
    "1899751571908685985",
    "1959281741073387638",
    "2090813740510023857",
    "2095779596545442160",
    "1996459696027513149",
    "1910683993890316493",
    "1762682498897871320",
    "1548260243435843584",
    "1697619073587454385",
    "1740151252963762270",
    "1799648824262320492",
    "2100229868646797669",
    "1507668678770257920",
    "1521657940088070145",
    "1593962423849222146",
    "2107782470808826265",
    "2091425273355149615",
    "1609191102707560449",
    "1797300694581727443",
    "1568559174396805121",
]


def main() -> None:
    SHOT.mkdir(parents=True, exist_ok=True)
    posts = pd.read_csv(POSTS, dtype=str, keep_default_na=False)
    url_of = dict(zip(posts.post_id, posts.post_url))
    rows = []
    if LOG.exists():
        prev = pd.read_csv(LOG, dtype=str, keep_default_na=False)
        done = set(prev.loc[prev.status.eq("ok"), "post_id"])
        rows = prev.to_dict("records")
    else:
        done = set()
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        ctx = browser.new_context(
            user_agent=ua,
            locale="ko-KR",
            viewport={"width": 1100, "height": 1400},
        )
        page = ctx.new_page()
        for i, pid in enumerate(IDS):
            dest = SHOT / f"{pid}.png"
            if pid in done and dest.exists():
                print("skip", pid)
                continue
            url = url_of.get(pid, f"https://x.com/i/status/{pid}")
            status = "ok"
            note = ""
            title = ""
            final = ""
            try:
                resp = page.goto(url, wait_until="commit", timeout=45000)
                code = None if resp is None else resp.status
                page.wait_for_timeout(4500)
                title = page.title()
                final = page.url
                body = page.inner_text("body")
                if "Something went wrong" in body or "문제가 발생" in body:
                    status = "오류 화면"
                if "로그인" in body and "게시" not in title and len(body) < 200:
                    status = "로그인 벽"
                page.screenshot(path=str(dest))
                note = f"http={code}; chars={len(body)}"
            except Exception as exc:
                status = "실패"
                note = str(exc)[:300]
            rows = [r for r in rows if r.get("post_id") != pid]
            rows.append(
                {
                    "post_id": pid,
                    "url": url,
                    "status": status,
                    "title": title[:180],
                    "final_url": final,
                    "shot": str(dest) if dest.exists() else "",
                    "note": note,
                    "method": "playwright headless chrome, 창 없음",
                }
            )
            pd.DataFrame(rows).to_csv(LOG, index=False, encoding="utf-8-sig")
            print(i, pid, status, title[:60])
            time.sleep(8)
        browser.close()
    print("done", len(rows))


if __name__ == "__main__":
    main()
