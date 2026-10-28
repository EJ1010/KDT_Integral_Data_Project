# -*- coding: utf-8 -*-
"""치이카와 X 게시물 시험 분류(100건)를 재현한다.

판정은 키워드 일치로 만들지 않았다. 본문을 읽고 정한 결과를 JUDGMENTS에 고정했고,
이 스크립트는 표집 재현, 원본 대조, 라벨 정합성 검사, 표본 CSV 저장만 한다.
전체 5,000건 분류는 하지 않는다.

실행: py -3.11 classification_pilot.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(r"C:/DATA/KDT_Integral_Data_Project/02_csv/03_x")
PARQUET = BASE / "typed" / "x_chiikawa_2022_2026_typed.parquet"
OUT_DIR = BASE / "classification"
OUT_CSV = OUT_DIR / "classification_sample_100.csv"
CODEBOOK_VERSION = "v1"
RANDOM_STATE = 42
SAMPLE_N = 20

SERIES = {
    "chiikawa_series": "치이카와(작품·브랜드)",
    "monjakgwi": "먼작귀(작품 별칭)",
}
CHARACTERS = {
    "chiikawa": "치이카와",
    "hachiware": "하치와레",
    "usagi": "우사기",
    "momonga": "모몽가",
    "rakko": "랏코",
    "kurimanju": "쿠리만쥬",
    "shisa": "시사",
    "yoroi": "갑옷씨",
}
FORMS = {
    "plush": "인형",
    "figure": "피규어",
    "keyring": "키링",
    "badge": "뱃지",
    "stationery": "문구",
    "apparel": "의류",
    "wallet": "지갑",
    "pouch": "파우치",
    "carrier": "캐리어",
    "deskad": "장패드",
    "griptok": "그립톡",
    "light": "조명",
    "coin_bank": "저금통",
    "food": "식품",
    "digital": "디지털",
    "video": "영상",
    "movie": "영화",
    "book": "만화·도서",
    "game": "게임",
    "popup": "팝업·행사",
    "scene": "작품 장면",
    "frame": "액자",
    "prop": "소품",
    "goods_unknown": "굿즈(형태 미상)",
}
BEHAVIORS = {
    "mention": "단순 언급",
    "purchase_done": "구매 완료",
    "purchase_wish": "구매 희망",
    "sale_offer": "판매 제안",
    "sale_done": "판매 완료",
    "trade_offer": "교환 제안",
    "trade_done": "교환 완료",
    "transfer_seek": "양도·공구 구함",
    "giveaway_offer": "증정 제안",
    "receive_gift": "수증",
    "watch_done": "관람 완료",
    "watch_wish": "관람 희망",
    "watch_now": "관람 중",
    "visit_done": "방문 완료",
    "create": "창작",
    "info_share": "정보 공유",
    "release_notice": "출시 안내",
    "release_wish": "출시 희망",
    "ownership_use": "보유·사용",
    "content_share": "콘텐츠 공유",
    "acquire_unclear": "획득(결제 불명)",
}
AXIS_STATUS = {"분류 가능", "미언급", "확인 필요"}
LINK_STATUS = AXIS_STATUS | {"해당 없음"}
KEYWORD_CHARACTER = {
    "하치와레": "hachiware",
    "우사기": "usagi",
    "모몽가": "momonga",
    "랏코": "rakko",
    "쿠리만쥬": "kurimanju",
    "시사": "shisa",
    "갑옷씨": "yoroi",
}

SAMPLE_POST_IDS = [
    "1596496206183600128", "1583779525716242434", "1567855257866358786",
    "1600638848588881920", "1586191911119114241", "1522231146066890755",
    "1591239159867670530", "1530424380890619905", "1542512070528495616",
    "1539069362442674177", "1518570107873636354", "1569623879055986693",
    "1601538424833724417", "1581252438073700352", "1515180204561698821",
    "1499296679719178242", "1520239137181233152", "1487295017769369600",
    "1536899411712032769", "1519135935560286208", "1617786801024045058",
    "1609474961563062273", "1697491954664423771", "1652977802327789573",
    "1741313902682751185", "1719705763625812280", "1697528291425714223",
    "1697446544671445470", "1630800867292217344", "1699381014731362597",
    "1730522196802707497", "1628019449726119937", "1739472342953431177",
    "1675015822266470400", "1730580458243813626", "1642083072618401792",
    "1674362149869854720", "1719664760407683087", "1630934690311049222",
    "1620745122899193858", "1826282908929360145", "1821412377218179187",
    "1788488910718509486", "1775365140516614339", "1873979263927673155",
    "1829164611616280742", "1816703799068885180", "1833622322215063726",
    "1756249263741538463", "1851430789986295816", "1742190486801231925",
    "1856985425237479663", "1741631449873494123", "1779840919187161172",
    "1784343676539556334", "1758145737307857079", "1816779668730896603",
    "1873749584645943514", "1803012820210270483", "1796405012152934654",
    "1975019429898727709", "1880949388924911765", "1896794622896320958",
    "1988822661615743336", "1963846134658371639", "1943918511845519689",
    "1906904916167446937", "1960337681344577688", "1983316913402134642",
    "1996420992021967110", "1945775225129619795", "1969995405749624853",
    "1886718660615790829", "1914137515419979890", "1898179828416950596",
    "1966489926142189763", "1917929935278399751", "1967214796820123765",
    "1896981221747646714", "1923293310266835192", "2067964683722817632",
    "2067582796345073853", "2025867695300952560", "2068615535538118988",
    "2083180991770952143", "2052595228381769757", "2082065226879611024",
    "2083108013045604567", "2020814175899983990", "2085289423927963907",
    "2032279971079835989", "2092304242208047370", "2074005673143423083",
    "2039279305323380965", "2006667922475987086", "2037092524742107604",
    "2034895976465682629", "2006636951139659973", "2031209246151553253",
    "2088527187226091648",
]


def L(form, behavior, characters=None, surface=""):
    return {
        "form": form,
        "behavior": behavior,
        "characters": list(characters or []),
        "surface": surface,
    }


def J(
    post_id,
    series,
    series_status,
    characters,
    character_status,
    forms,
    form_status,
    behaviors,
    behavior_status,
    links,
    link_status,
    evidence,
    reason,
    review="",
):
    return {
        "post_id": post_id,
        "series": list(series),
        "series_status": series_status,
        "characters": list(characters),
        "character_status": character_status,
        "forms": list(forms),
        "form_status": form_status,
        "behaviors": list(behaviors),
        "behavior_status": behavior_status,
        "links": list(links),
        "link_status": link_status,
        "evidence": evidence,
        "reason": reason,
        "review": review,
    }


S = "chiikawa_series"
M = "monjakgwi"
OK = "분류 가능"
NO = "미언급"
ASK = "확인 필요"
NA = "해당 없음"

JUDGMENTS = [
    J("1596496206183600128", [S], OK, ["chiikawa", "hachiware"], OK,
      ["figure", "keyring", "goods_unknown"], OK, ["giveaway_offer", "sale_offer"], OK,
      [L("figure", "giveaway_offer", surface="인테리어 미니 피규어"),
       L("keyring", "giveaway_offer", surface="키체인"),
       L("goods_unknown", "sale_offer", surface="스토어 치이카와 굿즈")],
      ASK, "치이카와 하치와레 인테리어 미니 피규어와 키체인",
      "알티 선물 세트는 증정 제안이고, 스토어 판매 문장은 따로 판매 제안이다. 세트 안에서 피규어와 키체인이 어느 캐릭터인지는 문장이 나누지 않는다.",
      "캐릭터-형태 대응은 확인 필요. 판매 완료로 보지 않음."),
    J("1583779525716242434", [], ASK, [], ASK, [], NO, ["mention"], OK, [], NA,
      "요즘 치이카와 살짝 끌림",
      "호감만 있고 상품·행동이 없다. 치이카와가 작품인지 캐릭터인지 문맥이 없다.",
      "층위 확인 필요."),
    J("1567855257866358786", [S], OK, [], NO, ["badge", "goods_unknown"], OK,
      ["transfer_seek"], OK,
      [L("badge", "transfer_seek", surface="뱃지류"),
       L("goods_unknown", "transfer_seek", surface="사진 속 양도 대상")],
      OK, "치이카와 양도 공구 구핮니다",
      "작성자가 양도를 받는 쪽이다. 뱃지는 본문에 있고, 사진 속 본류는 종류가 없어 형태 미상이다. 구매 완료가 아니다.",
      "이미지는 열지 않음. 사진이 세분류를 보여 줄 수 있으나 본문 밖으로 추정하지 않음."),
    J("1600638848588881920", [M], OK, ["usagi"], OK, [], NO, ["mention"], OK, [], NA,
      "그럼 우사기도 토끼가 아닌거야?",
      "먼작귀는 작품 별칭이고 우사기만 개별 캐릭터다. 치이카와라는 단어는 없다.",
      ""),
    J("1586191911119114241", [S], OK, [], NO, ["figure"], OK, ["sale_offer"], OK,
      [L("figure", "sale_offer", surface="소프비 퍼펫 마스코트")],
      OK, "소프비 퍼펫 마스코트",
      "매장 입고 안내라 판매 제안이다. 개별 캐릭터 이름은 없다.",
      ""),
    J("1522231146066890755", [], NO, ["chiikawa", "hachiware"], OK, ["goods_unknown"], OK,
      ["purchase_done", "visit_done"], OK,
      [L("goods_unknown", "purchase_done", ["chiikawa", "hachiware"], "첫 구매 대상")],
      OK, "나가노 마켓에서 첫 구매를 하게 되었습니다",
      "첫 구매와 매장 방문은 작성자 행동이다. 치이카와와 하치와레를 같은 자리의 이름으로 읽어 캐릭터로 두었다. 형태 단어는 없다.",
      "방문은 형태와 연결하지 않음."),
    J("1591239159867670530", [M], OK,
      ["chiikawa", "hachiware", "usagi", "momonga", "kurimanju"], OK,
      [], NO, ["mention"], OK, [], NA, "먼작귀 친구들은 무슨 빼빼러 맛을 좋아할까",
      "캐릭터 취향 비유다. 치익카와·하칰와레·쿠리는 이 글의 철자와 대응으로 각 캐릭터에 귀속했다. 빼빼로를 상품 구매로 보지 않는다.",
      ""),
    J("1530424380890619905", [], NO, ["hachiware", "chiikawa"], OK, ["goods_unknown"], OK,
      ["visit_done", "acquire_unclear", "receive_gift"], OK,
      [L("goods_unknown", "acquire_unclear", ["hachiware", "chiikawa"], "달팽이 하치와레·개구리 치이카와"),
       L("goods_unknown", "receive_gift", surface="노벨티")],
      OK, "달팽이 하치와레랑 개구리 치이카와 데려오고 노벨티도 받았당",
      "키디랜드 방문은 확인된다. 데려왔다는 말만 있고 결제 단어가 없어 구매 완료 대신 획득(결제 불명)이다. 노벨티는 수증이고 캐릭터를 붙이지 않았다.",
      "달팽이·개구리 옷은 변형으로 보고 원 캐릭터에 귀속."),
    J("1542512070528495616", [S], OK, ["hachiware"], OK, [], NO, ["watch_now"], OK, [], NA,
      "오늘도 하치와레 보며 지구뿌시는중",
      "보는 중이라 관람 중이다. 매체 단어가 없어 형태는 미언급이다. #ちいかわ는 본문 해시태그라 작품 언급으로 보았다.",
      ""),
    J("1539069362442674177", [S, M], OK, [], NO, ["digital"], OK, ["info_share"], OK,
      [L("digital", "info_share", surface="카카오톡 이모티콘")],
      OK, "치이카와(먼작귀) 카카오톡 이모티콘이 출시되었습니다",
      "작품 별칭을 괄호로 같게 적었다. 이모티콘 출시 소식이라 정보 공유이고 판매 제안이 아니다.",
      ""),
    J("1518570107873636354", [S], OK, ["chiikawa", "hachiware", "usagi"], OK,
      ["figure"], OK, ["sale_offer"], OK,
      [L("figure", "sale_offer", ["chiikawa", "hachiware", "usagi"], "파자마 마스코트 피규어")],
      OK, "파자마 마스코트 피규어 치이카와 하치와레 우사기 예약이 시작",
      "예약 시작은 판매 제안이다. 라인업의 치이카와는 하치와레·우사기와 같은 선택지라 캐릭터다. 시크릿은 캐릭터가 아니다.",
      "상품명 앞의 치이카와는 작품 층위로도 읽힌다."),
    J("1569623879055986693", [], ASK, [], ASK, [], ASK, ["mention"], OK, [], ASK,
      "치이카와 유체이탈시켜야함",
      "아이폰 업데이트 이유만 있고, 유체이탈의 대상이 기능·이미지·캐릭터 중 무엇인지 본문이 특정하지 않는다.",
      "외부 기능 설명은 확인하지 않음."),
    J("1601538424833724417", [S], OK, [], NO, ["stationery"], OK, ["sale_offer"], OK,
      [L("stationery", "sale_offer", surface="쯔메쯔메 지우개")],
      OK, "쯔메쯔메 지우개",
      "입고 안내라 판매 제안이다. 지우개는 문구다. 개별 캐릭터는 없다.",
      ""),
    J("1581252438073700352", [S], OK, ["hachiware"], OK, [], NO, ["mention"], OK, [], NA,
      "바쿠(고)(하치)와레",
      "치이카와×히로아카는 작품 단위 상상이다. 하치와레는 이름 유희로 호출돼 캐릭터 언급으로 두되 상품은 아니다.",
      "히로아카는 타 작품."),
    J("1515180204561698821", [], ASK, [], ASK, [], ASK, ["mention"], OK, [], ASK,
      "치이카와 메론빵이어요",
      "짧은 캡션이다. 식품인지, 캐릭터인지, 장면인지 본문만으로 갈리지 않고 이미지는 보지 않았다.",
      "메론빵을 식품 구매로 확정하지 않음."),
    J("1499296679719178242", [S], OK, [], NO, ["plush"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", surface="부르부르즈 누이구루미 마스코트")],
      OK, "누이구루미 마스코트 5종",
      "예약 구매 안내라 판매 제안이다. 5종·최애만 있어 개별 캐릭터는 미언급이다.",
      ""),
    J("1520239137181233152", [], NO, ["chiikawa", "hachiware"], OK, [], NO, ["mention"], OK, [], NA,
      "치이카와 하치와레 생일까지",
      "생일 주어가 두 이름이므로 캐릭터 언급이다. 상품과 구매는 없다.",
      ""),
    J("1487295017769369600", [S], OK, [], NO, ["figure"], OK, ["sale_offer"], OK,
      [L("figure", "sale_offer", surface="그네 피규어")],
      OK, "치이카와 그네 피규어 입고되었어요",
      "입고와 구매 문의는 판매 제안이지 구매 완료가 아니다.",
      ""),
    J("1536899411712032769", [S], OK,
      ["chiikawa", "kurimanju", "usagi", "hachiware", "rakko", "momonga"], OK,
      ["plush"], OK, ["release_notice", "mention"], OK,
      [L("plush", "release_notice", ["hachiware", "rakko", "momonga"], "이번 대사 마스코트 3종"),
       L("plush", "mention", ["chiikawa", "kurimanju", "usagi"], "이미 나왔다고 한 대사 마스코트")],
      OK, "하치와레 - 해달랭커 - 모몬가 3종류",
      "이번 발매 3종만 출시 안내로 연결했다. 앞서 나왔다는 세 명은 같은 인형 종류의 기존 언급이다. 기대된다는 구매 희망이 아니다. 해달랭커는 랏코, 모몬가는 모몽가다.",
      "작성자는 판매자가 아님."),
    J("1519135935560286208", [S], OK, [], NO, ["goods_unknown"], OK, ["sale_offer"], OK,
      [L("goods_unknown", "sale_offer", surface="반점 시리즈")],
      OK, "치이카와 반점 시리즈",
      "입금 후 폼은 판매 접수라 판매 제안이다. 반점 시리즈의 물품 종류는 본문에 없다.",
      ""),
    J("1617786801024045058", [], NO, [], NO, [], NO, [], NO, [], NA,
      "치이카와 애들은 아니지만",
      "이름을 부정하는 문장이다. 캐릭터·작품·상품·행동을 부여하지 않는다.",
      "검색 키워드와 달리 본문은 미언급."),
    J("1609474961563062273", [S], OK, ["hachiware"], OK, ["plush"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", ["hachiware"], "BIG 누이구루미")],
      OK, "하치와레 BIG 누이구루미 입고",
      "머리글의 치이카와는 브랜드이고, 입고된 대상은 하치와레 인형이다. 판매 제안이다.",
      ""),
    J("1697491954664423771", [S], OK, [], NO, [], ASK, [], ASK, [], ASK,
      "치이카와 메지루시 재입고???",
      "재입고 질문이라 브랜드는 읽히지만, 메지루시의 물품 종류와 구매 의사는 이 문장에 없다.",
      "다른 게시물의 키링 용례를 이 글에 이식하지 않음."),
    J("1652977802327789573", [], ASK, ["usagi", "kurimanju"], OK, [], ASK, [], ASK, [], ASK,
      "쿠리만쥬 8",
      "상품 태그가 한 줄로 나열돼 우사기와 쿠리만쥬 이름만 확정했다. 치이카와는 작품명과 캐릭터명이 갈리고, 인형옷·양도 공구와 이름을 짝짓는 문장이 없다.",
      "키워드 나열을 판매 제안으로 확정하지 않음."),
    J("1741313902682751185", [], NO, ["kurimanju"], OK, [], NO, ["watch_now"], OK, [], NA,
      "이렇게 귀여운 쿠리만쥬 처음 봄",
      "처음 본다는 지각 동사가 있어 관람 중이다. 매체와 상품 종류는 없다.",
      ""),
    J("1719705763625812280", [M], OK, [], NO, ["carrier"], OK, ["purchase_wish"], OK,
      [L("carrier", "purchase_wish", surface="캐리어")],
      OK, "먼작귀 캐리어 말씀드리니까 사장님이 발주 넣어주심",
      "작성자가 원해서 말한 상황이라 구매 희망이다. 발주 주체는 사장님이고 결제·수령 문장이 없어 구매 완료가 아니다.",
      ""),
    J("1697528291425714223", [], ASK, [], ASK, [], NO, ["mention"], OK, [], NA,
      "치이카와..내 입꼬리 자꾸 올라가",
      "반응만 있다. 치이카와의 층위가 안 갈린다.",
      ""),
    J("1697446544671445470", [S], OK, [], NO, ["badge"], OK, ["purchase_wish"], OK,
      [L("badge", "purchase_wish", surface="노벨티 뱃지")],
      OK, "치이카와 노벨티 뱃지도 언젠가 구할 수 있겠지",
      "구하면 좋겠다는 희망이다. 가방에 달 뱃지로 적힌 농담곰·한큐는 치이카와 상품이 아니다.",
      ""),
    J("1630800867292217344", [], ASK, [], ASK, [], ASK, ["mention"], OK, [], ASK,
      "치이카와 단독샷",
      "사진 캡션이다. 작품 장면인지 굿즈인지, 누구인지 본문이 정하지 않고 이미지는 보지 않았다.",
      ""),
    J("1699381014731362597", [M], OK, ["rakko", "hachiware"], OK, ["griptok"], OK,
      ["purchase_done", "purchase_wish", "giveaway_offer"], OK,
      [L("griptok", "purchase_done", ["rakko"], "이미 나온 그립톡"),
       L("griptok", "purchase_wish", ["hachiware"], "또 뽑아 보려는 그립톡"),
       L("griptok", "giveaway_offer", surface="알티 경품")],
      OK, "저는 랏코 나왔는데 하치와레 너무 귀여운것 같아서",
      "랏코가 이미 나온 것과 하치와레를 더 뽑으려는 것을 나눴다. 알티 경품에는 캐릭터를 지정하지 않았다.",
      "뽑기는 편의점 그립톡 문맥의 유료 획득으로 보아 랏코만 구매 완료."),
    J("1730522196802707497", [M], OK, [], ASK, [], ASK, ["mention"], OK, [], ASK,
      "먼작귀 인증샷이",
      "먼작귀가 맞다고 했지만 친구의 이름이 없다. 양키 코스프레의 대상이 굿즈인지 장면인지도 사진 없이 정하지 않는다.",
      ""),
    J("1628019449726119937", [], NO, ["kurimanju"], OK, [], NO, ["mention"], OK, [], NA,
      "산왕의 쿠리만쥬",
      "승려 비유의 결론으로 캐릭터를 호출했다. 상품이 아니다.",
      ""),
    J("1739472342953431177", [], NO, ["kurimanju"], OK, [], ASK, ["mention"], OK, [], ASK,
      "쏘주와 함께찍은 쿠리만쥬",
      "함께 찍었다는 말만 있다. 인형인지 다른 대상인지 이미지가 필요하고, 보지 않았다.",
      ""),
    J("1675015822266470400", [S], OK, [], ASK, [], ASK, [], ASK, [], ASK,
      "치이카와 만두 중화반점",
      "가격처럼 보이는 목록 조각이다. 판매 문장이 잘려 있고, 만두·데스크탑의 물품 종류가 없다. 풍뎅이 제거를 캐릭터로 확정하지 않는다.",
      "산리오·몽당이는 타 IP."),
    J("1730580458243813626", [S], OK, ["yoroi"], OK, ["goods_unknown"], OK, ["purchase_done"], OK,
      [L("goods_unknown", "purchase_done", ["yoroi"], "가챠 결과")],
      OK, "돈 1만원 써서 갑옷씨 2개 나와서",
      "돈을 쓰고 결과가 나온 1인칭이라 구매 완료다. 갑옷씨를 랏코로 바꾸지 않았다. 나온 물건의 종류 단어는 없다.",
      ""),
    J("1642083072618401792", [S], OK, ["rakko", "shisa", "kurimanju", "usagi", "momonga"], OK,
      ["plush"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", ["rakko", "shisa", "kurimanju", "usagi", "momonga"], "마스코트 공구")],
      OK, "천사 랏코, 시사, 악마 쿠리만쥬, 우사기, 모몽가",
      "1차금이 있는 공구 모집이라 판매 제안이다. 다른 마스코트와 함께라는 말로 인형에 연결했다. 제목의 치이카와는 라인이고 목록에 그 캐릭터는 없다.",
      "천사·악마는 변형. 원 캐릭터에 귀속."),
    J("1674362149869854720", [S], OK, [], NO, ["plush"], OK, ["sale_offer", "giveaway_offer"], OK,
      [L("plush", "sale_offer", surface="누이구루미 2탄 예약"),
       L("plush", "giveaway_offer", surface="알티 추첨 누이구루미")],
      OK, "치이카와 누이구루미 2탄 캡슐토이",
      "예약 오픈은 판매 제안이고, 알티 추첨은 증정 제안이다. 둘 다 같은 누이구루미를 가리킨다.",
      ""),
    J("1719664760407683087", [M], OK, [], NO, ["goods_unknown"], OK, ["mention"], OK,
      [L("goods_unknown", "mention", surface="랜덤깡")],
      OK, "먼작귀 랜덤깡 스페 ㄱㄱ",
      "랜덤 상품을 여는 이야기와 스페이스 권유다. 작성자의 구매 완료 문장은 없다.",
      ""),
    J("1630934690311049222", [], NO, ["hachiware"], OK, ["plush"], OK, ["purchase_wish"], OK,
      [L("plush", "purchase_wish", ["hachiware"], "인형")],
      OK, "하치와레 인형 사야겠다",
      "사야겠다는 앞으로의 의도라 구매 희망이다.",
      ""),
    J("1620745122899193858", [S], OK, [], NO, ["frame"], OK, ["mention"], OK,
      [L("frame", "mention", surface="액자")],
      OK, "방에 치이카와 액자 거는거 잊지마세요",
      "남에게 걸라고 한 말이지 작성자의 구매가 아니다. 상품명 앞의 치이카와는 캐릭터로 확정하지 않는다.",
      ""),
    J("1826282908929360145", [], NO, ["hachiware", "chiikawa"], OK, ["stationery"], OK, ["create"], OK,
      [L("stationery", "create", ["hachiware"], "기생버섯 하치와레 도장")],
      OK, "기생버섯 하치와레 도장",
      "도장을 파고 그린 창작이다. 버섯치이는 참고한 치이카와 변형이라 캐릭터만 언급하고 도장 연결에는 넣지 않았다.",
      "팬 변형은 원 캐릭터에 귀속."),
    J("1821412377218179187", [S, M], OK, [], NO, ["badge"], OK, ["sale_offer"], OK,
      [L("badge", "sale_offer", surface="자수 캔배지 비스켓")],
      OK, "자수 캔배지 비스켓 입고",
      "입고 안내라 판매 제안이다. 캔배지는 뱃지다. 해시태그 먼작귀는 작품 별칭이다.",
      ""),
    J("1788488910718509486", [S], OK, ["chiikawa", "hachiware", "usagi"], OK, ["plush"], OK,
      ["sale_offer"], OK,
      [L("plush", "sale_offer", ["chiikawa", "hachiware", "usagi"], "파자마 옷 입히기 마스코트")],
      OK, "파자마 옷 입히기 마스코트",
      "입고 안내라 판매 제안이다. 옷은 마스코트에 포함된 설명이라 의류를 따로 두지 않았다. 시크릿은 캐릭터가 아니다.",
      ""),
    J("1775365140516614339", [], NO, ["usagi", "chiikawa", "hachiware"], OK, ["goods_unknown"], OK,
      ["purchase_wish", "purchase_done"], OK,
      [L("goods_unknown", "purchase_wish", ["usagi", "chiikawa"], "뽑고 싶었던 대상"),
       L("goods_unknown", "purchase_done", ["hachiware"], "실제로 나온 대상")],
      OK, "우사기(핑구)나 우무(치이카와) 뽑고싶어서 돌렸는데 또 하치와레 나왔어",
      "돌린 결과는 하치와레뿐이라 구매 완료는 하치와레만이다. 우무는 이 글이 치이카와라고 풀어 적었다. 핑구는 타 IP 별칭이라 캐릭터에 넣지 않았다.",
      "뽑기 물품의 종류 단어는 없음."),
    J("1873979263927673155", [], NO, ["hachiware"], OK, ["wallet"], OK, ["trade_done"], OK,
      [L("wallet", "trade_done", ["hachiware"], "지갑 세트")],
      OK, "하치와레 지갑 세트",
      "교환하려고 뛴 보람이라고 결과물을 제시해 교환 완료로 읽었다. 교환하자는 제안 글은 아니다.",
      "사진은 보지 않음. 문장의 교환 결과 해석을 승인 항목으로 남김."),
    J("1829164611616280742", [M], OK, [], NO, ["figure"], OK, ["mention"], OK,
      [L("figure", "mention", surface="줄자 피규어")],
      OK, "먼작귀 줄자 피규어 귀여운데",
      "귀엽다는 반응이라 단순 언급이다. 개별 캐릭터 이름은 없다.",
      ""),
    J("1816703799068885180", [S], OK, ["hachiware"], OK, ["pouch"], OK, ["mention"], OK,
      [L("pouch", "mention", ["hachiware"], "랜덤파우치")],
      OK, "랜덤파우치 어케 하치와레 나온거임",
      "파우치 결과가 하치와레라는 반응이다. 1인칭 결제 문장이 없어 구매 완료로 올리지 않았다. 구달 콜라보의 화장품 종류는 본문이 말하지 않는다.",
      ""),
    J("1833622322215063726", [], ASK, [], ASK, [], ASK, ["mention"], OK, [], ASK,
      "처연카와이",
      "치이카와와 분위기 단어만 있는 캡션이다. 층위와 형태는 이미지가 필요하고, 보지 않았다.",
      ""),
    J("1756249263741538463", [], ASK, [], ASK, [], ASK, [], ASK, [], ASK,
      "치이카와 벌써 랏코 앞에서만 몇번이나",
      "작품 속 반복인지, 굿즈 앞의 실물 행동인지 갈린다. 이미지는 보지 않았다.",
      "어느 쪽으로도 구매·관람을 확정하지 않음."),
    J("1851430789986295816", [S], OK, [], NO, ["plush", "goods_unknown"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", surface="인형·마스코트·큰애"),
       L("goods_unknown", "sale_offer", surface="다른 굿즈")],
      OK, "치이카와 인형 이삽십개 정도 팔 예정",
      "팔 예정·판매할게이므로 판매 제안이다. 판매 완료가 아니다. 개별 캐릭터 이름은 없다.",
      ""),
    J("1742190486801231925", [S, M], OK, [], NO, ["stationery"], OK, ["sale_offer"], OK,
      [L("stationery", "sale_offer", surface="다이어리")],
      OK, "치이카와 다이어리 2024",
      "쿠팡 파트너스 상품 링크라 판매 제안이다. 작성자가 샀다는 뜻이 아니고 판매 완료도 아니다.",
      ""),
    J("1856985425237479663", [S], OK, [], NO, ["plush", "prop"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", surface="クリスマスBIGぬいぐるみ"),
       L("prop", "sale_offer", surface="超BIGさすまた")],
      OK, "クリスマスBIGぬいぐるみ",
      "매장 등장이 내일부터라는 공식 판매 글이다. 인형과 사수마타 소품을 각각 연결했다. 어느 캐릭터의 인형인지는 특정되지 않는다.",
      ""),
    J("1741631449873494123", [], ASK, [], ASK, [], NO, ["mention"], OK, [], NA,
      "치이카와 때메 핑크템이 좀 늘어감",
      "핑크템은 치이카와 상품이라고 특정되지 않아 형태는 미언급이다. 호명의 층위는 안 갈린다.",
      ""),
    J("1779840919187161172", [], NO, ["chiikawa", "rakko"], OK, [], NO, ["mention"], OK, [], NA,
      "치이카와 랏코 닮앗다는데",
      "사람을 두 캐릭터에 비유한 언급이다. 상품이 아니다.",
      ""),
    J("1784343676539556334", [S, M], OK, [], NO, ["stationery"], OK, ["sale_offer"], OK,
      [L("stationery", "sale_offer", surface="sticker sheets")],
      OK, "Chiikawa sticker sheets available",
      "판매 가능 안내라 판매 제안이다. 스티커는 문구다.",
      ""),
    J("1758145737307857079", [M], OK, [], NO, ["book"], OK, ["content_share"], OK,
      [L("book", "content_share", surface="5권")],
      OK, "먼작귀 5권 시리즈 업로드",
      "권수 업로드 안내라 만화·도서를 콘텐츠 공유로 연결했다. 읽었다거나 샀다는 문장은 없다.",
      "업로드의 주체와 권리는 판단하지 않음."),
    J("1816779668730896603", [], NO, ["rakko"], OK, [], NO, ["mention"], OK, [], NA,
      "이 랏코 머햐",
      "캐릭터 반응이다. 형태 단어가 없고 이미지로 형태를 추정하지 않는다.",
      ""),
    J("1873749584645943514", [S], OK, ["hachiware"], OK, ["goods_unknown"], OK, ["sale_offer"], OK,
      [L("goods_unknown", "sale_offer", ["hachiware"], "패러랠하치 재고")],
      OK, "패러랠하치 재고있습니당",
      "재고와 구매 권유라 판매 제안이다. 패러랠하치는 하치와레 변형이다. 물품 종류는 없다.",
      ""),
    J("1803012820210270483", [M], OK, ["hachiware"], OK, ["video"], OK, ["watch_done"], OK,
      [L("video", "watch_done", surface="먼작귀 시청")],
      OK, "어제 먼작귀 보고 빠졋대",
      "어제 봤다는 완료 문장이 있어 관람 완료다. 하치와레를 닮았다는 말은 사람 비유라 영상 연결에 넣지 않았다.",
      ""),
    J("1796405012152934654", [], NO, ["hachiware"], OK, [], NO, ["mention"], OK, [], NA,
      "멍청한 하치와레 같은데",
      "고양이를 캐릭터에 비유했다. 그 고양이를 치이카와 상품으로 보지 않는다.",
      ""),
    J("1975019429898727709", [M], OK, [], NO, ["video"], OK, ["watch_wish"], OK,
      [L("video", "watch_wish", surface="짧은 영상")],
      OK, "추석에 먼작귀 몰아봅시다",
      "같이 보자고 권하는 말이라 관람 희망이다. 이미 봤다는 문장은 없다.",
      ""),
    J("1880949388924911765", [], NO, ["hachiware"], OK, [], NO, ["mention"], OK, [], NA,
      "하치와레 에디션이냐",
      "후드 색배치를 캐릭터에 비유한 질문이다. 그 후드를 치이카와 의류 상품으로 귀속하지 않는다.",
      ""),
    J("1896794622896320958", [], NO, ["hachiware"], OK, [], NO, ["watch_now"], OK, [], NA,
      "귀여운 하치와레 보면서 집가기",
      "보면서 이동한다는 현재 관람이다. 매체 단어가 없어 형태는 미언급이다.",
      ""),
    J("1988822661615743336", [], NO, ["rakko"], OK, [], NO, ["mention"], OK, [], NA,
      "랏코 넘 기엽다",
      "귀엽다는 반응만 있다. 형태를 이미지로 채우지 않는다.",
      ""),
    J("1963846134658371639", [], NO, ["chiikawa"], OK, ["goods_unknown"], OK,
      ["visit_done", "purchase_wish", "purchase_done"], OK,
      [L("goods_unknown", "purchase_wish", ["chiikawa"], "뽑고 싶었던 치이카와"),
       L("goods_unknown", "purchase_done", ["chiikawa"], "농담곰 거죽을 입은 채 뽑힌 치이카와")],
      OK, "실제로 뽑은 것 : 농담곰 거죽 입은 치이카와",
      "나가노마켓 방문은 작성자다. 원했던 치이카와와 실제로 뽑힌 치이카와를 행동만 나눴다. 농담곰은 다른 작품이라 캐릭터에 넣지 않았다.",
      "방문은 형태와 연결하지 않음. 뽑기 물품 종류는 없음."),
    J("1943918511845519689", [M], OK, ["usagi"], OK, ["figure"], OK, ["sale_offer"], OK,
      [L("figure", "sale_offer", ["usagi"], "누들스토퍼")],
      OK, "우사기 누들스토퍼 입고되었습니다",
      "입고 안내라 판매 제안이다. 누들스토퍼는 피규어로 분류했다.",
      ""),
    J("1906904916167446937", [], NO, ["rakko"], OK, [], ASK, [], ASK, [], ASK,
      "랏코 어디에 놓고 온거야?",
      "두고 온 실물인지 장면인지 갈린다. 이미지는 보지 않았다.",
      ""),
    J("1960337681344577688", [], NO, ["momonga", "chiikawa"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["momonga", "chiikawa"], "먹으려다 발차기하는 장면")],
      OK, "모몽가가 치이카와 먹으려고 해서 불꽃 발차기",
      "줄거리를 말한 반응이라 작품 장면과 단순 언급이다. 봤다는 1인칭은 없어 관람 완료가 아니다.",
      ""),
    J("1983316913402134642", [], NO, ["hachiware", "chiikawa"], OK, [], NO, ["mention"], OK, [], NA,
      "아이큐 치이카와",
      "두 캐릭터의 인상 비교다. 상품이 아니다.",
      ""),
    J("1996420992021967110", [S, M], OK, [], NO, ["goods_unknown"], OK, ["release_notice"], OK,
      [L("goods_unknown", "release_notice", surface="5주년 한정 굿즈")],
      OK, "한정 굿즈 & 캠페인을 준비했습니다",
      "공식 계정의 예고라 출시 안내이다. 지금 주문받지는 않고, 품목과 캐릭터가 없다.",
      ""),
    J("1945775225129619795", [S, M], OK, [], NO, ["goods_unknown"], OK, ["sale_offer"], OK,
      [L("goods_unknown", "sale_offer", surface="파치파치 데코 네임")],
      OK, "파치파치 데코 네임",
      "입고 안내라 판매 제안이다. 데코 네임의 물품 대분류는 본문이 정하지 않아 형태 미상으로 두었다.",
      ""),
    J("1969995405749624853", [S], OK, ["usagi"], OK, ["light"], OK, ["sale_offer"], OK,
      [L("light", "sale_offer", ["usagi"], "USBスタンドライト")],
      OK, "USBスタンドライト",
      "ちいかわ는 브랜드, うさぎ는 우사기다. 매장 등장이라 판매 제안이다.",
      ""),
    J("1886718660615790829", [], NO, ["chiikawa"], OK, [], NO, ["mention"], OK, [], NA,
      "식고문 당하는 치이카와 짤 있으신분",
      "짤을 구하는 말이지 구매나 관람 완료가 아니다. 폼폼푸린은 다른 작품이다.",
      "짤 요청을 별도 행동으로 만들지 않음."),
    J("1914137515419979890", [M], OK, ["hachiware"], OK, ["apparel"], OK, ["release_wish"], OK,
      [L("apparel", "release_wish", ["hachiware"], "유니폼 콜라보")],
      OK, "유니폼에 하치와레 붙어있을 생각",
      "구단이 콜라보를 하라는 희망이지 작성자의 구매 희망이 아니다. 아직 없는 유니폼이다.",
      "미출시 형태를 집계에 포함할지는 승인 항목."),
    J("1898179828416950596", [], NO, ["chiikawa", "hachiware", "usagi", "rakko"], OK,
      ["keyring", "stationery"], OK, ["ownership_use", "trade_done"], OK,
      [L("keyring", "ownership_use", ["rakko"], "랏코 키링"),
       L("stationery", "ownership_use", ["rakko"], "랏코 스티"),
       L("stationery", "trade_done", ["chiikawa"], "치이치이딱정곰돌 스티")],
      ASK, "랏코 키링 1",
      "수량 목록이라 보유·사용이다. 결제 문장이 없어 구매 완료가 아니다. 내가바꿈은 그 스티커만 교환 완료다. 치이·하치·우사는 이 목록의 대응으로 풀었다.",
      "도쟈스·카프스 줄의 형태는 미해독이라 연결하지 않음."),
    J("1966489926142189763", [M], OK, [], NO, ["pouch"], OK, ["purchase_done", "ownership_use"], OK,
      [L("pouch", "purchase_done", surface="홀로그램 파우치"),
       L("pouch", "ownership_use", surface="홀로그램 파우치")],
      OK, "주문했었어용 물티슈까지 야무지게 잘 쓰고있슴니당",
      "주문과 후회없는 소비가 있어 구매 완료이고, 잘 쓰고 있다는 보유·사용도 있다. 세일했다는 다른 사람의 문장을 작성자의 판매 제안으로 두지 않았다.",
      ""),
    J("1917929935278399751", [S], OK, [], NO, [], NO, ["mention"], OK, [], NA,
      "오빤쮸우사기",
      "치이카와는 포켓몬·산리오와 같이 적힌 작품명이다. 오빤쮸우사기는 우사기가 아니라 다른 캐릭터라 제외했다.",
      "검색 키워드의 우사기를 복사하지 않음."),
    J("1967214796820123765", [], NO, ["rakko"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["rakko"], "굶는다는 이야기")],
      ASK, "랏코 어떡해 굶어죽는다고",
      "랏코의 이야기 반응이라 장면과 단순 언급이다. 오다는 오데로 단정하지 않았다.",
      "오다의 지시 대상이 인물인지 확인 필요. 오다이바·다녀오다와 구분."),
    J("1896981221747646714", [M], OK, ["rakko"], OK, ["deskad"], OK,
      ["ownership_use", "release_wish"], OK,
      [L("deskad", "ownership_use", ["rakko"], "지금 쓰는 장패드"),
       L("deskad", "release_wish", surface="핑크 추가 희망")],
      OK, "랏코 있는 장패드인데",
      "잘 쓴다는 보유·사용이다. 샀다는 문장이 없어 구매 완료가 아니다. 핑크 추가 희망에는 랏코 도안이라고 단정하지 않았다.",
      ""),
    J("1923293310266835192", [S], OK, [], NO, ["food"], OK, ["purchase_done"], OK,
      [L("food", "purchase_done", surface="해피밀")],
      OK, "치이카와 해피밀을 주문햇서요",
      "주문했다는 완료된 구매 행동이다. 수령 문장은 없고, 상품명의 치이카와를 캐릭터로 확정하지 않는다.",
      "주문을 구매 완료로 둔 규칙은 승인 항목."),
    J("2067964683722817632", [], ASK, [], ASK, [], ASK, [], ASK, [], ASK,
      "건호🤍치이카와",
      "이름 나열과 사진뿐이라 층위·형태·행동을 정하지 않았다. 이미지는 보지 않았다.",
      ""),
    J("2067582796345073853", [], NO, ["momonga"], OK, ["goods_unknown"], OK, ["receive_gift"], OK,
      [L("goods_unknown", "receive_gift", ["momonga"], "트친이 사준 모몽가")],
      OK, "트친이 사준 모몽가",
      "산 사람은 트친이고 작성자는 받은 쪽이라 수증이다. 모몽가의 물품 종류는 없다. 같은 글의 아크릴은 치이카와라고 특정되지 않아 제외했다.",
      ""),
    J("2025867695300952560", [], NO, ["hachiware"], OK, ["plush"], OK, ["purchase_wish"], OK,
      [L("plush", "purchase_wish", ["hachiware"], "인형")],
      OK, "살찐 하치와레 인형 갖고싶다",
      "갖고 싶다는 구매 희망이다.",
      ""),
    J("2068615535538118988", [], NO, ["rakko"], OK, [], ASK, ["mention"], OK, [], ASK,
      "랏코 입에 찾아서 모카번 먹여주는거",
      "먹여 주는 장면을 말한 반응이다. 인형놀이는 먹여 준 사람의 어릴 적 비유라 랏코의 형태로 확정하지 않았다.",
      "이미지는 보지 않음."),
    J("2083180991770952143", [S], OK, [], NO, ["movie"], OK, ["watch_wish"], OK,
      [L("movie", "watch_wish", surface="한국 개봉")],
      OK, "치이카와 한국 언제 개봉해",
      "개봉 전 보고 싶다는 관람 희망이다. 관람 완료가 아니고 개별 캐릭터도 없다.",
      ""),
    J("2052595228381769757", [S], OK, ["hachiware"], OK, ["popup"], OK, ["visit_done"], OK,
      [L("popup", "visit_done", ["hachiware"], "치이카와 팝업")],
      OK, "치이카와 팝업에 왔어요",
      "팝업에 왔다는 방문 완료다. 하치와레를 입에 넣는 말을 식품 구매로 바꾸지 않았다.",
      ""),
    J("2082065226879611024", [M], OK, [], NO, ["game"], OK, ["mention"], OK,
      [L("game", "mention", surface="좀비고 콜라보")],
      OK, "좀비고 먼작귀 콜라보",
      "콜라보를 제시했을 뿐 플레이·구매 완료는 없다. 이미지 속 캐릭터는 추정하지 않는다.",
      ""),
    J("2083108013045604567", [M], OK, [], NO, ["game"], OK, ["mention"], OK,
      [L("game", "mention", surface="좀비고 콜라보")],
      OK, "좀비고 먼작귀",
      "같은 콜라보 제시이고 현우빈은 사람이다. 캐릭터와 구매를 만들지 않는다.",
      ""),
    J("2020814175899983990", [], NO, ["rakko"], OK, [], NO, ["purchase_wish"], OK, [], NA,
      "랏코 꼭 산다",
      "사겠다는 다짐이라 구매 희망이다. 산 것이 아니고 물품 종류도 없다.",
      ""),
    J("2085289423927963907", [], NO, ["chiikawa"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["chiikawa"], "발톱을 자르고 탭댄스")],
      OK, "치이카와 자를 발톱이 있는 것도",
      "발톱과 탭댄스는 캐릭터의 장면이다. 봤다는 1인칭이 없어 관람 완료가 아니다.",
      ""),
    J("2032279971079835989", [S], OK, ["momonga"], OK, ["popup", "goods_unknown"], OK,
      ["mention", "receive_gift"], OK,
      [L("popup", "mention", surface="치이카와 팝업"),
       L("goods_unknown", "receive_gift", ["momonga"], "짝꿍이 데려온 모몽가")],
      OK, "치이카와 팝업까지 가서 모몽가 데려옴",
      "팝업에 가고 산 사람은 짝꿍이다. 작성자의 방문·구매 완료로 올리지 않고 수증만 완료로 두었다. 모몽가의 종류는 없다.",
      ""),
    J("2092304242208047370", [M], OK, ["momonga"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["momonga"], "사회에 녹아들지 않는 장면")],
      OK, "이 장면에서 모몽가",
      "장면 해석이다. 먼작귀 사회는 작품 별칭이다. 관람 완료 문장은 없다.",
      ""),
    J("2074005673143423083", [], NO, ["rakko"], OK, [], NO, ["watch_now"], OK, [], NA,
      "랏코 요런 순딩부숭 모먼트 볼 때마다",
      "볼 때마다라고 해 관람 중이다. 매체 단어는 없어 형태는 미언급이다.",
      ""),
    J("2039279305323380965", [], NO, ["momonga"], OK, [], ASK, ["mention"], OK, [], ASK,
      "손이랑 주머니에 모몽가 넣고",
      "넣고 다니면 좋겠다는 부러움이다. 인형이라고 단정하지 않았다. 구매 문장도 없다.",
      ""),
    J("2006667922475987086", [M], OK, ["chiikawa"], OK, ["video"], OK,
      ["content_share", "mention"], OK,
      [L("video", "content_share", surface="177화 유튜브"),
       L("video", "mention", ["chiikawa"], "제목 치이카와의 꿈")],
      OK, "치이카와의 꿈6",
      "회차 링크를 올린 콘텐츠 공유다. 제목의 치이카와의 꿈은 캐릭터 이름으로 읽었다. 장내환경은 반응일 뿐 봤다는 문장이 아니다.",
      ""),
    J("2037092524742107604", [S, M], OK, [], NO, ["plush"], OK, ["sale_offer"], OK,
      [L("plush", "sale_offer", surface="캡슐 클립 누이구루미 2탄")],
      OK, "캡슐 클립 누이구루미 2탄",
      "입고 안내라 판매 제안이다. 클립 누이는 인형 하나로 두었고 키링을 겹치지 않았다.",
      ""),
    J("2034895976465682629", [], NO, ["rakko"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["rakko"], "고기 굽는 장면")],
      OK, "랏코 고기 꿉는거",
      "고기 굽는 장면 반응이다. 관람 완료나 식품 구매가 아니다.",
      ""),
    J("2006636951139659973", [S], OK, [], NO, ["coin_bank"], OK, ["purchase_done"], OK,
      [L("coin_bank", "purchase_done", surface="저금통")],
      OK, "5천원에 치이카와 저금통 뽑았어",
      "금액을 내고 뽑았다는 1인칭이라 구매 완료다. 상품명 앞의 치이카와는 캐릭터로 확정하지 않는다.",
      ""),
    J("2031209246151553253", [], NO, ["hachiware"], OK, [], ASK, ["mention"], OK, [], ASK,
      "하치와레 목소리 엄청 굵어졌네",
      "목소리 반응은 확정이다. 영상 음성인지 소리가 나는 굿즈인지는 본문이 정하지 않는다.",
      ""),
    J("2088527187226091648", [], NO, ["hachiware", "chiikawa"], OK, ["scene"], OK, ["mention"], OK,
      [L("scene", "mention", ["hachiware", "chiikawa"], "놀라는 장면")],
      OK, "하치와레 순수광기에 치이 놀란 거",
      "치이는 이 문장에서 하치와레와 같이 나오는 치이카와다. 장면 반응이고 관람 완료 문장은 없다.",
      "토랄·별랄은 이 문장의 치이카와 캐릭터로 넣지 않음."),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_post_id(links: pd.Series) -> pd.Series:
    found = links.astype("string").str.extract(r"/status/(\d+)", expand=False)
    if found.isna().any():
        raise SystemExit("게시물 링크에서 post_id를 추출하지 못한 행이 있다.")
    return found.astype("string")


def load_source():
    before = sha256_file(PARQUET)
    frame = pd.read_parquet(PARQUET)
    expected = {
        "게시물 링크": "string",
        "계정 ID": "string",
        "댓글 개수": "Int64",
        "리포스트 개수": "Int64",
        "본문": "string",
        "계정 이름": "string",
        "작성 시각": "datetime64[ns, Asia/Seoul]",
        "조회수": "Int64",
        "좋아요 수": "Int64",
        "키워드": "string",
        "source_file": "string",
        "source_row": "Int64",
        "source_year": "Int64",
    }
    if list(frame.columns) != list(expected):
        raise SystemExit(f"컬럼 불일치: {list(frame.columns)}")
    for column, dtype in expected.items():
        actual = str(frame[column].dtype)
        if actual != dtype:
            raise SystemExit(f"자료형 불일치 {column}: {actual} != {dtype}")
    if len(frame) != 5000:
        raise SystemExit(f"행 수 불일치: {len(frame)}")
    frame = frame.copy()
    frame["post_id"] = extract_post_id(frame["게시물 링크"])
    if frame["post_id"].nunique() != 5000 or frame["post_id"].duplicated().any():
        raise SystemExit("post_id가 유일하지 않다.")
    year = frame["작성 시각"].dt.year
    if int((year == frame["source_year"]).sum()) != 5000:
        raise SystemExit("작성 시각의 한국시간 연도와 source_year가 어긋난다.")
    if int(frame["조회수"].isna().sum()) != 946:
        raise SystemExit("조회수 결측이 946건이 아니다.")
    if int(((frame["source_year"] == 2022) & frame["조회수"].isna()).sum()) != 946:
        raise SystemExit("조회수 결측이 모두 2022년은 아니다.")
    if int((frame["계정 이름"] == "null").sum()) != 2:
        raise SystemExit("계정 이름 문자열 null이 2건이 아니다.")
    after = sha256_file(PARQUET)
    if before != after:
        raise SystemExit("읽기 전후 Parquet 지문이 달라졌다.")
    return frame, before


def draw_sample(frame: pd.DataFrame) -> pd.DataFrame:
    year = frame["작성 시각"].dt.year
    parts = []
    for value in (2022, 2023, 2024, 2025, 2026):
        group = frame.loc[year == value]
        if len(group) != 1000:
            raise SystemExit(f"{value}년 행 수가 1000이 아니다: {len(group)}")
        parts.append(group.sample(n=SAMPLE_N, random_state=RANDOM_STATE))
    sample = pd.concat(parts, axis=0)
    found = sample["post_id"].astype(str).tolist()
    if found != SAMPLE_POST_IDS:
        raise SystemExit("random_state=42 표집 결과가 고정된 post_id 순서와 다르다.")
    return sample


def normalize_text(value: str) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def labels(codes, mapping):
    return [{"code": code, "name": mapping[code]} for code in codes]


def validate_judgments(sample: pd.DataFrame) -> None:
    if len(JUDGMENTS) != 100:
        raise SystemExit(f"판정이 100건이 아니다: {len(JUDGMENTS)}")
    by_id = {}
    for item in JUDGMENTS:
        post_id = item["post_id"]
        if post_id in by_id:
            raise SystemExit(f"판정 post_id 중복: {post_id}")
        by_id[post_id] = item
    if set(by_id) != set(SAMPLE_POST_IDS):
        raise SystemExit("판정 post_id와 표집 post_id가 다르다.")
    bodies = {
        post_id: normalize_text(text)
        for post_id, text in zip(sample["post_id"].astype(str), sample["본문"].astype(str))
    }
    for item in JUDGMENTS:
        for field, allowed in (
            ("series_status", AXIS_STATUS),
            ("character_status", AXIS_STATUS),
            ("form_status", AXIS_STATUS),
            ("behavior_status", AXIS_STATUS),
            ("link_status", LINK_STATUS),
        ):
            if item[field] not in allowed:
                raise SystemExit(f"{item['post_id']} {field} 값 오류: {item[field]}")
        pairs = (
            ("series", "series_status", SERIES),
            ("characters", "character_status", CHARACTERS),
            ("forms", "form_status", FORMS),
            ("behaviors", "behavior_status", BEHAVIORS),
        )
        for key, status_key, mapping in pairs:
            unknown = [code for code in item[key] if code not in mapping]
            if unknown:
                raise SystemExit(f"{item['post_id']} 미정의 코드: {unknown}")
            if item[status_key] == "미언급" and item[key]:
                raise SystemExit(f"{item['post_id']} {key}는 미언급인데 라벨이 있다.")
            if item[status_key] == "분류 가능" and not item[key]:
                raise SystemExit(f"{item['post_id']} {key}는 분류 가능인데 라벨이 없다.")
        if item["link_status"] == "해당 없음" and item["links"]:
            raise SystemExit(f"{item['post_id']} 연결 해당 없음인데 연결이 있다.")
        if item["link_status"] == "분류 가능" and not item["links"]:
            raise SystemExit(f"{item['post_id']} 연결 분류 가능인데 연결이 없다.")
        seen_forms = set()
        for link in item["links"]:
            if link["form"] not in item["forms"] or link["behavior"] not in item["behaviors"]:
                raise SystemExit(f"{item['post_id']} 연결이 게시물 라벨 밖에 있다: {link}")
            if any(code not in item["characters"] for code in link["characters"]):
                raise SystemExit(f"{item['post_id']} 연결 캐릭터가 게시물 라벨 밖에 있다.")
            seen_forms.add(link["form"])
        if item["forms"] and item["links"] and seen_forms != set(item["forms"]):
            raise SystemExit(f"{item['post_id']} 형태가 연결에서 빠졌다: {set(item['forms']) - seen_forms}")
        evidence = normalize_text(item["evidence"])
        if evidence not in bodies[item["post_id"]]:
            raise SystemExit(f"{item['post_id']} 근거 문장이 본문에 없다: {item['evidence']}")
        axes = [
            item["series_status"], item["character_status"], item["form_status"],
            item["behavior_status"], item["link_status"],
        ]
        if all(status == "미언급" for status in axes[:4]) and item["link_status"] != "해당 없음":
            raise SystemExit(f"{item['post_id']} 전부 미언급이면 연결은 해당 없음이어야 한다.")
    checks = {
        "1917929935278399751": lambda item: "usagi" not in item["characters"],
        "1617786801024045058": lambda item: item["characters"] == [] and item["behaviors"] == [],
        "1730580458243813626": lambda item: item["characters"] == ["yoroi"],
        "1967214796820123765": lambda item: "oda" not in item["characters"] and "rakko" in item["characters"],
    }
    for post_id, check in checks.items():
        if not check(by_id[post_id]):
            raise SystemExit(f"부정 검증 실패: {post_id}")


def judgment_status(item: dict) -> str:
    axes = [
        item["series_status"], item["character_status"], item["form_status"],
        item["behavior_status"], item["link_status"],
    ]
    if all(status == "미언급" for status in axes[:4]) and item["link_status"] == "해당 없음":
        return "미언급"
    if any(status == "확인 필요" for status in axes):
        return "확인 필요"
    return "분류 가능"


def dump_labels(codes, mapping) -> str:
    return json.dumps(labels(codes, mapping), ensure_ascii=False)


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
            "surface": link["surface"],
        })
    return json.dumps(payload, ensure_ascii=False)


def build_output(sample: pd.DataFrame) -> pd.DataFrame:
    by_id = {item["post_id"]: item for item in JUDGMENTS}
    rows = []
    for _, row in sample.iterrows():
        item = by_id[str(row["post_id"])]
        rows.append({
            "codebook_version": CODEBOOK_VERSION,
            "post_id": str(row["post_id"]),
            "한국시간_연도": int(row["작성 시각"].year),
            "작품_라벨": dump_labels(item["series"], SERIES),
            "작품_상태": item["series_status"],
            "캐릭터_라벨": dump_labels(item["characters"], CHARACTERS),
            "캐릭터_상태": item["character_status"],
            "형태_라벨": dump_labels(item["forms"], FORMS),
            "형태_상태": item["form_status"],
            "행동_라벨": dump_labels(item["behaviors"], BEHAVIORS),
            "행동_상태": item["behavior_status"],
            "형태행동_연결": dump_links(item["links"]),
            "연결_상태": item["link_status"],
            "판단_상태": judgment_status(item),
            "근거_문장": item["evidence"],
            "판단_이유": item["reason"],
            "검토_메모": item["review"],
        })
    extra = pd.DataFrame(rows)
    base = sample.drop(columns=["post_id"]).reset_index(drop=True)
    merged = pd.concat([base.reset_index(drop=True), extra], axis=1)
    # 원본 13개 값 유지 확인
    for column in sample.columns:
        if column == "post_id":
            continue
        left = sample[column].reset_index(drop=True)
        right = merged[column].reset_index(drop=True)
        if column == "조회수":
            same = left.isna().eq(right.isna()) & (left.fillna(-1).eq(right.fillna(-1)))
        else:
            same = left.eq(right) | (left.isna() & right.isna())
        if not bool(same.all()):
            raise SystemExit(f"원본 컬럼이 달라졌다: {column}")
    return merged


def count_labels(items, key, mapping):
    counter = {name: 0 for name in mapping.values()}
    posts = {name: 0 for name in mapping.values()}
    for item in items:
        seen = set()
        for code in item[key]:
            name = mapping[code]
            counter[name] += 1
            seen.add(name)
        for name in seen:
            posts[name] += 1
    return [
        {"label": name, "label_count": counter[name], "post_count": posts[name]}
        for name in mapping.values()
        if counter[name]
    ]


def keyword_gap(sample: pd.DataFrame):
    by_id = {item["post_id"]: item for item in JUDGMENTS}
    gaps = []
    indexed = sample.set_index(sample["post_id"].astype(str))
    for post_id, item in by_id.items():
        tokens = str(indexed.at[post_id, "키워드"]).split("|")
        for token in tokens:
            code = KEYWORD_CHARACTER.get(token)
            if code and code not in item["characters"]:
                gaps.append({
                    "post_id": post_id,
                    "keyword_token": token,
                    "character_status": item["character_status"],
                    "judgment": judgment_status(item),
                })
    return gaps


def summarize(sample: pd.DataFrame, fingerprint: str) -> dict:
    items = []
    for item in JUDGMENTS:
        copied = dict(item)
        copied["judgment"] = judgment_status(item)
        items.append(copied)
    judgments = pd.Series([item["judgment"] for item in items]).value_counts().to_dict()
    by_year = {}
    sample_year = sample["작성 시각"].dt.year.astype(int)
    for item, year in zip(items, sample_year.tolist()):
        bucket = by_year.setdefault(str(year), {})
        bucket[item["judgment"]] = bucket.get(item["judgment"], 0) + 1
    link_rows = sum(len(item["links"]) for item in items)
    review_posts = [
        {
            "post_id": item["post_id"],
            "judgment": item["judgment"],
            "review": item["review"],
            "reason": item["reason"],
            "evidence": item["evidence"],
        }
        for item in items
        if item["judgment"] != "분류 가능"
    ]
    views_na = (
        sample.assign(year=sample_year)
        .groupby("year")["조회수"]
        .apply(lambda series: int(series.isna().sum()))
        .to_dict()
    )
    return {
        "fingerprint": fingerprint,
        "rows": int(len(sample)),
        "judgments": {key: int(value) for key, value in judgments.items()},
        "by_year": by_year,
        "series": count_labels(items, "series", SERIES),
        "characters": count_labels(items, "characters", CHARACTERS),
        "forms": count_labels(items, "forms", FORMS),
        "behaviors": count_labels(items, "behaviors", BEHAVIORS),
        "link_rows": link_rows,
        "posts_with_2plus_characters": int(sum(len(item["characters"]) >= 2 for item in items)),
        "posts_with_2plus_forms": int(sum(len(item["forms"]) >= 2 for item in items)),
        "posts_with_2plus_behaviors": int(sum(len(item["behaviors"]) >= 2 for item in items)),
        "character_label_sum": int(sum(len(item["characters"]) for item in items)),
        "form_label_sum": int(sum(len(item["forms"]) for item in items)),
        "behavior_label_sum": int(sum(len(item["behaviors"]) for item in items)),
        "review_posts": review_posts,
        "keyword_gaps": keyword_gap(sample),
        "views_na_in_sample": {str(key): int(value) for key, value in views_na.items()},
        "account_null_in_sample": int((sample["계정 이름"] == "null").sum()),
        "defined_but_unused": {
            "forms": [name for code, name in FORMS.items() if not any(code in item["forms"] for item in items)],
            "behaviors": [name for code, name in BEHAVIORS.items() if not any(code in item["behaviors"] for item in items)],
            "characters": [name for code, name in CHARACTERS.items() if not any(code in item["characters"] for item in items)],
        },
    }


def main() -> None:
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Python 3.11에서 실행해야 표집과 자료형이 재현된다.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, fingerprint = load_source()
    sample = draw_sample(frame)
    validate_judgments(sample)
    output = build_output(sample)
    output.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    stats = summarize(sample, fingerprint)
    reloaded = pd.read_csv(OUT_CSV, encoding="utf-8-sig", dtype={"post_id": "string"}, keep_default_na=False)
    if len(reloaded) != 100 or reloaded["post_id"].nunique() != 100:
        raise SystemExit("저장한 CSV의 행 수 또는 post_id 유일성이 깨졌다.")
    if sha256_file(PARQUET) != fingerprint:
        raise SystemExit("저장 후 Parquet 지문이 달라졌다.")
    for temporary in (OUT_DIR / "_sample_texts.json", OUT_DIR / "_sample_keys_r42.csv"):
        if temporary.exists():
            temporary.unlink()
    print(json.dumps({
        "csv": str(OUT_CSV),
        "rows": stats["rows"],
        "judgments": stats["judgments"],
        "character_label_sum": stats["character_label_sum"],
        "form_label_sum": stats["form_label_sum"],
        "behavior_label_sum": stats["behavior_label_sum"],
        "link_rows": stats["link_rows"],
        "fingerprint": fingerprint,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
