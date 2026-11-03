"""한국어 제목과 치이카와 내용 관련성으로 영상을 나눈다.

음성·자막·화면은 보지 않는다. 해시태그를 뺀 제목을 우선하고,
설명은 제목 조건을 충족하지 못한 영상을 A로 올리는 데 쓰지 않는다.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

RULE_VERSION = "ko-title-chiikawa-v1.1"
SOURCE = Path(
    r"C:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\1. column통합\youtube_total_cleaning.csv"
)
OUT_DIR = Path(
    r"C:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
)

STRONG = re.compile(
    r"치이\s*카와|먼작귀|치카와|まじかる\s*ちいかわ|ちいかわ|chiikawa|"
    r"하치\s*와레|ハチワレ|hachiware|"
    r"모몽가|모몬가|モモンガ|쿠리\s*만쥬|くりまんじゅう|"
    r"파자마\s*파티즈|파자마즈|데카\s*츠요|갑옷\s*씨|아노코|あのこ|"
    r"매지컬\s*치이\s*카와|마지컬\s*치이\s*카와|"
    r"먼가\s*작고\s*귀여운|뭔가\s*작고\s*귀여운",
    re.I,
)
AMBIG = re.compile(r"우사기|うさぎ|나가노|농담곰|シーサー|(?<![가-힣])시사(?![가-힣])|(?<![가-힣])카니(?![가-힣])")
OTHER_IP = re.compile(
    r"슬램덩크|산리오|헬로\s*키티|리락쿠마|스밋코|스미코구라시|디즈니|미키\s*마우스|"
    r"미키\s*[&＆]\s*미니|미키\s*마우스|피카츄|포켓몬|원피스|귀멸의\s*칼날|주술회전|"
    r"스파이\s*패밀리|뉴진스|레고|롤리포니|테니프리|하츠네\s*미쿠|"
    r"칸다소바|유니클로|rainbow\s*friends|sprunki|마비노기|스누피|짱구|도라에몽|"
    r"쿠키런|쿠로미|시나모롤|폼폼푸린|한교동|몰랑|잔망루피|브롤스타즈|"
    r"(?<![가-힣])키티(?![가-힣])",
    re.I,
)
HASHTAG = re.compile(r"[#＃][^\s#＃]+")
URL = re.compile(r"https?://\S+")
HANGUL_WORD = re.compile(r"[가-힣]{2,}")
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")
KANA = re.compile(r"[ぁ-んァ-ン]")
KANJI = re.compile(r"[\u4e00-\u9fff]")
FORMAT_WORD = {
    "쇼츠", "영상", "동영상", "유튜브", "추천", "떡상", "알고리즘", "구독", "좋아요",
    "shorts", "short", "youtube", "fyp", "fpy",
}
LOAN = {
    "vlog", "diy", "asmr", "unboxing", "shorts", "short", "review", "reviews", "haul",
    "plush", "cute", "dance", "dancing", "cover", "anime", "cafe", "popup", "goods",
    "gacha", "figure", "figures", "toy", "toys", "doll", "dolls", "opening", "official",
    "funny", "challenge", "fyp", "youtube", "ost", "bgm", "random", "kawaii", "japan",
    "japanese", "korea", "korean", "shop", "store", "new", "the", "and", "for", "with",
    "mv", "sub", "subs", "eng", "engsub",
}
FINAL = {
    "A_우선포함",
    "B_관련있음_한국어대상검토",
    "C_관련성검토",
    "D_비관련확인",
}
LANG = {"한국어 중심", "다국어 혼합", "외국어 중심", "판단 불가"}
REL = {"명확", "가능성 있음", "근거 없음"}
DESC_REL = {"관련 명확", "가능성 있음", "비관련 명확", "근거 부족", "결측"}


def text_or_empty(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def first_text(primary, fallback):
    primary_text = text_or_empty(primary)
    return primary_text or text_or_empty(fallback)


def normalize(text):
    return unicodedata.normalize("NFKC", text_or_empty(text))


def split_hashtags(title):
    title = normalize(title)
    tags = HASHTAG.findall(title)
    body = HASHTAG.sub(" ", title)
    body = re.sub(r"\s+", " ", body).strip(" \t-—|/")
    return body, " ".join(tags)


def strip_names(text):
    text = STRONG.sub(" ", text)
    text = AMBIG.sub(" ", text)
    text = URL.sub(" ", text)
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def content_flags(body):
    residual = strip_names(body)
    hangul = [word for word in HANGUL_WORD.findall(residual) if word not in FORMAT_WORD]
    latin = [word.lower() for word in LATIN_WORD.findall(residual)]
    latin = [word for word in latin if word not in FORMAT_WORD]
    kana = len(KANA.findall(residual))
    kanji = len(KANJI.findall(residual))
    return {
        "hangul": hangul,
        "latin": latin,
        "kana": kana,
        "kanji": kanji,
        "content_ko": bool(hangul),
        "content_en": bool(latin),
        "content_ja": kana >= 2 or kanji >= 1,
    }


def language_class(body):
    flags = content_flags(body)
    if flags["content_ko"]:
        nonloan = [word for word in flags["latin"] if word not in LOAN]
        ja_len = flags["kana"] + flags["kanji"]
        thin_korean = len(flags["hangul"]) <= 1
        foreign_clause = ja_len >= 12 or len(nonloan) >= 4
        # 한국어 구절이 내용을 전하면 번역문·작품명이 붙어 있어도 한국어 중심이다.
        return "다국어 혼합" if thin_korean and foreign_clause else "한국어 중심"
    if flags["content_en"] or flags["content_ja"]:
        return "외국어 중심"
    return "판단 불가"


def title_relevance(body):
    flags = content_flags(body)
    has_content = flags["content_ko"] or flags["content_en"] or flags["content_ja"]
    if STRONG.search(body) and has_content:
        return "명확"
    if STRONG.search(body) or AMBIG.search(body):
        return "가능성 있음"
    return "근거 없음"


def clean_description(description, account_name):
    text = normalize(description)
    if not text:
        return ""
    text = URL.sub(" ", text)
    text = HASHTAG.sub(" ", text)
    kept = []
    for line in re.split(r"[\r\n]+", text):
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        promo = re.search(r"구독|알림\s*설정|비즈니스\s*문의|협찬|광고|파트너스|저작권|무단|Provided to YouTube|쿠팡", line)
        if promo and not STRONG.search(line) and not AMBIG.search(line):
            continue
        kept.append(line)
    cleaned = re.sub(r"\s+", " ", " ".join(kept)).strip()
    name = normalize(account_name)
    if name and cleaned == name:
        return ""
    return cleaned


def substantive_description(cleaned):
    """출처·다음 영상 안내·타임스탬프 나열은 영상 주제를 확정하는 본문에서 뺀다."""
    parts = re.split(r"[\n]+|(?<=[.!?。])\s+", cleaned)
    kept = []
    credit = re.compile(r"브금|BGM|bgm|배경\s*음|배경\s*음악|폰트|OST|ost|Music provide|다음\s*영상|다음에는|전\s*영상|지난\s*영상|멤버십|맴버십")
    for part in parts:
        if credit.search(part) and not STRONG.search(part):
            continue
        part = re.sub(r"\d{1,2}:\d{2}\s*\S{0,24}", " ", part)
        kept.append(part)
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def description_relevance(description, account_name):
    original = normalize(description)
    if not original:
        return "결측", ""
    cleaned = clean_description(original, account_name)
    if not cleaned:
        return "근거 부족", ""
    flags = content_flags(cleaned)
    has_body = flags["content_ko"] or flags["content_en"] or flags["content_ja"]
    if STRONG.search(cleaned) and has_body:
        return "관련 명확", snippet(cleaned, STRONG)
    if STRONG.search(cleaned) or AMBIG.search(cleaned):
        pattern = STRONG if STRONG.search(cleaned) else AMBIG
        return "가능성 있음", snippet(cleaned, pattern)
    topic = substantive_description(cleaned)
    # 설명 앞부분의 다른 작품만 주제 충돌로 본다. 뒤에 적힌 식기·매장·재료는 제외한다.
    head = topic[:180]
    if head and OTHER_IP.search(head):
        return "비관련 명확", snippet(head, OTHER_IP)
    return "근거 부족", ""


def snippet(text, pattern, limit=80):
    found = pattern.search(text)
    if not found:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact[:limit]
    start = max(0, found.start() - 24)
    end = min(len(text), found.end() + 36)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:limit]


def has_strong_marker(text):
    return bool(STRONG.search(normalize(text)))


def classify(title, description, tags, account_name):
    body, hashtags = split_hashtags(title)
    lang = language_class(body)
    rel = title_relevance(body)
    desc_rel, desc_snip = description_relevance(description, account_name)
    tag_text = normalize(tags)
    marker_side = f"{hashtags} {tag_text}"
    side_strong = has_strong_marker(marker_side)
    title_other = bool(OTHER_IP.search(body))

    # 제목에 다른 작품이 함께 있으면 콜라보·합방 영상이므로 설명의 그 이름으로 충돌 처리하지 않는다.
    conflict = rel == "명확" and desc_rel == "비관련 명확" and not title_other
    if conflict:
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-CONFLICT",
            "description",
            desc_snip,
            "제목 본문은 치이카와 내용이 분명한데, 설명 본문은 다른 대상을 말한다.",
            "높음",
        )
    elif rel == "명확" and lang == "한국어 중심":
        final, rule, field, evidence, reason, priority = (
            "A_우선포함",
            "A-KO-CLEAR",
            "title_without_hashtags",
            body[:80],
            "해시태그를 뺀 제목이 한국어로 의미를 전하고, 작품·캐릭터와 내용이 함께 있다.",
            "해당 없음",
        )
    elif rel == "명확":
        final, rule, field, evidence, reason, priority = (
            "B_관련있음_한국어대상검토",
            "B-CLEAR-NOT-KO",
            "title_without_hashtags",
            body[:80],
            f"제목의 치이카와 내용은 분명하다. 제목 언어는 {lang}이라 한국어 대상은 더 봐야 한다.",
            "보통",
        )
    elif rel == "가능성 있음" and STRONG.search(body):
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-NAME-ONLY",
            "title_without_hashtags",
            body[:80],
            "제목 본문에 작품·캐릭터 이름은 있으나 무엇을 하는 영상인지 드러나지 않는다.",
            "높음",
        )
    elif rel == "가능성 있음":
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-AMBIGUOUS-NAME",
            "title_without_hashtags",
            body[:80],
            "제목의 이름만으로는 치이카와인지 다른 대상인지 가리지 못한다.",
            "높음",
        )
    elif desc_rel == "관련 명확":
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-DESC-ONLY",
            "description",
            desc_snip,
            "설명 본문에는 치이카와 내용이 있으나, 해시태그를 뺀 제목은 그 내용을 말하지 않는다.",
            "높음",
        )
    elif desc_rel == "비관련 명확" and title_other:
        final, rule, field, evidence, reason, priority = (
            "D_비관련확인",
            "D-OTHER-SUBJECT",
            "description",
            desc_snip,
            "제목과 설명 본문이 다른 대상을 말하고, 치이카와 내용은 확인되지 않는다.",
            "높음" if side_strong else "해당 없음",
        )
    elif side_strong:
        shown = hashtags or tag_text
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-HASHTAG-OR-TAG",
            "hashtags" if hashtags else "tags",
            re.sub(r"\s+", " ", shown).strip()[:80],
            "치이카와 표현이 해시태그·태그에만 있고 제목 본문에는 없다.",
            "높음",
        )
    elif desc_rel == "비관련 명확":
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-DESC-OTHER",
            "description",
            desc_snip,
            "설명 본문은 다른 대상을 말하지만 제목이 그 대상을 확정하지 않아 검토로 남긴다.",
            "높음",
        )
    elif title_other and desc_rel == "결측":
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-OTHER-UNCONFIRMED",
            "title_without_hashtags",
            body[:80],
            "제목은 다른 대상으로 보이나 설명이 없어 무관으로 확정하지 않는다.",
            "높음",
        )
    else:
        final, rule, field, evidence, reason, priority = (
            "C_관련성검토",
            "C-NO-POSITIVE",
            "title_without_hashtags" if body else "",
            body[:80] if body else "",
            "제목과 설명에서 치이카와 관련 또는 다른 대상이 확인되지 않아 검토로 남긴다.",
            "보통" if body else "높음",
        )

    if not evidence:
        evidence = ""
    return {
        "title_without_hashtags": body,
        "title_language_class": lang,
        "title_relevance_class": rel,
        "description_relevance": desc_rel,
        "final_class": final,
        "rule_id": rule,
        "evidence_field": field,
        "evidence_text": evidence,
        "decision_reason": reason,
        "review_priority": priority,
        "rule_version": RULE_VERSION,
    }


def annotate(frame):
    rows = []
    for row in frame.itertuples(index=False):
        title = first_text(row.full_title, row.post_title)
        description = first_text(row.full_description, row.description)
        rows.append(classify(title, description, row.tags, row.account_name))
    extra = pd.DataFrame(rows)
    return pd.concat([frame.reset_index(drop=True), extra], axis=1)


def run_examples():
    cases = [
        ("치이카와 인형 뽑다가 지갑 털렸어요", "", "", "A_우선포함", "한국어 중심", "명확"),
        ("치이카와 랜덤깡 unboxing", "", "", "A_우선포함", "한국어 중심", "명확"),
        ("ちいかわ 신상 굿즈 개봉", "", "", "A_우선포함", "한국어 중심", "명확"),
        ("하치와레 신상 파우치 개봉", "", "", "A_우선포함", "한국어 중심", "명확"),
        ("오늘 하루 너무 행복했다 #치이카와", "", "", "C_관련성검토", "한국어 중심", "근거 없음"),
        ("Funny dancing challenge #치이카와", "", "", "C_관련성검토", "외국어 중심", "근거 없음"),
        ("Chiikawa plush unboxing #치이카와", "", "", "B_관련있음_한국어대상검토", "외국어 중심", "명확"),
        ("귀여워서 샀어요 #치이카와", "", "", "C_관련성검토", "한국어 중심", "근거 없음"),
        ("슬램덩크 피규어 세트", "", "", "C_관련성검토", "한국어 중심", "근거 없음"),
        ("슬램덩크 피규어 세트", "슬램덩크 피규어 리뷰입니다", "", "D_비관련확인", "한국어 중심", "근거 없음"),
        ("슬램덩크 피규어 세트", "치이카와 피규어를 옆에 두고 찍었습니다", "", "C_관련성검토", "한국어 중심", "근거 없음"),
        ("먼가 작고 귀여운 녀석 125화 고구마빵", "", "", "A_우선포함", "한국어 중심", "명확"),
        ("우사기 인형 개봉", "", "", "C_관련성검토", "한국어 중심", "가능성 있음"),
        ("치이카와", "", "", "C_관련성검토", "판단 불가", "가능성 있음"),
    ]
    failed = []
    for title, description, tags, final, lang, rel in cases:
        got = classify(title, description, tags, "")
        if got["final_class"] != final or got["title_language_class"] != lang or got["title_relevance_class"] != rel:
            failed.append((title, final, lang, rel, got["final_class"], got["title_language_class"], got["title_relevance_class"], got["rule_id"]))
    return failed


def main():
    failed = run_examples()
    print("example_failures", len(failed))
    for item in failed:
        print(item)
    if failed:
        raise SystemExit("예시 문장 분류가 기준과 다릅니다.")

    source = pd.read_csv(SOURCE, encoding="utf-8-sig")
    result = annotate(source)
    assert len(result) == len(source)
    assert result["post_id"].tolist() == source["post_id"].tolist()
    for column in source.columns:
        left = source[column].fillna("__NA__").astype(str)
        right = result[column].fillna("__NA__").astype(str)
        assert left.equals(right), column
    assert set(result["final_class"]) <= FINAL
    assert set(result["title_language_class"]) <= LANG
    assert set(result["title_relevance_class"]) <= REL
    assert set(result["description_relevance"]) <= DESC_REL
    included = result["final_class"].eq("A_우선포함")
    assert result.loc[included, "title_language_class"].eq("한국어 중심").all()
    assert result.loc[included, "title_relevance_class"].eq("명확").all()
    assert result.loc[included, "title_without_hashtags"].str.len().gt(0).all()
    assert result.loc[included, "title_without_hashtags"].map(lambda text: bool(STRONG.search(text))).all()
    assert result.loc[included, "title_language_class"].ne("외국어 중심").all()
    dropped = result["final_class"].eq("D_비관련확인")
    assert not result.loc[dropped, "title_without_hashtags"].map(lambda text: bool(STRONG.search(text))).any()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_path = OUT_DIR / "youtube_total_cleaning_classified.csv"
    review = result[result["final_class"].isin(["B_관련있음_한국어대상검토", "C_관련성검토"])].copy()
    review_path = OUT_DIR / "youtube_total_cleaning_review_BC.csv"
    result.to_csv(all_path, index=False, encoding="utf-8-sig")
    review.to_csv(review_path, index=False, encoding="utf-8-sig")

    print("rows", len(result), "review_BC", len(review))
    print(result["final_class"].value_counts().to_string())
    print(result["title_language_class"].value_counts().to_string())
    print(result["rule_id"].value_counts().to_string())
    print("saved", all_path.name, review_path.name)


if __name__ == "__main__":
    main()
