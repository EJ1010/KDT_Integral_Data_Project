# -*- coding: utf-8 -*-
"""A 영상 제목·댓글 키워드 분석. 원본 CSV는 읽기만 한다.

실행:
  C:\\Users\\user\\anaconda3\\python.exe analyze_A_keywords_v1.py
작업 폴더: 이 파일이 있는 A_키워드 폴더
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from kiwipiepy import Kiwi
from matplotlib import font_manager

RULE_VERSION = "kw-title-comment-v1"
ANIBOX = "UCBTSkFNWmoOkBeZwANcbiIA"
ROOT = Path(__file__).resolve().parent
VID_PATH = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
    r"\youtube_total_cleaning_classified_A.csv"
)
CMT_PATH = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\03. 분석용테이블"
    r"\youtube_total_cleaning_classified_A_comments.csv"
)
FONT = r"C:\Windows\Fonts\malgun.ttf"

# 작품명과 캐릭터명이 한 표기에 겹치면 종류를 '모호'로 둔다.
# 우사기·うさぎ는 다른 뜻이 있어 서로 합치지 않는다.
ENTITIES = [
    ("치이카와", r"치이\s*카와|치카와|ちいかわ|ﾁｰｶﾜ|chiikawa", "작품·캐릭터_모호"),
    ("먼작귀", r"먼작귀|먼가\s*작고\s*귀여운\s*녀석|뭔가\s*작고\s*귀여운", "작품·캐릭터_모호"),
    ("하치와레", r"하치\s*와레|ハチワレ|hachiware", "캐릭터"),
    ("모몽가", r"모몽가|모몬가|モモンガ", "캐릭터"),
    ("쿠리만쥬", r"쿠리\s*만쥬|쿠리\s*만주|くりまんじゅう", "캐릭터"),
    ("아노코", r"아노코|あのこ", "캐릭터"),
    ("파자마파티즈", r"파자마\s*파티즈", "캐릭터"),
    ("데카츠요", r"데카\s*츠요", "캐릭터"),
    ("갑옷씨", r"갑옷\s*씨", "캐릭터"),
    ("우사기", r"우사기", "문맥의존"),
    ("うさぎ", r"うさぎ|ウサギ", "문맥의존"),
    ("라코", r"랏코|라코", "문맥의존"),
]
ENTITY_RES = [(n, re.compile(p, re.I), k) for n, p, k in ENTITIES]
NAME_RES = [p for _, p, _ in ENTITY_RES]

EVALS = [
    ("귀엽다", r"귀엽|귀여워|귀여움|귀여운|졸귀|기여워|귀요미|귀요워"),
    ("웃기다", r"웃기|웃겨|웃김|재밌|재미있"),
    ("예쁘다", r"예쁘|이쁘|예뻐|이뻐"),
    ("슬프다", r"슬프|슬퍼"),
    ("무섭다", r"무섭|무서워|무서움"),
    ("좋다", r"좋(?:다|아|네|음|아요|아요)"),
    ("싫다", r"싫(?:다|어|네|음)"),
    ("중독", r"중독"),
    ("대박", r"대박"),
    ("사랑", r"사랑"),
]
EVAL_RES = [(n, re.compile(p)) for n, p in EVALS]
NEG_RULES = [
    ("부정-귀엽다", r"안\s*귀엽|못\s*귀엽|안\s*귀여|별로.{0,8}귀엽|귀여(?:운|워|움)?\s*(?:건|것|게|거)\s*(?:아닌|아님|아닐)|귀엽지\s*않(?:다|아|어|음)(?!요)"),
    ("부정-웃기다", r"안\s*웃|웃기지\s*않|재미\s*없|노잼|안\s*재밌|안\s*재미"),
    ("부정-예쁘다", r"안\s*예쁘|안\s*이쁘|예쁘지\s*않|이쁘지\s*않"),
    ("부정-좋다", r"안\s*좋|좋지\s*않"),
]
NEG_RES = [(n, re.compile(p)) for n, p in NEG_RULES]
PHRASES = [
    ("갖고싶다", r"갖\s*고\s*싶|사\s*고\s*싶|사고싶|갖고싶"),
    ("보고싶다", r"보\s*고\s*싶"),
    ("목소리가 귀엽다", r"목소리.{0,12}귀엽"),
    ("인형뽑기", r"인형\s*뽑기"),
    ("택배깡", r"택배\s*깡"),
    ("가챠깡", r"가챠\s*깡|랜덤\s*깡|박스\s*깡"),
    ("극장판", r"극장\s*판"),
]
PHRASE_RES = [(n, re.compile(p)) for n, p in PHRASES]

OTHER_IP = re.compile(
    r"산리오|헬로키티|쿠로미|마이멜로디|포챠코|카카오프렌즈|춘식|히로아카|체인소|"
    r"스파이\s*패밀리|커비|포켓몬|피카츄|디즈니|리락쿠마|스누피|나루토|귀멸|원피스|"
    r"주술회전|최애의\s*아이|산리오"
)
CREATOR = re.compile(
    r"편집|자막|성우|더빙|올려\s*주|업로드|영상\s*잘\s*봤|잘\s*봤(?:습|어|다|네)|"
    r"구독|썸네일|브금|음원|커버"
)
SPAM = re.compile(
    r"파트너스|구매\s*링크|수수료를\s*받|텔레그램|카지노|대출\s*상담|"
    r"구독\s*하고\s*좋아요|무료\s*시청|오픈\s*카톡"
)
CLEAR_KO = re.compile(
    r"귀여워|귀엽|졸귀|기여|웃겨|웃기|예뻐|이쁘|대박|헐|짱|싫어|좋아|"
    r"갖고\s*싶|사고\s*싶|보고\s*싶|뭐야|왜|슬프|무섭|사랑|재밌|"
    r"쌉가능|미쳤|레전|실화|인정|공감|좋아죽|존멋|존귀"
)
KO_GRAMMAR = re.compile(
    r"[가-힣]{1,6}(?:습니다|네요|어요|아요|예요|이에요|했어요|했다|인데|거든|잖아|"
    r"까요|지요|하죠|요|다|네|지|음|임|냐|노|게|줘|걸|데|죠|함|용|여|셈|삼|도|고)"
)
HANGUL_RE = re.compile(r"[가-힣]")
KANA_RE = re.compile(r"[ぁ-ゟ゠-ヿ]")
KANJI_RE = re.compile(r"[一-龯]")
LATIN_RE = re.compile(r"[A-Za-z]{2,}")
HASH_RE = re.compile(r"[#＃]([^\s#＃]+)")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
HTML_RE = re.compile(r"&[a-zA-Z]+;|<[^>]+>")
LAUGH_RE = re.compile(r"[ㅋㅎ]{2,}")
SOB_RE = re.compile(r"[ㅠㅜ]{2,}")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
QUESTION_RE = re.compile(r"\?|？|까요|나요|까\b")

STOP = {
    "오늘", "진짜", "정말", "너무", "그냥", "이거", "저거", "그거", "우리", "여러분",
    "사람", "분들", "댓글", "영상", "부분", "장면", "내용", "생각", "느낌", "정도",
    "때문", "하나", "이번", "다음", "처음", "마지막", "지금", "여기", "거기", "계속",
    "완전", "살짝", "존나", "좀", "공식", "공개", "전편", "버전", "쇼츠", "자막",
    "번역", "풀버전", "채널", "구독", "좋아요", "알림", "설정", "이야기", "기분",
    "마음", "이유", "사실", "레알", "애니", "만화", "편", "화", "회", "것", "거",
    "수", "등", "때", "중", "전", "후", "위", "속", "분", "님", "씨", "더", "또",
    "잘", "못", "안", "개", "내", "제", "저", "그", "요", "네", "응", "어", "음",
    "이번", "이번화", "이번편", "다음화", "다음편", "전편", "풀", "버전", "쇼츠",
    "shorts", "short", "영상", "보기", "보다", "하다", "되다", "있다", "없다",
    "같다", "모르다", "알다", "싶다", "주다", "오다", "가다", "들다", "나다",
    "이번", "정도", "조금", "많이", "아주", "매우", "약간", "일단", "사실",
    "그리고", "그래서", "근데", "그런데", "하지만", "그럼", "이제", "아직",
    "항상", "계속", "다시", "바로", "벌써", "이미", "아직", "혹시", "진짜로",
    "여러분", "모두", "같이", "함께", "자신", "자체", "관련", "경우", "사이",
    "이름", "제목", "설명", "링크", "출처", "참고", "오늘", "어제", "내일",
    "아침", "저녁", "시간", "년도", "이번", "이번주", "요즘", "최근", "현재",
    "최고", "최악", "레전드", "실화", "현실", "포인트", "부분", "쪽", "번",
    "번째", "가지", "뭐", "왜", "어떻게", "언제", "어디", "누구", "무엇",
    "이거", "그거", "저거", "이거다", "그거다", "맞다", "틀리다", "모르다",
    "댓글", "답글", "하트", "이모지", "사진", "그림", "이미지", "화면",
    "중간", "앞", "뒤", "왼쪽", "오른쪽", "위쪽", "아래", "안", "밖",
    "사용", "금지", "출처", "음원", "제공", "포함", "제외", "기준", "전체",
    "한국", "일본", "한국어", "일본어", "영어", "더빙", "자막",
    "shorts", "short", "youtube", "video", "official",
}
# 더빙·자막은 소재로 남긴다. 위 집합에서 제거.
STOP.discard("더빙")
STOP.discard("자막")
HASH_STOP = {
    "shorts", "short", "fyp", "viral", "youtube", "like", "subscribe",
    "구독", "좋아요", "추천", "쇼츠", "foryou", "foryoupage",
}
USER_WORDS = [
    ("치이카와", "NNP"), ("먼작귀", "NNP"), ("하치와레", "NNP"), ("모몽가", "NNP"),
    ("모몬가", "NNP"), ("쿠리만쥬", "NNP"), ("쿠리만주", "NNP"), ("아노코", "NNP"),
    ("파자마파티즈", "NNP"), ("인형뽑기", "NNG"), ("택배깡", "NNG"), ("가챠깡", "NNG"),
    ("언박싱", "NNG"), ("혼잣말", "NNG"), ("극장판", "NNG"), ("랜덤깡", "NNG"),
    ("졸귀", "NNG"), ("치카와", "NNP"), ("데카츠요", "NNP"), ("갑옷씨", "NNP"),
    ("브이로그", "NNG"), ("콜라보", "NNG"), ("인어섬", "NNG"), ("연박사", "NNP"),
]
CAUTION = {
    "귀엽다": "포괄적 귀여움. 외형·목소리·성격으로 나누지 않음",
    "부정-귀엽다": "긍정 귀엽다와 분리한 부정·유보",
    "부정-웃기다": "긍정 웃기다와 분리",
    "부정-예쁘다": "긍정 예쁘다와 분리",
    "부정-좋다": "긍정 좋다와 분리",
    "치이카와": "작품명과 캐릭터명이 한 표기에 겹침",
    "먼작귀": "한국어 작품 제목. 치이카와와 합치지 않음",
    "우사기": "다른 의미 가능. うさぎ와 합치지 않음",
    "うさぎ": "다른 의미 가능. 우사기와 합치지 않음",
    "라코": "캐릭터 표기로 보이지만 문맥 없이 단정하지 않음",
    "좋다": "대상이 넓어 인기 이유로 쓰기 어려움",
    "사랑": "대상이 넓음",
    "대박": "감탄. 대상이 지정되지 않는 경우가 많음",
    "중독": "호감인 반복 시청과 습관 표현이 섞임",
}


def clean_text(text: str) -> str:
    t = "" if pd.isna(text) else str(text)
    t = URL_RE.sub(" ", t)
    t = HTML_RE.sub(" ", t)
    t = t.replace("\u200b", " ").replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def split_hash(text: str) -> tuple[str, list[str]]:
    tags = HASH_RE.findall(text)
    body = HASH_RE.sub(" ", text)
    body = re.sub(r"\s+", " ", body).strip()
    return body, tags


def mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    chars = list(text)
    for a, b in spans:
        for i in range(a, min(b, len(chars))):
            chars[i] = " "
    return "".join(chars)


def classify_language(text: str) -> str:
    raw = clean_text(text)
    if not raw:
        return "판단 불가"
    stripped = EMOJI_RE.sub("", raw)
    stripped = re.sub(r"[ㅋㅎㅠㅜ!?~.,\s]+", "", stripped)
    if not stripped:
        return "판단 불가"
    rest = raw
    for p in NAME_RES:
        rest = p.sub(" ", rest)
    rest_compact = re.sub(r"[^가-힣]+", "", rest)
    hangul = len(HANGUL_RE.findall(raw))
    kana = len(KANA_RE.findall(raw))
    kanji = len(KANJI_RE.findall(raw))
    latin = LATIN_RE.findall(raw)
    foreign = kana >= 2 or kanji >= 1 or len(latin) >= 2
    has_clear = bool(CLEAR_KO.search(rest))
    has_grammar = bool(KO_GRAMMAR.search(rest)) and len(rest_compact) >= 2
    koreanish = has_clear or has_grammar
    # 한글 고유명사만 남은 경우
    if not koreanish:
        if kana >= 2 or kanji >= 1 or len(latin) >= 2 or (hangul == 0 and (kana or kanji or latin)):
            return "외국어 중심"
        return "판단 불가"
    if foreign:
        return "혼합_한국어 중심"
    return "한국어 중심"


def title_allows_generic(title: str) -> bool:
    """일반 평가를 치이카와 반응으로 볼 수 있는 제목인지.

    작품명만 있고, 다른 캐릭터·다른 작품·제작 표지가 없을 때만 True.
    영상을 본 것은 아니다.
    """
    if not title:
        return False
    if OTHER_IP.search(title) or CREATOR.search(title) or "콜라보" in title:
        return False
    found = [name for name, cre, _ in ENTITY_RES if cre.search(title)]
    work = [n for n in found if n in ("치이카와", "먼작귀")]
    if not work:
        return False
    extra = [n for n in found if n not in ("치이카와", "먼작귀")]
    return len(extra) == 0


def classify_reaction(text: str, title: str) -> tuple[str, str]:
    raw = clean_text(text)
    if SPAM.search(raw):
        return "광고·스팸", "광고·제휴 문구"
    found = [name for name, cre, _ in ENTITY_RES if cre.search(raw)]
    work = [n for n in found if n not in ("우사기", "うさぎ", "라코")]
    has_other = bool(OTHER_IP.search(raw))
    has_creator = bool(CREATOR.search(raw))
    if work and has_other:
        return "불명확", "댓글에 치이카와 계열과 다른 작품이 함께 있음"
    if work and has_creator:
        return "불명확", "댓글에 캐릭터명과 제작·편집 단서가 함께 있음"
    if work:
        return "치이카와 관련", "댓글에 작품·캐릭터 표기가 있음"
    if ("우사기" in found or "うさぎ" in found or "라코" in found) and title_allows_generic(title):
        return "치이카와 관련", "문맥의존 표기이고 제목은 작품명만 있음. 영상은 확인하지 않음"
    if "우사기" in found or "うさぎ" in found or "라코" in found:
        return "불명확", "우사기·라코 등은 문맥 없이 치이카와로 단정하지 않음"
    if has_other:
        return "다른 캐릭터·상품", "댓글에 다른 작품 표기"
    if has_creator:
        return "제작자·편집", "댓글이 제작·편집·업로드를 가리킴"
    generic = bool(re.search(r"귀엽|귀여|졸귀|웃기|웃겨|예쁘|이쁘|슬프|무섭|중독|대박", raw))
    if generic and title_allows_generic(title):
        return "치이카와 관련", "일반 평가이고 제목은 작품명만 있음. 영상은 확인하지 않음"
    if generic:
        return "불명확", "일반 평가이나 제목에 대상이 여럿이거나 제작 단서가 있음"
    return "불명확", "반응 대상을 특정할 단서가 없음"


def build_kiwi() -> Kiwi:
    kiwi = Kiwi()
    for w, tag in USER_WORDS:
        kiwi.add_user_word(w, tag, 8)
    return kiwi


def extract(body: str, kiwi: Kiwi) -> dict[str, list]:
    """keyword -> [종류, 출현횟수]. 한 텍스트 안의 반복은 횟수에 더한다."""
    found: dict[str, list] = {}

    def add(kw: str, kind: str, n: int = 1) -> None:
        if n <= 0 or not kw:
            return
        if kw in found:
            found[kw][1] += n
            return
        found[kw] = [kind, n]

    spans: list[tuple[int, int]] = []
    # 확인 질문·이중 부정은 긍정으로 둔다. 부정 규칙이 원문에서 다시 집지 않도록 먼저 가린다.
    positive_masks = [
        r"귀엽지\s*않나",
        r"귀여(?:운|워|움)?\s*(?:건|것|게|거)\s*(?:아닌가요|아닌가|아니냐)",
        r"안\s*귀여[가-힣]{0,4}\s+[가-힣]{0,8}\s*(?:이|가)?\s*없",
    ]
    for pat in positive_masks:
        for m in re.finditer(pat, body):
            add("귀엽다", "평가", 1)
            spans.append((m.start(), m.end()))
    # '귀엽지 않아요'는 부정과 확인 질문이 둘 다 가능하다. 어느 쪽으로도 세지 않는다.
    for m in re.finditer(r"귀엽지\s*않아요", body):
        spans.append((m.start(), m.end()))
    masked_neg = mask_spans(body, spans)
    for name, cre in NEG_RES:
        hits = list(cre.finditer(masked_neg))
        if hits:
            add(name, "부정", len(hits))
            spans.extend((m.start(), m.end()) for m in hits)
    masked = mask_spans(body, spans)
    for name, cre, kind in ENTITY_RES:
        hits = list(cre.finditer(masked))
        if hits:
            add(name, kind, len(hits))
            spans.extend((m.start(), m.end()) for m in hits)
    masked = mask_spans(body, spans)
    for name, cre in PHRASE_RES:
        hits = list(cre.finditer(masked))
        if hits:
            add(name, "구절", len(hits))
            spans.extend((m.start(), m.end()) for m in hits)
    masked = mask_spans(body, spans)
    for name, cre in EVAL_RES:
        hits = list(cre.finditer(masked))
        if hits:
            add(name, "평가", len(hits))
            spans.extend((m.start(), m.end()) for m in hits)
    masked = mask_spans(body, spans)
    for tok in kiwi.tokenize(masked):
        if tok.tag not in ("NNG", "NNP"):
            continue
        form = tok.form.strip().lower() if tok.tag == "SL" else tok.form.strip()
        if len(form) < 2 or form in STOP or form.isdigit():
            continue
        if form in {n for n, _, _ in ENTITIES}:
            continue
        if form == "연박사":
            add(form, "채널호칭", 1)
            continue
        if re.fullmatch(r"[ㅋㅎㅠㅜ]+", form):
            continue
        add(form, "소재", 1)
    return found


def norm_tag(tag: str) -> tuple[str, str]:
    t = tag.strip().lower()
    for name, cre, kind in ENTITY_RES:
        if cre.fullmatch(tag) or cre.fullmatch(t):
            return name, kind
    if t in HASH_STOP or tag in HASH_STOP:
        return "", ""
    return tag, "해시태그"


def self_check(kiwi: Kiwi) -> None:
    cases = [
        ("안 귀여워", "한국어 중심", {"부정-귀엽다"}, {"귀엽다"}),
        ("귀여워", "한국어 중심", {"귀엽다"}, {"부정-귀엽다"}),
        ("귀여운 건 아닌데", "한국어 중심", {"부정-귀엽다"}, {"귀엽다"}),
        ("귀엽지 않나요", "한국어 중심", {"귀엽다"}, {"부정-귀엽다"}),
        ("귀엽지 않아요", "한국어 중심", set(), {"귀엽다", "부정-귀엽다"}),
        ("귀여운거 아닌가요", "한국어 중심", {"귀엽다"}, {"부정-귀엽다"}),
        ("안 귀여운 인형이 없고", "한국어 중심", {"귀엽다"}, {"부정-귀엽다"}),
        ("ㅋㅋㅋ", "판단 불가", set(), {"귀엽다"}),
        ("하치와레", "판단 불가", set(), {"귀엽다"}),
        ("후루베유라유라", "판단 불가", set(), set()),
        ("치이카와 너무 귀여워", "한국어 중심", {"치이카와", "귀엽다"}, set()),
        ("so cute 진짜 귀엽다", "혼합_한국어 중심", {"귀엽다"}, set()),
    ]
    for text, lang, must, ban in cases:
        got_lang = classify_language(text)
        kws = set(extract(clean_text(text), kiwi))
        if got_lang != lang or not must.issubset(kws) or kws & ban:
            raise SystemExit(f"규칙 점검 실패: {text} -> {got_lang} {kws}")
    rel, why = classify_reaction("귀여워", "[전편공개]먼작귀 10화_산책")
    if rel != "치이카와 관련" or "영상은 확인하지 않음" not in why:
        raise SystemExit(f"제목문맥 판정 실패: {rel} {why}")
    rel2, _ = classify_reaction("귀여워", "치이카와 하치와레 우사기 그리기")
    if rel2 != "불명확":
        raise SystemExit(f"복수 대상 판정 실패: {rel2}")
    rel3, _ = classify_reaction("편집 진짜 잘하시네요", "[전편공개]먼작귀 10화")
    if rel3 != "제작자·편집":
        raise SystemExit(f"제작 판정 실패: {rel3}")
    rel4, _ = classify_reaction("구매는 영상하단 파트너스 수수료를 받습니다", "먼작귀")
    if rel4 != "광고·스팸":
        raise SystemExit(f"광고 판정 실패: {rel4}")


def write_dicts() -> None:
    pd.DataFrame(
        [
            ["치이카와", "치이카와|치카와|ちいかわ|chiikawa", "작품·캐릭터_모호", "작품명과 주인공 표기가 겹쳐 합치되 모호성을 남김"],
            ["먼작귀", "먼작귀|먼가 작고 귀여운 녀석|뭔가 작고 귀여운", "작품·캐릭터_모호", "한국어 작품 제목. 치이카와와는 합치지 않음"],
            ["모몽가", "모몽가|모몬가", "캐릭터", "모몬가는 같은 이름의 다른 철자로 연결. 원표기는 댓글 파일에 남음"],
            ["하치와레", "하치와레|ハチワレ|hachiware", "캐릭터", ""],
            ["쿠리만쥬", "쿠리만쥬|쿠리만주|くりまんじゅう", "캐릭터", ""],
            ["우사기", "우사기", "문맥의존", "うさぎ와 합치지 않음"],
            ["うさぎ", "うさぎ|ウサギ", "문맥의존", "우사기와 합치지 않음"],
            ["귀엽다", "귀엽|귀여워|귀여움|졸귀|기여워|귀요미", "평가", "원표현은 문맥 표에 보존. 표준어는 귀엽다"],
        ],
        columns=["표준", "연결_표기", "종류", "메모"],
    ).to_csv(ROOT / "dict_표기통일.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(USER_WORDS, columns=["단어", "품사"]).to_csv(
        ROOT / "dict_사용자단어.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(sorted(STOP), columns=["불용어"]).to_csv(
        ROOT / "dict_불용어.csv", index=False, encoding="utf-8-sig"
    )
    rows = [{"구분": "부정", "표준": n, "패턴": p, "처리": "긍정 평가로 집계하지 않음"} for n, p in NEG_RULES]
    rows += [{"구분": "구절", "표준": n, "패턴": p, "처리": "이 패턴만 구절로 인정. 인접 형태소 조합은 구절이 아님"} for n, p in PHRASES]
    pd.DataFrame(rows).to_csv(ROOT / "dict_구절_부정규칙.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [{"rule_version": RULE_VERSION, "형태소": "kiwipiepy", "설명사용": "반응 판정에 사용하지 않음. 제목에 합치지 않음"}]
    ).to_csv(ROOT / "00_규칙버전.csv", index=False, encoding="utf-8-sig")


def rank_frame(records: list[dict], denom_video: int, denom_channel: int, extra: dict) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["출현영상비율"] = df["출현영상수"] / denom_video
    df["출현채널비율"] = df["출현채널수"] / denom_channel if denom_channel else pd.NA
    for k, v in extra.items():
        df[k] = v
    df["분모_영상"] = denom_video
    df["분모_채널"] = denom_channel
    df["주의"] = df["키워드"].map(lambda x: CAUTION.get(x, ""))
    return df.sort_values(["출현영상수", "총출현횟수", "키워드"], ascending=[False, False, True])


def comment_keyword_table(frame: pd.DataFrame, label: str, scope: str) -> pd.DataFrame:
    """frame은 이미 집단·범위로 걸러진 댓글. 키워드 열은 set이 아니라 리스트의 고유 키워드."""
    n_c = len(frame)
    n_v = frame["post_id"].nunique()
    n_ch = frame.loc[frame["account_id"].notna(), "account_id"].nunique()
    rows = []
    if n_c == 0:
        return pd.DataFrame()
    tmp = frame[["comment_id", "post_id", "account_id", "kw_list", "kw_count", "comment_description"]].copy()
    exp = tmp.explode("kw_list")
    exp = exp[exp["kw_list"].notna()]
    if exp.empty:
        return pd.DataFrame()
    exp["종류"] = exp["kw_list"].map(lambda x: x[1])
    exp["키워드"] = exp["kw_list"].map(lambda x: x[0])
    occ_map: dict[str, int] = defaultdict(int)
    for d in frame["kw_count"]:
        for k, n in d.items():
            occ_map[k] += int(n)
    for (kw, kind), g in exp.groupby(["키워드", "종류"], sort=False):
        # 댓글당 한 번. explode 전에 kw_list를 고유화해 두었다.
        c_n = g["comment_id"].nunique()
        v_n = g["post_id"].nunique()
        ch_n = g.loc[g["account_id"].notna(), "account_id"].nunique()
        occ = int(occ_map.get(kw, 0))
        ex = g.sort_values("comment_id").iloc[0]
        rows.append(
            {
                "집단": label,
                "범위": scope,
                "키워드": kw,
                "종류": kind,
                "총출현횟수": occ,
                "언급댓글수": c_n,
                "언급댓글비율": c_n / n_c,
                "출현영상수": v_n,
                "출현영상비율": v_n / n_v if n_v else pd.NA,
                "출현채널수": ch_n,
                "출현채널비율": ch_n / n_ch if n_ch else pd.NA,
                "분모_댓글": n_c,
                "분모_영상": n_v,
                "분모_채널": n_ch,
                "대표문맥": str(ex["comment_description"]).replace("\n", " ")[:80],
                "대표_comment_id": ex["comment_id"],
                "대표_post_id": ex["post_id"],
                "주의": CAUTION.get(kw, ""),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["언급댓글수", "총출현횟수"], ascending=False)


def three_ways(frame: pd.DataFrame, keywords: list[str], scope: str) -> pd.DataFrame:
    """영상 동일 비중은 유효 댓글이 있는 영상만. 없는 영상을 0으로 넣지 않는다."""
    if frame.empty:
        return pd.DataFrame()
    n_c = len(frame)
    per_video = frame.groupby("post_id").size()
    # 댓글에 키워드가 있는지
    has = {kw: [] for kw in keywords}
    for pid, kws, aid in zip(frame["post_id"], frame["kw_set"], frame["account_id"]):
        for kw in keywords:
            if kw in kws:
                has[kw].append((pid, aid))
    # video rate
    rows = []
    vid_meta = frame.groupby("post_id").agg(account_id=("account_id", "first"), n=("comment_id", "size"))
    for kw in keywords:
        mention_c = int(frame["kw_set"].map(lambda s, k=kw: k in s).sum())
        hits = pd.DataFrame(has[kw], columns=["post_id", "account_id"])
        if hits.empty:
            vrate = pd.Series(0.0, index=per_video.index)
        else:
            cnt = hits.groupby("post_id").size()
            vrate = cnt.reindex(per_video.index).fillna(0) / per_video
        video_mean = float(vrate.mean()) if len(vrate) else pd.NA
        # channel: 영상 비율을 채널 안에서 평균, 그다음 채널 평균. 채널 ID 없는 영상은 채널 평균에서 제외.
        tmp = vrate.rename("rate").to_frame().join(vid_meta[["account_id"]])
        tmp = tmp[tmp["account_id"].notna()]
        if tmp.empty:
            ch_mean = pd.NA
            n_ch = 0
        else:
            within = tmp.groupby("account_id")["rate"].mean()
            ch_mean = float(within.mean())
            n_ch = int(within.size)
        rows.append(
            {
                "범위": scope,
                "키워드": kw,
                "댓글기준_비율": mention_c / n_c if n_c else pd.NA,
                "댓글기준_분자": mention_c,
                "댓글기준_분모": n_c,
                "영상동일비중": video_mean,
                "영상수": int(per_video.size),
                "채널동일비중": ch_mean,
                "채널수": n_ch,
                "영상당_유효댓글_중앙값": float(per_video.median()),
            }
        )
    return pd.DataFrame(rows)


def barh(path: Path, labels, values, title: str, xlabel: str, color: str = "#3d6f8a") -> None:
    font_manager.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(list(reversed(labels)), list(reversed(values)), color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    write_dicts()
    kiwi = build_kiwi()
    self_check(kiwi)

    videos = pd.read_csv(VID_PATH, encoding="utf-8-sig")
    comments = pd.read_csv(CMT_PATH, encoding="utf-8-sig")
    src_v_rows, src_c_rows = len(videos), len(comments)
    if videos["post_id"].duplicated().any():
        raise SystemExit("영상 post_id 중복")
    if comments["comment_id"].duplicated().any() or comments["comment_id"].isna().any():
        raise SystemExit("댓글 ID 중복 또는 결측")
    outside = ~comments["post_id"].isin(set(videos["post_id"]))
    if outside.any():
        raise SystemExit(f"A 밖 영상 ID {int(outside.sum())}")

    vcols = ["post_id", "account_id", "account_name", "full_title", "post_title", "created_at"]
    base = videos[vcols].copy()
    # 댓글 쪽 영상 정보는 분석 테이블 값이 아니라 A 영상 원본으로 다시 붙인다.
    c = comments.drop(columns=[col for col in ("account_id", "account_name", "full_title", "post_title") if col in comments.columns])
    before = len(c)
    c = c.merge(base, on="post_id", how="left", validate="many_to_one")
    if len(c) != before:
        raise SystemExit("댓글 연결 중 행이 늘었다")

    title_src = base["full_title"].where(base["full_title"].notna(), base["post_title"])
    base["title_raw"] = title_src.fillna("")
    analyzable = base["title_raw"].str.strip() != ""
    n_title = int(analyzable.sum())
    n_ch_title = int(base.loc[analyzable & base["account_id"].notna(), "account_id"].nunique())

    # 제목 추출
    title_rows = []
    hash_rows = []
    title_kw = {}
    for rec in base.loc[analyzable, ["post_id", "account_id", "account_name", "title_raw"]].itertuples(index=False):
        cleaned = clean_text(rec.title_raw)
        body, tags = split_hash(cleaned)
        found = extract(body, kiwi) if body else {}
        title_kw[rec.post_id] = found
        for kw, (kind, n) in found.items():
            title_rows.append((kw, kind, n, rec.post_id, rec.account_id, rec.account_name, rec.title_raw))
        seen_tag = set()
        for tag in tags:
            name, _kind = norm_tag(tag)
            if not name or name in seen_tag:
                continue
            seen_tag.add(name)
            hash_rows.append((name, "해시태그", rec.post_id, rec.account_id, rec.title_raw))

    def pack_title(rows, kind_filter=None):
        df = pd.DataFrame(rows, columns=["키워드", "종류", "횟수", "post_id", "account_id", "account_name", "title"])
        if kind_filter:
            df = df[df["종류"].isin(kind_filter)]
        recs = []
        for (kw, kind), g in df.groupby(["키워드", "종류"], sort=False):
            ex = g.sort_values("post_id").iloc[0]
            recs.append(
                {
                    "키워드": kw,
                    "종류": kind,
                    "총출현횟수": int(g["횟수"].sum()),
                    "출현영상수": int(g["post_id"].nunique()),
                    "출현채널수": int(g.loc[g["account_id"].notna(), "account_id"].nunique()),
                    "대표제목": str(ex["title"]).replace("\n", " ")[:80],
                    "대표_post_id": ex["post_id"],
                }
            )
        return rank_frame(recs, n_title, n_ch_title, {"단위": "제목본문"})

    tdf = pd.DataFrame(title_rows, columns=["키워드", "종류", "횟수", "post_id", "account_id", "account_name", "title"])
    title_main = pack_title(title_rows, {"작품·캐릭터_모호", "캐릭터", "문맥의존", "소재", "평가", "부정"})
    title_phrase = pack_title(title_rows, {"구절"})
    hdf = pd.DataFrame(hash_rows, columns=["키워드", "종류", "post_id", "account_id", "title"])
    hrecs = []
    for (kw, kind), g in hdf.groupby(["키워드", "종류"], sort=False):
        ex = g.sort_values("post_id").iloc[0]
        hrecs.append(
            {
                "키워드": kw,
                "종류": kind,
                "총출현횟수": int(len(g)),
                "출현영상수": int(g["post_id"].nunique()),
                "출현채널수": int(g.loc[g["account_id"].notna(), "account_id"].nunique()),
                "대표제목": str(ex["title"]).replace("\n", " ")[:80],
                "대표_post_id": ex["post_id"],
            }
        )
    hash_rank = rank_frame(hrecs, n_title, n_ch_title, {"단위": "해시태그"})
    n_with_hash = int(hdf["post_id"].nunique()) if len(hdf) else 0
    if len(hash_rank):
        hash_rank["분모_해시태그있는영상"] = n_with_hash
        hash_rank["출현영상비율_해시태그있는영상"] = hash_rank["출현영상수"] / n_with_hash if n_with_hash else pd.NA

    # 댓글 판정
    c["text_original"] = c["comment_description"].fillna("")
    c["text_analysis"] = c["text_original"].map(clean_text)
    c["language_class"] = c["text_analysis"].map(classify_language)
    reac = [classify_reaction(t, ttl) for t, ttl in zip(c["text_analysis"], c["full_title"].fillna(""))]
    c["reaction_target"] = [a for a, _ in reac]
    c["reaction_basis"] = [b for _, b in reac]
    c["exclude_reason"] = ""
    spam = c["reaction_target"].eq("광고·스팸")
    c.loc[spam, "exclude_reason"] = "광고·스팸"
    empty = c["text_analysis"].str.strip().eq("")
    c.loc[empty, "exclude_reason"] = "빈 댓글"
    ko = c["language_class"].isin(["한국어 중심", "혼합_한국어 중심"])
    c["include_explore"] = ko & ~spam & ~empty
    c["include_major"] = c["include_explore"] & c["reaction_target"].eq("치이카와 관련")
    c["rule_version"] = RULE_VERSION
    c["반어_검토"] = c["text_analysis"].map(
        lambda t: bool(re.search(r"귀엽지\s*않아요", t) or (re.search(r"귀엽", t) and re.search(r"싫|역겹|징그|아니냐", t)))
    )

    # 키워드 추출은 탐색 집단만. 원문은 판정 파일에 남긴다.
    kw_list = []
    kw_count = []
    kw_set = []
    for flag, text in zip(c["include_explore"], c["text_analysis"]):
        if not flag:
            kw_list.append([])
            kw_count.append({})
            kw_set.append(set())
            continue
        body, _tags = split_hash(text)
        found = extract(body, kiwi) if body else {}
        kw_list.append([(k, v[0]) for k, v in found.items()])
        kw_count.append({k: v[1] for k, v in found.items()})
        kw_set.append(set(found))
    c["kw_list"] = kw_list
    c["kw_count"] = kw_count
    c["kw_set"] = kw_set

    explore = c[c["include_explore"]].copy()
    major = c[c["include_major"]].copy()
    explore_ex = explore[explore["account_id"] != ANIBOX]
    major_ex = major[major["account_id"] != ANIBOX]

    e_all = comment_keyword_table(explore, "탐색", "전체")
    e_ex = comment_keyword_table(explore_ex, "탐색", "AniBox제외")
    m_all = comment_keyword_table(major, "주요해석", "전체")
    m_ex = comment_keyword_table(major_ex, "주요해석", "AniBox제외")
    comment_rank = pd.concat([e_all, e_ex, m_all, m_ex], ignore_index=True)
    phrase_rank = comment_rank[comment_rank["종류"].eq("구절")].copy() if len(comment_rank) else comment_rank
    word_rank = comment_rank[~comment_rank["종류"].eq("구절")].copy() if len(comment_rank) else comment_rank

    # 최소 언급으로 집계 비교 키워드 선정
    focus = m_all[(m_all["종류"].isin(["평가", "소재", "구절", "부정"])) & (m_all["언급댓글수"] >= 30)]
    focus_kw = focus["키워드"].head(25).tolist()
    ways_all = three_ways(major, focus_kw, "전체")
    ways_ex = three_ways(major_ex, focus_kw, "AniBox제외")
    ways = pd.concat([ways_all, ways_ex], ignore_index=True)
    if len(ways):
        for scope, g in ways.groupby("범위"):
            ways.loc[g.index, "순위_댓글"] = g["댓글기준_비율"].rank(ascending=False, method="min")
            ways.loc[g.index, "순위_영상"] = g["영상동일비중"].rank(ascending=False, method="min")
            ways.loc[g.index, "순위_채널"] = g["채널동일비중"].rank(ascending=False, method="min")

    # 출현 범위: 주요해석 전체의 상위 키워드
    scope_tbl = m_all.head(40)[
        ["키워드", "종류", "언급댓글수", "언급댓글비율", "출현영상수", "출현영상비율", "출현채널수", "출현채널비율", "분모_댓글", "분모_영상", "분모_채널"]
    ].copy()
    scope_tbl.insert(0, "집단", "주요해석")
    scope_tbl.insert(1, "범위", "전체")

    # 제목-댓글 연결
    title_focus = title_main[title_main["종류"].isin(["캐릭터", "작품·캐릭터_모호", "소재", "구절"])]
    title_focus = title_focus[title_focus["출현영상수"] >= 40].head(12)
    comment_focus = m_all[m_all["종류"].isin(["평가", "소재", "구절", "부정"])].head(12)
    link_rows = []
    major_videos = set(major["post_id"])
    # 제목 키워드가 있는 영상
    title_sets = defaultdict(set)
    for pid, found in title_kw.items():
        for kw in found:
            title_sets[kw].add(pid)
    per_v = major.groupby("post_id").size()
    vid_account = major.groupby("post_id")["account_id"].first()
    for tkw in title_focus["키워드"]:
        has_t = title_sets.get(tkw, set()) & major_videos
        no_t = major_videos - has_t
        for side, ids in (("제목키워드_있음", has_t), ("제목키워드_없음", no_t)):
            sub = major[major["post_id"].isin(ids)]
            sub_ex = sub[sub["account_id"] != ANIBOX]
            for ckw in comment_focus["키워드"]:
                for scope, part in (("전체", sub), ("AniBox제외", sub_ex)):
                    if part.empty:
                        continue
                    pv = part.groupby("post_id").size()
                    hit = part["kw_set"].map(lambda s, k=ckw: k in s)
                    ment = part.loc[hit].groupby("post_id").size()
                    rate = ment.reindex(pv.index).fillna(0) / pv
                    link_rows.append(
                        {
                            "제목키워드": tkw,
                            "댓글키워드": ckw,
                            "비교": side,
                            "범위": scope,
                            "영상수": int(pv.size),
                            "채널수": int(part.loc[part["account_id"].notna(), "account_id"].nunique()),
                            "댓글수": int(len(part)),
                            "영상동일비중": float(rate.mean()) if len(rate) else pd.NA,
                            "댓글기준_비율": float(hit.mean()) if len(part) else pd.NA,
                            "동시출현영상수": int(ment.size) if side == "제목키워드_있음" else pd.NA,
                        }
                    )
    link = pd.DataFrame(link_rows)

    # 문맥 표본
    ctx_rows = []
    watch = list(dict.fromkeys(focus_kw[:12] + ["부정-귀엽다", "목소리가 귀엽다", "갖고싶다", "하치와레", "모몽가"]))
    for kw in watch:
        sub = major[major["kw_set"].map(lambda s, k=kw: k in s)]
        if sub.empty:
            continue
        picked = []
        seen_ch = set()
        # 비애니박스를 먼저
        ordered = pd.concat([sub[sub["account_id"] != ANIBOX], sub[sub["account_id"] == ANIBOX]])
        for rec in ordered.itertuples(index=False):
            aid = rec.account_id
            if aid in seen_ch:
                continue
            seen_ch.add(aid)
            picked.append(rec)
            if len(picked) >= 6:
                break
        for rec in picked:
            text = str(rec.text_original).replace("\n", " ")
            polarity = "부정" if kw.startswith("부정-") else ("질문" if QUESTION_RE.search(text) else "문맥 확인 필요")
            ctx_rows.append(
                {
                    "키워드": kw,
                    "comment_id": rec.comment_id,
                    "post_id": rec.post_id,
                    "account_id": rec.account_id,
                    "account_name": rec.account_name,
                    "제목": str(rec.full_title).replace("\n", " ")[:70],
                    "댓글": text[:160],
                    "reaction_basis": rec.reaction_basis,
                    "자동표시": polarity,
                    "문맥메모": "",
                }
            )
    ctx = pd.DataFrame(ctx_rows)

    # 보조 반응
    aux = pd.DataFrame(
        [
            {
                "지표": "ㅋㅋ·ㅎㅎ",
                "탐색_댓글수": int(explore["text_analysis"].map(lambda t: bool(LAUGH_RE.search(t))).sum()),
                "주요해석_댓글수": int(major["text_analysis"].map(lambda t: bool(LAUGH_RE.search(t))).sum()),
            },
            {
                "지표": "ㅠㅠ·ㅜㅜ",
                "탐색_댓글수": int(explore["text_analysis"].map(lambda t: bool(SOB_RE.search(t))).sum()),
                "주요해석_댓글수": int(major["text_analysis"].map(lambda t: bool(SOB_RE.search(t))).sum()),
            },
            {
                "지표": "이모지",
                "탐색_댓글수": int(explore["text_analysis"].map(lambda t: bool(EMOJI_RE.search(t))).sum()),
                "주요해석_댓글수": int(major["text_analysis"].map(lambda t: bool(EMOJI_RE.search(t))).sum()),
            },
        ]
    )
    aux["탐색_분모"] = len(explore)
    aux["주요해석_분모"] = len(major)
    aux["탐색_비율"] = aux["탐색_댓글수"] / len(explore) if len(explore) else pd.NA
    aux["주요해석_비율"] = aux["주요해석_댓글수"] / len(major) if len(major) else pd.NA

    # 유효 댓글 분포
    dist_rows = []
    for name, part in (("주요해석_전체", major), ("주요해석_AniBox제외", major_ex)):
        vc = part.groupby("post_id").size()
        ch = part.dropna(subset=["account_id"]).groupby("account_id")["post_id"].nunique()
        dist_rows.append(
            {
                "집단": name,
                "댓글수": int(len(part)),
                "영상수": int(vc.size),
                "채널수": int(part.loc[part["account_id"].notna(), "account_id"].nunique()),
                "영상당_댓글_중앙값": float(vc.median()) if len(vc) else pd.NA,
                "댓글1건_영상비율": float((vc == 1).mean()) if len(vc) else pd.NA,
                "댓글5건미만_영상비율": float((vc < 5).mean()) if len(vc) else pd.NA,
                "영상1개_채널비율": float((ch == 1).mean()) if len(ch) else pd.NA,
                "채널ID없음_댓글": int(part["account_id"].isna().sum()),
            }
        )
    dist = pd.DataFrame(dist_rows)

    basis_parts = {
        "주요해석_전체": major,
        "댓글에_작품표기": major[major["reaction_basis"].str.startswith("댓글에")],
        "제목문맥_일반평가": major[major["reaction_basis"].str.startswith("일반 평가")],
        "제목문맥_문맥의존표기": major[major["reaction_basis"].str.startswith("문맥의존")],
    }
    basis_rows = []
    for label, part in basis_parts.items():
        for kw in ["귀엽다", "부정-귀엽다", "웃기다", "좋다", "예쁘다", "무섭다", "슬프다", "갖고싶다", "목소리가 귀엽다"]:
            n = int(part["kw_set"].map(lambda s, k=kw: k in s).sum()) if len(part) else 0
            basis_rows.append(
                {
                    "집단": label,
                    "키워드": kw,
                    "언급댓글수": n,
                    "분모_댓글": int(len(part)),
                    "언급댓글비율": (n / len(part)) if len(part) else pd.NA,
                    "출현영상수": int(part.loc[part["kw_set"].map(lambda s, k=kw: k in s), "post_id"].nunique()) if len(part) else 0,
                    "출현채널수": int(part.loc[part["kw_set"].map(lambda s, k=kw: k in s) & part["account_id"].notna(), "account_id"].nunique()) if len(part) else 0,
                }
            )
    basis_tbl = pd.DataFrame(basis_rows)

    # 저장
    judge_cols = [
        "comment_id", "post_id", "account_id", "account_name", "language_class",
        "reaction_target", "reaction_basis", "include_explore", "include_major",
        "exclude_reason", "반어_검토", "text_original", "text_analysis", "rule_version",
    ]
    c[judge_cols].to_csv(ROOT / "01_댓글판정.csv", index=False, encoding="utf-8-sig")
    title_main.to_csv(ROOT / "02_제목_키워드.csv", index=False, encoding="utf-8-sig")
    title_phrase.to_csv(ROOT / "02_제목_구절.csv", index=False, encoding="utf-8-sig")
    hash_rank.to_csv(ROOT / "02_제목_해시태그.csv", index=False, encoding="utf-8-sig")
    word_rank.to_csv(ROOT / "03_댓글_키워드.csv", index=False, encoding="utf-8-sig")
    phrase_rank.to_csv(ROOT / "03_댓글_구절.csv", index=False, encoding="utf-8-sig")
    scope_tbl.to_csv(ROOT / "04_출현범위.csv", index=False, encoding="utf-8-sig")
    ways.to_csv(ROOT / "05_집계방식비교.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(ROOT / "05_유효댓글분포.csv", index=False, encoding="utf-8-sig")
    link.to_csv(ROOT / "06_제목댓글연결.csv", index=False, encoding="utf-8-sig")
    ctx.to_csv(ROOT / "07_문맥검수표.csv", index=False, encoding="utf-8-sig")
    aux.to_csv(ROOT / "08_보조반응.csv", index=False, encoding="utf-8-sig")
    basis_tbl.to_csv(ROOT / "03_판정근거별_키워드.csv", index=False, encoding="utf-8-sig")

    # 입력 검증
    both_cute = int(c["kw_set"].map(lambda s: "귀엽다" in s and "부정-귀엽다" in s).sum())
    anibox_c = int((c["account_id"] == ANIBOX).sum())
    pd.DataFrame(
        [
            ["영상행", src_v_rows, 6462],
            ["영상_고유ID", int(videos["post_id"].nunique()), 6462],
            ["제목_분석가능", n_title, src_v_rows],
            ["제목_채널분모", n_ch_title, ""],
            ["댓글행", src_c_rows, 90921],
            ["댓글_고유ID", int(c["comment_id"].nunique()), src_c_rows],
            ["댓글_연결영상", int(c["post_id"].nunique()), ""],
            ["조인후_행", len(c), src_c_rows],
            ["AniBox댓글", anibox_c, round(anibox_c / len(c), 4)],
            ["영상당댓글_최대", int(c.groupby("post_id").size().max()), 100],
            ["탐색", int(c["include_explore"].sum()), ""],
            ["주요해석", int(c["include_major"].sum()), ""],
            ["불명확", int(c["reaction_target"].eq("불명확").sum()), ""],
            ["광고스팸", int(spam.sum()), ""],
            ["반어검토", int(c["반어_검토"].sum()), ""],
            ["귀엽다_부정_동시", both_cute, "한 댓글에 긍정과 부정이 따로 있으면 남음"],
        ],
        columns=["항목", "값", "참고"],
    ).to_csv(ROOT / "00_입력검증.csv", index=False, encoding="utf-8-sig")

    # 그래프
    def top_labels(df, kind, n=12):
        part = df[df["종류"].isin(kind)].head(n)
        return part["키워드"].tolist(), (part["출현영상비율"] * 100).tolist()

    labs, vals = top_labels(title_main, ["작품·캐릭터_모호", "캐릭터"])
    if labs:
        barh(ROOT / "fig_제목_캐릭터.png", labs, vals, "제목 본문의 작품·캐릭터 표기", "분석 가능 제목 중 비율(%)")
    labs, vals = top_labels(title_main, ["소재", "평가", "구절"])
    if labs:
        barh(ROOT / "fig_제목_소재평가.png", labs, vals, "제목 본문의 소재·평가", "분석 가능 제목 중 비율(%)", "#b36b3a")
    mplot = m_all[m_all["종류"].isin(["평가", "소재", "구절", "부정"])].head(12)
    if len(mplot):
        barh(
            ROOT / "fig_댓글_키워드.png",
            mplot["키워드"].tolist(),
            (mplot["언급댓글비율"] * 100).tolist(),
            "주요 해석 집단 댓글 표현",
            "집단 댓글 중 언급 비율(%)",
            "#2f6f4e",
        )
        barh(
            ROOT / "fig_출현범위.png",
            mplot["키워드"].tolist(),
            (mplot["출현영상비율"] * 100).tolist(),
            "주요 해석 집단의 영상 출현 범위",
            "유효 댓글이 있는 영상 중 비율(%)",
            "#5c4d7a",
        )
    if len(ways_all):
        show = ways_all.head(8)
        font_manager.fontManager.addfont(FONT)
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(10, 5.8))
        import numpy as np

        y = np.arange(len(show))
        h = 0.25
        ax.barh(y - h, show["댓글기준_비율"] * 100, height=h, label="댓글 기준", color="#2f6f4e")
        ax.barh(y, show["영상동일비중"] * 100, height=h, label="영상 동일 비중", color="#3d6f8a")
        ax.barh(y + h, show["채널동일비중"] * 100, height=h, label="채널 동일 비중", color="#b36b3a")
        ax.set_yticks(y)
        ax.set_yticklabels(show["키워드"])
        ax.invert_yaxis()
        ax.set_xlabel("비율(%)")
        ax.set_title("주요 해석 집단, 집계 방식 비교")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ROOT / "fig_집계방식.png", dpi=140)
        plt.close(fig)

        both = ways_all.merge(ways_ex, on="키워드", suffixes=("_전체", "_제외"))
        both = both.head(8)
        fig, ax = plt.subplots(figsize=(10, 5.8))
        y = np.arange(len(both))
        ax.barh(y - 0.2, both["댓글기준_비율_전체"] * 100, height=0.4, label="전체", color="#2f6f4e")
        ax.barh(y + 0.2, both["댓글기준_비율_제외"] * 100, height=0.4, label="AniBox 제외", color="#8a3d3d")
        ax.set_yticks(y)
        ax.set_yticklabels(both["키워드"])
        ax.invert_yaxis()
        ax.set_xlabel("댓글 기준 비율(%)")
        ax.set_title("주요 해석 집단, AniBox 제외 민감도")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ROOT / "fig_애니박스제외.png", dpi=140)
        plt.close(fig)

    # 숫자 모음
    lang_counts = c["language_class"].value_counts().to_dict()
    reac_counts = c["reaction_target"].value_counts().to_dict()
    stats = {
        "n_title": n_title,
        "n_ch_title": n_ch_title,
        "n_c": len(c),
        "n_cv": int(c["post_id"].nunique()),
        "anibox_c": anibox_c,
        "anibox_share": anibox_c / len(c),
        "max_c": int(c.groupby("post_id").size().max()),
        "explore": int(len(explore)),
        "major": int(len(major)),
        "explore_v": int(explore["post_id"].nunique()),
        "major_v": int(major["post_id"].nunique()),
        "explore_ch": int(explore.loc[explore["account_id"].notna(), "account_id"].nunique()),
        "major_ch": int(major.loc[major["account_id"].notna(), "account_id"].nunique()),
        "major_ex": int(len(major_ex)),
        "major_ex_v": int(major_ex["post_id"].nunique()) if len(major_ex) else 0,
        "spam": int(spam.sum()),
        "irony": int(c["반어_검토"].sum()),
        "dup_body": int(c["text_original"].duplicated(keep=False).sum()),
        "unlinked_titles": int(n_title - c["post_id"].nunique()),
        "lang": lang_counts,
        "reac": reac_counts,
        "n_hash": n_with_hash,
    }
    write_report(stats, title_main, title_phrase, hash_rank, m_all, e_all, ways, dist, link, aux, basis_tbl)
    print("DONE", stats["explore"], stats["major"], "spam", stats["spam"])


def pct(x) -> str:
    if pd.isna(x):
        return "계산 불가"
    return f"{x * 100:.1f}%"


def num(x) -> str:
    return f"{int(x):,}"


def md_table(df: pd.DataFrame, cols: list[str], n=8) -> str:
    if df is None or df.empty:
        return "(해당 행 없음)"
    part = df.head(n)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    rate_cols = ("비율", "비중", "차이")
    for _, rec in part.iterrows():
        cells = []
        for col in cols:
            val = rec[col]
            if isinstance(val, float) and any(s in col for s in rate_cols):
                cells.append(f"{val * 100:.1f}%")
            elif isinstance(val, float) and float(val).is_integer():
                cells.append(str(int(val)))
            elif isinstance(val, float):
                cells.append(f"{val:.2f}")
            else:
                cells.append(str(val).replace("|", "/").replace("\n", " "))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(stats, title_main, title_phrase, hash_rank, major_rank, explore_rank, ways, dist, link, aux, basis_tbl) -> None:
    def kind(df, kinds, n=8):
        if df is None or df.empty:
            return df
        return df[df["종류"].isin(kinds)].head(n)

    t_char = kind(title_main, ["작품·캐릭터_모호", "캐릭터", "문맥의존"])
    t_topic = kind(title_main, ["소재", "평가", "부정", "구절"])
    m_eval = kind(major_rank, ["평가", "부정", "구절", "소재"])
    lines = []
    a = lines.append
    a("# A 영상 제목·댓글 키워드")
    a("")
    a(f"규칙 버전 `{RULE_VERSION}`. 형태소 분석은 kiwipiepy에 사용자 단어를 더해 사용했다. 이 문서는 키워드가 어디에 얼마나 퍼져 있는지를 정리한다. 빈도만으로 인기 이유를 확정하지 않는다.")
    a("")
    a("## 1. 분석 범위")
    a("")
    a("**핵심 발견.** 제목 분석은 A 영상 전체이고, 댓글 키워드 해석은 그중 한국어 댓글이면서 치이카와 관련으로 판정된 집단에 둔다. 댓글이 없는 영상도 제목 분석에는 들어 있다.")
    a("")
    a("**근거 수치.**")
    a(f"- 제목 분석 영상 {num(stats['n_title'])}편. 영상 비율의 분모는 이 수다. 채널 비율의 분모는 채널 ID가 있는 고유 채널 {num(stats['n_ch_title'])}개다.")
    a(f"- 댓글 {num(stats['n_c'])}건, 연결 영상 {num(stats['n_cv'])}편. 제목만 있고 이 댓글 표에 없는 영상은 {num(stats['unlinked_titles'])}편이다. 이 빠짐을 관심 없음으로 보지 않는다.")
    a(f"- AniBox(`{ANIBOX}`) 댓글 {num(stats['anibox_c'])}건, 전체 댓글의 {pct(stats['anibox_share'])}. 영상당 댓글 최대 {stats['max_c']}건이라 수집 상한 100과 맞다. 정렬 순서와 페이지 수는 이 파일만으로 확인할 수 없다. 작성자 ID와 대댓글 본문은 없다.")
    a(f"- 같은 본문이 두 개 이상 댓글 ID에 나타난 행은 {num(stats['dup_body'])}건이다. ID가 다르면 삭제하지 않았다.")
    a("")
    a("**해석.** 댓글 순위는 수집된 댓글의 구성에 끌린다. AniBox 비중이 크고, 영상당 100개에서 끊긴다. 그래서 댓글 비율과 함께 영상 동일 비중, 채널 동일 비중, AniBox 제외를 같이 본다.")
    a("")
    a("**한계.** 댓글 없는 영상 2천여 편의 반응은 이 댓글 표에 없다. 조회수와 댓글 키워드를 대응시켜 인기를 설명하지 않는다.")
    a("")
    a("## 2. 전처리·선별 결과")
    a("")
    a("**핵심 발견.** 한국어 댓글 전체를 탐색 집단으로 두고, 그중 치이카와 관련 판정만 주요 해석 집단으로 둔다. 불명확 댓글은 지우지 않고 판정 파일에 남긴다.")
    a("")
    a("**근거 수치.**")
    a("- 언어: " + ", ".join(f"{k} {num(v)}" for k, v in stats["lang"].items()))
    a("- 반응 대상: " + ", ".join(f"{k} {num(v)}" for k, v in stats["reac"].items()))
    a(f"- 탐색 집단 {num(stats['explore'])}건, 영상 {num(stats['explore_v'])}편, 채널 {num(stats['explore_ch'])}개.")
    a(f"- 주요 해석 집단 {num(stats['major'])}건, 영상 {num(stats['major_v'])}편, 채널 {num(stats['major_ch'])}개.")
    a(f"- 광고·스팸으로 키워드 집계에서 뺀 댓글 {num(stats['spam'])}건. 자동 규칙으로 반어·부정을 확정하지 못해 검토 표시만 한 댓글 {num(stats['irony'])}건.")
    a("")
    a("**해석.** 주요 해석 집단은 댓글에 작품·캐릭터 표기가 있거나, 제목이 작품명만 있는 영상의 일반 평가다. 제목에 캐릭터가 여럿이거나 제작 단서가 있으면 '귀엽다'만으로 치이카와 반응에 넣지 않았다. 이 판정은 제목 문맥이지, 영상을 보고 한 판정이 아니다.")
    a("")
    a("**한계.** 전체 표본을 사람 손으로 재라벨하지 않았으므로 정확도 퍼센트는 적지 않는다. 표본 검토에서 고친 오류는 `00_검수기록.md`에 적었다. 한글 고유명사 하나, 웃음·이모지만 있는 댓글은 한국어 중심에 넣지 않았다.")
    a("")
    a("## 3. 제목 키워드")
    a("")
    a("**핵심 발견.** 제목 본문에서는 작품·캐릭터 표기가 가장 넓고, 그다음이 상품·행동 쪽 명사다. 해시태그 출현은 본문 출현과 따로 센다.")
    a("")
    a(f"**근거 수치.** 분모는 제목 {num(stats['n_title'])}편, 채널 {num(stats['n_ch_title'])}개. 한 제목 안 반복은 영상 수에서 한 번이다.")
    a("")
    a("작품·캐릭터")
    a("")
    a(md_table(t_char, ["키워드", "종류", "총출현횟수", "출현영상수", "출현영상비율", "출현채널수", "출현채널비율"]))
    a("")
    a("소재·평가")
    a("")
    a(md_table(t_topic, ["키워드", "종류", "총출현횟수", "출현영상수", "출현영상비율", "출현채널수"]))
    a("")
    a("구절은 정해 둔 패턴만 인정했다. 형태소가 붙어 있다는 이유만으로 구절을 만들지 않았다.")
    a("")
    a(md_table(title_phrase, ["키워드", "총출현횟수", "출현영상수", "출현영상비율", "출현채널수"]))
    a("")
    a(f"해시태그가 하나 이상인 영상은 {num(stats['n_hash'])}편이다. 아래 비율의 기본 분모는 전체 제목이다. CSV에는 해시태그가 있는 영상만 분모로 한 비율도 있다.")
    a("")
    a(md_table(hash_rank, ["키워드", "총출현횟수", "출현영상수", "출현영상비율", "출현채널수"]))
    a("")
    a("**해석.** `치이카와`와 `먼작귀`는 둘 다 작품 쪽 표기지만 하나로 합치지 않았다. 어느 쪽을 쓰는지가 채널·형식에 따라 다를 수 있어서다. `우사기`와 `うさぎ`도 따로 둔다. 제목의 '귀엽다'는 영상 소개 문구인 경우가 많아, 이용자 반응과 같은 말로 읽지 않는다.")
    a("")
    a("**한계.** 사용자 사전에 없는 새 상품명과 줄임말은 일반 명사로 남거나 빠질 수 있다. 설명문은 제목에 합치지 않았다.")
    a("")
    a("## 4. 댓글 표현")
    a("")
    a("**핵심 발견.** 주요 해석 집단에서 가장 넓은 평가 표현은 특정 부위나 성격을 가리키지 않는 말이다. 그런 말은 포괄적 귀여움으로 남긴다.")
    a("")
    a(f"**근거 수치.** 주요 해석 분모는 댓글 {num(stats['major'])}건, 영상 {num(stats['major_v'])}편, 채널 {num(stats['major_ch'])}개. 같은 댓글 안 반복은 언급 댓글 수에서 한 번이다.")
    a("")
    a(md_table(m_eval, ["키워드", "종류", "총출현횟수", "언급댓글수", "언급댓글비율", "출현영상수", "출현영상비율", "출현채널수", "주의"]))
    a("")
    a("탐색 집단 상위(비교용)")
    a("")
    e_show = kind(explore_rank, ["평가", "부정", "구절", "소재"])
    a(md_table(e_show, ["키워드", "종류", "언급댓글수", "언급댓글비율", "출현영상수", "출현채널수"]))
    a("")
    a("보조 반응(키워드 순위에 넣지 않음)")
    a("")
    a(md_table(aux, ["지표", "탐색_댓글수", "탐색_비율", "주요해석_댓글수", "주요해석_비율"]))
    a("")
    a("판정 근거별로 다시 나눈 비율이다. `제목문맥_일반평가`는 귀엽다·웃기다 같은 말로 집단에 들어온 댓글이 섞여 있으므로, 그 집단의 귀엽다 비율을 독립된 발견처럼 읽지 않는다. 댓글 안에 작품 표기가 있는 집단이 순환이 덜하다.")
    a("")
    cute = basis_tbl[basis_tbl["키워드"].isin(["귀엽다", "부정-귀엽다", "웃기다", "무섭다", "갖고싶다", "목소리가 귀엽다"])]
    a(md_table(cute, ["집단", "키워드", "언급댓글수", "분모_댓글", "언급댓글비율", "출현영상수", "출현채널수"], n=24))
    a("")
    a("**해석.** 탐색 집단과 주요 해석 집단의 상위 단어는 비슷하다. 다만 주요 해석의 귀엽다 비율이 더 높은 데는, 제목이 작품명뿐인 영상의 일반 평가를 이 집단에 넣었기 때문이 섞여 있다. 부정 표현은 긍정 건수에 넣지 않았다. `귀엽지 않나요`는 긍정 쪽으로 두고, `귀엽지 않아요`는 어느 쪽으로도 세지 않고 검토 표시만 한다.")
    a("")
    a("**한계.** `좋다`와 `사랑`은 대상이 댓글마다 다르다. 문맥 표 없이 인기 요소로 올리지 않는다. 자동 반어 탐지는 검토 표시만 한다.")
    a("")
    a("## 5. 영상·채널 출현 범위")
    a("")
    a("**핵심 발견.** 언급 댓글 비율이 높아도 영상이 일부 채널에 몰리면 범위는 좁다. 출현 범위는 여러 영상·채널에서 보였다는 뜻이지, 시간에 따른 확산이 아니다.")
    a("")
    a("**근거 수치.** 위 표의 출현 영상 비율과 출현 채널 비율이 그 범위다. 분모는 해당 집단에서 댓글이 1건 이상인 영상·채널이다. 그래프 `fig_출현범위.png`는 주요 해석 집단의 영상 비율이다.")
    a("")
    a("**해석.** 캐릭터 이름은 그 캐릭터를 부르는 댓글에만 나타나므로 평가어보다 영상 비율이 낮을 수 있다. 비율이 낮다고 반응이 약하다고 말하지 않는다.")
    a("")
    a("**한계.** 수집 상한 100 때문에 댓글이 많은 영상의 뒷부분 표현은 없다.")
    a("")
    a("## 6. 집중도 영향")
    a("")
    a("**핵심 발견.** 댓글 기준 비율, 영상 동일 비중, 채널 동일 비중은 같은 순서를 보장하지 않는다. AniBox를 뺀 결과는 민감도이고, 기본 데이터에서 AniBox를 지우지는 않았다.")
    a("")
    a("**근거 수치.**")
    a("")
    a(md_table(dist, ["집단", "댓글수", "영상수", "채널수", "영상당_댓글_중앙값", "댓글5건미만_영상비율", "영상1개_채널비율"]))
    a("")
    wshow = ways[ways["범위"].eq("전체")] if len(ways) else ways
    a(md_table(wshow, ["키워드", "댓글기준_비율", "영상동일비중", "채널동일비중", "순위_댓글", "순위_영상", "순위_채널"], n=10))
    a("")
    a("**해석.** 댓글이 5건 미만인 영상이 많으면 영상 동일 비중은 0과 1로 출렁인다. 채널에 영상이 하나뿐이면 채널 동일 비중도 그 영상 하나에 묶인다. 순위가 바뀌면 그 표현이 특정 영상·채널의 말투인지 먼저 의심한다. 바뀌었다는 사실만으로 인기가 늘거나 줄었다고 말하지 않는다.")
    a("")
    a("**한계.** 세 방식은 서로 다른 질문이다. 어느 하나를 진짜 인기 비율로 부르지 않는다.")
    a("")
    a("## 7. 제목–댓글 관계")
    a("")
    a("**핵심 발견.** 제목 키워드가 있는 영상과 없는 영상의 댓글 표현을 `post_id`로 비교했다. 같이 나타났다는 것은 같은 영상에 두 표현이 있었다는 뜻이다.")
    a("")
    a("**근거 수치.** 비교는 주요 해석 댓글이 1건 이상인 영상만 쓴다. 제목 키워드는 한 영상에 여러 개일 수 있다. 전체 표는 `06_제목댓글연결.csv`다.")
    a("")
    if len(link):
        gap = link[link["비교"].eq("제목키워드_있음") & link["범위"].eq("전체")].copy()
        base = link[link["비교"].eq("제목키워드_없음") & link["범위"].eq("전체")][
            ["제목키워드", "댓글키워드", "영상동일비중", "영상수"]
        ].rename(columns={"영상동일비중": "없는쪽_영상동일비중", "영상수": "없는쪽_영상"})
        gap = gap.merge(base, on=["제목키워드", "댓글키워드"], how="left")
        gap = gap[gap["영상수"] >= 30]
        gap["차이"] = gap["영상동일비중"] - gap["없는쪽_영상동일비중"]
        gap = gap.sort_values("차이", ascending=False).head(8)
        a("영상 동일 비중 차이가 큰 조합(있는 쪽 영상 30편 이상, 전체). 차이가 곧 원인은 아니다.")
        a("")
        a(md_table(gap, ["제목키워드", "댓글키워드", "영상수", "채널수", "댓글수", "영상동일비중", "없는쪽_영상동일비중", "없는쪽_영상", "차이"], n=8))
    a("")
    a("**해석.** 제목에 캐릭터 이름이 있는 영상에서 그 이름이 댓글에도 자주 보이면, 시청자가 제목의 대상을 받아 적었을 가능성이 있다. 제목의 소재가 선호를 만들었다고 말하지 않는다. 댓글 수, 채널, 게시 시기가 다르면 차이도 달라진다. CSV의 AniBox 제외 열을 같이 본다. 영상이 적은 조합은 확대하지 않는다.")
    a("")
    a("**한계.** 동시 출현은 인과가 아니다. 제목과 댓글이 같은 말을 쓰는 것은 주제가 같다는 신호에 가깝다.")
    a("")
    a("## 8. 인기 요소 후보와 한계")
    a("")
    a("**핵심 발견.** 이번 분석이 지지하는 것은 후보의 목록이지 인기 이유의 확정이 아니다. `귀엽다`는 포괄적 귀여움으로 남긴다. '목소리가 귀엽다'처럼 댓글이 부위를 말할 때만 구체 후보로 적는다.")
    a("")
    a("**근거 수치.** 후보별 건수와 범위는 3~6절의 표와 `07_문맥검수표.csv`의 서로 다른 채널 문맥을 같이 본다. 대표 댓글은 채널이 겹치지 않게 골랐다. 작성자 개인정보는 파일에 없다.")
    a("")
    a("**해석.** 후보로 남길 말은 주요 해석 집단에서 여러 영상·채널에 나타나고, 집계를 바꿔도 완전히 사라지지 않으며, 문맥이 호감·질문·정보 중 무엇인지 읽히는 말이다. 한 채널의 반복 문구로 보이면 후보에서 한 단계 내린다. 자세한 문맥 메모는 검수표를 보고 보고서에 보강한다.")
    a("")
    a("**한계.** 영상을 재생해 확인하지 않았다. 댓글 정렬이 불명이라 수집된 100개가 전체 반응을 대표한다고 말할 수 없다. 키워드 빈도는 인기 이유가 아니다.")
    a("")
    a("## 실행")
    a("")
    a("원본은 수정하지 않는다. 이 폴더에서 다음을 실행하면 표·그림·이 보고서가 다시 만들어진다.")
    a("")
    a("```")
    a(r"C:\Users\user\anaconda3\python.exe analyze_A_keywords_v1.py")
    a("```")
    a("")
    a("입력은 `youtube_total_cleaning_classified_A.csv`와 `youtube_total_cleaning_classified_A_comments.csv`다. 사전은 `dict_표기통일.csv`, `dict_사용자단어.csv`, `dict_불용어.csv`, `dict_구절_부정규칙.csv`다.")
    (ROOT / "09_키워드_보고서.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
