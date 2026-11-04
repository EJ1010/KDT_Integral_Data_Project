# -*- coding: utf-8 -*-
"""Scan 5,000 posts for appearance-related wording. Not a labeler."""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_posts.csv")
KW = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_keywords.csv")
OUT = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\appearance_research\20261103_123659\working")

posts = []
with SRC.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        posts.append(row)

kw_map = defaultdict(list)
with KW.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        kw_map[row["post_id"]].append((int(row["keyword_order"]), row["keyword"]))

def keywords_of(pid):
    items = sorted(kw_map.get(pid, []), key=lambda x: x[0])
    return "|".join(k for _, k in items)

# Collapse stretched letters for search only. Original text is stored separately.
def norm(s):
    s2 = re.sub(r"\s+", "", s)
    s2 = re.sub(r"(.)\1{2,}", r"\1\1", s2)
    return s2.lower()

PATTERNS = {
    "side_profile": r"옆모습|측면얼굴|横顔|옆모습",
    "snout": r"주둥이|주등이| muzzle",
    "cheek": r"볼살|볼터치|볼을|볼이|뺨|볼살|볼이눌|볼눌",
    "bangs": r"앞머리|가르마머리|일자앞머리",
    "limbs": r"팔다리|짧은다리|짧은팔|짧은손|짧은발|手足|단족|다리가짧|팔이짧|다리가 짧|팔이 짧",
    "expression": r"표정",
    "eyes": r"눈망울|눈동자|초롱|눈매|큰눈|작은눈|반짝이|눈이|눈을",
    "roundness": r"동글|둥글|통통|동그란|동그랗|동글동글|둥글둥글|볼록",
    "texture": r"말랑|촉감|부들|폭신|손맛|보들|푹신|쫄깃|질감",
    "head_body": r"대가리|머리통|큰머리|작은몸|비율|머리크기|머리가크|몸이작|얼굴이크|얼굴크기",
    "ears": r"귀가|귀를|긴귀|토끼귀|고양이귀|귀여운귀",
    "tail_fur": r"꼬리|복실|복슬|털이|털복|폭신한털|무늬",
    "color": r"머리색|색감|파스텔|색깔|색이",
    "pose": r"뒷모습|실루엣|앉은|앉아서|누운|엎드",
    "clothes": r"오징어옷|옷입은|옷입|리본|모자쓴|파자마",
    "plush_form": r"인형|누이|ぬい|키링|피규어|가챠",
    "worthless": r"하찮|찌부|찌부러|작아보이",
    "negative_cute": r"안귀엽|안 귀엽|별로안|못생겼|이상하게생겼|징그럽|귀엽지않|안귀여",
    "cute_word": r"귀엽|기여워|귀여워|귀여움|귀여운|かわいい|可愛い|カワイイ|커엽",
}

# eyes pattern "눈이|눈을" is too broad. Keep a tighter eyes set for the dump.
TIGHT = {
    "side_profile": r"옆모습|横顔",
    "snout": r"주둥이|주등이",
    "cheek": r"볼살|볼터치|볼눌|볼이눌|볼을눌|볼살",
    "bangs": r"앞머리",
    "limbs": r"팔다리|짧은\s*다리|짧은\s*팔|手足|단족|다리가\s*짧|팔이\s*짧|다리가짧|팔이짧",
    "expression": r"표정",
    "eyes_specific": r"눈망울|눈동자|초롱초롱|눈매|큰\s*눈|작은\s*눈|눈이\s*반짝|눈\s*반짝|순정만화",
    "roundness": r"동글|둥글|통통|동그란|동그랗|볼록한",
    "texture": r"말랑|촉감|부들부들|폭신|보들보들|푹신|질감",
    "head_body": r"대가리|머리통|큰\s*머리|작은\s*몸|머리\s*크기|머리가\s*크|몸이\s*작|얼굴이\s*크|비율",
    "ears": r"귀가|귀를|긴\s*귀|토끼\s*귀|고양이\s*귀",
    "tail_fur": r"꼬리|복실|복슬|털이|무늬",
    "color": r"머리\s*색|색감|파스텔",
    "pose": r"뒷모습|실루엣|앉은\s*모습|앉은\s*치이|앉은\s*하치",
    "clothes": r"오징어\s*옷|리본|파자마",
    "negative_cute": r"안\s*귀엽|별로|못생겼|징그럽|귀엽지\s*않",
    "worthless": r"하찮|찌부",
}

compiled = {k: re.compile(v) for k, v in TIGHT.items()}

hits = []
counts = Counter()
post_hit_n = 0
for row in posts:
    text = row["text"] or ""
    ntext = norm(text)
    matched = [k for k, cre in compiled.items() if cre.search(ntext) or cre.search(text)]
    if not matched:
        continue
    post_hit_n += 1
    for k in matched:
        counts[k] += 1
    hits.append({
        "post_id": row["post_id"],
        "post_url": row["post_url"],
        "account_id": row["account_id"],
        "created_at": row["created_at"],
        "like_count": row["like_count"],
        "keywords": keywords_of(row["post_id"]),
        "features": "|".join(matched),
        "text": text.replace("\r\n", "\n").replace("\r", "\n"),
    })

# language of hit texts
def lang_bucket(text):
    hangul = len(re.findall(r"[가-힣]", text))
    kana = len(re.findall(r"[ぁ-んァ-ン]", text))
    hanja_or_kanji = len(re.findall(r"[一-龯]", text))
    if hangul >= 8 and kana < 4:
        return "ko_main"
    if kana >= 8 and hangul < 4:
        return "ja_main"
    if hangul >= 4 and kana >= 4:
        return "ko_ja_mixed"
    if hangul >= 4:
        return "ko_main"
    if kana >= 4:
        return "ja_main"
    return "other_or_short"

lang_c = Counter(lang_bucket(h["text"]) for h in hits)

summary_path = OUT / "candidate_summary.txt"
with summary_path.open("w", encoding="utf-8") as f:
    f.write(f"posts_total={len(posts)}\n")
    f.write(f"posts_with_any_tight_feature={post_hit_n}\n")
    f.write("feature_post_counts (a post can match several):\n")
    for k, v in counts.most_common():
        f.write(f"  {k}\t{v}\n")
    f.write("language_of_hit_posts:\n")
    for k, v in lang_c.most_common():
        f.write(f"  {k}\t{v}\n")

# dump full texts grouped
dump = OUT / "candidate_texts.md"
with dump.open("w", encoding="utf-8") as f:
    f.write(f"# Tight feature candidates: {len(hits)} posts / {len(posts)} total\n\n")
    for h in hits:
        f.write(f"## {h['post_id']} | {h['features']} | {h['created_at']} | likes={h['like_count']} | @{h['account_id']}\n")
        f.write(f"keywords: {h['keywords']}\n")
        f.write(f"url: {h['post_url']}\n\n")
        f.write(h["text"])
        f.write("\n\n---\n\n")

# also cute-word count without feature
cute_re = re.compile(r"귀엽|기여|귀여|かわいい|可愛|커엽")
cute_n = sum(1 for r in posts if cute_re.search(norm(r["text"] or "") or r["text"]))
with summary_path.open("a", encoding="utf-8") as f:
    f.write(f"posts_with_cute_word={cute_n}\n")

print("posts", len(posts))
print("hits", len(hits))
print(counts)
print("cute", cute_n)
print("lang", lang_c)
