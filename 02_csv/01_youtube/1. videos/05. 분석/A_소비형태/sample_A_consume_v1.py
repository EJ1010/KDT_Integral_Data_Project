# -*- coding: utf-8 -*-
"""소비 후보 표집.

전체 8천 건대를 한 번에 읽지 않는다.
시험 표본은 단서 유형을 고르게 보고, 순위용 표본은 후보에서 무작위다.
보강 표본은 드문 유형 확인용이며 순위에 넣지 않는다.
"""
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent
ORDER = [
    "인형뽑기", "쿠지", "가챠랜덤", "키링참", "피규어", "인형",
    "카드스티커문구", "식품음료", "의류생활", "방문", "교환선물",
    "시청열람", "굿즈일반", "구매획득",
]


def stratum(flags: str) -> str:
    have = set(flags.split("|"))
    for name in ORDER:
        if name in have:
            return name
    return "기타"


def main() -> None:
    raise SystemExit(
        "무작위 200건 표본과 그 판정은 삭제했다. "
        "시험·보강이 들어 있는 02_표집.csv를 다시 쓰지 않기 위해 이 스크립트는 중단한다."
    )
    cand = pd.read_csv(OUT / "01_후보_댓글.csv", encoding="utf-8-sig")
    cand["층"] = cand["단서"].map(stratum)
    pilot_parts = []
    for name, sub in cand.groupby("층"):
        take = sub.sample(n=min(6, len(sub)), random_state=20261103)
        pilot_parts.append(take.assign(표본구분="시험", 층=name))
    pilot = pd.concat(pilot_parts, ignore_index=True)
    rest = cand[~cand["comment_id"].isin(pilot["comment_id"])]
    random_part = rest.sample(n=200, random_state=20261104).assign(표본구분="무작위")
    # 순위에 쓰지 않는 보강. 무작위 200에 해당 층이 8건 미만이면 8건까지 채운다.
    boost_parts = []
    for name in ("식품음료", "교환선물", "키링참", "인형뽑기", "쿠지"):
        have = random_part[random_part["층"] == name]
        need = max(0, 8 - len(have))
        pool = rest[~rest["comment_id"].isin(random_part["comment_id"])]
        pool = pool[pool["층"] == name]
        if need and len(pool):
            boost_parts.append(pool.sample(n=min(need, len(pool)), random_state=20261105).assign(표본구분="보강"))
    boost = pd.concat(boost_parts, ignore_index=True) if boost_parts else pd.DataFrame(columns=random_part.columns)
    sample = pd.concat([pilot, random_part, boost], ignore_index=True)
    sample.insert(0, "표본번호", range(1, len(sample) + 1))
    keep = [
        "표본번호", "표본구분", "층", "comment_id", "post_id", "account_id", "account_name",
        "lang_re", "단서", "text", "title_without_hashtags", "video_title",
    ]
    sample[keep].to_csv(OUT / "02_표집.csv", index=False, encoding="utf-8-sig")
    summary = sample.groupby(["표본구분", "층"]).size().reset_index(name="댓글")
    summary.to_csv(OUT / "00_표집구성.csv", index=False, encoding="utf-8-sig")
    print("표집", len(sample), "시험", (sample["표본구분"] == "시험").sum(), "무작위", (sample["표본구분"] == "무작위").sum(), "보강", (sample["표본구분"] == "보강").sum())
    print(sample.groupby("표본구분")["층"].value_counts().to_string())


if __name__ == "__main__":
    main()
