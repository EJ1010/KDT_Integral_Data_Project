# -*- coding: utf-8 -*-
"""소비 관련 댓글 후보 추출.

판정이 아니다. 한국어 중심·혼합 댓글에서 상품·소비 행동·시청·방문 단서가
같이 있는 댓글을 고른다. '보다' 하나만으로는 넣지 않는다.
원본 CSV와 기존 분석 결과는 읽기만 한다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

CHAR_DIR = Path(__file__).resolve().parents[1] / "A_캐릭터반응"
sys.path.insert(0, str(CHAR_DIR))
import analyze_A_character_v1 as base  # noqa: E402

OUT = Path(__file__).resolve().parent
RULE = "consume-screen-v1.1"

# 댓글 본문만 본다. 제목의 상품명으로 댓글을 넣지 않는다.
# v1.1: 뽑기·사야/직구/하울·샵을 보완. 과자·음료·누이·불러모아는 단독으로 넣지 않는다.
FAMILIES: list[tuple[str, str]] = [
    ("인형", r"인형|봉제|누이구루미|ぬいぐるみ"),
    ("키링참", r"키링|키홀더|아크릴\s*참|아크릴참|스트랩"),
    ("피규어", r"피규어|피규아|넨도(?:로이드)?"),
    ("카드스티커문구", r"스티커|포토\s*카드|포카|트레카|콜렉트\s*북|콜렉트북|다꾸|마스킹\s*테이프|(?<![가-힣])마테(?![가-힣])|(?<![가-힣])씰(?![가-힣])|카드\s*깡|띠부"),
    ("의류생활", r"파우치|에코백|티셔츠|후드티|잠옷|슬리퍼|담요|쿠션|머그|파자마(?!\s*파티즈)"),
    ("식품음료", r"콜라보\s*카페|팝업\s*카페|식완|베이커리|팝콘|카페\s*한정|(?:과자|음료|젤리).{0,16}(?:샀|구매|한정|콜라보|카페|하울)|(?:카페|콜라보|한정|편의점).{0,16}(?:과자|음료|젤리)"),
    ("가챠랜덤", r"가챠|가샤폰|가샤|랜덤\s*깡|랜덤깡|랜덤\s*박스|블라인드\s*박스"),
    ("쿠지", r"쿠지|제일\s*복권|이치방\s*쿠지|이치방쿠지|一番くじ"),
    ("인형뽑기", r"인형\s*뽑|뽑(?:기|았|아)|크레인\s*게임|클로\s*머신"),
    ("굿즈일반", r"굿즈|비공(?:식)?|언박싱|택배\s*깡|택배깡|굿즈\s*깡|가챠\s*깡|가챠깡|개봉기|하울"),
    ("구매획득", r"샀어|샀다|샀네|샀음|샀죠|사서|사야|사러|사\s*왔|사왔|구매|구입|직구|주문(?:했|함|중|넣)|소장|모으고\s*있|모으는\s*중|모았다|갖고\s*싶|가지고\s*싶|사고\s*싶|사\s*고\s*싶|질렀|질러|득템|재입고|품절|어디서\s*사|예약|중고|메루카리|번개장터|매입"),
    ("교환선물", r"교환(?:했|함|하)|선물(?:로|했|받|해\s*줬|해줬)|나눠\s*주|양도"),
    ("시청열람", r"정주행|극장판|다시\s*봤|몇\s*번(?:이나)?\s*봤|회차|원작|단행본|만화책|(?:영상|애니|영화|만화).{0,12}(?:봤|보았|보는\s*중|보고\s*있)|(?:봤|보았).{0,8}(?:영상|애니|극장판|영화)|영화\s*(?:보러|개봉|관람)|애니\s*(?:보러|정주행)|개봉(?:했|한|일|작)|관람"),
    ("방문", r"팝업(?:스토어|샵)?|매장|가챠\s*샵|가챠샵|애니메이트|다녀\s*왔|들렀|방문(?:했|함)|행사(?:에|를)\s*(?:갔|가|다녀)|소품\s*샵|굿즈\s*샵|치이카와\s*샵|키디랜드|다이소|로프트|백엔\s*샵|100엔"),
]
FAMILY_RES = [(name, re.compile(pat, re.I)) for name, pat in FAMILIES]

# 후보에서 빠진 댓글에 남아 있을 수 있는 느슨한 단서. 선별 누락 점검용이다.
MISS = [
    ("뽑", re.compile(r"뽑")),
    ("샵스토어", re.compile(r"샵|스토어|상점")),
    ("한정콜라보", re.compile(r"한정|콜라보")),
    ("예약품절", re.compile(r"예약|품절|재고")),
    ("중고거래", re.compile(r"중고|메루카리|번개|당근")),
    ("관람", re.compile(r"관람|상영|개봉")),
    ("소장수집", re.compile(r"수집|컬렉|콜렉|진열")),
]


def population() -> pd.DataFrame:
    comments = pd.read_csv(
        base.CMT,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "account_name", "comment_id", "comment_description", "title_without_hashtags"],
    )
    judge = pd.read_csv(
        base.JUDGE,
        encoding="utf-8-sig",
        usecols=["comment_id", "language_class", "reaction_target"],
    )
    videos = pd.read_csv(
        base.VID,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "account_name", "title_without_hashtags"],
    )
    df = comments.merge(judge, on="comment_id", how="left", validate="one_to_one")
    df = df.merge(
        videos.rename(columns={
            "account_id": "video_account_id",
            "account_name": "video_account_name",
            "title_without_hashtags": "video_title",
        }),
        on="post_id",
        how="left",
        validate="many_to_one",
    )
    if len(df) != len(comments):
        raise SystemExit("조인으로 댓글 행이 늘었다")
    df["text"] = df["comment_description"].map(base.clean)
    df["lang_re"] = df["text"].map(base.language_of)
    df["spam_re"] = df["text"].map(lambda s: bool(base.SPAM.search(s))) | df["reaction_target"].eq("광고·스팸")
    pop = df[df["lang_re"].isin(["한국어 중심", "혼합_한국어 중심"]) & ~df["spam_re"]].copy()
    if len(pop) != 67891 or pop["comment_id"].duplicated().any():
        raise SystemExit(f"모집단 {len(pop)} 고유 {pop['comment_id'].nunique()}")
    mismatch = int((pop["account_id"] != pop["video_account_id"]).sum())
    if mismatch:
        raise SystemExit(f"댓글 채널과 영상 채널이 다른 행 {mismatch}")
    return pop


def scan(text: str) -> list[str]:
    return [name for name, cre in FAMILY_RES if cre.search(text)]


def main() -> None:
    pop = population()
    pop["단서"] = pop["text"].map(scan)
    cand = pop[pop["단서"].map(bool)].copy()
    cand["단서"] = cand["단서"].map(lambda xs: "|".join(xs))
    cand["단서_수"] = cand["단서"].str.count(r"\|") + 1
    rest = pop[pop["단서"].map(lambda xs: not xs)].copy()

    fam_rows = []
    for name, _ in FAMILIES:
        sub = cand[cand["단서"].str.contains(name, regex=False)]
        fam_rows.append({
            "단서": name,
            "댓글": int(sub["comment_id"].nunique()),
            "영상": int(sub["post_id"].nunique()),
            "채널": int(sub["account_id"].nunique()),
        })
    fam = pd.DataFrame(fam_rows).sort_values("댓글", ascending=False)

    check = pd.DataFrame([
        {"항목": "기준댓글", "값": int(len(pop)), "메모": "언어 재계산 한국어 중심·혼합, 광고·스팸 제외"},
        {"항목": "후보댓글", "값": int(cand["comment_id"].nunique()), "메모": RULE},
        {"항목": "후보영상", "값": int(cand["post_id"].nunique()), "메모": ""},
        {"항목": "후보채널", "값": int(cand["account_id"].nunique()), "메모": "영상 채널"},
        {"항목": "비후보", "값": int(len(rest)), "메모": "규칙 미검출. 소비 없음이 확정된 것은 아님"},
        {"항목": "언어_한국어중심", "값": int((pop["lang_re"] == "한국어 중심").sum()), "메모": ""},
        {"항목": "언어_혼합", "값": int((pop["lang_re"] == "혼합_한국어 중심").sum()), "메모": ""},
    ])

    miss_parts = []
    rng = pd.Series(range(len(rest)))
    for label, cre in MISS:
        hit = rest[rest["text"].map(lambda s, c=cre: bool(c.search(s)))]
        take = hit.sample(n=min(12, len(hit)), random_state=20261103) if len(hit) else hit
        take = take.assign(점검=label, 해당댓글수=len(hit))
        miss_parts.append(take)
    misses = pd.concat(miss_parts, ignore_index=True) if miss_parts else pd.DataFrame()

    examples = []
    for name, _ in FAMILIES:
        sub = cand[cand["단서"].str.contains(name, regex=False)]
        take = sub.sample(n=min(8, len(sub)), random_state=20261103) if len(sub) else sub
        examples.append(take.assign(예시단서=name))
    shown = pd.concat(examples, ignore_index=True) if examples else pd.DataFrame()

    keep = [
        "comment_id", "post_id", "account_id", "account_name",
        "lang_re", "language_class", "text", "title_without_hashtags", "video_title",
        "단서", "단서_수",
    ]
    cand[keep].to_csv(OUT / "01_후보_댓글.csv", index=False, encoding="utf-8-sig")
    fam.to_csv(OUT / "00_후보구성.csv", index=False, encoding="utf-8-sig")
    check.to_csv(OUT / "00_모집단검증.csv", index=False, encoding="utf-8-sig")
    if len(shown):
        shown[keep + ["예시단서"]].to_csv(OUT / "00_후보예시.csv", index=False, encoding="utf-8-sig")
    if len(misses):
        misses[keep[:9] + ["점검", "해당댓글수"]].to_csv(
            OUT / "00_누락점검_표본.csv", index=False, encoding="utf-8-sig"
        )

    print(check.to_string(index=False))
    print(fam.to_string(index=False))
    print("누락점검", {label: int(rest["text"].map(lambda s, c=cre: bool(c.search(s))).sum()) for label, cre in MISS})


if __name__ == "__main__":
    main()
