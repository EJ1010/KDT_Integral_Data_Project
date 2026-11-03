"""B 영상의 수집 댓글에서 한국어 반응이 우세한 영상을 가른다.

시청자 국가나 작성자 국적은 추정하지 않는다.
결과는 '수집 댓글 기준 한국어 반응 우세 영상'이다.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

RULE_VERSION = "b-kr-comment-v1"
VIDEO_PATH = Path(
    r"C:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
    r"\youtube_total_cleaning_classified.csv"
)
COMMENT_DIR = Path(
    r"C:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\2. comments\raw"
)
OUT_DIR = VIDEO_PATH.parent / "B_댓글_한국어반응"

NAMES = re.compile(
    r"치이\s*카와|하치\s*와레|우사기|모몽가|모몬가|먼작귀|치카와|쿠리\s*만쥬|"
    r"파자마\s*파티즈|랏코|갑옷\s*씨|아노코|데카\s*츠요|"
    r"chiikawa|hachiware|usagi|momonga",
    re.I,
)
HANGUL_WORD = re.compile(r"[가-힣]{2,}")
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
KANA = re.compile(r"[ぁ-んァ-ン]")
KANJI = re.compile(r"[\u4e00-\u9fff]")
LAUGH = re.compile(r"^[ㅋㅎㅠㅜ]+$")
URL = re.compile(r"https?://\S+|www\.\S+")
SPAM = re.compile(
    r"카지노|슬롯\s*머신|비트코인|코인\s*리딩|텔레그램|(?:^|\s)telegram(?:\s|$)|t\.me/|"
    r"대출\s*상담|성인\s*방송|무료\s*충전|홍보\s*문의",
    re.I,
)
REACTION_LATIN = {"lol", "lmao", "omg", "wow", "www", "kk", "kkk", "hhhh"}
KO = "한국어 중심"
KO_MIX = "혼합_한국어 중심"
FOREIGN = "외국어 중심"
UNKNOWN = "판단 불가"
EMPTY = "빈 댓글"
SPAM_LABEL = "광고·스팸"
JUDGEABLE = {KO, KO_MIX, FOREIGN}


def norm(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).replace("\u200b", "")
    return text.strip()


def comment_language(text):
    raw = norm(text)
    if not raw:
        return EMPTY, "본문이 비어 있음"
    if SPAM.search(raw):
        return SPAM_LABEL, "도박·대출·텔레그램 홍보 문구"
    stripped = URL.sub(" ", raw)
    stripped = re.sub(r"[\W_]+", " ", stripped, flags=re.UNICODE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if not stripped:
        return UNKNOWN, "이모지·기호·URL만 있음"
    residual = NAMES.sub(" ", stripped)
    hangul = [word for word in HANGUL_WORD.findall(residual) if not LAUGH.fullmatch(word)]
    latin = [word.lower() for word in LATIN_WORD.findall(residual)]
    latin = [word for word in latin if word not in REACTION_LATIN and not NAMES.fullmatch(word)]
    kana = len(KANA.findall(residual))
    kanji = len(KANJI.findall(residual))
    korean = bool(hangul)
    foreign = kana >= 2 or kanji >= 1 or len(latin) >= 1
    if korean and (kana >= 2 or kanji >= 1 or len(latin) >= 2):
        return KO_MIX, "한국어 문장과 다른 언어 문장이 함께 있음"
    if korean:
        return KO, "한국어로 의미가 전달됨"
    if foreign:
        return FOREIGN, "다른 언어로 의미가 전달됨"
    return UNKNOWN, "웃음·이모지·이름만 있어 언어를 정하지 않음"


def load_comments():
    frames = []
    for year in range(2022, 2027):
        frames.append(pd.read_csv(COMMENT_DIR / f"youtube_comments_{year}.csv", encoding="utf-8-sig"))
    comments = pd.concat(frames, ignore_index=True)
    before = len(comments)
    comments["comment_id"] = comments["comment_id"].map(norm)
    comments["video_id"] = comments["video_id"].map(norm)
    comments = comments.drop_duplicates("comment_id", keep="first")
    return comments, before - len(comments)


def load_status():
    frames = []
    for year in range(2022, 2027):
        frames.append(pd.read_csv(COMMENT_DIR / f"youtube_comment_status_{year}.csv", encoding="utf-8-sig"))
    status = pd.concat(frames, ignore_index=True)
    status["video_id"] = status["video_id"].map(norm)
    return status.drop_duplicates("video_id", keep="first")


def ratio(numerator, denominator):
    if denominator == 0:
        return pd.NA
    return round(numerator / denominator, 4)


def assign_class(matched, judgeable, ko_ratio, detectable_ratio, status):
    if matched == 0:
        if status == "comments_disabled":
            return "B-KR_근거부족", "댓글 기능이 꺼져 수집되지 않음"
        if status == "unavailable":
            return "B-KR_근거부족", "영상을 확인하지 못해 댓글 수집이 실패함"
        if status == "complete":
            return "B-KR_근거부족", "수집은 끝났고 API 결과가 0건임"
        return "B-KR_근거부족", "매칭 댓글 없음·원인 불명"
    if judgeable == 0 or pd.isna(ko_ratio):
        return "B-KR_근거부족", "언어를 판별할 수 있는 댓글이 없음"
    high = ko_ratio >= 0.70
    mid = 0.50 <= ko_ratio < 0.70
    enough = judgeable >= 20
    readable = (not pd.isna(detectable_ratio)) and detectable_ratio >= 0.50
    if enough and high and readable:
        return "B-KR_포함후보", "판별 가능 댓글 20개 이상, 한국어 반응 비율 70% 이상, 판별 가능 비율 50% 이상"
    if mid or (high and not enough) or (high and not readable):
        return "B-KR_추가검토", "한국어 반응 비율이나 댓글 수가 포함 기준에 못 미침"
    if enough and ko_ratio < 0.50 and readable:
        return "B-KR_기준미충족", "판별 가능 댓글은 충분하고 한국어 반응 비율은 50% 미만"
    return "B-KR_근거부족", "판별 가능 댓글 수 또는 판별 가능 비율이 부족함"


def run_examples():
    cases = [
        ("귀여워", KO),
        ("사고 싶다", KO),
        ("ㅋㅋㅋ", UNKNOWN),
        ("ㅠㅠ", UNKNOWN),
        ("치이카와", UNKNOWN),
        ("하치와레 かわいい", FOREIGN),
        ("かわいい", FOREIGN),
        ("하치야 지휘자인데 왜 돈이 없어", KO),
        ("so cute 진짜 귀엽다", KO_MIX),
        ("", EMPTY),
        ("https://example.com", UNKNOWN),
        ("텔레그램으로 문의 t.me/spamchannel", SPAM_LABEL),
    ]
    failed = []
    for text, expected in cases:
        got, _ = comment_language(text)
        if got != expected:
            failed.append((text, expected, got))
    return failed


def threshold_table(videos):
    rows = []
    base = videos[videos["ko_comment_ratio"].notna() & videos["detectable_ratio"].notna()]
    official = set(videos.loc[videos["b_kr_class"].eq("B-KR_포함후보"), "post_id"])
    for minimum in (10, 20, 30):
        for threshold in (0.60, 0.70, 0.80):
            picked = base[
                base["judgeable_comment_count"].ge(minimum)
                & base["ko_comment_ratio"].ge(threshold)
                & base["detectable_ratio"].ge(0.50)
            ]
            ids = set(picked["post_id"])
            rows.append({
                "최소_판별가능댓글": minimum,
                "한국어비율_기준": threshold,
                "포함후보_수": len(ids),
                "운영기준_20개_70%와_같음": len(ids & official),
                "운영기준보다_늘어난_영상": len(ids - official),
                "운영기준에서_빠지는_영상": len(official - ids),
            })
    return pd.DataFrame(rows)


def main():
    failed = run_examples()
    if failed:
        print("example_failures", failed)
        raise SystemExit("댓글 언어 예시가 기준과 다릅니다.")

    videos = pd.read_csv(VIDEO_PATH, encoding="utf-8-sig")
    source_b = videos.loc[videos["final_class"].eq("B_관련있음_한국어대상검토")].copy()
    source_b["post_id"] = source_b["post_id"].map(norm)
    assert source_b["post_id"].is_unique

    comments, duplicate_removed = load_comments()
    status = load_status()
    b_ids = set(source_b["post_id"])
    matched = comments.loc[comments["video_id"].isin(b_ids)].copy()
    matched["post_id"] = matched["video_id"]
    labels = [comment_language(text) for text in matched["text"]]
    matched["language_class"] = [item[0] for item in labels]
    matched["language_reason"] = [item[1] for item in labels]
    matched["in_valid"] = ~matched["language_class"].isin([EMPTY, SPAM_LABEL])
    matched["in_judgeable"] = matched["language_class"].isin(JUDGEABLE)
    matched["exclude_reason"] = ""
    matched.loc[matched["language_class"].eq(EMPTY), "exclude_reason"] = "빈 댓글"
    matched.loc[matched["language_class"].eq(SPAM_LABEL), "exclude_reason"] = "광고·스팸"
    matched.loc[matched["language_class"].eq(UNKNOWN), "exclude_reason"] = "언어 판별 분모에서 제외"

    grouped = []
    for post_id, frame in matched.groupby("post_id", sort=False):
        valid = frame["in_valid"]
        judge = frame["in_judgeable"]
        ko_n = int(frame["language_class"].isin([KO, KO_MIX]).sum())
        foreign_n = int(frame["language_class"].eq(FOREIGN).sum())
        unknown_n = int(frame["language_class"].eq(UNKNOWN).sum())
        judge_n = int(judge.sum())
        valid_n = int(valid.sum())
        grouped.append({
            "post_id": post_id,
            "raw_matched_comment_count": int(len(frame)),
            "deduped_comment_count": int(frame["comment_id"].nunique()),
            "valid_comment_count": valid_n,
            "judgeable_comment_count": judge_n,
            "ko_comment_count": int(frame["language_class"].eq(KO).sum()),
            "ko_mixed_comment_count": int(frame["language_class"].eq(KO_MIX).sum()),
            "foreign_comment_count": foreign_n,
            "unknown_comment_count": unknown_n,
            "empty_comment_count": int(frame["language_class"].eq(EMPTY).sum()),
            "spam_comment_count": int(frame["language_class"].eq(SPAM_LABEL).sum()),
            "ko_reaction_count": ko_n,
            "ko_comment_ratio": ratio(ko_n, judge_n),
            "detectable_ratio": ratio(judge_n, valid_n),
            "reply_count_sum": int(pd.to_numeric(frame["reply_count"], errors="coerce").fillna(0).sum()),
            "comments_with_replies": int(pd.to_numeric(frame["reply_count"], errors="coerce").fillna(0).gt(0).sum()),
        })
    metrics = pd.DataFrame(grouped)
    result = source_b.merge(metrics, on="post_id", how="left", validate="one_to_one")
    count_cols = [col for col in metrics.columns if col.endswith("_count") or col.endswith("_sum") or col.startswith("comments_with")]
    for col in count_cols:
        result[col] = result[col].fillna(0).astype(int)
    status_small = status.rename(columns={"video_id": "post_id", "status": "collection_status", "collected_count": "status_collected_count"})
    result = result.merge(
        status_small[["post_id", "collection_status", "status_collected_count", "error_reason", "next_token"]],
        on="post_id",
        how="left",
        validate="one_to_one",
    )
    classes = []
    reasons = []
    for row in result.itertuples(index=False):
        label, reason = assign_class(
            int(row.raw_matched_comment_count),
            int(row.judgeable_comment_count),
            row.ko_comment_ratio,
            row.detectable_ratio,
            norm(row.collection_status),
        )
        classes.append(label)
        reasons.append(reason)
    result["b_kr_class"] = classes
    result["decision_reason"] = reasons
    result["collection_capped"] = result["collection_status"].eq("capped")
    result["author_check"] = "수행불가_작성자ID없음"
    result["reply_body_check"] = "수행불가_대댓글본문없음"
    result["distortion_flag"] = "확인불가"
    result["match_note"] = result["collection_status"].map(lambda value: {
        "comments_disabled": "댓글 기능 꺼짐",
        "unavailable": "영상 확인 불가",
        "complete": "수집 완료",
        "capped": "영상당 100개 상한으로 수집이 중단됨",
    }.get(norm(value), "매칭 댓글 없음·원인 불명"))
    result.loc[result["raw_matched_comment_count"].gt(0) & result["collection_status"].isna(), "match_note"] = "상태 기록 없이 댓글만 매칭됨"
    result["rule_version"] = RULE_VERSION
    result["selection_label"] = "수집 댓글 기준 한국어 반응 우세 영상"

    assert len(result) == len(source_b)
    assert set(result["post_id"]) == set(source_b["post_id"])
    assert result["post_id"].is_unique
    assert int(metrics["post_id"].nunique()) == len(metrics)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_DIR / "b_kr_video_judgments.csv", index=False, encoding="utf-8-sig")
    include_cols = ["post_id", "ko_comment_ratio", "ko_reaction_count", "judgeable_comment_count", "detectable_ratio", "b_kr_class", "rule_version"]
    included = result.loc[result["b_kr_class"].eq("B-KR_포함후보"), include_cols].drop_duplicates("post_id")
    included.to_csv(OUT_DIR / "b_kr_include_candidates.csv", index=False, encoding="utf-8-sig")
    result.loc[result["b_kr_class"].eq("B-KR_추가검토")].to_csv(OUT_DIR / "b_kr_additional_review.csv", index=False, encoding="utf-8-sig")
    comment_out = matched[[
        "comment_id", "post_id", "published_at", "text", "language_class", "language_reason",
        "in_valid", "in_judgeable", "exclude_reason", "reply_count",
    ]].copy()
    comment_out.to_csv(OUT_DIR / "b_kr_comment_language.csv", index=False, encoding="utf-8-sig")
    grid = threshold_table(result)
    grid.to_csv(OUT_DIR / "b_kr_threshold_comparison.csv", index=False, encoding="utf-8-sig")

    print("B", len(result), "unique", result["post_id"].nunique())
    print(result["b_kr_class"].value_counts().to_string())
    print("matched comments", len(matched), "videos", matched["post_id"].nunique(), "dup_removed", duplicate_removed)
    print("no comments", int(result["raw_matched_comment_count"].eq(0).sum()))
    print("status missing", int(result["collection_status"].isna().sum()))
    print(result["collection_status"].value_counts(dropna=False).to_string())
    print(matched["language_class"].value_counts().to_string())
    print(grid.to_string(index=False))
    sample = matched.groupby("language_class", group_keys=False).head(6)[["language_class", "text"]]
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
