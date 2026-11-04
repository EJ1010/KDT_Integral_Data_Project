# -*- coding: utf-8 -*-
"""상품 구매·획득·소장·의향 1차 분류.

67,891건 전체를 규칙으로만 나눈다. 구매가 확정된 목록이 아니고,
문맥 판정이나 새 표본을 만들지 않는다. 원본 CSV와 기존 분석 결과는 읽기만 한다.
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
OLD_CAND = Path(__file__).resolve().parents[1] / "A_소비형태" / "01_후보_댓글.csv"
VER = "goods-screen-v1"
METHOD = "규칙"

BUY = "구매·획득 경험 후보"
OWN = "소장·수집 경험 후보"
INTENT = "구매·소장 의향 후보"
ASK = "구매 정보 질문 후보"
FAIL = "미구매·구매 포기 후보"
MENTION = "상품 단순 언급·평가"
AMBIG = "모호한 소비 후보"
NONE = "해당 없음"
BEHAVIOR = [BUY, OWN, INTENT, ASK, FAIL, AMBIG]
ORDER = BEHAVIOR + [MENTION]

# 근거는 댓글 원문 조각만 쓴다. 제목은 분류에 넣지 않는다.
RULES: list[tuple[str, str, str]] = [
    ("R-fail-neg", FAIL, r"안\s*샀|못\s*샀|사지\s*않|안\s*사(?:요|ㄹ|러)|못\s*사(?:요|ㄹ|러)|구매\s*안\s*했|구매하지\s*않|구입\s*안\s*했|안\s*사고\s*싶|사고\s*싶지\s*않|갖고\s*싶지\s*않|가지고\s*싶지\s*않|그닥\s*안\s*사고\s*싶|살\s*수는\s*없|살\s*수\s*는\s*없"),
    ("R-fail-stop", FAIL, r"품절|재고\s*없|구매\s*취소|주문\s*취소|취소(?:했|함|했어요)|포기(?:했|함|했어요)|안\s*팔(?:아|림|아요|네)?"),
    ("R-ask-where", ASK, r"어디서\s*(?:사|샀|구매|구입)|어디\s*서\s*사|어디에서\s*(?:사|샀)|구매처|구입처|판매처|어떻게\s*(?:사|구매)|얼마(?:에\s*사|에\s*팔|예요|에요|야\??|죠\??|인가요)|가격(?:이|은|요|좀|알려|문의)|재고\s*(?:있|남|있나|있나요)|사(?:세|셨)(?:어요|나요|나|죠)\s*\??|구매하셨|구입하셨|구매\s*정보|구매가능(?:할까|할까요|한가요)"),
    ("R-intent", INTENT, r"사고\s*싶|사\s*고\s*싶|갖고\s*싶|가지\s*고\s*싶|가지고\s*싶|사고\s*십|갖고\s*십|사야(?:지|겠|죠|함|해|할)|(?:이거|그거|저거|하나|또|더|꼭|당장|바로)\s*살(?:게|까)|살(?:래|려고|거예요|거야|건데|까\??)|사\s*러\s*가|사려고|지르러|지름신|사자고|구매하(?:고|구)\s*싶|구매\s*(?:할게|하겠|할\s*거|갈|할\s*의향)|구매할\s*의향|소장욕구"),
    ("R-own", OWN, r"(?<!고)소장(?:중|하|한|함|하고|했|할|하려)(?!가치|각)|모으(?:고\s*있|는\s*중|는데|았|기\s*시작|셨)|수집(?:중|하|한|함)|컬렉(?:션|중|터)|콜렉(?:션|중)|보관\s*중|진열(?:해|함|중)|전시\s*중|가지고\s*있(?:어|음|다|네|죠|습)|갖고\s*있(?:어|음|다|네|죠|습)|갖고있(?:어|음|다)"),
    ("R-buy", BUY, r"샀(?:어|다|네|음|죠|지|삼|슴|습|는|고|지만|어서|던|었|읍|쏘|구|나|오|걸|더|엉|서)|샀을(?!거)|사\s*왔|사왔|사와(?:요|욤)|사서|구매(?:했|함|해\s*봤|했어요|했습니다|하였|하신)|구입(?:했|함|해\s*봤|했어요|했습니다|하신)|직구(?:했|함|해\s*봤|했어요)|주문(?:했|함|했어요|했습니다)|결제(?:했|함|했어요)|득템(?:했|함|했어)|질렀(?:어|다|네|음|죠)?|선물\s*(?:로\s*)?받(?:았|아|음)|가챠(?:를?\s*)?(?:했|함|했어|했어요|돌렸|돌림|뽑았)|쿠지(?:를?\s*)?(?:했|함|했어|했어요|뽑았|뜯었)|인형\s*뽑(?:기\s*)?(?:했|함|했어|했어요|성공)"),
    ("R-pull", AMBIG, r"(?<!풀)(?<!풀\s)뽑(?:았|아\s*왔|아왔|음|았다)"),
    ("R-ambig-get", AMBIG, r"데려\s*왔|입양(?:했|함|해|했어)|들였(?:어|다|음)|배송\s*(?:왔|옴|도착)|언박싱|개봉기|택배\s*깡|예약(?:했|함|했어요)"),
    ("R-mention", MENTION, r"인형(?!\s*뽑)|봉제|누이구루미|ぬいぐるみ|키링|키홀더|아크릴\s*참|피규어|피규아|피큐어|넨도(?:로이드)?|소프비|스티커|포토\s*카드|포카|트레카|마스킹\s*테이프|띠부|파우치|에코백|티셔츠|후드(?:티|집)|잠옷|슬리퍼|담요|쿠션|머그|베개|파자마(?!\s*파티)|팝콘(?!게임)|식완|가챠|가샤폰|가샤|랜덤\s*깡|랜덤깡|블라인드\s*박스|쿠지|제일\s*복권|이치방\s*쿠지|一番くじ|굿즈|단행본|만화책|콜렉트\s*북|북마크"),
]
RULE_RES = [(rid, kind, re.compile(pat, re.I)) for rid, kind, pat in RULES]
PRODUCTS = [
    ("인형·봉제", re.compile(r"인형(?!\s*뽑)|봉제|누이구루미|ぬいぐるみ", re.I)),
    ("키링·참", re.compile(r"키링|키홀더|아크릴\s*참", re.I)),
    ("피규어", re.compile(r"피규어|피규아|피큐어|넨도(?:로이드)?|소프비", re.I)),
    ("카드·스티커·문구", re.compile(r"스티커|포토\s*카드|포카|트레카|마스킹\s*테이프|띠부|단행본|만화책|콜렉트\s*북|북마크", re.I)),
    ("의류·생활", re.compile(r"파우치|에코백|티셔츠|후드(?:티|집)|잠옷|슬리퍼|담요|쿠션|머그|베개|파자마(?!\s*파티)", re.I)),
    ("식품·음료", re.compile(r"팝콘(?!게임)|식완", re.I)),
    ("가챠·랜덤", re.compile(r"가챠|가샤폰|가샤|랜덤\s*깡|랜덤깡|블라인드\s*박스", re.I)),
    ("쿠지", re.compile(r"쿠지|제일\s*복권|이치방\s*쿠지|一番くじ", re.I)),
    ("굿즈", re.compile(r"굿즈", re.I)),
]
CHII = re.compile(r"치이\s*까?카와|치카와|ちいかわ|chiikawa|먼작귀|하치\s*와레|모몽가|모몬가|쿠리\s*만쥬|우사기|랏코|파자마\s*파티즈", re.I)
OTHER = re.compile(r"산리오|헬로\s*키티|쿠로미|폼폼|포켓몬|피카츄|지브리|토토로|드래곤\s*볼|귀멸|귀칼|히로아카|나의\s*히어로|스누피|커비|리락쿠마|몰랑|농담곰|한교동|짱구|디즈니|BT21|원신|스파이\s*패밀리|체인소|레제|실바니안|바니안|냥코", re.I)
OPANCHU = re.compile(r"오빤쮸|오판츄|오판추|빤쮸")
CHAR_BEFORE = re.compile(r"(?:치이\s*까?카와|하치\s*와레|하치|우사기|모몽가|랏코|파자마\s*파티즈|캐릭터|얘|애가)\s*(?:가|는|도|이)?\s*$")
GAME_NEAR = re.compile(r"게임|슬롯|원신|가챠\s*게임")
GIVEAWAY = re.compile(r"뽑아\s*주|뽑히|당첨")
IDIOM = re.compile(r"쏴리\s*질러|질러\s*버려|그냥\s*질러")
SELF_W = re.compile(r"저도|저는|내가|나는|제가|나도|전 ")
OTHER_W = re.compile(r"사셨|사신|구매하셨|구매하신|구입하셨|구입하신|친구(?:가|는)|언니(?:가|는)|오빠(?:가|는)|동생(?:이|은)|엄마(?:가|는)|아내(?:가|는)")
QUOTE = re.compile(r"(?:라고|라며|라는|했대|하더라)\s*$")
VIEW_ONLY = re.compile(r"정주행|극장판|관람|팝업|다녀\s*왔|다녀왔|방문")


def population() -> tuple[pd.DataFrame, dict]:
    comments = pd.read_csv(
        base.CMT,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "comment_id", "comment_description", "title_without_hashtags"],
    )
    judge = pd.read_csv(
        base.JUDGE,
        encoding="utf-8-sig",
        usecols=["comment_id", "language_class", "reaction_target"],
    )
    videos = pd.read_csv(
        base.VID,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "title_without_hashtags"],
    )
    info = {
        "원본댓글행": int(len(comments)),
        "원본_comment_id_결측": int(comments["comment_id"].isna().sum()),
        "원본_comment_id_중복": int(comments["comment_id"].duplicated().sum()),
        "판정행": int(len(judge)),
        "판정_comment_id_중복": int(judge["comment_id"].duplicated().sum()),
        "판정에_없는_댓글": int((~comments["comment_id"].isin(set(judge["comment_id"]))).sum()),
    }
    if info["원본_comment_id_중복"] or info["판정_comment_id_중복"]:
        raise SystemExit(f"ID 중복 {info}")
    df = comments.merge(judge, on="comment_id", how="left", validate="one_to_one")
    df = df.merge(
        videos.rename(columns={"account_id": "video_account_id", "title_without_hashtags": "video_title"}),
        on="post_id",
        how="left",
        validate="many_to_one",
    )
    if len(df) != len(comments):
        raise SystemExit(f"조인으로 행이 늘었다 {len(comments)} -> {len(df)}")
    df["text_clean"] = df["comment_description"].map(base.clean)
    df["lang_re"] = df["text_clean"].map(base.language_of)
    df["spam_re"] = df["text_clean"].map(lambda s: bool(base.SPAM.search(s))) | df["reaction_target"].eq("광고·스팸")
    info["언어재계산_한국어중심"] = int((df["lang_re"] == "한국어 중심").sum())
    info["언어재계산_혼합"] = int((df["lang_re"] == "혼합_한국어 중심").sum())
    info["광고스팸"] = int(df["spam_re"].sum())
    pop = df[df["lang_re"].isin(["한국어 중심", "혼합_한국어 중심"]) & ~df["spam_re"]].copy()
    info["기준댓글"] = int(len(pop))
    info["기준_comment_id_중복"] = int(pop["comment_id"].duplicated().sum())
    info["기준_comment_id_결측"] = int(pop["comment_id"].isna().sum())
    info["댓글채널_불일치"] = int((pop["account_id"] != pop["video_account_id"]).sum())
    info["영상제목_결측"] = int(pop["video_title"].isna().sum())
    if info["기준댓글"] != 67891 or info["기준_comment_id_중복"] or info["기준_comment_id_결측"] or info["댓글채널_불일치"]:
        raise SystemExit(f"모집단이 예상과 다르다. 맞추지 않고 중단. {info}")
    return pop, info


def saya_ok(text: str, start: int) -> bool:
    if start <= 0:
        return True
    prev = text[start - 1]
    if prev.isspace() or prev in ".,!?~\"'()[]":
        return True
    if prev in "또더꼭막":
        return True
    if text[max(0, start - 2):start] == "지금":
        return True
    if prev in "시의기회검":
        return False
    return False


def window(text: str, start: int, end: int, n: int = 24) -> str:
    return text[max(0, start - n):min(len(text), end + n)]


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def classify(raw: str) -> dict:
    text = "" if raw is None or (isinstance(raw, float) and pd.isna(raw)) else str(raw)
    text = text.replace("\u200b", "").replace("\xa0", " ")
    hits: list[dict] = []
    notes: list[str] = []
    for rid, kind, cre in RULE_RES:
        for m in cre.finditer(text):
            surface = m.group(0)
            if rid == "R-intent" and "사야" in surface and not saya_ok(text, m.start() + surface.find("사야")):
                notes.append("시사야 등 사야 오탐 제외")
                continue
            if rid == "R-buy" and IDIOM.search(window(text, m.start(), m.end(), 8)):
                notes.append("질러 비유 제외")
                continue
            if rid == "R-pull":
                around = window(text, m.start(), m.end(), 16)
                if "풀" in text[max(0, m.start() - 3):m.start()] or "풀뽑" in around:
                    notes.append("풀뽑기 제외")
                    continue
                if GAME_NEAR.search(around):
                    hits.append({"kind": AMBIG, "rule": "R-game-pull", "surface": surface, "start": m.start(), "end": m.end(), "note": "게임 내 획득일 수 있음"})
                    continue
                if GIVEAWAY.search(around):
                    hits.append({"kind": AMBIG, "rule": "R-giveaway", "surface": surface, "start": m.start(), "end": m.end(), "note": "나눔·당첨 뽑기일 수 있음"})
                    continue
                near = window(text, m.start(), m.end(), 20)
                kind_use = BUY if re.search(r"인형|가챠|쿠지|피규어|키링|굿즈", near) else AMBIG
                rule_use = "R-pull-buy" if kind_use == BUY else "R-pull-ambig"
                note = "" if kind_use == BUY else "뽑기의 대상이 규칙으로 안 갈림"
                hits.append({"kind": kind_use, "rule": rule_use, "surface": surface, "start": m.start(), "end": m.end(), "note": note})
                continue
            if rid == "R-buy":
                before = text[max(0, m.start() - 16):m.start()]
                if re.search(r"(?:치이\s*까?카와|하치(?:와레)?|우사기|모몽가|랏코|파자마\s*파티즈|캐릭터|얘|애가)\s*(?:가|는|도|이)?\s*(?:드디어\s*)?$", before) or QUOTE.search(before):
                    hits.append({"kind": AMBIG, "rule": "R-quote-buy", "surface": surface, "start": m.start(), "end": m.end(), "note": "작품 속·인용 구매일 수 있음"})
                    continue
                if re.search(r"[?？]\s*$", surface) or re.search(r"사셨|샀(?:어|다|네|죠|음)요?\s*[?？]", surface):
                    hits.append({"kind": AMBIG, "rule": "R-ask-bought", "surface": surface, "start": m.start(), "end": m.end(), "note": "샀다가 질문·인용일 수 있음"})
                    continue
            if rid == "R-ambig-get" and re.search(r"(?:영상|정주행).{0,12}(?:봤|보았|보는)|(?:봤|보았).{0,10}(?:언박싱|개봉기|택배)", window(text, m.start(), m.end(), 16)):
                notes.append("개봉·언박싱은 영상 시청")
                continue
            if rid == "R-own" and re.search(r"가지고\s*놀|갖고\s*놀", surface):
                continue
            hits.append({"kind": kind, "rule": rid, "surface": surface, "start": m.start(), "end": m.end(), "note": ""})

    fail_spans = [(h["start"], h["end"]) for h in hits if h["kind"] == FAIL]
    kept = []
    for h in hits:
        if h["kind"] in (BUY, INTENT, OWN) and any(overlaps((h["start"], h["end"]), sp) for sp in fail_spans):
            continue
        kept.append(h)
    hits = kept

    # 시청·방문만 있고 상품 행동·상품명이 없으면 상품 소비 후보가 아니다.
    kinds = {h["kind"] for h in hits}
    if kinds <= {MENTION} or not kinds:
        pass
    product_surfaces = [h["surface"] for h in hits if h["kind"] == MENTION]
    behavior_hits = [h for h in hits if h["kind"] in BEHAVIOR]
    if not behavior_hits and not product_surfaces:
        kinds = set()

    work = franchise_of(text)
    types = []
    for kind in ORDER:
        if any(h["kind"] == kind for h in hits):
            types.append(kind)
    if not types:
        types = [NONE]

    prod_labels = []
    prod_words = []
    for label, cre in PRODUCTS:
        found = [m.group(0) for m in cre.finditer(text)]
        if found:
            prod_labels.append(label)
            prod_words.extend(found)
    # 파자마 파티즈 의류 오탐은 패턴에서 이미 제외. 상품 단어가 없으면 불명확.
    behavior_on = any(t in BEHAVIOR for t in types)
    if prod_labels:
        prod_out = "|".join(prod_labels)
    elif behavior_on:
        prod_out = "불명확"
    else:
        prod_out = ""

    surfaces_action = []
    rules = []
    neg_bits = []
    for h in hits:
        if h["kind"] == MENTION:
            continue
        if h["surface"] not in surfaces_action:
            surfaces_action.append(h["surface"])
        if h["rule"] not in rules:
            rules.append(h["rule"])
        if h["kind"] == FAIL and h["surface"] not in neg_bits:
            neg_bits.append(h["surface"])
        if h.get("note") and h["note"] not in notes:
            notes.append(h["note"])
    for h in hits:
        if h["kind"] == MENTION and h["rule"] not in rules:
            rules.append(h["rule"])

    subj = subject_of(text, behavior_hits)
    if subj == "본인|타인":
        notes.append("본인과 타인이 같이 보임")
        subj = "불명확"
    evidence = evidence_of(text, hits)
    candidate = "예" if behavior_on else "아니오"
    if types == [NONE]:
        subj = ""
    return {
        "상품소비_후보여부": candidate,
        "소비행동_후보유형": "|".join(types),
        "검출_행동표현": "|".join(surfaces_action[:8]),
        "검출_상품표현": "|".join(dict.fromkeys(prod_words)) if prod_words else "",
        "상품종류_후보": prod_out,
        "관련작품_후보": work if (behavior_on or MENTION in types) else work,
        "행동주체_후보": subj if behavior_on else "",
        "부정_취소_실패단서": "|".join(neg_bits[:4]),
        "원문_근거": evidence,
        "재검토_사유": "|".join(dict.fromkeys(notes)),
        "적용규칙ID": "|".join(rules),
        "판정방법": METHOD,
        "규칙버전": VER,
    }


def franchise_of(text: str) -> str:
    chi = bool(CHII.search(text))
    other = bool(OTHER.search(text))
    if chi and OPANCHU.search(text) and not re.search(r"치이\s*까?카와|먼작귀|하치|모몽가|쿠리|랏코|파자마\s*파티즈", text, re.I):
        chi = False
        other = True
    if chi and other:
        return "혼합"
    if chi:
        return "치이카와"
    if other:
        return "다른 작품"
    return "불명확"


def subject_of(text: str, behavior_hits: list[dict]) -> str:
    if not behavior_hits:
        return ""
    self_hit = False
    other_hit = False
    for h in behavior_hits:
        w = window(text, h["start"], h["end"], 30)
        if SELF_W.search(w):
            self_hit = True
        if OTHER_W.search(w) or "사셨" in h["surface"] or "구매하셨" in h["surface"]:
            other_hit = True
    if self_hit and other_hit:
        return "본인|타인"
    if self_hit:
        return "본인"
    if other_hit:
        return "타인"
    return "불명확"


def evidence_of(text: str, hits: list[dict]) -> str:
    parts = []
    for h in hits:
        if h["kind"] == MENTION and any(x["kind"] in BEHAVIOR for x in hits):
            continue
        bit = text[h["start"]:h["end"]]
        if bit and bit not in parts:
            parts.append(bit)
        if len(parts) >= 4:
            break
    return " / ".join(parts)


def self_check() -> None:
    cases = [
        ("시사야 너무 웃겨", NONE),
        ("비공개라서 못 봤어", NONE),
        ("팝콘게임즈 재밌다", NONE),
        ("치이카와 풀뽑기 시험 응원해", NONE),
        ("파자마 파티즈 귀엽다", NONE),
        ("치이카와가 밥 먹었어", NONE),
        ("게임에서 캐릭터 뽑았다", AMBIG),
        ("하치가 드디어 샀어", AMBIG),
        ("저도 샀어요", BUY),
        ("선물 받았어요", BUY),
        ("이 시리즈 모으는 중", OWN),
        ("갖고 싶다", INTENT),
        ("어디서 사요?", ASK),
        ("품절이라 못 샀어요", FAIL),
        ("이 인형 귀여워요", MENTION),
        ("드디어 데려왔다", AMBIG),
        ("이미 샀는데 또 사고 싶다", BUY + "|" + INTENT),
        ("정주행 했어", NONE),
        ("극장판 봤어", NONE),
        ("팝업 다녀왔어", NONE),
        ("산리오 인형 샀어", BUY + "|" + MENTION),
        ("어디서 사셨어요? 저도 사고 싶어요", INTENT + "|" + ASK),
        ("안 사고 싶어요", FAIL),
        ("쏴리질러", NONE),
        ("그냥 질러버려", NONE),
        ("파자마 샀어", BUY + "|" + MENTION),
        ("열심히 살게", NONE),
        ("안녕 시사야 열심히 살게", NONE),
        ("그래서 샀읍니당", BUY),
        ("어디서 구매하셨나요", ASK),
        ("관할서에 고소장", NONE),
        ("하치와레 드디어 샀구나", AMBIG),
        ("아크릴스탠드까지 샀오요", BUY),
        ("샀을거 같아요", NONE),
        ("구매할 의향 있습니다", INTENT),
        ("모몽가만 모으는데", OWN),
    ]
    bad = []
    for text, expect in cases:
        got = classify(text)["소비행동_후보유형"]
        if got != expect:
            bad.append((text, expect, got))
    if bad:
        raise SystemExit(f"규칙 자체점검 실패 {bad}")
    row = classify("산리오 인형 샀어")
    if row["관련작품_후보"] != "다른 작품" or "인형·봉제" not in row["상품종류_후보"]:
        raise SystemExit(f"작품·상품 점검 실패 {row}")
    if classify("저도 샀어요")["상품종류_후보"] != "불명확":
        raise SystemExit("상품명 없는 구매가 빠졌다")
    if "의향" in classify("어디서 사요?")["소비행동_후보유형"]:
        raise SystemExit("질문을 의향으로 바꿨다")
    if classify("이 인형 귀여워요")["상품소비_후보여부"] != "아니오":
        raise SystemExit("단순 언급을 행동 후보로 넣었다")
    ev = classify("저도 샀어요")["원문_근거"]
    if ev not in "저도 샀어요":
        raise SystemExit(f"근거가 원문 밖이다 {ev}")


def main() -> None:
    self_check()
    pop, info = population()
    rows = []
    for raw in pop["comment_description"].tolist():
        rows.append(classify(raw))
    judged = pd.DataFrame(rows)
    out = pd.concat(
        [
            pop[["comment_id", "post_id", "account_id"]].reset_index(drop=True),
            pop["comment_description"].reset_index(drop=True).rename("댓글원문"),
            pop["video_title"].reset_index(drop=True).rename("영상제목"),
            pop["lang_re"].reset_index(drop=True).rename("언어판정"),
            judged,
        ],
        axis=1,
    )
    if len(out) != len(pop) or out["comment_id"].duplicated().any():
        raise SystemExit("출력 행 수가 기준 댓글과 다르다")
    behavior = out[out["상품소비_후보여부"] == "예"].copy()
    old_ids: set[str] = set()
    old_n = 0
    if OLD_CAND.exists():
        old = pd.read_csv(OLD_CAND, encoding="utf-8-sig", usecols=["comment_id"])
        old_ids = set(old["comment_id"])
        old_n = int(old["comment_id"].nunique())
    beh_ids = set(behavior["comment_id"])
    recovered = beh_ids - old_ids
    inside = beh_ids & old_ids
    old_outside_behavior = old_ids - beh_ids

    def n_videos(frame: pd.DataFrame) -> int:
        return int(frame["post_id"].nunique()) if len(frame) else 0

    def n_channels(frame: pd.DataFrame) -> int:
        return int(frame["account_id"].nunique()) if len(frame) else 0

    summary_rows = [
        {"항목": "기준댓글", "고유댓글": int(len(out)), "영상": n_videos(out), "채널": n_channels(out), "분모": int(len(out)), "메모": "한국어 중심·혼합, 광고·스팸 제외. 예상 67891과 같음"},
        {"항목": "행동후보", "고유댓글": int(len(behavior)), "영상": n_videos(behavior), "채널": n_channels(behavior), "분모": int(len(out)), "메모": "구매·획득·소장·의향·질문·미구매·모호. 단순 언급과 해당 없음 제외"},
    ]
    type_sum = 0
    for kind in ORDER + [NONE]:
        sub = out[out["소비행동_후보유형"].map(lambda s, k=kind: k in str(s).split("|"))]
        type_sum += int(len(sub))
        summary_rows.append({
            "항목": kind,
            "고유댓글": int(len(sub)),
            "영상": n_videos(sub),
            "채널": n_channels(sub),
            "분모": int(len(out)),
            "메모": "한 댓글이 여러 유형이면 각 유형에 들어 합이 기준 댓글보다 클 수 있음",
        })
    summary_rows.append({
        "항목": "유형고유댓글_합",
        "고유댓글": type_sum,
        "영상": "",
        "채널": "",
        "분모": int(len(out)),
        "메모": "중복 포함 합. 기준 댓글 수와 같지 않아도 됨",
    })
    explicit = behavior[behavior["상품종류_후보"].map(lambda s: bool(s) and s != "불명확")]
    unclear = behavior[behavior["상품종류_후보"].eq("불명확")]
    summary_rows.append({"항목": "행동후보_상품종류명시", "고유댓글": int(len(explicit)), "영상": n_videos(explicit), "채널": n_channels(explicit), "분모": int(len(behavior)), "메모": "행동 후보 분모"})
    summary_rows.append({"항목": "행동후보_상품종류불명확", "고유댓글": int(len(unclear)), "영상": n_videos(unclear), "채널": n_channels(unclear), "분모": int(len(behavior)), "메모": "상품명이 없어도 행동이면 후보에 남김"})
    for label in ["치이카와", "다른 작품", "혼합", "불명확"]:
        sub = behavior[behavior["관련작품_후보"] == label]
        summary_rows.append({"항목": f"행동후보_작품_{label}", "고유댓글": int(len(sub)), "영상": n_videos(sub), "채널": n_channels(sub), "분모": int(len(behavior)), "메모": "댓글 본문만. 제목으로 치이카와를 확정하지 않음"})
    summary_rows.append({"항목": "기존8719_대조파일", "고유댓글": old_n, "영상": "", "채널": "", "분모": "", "메모": str(OLD_CAND.name)})
    summary_rows.append({"항목": "행동후보_중_기존8719_밖", "고유댓글": int(len(recovered)), "영상": "", "채널": "", "분모": int(len(behavior)), "메모": "이번 행동 후보에만 있는 댓글"})
    summary_rows.append({"항목": "행동후보_중_기존8719_안", "고유댓글": int(len(inside)), "영상": "", "채널": "", "분모": int(len(behavior)), "메모": ""})
    summary_rows.append({"항목": "기존8719_중_이번행동후보_아님", "고유댓글": int(len(old_outside_behavior)), "영상": "", "채널": "", "분모": old_n, "메모": "시청·방문·오탐이 이전 후보에 섞여 있을 수 있음. 이전 집계를 재사용하지 않음"})

    # 해당 없음에 구매 표현이 남았는지. 사람 검수가 아니다.
    none = out[out["소비행동_후보유형"] == NONE]
    miss_pats = [
        ("해당없음_속_샀", re.compile(r"샀")),
        ("해당없음_속_구매", re.compile(r"구매|구입")),
        ("해당없음_속_싶", re.compile(r"사고\s*싶|갖고\s*싶|가지고\s*싶")),
        ("해당없음_속_어디서사", re.compile(r"어디서\s*사")),
        ("해당없음_속_소장", re.compile(r"(?<!고)소장(?!장|가치)|모으")),
    ]
    check_parts = []
    for label, cre in miss_pats:
        hit = none[none["댓글원문"].fillna("").map(lambda s, c=cre: bool(c.search(str(s))))]
        summary_rows.append({"항목": label, "고유댓글": int(len(hit)), "영상": "", "채널": "", "분모": int(len(none)), "메모": "규칙 누락 점검. 사람 검수 아님"})
        if len(hit):
            take = hit.sample(n=min(8, len(hit)), random_state=20261106)
            check_parts.append(take.assign(점검=label))
    # 오탐·경계 사례
    flags = [
        ("오탐점검_시사야", out["댓글원문"].fillna("").str.contains("시사야", regex=False) & out["소비행동_후보유형"].str.contains("의향|경험", regex=True)),
        ("경계_부정", out["부정_취소_실패단서"].fillna("").ne("")),
        ("경계_복수유형", out["소비행동_후보유형"].str.contains(r"\|", regex=True)),
        ("경계_상품명없는행동", (out["상품소비_후보여부"] == "예") & out["상품종류_후보"].eq("불명확")),
        ("경계_다른작품", out["관련작품_후보"].eq("다른 작품") & (out["상품소비_후보여부"] == "예")),
        ("경계_타인", out["행동주체_후보"].eq("타인")),
        ("경계_재검토", out["재검토_사유"].fillna("").ne("")),
    ]
    for label, mask in flags:
        sub = out[mask]
        summary_rows.append({"항목": label, "고유댓글": int(len(sub)), "영상": "", "채널": "", "분모": int(len(out)), "메모": "사람 검수 아님"})
        if len(sub):
            take = sub.sample(n=min(6, len(sub)), random_state=20261106)
            check_parts.append(take.assign(점검=label))
    checks = pd.concat(check_parts, ignore_index=True) if check_parts else pd.DataFrame()

    summary = pd.DataFrame(summary_rows)
    dict_rows = [{"규칙ID": rid, "유형": kind, "패턴": pat, "메모": "댓글 본문만. 제목 미사용"} for rid, kind, pat in RULES]
    pd.DataFrame(dict_rows).to_csv(OUT / "00_사전.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "03_유형별_요약.csv", index=False, encoding="utf-8-sig")
    out.to_csv(OUT / "01_전체_1차분류.csv", index=False, encoding="utf-8-sig")
    behavior.to_csv(OUT / "02_행동후보.csv", index=False, encoding="utf-8-sig")
    if len(checks):
        cols = ["점검", "comment_id", "post_id", "소비행동_후보유형", "상품종류_후보", "관련작품_후보", "행동주체_후보", "원문_근거", "재검토_사유", "댓글원문"]
        checks[cols].to_csv(OUT / "00_점검표본.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"항목": k, "값": v} for k, v in info.items()]).to_csv(
        OUT / "00_모집단검증.csv", index=False, encoding="utf-8-sig"
    )
    print(summary.to_string(index=False))
    print("기준", info["기준댓글"], "행동후보", len(behavior), "회수", len(recovered))


if __name__ == "__main__":
    main()
