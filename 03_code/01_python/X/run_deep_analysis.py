# -*- coding: utf-8 -*-
"""치이카와 X 게시물 심층 재분석.

게시물 1건이 분석 단위다. 검색 키워드 행으로 반응이나 게시물 수를 세지 않는다.
라벨은 문장·구절 규칙으로 붙인다. 단어가 있다는 사실만으로 호감의 측면,
구매 이유, 장벽을 확정하지 않는다.

판정 주체:
- rule_context: 이 스크립트의 구절 규칙. 5,000건 전체에 동일하게 적용한다.
- 규칙 설계와 검증 후 수정은 분석 코드북의 변경 이력에 적는다.
- 게시물마다 사람이 라벨을 고친 값은 없다.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from kiwipiepy import Kiwi

CODE_DIR = Path(r"C:\DATA\KDT_Integral_Data_Project\03_code\01_python")
sys.path.insert(0, str(CODE_DIR))
import normalize_x_tables as nz  # noqa: E402

BASE = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
NORM = BASE / "normalized"
OUT = BASE / "text_analysis_deep"
DOCS = OUT / "docs"
TABLES = OUT / "output"
AGG = TABLES / "agg"
WORK = OUT / "work"
SEOUL = ZoneInfo("Asia/Seoul")
CODEBOOK_VERSION = "2026-10-30.4"
DECISION_METHOD = "rule_context"

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@[0-9A-Za-z_]+")
PPANCHU_RE = re.compile(r"빤쮸\s*(?:우사기|토끼)")
PAJAMA_WORK_RE = re.compile(r"파자마\s*파티즈")
WS_RE = re.compile(r"\s+")

NONE = "언급 없음"
NA = "해당없음"
UNCLEAR_ASPECT = "구체적 대상 확인 불가"
ASPECT_LOOK = "캐릭터 외형"
ASPECT_ACT = "행동·성격"
ASPECT_REL = "관계성·이야기"
ASPECT_GOODS = "상품 디자인·구현"
ASPECT_OTHER = "기타 구체적 대상"

LEVEL_POST = "게시글 내 공존"
LEVEL_CLAUSE = "문장·구절 내 연결"
LEVEL_REASON = "명시적 이유 설명"

CTX_REACT = "개인 감상·반응"
CTX_OWN = "개인 구매·사용·소장 경험"
CTX_SHOP = "판매·입고·출시·이벤트 안내"
CTX_SELL = "개인 판매·교환"
CTX_INFO = "정보 공유·인용·재전달"
CTX_MIX = "혼합"
CTX_UNK = "판단 불가"


def blank_mask(pattern: re.Pattern[str], text: str) -> str:
    return pattern.sub(lambda match: " " * len(match.group()), text)


def prepare(raw: str) -> tuple[str, str, str]:
    """원문 줄바꿈만 LF로 맞춘 문자열, 읽기용 분석 텍스트, 검색용 텍스트.

    검색용 텍스트는 URL·멘션·보호 표현을 같은 길이의 공백으로 가려
    오프셋이 원문 LF 문자열과 같다. 이모지, 반복, 부정은 지우지 않는다.
    """
    original = str(raw).replace("\r\n", "\n").replace("\r", "\n")
    masked = blank_mask(URL_RE, original)
    masked = blank_mask(MENTION_RE, masked)
    masked = masked.replace("#", " ")
    search = blank_mask(PPANCHU_RE, masked)
    search = blank_mask(PAJAMA_WORK_RE, search)
    readable = URL_RE.sub(" ", original)
    readable = MENTION_RE.sub(" ", readable)
    readable = readable.replace("#", " ")
    readable = re.sub(r"[ \t]+", " ", readable)
    readable = re.sub(r" *\n *", "\n", readable).strip()
    return original, readable, search


def split_spans(text: str, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in pattern.finditer(text):
        if text[start : match.start()].strip():
            spans.append((start, match.start()))
        start = match.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    if not spans and text.strip():
        spans.append((0, len(text)))
    return spans


SENT_SPLIT_RE = re.compile(r"\n+|(?<=[\.!?。！？])\s+")
CLAUSE_SPLIT_RE = re.compile(r"\n+|(?<=[\.!?。！？])\s+|(?<=[,，])\s+")


def locate(spans: list[tuple[int, int]], pos: int) -> int | None:
    for index, (start, end) in enumerate(spans):
        if start <= pos < end:
            return index
    if spans and pos == spans[-1][1]:
        return len(spans) - 1
    return None


def squash(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def clip_quote(original: str, start: int, end: int, radius: int = 42, limit: int = 220) -> str:
    left = max(0, start - radius)
    right = min(len(original), end + radius)
    snippet = squash(original[left:right])
    if len(snippet) > limit:
        snippet = snippet[: limit - 1] + "…"
    return snippet


def overlaps(start: int, end: int, taken: list[tuple[int, int]]) -> bool:
    return any(not (end <= left or start >= right) for left, right in taken)


def nearest(cands: list[dict], anchor_start: int, anchor_end: int) -> dict | None:
    best = None
    best_key = None
    for item in cands:
        if item["end"] <= anchor_start:
            dist = anchor_start - item["end"]
            side = 0
        elif item["start"] >= anchor_end:
            dist = item["start"] - anchor_end
            side = 1
        else:
            dist = 0
            side = 0
        key = (dist, side, item["start"])
        if best_key is None or key < best_key:
            best_key = key
            best = item
    return best


def window_text(text: str, start: int, end: int, radius: int = 36) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


# 언급. 검색 키워드 목록을 본문 언급으로 복사하지 않는다.
CHAR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("하치와레", re.compile(r"하치와레|하치와래")),
    ("우사기", re.compile(r"(?<![가-힣])우사기")),
    ("모몽가", re.compile(r"모몽가|모몬가")),
    ("랏코", re.compile(r"(?<![가-힣])랏코")),
    ("쿠리만쥬", re.compile(r"쿠리만쥬|쿠리만주")),
    ("아노코", re.compile(r"아노코")),
    ("데카츠요", re.compile(r"데카츠요")),
    ("갑옷씨", re.compile(r"갑옷\s*(?:씨|아저씨|상)")),
]
CHII_RE = re.compile(r"치이카와|치이까와|치카와|chiikawa|ちいかわ|吉伊卡哇", re.IGNORECASE)
MUN_RE = re.compile(r"먼작귀")
SHISA_RE = re.compile(r"(?<![가-힣])시사(?!하|점|적|성)")
KANI_RE = re.compile(r"(?<![가-힣])카니(?!발|보)")
ARMOR_BARE_RE = re.compile(r"(?<![가-힣])갑옷(?!\s*(?:씨|아저씨|상))")
WORK_CUE_RE = re.compile(r"애니|애니메이션|영화|만화|극장|더빙|시리즈|세계관|원작|웹툰")
IP_CUE_RE = re.compile(
    r"치이카와|치이까와|치카와|먼작귀|하치와레|하치와래|모몽가|모몬가|랏코|쿠리만쥬|쿠리만주|"
    r"아노코|데카츠요|갑옷\s*(?:씨|아저씨|상)|chiikawa|ちいかわ|吉伊卡哇|굿즈|인형|키링|가챠|피규어|마스코트",
    re.IGNORECASE,
)
OTHER_IP_RE = [
    ("다른IP:농담곰", re.compile(r"농담곰")),
    ("다른작품:파자마파티즈", PAJAMA_WORK_RE),
    ("다른IP:빤쮸토끼", PPANCHU_RE),
]

FORM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("키링", re.compile(r"키링|키체인|키홀더|스트랩")),
    ("인형", re.compile(r"누이구루미|(?<![가-힣])누이(?![가-힣])|인형")),
    ("마스코트", re.compile(r"마스코트")),
    ("피규어", re.compile(r"넨도로이드|소프비|피규어|피규")),
    ("가챠", re.compile(r"제일복권|가챠|쿠지|(?<![가-힣])뽑기")),
    ("스티커", re.compile(r"스티커")),
    ("아크릴", re.compile(r"아크릴")),
    ("뱃지", re.compile(r"캔뱃지|뱃지|핀버튼")),
    ("파우치", re.compile(r"파우치")),
    ("문구", re.compile(r"다이어리|수첩|필통|(?<![가-힣])노트(?![가-힣])|수정테이프|마스킹")),
    ("의류", re.compile(r"잠옷|티셔츠|후드티|후드|유니폼|(?<![가-힣])파자마(?![가-힣])|수면복")),
    ("잡화", re.compile(r"팔찌|넥타이|양말|슬리퍼|모자|에코백|가방")),
    ("출판", re.compile(r"만화책|코믹|단행본|(?<![가-힣])책(?![가-힣])")),
    ("영화", re.compile(r"(?<![가-힣])영화")),
    ("애니", re.compile(r"애니메이션|(?<![가-힣])애니(?![가-힣])")),
    ("영상", re.compile(r"움짤|(?<![가-힣])짤(?![가-힣])|(?<![가-힣])영상|클립")),
    ("팝업", re.compile(r"팝업")),
    ("이모티콘", re.compile(r"이모티콘|(?<![가-힣])임티")),
    ("식품", re.compile(r"모찌|젤리|푸딩|과자|사탕|쿠키|팬케이크|후리카게|카레|붕어빵|찰빵")),
]
FOOD_PRODUCT_CUE_RE = re.compile(r"굿즈|콜라보|편의점|(?<![A-Za-z])CU(?![A-Za-z])|패키지|출시|샀|구입|한정|맛있|과자|모찌")
STORY_EAT_RE = re.compile(r"먹(?:고|는|었|어|음|다|자)|한\s*입|베어")

PROMO_CLAUSE_RE = re.compile(
    r"판매(?:합니다|해요|해용|합니|함|중)|팝니다|양도(?:합니다|해요|해용|합니|함)|"
    r"교환(?:합니다|해요|해용)|공구(?:합니다|해요|해용|합니|함)|급처|"
    r"배송비|스마트스토어|구매\s*링크|가격\s*문의|예약\s*(?:판매|접수)|"
    r"증정|특전|결제일|배송일|구매자의\s*부담|무통보|구매\s*제한"
)
SELL_SPEECH_RE = re.compile(
    r"판매(?:합니다|해요|해용|합니|함|중)|팝니다|양도(?:합니다|해요|해용|합니|함)|"
    r"공구(?:합니다|해요|해용|합니|함)|급처|구매\s*링크|예약\s*판매|주문\s*받"
)
PERSONAL_SALE_RE = re.compile(r"양도|급처|팝니다|교환(?:합니다|해요|해용|구함|원함)|개인\s*거래|제꺼|제\s*꺼")
SHOP_NEWS_RE = re.compile(r"출시|발매|재입고|입고\s*되었|입고되었|공개(?:됐|되었|합니다)")
SHOP_CUE_RE = re.compile(r"스마트스토어|배송일|결제일|공식|예약\s*판매|구매\s*링크|증정|특전|매장|팝업\s*오픈")
INFO_RE = re.compile(r"번역|출처|기사|보도|공지|타래|에\s*따르면|라고\s*합니다|정보\s*공유|정리했")
FIRST_RE = re.compile(r"내가|저는|제가|나는|난|저의|나의|저도|나도|내\s|제\s|저\s")
REACT_RE = re.compile(r"ㅋㅋ|ㅎㅎ|ㅠ|ㅜ|대박|헐|실화|미쳤|귀여|기여|커여|웃기|사랑|최고|예뻐|이쁘")
EMOJI_REACT_RE = re.compile(r"[☺♥❤💕😭😍🥰😊😂🤣😆👍🙏✨💗💙]")

POS_EVAL_RE = re.compile(
    r"귀여워|귀여운|귀여움|귀엽|귀여웠|기여워|기여운|커여워|커여운|귀요|존귀|기염|깜찍|사랑스|"
    r"이쁘|예쁘|예뻐|존예|"
    r"좋아(?:요|해|했|함|서|진|운|움|다)|좋았|좋겠|좋은|"
    r"사랑(?:해|함)|최고|맘에\s*들|마음에\s*들|힐링|소중|감동|"
    r"웃기|웃겨|웃김|빵\s*터|빵터|기특|착해|착하|착함|다정"
)
NEG_EVAL_RE = re.compile(
    r"싫(?:어|다|음|네|허)|별로(?:야|다|네|임)|실망|노잼|"
    r"(?:안|못)\s*귀여|귀엽지\s*않|못생겼|안\s*예쁜|안\s*이쁜"
)
TRAIT_WORD_RE = re.compile(r"기특|착해|착하|착함|다정|(?<![가-힣])잔인|(?<![가-힣])사악|순해|순하|말투|(?<![가-힣])대사|실수")
APPEAR_RE = re.compile(
    r"얼굴|표정|눈빛|눈매|눈이\s*(?:동|크|작|반짝)|만화눈|동글|둥글|조그맣|조그마|앙증|"
    r"꼬리|볼살|볼터치|볼(?:이|은|을)|실루엣|수염"
)
DESIGN_RE = re.compile(
    r"재질|마감|퀄리티|디테일|박음질|투명|사이즈|포즈|의상|코디|말랑|폭신|부들|실물|"
    r"(?<![가-힣])크기"
)
REL_RE = re.compile(r"케미|우정|친구\s*사이|명장면|콤비|상호작용")
PRICE_EVAL_RE = re.compile(r"비싸|아깝|부담스럽|가성비|저렴|(?<![가-힣비])싸(?:요|다|서|게)|가격이\s*부담|값이\s*부담")
FUNNY_RE = re.compile(r"웃기|웃겨|웃김|빵\s*터|빵터")

CHAR_NAMES = ["치이카와", "하치와레", "우사기", "모몽가", "랏코", "쿠리만쥬", "아노코", "데카츠요", "갑옷씨", "시사", "카니"]
CHAR_SUBJ_RE = re.compile(
    r"(치이카와|치이까와|치카와|하치와레|하치와래|우사기|모몽가|모몬가|랏코|쿠리만쥬|쿠리만주|"
    r"아노코|데카츠요|갑옷\s*(?:씨|아저씨|상)|시사|카니)(?:이|가|은|는|도)"
)
OTHER_SUBJ_RE = re.compile(
    r"(친구|룸메|언니|오빠|엄마|아빠|남친|여친|사장|점원|동생|선배|후임|오너|사람|누가|"
    r"아는\s*언니)(?:이|가|은|는|님|께서)?"
)

# 행동. 앞선 패턴이 차지한 구간은 다시 구매완료로 세지 않는다.
BEHAVIOR_SPECS: list[tuple[str, re.Pattern[str], str, str]] = [
    ("구매부정", re.compile(r"(?:안|못)\s*(?:샀|삿)(?:다|어|어요|습니다|습|음|네|당|구|따|어용|어여|고|는데|어)?"), "확정", "작성자의 부정 구매"),
    ("구매부정", re.compile(r"사지\s*않|사기\s*싫|사고\s*싶(?:지|진)\s*않|안\s*사고\s*싶|(?:안|못)\s*삽니다|(?:안|못)\s*사요"), "확정", "작성자의 부정 구매"),
    ("구매부정", re.compile(r"(?<![가-힣])안\s*삼|(?<![가-힣])안삼"), "확정", "안 샀다는 구어 표기"),
    ("구매포기", re.compile(r"(?:사기|사는\s*거|구매).{0,8}포기|포기(?:했|함)"), "확정", "포기를 말한 경우만"),
    ("구매희망", re.compile(r"사고\s*싶|사고싶|사고시프|사고\s*시프|구매하고\s*싶|겟하고\s*싶|지르고\s*싶"), "확정", "사고 싶다는 희망"),
    ("구매희망", re.compile(r"(?<![가-힣])사야(?:지|겠|대|됨|할|겠다)"), "확정", "사겠다는 의향. 완료가 아니다"),
    ("구매고민", re.compile(r"(?<![가-힣])살(?:까|래|지)(?![가-힣])"), "확정", "살까는 미결정이라 구매희망이나 구매완료로 세지 않는다"),
    ("소장희망", re.compile(r"갖고\s*싶|가지고\s*싶|소장하고\s*싶"), "확정", "갖고 싶다는 소장 희망. 결제 희망과 다르다"),
    ("구매희망", re.compile(r"(?<![가-힣])(?:삽니다|구합니다|구해요)(?![가-힣])|양도\s*받|양도받"), "확정", "구하는 표현. 결제 완료가 아니다"),
    ("구매완료", re.compile(r"(?:샀|삿)(?:어요|습니다|읍니다|는데|더니|다가|어용|어욤|어여|다|어|습|음|네|당|구|지|고|따|더|던)(?![가-힣])"), "확정", "샀다 계열. 삿포로의 삿, 샀을 추정은 제외"),
    ("구매완료", re.compile(r"(?<![가-힣])사버렸(?:다|어|어요|음|네)?|(?<![가-힣])사버림"), "확정", "사버렸다·사버림"),
    ("구매완료", re.compile(r"(?<![가-힣])사왔(?:다|어|어요|습니다|음|네|고|더니)?|(?<![가-힣])사옴"), "확정", "사왔다 계열"),
    ("구매완료", re.compile(r"구매(?:했다|했어|했어요|했습니다|했음|했네|해버렸|해버림|완료)|구매\s*완료"), "확정", "구매했다"),
    ("구매완료", re.compile(r"구입(?:했다|했어|했어요|했습니다|했음|했네|완료)"), "확정", "구입했다"),
    ("구매완료", re.compile(r"결제(?:했다|했어|했어요|했습니다|했음|완)(?!료)|결제완료(?!되지)|결제\s*완"), "확정", "결제했다"),
    ("구매완료", re.compile(r"(?<!소리)(?<!비명)(?<![가-힣])질렀(?:다|어|어요|음|네|어)?"), "확정", "질렀다. 소리질렀다는 제외"),
    ("구매완료", re.compile(r"(?<![가-힣])사서(?!함)"), "확인 필요", "사서. 상상·희망·다른 주어이면 작성자 완료로 세지 않는다"),
    ("획득", re.compile(r"겟(?:했|함|했어요|했다|또)|득템"), "확인 필요", "겟·득템은 획득 표현이라 결제 완료로 단정하지 않는다"),
    ("획득", re.compile(r"데려왔|데려온|델꾸"), "확인 필요", "데려오다는 비유일 수 있다"),
    ("뽑기", re.compile(r"뽑(?:았|음|았어|았다|았네|았음)"), "확정", "뽑았다. 구매완료로 바꾸지 않는다"),
    ("소지사용", re.compile(r"언박싱|개봉(?:했|함|했어|했다)|소장\s*중|달고\s*다|가방에\s*달"), "확정", "개봉·소장·부착"),
    ("시청경험", re.compile(r"(?:애니|애니메이션|영화|만화|영상|정주행).{0,18}(?:봤(?:어|다|음|네)?|보는\s*중|정주행(?:했|함)|관람(?:했|함))|(?:봤(?:어|다|음)|정주행(?:했|함)|관람(?:했|함)).{0,16}(?:애니|애니메이션|영화|만화)"), "확정", "시청 경험"),
    ("시청희망", re.compile(r"보고\s*싶(?:어|다|음|어요)|정주행\s*하고\s*싶"), "확인 필요", "보고 싶다. 대상 명사가 없으면 확인"),
    ("팝업방문", re.compile(r"팝업.{0,20}(?:갔(?:어|다|네)?|다녀|들렀|방문(?:했|함)|입장)|(?:갔(?:어|다)|다녀왔|방문(?:했|함)).{0,12}팝업"), "확정", "팝업에 갔다는 이동"),
    ("개인판매교환", re.compile(r"양도(?:합니다|해요|해용|합니|함)|교환(?:합니다|해요|해용)|급처|(?<![가-힣])팝니다"), "확정", "작성자가 넘기거나 바꾸겠다는 표현"),
    ("공구", re.compile(r"공구"), "확정", "공동구매 언급. 구매완료가 아니다"),
]
ACTION_IN_EFFECT_RE = re.compile(
    r"샀|삿|사왔|사옴|사서|구매|구입|결제|사고\s*싶|사고싶|살까|살래|사야|갖고\s*싶|가지고\s*싶|"
    r"안\s*샀|안샀|안\s*삿|안삿|못\s*샀|못샀|못\s*삿|못삿|안\s*삼|안삼|뽑|겟|포기|보(?:고\s*싶|고싶)|판매|양도"
)
MOTIVE_RE = re.compile(
    r"귀여|기여|커여|예쁘|이쁘|좋아|사랑|웃기|반가|우울|행복|힐링|싫|비싸|아깝|부담|"
    r"품절|재고|매물|공간|투명|발견|유일|같아|같아서|한정|퀄리티|마감|재질|디테일|"
    r"없어|없어서|얼굴|표정|동글|작아|조그마|다정|기특|맛있|커서|작아서"
)
# 아서/어서는 음절이 나뉜 경우만 잡힌다. 귀여워서의 '워서', 비싸서의 '싸서', 예뻐서의 '뻐서'를 따로 넣는다.
MARK_RE = re.compile(r"아서|어서|여서|워서|해서|때문에|니까|라서|길래|싸서|뻐서")
CONCESSIVE_RE = re.compile(r"지만|하지만|는데|ㄴ데|은데|인데|긴\s*하")

USE_SPECS = [
    ("휴대·부착", re.compile(r"가방에|달고\s*다|키링(?:을|를)?\s*달|고리에\s*달")),
    ("전시", re.compile(r"진열|전시해|세워\s*두|책상\s*위")),
    ("선물", re.compile(r"선물(?:했|함|로|용|받았|이야)|(?:줬|주었)(?:다|어)|받아(?:왔|서)")),
    ("착용", re.compile(r"(?:잠옷|티셔츠|후드|파자마|유니폼).{0,10}입|입(?:고|었|어|음).{0,10}(?:잠옷|티|후드|파자마|유니폼)")),
    ("감상", re.compile(r"정주행|관람|보는\s*중")),
    ("섭취", re.compile(r"먹(?:었|어|고|음)|마셨")),
]
COLLECT_RE = re.compile(r"모으(?:고\s*싶|려고|다|자)|수집|컬렉(?:션|트)|종류별|세트로\s*맞|다\s*모으|콤비로|조합")
CONTENT_SPECS = [
    ("장면·대사", re.compile(r"[「『“\"].{1,50}[」』”\"]|라고\s*(?:말|했|함|한다)|이\s*(?:장면|컷|부분|대사)|명장면|명대사")),
    ("반복 이용", re.compile(r"또\s*봤|다시\s*봤|몇\s*번(?:이나)?\s*봤|무한\s*재생|계속\s*봐|반복(?:해서)?\s*봤|[0-9]+\s*회차")),
    ("일상 비유", re.compile(r"나(?:랑|와|도)?.{0,6}(?:같|똑같)|내\s*(?:얘기|이야기|모습)|(?:회사|직장|출근|학교).{0,10}(?:같|떠올)|공감(?:돼|되|했|함)")),
    ("공유·추천", re.compile(r"추천(?:해|함|합니다|드려)|강추|꼭\s*봐|봐\s*봐|공유(?:해|함|합니다)")),
    ("관계·다음 이야기", re.compile(r"케미|우정|친구\s*사이|다음\s*(?:화|이야기|편)|그\s*다음에|사이가\s*좋")),
]
PAY_FALSE_RE = re.compile(r"배송비|해배비|택배비|결제일|결제창|나중에\s*결제")
IMAGINE_RE = re.compile(r"상상|꿈에서|꿈에|하면\s*좋겠")
TEMPLATE_PAY_RE = re.compile(r"결제완료되지|구매(?:시|자|제한|링크|의향|의사)|구입하면|배송일")


def build_kiwi() -> Kiwi:
    kiwi = Kiwi()
    for word in [
        "치이카와", "치이까와", "치카와", "하치와레", "하치와래", "우사기", "모몽가", "모몬가",
        "랏코", "쿠리만쥬", "쿠리만주", "먼작귀", "아노코", "데카츠요", "갑옷씨", "갑옷아저씨",
        "파자마파티즈", "빤쮸우사기", "키링", "키체인", "가챠", "피규어", "마스코트", "누이구루미",
        "아크릴", "스티커", "콜라보", "팝업", "이모티콘", "농담곰", "메지루시", "넨도로이드",
    ]:
        kiwi.add_user_word(word, "NNP", 8.0)
    return kiwi


def find_pattern_hits(text: str, pattern: re.Pattern[str]) -> list[tuple[int, int, str]]:
    return [(match.start(), match.end(), match.group()) for match in pattern.finditer(text)]


def mention_records(original: str, search: str) -> tuple[list[dict], list[str]]:
    reviews: list[str] = []
    found: list[dict] = []
    ip_cue = bool(IP_CUE_RE.search(search) or MUN_RE.search(search) or CHII_RE.search(search))
    for name, pattern in CHAR_PATTERNS:
        for start, end, surface in find_pattern_hits(search, pattern):
            found.append({"name": name, "start": start, "end": end, "surface": original[start:end], "kind": "캐릭터"})
    for start, end, _ in find_pattern_hits(search, CHII_RE):
        clause = search[max(0, start - 24) : min(len(search), end + 24)]
        other = any(item["name"] != "치이카와" and abs(item["start"] - start) < 40 for item in found)
        if WORK_CUE_RE.search(clause):
            role = "작품"
        elif other:
            role = "캐릭터"
        else:
            role = "구분불가"
        found.append({
            "name": "치이카와",
            "start": start,
            "end": end,
            "surface": original[start:end],
            "kind": role,
        })
    for start, end, _ in find_pattern_hits(search, MUN_RE):
        found.append({"name": "먼작귀", "start": start, "end": end, "surface": original[start:end], "kind": "작품"})
    for label, pattern in (("시사", SHISA_RE), ("카니", KANI_RE)):
        for start, end, _ in find_pattern_hits(search, pattern):
            if ip_cue:
                found.append({"name": label, "start": start, "end": end, "surface": original[start:end], "kind": "캐릭터"})
            else:
                reviews.append(f"동음이의어:{label}:{squash(original[max(0, start - 12):end + 12])}")
    if ARMOR_BARE_RE.search(search) and not any(item["name"] == "갑옷씨" for item in found):
        reviews.append("수식 없는 갑옷")
    for label, pattern in OTHER_IP_RE:
        if pattern.search(original if "빤쮸" in label or "파자마" in label else search):
            found.append({"name": label, "start": -1, "end": -1, "surface": label, "kind": "다른이름"})
    # 빤쮸·파자마 파티즈는 검색 텍스트에서 지웠으므로 원문에서만 확인한다.
    if PPANCHU_RE.search(original):
        if not any(item["name"] == "다른IP:빤쮸토끼" for item in found):
            found.append({"name": "다른IP:빤쮸토끼", "start": -1, "end": -1, "surface": "빤쮸", "kind": "다른이름"})
    if PAJAMA_WORK_RE.search(original):
        if not any(item["name"] == "다른작품:파자마파티즈" for item in found):
            found.append({"name": "다른작품:파자마파티즈", "start": -1, "end": -1, "surface": "파자마파티즈", "kind": "다른이름"})
    return found, reviews


def clause_promo(clause: str) -> bool:
    return bool(PROMO_CLAUSE_RE.search(clause))


STORY_FEEL_RE = re.compile(r"싫(?:어)?(?:하|한)|좋아(?:하|한)|무서워(?:하|한)|울었|울어|운다")


def subject_speaker(text: str, start: int) -> str | None:
    """동사에 가까운 주어를 본다.

    등장인물 이름 뒤의 귀엽다·다정하다는 작성자가 대상을 평가한 것이다.
    싫어한다·좋아한다·운다는 등장인물의 감정으로 둔다.
    """
    pre = text[max(0, start - 28) : start]
    other = list(OTHER_SUBJ_RE.finditer(pre))
    cast = list(CHAR_SUBJ_RE.finditer(pre))
    first = list(FIRST_RE.finditer(pre))
    cands = []
    if other:
        cands.append((other[-1].start(), "타인"))
    if cast:
        cands.append((cast[-1].start(), "작중"))
    if first:
        cands.append((first[-1].start(), "작성자"))
    if not cands:
        return None
    cands.sort()
    speaker = cands[-1][1]
    if speaker == "작중" and not STORY_FEEL_RE.search(text[max(0, start - 4) : start + 12]):
        return None
    return speaker


def aspect_for(local: str, match_text: str, has_form: bool) -> str:
    if TRAIT_WORD_RE.search(match_text) or TRAIT_WORD_RE.search(local):
        if not (has_form and DESIGN_RE.search(local) and not TRAIT_WORD_RE.search(match_text)):
            if TRAIT_WORD_RE.search(match_text) or TRAIT_WORD_RE.search(local):
                if REL_RE.search(local) and not TRAIT_WORD_RE.search(match_text):
                    return ASPECT_REL
                return ASPECT_ACT
    if REL_RE.search(local):
        return ASPECT_REL
    design_hit = bool(DESIGN_RE.search(local))
    appear_hit = bool(APPEAR_RE.search(local))
    if (has_form or re.search(r"스티커|키링|인형|피규어|마스코트|아크릴", local)) and appear_hit and re.search(r"동글|조그마|컷팅", local) and not re.search(r"얼굴|표정|볼살|볼터치|꼬리|눈빛", local):
        return ASPECT_GOODS
    if has_form and (design_hit or (appear_hit and re.search(r"표정|얼굴|포즈|의상|크기|사이즈", local))):
        return ASPECT_GOODS
    if appear_hit and not (has_form and re.search(r"크기|사이즈|(?<![가-힣])작(?:은|아)", local)):
        return ASPECT_LOOK
    if design_hit and has_form:
        return ASPECT_GOODS
    if FUNNY_RE.search(match_text) and re.search(r"장면|대사|행동|울|돕|먹|말하", local):
        return ASPECT_ACT
    return UNCLEAR_ASPECT


def reason_of(cause: str) -> tuple[str, str, str]:
    """작성자가 밝힌 이유 범주, 호감 측면, 연결 가족.

    반환 가족은 매력×행동, 구매×장벽, 상황×행동, 특징×호감 중 하나다.
    """
    if PRICE_EVAL_RE.search(cause) or re.search(r"비싸|아깝|부담스럽", cause):
        return "가격", ASPECT_OTHER, "구매×장벽"
    if re.search(r"공간|자리|둘\s*데|둘\s*곳", cause):
        return "공간", ASPECT_OTHER, "구매×장벽"
    if re.search(r"품절|재고|매물|구하기", cause):
        return "재고·구매경로", ASPECT_OTHER, "구매×장벽"
    if re.search(r"마감|퀄리티|재질|디테일|나사|비치|투명", cause):
        return "품질·구현", ASPECT_GOODS, "매력×행동"
    if APPEAR_RE.search(cause):
        if re.search(r"인형|키링|피규어|마스코트|아크릴|스티커|실물", cause):
            return "상품에 드러난 외형·크기", ASPECT_GOODS, "매력×행동"
        return "작성자가 밝힌 외형 특징", ASPECT_LOOK, "특징×호감"
    if TRAIT_WORD_RE.search(cause) or REL_RE.search(cause):
        aspect = ASPECT_REL if REL_RE.search(cause) and not TRAIT_WORD_RE.search(cause) else ASPECT_ACT
        return "작성자가 밝힌 행동·관계", aspect, "매력×행동"
    if re.search(r"귀여|기여|커여|예쁘|이쁘|존귀|깜찍", cause):
        return "호감 표현(귀엽다·예쁘다). 세부 특징은 이 구절에 없다", UNCLEAR_ASPECT, "매력×행동"
    if re.search(r"좋아|사랑|최고|맘에", cause):
        return "호감 표현(좋아한다). 세부 특징은 이 구절에 없다", UNCLEAR_ASPECT, "매력×행동"
    if re.search(r"우울|행복|힐링|위로|반가", cause):
        return "당시 정서나 반가움", ASPECT_OTHER, "상황×행동"
    if re.search(r"발견|유일", cause):
        return "발견·입수 상황", ASPECT_OTHER, "상황×행동"
    if re.search(r"같아|같아서|같이 생", cause):
        return "다른 대상과 비슷해 보인다고 밝힘", ASPECT_OTHER, "상황×행동"
    if re.search(r"한정", cause):
        return "한정이라고 이유 구절에 밝힘", ASPECT_OTHER, "상황×행동"
    if re.search(r"없어|없어서", cause):
        return "원하는 대상이 없다고 밝힘", ASPECT_OTHER, "구매×장벽"
    if re.search(r"맛있|맛나", cause):
        return "맛", ASPECT_OTHER, "매력×행동"
    return "작성자가 연결어로 붙인 기타 이유", ASPECT_OTHER, "상황×행동"


def behavior_effect_label(effect: str) -> str | None:
    if re.search(r"(?:안|못)\s*(?:샀|삿)|안\s*삼|안삼|사지\s*않", effect):
        return "구매부정"
    if re.search(r"포기", effect):
        return "구매포기"
    if re.search(r"사고\s*싶|사고싶|사야", effect):
        return "구매희망"
    if re.search(r"살까|살래", effect):
        return "구매고민"
    if re.search(r"갖고\s*싶|가지고\s*싶", effect):
        return "소장희망"
    if re.search(r"샀|삿|사왔|사옴|사서|구매했|구입했|결제했|결제\s*완|질렀", effect):
        return "구매완료"
    if re.search(r"뽑", effect):
        return "뽑기"
    if re.search(r"겟|득템", effect):
        return "획득"
    if POS_EVAL_RE.search(effect) or NEG_EVAL_RE.search(effect) or re.search(r"놀랐|당황|실망", effect):
        return "호감표현"
    return None


def find_causes(sentence: str, sent_start: int) -> list[dict]:
    marks = list(MARK_RE.finditer(sentence))
    rows = []
    for index, mark in enumerate(marks):
        prev_end = marks[index - 1].end() if index else 0
        next_start = marks[index + 1].start() if index + 1 < len(marks) else len(sentence)
        cause_raw = sentence[max(prev_end, mark.start() - 42) : mark.start()]
        parts = CONCESSIVE_RE.split(cause_raw)
        cause = parts[-1]
        effect = sentence[mark.end() : min(next_start, mark.end() + 48)]
        cause_blob = f"{cause}{mark.group()}"
        if not cause.strip() and not MOTIVE_RE.search(mark.group()):
            continue
        if not (MOTIVE_RE.search(cause_blob) or APPEAR_RE.search(cause_blob) or DESIGN_RE.search(cause_blob) or TRAIT_WORD_RE.search(cause_blob)):
            continue
        if not (ACTION_IN_EFFECT_RE.search(effect) or POS_EVAL_RE.search(effect) or NEG_EVAL_RE.search(effect) or re.search(r"놀랐|당황", effect)):
            continue
        effect_label = behavior_effect_label(effect)
        if effect_label is None:
            continue
        reason, aspect, family = reason_of(cause_blob)
        if effect_label == "호감표현" and aspect == UNCLEAR_ASPECT and "호감 표현" in reason:
            continue
        if effect_label == "호감표현":
            family = "특징×호감"
        elif effect_label in {"구매부정", "구매포기"} and family == "매력×행동":
            family = "매력×행동"
        elif effect_label in {"구매부정", "구매포기"} and "장벽" in family:
            family = "구매×장벽"
        rows.append({
            "cause": squash(cause),
            "effect": squash(effect),
            "mark": mark.group(),
            "reason": reason,
            "aspect": aspect,
            "family": family,
            "effect_label": effect_label,
            "abs_start": sent_start + max(prev_end, mark.start() - 42),
            "abs_end": sent_start + min(next_start, mark.end() + 48),
            "effect_abs_start": sent_start + mark.end(),
            "effect_abs_end": sent_start + min(next_start, mark.end() + 48),
        })
    return rows


def forms_in(text: str, abs_start: int = 0) -> list[dict]:
    rows = []
    occupied: list[tuple[int, int]] = []
    for label, pattern in FORM_PATTERNS:
        for match in pattern.finditer(text):
            if overlaps(match.start(), match.end(), occupied):
                continue
            if label == "식품":
                if STORY_EAT_RE.search(text) and not FOOD_PRODUCT_CUE_RE.search(text):
                    continue
            if label == "의류" and PAJAMA_WORK_RE.search(text):
                continue
            occupied.append((match.start(), match.end()))
            rows.append({
                "label": label,
                "start": abs_start + match.start(),
                "end": abs_start + match.end(),
                "surface": match.group(),
            })
    return rows


def entities_for_target(mentions: list[dict], forms: list[dict], clause_start: int, clause_end: int) -> list[dict]:
    rows = []
    for item in mentions:
        if item["start"] < 0:
            continue
        if clause_start <= item["start"] < clause_end:
            if item["kind"] == "작품":
                kind = "작품"
            elif item["kind"] == "다른이름":
                kind = "다른이름"
            elif item["kind"] == "구분불가":
                kind = "이름"
            else:
                kind = "캐릭터"
            rows.append({**item, "target_type": kind, "target": item["name"]})
    for item in forms:
        if clause_start <= item["start"] < clause_end:
            rows.append({
                "start": item["start"],
                "end": item["end"],
                "target_type": "상품" if item["label"] not in {"영화", "애니", "영상"} else "콘텐츠",
                "target": item["label"],
                "name": item["label"],
            })
    return rows


def new_evidence(**kwargs: object) -> dict:
    base = {
        "axis": NA,
        "label": NA,
        "polarity": NA,
        "target_entity": NONE,
        "target_type": NA,
        "affection_aspect": NA,
        "speaker": NA,
        "product_form": NONE,
        "use_mode": NONE,
        "selection_reason": NONE,
        "collection_reason": NONE,
        "behavior": NONE,
        "barrier": NONE,
        "certainty": "확정",
        "judgment_method": DECISION_METHOD,
        "judgment_note": "",
        "about_ip": True,
        "match_text": "",
        "quote": "",
        "quote_start": -1,
        "quote_end": -1,
    }
    base.update(kwargs)
    return base


def analyze_post(raw_text: str, kiwi: Kiwi | None = None) -> dict:
    original, readable, search = prepare(raw_text)
    sentences = split_spans(original, SENT_SPLIT_RE)
    clauses = split_spans(original, CLAUSE_SPLIT_RE)
    mentions, mention_reviews = mention_records(original, search)
    ip_in_post = any(item["kind"] in {"캐릭터", "작품", "구분불가"} for item in mentions) or bool(CHII_RE.search(search) or MUN_RE.search(search))
    post_sale = bool(SELL_SPEECH_RE.search(search))
    evidence: list[dict] = []
    reviews = list(mention_reviews)

    mention_labels = []
    for item in mentions:
        if item["name"] == "치이카와":
            if item["kind"] == "작품":
                mention_labels.append("작품:치이카와")
            elif item["kind"] == "캐릭터":
                mention_labels.append("등장인물:치이카와")
            else:
                mention_labels.append("구분불가:치이카와이름")
        elif item["name"] == "먼작귀":
            mention_labels.append("작품:먼작귀")
        elif item["kind"] == "캐릭터":
            mention_labels.append(f"등장인물:{item['name']}")
        else:
            mention_labels.append(item["name"])
    # 구절마다 역할이 달라도 게시물 라벨은 중복을 제거해 모두 남긴다.
    mention_labels = list(dict.fromkeys(mention_labels))

    taken: list[tuple[int, int]] = []
    behaviors: list[dict] = []
    for label, pattern, certainty, note in BEHAVIOR_SPECS:
        for match in pattern.finditer(search):
            if overlaps(match.start(), match.end(), taken):
                continue
            sentence_index = locate(sentences, match.start())
            clause_index = locate(clauses, match.start())
            if sentence_index is None or clause_index is None:
                continue
            sent_a, sent_b = sentences[sentence_index]
            cl_a, cl_b = clauses[clause_index]
            sentence = search[sent_a:sent_b]
            clause = search[cl_a:cl_b]
            local_certainty = certainty
            local_note = note
            if TEMPLATE_PAY_RE.search(sentence) and label == "구매완료":
                continue
            if label == "구매완료" and PAY_FALSE_RE.search(sentence) and not forms_in(sentence):
                local_certainty = "확인 필요"
                local_note += " 배송·결제 안내 문맥이면 작성자 구매로 세지 않는다."
            if label == "구매완료" and IMAGINE_RE.search(sentence):
                local_certainty = "확인 필요"
                local_note += " 상상·가정이 같은 문장에 있다."
            if label == "구매완료" and re.search(r"배대지|통관|합배송", sentence):
                local_certainty = "확인 필요"
                local_note += " 배송 상태 목록 안의 구매완료는 확정 구매로 세지 않는다."
            if label == "구매희망" and "구하는 표현" in note and clause_promo(clause):
                local_certainty = "확인 필요"
                local_note += " 안내 문안의 구함은 작성자 구매희망으로 세지 않는다."
            if label == "시청희망":
                local_certainty = "확정" if re.search(r"애니|영화|만화|영상|정주행|먼작귀|치이|하치와레", sentence) else "확인 필요"
            speaker = subject_speaker(search, match.start())
            if speaker is None:
                speaker = "작성자"
                if clause_promo(clause) and label in {"개인판매교환", "공구"}:
                    speaker = "작성자"
                elif clause_promo(clause) and label not in {"개인판매교환", "공구", "구매희망"}:
                    speaker = "홍보문구"
            if label == "구매완료" and speaker == "작성자":
                pre = search[max(0, match.start() - 18) : match.start()]
                if re.search(r"(?:안|못)\s*$", pre):
                    continue
            if label == "획득" and re.search(r"샀|삿|사왔|구매했", sentence):
                local_note += " 같은 문장에 구매 동사가 있어 획득을 별도 구매로 세지 않는다."
                local_certainty = "확인 필요"
            if label == "개인판매교환":
                speaker = "작성자"
            taken.append((match.start(), match.end()))
            form_here = forms_in(search[cl_a:cl_b], cl_a)
            nearest_form = nearest(form_here, match.start(), match.end())
            behaviors.append({
                "label": label,
                "start": match.start(),
                "end": match.end(),
                "speaker": speaker,
                "certainty": local_certainty,
                "note": local_note,
                "clause": (cl_a, cl_b),
                "sentence": (sent_a, sent_b),
                "form": nearest_form["label"] if nearest_form else NONE,
            })
            evidence.append(new_evidence(
                axis="행동",
                label=label,
                behavior=label,
                speaker=speaker,
                certainty=local_certainty,
                product_form=nearest_form["label"] if nearest_form else NONE,
                target_entity=nearest_form["label"] if nearest_form else NONE,
                target_type="상품" if nearest_form else NA,
                judgment_note=local_note,
                about_ip=ip_in_post,
                match_text=original[match.start() : match.end()],
                quote=clip_quote(original, match.start(), match.end()),
                quote_start=match.start(),
                quote_end=match.end(),
            ))

    sentiments: list[dict] = []
    sent_taken: list[tuple[int, int]] = []
    sentiment_matches = []
    for polarity_default, pattern in (("긍정", POS_EVAL_RE), ("부정", NEG_EVAL_RE)):
        for match in pattern.finditer(search):
            sentiment_matches.append((match.start(), match.end(), match.group(), polarity_default))
    sentiment_matches.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
    chosen = []
    for start, end, surface, polarity_default in sentiment_matches:
        if overlaps(start, end, sent_taken):
            continue
        sent_taken.append((start, end))
        chosen.append((start, end, surface, polarity_default))
    chosen.sort()
    for start, end, surface, polarity_default in chosen:
        clause_index = locate(clauses, start)
        if clause_index is None:
            continue
        cl_a, cl_b = clauses[clause_index]
        local = search[max(cl_a, start - 36) : min(cl_b, end + 36)]
        clause = search[cl_a:cl_b]
        pre = search[max(0, start - 6) : start]
        post = search[end : end + 8]
        if polarity_default == "긍정":
            polarity = "부정" if re.search(r"(?:안|못)\s*$", pre) or re.search(r"^\s*지\s*않", post) else "긍정"
        else:
            polarity = "긍정" if re.search(r"(?:안|못)\s*$", pre) else "부정"
        speaker = subject_speaker(search, start) or "작성자"
        if speaker == "작성자" and clause_promo(clause):
            speaker = "홍보문구"
        elif speaker == "작성자" and post_sale and not FIRST_RE.search(clause) and label_not_personal_sale(clause):
            # 판매 글의 다른 문장도 1인칭이 없으면 홍보 문안으로 둔다.
            if SELL_SPEECH_RE.search(search) and not FIRST_RE.search(clause):
                speaker = "홍보문구"
        form_here = forms_in(clause, cl_a)
        has_form = bool(form_here)
        if PRICE_EVAL_RE.search(surface) or (polarity == "부정" and PRICE_EVAL_RE.search(local) and not NEG_EVAL_RE.search(surface)):
            aspect = ASPECT_OTHER
            target = "가격"
            target_type = "가격"
        else:
            aspect = aspect_for(local, surface, has_form)
            ents = entities_for_target(mentions, form_here, cl_a, cl_b)
            picked = nearest(ents, start, end) if ents else None
            if picked is None:
                target, target_type = NONE, "불명"
            else:
                target, target_type = picked["target"], picked["target_type"]
            # 가까운 일반명사가 있어도 특징 단어가 없으면 측면은 확인 불가다.
            # Kiwi 명사로 측면을 '기타'로 바꾸지 않는다.
        if polarity == "부정" and target_type == "가격":
            aspect = ASPECT_OTHER
        hard_promo = re.compile(r"발매|구매\s*가능|예약\s*판매|증정|온라인\s*에서\s*구매")
        if speaker == "작성자" and (hard_promo.search(clause) or hard_promo.search(search)) and not FIRST_RE.search(clause) and not re.search(r"샀|삿|ㅠ|ㅋㅋ|ㅎㅎ", clause):
            speaker = "홍보문구"
        sentiments.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "polarity": polarity,
            "aspect": aspect,
            "target": target,
            "target_type": target_type,
            "clause": (cl_a, cl_b),
        })
        evidence.append(new_evidence(
            axis="호감",
            label=aspect,
            polarity=polarity,
            target_entity=target,
            target_type=target_type,
            affection_aspect=aspect,
            speaker=speaker,
            certainty="확정",
            judgment_note="호감 표현의 측면은 같은 구절에 특징 단어가 있을 때만 외형·행동·관계·상품구현으로 둔다. 귀엽다·좋다 자체는 측면이 아니다.",
            about_ip=ip_in_post or target_type in {"캐릭터", "작품", "상품", "콘텐츠"},
            match_text=original[start:end],
            quote=clip_quote(original, start, end),
            quote_start=start,
            quote_end=end,
        ))
        if speaker == "작성자" and aspect == UNCLEAR_ASPECT and polarity == "긍정":
            pass
        if speaker == "불명":
            reviews.append("호감 주어 불명")

    all_forms = forms_in(search, 0)
    for item in all_forms:
        clause_index = locate(clauses, item["start"])
        speaker = "홍보문구" if clause_index is not None and clause_promo(search[clauses[clause_index][0] : clauses[clause_index][1]]) else "작성자"
        evidence.append(new_evidence(
            axis="형태",
            label=item["label"],
            product_form=item["label"],
            target_entity=item["label"],
            target_type="콘텐츠" if item["label"] in {"영화", "애니", "영상"} else "상품",
            speaker=speaker,
            judgment_note="본문에 나온 형태. 선택 이유는 별도 연결이 있을 때만 채운다.",
            about_ip=ip_in_post,
            match_text=original[item["start"] : item["end"]],
            quote=clip_quote(original, item["start"], item["end"]),
            quote_start=item["start"],
            quote_end=item["end"],
        ))

    connections: list[dict] = []

    def add_connection(**kwargs: object) -> None:
        row = {
            "link_family": NA,
            "left_label": NA,
            "right_label": NA,
            "target_entity": NONE,
            "affection_aspect": NA,
            "product_form": NONE,
            "behavior": NONE,
            "barrier": NONE,
            "selection_reason": NONE,
            "evidence_level": LEVEL_CLAUSE,
            "speaker": "작성자",
            "quote": "",
            "judgment_note": "",
            "judgment_method": DECISION_METHOD,
            "local_evidence_indexes": [],
        }
        row.update(kwargs)
        connections.append(row)

    linked_behavior_forms: set[tuple[int, str]] = set()
    for sent_a, sent_b in sentences:
        sentence = search[sent_a:sent_b]
        for cause in find_causes(sentence, sent_a):
            speaker = subject_speaker(search, cause["effect_abs_start"]) or "작성자"
            if speaker != "작성자":
                # 타인이 이유를 말한 경우는 작성자 집계에서 빼되 근거는 남긴다.
                pass
            effect_label = cause["effect_label"]
            barrier = cause["reason"] if cause["family"] == "구매×장벽" else NONE
            behavior = effect_label if effect_label != "호감표현" else NONE
            form_here = forms_in(search[sent_a:sent_b], sent_a)
            nearest_form = nearest(
                [item for item in form_here if cause["effect_abs_start"] - 20 <= item["start"] <= cause["effect_abs_end"] + 10],
                cause["effect_abs_start"],
                cause["effect_abs_end"],
            )
            add_connection(
                link_family=cause["family"],
                left_label=cause["reason"],
                right_label=effect_label,
                target_entity=nearest_form["label"] if nearest_form else NONE,
                affection_aspect=cause["aspect"],
                product_form=nearest_form["label"] if nearest_form else NONE,
                behavior=behavior,
                barrier=barrier,
                selection_reason=cause["reason"],
                evidence_level=LEVEL_REASON,
                speaker=speaker,
                quote=squash(original[max(0, cause["abs_start"]) : min(len(original), cause["abs_end"])]),
                judgment_note="연결어 앞을 이유, 뒤를 결과로 붙였다. 작성자가 그렇게 말한 것이며 인과가 입증된 것은 아니다. 양보(지만·는데) 앞의 평가는 이유로 붙이지 않는다.",
            )

    # 같은 구절의 형태-행동, 호감-행동. 이유 연결어가 없으면 이유로 만들지 않는다.
    for behavior_index, behavior in enumerate(behaviors):
        if behavior["speaker"] != "작성자":
            continue
        cl_a, cl_b = behavior["clause"]
        clause_forms = [item for item in all_forms if cl_a <= item["start"] < cl_b]
        if clause_forms:
            if len(clause_forms) == 1:
                picked_form = clause_forms[0]
            else:
                picked_form = nearest(clause_forms, behavior["start"], behavior["end"])
                distances = []
                for item in clause_forms:
                    distances.append(abs(item["start"] - behavior["start"]))
                distances.sort()
                if len(distances) >= 2 and distances[1] - distances[0] < 6:
                    reviews.append("한 구절의 상품이 여럿이라 행동과 연결하지 않음")
                    picked_form = None
            if picked_form is not None:
                linked_behavior_forms.add((behavior_index, picked_form["label"]))
                add_connection(
                    link_family="형태×선택이유",
                    left_label=picked_form["label"],
                    right_label=behavior["label"],
                    target_entity=picked_form["label"],
                    product_form=picked_form["label"],
                    behavior=behavior["label"],
                    selection_reason=NONE,
                    evidence_level=LEVEL_CLAUSE,
                    speaker="작성자",
                    quote=clip_quote(original, behavior["start"], behavior["end"]),
                    judgment_note="같은 구절의 형태와 행동이다. 선택 이유는 언급되지 않았다.",
                )
        clause_sents = [item for item in sentiments if item["speaker"] == "작성자" and item["clause"] == behavior["clause"]]
        if len(clause_sents) == 1:
            sent_item = clause_sents[0]
        elif clause_sents:
            sent_item = nearest(clause_sents, behavior["start"], behavior["end"])
        else:
            sent_item = None
        if sent_item is not None:
            already = any(
                row["evidence_level"] == LEVEL_REASON
                and row["behavior"] == behavior["label"]
                and behavior["start"] >= row_start_guess(row, original)
                for row in connections
            )
            # 명시 이유가 같은 행동에 있으면 구절 공존을 이유로 업그레이드하지 않는다.
            if not any(row["evidence_level"] == LEVEL_REASON and row["behavior"] == behavior["label"] and row["quote"] and behavior["label"] in row["quote"] for row in connections):
                add_connection(
                    link_family="매력×행동",
                    left_label=sent_item["aspect"],
                    right_label=behavior["label"],
                    target_entity=sent_item["target"],
                    affection_aspect=sent_item["aspect"],
                    product_form=behavior["form"],
                    behavior=behavior["label"],
                    selection_reason=NONE,
                    evidence_level=LEVEL_CLAUSE,
                    speaker="작성자",
                    quote=clip_quote(original, min(sent_item["start"], behavior["start"]), max(sent_item["end"], behavior["end"])),
                    judgment_note="같은 구절에 호감 표현과 행동이 있다. 이유 연결어가 없어 선택 이유로 보지 않는다.",
                )

    author_purchase = [
        (index, item) for index, item in enumerate(behaviors)
        if item["speaker"] == "작성자" and item["label"] in {"구매완료", "구매희망", "구매고민", "구매부정", "구매포기", "소장희망", "획득", "뽑기"}
    ]
    if len(author_purchase) == 1 and len(all_forms) == 1:
        index, item = author_purchase[0]
        form_label = all_forms[0]["label"]
        if (index, form_label) not in linked_behavior_forms:
            if item["clause"] != (locate_span_tuple(clauses, all_forms[0]["start"])):
                add_connection(
                    link_family="형태×선택이유",
                    left_label=form_label,
                    right_label=item["label"],
                    target_entity=form_label,
                    product_form=form_label,
                    behavior=item["label"],
                    selection_reason=NONE,
                    evidence_level=LEVEL_POST,
                    speaker="작성자",
                    quote=clip_quote(original, item["start"], item["end"]),
                    judgment_note="게시물에 형태와 행동이 하나씩이라 공존만 기록한다. 같은 구절의 연결은 확인되지 않았다.",
                )

    # 사용, 수집, 콘텐츠 이용
    for label, pattern in USE_SPECS:
        for match in pattern.finditer(search):
            clause_index = locate(clauses, match.start())
            if clause_index is None:
                continue
            clause = search[clauses[clause_index][0] : clauses[clause_index][1]]
            if clause_promo(clause):
                continue
            if label == "섭취" and not FOOD_PRODUCT_CUE_RE.search(clause):
                evidence.append(new_evidence(
                    axis="콘텐츠이용",
                    label="작중 섭취 장면",
                    speaker="작중" if CHAR_SUBJ_RE.search(clause) else "작성자",
                    judgment_note="먹는 장면. 상품 섭취로 단정하지 않는다.",
                    about_ip=ip_in_post,
                    match_text=original[match.start() : match.end()],
                    quote=clip_quote(original, match.start(), match.end()),
                    quote_start=match.start(),
                    quote_end=match.end(),
                ))
                continue
            evidence.append(new_evidence(
                axis="사용",
                label=label,
                use_mode=label,
                speaker="작성자",
                judgment_note="사용 방식이 구절에 있다.",
                about_ip=ip_in_post,
                match_text=original[match.start() : match.end()],
                quote=clip_quote(original, match.start(), match.end()),
                quote_start=match.start(),
                quote_end=match.end(),
            ))
    if COLLECT_RE.search(search):
        match = COLLECT_RE.search(search)
        assert match is not None
        evidence.append(new_evidence(
            axis="수집",
            label="수집 표현",
            collection_reason="모으거나 종류를 맞추려는 표현이 있다",
            speaker="작성자" if not post_sale else "홍보문구",
            judgment_note="수집 단어가 있다. 구매 이유로 자동 연결하지 않는다.",
            about_ip=ip_in_post,
            match_text=original[match.start() : match.end()],
            quote=clip_quote(original, match.start(), match.end()),
            quote_start=match.start(),
            quote_end=match.end(),
        ))
    for label, pattern in CONTENT_SPECS:
        for match in pattern.finditer(search):
            clause_index = locate(clauses, match.start())
            if clause_index is None:
                continue
            clause = search[clauses[clause_index][0] : clauses[clause_index][1]]
            if clause_promo(clause) and label == "공유·추천":
                continue
            if label == "장면·대사" and not (CHII_RE.search(clause) or any(name in clause for name in ("하치와레", "우사기", "모몽가", "랏코", "먼작귀"))):
                continue
            if label == "반복 이용":
                note = "이 작성자가 이 글에서 반복해 봤다고 말한 표현만 해당한다. 다른 글의 같은 대사는 반복 소비가 아니다."
            else:
                note = "본문에 확인되는 콘텐츠 이용 표현."
            evidence.append(new_evidence(
                axis="콘텐츠이용",
                label=label,
                speaker="작성자",
                judgment_note=note,
                about_ip=ip_in_post,
                match_text=original[match.start() : match.end()],
                quote=clip_quote(original, match.start(), match.end()),
                quote_start=match.start(),
                quote_end=match.end(),
            ))

    contexts, context_notes = infer_contexts(search, original, evidence, ip_in_post)
    for label, quote, note in context_notes:
        evidence.append(new_evidence(
            axis="게시맥락",
            label=label,
            speaker=NA,
            judgment_note=note,
            about_ip=ip_in_post,
            match_text=quote[:80],
            quote=quote,
            quote_start=0,
            quote_end=0,
        ))

    unsure = [item["label"] for item in evidence if item["certainty"] == "확인 필요"]
    if unsure:
        reviews.append("확인 필요:" + ",".join(dict.fromkeys(unsure)))
    if not ip_in_post:
        reviews.append("본문에서 치이카와 계열 이름을 확인하지 못함")

    behavior_labels = list(dict.fromkeys(
        item["label"] for item in behaviors if item["speaker"] == "작성자" and item["certainty"] == "확정"
    ))
    if ip_in_post and not behavior_labels:
        behavior_labels = ["단순 언급"]
    author_aspects = list(dict.fromkeys(
        item["aspect"] for item in sentiments if item["speaker"] == "작성자" and item["polarity"] == "긍정"
    ))
    return {
        "original": original,
        "readable": readable,
        "mention_labels": mention_labels,
        "contexts": contexts,
        "evidence": evidence,
        "connections": connections,
        "reviews": list(dict.fromkeys(reviews)),
        "behavior_labels": behavior_labels,
        "author_aspects": author_aspects,
        "ip_in_post": ip_in_post,
    }


def label_not_personal_sale(clause: str) -> bool:
    return "양도" not in clause and "팝니다" not in clause


def locate_span_tuple(spans: list[tuple[int, int]], pos: int) -> tuple[int, int] | None:
    index = locate(spans, pos)
    if index is None:
        return None
    return spans[index]


def row_start_guess(row: dict, original: str) -> int:
    return 0


def infer_contexts(search: str, original: str, evidence: list[dict], ip_in_post: bool) -> tuple[list[str], list[tuple[str, str, str]]]:
    labels = []
    notes = []
    author_aff = any(item["axis"] == "호감" and item["speaker"] == "작성자" for item in evidence)
    author_intent = any(
        item["axis"] == "행동" and item["speaker"] == "작성자" and item["certainty"] == "확정"
        and item["label"] in {"구매희망", "구매고민", "구매부정", "구매포기", "소장희망", "시청희망"}
        for item in evidence
    )
    author_react = author_aff or author_intent or (bool(REACT_RE.search(search) or EMOJI_REACT_RE.search(original)) and ip_in_post and not (SELL_SPEECH_RE.search(search) and not FIRST_RE.search(search)))
    if SELL_SPEECH_RE.search(search) and not FIRST_RE.search(search) and not author_aff and not author_intent:
        author_react = False
    author_exp = any(
        item["axis"] == "행동" and item["speaker"] == "작성자" and item["certainty"] == "확정"
        and item["label"] in {"구매완료", "획득", "소지사용", "시청경험", "뽑기", "팝업방문"}
        for item in evidence
    )
    # 획득은 확인 필요가 기본이라 경험에 넣지 않는다. 구매완료·소지·시청·뽑기·팝업만 경험.
    author_exp = any(
        item["axis"] == "행동" and item["speaker"] == "작성자" and item["certainty"] == "확정"
        and item["label"] in {"구매완료", "소지사용", "시청경험", "뽑기", "팝업방문"}
        for item in evidence
    )
    personal_sale = bool(PERSONAL_SALE_RE.search(search))
    shop_speech = bool(SELL_SPEECH_RE.search(search) and (SHOP_CUE_RE.search(search) or SHOP_NEWS_RE.search(search) or "판매" in search))
    if personal_sale and SHOP_CUE_RE.search(search) and "양도" not in search and "팝니다" not in search and "급처" not in search:
        personal_sale = False
    info = bool(INFO_RE.search(search) or (SHOP_NEWS_RE.search(search) and not SELL_SPEECH_RE.search(search)))
    if author_react:
        labels.append(CTX_REACT)
        notes.append((CTX_REACT, squash(original)[:160], "작성자 평가·반응 표지가 있고 그 구절을 판매 문안으로만 보지 않았다."))
    if author_exp:
        labels.append(CTX_OWN)
        notes.append((CTX_OWN, squash(original)[:160], "작성자의 구매 완료, 사용, 시청, 뽑기, 팝업 방문 중 하나가 있다."))
    if shop_speech or (SHOP_NEWS_RE.search(search) and SELL_SPEECH_RE.search(search)):
        labels.append(CTX_SHOP)
        notes.append((CTX_SHOP, squash(original)[:160], "판매·입고·출시·이벤트 안내 표현이 있다. 그 문장의 호감을 작성자 감상으로 세지 않는다."))
    elif SELL_SPEECH_RE.search(search) and not personal_sale:
        labels.append(CTX_SHOP)
        notes.append((CTX_SHOP, squash(original)[:160], "판매 안내 표현이 있다."))
    if personal_sale:
        labels.append(CTX_SELL)
        notes.append((CTX_SELL, squash(original)[:160], "양도·교환·개인 판매 표현이 있다."))
    if re.search(r"공구(?:합니다|해요|해용|합니|함)|1차금|소분(?:합니다|해요)", search):
        recruit = CTX_SHOP if SHOP_CUE_RE.search(search) else CTX_SELL
        labels.append(recruit)
        notes.append((recruit, squash(original)[:160], "공동구매 모집이나 차수금이 있다. 구매 완료로 세지 않는다."))
    if info:
        labels.append(CTX_INFO)
        notes.append((CTX_INFO, squash(original)[:160], "출시 소식·출처·번역·공지처럼 정보를 전하는 표현이 있다."))
    if not labels:
        labels.append(CTX_UNK)
        notes.append((CTX_UNK, squash(original)[:160], "개인 감상, 구매 경험, 판매, 안내, 정보 전달을 본문만으로 정하지 못했다."))
    return list(dict.fromkeys(labels)), notes


def primary_context(labels: list[str]) -> str:
    substantive = [label for label in labels if label != CTX_UNK]
    if not substantive:
        return CTX_UNK
    if len(substantive) == 1:
        return substantive[0]
    return CTX_MIX


def self_check(kiwi: Kiwi) -> None:
    checks: list[tuple[str, str]] = []

    def run(text: str) -> dict:
        return analyze_post(text, kiwi)

    def author_behaviors(result: dict) -> set[str]:
        return {
            item["label"]
            for item in result["evidence"]
            if item["axis"] == "행동" and item["speaker"] == "작성자" and item["certainty"] == "확정"
        }

    def author_aspects(result: dict) -> set[str]:
        return {
            item["affection_aspect"]
            for item in result["evidence"]
            if item["axis"] == "호감" and item["speaker"] == "작성자"
        }

    sample = run("치이카와 너무 귀엽다")
    aspects = author_aspects(sample)
    if ASPECT_LOOK in aspects or "구매완료" in author_behaviors(sample):
        checks.append(("cute-only", "귀엽다를 외형이나 구매로 보면 안 된다"))
    if UNCLEAR_ASPECT not in aspects:
        checks.append(("cute-only-aspect", str(aspects)))

    sample = run("눈이 동그래 보여서 귀엽다")
    if not any(row["evidence_level"] == LEVEL_REASON and row["affection_aspect"] == ASPECT_LOOK for row in sample["connections"]):
        checks.append(("eyes", str(sample["connections"])))

    sample = run("생각보다 비싸서 결국 안삿따")
    behaviors = author_behaviors(sample)
    if "구매완료" in behaviors or "구매부정" not in behaviors:
        checks.append(("price-neg", str(behaviors)))
    if not any(row["evidence_level"] == LEVEL_REASON and row["barrier"] == "가격" for row in sample["connections"]):
        checks.append(("price-link", str(sample["connections"])))
    if any(item["speaker"] == "작성자" and item["target_type"] == "캐릭터" and item["polarity"] == "부정" for item in sample["evidence"]):
        checks.append(("price-not-character", "가격 부정을 캐릭터 비호감으로 봤다"))

    sample = run("치이카와 아크릴 판매합니다 귀여워요")
    if any(item["axis"] == "호감" and item["speaker"] == "작성자" for item in sample["evidence"]):
        checks.append(("promo", "판매 문장 호감을 작성자 감상으로 봤다"))

    sample = run("치이카와 아크릴 판매합니다\n정말 귀여워요")
    if any(item["axis"] == "호감" and item["speaker"] == "작성자" for item in sample["evidence"]):
        checks.append(("promo-line", "다음 줄 판매 문안을 작성자 감상으로 봤다"))

    sample = run("빤쮸우사기 마스코트 샀다")
    if any(item.startswith("등장인물:우사기") for item in sample["mention_labels"]):
        checks.append(("ppanchu", str(sample["mention_labels"])))
    if "구매완료" not in author_behaviors(sample):
        checks.append(("ppanchu-buy", str(author_behaviors(sample))))

    sample = run("이 장면은 시사하는 바가 크다")
    if any(item.startswith("등장인물:시사") for item in sample["mention_labels"]):
        checks.append(("shisa", str(sample["mention_labels"])))

    sample = run("내가 먼작귀에서 제일 좋아하는 시사야")
    if "구매희망" in author_behaviors(sample) or "구매완료" in author_behaviors(sample):
        checks.append(("shisa-ya", str(author_behaviors(sample))))
    if "등장인물:시사" not in sample["mention_labels"]:
        checks.append(("shisa-yes", str(sample["mention_labels"])))

    sample = run("귀여워서 소리질렀어")
    if "구매완료" in author_behaviors(sample):
        checks.append(("scream", str(author_behaviors(sample))))

    sample = run("결제일 기준 20일에서 30일. 결제완료되지 않은 주문은 취소됩니다")
    if "구매완료" in author_behaviors(sample):
        checks.append(("pay-template", str(author_behaviors(sample))))

    sample = run("룸메가 먼작귀 젤리 사옴")
    if "구매완료" in author_behaviors(sample):
        checks.append(("roommate", str([(item["label"], item["speaker"]) for item in sample["evidence"] if item["axis"] == "행동"])))

    sample = run("너어무 귀여워서 하치와레 살까 고민")
    if "구매고민" not in author_behaviors(sample) or "구매완료" in author_behaviors(sample):
        checks.append(("hesitate", str(author_behaviors(sample))))
    if not any(row["evidence_level"] == LEVEL_REASON and row["behavior"] == "구매고민" for row in sample["connections"]):
        checks.append(("hesitate-reason", str(sample["connections"])))

    sample = run("한정판 키링 나왔다")
    if any(row["evidence_level"] == LEVEL_REASON for row in sample["connections"]):
        checks.append(("limited", str(sample["connections"])))

    sample = run("치이카와가 브로콜리를 싫어한다")
    if any(item["axis"] == "호감" and item["speaker"] == "작성자" and item["polarity"] == "부정" for item in sample["evidence"]):
        checks.append(("story-hate", str(sample["evidence"])))

    sample = run("아는언니가 치이카와 좋아해서 책샀어")
    if "구매완료" in author_behaviors(sample):
        checks.append(("sister-buy", str([(item["label"], item["speaker"]) for item in sample["evidence"] if item["axis"] == "행동"])))

    sample = run("귀엽긴 하지만 비싸서 안 샀다")
    reason_rows = [row for row in sample["connections"] if row["evidence_level"] == LEVEL_REASON]
    if any("귀엽" in row["selection_reason"] for row in reason_rows):
        checks.append(("concessive", str(reason_rows)))
    if not any(row["barrier"] == "가격" for row in reason_rows):
        checks.append(("concessive-price", str(reason_rows)))

    sample = run("도와주는 하치와레가 너무 다정하다")
    if ASPECT_ACT not in author_aspects(sample):
        checks.append(("trait", str(author_aspects(sample))))
    if ASPECT_LOOK in author_aspects(sample):
        checks.append(("trait-look", str(author_aspects(sample))))

    sample = run("치이카와 책샀어")
    if "구매완료" not in author_behaviors(sample):
        checks.append(("book-buy", str(author_behaviors(sample))))

    sample = run("카니발 티켓 샀다")
    if any(item.startswith("등장인물:카니") for item in sample["mention_labels"]):
        checks.append(("kani", str(sample["mention_labels"])))

    sample = run("삿포로에서 치이카와 팝업을 걸었다")
    if "구매완료" in author_behaviors(sample):
        checks.append(("sapporo", str(author_behaviors(sample))))

    sample = run("하치와레가 닮았다 하고 샀을 생각에 귀엽다")
    if "구매완료" in author_behaviors(sample):
        checks.append(("would-have-bought", str(author_behaviors(sample))))

    sample = run("결국 하치와레 캐리어를 사버렸다")
    if "구매완료" not in author_behaviors(sample):
        checks.append(("sabbeoryeotda", str(author_behaviors(sample))))

    if checks:
        detail = "\n".join(f"{name}: {message}" for name, message in checks)
        raise SystemExit(f"self-check failed\n{detail}")


def read_table(path: Path, table: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype="string", encoding="utf-8-sig", na_filter=False, keep_default_na=False)
    raw.columns = [column.replace("\r", "") for column in raw.columns]
    expected = list(nz.TABLE_SPECS[table]["columns"])
    if list(raw.columns) != expected:
        raise ValueError(f"{table} columns {list(raw.columns)}")
    frame = pd.DataFrame(index=raw.index)
    for column in nz.STRING_BY_TABLE[table]:
        frame[column] = raw[column].astype("string")
    for column in nz.INT_BY_TABLE[table]:
        frame[column] = nz.parse_int_column(raw[column], (table, column) in nz.NULLABLE_INT, column)
    for column in nz.DATETIME_BY_TABLE.get(table, []):
        parsed = pd.to_datetime(raw[column], format="%Y-%m-%d %H:%M:%S%z")
        frame[column] = parsed.dt.tz_convert(nz.SEOUL)
        clock = raw[column].str.slice(0, 19)
        parsed_clock = frame[column].dt.strftime("%Y-%m-%d %H:%M:%S")
        if not bool((clock == parsed_clock).all()):
            raise ValueError(f"{column} timezone shift")
        if not bool(raw[column].str.endswith("+09:00").all()):
            raise ValueError(f"{column} offset is not +09:00")
    return frame[expected]


def pipe(values: list[str]) -> str:
    cleaned = [value for value in values if value and value not in {NA, NONE}]
    return "|".join(dict.fromkeys(cleaned))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    export = frame.copy()
    if "created_at" in export.columns:
        export["created_at"] = frame["created_at"].map(
            lambda value: "" if pd.isna(value) else value.isoformat(sep=" ", timespec="seconds")
        )
    export.to_csv(path, index=False, encoding="utf-8-sig", na_rep="", lineterminator="\n")


def write_both(path: Path, frame: pd.DataFrame) -> None:
    write_csv(path, frame)
    parquet_frame = frame.copy()
    frame.to_parquet(path.with_suffix(".parquet"), index=False)


def script_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


def load_inputs() -> pd.DataFrame:
    posts = read_table(NORM / "x_posts.csv", "x_posts")
    sources = read_table(NORM / "x_post_sources.csv", "x_post_sources")
    files = read_table(NORM / "x_source_files.csv", "x_source_files")
    keywords = read_table(NORM / "x_post_keywords.csv", "x_post_keywords")
    if len(posts) != posts["post_id"].nunique():
        raise ValueError("post_id duplicated")
    merged = posts.merge(sources, on="post_id", how="left", validate="one_to_one")
    merged = merged.merge(files, on="source_file", how="left", validate="many_to_one")
    if len(merged) != len(posts):
        raise ValueError("source join changed post count")
    ordered = keywords.sort_values(["post_id", "keyword_order"])
    keyword_map = ordered.groupby("post_id", sort=False)["keyword"].agg(lambda series: "|".join(series.astype(str)))
    merged["collection_keywords"] = merged["post_id"].map(keyword_map).fillna("").astype("string")
    merged["created_year_kst"] = merged["created_at"].dt.year.astype("int64")
    return merged


def checkpoint_path() -> Path:
    return WORK / "posts.jsonl"


def analyze_all(posts: pd.DataFrame, kiwi: Kiwi) -> tuple[list[dict], list[dict]]:
    WORK.mkdir(parents=True, exist_ok=True)
    path = checkpoint_path()
    digest = script_hash()
    done: dict[str, dict] = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("script_hash") == digest:
                    done[row["post_id"]] = row
    errors: list[dict] = []
    mode = "a" if done else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for index, record in enumerate(posts.itertuples(index=False), start=1):
            post_id = str(record.post_id)
            if post_id in done:
                continue
            try:
                result = analyze_post(str(record.text), kiwi)
                payload = {
                    "script_hash": digest,
                    "post_id": post_id,
                    "ok": True,
                    "result": {
                        "readable": result["readable"],
                        "mention_labels": result["mention_labels"],
                        "contexts": result["contexts"],
                        "evidence": result["evidence"],
                        "connections": result["connections"],
                        "reviews": result["reviews"],
                        "behavior_labels": result["behavior_labels"],
                        "author_aspects": result["author_aspects"],
                        "ip_in_post": result["ip_in_post"],
                    },
                }
            except Exception as exc:  # noqa: BLE001
                payload = {
                    "script_hash": digest,
                    "post_id": post_id,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "trace": traceback.format_exc(limit=8),
                }
                errors.append({"post_id": post_id, "error": payload["error"]})
            done[post_id] = payload
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            if index % 250 == 0:
                handle.flush()
                print(f"processed {index}/{len(posts)}", flush=True)
    ordered_results = []
    ordered_errors = []
    for record in posts.itertuples(index=False):
        post_id = str(record.post_id)
        payload = done.get(post_id)
        if payload is None:
            ordered_errors.append({"post_id": post_id, "error": "checkpoint missing"})
            continue
        if not payload.get("ok"):
            ordered_errors.append({"post_id": post_id, "error": payload.get("error", "unknown")})
        ordered_results.append(payload)
    return ordered_results, ordered_errors


def build_frames(posts: pd.DataFrame, results: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    by_id = {row["post_id"]: row for row in results}
    post_rows = []
    evidence_rows = []
    connection_rows = []
    review_rows = []
    evidence_seq = 1
    connection_seq = 1
    for record in posts.itertuples(index=False):
        post_id = str(record.post_id)
        payload = by_id[post_id]
        if not payload.get("ok"):
            post_rows.append({
                "post_id": post_id,
                "post_url": record.post_url,
                "account_id": record.account_id,
                "account_name": record.account_name,
                "text": record.text,
                "analysis_text": "",
                "created_at": record.created_at,
                "created_year_kst": int(record.created_year_kst),
                "comment_count": record.comment_count,
                "repost_count": record.repost_count,
                "view_count": record.view_count,
                "like_count": record.like_count,
                "source_file": record.source_file,
                "source_row": record.source_row,
                "source_year": record.source_year,
                "collection_keywords": record.collection_keywords,
                "mention_labels": "",
                "ip_in_text": "아니오",
                "context_labels": "",
                "context_primary": "",
                "author_affection_aspects": "",
                "behavior_labels": "",
                "processing_status": "처리 실패",
                "review_flag": "예",
                "review_reasons": payload.get("error", ""),
                "decision_method": DECISION_METHOD,
                "codebook_version": CODEBOOK_VERSION,
            })
            continue
        result = payload["result"]
        local_to_id: dict[int, str] = {}
        for local_index, item in enumerate(result["evidence"]):
            evidence_id = f"E{evidence_seq:06d}"
            evidence_seq += 1
            local_to_id[local_index] = evidence_id
            evidence_rows.append({
                "evidence_id": evidence_id,
                "post_id": post_id,
                "quote": item["quote"],
                "match_text": item["match_text"],
                "quote_start": item["quote_start"],
                "quote_end": item["quote_end"],
                "axis": item["axis"],
                "label": item["label"],
                "polarity": item["polarity"],
                "target_entity": item["target_entity"],
                "target_type": item["target_type"],
                "affection_aspect": item["affection_aspect"],
                "speaker": item["speaker"],
                "product_form": item["product_form"],
                "use_mode": item["use_mode"],
                "selection_reason": item["selection_reason"],
                "collection_reason": item["collection_reason"],
                "behavior": item["behavior"],
                "barrier": item["barrier"],
                "certainty": item["certainty"],
                "about_ip": "예" if item["about_ip"] else "아니오",
                "judgment_method": item["judgment_method"],
                "judgment_note": item["judgment_note"],
                "codebook_version": CODEBOOK_VERSION,
            })
        for item in result["connections"]:
            connection_id = f"C{connection_seq:06d}"
            connection_seq += 1
            connection_rows.append({
                "connection_id": connection_id,
                "post_id": post_id,
                "link_family": item["link_family"],
                "left_label": item["left_label"],
                "right_label": item["right_label"],
                "target_entity": item["target_entity"],
                "affection_aspect": item["affection_aspect"],
                "product_form": item["product_form"],
                "behavior": item["behavior"],
                "barrier": item["barrier"],
                "selection_reason": item["selection_reason"],
                "evidence_level": item["evidence_level"],
                "speaker": item["speaker"],
                "quote": item["quote"],
                "judgment_method": item["judgment_method"],
                "judgment_note": item["judgment_note"],
                "codebook_version": CODEBOOK_VERSION,
            })
        contexts = result["contexts"]
        review_reasons = result["reviews"]
        if review_reasons:
            review_rows.append({
                "post_id": post_id,
                "review_reasons": "|".join(review_reasons),
                "quote": squash(str(record.text))[:240],
                "context_primary": primary_context(contexts),
            })
        post_rows.append({
            "post_id": post_id,
            "post_url": record.post_url,
            "account_id": record.account_id,
            "account_name": record.account_name,
            "text": record.text,
            "analysis_text": result["readable"],
            "created_at": record.created_at,
            "created_year_kst": int(record.created_year_kst),
            "comment_count": record.comment_count,
            "repost_count": record.repost_count,
            "view_count": record.view_count,
            "like_count": record.like_count,
            "source_file": record.source_file,
            "source_row": record.source_row,
            "source_year": record.source_year,
            "collection_keywords": record.collection_keywords,
            "mention_labels": pipe(result["mention_labels"]),
            "ip_in_text": "예" if result["ip_in_post"] else "아니오",
            "context_labels": pipe(contexts),
            "context_primary": primary_context(contexts),
            "author_affection_aspects": pipe(result["author_aspects"]),
            "behavior_labels": pipe(result["behavior_labels"]),
            "processing_status": "완료",
            "review_flag": "예" if review_reasons else "아니오",
            "review_reasons": "|".join(review_reasons),
            "decision_method": DECISION_METHOD,
            "codebook_version": CODEBOOK_VERSION,
        })
    post_frame = pd.DataFrame(post_rows)
    evidence_frame = pd.DataFrame(evidence_rows)
    connection_frame = pd.DataFrame(connection_rows)
    review_frame = pd.DataFrame(review_rows)
    return post_frame, evidence_frame, connection_frame, review_frame


def agg_base(unit: str, denominator_name: str, denominator_value: int, overlap: str) -> dict:
    return {
        "agg_unit": unit,
        "denominator_name": denominator_name,
        "denominator_value": denominator_value,
        "multi_label_overlap": overlap,
    }


def build_aggs(posts: pd.DataFrame, evidence: pd.DataFrame, connections: pd.DataFrame) -> dict[str, pd.DataFrame]:
    n = len(posts)
    year_n = posts.groupby("created_year_kst")["post_id"].nunique().to_dict()
    author_aff = evidence[(evidence["axis"] == "호감") & (evidence["speaker"] == "작성자") & (evidence["about_ip"] == "예")].copy()
    rows = []
    for (aspect, polarity, target_type), part in author_aff.groupby(["affection_aspect", "polarity", "target_type"], dropna=False):
        row = agg_base("표현 건수와 고유 게시물 수", "본문에 IP가 있거나 대상이 IP인 작성자 호감 표현의 모집단 게시물", n, "한 게시물에 측면이 여럿이면 게시물 수 합이 전체보다 클 수 있다")
        row.update({
            "affection_aspect": aspect,
            "polarity": polarity,
            "target_type": target_type,
            "evidence_count": int(len(part)),
            "post_count": int(part["post_id"].nunique()),
        })
        rows.append(row)
    affection = pd.DataFrame(rows).sort_values(["post_count", "evidence_count"], ascending=False) if rows else pd.DataFrame()

    charm_rows = []
    charm = connections[(connections["link_family"].isin(["매력×행동", "특징×호감"])) & (connections["speaker"] == "작성자")].copy()
    if len(charm):
        for keys, part in charm.groupby(["link_family", "affection_aspect", "behavior", "evidence_level", "selection_reason"], dropna=False):
            row = agg_base("연결 건수와 고유 게시물 수", "입력 게시물", n, "연결 단위. 게시물당 여러 연결이 있을 수 있다")
            row.update({
                "link_family": keys[0],
                "affection_aspect": keys[1],
                "behavior": keys[2],
                "evidence_level": keys[3],
                "selection_reason": keys[4],
                "connection_count": int(len(part)),
                "post_count": int(part["post_id"].nunique()),
            })
            charm_rows.append(row)
    charm_agg = pd.DataFrame(charm_rows)
    if len(charm_agg):
        charm_agg = charm_agg.sort_values(["evidence_level", "connection_count"], ascending=[True, False])

    form_rows = []
    forms = connections[(connections["link_family"] == "형태×선택이유") & (connections["speaker"] == "작성자")].copy()
    if len(forms):
        for keys, part in forms.groupby(["product_form", "selection_reason", "behavior", "evidence_level"], dropna=False):
            row = agg_base("연결 건수와 고유 게시물 수", "입력 게시물", n, "이유 언급 없음은 같은 위치의 공존이지 선택 이유가 아니다")
            row.update({
                "product_form": keys[0],
                "selection_reason": keys[1],
                "behavior": keys[2],
                "evidence_level": keys[3],
                "connection_count": int(len(part)),
                "post_count": int(part["post_id"].nunique()),
            })
            form_rows.append(row)
    form_agg = pd.DataFrame(form_rows)
    if len(form_agg):
        form_agg = form_agg.sort_values(["evidence_level", "connection_count"], ascending=[True, False])

    buy_labels = {"구매완료", "구매희망", "구매고민", "구매부정", "구매포기", "소장희망"}
    buy = connections[(connections["behavior"].isin(buy_labels)) & (connections["speaker"] == "작성자")].copy()
    buy_rows = []
    if len(buy):
        buy["barrier_filled"] = buy["barrier"].where(buy["barrier"] != NONE, "장벽 언급 없음")
        for keys, part in buy.groupby(["behavior", "barrier_filled", "evidence_level"], dropna=False):
            row = agg_base("연결 건수와 고유 게시물 수", "입력 게시물", n, "장벽 언급 없음은 구매 표현만 있고 장벽 이유가 확인되지 않은 연결")
            row.update({
                "behavior": keys[0],
                "barrier": keys[1],
                "evidence_level": keys[2],
                "connection_count": int(len(part)),
                "post_count": int(part["post_id"].nunique()),
            })
            buy_rows.append(row)
    buy_agg = pd.DataFrame(buy_rows)
    if len(buy_agg):
        buy_agg = buy_agg.sort_values(["connection_count"], ascending=False)

    context_rows = []
    for context in [CTX_REACT, CTX_OWN, CTX_SHOP, CTX_SELL, CTX_INFO, CTX_UNK]:
        mask = posts["context_labels"].fillna("").map(lambda value: context in str(value).split("|"))
        part = posts[mask]
        def has_behavior(frame: pd.DataFrame, label: str) -> int:
            return int(frame["behavior_labels"].fillna("").map(lambda value: label in str(value).split("|")).sum())
        row = agg_base("고유 게시물 수", "해당 맥락 라벨이 있는 게시물. 복수 맥락은 각 행에 다시 센다", int(len(part)), "복수 맥락 게시물은 여러 행에 들어 간다. 비율 합은 100%를 넘을 수 있다")
        row.update({
            "context_label": context,
            "post_count": int(len(part)),
            "share_of_input": round(len(part) / n, 4) if n else 0,
            "author_explicit_look_posts": int(part["author_affection_aspects"].fillna("").map(lambda value: ASPECT_LOOK in str(value).split("|")).sum()),
            "author_unclear_aspect_posts": int(part["author_affection_aspects"].fillna("").map(lambda value: UNCLEAR_ASPECT in str(value).split("|")).sum()),
            "purchase_done_posts": has_behavior(part, "구매완료"),
            "purchase_wish_posts": has_behavior(part, "구매희망"),
            "purchase_hesitate_posts": has_behavior(part, "구매고민"),
            "purchase_neg_posts": has_behavior(part, "구매부정"),
        })
        context_rows.append(row)
    primary = posts["context_primary"].value_counts()
    for label, count in primary.items():
        row = agg_base("고유 게시물 수", "context_primary 상호배타", n, "혼합은 한 번만 센다. 위 행과 분모가 다르다")
        row.update({
            "context_label": f"primary:{label}",
            "post_count": int(count),
            "share_of_input": round(int(count) / n, 4),
            "author_explicit_look_posts": pd.NA,
            "author_unclear_aspect_posts": pd.NA,
            "purchase_done_posts": pd.NA,
            "purchase_wish_posts": pd.NA,
            "purchase_hesitate_posts": pd.NA,
            "purchase_neg_posts": pd.NA,
        })
        context_rows.append(row)
    context_agg = pd.DataFrame(context_rows)

    content = evidence[evidence["axis"] == "콘텐츠이용"].copy()
    content_rows = []
    if len(content):
        for (label, speaker), part in content.groupby(["label", "speaker"], dropna=False):
            row = agg_base("표현 건수와 고유 게시물 수", "입력 게시물", n, "한 게시물에 이용 방식이 여럿일 수 있다")
            row.update({
                "content_use": label,
                "speaker": speaker,
                "evidence_count": int(len(part)),
                "post_count": int(part["post_id"].nunique()),
            })
            content_rows.append(row)
    content_agg = pd.DataFrame(content_rows)
    if len(content_agg):
        content_agg = content_agg.sort_values("post_count", ascending=False)

    year_rows = []
    for year, part in posts.groupby("created_year_kst"):
        row = agg_base("고유 게시물 수", "해당 한국시간 작성 연도의 입력 게시물", int(len(part)), "연도 안에서도 복수 라벨 합은 분모를 넘을 수 있다")
        ids = set(part["post_id"])
        aff = author_aff[author_aff["post_id"].isin(ids)] if len(author_aff) else author_aff
        row.update({
            "created_year_kst": int(year),
            "post_count": int(len(part)),
            "view_null_posts": int(part["view_count"].isna().sum()),
            "source_year_mismatch_posts": int((part["source_year"].astype("int64") != part["created_year_kst"]).sum()),
            "author_positive_posts": int(aff[aff["polarity"] == "긍정"]["post_id"].nunique()) if len(aff) else 0,
            "explicit_look_posts": int(part["author_affection_aspects"].fillna("").map(lambda value: ASPECT_LOOK in str(value).split("|")).sum()),
            "unclear_aspect_posts": int(part["author_affection_aspects"].fillna("").map(lambda value: UNCLEAR_ASPECT in str(value).split("|")).sum()),
            "purchase_done_posts": int(part["behavior_labels"].fillna("").map(lambda value: "구매완료" in str(value).split("|")).sum()),
            "purchase_wish_posts": int(part["behavior_labels"].fillna("").map(lambda value: "구매희망" in str(value).split("|")).sum()),
            "purchase_neg_posts": int(part["behavior_labels"].fillna("").map(lambda value: "구매부정" in str(value).split("|")).sum()),
        })
        year_rows.append(row)
    year_agg = pd.DataFrame(year_rows).sort_values("created_year_kst")
    _ = year_n
    return {
        "agg_affection_target": affection,
        "agg_charm_by_behavior": charm_agg,
        "agg_form_by_reason": form_agg,
        "agg_purchase_by_barrier": buy_agg,
        "agg_context_comparison": context_agg,
        "agg_content_use": content_agg,
        "agg_by_year": year_agg,
    }


def token_frequency(posts: pd.DataFrame, kiwi: Kiwi) -> pd.DataFrame:
    stop = {"하", "되", "있", "오", "가", "싶", "않", "수", "것", "등", "거", "나", "내", "저", "제", "좀", "더", "또", "안", "못", "수", "때", "중"}
    counts: Counter[tuple[str, str]] = Counter()
    post_counts: Counter[tuple[str, str]] = Counter()
    keywords = set()
    for value in posts["collection_keywords"].fillna(""):
        keywords.update(str(value).split("|"))
    for text in posts["analysis_text"].fillna(""):
        seen = set()
        for token in kiwi.tokenize(str(text)):
            if token.tag not in {"NNG", "NNP", "VV", "VA", "MAG"}:
                continue
            if token.form in stop or len(token.form) < 2:
                continue
            key = (token.form, token.tag)
            counts[key] += 1
            seen.add(key)
        for key in seen:
            post_counts[key] += 1
    rows = []
    for (form, tag), count in counts.most_common(80):
        rows.append({
            "token": form,
            "pos": tag,
            "token_count": count,
            "post_count": post_counts[(form, tag)],
            "surface_is_collection_keyword": "예" if form in keywords or form == "파자마" else "아니오",
            "agg_unit": "형태소 출현 횟수와 고유 게시물 수",
            "denominator_name": "입력 게시물",
            "denominator_value": len(posts),
            "note": "빈도이며 호감·구매 라벨이 아니다. 수집 키워드 표면은 별도 표시한다.",
        })
    return pd.DataFrame(rows)


def previous_purchase_compare(posts: pd.DataFrame) -> pd.DataFrame:
    old_path = BASE / "text_analysis" / "label_pass" / "output" / "x_posts_text_analysis.parquet"
    old = pd.read_parquet(old_path, columns=["post_id", "action_labels_json"])
    def has(raw: str, label: str) -> bool:
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError:
            return False
        return any(item.get("label") == label and item.get("audience") == "user" and not item.get("needs_review") for item in rows)
    old["old_buy"] = old["action_labels_json"].map(lambda value: has(value, "구매완료"))
    old["old_wish"] = old["action_labels_json"].map(lambda value: has(value, "구매희망"))
    merged = posts.merge(old[["post_id", "old_buy", "old_wish"]], on="post_id", how="left", validate="one_to_one")
    merged["new_buy"] = merged["behavior_labels"].fillna("").map(lambda value: "구매완료" in str(value).split("|"))
    merged["new_wish"] = merged["behavior_labels"].fillna("").map(lambda value: "구매희망" in str(value).split("|"))
    rows = []
    for kind, old_col, new_col in (
        ("구매완료", "old_buy", "new_buy"),
        ("구매희망", "old_wish", "new_wish"),
    ):
        both = int((merged[old_col] & merged[new_col]).sum())
        old_only = merged[merged[old_col] & ~merged[new_col]]
        new_only = merged[~merged[old_col] & merged[new_col]]
        rows.append({
            "label": kind,
            "previous_user_confirmed": int(merged[old_col].sum()),
            "this_analysis_author_confirmed": int(merged[new_col].sum()),
            "both": both,
            "previous_only": int(len(old_only)),
            "this_only": int(len(new_only)),
            "note": "이전 라벨은 정답이 아니다. 정의 차이와 오탐 후보를 대조한 것이다.",
        })
        for side, part in (("previous_only", old_only), ("this_only", new_only)):
            for record in part.itertuples(index=False):
                rows.append({
                    "label": kind,
                    "previous_user_confirmed": "",
                    "this_analysis_author_confirmed": "",
                    "both": "",
                    "previous_only": "",
                    "this_only": "",
                    "note": side,
                    "post_id": record.post_id,
                    "behavior_labels": record.behavior_labels,
                    "quote": squash(str(record.text))[:220],
                })
    return pd.DataFrame(rows)


def example_quotes(evidence: pd.DataFrame, posts: pd.DataFrame, mask: pd.Series, limit: int = 3) -> list[str]:
    part = evidence[mask].copy()
    if not len(part):
        return []
    likes = posts.set_index("post_id")["like_count"]
    part["like_count"] = part["post_id"].map(likes)
    part = part.sort_values("like_count", ascending=False)
    lines = []
    seen = set()
    for record in part.itertuples(index=False):
        key = (record.post_id, record.quote)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{record.quote} (post_id {record.post_id})")
        if len(lines) >= limit:
            break
    return lines


def write_codebook() -> None:
    text = f"""# 심층 분석 기준서

