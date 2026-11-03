# -*- coding: utf-8 -*-
"""캐릭터·작품 호감 후보 테이블.

이름·작품 표기와 긍정 표현이 같은 댓글에 있는지를 고른다.
평가 대상과 호감 이유는 확정하지 않는다. 빈 문맥 칸은 후속 판정용이다.
"""
from pathlib import Path
import re
import sys
import pandas as pd

CHAR_DIR = Path(__file__).resolve().parents[1] / "A_캐릭터반응"
sys.path.insert(0, str(CHAR_DIR))
import analyze_A_character_v1 as base  # noqa: E402

ROOT = Path(__file__).resolve().parent
RULE = "candidate-table-v1"
DICT = "A_캐릭터반응 CHAR/REACT 호감 + A_키워드 작품표기·재미있다. 짭몽가만 모몽가에 추가"

# 기존 호감 사전. ㅋㅋ·ㅎㅎ·이모지·구매는 넣지 않는다.
OLD_POS = base.REACT[0][1]
POS = re.compile(
    r"귀엽|귀여|졸귀|기여워|예쁘|이쁘|사랑스럽|사랑|최애|입덕|반했|최고|"
    r"좋아|좋네|좋음|재밌|재미있"
)
LIKE_BTN = re.compile(r"좋아요\s*(?:눌|부탁)|구독\s*과?\s*좋아요|좋아요\s*구독")
MEDIA = re.compile(
    r"(?:편집|커버|자막|썸네일|성우|더빙|빈님).{0,18}"
    r"(?:귀엽|귀여|졸귀|좋아|좋네|좋음|재밌|재미있|사랑|최고)"
    r"|(?:귀엽|귀여|졸귀|좋아|좋네|재밌|사랑).{0,12}(?:편집|커버|자막|썸네일|성우|더빙)"
    r"|보러\s*왔.{0,20}(?:편집|성우|더빙|커버)"
)
WORK_PHRASE = re.compile(r"먼가\s*작고\s*귀여운(?:\s*녀석)?|뭔가\s*작고\s*귀여운")
JJAP = re.compile(r"짭\s*몽가|짭몽가|짭\s*모몽가")
JIN = re.compile(r"찐\s*몽가|찐몽가")
LABELS = [
    ("귀엽다", re.compile(r"귀엽|귀여|졸귀|기여워")),
    ("예쁘다", re.compile(r"예쁘|이쁘")),
    ("사랑스럽다", re.compile(r"사랑스럽|사랑")),
    ("최애", re.compile(r"최애")),
    ("입덕", re.compile(r"입덕|반했")),
    ("최고", re.compile(r"최고")),
    ("좋다", re.compile(r"좋아|좋네|좋음")),
    ("재미있다", re.compile(r"재밌|재미있")),
]


def spans(cre, text):
    return [(m.start(), m.end()) for m in cre.finditer(text)]


def overlap(a, b):
    return not (a[1] <= b[0] or b[1] <= a[0])


def live_positive(text):
    neg = spans(base.NEG_AFFECT, text)
    blocked = spans(LIKE_BTN, text)
    raw = spans(POS, text)
    live, dead = [], []
    for sp in raw:
        if any(overlap(sp, n) for n in neg):
            dead.append(sp)
        elif any(overlap(sp, b) for b in blocked):
            continue
        else:
            live.append(sp)
    return live, dead


def labels_of(text, live):
    found = []
    for name, cre in LABELS:
        for m in cre.finditer(text):
            sp = (m.start(), m.end())
            if any(overlap(sp, s) for s in live):
                found.append(name)
                break
    return found


def window(text, start, end, pad=16):
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return text[a:b].strip()


def evidence(text, anchors):
    bits = []
    for a, b in anchors:
        w = window(text, a, b)
        if w and w not in bits:
            bits.append(w)
    return " / ".join(bits)[:180]


