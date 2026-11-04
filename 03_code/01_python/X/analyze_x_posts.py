# -*- coding: utf-8 -*-
"""X 게시물 전체 본문 분석.

기준 폴더의 normalized CSV만 읽고, 결과는 text_analysis/label_pass에만 쓴다.
검색 키워드는 수집 경로로만 붙이며 언급·호감·구매 라벨의 근거로 쓰지 않는다.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from kiwipiepy import Kiwi

CODE_DIR = Path(r"C:\DATA\KDT_Integral_Data_Project\03_code\01_python")
sys.path.insert(0, str(CODE_DIR))
import normalize_x_tables as nz  # noqa: E402

BASE = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
NORM = BASE / "normalized"
ANALYSIS = BASE / "text_analysis"
OUT = ANALYSIS / "label_pass"
DOCS = OUT / "docs"
TABLES = OUT / "output"
WORK = ANALYSIS / "work"
BATCH = WORK / "batches"
CODEBOOK_VERSION = "2026-10-29.3"
UNIT_NAME = "line_or_clause"

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@[0-9A-Za-z_]+")
EMOJI_RE = re.compile("[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]+")
REPEAT_RE = re.compile(r"[ㅋㅎㅠㅜ]{2,}")

CONTENT_TAGS = {"NNG", "NNP", "NNB", "VV", "VA", "MAG", "XR", "IC", "SL"}
STOP_FORMS = {
    "하", "되", "있", "오", "가", "싶", "않", "대하", "위하", "따르", "관련", "통하",
    "수", "것", "등", "뿐", "데", "이", "그", "저", "거", "게", "더", "또", "좀",
    "잘", "그냥", "정말", "진짜", "너무", "넘", "매우", "아주", "완전", "좀",
    "나", "내", "저", "제", "우리", "너", "때", "중", "및", "또는", "그리고",
    "http", "https", "www", "html", "com", "co", "t", "status",
}
URL_TOKEN = re.compile(r"^(https?|www|html|com|co|net|jp|kr|php|amp)$", re.I)

COLLECTION_KEYWORDS = {
    "갑옷씨", "데카츠요", "랏코", "먼작귀", "모몽가", "시사", "아노코", "우사기",
    "치이카와", "카니", "쿠리만쥬", "파자마 파티즈", "하치와레",
}

CAST_CANON = {
    "하치와레": "등장인물:하치와레",
    "하치와래": "등장인물:하치와레",
    "우사기": "등장인물:우사기",
    "모몽가": "등장인물:모몽가",
    "모몬가": "등장인물:모몽가",
    "랏코": "등장인물:랏코",
    "쿠리만쥬": "등장인물:쿠리만쥬",
    "쿠리만주": "등장인물:쿠리만쥬",
    "아노코": "등장인물:아노코",
    "데카츠요": "등장인물:데카츠요",
}
CAST_RE = re.compile(
    r"하치와래|하치와레|쿠리만쥬|쿠리만주|데카츠요|아노코|모몽가|모몬가|우사기|랏코"
)
NAME_RE = re.compile(
    r"치이까와|치이카와|치카와|ちいかわ|吉伊卡哇|吉伊|chiikawa",
    re.IGNORECASE,
)
WORK_CUE_RE = re.compile(r"애니메이션|세계관|시리즈|원작|만화|애니|영화")
INDIVIDUAL_CUE_RE = re.compile(r"팔다리|짧은 팔|울었|울어|작아서|작다|손발|귀여운 애|주인공")
SHISA_RE = re.compile(r"(?<![가-힣])시사")
KANI_RE = re.compile(r"(?<![가-힣A-Za-z])카니")
ARMOR_RE = re.compile(r"갑옷\s*아저씨|갑옷아저씨|갑옷\s*씨|갑옷씨|갑옷\s*상|갑옷상")
ARMOR_BARE_RE = re.compile(r"(?<![가-힣])갑옷(?![가-힣])")
PAJAMA_WORK_RE = re.compile(r"파자마\s*파티즈|파자마파티즈")
PPANCHU_RE = re.compile(r"빤쮸\s*우사기|빤쮸우사기|빤쮸\s*토끼|빤쮸토끼|오빤쮸")
JOKEBEAR_RE = re.compile(r"농담곰")
USAGI_RE = re.compile(r"(?<![가-힣])우사기")

FORM_PATTERNS = [
    ("키링", re.compile(r"키링|키체인|키홀더")),
    ("스트랩", re.compile(r"스트랩")),
    ("인형", re.compile(r"누이구루미|누이|인형")),
    ("마스코트", re.compile(r"마스코트")),
    ("피규어", re.compile(r"넨도로이드|소프비|피규어")),
    ("가챠", re.compile(r"제일복권|가챠|뽑기|쿠지")),
    ("스티커", re.compile(r"스티커")),
    ("아크릴", re.compile(r"아크릴")),
    ("뱃지", re.compile(r"캔뱃지|뱃지|핀버튼")),
    ("파우치", re.compile(r"파우치")),
    ("캘린더", re.compile(r"캘린더|탁상\s*달력|달력")),
    ("문구", re.compile(r"다이어리|수첩|필통|노트|문구")),
    ("의류", re.compile(r"파자마|잠옷|티셔츠|후드티|수면잠옷")),
    ("영화", re.compile(r"영화")),
    ("애니", re.compile(r"애니메이션|애니")),
    ("영상", re.compile(r"움짤|(?<![가-힣])짤(?![가-힣])|영상|클립")),
    ("팝업", re.compile(r"팝업")),
    ("콜라보", re.compile(r"콜라보")),
    ("식품", re.compile(r"모찌|젤리|푸딩|과자|사탕|쿠키|팬케이크")),
]

SHOP_OFFER_RE = re.compile(
    r"판매(?:합니다|해요|해용|합니|함|중)|팝니다|양도(?:합니다|해요|해용|합니|함)|"
    r"소분(?:합니다|해요|합니)|구매대행|스마트스토어|배송비|가격\s*문의|"
    r"공구(?:합니다|해요|해용|합니|함)|급처"
)
RELEASE_RE = re.compile(r"출시|발매|재입고|입고\s*되었|입고되었|신상")
EVENT_RE = re.compile(r"추첨|이벤트|나눔|(?<![A-Za-z])RT(?![A-Za-z])|알티")
TRADE_WORD_RE = re.compile(r"판매|양도|교환|공구|소분")

CUTE_RE = re.compile(r"귀여워|귀여운|귀여움|귀엽|귀여웠|기여워|기여운|커여워|커여운|귀요|존귀|기염|이쁘|예쁘|예뻐|깜찍|사랑스|말랑|부들부들|폭신")
CUTE_NEG_RE = re.compile(r"(?:안|못)\s*귀여|귀엽지\s*않|별로")
FUNNY_RE = re.compile(r"웃기|웃겨|웃김|빵터|빵\s*터")
HEAL_RE = re.compile(r"힐링(?!템)|위로(?!금)|소중|공감|마음(?:이|을)?.{0,6}(?:따뜻|놓)")
STORY_REL_RE = re.compile(r"우정|세계관|명장면|친구\s*사이")
PRICE_BAD_RE = re.compile(r"비싸|아깝|부담스|가격이\s*부담|값이\s*부담")
PRICE_GOOD_RE = re.compile(r"저렴|가성비|(?<![비])싸(?:게|요|서)|(?<![비])싸다")
SCARCITY_RE = re.compile(r"품절|한정|조기\s*소진|재입고|구하기.{0,6}힘|재고\s*없")
SCARCITY_NEG_RE = re.compile(r"아쉽|슬프|슬퍼|ㅠ|못\s*샀|안\s*샀|없네|없다")
DESIGN_POS_RE = re.compile(r"(?:마감|재질|디테일|퀄리티|박음질).{0,8}(?:좋|예쁘|귀여|탄탄|부드)")
DESIGN_NEG_RE = re.compile(r"(?:마감|재질|디테일|퀄리티|박음질).{0,8}(?:별로|엉망|아쉽|나쁘|별로)")
PERSONALITY_RE = re.compile(r"착하|착해|착함|(?<![가-힣])잔인|(?<![가-힣])사악|순해|기특|바보\s*같")
WISH_RE = re.compile(r"사고\s*싶|사고싶|사고시프|사고\s*시프|갖고\s*싶|가지고\s*싶|사야겠|사야지|살까|살래|살지|구매하고\s*싶|겟하고\s*싶")
WISH_NEG_RE = re.compile(r"사고\s*싶(?:지|진)\s*않|갖고\s*싶(?:지|진)\s*않|안\s*사고\s*싶|사기\s*싫")
BUY_NEG_RE = re.compile(r"안\s*샀|안샀|못\s*샀|못샀|사지\s*않|안\s*살(?:래|거|아)|못\s*살")
BUY_DONE_RE = re.compile(r"샀|사왔|사옴|사버렸|사버림|사서(?!함)|구매했|구입했|겟했|질렀|질럿")
OTHER_BUYER_RE = re.compile(r"(사장이|룸메가|언니가|오빠가|엄마가|아빠가|남친이|여친이|친구가).{0,18}(?:샀|사왔|사옴|사서)")
LOOK_RE = re.compile(r"정주행|관람")
POPUP_GO_RE = re.compile(r"팝업.{0,16}(?:갔|다녀|방문|들렀|입장)|(?:갔|다녀왔|방문).{0,10}팝업")
ANIME_WATCH_RE = re.compile(r"(?:애니|애니메이션|영화).{0,12}(?:봤|보는\s*중|정주행)|(?:봤|정주행).{0,12}(?:애니|애니메이션|영화)")
CLIP_WATCH_RE = re.compile(r"(?:영상|움짤|짤|클립).{0,12}(?:봤|보는\s*중)|(?:봤).{0,8}(?:영상|움짤|짤)")
GACHA_DRAW_RE = re.compile(r"뽑았|뽑음|뽑았다|뽑았어")
OWN_RE = re.compile(r"언박싱|개봉|소장\s*중|소장했|들고\s*다|가방에|키링을?\s*달")
OWN_WISH_RE = re.compile(r"소장하고\s*싶|소장\s*싶|갖고\s*싶|가지고\s*싶")
SEEK_RE = re.compile(r"(?<![가-힣])삽니다|구합니다|구해요|구함|양도\s*받|양도받|양도\s*구")
STORY_EX_RE = re.compile(r"교환하자|교환해\s*줌|교환해줌|교환했다")
FIRST_PERSON_RE = re.compile(r"내가|저는|저는|제가|나는|난 |저의|나의")
CAST_SUBJECT_RE = re.compile(
    r"(치이카와|하치와레|우사기|모몽가|모몬가|랏코|쿠리만쥬|시사|카니|갑옷씨|갑옷아저씨)"
    r"(?:이|가|은|는|도)"
)
STORY_FEEL_RE = re.compile(r"싫어|싫다|좋아해|울었|울어|무서워")
IP_CUE_RE = re.compile(
    r"치이까와|치이카와|치카와|먼작귀|하치와레|하치와래|모몽가|모몬가|랏코|쿠리만쥬|쿠리만주|"
    r"아노코|데카츠요|갑옷씨|갑옷아저씨|chiikawa|ちいかわ|吉伊卡哇|애니|가챠|인형|키링|피규어|굿즈",
    re.IGNORECASE,
)


def read_table(path: Path, table: str) -> pd.DataFrame:
    """정의서와 같은 자료형 규칙으로 CSV를 읽는다.

    공식 read_csv_table은 lineterminator='\\n'이라 이 파일의 CRLF에서
    마지막 컬럼명에 CR이 붙는다. 구분자만 기본값으로 두고 정수·시간대 해석은
    기존 함수를 그대로 쓴다. 이미 +09:00인 시각에 9시간을 더하지 않는다.
    """
    raw = pd.read_csv(
        path,
        dtype="string",
        encoding="utf-8-sig",
        na_filter=False,
        keep_default_na=False,
    )
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


def dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def text_lf(text: str) -> str:
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def make_analysis_text(text: str) -> str:
    masked = URL_RE.sub(" ", text_lf(text))
    masked = MENTION_RE.sub(" ", masked)
    masked = masked.replace("#", " ")
    masked = re.sub(r"[ \t]+", " ", masked)
    masked = re.sub(r" *\n *", "\n", masked)
    return masked.strip()


def make_kiwi_text(analysis: str) -> str:
    out = re.sub(r"파자마\s*파티즈", "파자마파티즈", analysis)
    out = re.sub(r"갑옷\s*아저씨", "갑옷아저씨", out)
    out = re.sub(r"갑옷\s*씨", "갑옷씨", out)
    out = re.sub(r"갑옷\s*상", "갑옷상", out)
    out = re.sub(r"빤쮸\s*우사기", "빤쮸우사기", out)
    out = re.sub(r"빤쮸\s*토끼", "빤쮸토끼", out)
    return out


def build_kiwi() -> Kiwi:
    kiwi = Kiwi()
    words = [
        "치이카와", "치이까와", "치카와", "하치와레", "하치와래", "우사기", "모몽가", "모몬가",
        "랏코", "쿠리만쥬", "쿠리만주", "먼작귀", "아노코", "데카츠요", "갑옷씨", "갑옷아저씨",
        "갑옷상", "파자마파티즈", "빤쮸우사기", "빤쮸토끼", "키링", "키체인", "키홀더",
        "가챠", "피규어", "넨도로이드", "소프비", "아크릴", "스티커", "파우치", "뱃지",
        "캔뱃지", "콜라보", "팝업", "언박싱", "마스코트", "누이구루미", "다이어리",
        "산리오", "농담곰", "스파오", "다이소", "나가노", "치이카와", "스트랩",
    ]
    for word in words:
        kiwi.add_user_word(word, "NNP", 10.0)
    return kiwi


def iter_units(text: str) -> list[str]:
    units: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) <= 140:
            units.append(line)
            continue
        pieces = re.split(r"(?<=[\.!?。！？])\s+|(?<=[,，])\s+", line)
        buf = ""
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            if not buf:
                buf = piece
            elif len(buf) + 1 + len(piece) <= 140:
                buf = f"{buf} {piece}"
            else:
                units.append(buf)
                buf = piece
        if buf:
            units.append(buf)
    if not units and text.strip():
        units.append(text.strip())
    return units


def negated_span(text: str, start: int, end: int) -> bool:
    pre = text[max(0, start - 8) : start]
    post = text[end : end + 8]
    if re.search(r"(안|못)\s*$", pre):
        return True
    if re.search(r"^\s*지\s*않", post):
        return True
    return False


def clip(text: str, limit: int = 160) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1] + "…"


def hit(
    axis: str,
    label: str,
    evidence: str,
    reason: str,
    unit: str,
    needs_review: bool = False,
    polarity: str | None = None,
    target: str | None = None,
    audience: str | None = None,
) -> dict:
    return {
        "axis": axis,
        "label": label,
        "evidence": clip(evidence),
        "reason": reason,
        "needs_review": needs_review,
        "polarity": polarity,
        "target": target,
        "audience": audience,
        "unit": unit,
        "method": "rule_context",
    }


def commercial_unit(unit: str) -> bool:
    return bool(SHOP_OFFER_RE.search(unit))


def find_mentions(analysis: str, units: list[str]) -> list[dict]:
    hits: list[dict] = []
    post_has_cast = bool(CAST_RE.search(analysis) or ARMOR_RE.search(analysis) or SHISA_RE.search(analysis) or KANI_RE.search(analysis))
    pajama_work = bool(PAJAMA_WORK_RE.search(analysis))
    if pajama_work:
        hits.append(hit("mention", "다른작품:파자마파티즈", PAJAMA_WORK_RE.search(analysis).group(), "작품명 '파자마 파티즈'가 본문에 있다. 파자마 상품과 합치지 않는다.", analysis))
    if PPANCHU_RE.search(analysis):
        hits.append(hit("mention", "다른IP:빤쮸토끼", PPANCHU_RE.search(analysis).group(), "빤쮸토끼·빤쮸우사기는 치이카와 우사기와 다른 이름이다.", analysis))
    if JOKEBEAR_RE.search(analysis):
        hits.append(hit("mention", "다른IP:농담곰", "농담곰", "농담곰은 같은 작가의 다른 작품명으로만 적는다.", analysis))

    for name, label in CAST_CANON.items():
        if name in analysis:
            variant = "" if name in {"하치와레", "우사기", "모몽가", "랏코", "쿠리만쥬", "아노코", "데카츠요"} else f" 표기 '{name}'은 대표 표기로 묶는다."
            if name == "우사기":
                continue
            hits.append(hit("mention", label, name, f"본문에 '{name}'이 있다.{variant}", analysis))

    if USAGI_RE.search(analysis):
        standalone = False
        human_only = False
        for match in USAGI_RE.finditer(analysis):
            pre = analysis[max(0, match.start() - 3) : match.start()]
            if pre.endswith("빤쮸") or pre.endswith("쮸"):
                continue
            post = analysis[match.end() : match.end() + 3]
            if post.startswith("님께") or post.startswith("님("):
                human_only = True
                continue
            standalone = True
            break
        if standalone:
            cue = bool(IP_CUE_RE.search(USAGI_RE.sub(" ", analysis)))
            hits.append(
                hit(
                    "mention",
                    "등장인물:우사기",
                    "우사기",
                    "조사 앞의 '우사기'다. 빤쮸우사기와 사람 호칭 '우사기님께서'는 제외한다.",
                    analysis,
                    needs_review=not cue,
                )
            )
        elif human_only:
            hits.append(
                hit(
                    "mention",
                    "확인필요:우사기",
                    "우사기님",
                    "우사기 뒤에 님께서 또는 님이 붙어 사람 이름일 수 있다.",
                    analysis,
                    needs_review=True,
                )
            )

    for match in SHISA_RE.finditer(analysis):
        after = analysis[match.end() : match.end() + 3]
        if after.startswith(("점", "성", "하", "적", "프", "발")):
            continue
        cue = bool(re.search(r"치이카와|먼작귀|하치와레|모몽가|랏코|쿠리만쥬|우사기|인형|누이|가챠|키링|피규어|굿즈|chiikawa", analysis, re.I))
        hits.append(
            hit(
                "mention",
                "등장인물:시사",
                analysis[max(0, match.start() - 12) : match.end() + 12],
                "단어 경계의 '시사'다. '시사하는·시사점'이 아니어야 한다.",
                analysis,
                needs_review=not cue,
            )
        )
        break

    kani_match = next((match for match in KANI_RE.finditer(analysis) if not analysis[match.end() : match.end() + 1].startswith("발")), None)
    if kani_match:
        cue = bool(re.search(r"치이카와|먼작귀|하치와레|모몽가|랏코|쿠리만쥬|우사기|시사|인형|가챠|키링|피규어|굿즈|chiikawa", analysis, re.I))
        hits.append(
            hit(
                "mention",
                "등장인물:카니",
                "카니",
                "단어 경계의 '카니'다. '카니발'이나 다른 단어 내부는 제외했다.",
                analysis,
                needs_review=not cue,
            )
        )

    if ARMOR_RE.search(analysis):
        hits.append(hit("mention", "등장인물:갑옷씨", ARMOR_RE.search(analysis).group(), "갑옷씨·갑옷 아저씨·갑옷상은 같은 등장인물의 표기로 본다.", analysis))
    elif ARMOR_BARE_RE.search(analysis):
        hits.append(
            hit(
                "mention",
                "확인필요:갑옷",
                "갑옷",
                "씨·아저씨·상 없이 '갑옷'만 있어 등장인물인지 확정하지 않는다.",
                analysis,
                needs_review=True,
            )
        )

    name_match = NAME_RE.search(analysis)
    work_alias = "먼작귀" in analysis
    other_cast = any(item["label"].startswith("등장인물:") and not item["needs_review"] for item in hits)
    if work_alias:
        hits.append(hit("mention", "작품:치이카와", "먼작귀", "먼작귀는 작품 별칭이다. 이 별칭만으로 주인공 개인을 확정하지 않는다.", analysis))
    if name_match:
        surface = name_match.group()
        if other_cast:
            hits.append(hit("mention", "등장인물:치이카와", surface, "다른 등장인물과 함께 나와 개별 이름으로 본다.", analysis))
        elif WORK_CUE_RE.search(analysis) or work_alias:
            hits.append(hit("mention", "작품:치이카와", surface, "작품 단서(애니·영화·세계관·시리즈·먼작귀)와 함께 쓰였다.", analysis))
        elif INDIVIDUAL_CUE_RE.search(analysis):
            hits.append(
                hit(
                    "mention",
                    "판단불명확:치이카와이름",
                    surface,
                    "신체·울음 단서가 있으나 작품명과 주인공을 가르는 대조가 없다.",
                    analysis,
                    needs_review=True,
                )
            )
        else:
            hits.append(
                hit(
                    "mention",
                    "판단불명확:치이카와이름",
                    surface,
                    "치이카와·chiikawa 표기만 있고 다른 등장인물이나 작품 단서가 없어 작품/주인공을 가르지 않는다.",
                    analysis,
                )
            )
    elif work_alias and not other_cast:
        pass

    # 같은 라벨은 한 번만 남긴다. 확인 필요가 하나라도 있으면 그 쪽을 남긴다.
    merged: dict[str, dict] = {}
    for item in hits:
        old = merged.get(item["label"])
        if old is None or (item["needs_review"] and not old["needs_review"]):
            merged[item["label"]] = item
    return list(merged.values())


def find_forms(units: list[str]) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    for unit in units:
        for label, pattern in FORM_PATTERNS:
            match = pattern.search(unit)
            if not match or label in seen:
                continue
            if label == "의류" and PAJAMA_WORK_RE.search(unit) and not re.search(r"파자마(?!\s*파티즈)|잠옷|티셔츠", unit):
                continue
            if label == "식품" and re.search(r"마스코트|인형|누이", unit) and not re.search(r"맛있|먹었|편의점|먹어", unit):
                continue
            if label == "식품" and re.search(r"메이커|기계", unit):
                continue
            if label == "식품" and re.search(r"사탕|젤리|쿠키|팬케이크", unit) and not re.search(r"맛있|먹었|편의점|판매|샀|굿즈|콜라보|모찌|과자", unit):
                continue
            reason = f"같은 단위에 '{match.group()}'이 있다."
            if label == "애니" and "애니" in match.group() and "애니메이션" not in unit and len(match.group()) <= 2:
                reason += " '애니메이션'이 아닌 짧은 '애니'다."
            hits.append(hit("form", label, unit, reason, unit))
            seen.add(label)
    return hits


def find_factors(units: list[str], mention_labels: list[str]) -> list[dict]:
    hits: list[dict] = []
    targets = [label for label in mention_labels if label.startswith("등장인물:") or label.startswith("작품:") or label.startswith("판단불명확:")]
    target = "복수대상" if len(targets) > 1 else (targets[0] if targets else None)

    def add_once(bucket: dict, item: dict) -> None:
        old = bucket.get(item["label"])
        if old is None:
            bucket[item["label"]] = item
        elif item["audience"] == "user" and old["audience"] != "user":
            bucket[item["label"]] = item

    bucket: dict[str, dict] = {}
    shop_post = any(commercial_unit(unit) for unit in units)
    for unit in units:
        shop = commercial_unit(unit)
        personal = bool(re.search(r"내가|저는|제가|샀|겟했", unit))
        audience = "promo_copy" if (shop or shop_post) and not personal else "user"
        local_target = target
        if local_target == "복수대상":
            names = CAST_SUBJECT_RE.findall(unit)
            if len(set(names)) == 1:
                local_target = f"등장인물:{names[0]}" if names[0] != "모몬가" else "등장인물:모몽가"
            elif len(set(names)) > 1:
                local_target = "복수대상"
        if CUTE_RE.search(unit):
            negated = bool(CUTE_NEG_RE.search(unit)) or negated_span(unit, CUTE_RE.search(unit).start(), CUTE_RE.search(unit).end())
            if negated:
                add_once(bucket, hit("factor", "외형불만", unit, "귀엽다·예쁘다 계열이 부정어와 함께 있다.", unit, polarity="negative", target=local_target, audience=audience))
            elif audience == "promo_copy":
                add_once(bucket, hit("factor", "홍보문호감", unit, "판매·양도·공구 글 안의 호감 표현이라 이용자 감상으로 세지 않는다.", unit, polarity="positive", target=local_target, audience="promo_copy"))
            else:
                add_once(bucket, hit("factor", "외형호감", unit, "귀엽다·예쁘다 계열이 있고, 그 문장만으로 구매를 부여하지 않는다.", unit, polarity="positive", target=local_target, audience="user"))
        if FUNNY_RE.search(unit) and audience == "user":
            add_once(bucket, hit("factor", "유머", unit, "웃기다 계열이 있다. ㅋㅋ만으로는 유머를 부여하지 않는다.", unit, polarity="positive", target=local_target, audience="user"))
        if HEAL_RE.search(unit) and audience == "user":
            add_once(bucket, hit("factor", "정서적공감", unit, "힐링템처럼 상품 홍보 문구가 아닌 공감·위로·소중 표현이다.", unit, polarity="positive", target=local_target, audience="user"))
        if STORY_REL_RE.search(unit):
            add_once(bucket, hit("factor", "관계서사", unit, "우정·세계관·명장면·친구 사이가 있다. '트친'이나 맨 '친구'는 넣지 않는다.", unit, polarity="mentioned", target=local_target, audience="user"))
        if PRICE_BAD_RE.search(unit):
            add_once(bucket, hit("factor", "가격부담", unit, "비싸다·부담·아깝다는 가격 평가다. 등장인물 자체의 부정으로 옮기지 않는다.", unit, polarity="negative", target="가격", audience="user"))
        elif PRICE_GOOD_RE.search(unit) and not shop:
            add_once(bucket, hit("factor", "가격긍정", unit, "저렴·가성비·싸다 계열이다. '비싸다' 안의 '싸다'는 제외했다.", unit, polarity="positive", target="가격", audience="user"))
        if SCARCITY_RE.search(unit):
            polarity = "negative" if SCARCITY_NEG_RE.search(unit) else "mentioned"
            add_once(bucket, hit("factor", "희소성", unit, "품절·한정·재입고·구하기 어려움이 있다. 희소성만으로 호감이나 판매량을 단정하지 않는다.", unit, polarity=polarity, target=local_target, audience="user"))
        if DESIGN_POS_RE.search(unit):
            add_once(bucket, hit("factor", "상품디자인호감", unit, "마감·재질·디테일·퀄리티에 긍정 평가가 같은 단위에 있다.", unit, polarity="positive", target=local_target, audience=audience))
        if DESIGN_NEG_RE.search(unit):
            add_once(bucket, hit("factor", "상품디자인불만", unit, "마감·재질·디테일·퀄리티에 부정 평가가 같은 단위에 있다.", unit, polarity="negative", target=local_target, audience="user"))
        if PERSONALITY_RE.search(unit) and not shop:
            trait = PERSONALITY_RE.search(unit).group()
            review = trait.startswith("잔인") or trait.startswith("사악")
            add_once(
                bucket,
                hit(
                    "factor",
                    "성격특성",
                    unit,
                    "착하다·기특·잔인·사악처럼 성격 평가가 있다. 잔인·사악은 개그성 호감일 수 있어 확인 필요로 둔다.",
                    unit,
                    needs_review=review and not bool(FUNNY_RE.search(unit)),
                    polarity="mixed" if review else "positive",
                    target=local_target,
                    audience="user",
                ),
            )
        feel = STORY_FEEL_RE.search(unit)
        subject = CAST_SUBJECT_RE.search(unit)
        first = FIRST_PERSON_RE.search(unit)
        if feel and subject:
            subject_pos = subject.start()
            first_pos = first.start() if first else -1
            if first_pos == -1 or subject_pos < first_pos:
                add_once(bucket, hit("factor", "작중감정", unit, "등장인물이 주어에 가깝고 싫어하다·울다 같은 작중 감정이다. 이용자 불만으로 세지 않는다.", unit, polarity="in_story", target=local_target, audience="character_in_story"))
            elif first and "싫" in feel.group():
                add_once(bucket, hit("factor", "불호", unit, "1인칭과 싫다가 함께 있으나 외형·가격·디자인 요인이 분리되지 않는다.", unit, needs_review=True, polarity="negative", target=local_target, audience="user"))
        elif feel and first and "싫" in feel.group() and targets:
            add_once(bucket, hit("factor", "불호", unit, "싫다는 1인칭 표현이 있으나 요인이 문장 안에 구체적이지 않다.", unit, needs_review=True, polarity="negative", target=local_target, audience="user"))
    return list(bucket.values())


def masked_for_buy(unit: str) -> str:
    masked = WISH_NEG_RE.sub(lambda m: " " * len(m.group()), unit)
    masked = WISH_RE.sub(lambda m: " " * len(m.group()), masked)
    masked = BUY_NEG_RE.sub(lambda m: " " * len(m.group()), masked)
    return masked


def unit_has_subject(unit: str) -> bool:
    if IP_CUE_RE.search(unit) or ARMOR_RE.search(unit) or USAGI_RE.search(unit) or SHISA_RE.search(unit) or KANI_RE.search(unit) or "먼작귀" in unit:
        return True
    return any(pattern.search(unit) for _label, pattern in FORM_PATTERNS)


def find_actions(units: list[str], has_ip: bool) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()

    def add(item: dict) -> None:
        if item["label"] in seen:
            return
        seen.add(item["label"])
        hits.append(item)

    for unit in units:
        if not unit_has_subject(unit):
            continue
        shop = commercial_unit(unit)
        story_exchange = bool(STORY_EX_RE.search(unit) and CAST_SUBJECT_RE.search(unit) and not TRADE_WORD_RE.search(unit))
        if WISH_NEG_RE.search(unit):
            add(hit("action", "구매부정", unit, "사고 싶다·갖고 싶다가 부정형이다.", unit, audience="user"))
        elif WISH_RE.search(unit):
            label = "소장희망" if OWN_WISH_RE.search(unit) and not re.search(r"사고\s*싶|사고싶|살까|살래|사야", unit) else "구매희망"
            if re.search(r"사고\s*싶|사고싶|살까|살래|사야", unit):
                label = "구매희망"
            add(hit("action", label, unit, "희망·고려 표현이며 구매 완료가 아니다.", unit, audience="user"))
        if BUY_NEG_RE.search(unit):
            add(hit("action", "구매부정", unit, "샀다의 부정형이다. 구매 완료로 세지 않는다.", unit, audience="user"))
        buy_text = masked_for_buy(unit)
        done = BUY_DONE_RE.search(buy_text)
        if done and not negated_span(buy_text, done.start(), done.end()):
            subject = CAST_SUBJECT_RE.search(unit)
            first = FIRST_PERSON_RE.search(unit)
            storyish = subject and (first is None or subject.start() < (first.start() if first else 10**9)) and re.search(r"닮|먹|주워|집었", unit)
            if storyish:
                add(hit("action", "작중행동", unit, "샀다의 주어가 등장인물 쪽으로 보여 이용자 구매로 확정하지 않는다.", unit, needs_review=True, audience="character_in_story"))
            elif OTHER_BUYER_RE.search(unit) and not FIRST_PERSON_RE.search(unit):
                add(hit("action", "구매완료", unit, "샀다의 가까운 주어가 사장·친구·룸메 등 다른 사람이다.", unit, needs_review=True, audience="other_person"))
            else:
                add(hit("action", "구매완료", unit, "샀다·구매했다·겟했다·질렀다 계열이고 같은 위치의 부정·희망 표현은 제외했다.", unit, audience="user"))
        if SEEK_RE.search(unit):
            add(hit("action", "구매희망", unit, "삽니다·구합니다·양도받다는 구매 완료가 아니라 구하는 표현이다.", unit, audience="user"))
        if shop or re.search(r"판매(?:합니다|해요|해용|함|중)|팝니다|양도(?:합니다|해요|해용|함)", unit):
            add(hit("action", "판매양도", unit, "판매합니다·팝니다·양도합니다처럼 제공하는 쪽 표현이다.", unit, audience="promo_copy"))
        elif re.search(r"판매|양도", unit) and not story_exchange:
            add(hit("action", "거래언급", unit, "판매·양도 단어는 있으나 작성자가 판다는 어미는 아니다.", unit, audience="user"))
        if re.search(r"교환(?:합니다|해요|해용|원|구함|구해요|하실)", unit) or (re.search(r"교환", unit) and re.search(r"양도|판매", unit)):
            add(hit("action", "교환", unit, "교환 의사나 교환·양도 병기가 있다.", unit, audience="user"))
        elif story_exchange:
            add(hit("action", "작중행동", unit, "작중 인물이 교환하자고 한 장면으로 본다.", unit, audience="character_in_story"))
        if re.search(r"공구", unit):
            add(hit("action", "공구", unit, "공구는 공동구매 모집·참여 표현이지 구매 완료나 판매량이 아니다.", unit, audience="promo_copy" if shop else "user"))
        if re.search(r"(?<![가-힣])나눔(?![가-힣])", unit):
            add(hit("action", "나눔", unit, "나눔은 증정·이벤트 맥락으로 두고 판매와 구분한다.", unit, audience="promo_copy"))
        if OWN_RE.search(unit) and not shop:
            add(hit("action", "소지사용", unit, "언박싱·개봉·소장·가방에 다는 등 가진 뒤의 표현이다.", unit, audience="user"))
        if OWN_WISH_RE.search(unit) and "소장희망" not in seen and "구매희망" not in seen:
            add(hit("action", "소장희망", unit, "갖고 싶다·소장하고 싶다는 소유 희망이다.", unit, audience="user"))
        if GACHA_DRAW_RE.search(unit):
            add(hit("action", "가챠뽑기", unit, "뽑았다 계열이다. 판매량으로 해석하지 않는다.", unit, audience="user"))
        if LOOK_RE.search(unit) or ANIME_WATCH_RE.search(unit):
            add(hit("action", "관람", unit, "애니·영화·정주행·관람처럼 콘텐츠를 봤다는 표현이다.", unit, audience="user"))
        if POPUP_GO_RE.search(unit):
            add(hit("action", "팝업방문", unit, "팝업과 갔다가 같은 단위에 있다.", unit, audience="user"))
        if CLIP_WATCH_RE.search(unit):
            add(hit("action", "영상시청", unit, "영상·짤을 봤다는 표현이다. 영화 관람과 구분한다.", unit, audience="user"))
        if subject_action_without_user(unit):
            add(hit("action", "작중행동", unit, "등장인물 주어의 먹거나 울거나 하는 행동이다.", unit, audience="character_in_story"))
    if has_ip and not hits:
        add(hit("action", "단순언급", " ".join(units)[:160], "구매·소장·판매·관람 표현이 확인되지 않는다.", " ".join(units)[:160], audience="user"))
    return hits


def subject_action_without_user(unit: str) -> bool:
    if not CAST_SUBJECT_RE.search(unit):
        return False
    if FIRST_PERSON_RE.search(unit):
        return False
    return bool(re.search(r"먹어|먹방|울었|기어|뛰어|도망", unit))


def find_contexts(units: list[str], factors: list[dict], actions: list[dict], has_ip: bool) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    blob = "\n".join(units)

    def add(label: str, evidence: str, reason: str) -> None:
        if label in seen:
            return
        seen.add(label)
        hits.append(hit("context", label, evidence, reason, evidence))

    if SHOP_OFFER_RE.search(blob) or any(item["label"] in {"판매양도", "공구"} for item in actions):
        add("판매양도글", blob, "판매·양도·공구·구매대행 등 거래 제공 표현이 있다.")
    if RELEASE_RE.search(blob):
        add("출시입고안내", blob, "출시·발매·입고·신상·재입고 표현이 있다.")
    if re.search(r"번역|정보공유|자막", blob):
        add("정보공유", blob, "번역·자막·정보 공유 표현이 있다.")
    if EVENT_RE.search(blob):
        add("이벤트홍보", blob, "추첨·이벤트·나눔·RT 표현이 있다.")
    if any(item["audience"] == "user" and item["label"] in {"외형호감", "외형불만", "유머", "정서적공감", "성격특성", "가격부담", "가격긍정", "상품디자인호감", "상품디자인불만", "불호"} for item in factors):
        add("개인반응", blob, "홍보 문장이 아닌 단위에 이용자 평가가 있다.")
    if any(item["audience"] == "user" and item["label"] in {"구매완료", "구매희망", "구매부정", "소지사용", "소장희망", "관람", "팝업방문", "영상시청", "가챠뽑기"} for item in actions):
        add("개인경험", blob, "이용자의 구매·소장·관람·뽑기 표현이 있다.")
    if any(item["label"] == "작중감정" for item in factors) or any(item["label"] == "작중행동" for item in actions):
        add("장면공유", blob, "작중 감정이나 작중 행동이 있다.")
    if has_ip and not hits:
        add("맥락단정불가", blob, "작품·이름 언급은 있으나 개인 감상, 판매, 출시, 장면 단서가 없다.")
    return hits


def link_pairs(forms: list[dict], actions: list[dict], factors: list[dict]) -> tuple[list[dict], list[dict]]:
    form_action = []
    factor_form = []
    seen_fa = set()
    seen_ff = set()
    for form in forms:
        for action in actions:
            if action["unit"] != form["unit"]:
                continue
            if action["label"] in {"단순언급", "작중행동"}:
                continue
            key = (form["label"], action["label"], form["unit"])
            if key in seen_fa:
                continue
            seen_fa.add(key)
            review = len(form["unit"]) > 180 or action["needs_review"] or form["needs_review"]
            form_action.append(
                {
                    "form": form["label"],
                    "action": action["label"],
                    "evidence": clip(form["unit"]),
                    "reason": "같은 줄 또는 절 안에 형태와 행동이 있다.",
                    "unit_type": UNIT_NAME,
                    "needs_review": review,
                    "method": "rule_context",
                }
            )
        for factor in factors:
            if factor["unit"] != form["unit"]:
                continue
            if factor["label"] in {"작중감정"}:
                continue
            key = (factor["label"], form["label"], factor["audience"], form["unit"])
            if key in seen_ff:
                continue
            seen_ff.add(key)
            factor_form.append(
                {
                    "factor": factor["label"],
                    "form": form["label"],
                    "audience": factor["audience"],
                    "polarity": factor["polarity"],
                    "evidence": clip(form["unit"]),
                    "reason": "같은 줄 또는 절 안에 요인과 형태가 있다. 원인으로 단정하지 않는다.",
                    "unit_type": UNIT_NAME,
                    "needs_review": len(form["unit"]) > 180 or factor["needs_review"],
                    "method": "rule_context",
                }
            )
    return form_action, factor_form


def axis_status(items: list[dict], empty_label: str = "미언급") -> str:
    if any(item["needs_review"] for item in items):
        return "확인 필요"
    if any(item["label"].startswith("판단불명확") or item["label"] == "맥락단정불가" for item in items):
        if any(not item["label"].startswith("판단불명확") and item["label"] != "맥락단정불가" for item in items):
            return "분류 가능"
        return "판단 불명확"
    if items:
        return "분류 가능"
    return empty_label


def public_item(item: dict) -> dict:
    return {
        "label": item["label"],
        "polarity": item["polarity"],
        "target": item["target"],
        "audience": item["audience"],
        "evidence": item["evidence"],
        "reason": item["reason"],
        "needs_review": item["needs_review"],
        "method": item["method"],
    }


def classify_post(analysis: str) -> dict:
    units = iter_units(analysis)
    mentions = find_mentions(analysis, units)
    mention_labels = [item["label"] for item in mentions]
    has_ip = any(
        label.startswith("작품:치이카와") or label.startswith("등장인물:") or label.startswith("판단불명확:치이카와") or label.startswith("확인필요:")
        for label in mention_labels
    )
    forms = find_forms(units) if analysis else []
    factors = find_factors(units, mention_labels) if has_ip or forms else []
    actions = find_actions(units, has_ip)
    contexts = find_contexts(units, factors, actions, has_ip)
    form_action, factor_form = link_pairs(forms, actions, factors)
    mention_status = axis_status(mentions)
    form_status = axis_status(forms)
    factor_status = axis_status(factors)
    action_status = axis_status(actions)
    context_status = axis_status(contexts)
    review_reasons = []
    for bucket, axis_name in (
        (mentions, "언급 대상"),
        (forms, "상품·콘텐츠 형태"),
        (factors, "호감·불만 요인"),
        (actions, "행동·의도"),
        (contexts, "게시 맥락"),
    ):
        for item in bucket:
            if item["needs_review"]:
                review_reasons.append({"axis": axis_name, "label": item["label"], "reason": item["reason"], "evidence": item["evidence"]})
    for link in form_action:
        if link["needs_review"]:
            review_reasons.append({"axis": "형태-행동", "label": f"{link['form']}-{link['action']}", "reason": link["reason"], "evidence": link["evidence"]})
    needs_review = bool(review_reasons)
    if needs_review:
        judgment = "확인 필요"
    elif any(status in {"분류 가능", "판단 불명확"} for status in (mention_status, form_status, factor_status, action_status, context_status)):
        judgment = "분류 가능"
    else:
        judgment = "미언급"
    reason_bits = [
        f"언급 {mention_status}",
        f"형태 {form_status}",
        f"요인 {factor_status}",
        f"행동 {action_status}",
        f"맥락 {context_status}",
    ]
    return {
        "mention_labels_json": dumps([public_item(item) for item in mentions]),
        "mention_status": mention_status,
        "mention_evidence_json": dumps([item["evidence"] for item in mentions]),
        "mention_reason": " ".join(item["reason"] for item in mentions) if mentions else "본문에서 작품·등장인물 이름을 찾지 못했다.",
        "form_labels_json": dumps([public_item(item) for item in forms]),
        "form_status": form_status,
        "form_evidence_json": dumps([item["evidence"] for item in forms]),
        "form_reason": " ".join(item["reason"] for item in forms) if forms else "상품·콘텐츠 형태 단어가 없다.",
        "factor_labels_json": dumps([public_item(item) for item in factors]),
        "factor_status": factor_status,
        "factor_evidence_json": dumps([item["evidence"] for item in factors]),
        "factor_reason": " ".join(item["reason"] for item in factors) if factors else "호감·불만 요인을 문장에서 확인하지 못했다.",
        "action_labels_json": dumps([public_item(item) for item in actions]),
        "action_status": action_status,
        "action_evidence_json": dumps([item["evidence"] for item in actions]),
        "action_reason": " ".join(item["reason"] for item in actions) if actions else "행동·의도 표현이 없다.",
        "context_labels_json": dumps([public_item(item) for item in contexts]),
        "context_status": context_status,
        "context_evidence_json": dumps([item["evidence"] for item in contexts]),
        "context_reason": " ".join(item["reason"] for item in contexts) if contexts else "게시 맥락을 나눌 단서가 없다.",
        "form_action_links_json": dumps(form_action),
        "factor_form_links_json": dumps(factor_form),
        "judgment_status": judgment,
        "judgment_reason": "; ".join(reason_bits),
        "decision_method": "rule_context",
        "codebook_version": CODEBOOK_VERSION,
        "needs_review": needs_review,
        "review_reasons_json": dumps(review_reasons),
        "chiikawa_mentioned": has_ip,
    }


def content_tokens(tokens: list) -> list[str]:
    out = []
    for token in tokens:
        tag = token.tag
        base = tag.split("-")[0]
        if base not in CONTENT_TAGS and tag not in CONTENT_TAGS:
            continue
        form = token.form
        if form in STOP_FORMS or URL_TOKEN.match(form):
            continue
        if tag == "SL" and (len(form) < 4 or URL_TOKEN.match(form) or "." in form or "/" in form):
            if form.lower() not in {"chiikawa"}:
                continue
        if tag == "NNB" and form in {"수", "것", "등", "뿐", "데"}:
            continue
        out.append(f"{form}/{tag}")
    return out


def self_check() -> None:
    cases = [
        (
            "하치와레 키링 너무 귀여워서 샀는데 가격이 비싸서 하나밖에 안 샀어",
            {"등장인물:하치와레", "키링", "외형호감", "구매완료", "구매부정", "가격부담"},
            {"외형불만"},
        ),
        (
            "생각보다 비싸서 결국 안샀다 하치와레",
            {"구매부정", "가격부담", "등장인물:하치와레"},
            {"구매완료"},
        ),
        ("이 결과는 시사하는 바가 크다", set(), {"등장인물:시사"}),
        ("모몽가, 시사 인형", {"등장인물:모몽가", "등장인물:시사", "인형"}, set()),
        ("카니발 티켓 예매", set(), {"등장인물:카니"}),
        ("차카니백개 먹은 목소리로 치이카와", {"판단불명확:치이카와이름"}, {"등장인물:카니"}),
        ("빤쮸우사기 마스코트 샀다", {"다른IP:빤쮸토끼", "구매완료"}, {"등장인물:우사기"}),
        ("파자마 파티즈 새 소식이 있다", {"다른작품:파자마파티즈"}, {"작품:치이카와", "의류"}),
        ("스파오 먼작귀 키즈 파자마 출시", {"작품:치이카와", "의류", "출시입고안내"}, {"다른작품:파자마파티즈"}),
        ("먼작귀 키링 귀여워", {"작품:치이카와", "키링", "외형호감"}, {"등장인물:치이카와", "구매완료"}),
        ("치이카와랑 하치와레가 같이 있어", {"등장인물:치이카와", "등장인물:하치와레"}, {"판단불명확:치이카와이름"}),
        ("치이카와 너무 귀엽다", {"판단불명확:치이카와이름", "외형호감"}, {"구매완료", "구매희망"}),
        ("치이카와가 브로콜리 싫어해", {"작중감정"}, {"가격부담", "외형불만"}),
        ("치이카와 아크릴 판매합니다 귀여워요", {"홍보문호감", "판매양도", "아크릴"}, {"외형호감"}),
        ("하치와레 진짜 착함", {"등장인물:하치와레", "성격특성"}, set()),
        ("우사기는 먹고 치이카와는 본다", {"등장인물:우사기", "등장인물:치이카와"}, set()),
        ("시사와 랏코 인형", {"등장인물:시사", "등장인물:랏코", "인형"}, set()),
        ("카니와 함께하는 치이카와", {"등장인물:카니", "등장인물:치이카와"}, {"판단불명확:치이카와이름"}),
        ("치이카와 아크릴 판매합니다\n정말 귀여워요", {"홍보문호감", "판매양도", "아크릴"}, {"외형호감"}),
        ("우사기님께서 자막을 달았어요 치이카와", {"확인필요:우사기"}, {"등장인물:우사기"}),
        ("이번에 나온 천사악마 치이카와 정말 귀엽더라고요", {"외형호감"}, {"성격특성", "가격부담"}),
        ("배송비는 제가 부담합니다 치이카와", set(), {"가격부담"}),
    ]
    failures = []
    for text, expected, forbidden in cases:
        result = classify_post(make_analysis_text(text))
        labels = set()
        for column in (
            "mention_labels_json",
            "form_labels_json",
            "factor_labels_json",
            "action_labels_json",
            "context_labels_json",
        ):
            labels.update(item["label"] for item in json.loads(result[column]))
        missing = expected - labels
        extra = forbidden & labels
        if missing or extra:
            failures.append((text, sorted(missing), sorted(extra), sorted(labels)))
    if failures:
        detail = "\n".join(f"{text}\n  missing={missing}\n  forbidden={extra}\n  labels={labels}" for text, missing, extra, labels in failures)
        raise AssertionError(detail)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    posts = read_table(NORM / "x_posts.csv", "x_posts")
    post_keywords = read_table(NORM / "x_post_keywords.csv", "x_post_keywords")
    sources = read_table(NORM / "x_post_sources.csv", "x_post_sources")
    files = read_table(NORM / "x_source_files.csv", "x_source_files")
    if len(posts) != 5000 or posts["post_id"].nunique() != 5000:
        raise AssertionError("x_posts 행 수 또는 post_id 유일성이 기대와 다르다.")
    if int(posts["view_count"].isna().sum()) != 946:
        raise AssertionError("조회수 결측이 946이 아니다.")
    if int((posts["account_name"] == "null").sum()) != 2:
        raise AssertionError("계정 이름 문자열 null이 2건이 아니다.")
    if posts["post_id"].duplicated().any():
        raise AssertionError("post_id 중복")
    src = sources.merge(files, on="source_file", how="left", validate="many_to_one")
    if src["post_id"].duplicated().any() or len(src) != len(posts):
        raise AssertionError("출처 연결이 게시물 1대1이 아니다.")
    kw = (
        post_keywords.sort_values(["post_id", "keyword_order"])
        .groupby("post_id", sort=False)["keyword"]
        .apply(list)
    )
    if kw.index.nunique() != len(posts):
        raise AssertionError("키워드가 없는 게시물이 있다. 키워드 행으로 게시물을 늘리지는 않는다.")
    posts = posts.merge(src[["post_id", "source_file", "source_row", "source_year"]], on="post_id", how="left", validate="1:1")
    posts["collection_keywords_json"] = posts["post_id"].map(lambda pid: dumps(kw.loc[pid]))
    posts["created_year_kst"] = posts["created_at"].dt.year.astype("int64")
    return posts, post_keywords, sources, files


def analyze_all(posts: pd.DataFrame, kiwi: Kiwi) -> tuple[pd.DataFrame, pd.DataFrame]:
    WORK.mkdir(parents=True, exist_ok=True)
    BATCH.mkdir(parents=True, exist_ok=True)
    progress_path = WORK / "progress.json"
    completed: dict[str, dict] = {}
    errors: list[dict] = []
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("version") == CODEBOOK_VERSION:
            for path in sorted(BATCH.glob("batch_*.parquet")):
                frame = pd.read_parquet(path)
                for record in frame.to_dict(orient="records"):
                    completed[str(record["post_id"])] = record
            error_path = WORK / "errors_partial.csv"
            if error_path.exists():
                old = pd.read_csv(error_path, dtype="string", encoding="utf-8-sig", keep_default_na=False)
                errors.extend(old.to_dict(orient="records"))
        else:
            for path in BATCH.glob("batch_*.parquet"):
                path.unlink()
    ids = posts["post_id"].astype(str).tolist()
    texts = posts["text"].tolist()
    pending_index = [i for i, pid in enumerate(ids) if pid not in completed]
    batch_size = 500
    print(f"pending {len(pending_index)} completed {len(completed)}", flush=True)
    for batch_no, start in enumerate(range(0, len(pending_index), batch_size)):
        indexes = pending_index[start : start + batch_size]
        kiwi_inputs = [make_kiwi_text(make_analysis_text(texts[i])) for i in indexes]
        tokenized = list(kiwi.tokenize(kiwi_inputs))
        records = []
        for index, tokens in zip(indexes, tokenized):
            pid = ids[index]
            try:
                analysis = make_analysis_text(texts[index])
                classified = classify_post(analysis)
                classified["post_id"] = pid
                classified["analysis_text"] = analysis
                classified["content_tokens_json"] = dumps(content_tokens(tokens))
                records.append(classified)
                completed[pid] = classified
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "post_id": pid,
                        "stage": "classify",
                        "error_type": type(exc).__name__,
                        "error_message": f"{exc}\n{traceback.format_exc(limit=2)}",
                    }
                )
        batch_frame = pd.DataFrame(records)
        batch_id = f"{len(list(BATCH.glob('batch_*.parquet'))):04d}"
        if len(batch_frame):
            batch_frame.to_parquet(BATCH / f"batch_{batch_id}.parquet", index=False)
        pd.DataFrame(errors).to_csv(WORK / "errors_partial.csv", index=False, encoding="utf-8-sig")
        progress_path.write_text(
            dumps({"version": CODEBOOK_VERSION, "completed": len(completed), "failed": len(errors), "last_batch": batch_id}),
            encoding="utf-8",
        )
        print(f"batch {batch_id} rows {len(records)} total {len(completed)} errors {len(errors)}", flush=True)
    analysis = pd.DataFrame([completed[pid] for pid in ids if pid in completed])
    error_frame = pd.DataFrame(errors, columns=["post_id", "stage", "error_type", "error_message"])
    return analysis, error_frame


def token_rows(frame: pd.DataFrame) -> pd.DataFrame:
    hit_count: Counter[str] = Counter()
    post_count: Counter[str] = Counter()
    for raw in frame["content_tokens_json"]:
        tokens = json.loads(raw)
        hit_count.update(tokens)
        post_count.update(set(tokens))
    rows = []
    for token, hits in hit_count.items():
        form, tag = token.rsplit("/", 1)
        rows.append(
            {
                "token": form,
                "pos": tag,
                "hit_count": hits,
                "post_count": post_count[token],
                "surface_is_collection_keyword": form in COLLECTION_KEYWORDS or (form == "파자마파티즈"),
                "collection_note": "검색 키워드 표면형. 수집 방식의 영향을 받으므로 관심도 순위로 쓰지 않는다."
                if form in COLLECTION_KEYWORDS
                else "",
            }
        )
    out = pd.DataFrame(rows).sort_values(["post_count", "hit_count", "token"], ascending=[False, False, True])
    return out


def expression_rows(frame: pd.DataFrame) -> pd.DataFrame:
    phrase_posts: dict[str, set[str]] = defaultdict(set)
    phrase_hits: Counter[str] = Counter()
    phrases = {
        "사고 싶다": re.compile(r"사고\s*싶|사고싶"),
        "안 샀다": re.compile(r"안\s*샀|안샀|못\s*샀|못샀"),
        "샀다": re.compile(r"(?<![안못])(?<!안 )(?<!못 )샀"),
        "귀엽다": re.compile(r"귀여|귀엽|기여워"),
        "비싸다": re.compile(r"비싸"),
        "파자마 파티즈": PAJAMA_WORK_RE,
        "갑옷씨": ARMOR_RE,
        "먼작귀": re.compile(r"먼작귀"),
    }
    pair_posts: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in frame.itertuples(index=False):
        pid = row.post_id
        text = row.analysis_text
        for name, pattern in phrases.items():
            found = pattern.findall(text)
            if found:
                phrase_posts[name].add(pid)
                phrase_hits[name] += len(found)
        repeats = REPEAT_RE.findall(text)
        if repeats:
            phrase_posts["자모 반복(ㅋㅎㅠㅜ)"].add(pid)
            phrase_hits["자모 반복(ㅋㅎㅠㅜ)"] += len(repeats)
        for link in json.loads(row.form_action_links_json):
            pair_posts[("form_action", link["form"], link["action"])].add(pid)
        for link in json.loads(row.factor_form_links_json):
            if link.get("audience") == "user":
                pair_posts[("factor_form_user", link["factor"], link["form"])].add(pid)
        labels = [item["label"] for item in json.loads(row.mention_labels_json) if item["label"].startswith("등장인물:")]
        for i, left in enumerate(labels):
            for right in labels[i + 1 :]:
                pair_posts[("character_pair_same_post", left, right)].add(pid)
    rows = []
    for name, posts in phrase_posts.items():
        rows.append(
            {
                "expression": name,
                "expression_type": "phrase",
                "cooccurrence_unit": "post_text",
                "post_count": len(posts),
                "hit_count": phrase_hits[name],
                "left": name,
                "right": "",
                "notes": "게시물 본문 기준. 검색 키워드 테이블은 세지 않는다.",
            }
        )
    for (kind, left, right), posts in pair_posts.items():
        if len(posts) < 5 and kind != "form_action":
            continue
        unit = UNIT_NAME if kind != "character_pair_same_post" else "same_post"
        rows.append(
            {
                "expression": f"{left} + {right}",
                "expression_type": kind,
                "cooccurrence_unit": unit,
                "post_count": len(posts),
                "hit_count": len(posts),
                "left": left,
                "right": right,
                "notes": "형태-행동·요인-형태는 같은 줄/절. 등장인물 쌍은 같은 게시물. 원인은 아니다.",
            }
        )
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["expression_type", "post_count"], ascending=[True, False])
    return out


def yearly_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    years = sorted(frame["created_year_kst"].unique())
    slices = [("ALL", frame)] + [(str(year), frame[frame["created_year_kst"] == year]) for year in years]

    def add(year, axis, label, count, denom, note, not_mentioned, review, unclear):
        rows.append(
            {
                "year": year,
                "axis": axis,
                "label": label,
                "post_count": count,
                "denominator_posts": denom,
                "share": round(count / denom, 4) if denom else None,
                "axis_not_mentioned_posts": not_mentioned,
                "axis_review_posts": review,
                "axis_unclear_posts": unclear,
                "notes": note,
            }
        )

    for year, part in slices:
        denom = len(part)
        note = "분모는 해당 연도 게시물 수. 라벨은 복수라 비율 합이 1을 넘을 수 있다. 연도별 1000건 추출이며 전체 X 관심량이 아니다."
        status_cols = {
            "언급 대상": "mention_status",
            "상품·콘텐츠 형태": "form_status",
            "호감·불만 요인": "factor_status",
            "행동·의도": "action_status",
            "게시 맥락": "context_status",
        }
        label_cols = {
            "언급 대상": "mention_labels_json",
            "상품·콘텐츠 형태": "form_labels_json",
            "호감·불만 요인": "factor_labels_json",
            "행동·의도": "action_labels_json",
            "게시 맥락": "context_labels_json",
        }
        for axis, status_col in status_cols.items():
            not_mentioned = int((part[status_col] == "미언급").sum())
            review = int((part[status_col] == "확인 필요").sum())
            unclear = int((part[status_col] == "판단 불명확").sum())
            add(year, axis, "__status_미언급", not_mentioned, denom, note, not_mentioned, review, unclear)
            add(year, axis, "__status_확인필요", review, denom, note, not_mentioned, review, unclear)
            add(year, axis, "__status_판단불명확", unclear, denom, note, not_mentioned, review, unclear)
            add(year, axis, "__status_분류가능", int((part[status_col] == "분류 가능").sum()), denom, note, not_mentioned, review, unclear)
            counts: Counter[str] = Counter()
            for raw in part[label_cols[axis]]:
                labels = {item["label"] for item in json.loads(raw) if not item.get("needs_review")}
                counts.update(labels)
            for label, count in counts.most_common():
                add(year, axis, label, count, denom, note, not_mentioned, review, unclear)
        user_cute = 0
        for raw in part["factor_labels_json"]:
            if any(item["label"] == "외형호감" and item.get("audience") == "user" for item in json.loads(raw)):
                user_cute += 1
        add(year, "호감·불만 요인", "외형호감(이용자)", user_cute, denom, "홍보 문장 호감은 제외한 이용자 단위.", int((part["factor_status"] == "미언급").sum()), int((part["factor_status"] == "확인 필요").sum()), int((part["factor_status"] == "판단 불명확").sum()))
    return pd.DataFrame(rows)


def write_table(path: Path, frame: pd.DataFrame) -> None:
    export = frame.copy()
    if "created_at" in export.columns:
        export["created_at"] = frame["created_at"].map(lambda value: value.isoformat(sep=" ", timespec="seconds"))
    export.to_csv(path, index=False, encoding="utf-8-sig", na_rep="", lineterminator="\n")


def validate(posts: pd.DataFrame, out: pd.DataFrame, errors: pd.DataFrame) -> dict:
    merged = posts.merge(out, on="post_id", how="left", suffixes=("", "_out"), validate="1:1")
    checks = {
        "input_posts": int(len(posts)),
        "completed_posts": int(len(out)),
        "failed_posts": int(len(errors)),
        "sum_matches_input": int(len(out) + len(errors) == len(posts)),
        "duplicate_post_id": int(out["post_id"].duplicated().sum()),
        "missing_from_input": int(len(set(posts["post_id"]) - set(out["post_id"]) - set(errors["post_id"] if len(errors) else []))),
        "text_preserved": bool(out["text"].astype(str).equals(posts.set_index("post_id").loc[out["post_id"], "text"].astype(str).reset_index(drop=True))),
        "view_na": int(out["view_count"].isna().sum()),
        "view_na_expected": 946,
        "literal_null_name": int((out["account_name"] == "null").sum()),
        "created_year_sum": int(out["created_year_kst"].value_counts().sort_index().to_dict().__len__()),
        "year_counts": {str(k): int(v) for k, v in out["created_year_kst"].value_counts().sort_index().items()},
        "source_year_mismatch": int((out["source_year"].astype("int64") != out["created_year_kst"]).sum()),
        "review_posts": int(out["needs_review"].sum()),
        "judgment_counts": {str(k): int(v) for k, v in out["judgment_status"].value_counts().items()},
        "mention_status_counts": {str(k): int(v) for k, v in out["mention_status"].value_counts().items()},
    }
    # text equality in input order
    aligned = posts[["post_id", "text", "view_count", "account_name", "created_at"]].merge(
        out[["post_id", "text", "view_count", "account_name", "created_at"]],
        on="post_id",
        suffixes=("_in", "_out"),
        how="inner",
    )
    checks["text_preserved"] = bool((aligned["text_in"] == aligned["text_out"]).all())
    checks["view_na_preserved"] = bool(aligned["view_count_in"].isna().equals(aligned["view_count_out"].isna()))
    checks["null_name_preserved"] = bool((aligned["account_name_in"] == aligned["account_name_out"]).all())
    checks["clock_preserved"] = bool(
        (aligned["created_at_in"].dt.strftime("%Y-%m-%d %H:%M:%S") == aligned["created_at_out"].dt.strftime("%Y-%m-%d %H:%M:%S")).all()
    )
    return checks


def label_counter(frame: pd.DataFrame, column: str, audience: str | None = None) -> Counter:
    counts: Counter[str] = Counter()
    for raw in frame[column]:
        labels = []
        for item in json.loads(raw):
            if item.get("needs_review"):
                continue
            if audience is not None and item.get("audience") not in {None, audience}:
                continue
            labels.append(item["label"])
        counts.update(set(labels))
    return counts


def example_quotes(frame: pd.DataFrame, column: str, label: str, limit: int = 3, audiences: set[str] | None = None) -> list[str]:
    allowed = audiences or {"user"}
    quotes = []
    for row in frame.itertuples(index=False):
        for item in json.loads(getattr(row, column)):
            audience = item.get("audience") or "user"
            if item["label"] == label and not item.get("needs_review") and audience in allowed:
                quotes.append(item["evidence"])
                break
        if len(quotes) >= limit:
            break
    return quotes


def write_markdown(out: pd.DataFrame, checks: dict, tokens: pd.DataFrame, expressions: pd.DataFrame, yearly: pd.DataFrame) -> None:
    mention = label_counter(out, "mention_labels_json")
    forms = label_counter(out, "form_labels_json")
    factors = label_counter(out, "factor_labels_json", audience="user")
    factors_all = label_counter(out, "factor_labels_json")
    actions = label_counter(out, "action_labels_json", audience="user")
    promo_cute = 0
    user_cute = factors.get("외형호감", 0)
    for raw in out["factor_labels_json"]:
        if any(item["label"] == "홍보문호감" for item in json.loads(raw)):
            promo_cute += 1
    n = len(out)
    review_n = int(out["needs_review"].sum())
    fail_n = checks["failed_posts"]

    def pct(count: int) -> str:
        return f"{count}건 ({count / n:.1%})" if n else "0건"

    plan = f"""# X 게시물 텍스트 분석 계획

