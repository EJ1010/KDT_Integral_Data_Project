# -*- coding: utf-8 -*-
"""캐릭터 × 매력 요소 × 반응. 원본 CSV는 읽기만 한다."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent
CMT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\03. 분석용테이블"
    r"\youtube_total_cleaning_classified_A_comments.csv"
)
VID = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
    r"\youtube_total_cleaning_classified_A.csv"
)
JUDGE = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_키워드\01_댓글판정.csv"
)
ANIBOX = "UCBTSkFNWmoOkBeZwANcbiIA"
FONT = r"C:\Windows\Fonts\malgun.ttf"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

NAVY, GREEN, AMBER = "#3d6f8a", "#2f6f4e", "#b36b3a"
PURPLE, RED, GRAY = "#5c4d7a", "#8a3d3d", "#6e737a"
PALETTE = ["#3d6f8a", "#2f6f4e", "#b36b3a", "#5c4d7a", "#8a3d3d", "#6e737a", "#1f4e79", "#7a5c3a"]

# 표기는 댓글에서 관찰된 것만. 확인하지 않은 별명은 넣지 않는다.
CHARS = [
    ("치이카와", r"치이\s*까?카와|치카와|ちいかわ|chiikawa", "작품가능"),
    ("먼작귀", r"먼작귀", "작품가능"),
    ("하치와레", r"하치\s*와레|하치와래|하찌와레|하츠와레|ハチワレ|hachiware", "캐릭터"),
    ("모몽가", r"모몽가|모몬가|モモンガ", "캐릭터"),
    ("쿠리만쥬", r"쿠리\s*만쥬|쿠리\s*만주|くりまんじゅう", "캐릭터"),
    ("우사기", r"우사기", "캐릭터"),
    ("うさぎ", r"うさぎ|ウサギ", "문맥의존"),
    ("라코", r"랏코|ラッコ|(?<![가-힣])라코(?![가-힣])|랭커상|랭커", "캐릭터"),
    ("시사", r"시샤|シーサー|(?<!우레)시사(?!회|점|디테일|프로그램|이슈)", "캐릭터"),
    ("갑옷씨", r"갑옷\s*씨|요로이", "캐릭터"),
    ("데카츠요", r"데카\s*츠요", "캐릭터"),
    ("아노코", r"아노코", "캐릭터"),
    ("파자마파티즈", r"파자마\s*파티즈", "캐릭터"),
    ("카니", r"(?<![가-힣])카니(?![가-힣])", "캐릭터"),
]
CHAR_RES = [(n, re.compile(p, re.I), k) for n, p, k in CHARS]
OPANCHU = re.compile(r"오빤쮸|오판츄|오판추|빤쮸|팬티")
PERSONAL = re.compile(
    r"치이\s*까?카와(?:가|는|도|만|보다).{0,24}"
    r"(?:작아|작은|얼굴|눈이|손을|손이|손으로|입을|입이|입모양|표정|얘|애가|목소리|성격)"
    r"|(?:작아|작은|얼굴|눈이|표정).{0,12}치이\s*까?카와"
)
CRY = re.compile(
    r"치이\s*까?카와(?:가|는|도|만|보다).{0,24}(?:울어|울었|우는|울음)"
    r"|(?:울어|울었|우는|울음).{0,12}치이\s*까?카와"
)
CONTRAST = re.compile(r"치이\s*까?카와(?:가|는|보다)")
WORK_CUE = re.compile(r"극장판|세계관|애니|만화|시리즈|작품|먼작귀")
SPAM = re.compile(
    r"파트너스|구매\s*링크|수수료를\s*받|텔레그램|카지노|대출\s*상담|"
    r"구독\s*하고\s*좋아요|무료\s*시청|오픈\s*카톡"
)
CLEAR_KO = re.compile(
    r"귀여워|귀엽|졸귀|기여|웃겨|웃기|예뻐|이쁘|대박|헐|짱|싫어|좋아|"
    r"갖고\s*싶|사고\s*싶|보고\s*싶|뭐야|왜|슬프|무섭|사랑|재밌|"
    r"미쳤|레전|실화|인정|공감|존귀"
)
KO_GRAMMAR = re.compile(
    r"[가-힣]{1,6}(?:습니다|네요|어요|아요|예요|이에요|했어요|했다|인데|거든|잖아|"
    r"까요|지요|하죠|요|다|네|지|음|임|냐|노|게|줘|걸|데|죠|함|용|여)"
)
HANGUL_RE = re.compile(r"[가-힣]")
KANA_RE = re.compile(r"[ぁ-ゟ゠-ヿ]")
KANJI_RE = re.compile(r"[一-龯]")
LATIN_RE = re.compile(r"[A-Za-z]{2,}")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
NEG_AFFECT = re.compile(
    r"안\s*귀엽|못\s*귀엽|안\s*귀여|귀여(?:운|워|움)?\s*(?:건|것|게|거)\s*(?:아닌|아님|아닐)"
    r"|귀엽지\s*않(?:다|아|어|음)(?!요)|안\s*좋|좋지\s*않|안\s*예쁘|안\s*이쁘|싫(?:다|어)"
)
APPEAL = [
    ("외형", re.compile(r"얼굴|눈이|귀가|털이|조그마|작아|동글|표정|궁디|볼이|꼬리|이빨")),
    ("목소리", re.compile(r"목소리|성우|더빙|말투|음성|발음")),
    ("성격", re.compile(r"성격|착해|착하|순해|순하|소심|용감|열심히|다정|기특")),
    ("행동", re.compile(r"먹어|먹는|먹었|울어|울었|우는|뛰어|뛰는|달리|춤추|싸워|싸우|도망|뒤뚱")),
    ("관계", re.compile(r"친구|베프|칭구|콤비|사이좋")),
]
REACT = [
    ("호감", re.compile(r"귀엽|귀여|졸귀|기여워|예쁘|이쁘|사랑|최애|입덕|반했|최고|좋아|좋네|좋음")),
    ("유머", re.compile(r"웃기|웃겨|웃김|재밌|재미있|ㅋㅋ|ㅎㅎ")),
    ("공감", re.compile(r"공감|짠하|짠해|슬프|눈물|힐링|불쌍")),
    ("보호", re.compile(r"지켜|보호|안아|꼬옥|기특|힘내|아프지")),
    ("구매의향", re.compile(r"사\s*고\s*싶|갖\s*고\s*싶|사고싶|갖고싶|구매|지갑|샀어|샀다|질렀")),
]
GOODS = re.compile(r"굿즈|인형|가챠|키링|피규어|파우치|마스코트|언박싱")
WORLD = re.compile(r"세계관|스토리|이야기|에피소드|설정|만화|극장판|인어섬")


def clean(text: str) -> str:
    t = "" if pd.isna(text) else str(text)
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    t = t.replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def language_of(text: str) -> str:
    raw = clean(text)
    if not raw:
        return "판단 불가"
    stripped = EMOJI_RE.sub("", raw)
    stripped = re.sub(r"[ㅋㅎㅠㅜ!?~.,\s]+", "", stripped)
    if not stripped:
        return "판단 불가"
    rest = raw
    for _, cre, _ in CHAR_RES:
        rest = cre.sub(" ", rest)
    rest_h = re.sub(r"[^가-힣]+", "", rest)
    hangul = len(HANGUL_RE.findall(raw))
    kana = len(KANA_RE.findall(raw))
    kanji = len(KANJI_RE.findall(raw))
    latin = LATIN_RE.findall(raw)
    foreign = kana >= 2 or kanji >= 1 or len(latin) >= 2
    koreanish = bool(CLEAR_KO.search(rest)) or (bool(KO_GRAMMAR.search(rest)) and len(rest_h) >= 2)
    if not koreanish:
        if foreign or (hangul == 0 and (kana or kanji or latin)):
            return "외국어 중심"
        return "판단 불가"
    return "혼합_한국어 중심" if foreign else "한국어 중심"


def name_only(text: str) -> bool:
    rest = clean(text)
    for _, cre, _ in CHAR_RES:
        rest = cre.sub(" ", rest)
    rest = EMOJI_RE.sub(" ", rest)
    rest = re.sub(r"[ㅋㅎㅠㅜ!?~.,\s]+", "", rest)
    hangul = re.sub(r"[^가-힣]+", "", rest)
    return len(hangul) < 2 and not CLEAR_KO.search(rest)


def chiikawa_role(text: str, others: list[str]) -> str:
    if PERSONAL.search(text):
        return "개인"
    if CRY.search(text):
        return "개인_행동"
    if others and CONTRAST.search(text):
        return "개인_대비"
    if WORK_CUE.search(text) and not others:
        return "작품_쪽"
    return "작품·캐릭터 불명확"


def hits_of(text: str) -> list[tuple[str, str]]:
    found = []
    for name, cre, kind in CHAR_RES:
        if not cre.search(text):
            continue
        if name == "우사기" and OPANCHU.search(text):
            found.append(("다른작품_우사기", "제외"))
            continue
        found.append((name, kind))
    return found


def mask_names(text: str) -> str:
    for _, cre, _ in CHAR_RES:
        text = cre.sub(" ", text)
    return text


def flag_map(text: str, patterns) -> dict[str, bool]:
    return {name: bool(cre.search(text)) for name, cre in patterns}


def self_check() -> None:
    assert "시사" not in [n for n, _ in hits_of("인어섬 시사회 갔다")]
    assert "시사" not in [n for n, _ in hits_of("우레시사")]
    assert "라코" not in [n for n, _ in hits_of("바닐라코 리뷰")]
    assert "우사기" not in [n for n, _ in hits_of("오빤쮸우사기 귀여워")]
    assert any(n == "우사기" for n, _ in hits_of("우사기가 웃겨"))
    assert any(n == "라코" for n, _ in hits_of("랏코 귀여워"))
    assert any(n == "시사" for n, _ in hits_of("시사야 귀여워"))
    assert chiikawa_role("치이카와 귀여워", []) == "작품·캐릭터 불명확"
    assert chiikawa_role("치이카와가 울었어", []) == "개인_행동"
    assert chiikawa_role("치이카와는 얼굴이 작아", []) == "개인"
    assert not (flag_map("안 귀여워", REACT)["호감"] and not NEG_AFFECT.search("안 귀여워"))
    assert NEG_AFFECT.search("안 귀여워")


def main() -> None:
    self_check()
    videos = pd.read_csv(VID, encoding="utf-8-sig", usecols=["post_id", "final_class"])
    comments = pd.read_csv(
        CMT,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "comment_id", "comment_description"],
    )
    judge = pd.read_csv(
        JUDGE,
        encoding="utf-8-sig",
        usecols=["comment_id", "language_class", "reaction_target", "include_explore", "include_major"],
    )
    audit = {
        "A영상": len(videos),
        "A고유": int(videos["post_id"].nunique()),
        "A만": int((videos["final_class"] == "A_우선포함").all()),
        "댓글": len(comments),
        "댓글고유": int(comments["comment_id"].nunique()),
        "판정": len(judge),
        "판정고유": int(judge["comment_id"].nunique()),
        "댓글이_A밖": int((~comments["post_id"].isin(set(videos["post_id"]))).sum()),
    }
    df = comments.merge(judge, on="comment_id", how="left", validate="one_to_one")
    df["text"] = df["comment_description"].map(clean)
    df["lang_re"] = df["text"].map(language_of)
    df["spam_re"] = df["text"].map(lambda s: bool(SPAM.search(s))) | df["reaction_target"].eq("광고·스팸")
    df["name_only"] = df["text"].map(name_only)
    df["text_mask"] = df["text"].map(mask_names)
    norm = df["text"].str.replace(r"\s+", "", regex=True)
    dup_rows = int(norm.duplicated(keep=False).sum())
    dup_videos = int(df.duplicated(["post_id", "text"], keep=False).sum())
    parsed = df["text"].map(hits_of)
    df["names"] = parsed.map(lambda xs: [n for n, k in xs if k != "제외"])
    df["excluded_other"] = parsed.map(lambda xs: any(n == "다른작품_우사기" for n, _ in xs))
    df["n_names"] = df["names"].map(len)
    roles = []
    for text, names in zip(df["text"], df["names"]):
        if "치이카와" not in names:
            roles.append("")
        else:
            roles.append(chiikawa_role(text, [n for n in names if n not in ("치이카와", "먼작귀")]))
    df["chiikawa_role"] = roles
    ko = df["lang_re"].isin(["한국어 중심", "혼합_한국어 중심"])
    df["analysis"] = ko & ~df["spam_re"]
    df["mention_base"] = df["analysis"]
    df["react_base"] = df["analysis"] & ~df["name_only"] & df["n_names"].gt(0)

    lang_agree = float((df["lang_re"] == df["language_class"]).mean())
    pd.crosstab(df["language_class"], df["lang_re"], dropna=False).to_csv(
        ROOT / "00_언어대조.csv", encoding="utf-8-sig"
    )
    old_major_has_name = int((df["include_major"] & df["n_names"].gt(0)).sum())
    new_ko_has_name = int((df["mention_base"] & df["n_names"].gt(0)).sum())
    outside_major = int((~df["include_major"] & df["mention_base"] & df["n_names"].gt(0)).sum())
    outside_explore = int((~df["include_explore"].astype(bool) & df["n_names"].gt(0)).sum())

    rows = []
    for name, _, kind in CHARS:
        mask = df["names"].map(lambda xs, name=name: name in xs)
        sub = df[mask]
        ko_sub = sub[sub["mention_base"]]
        react = sub[sub["react_base"]]
        if name == "치이카와":
            personal = ko_sub["chiikawa_role"].isin(["개인", "개인_대비", "개인_행동"])
            unclear = ko_sub["chiikawa_role"].isin(["작품_쪽", "작품·캐릭터 불명확"])
            cry_only = int(ko_sub["chiikawa_role"].eq("개인_행동").sum())
        else:
            personal = pd.Series(True, index=ko_sub.index) if kind == "캐릭터" else pd.Series(False, index=ko_sub.index)
            unclear = ~personal if kind != "캐릭터" else pd.Series(False, index=ko_sub.index)
            cry_only = 0
        rows.append(
            {
                "캐릭터": name,
                "종류": kind,
                "전체댓글": int(mask.sum()),
                "기존주요해석": int((mask & df["include_major"]).sum()),
                "주요해석밖": int((mask & ~df["include_major"]).sum()),
                "한국어혼합": int(len(ko_sub)),
                "한국어_기존주요해석": int((ko_sub["include_major"]).sum()),
                "한국어_주요해석밖": int((~ko_sub["include_major"]).sum()),
                "이름만": int(ko_sub["name_only"].sum()),
                "반응분석댓글": int(len(react)),
                "영상": int(ko_sub["post_id"].nunique()),
                "채널": int(ko_sub["account_id"].dropna().nunique()),
                "AniBox댓글": int((ko_sub["account_id"] == ANIBOX).sum()),
                "개인_또는_캐릭터": int(personal.sum()),
                "우는만_개인": cry_only,
                "작품캐릭터불명확": int(unclear.sum()) if name in ("치이카와", "먼작귀", "うさぎ") else 0,
                "판단불가_언급": int((mask & df["lang_re"].eq("판단 불가")).sum()),
                "판단불가_이름만": int((mask & df["lang_re"].eq("판단 불가") & df["name_only"]).sum()),
                "외국어_언급": int((mask & df["lang_re"].eq("외국어 중심")).sum()),
            }
        )
    mention = pd.DataFrame(rows).sort_values("한국어혼합", ascending=False)
    ko_denom = int(df["mention_base"].sum())
    mention["한국어혼합_비율"] = mention["한국어혼합"] / ko_denom

    # 반응 분석: 특정 캐릭터. 치이카와는 개인 단서가 있는 댓글만.
    appeal_rows = []
    targets = []
    for name, _, kind in CHARS:
        if kind == "문맥의존" and name == "うさぎ":
            continue
        mask = df["names"].map(lambda xs, name=name: name in xs) & df["react_base"]
        if name == "치이카와":
            mask = mask & df["chiikawa_role"].isin(["개인", "개인_대비"])
        if name == "먼작귀":
            continue
        sub = df[mask]
        if len(sub) < 30:
            continue
        targets.append(name)
        pos = sub["text_mask"].map(lambda s: bool(REACT[0][1].search(s)) and not bool(NEG_AFFECT.search(s)))
        appeal_rows.append(
            {
                "캐릭터": name,
                "반응분석댓글": len(sub),
                "영상": int(sub["post_id"].nunique()),
                "채널": int(sub["account_id"].dropna().nunique()),
                "호감댓글": int(pos.sum()),
                "호감비율": float(pos.mean()),
            }
        )
    base_pos = pd.DataFrame(appeal_rows)

    long_rows = []
    for name in targets:
        mask = df["names"].map(lambda xs, name=name: name in xs) & df["react_base"]
        if name == "치이카와":
            mask = mask & df["chiikawa_role"].isin(["개인", "개인_대비"])
        sub = df[mask]
        n = len(sub)
        for label, cre in APPEAL + REACT + [("굿즈언급", GOODS), ("세계관이야기", WORLD)]:
            if label == "호감":
                hit = sub["text_mask"].map(lambda s, cre=cre: bool(cre.search(s)) and not bool(NEG_AFFECT.search(s)))
            else:
                hit = sub["text_mask"].map(lambda s, cre=cre: bool(cre.search(s)))
            long_rows.append(
                {
                    "캐릭터": name,
                    "항목": label,
                    "댓글": int(hit.sum()),
                    "분모": n,
                    "비율": float(hit.mean()) if n else 0,
                    "영상": int(sub.loc[hit, "post_id"].nunique()) if hit.any() else 0,
                    "채널": int(sub.loc[hit, "account_id"].dropna().nunique()) if hit.any() else 0,
                }
            )
    detail = pd.DataFrame(long_rows)

    # 공통·특화. 분모 80 이상.
    focus = [n for n in targets if int(base_pos.loc[base_pos["캐릭터"] == n, "반응분석댓글"].iloc[0]) >= 80]
    spec_rows = []
    for label in [a for a, _ in APPEAL] + [a for a, _ in REACT]:
        part = detail[(detail["항목"] == label) & (detail["캐릭터"].isin(focus))]
        if part.empty:
            continue
        med = float(part["비율"].median())
        for rec in part.itertuples(index=False):
            spec_rows.append(
                {
                    "항목": label,
                    "캐릭터": rec.캐릭터,
                    "비율": rec.비율,
                    "댓글": rec.댓글,
                    "분모": rec.분모,
                    "중앙값대비": rec.비율 - med,
                    "공통후보": rec.비율 >= 0.15 and rec.비율 >= med,
                    "특화후보": rec.비율 - med >= 0.08 and rec.분모 >= 80,
                }
            )
    spec = pd.DataFrame(spec_rows)

    world = df[df["mention_base"]]
    named = df[df["react_base"]]
    world_rows = []
    for label, cre in [("세계관이야기", WORLD), ("굿즈언급", GOODS), ("관계", APPEAL[4][1])]:
        hit = world["text_mask"].map(lambda s, cre=cre: bool(cre.search(s)))
        world_rows.append(
            {
                "항목": label,
                "댓글": int(hit.sum()),
                "분모": len(world),
                "비율": float(hit.mean()) if len(world) else 0,
                "영상": int(world.loc[hit, "post_id"].nunique()),
                "채널": int(world.loc[hit, "account_id"].dropna().nunique()),
            }
        )
    hit = named["n_names"] >= 2
    world_rows.append(
        {
            "항목": "여러캐릭터",
            "댓글": int(hit.sum()),
            "분모": len(named),
            "비율": float(hit.mean()) if len(named) else 0,
            "영상": int(named.loc[hit, "post_id"].nunique()),
            "채널": int(named.loc[hit, "account_id"].dropna().nunique()),
        }
    )
    world_tbl = pd.DataFrame(world_rows)

    # 표본
    samples = []
    def take(mask, tag, n=6):
        part = df[mask]
        for rec in part.head(n).itertuples(index=False):
            samples.append(
                {
                    "구분": tag,
                    "comment_id": rec.comment_id,
                    "언어": rec.lang_re,
                    "이름만": rec.name_only,
                    "치이카와역할": rec.chiikawa_role,
                    "문장": rec.text[:180],
                }
            )

    take(df["text"].str.contains(r"(?<!우레)시사(?!회)", regex=True) & df["mention_base"], "시사")
    take(df["excluded_other"], "오빤쮸우사기_제외")
    take(df["text"].str.contains("토끼") & df["mention_base"], "토끼_비통합")
    take(df["text"].str.contains("하늘다람쥐") & df["mention_base"], "하늘다람쥐_비통합")
    take(df["names"].map(lambda xs: "라코" in xs) & df["mention_base"], "라코")
    take(df["names"].map(lambda xs: "카니" in xs) & df["mention_base"], "카니")
    take(df["chiikawa_role"].eq("개인"), "치이카와_개인")
    take(df["chiikawa_role"].eq("작품·캐릭터 불명확") & df["mention_base"], "치이카와_불명확")
    sample_df = pd.DataFrame(samples)

    dict_rows = [
        ["치이카와", "치이카와·치이까와·치카와·ちいかわ·chiikawa", "표기만 통합", "작품명과 주인공이 겹침. 개인 단서가 없으면 작품·캐릭터 불명확", "시사·뉴스와 무관"],
        ["먼작귀", "먼작귀", "치이카와와 합치지 않음", "한국어 작품 제목", ""],
        ["하치와레", "하치와레·하치와래·하찌와레·하츠와레·ハチワレ", "오타 통합", "같은 대상을 가리키는 철자가 댓글에 있음", ""],
        ["모몽가", "모몽가·모몬가·モモンガ", "철자 통합", "하늘다람쥐는 댓글이 한국 이름이라고 설명하지만 괴물 장면도 있어 합치지 않음", "하늘다람쥐"],
        ["쿠리만쥬", "쿠리만쥬·쿠리만주·くりまんじゅう", "철자 통합", "같은 이름", ""],
        ["우사기", "우사기", "うさぎ·토끼·오빤쮸와 합치지 않음", "오빤쮸·오판츄·빤쮸가 같은 댓글에 있으면 다른 작품으로 제외", "토끼, 오빤쮸우사기"],
        ["うさぎ", "うさぎ·ウサギ", "우사기와 합치지 않음", "건수가 적어 우사기 순위에 넣지 않음", "토끼"],
        ["라코", "랏코·ラッコ·라코·랭커·랭커상", "별칭 통합", "댓글이 랏코를 랭커상으로 부름. 바닐라코는 단어 경계로 제외", "우사기"],
        ["시사", "시사·시샤·シーサー", "철자 통합", "시사회·우레시사·시사점·시사프로그램은 제외. 남은 문장도 시사(current affairs)가 섞일 수 있음", "시사회, 뉴스"],
        ["갑옷씨", "갑옷씨·요로이", "표기 통합", "기존 사전과 댓글에 있음", ""],
        ["데카츠요", "데카츠요", "단독", "기존 사전과 댓글에 있음", ""],
        ["아노코", "아노코", "단독", "기존 사전과 댓글에 있음", ""],
        ["파자마파티즈", "파자마파티즈", "단독", "기존 사전과 댓글에 있음", ""],
        ["카니", "카니", "단독", "헌책방·게로 설명된 댓글이 있음. 짧은 이름이라 다른 말과 겹칠 수 있음", "짧은 음절"],
        ["하늘다람쥐", "하늘다람쥐", "모몽가에 합치지 않음", "등치 설명과 괴물 장면이 같이 있음", "모몽가"],
        ["토끼", "토끼", "우사기에 합치지 않음", "우드스탁·오빤쮸 등 다른 토끼가 있음", "우사기"],
        ["포셰트", "포셰트", "캐릭터 아님", "가방·파우치 상품", ""],
        ["인어", "인어·인어섬", "캐릭터 아님", "극장판·변신 이야기", ""],
        ["먹보", "먹보", "캐릭터 아님", "우사기의 먹는 행동 수식", "우사기"],
    ]
    dictionary = pd.DataFrame(dict_rows, columns=["대표이름", "표기", "통합", "근거", "오분류위험"])

    input_tbl = pd.DataFrame(
        [
            ["A영상", audit["A영상"], "기대 6462"],
            ["댓글", audit["댓글"], "기대 90921"],
            ["댓글ID중복", audit["댓글"] - audit["댓글고유"], "0이면 수집 ID 중복 없음"],
            ["댓글이_A밖", audit["댓글이_A밖"], ""],
            ["언어재계산_일치율", round(lang_agree, 4), "기존 판정과 비교. 정답으로 쓰지 않음"],
            ["광고스팸_재계산", int(df["spam_re"].sum()), "기존 광고 표시 또는 같은 문구"],
            ["같은문장_행", dup_rows, "삭제하지 않음. 서로 다른 댓글이 같은 문장일 수 있음"],
            ["같은영상_같은문장_행", dup_videos, ""],
            ["한국어혼합", ko_denom, "본 분석 대상. 이름만 포함"],
            ["이름만_판단불가", int((df["name_only"] & df["n_names"].gt(0) & df["lang_re"].eq("판단 불가")).sum()), "언어를 이름만으로 확정하지 않음. 언급량 보조"],
            ["반응분석_캐릭터있는댓글", int(df["react_base"].sum()), "이름만 제외"],
            ["기존주요해석_이름있음", old_major_has_name, ""],
            ["이번_이름있음", new_ko_has_name, "주요해석 밖 포함"],
            ["주요해석밖에_이름있음", outside_major, "기존 23,624 밖"],
            ["탐색밖에_이름있음", outside_explore, "판단불가·외국어 포함"],
        ],
        columns=["항목", "값", "메모"],
    )

    mention.to_csv(ROOT / "02_언급량.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(ROOT / "03_매력반응.csv", index=False, encoding="utf-8-sig")
    spec.to_csv(ROOT / "04_공통특화.csv", index=False, encoding="utf-8-sig")
    world_tbl.to_csv(ROOT / "05_세계관굿즈.csv", index=False, encoding="utf-8-sig")
    sample_df.to_csv(ROOT / "06_문맥표본.csv", index=False, encoding="utf-8-sig")
    dictionary.to_csv(ROOT / "00_사전_캐릭터.csv", index=False, encoding="utf-8-sig")
    input_tbl.to_csv(ROOT / "00_입력검증.csv", index=False, encoding="utf-8-sig")
    base_pos.to_csv(ROOT / "02_호감.csv", index=False, encoding="utf-8-sig")

    plot_mention(mention)
    plot_positive(base_pos)
    plot_group(detail, [a for a, _ in APPEAL], "fig_매력.png", "캐릭터를 부른 댓글 중 매력 요소가 같이 있는 비율")
    plot_group(detail, [a for a, _ in REACT], "fig_반응.png", "캐릭터를 부른 댓글 중 반응 표현이 같이 있는 비율")
    write_report(input_tbl, mention, detail, spec, world_tbl, base_pos, ko_denom)
    print("done", ROOT)
    print(input_tbl.to_string(index=False))
    print(mention[["캐릭터", "전체댓글", "한국어혼합", "기존주요해석", "주요해석밖", "작품캐릭터불명확", "호감" if False else "반응분석댓글"]].head(15).to_string(index=False))


def plot_mention(mention: pd.DataFrame) -> None:
    use = mention[mention["종류"] == "캐릭터"].head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.barh(use["캐릭터"], use["한국어혼합"], color=NAVY)
    ax.set_xlabel("댓글 수")
    ax.set_xlim(0, use["한국어혼합"].max() * 1.15)
    ax.set_title("한국어·혼합 댓글의 캐릭터 언급")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_언급량.png", dpi=140)
    plt.close()


def plot_positive(base_pos: pd.DataFrame) -> None:
    use = base_pos.sort_values("호감비율").copy()
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.barh(use["캐릭터"], use["호감비율"] * 100, color=GREEN)
    ax.set_xlabel("호감 표현 비율 (%)")
    ax.set_xlim(0, 100)
    ax.set_title("그 캐릭터를 부른 댓글 안의 호감 표현")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_호감비율.png", dpi=140)
    plt.close()


def plot_group(detail: pd.DataFrame, labels: list[str], fname: str, title: str) -> None:
    part = detail[detail["항목"].isin(labels)]
    # 댓글 많은 상위 6
    order = (
        part.groupby("캐릭터")["분모"].max().sort_values(ascending=False).head(6).index.tolist()
    )
    fig, ax = plt.subplots(figsize=(9, 5.4))
    import numpy as np

    x = np.arange(len(labels))
    width = 0.12
    for i, name in enumerate(order):
        vals = []
        for lab in labels:
            row = part[(part["캐릭터"] == name) & (part["항목"] == lab)]
            vals.append(float(row["비율"].iloc[0]) * 100 if len(row) else 0)
        ax.bar(x + (i - len(order) / 2) * width + width / 2, vals, width, label=name, color=PALETTE[i % len(PALETTE)])
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("해당 캐릭터 댓글 중 비율 (%)")
    ax.set_title(title)
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / fname, dpi=140)
    plt.close()


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def write_report(inp, mention, detail, spec, world, base_pos, ko_denom) -> None:
    lines = []
    a = lines.append
    a("# 캐릭터 × 매력 × 반응")
    a("")
    a("대상은 연결 댓글 전체에서 다시 고른 한국어 중심·한국어 중심 혼합이다. 기존 주요 해석 23,624건만 쓰지 않았다. 이름만 있는 댓글은 언어를 판단 불가로 두고 보조 열에만 센다. 한국어 언급량과 매력 비율에는 넣지 않는다. 채널 수는 댓글 작성자가 아니라 영상이 올라온 채널이다. 작성자 ID는 없다.")
    a("")
    a("## 1. 어떤 캐릭터가 많이 언급되는가")
    a("")
    a("**기준.** 분모는 광고를 뺀 한국어·혼합 댓글이다. 치이카와·먼작귀는 작품명과 겹치므로 아래 개인 순위와 분리한다. 우사기와 うさぎ, 우사기와 토끼, 라코와 우사기는 합치지 않았다.")
    a("")
    show = mention[mention["캐릭터"].isin(["우사기", "하치와레", "모몽가", "라코", "쿠리만쥬", "시사", "아노코", "갑옷씨", "데카츠요", "카니", "파자마파티즈", "うさぎ"])]
    a("| 캐릭터 | 한국어·혼합 댓글 | 기존 주요해석 | 주요해석 밖 | 영상 | 채널 |")
    a("| --- | --- | --- | --- | --- | --- |")
    for rec in show.itertuples(index=False):
        a(f"| {rec.캐릭터} | {rec.한국어혼합:,} | {rec.한국어_기존주요해석:,} | {rec.한국어_주요해석밖:,} | {rec.영상:,} | {rec.채널:,} |")
    a("")
    chi = mention[mention["캐릭터"] == "치이카와"].iloc[0]
    a(f"치이카와 표기는 한국어·혼합 {int(chi.한국어혼합):,}건이다. 개인 단서가 있는 댓글은 {int(chi.개인_또는_캐릭터):,}건이고, 작품명인지 주인공인지 나누기 어려운 댓글은 {int(chi.작품캐릭터불명확):,}건이다. 매력 비교에는 얼굴·목소리·성격·지칭이나 다른 캐릭터와의 대비가 있는 댓글만 넣었다. 우는·울어만으로 개인이 된 {int(chi.우는만_개인):,}건은 개인으로 세되, 그 단어가 행동 사전과 같아서 행동 비율 분모에서는 뺐다. 먼작귀는 작품 제목이라 캐릭터 순위에 넣지 않았다.")
    a("이름만 있고 다른 한국어 문장이 없는 댓글은 언어를 판단 불가로 두었다. 캐릭터별 건수는 `02_언급량.csv`의 판단불가_이름만이다. 그 건수를 한국어 시청자 수로 더하지 않는다.")
    a("")
    a("**해석.** 언급이 많다는 것은 그 이름이 댓글에 자주 올랐다는 뜻이다. 영상 소재로 자주 나와서 이름이 따라온 경우와, 그 캐릭터를 좋게 말한 경우는 다음 절에서 나눈다.")
    a("")
    a("## 2. 무엇을 좋아하고 어떻게 표현하는가")
    a("")
    a("**기준.** 분모는 그 캐릭터 이름이 있고, 이름 외에 한국어 문장이 있는 댓글이다. 비율은 같은 댓글에 그 표현이 같이 있는 비율이다. 문장 안에서 누구를 가리키는지까지 나누지는 못했다. 호감은 `안 귀엽다` 같은 부정을 빼었다. `귀엽다`만 있는 댓글은 외형으로 세지 않는다.")
    a("")
    a("| 캐릭터 | 분모 | 호감 | 호감 비율 |")
    a("| --- | --- | --- | --- |")
    for rec in base_pos.sort_values("반응분석댓글", ascending=False).itertuples(index=False):
        a(f"| {rec.캐릭터} | {rec.반응분석댓글:,} | {rec.호감댓글:,} | {pct(rec.호감비율)} |")
    a("")
    a("매력 요소와 반응의 댓글 수·비율·영상·채널은 `03_매력반응.csv`에 있다.")
    a("")
    # 특화 요약
    a("**공통.** 호감 표현은 이름이 충분히 있는 캐릭터 모두에서 가장 넓은 반응이다. 외형 단어만으로 좁히면 비율이 낮아진다. 자주 쓰는 `귀엽다`가 얼굴·목소리·성격을 지정하지 않기 때문이다.")
    if len(spec):
        hot = spec[spec["특화후보"]].sort_values("중앙값대비", ascending=False)
        a("")
        a("**한 캐릭터에서 비율이 더 높은 항목.** 중앙값보다 8%포인트 이상 높고, 분모가 80댓글 이상인 경우만 적는다.")
        a("")
        a("| 항목 | 캐릭터 | 비율 | 분모 |")
        a("| --- | --- | --- | --- |")
        for rec in hot.head(12).itertuples(index=False):
            a(f"| {rec.항목} | {rec.캐릭터} | {pct(rec.비율)} | {rec.분모:,} |")
    a("")
    a("**언급과 호감을 나누면.** 우사기·하치와레·모몽가의 호감 비율은 서로 가깝다. 우사기 언급이 많다고 호감 비율까지 높지는 않다. 시사·라코·쿠리만쥬는 언급은 더 적고 호감 비율은 더 높다. 시사는 일반 단어가 남을 수 있어, 이 비율만으로 선호를 확정하지 않는다.")
    a("외형·목소리·성격·보호·구매 의향은 분모 80 이상에서 중앙값보다 8%포인트 넘게 높은 캐릭터가 없다. 댓글에 적힌 반응의 공통 축은 `귀엽다`·`좋아` 같은 넓은 호감과, `웃기다`·웃음 같은 유머다. 얼굴·목소리·성격을 가리키는 단어는 그 안에 잘 들어 있지 않다. 치이카와의 외형·목소리·성격 비율은 그 단어가 있는 댓글만 분모로 잡았으므로 다른 캐릭터보다 높게 나오기 쉽다. 그렇게 잡아도 8%포인트를 넘기지 않았다.")
    a("구매를 말하는 댓글은 캐릭터마다 한 자릿수 비율에 머문다. 캐릭터를 사고 싶다는 문장보다, 굿즈·인형·가챠를 말하는 댓글이 한국어·혼합 전체에서 더 넓다. 굿즈 언급을 그 캐릭터의 구매 의향으로 바꾸어 읽지 않는다.")
    a("")
    a("## 3. 캐릭터 밖의 매력")
    a("")
    a("| 항목 | 댓글 | 분모 | 비율 | 영상 | 채널 |")
    a("| --- | --- | --- | --- | --- | --- |")
    for rec in world.itertuples(index=False):
        a(f"| {rec.항목} | {rec.댓글:,} | {rec.분모:,} | {pct(rec.비율)} | {rec.영상:,} | {rec.채널:,} |")
    a("")
    a("세계관·굿즈·관계의 분모는 광고를 뺀 한국어·혼합 전체다. 여러 캐릭터의 분모는 이름이 하나 이상 있고 이름 밖에 문장이 있는 댓글이다. 인어섬과 극장판은 세계관이야기에 넣었고, 인어를 캐릭터로 세지 않았다.")
    a("")
    a("## 4. 해석의 한계")
    a("")
    a(f"한국어·혼합 분모는 {ko_denom:,}건이다. 기존 주요 해석에 없는 이름 언급도 이번 언급량에 포함했다. 언어를 기존 판정과 다시 매기면 일치율은 `00_입력검증.csv`에 있다. 차이는 시사·랏코·오타를 이름 표기로 뺀 뒤 남은 문장을 다시 보았기 때문이다. 기존 판정을 정답으로 쓰지 않았다.")
    a("같은 댓글 안의 공동 출현이므로, 그 캐릭터의 그 특징이 호감의 이유라고 확정하지 않는다. 마케팅에 쓸 때는 메시지 후보로 두고, 어떤 문장이 실제로 반응이 커지는지는 따로 확인해야 한다.")
    a("시사는 시사회와 가사 우레시사를 뺐다. 그래도 시사라는 일반 단어가 남을 수 있다. 카니와 랭커는 짧은 이름이라 오분류 위험이 사전에 적혀 있다.")
    (ROOT / "08_보고서.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
