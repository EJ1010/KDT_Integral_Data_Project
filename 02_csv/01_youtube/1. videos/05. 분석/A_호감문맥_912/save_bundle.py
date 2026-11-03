"""판정 모듈을 원문과 대조해 묶음 파일과 진행 파일을 갱신한다. 판정은 만들지 않는다."""
import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
LEVELS = {
    "직접 밝힌 이유", "구체적 긍정 평가", "포괄적 호감",
    "특징 묘사만 있음", "호감 근거 없음", "판단 불가",
}
RANK = {
    "직접 밝힌 이유": 1, "구체적 긍정 평가": 2, "포괄적 호감": 3,
    "특징 묘사만 있음": 4, "호감 근거 없음": 5, "판단 불가": 6,
}
SEP = {"굿즈·상품", "성우·커버 가수", "제작자·편집"}


def main():
    module_name, bundle, start, end = sys.argv[1:5]
    start, end = int(start), int(end)
    src = pd.read_csv(ROOT / "01_입력_912.csv", encoding="utf-8-sig", dtype=str)
    src["순번"] = src["순번"].astype(int)
    text = dict(zip(src.순번, src.댓글원문))
    meta = src.set_index("순번")
    mod_path = Path(module_name)
    if not mod_path.is_file():
        mod_path = ROOT / module_name
    if not mod_path.is_file():
        mod_path = ROOT.parent / "90_보관" / "A_호감문맥_912" / Path(module_name).name
    if not mod_path.is_file():
        raise SystemExit(f"module {module_name}")
    spec = importlib.util.spec_from_file_location("j", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows, bad = [], []
    for i, item in enumerate(mod.LINKS, 1):
        aux = item[11] if len(item) > 11 else ""
        n, target, who, direction, level, feat, detail, quote, main, ctx, note = item[:11]
        if level not in LEVELS:
            raise SystemExit(f"level {n} {level}")
        if quote not in text[n]:
            bad.append((n, quote))
        rows.append(dict(
            묶음=bundle, 연결순=i, 순번=n, comment_id=meta.loc[n, "comment_id"],
            post_id=meta.loc[n, "post_id"], 입력_주유형=meta.loc[n, "1차_주유형"],
            평가대상=target, 대상_상세=who, 평가_방향=direction, 호감근거_수준=level,
            보조_간접관심=aux, 특징_범주=feat, 구체적_특징=detail, 근거문구=quote,
            대표=main, 문맥사용=ctx, 비고=note, 모델="Grok 4.7",
            프롬프트="context-912-v2", 판정="댓글을 직접 읽음",
        ))
    if bad:
        for n, q in bad:
            print("BAD", n, q)
        raise SystemExit(f"quote {len(bad)}")
    from collections import Counter
    mains = Counter(r["순번"] for r in rows if r["대표"] == 1)
    miss = [i for i in range(start, end + 1) if mains[i] != 1]
    if miss:
        raise SystemExit(f"main {miss}")
    new = pd.DataFrame(rows)
    new.to_csv(ROOT / f"03_연결_{bundle}.csv", index=False, encoding="utf-8-sig")
    old = pd.read_csv(ROOT / "03_연결_진행.csv", encoding="utf-8-sig")
    old = old[~old.묶음.eq(bundle)]
    link = pd.concat([old, new], ignore_index=True)
    expect = old.comment_id.nunique() + new.comment_id.nunique()
    if link.comment_id.nunique() != expect:
        raise SystemExit(f"dup {link.comment_id.nunique()} {expect}")
    link.to_csv(ROOT / "03_연결_진행.csv", index=False, encoding="utf-8-sig")
    link[link.평가대상.isin(list(SEP))].to_csv(
        ROOT / "03_분리_성우굿즈제작_진행.csv", index=False, encoding="utf-8-sig")
    done = set(link.comment_id.astype(str))
    src["상태"] = src.comment_id.map(lambda x: "완료" if x in done else "대기")
    src.groupby(["묶음", "상태"]).size().unstack(fill_value=0).reset_index().to_csv(
        ROOT / "00_진행.csv", index=False, encoding="utf-8-sig")
    out_rows = []
    for n, g in link.groupby("순번", sort=True):
        rep = g[g.대표.astype(str).isin(["1", "1.0"])].iloc[0]
        pos = g.copy()
        pos["rk"] = pos.호감근거_수준.map(RANK)
        best = pos.sort_values("rk").iloc[0]
        d = g[g.호감근거_수준.eq("직접 밝힌 이유")]
        who = " | ".join(dict.fromkeys(d.평가대상.astype(str) + "(" + d.대상_상세.astype(str) + ")"))
        others = g[~g.대표.astype(str).isin(["1", "1.0"])]
        extra = " | ".join(others.평가대상.astype(str) + "(" + others.대상_상세.astype(str) + ")")
        aux = " | ".join(x for x in g.보조_간접관심.fillna("") if str(x) not in ("", "nan"))
        flag = "대표가 굿즈·성우·제작·기타" if rep.평가대상 in SEP | {"기타·대상 불명확"} else ""
        rec = rep.to_dict()
        rec.update(가장_구체적_근거=best.호감근거_수준, 직접이유_대상=who, 다른_평가=extra, 보조_간접관심_모음=aux, 분리=flag)
        out_rows.append(rec)
    out = pd.DataFrame(out_rows)
    if out.comment_id.nunique() != link.comment_id.nunique():
        raise SystemExit("comment summary mismatch")
    out.to_csv(ROOT / "03_댓글판정_진행.csv", index=False, encoding="utf-8-sig")
    nxt = src.loc[src.상태.eq("대기")].sort_values("순번")
    done_n = int((src.상태 == "완료").sum())
    if nxt.empty:
        print(f"완료 {done_n} 남음 0")
    else:
        r = nxt.iloc[0]
        print(f"완료 {done_n} 남음 {len(nxt)} 다음 {int(r.순번)} {r.묶음} {r.comment_id}")


if __name__ == "__main__":
    main()