- 기준 버전: `{CODEBOOK_VERSION}`
- 기준 폴더: `{BASE}`
- 분석 단위: 고유 `post_id` 1개. 키워드 연결 행으로 게시물을 늘리지 않는다.

## 분석 질문

1. 어떤 캐릭터·상품·콘텐츠가 언급되는가?
2. 이용자가 표현하는 호감·불만의 이유는 무엇인가?
3. 어떤 표현이 구매·소장·관람 등의 행동이나 의도와 함께 나타나는가?
4. 연도별로 표현과 반응의 구성이 어떻게 달라지는가?
5. 관측 결과를 신규 IP 평가 항목 후보로 어떻게 연결할 수 있는가?

프로젝트 방향은 대원미디어의 국내 창작자 협업과 차기 캐릭터 IP 선정 기준이다. 치이카와 국내 SNS 반응에서 반복되는 표현을 평가 항목 후보로 옮기되, 이 게시물 집합을 시장 점유율이나 판매량으로 쓰지 않는다.

## 입력 관계

| 파일 | 사용 |
| --- | --- |
| `normalized/x_posts.csv` | 본문 분석의 주 입력. 게시물 1행 |
| `normalized/x_post_keywords.csv` | 수집 키워드를 게시물당 JSON으로만 첨부 |
| `normalized/x_keywords.csv` | 검색 키워드 목록 확인 |
| `normalized/x_post_sources.csv` | 원본 파일·행 추적. 이 데이터에서는 게시물과 1대1 |
| `normalized/x_source_files.csv` | `source_year`는 파일 기준 연도 |
| 정의서·정규화 보고서 | 자료형, 결측, 키워드 의미 확인 |
| `프로젝트흐름.pdf` | 사업 질문 확인. 재무 결론은 이 분석 범위가 아님 |

