# -*- coding: utf-8 -*-
"""Attach the context re-read to the 200-comment boundary sample.

Defaults keep the existing primary. Overrides are the rows re-read as a
different primary, a criterion gap, or insufficient text.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
src = pd.read_csv(HERE / "_검토입력.csv", encoding="utf-8-sig")
for col in ("보조유형", "원문근거", "검토사유", "제목제안유형", "판정이유", "댓글원문", "영상제목"):
    src[col] = src[col].fillna("").astype(str)

NAMES = {
    "A": "작품·캐릭터 감상·장면 공유",
    "B": "개인 상품 관심·소비·소유·사용",
    "C": "팬 창작·꾸미기·제작물 공유",
    "D": "상품·거래·협찬·이벤트 안내",
    "E": "다른 인물·대상·팬덤 관련",
    "F": "콘텐츠 정보·번역·독자 교류",
    "G": "본문만으로 목적 판단 어려움",
    "H": "비한국어 본문",
}

# key = 순번
# conclusion, pri, aux, title_use, title_sug, quote, why, user
O = {}

def put(n, conclusion, pri, aux, title_use, title_sug, quote, why, user="아니오"):
    O[n] = dict(conclusion=conclusion, pri=pri, aux=aux, title_use=title_use,
                title_sug=title_sug, quote=quote, why=why, user=user)

CHG = "기존 기준 적용 오류로 변경 제안"
KEEP = "기존 판정 유지"
GAP = "기준 보완 필요"
HOLD = "근거 부족으로 판단 보류"

put(320, CHG, "E", "F", "예", "C", "완전 금손",
    "소리 칭찬과 금손은 사람 솜씨다. 만들기 영상이라는 이유만으로 C로 둔 적용이다. 같은 금손 칭찬인 437번은 E다.", "예")
put(1556, CHG, "E", "", "예", "C", "개 잘하는데",
    "계속하라고 상대의 춤 솜씨를 말한다. 만든 결과물을 평가하는 문장이 아니다.", "아니오")
put(1604, CHG, "B", "", "아니오", "", "판매하실 생각",
    "작성자가 판매 의사를 묻는 구매 질문이다. 판매 공지가 아니다.", "예")
put(2776, CHG, "B", "A", "아니오", "", "맞구 가능",
    "맞교환이 되는지 묻는 작성자의 질문이고, 치이카와가 귀엽다는 말이 있다. 교환 안내문이 아니다.", "아니오")
put(2170, CHG, "B", "D|E", "아니오", "", "태닝키티 취향저격",
    "상품 칭찬이 본문이고 이벤트 참여는 끝의 한 줄이다. 1269번과 같은 구조인데 주유형만 D로 되어 있다.", "아니오")
put(2651, CHG, "B", "D", "아니오", "", "하치와레 원해요",
    "히퍼를 사려다 못 샀고 하치와레를 원한다는 개인 소비가 있다. 응모 양식은 없다.", "아니오")
put(4409, CHG, "F", "", "아니오", "", "레몬탱 해주세용",
    "만들어 달라는 말이 없는 요청이다. 기존 기준의 업로드·버전 요청은 F다.", "아니오")
put(3960, CHG, "G", "", "예", "A", "어머니랑 생일",
    "본문은 어머니 생일이지 작품 감상이 아니다. 제목의 치이카와 생일을 본문에 넣었다.", "예")

put(523, GAP, "H", "", "아니오", "", "난다 모 아사카토",
    "한국어 문장 없이 일본어 가사 음차만 있다. H로 둘 수 있으나, 글자 기준 언어 선별의 한국어 중심과 이번 H가 다르므로 문구로 고정할 부분이다.", "예")
put(4979, GAP, "H", "", "아니오", "", "난다 모오 아사가토",
    "523번과 같이 일본어 노랫말의 한글 음차만 있다. 라벨은 유지할 수 있고, 기준 문장으로 남길 부분이다.", "아니오")
put(1738, GAP, "H", "", "아니오", "", "귀여워",
    "내용을 말하는 문장은 일본어이고 한국어는 대상 없는 귀여워뿐이다. H로 둘지, 귀여워 한 단어 때문에 혼합으로 남길지 기준이 아직 한 줄로 고정되지 않았다.", "예")
put(159, GAP, "E", "", "아니오", "", "이 사람 진짜 귀엽다",
    "이 사람이 출연자인지 캐릭터를 사람이라고 부른 것인지 본문이 가르지 않는다. E로 단정하면 기준을 보태는 것이다.", "아니오")
put(2002, GAP, "E", "", "아니오", "", "알바생",
    "알바생이 영상 속 사람인지 장면 설정인지 이름이 없다. 기존 E는 한 읽기일 뿐 기준이 정한 답이 아니다.", "아니오")
put(3591, GAP, "E", "", "아니오", "", "히나답다",
    "히나가 사람인지 캐릭터인지 본문이 없다. 이름만으로 E를 확정하지 않는 문구가 필요하다.", "아니오")
put(1663, GAP, "F", "E", "아니오", "", "큘라보 하고 싶당",
    "콜라보하고 싶다는 말이 업로드 요청인지 그 사람과의 관계인지 기준이 나누지 않는다. 영상을 잘 본다는 말도 있다.", "예")
put(162, GAP, "B", "E|F", "아니오", "", "가챠만 구매",
    "업로더 칭찬으로 시작하고 본인 가챠 구매 만족이 뒤에 있다. 어느 문장을 핵심으로 볼지 기준이 순서를 정하지 않는다.", "예")
put(4403, GAP, "A", "B|F", "아니오", "", "사고싶어지는",
    "영상으로 작품에 빠졌다는 말과 그림 때문에 책이 사고 싶다는 말이 둘 다 문장으로 있다.", "아니오")
put(478, GAP, "G", "", "예", "A", "사랑해요",
    "본문만으로는 G가 맞다. 제목에 성우와 캐릭터가 같이 있어 제안 유형을 A 하나로 두면 제목이 고른 것이다.", "아니오")
put(2800, GAP, "D", "", "아니오", "", "스티커를진짜드리고싶은데",
    "스티커를 보내겠다는 개인 제안이다. 판매·이벤트 안내로 볼지 개인 증여로 볼지 기준이 없다.", "아니오")
put(3722, GAP, "B", "", "아니오", "", "링크좀",
    "링크를 달라는 말만 있어 구매 질문인지 다른 링크인지 본문이 정하지 않는다.", "아니오")
put(2329, GAP, "E", "", "아니오", "", "금손이다",
    "금손이라는 말만 있다. 뽑기 실력인지 제작 솜씨인지 본문이 없다.", "아니오")
put(4152, GAP, "B", "F", "아니오", "", "포장 해주세요",
    "카드로 포장해 달라는 말이 구매 주문인지 영상 요청인지 본문만으로 좁혀지지 않는다.", "아니오")
put(2738, GAP, "A", "", "예", "B", "하치와레로 가득",
    "본문은 하치와레가 가득하다는 말뿐이라 A로 둘 수 있다. 제목이 쇼핑이면 상품이 가득하다는 읽기도 되어 제목 보조가 비어 있는 점이 남는다.", "아니오")
put(3097, HOLD, "G", "", "아니오", "", "",
    "글자가 깨져 먹을 곳인지 다른 말인지 복원하지 않는다. G는 잠정 표기이고 확정 판정이 아니다.", "예")

# representative keeps that the report asks the user to see
USER_KEEP = {
    18: "여기가 본문에 없다. 제목이 인형뽑기 방문이어도 주유형은 G이고 제안만 B다.",
    463: "중안부가 길다는 외형 말이다. 제목의 테무 상품을 본문에 넣지 않으면 A이고 제안만 B다.",
    2527: "솟아난다는 장면 대사를 돈으로 착각했다가 캐릭터 사정으로 되돌린다. 작성자 구매가 아니다.",
    1269: "갖고 싶다는 상품 말이 길고 이벤트 참여는 끝의 한 줄이다. 주유형 B, 보조 D가 맞다.",
    1049: "이벤트 표시가 앞에 있고 우사기를 뽑고 싶다는 말이 따른다. 주유형 D, 보조 B가 맞다.",
    4813: "자모와 영문 나열은 외국어 문장이 아니다. G가 맞고 H가 아니다.",
    2159: "연박사에게 책임지라고 하고 입덕 대상은 작품이다. 주유형 E, 보조 A가 맞다.",
    723: "투바투 포카를 꾸미자는 말이다. 창작 요청 C이고 다른 팬덤은 보조 E다. 영상 제목만으로 C가 된 것이 아니다.",
}

rows = []
for rec in src.itertuples(index=False):
    n = int(rec.순번)
    text = rec.댓글원문
    if n in O:
        item = O[n]
    else:
        quote = rec.원문근거 if rec.원문근거 and rec.원문근거 in text else ""
        why = "본문만 다시 읽어도 기존 주유형이 핵심 발화와 맞다."
        if n in USER_KEEP:
            why = USER_KEEP[n]
        item = dict(
            conclusion=KEEP,
            pri=rec.주유형코드,
            aux=rec.보조유형,
            title_use=rec.제목보조해석,
            title_sug=rec.제목제안유형,
            quote=quote,
            why=why,
            user="예" if n in USER_KEEP else "아니오",
        )
    quote = item["quote"]
    if quote and quote not in text:
        raise SystemExit(f"quote not in text {n}: {quote}")
    rows.append({
        "순번": n,
        "comment_id": rec.comment_id,
        "post_id": rec.post_id,
        "댓글원문": text,
        "영상제목": rec.영상제목,
        "추출집단": rec.선정집단,
        "해당경계": rec.해당경계,
        "기존_주유형": rec.주유형코드,
        "기존_보조유형": rec.보조유형,
        "기존_판정이유": rec.판정이유,
        "재검토_주유형": item["pri"],
        "재검토_주유형이름": NAMES[item["pri"]],
        "재검토_보조유형": item["aux"],
        "제목보조해석": item["title_use"],
        "제목제안유형": item["title_sug"],
        "원문근거": quote,
        "변경제안이유": item["why"],
        "검토결론": item["conclusion"],
        "사용자_확인필요": item["user"],
        "검토모델": "Grok 4.7",
        "기준버전": "ah-context-v1",
        "사용자_확인": "",
        "사용자_의견": "",
    })

out = pd.DataFrame(rows).sort_values("순번")
assert len(out) == 200
assert out["comment_id"].nunique() == 200
out.to_csv(HERE / "02_경계검토_최대200건.csv", index=False, encoding="utf-8-sig")
print(out["검토결론"].value_counts().to_dict())
print("primary changed", int((out["기존_주유형"] != out["재검토_주유형"]).sum()))
print("user", int((out["사용자_확인필요"] == "예").sum()))
print("strata", out["추출집단"].value_counts().to_dict())
