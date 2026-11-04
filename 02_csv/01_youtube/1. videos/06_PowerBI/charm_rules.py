# -*- coding: utf-8 -*-
"""Assign specific charm labels from existing judgments. Does not edit source files."""
import pandas as pd
from pathlib import Path

BASE = Path(r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project\02_csv\01_youtube\1. videos\05. 분석\A_호감문맥_912")
OUT = Path(r"C:\Users\user\AppData\Local\Cursor\AgentStores\cursor_agent_stores\dc6ab1ac-89a2-4949-a397-b9147b6bf627\files")


def has(text, *words):
    return any(w in text for w in words)


def charm_action(text):
    run = has(text, "달려", "뛰어오", "우다다", "헥헥", "쪼르르", "냅다")
    food = has(text, "먹", "음식", "당고", "밥", "멜론", "사과", "푸딩", "치즈", "식빵", "디저트", "마시는", "벌컥", "맛있")
    if run and food:
        return "먹으러 달려옴"
    if has(text, "춤", "율동", "박자", "리듬", "춤선", "춤사위"):
        return "춤·율동"
    if "따라" in text:
        return "다른 이를 따라 함"
    if has(text, "나눠", "나누어", "나눠주", "나눠먹", "챙기", "위로", "도와", "고마워", "나누"):
        return "나누거나 챙김"
    if has(text, "노래", "노래부"):
        return "노래"
    if has(text, "그림", "그리는", "그린", "그려"):
        return "얼굴이나 물건에 그림"
    if food or has(text, "냠", "념념", "먹방", "요구르트", "국수", "먀금", "마시는", "벌컥"):
        return "먹는 모습"
    if has(text, "집중", "의젓", "열심히", "기특", "풀 뽑", "풀뽑", "자격증", "조수", "대견", "공부"):
        return "열심히·집중"
    if "꼬리" in text:
        return "꼬리를 흔듦"
    if has(text, "눈물", "울면", "우는", "글썽"):
        return "울거나 눈물"
    if has(text, "추임", "샤부", "캬", "야하"):
        return "추임새와 함께하는 행동"
    if has(text, "뛰", "뛸", "뜀", "방방", "달려", "포즈", "박수", "휘적", "팔딱", "꼬물", "다리", "뒤뚱", "뽈", "운전", "납작"):
        return "뛰거나 특정 몸짓"
    if has(text, "쓰러", "꾸익"):
        return "하찮게 쓰러짐"
    if has(text, "자는", "잠자"):
        return "자는 모습"
    return "서로 다른 장면의 몸짓"


def charm_personality(text):
    if has(text, "광기", "똘끼", "스타성"):
        return "광기·똘끼"
    if has(text, "표독", "자기밖에", "싸가지", "성격더럽", "폐급", "갭", "나쁜 행동", "인성", "추악"):
        return "표독하거나 자기중심적"
    if has(text, "친구", "배려", "나눠", "나누", "걱정", "지키", "권유", "후리카케", "소금밥", "알려"):
        return "친구를 위한 배려·나눔"
    if has(text, "용기", "용감", "용맹", "포기", "강하", "싸우", "장하"):
        return "겁이 있어도 나서는 용기"
    if has(text, "상냥", "어른", "아저씨", "잠옷", "선물", "동질감", "술"):
        return "상냥하거나 어른스러운 면"
    if has(text, "성실", "공부", "열심히", "노력"):
        return "성실·노력"
    if has(text, "요리"):
        return "상냥하거나 어른스러운 면"
    if has(text, "애교", "사랑받", "당돌", "천진", "귀엽고싶", "귀엽고 싶"):
        return "애교·당돌함"
    if has(text, "착", "순수", "다정", "마음", "따뜻"):
        return "착함·다정"
    if has(text, "하찮", "소심"):
        return "하찮음·소심"
    if has(text, "웃기", "웃김", "재미"):
        return "웃김"
    return "내용을 특정하지 않은 성격"


def charm_look(text):
    if has(text, "추악", "인성", "괴물", "갭"):
        return "귀여운 겉과 다른 속"
    if "가르마" in text:
        return "가르마"
    if has(text, "볼", "이빨", "송곳니", "주름", "입모양", "ㅁ 모양"):
        return "볼·입·이빨"
    if has(text, "엉덩이", "궁뎅", "궁디", "뒷통", "똥꼬"):
        return "엉덩이·뒷모습"
    if has(text, "꼬리", "귀가", "토끼귀", "귀 ", "털", "솜", "포송", "복슬", "복실"):
        return "꼬리·귀·털"
    if has(text, "눈썹", "눈빛", "초롱", "눈의", "눈 크기", "눈이"):
        return "눈·눈썹"
    if has(text, "통통", "뚱뚱"):
        return "통통한 몸"
    if has(text, "옷", "패션", "리본", "뱀파이어", "문어"):
        return "의상·변신한 모습"
    if has(text, "하찮", "꼬질"):
        return "하찮거나 꼬질한 모습"
    if has(text, "동글", "말랑", "작", "쪼꼬", "소중", "몽글", "하얗", "화이트", "쫀득", "포동"):
        return "동글·말랑·작음"
    return "부위를 말하지 않은 생김"


def charm_face(text):
    if has(text, "표독", "사나운", "절레", "악마"):
        return "표독·사나운 표정"
    if has(text, "눈썹", "눈빛", "눈섭", "능글", "처진", "돌아있", "초롱"):
        return "눈썹·눈빛"
    if has(text, "시무룩", "울먹", "눈물", "글썽", "아련"):
        return "시무룩·울먹"
    if has(text, "먹", "볼", "짜부", "빵"):
        return "먹거나 볼이 변하는 표정"
    if has(text, "진지", "집중", "무표정"):
        return "진지·무표정"
    if has(text, "멍", "댕", "나사", "왜저러", "해맑", "똘망"):
        return "멍하거나 엉뚱한 표정"
    if has(text, "순한", "착해서", "착둥", "착해"):
        return "순한 표정"
    if has(text, "찌푸", "충격", "어이", "눈치", "당황"):
        return "당황하거나 찌푸린 표정"
    if has(text, "빨개", "기대", "극락", "오묘", "얍", "갸웃", "찡그", "빛나", "콧등"):
        return "한 장면의 표정"
    return "어떤 표정인지 말하지 않음"


def charm_speech(text):
    if has(text, "캬", "샤부", "야하", "머시따", "추임", "하아", "칭구"):
        return "특정 말·추임새"
    if has(text, "짓궂", "톤", "시무룩"):
        return "짓궂거나 시무룩한 말투"
    return "어떤 말투인지 말하지 않음"


def charm_voice(text):
    if has(text, "야하", "야~하", "응쇼", "뿌애", "울라", "시러", "히러", "퉤", "응차", "젠장"):
        return "특정 추임새·울음"
    if has(text, "발음", "의성어", "웅얼", "고날", "고라고"):
        return "발음·의성어"
    if has(text, "일본", "한국", "더빙판", "한더빙", "국내", "일본판", "한국판"):
        return "한국·일본 더빙 비교"
    if has(text, "입덕", "반했", "반해", "빠졌", "빠지게", "빠졌"):
        return "목소리 때문에 입덕·반함"
    if has(text, "찰떡", "그 자체", "어울"):
        return "캐릭터와 어울리는 목소리"
    if has(text, "허스키", "스윗", "미성", "청량", "말랑", "힘없", "중성", "애기", "성숙", "달달", "잘생", "씩씩", "가련", "시원", "소년", "광기"):
        return "음색"
    return "음색을 특정하지 않은 목소리"


def charm_rel(text, cat):
    if cat == "관계" or has(text, "우정", "다음을 약속", "같이 있어야", "같이 있기"):
        return "우정·함께 있음"
    if cat == "행동":
        if has(text, "말려", "챙겨", "나눠", "나누어", "도와", "위로"):
            return "챙겨 주거나 말려 줌"
        if has(text, "먹", "춤", "아이스크림", "디저트"):
            return "같이 먹거나 춤"
        return "여럿이 하는 몸짓"
    if cat == "표정":
        return "여럿의 표정"
    if cat == "외형":
        return "여럿의 생김·크기"
    if cat == "성격":
        return "여럿의 성격"
    if has(text, "우정", "함께"):
        return "우정·함께 있음"
    return "관계를 짧게 칭찬"


def charm_work(text, cat):
    if has(text, "상냥", "따뜻", "의지", "도우", "우정", "도와"):
        return "상냥하고 서로 도움"
    if has(text, "다크", "호러", "위험", "무서운", "대비", "가혹", "씁쓸", "불편", "잔혹", "무게", "고통"):
        return "귀여움과 무거운 이야기의 대비"
    if has(text, "MZ", "청년", "먹고살", "현실", "대변"):
        return "현실·먹고사는 공감"
    if has(text, "짠", "위안", "감동", "뭉클", "교훈"):
        return "귀엽고 짠하거나 위로가 됨"
    if has(text, "연출", "의성어", "자극", "소통"):
        return "쉬운 연출·의성어"
    if has(text, "비장", "지키려"):
        return "지키려는 비장함"
    if has(text, "열심히 사"):
        return "귀여운 척 없이 열심히 삶"
    if has(text, "파자마", "에피소드"):
        return "특정 전개가 재미있음"
    if has(text, "서사", "세계관을 완성", "감초", "빌런"):
        return "서사가 이야기를 받침"
    if cat == "세계관":
        return "세계관을 긍정"
    if cat == "스토리":
        return "스토리를 긍정"
    return "작품 요소를 긍정"


def charm_goods(text, cat):
    if has(text, "벗겨", "만져"):
        return "만져 보거나 벗겨 보고 싶음"
    if has(text, "얼굴만"):
        return "얼굴만 있는 형태"
    if has(text, "파츠", "말풍선", "포장", "홀로그램", "이불", "지퍼"):
        return "파츠·포장 같은 디테일"
    if has(text, "같이 있", "세 마리", "세마리", "함께"):
        return "여러 캐릭터가 같이 있음"
    if has(text, "모찌", "촉감", "질감", "몽글", "쫀득", "복슬", "유리", "말랑"):
        return "촉감·재질·색감"
    if has(text, "작", "크기", "왕크", "사이즈", "비율", "쪼꼬", "쬐끄", "왕 크"):
        return "크기·비율"
    if has(text, "표정", "포즈", "눈", "울먹"):
        return "표정·포즈"
    if has(text, "실물", "모으", "소장", "소중하게", "가지고 싶"):
        return "실물·소장 경험"
    if has(text, "수납", "실용", "퀄", "품질", "양과"):
        return "품질·실용"
    if cat == "굿즈 디자인" or "디자인" in text:
        return "디테일을 말하지 않은 디자인"
    return "부위를 말하지 않은 실물"


def charm_staff(text, cat, target):
    if target == "성우·커버 가수":
        if has(text, "자오", "성우다", "같은 성우"):
            return "특정 성우를 알아봄"
        if cat == "연기" or "연기" in text:
            return "연기"
        return "성우 목소리 덕분에 귀여움"
    if has(text, "포장", "언박싱", "구성", "바느질", "솜"):
        return "포장·바느질·구성"
    if has(text, "현장감", "목소리 들어", "더빙", "목소리"):
        return "목소리·현장감을 넣은 편집"
    if has(text, "포근", "잠", "힐링", "분위기"):
        return "영상 분위기"
    return "내용을 특정하지 않은 제작·편집"


def _vague(name):
    if not name:
        return True
    return any(v in name for v in ("특정하지", "말하지", "서로 다른", "내용을 특정", "그 밖의", "짧게", "요소를 긍정"))


def classify(text, target, cat):
    if target == "특정 캐릭터":
        if cat == "관계":
            return "친구를 위해 공부하거나 선물"
        if cat == "성우 연결":
            return "특정 성우를 알아봄"
        if cat == "소지품":
            return "하찮은 소지품"
        if cat == "굿즈 디자인":
            return "캐릭터 굿즈의 품질"
        if cat == "연출":
            return "노래"
        fn = {
            "행동": charm_action,
            "성격": charm_personality,
            "외형": charm_look,
            "표정": charm_face,
            "말투": charm_speech,
            "목소리": charm_voice,
            "스토리": charm_work,
        }.get(cat)
        if fn is None:
            return "그 밖의 긍정"
        return fn(text, cat) if fn == charm_work else fn(text)
    if target == "캐릭터 관계·복수 캐릭터":
        return charm_rel(text, cat)
    if target == "작품 전체·스토리·세계관":
        return charm_work(text, cat)
    if target == "작품·캐릭터 불명확":
        fn = {"행동": charm_action, "성격": charm_personality, "외형": charm_look, "표정": charm_face, "말투": charm_speech}.get(cat)
        return fn(text) if fn else "특징을 짧게 칭찬"
    if target == "캐릭터 음성·더빙":
        return charm_voice(text)
    if target == "굿즈·상품":
        return charm_goods(text, cat)
    if target in ("성우·커버 가수", "제작자·편집"):
        return charm_staff(text, cat, target)
    return "그 밖의 긍정"


def assign(row):
    if row["평가_방향"] != "긍정":
        return None
    if row["호감근거_수준"] not in ("직접 밝힌 이유", "구체적 긍정 평가"):
        return None
    cat = str(row["특징_범주"])
    if cat in ("포괄", "없음"):
        return None
    target = row["평가대상"]
    quote = "" if pd.isna(row["근거문구"]) else str(row["근거문구"])
    feat = "" if pd.isna(row["구체적_특징"]) else str(row["구체적_특징"])
    first = classify(quote, target, cat)
    if not _vague(first):
        return first
    second = classify(feat, target, cat)
    if not _vague(second):
        return second
    return first or second


def main():
    link = pd.read_csv(BASE / "03_연결_진행.csv")
    meta = pd.read_csv(BASE / "01_입력_912.csv", usecols=["comment_id", "account_id", "post_id", "영상제목"])
    df = link.merge(meta, on="comment_id", how="left", suffixes=("", "_m"))
    if not (df["post_id"] == df["post_id_m"]).all():
        bad = (df["post_id"] != df["post_id_m"]).sum()
        print("post mismatch", bad)
    df["매력"] = df.apply(assign, axis=1)
    pos = df[df["호감근거_수준"].isin(["직접 밝힌 이유", "구체적 긍정 평가"])]
    print("positive rows", len(pos), "assigned", pos["매력"].notna().sum(), "excluded", pos["매력"].isna().sum())
    print("excluded direction", pos.loc[pos["매력"].isna(), "평가_방향"].value_counts().to_string())
    print("excluded feature", pos.loc[pos["매력"].isna(), "특징_범주"].value_counts().to_string())
    use = df[df["매력"].notna()].copy()
    mains = ["우사기", "치이카와", "하치와레", "모몽가", "라코", "시사", "쿠리만쥬", "갑옷씨"]
    sub = use[(use["평가대상"] == "특정 캐릭터") & (use["대상_상세"].isin(mains))]
    ct = sub.groupby(["대상_상세", "특징_범주", "매력"])["comment_id"].nunique().reset_index(name="n")
    ct = ct.sort_values(["대상_상세", "특징_범주", "n"], ascending=[True, True, False])
    print("\n=== MAIN CHARM COUNTS ===")
    print(ct.to_string(index=False))
    print("\n=== OTHER TARGETS ===")
    oth = use[use["평가대상"] != "특정 캐릭터"]
    print(oth.groupby(["평가대상", "매력"])["comment_id"].nunique().sort_values(ascending=False).to_string())
    print("\n=== residual-like ===")
    residual = use[use["매력"].str.contains("짧게|그 장면|그 밖|요소를|스토리를 긍정|세계관을 긍정|실물 생김|디자인$")]
    print("residual rows", len(residual), "ids", residual.comment_id.nunique())
    for target, g in residual.groupby("평가대상"):
        print(f"\n--- {target} {len(g)} ---")
        for _, r in g.iterrows():
            print(f"{r['대상_상세']}|{r['특징_범주']}|{r['매력']}|{r['구체적_특징']} || {str(r['근거문구'])[:60]}")
    use.to_csv(OUT / "assigned.tsv", sep="\t", index=False, encoding="utf-8-sig")
    print("\nwrote", len(use))


if __name__ == "__main__":
    main()
