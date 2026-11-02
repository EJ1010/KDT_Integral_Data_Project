"""텍스트만으로 적격성과 유형 후보를 가른다. 자막·화면 판정이 아니다."""
import re

import pandas as pd

USER_UNRELATED = {
    "UC_bq6EA8U2xCcBgMjshCh0Q": "Antistress Toys",
    "UCDtDKN4I6SS6rCiUi7lPyXg": "NekYos",
    "UCiHMmtaCy2vIcs17gFqC4fQ": "Favorite Toys",
}
REVIEW_DATE = "2026-11-02"
EVIDENCE_SCOPE = "제목·설명·태그. 자막·발화·썸네일·영상 화면은 자료에 없음"

WORK = re.compile(r"치이카와|먼작귀|ちいかわ|まじかるちいかわ|chiikawa", re.I)
CHAR = re.compile(
    r"하치와레|우사기|모몽가|모몬가|랏코|쿠리만쥬|파자마\s*파티즈|파자마즈|데카츠요|갑옷씨|아노코|ハチワレ|うさぎ|モモンガ"
)
NAME_STOP = {
    "치이카와", "먼작귀", "하치와레", "우사기", "모몽가", "모몬가", "랏코", "쿠리만쥬",
    "파자마파티즈", "데카츠요", "갑옷씨", "아노코", "치카와",
}
PARTICLE_STOP = {"함께", "그리고", "하는", "있는", "없는", "이런", "저런", "그냥", "정말", "너무"}
PRODUCT_STOP = {
    "인형", "키링", "피규어", "스티커", "굿즈", "언박싱", "하울", "개봉", "마스코트", "아크릴",
    "파우치", "쿠션", "포카", "가챠", "쿠지", "복권", "뽑기", "빵", "도시락", "케이크", "과자",
    "초콜릿", "팝업", "카페", "콜라보", "더빙", "팬아트", "그리기", "만들기", "인형계", "인형뽑기",
    "최신화", "극장판", "영화", "애니",
}
V3_TYPES = [
    "굿즈", "포토카드", "가챠·쿠지", "인형뽑기", "애니메이션·영화 관련 콘텐츠",
    "팝업·카페", "식음", "콜라보", "팬 창작·놀이",
]
EPISODE = re.compile(r"전편공개|제\s*\d+\s*화|\d+\s*화")
OFFICIAL_JP = re.compile(r"フジテレビ|【公式】|Provided to YouTube")
OTHER_IP = re.compile(r"rainbow\s*friends|sprunki", re.I)
HANGUL_WORD = re.compile(r"[가-힣]{2,}")
HASHTAG = re.compile(r"[#＃][^\s#＃]+")
URL = re.compile(r"https?://\S+")


def strip_tags(text):
    return re.sub(r"\s+", " ", HASHTAG.sub(" ", text or "")).strip()


def content_tokens(text):
    words = []
    for word in HANGUL_WORD.findall(text or ""):
        for name in sorted(NAME_STOP, key=len, reverse=True):
            if word.startswith(name):
                word = word[len(name):]
                break
        word = word.strip("와과를을가이은는도만의")
        if not word or word in NAME_STOP or word in PARTICLE_STOP or word in set("와과를을가이은는도만의"):
            continue
        words.append(word)
    return words


def korean_concrete(text):
    tokens = content_tokens(text)
    return any(word not in PRODUCT_STOP for word in tokens)


def split_title(title):
    title = "" if title is None or (isinstance(title, float) and pd.isna(title)) else str(title)
    tags = re.findall(r"[#＃]([^\s#＃]+)", title)
    return strip_tags(title), " ".join(tags)


def clean_desc(text):
    text = "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text)
    text = URL.sub(" ", text)
    return strip_tags(text)


