# -*- coding: utf-8 -*-
"""기준서 v1으로 X 게시물 5,000건을 분류한다.

시험 100건은 classification_pilot.py의 수동 판정을 유지한다.
나머지 4,900건은 본문 문맥 규칙으로 분류한다. 검색 키워드 컬럼은 쓰지 않는다.
기준서에 없는 이름은 라벨로 만들지 않고 보류 후보로만 남긴다.

실행: py -3.11 classify_x_posts.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = Path(r"C:/DATA/KDT_Integral_Data_Project/02_csv/03_x")
PARQUET = BASE / "typed" / "x_chiikawa_2022_2026_typed.parquet"
OUT_DIR = BASE / "classification"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
FINAL_PARQUET = OUT_DIR / "x_posts_classified.parquet"
FINAL_CSV = OUT_DIR / "x_posts_classified.csv"
REVIEW_CSV = OUT_DIR / "classification_review_required.csv"
PROGRESS = OUT_DIR / "classification_progress.jsonl"
CODEBOOK_VERSION = "v1"
BATCH = 1000

sys.path.insert(0, str(OUT_DIR))
PILOT_PATH = OUT_DIR / "classification_pilot.py"
spec = importlib.util.spec_from_file_location("classification_pilot", PILOT_PATH)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)

SERIES = pilot.SERIES
CHARACTERS = pilot.CHARACTERS
FORMS = pilot.FORMS
BEHAVIORS = pilot.BEHAVIORS
OK, NO, ASK, NA = "분류 가능", "미언급", "확인 필요", "해당 없음"

import re

FLAGS = re.IGNORECASE

def R(pattern):
    return re.compile(pattern, FLAGS)


OPP = R(r"오빤쮸우사기|오빠쮸우사기")
FULL_CHAR = [
    ("hachiware", R(r"하치와레|하칰와레|ハチワレ|패러랠\s*하치|hachiware")),
    ("usagi", R(r"우사기|うさぎ|(?<![A-Za-z])usagi(?![A-Za-z])")),
    ("momonga", R(r"모몽가|모몬가|モモンガ")),
    ("kurimanju", R(r"쿠리만쥬|쿠리만주|くりまんじゅう")),
    ("rakko", R(r"해달랭커|랏코|ラッコ|(?<![A-Za-z])rakko(?![A-Za-z])")),
    ("yoroi", R(r"갑옷씨")),
    ("shisa", R(r"(?<![가-힣])시사(?![가-힣])")),
]
CHI = R(r"치이카와|치익카와|ちいかわ|吉伊卡哇|(?<![A-Za-z])chiikawa(?![A-Za-z])")
PRODUCT = R(
    r"인형|누이|ぬい|피규어|フィギュア|소프비|키링|키체인|굿즈|가챠|이모티콘|"
    r"영화|개봉|다이어리|스티커|뱃지|배지|캔배지|파우치|팝업|해피밀|저금통|"
    r"마스코트|콜라보|마켓|캡슐|그립톡|장패드|캐리어|지갑|조명|라이트|액자|"
    r"지우개|도장|유니폼|문구|과자|세트|예약|판매|공구|누들"
)
PEER_SPLIT = R(r"와|과|랑|·|ㆍ|,|，|/|＆|&|하고|그리고")
CHAR_BODY = R(r"발톱|생일|놀란|목소리|의\s*꿈|꿈\s*\d")
HASH_CHI = R(r"#\s*(치이카와|ちいかわ|chiikawa|吉伊卡哇)")
HASH_MON = R(r"#\s*먼작귀")
MON = R(r"먼작귀")
NEG = R(r"치이카와(?:는|가|도|의)?\s*(?:애들은?\s*)?(?:아니지만|아니고|아님|아니다)")
SHORT = {
    "chiikawa": R(r"(?<![가-힣])치이(?![가-힣])"),
    "hachiware": R(r"(?<![가-힣])하치(?![가-힣])"),
    "usagi": R(r"(?<![가-힣])우사(?![가-힣])"),
    "kurimanju": R(r"(?<![가-힣])쿠리(?![가-힣])"),
}
HELD = [
    ("아노코", R(r"아노코")),
    ("오데", R(r"(?<![가-힣])오데(?![가-힣])")),
    ("포토카드", R(r"(?<![가-힣])포카(?![가-힣])")),
    ("아크릴", R(r"아크릴")),
    ("데카츠요(통칭)", R(r"데카츠요")),
]
FORM_PATTERNS = [
    ("plush", R(r"누이구루미|ぬいぐるみ|(?<![가-힣])누이(?![가-힣를은])|(?<![가-힣])인형(?!옷)|마스코트|소프비\s*퍼펫")),
    ("figure", R(r"피규어|フィギュア|소프비|누들스토퍼|누들\s*스토퍼")),
    ("keyring", R(r"키링|키체인")),
    ("badge", R(r"캔배지|뱃지|배지")),
    ("stationery", R(r"스티커|sticker|다이어리|지우개|도장")),
    ("apparel", R(r"유니폼|후드티|후드|티셔츠|의류")),
    ("wallet", R(r"지갑")),
    ("pouch", R(r"파우치")),
    ("carrier", R(r"캐리어")),
    ("deskad", R(r"장패드")),
    ("griptok", R(r"그립톡")),
    ("light", R(r"スタンドライト|스탠드\s*라이트|조명")),
    ("coin_bank", R(r"저금통")),
    ("food", R(r"해피밀")),
    ("digital", R(r"이모티콘")),
    ("video", R(r"유튜브|youtube|영상|애니")),
    ("movie", R(r"영화|극장판|극장")),
    ("book", R(r"만화|\d+\s*권")),
    ("game", R(r"좀비고|게임")),
    ("popup", R(r"팝업")),
    ("frame", R(r"액자")),
    ("prop", R(r"さすまた|사수마타")),
    ("scene", R(r"이\s*장면|장면에서|장면")),
]
BEHAVIOR_PATTERNS = [
    ("sale_done", R(r"팔았|팔았습니다|판매\s*완료|판매했(?!게)")),
    ("sale_offer", R(
        r"입고\s*(되었|됐|완료|합니)|재입고(?!\s*\?)|예약\w{0,3}\s*(시작|개시|오픈|받|마감)|"
        r"신규\s*예약|1차금|예약판매|입금|재고\s*있|팔\s*예정|판매할|판매합|판매중|팝니다|"
        r"구매\s*문의|구매\s*링크|파트너스|available|공구\s*(오픈|받|모집)|신상\s*공구|"
        r"양도합니다|양도해요|양도합|より登場|登場|発売|入荷|"
        r"굿즈\s*입고|(?<![가-힣])입고(?:\s*[!💛❤✨🌟]|$)"
    )),
    ("purchase_done", R(
        r"샀|구매했|주문했|주문햇|주문함|뽑았|첫\s*구매|후회없는\s*소비|"
        r"돈.{0,16}써서|\d+\s*만?\s*원.{0,16}(뽑|샀|질렀)|예약했|사왔|사옴|사버렸"
    )),
    ("purchase_wish", R(r"사고\s*싶|갖고\s*싶|사고싶|갖고싶|사야겠|살\s*예정|꼭\s*산|뽑아\s*보려|뽑고\s*싶|구할\s*수\s*있|발주")),
    ("trade_done", R(r"교환했|바꿨|바꿔왔|교환\s*완료|내가\s*바꿈|교환을\s*위해.{0,16}보람")),
    ("trade_offer", R(r"교환하자|교환\s*구|교환할\s*사람|교환\s*원")),
    ("transfer_seek", R(r"양도\s*(구|받|희망)|공구\s*구|구합니다|구함|구핮")),
    ("giveaway_offer", R(r"(알티|RT|추첨|이벤트).{0,40}(선물|보내|드립|나눔|추첨)|(선물|보내드).{0,20}(알티|RT|추첨)")),
    ("receive_gift", R(r"사준|사줬|사주심|선물\s*받았|노벨티.{0,8}받았|받았(?:습|어|다|네)|받았당")),
    ("acquire_unclear", R(r"데려왔|데려오|데려옴|겟했|겟\s*!")),
    ("watch_done", R(r"보고\s*빠|봤어|봤다|정주행\s*했|완주")),
    ("watch_wish", R(r"보고\s*싶|보고싶|몰아보|빨리\s*보|보구시포|보고\s*싶")),
    ("watch_now", R(r"보면서|보며|볼\s*때마다|보는\s*중|처음\s*봄")),
    ("visit_done", R(r"다녀왔|다녀온|(?<![가-힣나])왔(?:어요|다|네)|들렀|들어갔|마켓에서|마켓\s*갔|팝업에\s*왔")),
    ("create", R(r"그렸|그렸어요|그려봤|도장을?\s*팠|만들었어|깎|깍는")),
    ("info_share", R(r"이모티콘.{0,20}출시|출시되었")),
    ("release_notice", R(r"발매|출시\s*예정|준비했습니다|기대해\s*주")),
    ("release_wish", R(r"내주면|콜라보\s*해라|나왔으면|발매\s*해\s*주|하나\s*더\s*내")),
    ("ownership_use", R(r"잘\s*쓰|쓰고\s*있|소장")),
    ("content_share", R(r"업로드|전편\s*공개|전편공개")),
]
OTHER_AGENT = R(r"(친구|트친|짝꿍|사장님|동료|남친|여친).{0,18}(샀|사줬|사준|가서|데려|주문)")
SIMILE = R(r"같은데|닮|에디션이냐|처럼")
OTHER_IP = R(r"농담곰|산리오|포켓몬|쿠로미|폼폼|시나모롤|헬로키티|짱구|금담곰|흑담곰|더보이즈|세븐틴")
HASH_TOKEN = R(r"#[^\s#]+")
COMMERCE = {
    "sale_done", "sale_offer", "purchase_done", "purchase_wish", "trade_done", "trade_offer",
    "transfer_seek", "giveaway_offer", "receive_gift", "acquire_unclear", "ownership_use",
    "info_share", "release_notice", "release_wish", "content_share", "create",
}
LINKABLE = COMMERCE | {"watch_done", "watch_wish", "watch_now", "mention"}


def normalize(text: str) -> str:
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def clauses_of(text: str) -> list[str]:
    parts = re.split(r"[\n]+|(?<=[\.!?。])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def mask_opp(text: str) -> str:
    return OPP.sub(" " * 6, text)


def find_codes(text: str, table) -> set[str]:
    return {code for code, pattern in table if pattern.search(text)}


def blank_full_names(text: str) -> str:
    masked = mask_opp(text)
    for _, pattern in FULL_CHAR:
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    masked = CHI.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


def short_characters(text: str, full: set[str]) -> tuple[set[str], bool]:
    pool = blank_full_names(text)
    found = {code for code, pattern in SHORT.items() if pattern.search(pool)}
    if len(found) >= 2 or (len(found) == 1 and full):
        return found, False
    if found:
        return set(), True
    return set(), False


def chiikawa_roles(text: str, peers_present: bool) -> tuple[bool, bool, bool]:
    series = bool(HASH_CHI.search(text))
    character = False
    ambiguous = False
    for match in CHI.finditer(text):
        if text[max(0, match.start() - 1):match.start()] == "#":
            series = True
            continue
        start = max(0, match.start() - 14)
        end = min(len(text), match.end() + 20)
        window = text[start:end]
        clause = text[max(0, text.rfind("\n", 0, match.start()) + 1):text.find("\n", match.end())]
        if clause == "":
            clause = window
        peer = peers_present and bool(PEER_SPLIT.search(clause)) and find_codes(mask_opp(clause), FULL_CHAR)
        if PRODUCT.search(window):
            series = True
            if peer:
                character = True
        elif peer:
            character = True
        elif CHAR_BODY.search(window):
            character = True
        elif R(r"우무\s*\(\s*치이").search(text):
            character = True
        else:
            ambiguous = True
    return series, character, ambiguous


def detect_behaviors(clause: str) -> set[str]:
    found = set()
    other = bool(OTHER_AGENT.search(clause))
    for code, pattern in BEHAVIOR_PATTERNS:
        if not pattern.search(clause):
            continue
        if other and code in {"purchase_done", "visit_done", "acquire_unclear"}:
            found.add("receive_gift")
            continue
        if code == "transfer_seek" and R(r"양도합니다|양도해요|판매").search(clause):
            found.add("sale_offer")
            continue
        if code == "info_share" and "이모티콘" not in clause and "출시되었" not in clause:
            continue
        if code == "sale_offer" and R(r"입고\s*싶|입고\s*다니").search(clause) and not R(r"입고\s*(되었|됐)").search(clause):
            continue
        if code == "watch_now" and R(r"보며").search(clause) and R(r"판매|입고|예약").search(clause):
            continue
        found.add(code)
    if R(r"나왔는데").search(clause) and R(r"뽑|가챠|그립톡").search(clause):
        found.add("purchase_done")
    if "purchase_done" in found and R(r"사준|사줬").search(clause):
        found.discard("purchase_done")
        found.add("receive_gift")
    if "sale_offer" in found and "release_notice" in found and R(r"입고|예약|입금|재고|판매|팝니다").search(clause):
        found.discard("release_notice")
    return found


def detect_forms(clause: str) -> set[str]:
    clause = HASH_TOKEN.sub(" ", clause)
    simile = bool(SIMILE.search(clause)) and not (detect_behaviors(clause) & COMMERCE)
    found = set()
    for code, pattern in FORM_PATTERNS:
        if simile and code == "apparel":
            continue
        for match in pattern.finditer(clause):
            prev = clause[max(0, match.start() - 12):match.start()]
            if OTHER_IP.search(prev):
                continue
            found.add(code)
            break
    return found


def opening_release(text: str) -> bool:
    return bool(R(r"개봉").search(text)) and bool(R(r"보|관람|영화|극장").search(text)) and not bool(R(r"굿즈|인형|가챠").search(text))


def classify_rules(text: str) -> dict:
    norm = normalize(text)
    held = [name for name, pattern in HELD if pattern.search(norm)]
    notes = []
    if not norm.strip():
        return empty_result("본문이 비어 있다.", "", held)

    if NEG.search(norm) and not find_codes(mask_opp(norm), FULL_CHAR) and not FORM_PATTERNS[0][1].search(norm):
        if not any(pattern.search(norm) for _, pattern in FORM_PATTERNS):
            evidence = NEG.search(norm).group(0)
            return {
                "series": [], "series_status": NO,
                "characters": [], "character_status": NO,
                "forms": [], "form_status": NO,
                "behaviors": [], "behavior_status": NO,
                "links": [], "link_status": NA,
                "evidence": evidence,
                "reason": "이름을 부정하는 문장만 있어 작품·캐릭터·형태·행동을 두지 않았다.",
                "review": "부정 언급은 미언급.",
                "held": held,
                "judgment": NO,
            }

    masked = mask_opp(norm)
    if OPP.search(norm):
        notes.append("오빤쮸우사기는 우사기로 넣지 않음")
    full = find_codes(masked, FULL_CHAR)
    shorts, short_ask = short_characters(norm, full)
    characters = set(full) | shorts
    if short_ask:
        notes.append("혼자 있는 약칭은 캐릭터로 확정하지 않음")
    series_flag, char_flag, ambiguous = chiikawa_roles(masked, bool(characters))
    series = set()
    if MON.search(masked) or HASH_MON.search(masked):
        series.add("monjakgwi")
    if series_flag:
        series.add("chiikawa_series")
    if char_flag:
        characters.add("chiikawa")

    series_status = OK if series else (ASK if ambiguous else NO)
    if ambiguous and "chiikawa" not in characters:
        character_status_chi_ask = True
    else:
        character_status_chi_ask = ambiguous and not char_flag
    if short_ask:
        character_status_chi_ask = True

    links = []
    forms = set()
    behaviors = set()
    link_ask = False
    evidence = ""

    for clause in clauses_of(masked):
        plain = HASH_TOKEN.sub(" ", clause)
        clause_forms = detect_forms(plain)
        clause_behaviors = detect_behaviors(plain)
        if opening_release(clause):
            clause_forms.add("movie")
        clause_chars = sorted(find_codes(mask_opp(clause), FULL_CHAR))
        for code in shorts:
            if SHORT[code].search(blank_full_names(clause)):
                clause_chars = sorted(set(clause_chars) | {code})
        if char_flag and CHI.search(clause) and "chiikawa" in characters:
            # only attach when this clause resolved as character, approximate by peer or body
            window_role = chiikawa_roles(clause, bool(clause_chars))
            if window_role[1]:
                clause_chars = sorted(set(clause_chars) | {"chiikawa"})
        forms |= clause_forms
        behaviors |= clause_behaviors
        linkable = [code for code in clause_behaviors if code in LINKABLE]
        if not evidence and (clause_forms or clause_behaviors or clause_chars):
            evidence = clause[:80]
        if len(linkable) == 1 and clause_forms:
            for form in sorted(clause_forms):
                links.append((form, linkable[0], tuple(clause_chars)))
        elif len(linkable) > 1 and clause_forms:
            link_ask = True
            # 한 문장에 행동이 여러 개면 형태마다 가장 먼저 나온 행동 하나만 연결하지 않고 보류한다.
        elif clause_forms and not linkable:
            for form in sorted(clause_forms):
                links.append((form, "", tuple(clause_chars)))

    if R(r"알티|RT|#RT").search(norm) and R(r"추첨|보내드|선물|뽑을게|나눔").search(norm):
        behaviors.add("giveaway_offer")
    if "sale_offer" in behaviors:
        behaviors.discard("release_notice")

    real_behaviors = {code for code in behaviors if code != "mention"}
    rewritten = []
    for form, behavior, chars in links:
        if behavior == "" and len(real_behaviors) == 1:
            rewritten.append((form, next(iter(real_behaviors)), chars))
        elif behavior == "" and not real_behaviors:
            behaviors.add("mention")
            rewritten.append((form, "mention", chars))
        elif behavior == "":
            link_ask = True
        else:
            rewritten.append((form, behavior, chars))
    links = rewritten

    commerce = behaviors & {
        "sale_done", "sale_offer", "purchase_done", "purchase_wish", "trade_done", "trade_offer",
        "transfer_seek", "giveaway_offer", "receive_gift", "acquire_unclear", "ownership_use",
    }
    specific_forms = {form for form in forms if form != "goods_unknown"}
    if commerce and not specific_forms:
        forms.add("goods_unknown")
        if len(commerce) == 1:
            only = next(iter(commerce))
            links.append(("goods_unknown", only, tuple(sorted(characters)) if len(characters) == 1 else tuple()))
        else:
            link_ask = True
            for code in sorted(commerce):
                links.append(("goods_unknown", code, tuple()))

    if (characters or series or ambiguous) and not behaviors:
        behaviors.add("mention")

    if "mention" in behaviors and behaviors - {"mention"} and not any(link[1] == "mention" for link in links):
        # 다른 행동이 있으면 단독 감상만 있을 때 단순 언급을 남긴다. 연결용으로만 넣은 경우는 유지.
        if any(link[1] != "mention" for link in links) or commerce or (behaviors - {"mention"} - {"visit_done"}):
            if not any(link[1] == "mention" for link in links):
                behaviors.discard("mention")

    # 방문은 형태와 잇지 않는다.
    dedup = []
    seen = set()
    for form, behavior, chars in links:
        if form not in forms or behavior not in behaviors:
            continue
        key = (form, behavior, chars)
        if key in seen:
            continue
        seen.add(key)
        dedup.append({"form": form, "behavior": behavior, "characters": list(chars), "surface": ""})

    if forms and dedup and {item["form"] for item in dedup} != forms:
        link_ask = True
    if link_ask:
        link_status = ASK
    elif dedup:
        link_status = OK
    else:
        link_status = NA

    character_status = OK if characters else (ASK if character_status_chi_ask or short_ask or (ambiguous and not characters) else NO)
    if ambiguous and "chiikawa" not in characters and not characters:
        character_status = ASK
    elif ambiguous and "chiikawa" not in characters and series:
        character_status = ASK if character_status == NO else character_status
        if character_status == NO:
            character_status = ASK
    form_status = OK if forms else (ASK if ambiguous and not forms and R(r"메론빵|단독샷|놓고").search(norm) else NO)
    if R(r"메론빵|단독샷").search(norm) and not specific_forms:
        form_status = ASK
        forms = set()
        dedup = [item for item in dedup if item["form"] != "goods_unknown"]
    behavior_status = OK if behaviors else (ASK if form_status == ASK and not behaviors else NO)
    if not behaviors and form_status == ASK:
        behaviors.add("mention")
        behavior_status = OK

    if not evidence:
        evidence = norm[:40].strip() or norm[:20]
    if evidence not in norm:
        evidence = norm[:20]

    reason_bits = []
    if series:
        reason_bits.append("작품 " + ",".join(SERIES[code] for code in sorted(series)))
    if characters:
        reason_bits.append("캐릭터 " + ",".join(CHARACTERS[code] for code in sorted(characters)))
    if forms:
        reason_bits.append("형태 " + ",".join(FORMS[code] for code in sorted(forms)))
    if behaviors:
        reason_bits.append("행동 " + ",".join(BEHAVIORS[code] for code in sorted(behaviors)))
    reason = "기준 v1 문맥 규칙. " + ". ".join(reason_bits) + "."
    if notes:
        reason += " " + " ".join(notes) + "."
    if link_ask:
        reason += " 한 문장 안에서 형태와 행동이 여러 갈래라 연결 일부는 확인 필요로 남겼다."
    review = ""
    if held:
        review = "기준서에 없는 표현 보류: " + ", ".join(held) + "."
    if ambiguous and "chiikawa" not in characters:
        review = (review + " " if review else "") + "치이카와 층위가 안 갈리는 호칭이 있다."
    if short_ask:
        review = (review + " " if review else "") + "단독 약칭은 확정하지 않음."

    axes = [series_status, character_status, form_status, behavior_status, link_status]
    if all(status == NO for status in axes[:4]) and link_status == NA:
        judgment = NO
    elif any(status == ASK for status in axes):
        judgment = ASK
    else:
        judgment = OK

    return {
        "series": sorted(series),
        "series_status": series_status,
        "characters": sorted(characters),
        "character_status": character_status,
        "forms": sorted(forms),
        "form_status": form_status,
        "behaviors": sorted(behaviors),
        "behavior_status": behavior_status,
        "links": dedup,
        "link_status": link_status,
        "evidence": evidence,
        "reason": reason,
        "review": review.strip(),
        "held": held,
        "judgment": judgment,
    }


def empty_result(reason, evidence, held):
    return {
        "series": [], "series_status": NO, "characters": [], "character_status": NO,
        "forms": [], "form_status": NO, "behaviors": [], "behavior_status": NO,
        "links": [], "link_status": NA, "evidence": evidence or " ",
        "reason": reason, "review": "", "held": held, "judgment": NO,
    }


def from_pilot(item: dict) -> dict:
    judgment_axes = [
        item["series_status"], item["character_status"], item["form_status"],
        item["behavior_status"], item["link_status"],
    ]
    if all(status == NO for status in judgment_axes[:4]) and item["link_status"] == NA:
        judgment = NO
    elif any(status == ASK for status in judgment_axes):
        judgment = ASK
    else:
        judgment = OK
    return {
        "series": list(item["series"]),
        "series_status": item["series_status"],
        "characters": list(item["characters"]),
        "character_status": item["character_status"],
        "forms": list(item["forms"]),
        "form_status": item["form_status"],
        "behaviors": list(item["behaviors"]),
        "behavior_status": item["behavior_status"],
        "links": item["links"],
        "link_status": item["link_status"],
        "evidence": item["evidence"],
        "reason": item["reason"],
        "review": item["review"],
        "held": [],
        "judgment": judgment,
        "source": "시험 수동 판정",
    }


def labels(codes, mapping):
    return [{"code": code, "name": mapping[code]} for code in codes]


def dump_links(links) -> str:
    payload = []
    for link in links:
        payload.append({
            "form_code": link["form"],
            "form_name": FORMS[link["form"]],
            "behavior_code": link["behavior"],
            "behavior_name": BEHAVIORS[link["behavior"]],
            "character_codes": link["characters"],
            "character_names": [CHARACTERS[code] for code in link["characters"]],
            "surface": link.get("surface", ""),
        })
    return json.dumps(payload, ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def log_progress(payload: dict) -> None:
    payload["at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_source():
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Python 3.11에서 실행해야 한다.")
    before = sha256_file(PARQUET)
    frame = pd.read_parquet(PARQUET)
    if len(frame) != 5000 or list(frame.columns) != [
        "게시물 링크", "계정 ID", "댓글 개수", "리포스트 개수", "본문", "계정 이름",
        "작성 시각", "조회수", "좋아요 수", "키워드", "source_file", "source_row", "source_year",
    ]:
        raise SystemExit("입력 행 수 또는 컬럼이 기준과 다르다.")
    frame = frame.copy()
    frame["post_id"] = frame["게시물 링크"].astype("string").str.extract(r"/status/(\d+)", expand=False).astype("string")
    if frame["post_id"].nunique() != 5000:
        raise SystemExit("post_id가 유일하지 않다.")
    if sha256_file(PARQUET) != before:
        raise SystemExit("읽기 전후 입력 지문이 달라졌다.")
    return frame, before


def checkpoint_path(batch_index: int) -> Path:
    return CHECKPOINT_DIR / f"batch_{batch_index:02d}.jsonl"


def classify_frame(frame: pd.DataFrame, fingerprint: str) -> list[dict]:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    header = CHECKPOINT_DIR / "run_header.json"
    pilot_by_id = {item["post_id"]: from_pilot(item) for item in pilot.JUDGMENTS}
    rows = []
    total = len(frame)
    for start in range(0, total, BATCH):
        batch_index = start // BATCH
        path = checkpoint_path(batch_index)
        reuse = False
        if path.exists() and header.exists():
            meta = json.loads(header.read_text(encoding="utf-8"))
            if meta.get("fingerprint") == fingerprint and meta.get("codebook") == CODEBOOK_VERSION:
                cached = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                if len(cached) == min(BATCH, total - start):
                    rows.extend(cached)
                    reuse = True
                    log_progress({"event": "resume_batch", "batch": batch_index, "rows": len(cached)})
        if reuse:
            continue
        chunk = []
        for _, row in frame.iloc[start:start + BATCH].iterrows():
            post_id = str(row["post_id"])
            text = str(row["본문"])
            held = [name for name, pattern in HELD if pattern.search(normalize(text))]
            if post_id in pilot_by_id:
                item = dict(pilot_by_id[post_id])
                item["held"] = held
                if held:
                    extra = "기준서에 없는 표현 보류: " + ", ".join(held) + "."
                    item["review"] = (item["review"] + " " + extra).strip() if item["review"] else extra
            else:
                item = classify_rules(text)
                item["source"] = "전체 규칙 판정"
            item["post_id"] = post_id
            item["year"] = int(row["작성 시각"].year)
            if item["evidence"] and normalize(item["evidence"]) not in normalize(text):
                item["evidence"] = normalize(text)[:30]
                item["review"] = (item.get("review") or "") + " 근거 문자열을 본문 앞부분으로 맞췄다."
            chunk.append(item)
        path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in chunk) + "\n", encoding="utf-8")
        header.write_text(json.dumps({"fingerprint": fingerprint, "codebook": CODEBOOK_VERSION}, ensure_ascii=False), encoding="utf-8")
        log_progress({"event": "saved_batch", "batch": batch_index, "rows": len(chunk), "through": start + len(chunk)})
        rows.extend(chunk)
    if len(rows) != total:
        raise SystemExit(f"분류 행 수가 입력을 벗어났다: {len(rows)}")
    return rows


def agreement(frame: pd.DataFrame) -> dict:
    by_id = {item["post_id"]: item for item in pilot.JUDGMENTS}
    scores = {"characters": 0, "forms": 0, "behaviors": 0, "judgment": 0, "n": 0}
    samples = []
    for _, row in frame.iterrows():
        post_id = str(row["post_id"])
        if post_id not in by_id:
            continue
        gold = by_id[post_id]
        pred = classify_rules(str(row["본문"]))
        scores["n"] += 1
        for key in ("characters", "forms", "behaviors"):
            if set(pred[key]) == set(gold[key]):
                scores[key] += 1
        if key_match_judgment(pred) == key_match_judgment(gold):
            scores["judgment"] += 1
        elif len(samples) < 12:
            samples.append({
                "post_id": post_id,
                "gold_c": gold["characters"], "pred_c": pred["characters"],
                "gold_f": gold["forms"], "pred_f": pred["forms"],
                "gold_b": gold["behaviors"], "pred_b": pred["behaviors"],
                "text": str(row["본문"]).replace("\n", " ")[:120],
            })
    return scores | {"samples": samples}


def key_match_judgment(item):
    if "judgment" in item and "series_status" not in item:
        return item["judgment"]
    axes = [item["series_status"], item["character_status"], item["form_status"], item["behavior_status"], item["link_status"]]
    if all(status == NO for status in axes[:4]) and item["link_status"] == NA:
        return NO
    if any(status == ASK for status in axes):
        return ASK
    return OK


def build_outputs(frame: pd.DataFrame, classified: list[dict], fingerprint: str) -> None:
    by_id = {item["post_id"]: item for item in classified}
    ordered = []
    for post_id in frame["post_id"].astype(str):
        ordered.append(by_id[post_id])
    extra = pd.DataFrame({
        "codebook_version": CODEBOOK_VERSION,
        "post_id": [item["post_id"] for item in ordered],
        "한국시간_연도": [item["year"] for item in ordered],
        "작품_라벨": [json.dumps(labels(item["series"], SERIES), ensure_ascii=False) for item in ordered],
        "작품_상태": [item["series_status"] for item in ordered],
        "캐릭터_라벨": [json.dumps(labels(item["characters"], CHARACTERS), ensure_ascii=False) for item in ordered],
        "캐릭터_상태": [item["character_status"] for item in ordered],
        "형태_라벨": [json.dumps(labels(item["forms"], FORMS), ensure_ascii=False) for item in ordered],
        "형태_상태": [item["form_status"] for item in ordered],
        "행동_라벨": [json.dumps(labels(item["behaviors"], BEHAVIORS), ensure_ascii=False) for item in ordered],
        "행동_상태": [item["behavior_status"] for item in ordered],
        "형태행동_연결": [dump_links(item["links"]) for item in ordered],
        "연결_상태": [item["link_status"] for item in ordered],
        "판단_상태": [item["judgment"] for item in ordered],
        "근거_문장": [item["evidence"] for item in ordered],
        "판단_이유": [item["reason"] for item in ordered],
        "검토_메모": [item.get("review") or "" for item in ordered],
        "보류_후보": [json.dumps(item.get("held") or [], ensure_ascii=False) for item in ordered],
        "판정_출처": [item.get("source") or "전체 규칙 판정" for item in ordered],
    })
    base = frame.drop(columns=["post_id"]).reset_index(drop=True)
    merged = pd.concat([base, extra], axis=1)
    for column in frame.columns:
        if column == "post_id":
            continue
        left = frame[column].reset_index(drop=True)
        right = merged[column].reset_index(drop=True)
        if column == "조회수":
            same = left.isna().eq(right.isna()) & left.fillna(-1).eq(right.fillna(-1))
        else:
            same = left.eq(right) | (left.isna() & right.isna())
        if not bool(same.all()):
            raise SystemExit(f"원본 컬럼 값이 달라졌다: {column}")
    if int(merged["조회수"].isna().sum()) != 946:
        raise SystemExit("조회수 결측 수가 달라졌다.")
    if int((merged["계정 이름"] == "null").sum()) != 2:
        raise SystemExit("계정 이름 null 수가 달라졌다.")
    if merged["post_id"].nunique() != 5000:
        raise SystemExit("결과 post_id가 유일하지 않다.")
    # 시험 100건 라벨이 수동 판정과 같은지
    pilot_by_id = {item["post_id"]: item for item in pilot.JUDGMENTS}
    for _, row in merged.iterrows():
        post_id = str(row["post_id"])
        if post_id not in pilot_by_id:
            continue
        gold = pilot_by_id[post_id]
        got = json.loads(row["캐릭터_라벨"])
        if [item["code"] for item in got] != gold["characters"]:
            raise SystemExit(f"시험 판정 캐릭터가 덮였다: {post_id}")
        if row["판정_출처"] != "시험 수동 판정":
            raise SystemExit(f"시험 출처가 아니다: {post_id}")

    merged.to_parquet(FINAL_PARQUET, index=False)
    csv_frame = merged.copy()
    csv_frame["작성 시각"] = csv_frame["작성 시각"].dt.strftime("%Y-%m-%d %H:%M:%S%z").str.replace(
        r"(\d{2})(\d{2})$", r"\1:\2", regex=True
    )
    csv_frame.to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")

    review = merged[(merged["판단_상태"] != OK) | (merged["보류_후보"] != "[]")].copy()
    review_out = review[[
        "post_id", "게시물 링크", "작성 시각", "한국시간_연도", "키워드", "본문",
        "판단_상태", "작품_상태", "캐릭터_상태", "형태_상태", "행동_상태", "연결_상태",
        "근거_문장", "판단_이유", "검토_메모", "보류_후보", "판정_출처",
        "작품_라벨", "캐릭터_라벨", "형태_라벨", "행동_라벨", "형태행동_연결",
    ]]
    review_out.to_csv(REVIEW_CSV, index=False, encoding="utf-8-sig")

    reloaded = pd.read_parquet(FINAL_PARQUET)
    if len(reloaded) != 5000 or reloaded["post_id"].nunique() != 5000:
        raise SystemExit("Parquet 재로딩 검증 실패")
    if str(reloaded["작성 시각"].dtype) != "datetime64[ns, Asia/Seoul]":
        raise SystemExit(f"작성 시각 자료형이 달라졌다: {reloaded['작성 시각'].dtype}")
    if str(reloaded["조회수"].dtype) != "Int64" or int(reloaded["조회수"].isna().sum()) != 946:
        raise SystemExit("조회수 자료형 또는 결측이 달라졌다.")
    for column in frame.columns:
        if column == "post_id":
            continue
        if str(reloaded[column].dtype) != str(frame[column].dtype):
            raise SystemExit(f"재로딩 자료형 불일치 {column}")
    if sha256_file(PARQUET) != fingerprint:
        raise SystemExit("결과 저장 후 입력 Parquet 지문이 달라졌다.")
    stats = summarize(ordered)
    stats["fingerprint"] = fingerprint
    stats["review_rows"] = int(len(review))
    (OUT_DIR / "_full_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log_progress({"event": "finished", "rows": 5000, "review_rows": int(len(review)), "judgments": stats["judgments"]})
    print(json.dumps({
        "rows": 5000,
        "judgments": stats["judgments"],
        "review_rows": int(len(review)),
        "character_labels": stats["character_label_sum"],
        "form_labels": stats["form_label_sum"],
        "behavior_labels": stats["behavior_label_sum"],
        "links": stats["link_rows"],
        "sources": stats["sources"],
    }, ensure_ascii=False, indent=2))


def summarize(items: list[dict]) -> dict:
    def count(key, mapping):
        counter = {name: 0 for name in mapping.values()}
        for item in items:
            for code in item[key]:
                counter[mapping[code]] += 1
        return [{"label": name, "count": counter[name]} for name in mapping.values() if counter[name]]

    judgments = {}
    sources = {}
    held = {}
    by_year = {}
    for item in items:
        judgments[item["judgment"]] = judgments.get(item["judgment"], 0) + 1
        source = item.get("source") or "전체 규칙 판정"
        sources[source] = sources.get(source, 0) + 1
        year = str(item["year"])
        bucket = by_year.setdefault(year, {})
        bucket[item["judgment"]] = bucket.get(item["judgment"], 0) + 1
        for name in item.get("held") or []:
            held[name] = held.get(name, 0) + 1
    return {
        "judgments": judgments,
        "sources": sources,
        "by_year": by_year,
        "series": count("series", SERIES),
        "characters": count("characters", CHARACTERS),
        "forms": count("forms", FORMS),
        "behaviors": count("behaviors", BEHAVIORS),
        "character_label_sum": sum(len(item["characters"]) for item in items),
        "form_label_sum": sum(len(item["forms"]) for item in items),
        "behavior_label_sum": sum(len(item["behaviors"]) for item in items),
        "link_rows": sum(len(item["links"]) for item in items),
        "posts_with_2plus_characters": sum(len(item["characters"]) >= 2 for item in items),
        "posts_with_2plus_forms": sum(len(item["forms"]) >= 2 for item in items),
        "posts_with_2plus_behaviors": sum(len(item["behaviors"]) >= 2 for item in items),
        "held": held,
        "rule_rows": sources.get("전체 규칙 판정", 0),
        "manual_rows": sources.get("시험 수동 판정", 0),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, fingerprint = load_source()
    if "--eval" in sys.argv:
        print(json.dumps(agreement(frame), ensure_ascii=False, indent=2))
        return
    classified = classify_frame(frame, fingerprint)
    build_outputs(frame, classified, fingerprint)


if __name__ == "__main__":
    main()
