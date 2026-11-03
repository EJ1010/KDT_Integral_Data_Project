# -*- coding: utf-8 -*-
"""분모 이동과 호감의 반응 대상을 점검한다. 원본 CSV는 읽기만 한다.

치이카와 개인 분모는 외형·목소리·성격 단어를 포함 조건으로 쓰므로
다른 캐릭터의 비율과 나란히 비교하지 않는다.
중앙값+8%포인트는 이 파일에서 두드러진 매력의 확정 기준으로 쓰지 않는다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import analyze_A_character_v1 as base  # noqa: E402

FONT = r"C:\Windows\Fonts\malgun.ttf"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
NAVY, GREEN, AMBER = "#3d6f8a", "#2f6f4e", "#b36b3a"
PURPLE, GRAY = "#5c4d7a", "#6e737a"

OLD_NAMES = [
    re.compile(p, re.I)
    for p in [
        r"치이\s*카와|치카와|ちいかわ|ﾁｰｶﾜ|chiikawa",
        r"먼작귀|먼가\s*작고\s*귀여운\s*녀석|뭔가\s*작고\s*귀여운",
        r"하치\s*와레|ハチワレ|hachiware",
        r"모몽가|모몬가|モモンガ",
        r"쿠리\s*만쥬|쿠리\s*만주|くりまんじゅう",
        r"아노코|あのこ",
        r"파자마\s*파티즈",
        r"데카\s*츠요",
        r"갑옷\s*씨",
        r"우사기",
        r"うさぎ|ウサギ",
        r"랏코|라코",
    ]
]
NEW_ONLY = [
    ("시사", re.compile(r"시샤|シーサー|(?<!우레)시사(?!회|점|디테일|프로그램|이슈)")),
    ("표기오타", re.compile(r"하치와래|하찌와레|하츠와레|치이\s*까와")),
    ("랭커", re.compile(r"랭커상|랭커")),
    ("카니", re.compile(r"(?<![가-힣])카니(?![가-힣])")),
    ("요로이", re.compile(r"요로이")),
]
COMPARE = [
    "우사기",
    "하치와레",
    "모몽가",
    "라코",
    "시사",
    "쿠리만쥬",
    "아노코",
    "갑옷씨",
    "데카츠요",
    "카니",
    "파자마파티즈",
]
CLAUSE_SPLIT = re.compile(r"[.!?。\n]+|(?:지만|는데|면서|으나)")
MEDIA = re.compile(
    r"(?:편집|커버|자막|썸네일|성우|더빙|빈님).{0,18}"
    r"(?:귀엽|귀여|졸귀|좋아|좋네|좋음|웃기|웃겨|재밌|재미있)"
    r"|(?:귀엽|귀여|졸귀|좋아|좋네|웃기|웃겨|재밌).{0,12}(?:편집|커버|자막|썸네일|성우|더빙)"
)
VOICE_CHAR = re.compile(r"목소리|말투|음성|발음")
VOICE_STAFF = re.compile(r"성우|더빙")
AFFECT = base.REACT[0][1]
HUMOR = base.REACT[1][1]


OLD_CLEAR = re.compile(
    r"귀여워|귀엽|졸귀|기여|웃겨|웃기|예뻐|이쁘|대박|헐|짱|싫어|좋아|"
    r"갖고\s*싶|사고\s*싶|보고\s*싶|뭐야|왜|슬프|무섭|사랑|재밌|"
    r"쌉가능|미쳤|레전|실화|인정|공감|좋아죽|존멋|존귀"
)
OLD_GRAMMAR = re.compile(
    r"[가-힣]{1,6}(?:습니다|네요|어요|아요|예요|이에요|했어요|했다|인데|거든|잖아|"
    r"까요|지요|하죠|요|다|네|지|음|임|냐|노|게|줘|걸|데|죠|함|용|여|셈|삼|도|고)"
)
NEAR_POS = re.compile(r"귀엽|귀여|졸귀|예쁘|이쁘|사랑|좋아|좋네|좋음")


def language_with(text: str, patterns, clear=None, grammar=None) -> str:
    clear = base.CLEAR_KO if clear is None else clear
    grammar = base.KO_GRAMMAR if grammar is None else grammar
    raw = base.clean(text)
    if not raw:
        return "판단 불가"
    stripped = base.EMOJI_RE.sub("", raw)
    stripped = re.sub(r"[ㅋㅎㅠㅜ!?~.,\s]+", "", stripped)
    if not stripped:
        return "판단 불가"
    rest = raw
    for cre in patterns:
        rest = cre.sub(" ", rest)
    rest_h = re.sub(r"[^가-힣]+", "", rest)
    hangul = len(base.HANGUL_RE.findall(raw))
    kana = len(base.KANA_RE.findall(raw))
    kanji = len(base.KANJI_RE.findall(raw))
    latin = base.LATIN_RE.findall(raw)
    foreign = kana >= 2 or kanji >= 1 or len(latin) >= 2
    koreanish = bool(clear.search(rest)) or (
        bool(grammar.search(rest)) and len(rest_h) >= 2
    )
    if not koreanish:
        if foreign or (hangul == 0 and (kana or kanji or latin)):
            return "외국어 중심"
        return "판단 불가"
    return "혼합_한국어 중심" if foreign else "한국어 중심"


def clauses_of(text: str) -> list[str]:
    parts = [p.strip() for p in CLAUSE_SPLIT.split(text) if p and p.strip()]
    return parts or [text]


def near_hit(text: str, cre: re.Pattern) -> bool:
    """이름 앞 20자·뒤 28자 안에 호감 단어가 있고, 그 구간에 부정이 없을 때."""
    for m in cre.finditer(text):
        left = text[max(0, m.start() - 20) : m.start()]
        right = text[m.end() : m.end() + 28]
        if not (NEAR_POS.search(left) or NEAR_POS.search(right)):
            continue
        if base.NEG_AFFECT.search(left + m.group() + right):
            continue
        return True
    return False


def near_label(text: str, name_cre: re.Pattern, label_cre: re.Pattern) -> bool:
    for m in name_cre.finditer(text):
        left = text[max(0, m.start() - 20) : m.start()]
        right = text[m.end() : m.end() + 28]
        if label_cre.search(left) or label_cre.search(right):
            return True
    return False


def nearest(spans: list[tuple[int, int, str]], start: int, end: int):
    if not spans:
        return None, None
    mid = (start + end) / 2
    ranked = []
    for a, b, name in spans:
        dist = 0 if a <= mid <= b else min(abs(mid - a), abs(mid - b))
        ranked.append((dist, name))
    ranked.sort()
    if len(ranked) >= 2 and ranked[1][0] - ranked[0][0] <= 4:
        return ranked[0][1], "공유"
    return ranked[0][1], "단일"


def link_comment(text: str) -> dict:
    """절 안에서 이름과 평가어가 맞닿을 때만 연결한다."""
    found = base.hits_of(text)
    names = [n for n, k in found if k != "제외"]
    out = {
        "names": names,
        "n_names": len(set(names)),
        "affect_any": False,
        "humor_any": False,
        "directed": {n: set() for n in set(names)},
        "shared_affect": False,
        "media_not_character": False,
        "unclear_affect": False,
    }
    for clause in clauses_of(text):
        name_spans = []
        for n, cre, k in base.CHAR_RES:
            if k == "제외":
                continue
            if n not in names and n != "치이카와" and n != "먼작귀":
                continue
            for m in cre.finditer(clause):
                if n == "우사기" and base.OPANCHU.search(clause):
                    continue
                name_spans.append((m.start(), m.end(), n))
        affects = [m for m in AFFECT.finditer(clause) if not base.NEG_AFFECT.search(clause)]
        humors = list(HUMOR.finditer(clause))
        if affects:
            out["affect_any"] = True
        if humors:
            out["humor_any"] = True
        media = bool(MEDIA.search(clause))
        if media and (affects or humors):
            out["media_not_character"] = True
        targets = [("호감", m) for m in affects] + [("유머", m) for m in humors]
        for label, cre in base.APPEAL:
            for m in cre.finditer(clause):
                if label == "목소리" and VOICE_STAFF.search(m.group()) and not VOICE_CHAR.search(clause):
                    out["media_not_character"] = True
                    continue
                targets.append((label, m))
        if not targets:
            continue
        if media:
            continue
        if not name_spans:
            if affects or humors:
                out["unclear_affect"] = True
            continue
        for label, m in targets:
            who, how = nearest(name_spans, m.start(), m.end())
            if how == "공유":
                if label == "호감":
                    out["shared_affect"] = True
                continue
            if who in out["directed"]:
                out["directed"][who].add(label)
    return out


def main() -> None:
    comments = pd.read_csv(
        base.CMT,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "comment_id", "comment_description"],
    )
    judge = pd.read_csv(
        base.JUDGE,
        encoding="utf-8-sig",
        usecols=["comment_id", "language_class", "reaction_target", "include_explore", "include_major"],
    )
    videos = pd.read_csv(base.VID, encoding="utf-8-sig")
    title_col = "title_without_hashtags" if "title_without_hashtags" in videos.columns else "post_title"
    df = comments.merge(judge, on="comment_id", how="left", validate="one_to_one")
    df["text"] = df["comment_description"].map(base.clean)
    df["lang_re"] = df["text"].map(base.language_of)
    df["spam_re"] = df["text"].map(lambda s: bool(base.SPAM.search(s))) | df["reaction_target"].eq("광고·스팸")
    df["name_only"] = df["text"].map(base.name_only)
    ko_new = df["lang_re"].isin(["한국어 중심", "혼합_한국어 중심"]) & ~df["spam_re"]
    old = df["include_explore"].fillna(False).astype(bool)
    only_old = old & ~ko_new
    only_new = ~old & ko_new

    def lang_at(text: str, patterns, clear, grammar) -> str:
        return language_with(text, patterns, clear, grammar)

    reasons = []
    examples = []
    for rec in df.loc[only_old, ["comment_id", "text", "lang_re", "spam_re", "reaction_target"]].itertuples(index=False):
        if rec.spam_re and rec.reaction_target != "광고·스팸":
            reasons.append("이번 광고 문구에 추가로 걸림")
            continue
        if rec.lang_re == "외국어 중심":
            reasons.append("외국어 중심으로 재분류")
            continue
        old_rule = lang_at(rec.text, OLD_NAMES, OLD_CLEAR, OLD_GRAMMAR)
        grammar_only = lang_at(rec.text, [cre for _, cre, _ in base.CHAR_RES], OLD_CLEAR, OLD_GRAMMAR)
        names_only = lang_at(rec.text, OLD_NAMES, base.CLEAR_KO, base.KO_GRAMMAR)
        ko = ("한국어 중심", "혼합_한국어 중심")
        if old_rule not in ko:
            label = "기존 규칙 재현과 불일치"
        elif grammar_only in ko and names_only not in ko:
            label = "어미 고·도·셈·삼 등을 한국어 단서에서 빼서 판단 불가가 됨"
        elif names_only in ko and grammar_only not in ko:
            label = "늘어난 이름 표기를 뺀 뒤 한국어 단서가 남지 않음"
        elif grammar_only not in ko and names_only not in ko:
            label = "어미 축소와 이름 표기 확대가 같이 작용"
        else:
            label = "기타"
        reasons.append(label)
        n_same = sum(1 for x in examples if x["사유"] == label)
        if n_same < 6:
            examples.append({"사유": label, "comment_id": rec.comment_id, "문장": rec.text[:180]})
    reason_tbl = (
        pd.Series(reasons).value_counts().rename_axis("사유").reset_index(name="댓글")
        if reasons
        else pd.DataFrame(columns=["사유", "댓글"])
    )
    enter = df.loc[only_new, "language_class"].fillna("(없음)").value_counts()
    bridge = pd.DataFrame(
        [
            {"구분": "기존 탐색 집단", "댓글": int(old.sum()), "메모": "기존 한국어·혼합, 광고·빈 댓글 제외"},
            {"구분": "이번 분석 대상", "댓글": int(ko_new.sum()), "메모": "언어를 다시 판정하고 광고를 뺀 값"},
            {"구분": "기존에만 있음", "댓글": int(only_old.sum()), "메모": "이번 대상에서 빠짐"},
            {"구분": "이번에만 있음", "댓글": int(only_new.sum()), "메모": "기존 탐색 밖에서 들어옴"},
            {
                "구분": "순감소",
                "댓글": int(only_old.sum() - only_new.sum()),
                "메모": "70,437과 67,891의 차이",
            },
        ]
    )
    bridge.to_csv(ROOT / "00_분모이동.csv", index=False, encoding="utf-8-sig")
    reason_tbl.to_csv(ROOT / "00_분모이동_사유.csv", index=False, encoding="utf-8-sig")
    enter.rename("댓글").rename_axis("기존언어").reset_index().to_csv(
        ROOT / "00_분모이동_유입.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(examples).to_csv(ROOT / "00_분모이동_예시.csv", index=False, encoding="utf-8-sig")

    # 문장 연결. 반응 분석 댓글만.
    work = df[ko_new & ~df["name_only"]].copy()
    linked = work["text"].map(link_comment)
    work["n_names"] = linked.map(lambda d: d["n_names"])
    work["affect_any"] = linked.map(lambda d: d["affect_any"])
    work["humor_any"] = linked.map(lambda d: d["humor_any"])
    work["shared_affect"] = linked.map(lambda d: d["shared_affect"])
    work["media_block"] = linked.map(lambda d: d["media_not_character"])
    work["unclear_affect"] = linked.map(lambda d: d["unclear_affect"])
    work["directed"] = linked.map(lambda d: d["directed"])
    work["chiikawa_role"] = [
        base.chiikawa_role(t, [n for n in d["names"] if n != "치이카와"]) if "치이카와" in d["names"] else ""
        for t, d in zip(work["text"], linked)
    ]

    rows = []
    multi_rows = []
    for name in COMPARE:
        sub = work[work["directed"].map(lambda d, name=name: name in d)]
        cre = next(c for n, c, _ in base.CHAR_RES if n == name)
        near = sub["text"].map(lambda s, cre=cre: near_hit(s, cre))
        directed_pos = sub["directed"].map(lambda d, name=name: "호감" in d[name])
        directed_humor = sub["directed"].map(lambda d, name=name: "유머" in d[name])
        multi = sub["n_names"] >= 2
        rows.append(
            {
                "캐릭터": name,
                "이름있는댓글": int(len(sub)),
                "영상": int(sub["post_id"].nunique()),
                "채널": int(sub["account_id"].dropna().nunique()),
                "공동출현_호감": int(sub["affect_any"].sum()),
                "인접_호감": int(near.sum()),
                "문장연결_호감": int(directed_pos.sum()),
                "공동출현_유머": int(sub["humor_any"].sum()),
                "문장연결_유머": int(directed_humor.sum()),
                "복수댓글": int(multi.sum()),
                "복수_이캐릭터호감": int((multi & directed_pos).sum()),
                "복수_호감있으나_이캐릭터아님": int((multi & sub["affect_any"] & ~directed_pos).sum()),
                "복수_호감공유": int((multi & sub["shared_affect"]).sum()),
                "편집등에_막힌호감": int((sub["media_block"] & sub["affect_any"] & ~directed_pos).sum()),
            }
        )
        appeal_pats = [("목소리", VOICE_CHAR) if lab == "목소리" else (lab, cre) for lab, cre in base.APPEAL]
        for label, lab_cre in appeal_pats:
            hit = sub["text"].map(lambda s, cre=cre, lab_cre=lab_cre: near_label(s, cre, lab_cre))
            multi_rows.append(
                {
                    "캐릭터": name,
                    "항목": label,
                    "문장연결": int(hit.sum()),
                    "분모": int(len(sub)),
                    "비율": float(hit.mean()) if len(sub) else 0,
                    "영상": int(sub.loc[hit, "post_id"].nunique()) if hit.any() else 0,
                    "채널": int(sub.loc[hit, "account_id"].dropna().nunique()) if hit.any() else 0,
                    "비율비교": "가능" if len(sub) >= 200 else "건수위주",
                }
            )
    pos = pd.DataFrame(rows)
    appeal = pd.DataFrame(multi_rows)
    pos.to_csv(ROOT / "07_호감연결.csv", index=False, encoding="utf-8-sig")
    appeal.to_csv(ROOT / "07_매력연결.csv", index=False, encoding="utf-8-sig")

    # 치이카와는 건수만. 비율 비교 표에 넣지 않는다.
    chi = work[work["directed"].map(lambda d: "치이카와" in d)]
    chi_pos = chi["directed"].map(lambda d: "호감" in d["치이카와"])
    chi_tbl = pd.DataFrame(
        [
            {
                "구분": role if role else "(없음)",
                "댓글": int((chi["chiikawa_role"] == role).sum()) if role else int(chi["chiikawa_role"].eq("").sum()),
                "문장연결_호감": int(((chi["chiikawa_role"] == role) & chi_pos).sum()),
            }
            for role in ["개인", "개인_대비", "개인_행동", "작품_쪽", "작품·캐릭터 불명확"]
        ]
    )
    chi_tbl.to_csv(ROOT / "07_치이카와_건수.csv", index=False, encoding="utf-8-sig")

    # 제목 언급은 보조. 화면 등장과 같지 않다.
    titles = videos[[title_col]].fillna("")
    title_rows = []
    for name, cre, _ in base.CHAR_RES:
        hit = titles[title_col].map(lambda s, cre=cre: bool(cre.search(s)))
        title_rows.append({"캐릭터": name, "제목에_이름있는_영상": int(hit.sum()), "A영상": len(titles)})
    pd.DataFrame(title_rows).to_csv(ROOT / "07_제목언급.csv", index=False, encoding="utf-8-sig")

    samples = []
    multi_aff = work[(work["n_names"] >= 2) & work["affect_any"]]
    for rec, link in zip(multi_aff.head(40).itertuples(index=False), multi_aff.head(40)["directed"]):
        samples.append(
            {
                "comment_id": rec.comment_id,
                "이름수": rec.n_names,
                "연결": " | ".join(f"{k}:{','.join(sorted(v))}" for k, v in link.items() if v),
                "공유": rec.shared_affect,
                "편집등": rec.media_block,
                "문장": rec.text[:240],
            }
        )
    pd.DataFrame(samples).to_csv(ROOT / "07_문장표본.csv", index=False, encoding="utf-8-sig")

    plot_bridge(reason_tbl, int(only_new.sum()))
    plot_affect(pos)
    plot_multi(pos)
    plot_heat(appeal)
    print("only_old", int(only_old.sum()), "only_new", int(only_new.sum()))
    print(reason_tbl.to_string(index=False))
    print(pos.to_string(index=False))
    print(chi_tbl.to_string(index=False))


def plot_bridge(reason_tbl: pd.DataFrame, entered: int) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    use = reason_tbl.sort_values("댓글")
    ax.barh(use["사유"], use["댓글"], color=NAVY)
    ax.set_xlabel("기존 탐색 집단에서 빠진 댓글 수")
    ax.set_xlim(0, max(use["댓글"].max() * 1.15, 1))
    ax.set_title(f"한국어 분모에서 빠진 사유  ·  새로 들어온 댓글 {entered:,}건")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_분모이동.png", dpi=140)
    plt.close()


def plot_affect(pos: pd.DataFrame) -> None:
    use = pos.sort_values("이름있는댓글", ascending=True)
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    y = range(len(use))
    co = use["공동출현_호감"] / use["이름있는댓글"] * 100
    di = use["인접_호감"] / use["이름있는댓글"] * 100
    ax.barh([i + 0.18 for i in y], co, height=0.36, color=GRAY, label="같은 댓글 안")
    ax.barh([i - 0.18 for i in y], di, height=0.36, color=GREEN, label="이름 앞 20자·뒤 28자")
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{n}  (n={d:,})" for n, d in zip(use["캐릭터"], use["이름있는댓글"])])
    ax.set_xlabel("그 캐릭터를 부른 댓글 중 비율 (%)")
    ax.set_xlim(0, 100)
    ax.set_title("호감 단어가 있는 범위  ·  치이카와 비율은 넣지 않음")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_호감_문장연결.png", dpi=140)
    plt.close()


def plot_multi(pos: pd.DataFrame) -> None:
    use = pos.sort_values("복수댓글", ascending=True)
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    y = range(len(use))
    linked = use["복수_이캐릭터호감"]
    other = use["복수_호감있으나_이캐릭터아님"]
    ax.barh(list(y), linked, color=GREEN, label="그 이름과 같은 절")
    ax.barh(list(y), other, left=linked, color=AMBER, label="호감은 있으나 그 이름과 같은 절이 아님")
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{n}  (복수 {d:,})" for n, d in zip(use["캐릭터"], use["복수댓글"])])
    ax.set_xlabel("댓글 수")
    ax.set_xlim(0, (linked + other).max() * 1.12)
    ax.set_title("이름이 둘 이상인 댓글의 호감  ·  건수")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_복수캐릭터_호감.png", dpi=140)
    plt.close()


def plot_heat(appeal: pd.DataFrame) -> None:
    labels = [a for a, _ in base.APPEAL]
    order = (
        appeal.groupby("캐릭터")["분모"].max().sort_values(ascending=False).index.tolist()
    )
    mat = []
    ann = []
    for name in order:
        row = []
        arow = []
        for lab in labels:
            rec = appeal[(appeal["캐릭터"] == name) & (appeal["항목"] == lab)].iloc[0]
            row.append(rec.비율 * 100)
            mark = "" if rec.비율비교 == "가능" else "*"
            arow.append(f"{rec.문장연결:,}{mark}")
        mat.append(row)
        ann.append(arow)
    import numpy as np

    arr = np.array(mat)
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    im = ax.imshow(arr, cmap="Blues", vmin=0, vmax=max(12, arr.max()))
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    for i in range(len(order)):
        for j in range(len(labels)):
            ax.text(j, i, ann[i][j], ha="center", va="center", color="black", fontsize=8)
    ax.set_title("이름 앞 20자·뒤 28자의 매력 단어  ·  칸 안은 댓글 수")
    fig.colorbar(im, ax=ax, label="이름 있는 댓글 중 비율 (%)")
    fig.tight_layout()
    fig.savefig(ROOT / "fig_매력히트맵.png", dpi=140)
    plt.close()


if __name__ == "__main__":
    main()
