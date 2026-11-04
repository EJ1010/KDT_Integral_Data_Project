# -*- coding: utf-8 -*-
"""Power BI용 최소 테이블을 만든다. 원본·판정·기존 요약 CSV는 읽기만 한다.

세부 매력 이름은 05_세부매력.csv를 만든 assign 규칙을 그대로 붙인다.
규칙이 공개된 요약과 다르면 파일을 쓰지 않고 멈춘다.
"""

from __future__ import annotations

import csv
import importlib.util
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos"
)
ANALYSIS = ROOT / "05. 분석"
OUT = ROOT / "06_PowerBI"
DATA = OUT / "data"
CHARM_SRC = Path(
    r"C:\Users\user\AppData\Local\Cursor\AgentStores\cursor_agent_stores"
    r"\dc6ab1ac-89a2-4949-a397-b9147b6bf627\files\assign_charm.py"
)
VID_PATH = ROOT / "02. cleaning" / "2. 제목분류" / "youtube_total_cleaning_classified_A.csv"
CMT_PATH = ROOT / "03. 분석용테이블" / "youtube_total_cleaning_classified_A_comments.csv"
ANIBOX = "UCBTSkFNWmoOkBeZwANcbiIA"
LEVELS = ["직접 밝힌 이유", "구체적 긍정 평가", "포괄적 호감", "특징 묘사만 있음", "호감 근거 없음", "판단 불가"]
BIN_ORDER = [
    "60초 이하",
    "60초 초과–180초 이하",
    "180초 초과–600초 이하",
    "600초 초과–1,200초 이하",
    "1,200초 초과",
    "변환 불가·결측",
]
DUR_RE = __import__("re").compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


def fail(message: str) -> None:
    raise SystemExit(message)


def load_charm():
    if not CHARM_SRC.exists():
        fail(f"세부 매력 규칙 파일이 없습니다: {CHARM_SRC}")
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "charm_rules.py"
    shutil.copyfile(CHARM_SRC, dest)
    spec = importlib.util.spec_from_file_location("charm_rules", dest)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_duration_seconds(value) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().upper()
    if text in ("", "NAN"):
        return np.nan
    match = DUR_RE.fullmatch(text)
    if not match or not any(match.groupdict().values()):
        return np.nan
    parts = match.groupdict()
    return (
        int(parts["days"] or 0) * 86400
        + int(parts["hours"] or 0) * 3600
        + int(parts["minutes"] or 0) * 60
        + float(parts["seconds"] or 0)
    )


def duration_bin(seconds) -> str:
    if pd.isna(seconds):
        return "변환 불가·결측"
    if seconds <= 60:
        return "60초 이하"
    if seconds <= 180:
        return "60초 초과–180초 이하"
    if seconds <= 600:
        return "180초 초과–600초 이하"
    if seconds <= 1200:
        return "600초 초과–1,200초 이하"
    return "1,200초 초과"


def blank_text(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.replace("\r", " ", regex=False).str.replace("\n", " ", regex=False)
    text = text.str.replace(r"\s+", " ", regex=True).str.strip()
    text = text.replace({"nan": "", "None": "", "<NA>": ""})
    return text.mask(text.eq(""), pd.NA)


def write_csv(frame: pd.DataFrame, name: str) -> None:
    path = DATA / name
    frame.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_NONNUMERIC)
    print(f"wrote {name} {len(frame):,} rows")


def channel_label(account_id) -> str:
    if pd.isna(account_id) or str(account_id).strip() == "":
        return "채널 정보 없음"
    if account_id == ANIBOX:
        return "AniBox"
    return "AniBox 외"