`integrated`, `typed`, 연도별 원본 CSV는 분석 입력에 넣지 않았다. `classification` 폴더는 읽지 않았다.

연도는 `created_at`을 한국시간으로 해석한 연도다. 입력 시각은 모두 `+09:00`이었고, 이미 한국시간인 값에 9시간을 더하지 않았다. 이번 5,000건에서 `source_year`와 작성 연도의 불일치는 {checks['source_year_mismatch']}건이지만, 의미가 다르므로 서로 대체하지 않았다.

## 도구

- Python, pandas, pyarrow
- kiwipiepy {__import__('kiwipiepy').__version__}: 형태소 분리와 사용자 사전
- 문맥 라벨: 줄·절 단위 규칙. Kiwi는 호감의 대상이나 구매 완료 여부를 판정하지 않는다.
- 설치된 MCP 가운데 한국어 문맥 분류기는 없었다. 게시물을 외부 유료 API로 보내지 않았다.

## 처리 규칙

- 원본 `text`는 유지하고 `analysis_text`에서 URL, @계정, 해시태그 기호 `#`만 공백으로 바꾼다. 해시태그 단어는 남긴다.
- 이모지, ㅋㅋ·ㅠㅠ, 부정어는 삭제하지 않는다. 이모지만으로 호감 라벨을 주지 않는다.
- 조회수 빈칸은 결측으로 둔다. 계정 이름 문자열 `null`은 결측이 아니다.
- 검색 키워드가 본문에 없다는 이유로 캐릭터 라벨을 만들지 않는다.
- 동시 등장 기본 단위는 `{UNIT_NAME}`이다. 등장인물 쌍만 같은 게시물 단위를 따로 적는다.
- 판매글의 '귀엽다'는 `홍보문호감`으로 두고 이용자 호감 집계에서 뺀다.
- 가격 불만은 `가격부담`이지 캐릭터 부정이 아니다.
- 확인이 필요한 게시물이 있어도 전체 처리를 멈추지 않는다.

