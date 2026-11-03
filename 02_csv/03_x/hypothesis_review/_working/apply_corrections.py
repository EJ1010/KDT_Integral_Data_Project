# -*- coding: utf-8 -*-
"""Apply second-pass corrections and write evidence rows as JSON for the report builder."""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

base = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
work = base / "hypothesis_review" / "_working"
posts = {
    r["post_id"]: r
    for r in csv.DictReader(open(base / "normalized" / "x_posts.csv", encoding="utf-8-sig", newline=""))
}

files = {
    "H1": ["judgments_h1_p1.csv", "judgments_h1_p2.csv"],
    "H2": ["judgments_h2_p1.csv"],
    "H3": ["judgments_h3_p1.csv", "judgments_h3_p2.csv"],
}

# (post_id, facet) -> field updates. facet None means all rows of that post.
COR = {}

def set_cor(pid, facet, **kw):
    COR[(pid, facet)] = kw

# H1: scene gags and announcements are not "story is the reason".
H1_SCENE_NEUTRAL = {
    "1524676495108882434",
    "1545562789775036416",
    "1557752953707978752",
    "1565517408621985792",
    "1751289199054266805",
    "1873363753212993867",
    "1959068577845452979",
    "1959246555656942055",
    "2071599159900319761",
    "2083298499190497656",
    "2089409632892756098",
    "2095143483573239976",
    "2102179672230625715",
    "2103785407922286980",
    "2103886485896515716",
    "2105578888168624279",
    "2108615645571203124",
}
for pid in H1_SCENE_NEUTRAL:
    set_cor(pid, "서사 긍정 평가", relation="중립·관련 언급", evidence_level="명시적 평가·경험",
            judgment_reason="장면이나 에피소드를 좋게 말한 글이다. 그 이야기가 캐릭터 호감의 이유라고 적혀 있지는 않다.")

# Downgrade false 'direct reason' where the sentence evaluates or empathizes but does not say why they like the IP.
DIRECT_TO_EXPLICIT = {
    ("1541364020481265665", "사연·노력·일상 연결"),
    ("1543247183792578560", "사연·노력·일상 연결"),
    ("1650411719628578816", "사연·노력·일상 연결"),
    ("1652030532375707649", "사연·노력·일상 연결"),
    ("1794954532998570402", "사연·노력·일상 연결"),
    ("1831673833881006087", "사연·노력·일상 연결"),
    ("1886763549101580632", "성격·말투 호감"),
    ("1959240569785573505", "어두운·불편한 설정 반응"),
    ("1995108298509697518", "이야기 후 호감 증가·응원"),
    ("2029231638903923070", "어두운·불편한 설정 반응"),
    ("2082776340969971918", "어두운·불편한 설정 반응"),
    ("2083896210125967655", "성격·말투 호감"),
    ("2085298375780688249", "서사 긍정 평가"),
    ("2087209297612820667", "서사 긍정 평가"),
    ("2090086900547846264", "관계·우정 호감"),
    ("2091464065214493000", "관계·우정 호감"),
    ("2105578888168624279", "서사 긍정 평가"),
}
for key in DIRECT_TO_EXPLICIT:
    COR.setdefault(key, {})
    COR[key]["evidence_level"] = "명시적 평가·경험"

set_cor("1886763549101580632", "성격·말투 호감",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="성우 교체에 반대하는 글이다. 그 목소리가 호감의 이유라고 밝히지는 않는다.")
set_cor("1989941835834560522", "사연·노력·일상 연결",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="에피소드와 같은 음식을 해 먹었다. 그 이야기가 캐릭터를 좋아하는 이유라는 말은 아니다.")
set_cor("1965478322030436590", "성격·말투 호감",
       relation="중립·관련 언급", evidence_level="단순 공존",
       judgment_reason="공포 게임 방송에서 의성어 덕분에 덜 놀랐다는 말이지, 캐릭터 호감의 이유는 아니다.")
