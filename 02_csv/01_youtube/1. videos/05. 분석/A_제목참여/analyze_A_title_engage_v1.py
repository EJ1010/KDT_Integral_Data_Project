# -*- coding: utf-8 -*-
"""제목 본문의 캐릭터 언급과 영상 참여지표. 원본 CSV는 읽기만 한다."""
from __future__ import annotations

import re
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
OUT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\05. 분석\A_제목참여"
)
ANIBOX = "UCBTSkFNWmoOkBeZwANcbiIA"
HASH_RE = re.compile(r"[#＃]([^\s#＃]+)")
OPANCHU = re.compile(r"오빤쮸|오판츄|오판추|빤쮸|팬티")
MIN_MENTION = 20
NAVY, RED, GRAY = "#3d6f8a", "#8a3d3d", "#6e737a"
METRICS = [
    ("view_count", "조회수"),
    ("like_count", "좋아요 수"),
    ("comment_count", "댓글 수"),
]
RATES = [
    ("like_rate", "좋아요율"),
    ("comment_rate", "댓글률"),
]
# 사용자 지정 순서. 치이카와(개인)은 구분 불가라 상관계수를 계산하지 않는다.
ORDER = ["우사기", "하치와레", "치이카와(개인)", "라코", "모몽가", "카니", "시사", "쿠리만쥬", "갑옷씨"]
PATTERNS = {
    "우사기": re.compile(r"우사기", re.I),
    "하치와레": re.compile(r"하치\s*와레|하치와래|하찌와레|하츠와레|ハチワレ|hachiware", re.I),
    "모몽가": re.compile(r"모몽가|모몬가|モモンガ|짭\s*몽가|짭몽가|짭\s*모몽가", re.I),
    "라코": re.compile(r"랏코|ラッコ|(?<![가-힣])라코(?![가-힣])|랭커상|랭커", re.I),
    "카니": re.compile(r"(?<![가-힣])카니(?![가-힣])"),
    "시사": re.compile(r"시샤|シーサー|(?<!우레)시사(?!회|점|디테일|프로그램|이슈)"),
    "쿠리만쥬": re.compile(r"쿠리\s*만쥬|쿠리\s*만주|くりまんじゅう", re.I),
    "갑옷씨": re.compile(r"갑옷\s*씨|요로이", re.I),
}
CHI = re.compile(r"치이\s*까?카와|치카와|ちいかわ|chiikawa", re.I)
PERSONAL = re.compile(
    r"치이\s*까?카와(?:가|는|도|만|보다|랑).{0,24}"
    r"(?:작아|작은|얼굴|눈이|손을|손이|입으로|입을|입이|입모양|표정|얘|애가|목소리|성격|울어|울었|우는|울음)"
    r"|(?:작아|작은|얼굴|눈이|표정|울어|울었|우는).{0,12}치이\s*까?카와",
    re.I,
)
DUR_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


def split_hash(text: str) -> tuple[str, list[str]]:
    tags = HASH_RE.findall(text)
    body = re.sub(r"\s+", " ", HASH_RE.sub(" ", text)).strip()
    return body, tags


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


def raco_text(text: str) -> str:
    return re.sub(r"상위\s*랭커", " ", text)


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
    return {"유효수": int(len(s)), "중앙값": float(med), "사분위범위": float(q3 - q1), "Q1": float(q1), "Q3": float(q3)}