def judge_ab(channel_id, body, desc):
    named_body = bool(WORK.search(body) or CHAR.search(body))
    named_desc = bool(WORK.search(desc) or CHAR.search(desc))
    concrete = korean_concrete(body) or korean_concrete(desc)
    desc_rest = WORK.sub(" ", desc)
    desc_rest = CHAR.sub(" ", desc_rest)
    desc_kana_left = len(re.findall(r"[ぁ-んァ-ン]", desc_rest))
    official = bool(OFFICIAL_JP.search(body) or OFFICIAL_JP.search(desc))
    latin_words = re.findall(r"[A-Za-z]{3,}", body)
    other_ip = bool(OTHER_IP.search(body))

    if named_body and concrete:
        relevance, rel_why = "관련", "제목 본문에 작품·캐릭터 명칭과 이름 이외의 한국어 서술이 있다"
    elif named_desc and korean_concrete(desc):
        relevance, rel_why = "관련", "설명에 작품·캐릭터를 다루는 한국어 서술이 있다. 해시태그만 있는 경우와 구분"
    elif named_desc and desc_kana_left >= 8 and re.search(r"です|ます|だった", desc):
        relevance, rel_why = "관련", "설명에 작품 명칭과 일본어 장면 서술이 있다. 한국어 대상 판정과는 별개"
    elif named_body and re.search(r"公式|第\d|話", body):
        relevance, rel_why = "관련", "제목이 공식 회차나 일본어 방송 제목이다"
    elif CHAR.search(body):
        relevance, rel_why = "관련", "제목 본문에 개별 캐릭터 이름이 있다"
    elif named_body or named_desc:
        relevance, rel_why = "불명확", "명칭은 있으나 장면·상품·창작을 설명하는 문장이 부족하다"
    else:
        relevance, rel_why = "불명확", "작품 명칭이 제목 본문·설명 서술에 없고 해시태그·태그에만 있거나 보이지 않는다"

    if concrete:
        audience, aud_why = "확인", "해시태그·명칭·상품명을 뺀 뒤에도 한국어 서술이 남는다"
    elif official or other_ip or len(latin_words) >= 4:
        audience, aud_why = "비대상", "한국어 서술이 없고, 공식 일본어 방송·다른 IP·다른 언어 문장이 제목에 있다"
    else:
        audience, aud_why = "불명확", "한국어 대상인지 판단할 구체적 소개가 없다. 다른 언어가 섞였다는 이유만으로 제외하지 않음"
    if channel_id in USER_UNRELATED:
        relevance = "무관"
        rel_why = "사용자가 치이카와와 무관하다고 확인한 채널. 해시태그 일치만으로 관련을 유지하지 않음"
        aud_why = "채널 전체에 대상 언어를 전파하지 않고, 이 영상 텍스트만 본다. " + aud_why
    return relevance, rel_why, audience, aud_why


def candidates(body, tags):
    text = f"{body} {tags}"
    found = {label: [] for label in V3_TYPES}
    goods_patterns = [
        ("인형", r"인형(?!계)"),
        ("키링", r"키링"), ("피규어", r"피규어"), ("스티커", r"스티커"), ("굿즈", r"굿즈"),
        ("언박싱", r"언박싱|unboxing"), ("하울", r"하울"), ("개봉", r"개봉"), ("마스코트", r"마스코트"),
        ("아크릴", r"아크릴"), ("파우치", r"파우치"), ("쿠션", r"쿠션"),
    ]
    for name, pattern in goods_patterns:
        if re.search(pattern, text, re.I):
            found["굿즈"].append(name)
    if re.search(r"포카", text):
        found["포토카드"].append("포카")
    for name, pattern in [
        ("가챠", r"가챠"), ("랜덤깡", r"랜덤깡"), ("쿠지", r"쿠지"),
        ("제일복권", r"제일복권"), ("복권", r"복권"), ("뽑기", r"(?<!인형)뽑기"),
    ]:
        if re.search(pattern, text):
            found["가챠·쿠지"].append(name)
    if re.search(r"인형\s*뽑기", text):
        found["인형뽑기"].append("인형뽑기")
    for name, pattern in [("전편공개", r"전편공개"), ("최신화", r"최신화"), ("애니", r"애니"), ("극장판", r"극장판"), ("영화", r"영화")]:
        if re.search(pattern, text):
            found["애니메이션·영화 관련 콘텐츠"].append(name)
    for name in ("팝업", "카페"):
        if name in text:
            found["팝업·카페"].append(name)
    for name in ("빵", "도시락", "케이크", "과자", "초콜릿"):
        if name in text:
            found["식음"].append(name)
    if "콜라보" in text:
        found["콜라보"].append("콜라보")
    for name, pattern in [
        ("인형계", r"인형계"), ("더빙", r"더빙"), ("팬아트", r"팬아트"), ("그리기", r"그리기"), ("만들기", r"만들기"),
    ]:
        if re.search(pattern, text):
            found["팬 창작·놀이"].append(name)
    return {label: names for label, names in found.items() if names}