set_cor("1783928956049391648", "다음 이야기 기대",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="다시 정주행하겠다는 계획만 있다. 이야기의 어떤 점이 호감의 이유인지는 없다.")
set_cor("1802575328029892899", "세계관 호감",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="행사 구역이 기대된다는 안내성 문장이다. 세계관이 애착의 이유라고 하지 않는다.")
set_cor("1926172433876185409", "다음 이야기 기대",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="팬아트 캡션의 '원하는 전개'만 있어 무엇을 기대하는 말인지 확정할 수 없다.")
set_cor("1992905205692923983", "다음 이야기 기대",
       relation="중립·관련 언급", evidence_level="단순 공존", speaker="팬 창작 안내",
       judgment_reason="팬 영화화를 알리며 기대를 부탁한 글이다. 시청자가 이야기를 호감의 이유로 밝힌 글이 아니다.")
set_cor("1639120291623493633", "세계관 호감",
       relation="중립·관련 언급", evidence_level="단순 공존",
       judgment_reason="성우가 다른 작품 인물과 겹친다는 농담이다. 세계관 호감이 아니다.")
set_cor("1686377372470345729", "세계관 호감",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="최강 설정과 귀여운 모습을 대비해 애칭한 글이다. 세계관이 이유라고 쓰지 않는다.")
set_cor("2079831019331727748", "세계관 호감",
       relation="중립·관련 언급", evidence_level="단순 공존",
       judgment_reason="다른 대상을 이 세계관에 넣고 싶다는 말만 있다.")
set_cor("2086433288064004432", "세계관 호감",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="젠더리스 설정에 맞춰 굿즈를 늘리자는 의견이다. 그 세계 때문에 좋아한다는 문장은 아니다.")
set_cor("2083152999397150724", "다음 이야기 기대",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="극장판을 보러 간다는 계획이다. 이야기를 호감의 이유로 설명하지는 않는다.")
set_cor("1740754736499012086", "이야기 후 호감 증가·응원",
       relation="명시적 평가·경험" and "지지",
       )
# fix the bad set_cor above - I'll handle 174075 separately if needed. The and expression is wrong.
# Remove that key if created badly.
COR.pop(("1740754736499012086", "이야기 후 호감 증가·응원"), None)

# H2
set_cor("1803727354289930677", "동물 유사성 긍정",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="소동물 같다는 대상이 캐릭터가 아니라 먼작귀를 따라 하는 사람들이다.")
set_cor("1935180709037228523", "동물 부위 호감",
       relation="중립·관련 언급", evidence_level="단순 공존",
       judgment_reason="아이돌이 인형 귀를 만지는 장면이 귀엽다는 말이지, 귀 모양이 호감의 이유라고 하지 않는다.")
set_cor("1802035047027052960", "동물 부위 호감",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="성우가 고양이 입 모양을 알아봐 줘서 기뻤다고 전한 글이다. 작성자 본인의 호감 이유는 아니다.")
set_cor("1740422959238664376", "동물 유사성 긍정",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="다람쥐에 비유한 대상이 모몽가인지 사람(규호)인지 문장만으로 갈라지지 않는다.")
set_cor("1851788913058419194", "동물 부위 호감",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="아기 고양이와 털을 말한 대상이 하치와레 캐릭터인지 사람에게 붙인 호칭인지 확정되지 않는다.")
set_cor("1959659878060068982", "동물 유사성 긍정",
       evidence_level="명시적 평가·경험",
       judgment_reason="고양이라 헤어볼을 뱉는 장면이 귀엽다고 했다. 작품 전체의 호감 이유라고 확대하지 않는다.")
set_cor("1984545833589829794", "동물 부위 호감",
       evidence_level="명시적 평가·경험", speaker="인용된 타인",
       judgment_reason="복실한 털 때문에 다른 사람이 머리를 쓰다듬는 장면이다. 작성자가 그 털을 구매 이유로 밝히지는 않는다.")
set_cor("1985666749333979266", "동물 부위 호감",
       relation="혼합", evidence_level="명시적 평가·경험",
       judgment_reason="꼬리가 없는 것을 아쉬워한다. 꼬리에 대한 관심은 있으나 호감 이유라고 쓰지는 않는다.")
