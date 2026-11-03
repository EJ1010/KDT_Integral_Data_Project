# -*- coding: utf-8 -*-
"""호감 후보 7,141건의 1차 유형.

절 안에서 이름·특징·호감·이유 표현이 가까이 있는지만 본다.
왜 좋아하는지는 확정하지 않고, 결과를 LLM 판정으로 적지 않는다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

CHAR_DIR = Path(__file__).resolve().parents[1] / "A_캐릭터반응"
sys.path.insert(0, str(CHAR_DIR))
import analyze_A_character_v1 as base  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "A_호감후보" / "A_캐릭터_작품_호감후보_comments.csv"
ROOT = Path(__file__).resolve().parent
RULE = "screen-v2"
METHOD = "키워드·절단위 패턴"

POS = re.compile(
    r"귀엽|귀여|졸귀|기여워|예쁘|이쁘|사랑스럽|사랑|최애|입덕|반했|최고|"
        r"좋아|좋네|좋음|재밌|재미있|매력|정이\s*가|어울리|찰떡|마음에\s*들|심쿵|"
    r"미워(?:할|하)?\s*수(?:가)?\s*없|싫(?:을|어할)?\s*수(?:가)?\s*없"
)
LIKE_BTN = re.compile(r"좋아요\s*(?:눌|부탁)|구독\s*과?\s*좋아요|좋아요\s*구독")
GREET = re.compile(r"좋은\s*(?:하루|밤|꿈|저녁|아침)\s*(?:되|보내|보냅)")
NEG_IDIOM = re.compile(
    r"귀엽지\s*않(?:나|니|을까)|좋지\s*않(?:나|니|을까)|"
    r"미워(?:할|하)?\s*수(?:가)?\s*없|싫(?:을|어\s*할|어할)?\s*수(?:가)?\s*없|"
    r"안\s*(?:미워|싫)"
)
REAL_NEG = re.compile(
    r"안\s*귀엽|못\s*귀엽|안\s*귀여|귀여(?:운|워)?\s*(?:건|것|게|거)\s*(?:아닌|아님|아닐)|"
    r"귀엽지\s*않(?:다|아|어|음)(?!요)|안\s*좋아(?!진|서|하|할)|안\s*좋(?:네|다|음)(?!요)|"
    r"좋지\s*않(?:다|아|어|음)(?!요)|별로|실망|노잼|재미\s*없|재미없|"
    r"싫(?:다|어|음|네)"
)
FALSE_FRAME = re.compile(
    r"좋아하?는\s*(?:사람|분|이들)|누가\s*.{0,8}좋아|누구(?:가|든).{0,8}좋아|"
    r"최애는?\s*누구|좋(?:아|다)고\s*(?:하|들|생각|소문)|서로\s*좋아"
)
WRITER_IN_FRAME = re.compile(r"(?:이|가)?\s*(?:저|나|제)\s*(?:밖에|만|도|가|는)?")
KEEP_POS = re.compile(
    r"안\s*귀여(?:운|워)?(?:\s*게|\s*거|\s*건)?\s*없|"
    r"귀여(?:운|워)?\s*(?:건|것|게|거)\s*아닌(?:가요|가\?|지)"
)
INFO = re.compile(
    r"어디|얼마|가격|몇\s*시|언제|누구|누가|인가요|일까요|맞나요|나와요|나왔나|판매|"
    r"어디서\s*사|살\s*수\s*있"
)
BAD_CAUSE = re.compile(
    r"품절|웨이팅|인터넷|비싸|배송|재고|늦|못\s*가|못\s*사|안\s*사|거리|시간이|돈이"
)
LINKER = re.compile(r"때문에|땜에|뗌에|덕분에|덕에|(?<=[가-힣])(?:아서|어서|해서|니까|라서|길래)")
SPLIT = re.compile(r"[\n!?。]+|(?<!\.)\.(?!\.)|지만|는데|은데|면서|그러나|근데")
JJAP = re.compile(r"짭\s*몽가|짭몽가|짭\s*모몽가")
JIN = re.compile(r"찐\s*몽가|찐몽가")
PICK = re.compile(r"(?:전|저는|난)\s*(?:은|는)?\s*(하치\s*와레|우사기|모몽가|랏코|라코|시사|쿠리\s*만쥬|갑옷\s*씨|치이\s*까?카와)")
WORK = re.compile(r"먼작귀|먼가\s*작고\s*귀여운(?:\s*녀석)?|뭔가\s*작고\s*귀여운")
STAFF_EDIT = re.compile(r"편집|자막|썸네일|빈님|촬영")
STAFF_VA = re.compile(r"성우|더빙|커버")
GOODS = re.compile(r"굿즈|인형|가챠|키링|피규어|파우치|마스코트|타이야|빵|스티커|누이|콜라보|신상|언박싱")
OTHER_IP = re.compile(r"메루카|모루카|농담곰|담곰|히로아카|산리오|뿌이뿌이")
REQUEST = re.compile(r"([가-힣]{2,10})도\s*만들어\s*주")
SHIFT_NEG = re.compile(r"좋아했(?:는데|었는데|다가).{0,40}(?:찌푸|악마|싫어|별로|나가)")
NICK_PERSON = re.compile(r"치이카와님")
VIDEO_AFFECT = re.compile(r"영상|ASMR|포근|편안")
REL = re.compile(r"사이|우정|콤비|베프|칭구")
VIDEO_WORD = re.compile(r"영상")

FEATURES = [
    ("목소리", re.compile(r"목소리|말투|음성|발음")),
    ("외형", re.compile(r"얼굴|눈이|눈빛|귀가|털이|털색|표정|무표정|볼이|볼따구|가르마|꼬리|이빨|동글|작아|조그마|작고|디자인|코스튬|궁디|포즈|포송|주름|콧등|눈썹|하찮|소중|쪼꼬미|말랑|쫀득|눈물|글썽|울먹|뿌애")),
    ("성격", re.compile(r"성격|착해|착하|착둥|순해|순하|소심|용감|다정|기특|열심히|여려|의지|정신력|광기")),
    ("행동", re.compile(r"뛰어|뛰는|달려|달리|먹는\s*(?:거|게|것|모습)|먹방|야무지게\s*먹|춤|댄스|발재간|흔들|뒤뚱|싸워|싸우|도망|챙기|포기|구하|도와")),
    ("관계", re.compile(r"(?<!남자)(?<!여자)친구\s*(?:끼리|사이|랑)|베프|칭구|우정|콤비|사이\s*좋|같이\s*있")),
    ("스토리", re.compile(r"스토리|이야기|세계관|에피소드|설정|결말|전개|분위기")),
    ("굿즈경험", re.compile(r"무광|유광|질감|마감|실물|만졌|크기")),
]
FEAT_ANY = re.compile("|".join(p.pattern for _, p in FEATURES))
CORE = {"특정 캐릭터", "작품 전체", "작품·캐릭터 불명확", "캐릭터 관계"}
STAFF = {"성우·더빙·커버", "제작자·편집"}


def spans(cre, text):
    return [(m.start(), m.end(), m.group()) for m in cre.finditer(text)]


def overlap(a, b):
    return not (a[1] <= b[0] or b[1] <= a[0])


def near(a, b, limit):
    gap = max(a[0], b[0]) - min(a[1], b[1])
    if overlap(a, b):
        return True
    return 0 <= gap <= limit


def live_pos(text):
    blocked = spans(LIKE_BTN, text) + spans(GREET, text)
    for m in FALSE_FRAME.finditer(text):
        # '좋아하는 사람이 저밖에'는 작성자 호감이다. 질문·지목 요청만 뺀다.
        tail = text[m.end():m.end() + 10]
        if m.group().startswith("좋아") and WRITER_IN_FRAME.search(tail):
            continue
        blocked.append((m.start(), m.end(), m.group()))
    neg = [sp for sp in spans(base.NEG_AFFECT, text) if not any(overlap(sp, n) for n in spans(NEG_IDIOM, text))]
    out = []
    for sp in spans(POS, text):
        if any(overlap(sp, b) for b in blocked):
            continue
        if any(overlap(sp, k) for k in spans(KEEP_POS, text)):
            out.append(sp)
            continue
        if re.search(r"먼가\s*작고\s*귀여운[가-힣A-Za-z0-9]{0,8}님", text[max(0, sp[0] - 12):sp[1] + 8]):
            continue
        if any(overlap(sp, n) for n in neg) and not any(overlap(sp, n) for n in spans(NEG_IDIOM, text)):
            continue
        if re.match(r"재밌게\s*(?:놀|보내|지내|보세)", text[sp[0]:sp[0] + 8]):
            continue
        out.append(sp)
    return out


def name_spans(text):
    found = []
    blocked_usagi = bool(base.OPANCHU.search(text))
    for name, cre, kind in base.CHAR_RES:
        if name == "우사기" and blocked_usagi:
            continue
        if name in ("먼작귀",):
            continue
        for m in cre.finditer(text):
            if name == "치이카와":
                if text[m.end():m.end() + 1] == "님" and re.search(r"사과|공론", text) and not re.search(r"귀엽|사랑해|최애", text):
                    continue
                found.append((m.start(), m.end(), "치이카와", "치이카와"))
            elif kind == "캐릭터" or name == "うさぎ":
                found.append((m.start(), m.end(), name, "캐릭터"))
    if JJAP.search(text):
        for m in JJAP.finditer(text):
            found.append((m.start(), m.end(), "모몽가", "캐릭터"))
    for m in WORK.finditer(text):
        tail = text[m.end():m.end() + 10]
        if re.match(r"[가-힣A-Za-z0-9]{0,8}님", tail):
            continue
        found.append((m.start(), m.end(), "먼작귀", "작품"))
    return found


def feature_spans(text):
    out = []
    for label, cre in FEATURES:
        for m in cre.finditer(text):
            out.append((m.start(), m.end(), label))
    return out


def clauses_of(text):
    parts = []
    start = 0
    for m in SPLIT.finditer(text):
        parts.append((start, m.start(), text[start:m.start()]))
        start = m.end()
    parts.append((start, len(text), text[start:]))
    return [(a, b, s) for a, b, s in parts if s.strip()]


def target_at(text, anchor, names):
    """호감·특징 위치에서 가장 가까운 대상. 확정이 아니라 후보이다."""
    window = 18
    cands = []
    for a, b, name, kind in names:
        if near((a, b), anchor, window):
            cands.append((min(abs(anchor[0] - b), abs(a - anchor[1])), kind, name, a))
    staff_e = [(sp, "제작자·편집") for sp in spans(STAFF_EDIT, text)]
    staff_v = [(sp, "성우·더빙·커버") for sp in spans(STAFF_VA, text)]
    goods = [(sp, "굿즈·상품") for sp in spans(GOODS, text)]
    rel = [(sp, "캐릭터 관계") for sp in spans(REL, text)]
    labeled = []
    for (a, b, _), lab in staff_e + staff_v + goods + rel:
        if near((a, b), anchor, 14):
            labeled.append((min(abs(anchor[0] - b), abs(a - anchor[1])), lab, lab, a))
    if not cands and not labeled:
        if VIDEO_WORD.search(text[max(0, anchor[0] - 12):anchor[1] + 12]):
            return "불명확", ""
        return "불명확", ""
    for m in OTHER_IP.finditer(text):
        if near((m.start(), m.end()), anchor, 14):
            labeled.append((min(abs(anchor[0] - m.end()), abs(m.start() - anchor[1])), "기타", "다른작품", m.start()))
    pool = cands + labeled
    pool.sort()
    _, kind, name, _ = pool[0]
    around = text[max(0, anchor[0] - 14):anchor[1] + 14]
    if VIDEO_AFFECT.search(around) and "목소리" not in around and kind in ("치이카와", "캐릭터"):
        return "제작자·편집", name
    if kind == "치이카와":
        if re.search(r"대변|사회전선|2030세대|청년들", text):
            return "작품 전체", name
        personal = any(lab in ("목소리", "외형", "성격", "행동") for _, _, lab in feature_spans(text[max(0, anchor[0] - 18):anchor[1] + 18]))
        # feature_spans on a slice shifts indexes; only the label matters
        return ("특정 캐릭터" if personal else "작품·캐릭터 불명확"), name
    if kind == "캐릭터":
        return "특정 캐릭터", name
    if kind == "작품":
        return "작품 전체", name
    return kind, name


def reason_links(clause, base_at):
    links = []
    for m in LINKER.finditer(clause):
        left = clause[max(0, m.start() - 12):m.start()]
        right = clause[m.end():m.end() + 16]
        if BAD_CAUSE.search(left) or re.search(r"귀여(?:운)?\s*(?:걸|거|것).{0,6}좋아", right):
            continue
        if m.group() in ("어서", "아서") and re.search(r"(?:있|없|같)(?:어서|아서)$", clause[max(0, m.start() - 2):m.end()]):
            left = clause[max(0, m.start() - 6):m.start()]
        person_only = re.search(r"언니|박사|그린넴", left) and not FEAT_ANY.search(left) and not re.search(r"성우|더빙", left)
        if person_only or not POS.search(right):
            continue
        if FEAT_ANY.search(left):
            feat = next(lab for lab, cre in FEATURES if cre.search(left))
        elif re.search(r"성우|더빙", left):
            feat = "목소리"
        elif re.search(r"귀엽|재밌|재미|매력|하찮|사랑", left):
            feat = "포괄표현"
        else:
            continue
        abs_left = base_at + max(0, m.start() - 22)
        quote = clause[max(0, m.start() - 22):m.end() + 18].strip()
        links.append({
            "kind": 3,
            "feat": feat,
            "quote": quote,
            "at": abs_left,
            "linker": m.group(),
        })
    return links


def classify_text(text, irony=False):
    text = base.clean(text)
    names = name_spans(text)
    feats_all = feature_spans(text)
    pos_all = live_pos(text)
    neg_spans = []
    for sp in spans(REAL_NEG, text):
        if any(overlap(sp, n) for n in spans(NEG_IDIOM, text) + spans(KEEP_POS, text)):
            continue
        pre = text[max(0, sp[0] - 10):sp[0]]
        if re.search(r"가격|돈이|플미|배송|구하", pre):
            continue
        if text[sp[0]:sp[1]] == "별로" and re.match(r"\s*없", text[sp[1]:sp[1] + 3]):
            continue
        if text.startswith("실망시", sp[0]):
            continue
        if "별로" in text[sp[0]:sp[1]] and text[max(0, sp[0] - 1):sp[0]] in ("똥", "별"):
            continue
        if "별로" in text[sp[0]:sp[1]] and re.search(r"조회수.{0,12}별로|별로\s*못\s*봤|별로\s*안\s*나", text[max(0, sp[0] - 10):sp[1] + 6]):
            continue
        neg_spans.append(sp)
    for m in SHIFT_NEG.finditer(text):
        neg_spans.append((m.start(), m.end(), m.group()))
    links = []
    ambiguous = []
    prev = None
    for a, b, clause in clauses_of(text):
        local_pos = [sp for sp in pos_all if a <= sp[0] < b]
        local_feat = [sp for sp in feats_all if a <= sp[0] < b]
        local_names = [sp for sp in names if a <= sp[0] < b]
        own_names = list(local_names)
        own_feats = list(local_feat)
        # 물음표·는데 뒤에서 이름 없이 짧은 호감만 남은 경우, 직전 절의 이름 하나를 이어 본다.
        if prev and local_pos and not local_names and len(clause.strip()) <= 40:
            if not re.search(r"영상|편집|가격|플미|배송|감사|박사|빈님|구독", clause):
                prev_names = [n for n in prev["names"] if n[3] in ("캐릭터", "작품", "치이카와")]
                uniq_prev = list(dict.fromkeys(n[2] for n in prev_names))
                if len(uniq_prev) == 1:
                    local_names = prev_names
                    if not prev["pos"]:
                        local_feat = local_feat + prev["feats"]
        local_neg = [sp for sp in neg_spans if a <= sp[0] < b]
        reasons = reason_links(clause, a)
        if local_neg and (local_pos or local_names or local_feat):
            # 다른 절의 구매 실패·배송은 위에서 BAD가 아니라 부정 단어가 아닐 수 있다.
            quote = clause.strip()[:80]
            same_target = True
            if local_neg and local_pos:
                # 부정과 호감 사이에 다른 이름만 있고 거리가 멀면 보류
                for ns in local_neg:
                    for ps in local_pos:
                        if not near(ns, ps, 24) and len(local_names) >= 2:
                            same_target = False
            if same_target:
                links.append({"kind": 5, "feat": "", "quote": quote, "at": a, "linker": ""})
            else:
                ambiguous.append("부정 대상이 갈림")
        for rk in reasons:
            anchor = (rk["at"], rk["at"] + 8)
            lab, who = target_at(clause, (max(0, rk["at"] - a), max(0, rk["at"] - a) + 8), [(n[0] - a, n[1] - a, n[2], n[3]) for n in local_names] or [(n[0] - a, n[1] - a, n[2], n[3]) for n in names])
            rk["target"] = lab
            rk["who"] = who
            links.append(rk)
        used_pos = set()
        staff_rel = spans(STAFF_EDIT, clause) + spans(STAFF_VA, clause)
        for ft in local_feat:
            ft_rel = (ft[0] - a, ft[1] - a)
            for ps in local_pos:
                ps_rel = (ps[0] - a, ps[1] - a)
                if not near(ft, ps, 24):
                    continue
                between_staff = any(min(ft_rel[0], ps_rel[0]) < s[0] < max(ft_rel[1], ps_rel[1]) for s in staff_rel)
                names_near = [n for n in local_names if near((n[0], n[1]), ft, 16)]
                only_name = list(dict.fromkeys(n[2] for n in local_names if n[3] in ("캐릭터", "작품", "치이카와")))
                goods_near = any(near((s[0] + a, s[1] + a), ft, 16) for s in spans(GOODS, clause))
                if len({n[2] for n in names_near}) >= 2 or (not names_near and len(only_name) >= 2):
                    ambiguous.append("특징 옆에 이름이 둘")
                    links.append({
                        "kind": 2, "feat": ft[2],
                        "quote": text[max(0, min(ft[0], ps[0]) - 8):max(ft[1], ps[1]) + 8].strip(),
                        "at": ft[0], "linker": "", "target": "복수 대상", "who": "",
                    })
                    used_pos.add(ps[0])
                    continue
                if not names_near and len(only_name) != 1 and not goods_near:
                    continue
                if between_staff and not names_near:
                    ambiguous.append("특징과 제작 표현이 겹침")
                    continue
                lab, who = target_at(clause, ft_rel, [(n[0] - a, n[1] - a, n[2], n[3]) for n in local_names])
                if not who and len(only_name) == 1:
                    who = only_name[0]
                    if who == "먼작귀":
                        lab = "작품 전체"
                    elif who != "치이카와":
                        lab = "특정 캐릭터"
                if who == "치이카와" and ft[2] in ("목소리", "외형", "성격", "행동"):
                    lab = "특정 캐릭터"
                elif who == "치이카와" and ft[2] == "스토리":
                    lab = "작품 전체"
                if ft[2] == "굿즈경험":
                    lab, who = "굿즈·상품", who
                if lab == "불명확" and not goods_near:
                    continue
                if JIN.search(text[max(0, ps[0] - 12):ps[1] + 8]) and not JJAP.search(text[max(0, ps[0] - 12):ps[1] + 8]):
                    ambiguous.append("찐몽가 별칭 미확대")
                    continue
                staff_closer = any(near((s[0], s[1]), ps_rel, 12) and not near(ft_rel, ps_rel, 12) for s in staff_rel)
                if staff_closer:
                    continue
                links.append({
                    "kind": 2,
                    "feat": ft[2],
                    "quote": text[max(0, min(ft[0], ps[0]) - 8):max(ft[1], ps[1]) + 8].strip(),
                    "at": ft[0],
                    "linker": "",
                    "target": lab,
                    "who": who,
                })
                used_pos.add(ps[0])
        for ps in local_pos:
            if ps[0] in used_pos:
                continue
            lab, who = target_at(clause, (ps[0] - a, ps[1] - a), [(n[0] - a, n[1] - a, n[2], n[3]) for n in local_names])
            # 이름·작품·굿즈·제작 중 하나는 절 안에 있어야 단순 호감으로 본다.
            near_names = [n for n in local_names if near((n[0], n[1]), ps, 22)]
            only_name = list(dict.fromkeys(n[2] for n in local_names if n[3] in ("캐릭터", "작품", "치이카와")))
            near_other = (
                any(near((s[0] + a, s[1] + a), ps, 18) for s in spans(GOODS, clause) + spans(STAFF_EDIT, clause) + spans(STAFF_VA, clause) + spans(WORK, clause))
            )
            # 절에 이름이 하나뿐이면 그 절의 호감을 그 이름으로 본다. 둘이면 가까운 쪽만 본다.
            if len(only_name) == 1:
                near_names = [n for n in local_names if n[2] == only_name[0]] or near_names
            elif not near_names and not near_other:
                continue
            if len({n[2] for n in near_names}) >= 2 and not (GOODS.search(clause) or STAFF_EDIT.search(clause)):
                ambiguous.append("호감 옆에 이름이 둘")
                links.append({"kind": 4, "feat": "", "quote": clause.strip()[:80], "at": ps[0], "linker": "", "target": "복수 대상", "who": ""})
                continue
            req = False
            for m in REQUEST.finditer(text):
                same = who and (who in m.group(0) or (who == "라코" and m.group(1).startswith("랏")))
                if same and ps[0] < m.start():
                    req = True
            if req:
                lab = "제작자·편집"
                who = ""
            links.append({
                "kind": 1,
                "feat": "",
                "quote": clause.strip()[:80],
                "at": ps[0],
                "linker": "",
                "target": lab,
                "who": "" if req else who,
            })
        prev = {"names": own_names, "feats": own_feats, "pos": [sp for sp in pos_all if a <= sp[0] < b]}
    if names and any(near((m.start(), m.end()), (p[0], p[1]), 18) for m in STAFF_VA.finditer(text) for p in pos_all):
        links.append({
            "kind": 0, "feat": "", "quote": "", "at": 0, "linker": "",
            "target": "성우·더빙·커버", "who": "",
        })
    # 호감은 있는데 어느 절에도 이름이 없고 질문·정보이면 6의 후보다.
    info_only = bool(INFO.search(text)) and not pos_all
    kinds = {lk["kind"] for lk in links}
    aux = []
    hold = []
    if irony:
        primary = 4
        hold.append("반어_검토")
        for k in (3, 2, 1, 5):
            if k in kinds:
                aux.append(k)
    elif 5 in kinds:
        primary = 5
        hold.append("긍정·부정 또는 부정")
        for k in (3, 2, 1):
            if k in kinds:
                aux.append(k)
    elif ambiguous and 3 not in kinds and 2 not in kinds:
        primary = 4
        hold.extend(ambiguous)
    elif 3 in kinds:
        primary = 3
        for k in (2, 1, 5):
            if k in kinds and k != 3:
                aux.append(k)
        if ambiguous:
            hold.extend(ambiguous)
    elif 2 in kinds:
        primary = 2
        if 1 in kinds:
            aux.append(1)
        if ambiguous:
            hold.extend(ambiguous)
    elif 4 in kinds and 1 not in kinds:
        primary = 4
        hold.extend(ambiguous or ["대상 연결이 불명확"])
    elif 1 in kinds:
        # 같은 댓글의 다른 절에만 특징이 있으면 연결하지 않는다.
        # 호감 절 안에 특징이 있었는데 연결이 거절된 경우만 4.
        if ambiguous:
            primary = 4
            hold.extend(ambiguous)
            aux.append(1)
        else:
            primary = 1
    elif not links and PICK.search(text) and not irony:
        primary = 1
        hold.append("짧은 최애 지목")
        m = PICK.search(text)
        links.append({"kind": 1, "feat": "", "quote": m.group(), "at": m.start(), "linker": "", "target": "특정 캐릭터", "who": m.group()})
    elif not pos_all and (INFO.search(text) or FALSE_FRAME.search(text)):
        primary = 6
        hold.append("질문·정보·묘사")
    else:
        primary = 4
        hold.append("규칙으로 유형을 안정적으로 나누기 어려움")

    targets = []
    whos = []
    feat_labels = []
    linkers = []
    quotes = []
    for lk in links:
        if lk["kind"] == 0 or lk["kind"] == primary or (primary == 4 and lk["kind"] in (1, 2, 3, 4)) or (primary == 5 and lk["kind"] in (5, 2, 3)):
            if lk.get("target"):
                targets.append(lk["target"])
            if lk.get("who"):
                whos.append(lk["who"])
            if lk.get("feat"):
                feat_labels.append(lk["feat"])
            if lk.get("linker"):
                linkers.append(lk["linker"])
            if lk.get("quote"):
                quotes.append(lk["quote"])
    if not any(quotes):
        m = POS.search(text)
        if m:
            quotes.append(text[max(0, m.start() - 16):m.end() + 16].strip())
        elif text:
            quotes.append(text[:60].strip())
    if not targets:
        for lk in links:
            if lk.get("target"):
                targets.append(lk["target"])
            if lk.get("who"):
                whos.append(lk["who"])
    # 치이카와 표기만 있고 개인 특징이 없으면 불명확을 유지한다.
    all_targets = [lk.get("target") for lk in links if lk["kind"] in (0, 1, 2, 3) and lk.get("target")]
    all_whos = [lk.get("who") for lk in links if lk["kind"] in (1, 2, 3) and lk.get("who")]
    # 치이카와 표기와 작품 표기가 같은 평가에서 같이 나와도 복수 대상으로 세지 않는다.
    distinct_who = [w for w in dict.fromkeys(all_whos) if w not in ("치이카와", "먼작귀")]
    mixed_domain = ("굿즈·상품" in all_targets or "제작자·편집" in all_targets or "성우·더빙·커버" in all_targets) and (
        "특정 캐릭터" in all_targets or "작품 전체" in all_targets or "작품·캐릭터 불명확" in all_targets
    )
    if len(distinct_who) >= 2 or mixed_domain:
        targets = list(dict.fromkeys(all_targets))
        whos = list(dict.fromkeys(all_whos))
    uniq_t = list(dict.fromkeys(targets))
    if len(uniq_t) >= 2:
        target = "복수 대상"
    elif uniq_t:
        target = uniq_t[0]
    else:
        target = "불명확"
    multi = "예" if len(uniq_t) >= 2 or "복수 대상" in uniq_t else ""
    if "이름이 둘" in " ".join(hold):
        multi = "예"
        if target == "불명확":
            target = "복수 대상"
    # 호감 바로 옆에 캐릭터 이름이 둘 이상이면 한 명으로 모으지 않는다.
    near_who = []
    for ps in pos_all:
        for n in names:
            if n[3] in ("캐릭터", "치이카와", "작품") and near((n[0], n[1]), ps, 18):
                near_who.append(n[2])
    if len(set(near_who)) >= 2 and target == "특정 캐릭터":
        target = "복수 대상"
        multi = "예"
        uniq_t = list(dict.fromkeys(list(uniq_t) + ["복수 대상"]))
    if target == "불명확" and re.search(r"애니|만화", text) and any(n[2] in ("치이카와", "먼작귀") for n in names):
        target = "작품 전체"
        uniq_t = list(dict.fromkeys(list(uniq_t) + ["작품 전체"]))
    elif target == "불명확" and any(n[2] == "치이카와" for n in names) and primary in (2, 3):
        target = "작품·캐릭터 불명확"
        uniq_t = list(dict.fromkeys(list(uniq_t) + ["작품·캐릭터 불명확"]))
    if target == "특정 캐릭터" and re.search(r"대변|사회전선|2030세대", text):
        target = "작품 전체"
    if re.search(r"포근|ASMR", text) and re.search(r"영상", text) and target == "특정 캐릭터":
        target = "작품·캐릭터 불명확"
        hold.append("포근함은 영상 평가")
    rule = {
        1: "S1-단순호감",
        2: "S2-특징근접",
        3: "S3-이유절",
        4: "S4-보류",
        5: "S5-부정혼합",
        6: "S6-질문정보",
    }[primary]
    if irony and primary == 4:
        rule = "S4-반어"
    chars = list(dict.fromkeys(n[2] for n in names if n[3] == "캐릭터" or n[2] == "모몽가"))
    if any(n[2] == "치이카와" for n in names) and target == "특정 캐릭터" and "치이카와" not in chars:
        chars.append("치이카와")
    return {
        "primary": primary,
        "aux": "|".join(str(k) for k in dict.fromkeys(aux)),
        "target": target,
        "details": "|".join(uniq_t),
        "chars": "|".join(dict.fromkeys(whos or chars)),
        "feats": "|".join(dict.fromkeys(feat_labels)),
        "linkers": "|".join(dict.fromkeys(linkers)),
        "neg": "예" if 5 in kinds or neg_spans else "",
        "multi": multi,
        "quote": " / ".join(dict.fromkeys(q for q in quotes if q))[:180],
        "rule": rule,
        "hold": "|".join(dict.fromkeys(hold)),
        "text": text,
    }


def priority_of(row):
    details = set(filter(None, str(row["평가대상_세부"]).split("|")))
    aux = set(filter(None, str(row["보조_유형"]).split("|")))
    primary = str(row["1차_주유형"])
    has_core = bool(details & CORE)
    has_goods = "굿즈·상품" in details
    only_staff = bool(details) and details <= STAFF
    clue = bool(row["검출_특징"] or row["검출_이유연결표현"] or aux & {"2", "3"})
    va = "목소리" in str(row["검출_특징"]) and bool(STAFF_VA.search(str(row["댓글_정규화"])))
    num = primary.split("_", 1)[0]
    if num == "4" or (num == "5" and clue) or (va and num in ("2", "3")):
        return "재검토"
    if num in ("2", "3") and (has_core or "복수 대상" in details or str(row["평가대상_후보"]) == "복수 대상"):
        return "우선"
    if num in ("2", "3") and has_goods:
        return "별도_굿즈"
    if only_staff:
        return "핵심대상_밖"
    return "보관"


def main():
    checks = [
        ("하치와레 귀여워", 1, "특정 캐릭터"),
        ("치이카와 귀여워", 1, "작품·캐릭터 불명확"),
        ("치이카와 목소리 너무 귀여워", 2, "특정 캐릭터"),
        ("친구 챙기는 모습 때문에 하치와레가 좋아", 3, None),
        ("우사기 어디 나와요?", 6, None),
        ("우사기 안 귀여워", 5, None),
        ("하치와레 귀엽지 않나요?", 1, None),
        ("미워할 수가 없어 하치와레", 1, None),
        ("품절이라 못 사서 슬퍼 하치와레 귀여워", 1, None),
        ("우사기 영상 편집이 좋아요", 1, "제작자·편집"),
        ("하치와레 귀여운거 아닌가요", 1, None),
        ("치이카와 귀여운데 가격은 안귀엽네요", 1, None),
        ("모몽가 콧등 주름? 귀여워", 2, "특정 캐릭터"),
        ("모몽가 좋아하는 사람이 저밖에 없었어요", 1, "특정 캐릭터"),
        ("치이카와 애니를 보다보니 귀엽고 재밌어서 좋아졌다", 3, None),
        ("하치와레 사랑해 우리 착둥이", 2, "특정 캐릭터"),
        ("우사기가 서로 좋아하는게 보임", 6, None),
    ]
    for text, exp, tgt in checks:
        got = classify_text(text)
        if got["primary"] != exp:
            raise SystemExit(f"점검 실패 {text!r} → {got['primary']} {got['rule']} {got['hold']}")
        if tgt and got["target"] != tgt:
            raise SystemExit(f"대상 실패 {text!r} → {got['target']} {got['details']}")

    df = pd.read_csv(SRC, encoding="utf-8-sig")
    if len(df) != 7141 or df["comment_id"].duplicated().any() or df["comment_id"].isna().any():
        raise SystemExit(f"입력 이상 {len(df)}")
    rows = []
    for rec in df.itertuples(index=False):
        irony = "반어" in str(getattr(rec, "평가대상_재검토") or "")
        got = classify_text(rec.댓글원문 if isinstance(rec.댓글원문, str) else "", irony=irony)
        # 근거는 정규화 원문의 부분문자열이어야 한다.
        for part in got["quote"].split(" / "):
            if part and part not in got["text"]:
                got["quote"] = got["text"][:40]
                got["hold"] = (got["hold"] + "|근거문구는 댓글 앞부분").strip("|")
                break
        label = f"{got['primary']}_{['','단순호감','특징호감후보','이유설명후보','모호한후보','부정혼합후보','호감근거없음후보'][got['primary']]}"
        rows.append({
            "1차_주유형": label,
            "보조_유형": got["aux"],
            "평가대상_후보": got["target"],
            "평가대상_세부": got["details"],
            "1차_연결캐릭터": got["chars"],
            "검출_특징": got["feats"],
            "검출_이유연결표현": got["linkers"],
            "긍정부정_충돌": "예" if got["neg"] else "",
            "복수대상_검토": got["multi"],
            "판정_근거문구": got["quote"],
            "판정_규칙ID": got["rule"],
            "보류_사유": got["hold"],
            "판정방법": METHOD,
            "판정_규칙버전": RULE,
            "댓글_정규화": got["text"],
        })
    extra = pd.DataFrame(rows)
    out = pd.concat([df.reset_index(drop=True), extra], axis=1)
    out["심층분석_우선순위"] = out.apply(priority_of, axis=1)
    if not out["comment_id"].equals(df["comment_id"]):
        raise SystemExit("ID 순서가 달라졌다")
    if set(out["comment_id"]) != set(df["comment_id"]) or out["comment_id"].duplicated().any():
        raise SystemExit("ID 불일치")

    out.to_csv(ROOT / "A_호감후보_1차유형_comments.csv", index=False, encoding="utf-8-sig")

    def has_type(series, code):
        return series.fillna("").map(lambda s: code in str(s).split("|"))

    core_mask = out["평가대상_세부"].fillna("").map(lambda s: bool(set(str(s).split("|")) & CORE))
    aux23 = has_type(out["보조_유형"], "2") | has_type(out["보조_유형"], "3")
    main23 = out["1차_주유형"].str.startswith(("2_", "3_"))
    multi_mask = out["평가대상_후보"].eq("복수 대상")
    priority_file = out[(main23 | aux23) & (core_mask | multi_mask)].copy()
    goods_mask = out["평가대상_세부"].fillna("").str.contains("굿즈")
    goods_file = out[goods_mask & (main23 | aux23)].copy()
    review_file = out[
        out["1차_주유형"].str.startswith("4_")
        | (out["1차_주유형"].str.startswith("5_") & (aux23 | out["검출_특징"].fillna("").ne("") | out["검출_이유연결표현"].fillna("").ne("")))
        | (out["검출_특징"].fillna("").str.contains("목소리") & out["댓글_정규화"].map(lambda s: bool(STAFF_VA.search(str(s)))) & main23)
    ].copy()
    priority_file.to_csv(ROOT / "A_호감후보_우선분석.csv", index=False, encoding="utf-8-sig")
    review_file.to_csv(ROOT / "A_호감후보_재검토.csv", index=False, encoding="utf-8-sig")
    goods_file.to_csv(ROOT / "A_호감후보_굿즈.csv", index=False, encoding="utf-8-sig")

    samples = []
    for key, sub in out.groupby("1차_주유형", sort=True):
        take = sub.sample(n=min(20, len(sub)), random_state=20261103)
        samples.append(take)
    sample = pd.concat(samples, ignore_index=True)
    sample["검수상태"] = "사람 검수 미실시"
    sample["사람검수"] = ""
    sample["검수메모"] = ""
    sample.to_csv(ROOT / "A_호감후보_검수표본.csv", index=False, encoding="utf-8-sig")

    both_pr = len(set(priority_file["comment_id"]) & set(review_file["comment_id"]))
    both_pg = len(set(priority_file["comment_id"]) & set(goods_file["comment_id"]))
    both_rg = len(set(review_file["comment_id"]) & set(goods_file["comment_id"]))
    summary = pd.DataFrame([
        ["입력", len(df)],
        ["출력", len(out)],
        ["ID일치", int(set(out.comment_id) == set(df.comment_id))],
        ["중복", int(out.comment_id.duplicated().sum())],
        ["우선파일", len(priority_file)],
        ["우선파일_영상", int(priority_file.post_id.nunique())],
        ["우선파일_채널", int(priority_file.account_id.nunique())],
        ["재검토파일", len(review_file)],
        ["재검토파일_영상", int(review_file.post_id.nunique())],
        ["재검토파일_채널", int(review_file.account_id.nunique())],
        ["굿즈파일", len(goods_file)],
        ["우선과재검토_겹침", both_pr],
        ["우선과굿즈_겹침", both_pg],
        ["재검토와굿즈_겹침", both_rg],
    ], columns=["항목", "값"])
    summary.to_csv(ROOT / "00_집계_범위.csv", index=False, encoding="utf-8-sig")
    out["1차_주유형"].value_counts().rename_axis("1차_주유형").reset_index(name="댓글").to_csv(
        ROOT / "00_주유형.csv", index=False, encoding="utf-8-sig"
    )
    out["평가대상_후보"].value_counts().rename_axis("평가대상_후보").reset_index(name="댓글").to_csv(
        ROOT / "00_평가대상.csv", index=False, encoding="utf-8-sig"
    )
    out["심층분석_우선순위"].value_counts().rename_axis("심층분석_우선순위").reset_index(name="댓글").to_csv(
        ROOT / "00_우선순위.csv", index=False, encoding="utf-8-sig"
    )
    old = pd.read_csv(
        Path(__file__).resolve().parents[1] / "90_보관" / "A_호감후보_1차유형" / "A_호감후보_1차유형_comments.csv",
        encoding="utf-8-sig",
        usecols=["comment_id", "1차_주유형", "심층분석_우선순위", "평가대상_후보"],
    )
    chg = out[["comment_id", "1차_주유형", "심층분석_우선순위", "평가대상_후보", "보조_유형"]].merge(
        old, on="comment_id", suffixes=("_수정", "_이전")
    )
    chg["주유형변경"] = chg["1차_주유형_이전"] != chg["1차_주유형_수정"]
    chg["우선순위변경"] = chg["심층분석_우선순위_이전"] != chg["심층분석_우선순위_수정"]
    chg["대상변경"] = chg["평가대상_후보_이전"] != chg["평가대상_후보_수정"]
    chg.to_csv(ROOT / "00_변경.csv", index=False, encoding="utf-8-sig")
    print("변경", int(chg["주유형변경"].sum()), int(chg["우선순위변경"].sum()), int(chg["대상변경"].sum()))
    print(out["1차_주유형"].value_counts().to_string())
    print(out["평가대상_후보"].value_counts().to_string())
    print(out["심층분석_우선순위"].value_counts().to_string())
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
