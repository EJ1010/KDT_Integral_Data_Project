# Verify published numbers against v3 CSVs. Does not change classifications.
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
posts = pd.read_csv(ROOT / "post_reaction_analysis.csv", dtype=str, keep_default_na=False)
ev = pd.read_csv(ROOT / "reaction_evidence.csv", dtype=str, keep_default_na=False)
review = pd.read_csv(ROOT / "review_required.csv", dtype=str, keep_default_na=False)
name_only = pd.read_csv(ROOT / "name_only_posts.csv", dtype=str, keep_default_na=False)

print("VERSION", posts.codebook_version.unique().tolist(), ev.codebook_version.unique().tolist())
print("posts", len(posts), "unique", posts.post_id.nunique(), "accounts", posts.account_id.nunique())
print("years", posts.created_year.value_counts().sort_index().to_dict())
print("lang", posts.language.value_counts().to_dict())
t = posts[posts.analysis_target == "예"]
print("target", len(t), "name_only file", len(name_only), "name_only flag", (t.name_only == "예").sum())
print("author_eval target", (t.author_evaluated == "예").sum())
print("review file", len(review), "review flag nonempty", (posts.review_flags != "").sum())
print("evidence rows", len(ev), "unique posts", ev.post_id.nunique())
print("view missing", (posts.view_missing == "예").sum(), "by year", posts[posts.view_missing == "예"].created_year.value_counts().to_dict())
print("view blank among missing", ((posts.view_missing == "예") & (posts.view_count == "")).sum())
print("view zero string", (posts.view_count == "0").sum())

# chiikawa roles among target name posts
chi = t[t.characters_confirmed.str.split("|").apply(lambda xs: "치이카와" in xs)]
print("chiikawa name posts", chi.post_id.nunique(), "accounts", chi.account_id.nunique())
for role in ["주인공", "작품", "불명확"]:
    ss = chi[chi.chiikawa_roles.str.contains(role)]
    print(role, ss.post_id.nunique(), "accounts", ss.account_id.nunique())
multi_role = chi[chi.chiikawa_roles.str.count(r"\|") >= 1]
print("chiikawa multi-role posts", multi_role.post_id.nunique())

author = ev[(ev.speaker == "작성자") & (ev.analysis_target == "예")]
print("author evidence rows", len(author), "posts", author.post_id.nunique())
print("evidence level posts")
print(author.groupby("evidence_level").post_id.nunique())
print("reaction target posts")
print(author.groupby("reaction_target").post_id.nunique())

affective = {"호감", "웃음·재미", "위로", "공감", "응원·보호 욕구", "비호감·불편", "혼합"}

def is_eval(r):
    emos = set(str(r.emotion).split("|"))
    return bool(emos & affective) or str(r.evidence_level).startswith("직접") or str(r.evidence_level).startswith("특징")

directed = author[(author.reaction_target == "특정 캐릭터") & (author.character != "")]
directed_eval = directed[directed.apply(is_eval, axis=1)]
print("directed eval posts", directed_eval.post_id.nunique(), "rows", len(directed_eval))
for char in ["하치와레", "랏코", "모몽가", "우사기", "쿠리만쥬", "치이카와", "시사"]:
    sub = directed_eval[directed_eval.character == char]
    voice = sub[sub.appeal.str.contains("목소리·말투")]
    generic = sub[sub.appeal.str.contains("구체적 이유 없는 호감")]
    print(char, "eval", sub.post_id.nunique(), "acc", t[t.post_id.isin(sub.post_id)].account_id.nunique(),
          "generic", generic.post_id.nunique(), "voice", voice.post_id.nunique(),
          "direct", sub[sub.evidence_level == "직접 이유"].post_id.nunique(),
          "feature", sub[sub.evidence_level.str.startswith("특징")].post_id.nunique())

rakko_voice = directed_eval[(directed_eval.character == "랏코") & (directed_eval.appeal.str.contains("목소리·말투"))]
print("--- rakko voice rows ---")
for _, r in rakko_voice.iterrows():
    q = r.evidence_quote.replace("\n", " ")
    same = ("랏코" in q) or ("락코" in q) or ("ラッコ" in q)
    acc = t.loc[t.post_id == r.post_id, "account_id"].iloc[0]
    print(r.post_id, acc, r.link_basis, r.evidence_level, "NAME_IN_QUOTE" if same else "NO_NAME", q[:80])

# goldengyul among rakko directed (all author rows, not only eval)
rakko_dir = author[(author.character == "랏코") & (author.reaction_target == "특정 캐릭터")]
print("rakko directed posts", rakko_dir.post_id.nunique())
acc = t[t.post_id.isin(rakko_dir.post_id)].groupby("account_id").size().sort_values(ascending=False)
print("top rakko directed", acc.head(3).to_dict())

hachi_dir = author[(author.character == "하치와레") & (author.reaction_target == "특정 캐릭터")]
acc_h = t[t.post_id.isin(hachi_dir.post_id)].groupby("account_id").size().sort_values(ascending=False)
print("hachi directed posts", hachi_dir.post_id.nunique(), "top", acc_h.head(1).to_dict())

# quote substring check
text_map = dict(zip(posts.post_id, posts.text))
bad = 0
for _, r in ev.iterrows():
    if r.evidence_quote and r.evidence_quote not in text_map.get(r.post_id, ""):
        # html escaped?
        if r.evidence_quote.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&") not in text_map.get(r.post_id, ""):
            bad += 1
print("bad quotes", bad)

# unclear affection posts
unclear_aff = author[(author.reaction_target == "불명확") & author.emotion.str.contains("호감")]
print("unclear affection posts", unclear_aff.post_id.nunique(), "accounts", t[t.post_id.isin(unclear_aff.post_id)].account_id.nunique())
rel = author[author.reaction_target == "캐릭터 간 관계"]
print("relation posts", rel.post_id.nunique(), "accounts", t[t.post_id.isin(rel.post_id)].account_id.nunique(), "direct", rel[rel.evidence_level == "직접 이유"].post_id.nunique())