set_cor("2047494837407240583", "인간형 대비 동물형 선호",
       judgment_reason="팬아트에서 의인화보다 원판 랏코가 귀여움과 어른의 인상을 함께 담는다고 비교했다. 상품 소비자의 일반 선호 비교는 아니다.")

# H3
set_cor("1674538594713882624", "휴대·부착 경험",
       relation="혼합", evidence_level="명시적 평가·경험",
       judgment_reason="폰에 붙여 봤으나 실용성은 모르겠고 귀엽다는 쪽을 말했다. 휴대성이 선택 이유는 아니다.")
set_cor("1841450402505728197", "휴대·부착 경험",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="10대 가방의 구성 예시로 헤어핀이 나열됐다. 작성자의 휴대 경험인지는 확정되지 않는다.")
set_cor("1841737695518982258", "휴대·부착 경험",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="다른 사람들이 군번줄째 가방에 다는 것을 보고 떨어질 수 있다고 경고한다. 작성자의 선호 이유는 아니다.")
set_cor("1918585306221006890", "휴대·부착 희망",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="여행에 챙긴다는 대상이 캐릭터 이름 팩·버거로 읽힌다. 휴대 굿즈 선호로 확정하지 않는다.")
set_cor("1984545833589829794", "가까이 두고 보는 경험·희망",
       speaker="인용된 타인", evidence_level="명시적 평가·경험",
       judgment_reason="집에 둔 랏코를 다른 사람이 쓰다듬는 장면이다.")
set_cor("2015692848113610973", "전시·보관 선호",
       relation="혼합", evidence_level="명시적 평가·경험",
       judgment_reason="직장 책상 위에 다른 작품 피규어와 함께 하치와레를 두었다. 휴대 이유는 아니고, 가까이 두는 전시이다.")
set_cor("2032243186660520089", "휴대·부착 경험",
       relation="중립·관련 언급", evidence_level="단순 공존", speaker="판단 불가",
       judgment_reason="가방에 단 물건의 주체가 작성자인지 남자아이인지 문장만으로 확정되지 않는다.")
set_cor("2109237607641284859", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="단순 공존", speaker="정보 공유",
       judgment_reason="팝콘통 스티커를 버리지 말고 보관하라는 안내이다. 작성자의 미사용 선호가 아니다.")
set_cor("1571422805656469507", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="통에 넣어 두면 귀여울 것이라는 제안이다. 휴대보다 전시를 택했다는 본인 경험은 아니다.")
set_cor("1596757804723081222", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="미니트리 장식으로 단 경험이다. 휴대하지 않겠다는 말은 아니다.")
set_cor("1583818855020797952", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="키링 택을 보관함에 모았다. 휴대 포기는 아니다.")
set_cor("1533091469476896769", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="식완이 나오면 피규어와 함께 장식하고 싶다는 희망이다.")
set_cor("1740215784230834546", "전시·보관 선호",
       relation="혼합", evidence_level="명시적 평가·경험",
       judgment_reason="보면 마음이 편해 유리통에 넣어 두고 싶다고 했다. 가까이 보는 즐거움과 보관이 함께 있다.")
set_cor("2049399862442230003", "전시·보관 선호",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="벽 진열에서 컬렉트북 보관으로 옮겼다. 휴대성 거부는 아니다.")
set_cor("1620592787417870336", "휴대·부착 경험",
       relation="판단 불가", evidence_level="판단 불가",
       judgment_reason="군번줄을 고정한다는 문장의 화자가 작성자 본인인지 확인되지 않는다.")
set_cor("1834821535799947400", "가까이 두고 보는 경험·희망",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="당첨 후기에 엽서를 방에 붙이고 후리카케를 매일 흔들겠다는 말이 있다. 휴대 굿즈를 고른 이유는 아니다.")
set_cor("1880605610171154453", "휴대·부착 경험",
       facet_new="휴대·사용이 선택 이유", evidence_level="직접적인 이유·비교", relation="지지",
       judgment_reason="파우치를 보자 룩업 파우치로 쓰기로 했고, 용도에 맞았다고 했다. 귀여움만 이유로 두지 않는다.")