def main():
    comments = pd.read_csv(
        base.CMT,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "account_name", "comment_id", "comment_description", "title_without_hashtags"],
    )
    judge = pd.read_csv(
        base.JUDGE,
        encoding="utf-8-sig",
        usecols=["comment_id", "language_class", "reaction_target", "반어_검토"],
    )
    videos = pd.read_csv(
        base.VID,
        encoding="utf-8-sig",
        usecols=["post_id", "account_id", "account_name", "title_without_hashtags"],
    )
    df = comments.merge(judge, on="comment_id", how="left", validate="one_to_one")
    df = df.merge(
        videos.rename(columns={
            "account_id": "video_account_id",
            "account_name": "video_account_name",
            "title_without_hashtags": "video_title",
        }),
        on="post_id",
        how="left",
        validate="many_to_one",
    )
    if len(df) != len(comments):
        raise SystemExit("조인으로 댓글 행이 늘었다")
    df["text"] = df["comment_description"].map(base.clean)
    df["lang_re"] = df["text"].map(base.language_of)
    df["spam_re"] = df["text"].map(lambda s: bool(base.SPAM.search(s))) | df["reaction_target"].eq("광고·스팸")
    pop = df[df["lang_re"].isin(["한국어 중심", "혼합_한국어 중심"]) & ~df["spam_re"]].copy()
    if len(pop) != 67891 or pop["comment_id"].duplicated().any():
        raise SystemExit(f"모집단 {len(pop)} 고유 {pop['comment_id'].nunique()}")

    rows = []
    links = []
    for rec in pop.itertuples(index=False):
        text = rec.text
        live, dead = live_positive(text)
        if not live:
            continue
        names = [n for n, k in base.hits_of(text) if k != "제외"]
        chars = [n for n in names if n not in ("치이카와", "먼작귀")]
        alias = ""
        if JJAP.search(text) and "모몽가" not in chars:
            chars.append("모몽가")
            alias = "짭몽가"
        elif JJAP.search(text):
            alias = "짭몽가"
        has_chi = "치이카와" in names
        works = []
        if "먼작귀" in names:
            works.append("먼작귀")
        if WORK_PHRASE.search(text):
            works.append("먼가 작고 귀여운 녀석")
        if not chars and not has_chi and not works:
            continue
        # 찐몽가는 모몽가로 넣지 않는다. 검출 이름에 남지 않았는지만 확인.
        if JIN.search(text) and "모몽가" not in [n for n, _ in base.hits_of(text)] and not JJAP.search(text):
            pass

        old_chars = [n for n in names if n not in ("치이카와", "먼작귀", "うさぎ")]
        old_chi = False
        if has_chi:
            role = base.chiikawa_role(text, [n for n in names if n not in ("치이카와", "먼작귀")])
            old_chi = role in ("개인", "개인_대비")
        old_hit = bool(OLD_POS.search(text)) and not bool(base.NEG_AFFECT.search(text))
        in_old = old_hit and (bool(old_chars) or old_chi)

        paths = []
        if chars:
            paths.append("A")
        if has_chi:
            paths.append("B")
        if works:
            paths.append("C")
        if not paths:
            continue

        if len(chars) >= 2 or (chars and (has_chi or works)) or (has_chi and works):
            prelim = "복수·혼합"
        elif len(chars) == 1:
            prelim = "특정 캐릭터 후보"
        elif has_chi:
            prelim = "작품·캐릭터 불명확"
        else:
            prelim = "작품 전체 후보"

        pos_names = labels_of(text, live)
        reviews = []
        if dead:
            reviews.append("긍정·부정 공존")
        if bool(rec.반어_검토) if not pd.isna(rec.반어_검토) else False:
            reviews.append("반어_검토")
        if MEDIA.search(text):
            reviews.append("편집·성우·커버와 인접")

        anchors = []
        for cre in (JJAP, base.CHAR_RES[0][1], WORK_PHRASE):
            m = cre.search(text)
            if m:
                anchors.append((m.start(), m.end()))
                break
        for n, cre, _k in base.CHAR_RES:
            if n in chars or n in ("치이카와", "먼작귀") and ((n == "치이카와" and has_chi) or (n == "먼작귀" and "먼작귀" in works)):
                m = cre.search(text)
                if m:
                    anchors.append((m.start(), m.end()))
                    break
        if live:
            anchors.append(live[0])

        src = []
        if in_old:
            src.append("A_캐릭터반응 호감공동출현")
        src.append("A_키워드 언어·반응대상")
        title = rec.video_title if isinstance(rec.video_title, str) and rec.video_title else rec.title_without_hashtags
        account_id = rec.video_account_id if isinstance(rec.video_account_id, str) else rec.account_id
        account_name = rec.video_account_name if isinstance(rec.video_account_name, str) else rec.account_name

        rows.append({
            "comment_id": rec.comment_id,
            "post_id": rec.post_id,
            "account_id": account_id,
            "account_name": account_name,
            "댓글원문": rec.comment_description if isinstance(rec.comment_description, str) else "",
            "영상제목": title if isinstance(title, str) else "",
            "기존_언어판정": rec.language_class,
            "언어_재계산": rec.lang_re,
            "후보_선정경로": "|".join(paths),
            "검출_캐릭터": "|".join(dict.fromkeys(chars)),
            "검출_작품표기": "|".join(dict.fromkeys((["치이카와"] if has_chi else []) + works)),
            "검출_호감표현": "|".join(pos_names),
            "기존_평가": rec.reaction_target if isinstance(rec.reaction_target, str) else "",
            "기존_판정출처": " / ".join(src),
            "대상_예비구분": prelim,
            "긍정부정_충돌여부": "예" if dead else "",
            "평가대상_재검토": "|".join(reviews),
            "선정_근거문구": evidence(text, anchors),
            "규칙버전": RULE,
            "기존규칙_호감후보": "예" if in_old else "",
            "문맥_최종대상": "",
            "문맥_평가": "",
            "호감근거_수준": "",
            "매력요소": "",
            "구체적_특징": "",
            "최종_근거문구": "",
            "검수상태": "",
        })
        for name in dict.fromkeys(chars):
            links.append({
                "comment_id": rec.comment_id,
                "구분": "캐릭터",
                "이름": name,
                "별칭": alias if name == "모몽가" and alias else "",
                "선정경로": "A",
            })
        if has_chi:
            links.append({
                "comment_id": rec.comment_id, "구분": "치이카와", "이름": "치이카와",
                "별칭": "", "선정경로": "B",
            })
        for w in dict.fromkeys(works):
            links.append({
                "comment_id": rec.comment_id, "구분": "작품", "이름": w, "별칭": "", "선정경로": "C",
            })

    out = pd.DataFrame(rows)
    link = pd.DataFrame(links)
    if out["comment_id"].duplicated().any() or out["comment_id"].isna().any():
        raise SystemExit("후보 comment_id 중복 또는 결측")
    if not set(out["comment_id"]).issubset(set(pop["comment_id"])):
        raise SystemExit("모집단 밖 ID")
    # 근거 문구는 원문 일부여야 한다. 구분자만 빼고 확인한다.
    bad = 0
    text_map = dict(zip(pop["comment_id"], pop["text"]))
    for cid, quote in zip(out["comment_id"], out["선정_근거문구"]):
        src_text = text_map[cid]
        for part in str(quote).split(" / "):
            if part and part not in src_text:
                bad += 1
                break
    if bad:
        raise SystemExit(f"근거 문구가 원문에 없음 {bad}")

    out.to_csv(ROOT / "A_캐릭터_작품_호감후보_comments.csv", index=False, encoding="utf-8-sig")
    link.to_csv(ROOT / "A_캐릭터_작품_호감후보_연결.csv", index=False, encoding="utf-8-sig")

    def ids_of(flag):
        return set(out.loc[out["후보_선정경로"].map(lambda s: flag in str(s).split("|")), "comment_id"])

    a_ids, b_ids, c_ids = ids_of("A"), ids_of("B"), ids_of("C")
    old_ids = set(out.loc[out["기존규칙_호감후보"].eq("예"), "comment_id"])
    final_ids = set(out["comment_id"])
    added_b = b_ids - old_ids
    added_c_only = c_ids - old_ids - b_ids
    added_total = final_ids - old_ids
    summary = pd.DataFrame([
        ["모집단", len(pop)],
        ["기존규칙_호감후보_고유", len(old_ids)],
        ["경로A_특정캐릭터_고유", len(a_ids)],
        ["경로B_치이카와_고유", len(b_ids)],
        ["경로C_작품표기_고유", len(c_ids)],
        ["B로_기존규칙에_없던_고유", len(added_b)],
        ["C로만_새로_추가된_고유", len(added_c_only)],
        ["기존규칙_대비_새로_추가된_고유", len(added_total)],
        ["최종_고유댓글", len(final_ids)],
        ["영상", int(out["post_id"].nunique())],
        ["채널", int(out["account_id"].nunique())],
        ["긍정부정_충돌", int(out["긍정부정_충돌여부"].eq("예").sum())],
        ["평가대상_재검토", int(out["평가대상_재검토"].fillna("").ne("").sum())],
        ["연결행", len(link)],
        ["찐몽가_자동확대", 0],
    ], columns=["항목", "값"])
    prelim = out["대상_예비구분"].value_counts().rename_axis("대상_예비구분").reset_index(name="댓글")
    summary.to_csv(ROOT / "00_요약.csv", index=False, encoding="utf-8-sig")
    prelim.to_csv(ROOT / "00_예비구분.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    print(prelim.to_string(index=False))
    print("jinmongga in chars", int(out["검출_캐릭터"].fillna("").str.contains("찐").sum()))


if __name__ == "__main__":
    main()
