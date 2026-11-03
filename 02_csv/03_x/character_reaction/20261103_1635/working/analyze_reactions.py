# -*- coding: utf-8 -*-
"""Character x appeal x author reaction on Chiikawa X posts.

Rules were drafted from a development sample, then applied to every post.
Source files are not modified. Evidence row counts are not post counts.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
NORM = ROOT / "normalized"
OUT = ROOT / "character_reaction" / "20261103_1635"
WORK = OUT / "working"
TABLES = OUT / "tables"
CHARTS = OUT / "charts"
for p in (WORK, TABLES, CHARTS):
    p.mkdir(parents=True, exist_ok=True)

VERSION = "2026-11-03.reaction.v3"

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
HASHTAG_RE = re.compile(r"#([^\s#]+)")
HANGUL_RE = re.compile(r"[가-힣]")
KANA_RE = re.compile(r"[ぁ-んァ-ン]")
CJK_RE = re.compile(r"[一-龯]")
LATIN_RE = re.compile(r"[A-Za-z]")
WS_RE = re.compile(r"\s+")

CONN_RE = re.compile(r"아서|어서|해서|여서|워서|뻐서|겨서|싸서|라서|때문에|니까|길래|덕분에")
SPLIT_RE = re.compile(r"[\n\r]+|(?<=[\.!?。！？])\s+| ?근데 | ?그런데 | ?하지만 | ?그러나 ")

ANCHOR_RE = re.compile(
    r"치이카와|치이까와|치카와|먼작귀|하치와레|하치와래|모몽가|모몬가|랏코|락코|쿠리만|갑옷\s*씨|갑옷\s*아저씨|갑옷상|"
    r"아노코|데카츠요|ちいかわ|チイカワ|chiikawa|ハチワレ|モモンガ|ラッコ|クリマンジュ",
    re.I,
)

# Longest-first matching is handled by overlap resolution, not list order.
CHAR_SPECS = [
    ("하치와레", "confirmed", re.compile(r"하치와레|하치와래|하찌와레|하찌와래|뿔치와레|우쭐\s*하치|ハチワレ|はちわれ|hachiware", re.I)),
    ("모몽가", "confirmed", re.compile(r"모몽가|모몬가|モモンガ")),
    ("랏코", "confirmed", re.compile(r"랏코|락코|ラッコ|らっこ")),
    ("쿠리만쥬", "confirmed", re.compile(r"쿠리만쥬|쿠리만주|くりまんじゅう|クリマンジュウ")),
    ("갑옷씨", "confirmed", re.compile(r"갑옷\s*씨|갑옷\s*아저씨|갑옷상|鎧さん")),
    ("아노코", "confirmed", re.compile(r"아노코|あのこ|あの子")),
    ("데카츠요", "confirmed", re.compile(r"데카츠요|デカツヨ")),
    ("치이카와", "chiikawa", re.compile(r"치이카와|치이까와|(?<![하이])치카와|(?<![하이])치까와|ちいかわ|チイカワ|chiikawa|吉伊卡哇", re.I)),
    ("우사기", "usagi", re.compile(r"우사기|うさぎ|ウサギ|usagi", re.I)),
    ("시사", "shisa", re.compile(r"시사(?!하|점|성|프|교|저|인|IN)|シーサー")),
    ("카니", "kani", re.compile(r"카니(?!발)|(?<![ァ-ン])カニ(?![ァ-ン])")),
    ("오데", "anchored", re.compile(r"(?<![가-힣])오데")),
    ("고블린", "anchored", re.compile(r"고블린")),
    ("키메라", "anchored", re.compile(r"키메라")),
    ("풍뎅이", "anchored", re.compile(r"풍뎅이|카부토무시|カブトムシ")),
    ("스핑크스", "anchored", re.compile(r"스핑크스")),
]
WORK_TITLE_RE = re.compile(r"먼작귀|뭔가 작고 귀여운|먼가 작고 귀여운")
ALIAS_RE = {
    "가르마": re.compile(r"가르마"),
    "토끼": re.compile(r"(?<![가-힣])토끼(?![가-힣])"),
    "하치짧은": re.compile(r"(?<![가-힣])하치(?!와|병)"),
    "치이짧은": re.compile(r"(?<![가-힣])치이(?!카|까)"),
}

PRODUCT_RE = re.compile(
    r"인형|키링|키홀더|피규어|마스코트|누이|가챠|쿠지|스티커|파우치|시계|달력|캘린더|아크릴|"
    r"뱃지|캔뱃지|굿즈|나노블럭|블럭|블록|스트랩|쿠션|파자마|잠옷|티셔츠|케이스|그립톡|"
    r"메모|클립|캘린더|다이어리|문구|텀블러|컵|양말|슬립퍼|룸라이트|조명"
)
SCENE_RE = re.compile(r"애니|만화|에피|장면|극장|영화|\d+\s*화|편")
WORK_CUE_RE = re.compile(
    r"애니|영화|만화|극장|팝업|콜라보|시리즈|카페|에피|더빙|자막|정주행|굿즈|마켓|샵|스토어|"
    r"발매|입고|공식|월드|세계관|원작|웹툰|\d+\s*화"
)
CHAR_GRAMMAR_RE = re.compile(
    r"치이카와(?:이|가)\b|치이카와(?:이|가)(?=[^가-힣]|$)|"
    r"치이카와(?:은|는|도)\s*(?:울|웃|춤|먹|달리|겁|말|뛰|앉|자|크|작|귀|좋)|"
    r"치이카와(?:의)?\s*(?:표정|얼굴|목소리|말투|성격|볼|눈|입|팔|다리)"
)
# particles after the name are hangul, so \b is unreliable. Use explicit tails.
CHAR_GRAMMAR_RE = re.compile(
    r"치이카와(?:이|가)(?:\s|$|[^가-힣])|"
    r"치이카와(?:은|는|도)\s*(?:울|웃|춤|먹|달리|겁|뛰|앉)|"
    r"치이카와(?:의)?\s*(?:표정|얼굴|목소리|말투|성격|볼살|볼 |눈 |입 )"
)

PROMO_RE = re.compile(
    r"입고\s*되었|입고되었|입고\s*완료|입고합|입고\s*됐|발매|예약\s*판매|재입고|증정|"
    r"가격\s*문의|판매합니다|팝니다|공구해|공구\s*모집|공구합니다|신제품|품절\s*안내|"
    r"세금\s*포함|팔로우|추첨해|디엠\s*주|DM\s*주|스마트스토어|윗치폼|구매하세요|오픈합니다|"
    r"입고\s*알림|재고\s*현황|네이버\s*스토어"
)
TRADE_RE = re.compile(r"양도|급처|교환합니다|교환해요|교환\s*가능|교환\s*원|구합니다|구해요|반택|나눔합니다")
PERSONAL_GET_RE = re.compile(
    r"샀어|샀다|샀네|샀음|구매했|구매\s*완료|구매완료|주문했|결제했|겟했|득템|데려왔|데려온|"
    r"뽑았|뽑았다|질렀|받아왔|받아왔|구했|구해왔|사서|샀지|겟\s*했|도착했|배송\s*왔"
)
HOPE_RE = re.compile(
    r"사고\s*싶|사고싶|사야지|살까|갖고\s*싶|갖고싶|가지고\s*싶|소장하고\s*싶|사고\s*시픔|"
    r"내놔\s*\(?주|양도\s*받|사고\s*팠|질러야|구매\s*걸어|사고\s*팠"
)
NOBUY_RE = re.compile(r"못\s*샀|안\s*샀|못샀|안샀|구매\s*못|못\s*사겠|살\s*수\s*없|못\s*감|예약\s*마감")
USE_RE = re.compile(r"가방에|달고\s*다|달았|달아\s*둠|달아둠|붙여\s*뒀|전시|차고\s*다|끼고\s*다|들고\s*다녔|케이스에\s*넣|침대에|책상\s*위")
VISIT_RE = re.compile(
    r"(?:팝업|카페|스토어|매장|팝업스토어).{0,18}(?:갔|가봤|다녀|갈게|갈\s*예정|못\s*감|방문)|"
    r"(?:갔|가봤|다녀왔|방문했).{0,12}(?:팝업|카페|매장)"
)
TRANSLATE_RE = re.compile(r"번역")
CREATE_RE = re.compile(r"그렸|그려봤|그려\s*봄|팬아트|자작|픽크루|만들어\s*봤|만들어봤|만들어\s*봄")
RECOMMEND_RE = re.compile(r"추천|강추|봐\s*보세|꼭\s*보|꼭\s*들|보셈|보세요")
SCENE_ACT_RE = re.compile(r"먹|울|춤|달리|기어|말리|쫓|뛰|앉|웃는|고개|말하|부르")

EVAL_POS_RE = re.compile(
    r"귀엽|귀여|기여|뀌엽|귀욥|코여|조아|조와|좋아하|좋아요|좋았|좋다|좋네|좋지|좋음|좋은데|"
    r"사랑|웃기|웃겨|웃김|웃겼|빵터|힐링|소중|설레|행복|기특|최고|레전|취향|마음에\s*들|"
    r"모에|귀염|뽀짝|커여|커엽|개귀|존귀|핵귀"
)
EVAL_NEG_RE = re.compile(r"안\s*귀엽|귀엽지\s*않|별로|안\s*좋|좋지\s*않|마음에\s*안|노잼|못생겼|불편|짜증\s*나")
NEG_WINDOW_RE = re.compile(r"안\s*$|못\s*$|별로\s*$")
AFFECT_WORD_RE = re.compile(r"힐링|위로|행복|소중|공감|힘내|지켜|응원|불쌍|측은|울지\s*마")
FUNNY_RE = re.compile(r"웃기|웃겨|웃김|웃겼|빵터|빵\s*터|ㅈㄴ\s*웃|개웃")
COMFORT_RE = re.compile(r"힐링|위로|치유|행복하|마음\s*편|안정")
EMPATHY_RE = re.compile(r"공감|나랑\s*같|내\s*얘기|나도\s*그래|현실")
PROTECT_RE = re.compile(r"지켜\s*주|보호|응원|불쌍|측은|고생|화이팅|울지\s*마|안아")
LOVE_RE = re.compile(
    r"귀엽|귀여|기여|뀌엽|귀욥|코여|조아|조와|좋아하|좋아요|좋았|좋다|좋네|좋지|좋음|"
    r"사랑|최고|레전|취향|마음에\s*들|모에|귀염|뽀짝|커여|설레|기특|소중"
)

FEATURE = [
    ("외형·표정", re.compile(r"표정|얼굴|볼살|볼터치|볼이|볼을|주둥이|옆모습|앞머리|일자앞머리|눈망울|눈동자|눈빛|동그란|둥근|똥글|동글|작디작|팔다리|짧은\s*팔|짧은\s*다리|꼬리|털빛|실루엣|비율|코스튬|옷\s*입|뚠빵|통실|보송|부들|뒷모습|털공")),
    ("목소리·말투", re.compile(r"목소리|성우|더빙|말투|발음|웃음소리|웃는\s*소리|대사투리|억양|싱크로|톤도")),
    ("성격", re.compile(r"성격|다정|착하|겁\s*없|겁이\s*없|순수|열정|똑부러|깐죽|잔인|사악|기특|용감|소심|친절|순둥|악랄|나쁜\s*놈|인간적|똑부러지|의젓|하찮|간악|갭")),
    ("행동·움직임", re.compile(r"춤|달리|먹방|기어|몸짓|알바|움직임|폴짝|까불|쫓아|말리|행동|제스처|걷는|걸어|발버둥|흔들|달라붙")),
    ("관계", re.compile(r"우정|케미|사이가|돌봐|곁에|함께라서|친구\s*사이|조합")),
    ("이야기·설정", re.compile(r"세계관|설정|스토리|이야기|에피소드|자격증|노동|섬의|명장면|전개|결말")),
    ("상품의 디자인·소재·쓰임", re.compile(r"재질|마감|퀄리티|말랑|폭신|부들|촉감|사이즈|소재|투명|봉제|털이\s*송|만졌|쓰임|실용|크기")),
]
# 작다/귀엽다 alone is not a feature. Title phrase is excluded later.
TITLE_SMALL_RE = re.compile(r"작고 귀여운 녀석|먼가 작고|뭔가 작고")
GROUP_RE = re.compile(r"다들|모두|셋\s*다|애들|애기들|친구들|삼총사")
ATTACH_RE = re.compile(r"이\s*표정|이\s*장면|이거|요거|사진|영상|짤")
DISLIKE_STORY_RE = re.compile(r"싫어하는\s*거|싫어하는거|브로콜리")


def counts(s: str):
    return (
        len(HANGUL_RE.findall(s)),
        len(KANA_RE.findall(s)),
        len(CJK_RE.findall(s)),
        len(LATIN_RE.findall(s)),
    )


def analysis_text(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = t.replace("#", " ")
    return t


def language_of(raw: str) -> str:
    body = MENTION_RE.sub(" ", URL_RE.sub(" ", raw))
    tags = " ".join(HASHTAG_RE.findall(body))
    body_wo = HASHTAG_RE.sub(" ", body)
    h, k, c, l = counts(body_wo)
    ko_s = ot_s = 0
    for part in re.split(r"[\n\r.!?。！？]+", body_wo):
        hh, kk, cc, ll = counts(part)
        if hh >= 4 and hh > kk + cc:
            ko_s += 1
        elif hh == 0 and (kk + cc >= 4 or ll >= 15):
            ot_s += 1
    if ko_s >= 1 and ot_s >= 1 and h >= 8:
        return "한국어 중심 혼합"
    if ko_s >= 1:
        return "한국어 중심"
    if h + k + c + l < 2:
        return "판단 불가"
    if k + c >= 4 or l >= 15:
        return "다른 언어 중심"
    if h >= 2:
        return "한국어 중심"
    if counts(tags)[0] + counts(tags)[1] + counts(tags)[2] >= 2:
        return "판단 불가"
    return "판단 불가"


def norm(s: str) -> str:
    return WS_RE.sub(" ", s).strip()


def find_spans(text: str):
    spans = []
    for name, kind, rx in CHAR_SPECS:
        for m in rx.finditer(text):
            spans.append({"name": name, "kind": kind, "start": m.start(), "end": m.end(), "surface": m.group()})
    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    kept = []
    last_end = -1
    for s in spans:
        if s["start"] < last_end:
            continue
        kept.append(s)
        last_end = s["end"]
    return kept


def gate_mentions(text: str, spans: list) -> list:
    anchored = bool(ANCHOR_RE.search(text))
    # 우사기 itself should not count as the only anchor for itself.
    other_anchor = bool(
        re.search(
            r"치이카와|치이까와|먼작귀|하치와레|모몽가|모몬가|랏코|락코|쿠리만|갑옷\s*씨|갑옷\s*아저씨|아노코|데카츠요|ちいかわ|chiikawa",
            text,
            re.I,
        )
    )
    out = []
    for s in spans:
        pre = text[max(0, s["start"] - 4) : s["start"]]
        if s["name"] == "우사기" and ("빤쮸" in pre or "팬티" in pre):
            s = {**s, "status": "제외_다른대상"}
            out.append(s)
            continue
        if s["kind"] == "confirmed" or s["kind"] == "chiikawa":
            s = {**s, "status": "확정"}
        elif s["kind"] == "usagi":
            s = {**s, "status": "확정" if other_anchor or anchored else "문맥확인필요"}
            # 우사기 in a Korean post collected as the name is still ambiguous without another cue.
            # other_anchor excludes the usagi token. If the only cue is usagi, leave unconfirmed.
            if s["name"] == "우사기" and not other_anchor:
                # chiikawa/hachiware etc. absent. Keep unconfirmed even if ANCHOR matched 우사기 itself.
                if not re.search(
                    r"치이카와|치이까와|먼작귀|하치와레|모몽가|모몬가|랏코|락코|쿠리만|갑옷|아노코|데카츠요|ちいかわ|chiikawa|나가노",
                    text,
                    re.I,
                ):
                    s["status"] = "문맥확인필요"
                else:
                    s["status"] = "확정"
        elif s["kind"] in {"shisa", "kani"}:
            cue = other_anchor or bool(re.search(r"성우|최애|캐릭터|먼작귀|치이카와", text))
            s = {**s, "status": "확정" if cue else "문맥확인필요"}
        elif s["kind"] == "anchored":
            s = {**s, "status": "확정" if (other_anchor or anchored) else "문맥확인필요"}
        else:
            s = {**s, "status": "확정"}
        out.append(s)
    return out


def chiikawa_role(clause: str) -> str:
    """작품 / 주인공 / 불명확. 다른 이름이 같이 있다는 이유만으로 주인공이 되지 않는다."""
    if not re.search(r"치이카와|치이까와|치카와|치까와|ちいかわ|chiikawa|吉伊卡哇", clause, re.I):
        return ""
    productish = bool(PRODUCT_RE.search(clause)) and bool(
        re.search(r"(?:치이카와|치이까와|치카와).{0,8}(?:인형|키링|피규어|가챠|쿠지|스티커|파우치|시계|마스코트|누이|굿즈)|(?:인형|키링|피규어).{0,8}치이카와", clause)
    )
    body = bool(re.search(r"볼살|볼이|볼을|표정|팔다리|짧은\s*다리|똥글|동그란|몸\s*말랑", clause)) and not productish
    char_g = bool(CHAR_GRAMMAR_RE.search(clause)) or body
    media = bool(re.search(r"애니|영화|만화|극장|팝업|에피소드|더빙판", clause))
    shop = bool(re.search(r"(?:치이카와|치이까와)\s*(?:마켓|샵|스토어|굿즈|콜라보|시리즈)", clause))
    if char_g and not productish:
        return "주인공"
    if media or shop or productish:
        return "작품"
    return "불명확"


def split_clauses(text: str):
    parts = []
    idx = 0
    for m in SPLIT_RE.finditer(text):
        chunk = text[idx : m.start()]
        if norm(chunk):
            parts.append({"text": chunk, "start": idx, "end": m.start()})
        idx = m.end()
    tail = text[idx:]
    if norm(tail):
        parts.append({"text": tail, "start": idx, "end": len(text)})
    if not parts and norm(text):
        parts.append({"text": text, "start": 0, "end": len(text)})
    return parts


def features_in(text: str) -> list[str]:
    if TITLE_SMALL_RE.search(text):
        # still allow other features; drop a false 'small' from the title by masking
        text_for_small = TITLE_SMALL_RE.sub(" ", text)
    else:
        text_for_small = text
    found = []
    for label, rx in FEATURE:
        src = text_for_small if label == "외형·표정" else text
        if rx.search(src):
            # material words on a product stay in 상품; also keep them out of character body
            found.append(label)
    # 말랑/폭신/작다 without the feature regex already included in 상품
    return found


def emotion_of(text: str) -> str:
    if DISLIKE_STORY_RE.search(text) and not EVAL_NEG_RE.search(text):
        neg = False
    else:
        neg = bool(EVAL_NEG_RE.search(text))
    # 싫어하는거 is the character's dislike, not the author's
    if re.search(r"싫", text) and not re.search(r"싫어하는", text):
        if re.search(r"(치이카와|하치와레|우사기|얘|이거).{0,8}싫|싫.{0,6}(치이카와|하치와레)", text):
            if not re.search(r"싫으면", text):
                neg = True
    if re.search(r"핫플|굿즈샵|피규어샵", text) and re.search(r"좋아요", text) and not re.search(r"너무|진짜|넘 |존나", text):
        text = text.replace("좋아요", " ")
    pos_love = bool(LOVE_RE.search(text))
    funny = bool(FUNNY_RE.search(text))
    comfort = bool(COMFORT_RE.search(text))
    empathy = bool(EMPATHY_RE.search(text))
    protect = bool(PROTECT_RE.search(text))
    # negation window near a positive word flips that positive
    flipped = False
    for m in LOVE_RE.finditer(text):
        window = text[max(0, m.start() - 8) : m.start()]
        if NEG_WINDOW_RE.search(window) or re.search(r"지\s*않$|지\s*안$", window):
            flipped = True
    if flipped:
        pos_love = False
        neg = True
    labels = []
    if pos_love and not flipped:
        labels.append("호감")
    if funny and not flipped:
        labels.append("웃음·재미")
    if comfort:
        labels.append("위로")
    if empathy:
        labels.append("공감")
    if protect:
        labels.append("응원·보호 욕구")
    if neg:
        labels.append("비호감·불편")
    if not labels:
        if "?" in text or re.search(r"어디|뭐야|정보|안내|소식", text):
            return "질문·정보·중립"
        return ""
    if "비호감·불편" in labels and any(x in labels for x in ("호감", "웃음·재미", "위로")):
        return "혼합"
    # prefer a specific positive if several, but keep multi by joining later
    return "|".join(dict.fromkeys(labels))


def behaviors_of(text: str) -> list[str]:
    out = []
    if TRANSLATE_RE.search(text):
        out.append("번역·팬 창작")
    if CREATE_RE.search(text):
        out.append("번역·팬 창작")
    if RECOMMEND_RE.search(text):
        out.append("추천·공유 의향")
    if HOPE_RE.search(text):
        out.append("구매·소장 희망")
    if PERSONAL_GET_RE.search(text) and not PROMO_RE.search(text):
        out.append("구매·획득 경험")
    elif PERSONAL_GET_RE.search(text) and re.search(r"내가|저는|저 |샀|겟|뽑았|데려", text):
        out.append("구매·획득 경험")
    if USE_RE.search(text):
        out.append("사용·휴대·전시·보관 경험")
    if VISIT_RE.search(text):
        out.append("방문 희망·경험")
    if NOBUY_RE.search(text):
        out.append("미구매")
    if SCENE_ACT_RE.search(text) and re.search(
        r"하치와레|우사기|모몽가|랏코|쿠리만|치이카와|시사|카니|갑옷|오데|스핑크스|풍뎅이", text
    ):
        if not PROMO_RE.search(text):
            out.append("장면·대사 인용")
    # dedupe
    return list(dict.fromkeys(out))


def speaker_of(text: str, post_promo: bool = False) -> str:
    personal = bool(re.search(r"내가|저는|개인적으로|샀다|구매했|데려왔", text))
    if post_promo and not personal:
        return "홍보문구"
    if PROMO_RE.search(text) and not personal:
        return "홍보문구"
    if TRANSLATE_RE.search(text) and not EVAL_POS_RE.search(text):
        return "번역문"
    return "작성자"


def author_result(text: str) -> bool:
    if emotion_of(text):
        emo = emotion_of(text)
        if emo and emo != "질문·정보·중립":
            return True
    if any(
        b in behaviors_of(text)
        for b in (
            "구매·소장 희망",
            "구매·획득 경험",
            "사용·휴대·전시·보관 경험",
            "방문 희망·경험",
            "미구매",
            "추천·공유 의향",
            "번역·팬 창작",
        )
    ):
        return True
    return False


def names_near(clause: str, pos: int, names: list[str], radius: int = 18) -> list[str]:
    window = clause[max(0, pos - radius) : pos + 8]
    hit = []
    for n in names:
        if n == "치이카와" and re.search(r"치이카와|치이까와|치카와", window):
            hit.append(n)
        elif n == "모몽가" and ("모몽가" in window or "모몬가" in window):
            hit.append(n)
        elif n == "랏코" and ("랏코" in window or "락코" in window):
            hit.append(n)
        elif n == "하치와레" and "하치와레" in window:
            hit.append(n)
        elif n not in {"치이카와", "모몽가", "랏코", "하치와레"} and n in window:
            hit.append(n)
    return list(dict.fromkeys(hit))


def focus_character(clause: str, names: list[str]) -> str:
    """평가어 바로 앞에 이름이 하나일 때만 그 캐릭터로 돌린다."""
    if not names:
        return ""
    positions = []
    for rx in (LOVE_RE, FUNNY_RE, EVAL_NEG_RE, COMFORT_RE):
        for m in rx.finditer(clause):
            positions.append(m.start())
    for _, rx in FEATURE:
        for m in rx.finditer(clause):
            positions.append(m.start())
    if not positions:
        return names[0] if len(names) == 1 else ""
    near_sets = [names_near(clause, p, names) for p in positions]
    nonempty = [s for s in near_sets if s]
    if nonempty and all(len(s) == 1 and s[0] == nonempty[0][0] for s in nonempty):
        return nonempty[0][0]
    if len(names) == 1:
        return names[0]
    return ""


def assign_target(clause: str, names: list[str], feats: list[str]) -> tuple[str, str]:
    """Return (reaction_target, character_or_blank)."""
    product = bool(PRODUCT_RE.search(clause))
    scene = bool(SCENE_RE.search(clause))
    who = focus_character(clause, names)
    interaction = bool(re.search(r"달라붙|구해주|데려다|말리|돌봐|뺏|나눠\s*주|함께|같이|허리에|안아", clause))
    if product and not scene:
        return "굿즈", who if len(names) == 1 else ""
    if len(names) >= 2 and (interaction or re.search(r"우정|케미|관계|사이좋", clause)):
        return "캐릭터 간 관계", ""
    cause = re.search(r"(하치와레|우사기|모몽가|모몬가|랏코|락코|쿠리만쥬|쿠리만주|시사|카니|갑옷\s*씨|치이카와)\s*때문에", clause)
    if cause and (LOVE_RE.search(clause) or FUNNY_RE.search(clause) or COMFORT_RE.search(clause)):
        token = cause.group(1)
        mapped = {"모몬가": "모몽가", "락코": "랏코", "쿠리만주": "쿠리만쥬", "갑옷 씨": "갑옷씨"}.get(token, token)
        if mapped == "치이카와" and chiikawa_role(clause) != "주인공":
            return "불명확", "치이카와"
        return "특정 캐릭터", mapped
    if re.search(r"세계관|설정|스토리|에피소드|자격증", clause) and not who:
        return "작품·스토리·세계관", ""
    if re.search(r"그렸|팬아트|번역|픽크루", clause) and not product and not who:
        return "팬아트·번역·편집·창작자", ""
    if who == "치이카와":
        role = chiikawa_role(clause)
        if role == "주인공":
            return "특정 캐릭터", "치이카와"
        if role == "작품":
            return "작품·스토리·세계관", ""
        return "불명확", "치이카와"
    if who:
        return "특정 캐릭터", who
    if WORK_TITLE_RE.search(clause) or chiikawa_role(clause) == "작품":
        return "작품·스토리·세계관", ""
    return "불명확", ""


def reason_parts(clause: str):
    """직접 이유는 왼쪽이 특징이나 호감이고, 오른쪽이 작성자의 감정·행동일 때만."""
    matches = list(CONN_RE.finditer(clause))
    if not matches:
        return None
    chosen = None
    for m in matches:
        right = clause[m.end() :]
        left = clause[: m.start()]
        cut = max(left.rfind("지만"), left.rfind("는데"), left.rfind("다만"))
        if cut != -1:
            left = left[cut + 2 :]
        if re.search(r"(있길래|없어서|있어서|없길래|없기 때문에)\s*$", left) and not features_in(left):
            continue
        left_feat = features_in(left)
        left_aff = bool(LOVE_RE.search(left) or FUNNY_RE.search(left) or EVAL_NEG_RE.search(left) or COMFORT_RE.search(left))
        right_emo = emotion_of(right)
        right_aff = bool(right_emo) and right_emo != "질문·정보·중립"
        right_act = bool(
            HOPE_RE.search(right)
            or PERSONAL_GET_RE.search(right)
            or CREATE_RE.search(right)
            or USE_RE.search(right)
            or re.search(r"숨|미치|기절|쓰러|환장|눈물|실신", right)
        )
        if (left_feat or left_aff) and (right_aff or right_act):
            chosen = (left, m.group(), right)
    if chosen is None:
        return None
    return chosen


def evidence_level(left_feats, has_reason, has_eval, has_behavior) -> str:
    if has_reason and (left_feats or has_eval or has_behavior):
        return "직접 이유"
    if left_feats and has_eval:
        return "특징을 지목해 평가했으나 이유는 설명하지 않음"
    if has_eval or has_behavior:
        return "언급 또는 행동만"
    return ""


def classify_post(row) -> tuple[dict, list]:
    raw = row["text"]
    text = analysis_text(raw)
    lang = language_of(raw)
    target_ok = lang in {"한국어 중심", "한국어 중심 혼합"}
    spans = gate_mentions(text, find_spans(text))
    confirmed = [s for s in spans if s["status"] == "확정"]
    unconfirmed = [s for s in spans if s["status"] == "문맥확인필요"]
    excluded = [s for s in spans if s["status"] == "제외_다른대상"]
    work_title = bool(WORK_TITLE_RE.search(text))
    clauses = split_clauses(text)
    evidences = []
    post_promo = bool(PROMO_RE.search(text)) and not PERSONAL_GET_RE.search(text) and not re.search(
        r"개인적으로|내가\s*샀|저는\s*샀", text
    )

    # map mentions into clauses
    def names_in(cl):
        found = []
        roles = []
        for s in confirmed:
            if s["end"] > cl["start"] and s["start"] < cl["end"]:
                if s["name"] == "치이카와":
                    role = chiikawa_role(cl["text"])
                    roles.append(role)
                    found.append("치이카와")
                else:
                    found.append(s["name"])
        return list(dict.fromkeys(found)), list(dict.fromkeys(roles))

    post_roles = []
    for s in confirmed:
        if s["name"] == "치이카와":
            # role using a window around the span
            window = text[max(0, s["start"] - 10) : s["end"] + 24]
            post_roles.append(chiikawa_role(window) or "불명확")
    post_roles = list(dict.fromkeys(post_roles))

    review = []
    if unconfirmed:
        review.append("애매한_이름")
    if excluded:
        review.append("다른대상_제외")
    if EVAL_NEG_RE.search(text) or re.search(r"안\s*귀엽|별로", text):
        review.append("부정·반어")
    confirmed_names = list(dict.fromkeys(s["name"] for s in confirmed))
    if len(confirmed_names) >= 2 and (EVAL_POS_RE.search(text) or FUNNY_RE.search(text)):
        review.append("여러_캐릭터")
    if PROMO_RE.search(text) and (PERSONAL_GET_RE.search(text) or (EVAL_POS_RE.search(text) and re.search(r"내가|저는|저 |샀|좋아", text))):
        review.append("홍보와_개인_공존")
    elif PROMO_RE.search(text) and TRADE_RE.search(text):
        review.append("홍보와_거래_공존")
    if ATTACH_RE.search(text) and not confirmed_names and (EVAL_POS_RE.search(text) or FUNNY_RE.search(text)):
        review.append("첨부_확인_필요")

    for i, cl in enumerate(clauses):
        ctext = cl["text"]
        names, roles = names_in(cl)
        spk = speaker_of(ctext, post_promo)
        feats = features_in(ctext)
        # product material should not also count as character appearance
        if PRODUCT_RE.search(ctext) and "상품의 디자인·소재·쓰임" in feats:
            feats = [f for f in feats if f != "외형·표정" or re.search(r"표정|얼굴|볼", ctext)]
        emo = emotion_of(ctext)
        beh = behaviors_of(ctext)
        # promo voice: strip author emotion
        if spk == "홍보문구":
            emo_author = ""
        else:
            emo_author = emo
        reason = reason_parts(ctext) if spk == "작성자" else None
        reason_left_feats = features_in(reason[0]) if reason else []
        if reason and PRODUCT_RE.search(ctext) and "상품의 디자인·소재·쓰임" in reason_left_feats:
            pass
        has_eval = bool(emo_author) and emo_author != "질문·정보·중립"
        has_beh = bool(beh)
        # scene action alone is a behavior but not an evaluation
        level = ""
        if reason and (has_eval or has_beh):
            level = "직접 이유"
            if reason_left_feats:
                feats = list(dict.fromkeys(reason_left_feats + feats))
        elif feats and has_eval:
            level = "특징을 지목해 평가했으나 이유는 설명하지 않음"
        elif has_eval or has_beh:
            level = "언급 또는 행동만"
        if not level:
            continue
        # generic affection if eval and no feature
        appeal_list = list(feats)
        if has_eval and not appeal_list:
            appeal_list = ["구체적 이유 없는 호감"]
        if not appeal_list and has_beh:
            appeal_list = ["기타·불명확"]
        target, who = assign_target(ctext, names, feats)
        # if reason explains behavior, record that
        explains = ""
        if reason:
            right = reason[2]
            rb = behaviors_of(right)
            re_emo = emotion_of(right)
            if rb:
                explains = "행동:" + "|".join(rb)
            elif re_emo:
                explains = "감정:" + re_emo
            else:
                explains = "판단 불가"
        # do not treat scene-only rows as author emotion
        if emo_author == "" and beh == ["장면·대사 인용"]:
            emo_out = "판단 불가"
            if "구체적 이유 없는 호감" in appeal_list:
                appeal_list = ["기타·불명확"]
        else:
            emo_out = emo_author or ("질문·정보·중립" if spk == "작성자" and not emo_author else "")
        if spk == "홍보문구":
            emo_out = "질문·정보·중립"
            level = "언급 또는 행동만"
            appeal_list = ["기타·불명확"] if not feats else feats
            explains = ""
        quote = norm(ctext)[:180]
        src = "작성자 본문"
        if spk == "번역문":
            src = "작성자 본문"
        if "첨부_확인_필요" in review and target == "불명확" and not who:
            src = "확인 불가"
        link_basis = "같은 구절"
        evidences.append(
            {
                "post_id": row["post_id"],
                "character": who,
                "reaction_target": target,
                "appeal": "|".join(appeal_list),
                "emotion": emo_out,
                "behavior": "|".join(beh) if beh else "행동 표현 없음",
                "reason_explains": explains,
                "evidence_quote": quote,
                "evidence_source": src,
                "speaker": spk,
                "evidence_level": level,
                "link_basis": link_basis,
                "clause_index": i,
                "chiikawa_role_in_clause": "|".join(roles),
                "analysis_target": "예" if target_ok else "아니오",
            }
        )

    # adjacent link: previous clause has exactly one confirmed non-goods character, this clause has eval and no name
    if target_ok:
        for i, cl in enumerate(clauses):
            if i == 0:
                continue
            prev = clauses[i - 1]
            prev_names, _ = names_in(prev)
            cur_names, _ = names_in(cl)
            if cur_names or len(prev_names) != 1:
                continue
            if speaker_of(cl["text"], post_promo) != "작성자" or speaker_of(prev["text"], post_promo) != "작성자":
                continue
            emo = emotion_of(cl["text"])
            if not emo or emo == "질문·정보·중립":
                continue
            who = prev_names[0]
            if who == "치이카와":
                role_prev = chiikawa_role(prev["text"])
                if role_prev == "주인공":
                    target_name = "특정 캐릭터"
                    who_out = "치이카와"
                elif role_prev == "작품":
                    target_name = "작품·스토리·세계관"
                    who_out = ""
                else:
                    target_name = "불명확"
                    who_out = "치이카와"
            else:
                target_name = "특정 캐릭터"
                who_out = who
            existing = [e for e in evidences if e["clause_index"] == i and e["speaker"] == "작성자" and e["character"] == ""]
            if existing:
                for e in existing:
                    e["character"] = who_out
                    e["reaction_target"] = target_name
                    e["link_basis"] = "인접 문장"
                    if who == "치이카와":
                        e["chiikawa_role_in_clause"] = chiikawa_role(prev["text"])
                continue
            feats = features_in(cl["text"]) or features_in(prev["text"])
            appeal = "|".join(feats) if feats else "구체적 이유 없는 호감"
            level = "특징을 지목해 평가했으나 이유는 설명하지 않음" if feats else "언급 또는 행동만"
            evidences.append(
                {
                    "post_id": row["post_id"],
                    "character": who_out,
                    "reaction_target": target_name,
                    "appeal": appeal,
                    "emotion": emo,
                    "behavior": "행동 표현 없음",
                    "reason_explains": "",
                    "evidence_quote": norm(prev["text"])[:80] + " / " + norm(cl["text"])[:80],
                    "evidence_source": "작성자 본문",
                    "speaker": "작성자",
                    "evidence_level": level,
                    "link_basis": "인접 문장",
                    "clause_index": i,
                    "chiikawa_role_in_clause": chiikawa_role(prev["text"]) if who == "치이카와" else "",
                    "analysis_target": "예",
                }
            )

    author_ev = [e for e in evidences if e["speaker"] == "작성자" and e["analysis_target"] == "예"]
    author_eval = any(
        e["emotion"] not in {"", "질문·정보·중립", "판단 불가"} or (
            e["evidence_level"].startswith("특징") or e["evidence_level"] == "직접 이유"
        )
        for e in author_ev
        if e["reaction_target"] in {"특정 캐릭터", "불명확", "캐릭터 간 관계", "작품·스토리·세계관", "굿즈", "팬아트·번역·편집·창작자"}
        and e["emotion"] not in {"", "질문·정보·중립", "판단 불가"}
    )
    # name only: confirmed name or work title, no author emotion, inside analysis target
    has_name = bool(confirmed_names) or work_title
    author_emotion_any = any(e["emotion"] not in {"", "질문·정보·중립", "판단 불가"} for e in author_ev)
    name_only = "예" if target_ok and has_name and not author_emotion_any else "아니오"

    purposes = []
    if author_emotion_any:
        purposes.append("개인 감상")
    if any(e["behavior"] not in {"", "행동 표현 없음", "장면·대사 인용"} and e["speaker"] == "작성자" for e in evidences):
        purposes.append("개인 경험")
    if PROMO_RE.search(text):
        purposes.append("판매·홍보")
    if TRADE_RE.search(text):
        purposes.append("개인 거래")
    if TRANSLATE_RE.search(text) or CREATE_RE.search(text):
        purposes.append("팬 창작")
    if re.search(r"안내|소식|공개|출시", text) and "판매·홍보" not in purposes:
        purposes.append("정보 공유")
    if not purposes:
        purposes.append("기타·판단 불가")

    if "치이카와" in confirmed_names and "불명확" in post_roles and author_emotion_any:
        review.append("치이카와_역할_불명확_평가")

    keywords = row.get("keywords", "")
    post = {
        "post_id": row["post_id"],
        "post_url": row["post_url"],
        "account_id": row["account_id"],
        "created_at": row["created_at"],
        "created_year": row["created_at"][:4],
        "language": lang,
        "analysis_target": "예" if target_ok else "아니오",
        "text": raw,
        "characters_confirmed": "|".join(confirmed_names),
        "characters_unconfirmed": "|".join(dict.fromkeys(s["name"] for s in unconfirmed)),
        "chiikawa_roles": "|".join(post_roles),
        "work_title_mentioned": "예" if work_title else "아니오",
        "name_only": name_only,
        "author_evaluated": "예" if author_eval else "아니오",
        "purposes": "|".join(purposes),
        "review_flags": "|".join(dict.fromkeys(review)),
        "review_status": "검토 필요" if review else "자동",
        "n_evidence": len(evidences),
        "view_count": row["view_count"],
        "view_missing": "예" if row["view_count"] == "" else "아니오",
        "like_count": row["like_count"],
        "repost_count": row["repost_count"],
        "comment_count": row["comment_count"],
        "keywords": keywords,
        "codebook_version": VERSION,
        "method": "자동 규칙",
    }
    return post, evidences


def load_inputs():
    posts = pd.read_csv(NORM / "x_posts.csv", dtype=str, keep_default_na=False)
    kw = pd.read_csv(NORM / "x_post_keywords.csv", dtype=str, keep_default_na=False)
    src = pd.read_csv(NORM / "x_post_sources.csv", dtype=str, keep_default_na=False)
    agg = (
        kw.sort_values(["post_id", "keyword_order"])
        .groupby("post_id")["keyword"]
        .agg(lambda s: "|".join(s))
        .rename("keywords")
    )
    posts = posts.merge(agg, on="post_id", how="left")
    posts["keywords"] = posts["keywords"].fillna("")
    files = pd.read_csv(NORM / "x_source_files.csv", dtype=str, keep_default_na=False)
    src = src.merge(files, on="source_file", how="left")
    posts = posts.merge(src[["post_id", "source_file", "source_year"]], on="post_id", how="left")
    return posts, kw


def main():
    posts, kw = load_inputs()
    assert len(posts) == 5000
    assert posts["post_id"].nunique() == 5000
    assert len(kw) == 7466

    post_rows = []
    ev_rows = []
    for rec in posts.to_dict("records"):
        post, evs = classify_post(rec)
        post_rows.append(post)
        ev_rows.extend(evs)

    # apply overrides if present
    ov_path = WORK / "overrides.jsonl"
    n_override = 0
    if ov_path.exists():
        overs = []
        for line in ov_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                overs.append(json.loads(line))
        by_post = defaultdict(list)
        for o in overs:
            by_post[o["post_id"]].append(o)
        new_ev = [e for e in ev_rows if e["post_id"] not in by_post]
        for pid, items in by_post.items():
            n_override += 1
            for o in items:
                o.setdefault("speaker", "작성자")
                o.setdefault("evidence_source", "작성자 본문")
                o.setdefault("link_basis", "모델 문맥 수정")
                o.setdefault("analysis_target", "예")
                o.setdefault("clause_index", -1)
                o.setdefault("chiikawa_role_in_clause", "")
                o["method_note"] = "모델 문맥 수정"
                new_ev.append(o)
        ev_rows = new_ev
        for p in post_rows:
            if p["post_id"] in by_post:
                p["method"] = "자동 규칙+모델 문맥 수정"
                p["review_status"] = "모델 검토"

    for i, e in enumerate(ev_rows, 1):
        e["evidence_id"] = f"E{i:05d}"
        e["codebook_version"] = VERSION

    post_df = pd.DataFrame(post_rows)
    ev_df = pd.DataFrame(ev_rows)

    # quote substring check
    text_map = dict(zip(post_df.post_id, post_df.text.map(lambda t: norm(analysis_text(t)))))
    bad_quote = 0
    for e in ev_rows:
        q = e["evidence_quote"].split(" / ")[0]
        if q and q[:40] not in text_map.get(e["post_id"], "") and norm(q)[:40] not in text_map.get(e["post_id"], ""):
            bad_quote += 1

    post_df.to_csv(OUT / "post_reaction_analysis.csv", index=False, encoding="utf-8-sig")
    ev_df.to_csv(OUT / "reaction_evidence.csv", index=False, encoding="utf-8-sig")

    target = post_df[post_df.analysis_target == "예"].copy()
    # scope
    scope = pd.DataFrame(
        [
            {"item": "입력 게시물", "n": len(post_df)},
            {"item": "고유 post_id", "n": post_df.post_id.nunique()},
            {"item": "고유 계정", "n": post_df.account_id.nunique()},
            {"item": "키워드 연결 행", "n": len(kw)},
            {"item": "키워드가 가리키는 고유 게시물", "n": kw.post_id.nunique()},
            {"item": "분석 대상 한국어 중심", "n": int((post_df.language == "한국어 중심").sum())},
            {"item": "분석 대상 한국어 중심 혼합", "n": int((post_df.language == "한국어 중심 혼합").sum())},
            {"item": "분석 대상 합계", "n": int(len(target))},
            {"item": "다른 언어 중심 제외", "n": int((post_df.language == "다른 언어 중심").sum())},
            {"item": "언어 판단 불가 제외", "n": int((post_df.language == "판단 불가").sum())},
            {"item": "조회수 결측", "n": int((post_df.view_missing == "예").sum())},
            {"item": "이름만 있는 글(분석 대상)", "n": int((target.name_only == "예").sum())},
            {"item": "작성자 평가 있음(분석 대상)", "n": int((target.author_evaluated == "예").sum())},
            {"item": "검토 필요", "n": int((post_df.review_status == "검토 필요").sum())},
            {"item": "근거 행", "n": len(ev_df)},
            {"item": "근거 인용 불일치", "n": bad_quote},
            {"item": "모델 수정 게시물", "n": n_override},
        ]
    )
    scope.to_csv(TABLES / "01_scope.csv", index=False, encoding="utf-8-sig")

    lang_year = pd.crosstab(post_df.created_year, post_df.language)
    lang_year.to_csv(TABLES / "02_language_by_year.csv", encoding="utf-8-sig")

    view_year = (
        post_df.groupby("created_year")
        .apply(lambda g: pd.Series({
            "posts": len(g),
            "view_missing": int((g.view_missing == "예").sum()),
            "view_present": int((g.view_missing == "아니오").sum()),
        }), include_groups=False)
        .reset_index()
    )
    view_year.to_csv(TABLES / "03_view_missing_by_year.csv", index=False, encoding="utf-8-sig")

    # keyword vs body
    body_pat = {
        "치이카와": r"치이카와|치이까와|치카와|치까와|ちいかわ|chiikawa|吉伊卡哇",
        "하치와레": r"하치와레|하치와래|ハチワレ|hachiware|뿔치와레",
        "먼작귀": r"먼작귀",
        "랏코": r"랏코|락코|ラッコ",
        "우사기": r"우사기|うさぎ|ウサギ",
        "모몽가": r"모몽가|모몬가",
        "쿠리만쥬": r"쿠리만쥬|쿠리만주",
        "시사": r"시사|シーサー",
        "갑옷씨": r"갑옷\s*씨|갑옷\s*아저씨|갑옷상",
        "카니": r"카니|カニ",
        "데카츠요": r"데카츠요",
        "아노코": r"아노코",
        "파자마 파티즈": r"파자마\s*파티즈",
    }
    merged = posts.merge(post_df[["post_id", "analysis_text"]] if "analysis_text" in post_df.columns else post_df[["post_id"]], on="post_id", how="left")
    # rebuild analysis text
    analysis_map = {r["post_id"]: analysis_text(r["text"]) for r in posts.to_dict("records")}
    kw_rows = []
    kw_small = kw.copy()
    kw_small["body"] = kw_small.post_id.map(analysis_map)
    for keyword, pat in body_pat.items():
        sub = kw_small[kw_small.keyword == keyword]
        hit = sub.body.str.contains(pat, regex=True, case=False)
        kw_rows.append({
            "keyword": keyword,
            "keyword_links": int(len(sub)),
            "unique_posts": int(sub.post_id.nunique()),
            "body_has_surface": int(hit.sum()),
            "body_without_surface": int((~hit).sum()),
        })
    pd.DataFrame(kw_rows).to_csv(TABLES / "04_keyword_vs_body.csv", index=False, encoding="utf-8-sig")

    # mentions inside analysis target
    mention_rows = []
    t = target
    def posts_with(char):
        return t[t.characters_confirmed.str.split("|").apply(lambda xs: char in xs if isinstance(xs, list) else False)]

    chars = ["치이카와", "하치와레", "우사기", "모몽가", "랏코", "쿠리만쥬", "시사", "카니", "갑옷씨", "아노코", "데카츠요", "오데", "고블린", "키메라", "풍뎅이", "스핑크스"]
    for char in chars:
        sub = posts_with(char)
        if char == "치이카와":
            for role, mask in [
                ("치이카와·주인공", sub.chiikawa_roles.str.contains("주인공")),
                ("치이카와·작품", sub.chiikawa_roles.str.contains("작품")),
                ("치이카와·불명확", sub.chiikawa_roles.str.contains("불명확")),
                ("치이카와·이름출현", pd.Series(True, index=sub.index)),
            ]:
                ss = sub[mask]
                mention_rows.append(mention_record(role, ss))
        else:
            mention_rows.append(mention_record(char, sub))
    # work title
    wt = t[t.work_title_mentioned == "예"]
    mention_rows.append(mention_record("작품명·먼작귀", wt))
    men_df = pd.DataFrame(mention_rows)
    men_df.to_csv(TABLES / "05_character_mentions.csv", index=False, encoding="utf-8-sig")

    # author evidence inside target
    author = ev_df[(ev_df.speaker == "작성자") & (ev_df.analysis_target == "예")].copy()
    directed = author[(author.reaction_target == "특정 캐릭터") & (author.character != "")]
    # evaluation = emotion is affective or evidence level is feature/reason
    affective = {"호감", "웃음·재미", "위로", "공감", "응원·보호 욕구", "비호감·불편", "혼합"}

    def is_eval_row(r):
        emos = set(str(r.emotion).split("|"))
        return bool(emos & affective) or str(r.evidence_level).startswith("직접") or str(r.evidence_level).startswith("특징")

    directed = directed[directed.apply(is_eval_row, axis=1)]
    # denominator per character: unique posts
    appeal_labels = [
        "외형·표정",
        "목소리·말투",
        "성격",
        "행동·움직임",
        "관계",
        "이야기·설정",
        "상품의 디자인·소재·쓰임",
        "구체적 이유 없는 호감",
        "기타·불명확",
    ]
    char_eval_posts = directed.groupby("character").post_id.nunique().to_dict()
    heat_rows = []
    for char, n_den in sorted(char_eval_posts.items(), key=lambda kv: -kv[1]):
        sub = directed[directed.character == char]
        den = sub.post_id.nunique()
        accounts = t[t.post_id.isin(sub.post_id)].account_id.nunique()
        row = {"character": char, "eval_posts": den, "eval_accounts": int(accounts)}
        for lab in appeal_labels:
            ids = sub[sub.appeal.str.contains(lab, regex=False)].post_id.nunique()
            row[lab] = int(ids)
        # emotions
        for emo in ["호감", "웃음·재미", "위로", "공감", "응원·보호 욕구", "비호감·불편", "혼합"]:
            row["감정_" + emo] = int(sub[sub.emotion.str.contains(emo, regex=False)].post_id.nunique())
        row["직접이유"] = int(sub[sub.evidence_level == "직접 이유"].post_id.nunique())
        row["특징지목"] = int(sub[sub.evidence_level.str.startswith("특징")].post_id.nunique())
        row["이유없음포함_분모"] = den
        heat_rows.append(row)
    heat = pd.DataFrame(heat_rows)
    heat.to_csv(TABLES / "06_character_appeal.csv", index=False, encoding="utf-8-sig")

    # behaviors linked
    beh_labels = [
        "장면·대사 인용",
        "번역·팬 창작",
        "추천·공유 의향",
        "구매·소장 희망",
        "구매·획득 경험",
        "사용·휴대·전시·보관 경험",
        "방문 희망·경험",
        "미구매",
    ]
    beh_rows = []
    for char, sub0 in author[author.character != ""].groupby("character"):
        for target_name, sub in [("특정 캐릭터", sub0[sub0.reaction_target == "특정 캐릭터"]), ("굿즈", sub0[sub0.reaction_target == "굿즈"])]:
            if sub.empty:
                continue
            rec = {"character": char, "reaction_target": target_name, "posts": int(sub.post_id.nunique())}
            for b in beh_labels:
                rec[b] = int(sub[sub.behavior.str.contains(b, regex=False)].post_id.nunique())
            beh_rows.append(rec)
    pd.DataFrame(beh_rows).to_csv(TABLES / "07_character_behavior.csv", index=False, encoding="utf-8-sig")

    # non-character targets
    nontarget_rows = []
    for tgt, sub in author.groupby("reaction_target"):
        nontarget_rows.append({
            "reaction_target": tgt,
            "posts": int(sub.post_id.nunique()),
            "accounts": int(t[t.post_id.isin(sub.post_id)].account_id.nunique()),
            "direct_reason_posts": int(sub[sub.evidence_level == "직접 이유"].post_id.nunique()),
        })
    pd.DataFrame(nontarget_rows).to_csv(TABLES / "08_reaction_targets.csv", index=False, encoding="utf-8-sig")

    # account concentration for directed evals and for direct reasons
    conc_rows = []
    subsets = {
        "캐릭터_평가": directed,
        "직접이유_캐릭터": directed[directed.evidence_level == "직접 이유"],
        "특징지목_캐릭터": directed[directed.evidence_level.str.startswith("특징")],
        "포괄호감_캐릭터": directed[directed.appeal.str.contains("구체적 이유 없는 호감", regex=False)],
    }
    for label, sub in subsets.items():
        if sub.empty:
            continue
        ids = set(sub.post_id)
        acc = t[t.post_id.isin(ids)].groupby("account_id").size().sort_values(ascending=False)
        top_n = int(acc.iloc[0]) if len(acc) else 0
        top_id = acc.index[0] if len(acc) else ""
        # remove top account
        remain_posts = t[(t.post_id.isin(ids)) & (t.account_id != top_id)]
        conc_rows.append({
            "subset": label,
            "posts": len(ids),
            "accounts": int(acc.shape[0]),
            "top_account": top_id,
            "top_account_posts": top_n,
            "top_share": round(top_n / len(ids), 3) if ids else None,
            "posts_without_top_account": int(remain_posts.post_id.nunique()),
        })
    pd.DataFrame(conc_rows).to_csv(TABLES / "09_account_concentration.csv", index=False, encoding="utf-8-sig")

    # per character top account for direct reasons
    sens = []
    for char, sub in directed[directed.evidence_level == "직접 이유"].groupby("character"):
        ids = set(sub.post_id)
        acc = t[t.post_id.isin(ids)].groupby("account_id").size().sort_values(ascending=False)
        if acc.empty:
            continue
        sens.append({
            "character": char,
            "direct_posts": len(ids),
            "accounts": int(acc.shape[0]),
            "top_account": acc.index[0],
            "top_posts": int(acc.iloc[0]),
            "without_top": int(len(ids) - acc.iloc[0]),
        })
    pd.DataFrame(sens).to_csv(TABLES / "10_direct_reason_concentration.csv", index=False, encoding="utf-8-sig")

    # alias audit on all posts, not only target
    alias_rows = []
    all_text = {r["post_id"]: analysis_text(r["text"]) for r in posts.to_dict("records")}
    for label, rx in ALIAS_RE.items():
        ids = [pid for pid, tx in all_text.items() if rx.search(tx)]
        alias_rows.append({"alias": label, "posts_all": len(ids)})
    # 가르마 without 하치와레
    gar = [pid for pid, tx in all_text.items() if "가르마" in tx]
    gar_full = [pid for pid in gar if re.search(r"하치와레|하치와래", all_text[pid])]
    gar_gloss = [pid for pid in gar if re.search(r"가르마\s*[\(（]\s*하치와레", all_text[pid])]
    tok = [pid for pid, tx in all_text.items() if re.search(r"(?<![가-힣])토끼(?![가-힣])", tx)]
    tok_gloss = [pid for pid in tok if re.search(r"토끼\s*[\(（]\s*우사기", all_text[pid])]
    alias_extra = pd.DataFrame([
        {"item": "가르마 출현", "n": len(gar)},
        {"item": "가르마와 하치와레가 같은 글", "n": len(gar_full)},
        {"item": "가르마(하치와레) 괄호", "n": len(gar_gloss)},
        {"item": "가르마만 있고 하치와레 없음", "n": len(gar) - len(gar_full)},
        {"item": "토끼 단독 출현", "n": len(tok)},
        {"item": "토끼(우사기) 괄호", "n": len(tok_gloss)},
        {"item": "락코 표기", "n": sum(1 for tx in all_text.values() if "락코" in tx)},
        {"item": "라코 단독", "n": sum(1 for tx in all_text.values() if re.search(r"(?<![가-힣])라코(?![가-힣])", tx))},
    ])
    alias_extra.to_csv(TABLES / "11_alias_audit.csv", index=False, encoding="utf-8-sig")

    # evidence level counts on author + target
    lvl = author.groupby("evidence_level").post_id.nunique().rename("posts").reset_index()
    lvl.to_csv(TABLES / "12_evidence_levels.csv", index=False, encoding="utf-8-sig")

    # review flags
    flags = []
    for flag in ["애매한_이름", "다른대상_제외", "부정·반어", "여러_캐릭터", "홍보와_개인_공존", "홍보와_거래_공존", "첨부_확인_필요", "치이카와_역할_불명확_평가"]:
        flags.append({"flag": flag, "posts": int(post_df.review_flags.str.contains(flag, regex=False).sum())})
    pd.DataFrame(flags).to_csv(TABLES / "13_review_flags.csv", index=False, encoding="utf-8-sig")

    review_df = post_df[post_df.review_flags != ""][
        ["post_id", "post_url", "account_id", "created_year", "language", "analysis_target", "characters_confirmed", "characters_unconfirmed", "chiikawa_roles", "review_flags", "text"]
    ]
    review_df.to_csv(OUT / "review_required.csv", index=False, encoding="utf-8-sig")
    name_only_df = target[target.name_only == "예"][
        ["post_id", "post_url", "account_id", "created_year", "characters_confirmed", "work_title_mentioned", "chiikawa_roles", "text"]
    ]
    name_only_df.to_csv(OUT / "name_only_posts.csv", index=False, encoding="utf-8-sig")

    # direct reason markdown for model review
    direct = author[author.evidence_level == "직접 이유"]
    lines = ["# 직접 이유 후보", "", f"근거 행 {len(direct)} / 게시물 {direct.post_id.nunique()}", ""]
    for _, r in direct.sort_values(["character", "post_id"]).iterrows():
        lines.append(
            f"## {r.post_id} | {r.character} | {r.reaction_target} | {r.appeal} | {r.emotion} | {r.behavior} | {r.reason_explains} | {r.link_basis}"
        )
        lines.append(r.evidence_quote)
        lines.append("")
    (WORK / "direct_reasons.md").write_text("\n".join(lines), encoding="utf-8")

    feat = author[author.evidence_level.str.startswith("특징")]
    flines = ["# 특징 지목 후보", "", f"근거 행 {len(feat)} / 게시물 {feat.post_id.nunique()}", ""]
    for _, r in feat.sort_values(["character", "post_id"]).iterrows():
        flines.append(f"## {r.post_id} | {r.character} | {r.reaction_target} | {r.appeal} | {r.emotion} | {r.behavior}")
        flines.append(r.evidence_quote)
        flines.append("")
    (WORK / "feature_points.md").write_text("\n".join(flines), encoding="utf-8")

    # holdout
    dev_text = (WORK / "dev_sample.md").read_text(encoding="utf-8") if (WORK / "dev_sample.md").exists() else ""
    dev_ids = set(re.findall(r"## \S+ \| (\d+) \|", dev_text))
    hold_pool = target[~target.post_id.isin(dev_ids)].copy()
    rng = hold_pool.sample(frac=1, random_state=20261107)
    picked = []
    seen = set()

    def take_ids(idset, n, bucket):
        sub = rng[rng.post_id.isin(idset) & ~rng.post_id.isin(seen)]
        for _, r in sub.head(n).iterrows():
            picked.append((bucket, r))
            seen.add(r.post_id)

    take_ids(set(direct.post_id) - dev_ids, 12, "holdout_direct")
    take_ids(set(feat.post_id) - dev_ids, 12, "holdout_feature")
    take_ids(set(post_df[post_df.review_flags.str.contains("부정", regex=False)].post_id) - dev_ids, 8, "holdout_neg")
    take_ids(set(post_df[post_df.review_flags.str.contains("여러_캐릭터", regex=False)].post_id) - dev_ids, 8, "holdout_multi")
    take_ids(set(post_df[post_df.purposes.str.contains("판매·홍보", regex=False)].post_id) - dev_ids, 8, "holdout_promo")
    take_ids(set(name_only_df.post_id) - dev_ids, 8, "holdout_name_only")
    ev_by = ev_df.groupby("post_id")
    hlines = ["# 최종 점검 표본", "", "규칙 작성 표본과 post_id가 겹치지 않는다.", ""]
    for bucket, r in picked:
        hlines.append(f"## {bucket} | {r.post_id} | {r.created_year} | {r.language} | {r.account_id}")
        hlines.append(r.text)
        hlines.append("")
        hlines.append(f"예측 캐릭터: {r.characters_confirmed} / 치이카와역할: {r.chiikawa_roles} / 이름만: {r.name_only} / 평가: {r.author_evaluated}")
        if r.post_id in ev_by.groups:
            for _, e in ev_by.get_group(r.post_id).iterrows():
                hlines.append(
                    f"- {e.speaker} | {e.character} | {e.reaction_target} | {e.appeal} | {e.emotion} | {e.behavior} | {e.evidence_level} | {e.reason_explains} | {e.evidence_quote[:120]}"
                )
        hlines.append("")
    (WORK / "holdout_review.md").write_text("\n".join(hlines), encoding="utf-8")

    # assertions from the development read
    checks = []
    def has(pid, **kwargs):
        sub = ev_df[ev_df.post_id == pid]
        ok = False
        for _, e in sub.iterrows():
            good = True
            for k, v in kwargs.items():
                if v not in str(e[k]):
                    good = False
            if good:
                ok = True
        checks.append({"post_id": pid, "expect": str(kwargs), "ok": ok, "got": " || ".join(
            f"{e.character}/{e.reaction_target}/{e.appeal}/{e.emotion}/{e.evidence_level}/{e.speaker}" for _, e in sub.iterrows()
        )[:400]})

    has("2084989276413173925", character="시사", appeal="성격", evidence_level="직접 이유")
    has("2090450515369046251", character="랏코", appeal="외형·표정")
    has("1826582742358000121", character="랏코", appeal="목소리·말투")
    has("2075604262890225925", character="하치와레", evidence_level="직접 이유")
    has("1524898592640491520", reaction_target="작품")
    has("1581247470121910272", speaker="홍보문구")
    has("1645055492832788480", behavior="번역")
    # dialogue should not be author affection
    sub = ev_df[(ev_df.post_id == "1555064410321952770") & (ev_df.speaker == "작성자") & (ev_df.emotion.str.contains("호감"))]
    checks.append({"post_id": "1555064410321952770", "expect": "no author 호감", "ok": sub.empty, "got": str(len(sub))})
    # shop cute is not author
    sub = ev_df[(ev_df.post_id == "1697574938700652650") & (ev_df.speaker == "작성자") & (ev_df.emotion.str.contains("호감"))]
    checks.append({"post_id": "1697574938700652650", "expect": "promo not author love", "ok": sub.empty, "got": str(len(sub))})
    pd.DataFrame(checks).to_csv(WORK / "assertion_check.csv", index=False, encoding="utf-8-sig")

    summary = {
        "version": VERSION,
        "posts": len(post_df),
        "evidence_rows": len(ev_df),
        "analysis_target": int(len(target)),
        "bad_quotes": bad_quote,
        "overrides": n_override,
        "direct_posts": int(direct.post_id.nunique()),
        "feature_posts": int(feat.post_id.nunique()),
        "assertions_failed": int(sum(1 for c in checks if not c["ok"])),
        "dev_sample_posts": len(dev_ids),
        "holdout_posts": len(picked),
    }
    (WORK / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(pd.DataFrame(checks)[["post_id", "ok"]].to_string(index=False))
    print("mentions")
    print(men_df[["character", "posts", "accounts", "name_only_posts", "author_eval_posts"]].to_string(index=False))


def mention_record(name, ss: pd.DataFrame) -> dict:
    if ss.empty:
        return {"character": name, "posts": 0, "accounts": 0, "name_only_posts": 0, "author_eval_posts": 0}
    return {
        "character": name,
        "posts": int(ss.post_id.nunique()),
        "accounts": int(ss.account_id.nunique()),
        "name_only_posts": int((ss.name_only == "예").sum()),
        "author_eval_posts": int((ss.author_evaluated == "예").sum()),
    }


if __name__ == "__main__":
    main()
