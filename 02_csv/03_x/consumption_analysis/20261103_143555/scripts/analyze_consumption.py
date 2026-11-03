# -*- coding: utf-8 -*-
"""치이카와 X 게시물의 상품 소비·이용 방식 분석.

판단 층
- rule_screen: 선별 어휘에 걸리지 않은 게시물. 게시물마다 읽지 않음.
- rule_calibrated: 본 스크립트의 구절 규칙. 예시 원문을 읽고 규칙을 고친 뒤 적용.
- model_context: working/model_read_ids.txt 에 있는 게시물. 모델이 원문을 읽고 수용하거나 고침.

기존 text_analysis_v2 라벨은 읽지 않고, 정답으로 쓰지 않는다.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

RUN = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\consumption_analysis\20261103_143555")
POSTS = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_posts.csv")
SOURCES = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_sources.csv")
FILES = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_source_files.csv")
WORKING = RUN / "working"
TABLES = RUN / "tables"
CHARTS = RUN / "charts"

SCREEN_PATTERNS = {
    "상품어": r"인형|누이|피규어|피규|소프비|마스코트|키링|키홀더|키체인|스트랩|아크릴|뱃지|와펜|스티커|다이컷|씰|포토카드|트레카|지우개|필통|다이어리|파우치|포셰트|포쉐트|에코백|텀블러|머그|쿠션|담요|슬리퍼|양말|티셔츠|티샤쓰|후드|샤워볼|무드등|봉제|러버|마그넷|코스터|스푼|포크|부채|랜턴|보틀|지갑|타월|베개|이불|홀더|스탠드|굿즈|상품|노벨티|프라이즈|스마트톡|그립톡|콜렉트북|구미|파일홀더|도장|시계|파자마|잠옷|인형옷|캔디|쿠키|과자|초콜릿|크레페|이모티콘|임티|가챠|쿠지|제일복권|팝업|콜라보|팬케이크메이커|다마고치|ぬい|ガチャ|マスコット|クッション|フィギュア|アクリル|ステッカー|저금통|약통|여권|북마크|스탬프|팔찌|넥타이|램프|데스크매트|수정테이프|띠부|키캡|해피밀|오챠즈케|후리카게|마쉬멜로|네소베리|스퀴시",
    "획득어": r"샀|사버려|산거|살말|구매|겟했|겟함|겟한|득템|뽑|공구|직구|예약판매|선물|증정|나눔|양도|급처|팝니다|구합니다|구함|언박싱|개봉|실물|현물|품절|재입고|결제|배송왔|택배|질렀|입고되었|입고완료|판매중|판매합니다|미개봉|데려왔|모셔왔|탑승|買った|購入",
    "사용어": r"갖고싶|가지고싶|사고싶|소장|달고다|가방에|쓰다듬|아까워|진열|책상|선반|모으|수집|착용|다꾸|안뜯|못쓰|못써|다녀왔|정주행",
    "콘텐츠어": r"이모티콘|임티|애니메이션|영화관|극장|팝업|콜라보|전시회|카페|애니",
}


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"@\w+", "", s)
    s = s.replace("#", "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)
    return s


def newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def clauses_of(text: str) -> list[str]:
    parts = re.split(r"\n+", newlines(text))
    out: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        bits = re.split(r"(?<=[\.!?…])\s+", part)
        for bit in bits:
            bit = bit.strip()
            if bit:
                out.append(bit)
    return out or [newlines(text).strip()]


def contains(n: str, pat: str) -> bool:
    return re.search(pat, n) is not None


def load_model_read() -> set[str]:
    path = WORKING / "model_read_ids.txt"
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def load_overrides() -> list[dict]:
    path = WORKING / "overrides.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_image_checks() -> dict[str, dict]:
    path = WORKING / "image_checks.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    return {r["post_id"]: r.to_dict() for _, r in df.iterrows()}


CHAR_SPECS = [
    ("하치와레", r"하치와레"),
    ("우사기", r"우사기|토끼\(우사기\)"),
    ("모몽가", r"모몽가|모몬가"),
    ("랏코", r"랏코"),
    ("쿠리만쥬", r"쿠리만쥬"),
    ("갑옷씨", r"갑옷씨|갑옷아저씨|갑옷상"),
    ("시사", r"시사(?!하|점|회|용)"),
    ("카니", r"카니(?!발)"),
    ("아노코", r"아노코"),
    ("데카츠요", r"데카츠요"),
    ("키메라", r"키메라"),
    ("치이카와", r"치이카와"),
    ("먼작귀", r"먼작귀"),
    ("농담곰", r"농담곰"),
    ("파자마파티즈", r"파자마파티즈"),
]

# (label, regex on norm text, priority, function, note)
# Longer / more specific patterns have higher priority and consume overlaps via priority sort.
PRODUCT_SPECS = [
    ("키링·스트랩", r"키링인형|인형키링|마스코트키링|파자마키링|키링|키홀더|키체인|러버스트랩", 90, "부착·휴대", "부착 기능이 이름에 있음"),
    ("마스코트(소형 봉제)", r"마스코트인형|인형마스코트|마스코트", 85, "기능 불명확", "마스코트는 인형과 별도 형태명"),
    ("봉제 인형", r"누이구루미|봉제인형|누이|인형", 70, "기능 불명확", ""),
    ("피규어", r"미니피규어|랜덤피규어|코스튬미니피규어|소프비|피규어|피규", 70, "기능 불명확", ""),
    ("아크릴 제품", r"아크릴스탠드|아크릴키체인|아크릴키링|아크릴클립|아크릴스틱|아크릴", 80, "기능 불명확", ""),
    ("스티커·씰", r"다이컷스티커|데코스티커|씰스티커|스티커|다이컷|씰", 70, "기능 불명확", ""),
    ("카드·트레카", r"포토카드|트레카|컬렉션카드|카드컬렉션|교통카드케이스|카드케이스", 75, "기능 불명확", ""),
    ("뱃지·마그넷", r"캔뱃지|뱃지|와펜|마그넷|자석(?!처럼)", 70, "부착·휴대", ""),
    ("휴대폰 부착 소품", r"스마트톡|그립톡", 80, "부착·휴대", ""),
    ("문구", r"지우개|필통|다이어리|유선노트|모눈노트|노트|달력|도장|파일홀더", 70, "실사용", "문구로 분류. 실제 사용 여부는 별도"),
    ("파우치·수납", r"콜렉트북|포셰트|포쉐트|파우치|에코백|카드지갑|지갑", 70, "수납", ""),
    ("식기·컵", r"텀블러|머그컵|머그|유리컵|덮밥그릇|밥그릇|그릇|접시|스푼|포크|코스터|보틀|컵샀|컵을|컵이", 70, "실사용", ""),
    ("생활섬유", r"러그매트|러그|담요|이불|쿠션|타월|베개|수건", 70, "기능 불명확", ""),
    ("의류·패션소품", r"인형옷|티셔츠|티샤쓰|잠옷|파자마|반팔|양말|슬리퍼|후드티|후드|메이드옷|팔찌|넥타이", 60, "실사용", ""),
    ("생활용품", r"샤워볼|무드등|램프|랜턴|부채|거울|시계|케이블홀더|우산|앞치마|약통|저금통|데스크매트|팬케이크메이커", 70, "기능 불명확", ""),
    ("식품·음료", r"수제쿠키|쿠키|캔디보틀|캔디|초콜릿|초코볼|과자|구미|크레페|해피밀|오챠즈케|후리카게|마쉬멜로|메뉴", 55, "실사용", ""),
    ("문구", r"수정테이프|북마크|스탬프|띠부씰|여권케이스", 72, "실사용", ""),
    ("만화·서적", r"단행본|만화책|코믹스|특별판|콩알도감|책샀|책을샀", 65, "기능 불명확", ""),
    ("이모티콘", r"카카오톡이모티콘|라인임티|이모티콘|임티|라인테마", 80, "기능 불명확", ""),
    ("애니메이션", r"애니메이션", 40, "기능 불명확", ""),
    ("영화", r"영화관|극장|영화", 40, "기능 불명확", ""),
    ("팝업·전시", r"팝업스토어|팝업|전시회|전시", 45, "기능 불명확", ""),
    ("카페·매장", r"콜라보카페|카페", 45, "기능 불명확", ""),
    ("콜라보·행사", r"콜라보", 30, "기능 불명확", ""),
]


def find_products(n: str) -> list[dict]:
    stripped = re.sub(r"피규어샵|피규어프레소|피규어픽|가챠샵|굿즈샵|원피규어|홍대피규어|대전피규어", "", n)
    # 작중 음식·작중 옷은 상품에서 뺀다.
    story_food = contains(stripped, r"푸딩|핫케이크|브로콜리|마요네즈|군고구마")
    goods_food = contains(stripped, r"콜라보|메뉴|과자|쿠키|캔디|구미|초콜릿|초코|판매|상품|선물|편의점|포장|증정|수제")
    story_wear = contains(stripped, r"오징어옷|옷입") and not contains(
        stripped, r"인형|키링|마스코트|피규어|판매|굿즈|스파오|티셔츠"
    )
    spans = []
    for label, pat, prio, func, note in PRODUCT_SPECS:
        for m in re.finditer(pat, stripped):
            spans.append((m.start(), m.end(), prio, label, func, note, m.group()))
    spans.sort(key=lambda x: (-x[2], -(x[1] - x[0]), x[0]))
    kept = []
    occupied = []
    for start, end, prio, label, func, note, group in spans:
        if any(not (end <= a or start >= b) for a, b in occupied):
            continue
        if label == "식품·음료" and story_food and not goods_food:
            continue
        if label == "의류·패션소품" and story_wear:
            continue
        if label == "의류·패션소품" and contains(stripped, r"파자마파티즈") and not contains(stripped, r"티셔츠|잠옷|스파오|반팔"):
            continue
        if label == "의류·패션소품" and contains(group, r"파자마|잠옷") and contains(
            stripped, r"키링|마스코트|피규어|누이|인형"
        ):
            continue
        if label == "식품·음료" and contains(stripped, r"쿠키키링|캔디보틀"):
            continue
        if label == "피규어" and contains(stripped, r"샤워볼"):
            continue
        if label == "봉제 인형" and contains(group, r"인형") and contains(stripped, r"마스코트인형|인형마스코트|키링인형|인형키링"):
            continue
        if label == "애니메이션" and not contains(stripped, r"애니|애니메이션"):
            continue
        if label == "영화" and contains(group, r"영화") and not contains(stripped, r"영화관|극장|영화봤|영화보|개봉"):
            # '영화' 한 단어는 아래 단일 패턴에서만. 여기 스펙은 영화관|극장|영화 를 포함.
            if group == "영화" and not contains(stripped, r"영화봤|영화보|영화관|극장|영화개봉|영화후기"):
                continue
        if label == "팝업·전시" and group == "전시" and not contains(stripped, r"전시회|팝업|전시했|전시하|진열"):
            # '자세하게' '전시' 오탐. 전시해야/전시회/팝업만.
            if not contains(stripped, r"전시해야|전시했|전시회|전시장|진열|팝업"):
                continue
        if label == "카페·매장" and not contains(stripped, r"카페"):
            continue
        occupied.append((start, end))
        func_out = func
        if label == "아크릴 제품":
            if contains(group, r"스탠드"):
                func_out = "장식·전시"
            elif contains(group, r"키체인|키링|클립|스틱"):
                func_out = "부착·휴대"
        if label == "파우치·수납":
            func_out = "수납"
        if label == "스티커·씰" and contains(stripped, r"다꾸|꾸몄|붙여"):
            func_out = "부착·휴대"
        variant = ""
        if contains(stripped, r"파자마|잠옷") and label in {"키링·스트랩", "마스코트(소형 봉제)", "피규어", "봉제 인형"}:
            variant = "파자마·잠옷 버전"
        kept.append(
            {
                "product_form": label,
                "product_span": group,
                "function_axis": func_out,
                "variant": variant,
                "product_note": note,
            }
        )
    # 같은 구절에서 같은 형태는 한 번
    uniq = []
    seen = set()
    for item in kept:
        if item["product_form"] in seen:
            continue
        seen.add(item["product_form"])
        uniq.append(item)
    if not uniq and contains(stripped, r"굿즈|상품|가챠|쿠지|제일복권") and not contains(
        stripped, r"피규어샵|굿즈샵|가챠샵"
    ):
        # 가게 이름만 남은 경우는 위에서 제거됨. 일반 굿즈·가챠 대상.
        if contains(stripped, r"굿즈|상품|가챠|쿠지|제일복권"):
            uniq.append(
                {
                    "product_form": "형태 불특정 굿즈",
                    "product_span": "굿즈·상품·가챠·쿠지",
                    "function_axis": "기능 불명확",
                    "variant": "",
                    "product_note": "구체 형태 명사 없음. 가챠·쿠지는 획득·판매 방식이라 형태로 세지 않음",
                }
            )
    return uniq


def find_characters(n: str) -> list[str]:
    found = []
    for name, pat in CHAR_SPECS:
        if re.search(pat, n):
            found.append(name)
    if "치이카와" in found and "먼작귀" in found:
        pass
    return found


def character_fields(names: list[str]) -> tuple[str, str, str]:
    ip_names = [x for x in names if x not in {"농담곰", "파자마파티즈"}]
    others = [x for x in names if x in {"농담곰", "파자마파티즈"}]
    if not names:
        return "본문에서 캐릭터 미언급", "연결 불명확", "치이카와 계열 이름 없음"
    if ip_names == ["먼작귀"]:
        char = "먼작귀(작품명, 캐릭터 특정 안 됨)"
    elif ip_names == ["치이카와"] or ip_names == ["치이카와", "먼작귀"] or ip_names == ["먼작귀", "치이카와"]:
        char = "치이카와"
    else:
        # 치이카와가 작품 총칭으로 같이 있으면 개별 이름을 남기되 치이카와도 보존
        char = "|".join(ip_names) if ip_names else "해당 없음"
    if others:
        char = (char + "|" if char != "해당 없음" else "") + "|".join(f"{o}(다른 작품)" for o in others)
        char = char.strip("|")
    if len([x for x in ip_names if x not in {"먼작귀"}]) > 1:
        link = "복수 캐릭터 동시 언급"
    elif ip_names:
        link = "상품·행동 구절에 이름 있음"
    else:
        link = "다른 작품 이름만 있음"
    about = "치이카와 계열" if ip_names else "다른 작품"
    if ip_names and others:
        about = "치이카와 계열과 다른 작품 병기"
    return char, link, about


PROMO_RE = re.compile(
    r"판매합니다|판매중|판매합니다|입고되었|입고완료|입고안내|재입고|예약판매|예약시작|예약이시작|공구합니다|공구해요|공구모집|스마트스토어|구매문의|당일발송|선착순|재고|디엠|dm|오픈합니다|증정|rt이벤트|팔로우|추첨|위치|매장|스토어|샵|폼~|위치"
)
PERSONAL_PAST_RE = re.compile(
    r"샀|사왔|사버려|사버림|산거|구매했|구매함|구매완료|겟했|겟함|겟한|득템|(?<![못안])뽑았(?!던)|(?<![못안])뽑음|뽑아봤|질렀|질러버렸|다녀왔|다녀옴|다녀왔어요|방문했|선물받았|선물받음|받았어|탑승|를삼|을삼"
)
PERSONAL_OTHER_RE = re.compile(
    r"갖고싶|가지고싶|사고싶|사고싶어|살까|살지|고민|구매걸어|예약했|결제했|안샀|못샀|포기|달고다|쓰다듬|아까워|가고싶|보고싶|정주행"
)
TRADE_RE = re.compile(r"양도|급처|반택|교환합니다|교환or|팝니다|구합니다|구함|소분|양도받")
SHOP_STOCK_RE = re.compile(r"입고되었|입고완료|예약판매|스마트스토어|당일발송|판매중입니다|재입고")
INFO_RE = re.compile(r"출시|발매|나왔|새로나|공개됐|공개되었|정보")
RAFFLE_RE = re.compile(r"\d+분|추첨|당첨|이벤트")


def speaker_of(n: str, post_n: str) -> str:
    if contains(post_n, r"양도합니다|양도합|반택포|팝니다") and not contains(n, r"귀엽|기여|행복|조아"):
        return "개인 거래"
    if contains(n, r"입으시|쓰고계시|사셨어|님이샀"):
        return "인용된 타인"
    if contains(n, r"들보면|사람들이달|갓반인들"):
        return "다른 사람 관찰"
    personal = contains(n, PERSONAL_PAST_RE.pattern) or contains(n, PERSONAL_OTHER_RE.pattern)
    trade = contains(n, TRADE_RE.pattern)
    shop = contains(n, SHOP_STOCK_RE.pattern) or contains(n, r"판매합니다|판매중|공구합니다|공구해요|구매문의|증정|rt이벤트|팔로우이벤트")
    # 명령형 판매 문안은 작성자 구매가 아님
    imperative = contains(n, r"구매하세|뽑아가|방문하세|사세|받아가|구매하시는분|드립니다|드려요|보내드려")
    if personal and not imperative:
        return "작성자"
    if trade and not shop:
        return "개인 거래"
    if shop or imperative or contains(n, r"판매|입고|예약|공구|이벤트|추첨"):
        # 게시물 전체에만 홍보가 있고 이 구절은 짧은 감상일 수 있다.
        if personal:
            return "작성자"
        if contains(n, r"판매|입고|예약판매|공구|이벤트|추첨|드립니다|구매문의|재고|품절|양도|팝니다|구합니다|스마트스토어|오픈"):
            return "판매·홍보" if not trade else "개인 거래"
    if contains(n, INFO_RE.pattern) and not personal:
        return "정보 공유"
    if contains(post_n, r"판매합니다|입고되었|공구합니다|예약판매") and not personal:
        return "판매·홍보"
    return "작성자"


def is_raffle(n: str) -> bool:
    return contains(n, r"추첨|당첨|분뽑|명을뽑|분에게|이벤트") and not contains(n, r"내가뽑|뽑았|뽑음|가챠뽑")


def purchase_state(n: str) -> str | None:
    if contains(n, r"꿈에서|꿈에"):
        return "꿈"
    # 가정·회상은 완료가 아니다.
    if contains(n, r"구매했을|샀을|샀다면|샀으면|살걸|살까말까했"):
        counterfactual = True
    else:
        counterfactual = False
    negative = contains(n, r"결국안샀|안샀다|안샀어|못샀다|못샀어|사지않|안살래|포기했|포기함")
    # '몇 개 안 샀는데', '한 마리밖에 못 사서'는 소량 구매다. '못샀던' 뒤에 결제 완료가 있으면 완료다.
    small_buy = contains(n, r"안샀는데|몇개안샀|밖에못사|밖에 못사")
    later_done = contains(n, r"결제완|구매완료|구매했|샀다|샀어|샀음|사버렸|사버려")
    if negative and not small_buy and not (contains(n, r"못샀던") and later_done):
        return "미수행"
    if contains(n, r"살까말까|살지말지|고민하|살까말|살말|고민중"):
        if later_done or contains(n, r"를삼|을삼|샀어|샀다|구매했"):
            return "완료"
        return "고민"
    if contains(n, r"사고싶|사고싶어|갖고싶|가지고싶|뽑고싶|구매하고싶|사고프|갖고프|질르고싶|원해"):
        if later_done:
            return "완료"
        return "희망"
    if contains(n, r"구매걸어|예약했|결제했|주문했"):
        if contains(n, r"도착|받았|왔당|왔다|개봉"):
            return "완료"
        return "시도"
    if contains(n, r"장바구니에담|장바구니넣"):
        return "시도"
    if counterfactual and not later_done:
        return None
    if contains(n, r"샀|사왔|사버렸|사버려|사버림|산거|구매했|구매함|구매완료|겟했|겟함|겟한|득템|질렀|질러버렸|를삼|을삼"):
        return "완료"
    if contains(n, r"(?<![못안])뽑았(?!던)|(?<![못안])뽑음|뽑아봤"):
        if contains(n, r"뽑으려|뽑아보려|뽑고싶"):
            return "희망"
        if contains(n, r"다고|라고") and contains(n, r"줬|주었|주심"):
            return None
        return "완료"
    if contains(n, r"뽑아보려|뽑으려구|뽑으러|뽑으러간"):
        return "희망"
    return None


def acquisition_of(n: str, state: str | None) -> str:
    if state is None:
        if contains(n, r"가챠|쿠지|제일복권"):
            return "판매·획득 방식만 언급"
        if contains(n, r"공구"):
            return "공동구매 문안"
        return "불명확"
    if is_raffle(n) and not contains(n, r"뽑았|뽑음|가챠"):
        return "불명확"
    if contains(n, r"선물받았|선물받음|선물해줬|선물주|선물해주"):
        return "선물"
    if contains(n, r"양도받|양도받았|교환했|교환해"):
        return "교환"
    if contains(n, r"나눔받|나눔해"):
        return "나눔"
    if contains(n, r"탑승|공구참여|공구했|공구로샀|공구로"):
        return "공동구매"
    if contains(n, r"인형뽑기"):
        return "인형뽑기"
    if contains(n, r"뽑았|뽑음|뽑아봤|가챠|쿠지|제일복권|돌렸") and contains(n, r"뽑|가챠|쿠지|제일복권"):
        if contains(n, r"샀|구매") and not contains(n, r"뽑았|뽑음|뽑아봤|돌렸"):
            return "직접 구매"
        return "가챠·뽑기"
    if contains(n, r"직구"):
        return "직접 구매"
    if state in {"완료", "시도", "희망", "고민", "미수행"} and contains(n, r"샀|사왔|사버렸|사서|구매|겟|득템|질렀|사고싶|갖고싶|살까"):
        if contains(n, r"가챠|뽑") and contains(n, r"뽑았|뽑음|뽑아"):
            return "가챠·뽑기"
        return "직접 구매"
    if contains(n, r"다녀왔|방문"):
        return "해당 없음(방문)"
    return "불명확"


def use_modes(n: str) -> list[tuple[str, str]]:
    """(use_mode, temporal) temporal: 경험/희망/보류"""
    modes = []
    rules = [
        ("가방·휴대전화 등에 달고 다니기", "경험", r"달고다|매달고다|가방에달|가방에착|폰에부착|붙여다|달고있"),
        ("가방·휴대전화 등에 달고 다니기", "희망", r"달고싶|매달고싶|부착해보고싶|달아보"),
        ("책상·선반 등에 전시하기", "경험", r"전시했|전시만|진열했|책상에두|선반에|올려뒀|올려두었|올려놓고|바라보는중"),
        ("책상·선반 등에 전시하기", "희망", r"전시해야지|진열하고싶|올려두고싶"),
        ("보관·소장하고 바라보기", "경험", r"쓰다듬|간직|바라보|안뜯|택보관|가지고놀|놀는중"),
        ("보관·소장하고 바라보기", "보류", r"아까워|먹기아깝|어케먹어|못쓰겠|절대못쓰"),
        ("문구·생활용품으로 사용하기", "경험", r"사용했|마셔봤|신어봤|끼고다"),
        ("문구·생활용품으로 사용하기", "희망", r"쓰고싶|사용해보"),
        ("옷·소품으로 착용하기", "경험", r"입고다녔|착용했|맞춰입|입어봤"),
        ("사진을 찍거나 일상 기록에 활용하기", "경험", r"사진찍었|사진꾸몄|인증샷|셀카찍|사진찍는중"),
        ("사진을 찍거나 일상 기록에 활용하기", "희망", r"사진찍고싶"),
        ("꾸미기·제작·재해석에 활용하기", "경험", r"꾸몄|만들어봤|탑꾸|붙여봤|직접만들었|펠트"),
        ("꾸미기·제작·재해석에 활용하기", "희망", r"내줘라|상품화해|만들어줘"),
        ("특정 캐릭터의 여러 상품·버전 모으기", "경험", r"전종|다모았|다모으|중복없이|올클"),
        ("여러 캐릭터를 조합하거나 세트 완성하기", "경험", r"세트완성|다모으면|같이두고"),
        ("여러 캐릭터를 조합하거나 세트 완성하기", "희망", r"다모으고싶|세트사고싶|같이모으"),
        ("선물하거나 다른 사람과 함께 즐기기", "경험", r"선물했|나눠줬|같이봤|같이갔|같이먹"),
        ("선물하거나 다른 사람과 함께 즐기기", "희망", r"선물하고싶|나눠주고싶"),
        ("이모티콘·콘텐츠로 감정을 표현하거나 소통하기", "경험", r"이모티콘.*썼|임티.*썼|이모티콘으로"),
        ("시청·관람·방문하기", "경험", r"다녀왔|다녀옴|다녀왔어요|방문했|정주행했|정주행함|정주행하고|보러갔|관람했|보고왔"),
        ("시청·관람·방문하기", "희망", r"가고싶|보러가고|(?<!해)보고싶|가보고싶"),
    ]
    for mode, temporal, pat in rules:
        if contains(n, pat):
            modes.append((mode, temporal))
    # 전시해야 한다고 배웠습니다 + 이벤트 문안은 작성자 전시 경험이 아님. 호출부에서 화자 확인.
    uniq = []
    seen = set()
    for item in modes:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def classify_reason_left(left: str) -> tuple[str, str]:
    """return (kind, label). 분류에 안 들어가면 이유로 만들지 않는다."""
    seg = re.split(r"지만|는데", left)[-1][-18:]
    if contains(seg, r"싶$|싶어서|사야지|해야지|해야겠"):
        return "none", ""
    if contains(seg, r"비싸|비쌈|가격|돈없|예산|돈이"):
        return "barrier", "가격·예산"
    if contains(seg, r"품절|재고가없|없어서|못구") and not contains(seg, r"귀여|귀엽|기여|좋|이쁘"):
        return "barrier", "부재·품절·구매경로"
    if contains(seg, r"욕조|자리없|둘곳|장소가없"):
        return "barrier", "사용 환경"
    if contains(seg, r"파본|불량|하자|부서|망가|때탈|때묻"):
        return "barrier", "품질·관리 걱정"
    if contains(seg, r"표정|포즈|의상|눈빛|눈망|볼살|미소|앞머리"):
        return "like", "특정 표정·의상·포즈·장면"
    if contains(seg, r"말랑|부들|부드럽|투명|퀄리티|품질|마감|재질|촉감|별모양|작아서|쪼끄|동그랗"):
        return "like", "촉감·품질·기능 등 상품 구현"
    if contains(seg, r"힐링|위로|소중"):
        return "like", "바라볼 때 느끼는 즐거움·위로"
    if contains(seg, r"다모으|모으면|같이두|전종|올클"):
        return "like", "세트·조합·시리즈를 완성하는 즐거움"
    if contains(seg, r"실용|편하|유용"):
        return "like", "실용성과 캐릭터 디자인의 결합"
    if contains(seg, r"옆에|가까이|매일보|데리고다|달고다니"):
        return "like", "좋아하는 캐릭터를 가까이 두는 즐거움"
    if contains(seg, r"꾸미|데코|인증"):
        return "like", "취향을 드러내거나 일상을 꾸미는 즐거움"
    if contains(seg, r"아까워|아깝"):
        return "like", "기타: 아까워서 아껴 둠"
    if contains(seg, r"우울|심심|힘들|위로받"):
        return "other", "기타: 기분·상황"
    if contains(seg, r"싸서|싸게|할인"):
        return "other", "기타: 가격 조건"
    if contains(seg, r"있길래|팔길래|반가|보이길래"):
        return "other", "기타: 발견·반가움·눈에 띔"
    if contains(seg, r"닮|지미니|똑같"):
        return "other", "기타: 다른 대상과 닮아 보임"
    if contains(seg, r"귀여|귀엽|기여|이쁘|예쁘|조아|조흠|취향"):
        return "like", "포괄 호감(세부 특징 없음)"
    return "none", ""


def reasons_in(n: str) -> list[dict]:
    found = []
    for m in re.finditer(r"아서|어서|해서|여서|워서|뻐서|겨서|싸서|라서|때문에|니까|길래", n):
        prev = n[m.start() - 1 : m.start()]
        token = m.group()
        if token == "어서" and prev == "에":
            continue
        if token == "아서" and "것같" in n[max(0, m.start() - 3) : m.start() + 2]:
            continue
        left = n[: m.start()]
        right = n[m.end() :]
        if token == "길래" and re.search(r"(있|팔|반가)$", left):
            found.append({"kind": "other", "label": "기타: 발견·반가움·눈에 띔", "left": left[-40:], "right": right, "conn": token, "at": m.end()})
            continue
        if token == "니까" and n[max(0, m.start() - 2) : m.start()] == "하":
            # '하니까' 인용·전달은 이유 연결로 쓰지 않는다.
            if contains(n[m.end() : m.end() + 8], r"했|한|라고"):
                continue
        kind, label = classify_reason_left(left)
        if kind == "none":
            continue
        found.append({"kind": kind, "label": label, "left": left[-40:], "right": right, "conn": token, "at": m.end()})
    return found


def detect_actions(n: str, speaker: str) -> list[dict]:
    actions = []
    state = purchase_state(n)
    if state == "꿈":
        actions.append(
            {
                "behavior": "판단 불가",
                "behavior_status": "판단 불가",
                "temporal": "판단 불가",
                "acquisition": "불명확",
                "use_mode": "방식 불명확",
                "like_reason": "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "연결 불명확",
                "note": "꿈·상상 속 구매. 실제 획득으로 세지 않음",
            }
        )
        state = None
    acq = acquisition_of(n, state)
    reasons = reasons_in(n)
    like = next((r for r in reasons if r["kind"] == "like"), None)
    other = next((r for r in reasons if r["kind"] == "other"), None)
    barrier = next((r for r in reasons if r["kind"] == "barrier"), None)
    # 부정 구매가 있으면 호감 이유보다 장벽을 우선 기록하고, 호감은 같은 구절에 연결어가 있을 때만 남긴다.
    if state == "미수행":
        actions.append(
            {
                "behavior": "구매 시도·실패·포기",
                "behavior_status": "미수행·포기",
                "temporal": "경험",
                "acquisition": acq if acq != "판매·획득 방식만 언급" else "불명확",
                "use_mode": "방식 불명확",
                "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                "barrier": barrier["label"] if barrier else "장벽 이유는 문장으로 특정 안 됨",
                "link_level": "명시적 선호·이유" if like else ("문맥상 연결" if barrier else "문맥상 연결"),
                "note": "사지 않았다는 말. 호감 이유가 아니면 선호로 올리지 않음",
            }
        )
        if contains(n, r"고민|살말|살까"):
            actions.append(
                {
                    "behavior": "구매 고민",
                    "behavior_status": "고민",
                    "temporal": "희망",
                    "acquisition": "불명확",
                    "use_mode": "방식 불명확",
                    "like_reason": "이유 미언급·판단 불가",
                    "barrier": "",
                    "link_level": "문맥상 연결",
                    "note": "고민 끝에 사지 않음. 고민의 이유와 포기 이유는 따로 봄",
                }
            )
    elif state == "고민":
        actions.append(
            {
                "behavior": "구매 고민",
                "behavior_status": "고민",
                "temporal": "희망",
                "acquisition": acq if "구매" in acq or acq == "직접 구매" else "불명확",
                "use_mode": "방식 불명확",
                "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                "barrier": barrier["label"] if barrier else "",
                "link_level": "명시적 선호·이유" if like else "문맥상 연결",
                "note": "고민은 구매 완료가 아님",
            }
        )
    elif state == "희망":
        actions.append(
            {
                "behavior": "구매·소장·사용 희망",
                "behavior_status": "희망",
                "temporal": "희망",
                "acquisition": acq if acq not in {"판매·획득 방식만 언급"} else "불명확",
                "use_mode": "방식 불명확",
                "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                "barrier": barrier["label"] if barrier else "",
                "link_level": "명시적 선호·이유" if (like or other) else "문맥상 연결",
                "note": other["label"] if other and not like else "사고 싶다·갖고 싶다·뽑고 싶다",
            }
        )
        if other and not like:
            actions[-1]["like_reason"] = other["label"]
    elif state == "시도":
        actions.append(
            {
                "behavior": "구매 시도·실패·포기",
                "behavior_status": "시도(수령 확인 안 됨)",
                "temporal": "시도",
                "acquisition": "직접 구매",
                "use_mode": "방식 불명확",
                "like_reason": like["label"] if like else (other["label"] if other else "이유 미언급·판단 불가"),
                "barrier": "",
                "link_level": "명시적 선호·이유" if (like or other) else "문맥상 연결",
                "note": "결제·예약·구매를 걸어 두었다는 말. 수령·사용 완료로 올리지 않음",
            }
        )
    elif state == "완료":
        # 화자가 판매자면 작성자 구매가 아님
        if speaker in {"판매·홍보", "개인 거래"} and not contains(n, r"나는|난|제가|저는|내가|나만|저도"):
            pass
        else:
            actions.append(
                {
                    "behavior": "구매·획득 경험",
                    "behavior_status": "완료·경험",
                    "temporal": "경험",
                    "acquisition": acq,
                    "use_mode": "방식 불명확",
                    "like_reason": like["label"] if like else (other["label"] if other else "이유 미언급·판단 불가"),
                    "barrier": barrier["label"] if barrier else "",
                    "link_level": "명시적 선호·이유" if (like or other) else "문맥상 연결",
                    "note": "구매·뽑기·획득을 말했음. 이것만으로 만족이나 선호로 보지 않음",
                }
            )
    if contains(n, r"선물받았|선물받음|선물해줬|선물해주셨|협찬"):
        if speaker == "작성자" or contains(n, r"받았|받음"):
            actions.append(
                {
                    "behavior": "구매·획득 경험",
                    "behavior_status": "완료·경험",
                    "temporal": "경험",
                    "acquisition": "선물",
                    "use_mode": "방식 불명확",
                    "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                    "barrier": "",
                    "link_level": "명시적 선호·이유" if like else "문맥상 연결",
                    "note": "협찬·제공 포함 가능" if contains(n, r"협찬") else "선물 수령",
                }
            )
    if contains(n, r"다녀왔|다녀왔어요|방문했|보고왔|보러갔|관람했|정주행"):
        if speaker == "작성자" or contains(n, r"다녀|정주행|봤"):
            if not contains(n, r"방문하세|방문하시면"):
                actions.append(
                    {
                        "behavior": "시청·방문 경험",
                        "behavior_status": "완료·경험",
                        "temporal": "경험",
                        "acquisition": "해당 없음(방문·시청)",
                        "use_mode": "시청·관람·방문하기",
                        "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                        "barrier": "",
                        "link_level": "명시적 선호·이유" if like else "문맥상 연결",
                        "note": "다녀왔다·정주행 등 완료 표현",
                    }
                )
    if contains(n, r"가고싶|보러가고|보고싶|정주행하고싶|가보고싶"):
        actions.append(
            {
                "behavior": "시청·방문 희망",
                "behavior_status": "희망",
                "temporal": "희망",
                "acquisition": "해당 없음(방문·시청)",
                "use_mode": "시청·관람·방문하기",
                "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "문맥상 연결",
                "note": "방문·시청 희망",
            }
        )
    if speaker == "작성자":
        for mode, temporal in use_modes(n):
            if mode == "시청·관람·방문하기":
                if contains(n, r"스트리밍시작|정주행시작|방송시작"):
                    continue
            # 판매 문안의 '전시해야 한다고 배웠습니다' 는 작성자 사용이 아님
            if mode.startswith("책상") and contains(n, r"배웠습니다|이벤트|팔로우|rt|올려두면"):
                continue
            if mode.startswith("가방") and contains(n, r"들보면|사람들이|갓반인|분들보면"):
                continue
            if "모으" in mode and contains(n, r"악마적|조합처음|이런조합"):
                continue
            behavior = "실제 소유·사용·수집 경험" if temporal in {"경험", "보류"} else "구매·소장·사용 희망"
            actions.append(
                {
                    "behavior": behavior,
                    "behavior_status": "완료·경험" if temporal in {"경험", "보류"} else "희망",
                    "temporal": "경험" if temporal in {"경험", "보류"} else "희망",
                    "acquisition": "불명확",
                    "use_mode": mode,
                    "like_reason": "기타: 아까워서 아껴 둠" if temporal == "보류" else (like["label"] if like else "이유 미언급·판단 불가"),
                    "barrier": "",
                    "link_level": "명시적 선호·이유" if temporal == "보류" or like else "문맥상 연결",
                    "note": "아껴서 쓰지 않음. 불만이나 실패로 보지 않음" if temporal == "보류" else "사용·소장 표현",
                }
            )
    if speaker == "개인 거래" and contains(n, r"양도|팝니다|급처|교환|구합니다|구함|소분"):
        status = "희망" if contains(n, r"구합니다|구함|양도받|사요|삽니다") else "제안·진행"
        actions.append(
            {
                "behavior": "판매·교환·양도",
                "behavior_status": status,
                "temporal": "해당 없음",
                "acquisition": "교환" if contains(n, r"교환") else "불명확",
                "use_mode": "방식 불명확",
                "like_reason": "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "문맥상 연결",
                "note": "개인 거래 문안. 이용 만족으로 세지 않음",
            }
        )
    if speaker == "판매·홍보" and not actions:
        channel = sales_channel(n)
        actions.append(
            {
                "behavior": "판매·홍보 소개",
                "behavior_status": "판매 정보",
                "temporal": "해당 없음",
                "acquisition": channel,
                "use_mode": "방식 불명확",
                "like_reason": "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "문맥상 연결",
                "note": "판매·입고·모집 문안. 작성자 소유·선호로 세지 않음",
            }
        )
    if speaker == "정보 공유" and not any(a["behavior"] != "판매·홍보 소개" for a in actions):
        actions.append(
            {
                "behavior": "정보 공유",
                "behavior_status": "정보",
                "temporal": "해당 없음",
                "acquisition": "불명확",
                "use_mode": "방식 불명확",
                "like_reason": "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "단순 공존",
                "note": "출시·발매 소식. 작성자 구매로 세지 않음",
            }
        )
    if contains(n, r"데려왔|모셔왔|모셨"):
        actions.append(
            {
                "behavior": "판단 불가",
                "behavior_status": "판단 불가",
                "temporal": "판단 불가",
                "acquisition": "불명확",
                "use_mode": "방식 불명확",
                "like_reason": like["label"] if like else "이유 미언급·판단 불가",
                "barrier": "",
                "link_level": "연결 불명확",
                "note": "데려오다·모셔오다는 결제·선물·뽑기를 확정하지 않음",
            }
        )
    if contains(n, r"욕조가없|욕조없"):
        for a in actions:
            if a["behavior"] == "구매·획득 경험":
                a["barrier"] = "사용 환경"
                a["note"] += " 사고 난 뒤 쓸 곳이 없다고 말함. 상품 불만으로 단정하지 않음."
    actions = bind_reasons(actions, reasons)
    # 같은 행동·방식 중복 제거
    uniq = []
    seen = set()
    for a in actions:
        key = (a["behavior"], a["behavior_status"], a["use_mode"], a["acquisition"], a["like_reason"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq


def bind_reasons(actions: list[dict], reasons: list[dict]) -> list[dict]:
    """이유 연결어의 오른쪽에 있는 행동에만 이유를 붙인다."""
    for a in actions:
        if a.get("temporal") == "보류":
            continue
        a["like_reason"] = "이유 미언급·판단 불가"
        if a.get("link_level") == "명시적 선호·이유":
            a["link_level"] = "문맥상 연결"
    for a in actions:
        if a.get("temporal") == "보류":
            continue
        for r in reasons:
            right = r["right"]
            hit = False
            beh = a["behavior"]
            if beh == "구매·획득 경험" and contains(right, r"샀|사왔|사버렸|사버려|구매|겟|뽑|질렀"):
                hit = True
            elif beh == "구매·소장·사용 희망" and contains(right, r"싶|원해"):
                hit = True
            elif beh == "구매 고민" and contains(right, r"고민|살까|살말"):
                hit = True
            elif beh == "구매 시도·실패·포기" and str(a["behavior_status"]).startswith("미수행") and contains(right, r"안샀|못샀|포기"):
                hit = True
            elif beh == "구매 시도·실패·포기" and "시도" in str(a["behavior_status"]) and contains(right, r"구매걸어|예약했|결제"):
                hit = True
            elif beh in {"실제 소유·사용·수집 경험", "시청·방문 경험", "시청·방문 희망"} and contains(right, r"쓰|달고|보러|먹|입|다녀|정주행"):
                hit = True
            if not hit:
                continue
            if r["kind"] == "barrier":
                a["barrier"] = r["label"]
                a["judgment_note"] = a.get("note", "")
            elif r["kind"] in {"like", "other"} and not str(a["behavior_status"]).startswith("미수행"):
                a["like_reason"] = r["label"]
                a["link_level"] = "명시적 선호·이유"
    return actions


def sales_channel(n: str) -> str:
    channels = []
    if contains(n, r"가챠"):
        channels.append("가챠")
    if contains(n, r"쿠지|제일복권"):
        channels.append("쿠지")
    if contains(n, r"공구"):
        channels.append("공동구매 모집")
    if contains(n, r"직구|배대지|토레바"):
        channels.append("직구")
    if contains(n, r"예약판매|예약시작|예약이시작"):
        channels.append("예약판매")
    if contains(n, r"랜덤"):
        channels.append("랜덤")
    return "|".join(channels) if channels else "판매 채널 불명확"


def screen_hits(n: str) -> list[str]:
    hits = []
    for name, pat in SCREEN_PATTERNS.items():
        if contains(n, pat):
            hits.append(name)
    return hits


def code_post(row: dict) -> list[dict]:
    text = newlines(row["text"])
    post_n = norm(text)
    evid = []
    cls = clauses_of(text)
    for clause in cls:
        n = norm(clause)
        if not n:
            continue
        products = find_products(n)
        speaker = speaker_of(n, post_n)
        actions = detect_actions(n, speaker)
        chars = find_characters(n)
        char, char_link, about = character_fields(chars)
        # 상품도 행동도 없으면 소비 근거 아님
        if not products and not actions:
            continue
        # 행동만 있고 상품이 없으면, 소비 동사가 있는 경우만
        if not products and actions:
            # 장면 웃음·귀여움만인 희망 오탐 억제: 상품·장소·획득 단서가 하나도 없으면 제외
            if not contains(
                n,
                r"샀|구매|뽑|선물|가챠|굿즈|인형|키링|카페|팝업|애니|영화|이모티콘|임티|양도|공구|실물|갖고싶|사고싶|판매|예약|입고|잠옷|메이커|누이|마스코트|스티커|피규|파자마|살말|고민",
            ):
                continue
            products = [
                {
                    "product_form": "형태 불명확",
                    "product_span": "",
                    "function_axis": "기능 불명확",
                    "variant": "",
                    "product_note": "구절에 소비 동사는 있으나 상품 형태 명사가 없음",
                }
            ]
        if not actions and products:
            # 이름만 있는 상품. 귀엽다가 같이 있으면 감상 언급.
            vague = "포괄 호감(세부 특징 없음)" if contains(n, r"귀엽|기여|이쁘|좋|사랑") else "이유 미언급·판단 불가"
            link = "단순 공존" if vague.startswith("포괄") else "이용 방식 없음"
            actions = [
                {
                    "behavior": "상품·콘텐츠 언급",
                    "behavior_status": "언급",
                    "temporal": "해당 없음",
                    "acquisition": sales_channel(n) if speaker in {"판매·홍보", "개인 거래"} else "불명확",
                    "use_mode": "방식 불명확",
                    "like_reason": "이유 미언급·판단 불가",
                    "barrier": "",
                    "link_level": link,
                    "note": "상품 또는 행사 이름이 있음. 귀엽다·좋다는 선호 이유로 올리지 않음",
                }
            ]
        place_forms = {"팝업·전시", "카페·매장", "콜라보·행사"}
        goods_present = any(p["product_form"] not in place_forms | {"애니메이션", "영화", "이모티콘"} for p in products)
        buy_behaviors = {"구매·획득 경험", "구매·소장·사용 희망", "구매 고민", "구매 시도·실패·포기"}
        for product in products:
            for action in actions:
                if product["product_form"] in place_forms and goods_present and action["behavior"] in buy_behaviors:
                    continue
                if product["product_form"] in {"애니메이션", "영화"} and action["behavior"] in buy_behaviors:
                    continue
                # 판매 문안이 전시·사용 규칙을 가져온 경우 작성자 사용으로 둔 것은 detect에서 화자로 걸렀다.
                link_level = action["link_level"]
                if action["like_reason"] not in {"", "이유 미언급·판단 불가"} and action["link_level"] == "명시적 선호·이유":
                    link_level = "명시적 선호·이유"
                elif action["behavior"] == "상품·콘텐츠 언급":
                    link_level = action["link_level"]
                elif product["product_form"] == "형태 불명확":
                    link_level = "연결 불명확"
                evid.append(
                    {
                        "quote": clause,
                        "character": char,
                        "character_link": char_link,
                        "about_ip": about,
                        "product_form": product["product_form"],
                        "product_span": product["product_span"],
                        "variant": product["variant"],
                        "function_axis": product["function_axis"] if action["use_mode"] in {"방식 불명확", ""} else action["use_mode"],
                        "function_from_name": product["function_axis"],
                        "acquisition": action["acquisition"],
                        "use_mode": action["use_mode"],
                        "temporal": action["temporal"],
                        "behavior": action["behavior"],
                        "behavior_status": action["behavior_status"],
                        "like_reason": action["like_reason"],
                        "barrier": action["barrier"],
                        "speaker": speaker,
                        "link_level": link_level,
                        "judgment_note": " ".join(
                            x
                            for x in [
                                action["note"],
                                product["product_note"],
                                f"버전:{product['variant']}" if product["variant"] else "",
                            ]
                            if x
                        ),
                    }
                )
    # 구절을 넘는 연결은 상품 형태가 하나일 때만 단순 공존으로 붙인다.
    forms = [e for e in evid if e["product_form"] not in {"형태 불명확"}]
    unclear_actions = [e for e in evid if e["product_form"] == "형태 불명확"]
    distinct_forms = {e["product_form"] for e in forms}
    if len(distinct_forms) == 1 and unclear_actions:
        only = next(iter(distinct_forms))
        sample = next(e for e in forms if e["product_form"] == only)
        for e in unclear_actions:
            if e["behavior"] == "상품·콘텐츠 언급":
                continue
            e["product_form"] = only
            e["product_span"] = sample["product_span"]
            if e["link_level"] != "명시적 선호·이유":
                e["link_level"] = "단순 공존"
            e["judgment_note"] += " 같은 글의 상품 형태가 하나라 다른 구절의 행동과 단순 공존으로 연결."
            e["character"] = e["character"] if e["character"] != "본문에서 캐릭터 미언급" else sample["character"]
    elif len(distinct_forms) > 1 and unclear_actions:
        for e in unclear_actions:
            e["link_level"] = "연결 불명확"
            e["judgment_note"] += " 상품이 여러 형태라 다른 구절의 행동과 조합하지 않음."
    # 동일 키 축약
    uniq = []
    seen = set()
    for e in evid:
        key = (
            e["quote"],
            e["product_form"],
            e["behavior"],
            e["behavior_status"],
            e["use_mode"],
            e["like_reason"],
            e["speaker"],
            e["acquisition"],
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    return uniq


def apply_overrides(post_id: str, evid: list[dict], overrides: list[dict]) -> list[dict]:
    for ov in overrides:
        if ov.get("post_id") != post_id:
            continue
        op = ov.get("op")
        if op == "drop_post_evidence":
            return []
        if op == "drop_if_quote_contains":
            needle = ov["quote_contains"]
            evid = [e for e in evid if needle not in e["quote"]]
        elif op == "patch":
            needle = ov.get("quote_contains", "")
            for e in evid:
                if needle and needle not in e["quote"]:
                    continue
                for k, v in ov.get("fields", {}).items():
                    e[k] = v
                e["judgment_note"] = (e.get("judgment_note") or "") + " 모델 문맥 수정."
        elif op == "add":
            evid.append(ov["evidence"])
    return evid


def join_unique(values: list[str]) -> str:
    out = []
    for v in values:
        if v and v not in out:
            out.append(v)
    return "|".join(out)


def post_summary(row: dict, evid: list[dict], screened: list[str], model_read: set[str], image_checks: dict) -> dict:
    year = row["created_at"][:4]
    pid = row["post_id"]
    contexts = []
    if any(e["speaker"] == "판매·홍보" for e in evid):
        contexts.append("판매·홍보")
    if any(e["speaker"] == "개인 거래" for e in evid):
        contexts.append("개인 거래")
    if any(e["speaker"] == "정보 공유" for e in evid):
        contexts.append("정보 공유")
    if any(e["speaker"] == "작성자" and e["temporal"] == "경험" for e in evid):
        contexts.append("개인 경험")
    if any(e["speaker"] == "작성자" and e["temporal"] in {"희망", "시도"} for e in evid):
        contexts.append("개인 희망·시도")
    if any(e["speaker"] == "작성자" and e["behavior"] == "구매 고민" for e in evid):
        contexts.append("개인 고민")
    if any(e["speaker"] == "작성자" and e["behavior"] == "상품·콘텐츠 언급" for e in evid):
        contexts.append("개인 언급·감상")
    if not evid:
        if screened:
            contexts.append("선별됐으나 소비 근거 없음")
        else:
            contexts.append("소비·상품 관련 표현 없음")
    if any(e["temporal"] == "경험" and e["speaker"] == "작성자" for e in evid):
        primary = "개인 경험"
    elif any(e["behavior"] == "구매 고민" for e in evid):
        primary = "구매 고민"
    elif any(e["temporal"] in {"희망", "시도"} and e["speaker"] == "작성자" for e in evid):
        primary = "개인 희망·시도"
    elif "개인 거래" in contexts and "개인 경험" not in contexts:
        primary = "개인 거래"
    elif "판매·홍보" in contexts:
        primary = "판매·홍보"
    elif "정보 공유" in contexts:
        primary = "정보 공유"
    elif evid:
        primary = "상품·콘텐츠 언급"
    else:
        primary = contexts[0]
    img = image_checks.get(pid, {})
    needs_image = any(
        e["speaker"] == "작성자"
        and e["product_form"] in {"형태 불명확", "형태 불특정 굿즈"}
        and e["behavior"] not in {"상품·콘텐츠 언급", "정보 공유"}
        and "http" in row["text"]
        for e in evid
    )
    if img.get("image_checked") == "예":
        image_status = "확인함"
    elif img.get("image_checked") == "실패":
        image_status = "확인 실패"
    elif needs_image:
        image_status = "필요하나 미확인"
    elif "http" in row["text"] and evid:
        image_status = "본문으로 분류, 사진 미확인"
    else:
        image_status = "사진 확인 대상 아님"
    review = []
    if any(e["link_level"] == "연결 불명확" for e in evid):
        review.append("연결 불명확")
    if needs_image and img.get("image_checked") != "예":
        review.append("사진 확인 필요")
    if any(e["behavior"] == "판단 불가" for e in evid):
        review.append("행동 판단 불가")
    if screened and not evid:
        review.append("선별 잔여")
    method = "model_context" if pid in model_read else ("rule_calibrated" if evid or screened else "rule_screen")
    return {
        "post_id": pid,
        "post_url": row["post_url"],
        "account_id": row["account_id"],
        "account_name": row["account_name"],
        "text": row["text"],
        "created_at": row["created_at"],
        "created_year_kst": year,
        "source_year": row.get("source_year", ""),
        "comment_count": row["comment_count"],
        "repost_count": row["repost_count"],
        "view_count": row["view_count"],
        "like_count": row["like_count"],
        "screen_hits": "|".join(screened),
        "screen_status": "후보" if screened else "비후보",
        "post_context_labels": "|".join(contexts),
        "primary_context": primary,
        "context_mixed": "예" if len([c for c in contexts if c not in {"소비·상품 관련 표현 없음"}]) > 1 else "아니오",
        "evidence_n": len(evid),
        "product_forms": join_unique([e["product_form"] for e in evid]),
        "use_modes": join_unique([e["use_mode"] for e in evid if e["use_mode"] not in {"", "방식 불명확"}]),
        "behaviors": join_unique([e["behavior"] for e in evid]),
        "like_reasons": join_unique(
            [e["like_reason"] for e in evid if e["like_reason"] not in {"", "이유 미언급·판단 불가"}]
        ),
        "speakers": join_unique([e["speaker"] for e in evid]),
        "link_levels": join_unique([e["link_level"] for e in evid]),
        "image_status": image_status,
        "image_observation": img.get("image_observation", ""),
        "judgment_method": method,
        "review_flag": "예" if review else "아니오",
        "review_reasons": "|".join(review),
        "processing_status": "완료",
        "processing_error": "",
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def validate(posts: pd.DataFrame, evid: pd.DataFrame) -> list[str]:
    messages = []
    if posts["post_id"].nunique() != len(posts) or len(posts) != 5000:
        messages.append(f"게시물 수 오류 {len(posts)} 고유 {posts['post_id'].nunique()}")
    else:
        messages.append("게시물 5,000 고유 post_id 확인")
    if evid.empty:
        messages.append("근거 0건")
        return messages
    missing = (~evid["post_id"].isin(set(posts["post_id"]))).sum()
    messages.append(f"근거 게시물 누락 {int(missing)}")
    text_map = dict(zip(posts["post_id"], posts["text"].map(newlines)))
    bad = 0
    for pid, quote in zip(evid["post_id"], evid["quote"]):
        if quote not in text_map[pid]:
            bad += 1
    messages.append(f"원문에 없는 인용 {bad}")
    messages.append(f"근거 행 {len(evid)} 고유 게시물 {evid['post_id'].nunique()}")
    return messages


def agg_form_speaker(evid: pd.DataFrame, denom_posts: int) -> pd.DataFrame:
    rows = []
    if evid.empty:
        return pd.DataFrame()
    for (form, speaker), g in evid.groupby(["product_form", "speaker"], dropna=False):
        rows.append(
            {
                "product_form": form,
                "speaker": speaker,
                "unique_posts": g["post_id"].nunique(),
                "evidence_rows": len(g),
                "unique_accounts": g["account_id"].nunique(),
                "denominator_posts": denom_posts,
                "denominator_label": "전체 게시물",
                "row_overlap": "한 게시물이 여러 형태·화자에 중복될 수 있음",
                "count_unit": "고유 post_id 와 근거 행을 둘 다 표시",
            }
        )
    return pd.DataFrame(rows).sort_values(["speaker", "unique_posts"], ascending=[True, False])


def cross_table(evid: pd.DataFrame, row_col: str, col_col: str, denom: int, denom_label: str) -> pd.DataFrame:
    if evid.empty:
        return pd.DataFrame()
    records = []
    for (a, b), g in evid.groupby([row_col, col_col], dropna=False):
        records.append(
            {
                row_col: a,
                col_col: b,
                "unique_posts": g["post_id"].nunique(),
                "evidence_rows": len(g),
                "unique_accounts": g["account_id"].nunique(),
                "denominator_posts": denom,
                "denominator_label": denom_label,
                "row_overlap": "한 게시물이 여러 칸에 들어갈 수 있음. 칸 합은 게시물 총계가 아님",
                "count_unit": "고유 post_id / 근거 행",
            }
        )
    return pd.DataFrame(records)


def concentration(evid: pd.DataFrame, label: str) -> dict:
    if evid.empty:
        return {"slice": label, "posts": 0, "accounts": 0, "top_account_posts": 0, "top_account_share": ""}
    vc = evid.groupby("account_id")["post_id"].nunique().sort_values(ascending=False)
    posts = evid["post_id"].nunique()
    top = int(vc.iloc[0]) if len(vc) else 0
    return {
        "slice": label,
        "posts": posts,
        "accounts": int(evid["account_id"].nunique()),
        "top_account_posts": top,
        "top_account_share": f"{top / posts:.1%}" if posts else "",
        "top_account_id": vc.index[0] if len(vc) else "",
    }


def make_charts(form_speaker: pd.DataFrame, use_cross: pd.DataFrame, use_temp: pd.DataFrame, reasons: pd.DataFrame) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager
    from matplotlib import pyplot as plt

    font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    written = []
    CHARTS.mkdir(parents=True, exist_ok=True)

    # 1. 작성자 경험 vs 판매 소개, 형태별 고유 게시물
    if not form_speaker.empty:
        focus_speakers = ["작성자", "판매·홍보", "개인 거래"]
        sub = form_speaker[form_speaker["speaker"].isin(focus_speakers)].copy()
        # 상위 형태
        top_forms = (
            sub.groupby("product_form")["unique_posts"].sum().sort_values(ascending=False).head(12).index.tolist()
        )
        sub = sub[sub["product_form"].isin(top_forms)]
        pivot = sub.pivot_table(index="product_form", columns="speaker", values="unique_posts", fill_value=0)
        pivot = pivot.reindex(top_forms)
        fig, ax = plt.subplots(figsize=(10, 7))
        pivot.plot(kind="barh", ax=ax)
        ax.set_xlabel("고유 게시물 수")
        ax.set_ylabel("")
        ax.set_title("상품 형태별 게시물 수\n작성자 근거와 판매·홍보를 나눔. 한 글이 여러 형태에 중복될 수 있음")
        ax.invert_yaxis()
        fig.tight_layout()
        path = CHARTS / "01_form_by_speaker.png"
        fig.savefig(path, dpi=140)
        plt.close()
        written.append(str(path))

    if not use_cross.empty:
        pivot = use_cross.pivot_table(index="product_form", columns="use_mode", values="unique_posts", fill_value=0)
        if pivot.size:
            fig, ax = plt.subplots(figsize=(12, 8))
            im = ax.imshow(pivot.values, aspect="auto", cmap="Blues")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=8)
            ax.set_title("작성자 경험: 상품 형태 × 이용 방식\n칸 값은 고유 게시물. 합계는 총게시물이 아님")
            fig.colorbar(im, ax=ax, fraction=0.03)
            fig.tight_layout()
            path = CHARTS / "02_form_x_use_experience.png"
            fig.savefig(path, dpi=140)
            plt.close()
            written.append(str(path))

    if not use_temp.empty:
        pivot = use_temp.pivot_table(index="use_mode", columns="temporal", values="unique_posts", fill_value=0)
        fig, ax = plt.subplots(figsize=(8, 6))
        pivot.plot(kind="barh", ax=ax)
        ax.set_xlabel("고유 게시물 수")
        ax.set_title("이용 방식 × 경험·희망\n희망과 경험을 한 퍼널로 쌓지 않음")
        ax.invert_yaxis()
        fig.tight_layout()
        path = CHARTS / "03_use_by_temporal.png"
        fig.savefig(path, dpi=140)
        plt.close()
        written.append(str(path))

    if not reasons.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        plot_df = reasons.sort_values("unique_posts", ascending=True)
        ax.barh(plot_df["like_reason"], plot_df["unique_posts"])
        ax.set_xlabel("고유 게시물 수")
        ax.set_title("명시적 선호·이유 (작성자)\n포괄 호감은 세부 특징으로 세지 않음")
        fig.tight_layout()
        path = CHARTS / "04_explicit_reasons.png"
        fig.savefig(path, dpi=140)
        plt.close()
        written.append(str(path))
    return written


def write_review_packs(posts: pd.DataFrame, evid: pd.DataFrame) -> None:
    text_map = dict(zip(posts["post_id"], posts["text"].map(newlines)))
    url_map = dict(zip(posts["post_id"], posts["post_url"]))

    def dump(ids: list[str], path: Path, limit: int | None = None) -> None:
        lines = []
        use_ids = ids if limit is None else ids[:limit]
        for pid in use_ids:
            lines.append(f"\n### {pid}")
            lines.append(url_map.get(pid, ""))
            lines.append(text_map.get(pid, "").replace("\n", " / "))
            sub = evid[evid["post_id"] == pid]
            if sub.empty:
                lines.append("(근거 없음)")
                continue
            for _, e in sub.iterrows():
                lines.append(
                    " - {form} | {beh}/{st} | {use}/{temp} | {reason} | {link} | {spk} | {acq}".format(
                        form=e["product_form"],
                        beh=e["behavior"],
                        st=e["behavior_status"],
                        use=e["use_mode"],
                        temp=e["temporal"],
                        reason=e["like_reason"],
                        link=e["link_level"],
                        spk=e["speaker"],
                        acq=e["acquisition"],
                    )
                )
        path.write_text("\n".join(lines), encoding="utf-8")

    user = evid[(evid["speaker"] == "작성자") & (~evid["behavior"].isin(["상품·콘텐츠 언급"]))]
    user_ids = user["post_id"].drop_duplicates().tolist()
    dump(user_ids, WORKING / "review_user_actions.md")
    explicit = evid[(evid["speaker"] == "작성자") & (evid["link_level"] == "명시적 선호·이유")]
    dump(explicit["post_id"].drop_duplicates().tolist(), WORKING / "review_explicit.md")
    seller = evid[evid["speaker"] == "판매·홍보"]["post_id"].drop_duplicates()
    sample_seller = seller.sample(n=min(40, len(seller)), random_state=20261103).tolist() if len(seller) else []
    dump(sample_seller, WORKING / "review_seller_sample.md")
    residuals = posts[(posts["screen_status"] == "후보") & (posts["evidence_n"] == 0)]["post_id"].tolist()
    dump(residuals[:120], WORKING / "review_residuals.md")
    non = posts[posts["screen_status"] == "비후보"]
    sample_non = non.sample(n=min(40, len(non)), random_state=20261103)["post_id"].tolist()
    dump(sample_non, WORKING / "review_noncandidate_sample.md")
    queue = posts[posts["image_status"] == "필요하나 미확인"][
        ["post_id", "post_url", "primary_context", "product_forms", "behaviors", "text"]
    ]
    write_csv(queue, WORKING / "image_queue.csv")


def main() -> None:
    WORKING.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(POSTS, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    sources = pd.read_csv(SOURCES, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    files = pd.read_csv(FILES, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    src = sources.merge(files, on="source_file", how="left")
    raw = raw.merge(src[["post_id", "source_year", "source_file"]], on="post_id", how="left")
    if raw["post_id"].nunique() != 5000:
        raise SystemExit("post_id 고유 5000이 아님")
    mismatch = int((raw["created_at"].str[:4] != raw["source_year"]).sum())
    model_read = load_model_read()
    overrides = load_overrides()
    image_checks = load_image_checks()

    evidence_rows = []
    summaries = []
    eid = 1
    for row in raw.to_dict("records"):
        text_n = norm(newlines(row["text"]))
        screened = screen_hits(text_n)
        evid = code_post(row) if screened or True else []
        # 비후보는 규칙을 돌리되, 선별 어휘가 없으면 근거를 만들지 않는다.
        if not screened:
            evid = []
        evid = apply_overrides(row["post_id"], evid, overrides)
        for e in evid:
            e = dict(e)
            e["evidence_id"] = f"E{eid:05d}"
            eid += 1
            e["post_id"] = row["post_id"]
            e["post_url"] = row["post_url"]
            e["account_id"] = row["account_id"]
            e["created_year_kst"] = row["created_at"][:4]
            e["image_checked"] = image_checks.get(row["post_id"], {}).get("image_checked", "아니오")
            e["image_observation"] = image_checks.get(row["post_id"], {}).get("image_observation", "")
            e["judgment_method"] = "model_context" if row["post_id"] in model_read else "rule_calibrated"
            e["post_text"] = row["text"]
            evidence_rows.append(e)
        summaries.append(post_summary(row, evid, screened, model_read, image_checks))

    posts = pd.DataFrame(summaries)
    evid = pd.DataFrame(evidence_rows)
    checks = validate(posts, evid)
    # 연도 불일치
    checks.append(f"created_at 연도와 source_year 불일치 {mismatch}")

    # connections: 근거 1행당 연결 1행. 언급만은 연결 수준을 그대로 둔다.
    if not evid.empty:
        conn = evid.copy()
        conn["connection_id"] = [f"C{i:05d}" for i in range(1, len(conn) + 1)]
        conn_cols = [
            "connection_id",
            "evidence_id",
            "post_id",
            "post_url",
            "account_id",
            "created_year_kst",
            "character",
            "character_link",
            "about_ip",
            "product_form",
            "function_from_name",
            "use_mode",
            "temporal",
            "behavior",
            "behavior_status",
            "acquisition",
            "like_reason",
            "barrier",
            "speaker",
            "link_level",
            "quote",
            "judgment_note",
            "judgment_method",
            "image_checked",
        ]
        conn = conn[conn_cols]
    else:
        conn = pd.DataFrame()

    evid_cols = [
        "evidence_id",
        "post_id",
        "post_url",
        "account_id",
        "created_year_kst",
        "character",
        "character_link",
        "about_ip",
        "product_form",
        "product_span",
        "variant",
        "function_from_name",
        "function_axis",
        "acquisition",
        "use_mode",
        "temporal",
        "behavior",
        "behavior_status",
        "like_reason",
        "barrier",
        "speaker",
        "link_level",
        "quote",
        "post_text",
        "image_checked",
        "image_observation",
        "judgment_method",
        "judgment_note",
    ]
    if not evid.empty:
        evid = evid[evid_cols]

    write_csv(posts, RUN / "post_consumption_analysis.csv")
    write_csv(evid, RUN / "consumption_evidence.csv")
    write_csv(conn, RUN / "consumption_connections.csv")

    review = posts[posts["review_flag"] == "예"][
        [
            "post_id",
            "post_url",
            "account_id",
            "created_year_kst",
            "primary_context",
            "review_reasons",
            "product_forms",
            "behaviors",
            "image_status",
            "text",
            "judgment_method",
        ]
    ]
    write_csv(review, RUN / "review_required.csv")

    denom = 5000
    # slices
    user = evid[evid["speaker"] == "작성자"] if not evid.empty else evid
    user_exp = user[user["temporal"] == "경험"] if not user.empty else user
    user_hope = user[user["temporal"].isin(["희망", "시도"])] if not user.empty else user
    explicit = user[(user["link_level"] == "명시적 선호·이유") & (~user["like_reason"].isin(["이유 미언급·판단 불가", ""]))] if not user.empty else user
    seller = evid[evid["speaker"].isin(["판매·홍보", "개인 거래"])] if not evid.empty else evid
    use_exp = user_exp[~user_exp["use_mode"].isin(["방식 불명확", ""])] if not user_exp.empty else user_exp

    form_speaker = agg_form_speaker(evid, denom) if not evid.empty else pd.DataFrame()
    write_csv(form_speaker, TABLES / "01_form_by_speaker.csv")

    mention_level = []
    for label, sl in [
        ("단순히 언급·소개된 상품(전체 근거)", evid),
        ("판매·홍보가 소개한 상품", evid[evid["speaker"] == "판매·홍보"] if not evid.empty else evid),
        ("개인 거래 문안의 상품", evid[evid["speaker"] == "개인 거래"] if not evid.empty else evid),
        ("작성자가 언급만 한 상품", user[user["behavior"] == "상품·콘텐츠 언급"] if not user.empty else user),
        ("작성자 실제 경험(획득·사용·방문)", user_exp),
        ("작성자 희망·시도", user_hope),
        ("작성자 명시 이유", explicit),
    ]:
        mention_level.append(
            {
                "slice": label,
                "unique_posts": 0 if sl.empty else sl["post_id"].nunique(),
                "evidence_rows": 0 if sl.empty else len(sl),
                "unique_accounts": 0 if sl.empty else sl["account_id"].nunique(),
                "denominator_posts": denom,
                "denominator_label": "전체 게시물 5000. 슬라이스끼리 합산하지 않음",
                "row_overlap": "슬라이스는 서로 겹칠 수 있음",
            }
        )
    write_csv(pd.DataFrame(mention_level), TABLES / "02_mention_experience_reason_levels.csv")

    ctx_rows = []
    for label, g in posts.groupby("primary_context"):
        ctx_rows.append(
            {
                "primary_context": label,
                "unique_posts": g["post_id"].nunique(),
                "denominator_posts": denom,
                "denominator_label": "전체 게시물. primary는 복수 맥락 중 우선 하나",
                "row_overlap": "primary는 게시물당 하나. 복수 맥락은 다음 표",
            }
        )
    write_csv(pd.DataFrame(ctx_rows).sort_values("unique_posts", ascending=False), TABLES / "03_primary_context.csv")

    # multi context exploded
    multi = []
    for _, r in posts.iterrows():
        for lab in str(r["post_context_labels"]).split("|"):
            if lab:
                multi.append({"post_id": r["post_id"], "account_id": r["account_id"], "context": lab})
    multi_df = pd.DataFrame(multi)
    ctx_multi_rows = []
    for lab, g in multi_df.groupby("context"):
        ctx_multi_rows.append(
            {
                "context": lab,
                "unique_posts": g["post_id"].nunique(),
                "denominator_posts": denom,
                "denominator_label": "전체 게시물",
                "row_overlap": "복수 맥락 허용. 합은 5000을 넘을 수 있음",
            }
        )
    write_csv(pd.DataFrame(ctx_multi_rows).sort_values("unique_posts", ascending=False), TABLES / "04_context_multilabel.csv")

    write_csv(
        cross_table(use_exp, "product_form", "use_mode", int(user_exp["post_id"].nunique()) if not user_exp.empty else 0, "작성자 경험 게시물"),
        TABLES / "05_form_x_use_user_experience.csv",
    )
    write_csv(
        cross_table(explicit, "product_form", "like_reason", int(explicit["post_id"].nunique()) if not explicit.empty else 0, "명시 이유가 있는 작성자 게시물"),
        TABLES / "06_form_x_reason_explicit.csv",
    )
    hope_use = user[user["temporal"].isin(["경험", "희망", "시도", "보류"]) & ~user["use_mode"].isin(["방식 불명확", ""])] if not user.empty else user
    write_csv(
        cross_table(hope_use, "use_mode", "temporal", int(hope_use["post_id"].nunique()) if not hope_use.empty else 0, "이용 방식이 적힌 작성자 게시물"),
        TABLES / "07_use_x_temporal.csv",
    )
    # character x form for user experience, drop pure work-title-only if multiple? keep as coded
    char_exp = user_exp.copy() if not user_exp.empty else user_exp
    if not char_exp.empty:
        char_exp = char_exp.assign(character_row=char_exp["character"].str.split("|")).explode("character_row")
        char_exp = char_exp[char_exp["about_ip"].astype(str).str.contains("치이카와")]
    write_csv(
        cross_table(char_exp, "character_row", "product_form", int(user_exp["post_id"].nunique()) if not user_exp.empty else 0, "작성자 경험 게시물. 캐릭터는 구절 안 이름"),
        TABLES / "08_character_x_form_user_experience.csv",
    )
    char_use = use_exp.copy() if not use_exp.empty else use_exp
    if not char_use.empty:
        char_use = char_use.assign(character_row=char_use["character"].str.split("|")).explode("character_row")
        char_use = char_use[char_use["about_ip"].astype(str).str.contains("치이카와")]
    write_csv(
        cross_table(char_use, "character_row", "use_mode", int(use_exp["post_id"].nunique()) if not use_exp.empty else 0, "작성자 경험 중 이용 방식이 적힌 게시물"),
        TABLES / "09_character_x_use_user_experience.csv",
    )

    # collection distinction
    coll = user[user["use_mode"].isin(["특정 캐릭터의 여러 상품·버전 모으기", "여러 캐릭터를 조합하거나 세트 완성하기"])] if not user.empty else user
    write_csv(
        cross_table(coll, "use_mode", "temporal", denom, "전체 게시물"),
        TABLES / "10_collection_single_vs_combo.csv",
    )

    # personal vs seller forms
    compare_forms = evid[evid["speaker"].isin(["작성자", "판매·홍보", "개인 거래"])] if not evid.empty else evid
    write_csv(
        cross_table(compare_forms, "product_form", "speaker", denom, "전체 게시물"),
        TABLES / "11_personal_vs_seller_forms.csv",
    )

    barriers = user[user["barrier"].fillna("").astype(str).str.len() > 0] if not user.empty else user
    write_csv(
        cross_table(barriers, "barrier", "behavior", denom, "전체 게시물"),
        TABLES / "12_barriers.csv",
    )

    # year composition — not growth
    year_rows = []
    for year, g in posts.groupby("created_year_kst"):
        ids = set(g["post_id"])
        evy = evid[evid["post_id"].isin(ids)] if not evid.empty else evid
        year_rows.append(
            {
                "created_year_kst": year,
                "posts": g["post_id"].nunique(),
                "posts_with_evidence": 0 if evy.empty else evy["post_id"].nunique(),
                "user_experience_posts": 0 if evy.empty else evy[(evy["speaker"] == "작성자") & (evy["temporal"] == "경험")]["post_id"].nunique(),
                "user_hope_posts": 0 if evy.empty else evy[(evy["speaker"] == "작성자") & (evy["temporal"].isin(["희망", "시도"]))]["post_id"].nunique(),
                "seller_posts": 0 if evy.empty else evy[evy["speaker"] == "판매·홍보"]["post_id"].nunique(),
                "denominator_label": "해당 연도 인기 게시물 표본. 시장 성장률·전환율이 아님",
                "note": "연도 파일은 인기순 상한 표본. 2026은 부분 기간일 수 있음",
            }
        )
    write_csv(pd.DataFrame(year_rows), TABLES / "13_year_sample_composition.csv")

    conc_rows = [
        concentration(evid, "전체 근거"),
        concentration(user_exp, "작성자 경험"),
        concentration(explicit, "작성자 명시 이유"),
        concentration(seller, "판매·홍보 또는 개인 거래"),
        concentration(user_hope, "작성자 희망·시도"),
    ]
    write_csv(pd.DataFrame(conc_rows), TABLES / "14_account_concentration.csv")

    # acquisition among user acquisition behaviors only
    acq = user[user["behavior"].isin(["구매·획득 경험", "구매·소장·사용 희망", "구매 고민", "구매 시도·실패·포기"])] if not user.empty else user
    write_csv(
        cross_table(acq, "acquisition", "behavior", denom, "전체 게시물"),
        TABLES / "15_user_acquisition_x_behavior.csv",
    )
    if not evid.empty:
        link_rows = []
        for (level, speaker), g in evid.groupby(["link_level", "speaker"]):
            link_rows.append(
                {
                    "link_level": level,
                    "speaker": speaker,
                    "unique_posts": g["post_id"].nunique(),
                    "evidence_rows": len(g),
                    "denominator_posts": denom,
                    "denominator_label": "전체 게시물",
                    "row_overlap": "한 게시물의 근거가 여러 연결 수준일 수 있음",
                }
            )
        write_csv(pd.DataFrame(link_rows), TABLES / "16_link_levels.csv")

    # behavior x status user
    write_csv(
        cross_table(user, "behavior", "behavior_status", denom, "전체 게시물"),
        TABLES / "17_user_behavior_status.csv",
    )

    charts = []
    if not form_speaker.empty:
        use_cross = cross_table(use_exp, "product_form", "use_mode", 0, "")
        use_temp = cross_table(hope_use, "use_mode", "temporal", 0, "")
        reason_counts = []
        if not explicit.empty:
            for reason, g in explicit.groupby("like_reason"):
                reason_counts.append({"like_reason": reason, "unique_posts": g["post_id"].nunique(), "evidence_rows": len(g)})
        charts = make_charts(form_speaker, use_cross, use_temp, pd.DataFrame(reason_counts))

    write_review_packs(posts, evid if not evid.empty else pd.DataFrame(columns=["post_id"]))

    progress = {
        "run_id": "20261103_143555",
        "updated_at": now_iso(),
        "posts": 5000,
        "screen_candidates": int((posts["screen_status"] == "후보").sum()),
        "evidence_rows": int(len(evid)),
        "evidence_posts": int(evid["post_id"].nunique()) if not evid.empty else 0,
        "model_read_posts": len(model_read),
        "overrides": len(overrides),
        "image_checks": len(image_checks),
        "source_year_mismatch": mismatch,
        "validation": checks,
        "charts": charts,
        "resume": "같은 스크립트를 다시 실행하면 결과를 덮어 쓴다. model_read_ids.txt, overrides.jsonl, image_checks.csv 가 있으면 반영한다.",
    }
    (WORKING / "progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
    (WORKING / "validation.txt").write_text("\n".join(checks), encoding="utf-8")
    print(json.dumps(progress, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