- 기준 버전: `{CODEBOOK_VERSION}`
- 판정 방법: `{DECISION_METHOD}`
- 이 버전은 게시물 5,000건에 같은 규칙을 적용한다. 게시물마다 사람이 라벨을 고쳐 넣은 값은 없다.

## 변경 이력

| 버전 | 내용 |
| --- | --- |
| 2026-10-30.1 | 전체 재분석. 귀엽다만으로 외형 호감을 만들지 않는다. 이유 연결어가 있는 구절만 명시적 이유로 둔다. 구매완료는 작성자 완료 동사만, 겟·데려오다·살까·갖고 싶다는 분리한다. |
| 2026-10-30.2 | 같은 규칙을 전체 게시물에 다시 적용. 삿포로의 삿과 샀을 추정을 구매완료에서 제외하고 사버렸다를 넣었다. 형태소 명사만으로 호감 측면을 기타로 올리지 않는다. 눈을 뜨다 같은 눈은 외형이 아니다. 발매·구매가능 문안 호감은 홍보문구. 구합니다는 확정 구매희망. 구매 희망·부정은 감상 맥락에 포함한다. |
| 2026-10-30.3 | 측면이 '구체적 대상 확인 불가'인 것 자체는 확인 필요 게시물로 세지 않는다. 확인 필요는 동음이의어, 여러 상품의 행동 연결, 사서·꿈·배송상태표·겟처럼 완료로 단정하지 않은 행동만 남긴다. 스티커의 동글한 컷은 상품 구현으로 둔다. |
| 2026-10-30.4 | 샀던, 사버림을 구매완료에 포함한다. 형태소는 내용어 빈도에만 쓰고 호감 측면을 정하지 않는다. |