## 한계

- 연도별 파일은 각 1,000건이다. 전체 X 언급량, 시장점유율, 장기 충성도로 일반화하지 않는다.
- 이미지, 영상, 링크 안 페이지는 보지 않았다.
- 규칙이 문장 주어를 놓치면 작중 행동과 이용자 행동이 섞일 수 있다. 그 경우는 확인 필요로 남기거나 감사 항목으로 점검했다.
- 정답 집합과 비교하지 않았으므로 정확도 수치를 적지 않는다.
"""
    (DOCS / "text_analysis_plan.md").write_text(plan, encoding="utf-8")

    codebook = f"""# 텍스트 분석 기준서

- 기준 버전: `{CODEBOOK_VERSION}`
- 판정 방법: `rule_context`
- 모델이 게시물마다 문맥을 다시 읽은 라벨은 없다. 문맥 규칙은 표본 문장을 보고 코드로 고정했고, 도구가 판단하지 못하는 대상·부정·홍보문은 확인 필요 또는 별도 라벨로 남긴다.

## 변경 이력

| 버전 | 내용 |
| --- | --- |
| 2026-10-29.1 | 전체 게시물에 처음 적용. 파일럿 승인 단계 없이 기준을 데이터 표현에 맞춰 확정 |
| 2026-10-29.2 | 조사와 붙은 이름, 홍보문 분리, 같은 줄의 행동만 부여, 다른 사람 구매는 확인 필요, 작중 식품 제외, 번역은 정보공유 |
| 2026-10-29.3 | 가격의 단독 '부담'과 '천사악마' 안의 '사악'은 요인에서 제외. `하치`·`치이`는 자동 통합하지 않음 |