def spearman(flag: pd.Series, values: pd.Series) -> tuple[float, float, int]:
    ok = flag.notna() & values.notna()
    x = flag[ok].astype(float)
    y = values[ok].astype(float)
    n = int(ok.sum())
    if n < 3 or x.nunique() < 2 or y.nunique() < 2:
        return np.nan, np.nan, n
    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p), n


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    raw = pd.read_csv(SRC, encoding="utf-8-sig")
    if raw["post_id"].duplicated().any() or raw["post_id"].isna().any():
        raise SystemExit("post_id 중복 또는 결측")
    work = raw.copy()
    title_src = work["full_title"].where(work["full_title"].notna(), work["post_title"]).fillna("")
    split = title_src.map(split_hash)
    work["제목원문"] = title_src
    work["제목본문"] = split.map(lambda x: x[0])
    work["해시태그"] = split.map(lambda x: " ".join(x[1]))
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
    work["anibox"] = (work["account_id"] == ANIBOX).astype(int)
    work["views_per_day"] = np.where(
        work["elapsed_days"].notna() & (work["elapsed_days"] > 0) & work["view_count"].notna(),
        work["view_count"] / work["elapsed_days"],
        np.nan,
    )

    audit = []
    flags = {}
    hash_only = {}
    for name, cre in PATTERNS.items():
        body_hit = []
        tag_hit = []
        for body, tags in zip(work["제목본문"], work["해시태그"]):
            text = raco_text(body) if name == "라코" else body
            hit = bool(cre.search(text))
            if name == "우사기" and hit and OPANCHU.search(body):
                hit = False
                audit.append({"캐릭터": name, "구분": "오빤쮸와 겹쳐 제외", "제목본문": body})
            body_hit.append(int(hit))
            tag_text = tags if name != "라코" else raco_text(tags)
            tag_hit.append(int(bool(cre.search(tag_text)) and not (name == "우사기" and OPANCHU.search(tags))))
        flags[name] = pd.Series(body_hit, index=work.index)
        hash_only[name] = int(((pd.Series(tag_hit) == 1) & (flags[name] == 0)).sum())
    work_flags = pd.DataFrame(flags)
    for name in flags:
        work[f"언급_{name}"] = flags[name]

    # 치이카와 개인 후보. 상관계수에는 넣지 않는다.
    chi_rows = []
    for body in work["제목본문"]:
        if not CHI.search(body):
            continue
        chi_rows.append({"제목본문": body, "개인단서": int(bool(PERSONAL.search(body)))})
    chi = pd.DataFrame(chi_rows)
    chi_n = int(len(chi))
    personal_n = int(chi["개인단서"].sum()) if chi_n else 0
    chi.loc[chi["개인단서"] == 1].to_csv(OUT / "05_치이카와_개인단서.csv", index=False, encoding="utf-8-sig")

    # 라코에서 뺀 상위 랭커, 카니·시사 전수
    for body in work["제목본문"]:
        if re.search(r"상위\s*랭커", body) and not PATTERNS["라코"].search(raco_text(body)):
            audit.append({"캐릭터": "라코", "구분": "상위 랭커라 제외", "제목본문": body})
        if PATTERNS["카니"].search(body):
            audit.append({"캐릭터": "카니", "구분": "전수 확인 후 유지", "제목본문": body})
        if PATTERNS["시사"].search(body):
            audit.append({"캐릭터": "시사", "구분": "전수 확인 후 유지", "제목본문": body})
    pd.DataFrame(audit).to_csv(OUT / "06_오탐점검.csv", index=False, encoding="utf-8-sig")

    id_cols = [
        "post_id", "account_id", "account_name", "제목원문", "제목본문", "해시태그",
        "view_count", "like_count", "comment_count", "like_rate", "comment_rate",
        "year", "elapsed_days", "duration_sec", "anibox", "views_per_day",
    ] + [f"언급_{n}" for n in PATTERNS]
    work[id_cols].to_csv(OUT / "01_영상_언급.csv", index=False, encoding="utf-8-sig")

    comp_rows = []
    rho_rows = []
    for name in [n for n in ORDER if n != "치이카와(개인)"]:
        flag = work[f"언급_{name}"]
        for label, bit in (("언급 있음", 1), ("언급 없음", 0)):
            sub = work.loc[flag == bit]
            base = {"캐릭터": name, "집단": label, "영상수": int(len(sub))}
            for col, lab in METRICS + RATES:
                stat = summarize(sub[col])
                comp_rows.append({**base, "지표": lab, **stat})
        n_m = int(flag.sum())
        limited = n_m < MIN_MENTION
        for col, lab in METRICS + RATES + [("views_per_day", "경과일은 조회수")]:
            rho, p, n = spearman(flag, work[col])
            rho_rows.append({
                "캐릭터": name, "지표": lab, "언급영상수": n_m, "유효표본": n,
                "스피어만": rho if not limited else np.nan,
                "p": p if not limited else np.nan,
                "표시": "분석 제한" if limited or not np.isfinite(rho) else "계산",
                "범위": "전체",
            })
            if limited:
                continue
            ex = work.loc[work["anibox"] == 0]
            rho_x, p_x, n_x = spearman(ex[f"언급_{name}"], ex[col])
            rho_rows.append({
                "캐릭터": name, "지표": lab, "언급영상수": int(ex[f"언급_{name}"].sum()),
                "유효표본": n_x, "스피어만": rho_x, "p": p_x,
                "표시": "계산" if np.isfinite(rho_x) else "분석 제한", "범위": "AniBox제외",
            })
    # 치이카와 행은 계산하지 않고 제한만 남긴다.
    for lab in [x[1] for x in METRICS + RATES]:
        rho_rows.append({
            "캐릭터": "치이카와(개인)", "지표": lab, "언급영상수": 0, "유효표본": 0,
            "스피어만": np.nan, "p": np.nan, "표시": "분석 제한", "범위": "전체",
        })
    comp = pd.DataFrame(comp_rows)
    rho = pd.DataFrame(rho_rows)
    primary = rho[(rho["범위"] == "전체") & (rho["지표"].isin([m[1] for m in METRICS + RATES]))].copy()
    testable = primary["표시"].eq("계산") & primary["p"].notna()
    primary["FDR_q"] = np.nan
    if testable.any():
        primary.loc[testable, "FDR_q"] = bh(primary.loc[testable, "p"].to_numpy())
    comp.to_csv(OUT / "02_집단비교.csv", index=False, encoding="utf-8-sig")
    rho = rho.merge(primary[["캐릭터", "지표", "범위", "FDR_q"]], on=["캐릭터", "지표", "범위"], how="left")
    rho.to_csv(OUT / "03_스피어만.csv", index=False, encoding="utf-8-sig")

    # 연도·길이 조건. 언급 10건 미만인 칸은 적지 않는다.
    cond = []
    for name in [n for n in ORDER if n != "치이카와(개인)"]:
        flag = work[f"언급_{name}"]
        if int(flag.sum()) < MIN_MENTION:
            continue
        for year, g in work.dropna(subset=["year"]).groupby("year"):
            if int((g[f"언급_{name}"] == 1).sum()) < 10 or int((g[f"언급_{name}"] == 0).sum()) < 10:
                continue
            for col, lab in METRICS:
                a = summarize(g.loc[g[f"언급_{name}"] == 1, col])
                b = summarize(g.loc[g[f"언급_{name}"] == 0, col])
                cond.append({
                    "캐릭터": name, "조건": f"연도 {int(year)}", "지표": lab,
                    "언급_중앙값": a["중앙값"], "비언급_중앙값": b["중앙값"],
                    "언급_유효수": a["유효수"], "비언급_유효수": b["유효수"],
                })
        work["길이구간"] = work["duration_sec"].map(
            lambda s: "결측" if pd.isna(s) else ("60초 이하" if s <= 60 else "60초 초과–10분 이하" if s <= 600 else "10분 초과")
        )
        for dur, g in work.groupby("길이구간"):
            if int((g[f"언급_{name}"] == 1).sum()) < 10 or int((g[f"언급_{name}"] == 0).sum()) < 10:
                continue
            a = summarize(g.loc[g[f"언급_{name}"] == 1, "view_count"])
            b = summarize(g.loc[g[f"언급_{name}"] == 0, "view_count"])
            cond.append({
                "캐릭터": name, "조건": f"길이 {dur}", "지표": "조회수",
                "언급_중앙값": a["중앙값"], "비언급_중앙값": b["중앙값"],
                "언급_유효수": a["유효수"], "비언급_유효수": b["유효수"],
            })
    pd.DataFrame(cond).to_csv(OUT / "04_조정확인.csv", index=False, encoding="utf-8-sig")

    hash_note = pd.DataFrame([{"캐릭터": k, "본문없음_해시태그만": v} for k, v in hash_only.items()])
    hash_note.to_csv(OUT / "00_해시태그만.csv", index=False, encoding="utf-8-sig")

    plot_heat(primary, [m[1] for m in METRICS], "fig_상관계수_기본.png", "제목 본문 언급과 누적 참여지표의 순위상관계수")
    plot_heat(primary, [m[1] for m in RATES], "fig_상관계수_비율.png", "제목 본문 언급과 좋아요율·댓글률의 순위상관계수")
    for col, lab, fname in (
        ("view_count", "조회수", "fig_박스_조회수.png"),
        ("like_count", "좋아요 수", "fig_박스_좋아요.png"),
        ("comment_count", "댓글 수", "fig_박스_댓글.png"),
    ):
        plot_box(work, col, lab, fname)

    meta = {
        "영상수": int(len(work)),
        "치이카와본문": chi_n,
        "개인단서": personal_n,
        "조회수유효": int(work["view_count"].notna().sum()),
        "좋아요유효": int(work["like_count"].notna().sum()),
        "댓글유효": int(work["comment_count"].notna().sum()),
        "조회수0": int((work["view_count"] == 0).sum()),
        "경과유효": int(work["elapsed_days"].notna().sum()),
        "anibox": int(work["anibox"].sum()),
    }
    pd.Series(meta).to_csv(OUT / "00_입력요약.csv", encoding="utf-8-sig")
    print(meta)
    print(primary[primary["범위"] == "전체"][["캐릭터", "지표", "언급영상수", "스피어만", "표시", "FDR_q"]].to_string(index=False))