## 분석 단위와 텍스트

- 단위는 `post_id` 1개다. `x_post_keywords` 7,466행으로 게시물이나 반응을 세지 않는다.
- 원문 `text`는 바꾸지 않는다. `analysis_text`만 URL, 멘션, `#`을 공백으로 만든다.
- 이모지, ㅋㅋ, ㅠㅠ, 부정, 반복 글자는 삭제하지 않는다. ㅋㅋ나 이모지만으로 유머·슬픔 라벨을 만들지 않는다.
- 계정 이름 문자열 `null`은 결측이 아니다. 조회수 결측 게시물도 빼지 않는다.
- 연도는 `created_at`의 한국시간 연도다. `source_year`는 원본 파일 연도라 대체하지 않는다.
- 검색 키워드는 `collection_keywords`에만 남긴다. 본문 언급으로 복사하지 않는다.

## 언급

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 작품:먼작귀 | 먼작귀 | 캐릭터로 합치지 않음 |
| 작품:치이카와 | 치이카와 계열 이름이 애니·영화·만화·극장·더빙·시리즈·세계관과 같은 구절 | 이름만 있는 경우 |
| 등장인물:치이카와 | 같은 가까운 구간에 다른 등장인물이 있음 | 작품 단서 구절 |
| 구분불가:치이카와이름 | 이름만 있어 작품과 주인공을 가르지 못함 | 검색 키워드만 있는 경우 |
| 등장인물:하치와레 등 | 하치와레/하치와래, 우사기, 모몽가/모몬가, 랏코, 쿠리만쥬/쿠리만주, 아노코, 데카츠요, 갑옷씨·갑옷 아저씨·갑옷상 | 빤쮸우사기, 시사하는, 카니발, 파자마 단독 |
| 시사·카니 | 게시물에 다른 치이카와 단서가 있을 때만 | 단서가 없으면 확인 필요 |
| 다른 IP | 농담곰, 파자마 파티즈, 빤쮸토끼 | 치이카와 라벨로 합치지 않음 |

