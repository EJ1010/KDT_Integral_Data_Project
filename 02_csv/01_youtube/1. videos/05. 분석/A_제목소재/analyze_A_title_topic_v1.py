# -*- coding: utf-8 -*-
"""제목 본문의 소재 언급과 영상 참여지표. 원본 CSV는 읽기만 한다."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy import stats

SRC = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\02. cleaning\2. 제목분류"
    r"\youtube_total_cleaning_classified_A.csv"
)
MENTION = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_제목참여\01_영상_언급.csv"
)
KW_PATH = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_키워드\analyze_A_keywords_v1.py"
)
OUT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_제목소재"
)
ANIBOX = "UCBTSkFNWmoOkBeZwANcbiIA"
MIN_THEME = 140
MIN_COMBO = 20
MIN_STRATA = 10
NAVY, GRAY = "#3d6f8a", "#6e737a"
# 참여지표를 보기 전에 고정한 순서. 앞 다섯은 분석 요청의 예시다.
THEMES = [
    "가챠", "굿즈", "언박싱", "극장판", "브이로그",
    "가챠깡", "오타쿠", "피규어", "인형", "팝업", "콜라보",
    "리뷰", "토벌", "인형뽑기", "택배깡",
]
PUBLISHED = {
    "가챠": 354, "굿즈": 285, "언박싱": 281, "극장판": 155, "브이로그": 410,
    "가챠깡": 338, "오타쿠": 303, "피규어": 291, "인형": 247, "팝업": 195,
    "콜라보": 195, "리뷰": 164, "토벌": 151, "인형뽑기": 145, "택배깡": 140,
}
CHARS = ["우사기", "하치와레", "모몽가", "라코", "쿠리만쥬", "시사", "카니", "갑옷씨"]
METRICS = [("view_count", "조회수"), ("like_count", "좋아요 수"), ("comment_count", "댓글 수")]
RATES = [("like_rate", "좋아요율"), ("comment_rate", "댓글률")]
PRIMARY = [lab for _, lab in METRICS + RATES]
DUR_RE = __import__("re").compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)
EN_EXTRA = {
    "vlog": __import__("re").compile(r"vlog", __import__("re").I),
    "unboxing": __import__("re").compile(r"unboxing", __import__("re").I),
    "gacha": __import__("re").compile(r"gacha|ガチャ", __import__("re").I),
}
BIN_ORDER = [
    "60초 이하",
    "60초 초과–180초 이하",
    "180초 초과–600초 이하",
    "600초 초과–1,200초 이하",
    "1,200초 초과",
    "변환 불가·결측",
]


def load_kw():
    spec = importlib.util.spec_from_file_location("kw_v1", KW_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_duration_seconds(value) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().upper()
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


def bh(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(q, 0, 1)
    return out


def summarize(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return {"유효수": 0, "중앙값": np.nan, "사분위범위": np.nan, "Q1": np.nan, "Q3": np.nan}
    q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
    return {
        "유효수": int(len(s)),
        "중앙값": float(med),
        "사분위범위": float(q3 - q1),
        "Q1": float(q1),
        "Q3": float(q3),
    }


def spearman(flag: pd.Series, values: pd.Series) -> tuple[float, float, int]:
    ok = flag.notna() & values.notna()
    x = flag[ok].astype(float)
    y = values[ok].astype(float)
    n = int(ok.sum())
    if n < 3 or x.nunique() < 2 or y.nunique() < 2:
        return np.nan, np.nan, n
    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p), n


def partial_spearman(df: pd.DataFrame, flag_col: str, y_col: str) -> tuple[float, float, int]:
    """순위 잔차 상관. 연도, 길이, AniBox, 경과일을 선형으로 맞춘다."""
    need = [flag_col, y_col, "year", "duration_sec", "anibox", "elapsed_days"]
    sub = df.dropna(subset=need)
    n = int(len(sub))
    if n < 30:
        return np.nan, np.nan, n
    x = sub[flag_col].to_numpy(float)
    y = sub[y_col].to_numpy(float)
    if len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return np.nan, np.nan, n
    dummies = pd.get_dummies(sub["year"].astype(int), drop_first=True)
    cov = np.column_stack([
        np.ones(n),
        np.log1p(sub["duration_sec"].to_numpy(float)),
        sub["anibox"].to_numpy(float),
        np.log1p(sub["elapsed_days"].to_numpy(float)),
        dummies.to_numpy(float),
    ])
    rx = pd.Series(x).rank(method="average").to_numpy(float)
    ry = pd.Series(y).rank(method="average").to_numpy(float)

    def resid(v: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(cov, v, rcond=None)
        return v - cov @ beta

    xr, yr = resid(rx), resid(ry)
    if np.std(xr) < 1e-8 or np.std(yr) < 1e-8:
        return np.nan, np.nan, n
    rho, p = stats.pearsonr(xr, yr)
    return float(rho), float(p), n


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rho_row(name, lab, n_m, rho, p, n, limited, scope) -> dict:
    ok = (not limited) and np.isfinite(rho)
    return {
        "소재": name, "지표": lab, "언급영상수": n_m, "유효표본": n,
        "스피어만": rho if ok else np.nan,
        "p": p if ok else np.nan,
        "표시": "계산" if ok else "분석 제한",
        "범위": scope,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    kw = load_kw()
    kiwi = kw.build_kiwi()

    raw = pd.read_csv(SRC, encoding="utf-8-sig")
    if raw["post_id"].duplicated().any() or raw["post_id"].isna().any() or len(raw) != 6462:
        raise SystemExit("영상 ID 또는 행 수가 기대와 다름")
    mention = pd.read_csv(MENTION, encoding="utf-8-sig")
    flag_cols = [f"언급_{c}" for c in CHARS]
    if set(mention["post_id"]) != set(raw["post_id"]) or mention["post_id"].duplicated().any():
        raise SystemExit("캐릭터 언급 파일의 영상 ID가 원본과 다름")

    work = raw.copy()
    title_src = work["full_title"].where(work["full_title"].notna(), work["post_title"]).fillna("")
    work["제목원문"] = title_src
    bodies, tags = [], []
    for text in title_src:
        body, tag = kw.split_hash(kw.clean_text(text))
        bodies.append(body)
        tags.append(tag)
    work["제목본문"] = bodies
    work["해시태그"] = [" ".join(t) for t in tags]
    for col in ["view_count", "like_count", "comment_count"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work["like_rate"] = np.where(
        work["like_count"].notna() & work["view_count"].notna() & (work["view_count"] > 0),
        work["like_count"] / work["view_count"],
        np.nan,
    )
    work["comment_rate"] = np.where(
        work["comment_count"].notna() & work["view_count"].notna() & (work["view_count"] > 0),
        work["comment_count"] / work["view_count"],
        np.nan,
    )
    work["created_utc"] = pd.to_datetime(work["created_at"], utc=True, errors="coerce")
    work["collected_utc"] = pd.to_datetime(work["collected_at"], utc=True, errors="coerce")
    created_ok = work["created_at"].fillna("").astype(str).str.contains(r"Z$|[+-]\d{2}:?\d{2}$", regex=True)
    collected_ok = work["collected_at"].fillna("").astype(str).str.contains(r"Z$|[+-]\d{2}:?\d{2}$", regex=True)
    elapsed = (work["collected_utc"] - work["created_utc"]).dt.total_seconds() / 86400
    work["elapsed_days"] = elapsed.where(created_ok & collected_ok)
    work["year"] = work["created_utc"].dt.tz_convert("Asia/Seoul").dt.year.where(created_ok)
    work["duration_sec"] = work["duration"].map(parse_duration_seconds)
    work["길이구간"] = work["duration_sec"].map(duration_bin)
    work["anibox"] = (work["account_id"] == ANIBOX).astype(int)
    work["views_per_day"] = np.where(
        work["elapsed_days"].notna() & (work["elapsed_days"] > 0) & work["view_count"].notna(),
        work["view_count"] / work["elapsed_days"],
        np.nan,
    )
    ch = mention.set_index("post_id")[flag_cols]
    work = work.merge(ch, left_on="post_id", right_index=True, how="left", validate="one_to_one")

    phrase_res = dict(kw.PHRASE_RES)
    found_list = [kw.extract(body, kiwi) if body else {} for body in work["제목본문"]]
    hash_only_rows = []
    en_rows = []
    examples = []
    for name in THEMES:
        body_hit = [int(name in found) for found in found_list]
        tag_only = 0
        for hit, body, tag in zip(body_hit, work["제목본문"], tags):
            tag_text = " ".join(tag)
            in_tag = bool(phrase_res[name].search(tag_text)) if name in phrase_res else name in tag
            if in_tag and not hit:
                tag_only += 1
            if hit and sum(e["소재"] == name for e in examples) < 5:
                examples.append({"소재": name, "제목본문": body})
        work[f"소재_{name}"] = body_hit
        hash_only_rows.append({"소재": name, "본문없음_해시태그만": tag_only, "키워드보고서_영상수": PUBLISHED[name], "다시센_영상수": int(sum(body_hit))})
    en_pair = {"vlog": "브이로그", "unboxing": "언박싱", "gacha": "가챠"}
    for label, cre in EN_EXTRA.items():
        hit = work["제목본문"].map(lambda body: bool(cre.search(body)))
        korean = work[f"소재_{en_pair[label]}"] == 1
        en_rows.append({
            "표기": label,
            "제목본문_영상수": int(hit.sum()),
            "한글도_있음": int((hit & korean).sum()),
            "한글없음": int((hit & ~korean).sum()),
            "처리": "한글 소재와 합치지 않음",
        })
    check = pd.DataFrame(hash_only_rows)
    if not (check["다시센_영상수"] == check["키워드보고서_영상수"]).all():
        print(check.to_string(index=False))
        raise SystemExit("소재 영상 수가 키워드 보고서와 다름")
    check.to_csv(OUT / "00_해시태그만.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(en_rows).to_csv(OUT / "00_미포함영문.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(examples).to_csv(OUT / "00_소재예시.csv", index=False, encoding="utf-8-sig")

    pair_rows = []
    flags = np.column_stack([work[f"소재_{n}"].to_numpy() for n in THEMES])
    for i, a in enumerate(THEMES):
        for b in THEMES[i + 1:]:
            both = int(((work[f"소재_{a}"] == 1) & (work[f"소재_{b}"] == 1)).sum())
            pair_rows.append({"소재A": a, "소재B": b, "동시언급": both})
    pd.DataFrame(pair_rows).sort_values("동시언급", ascending=False).to_csv(
        OUT / "04_중복.csv", index=False, encoding="utf-8-sig"
    )
    n_multi = int((flags.sum(axis=1) >= 2).sum())
    n_any = int((flags.sum(axis=1) >= 1).sum())

    comp_rows, rho_rows = [], []
    for name in THEMES:
        flag = work[f"소재_{name}"]
        n_m = int(flag.sum())
        limited = n_m < MIN_THEME
        for label, bit in (("언급 있음", 1), ("언급 없음", 0)):
            sub = work.loc[flag == bit]
            base = {"소재": name, "집단": label, "영상수": int(len(sub)), "AniBox영상수": int(sub["anibox"].sum())}
            for col, lab in METRICS + RATES:
                comp_rows.append({**base, "지표": lab, **summarize(sub[col])})
        for col, lab in METRICS + RATES + [("views_per_day", "일평균 누적조회수")]:
            rho, p, n = spearman(flag, work[col])
            rho_rows.append(rho_row(name, lab, n_m, rho, p, n, limited, "전체"))
            if limited:
                continue
            ex = work.loc[work["anibox"] == 0]
            rho_x, p_x, n_x = spearman(ex[f"소재_{name}"], ex[col])
            rho_rows.append(rho_row(name, lab, int(ex[f"소재_{name}"].sum()), rho_x, p_x, n_x, False, "AniBox제외"))
            if lab == "일평균 누적조회수":
                continue
            rho_a, p_a, n_a = partial_spearman(work, f"소재_{name}", col)
            rho_rows.append(rho_row(name, lab, n_m, rho_a, p_a, n_a, False, "조정"))

    comp = pd.DataFrame(comp_rows)
    rho = pd.DataFrame(rho_rows)
    primary = rho[(rho["범위"] == "전체") & (rho["지표"].isin(PRIMARY))].copy()
    testable = primary["표시"].eq("계산") & primary["p"].notna()
    primary["FDR_q"] = np.nan
    if testable.any():
        primary.loc[testable, "FDR_q"] = bh(primary.loc[testable, "p"].to_numpy())
    rho = rho.merge(primary[["소재", "지표", "범위", "FDR_q"]], on=["소재", "지표", "범위"], how="left")
    comp.to_csv(OUT / "02_집단비교.csv", index=False, encoding="utf-8-sig")
    rho.to_csv(OUT / "03_스피어만.csv", index=False, encoding="utf-8-sig")

    cond = []
    ch_n = int(work["account_id"].nunique())
    single_ch = int((work.groupby("account_id").size() == 1).sum())
    cond.append({
        "구분": "채널구성", "소재": "", "조건": "전체", "지표": "",
        "값": ch_n, "값2": single_ch, "언급_유효수": int(len(work)), "비언급_유효수": np.nan,
        "메모": "값=채널수, 값2=영상 1편뿐인 채널수",
    })
    for name in THEMES:
        flag = work[f"소재_{name}"]
        both_ch = 0
        diffs = []
        for _, g in work.groupby("account_id"):
            if (g[f"소재_{name}"] == 1).any() and (g[f"소재_{name}"] == 0).any():
                both_ch += 1
                a = g.loc[g[f"소재_{name}"] == 1, "view_count"].median()
                b = g.loc[g[f"소재_{name}"] == 0, "view_count"].median()
                if pd.notna(a) and pd.notna(b):
                    diffs.append(a - b)
        cond.append({
            "구분": "길이중앙값", "소재": name, "조건": "초", "지표": "영상 길이",
            "값": float(work.loc[flag == 1, "duration_sec"].median()),
            "값2": float(work.loc[flag == 0, "duration_sec"].median()),
            "언급_유효수": int(work.loc[flag == 1, "duration_sec"].notna().sum()),
            "비언급_유효수": int(work.loc[flag == 0, "duration_sec"].notna().sum()),
            "메모": "값=언급 길이 중앙값(초), 값2=비언급",
        })
        cond.append({
            "구분": "경과일중앙값", "소재": name, "조건": "일", "지표": "경과일",
            "값": float(work.loc[flag == 1, "elapsed_days"].median()),
            "값2": float(work.loc[flag == 0, "elapsed_days"].median()),
            "언급_유효수": int(work.loc[flag == 1, "elapsed_days"].notna().sum()),
            "비언급_유효수": int(work.loc[flag == 0, "elapsed_days"].notna().sum()),
            "메모": "값=언급 경과일 중앙값, 값2=비언급. 최근 속도가 아님",
        })
        cond.append({
            "구분": "채널내비교", "소재": name, "조건": "언급과 비언급이 함께 있는 채널",
            "지표": "조회수", "값": both_ch,
            "값2": float(np.median(diffs)) if diffs else np.nan,
            "언급_유효수": int(len(diffs)), "비언급_유효수": np.nan,
            "메모": "값=채널수, 값2=채널별 중앙값 차이의 중앙값(있음-없음)",
        })
        for year, g in work.dropna(subset=["year"]).groupby("year"):
            n1 = int((g[f"소재_{name}"] == 1).sum())
            n0 = int((g[f"소재_{name}"] == 0).sum())
            if n1 < MIN_STRATA or n0 < MIN_STRATA:
                continue
            a = summarize(g.loc[g[f"소재_{name}"] == 1, "view_count"])
            b = summarize(g.loc[g[f"소재_{name}"] == 0, "view_count"])
            cond.append({
                "구분": "연도", "소재": name, "조건": str(int(year)), "지표": "조회수",
                "값": a["중앙값"], "값2": b["중앙값"],
                "언급_유효수": a["유효수"], "비언급_유효수": b["유효수"],
                "메모": "값=언급 중앙값, 값2=비언급 중앙값",
            })
        for dur in BIN_ORDER:
            g = work.loc[work["길이구간"] == dur]
            n1 = int((g[f"소재_{name}"] == 1).sum())
            n0 = int((g[f"소재_{name}"] == 0).sum())
            if n1 < MIN_STRATA or n0 < MIN_STRATA:
                continue
            a = summarize(g.loc[g[f"소재_{name}"] == 1, "view_count"])
            b = summarize(g.loc[g[f"소재_{name}"] == 0, "view_count"])
            cond.append({
                "구분": "길이", "소재": name, "조건": dur, "지표": "조회수",
                "값": a["중앙값"], "값2": b["중앙값"],
                "언급_유효수": a["유효수"], "비언급_유효수": b["유효수"],
                "메모": "값=언급 중앙값, 값2=비언급 중앙값. 60초 이하를 쇼츠로 보지 않음",
            })
    pd.DataFrame(cond).to_csv(OUT / "06_조정확인.csv", index=False, encoding="utf-8-sig")

    combo_rows = []
    for ch_name in CHARS:
        cflag = work[f"언급_{ch_name}"]
        inside = work.loc[cflag == 1]
        for name in THEMES:
            both = inside.loc[inside[f"소재_{name}"] == 1]
            none = inside.loc[inside[f"소재_{name}"] == 0]
            limited = len(both) < MIN_COMBO or len(none) < MIN_COMBO or int(cflag.sum()) < MIN_COMBO
            for col, lab in METRICS + RATES:
                sb, sn = summarize(both[col]), summarize(none[col])
                rho, p, n = (np.nan, np.nan, 0)
                if not limited:
                    rho, p, n = spearman(inside[f"소재_{name}"], inside[col])
                    if not np.isfinite(rho):
                        limited = True
                combo_rows.append({
                    "캐릭터": ch_name, "소재": name, "지표": lab,
                    "캐릭터언급": int(cflag.sum()),
                    "소재있음": int(len(both)), "소재없음": int(len(none)),
                    "있음_유효수": sb["유효수"], "없음_유효수": sn["유효수"],
                    "있음_중앙값": sb["중앙값"] if not limited else np.nan,
                    "없음_중앙값": sn["중앙값"] if not limited else np.nan,
                    "있음_사분위범위": sb["사분위범위"] if not limited else np.nan,
                    "없음_사분위범위": sn["사분위범위"] if not limited else np.nan,
                    "스피어만": rho if not limited else np.nan,
                    "p": p if not limited else np.nan,
                    "유효표본": n if not limited else int(inside[col].notna().sum()),
                    "표시": "분석 제한" if limited else "계산",
                })
    combo = pd.DataFrame(combo_rows)
    calc = combo["표시"].eq("계산") & combo["p"].notna()
    combo["FDR_q"] = np.nan
    if calc.any():
        combo.loc[calc, "FDR_q"] = bh(combo.loc[calc, "p"].to_numpy())
    combo.to_csv(OUT / "05_조합.csv", index=False, encoding="utf-8-sig")

    dur_rows = []
    for dur in BIN_ORDER:
        g = work.loc[work["길이구간"] == dur]
        base = {"길이구간": dur, "영상수": int(len(g))}
        for col, lab in METRICS + RATES:
            dur_rows.append({**base, "지표": lab, **summarize(g[col])})
    rho_d = []
    for col, lab in [("view_count", "조회수"), ("like_rate", "좋아요율"), ("comment_rate", "댓글률")]:
        rho, p, n = spearman(work["duration_sec"], work[col])
        rho_d.append({"지표": lab, "스피어만": rho, "p": p, "유효표본": n, "표시": "계산" if np.isfinite(rho) else "분석 제한"})
    dur_rho = pd.DataFrame(rho_d)
    if dur_rho["p"].notna().any():
        dur_rho["FDR_q"] = bh(dur_rho["p"].to_numpy())
    pd.DataFrame(dur_rows).to_csv(OUT / "07_길이_구간.csv", index=False, encoding="utf-8-sig")
    dur_rho.to_csv(OUT / "07_길이_상관.csv", index=False, encoding="utf-8-sig")

    keep = [
        "post_id", "account_id", "account_name", "제목원문", "제목본문", "해시태그",
        "view_count", "like_count", "comment_count", "like_rate", "comment_rate",
        "year", "elapsed_days", "duration_sec", "길이구간", "anibox", "views_per_day",
    ] + [f"소재_{n}" for n in THEMES] + flag_cols
    work[keep].to_csv(OUT / "01_영상_소재.csv", index=False, encoding="utf-8-sig")

    plot_heat(primary, [m[1] for m in METRICS], "fig_상관계수_기본.png", "제목 소재와 누적 참여지표의 순위상관계수")
    plot_heat(primary, [m[1] for m in RATES], "fig_상관계수_비율.png", "제목 소재와 좋아요율·댓글률의 순위상관계수")
    for col, lab, fname in (
        ("view_count", "조회수", "fig_박스_조회수.png"),
        ("like_count", "좋아요 수", "fig_박스_좋아요.png"),
        ("comment_count", "댓글 수", "fig_박스_댓글.png"),
    ):
        plot_box(work, col, lab, fname)
    drawn = plot_combo(combo)
    plot_duration(work, dur_rho)

    meta = {
        "영상수": int(len(work)),
        "소재하나이상": n_any,
        "소재둘이상": n_multi,
        "조회수유효": int(work["view_count"].notna().sum()),
        "좋아요유효": int(work["like_count"].notna().sum()),
        "댓글유효": int(work["comment_count"].notna().sum()),
        "조회수0": int((work["view_count"] == 0).sum()),
        "경과유효": int(work["elapsed_days"].notna().sum()),
        "anibox": int(work["anibox"].sum()),
        "채널수": ch_n,
        "영상1편채널": single_ch,
        "조합그림": int(drawn),
        "호감비율분석": 0,
    }
    pd.Series(meta).to_csv(OUT / "00_입력요약.csv", encoding="utf-8-sig")
    show = primary[primary["지표"].isin(["조회수", "좋아요 수", "댓글 수"])][
        ["소재", "지표", "언급영상수", "스피어만", "FDR_q", "표시"]
    ]
    print(meta)
    print(show.to_string(index=False))
    print("--- rates ---")
    print(primary[primary["지표"].isin(["좋아요율", "댓글률"])][["소재", "지표", "스피어만", "FDR_q"]].to_string(index=False))
    print("--- duration ---")
    print(dur_rho.to_string(index=False))
    print("combo cells", int((combo["표시"] == "계산").sum()), "drawn", drawn)


def plot_heat(primary: pd.DataFrame, metrics: list[str], fname: str, title: str) -> None:
    sub = primary[primary["지표"].isin(metrics)].copy()
    mat = np.full((len(THEMES), len(metrics)), np.nan)
    notes = []
    valids = []
    for i, name in enumerate(THEMES):
        rows = sub.loc[sub["소재"] == name]
        notes.append(int(rows["언급영상수"].iloc[0]))
        for j, lab in enumerate(metrics):
            row = rows.loc[rows["지표"] == lab].iloc[0]
            valids.append(int(row["유효표본"]))
            if row["표시"] == "계산":
                mat[i, j] = row["스피어만"]
    fig, ax = plt.subplots(figsize=(8.4, 8.8))
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(np.ma.masked_invalid(mat), cmap="RdBu_r", norm=norm, aspect="auto")
    ax.set_xticks(range(len(metrics)), metrics)
    ax.set_yticks(range(len(THEMES)), [f"{name}  ·  언급 {n}" for name, n in zip(THEMES, notes)])
    for i in range(len(THEMES)):
        for j in range(len(metrics)):
            row = sub[(sub["소재"] == THEMES[i]) & (sub["지표"] == metrics[j])].iloc[0]
            if np.isfinite(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.2f}\n{int(row['유효표본']):,}", ha="center", va="center", fontsize=8, color="#1a1a1a")
            else:
                ax.text(j, i, "분석 제한", ha="center", va="center", fontsize=8, color=GRAY)
    ax.set_title(title, loc="left", fontsize=13, pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("-1 ~ 1")
    fig.text(
        0.01, 0.01,
        "칸의 위는 순위상관계수, 아래는 유효 표본 수. 제목 본문만 사용. 수집 시점 누적값. 결측은 0으로 바꾸지 않음. 색 범위는 -1~1.",
        fontsize=8, color="#444",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.08)
    save_fig(fig, fname)


def plot_box(work: pd.DataFrame, col: str, lab: str, fname: str) -> None:
    data, positions, colors = [], [], []
    ymax = 0.0
    for i, name in enumerate(THEMES):
        for bit, color in ((1, NAVY), (0, "#c5ced6")):
            s = work.loc[work[f"소재_{name}"] == bit, col].dropna()
            vals = np.log1p(s.to_numpy(dtype=float))
            data.append(vals)
            positions.append(i * 3 + (0 if bit == 1 else 1))
            colors.append(color)
            if len(vals):
                ymax = max(ymax, float(np.nanpercentile(vals, 95)))
    fig, ax = plt.subplots(figsize=(18.5, 6.4))
    bp = ax.boxplot(
        data, positions=positions, widths=0.72, showfliers=False, patch_artist=True,
        medianprops={"color": "#1a1a1a", "linewidth": 1.2},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor("#333")
    ax.set_xlim(-1, len(THEMES) * 3 - 1)
    ax.set_ylim(0, ymax * 1.18 if ymax else 1)
    ax.set_xticks(
        [i * 3 + 0.5 for i in range(len(THEMES))],
        [f"{name}\n언급 {int((work[f'소재_{name}'] == 1).sum())}" for name in THEMES],
    )
    ax.set_ylabel(f"log1p({lab})")
    ax.set_title(f"제목 본문 소재 언급 여부에 따른 {lab}", loc="left", fontsize=13, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.plot([], [], color=NAVY, linewidth=8, label="언급 있음")
    ax.plot([], [], color="#c5ced6", linewidth=8, label="언급 없음")
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.01, 0.01, "남색이 언급 있음, 회색이 언급 없음. 축은 log1p이고 이상점은 숨김. 검은 선은 중앙값. 같은 그림 안의 축 범위는 하나다.", fontsize=8, color="#444")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.16)
    save_fig(fig, fname)


def plot_combo(combo: pd.DataFrame) -> bool:
    views = combo[combo["지표"] == "조회수"]
    passed = views[views["표시"] == "계산"]
    if passed.empty:
        return False
    chars = [c for c in CHARS if c in set(passed["캐릭터"])]
    themes = [t for t in THEMES if t in set(passed["소재"])]
    fig, axes = plt.subplots(1, 3, figsize=(max(11.2, 3.4 * len(themes) + 3.2), max(4.6, 1.15 * len(chars) + 2.4)), sharey=True)
    for ax, lab in zip(axes, [m[1] for m in METRICS]):
        sub = combo[combo["지표"] == lab]
        mat = np.full((len(chars), len(themes)), np.nan)
        text = [["" for _ in themes] for _ in chars]
        for i, ch_name in enumerate(chars):
            for j, theme in enumerate(themes):
                row = sub[(sub["캐릭터"] == ch_name) & (sub["소재"] == theme)].iloc[0]
                if row["표시"] != "계산":
                    text[i][j] = "분석 제한"
                    continue
                mat[i, j] = np.log1p(row["있음_중앙값"]) if pd.notna(row["있음_중앙값"]) else np.nan
                none_med = row["없음_중앙값"]
                none_txt = f"{none_med:,.0f}" if pd.notna(none_med) else "-"
                text[i][j] = f"{row['있음_중앙값']:,.0f}\nn={int(row['소재있음'])}\n없음 {none_txt}"
        finite = mat[np.isfinite(mat)]
        vmax = float(finite.max()) * 1.45 if len(finite) else 1
        im = ax.imshow(np.ma.masked_invalid(mat), cmap="Blues", vmin=0, vmax=vmax if vmax > 0 else 1, aspect="auto")
        ax.set_xticks(range(len(themes)), themes, rotation=40, ha="right")
        ax.set_yticks(range(len(chars)), chars)
        ax.set_title(lab, loc="left", fontsize=12)
        for i in range(len(chars)):
            for j in range(len(themes)):
                ax.text(j, i, text[i][j], ha="center", va="center", fontsize=7, color="#1a1a1a")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("log1p")
    fig.suptitle("캐릭터 언급 영상 안에서 소재가 같이 적힌 경우의 중앙값", x=0.01, ha="left", fontsize=13)
    fig.text(0.01, 0.01, "칸은 캐릭터와 소재가 모두 있는 영상의 중앙값과 표본 수. 없음은 그 캐릭터는 있고 그 소재는 없는 영상의 중앙값. 두 집단 중 하나가 20편 미만이면 분석 제한. 색은 시너지 효과가 아니다.", fontsize=8, color="#444")
    fig.tight_layout()
    fig.subplots_adjust(top=0.82, bottom=0.22)
    save_fig(fig, "fig_조합_중앙값.png")
    return True


def plot_duration(work: pd.DataFrame, dur_rho: pd.DataFrame) -> None:
    specs = [("view_count", "조회수", True), ("like_rate", "좋아요율", False), ("comment_rate", "댓글률", False)]
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6))
    x = work["duration_sec"]
    for ax, (col, lab, use_log) in zip(axes, specs):
        ok = x.notna() & work[col].notna()
        yy = np.log1p(work.loc[ok, col].to_numpy(float)) if use_log else work.loc[ok, col].to_numpy(float)
        ax.scatter(np.log1p(x[ok].to_numpy(float)), yy, s=8, alpha=0.18, c=NAVY, linewidths=0, rasterized=True)
        if not use_log and len(yy):
            ax.set_ylim(0, float(np.nanpercentile(yy, 99)) * 1.08)
        rho = dur_rho.loc[dur_rho["지표"] == lab, "스피어만"]
        rho_txt = f"{float(rho.iloc[0]):.2f}" if len(rho) and pd.notna(rho.iloc[0]) else "분석 제한"
        ax.set_title(f"{lab}  ·  순위상관계수 {rho_txt}", loc="left", fontsize=11)
        ax.set_xlabel("log1p(영상 길이, 초)")
        ax.set_ylabel(f"log1p({lab})" if use_log else lab)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(linestyle=":", alpha=0.4)
    fig.suptitle("영상 길이와 참여지표", x=0.01, ha="left", fontsize=13)
    fig.text(0.01, 0.01, "길이가 있는 영상만 그렸다. 길이만으로 쇼츠 여부를 정하지 않는다. 조회수는 log1p다. 비율 축은 상위 1%를 잘라 본체가 보이게 했다.", fontsize=8, color="#444")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18, top=0.82)
    save_fig(fig, "fig_길이_산점.png")

    short_bin = {
        "60초 이하": "60초 이하",
        "60초 초과–180초 이하": "60–180초",
        "180초 초과–600초 이하": "180–600초",
        "600초 초과–1,200초 이하": "600–1,200초",
        "1,200초 초과": "1,200초 초과",
    }
    present = [dur for dur in BIN_ORDER if (work["길이구간"] == dur).any()]
    fig, axes = plt.subplots(1, 3, figsize=(14.8, 5.6))
    for ax, (col, lab, use_log) in zip(axes, specs):
        data, ymax = [], 0.0
        labels = []
        for dur in present:
            s = work.loc[work["길이구간"] == dur, col].dropna()
            vals = np.log1p(s.to_numpy(float)) if use_log else s.to_numpy(float)
            data.append(vals if len(vals) else [np.nan])
            labels.append(f"{short_bin[dur]}\nn={len(s)}")
            if len(vals):
                ymax = max(ymax, float(np.nanpercentile(vals, 95)))
        bp = ax.boxplot(data, showfliers=False, patch_artist=True, medianprops={"color": "#1a1a1a", "linewidth": 1.2})
        for patch in bp["boxes"]:
            patch.set_facecolor("#c5d5e0")
            patch.set_edgecolor("#333")
        ax.set_xticks(range(1, len(present) + 1), labels, fontsize=8)
        if use_log:
            ax.set_ylim(0, ymax * 1.18 if ymax else 1)
        ax.set_title(lab, loc="left", fontsize=11)
        ax.set_ylabel(f"log1p({lab})" if use_log else lab)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.suptitle("영상 길이 구간별 참여지표", x=0.01, ha="left", fontsize=13)
    fig.text(0.01, 0.01, "구간 경계는 1차 탐색과 같다. 눈금만 짧게 적었다. 60초 이하는 쇼츠 확정이 아니다. 이상점은 숨겼고, 검은 선은 중앙값이다.", fontsize=8, color="#444")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.30, top=0.82)
    save_fig(fig, "fig_길이_구간.png")


if __name__ == "__main__":
    main()