def plot_heat(primary: pd.DataFrame, metrics: list[str], fname: str, title: str) -> None:
    sub = primary[primary["지표"].isin(metrics)].copy()
    mat = np.full((len(ORDER), len(metrics)), np.nan)
    notes = []
    for i, name in enumerate(ORDER):
        n_m = int(sub.loc[sub["캐릭터"] == name, "언급영상수"].iloc[0]) if name in set(sub["캐릭터"]) else 0
        notes.append(n_m if name != "치이카와(개인)" else None)
        for j, lab in enumerate(metrics):
            row = sub[(sub["캐릭터"] == name) & (sub["지표"] == lab)]
            if row.empty or row.iloc[0]["표시"] != "계산":
                continue
            mat[i, j] = row.iloc[0]["스피어만"]
    fig, ax = plt.subplots(figsize=(8.2, 6.4))
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(np.ma.masked_invalid(mat), cmap="RdBu_r", norm=norm, aspect="auto")
    ax.set_xticks(range(len(metrics)), metrics)
    labels = []
    for name, n in zip(ORDER, notes):
        labels.append(f"{name}  ·  언급 {n}" if n is not None else f"{name}  ·  구분 불가")
    ax.set_yticks(range(len(ORDER)), labels)
    for i in range(len(ORDER)):
        for j in range(len(metrics)):
            if np.isfinite(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=11, color="#1a1a1a")
            else:
                ax.text(j, i, "분석 제한", ha="center", va="center", fontsize=9, color=GRAY)
    ax.set_title(title, loc="left", fontsize=13, pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("-1 ~ 1")
    fig.text(
        0.01, 0.01,
        "제목 본문만 사용. 값은 수집 시점 누적. 결측은 제외하고 0으로 바꾸지 않음. 언급 20편 미만과 치이카와(개인)은 분석 제한. 조회수 유효 6,454, 좋아요 5,973, 댓글 6,121.",
        fontsize=8, color="#444",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    save_fig(fig, fname)


def plot_box(work: pd.DataFrame, col: str, lab: str, fname: str) -> None:
    names = [n for n in ORDER if n != "치이카와(개인)"]
    data, positions, colors, meds = [], [], [], []
    ymax = 0.0
    for i, name in enumerate(names):
        for bit, color in ((1, NAVY), (0, "#c5ced6")):
            s = work.loc[work[f"언급_{name}"] == bit, col].dropna()
            vals = np.log1p(s.to_numpy(dtype=float))
            data.append(vals)
            positions.append(i * 3 + (0 if bit == 1 else 1))
            colors.append(color)
            if len(vals):
                ymax = max(ymax, float(np.nanpercentile(vals, 95)))
            meds.append((name, bit, int(len(s)), float(s.median()) if len(s) else np.nan))
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    bp = ax.boxplot(
        data, positions=positions, widths=0.7, showfliers=False, patch_artist=True,
        medianprops={"color": "#1a1a1a", "linewidth": 1.2},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor("#333")
    ax.set_xlim(-1, len(names) * 3 - 1)
    ax.set_ylim(0, ymax * 1.18 if ymax else 1)
    tick = []
    for name in names:
        n_m = int((work[f"언급_{name}"] == 1).sum())
        tick.append(f"{name}\n언급 {n_m}")
    ax.set_xticks([i * 3 + 0.5 for i in range(len(names))], tick)
    ax.set_ylabel(f"log1p({lab})")
    ax.set_title(f"제목 본문 언급 여부에 따른 {lab}", loc="left", fontsize=13, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.plot([], [], color=NAVY, linewidth=8, label="언급 있음")
    ax.plot([], [], color="#c5ced6", linewidth=8, label="언급 없음")
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.01, 0.01, "남색이 언급 있음, 회색이 언급 없음. 축은 log1p이고 이상점은 숨김. 검은 선은 중앙값. 원 척도 중앙값과 사분위는 집단비교 표에 있음.", fontsize=8, color="#444")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.16)
    save_fig(fig, fname)


if __name__ == "__main__":
    main()