짧은 호칭 `치이`, `하치`, `가르마`, `토끼`는 자동으로 합치지 않는다. 복수 라벨을 허용한다.

## 게시 맥락

복수 라벨을 허용한다. 두 개 이상이면 `context_primary`는 `혼합`이다.

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 개인 감상·반응 | 작성자 호감·반응 표지. 판매 문안이 아닌 구절 | 판매합니다 구절의 귀엽다, 계정 이름으로 팬 단정 |
| 개인 구매·사용·소장 경험 | 작성자의 구매완료, 소지사용, 시청경험, 뽑기, 팝업 방문 | 희망만 있는 글, 타인·작중 구매 |
| 판매·입고·출시·이벤트 안내 | 판매 안내, 예약, 스마트스토어, 출시·발매가 판매 문장과 함께 있음 | 옷 입고, 개인 양도만 있는 글 |
| 개인 판매·교환 | 양도, 팝니다, 급처, 교환합니다 | 작중 교환하자 |
| 정보 공유·인용·재전달 | 출처, 번역, 공지, 출시 소식을 판매 문장 없이 전함 | 작성자 감상만 있는 글 |
| 판단 불가 | 위 단서가 없음 | 처리 실패가 아님 |

`입고` 단독은 입고 안내가 아니다. `재입고`, `입고되었`만 안내 단서로 본다.

