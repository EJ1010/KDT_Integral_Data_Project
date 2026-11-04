# -*- coding: utf-8 -*-
"""Pull the lines that triggered candidate tags, plus one neighboring line."""
import re
from pathlib import Path

SRC = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\hypothesis_review\_working")

# same groups as extractor
H1 = {
    "story": r"이야기|스토리|사연|세계관|설정|에피소드|서사|전개|명장면|명대사|뒷이야기|배경설정",
    "personality": r"성격|말투|기특|다정|착해|착하|순수|소심|개성|든든|의리|순둥|순해|겁쟁|용감|착함|착하다",
    "relation": r"우정|케미|콤비|사이가|서로|두 친구|둘의|같이 있|관계성",
    "empathy": r"공감|위로|힐링|짠하|짠해|불쌍|안쓰|안타까|눈물|울었|울어|울컥|뭉클|측은|대리|이입|투영|감정이입|마음\s*아",
    "self": r"내 얘기|나와 같|나랑 같|내 모습|내 일상|나 같아|나도 그래|완전 나|너무 나|나야|나임|나잖아|직장인|회사원|사회생활|퇴사|멘탈|우울",
    "support": r"응원|힘내|화이팅|파이팅|지켜보|입덕|정주행|더 좋아|좋아하게|좋아하는 이유|입덕각|입덕 포인트",
    "labor": r"자격증|급여|풀뽑|풀 뽑|월급|알바|노동|일하|출근|퇴근|시험|합격|불합격|야근|고생|열심히|노력",
    "dark": r"잔인|잔혹|섬뜩|소름|무서|폭력|어둡|불편|괴물|몬스터|귀신|요괴|때리|얻어맞|반전|갭",
    "precious": r"소중|애착|아끼",
    "prior": r"prior_",
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

GROUPS = {"h1": H1, "h2": H2, "h3": H3}


def split_posts(text):
    chunks = text.split("=" * 80)
    posts = []
    for ch in chunks:
        ch = ch.strip()
        if not ch.startswith("ID "):
            continue
        lines = ch.splitlines()
        meta = {}
        body_start = 0
        for i, line in enumerate(lines):
            if line.startswith("ID "):
                meta["id"] = line[3:].strip()
            elif line.startswith("URL "):
                meta["url"] = line[4:].strip()
            elif line.startswith("ACC "):
                meta["acc"] = line[4:].strip()
            elif line.startswith("LIKE "):
                meta["like"] = line[5:].strip()
            elif line.startswith("TAGS "):
                meta["tags"] = line[5:].strip()
            elif line.startswith("PURPOSE "):
                meta["purpose"] = line[8:].strip()
            elif line.startswith("ASPECT "):
                meta["aspect"] = line[7:].strip()
            elif line.startswith("USE "):
                meta["use"] = line[4:].strip()
            elif line.startswith("SPEAKER "):
                body_start = i + 1
                break
        body = "\n".join(lines[body_start:]).strip()
        posts.append((meta, body))
    return posts


def snippet_lines(body, group):
    lines = body.splitlines()
    # also treat the whole body as sentences split by punctuation if one line
    units = []
    for i, line in enumerate(lines):
        units.append((i, line))
    hit_idx = set()
    compiled = [(name, re.compile(pat)) for name, pat in group.items() if name != "prior"]
    for i, line in units:
        for name, rx in compiled:
            if rx.search(line):
                hit_idx.add(i)
                break
    # prior-only posts: keep full body short
    if not hit_idx:
        return [body[:500]]
    kept = []
    seen = set()
    for i in sorted(hit_idx):
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(lines) and j not in seen:
                s = lines[j].strip()
                if s:
                    kept.append(s)
                    seen.add(j)
    return kept


for key, group in GROUPS.items():
    raw = (SRC / f"{key}_candidates.txt").read_text(encoding="utf-8")
    posts = split_posts(raw)
    out = SRC / f"{key}_snippets.txt"
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# {key} snippet review n={len(posts)}\n")
        for meta, body in posts:
            snips = snippet_lines(body, group)
            f.write("\n---\n")
            f.write(f"{meta.get('id')} | {meta.get('acc')} | like={meta.get('like')} | {meta.get('tags')}\n")
            f.write(f"purpose={meta.get('purpose')} | aspect={meta.get('aspect')} | use={meta.get('use')}\n")
            for s in snips:
                f.write("· " + s.replace("\t", " ") + "\n")
            if len(body) <= 280:
                f.write("FULL " + body.replace("\n", " / ") + "\n")
    print(key, len(posts), out, out.stat().st_size)