## 분석용 텍스트

| 항목 | 규칙 |
| --- | --- |
| 줄바꿈 | 분석 텍스트만 CRLF를 LF로 바꾼다. 저장하는 원문 `text`는 CSV에서 읽은 값 그대로다. |
| URL | `http`, `https`, `www`로 시작하는 구간을 공백으로 바꾼다. URL 안의 영문 이름을 언급으로 세지 않는다. |
| 계정 멘션 | `@영문`은 공백으로 바꾼다. |
| 해시태그 | `#`만 공백으로 바꾼다. `#치이카와`의 `치이카와`는 남긴다. |
| 이모지·반복·부정 | 삭제하지 않는다. ㅋㅋ·ㅠㅠ는 표현 빈도에만 넣고 유머·슬픔 라벨의 단독 근거로 쓰지 않는다. |
| 보호 표기 | Kiwi 입력에서만 `파자마 파티즈`, `갑옷 아저씨`, `갑옷 씨`, `갑옷 상`, `빤쮸 우사기`, `빤쮸 토끼`를 붙여 한 단어로 둔다. |

## 사용자 사전

Kiwi 사용자 사전(NNP)에 올린 단어: 치이카와, 치이까와, 치카와, 하치와레, 하치와래, 우사기, 모몽가, 모몬가, 랏코, 쿠리만쥬, 쿠리만주, 먼작귀, 아노코, 데카츠요, 갑옷씨, 갑옷아저씨, 갑옷상, 파자마파티즈, 빤쮸우사기, 빤쮸토끼, 키링, 키체인, 키홀더, 가챠, 피규어, 넨도로이드, 소프비, 아크릴, 스티커, 파우치, 뱃지, 캔뱃지, 콜라보, 팝업, 언박싱, 마스코트, 누이구루미, 다이어리, 산리오, 농담곰, 스파오, 다이소, 나가노, 스트랩.