## 호감의 대상과 측면

긍정·부정 표현을 찾고, 같은 구절의 특징 단어가 있을 때만 측면을 정한다.

| 측면 | 포함할 때 | 제외 |
| --- | --- | --- |
| 캐릭터 외형 | 얼굴, 표정, 눈, 볼, 동글, 꼬리처럼 부위·형태가 있음 | 귀엽다, 예쁘다, 좋아한다만 있는 경우 |
| 행동·성격 | 기특, 다정, 착하다, 말투, 대사, 실수 | 작중 주어의 감정은 작성자 비호감이 아님 |
| 관계성·이야기 | 케미, 우정, 친구 사이, 명장면 | 트친, 친구 단독 |
| 상품 디자인·구현 | 재질, 마감, 투명, 포즈, 의상, 크기가 상품 명사와 함께 있음 | 디자인 단어만 있고 평가가 없는 경우 |
| 기타 구체적 대상 | 가격, 맛, 발견, 정서처럼 대상이 따로 있음 | 가격 불만을 캐릭터 비호감으로 옮기지 않음 |
| 구체적 대상 확인 불가 | 호감 단어는 있으나 측면 단어가 없음 | 외형 호감으로 올리지 않음 |

판매·안내 구절의 호감은 `speaker=홍보문구`다. 작성자 집계에 넣지 않는다. 작중 주어의 싫어하다·좋아하다는 `speaker=작중`이다.

