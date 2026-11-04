# -*- coding: utf-8 -*-
"""전체 본문에서 외형 호감 후보를 고른다.

이 단계는 규칙 기반 후보 탐색이다. 라벨의 최종 판단이 아니다.
기존 분석 라벨은 읽지 않는다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
OUT = ROOT / "appearance_analysis" / "20261103_105724" / "working"
POSTS = ROOT / "normalized" / "x_posts.csv"

# 검색용으로만 늘어진 글자와 공백을 줄인다. 원문은 따로 둔다.
ELONG = re.compile(r"(.)\1{2,}")
HSPACE = re.compile(r"(?<=[가-힣])\s+(?=[가-힣])")

FEATURE_GROUPS = {
    "얼굴머리형태": r"얼굴|얼골|두상|머리통|머리\s*모양|머리\s*형태|윤곽|실루엣|둥글|둥근|동글|동그랗|동그란|똥글|원형|동그라미|공처럼|만두|찹쌀|모찌처럼|콩알|방울토마토",
    "눈눈매": r"눈망울|눈매|왕눈|눈꼬리|쌍커풀|초롱|눈동자|큰\s*눈|동그란\s*눈|눈이\s*(?:크|동|반짝|빛|작|초롱)|반짝(?:이|이는)?\s*눈|빛나는\s*눈",
    "입볼": r"볼살|볼빵|볼콕|볼터치|보조개|입술|입\s*모양|작은\s*입|입이\s*작|입꼬리|수염|볼이|분홍\s*볼|핑크\s*볼|홍조|볼\s*빨",
    "신체비율": r"팔다리|짧은\s*팔|짧은\s*다리|짧은\s*손|짧은\s*발|몸통|체형|비율|등신|데포르메|조막|앙증|작디작|자그마|아담|통통|동글동글|꼬리|긴\s*귀|귀가\s*길|작은\s*몸|몸이\s*(?:작|둥|동|짧)|손발|덩치|미니\s*사이즈|콩만",
    "표정": r"표정|웃는\s*얼굴|우는\s*얼굴|울상|눈물|멍한|멍때|멍한\s*표정|무표정|미소|윙크|눈웃음|화난|놀란\s*표정|해맑|새침|시무룩|찡|뿌듯|황당한\s*표정|입꼬리",
    "자세실루엣": r"포즈|자세|옆모습|뒷모습|뒷태|정면|실루엣|앉은|누운\s*모습|돌아본|고개\s*돌|기지개",
    "색상무늬": r"색감|배색|색깔|파스텔|무늬|컬러감|컬러\s*조합|분홍\s*볼|파란\s*귀|노란\s*귀|얼룩",
    "의상소품모습": r"옷\s*입|의상|코스튬|코스프레|모자|리본|망토|앞치마|오징어\s*옷|잠옷|파자마|머리띠|안경",
    "상품구현": r"말랑|폭신|부들|촉감|재질|마감|입체|봉제|자수|프린팅|퀄리티|디테일|말캉|폭신폭신|솜",
    "그림체": r"작화|그림체|일러스트|선화|작풍|그림\s*스타일|이\s*그림|이\s*짤|이\s*일러",
}

EVAL_RE = re.compile(
    r"귀엽|귀여|커여|기여|기엽|기염|깜찍|사랑스|존귀|이쁘|예쁘|예뻐|이뻐|멋있|못생|"
    r"별로|싫|안\s*귀|취향|반했|홀렸|최애|좋아|조아|최고|소중|대박|기특|"
    r"카와이|키와|kawaii|かわいい|可愛|갖고\s*싶|사고\s*싶|사고싶|샀|구매|겟"
)
POINT_RE = re.compile(
    r"이\s*사진|이\s*짤|이\s*그림|이\s*표정|이\s*모습|이\s*포즈|이거\s*봐|이것\s*봐|"
    r"봐봐|사진\s*속|첨부|짤\s*봐|이\s*얼굴|이\s*애|얘\s*봐|이거\s*뭐야|실물|"
    r"사진\s*봐|이미지|썸네"
)
COMPARE_RE = re.compile(
    r"보다\s*(?:더|낫|귀|예)|쪽이\s*(?:더|좋|귀)|취향|선호|호불호|"
    r"이게\s*더|이게\s*낫|중에(?:서)?\s*.{0,12}(?:좋|귀|예)|"
    r"버전|쪽이\s*내\s*취향|더\s*귀엽|더\s*이쁘|더\s*예쁘"
)
NEG_RE = re.compile(r"싫|별로|못생|안\s*귀|귀엽지\s*않|귀엽진\s*않|질색|노잼|징그|무섭")
PROMO_RE = re.compile(
    r"예약\s*판매|판매\s*안내|입고\s*(?:안내|완료)|재입고|판매\s*링크|수요조사|"
    r"증정|특전|발매|오픈\s*카톡|RT\s*이벤트|알티\s*이벤트|추첨하여|"
    r"양도|급처|교환\s*합니다|팝니다|판매합니다|구합니다|삽니다"
)
DEICTIC_CUTE = re.compile(
    r"(?:이거|이것|얘|애|사진|짤|그림|표정|모습|포즈|실물).{0,18}(?:귀엽|귀여|기여|기엽|카와이|이쁘|예쁘|사랑)|"
    r"(?:귀엽|귀여|기여|기엽|카와이|이쁘|예쁘).{0,12}(?:이거|사진|짤|표정|모습|포즈)"
)

# 짧은 지시 사진 호감. 특징 단어가 없어도 후보.
PHOTO_AFFECTION = re.compile(
    r"(?:너무|넘|진짜|완전|존나|개|겁나|ㄹㅇ|레알)?\s*(?:귀엽|귀여|기여|기엽|커여|카와이|키와|kawaii|かわいい|可愛)"
)


def norm_search(text: str) -> str:
    t = ELONG.sub(r"\1", text)
    t = HSPACE.sub("", t)
    return t


def clauses(text: str) -> list[tuple[int, str]]:
    parts = re.split(r"(?<=[\n.!?…。])", text)
    out = []
    pos = 0
    for part in parts:
        if part:
            out.append((pos, part))
            pos += len(part)
    if not out:
        out.append((0, text))
    return out


def main() -> None:
    df = pd.read_csv(POSTS, dtype=str, keep_default_na=False)
    rows = []
    for rec in df.itertuples(index=False):
        text = rec.text
        ntext = norm_search(text)
        hits = []
        for group, pat in FEATURE_GROUPS.items():
            for m in re.finditer(pat, ntext, flags=re.I):
                hits.append((group, m.group(0), m.start()))
        point = bool(POINT_RE.search(ntext) or DEICTIC_CUTE.search(ntext))
        compare = bool(COMPARE_RE.search(ntext))
        neg = bool(NEG_RE.search(ntext))
        promo = bool(PROMO_RE.search(text))
        has_eval = bool(EVAL_RE.search(ntext) or PHOTO_AFFECTION.search(ntext))
        # 후보: 특징 단어가 있거나, 사진을 가리키며 호감이 있거나, 외형 비교가 있는 글
        if not hits and not (point and has_eval) and not (compare and has_eval):
            continue
        # 특징 단어만 있고 평가·지시·비교가 전혀 없으면 설명·나열일 수 있어 낮은 우선으로 남긴다.
        priority = "특징+평가" if hits and has_eval else (
            "사진지시+호감" if point and has_eval else (
                "비교+호감" if compare and has_eval else "특징단어만"
            )
        )
        if neg and priority != "특징단어만":
            priority = priority + "+부정어"
        rows.append(
            {
                "post_id": rec.post_id,
                "post_url": rec.post_url,
                "account_id": rec.account_id,
                "like_count": rec.like_count,
                "priority": priority,
                "promo_flag": "예" if promo else "아니오",
                "feature_groups": "|".join(sorted({g for g, _, _ in hits})) if hits else "",
                "feature_spans": "|".join(f"{g}:{s}" for g, s, _ in hits[:12]),
                "text": text.replace("\r\n", "\n").replace("\r", "\n"),
            }
        )
    out = pd.DataFrame(rows)
    out_path = OUT / "candidates.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print("candidates", len(out))
    print(out["priority"].value_counts().to_string())
    print("--- groups ---")
    groups = out["feature_groups"].str.split("|").explode()
    print(groups[groups.ne("")].value_counts().to_string())
    # 사람이 읽기 쉬운 텍스트. 우선순위 높은 것부터.
    order = {
        "특징+평가+부정어": 0,
        "특징+평가": 1,
        "사진지시+호감+부정어": 2,
        "사진지시+호감": 3,
        "비교+호감+부정어": 4,
        "비교+호감": 5,
        "특징단어만": 6,
    }
    out["_o"] = out["priority"].map(lambda x: order.get(x, 9))
    out = out.sort_values(["_o", "post_id"])
    lines = []
    for i, r in enumerate(out.itertuples(index=False), 1):
        if r.priority == "특징단어만":
            continue
        lines.append(
            f"\n===== {i} | {r.post_id} | {r.account_id} | likes={r.like_count} | {r.priority} | promo={r.promo_flag}\n"
            f"groups: {r.feature_groups}\nspans: {r.feature_spans}\n{r.text}\n"
        )
    (OUT / "candidates_review.txt").write_text("".join(lines), encoding="utf-8")
    print("review posts", sum(1 for r in out.itertuples() if r.priority != "특징단어만"))
    print("review chars", sum(len(x) for x in lines))


if __name__ == "__main__":
    main()