set_cor("2052984507066986677", "휴대·부착 경험",
       relation="중립·관련 언급", evidence_level="명시적 평가·경험",
       judgment_reason="주인을 찾는 동안 여행길에 인형을 챙기겠다는 글이다. 본인이 휴대성을 보고 고른 것은 아니다.")

def unescape(s):
    return (s or "").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def restore_quote(quote, text):
    q = unescape(quote or "")
    t = text or ""
    if q and q in t:
        return q
    parts = [p.strip() for p in re.split(r"\s*/\s*", q) if p.strip()]
    if not parts:
        return t
    starts = []
    ends = []
    cursor = 0
    for p in parts:
        i = t.find(p, cursor)
        if i < 0:
            i = t.find(p)
        if i < 0:
            return q
        starts.append(i)
        ends.append(i + len(p))
        cursor = i + len(p)
    return t[min(starts):max(ends)]

rows = []
for hyp, names in files.items():
    for name in names:
        for r in csv.DictReader(open(work / name, encoding="utf-8", newline="")):
            r = dict(r)
            r["hypothesis"] = hyp
            key = (r["post_id"], r["facet"])
            upd = COR.get(key, {})
            if "facet_new" in upd:
                r["facet"] = upd["facet_new"]
            for k, v in upd.items():
                if k == "facet_new":
                    continue
                r[k] = v
            post = posts[r["post_id"]]
            r["post_url"] = post["post_url"]
            r["account_id"] = post["account_id"]
            r["like_count"] = post["like_count"]
            r["text"] = post["text"]
            r["quote_restored"] = restore_quote(r.get("quote", ""), post["text"])
            r["image_checked"] = "아니오"
            r["image_note"] = "이번 검토는 본문으로 판단했다. 새 이미지 확인은 하지 않았다."
            rows.append(r)

# sanity: restored quote should be in text, allowing the unescape case
bad = 0
for r in rows:
    qt = re.sub(r"\s+", "", r["quote_restored"])
    tx = re.sub(r"\s+", "", r["text"])
    if qt not in tx:
        bad += 1
        print("STILL BAD", r["hypothesis"], r["post_id"], r["quote_restored"][:80])
print("bad_quotes", bad, "rows", len(rows))

outp = work / "corrected_rows.json"
outp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

def uniq(rs, pred):
    return {r["post_id"] for r in rs if pred(r)}

for hyp in ("H1", "H2", "H3"):
    sub = [r for r in rows if r["hypothesis"] == hyp]
    print("\n====", hyp, "rows", len(sub), "posts", len({r["post_id"] for r in sub}))
    print(" relation posts")
    for rel in ["지지", "반대", "혼합", "중립·관련 언급", "판단 불가"]:
        ids = uniq(sub, lambda r, rel=rel: r["relation"] == rel)
        print(f"  {rel} rows {sum(1 for r in sub if r['relation']==rel)} posts {len(ids)}")
    print(" level posts")
    for lev in ["직접적인 이유·비교", "명시적 평가·경험", "단순 공존", "판단 불가"]:
        ids = uniq(sub, lambda r, lev=lev: r["evidence_level"] == lev)
        print(f"  {lev} rows {sum(1 for r in sub if r['evidence_level']==lev)} posts {len(ids)}")
    print(" facet x relation posts")
    fac = defaultdict(lambda: Counter())
    for r in sub:
        fac[r["facet"]][r["relation"]] += 1
    for f, c in sorted(fac.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {f} {dict(c)}")
    # author-only support
    sup = [r for r in sub if r["relation"] == "지지" and r["speaker"] == "작성자 개인"]
    print(" author support posts", len({r["post_id"] for r in sup}), "accounts", len({r["account_id"] for r in sup}))
    direct = [r for r in sub if r["evidence_level"] == "직접적인 이유·비교" and r["relation"] == "지지" and r["speaker"] == "작성자 개인"]
    print(" author direct-support posts", len({r["post_id"] for r in direct}), "accounts", len({r["account_id"] for r in direct}))
    acc = Counter(r["account_id"] for r in sup)
    if acc:
        top = acc.most_common(3)
        print(" top accounts", top, "max share", round(top[0][1] / len(sup), 3) if sup else None)