## 행동

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 구매완료 | 샀다, 사왔다, 구매했다, 구입했다, 결제했다, 질렀다 | 안 샀다, 사고 싶다, 살까, 겟했다, 소리질렀다, 결제일 안내, 타인·작중 주어 |
| 구매희망 | 사고 싶다, 사야지, 사야겠다, 구합니다, 삽니다, 양도받겠다 | 살까, 갖고 싶다, 구매 완료, 안내 문안의 구함 |
| 구매고민 | 살까, 살래 | 구매희망 합계에 넣지 않음 |
| 구매부정 | 안 샀다, 못 샀다, 안 삼 | 구매완료 |
| 구매포기 | 사기 포기, 포기했다 | 포기 권유 문안 |
| 소장희망 | 갖고 싶다, 가지고 싶다 | 사고 싶다와 별도 |
| 획득 | 겟했다, 득템, 데려왔다 | 구매완료로 승격하지 않음. 확인 필요 |
| 뽑기 | 뽑았다 | 구매완료로 승격하지 않음 |
| 소지사용 | 언박싱, 개봉했다, 소장 중, 달고 다님 | 미개봉 판매 문구, 판매 글의 도착 안내 |
| 시청경험·시청희망 | 애니·영화·만화를 봤다 / 보고 싶다 | 등장인물이 바라본다는 문장 |
| 개인판매교환 | 양도합니다, 팝니다, 교환합니다, 급처 | 작성자 구매가 아님 |
| 공구 | 공구 | 구매완료·판매량이 아님 |
| 단순 언급 | IP는 있으나 위 확정 행동이 없음 | 행동 표현이 있는 글 |