`시사`, `카니`, `갑옷`은 짧은 일반어와 겹치므로 사용자 사전에 넣지 않고 단어 경계와 문맥으로 본다.

## 표기 통합

| 분석 표기 | 원문 표기 | 근거 |
| --- | --- | --- |
| 하치와레 | 하치와레, 하치와래 | 같은 이름의 표기 차이 |
| 모몽가 | 모몽가, 모몬가 | 같은 이름의 표기 차이 |
| 쿠리만쥬 | 쿠리만쥬, 쿠리만주 | 같은 이름의 표기 차이 |
| 치이카와 이름 | 치이카와, 치이까와, 치카와, chiikawa, ちいかわ, 吉伊卡哇 | 같은 이름. 작품/주인공 구분은 표기가 아니라 문맥으로 한다 |
| 갑옷씨 | 갑옷씨, 갑옷 아저씨, 갑옷상 | 본문에서 같은 인물을 가리키는 호칭 |
| 파자마파티즈 | 파자마 파티즈, 파자마파티즈 | 나가노의 별개 작품명 |

합치지 않는 것: `토끼`만으로 우사기를 만들지 않는다. `빤쮸우사기`·`빤쮸토끼`는 치이카와 우사기가 아니다. `파자마`만으로 파자마 파티즈를 만들지 않는다. `갑옷`만으로는 갑옷씨를 확정하지 않는다. `가르마`, `하치`, `치이`는 하치와레·치이카와의 짧은 호칭으로 쓰이기도 하지만 자동으로 합치지 않는다. `천사악마` 안의 `사악`은 성격 평가가 아니다.

## 불용어

빈도표에서 뺀 기능어: 하다, 되다, 있다, 오다, 가다, 싶다, 않다, 수, 것, 등, 너무, 진짜, 나, 내 등. 부정 부사 `안`, `못`은 라벨 판정에는 쓰되, 위 불용어 목록의 '않'과 함께 주제 빈도에서는 제외한다. URL 조각 `http`, `com`, `co`는 제외한다.