def confirmed_types(body, relevance):
    if relevance != "관련":
        return []
    episode = bool(EPISODE.search(body))
    labels = []
    goods_direct = re.search(r"키링|피규어|스티커|굿즈|언박싱|unboxing|하울|개봉|마스코트|아크릴|파우치|쿠션", body, re.I)
    doll = re.search(r"인형(?!계)", body)
    doll_scene = re.search(r"인형이\s*된|인형으로\s*변", body)
    doll_span = re.search(r"인형\s*뽑기", body)
    doll_cue = re.search(r"방\s*꾸|덕후|리뷰|후기|퀄리티|보여\s*드|컬렉션|브이로그|vlog|VLOG", body, re.I)
    if goods_direct or (doll and doll_cue and not doll_scene and not episode):
        labels.append("굿즈")
    if "포카" in body and not episode:
        labels.append("포토카드")
    if re.search(r"가챠|랜덤깡|쿠지|제일복권", body) and not episode:
        labels.append("가챠·쿠지")
    if doll_span and not episode:
        labels.append("인형뽑기")
    movie_words = re.search(r"전편공개|최신화|극장판", body)
    goods_context = re.search(r"콜라보|상품|굿즈|언박싱", body)
    if movie_words and not (goods_context and "전편공개" not in body and "최신화" not in body):
        labels.append("애니메이션·영화 관련 콘텐츠")
    if re.search(r"팝업|카페", body) and not episode:
        labels.append("팝업·카페")
    food = re.search(r"빵|도시락|케이크|과자|초콜릿", body)
    food_scene = re.search(r"핫케이크|팬케이크", body)
    food_act = re.search(r"먹방|레시피|만들기|후기|리뷰|asmr|ASMR|디저트|맛집", body, re.I)
    if food and not episode and not food_scene and (food_act or re.search(r"케이크|도시락|초콜릿", body)):
        if not (re.search(r"빵|과자", body) and not food_act and not re.search(r"케이크|도시락|초콜릿", body)):
            labels.append("식음")
    if "콜라보" in body and not episode:
        labels.append("콜라보")
    if re.search(r"더빙|팬아트|그리기", body) and not episode:
        labels.append("팬 창작·놀이")
    elif re.search(r"인형계", body) and not episode:
        labels.append("팬 창작·놀이")
    elif re.search(r"만들기", body) and not episode and not re.search(r"피자\s*만들기", body):
        labels.append("팬 창작·놀이")
    # 인형계는 제목 본문에 있을 때만 확정한다. body는 해시태그를 뺀 문자열이다.
    return list(dict.fromkeys(labels))


def disposition(relevance, audience):
    if relevance == "무관" and audience == "비대상":
        return "제외", "관련성 무관, 한국어 이용자 대상 아님"
    if relevance == "무관":
        return "제외", "관련성 무관"
    if audience == "비대상":
        return "제외", "한국어 이용자 대상 아님"
    if relevance == "관련" and audience == "확인":
        return "포함", "관련이고 한국어 이용자 대상이 확인됨"
    return "보류", "관련성 또는 한국어 대상 근거가 부족함. 무관으로 처리하지 않음"


def annotate(frame):
    rows = []
    for row in frame.itertuples(index=False):
        body, tags = split_title(row.title)
        desc = clean_desc(row.description)
        relevance, rel_why, audience, aud_why = judge_ab(row.channel_id, body, desc)
        cand = candidates(body, tags)
        types = confirmed_types(body, relevance)
        status, why = disposition(relevance, audience)
        cand_text = " | ".join(f"{label}:{','.join(names)}" for label, names in cand.items())
        rows.append({
            "title_body": body,
            "hashtags": tags,
            "relevance": relevance,
            "relevance_evidence": rel_why,
            "audience": audience,
            "audience_evidence": aud_why,
            "type_candidates": cand_text,
            "type_confirmed": "|".join(types),
            "disposition": status,
            "disposition_reason": why,
        })
    extra = pd.DataFrame(rows)
    return pd.concat([frame.reset_index(drop=True), extra], axis=1)