`사서`는 확인 필요라 확정 구매완료에 넣지 않는다. `삿포로`의 삿, `샀을 생각`은 구매완료가 아니다. `사버렸다`는 구매완료다. 꿈·상상 문장의 구매와 배대지·통관 상태표의 구매완료는 확인 필요다.

## 근거 수준

| 수준 | 의미 |
| --- | --- |
| 명시적 이유 설명 | 아서·어서·해서·때문에·니까·라서·길래 앞의 이유가 바로 뒤 행동이나 호감에 붙음. 지만·는데 앞의 말은 이유로 붙이지 않음 |
| 문장·구절 내 연결 | 같은 구절에 대상과 행동이 있음. 이유 연결어가 없으면 선택 이유는 언급 없음 |
| 게시글 내 공존 | 게시물에 형태와 구매 계열 행동이 하나씩뿐이라 공존만 기록. 여러 상품이 있으면 만들지 않음 |

명시적 이유는 작성자가 밝힌 표현이다. 실제 원인으로 입증되었다고 쓰지 않는다. `한정`은 이유 구절에 있을 때만 이유로 남긴다.

## 콘텐츠 이용

장면·대사, 이 글에서 직접 말한 반복 시청, 일상 비유, 공유·추천, 관계·다음 이야기만 기록한다. 여러 게시물에 같은 대사가 반복된다는 이유로 한 사람의 반복 소비나 충성도로 해석하지 않는다.

## 형태소

Kiwi 사용자 사전으로 이름·상품명을 보호하고 내용어 빈도를 낸다. 호감 측면, 구매, 이유의 최종 라벨은 구절 규칙이다. 형태소 명사만으로 측면을 만들지 않는다.

## 집계

- 게시물 비율의 분모는 5,000이다.
- 표현·연결 표는 건수와 고유 게시물 수를 같이 적는다.
- 복수 라벨이라 비율 합이 100%를 넘을 수 있다.
- 개인 반응과 홍보 문안은 `speaker`로 나눈다.
- 정답 데이터가 없으므로 정확도 수치를 만들지 않는다.
"""
    (DOCS / "analysis_codebook.md").write_text(text, encoding="utf-8")


def write_definitions() -> None:
    text = """# 심층 분석 출력 테이블 정의

분석 단위는 게시물 `post_id`다. 검색 키워드 테이블과 조인하면 행이 늘어나므로, 게시물 수와 좋아요·조회수 합계는 조인 전에 계산한다.

## 관계

- `x_posts_deep_analysis.post_id` 1행 = 게시물 1개
- `x_post_evidence.post_id` → 게시물. 한 게시물에 근거가 여러 행
- `x_post_connections.post_id` → 게시물. 한 게시물에 연결이 여러 행
- 근거와 연결은 서로 다른 사실이라 evidence_id로 강제 조인하지 않는다. 연결의 근거 문장은 `quote`에 있다.

## x_posts_deep_analysis

| 컬럼 | 자료형 | 설명 |
| --- | --- | --- |
| post_id | 문자열 | 기본키 |
| text | 문자열 | 원문. 수정하지 않음 |
| analysis_text | 문자열 | URL·멘션을 뺀 읽기용 텍스트 |
| created_at | 타임존 있는 시각 | 한국시간. CSV는 `YYYY-MM-DD HH:MM:SS+09:00` |
| created_year_kst | 정수 | 한국시간 연도. 연도 분석은 이 컬럼 |
| source_year | 정수 | 원본 파일 연도. 작성 연도로 쓰지 않음 |
| view_count | 정수, 결측 허용 | 빈 값은 0이 아님 |
| account_name | 문자열 | 문자열 `null`은 결측이 아님 |
| collection_keywords | 문자열 | 수집 조건. 언급·선호가 아님. `|`로 연결 |
| context_labels | 문자열 | 복수 맥락. `|` 구분. 이 컬럼을 펼치면 게시물이 늘어난다 |
| context_primary | 문자열 | 하나면 그 맥락, 둘 이상이면 혼합, 없으면 판단 불가 |
| author_affection_aspects | 문자열 | 작성자 긍정 호감의 측면. 홍보 문안 제외 |
| behavior_labels | 문자열 | 작성자·확정 행동만. 확인 필요 행동은 여기 없고 근거 테이블에 있다 |
| processing_status | 문자열 | 완료 또는 처리 실패 |
| review_flag | 문자열 | 예 또는 아니오. 실패가 아님 |

Power BI에서 게시물 수를 셀 때는 이 테이블의 `post_id`를 센다. `context_labels`를 분할한 뒤 게시물 수를 합하면 혼합 글이 두 번 들어간다. 상호배타 구성은 `context_primary`를 쓴다.

## x_post_evidence

한 행은 근거 표현 1개다. 게시물 수가 아니다.

| 컬럼 | 설명 |
| --- | --- |
| evidence_id | 근거 키 |
| quote | 원문 LF 기준 앞뒤 문맥. 내부 공백은 한 칸으로 줄였다 |
| match_text | 규칙이 맞은 표면 |
| axis | 게시맥락, 호감, 형태, 행동, 사용, 수집, 콘텐츠이용 |
| speaker | 작성자, 홍보문구, 작중, 타인, 해당없음 |
| affection_aspect | 호감 행이 아니면 해당없음 |
| selection_reason, barrier, use_mode, collection_reason | 그 표현에 없으면 언급 없음 |
| certainty | 확정 또는 확인 필요 |
| about_ip | 아니오이면 치이카와 계열 집계에서 뺀다 |

작성자 호감 집계는 `axis=호감`, `speaker=작성자`, `about_ip=예`다.

## x_post_connections

한 행은 연결 1개다.

| 컬럼 | 설명 |
| --- | --- |
| connection_id | 연결 키 |
| link_family | 매력×행동, 특징×호감, 형태×선택이유, 구매×장벽, 상황×행동 |
| evidence_level | 명시적 이유 설명, 문장·구절 내 연결, 게시글 내 공존 |
| selection_reason | 명시적 이유가 아니면 언급 없음 |
| speaker | 작성자가 아닌 연결은 작성자 집계에서 뺀다 |

`selection_reason=언급 없음`인 형태×행동 행을 선택 이유 순위로 쓰면 안 된다.

## 집계 CSV

파일은 `output/agg/`에 있다. 모든 집계에 `agg_unit`, `denominator_name`, `denominator_value`, `multi_label_overlap`이 있다.

- `agg_affection_target`: 작성자 호감 표현
- `agg_charm_by_behavior`: 매력·특징과 행동의 연결
- `agg_form_by_reason`: 형태와 선택 이유. 이유 없음 포함
- `agg_purchase_by_barrier`: 구매 계열 행동과 장벽
- `agg_context_comparison`: 맥락 라벨별 게시물. `primary:` 행은 상호배타
- `agg_content_use`: 콘텐츠 이용 표현
- `agg_by_year`: 한국시간 작성 연도. 연도별 최대 1,000건 표본

## 반응 지표

좋아요, 리포스트, 댓글, 조회수는 게시물 테이블에만 있다. 근거·연결 테이블과 조인한 뒤 합계를 내면 한 게시물의 반응이 근거 수만큼 늘어난다. 합계 전에 게시물 단위로 되돌려야 한다.

## 결측

CSV의 빈 칸은 조회수 결측이다. Parquet는 `Int64` 결측과 시간대를 유지한다.
"""
    (DOCS / "output_table_definitions.md").write_text(text, encoding="utf-8")


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def write_report(
    posts: pd.DataFrame,
    evidence: pd.DataFrame,
    connections: pd.DataFrame,
    aggs: dict[str, pd.DataFrame],
    compare: pd.DataFrame,
    errors: pd.DataFrame,
    reviews: pd.DataFrame,
    tokens: pd.DataFrame,
) -> None:
    n = len(posts)
    done = int((posts["processing_status"] == "완료").sum())
    failed = int((posts["processing_status"] == "처리 실패").sum())
    review_n = int((posts["review_flag"] == "예").sum())
    view_null = int(posts["view_count"].isna().sum())
    null_name = int((posts["account_name"] == "null").sum())
    year_mismatch = int((posts["source_year"].astype("int64") != posts["created_year_kst"]).sum())

    def post_has(column: str, label: str) -> int:
        return int(posts[column].fillna("").map(lambda value: label in str(value).split("|")).sum())

    author = evidence[(evidence["axis"] == "호감") & (evidence["speaker"] == "작성자") & (evidence["about_ip"] == "예")]
    promo = evidence[(evidence["axis"] == "호감") & (evidence["speaker"] == "홍보문구")]
    aspect_posts = author.groupby("affection_aspect")["post_id"].nunique().sort_values(ascending=False)
    buy_done = post_has("behavior_labels", "구매완료")
    buy_wish = post_has("behavior_labels", "구매희망")
    buy_hes = post_has("behavior_labels", "구매고민")
    buy_neg = post_has("behavior_labels", "구매부정")
    buy_drop = post_has("behavior_labels", "구매포기")
    own_wish = post_has("behavior_labels", "소장희망")
    explicit = connections[(connections["evidence_level"] == LEVEL_REASON) & (connections["speaker"] == "작성자")]
    explicit_charm = explicit[explicit["link_family"].isin(["매력×행동", "특징×호감"])]
    explicit_barrier = explicit[explicit["link_family"] == "구매×장벽"]

    def quotes(mask: pd.Series, limit: int = 3) -> str:
        lines = example_quotes(evidence, posts, mask, limit)
        if not lines:
            return "- 해당 조건의 근거 행이 없다."
        return "\n".join(f"- {line}" for line in lines)

    def conn_quotes(frame: pd.DataFrame, limit: int = 4) -> str:
        if not len(frame):
            return "- 해당 연결이 없다."
        likes = posts.set_index("post_id")["like_count"]
        part = frame.copy()
        part["like_count"] = part["post_id"].map(likes)
        part = part.sort_values("like_count", ascending=False)
        lines = []
        for record in part.head(limit).itertuples(index=False):
            lines.append(f"- {record.quote} (post_id {record.post_id}; {record.selection_reason}; {record.behavior or record.right_label})")
        return "\n".join(lines)

    aspect_lines = [f"| {name} | {int(count)} |" for name, count in aspect_posts.items()]
    compare_summary = compare[compare["post_id"].isna()] if "post_id" in compare.columns else compare
    if "post_id" in compare.columns:
        compare_summary = compare[compare["post_id"].isna() | (compare["post_id"].astype(str) == "")]
        if not len(compare_summary):
            compare_summary = compare[compare["previous_user_confirmed"].astype(str) != ""]
    compare_summary = compare[compare["note"].astype(str).str.startswith("이전")]
    form_counts = evidence[evidence["axis"] == "형태"].groupby("label")["post_id"].nunique().sort_values(ascending=False)
    form_lines = [f"| {name} | {int(count)} |" for name, count in form_counts.head(12).items()]
    token_lines = []
    for record in tokens.head(8).itertuples(index=False):
        token_lines.append(f"| {record.token} | {record.pos} | {record.token_count} | {record.post_count} | {record.surface_is_collection_keyword} |")

    explicit_reason_counts = explicit.groupby("selection_reason")["post_id"].nunique().sort_values(ascending=False)
    reason_lines = [f"| {name} | {int(count)} |" for name, count in explicit_reason_counts.items()]

    text = f"""# 치이카와 X 게시물 심층 분석 보고서

- 기준 버전: `{CODEBOOK_VERSION}`
- 생성 시각: {datetime.now(SEOUL).isoformat(timespec="seconds")}
- 스크립트: `text_analysis_deep/run_deep_analysis.py`

## 핵심 요약

입력 게시물 {n}건을 모두 처리했다. 완료 {done}건, 처리 실패 {failed}건, 확인 필요 표시 {review_n}건이다. 확인 필요는 실패가 아니다.

작성자가 밝힌 호감 가운데 얼굴·표정·몸 같은 특징이 구절에 있는 경우는 따로 세고, `귀엽다`만 있는 경우는 외형 호감으로 넣지 않았다. 구매완료는 작성자의 샀다·구매했다·결제했다·질렀다만 확정으로 세고, 겟·데려오다·살까·갖고 싶다는 다른 행동으로 남겼다. 이전 분석의 구매완료 61건, 구매희망 49건은 정답으로 쓰지 않고 정의 차이를 대조했다.

명시적 이유 연결(작성자)은 {int(len(explicit))}건, 서로 다른 게시물 {int(explicit['post_id'].nunique()) if len(explicit) else 0}개다. 건수가 작은 이유는 순위로 일반화하지 않는다.

## 분석 범위와 방법

| 항목 | 값 |
| --- | --- |
| 입력 게시물 | {n} |
| 처리 완료 | {done} |
| 처리 실패 | {failed} |
| 확인 필요 게시물 | {review_n} |
| 입력 = 완료 + 실패 | {n == done + failed} |
| post_id 중복 | {int(posts['post_id'].duplicated().sum())} |
| 조회수 결측 | {view_null} |
| 계정 이름 문자열 null | {null_name} |
| source_year와 작성 연도 불일치 | {year_mismatch} |
| 본문 IP 언급 게시물 | {int((posts['ip_in_text'] == '예').sum())} |
| 판단 방법 | 구절 규칙 `{DECISION_METHOD}` |
| 사람 재라벨 | 없음 |
| 정답 대조 정확도 | 만들지 않음 |