`하/VV`처럼 형태소 분석기가 잘게 나누는 기능 동사는 주제 단어로 해석하지 않는다.

## 검색 키워드

수집 키워드 13개(갑옷씨, 데카츠요, 랏코, 먼작귀, 모몽가, 시사, 아노코, 우사기, 치이카와, 카니, 쿠리만쥬, 파자마 파티즈, 하치와레)는 빈도표에 `surface_is_collection_keyword`로만 표시한다. 본문 라벨로 복사하지 않는다.

## 분류 축

복수 라벨을 허용한다. 근거는 그 라벨이 나온 단위의 문장이다. 형태와 행동, 요인과 형태는 같은 줄 또는 140자 안팎의 절에 같이 있을 때만 연결한다. 긴 단위에서 연결되면 확인 필요로 표시한다.

### 언급 대상

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 작품:치이카와 | 먼작귀, 또는 치이카와 이름이 애니·영화·만화·세계관·시리즈와 함께 있음 | 검색 키워드만 있는 경우 |
| 등장인물:이름 | 하치와레, 우사기, 모몽가, 랏코, 쿠리만쥬, 아노코, 데카츠요, 시사, 카니, 갑옷씨. 치이카와는 다른 등장인물과 같이 나올 때 | 시사하는·시사점, 카니발, 단어 내부의 카니, 빤쮸우사기 |
| 판단불명확:치이카와이름 | 치이카와 계열 표기만 있고 작품 단서도 다른 등장인물도 없음 |  |
| 다른작품:파자마파티즈 | 파자마 파티즈 전체 이름 | 파자마, 잠옷 |
| 다른IP:농담곰, 다른IP:빤쮸토끼 | 해당 이름 | 치이카와 라벨로 합치지 않음 |
| 확인필요:갑옷 | 수식 없는 갑옷 |  |

시사·카니·우사기는 작품 단서(다른 이름, 굿즈, 애니)가 게시물에 없으면 확인 필요하다. 이번 데이터에서 시사·카니의 오탐 패턴 `시사하는`은 거의 없었고, 독립 우사기 중 다른 단서가 없는 글은 확인 필요로 남긴다.

### 상품·콘텐츠 형태

키링, 스트랩, 인형, 마스코트, 피규어, 가챠(가챠·쿠지·제일복권·뽑기), 스티커, 아크릴, 뱃지, 파우치, 캘린더, 문구, 의류, 영화, 애니, 영상, 팝업, 콜라보, 식품.

마스코트는 인형과 따로 둔다. 식품 단어가 마스코트·인형과 같이 있고 맛·섭취 단서가 없으면 식품으로 넣지 않는다. `랜덤` 한 단어는 가챠가 아니다.

### 호감·불만 요인

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 외형호감 | 귀엽다, 예쁘다, 깜찍, 말랑, 폭신. 이용자 문장 | 홍보·판매 문장, 부정형, 구매 의도 |
| 홍보문호감 | 판매합니다 등 제공 문장 안의 호감 | 이용자 호감 집계 |
| 외형불만 | 안 귀엽다, 귀엽지 않다 | 가격이 비싸다는 문장 |
| 유머 | 웃기다, 빵 터지다 | ㅋㅋ만 있는 문장 |
| 정서적공감 | 힐링, 위로, 소중, 공감 | 힐링템 |
| 관계서사 | 우정, 세계관, 명장면, 친구 사이 | 트친, 친구 단독 |
| 성격특성 | 착하다, 기특, 잔인, 사악 | 잔인·사악은 웃음 단서가 없으면 확인 필요 |
| 가격부담 | 비싸다, 아깝다, 부담스럽다, 가격이 부담 | `부담입니다`처럼 약관·배송비 부담, 캐릭터 부정 |
| 가격긍정 | 저렴, 가성비, 비싸다와 무관한 싸다 | 판매 문장의 가격 안내 |
| 희소성 | 품절, 한정, 재입고, 구하기 힘듦 | 그 자체를 호감으로 단정하지 않음 |
| 상품디자인호감/불만 | 마감·재질·디테일·퀄리티와 평가가 같은 단위 | 디자인 단어만 있는 경우 |
| 작중감정 | 등장인물 주어의 싫어하다·울다 | 이용자 불만 집계 |
| 불호 | 1인칭 싫다인데 요인이 불명확 | 확인 필요 |

### 행동·의도

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 구매완료 | 샀다, 구매했다, 겟했다, 질렀다, 사서 | 안 샀다, 사고 싶다, 사기당하다 |
| 구매희망 | 사고 싶다, 살까, 사야지, 삽니다, 구합니다, 양도받다 | 구매 완료 |
| 구매부정 | 안 샀다, 못 샀다, 사고 싶지 않다 | 구매 완료 |
| 소장희망 | 갖고 싶다, 소장하고 싶다. 사고 싶다와 같이 있으면 구매희망 |  |
| 소지사용 | 언박싱, 개봉, 소장 중, 가방에 달다 | 판매글의 도착 안내 |
| 판매양도 | 판매합니다, 팝니다, 양도합니다 | 작중 교환, 판매라는 단어만 있는 경고문 |
| 거래언급 | 판매·양도 단어만 있음 | 작성자의 판매 완료로 세지 않음 |
| 교환 | 교환합니다, 교환과 양도 병기 | 작중 '교환하자' |
| 공구 | 공구 | 구매 완료·판매량 |
| 나눔 | 나눔 | 판매 |
| 가챠뽑기 | 뽑았다 |  |
| 관람 | 애니·영화·정주행·관람 | 영상 짤만 본 경우 |
| 팝업방문 | 팝업과 이동 동사 | 팝업 단어만 |
| 영상시청 | 영상·짤을 봤다는 표현 | URL만 있는 경우 |
| 작중행동 | 등장인물 주어의 행동, 작중 교환, 등장인물이 샀다는 문장 | 이용자 행동 집계 |
| 단순언급 | 작품 언급은 있으나 위 행동이 없음 |  |

### 게시 맥락

개인반응, 개인경험, 판매양도글, 출시입고안내, 이벤트홍보, 장면공유, 맥락단정불가.

### 판단 상태

- 분류 가능: 근거 문장으로 라벨을 부여했다.
- 판단 불명확: 치이카와 이름만 있어 작품과 주인공을 일부러 가르지 않았다. 처리 실패가 아니다.
- 미언급: 그 축의 근거가 본문에 없다.
- 확인 필요: 이름 경계, 주어, 긴 문장의 연결처럼 규칙의 근거가 부족하다.

한 게시물의 `judgment_status`는 어느 축이든 확인 필요가 있으면 `확인 필요`, 아니면 라벨이나 판단 불명확이 있으면 `분류 가능`, 아니면 `미언급`이다.

## 집계

비율의 분모는 게시물 수다. 키워드 행 7,466을 분모로 쓰지 않는다. 조회수가 비어 있어도 게시물을 빼지 않는다.
"""
    (DOCS / "text_codebook.md").write_text(codebook, encoding="utf-8")

    def top_line(counter: Counter, k: int = 12) -> str:
        return ", ".join(f"{label} {count}" for label, count in counter.most_common(k))

    quotes_cute = example_quotes(out, "factor_labels_json", "외형호감")
    quotes_price = example_quotes(out, "factor_labels_json", "가격부담")
    quotes_buy = example_quotes(out, "action_labels_json", "구매완료")
    quotes_wish = example_quotes(out, "action_labels_json", "구매희망")
    quotes_neg = example_quotes(out, "action_labels_json", "구매부정")
    quotes_story = example_quotes(out, "factor_labels_json", "작중감정", audiences={"character_in_story"})

    def qblock(lines: list[str]) -> str:
        if not lines:
            return "- 해당 라벨의 예시 문장을 찾지 못했다."
        return "\n".join(f"- {line}" for line in lines)

    chiikawa_posts = int(out["chiikawa_mentioned"].sum())
    ip = f"""# 신규 IP 평가 항목으로 옮길 수 있는 관측

이 문서는 X 게시물 {n}건에서 확인한 표현과, 그 표현이 대원미디어의 차기 국내 창작자 IP 평가에서 어떤 질문 후보가 될 수 있는지를 적는다. 후보가 곧 선정 기준의 확정은 아니다.

데이터는 2022~2026년 파일에서 각각 1,000건이다. 검색 키워드로 모인 글이므로 캐릭터 이름 빈도는 수집 설계의 영향을 받는다. 판매글·구매 희망은 판매량·구매량이 아니다. 연령·성별, 장기 충성도, 시장점유율은 이 게시물만으로 말하지 않는다.

## 1. 외형 호감이 반복된다

- 관측된 표현: 이용자 문장의 외형호감 {pct(user_cute)}. 홍보·판매 문장의 호감은 {pct(promo_cute)}이며 이용자 집계에 넣지 않았다.
- 원문 근거:
{qblock(quotes_cute)}
- 해석 가능한 범위: 이 표본에서 호감은 '작다, 말랑하다, 귀엽다' 같은 외형 표현과 자주 같이 나온다. 그 표현이 구매의 원인은 아니다.
- 신규 IP 평가 항목 후보: 작은 실루엣과 표정이 한 문장으로 전달되는지. 상품 사진 없이도 텍스트만으로 외형 인상이 반복되는가.
- 추가 검증 자료: 이미지·영상 반응, 비구매 팬과 구매자의 인터뷰. 다른 국내 IP와 같은 기준의 비교 표본.

## 2. 작품 이름과 주인공 이름이 자주 겹친다

- 관측된 표현: 치이카와 계열을 본문에서 어떤 방식으로든 언급한 게시물 {pct(chiikawa_posts)}. 이 가운데 `판단불명확:치이카와이름` {mention.get('판단불명확:치이카와이름', 0)}건은 작품과 주인공을 가르지 못했다. `작품:치이카와` {mention.get('작품:치이카와', 0)}건, `등장인물:치이카와` {mention.get('등장인물:치이카와', 0)}건이다.
- 원문 근거: `먼작귀`는 작품 별칭으로만 두었다. 다른 등장인물과 나란히 나온 `치이카와`만 주인공으로 두었다.
- 해석 가능한 범위: 국내 반응은 개별 캐릭터 이름과 시리즈 별칭이 같이 돈다. 이름 빈도 1위를 주인공 인기로 읽으면 수집 키워드와 호칭 습관을 인기로 오인한다.
- 신규 IP 평가 항목 후보: 시리즈 이름과 대표 캐릭터 이름이 달라도 팬이 구분해서 부르는지, 아니면 한 이름으로 뭉치는지.
- 추가 검증 자료: 검색어별 노출을 통제한 표본. 이름 인지 조사.

등장인물 라벨 게시물 수(확인 필요 제외, 한 게시물에 여러 명 가능): {top_line(mention)}.

## 3. 상품 형태는 인형·마스코트·피규어·가챠·키링에 몰려 있다

- 관측된 표현: {top_line(forms)}.
- 원문 근거: 형태 단어가 본문에 있는 게시물만 센다. 검색 키워드로 대체하지 않는다.
- 해석 가능한 범위: 이 표본의 대화는 애니메이션 감상만이 아니라 작은 상품 이름으로 많이 구성된다. 영화 언급은 {forms.get('영화', 0)}건으로 작다.
- 신규 IP 평가 항목 후보: 초기에 인형·키링·가챠처럼 작은 상품으로 옮길 수 있는 형태인가. 영화화는 이 데이터만으로 평가 항목에 넣지 않는다.
- 추가 검증 자료: 실제 상품 출시 목록, 재고·가격, 구매 영수증이나 판매 데이터.

## 4. 귀엽다는 구매가 아니다

