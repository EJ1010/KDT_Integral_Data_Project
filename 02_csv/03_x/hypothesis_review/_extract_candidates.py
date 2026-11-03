# -*- coding: utf-8 -*-
"""Extract hypothesis candidate posts for manual review. Does not classify support."""
import csv
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
OUT = BASE / "hypothesis_review" / "_working"
OUT.mkdir(parents=True, exist_ok=True)

posts = list(csv.DictReader(open(BASE / "normalized" / "x_posts.csv", encoding="utf-8-sig", newline="")))
analysis = {}
with open(BASE / "text_analysis_v2" / "x_posts_analysis.csv", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        analysis[row["post_id"]] = row

# Pattern groups. A hit is a candidate, not support.
H1 = {
    "story": r"이야기|스토리|사연|세계관|설정|에피소드|서사|전개|명장면|명대사|뒷이야기|배경설정",
    "personality": r"성격|말투|기특|다정|착해|착하|순수|소심|개성|든든|의리|순둥|순해|겁쟁|용감|착함|착하다",
    "relation": r"우정|케미|콤비|사이가|우정|서로|두 친구|둘의|같이 있|관계성",
    "empathy": r"공감|위로|힐링|짠하|짠해|불쌍|안쓰|안타까|눈물|울었|울어|울컥|뭉클|측은|대리|이입|투영|감정이입|마음\s*아",
    "self": r"내 얘기|나와 같|나랑 같|내 모습|내 일상|나 같아|나도 그래|완전 나|너무 나|나야|나임|나잖아|직장인|회사원|사회생활|퇴사|멘탈|우울",
    "support": r"응원|힘내|화이팅|파이팅|지켜보|입덕|정주행|더 좋아|좋아하게|좋아하는 이유|입덕각|입덕 포인트",
    "labor": r"자격증|급여|풀뽑|풀 뽑|월급|알바|노동|일하|출근|퇴근|시험|합격|불합격|야근|고생|열심히|노력",
    "dark": r"잔인|잔혹|섬뜩|소름|무서|폭력|어둡|불편|괴물|몬스터|귀신|요괴|때리|얻어맞|반전|갭",
    "precious": r"소중|애착|아끼",
}
H2 = {
    "part": r"꼬리|주둥|발바닥|앞발|뒷발|수염|복슬|복실|털이|털복|쫑긋",
    "ear": r"토끼귀|고양이귀|다람쥐귀|긴 귀|큰 귀|작은 귀|귀가 |귀는 |귀를 |귀도 |귀랑 |귀 모양",
    "animal_word": r"동물|의인화|인간형|동물형|수인|케모노|동물같|동물 같|동물캐릭|동물 캐릭",
    "species": r"수달|해달|너구리|다람쥐|날다람|햄스터|토끼|고양이|곰돌|강아지처럼|쥐처럼|고양이처럼|토끼처럼",
    "compare": r"인간형|동물형|사람보다|사람 보다|인간보다|사람 모습|인간 모습|동물 모습|사람이었|인간이면",
}
H3 = {
    "form": r"키링|키홀더|열쇠고리|스마트톡|그립톡|군번줄|폰케이스|에어팟|버즈|파우치|스트랩|뱃지|와펜|러버스트랩|아크릴",
    "carry": r"휴대|들고\s*다|달고\s*다|매달|가방에|가방을|백팩|품에|주머니|포켓|외출|같이 가|함께 가|여행|출근길|데일리",
    "small": r"작아서|조그맣|아담|손바닥|휴대성|미니|작아서 좋|크기",
    "near": r"책상|옆에 두|옆에두|맨날|매일|항상 보|가까이",
    "counter": r"아까워|전시|진열|장식|보관|못 쓰|못쓰|안 쓰|안쓰|개봉 안|안 뜯|안뜯|비닐",
    "bag": r"가방",
}

PROMO = re.compile(
    r"입고|예약|공구|증정|판매합니다|판매해요|샵|스토어|구매\s*링크|폼\b|오픈|특전|재고|품절|원\b|가격|배송|공동구매|나눔|양도|급처|입장"
)


def tags_for(text, groups):
    found = []
    for name, pat in groups.items():
        if re.search(pat, text):
            found.append(name)
    return found


def write_pack(name, id_to_tags):
    path = OUT / f"{name}_candidates.txt"
    items = []
    for row in posts:
        pid = row["post_id"]
        if pid not in id_to_tags:
            continue
        a = analysis.get(pid, {})
        text = row["text"]
        items.append((pid, row, a, id_to_tags[pid], text))
    items.sort(key=lambda x: x[0])
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {name} candidates {len(items)}\n")
        for pid, row, a, tags, text in items:
            promo = "PROMO_HINT" if PROMO.search(text) else "no_promo_hint"
            f.write("\n" + "=" * 80 + "\n")
            f.write(
                f"ID {pid}\nURL {row['post_url']}\nACC {row['account_id']}\n"
                f"LIKE {row['like_count']}\nTAGS {','.join(tags)}\n{promo}\n"
                f"PURPOSE {a.get('purpose_labels','')}\n"
                f"ASPECT {a.get('affection_aspects_author','')}\n"
                f"USE {a.get('use_modes','')}\n"
                f"SPEAKER {a.get('speakers','')}\n"
            )
            f.write(text.replace("\r\n", "\n").replace("\r", "\n"))
            f.write("\n")
    print(name, len(items), path)


h1_map = {}
h2_map = {}
h3_map = {}
for row in posts:
    t = row["text"]
    pid = row["post_id"]
    a = analysis.get(pid, {})
    t1 = tags_for(t, H1)
    asp = a.get("affection_aspects_author", "")
    if "행동·말투·성격" in asp:
        t1.append("prior_personality")
    if "관계·조합·이야기·장면" in asp:
        t1.append("prior_relation")
    if "위로·공감·일상과의 연결" in asp:
        t1.append("prior_empathy")
    if "일상 비유" in a.get("content_uses", ""):
        t1.append("prior_daily_metaphor")
    if t1:
        h1_map[pid] = t1
    t2 = tags_for(t, H2)
    if t2:
        h2_map[pid] = t2
    t3 = tags_for(t, H3)
    use = a.get("use_modes", "")
    for mode in ("휴대", "가방 부착", "실사용", "전시", "보관", "아껴서 미사용"):
        if mode in use:
            t3.append("prior_" + mode)
    if t3:
        h3_map[pid] = t3

write_pack("h1", h1_map)
write_pack("h2", h2_map)
write_pack("h3", h3_map)

# overlap
print("overlap h1&h2", len(set(h1_map) & set(h2_map)))
print("overlap h1&h3", len(set(h1_map) & set(h3_map)))
print("overlap h2&h3", len(set(h2_map) & set(h3_map)))