CSV는 식별자·계정·본문을 문자열로 읽고, 기본 결측 추론을 끄고, 빈 조회수만 결측으로 두었다. 작성 시각은 `+09:00`을 유지한 채 한국시간으로 해석했고 9시간을 더하지 않았다.

규칙은 문장과 구절을 나누고, 부정·희망·완료가 겹치면 부정과 희망을 먼저 차지하게 했다. 주어가 친구·룸메·등장인물이면 작성자 행동에서 뺐다. 판매 문안의 호감은 홍보문구로 두었다. Kiwi는 사용자 사전으로 이름과 상품명을 보호한 뒤 내용어 빈도에만 썼다. 호감 측면과 구매 여부는 형태소 품사로 정하지 않는다.

이 집합은 연도별 인기 게시물 최대 1,000건이다. 연도별 건수를 X 전체의 관심 증가나 시장 규모로 읽지 않는다. 검색 키워드는 수집 조건이다.

## 호감은 무엇을 향하는가

작성자 호감 표현이 있는 고유 게시물 {int(author['post_id'].nunique()) if len(author) else 0}개, 표현 {int(len(author))}건. 홍보문구 호감 표현 {int(len(promo))}건은 작성자 수에 넣지 않았다. 분모는 게시물 {n}개. 한 글에 측면이 여러 개면 아래 게시물 수 합은 {n}을 넘을 수 있다.

| 측면 | 작성자 호감이 있는 게시물 수 |
| --- | --- |
{chr(10).join(aspect_lines) if aspect_lines else "| 없음 | 0 |"}

외형으로 둔 작성자 예:

{quotes((evidence['axis'] == '호감') & (evidence['speaker'] == '작성자') & (evidence['affection_aspect'] == ASPECT_LOOK))}

측면을 확정하지 않은 작성자 예 (`귀엽다`만으로는 외형이 아님):

{quotes((evidence['axis'] == '호감') & (evidence['speaker'] == '작성자') & (evidence['affection_aspect'] == UNCLEAR_ASPECT))}

행동·성격:

{quotes((evidence['axis'] == '호감') & (evidence['speaker'] == '작성자') & (evidence['affection_aspect'] == ASPECT_ACT))}

관계·이야기:

{quotes((evidence['axis'] == '호감') & (evidence['speaker'] == '작성자') & (evidence['affection_aspect'] == ASPECT_REL))}

상품 구현:

{quotes((evidence['axis'] == '호감') & (evidence['speaker'] == '작성자') & (evidence['affection_aspect'] == ASPECT_GOODS))}

가격처럼 캐릭터가 아닌 대상의 부정은 캐릭터 비호감으로 옮기지 않았다. 가격이 이유 구절에 붙은 작성자 연결은 아래 장벽 건수에 있다. 호감 표의 가격 대상 행이 없으면, 가격 문장을 캐릭터 평가로 만들지 않은 것이다.

## 선택 이유와 행동

확정 행동의 게시물 수다. 한 글에 행동이 여러 개면 합이 전체를 넘을 수 있다. 분모 {n}.

| 행동 | 게시물 수 |
| --- | --- |
| 구매완료 | {buy_done} |
| 구매희망 | {buy_wish} |
| 구매고민 | {buy_hes} |
| 구매부정 | {buy_neg} |
| 구매포기 | {buy_drop} |
| 소장희망 | {own_wish} |
| 소지사용 | {post_has('behavior_labels', '소지사용')} |
| 뽑기 | {post_has('behavior_labels', '뽑기')} |
| 시청경험 | {post_has('behavior_labels', '시청경험')} |
| 팝업방문 | {post_has('behavior_labels', '팝업방문')} |
| 개인판매교환 | {post_has('behavior_labels', '개인판매교환')} |
| 공구 | {post_has('behavior_labels', '공구')} |
| 단순 언급 | {post_has('behavior_labels', '단순 언급')} |

작성자가 연결어로 이유를 붙인 표현의 게시물 수다. 적은 수는 순위가 아니다.

| 작성자가 밝힌 이유 | 게시물 수 |
| --- | --- |
{chr(10).join(reason_lines) if reason_lines else "| 없음 | 0 |"}

명시적 이유 예:

{conn_quotes(explicit)}

가격·재고·공간이 이유 구절에 붙은 경우만 장벽이다. 삼만원처럼 금액만 있는 문장, 한정이라는 단어만 있는 문장은 장벽이나 희소성 이유로 연결하지 않았다. 명시적 장벽 연결 {int(len(explicit_barrier))}건.

## 상품·콘텐츠 형태

형태 단어가 있는 게시물 수다. 선택 이유가 확인된 것은 아니다.

| 형태 | 게시물 수 |
| --- | --- |
{chr(10).join(form_lines) if form_lines else "| 없음 | 0 |"}

형태와 행동이 같은 구절에 있어도 `selection_reason`이 언급 없음이면 그 형태를 고른 이유로 세지 않는다. 집계 `agg_form_by_reason.csv`의 `evidence_level`로 구분한다.

## 게시 맥락

`context_labels`는 복수다. `context_primary`가 혼합인 게시물은 {post_has('context_primary', CTX_MIX) if False else int((posts['context_primary'] == CTX_MIX).sum())}건이고, 이 글은 위 맥락 행에 각각 들어간다. 상호배타 수치는 집계의 `primary:` 행이다.

## 콘텐츠를 즐기는 방식

집계는 `agg_content_use.csv`다. 반복 이용은 그 글에서 다시 봤다고 말한 경우만이다. 여러 글에 같은 대사가 나온다고 해서 같은 사람의 반복 소비로 보지 않았다.

## 이전 구매 61건·희망 49건과의 대조

이전 분석의 이용자 확정 라벨과 이번 확정 라벨을 게시물 단위로 겹쳐 보았다. 이전 수를 맞추는 것이 목적이 아니다.

{md_table(
    ['라벨', '이전 확정', '이번 확정', '둘 다', '이전에만', '이번에만'],
    [
        [str(record.label), str(record.previous_user_confirmed), str(record.this_analysis_author_confirmed), str(record.both), str(record.previous_only), str(record.this_only)]
        for record in compare_summary.itertuples(index=False)
    ] if len(compare_summary) else [['없음', '', '', '', '', '']]
)}

차이 원문 목록은 `validation_previous_purchase.csv`에 있다. 이전에만 있는 구매완료에는 겟했다, 사서, 다른 사람 구매, 안내 문장의 구매, 꿈·상상 속 구매가 섞여 있다. 이전에만 있는 구매희망에는 살까와 갖고 싶다가 섞여 있다. 이번 분석은 살까를 구매고민, 갖고 싶다를 소장희망으로 나누고, 구합니다는 구매희망에 둔다.

## 내용어 빈도

형태소 빈도이며 선호 순위가 아니다. 수집 키워드 표면은 따로 표시했다.

| 토큰 | 품사 | 출현 | 게시물 | 수집 키워드 |
| --- | --- | --- | --- | --- |
{chr(10).join(token_lines)}

## 연도

연도 분모는 작성 연도별 입력 건수다. 이번 데이터는 연도별 1,000건 구성인지 집계 파일을 확인한다. 조회수 결측이 특정 연도에 몰리면 조회수로 연도를 비교하지 않는다. `source_year` 불일치 {year_mismatch}건.

## 기존 분석과 달라진 점

- 이전 이용자 외형호감은 귀엽다·예쁘다·말랑·폭신을 외형으로 보았다. 이번에는 부위나 형태가 있는 구절만 캐릭터 외형이다.
- 이전 구매완료 61, 구매희망 49는 겟, 사서, 살까, 갖고 싶다의 포함 범위가 달랐다. 이번 확정 수와 다르면 그 정의를 따른 것이다.
- 이전에는 요인과 행동을 주로 따로 집계했다. 이번에는 연결어가 있을 때만 명시적 이유로 저장한다.
- 판매 문장 호감, 가격 불만, 작중 감정을 작성자 캐릭터 호감과 섞지 않는 점은 유지했다.

## 한계

- 이미지와 영상 내용은 본문에 없으면 확인하지 못한다.
- 규칙이 놓친 구어, 오탈자, 비유는 확인 필요이거나 미포착이다. 정확도 수치는 없다.
- 명시적 이유가 적어도 그 이유가 없다고 말할 수는 없다. 글에 안 썼을 수 있다.
- 게시물 표본은 검색과 인기순의 영향을 받는다. 판매량, 시장 규모, 연령, 충성도, 계약 조건, 수익성은 판단하지 않는다.
- 사람 검토자가 5,000건을 다시 읽지는 않았다.

## 국내 IP 검토에 연결할 수 있는 근거와 가설

아래는 선정 기준 확정이 아니다. 사업성·계약·수익 판단도 아니다.

1. 관찰: 호감 단어는 반복되지만, 얼굴·표정·몸 형태를 같이 쓴 글은 그 단어 전체보다 적다. 원문은 위 외형 예와 측면 미확정 예.
   해석 범위: 이 표본의 텍스트 호감은 짧은 총평이 많고, 어떤 부위가 좋은지는 자주 적히지 않는다.
   검토 가설: 국내 IP 텍스트 반응을 볼 때 `귀엽다` 건수를 외형 설계의 근거로 쓰지 않고, 표정·눈·크기·상품 실물처럼 특징이 같이 적힌 글만 외형 단서로 볼 수 있는지.
   추가 검증: 이미지 반응, 인터뷰에서 부위와 표정을 짚게 하는 질문.

2. 관찰: 구매 완료·희망·고민·부정·소장은 서로 다른 표현이고 건수가 호감 게시물보다 작다. 이유를 문장으로 붙인 경우는 더 작다.
   해석 범위: 호감 문장이 구매 문장은 아니다. 이유 연결은 작성자가 말한 범위만 알 수 있다.
   검토 가설: 상품을 고른 이유로 볼 항목을 호감 건수가 아니라, 같은 구절에 형태와 이유 연결어가 같이 있는 사례로 제한할 수 있는지. 이번 데이터에서 그 사례가 적으면 그 항목은 가설로 남긴다.
   추가 검증: 구매 화면의 선택 로그, 소수 구매자 면접.

3. 관찰: 가격을 이유로 안 샀다는 문장은 캐릭터를 싫다는 문장과 따로 있다. 금액만 적힌 문장은 장벽으로 연결하지 않았다.
   검토 가설: 가격 불만을 캐릭터 매력 감점으로 넣지 않고, `비싸서 안 샀다`처럼 이유 구절이 있는 경우만 가격 장벽 신호로 볼 수 있는지.
   추가 검증: 정가와 양도가, 구매 포기 인터뷰.

4. 관찰: 인형·키링·피규어·가챠·스티커처럼 작은 상품 이름과, 애니·영상 이름이 같이 등장한다. 형태 표는 언급이지 판매량이 아니다.
   검토 가설: 초기에 텍스트로 자주 불리는 형태가 작은 부착·수집 상품인지, 영상 감상인지를 판매 데이터가 아니라 언급 유형으로만 가설할 수 있는지.
   추가 검증: 실제 출시 목록과 판매 데이터.

5. 관찰: 작품 이름 `먼작귀`와 등장인물 이름이 한 표본에 같이 있고, 치이카와는 구절에 따라 작품일 수도 있고 인물일 수도 있으며 상당수는 구분되지 않는다.
   검토 가설: 시리즈명과 대표 캐릭터명이 같을 때, 팬이 둘을 나눠 부르는지 검색어를 통제한 표본으로 확인할 필요가 있는지.
   추가 검증: 이름 인지 조사. 이 게시물의 이름 빈도는 수집 키워드의 영향을 받는다.

## 확인 필요와 실패

확인 필요 {review_n}건은 `output/review_required.csv`에 있다. 처리 실패 {failed}건은 `output/processing_errors.csv`에 있다. 실패가 0이면 그 파일은 헤더만 있다.
"""
    (DOCS / "deep_analysis_report.md").write_text(text, encoding="utf-8")


def validate(posts: pd.DataFrame, evidence: pd.DataFrame, errors: pd.DataFrame) -> dict:
    checks = {
        "input_posts": int(len(posts)),
        "completed": int((posts["processing_status"] == "완료").sum()),
        "failed": int((posts["processing_status"] == "처리 실패").sum()),
        "review_posts": int((posts["review_flag"] == "예").sum()),
        "unique_post_id": int(posts["post_id"].nunique()),
        "evidence_rows": int(len(evidence)),
        "evidence_missing_quote": int((evidence["quote"].fillna("") == "").sum()) if len(evidence) else 0,
        "view_null": int(posts["view_count"].isna().sum()),
        "account_name_null_string": int((posts["account_name"] == "null").sum()),
        "balance_ok": int(len(posts)) == int((posts["processing_status"] == "완료").sum()) + int(len(errors)),
    }
    original_by_id = {str(record.post_id): str(record.text).replace("\r\n", "\n").replace("\r", "\n") for record in posts.itertuples(index=False)}
    bad_match = 0
    if len(evidence):
        for record in evidence.itertuples(index=False):
            if record.axis == "게시맥락":
                continue
            match = str(record.match_text or "")
            if match and match not in original_by_id.get(str(record.post_id), ""):
                bad_match += 1
                if bad_match > 20:
                    break
    checks["match_text_not_in_original"] = bad_match
    return checks


def write_run_log(checks: dict, errors: pd.DataFrame) -> None:
    lines = [
        f"# 실행 기록",
        "",
        f"- 시각: {datetime.now(SEOUL).isoformat(timespec='seconds')}",
        f"- 코드 버전: {CODEBOOK_VERSION}",
        f"- 스크립트 해시: {script_hash()}",
        f"- 판정: {DECISION_METHOD}. 게시물별 사람 수정 없음.",
        f"- 재개: `work/posts.jsonl`에 스크립트 해시가 같으면 이어서 처리한다.",
        "",
        "## 건수",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"처리 실패 {len(errors)}건. 0건이면 실패 사례가 없다.")
    (DOCS / "run_log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (WORK / "validation_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    for path in (OUT, DOCS, TABLES, AGG, WORK):
        path.mkdir(parents=True, exist_ok=True)
    print("self-check", flush=True)
    kiwi = build_kiwi()
    self_check(kiwi)
    print("load", flush=True)
    posts = load_inputs()
    print("analyze", len(posts), flush=True)
    results, error_rows = analyze_all(posts, kiwi)
    post_frame, evidence, connections, reviews = build_frames(posts, results)
    errors = pd.DataFrame(error_rows)
    if not len(errors):
        errors = pd.DataFrame(columns=["post_id", "error_type", "error_message"])
    else:
        errors = errors.rename(columns={"error": "error_message"})
        errors["error_type"] = "processing_error"
    if not len(reviews):
        reviews = pd.DataFrame(columns=["post_id", "review_reasons", "quote", "context_primary"])
    aggs = build_aggs(post_frame, evidence, connections)
    print("tokens", flush=True)
    tokens = token_frequency(post_frame[post_frame["processing_status"] == "완료"], kiwi)
    compare = previous_purchase_compare(post_frame)
    checks = validate(post_frame, evidence, errors)
    write_both(TABLES / "x_posts_deep_analysis.csv", post_frame)
    write_both(TABLES / "x_post_evidence.csv", evidence)
    write_both(TABLES / "x_post_connections.csv", connections)
    write_csv(TABLES / "review_required.csv", reviews)
    write_csv(TABLES / "processing_errors.csv", errors)
    write_csv(TABLES / "validation_previous_purchase.csv", compare)
    for name, frame in aggs.items():
        write_csv(AGG / f"{name}.csv", frame)
        if len(frame):
            frame.to_parquet(AGG / f"{name}.parquet", index=False)
    write_csv(TABLES / "token_frequency.csv", tokens)
    write_codebook()
    write_definitions()
    write_report(post_frame, evidence, connections, aggs, compare, errors, reviews, tokens)
    write_run_log(checks, errors)
    print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
    if checks["match_text_not_in_original"]:
        raise SystemExit("quote validation failed")
    if not checks["balance_ok"]:
        raise SystemExit("post count balance failed")


if __name__ == "__main__":
    main()