def choose_names(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    named = frame.dropna(subset=["account_id"])
    for account_id, group in named.groupby("account_id", sort=False):
        names = group["account_name"].fillna("(이름 결측)")
        counts = names.value_counts()
        top = counts[counts == int(counts.max())].index.tolist()
        if len(top) == 1:
            display = top[0]
        else:
            latest = group.assign(_name=names).sort_values(
                ["created_kst", "post_id"], ascending=[False, True]
            )
            display = latest["_name"].iloc[0]
        rows.append({"account_id": account_id, "채널명": display, "이름수": int(names.nunique())})
    return pd.DataFrame(rows)


def build_videos() -> pd.DataFrame:
    raw = pd.read_csv(VID_PATH, encoding="utf-8-sig")
    if raw["post_id"].duplicated().any() or raw["post_id"].isna().any():
        fail("영상 post_id가 고유하지 않습니다.")
    if len(raw) != 6462:
        fail(f"영상 행 수가 6,462가 아닙니다: {len(raw)}")
    work = raw.copy()
    created = work["created_at"].fillna("").astype(str).str.strip()
    explicit = created.str.endswith("Z") | created.str.contains(r"[+-]\d\d:\d\d$", regex=True)
    created_utc = pd.to_datetime(work["created_at"], utc=True, errors="coerce")
    created_kst = created_utc.dt.tz_convert("Asia/Seoul")
    created_kst = created_kst.where(explicit)
    work["created_kst"] = created_kst
    work["view_count"] = pd.to_numeric(work["view_count"], errors="coerce")
    work["duration_sec"] = work["duration"].map(parse_duration_seconds)
    names = choose_names(work)
    if int((names["이름수"] > 1).sum()) != 0:
        fail("이름이 둘 이상인 채널이 있습니다. 기존 검증과 다릅니다.")
    out = work.merge(names[["account_id", "채널명"]], on="account_id", how="left")
    out["게시연도"] = out["created_kst"].dt.year.astype("Int64").astype(str).replace("<NA>", pd.NA)
    out.loc[out["created_kst"].isna(), "게시연도"] = "게시 시각 없음"
    out["게시월"] = out["created_kst"].dt.strftime("%Y-%m")
    out.loc[out["created_kst"].isna(), "게시월"] = pd.NA
    out["게시월순서"] = out["created_kst"].dt.year * 100 + out["created_kst"].dt.month
    out["연도순서"] = out["created_kst"].dt.year
    out.loc[out["created_kst"].isna(), "연도순서"] = 9999
    out["길이구간"] = out["duration_sec"].map(duration_bin)
    out["길이순서"] = out["길이구간"].map({name: i + 1 for i, name in enumerate(BIN_ORDER)})
    out["채널구분"] = out["account_id"].map(channel_label)
    out["영상제목"] = blank_text(out["full_title"] if "full_title" in out.columns else out["post_title"])
    views = out["view_count"]
    if int(views.notna().sum()) != 6454:
        fail(f"조회수 유효 영상 수가 6,454가 아닙니다: {int(views.notna().sum())}")
    if int(views.sum()) != 553330431:
        fail(f"조회수 합계가 다릅니다: {views.sum()}")
    if float(np.nanmedian(views.to_numpy(dtype=float))) != 2107:
        fail(f"조회수 중앙값이 2,107이 아닙니다: {np.nanmedian(views.to_numpy(dtype=float))}")
    channels = out.loc[out["account_id"].notna(), "account_id"].nunique()
    if channels != 2949:
        fail(f"채널 수가 2,949가 아닙니다: {channels}")
    if int(out["created_kst"].isna().sum()) != 8:
        fail("게시 시각 결측이 8편이 아닙니다.")
    if set(out["final_class"].dropna().unique()) != {"A_우선포함"}:
        fail("final_class가 모두 A_우선포함이 아닙니다.")
    keep = out[
        [
            "post_id",
            "account_id",
            "채널명",
            "채널구분",
            "영상제목",
            "게시연도",
            "연도순서",
            "게시월",
            "게시월순서",
            "길이구간",
            "길이순서",
            "view_count",
        ]
    ].rename(columns={"view_count": "조회수"})
    keep["연도순서"] = keep["연도순서"].astype("Int64")
    keep["게시월순서"] = keep["게시월순서"].astype("Int64")
    keep["길이순서"] = keep["길이순서"].astype("Int64")
    keep["조회수"] = keep["조회수"].astype("Int64")
    return keep


def build_comments(videos: pd.DataFrame) -> pd.DataFrame:
    if not CMT_PATH.exists():
        fail(f"댓글 원본이 없습니다: {CMT_PATH}")
    raw = pd.read_csv(CMT_PATH, encoding="utf-8-sig", usecols=["comment_id", "post_id"])
    if len(raw) != 90921:
        fail(f"댓글 행 수가 90,921이 아닙니다: {len(raw)}")
    if raw["comment_id"].duplicated().any() or raw["comment_id"].isna().any():
        fail("comment_id가 고유하지 않습니다.")
    missing = ~raw["post_id"].isin(set(videos["post_id"]))
    if missing.any():
        fail(f"영상에 없는 post_id를 가진 댓글이 {int(missing.sum())}건입니다.")
    judge = pd.read_csv(
        ANALYSIS / "A_키워드" / "01_댓글판정.csv",
        encoding="utf-8-sig",
        usecols=["comment_id"],
    )
    if set(judge["comment_id"]) != set(raw["comment_id"]):
        fail("키워드 댓글 판정의 comment_id가 원본 댓글과 다릅니다.")
    return raw


VAGUE_MARKERS = (
    "말하지 않음",
    "특정하지 않은",
    "서로 다른 장면",
    "그 밖의 긍정",
    "부위를 말하지 않은",
    "디테일을 말하지 않은",
    "내용을 특정하지 않은",
)


def display_rank(frame: pd.DataFrame) -> pd.DataFrame:
    """발표 화면용 표시 순서. 기존 매력 이름을 바꾸거나 새로 나누지 않는다."""
    out = frame.copy()
    charm = out["매력"].fillna("").astype(str)
    vague = charm.apply(lambda text: any(marker in text for marker in VAGUE_MARKERS))
    out["본문우선"] = np.where((out["매력집계"] == "포함") & ~vague & charm.ne(""), "본문", "상세")
    level = out["호감근거_수준"].map({"직접 밝힌 이유": 0, "구체적 긍정 평가": 1}).fillna(9)
    rep = pd.to_numeric(out["대표"], errors="coerce").fillna(0)
    work = out.assign(_level=level, _rep=-rep)
    eligible = work["매력집계"].eq("포함") & work["매력"].fillna("").ne("")
    chosen = (
        work.loc[eligible]
        .sort_values(["_level", "_rep", "comment_id", "연결키"])
        .groupby(["표시대상", "매력", "comment_id"], sort=False)
        .head(1)
    )
    out["댓글대표행"] = pd.NA
    out.loc[chosen.index, "댓글대표행"] = 1
    ranked = chosen.sort_values(["_level", "comment_id", "연결키"]).copy()
    ranked["카드순"] = ranked.groupby(["표시대상", "매력"]).cumcount() + 1
    out["카드순"] = pd.NA
    out.loc[ranked.index, "카드순"] = ranked["카드순"].astype(int)
    return out


def excerpt(text: str, limit: int = 240) -> str:
    if not isinstance(text, str) or text.strip() == "":
        return pd.NA
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def aggregate_charm(frame: pd.DataFrame) -> pd.DataFrame:
    use = frame[frame["매력"].notna()].copy()
    rows = []
    keys = ["평가대상", "표시대상", "특징_범주", "매력"]
    for key, group in use.groupby(keys, dropna=False):
        per = group.groupby("comment_id").agg(
            이유=("호감근거_수준", lambda s: bool((s == "직접 밝힌 이유").any())),
            구체=("호감근거_수준", lambda s: bool((s == "구체적 긍정 평가").any())),
            post_id=("post_id", "first"),
            account_id=("account_id", "first"),
        ).reset_index()
        rows.append(
            {
                "평가대상_구분": key[0],
                "평가_대상": key[1],
                "큰_범주": key[2],
                "구체적_매력": key[3],
                "직접_이유_댓글": int(per["이유"].sum()),
                "구체적_긍정_댓글": int(per["구체"].sum()),
                "합집합_댓글": int(len(per)),
                "영상": int(per["post_id"].nunique()),
                "채널": int(per["account_id"].nunique()),
                "애니박스_댓글": int((per["account_id"] == ANIBOX).sum()),
                "그외_댓글": int((per["account_id"] != ANIBOX).sum()),
                "그외_채널": int(per.loc[per["account_id"] != ANIBOX, "account_id"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_category(frame: pd.DataFrame) -> pd.DataFrame:
    char = frame[
        frame["평가대상"].eq("특정 캐릭터")
        & frame["평가_방향"].eq("긍정")
        & frame["호감근거_수준"].isin(LEVELS[:2])
        & ~frame["특징_범주"].isin(["포괄", "없음"])
    ]
    rows = []
    for key, group in char.groupby(["대상_상세", "특징_범주"], dropna=False):
        per = group.groupby("comment_id").agg(
            이유=("호감근거_수준", lambda s: bool((s == "직접 밝힌 이유").any())),
            구체=("호감근거_수준", lambda s: bool((s == "구체적 긍정 평가").any())),
            post_id=("post_id", "first"),
            account_id=("account_id", "first"),
        ).reset_index()
        rows.append(
            {
                "대상_상세": key[0],
                "특징_범주": key[1],
                "직접_이유_댓글": int(per["이유"].sum()),
                "구체적_긍정_댓글": int(per["구체"].sum()),
                "합집합_댓글": int(len(per)),
                "연결행": int(len(group)),
                "영상": int(per["post_id"].nunique()),
                "채널": int(per["account_id"].nunique()),
                "애니박스_댓글": int((per["account_id"] == ANIBOX).sum()),
                "그외_댓글": int((per["account_id"] != ANIBOX).sum()),
                "그외_채널": int(per.loc[per["account_id"] != ANIBOX, "account_id"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def compare(name: str, got: pd.DataFrame, expected: pd.DataFrame, keys: list[str], values: list[str]) -> None:
    left = got[keys + values].copy()
    right = expected[keys + values].copy()
    for col in values:
        left[col] = pd.to_numeric(left[col])
        right[col] = pd.to_numeric(right[col])
    merged = left.merge(right, on=keys, how="outer", suffixes=("_계산", "_기존"), indicator=True)
    bad = merged[merged["_merge"] != "both"]
    if len(bad):
        print(bad.head(20).to_string(index=False))
        fail(f"{name} 키가 기존 요약과 다릅니다. 한쪽만 있는 행 {len(bad)}")
    for col in values:
        diff = merged[merged[f"{col}_계산"] != merged[f"{col}_기존"]]
        if len(diff):
            print(diff[keys + [f"{col}_계산", f"{col}_기존"]].head(20).to_string(index=False))
            fail(f"{name}의 {col}이 기존 요약과 다릅니다. {len(diff)}행")
    print(f"match {name} {len(merged)} rows")


def build_judgement(videos: pd.DataFrame, charm):
    link = pd.read_csv(ANALYSIS / "A_호감문맥_912" / "03_연결_진행.csv", encoding="utf-8-sig")
    context = pd.read_csv(ANALYSIS / "A_호감문맥_912" / "03_댓글판정_진행.csv", encoding="utf-8-sig")
    entered = pd.read_csv(ANALYSIS / "A_호감문맥_912" / "01_입력_912.csv", encoding="utf-8-sig")
    if len(link) != 1442:
        fail(f"연결 행이 1,442가 아닙니다: {len(link)}")
    if link["comment_id"].nunique() != 912 or context["comment_id"].nunique() != 912:
        fail("고유 comment_id가 912가 아닙니다.")
    if len(context) != 912 or len(entered) != 912:
        fail("댓글 판정 또는 입력 행 수가 912가 아닙니다.")
    if context["comment_id"].duplicated().any() or entered["comment_id"].duplicated().any():
        fail("댓글 단위 파일이 댓글당 한 행이 아닙니다.")
    if set(link["프롬프트"].unique()) != {"context-912-v2"}:
        fail(f"프롬프트가 context-912-v2가 아닙니다: {link['프롬프트'].unique()}")
    if not link["순번"].between(1, 912).all() or link.groupby("comment_id")["순번"].nunique().max() != 1:
        fail("순번 1–912가 댓글과 맞지 않습니다.")
    if not (link.groupby("comment_id")["대표"].sum() == 1).all():
        fail("대표 연결이 댓글당 하나가 아닙니다.")
    key = link["묶음"].astype(str) + "|" + link["연결순"].astype(str)
    if key.duplicated().any():
        fail("묶음+연결순이 고유하지 않습니다.")
    meta_cols = ["comment_id", "post_id", "account_id", "영상제목", "댓글원문"]
    meta = entered[meta_cols].rename(columns={"post_id": "post_id_입력", "account_id": "account_id"})
    df = link.merge(meta, on="comment_id", how="left")
    if df["account_id"].isna().any() or df["post_id_입력"].isna().any():
        fail("입력 912와 연결이 맞지 않습니다.")
    if not (df["post_id"] == df["post_id_입력"]).all():
        fail("연결의 post_id와 입력의 post_id가 다릅니다.")
    video_ids = videos[["post_id", "account_id"]].rename(columns={"account_id": "account_id_영상"})
    df = df.merge(video_ids, on="post_id", how="left")
    mismatch = int((df["account_id"] != df["account_id_영상"]).sum())
    if mismatch:
        fail(f"입력 채널과 영상 채널이 다른 연결이 {mismatch}행입니다.")
    if not set(df["post_id"]).issubset(set(videos["post_id"])):
        fail("연결 영상이 A 영상 밖에 있습니다.")
    rep = df[df["대표"] == 1]
    level_comment = {lv: int(df.loc[df["호감근거_수준"].eq(lv), "comment_id"].nunique()) for lv in LEVELS}
    level_link = {lv: int(df["호감근거_수준"].eq(lv).sum()) for lv in LEVELS}
    if level_comment["직접 밝힌 이유"] != 299 or level_comment["구체적 긍정 평가"] != 416 or level_comment["포괄적 호감"] != 338:
        fail(f"수준별 고유 댓글이 다릅니다: {level_comment}")
    if level_link["직접 밝힌 이유"] != 317 or level_link["구체적 긍정 평가"] != 515 or level_link["포괄적 호감"] != 426:
        fail(f"수준별 연결 행이 다릅니다: {level_link}")
    rep_reason = int(rep["호감근거_수준"].eq("직접 밝힌 이유").sum())
    rep_spec = int(rep["호감근거_수준"].eq("구체적 긍정 평가").sum())
    if rep_reason != 284 or rep_spec != 356 or len(rep) != 912:
        fail(f"대표 판정이 다릅니다: 이유 {rep_reason}, 구체 {rep_spec}, 행 {len(rep)}")
    both_levels = int((df.groupby("comment_id")["호감근거_수준"].nunique() >= 2).sum())
    if both_levels != 278:
        fail(f"여러 수준에 들어간 댓글이 278이 아닙니다: {both_levels}")
    ani_comments = df.drop_duplicates("comment_id")
    ani_n = int((ani_comments["account_id"] == ANIBOX).sum())
    if ani_n != 331 or ani_comments["post_id"].nunique() != 507 or ani_comments["account_id"].nunique() != 186:
        fail(
            f"912 범위가 다릅니다: AniBox {ani_n}, 영상 {ani_comments['post_id'].nunique()}, 채널 {ani_comments['account_id'].nunique()}"
        )
    df["매력"] = df.apply(charm.assign, axis=1)
    df["표시대상"] = np.where(df["평가대상"].eq("특정 캐릭터"), df["대상_상세"], df["평가대상"])
    detail = aggregate_charm(df)
    published = pd.read_csv(ANALYSIS / "A_호감근거_912" / "05_세부매력.csv", encoding="utf-8-sig")
    compare(
        "세부매력",
        detail,
        published,
        ["평가대상_구분", "평가_대상", "큰_범주", "구체적_매력"],
        ["직접_이유_댓글", "구체적_긍정_댓글", "합집합_댓글", "영상", "채널", "애니박스_댓글", "그외_댓글", "그외_채널"],
    )
    category = aggregate_category(df)
    published_cat = pd.read_csv(ANALYSIS / "A_호감근거_912" / "02_요약_캐릭터매력.csv", encoding="utf-8-sig")
    compare(
        "캐릭터매력",
        category,
        published_cat,
        ["대상_상세", "특징_범주"],
        ["직접_이유_댓글", "구체적_긍정_댓글", "합집합_댓글", "연결행", "영상", "채널", "애니박스_댓글", "그외_댓글", "그외_채널"],
    )
    same_cell = df[df["매력"].notna()].groupby(["comment_id", "표시대상", "매력"])["호감근거_수준"].nunique()
    overlap = int((same_cell >= 2).sum())
    feature = df[df["호감근거_수준"].isin(LEVELS[:2])].groupby(
        ["comment_id", "평가대상", "구체적_특징"], dropna=False
    )["호감근거_수준"].nunique()
    print(f"같은 댓글·대상·매력에 이유와 구체가 함께 있는 칸 {overlap}")
    print(f"같은 댓글·대상·구체적 특징에 이유와 구체가 함께 있는 칸 {int((feature >= 2).sum())}")
    interest = df["보조_간접관심"].fillna("").astype(str).str.strip()
    interest = interest.mask(interest.isin(["", "nan"]))
    print("보조_간접관심 값")
    print(interest.value_counts(dropna=False).head(20).to_string())
    context_out = context[
        ["comment_id", "post_id", "순번", "가장_구체적_근거", "평가대상", "프롬프트"]
    ].rename(columns={"가장_구체적_근거": "대표근거", "평가대상": "대표대상"})
    # 댓글 판정 파일의 평가대상은 대표 연결의 대상이다. 대표 행과 맞는지 확인한다.
    rep_check = rep[["comment_id", "호감근거_수준", "평가대상"]].merge(context_out, on="comment_id")
    if not (rep_check["호감근거_수준"] == rep_check["대표근거"]).all():
        differ = int((rep_check["호감근거_수준"] != rep_check["대표근거"]).sum())
        print(f"대표 연결과 가장_구체적_근거가 다른 댓글 {differ}건. 문맥 표에는 댓글 판정의 대표 근거를 둡니다.")
    link_out = pd.DataFrame(
        {
            "연결키": key,
            "comment_id": df["comment_id"],
            "post_id": df["post_id"],
            "account_id": df["account_id"],
            "채널구분": df["account_id"].map(channel_label),
            "평가대상": df["평가대상"],
            "대상_상세": blank_text(df["대상_상세"]),
            "표시대상": df["표시대상"],
            "평가_방향": df["평가_방향"],
            "호감근거_수준": df["호감근거_수준"],
            "특징_범주": blank_text(df["특징_범주"]),
            "구체적_특징": blank_text(df["구체적_특징"]),
            "매력": df["매력"],
            "매력집계": np.where(df["매력"].notna(), "포함", "제외"),
            "근거문구": blank_text(df["근거문구"]),
            "댓글발췌": df["댓글원문"].map(excerpt),
            "발췌표시": np.where(df["댓글원문"].map(lambda text: len(" ".join(str(text).split())) > 240 if isinstance(text, str) else False), "앞부분 발췌", "이 길이의 댓글"),
            "댓글원문": blank_text(df["댓글원문"]),
            "영상제목": blank_text(df["영상제목"]),
            "대표": df["대표"].astype("Int64"),
            "비고": blank_text(df["비고"]),
            "보조_간접관심": interest,
        }
    )
    link_out = display_rank(link_out)
    return context_out, link_out


def static_tables() -> None:
    title = pd.read_csv(ANALYSIS / "A_키워드" / "02_제목_키워드.csv", encoding="utf-8-sig")
    body = title[title["단위"].eq("제목본문")].copy()
    theme = body[body["종류"].eq("소재")].sort_values(["출현영상수", "키워드"], ascending=[False, True]).head(10)
    theme = theme.assign(위치="제목 본문", 자료="고정 집계")
    phrase_names = ["가챠깡", "극장판", "인형뽑기", "택배깡", "갖고싶다", "보고싶다"]
    phrase_src = pd.read_csv(ANALYSIS / "A_키워드" / "02_제목_구절.csv", encoding="utf-8-sig")
    phrase = phrase_src[phrase_src["키워드"].isin(phrase_names) & phrase_src["단위"].eq("제목본문")].copy()
    if len(phrase) != len(phrase_names):
        fail(f"제목 구절 일부가 없습니다: {sorted(set(phrase_names) - set(phrase['키워드']))}")
    phrase = phrase.assign(위치="제목 구절", 자료="고정 집계")
    names = body[body["종류"].isin(["작품·캐릭터_모호", "캐릭터", "문맥의존"])].sort_values(
        ["출현영상수", "키워드"], ascending=[False, True]
    ).head(12)
    names = names.assign(위치="제목 본문", 자료="고정 집계")
    tags = pd.read_csv(ANALYSIS / "A_키워드" / "02_제목_해시태그.csv", encoding="utf-8-sig")
    tags = tags.sort_values(["출현영상수", "키워드"], ascending=[False, True]).head(8).copy()
    tags["위치"] = "해시태그"
    tags["자료"] = "고정 집계"
    cols = ["키워드", "종류", "위치", "총출현횟수", "출현영상수", "출현영상비율", "출현채널수", "출현채널비율", "분모_영상", "분모_채널", "주의", "자료"]
    theme_out = pd.concat([theme, phrase], ignore_index=True)
    for frame in (theme_out, names, tags):
        if "주의" not in frame.columns:
            frame["주의"] = pd.NA
        frame["주의"] = blank_text(frame["주의"])
    write_csv(theme_out[cols].reset_index(drop=True).assign(정렬=lambda d: np.arange(1, len(d) + 1)), "제목소재.csv")
    write_csv(names[cols].reset_index(drop=True).assign(정렬=lambda d: np.arange(1, len(d) + 1)), "제목표기.csv")
    tag_cols = cols + ["분모_해시태그있는영상", "출현영상비율_해시태그있는영상"]
    write_csv(tags[tag_cols].reset_index(drop=True).assign(정렬=lambda d: np.arange(1, len(d) + 1)), "제목해시태그.csv")
    if int(theme.loc[theme["키워드"].eq("브이로그"), "출현영상수"].iloc[0]) != 410:
        fail("브이로그 출현 영상 수가 410이 아닙니다.")

    mention = pd.read_csv(ANALYSIS / "A_캐릭터반응" / "02_언급량.csv", encoding="utf-8-sig")
    usagi = mention[mention["캐릭터"].eq("우사기")].iloc[0]
    if int(usagi["한국어혼합"]) != 4073 or int(usagi["영상"]) != 960 or int(usagi["채널"]) != 376:
        fail("우사기 언급량 기존 값이 다릅니다.")
    chi = mention[mention["캐릭터"].eq("치이카와")].iloc[0]
    if int(chi["한국어혼합"]) != 7263 or int(chi["작품캐릭터불명확"]) != 6952 or int(chi["개인_또는_캐릭터"]) != 311:
        fail("치이카와 언급 구분이 기존 값과 다릅니다.")
    mention_out = mention[
        ["캐릭터", "종류", "한국어혼합", "영상", "채널", "개인_또는_캐릭터", "작품캐릭터불명확", "판단불가_이름만", "외국어_언급"]
    ].copy()
    mention_out["자료"] = "고정 집계"
    mention_out["분모설명"] = "광고를 뺀 한국어·혼합 댓글. 이름만 있는 판단 불가 댓글은 한국어혼합에 넣지 않음"
    mention_out = mention_out.sort_values(["종류", "한국어혼합"], ascending=[True, False])
    write_csv(mention_out, "댓글언급.csv")

    words = pd.read_csv(ANALYSIS / "A_키워드" / "03_댓글_키워드.csv", encoding="utf-8-sig")
    evals = words[
        words["집단"].eq("주요해석") & words["범위"].eq("전체") & words["종류"].eq("평가")
    ].sort_values(["언급댓글수", "키워드"], ascending=[False, True]).head(8)
    cute = evals[evals["키워드"].eq("귀엽다")].iloc[0]
    if int(cute["언급댓글수"]) != 10753 or int(cute["분모_댓글"]) != 23624:
        fail("귀엽다 집계가 기존 값과 다릅니다.")
    eval_out = evals[
        ["키워드", "종류", "언급댓글수", "언급댓글비율", "출현영상수", "출현채널수", "분모_댓글", "분모_영상", "분모_채널", "주의"]
    ].copy()
    eval_out["주의"] = blank_text(eval_out["주의"])
    eval_out["자료"] = "고정 집계"
    eval_out["분모설명"] = "주요 해석 집단. 포함 규칙의 영향이 있으므로 전체 팬의 호감 비율이 아님"
    write_csv(eval_out.reset_index(drop=True).assign(정렬=lambda d: np.arange(1, len(d) + 1)), "댓글평가.csv")

    status = pd.read_csv(ANALYSIS / "A_호감근거_912" / "01_요약_판정현황.csv", encoding="utf-8-sig")
    keep_targets = [
        "작품 전체·스토리·세계관",
        "캐릭터 관계·복수 캐릭터",
        "캐릭터 음성·더빙",
        "굿즈·상품",
        "성우·커버 가수",
        "제작자·편집",
        "특정 캐릭터",
        "작품·캐릭터 불명확",
        "전체",
    ]
    status_out = status[
        status["집계단위"].eq("고유댓글") & status["평가대상"].isin(keep_targets)
    ][
        ["집계단위", "평가대상", "수", "영상", "채널", "직접 밝힌 이유", "구체적 긍정 평가", "포괄적 호감", "호감 근거 없음"]
    ].copy()
    status_out["자료"] = "고정 집계"
    status_out["설명"] = "연결 전체의 고유 댓글. 수준이 겹치면 칸마다 다시 센다. 포괄을 포함한다."
    write_csv(status_out, "판정현황_고정.csv")


def narrative() -> None:
    findings = pd.DataFrame(
        [
            {
                "구분": "발견",
                "화면": "캐릭터 관계·복수 캐릭터",
                "짧은문장": "우정·함께 있음 11댓글(이유 8, 영상 10, 채널 8). 탐색적으로 확인된 매력이다.",
                "상세문장": "우정·함께 있음은 11댓글(이유 8, 영상 10, 채널 8)이다. 작품 전체와 관계의 표본은 작다.",
            },
            {
                "구분": "발견",
                "화면": "작품 전체·스토리·세계관",
                "짧은문장": "귀여움과 무거운 이야기의 대비는 이유 4건, 영상 4, 채널 4, AniBox 0. 탐색적 확인이다.",
                "상세문장": "귀여움과 무거운 이야기의 대비는 이유 4건, 영상 4개, 채널 4개, AniBox 0건이다. 작은 표본이다.",
            },
            {
                "구분": "발견",
                "화면": "캐릭터 음성·더빙",
                "짧은문장": "한국·일본 더빙 비교 15댓글(AniBox 밖 13). 목소리로 입덕·반함 5댓글은 모두 AniBox 밖이다.",
                "상세문장": "한국·일본 더빙 비교는 15댓글이고 AniBox 밖이 13건이다. 목소리 때문에 입덕·반함으로 묶인 5댓글은 모두 AniBox 밖이다. 성우 본인 칭찬 25댓글은 이 영역과 별도다.",
            },
            {
                "구분": "제안",
                "화면": "캐릭터 음성·더빙",
                "짧은문장": "성우 이름을 내세울 때와 캐릭터 목소리만 말할 때 대상이 갈리는지는 확인되지 않았다.",
                "상세문장": "성우 이름을 내세울 때와 캐릭터 목소리만 비교할 때 댓글의 평가 대상이 갈리는지는 확인되지 않았다. 입덕이라고 적은 5건은 효과의 증거가 아니다.",
            },
            {
                "구분": "발견",
                "화면": "굿즈·상품",
                "짧은문장": "크기·비율 7댓글, 채널 3곳, AniBox 0. 구매 경험과 구매 의향은 다른 종류다.",
                "상세문장": "굿즈의 크기·비율은 7댓글·채널 3개·AniBox 0이다. 가격이 안 귀엽다는 혼합, 모으고 싶다는 의향, 이미 가지고 있다는 경험은 서로 다른 종류다.",
            },
            {
                "구분": "제안",
                "화면": "굿즈·상품",
                "짧은문장": "크기와 파츠 중 어디가 디자인 이유와 함께 보이는지는 확인되지 않았다.",
                "상세문장": "크기 클로즈업과 파츠 클로즈업 중 어디가 디자인 이유 댓글과 같이 나타나는지는 확인되지 않았다. 효과나 매출은 검증되지 않았다.",
            },
            {
                "구분": "발견",
                "화면": "캐릭터",
                "짧은문장": "우사기 행동 52댓글. 그 안은 몸짓 16, 먹는 모습 10, 춤 6. 몸짓의 이유는 1건이다.",
                "상세문장": "우사기 행동의 합집합은 52댓글이다. 그 안은 뛰거나 특정 몸짓 16, 먹는 모습 10, 춤·율동 6이다. 몸짓 16건 중 이유는 1건이고 AniBox가 14건, 한 영상이 5건이다.",
            },
            {
                "구분": "발견",
                "화면": "캐릭터",
                "짧은문장": "치이카와 성격 22댓글 중 이유 14. 배려·나눔 8(이유 7), 용기 8(이유 5).",
                "상세문장": "치이카와 성격 합집합 22댓글 중 이유는 14건이다. 친구를 위한 배려·나눔은 8댓글(이유 7), 겁이 있어도 나서는 용기는 8댓글(이유 5)이다.",
            },
            {
                "구분": "발견",
                "화면": "캐릭터",
                "짧은문장": "하치와레 착함·다정 7댓글. 모몽가 표독은 이유 4건, 꼬리·귀·털은 6댓글·채널 6곳.",
                "상세문장": "하치와레의 착함·다정은 7댓글(영상 7, 채널 5)이다. 모몽가의 표독하거나 자기중심적은 이유 4건이고, 꼬리·귀·털은 6댓글·채널 6개다.",
            },
            {
                "구분": "제안",
                "화면": "캐릭터",
                "짧은문장": "같은 몸짓·배려·용기 문장이 다른 채널에서도 늘어나는지는 확인되지 않았다.",
                "상세문장": "먹는 장면과 뛰는 장면에 구체적 긍정이 붙고 이유 문장은 적다. 같은 몸짓을 다른 채널의 장면에 붙였을 때 이유 문장이 늘어나는지는 확인되지 않았다. 배려와 용기를 카피로 썼을 때 AniBox 밖에서도 같은 이유가 쓰이는지도 확인되지 않았다.",
            },
            {
                "구분": "제안",
                "화면": "캐릭터",
                "짧은문장": "모몽가의 꼬리와 표독을 같이 보여줄 때의 반응 차이는 확인되지 않았다.",
                "상세문장": "꼬리와 표독을 같이 보여줄 때 긍정 이유와 거부 댓글이 어떻게 갈리는지는 확인되지 않았다. 귀여운 겉과 다른 속은 2건이라 그 문장만으로 캠페인을 말하기에는 적다.",
            },
        ]
    )
    findings.insert(0, "순번", np.arange(1, len(findings) + 1))
    findings["자료"] = "보고서 문장. 슬라이서로 다시 계산되지 않음. 제안은 효과나 매출이 검증된 결과가 아님"
    write_csv(findings, "발견가설.csv")
    write_csv(
        pd.DataFrame(
            [
                {"영역명": "캐릭터 관계·복수 캐릭터", "짧은이름": "관계", "정렬": 1},
                {"영역명": "작품 전체·스토리·세계관", "짧은이름": "세계관·스토리", "정렬": 2},
                {"영역명": "캐릭터 음성·더빙", "짧은이름": "음성·더빙", "정렬": 3},
                {"영역명": "굿즈·상품", "짧은이름": "굿즈", "정렬": 4},
            ]
        ),
        "영역.csv",
    )
    write_csv(
        pd.DataFrame(
            [
                {"항목": "분석 범위", "내용": "912건은 전체 67,891건 중 규칙으로 고른 특징·이유 후보를 문맥 분석한 결과(context-912-v2)다. 연결은 1,442행이다."},
                {"항목": "채널 수", "내용": "account_id가 비어 있는 영상 8편은 채널이 아니다. 빈 값을 채널 1개로 세지 않으면 2,949개다."},
                {"항목": "조회수", "내용": "2026-10-26~27에 수집한 누적 조회수다. 한국에서 발생한 조회수가 아니고, 연간 성장률은 만들지 않는다."},
                {"항목": "언급과 호감", "내용": "언급량은 선호도 순위가 아니다. 귀엽다 45.5%는 주요 해석 집단 23,624건 안의 포함 비율이다."},
                {"항목": "매력 집계", "내용": "본문 매력은 긍정 방향의 직접 밝힌 이유 또는 구체적 긍정 평가이고, 같은 댓글은 한 번만 센다. 특징을 특정하지 않은 항목은 상세조회에 둔다."},
                {"항목": "AniBox", "내용": "기본 분석에 AniBox가 포함된다. 이 페이지의 채널 범위로 포함과 제외를 다시 계산할 수 있다."},
            ]
        ),
        "한계.csv",
    )
    write_csv(pd.DataFrame({"구분": ["보고서"]}), "안내.csv")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    charm = load_charm()
    videos = build_videos()
    comments = build_comments(videos)
    context, links = build_judgement(videos, charm)
    write_csv(videos, "영상.csv")
    write_csv(comments, "댓글.csv")
    write_csv(context, "문맥.csv")
    write_csv(links, "연결.csv")
    static_tables()
    narrative()
    included = int(links["매력집계"].eq("포함").sum())
    print(f"매력 포함 연결 {included:,}행 / 전체 {len(links):,}행")
    print("검증 통과")


if __name__ == "__main__":
    sys.exit(main())