- 관측된 표현: 이용자 구매완료 {actions.get('구매완료', 0)}건, 구매희망 {actions.get('구매희망', 0)}건, 구매부정 {actions.get('구매부정', 0)}건, 소장희망 {actions.get('소장희망', 0)}건, 소지사용 {actions.get('소지사용', 0)}건, 판매양도(제공 표현)는 행동 표의 별도 집계, 관람 {actions.get('관람', 0)}건, 팝업방문 {actions.get('팝업방문', 0)}건, 영상시청 {actions.get('영상시청', 0)}건, 가챠뽑기 {actions.get('가챠뽑기', 0)}건.
- 원문 근거:
{qblock(quotes_buy)}
{qblock(quotes_wish)}
{qblock(quotes_neg)}
- 해석 가능한 범위: 희망, 완료, 부정은 서로 다른 라벨이다. 건수가 작으면 그 행동을 인기의 중심으로 올리지 않는다.
- 신규 IP 평가 항목 후보: 호감 표현과 따로, '사고 싶다/샀다/안 샀다'가 상품 형태와 같은 문장에 있는지만 점검한다. 문장 밖 추론으로 구매 점수를 주지 않는다.
- 추가 검증 자료: 주문·결제 데이터. 게시물 구매 표현의 표본 검수.

이용자 요인 상위: {top_line(factors)}.

## 5. 가격 불만은 캐릭터 부정이 아니다

- 관측된 표현: 가격부담 {factors.get('가격부담', 0)}건, 가격긍정 {factors.get('가격긍정', 0)}건, 희소성 {factors.get('희소성', 0)}건.
- 원문 근거:
{qblock(quotes_price)}
- 해석 가능한 범위: 비싸서 안 샀다는 문장은 가격과 구매 거부의 연결이지, 캐릭터를 싫다는 뜻이 아니다.
- 신규 IP 평가 항목 후보: 기대 가격대와 품절·양도 표현이 호감과 따로 나타나는가. 가격을 캐릭터 매력 점수의 감점으로 넣지 않는다.
- 추가 검증 자료: 소비자가, 양도 가격, 정가 비교.

## 6. 작중 감정과 이용자 감정을 나눈다

- 관측된 표현: 작중감정 {factors_all.get('작중감정', 0)}건, 관계서사 {factors.get('관계서사', 0)}건, 성격특성 {factors.get('성격특성', 0)}건, 정서적공감 {factors.get('정서적공감', 0)}건, 유머 {factors.get('유머', 0)}건. 작중감정은 이용자 불만 집계에 넣지 않는다.
- 원문 근거:
{qblock(quotes_story)}
- 해석 가능한 범위: '치이카와가 브로콜리를 싫어한다'는 이용자의 불만이 아니다. 우정·세계관 표현이 외형 호감보다 적으면, 서사를 외형과 같은 크기의 평가 항목으로 올리지 않는다.
- 신규 IP 평가 항목 후보: 성격이 한 문장으로 전달되는 조연이 있는지. 항목으로 채택하려면 관계서사·성격특성 건수가 외형 호감과 비교해 반복된다고 볼 수준인지 아래 수치로 판단한다.
- 추가 검증 자료: 에피소드 단위 댓글, 영상 댓글.

관계서사 {factors.get('관계서사', 0)}건, 성격특성 {factors.get('성격특성', 0)}건은 외형호감 {user_cute}건과 같은 분모 {n}건 위의 수다. 서사·성격은 관찰되지만 외형 표현보다 드물다. 따라서 '서사가 인기의 중심'이라는 평가 항목은 이 데이터만으로 두지 않는다. '조연의 성격이 한 문장으로 전달되는가'는 보조 질문으로만 둔다.

## 7. 연도 구성

연도별 분모는 각 1,000건이다(`ALL`은 {n}건). 비율은 `yearly_analysis_summary.csv`에 있다. 연도 간 차이는 이 추출 안에서의 구성 차이다. 2022년 조회수 결측이 집중돼 있으므로 조회수로 연도 인기를 비교하지 않는다.

## 8. 데이터로 채우지 않는 항목

- 국내 창작자 IP가 해외 IP보다 수익성이 높은지: 게시물에 근거가 없다.
- 장기 브랜드 충성도: 반복 표현과 작성 연도 분포만으로 입증하지 않는다.
- 이용자 연령·성별: 추정하지 않는다.
- 영화, 해외 진출, 라이선스 계약 조건: 언급이 매우 적거나 본문에 없다.

## 확인된 관측과 가설

확인된 관측은 위 건수와 원문 라벨이다. 가설은 '작은 상품으로 확장 가능한 외형'이 차기 IP 검토에 유용할 수 있다는 제안이며, 이 게시물이 그 가설을 사업 성과로 증명하지는 않는다.
"""
    (DOCS / "ip_selection_evidence.md").write_text(ip, encoding="utf-8")

    top_tokens = tokens.head(15)
    token_lines = "\n".join(
        f"| {row.token} | {row.pos} | {row.hit_count} | {row.post_count} | {'예' if row.surface_is_collection_keyword else ''} |"
        for row in top_tokens.itertuples(index=False)
    )
    report = f"""# X 게시물 텍스트 분석 보고서

- 기준 버전: `{CODEBOOK_VERSION}`
- 생성 스크립트: `text_analysis/label_pass/analyze_x_posts.py`

## 처리 건수

| 항목 | 값 |
| --- | --- |
| 입력 게시물 | {checks['input_posts']} |
| 처리 완료 | {checks['completed_posts']} |
| 처리 실패 | {checks['failed_posts']} |
| 확인 필요 게시물 | {checks['review_posts']} |
| 입력 = 완료 + 실패 | {bool(checks['sum_matches_input'])} |
| post_id 중복 | {checks['duplicate_post_id']} |
| 누락 | {checks['missing_from_input']} |
| 조회수 결측 | {checks['view_na']} (기대 946, 보존 {checks['view_na_preserved']}) |
| 계정 이름 문자열 null | {checks['literal_null_name']} (보존 {checks['null_name_preserved']}) |
| 원문 보존 | {checks['text_preserved']} |
| 시각 보존(9시간 추가 없음) | {checks['clock_preserved']} |
| source_year와 작성 연도 불일치 | {checks['source_year_mismatch']} |
| 판단 상태 | {checks['judgment_counts']} |
| 언급 상태 | {checks['mention_status_counts']} |
| 작성 연도 | {checks['year_counts']} |

정답 데이터와 비교하지 않았으므로 정확도는 적지 않는다. 확인 필요는 처리 실패가 아니다.

## 검증에서 본 규칙

- `안 샀다` 구간은 구매완료에서 제외하고 구매부정으로 둔다.
- `빤쮸우사기`는 우사기 라벨로 넣지 않는다.
- `시사하는` 형태는 등장인물 시사로 넣지 않는다.
- `카니발`, 다른 단어 내부의 `카니`는 제외한다.
- `파자마`만으로 파자마 파티즈를 만들지 않는다.
- 판매 문장의 귀엽다는 이용자 외형호감이 아니다.
- 가격부담 라벨의 대상은 가격이다.

## 주요 결과

치이카와 계열 본문 언급 {chiikawa_posts}건. 이용자 외형호감 {user_cute}건. 홍보문 호감 {promo_cute}건.

언급 라벨: {top_line(mention)}

형태 라벨: {top_line(forms)}

이용자 요인: {top_line(factors)}

이용자 행동: {top_line(actions)}

내용어 상위(불용어 제외). 수집 키워드 표면은 별도 표시.

| 토큰 | 품사 | 출현 횟수 | 게시물 수 | 수집 키워드 |
| --- | ---: | ---: | ---: | --- |
{token_lines}

연도별 수와 분모는 `yearly_analysis_summary.csv`에 있다. 상태 행 `__status_*`는 그 축에서 서로 겹치지 않는다. 개별 라벨 행은 복수 라벨이라 합이 분모를 넘을 수 있다.

## 해석 한계

이 집합은 연도별 인기·검색 표본에 가깝다. 전체 X의 관심량이나 국내 캐릭터 시장 점유율이 아니다. 링크와 이미지는 확인하지 않았다. Kiwi는 형태소를 나누지만, 호감의 대상과 구매 여부는 문장 규칙으로 부여했다. 규칙이 놓친 게시물은 `review_required.csv`에 있다.

## 저장 경로

- `{DOCS / 'text_analysis_plan.md'}`
- `{DOCS / 'text_codebook.md'}`
- `{TABLES / 'x_posts_text_analysis.csv'}`
- `{TABLES / 'x_posts_text_analysis.parquet'}`
- `{TABLES / 'token_frequency.csv'}`
- `{TABLES / 'expression_frequency.csv'}`
- `{TABLES / 'yearly_analysis_summary.csv'}`
- `{TABLES / 'review_required.csv'}`
- `{TABLES / 'processing_errors.csv'}`
- `{DOCS / 'ip_selection_evidence.md'}`
- `{DOCS / 'text_analysis_report.md'}`
- `{OUT / 'analyze_x_posts.py'}`
"""
    (DOCS / "text_analysis_report.md").write_text(report, encoding="utf-8")


def build_review(out: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in out.itertuples(index=False):
        if not row.needs_review:
            continue
        reasons = json.loads(row.review_reasons_json)
        if not reasons:
            reasons = [{"axis": "", "label": "", "reason": row.judgment_reason, "evidence": ""}]
        for reason in reasons:
            rows.append(
                {
                    "post_id": row.post_id,
                    "created_year_kst": row.created_year_kst,
                    "axis": reason.get("axis", ""),
                    "label": reason.get("label", ""),
                    "reason": reason.get("reason", ""),
                    "evidence": reason.get("evidence", ""),
                    "decision_method": row.decision_method,
                    "codebook_version": row.codebook_version,
                }
            )
    return pd.DataFrame(rows, columns=["post_id", "created_year_kst", "axis", "label", "reason", "evidence", "decision_method", "codebook_version"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    self_check()
    posts, _post_keywords, _sources, _files = load_inputs()
    kiwi = build_kiwi()
    analysis, errors = analyze_all(posts, kiwi)
    base_cols = [
        "post_id", "post_url", "account_id", "account_name", "text", "created_at",
        "comment_count", "repost_count", "view_count", "like_count",
        "source_file", "source_row", "source_year", "collection_keywords_json", "created_year_kst",
    ]
    extra_cols = [
        "analysis_text", "content_tokens_json",
        "mention_labels_json", "mention_status", "mention_evidence_json", "mention_reason",
        "form_labels_json", "form_status", "form_evidence_json", "form_reason",
        "factor_labels_json", "factor_status", "factor_evidence_json", "factor_reason",
        "action_labels_json", "action_status", "action_evidence_json", "action_reason",
        "context_labels_json", "context_status", "context_evidence_json", "context_reason",
        "form_action_links_json", "factor_form_links_json",
        "judgment_status", "judgment_reason", "decision_method", "codebook_version",
        "needs_review", "review_reasons_json", "chiikawa_mentioned",
    ]
    out = posts[base_cols].merge(analysis[["post_id", *extra_cols]], on="post_id", how="inner", validate="1:1")
    out = out[base_cols + extra_cols]
    checks = validate(posts, out, errors)
    if not checks["text_preserved"] or not checks["clock_preserved"] or not checks["view_na_preserved"]:
        raise AssertionError(f"원문 보존 검증 실패: {checks}")
    if checks["completed_posts"] + checks["failed_posts"] != checks["input_posts"]:
        raise AssertionError("완료와 실패의 합이 입력이 아니다.")
    tokens = token_rows(out)
    expressions = expression_rows(out)
    yearly = yearly_rows(out)
    review = build_review(out)
    write_table(TABLES / "x_posts_text_analysis.csv", out)
    out.to_parquet(TABLES / "x_posts_text_analysis.parquet", index=False)
    write_table(TABLES / "token_frequency.csv", tokens)
    write_table(TABLES / "expression_frequency.csv", expressions)
    write_table(TABLES / "yearly_analysis_summary.csv", yearly)
    write_table(TABLES / "review_required.csv", review)
    write_table(TABLES / "processing_errors.csv", errors if len(errors) else pd.DataFrame(columns=["post_id", "stage", "error_type", "error_message"]))
    write_markdown(out, checks, tokens, expressions, yearly)
    summary = {
        "input": checks["input_posts"],
        "completed": checks["completed_posts"],
        "failed": checks["failed_posts"],
        "review_posts": checks["review_posts"],
        "review_rows": int(len(review)),
        "checks": checks,
    }
    (WORK / "final_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("input", "completed", "failed", "review_posts", "review_rows")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
