# -*- coding: utf-8 -*-
"""치이카와 X 게시물 문맥 규칙. 라벨의 최종 판단은 구절 안 주체·부정·연결이다.

형태소 분석기는 이 파일을 쓰지 않는다. 빈도 집계만 별도 스크립트에서 한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

VERSION = "2026-10-30.v2.3"
METHOD = "clause_context_rules"

HANGUL = re.compile(r"[가-힣]")
KANA = re.compile(r"[ぁ-んァ-ヶ]")
KANJI = re.compile(r"[一-龯]")
LATIN = re.compile(r"[A-Za-z]")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
HASHTAG_RE = re.compile(r"#([^\s#]+)")
WS_RE = re.compile(r"[ \t]+")

# 확인된 표기. 짧은 호칭(치이, 하치, 가르마, 토끼)은 자동으로 합치지 않는다.
STRONG_NAME_RES = [
    ("치이카와", re.compile(r"치이까와|치이카와|치카와|chiikawa|ちいかわ|吉伊卡哇", re.I)),
    ("하치와레", re.compile(r"하치와레|하치와래|ハチワレ")),
    ("모몽가", re.compile(r"모몽가|모몬가")),
    ("랏코", re.compile(r"(?<![가-힣])랏코(?![가-힣])")),
    ("쿠리만쥬", re.compile(r"쿠리만쥬|쿠리만주")),
    ("갑옷씨", re.compile(r"갑옷\s*씨|갑옷\s*아저씨|갑옷아저씨|갑옷\s*상")),
    ("먼작귀", re.compile(r"먼작귀|뭔가\s*작고\s*귀여운")),
]
# 본문에 다른 치이카와 단서가 있을 때만 등장인물로 인정한다.
AMBIGUOUS_NAME_RES = [
    ("우사기", re.compile(r"(?<![가-힣])우사기(?![가-힣])|うさぎ")),
    ("시사", re.compile(r"(?<![가-힣])시사(?![하가은는을를의와과점])")),
    ("카니", re.compile(r"(?<![가-힣])카니(?!발)")),
    ("아노코", re.compile(r"(?<![가-힣])아노코(?![가-힣])")),
    ("데카츠요", re.compile(r"데카츠요")),
]
PAREN_ALIAS_RES = [
    ("하치와레", re.compile(r"가르마\s*[\(（]\s*하치와레\s*[\)）]")),
    ("우사기", re.compile(r"토끼\s*[\(（]\s*우사기\s*[\)）]")),
]
OTHER_FRANCHISE_RE = re.compile(
    r"유유백서|산리오|체인소|주술회전|히로아카|스파이\s*패밀리|디지몬|포켓몬|헬로키티|최애캐가"
)
OTHER_IP_RES = [
    ("파자마파티즈", re.compile(r"파자마\s*파티즈|파자마파티즈")),
    ("농담곰", re.compile(r"농담곰")),
    ("빤쮸토끼", re.compile(r"빤쮸\s*우사기|빤쮸우사기|오빤쮸|빤쮸\s*토끼")),
]
WORK_CUE_RE = re.compile(
    r"애니|애니메이션|영화|만화|극장|세계관|시리즈|더빙|에피소드|"
    r"\d+\s*화|정발|원작|연재|방영"
)
CHARACTER_CUE_WORDS = re.compile(r"캐릭터|주인공|얘|애|햄찌|등장")

POS_EVAL_RE = re.compile(
    r"귀엽|귀여|커여|기여|기엽|기염|깜찍|사랑스|존귀|좋아|좋다|조아|최고|소중|"
    r"힐링|기특|다정|착하|멋있|대박|행복|취향|반했|홀렸|설레|반가워|반갑|신나"
)
HUMOR_RE = re.compile(r"웃기|웃겨|웃김|개웃|빵터|빵\s*터|ㅈㄴ웃|존웃")
NEG_EVAL_RE = re.compile(r"싫|별로|못생겼|안\s*귀여|귀엽지\s*않|귀엽진\s*않|짜증|무서|질색|노답")
NEGATOR_RE = re.compile(r"(?:안|못)\s*$|지\s*않$|진\s*않$")

APPEAR_RE = re.compile(
    r"얼굴|표정|볼살|볼콕|꼬리|팔다리|짧은\s*팔|짧은\s*다리|동글|동그랗|작디작|"
    r"눈망울|큰\s*눈|반짝이는\s*눈|색감|귀여운\s*입|옷\s*입|코스튬|모자"
)
# 눈만으로는 외형이 아니다. 형태 수식이 있을 때만.
EYE_FORM_RE = re.compile(r"눈(?:이|도)?\s*(?:크|동그|반짝|빛나|초롱|말랑)")
BODY_RE = re.compile(r"(?:몸|볼|귀|입|팔|다리|꼬리)(?:이|도|은|는|을|를)?")
TEXTURE_RE = re.compile(r"말랑|폭신|부들|부드러|포근|촉감|재질|마감|퀄리티|품질|디테일")
PERSONALITY_RE = re.compile(
    r"말투|대사|목소리|기특|다정|착하|잔인|사악|순수|용감|깐죽|성격|츤데레|다정함"
)
ACTION_VERB_RE = re.compile(
    r"먹(?:고|어|음|는|다|었|네)|울(?:고|어|음|었|네|다)|뛰(?:는|어|고|었)|"
    r"춤(?:추|을|췄)|기어|미끄러|떨(?:고|며|면서)|인사|싸우|도와|"
    r"토벌(?:하|했|함|한다)|공부(?:하|했)|숨(?:고|어)|달리|안(?:고|아)|잡(?:고|아)|"
    r"말(?:하|함|해|했)|노래|자(?:고|는)|방방"
)
REL_RE = re.compile(r"우정|케미|친구\s*사이|명장면|나란히|둘이|서로|같이|옆에서|콤비")
COMFORT_RE = re.compile(r"힐링|위로|공감|소중|와닿|겹치|내\s*얘기|현실|일상|마음")
PRODUCT_QUALITY_RE = re.compile(
    r"재질|마감|퀄리티|품질|디테일|말랑|폭신|부들|부드러|자수|프린팅|기능|무게|사이즈|크기"
)

FORM_RES = [
    ("인형", re.compile(r"인형|누이구루미|누이")),
    ("피규어", re.compile(r"피규어|넨도로이드|소프비")),
    ("스티커", re.compile(r"스티커|조각스티커|씰|씰스티커|다이컷")),
    ("키링", re.compile(r"키링|키체인|키홀더|볼체인|스트랩")),
    ("아크릴", re.compile(r"아크릴")),
    ("뱃지", re.compile(r"뱃지|캔뱃지|배지")),
    ("파우치", re.compile(r"파우치|포셰트")),
    ("의류", re.compile(r"티셔츠|후드|맨투맨|파자마|잠옷|양말|옷")),
    ("문구", re.compile(r"노트|다이어리|캘린더|달력|펜|문구")),
    ("식품", re.compile(r"모찌|쿠키|푸딩|캔디|과자|빵|라면|카레|후리카게")),
    ("이모티콘", re.compile(r"이모티콘|임티")),
    ("마스코트", re.compile(r"마스코트")),
    ("카드", re.compile(r"(?<![가-힣])카드(?![가-힣])")),
    ("기타 상품", re.compile(r"굿즈|상품")),
]
# 식품 단어가 인형·마스코트와 같이 있고 섭취 단서가 없으면 식품으로 확정하지 않는다.
EAT_RE = re.compile(r"맛있|먹어|먹었|맛남|섭취|간식")
CHANNEL_RES = [
    ("가챠", re.compile(r"가챠|가샤")),
    ("랜덤", re.compile(r"랜덤")),
    ("쿠지", re.compile(r"쿠지|제일복권")),
    ("공동구매", re.compile(r"공구|공동\s*구매")),
    ("직구", re.compile(r"직구|배대지|구매대행")),
    ("예약판매", re.compile(r"예약\s*판매|예약판매")),
]
CONTENT_RES = [
    ("애니메이션", re.compile(r"애니메이션|애니")),
    ("영화", re.compile(r"영화|극장")),
    ("만화", re.compile(r"만화")),
    ("팝업", re.compile(r"팝업")),
    ("카페·매장", re.compile(r"카페|팝업스토어|스토어")),
    ("콜라보", re.compile(r"콜라보")),
    ("이모티콘", re.compile(r"이모티콘")),
]
FUNCTION_RES = [
    ("부착", re.compile(r"달고|달아|붙여|가방에\s*착|자석")),
    ("장식", re.compile(r"진열|전시|올려\s*두|책상\s*위|인테리어")),
    ("수납", re.compile(r"수납|파우치에\s*넣|보관")),
    ("실사용", re.compile(r"쓰다듬|사용해|써\s*봤|입고\s*다|꺼내\s*다")),
    ("착용", re.compile(r"입고\s*나갔|걸쳐\s*입|양말\s*신")),
]

DOMESTIC_RE = re.compile(
    r"홍대|강남|명동|성수|부산|대구|대전|광주|인천|제주|코엑스|스타필드|더현대|"
    r"신도림|건대|잠실|판교|수원|일산|서울|한국|국내|정발|"
    r"다이소|스파오|쿠팡|스마트스토어|올리브영|핫트랙스|교보|알라딘|예스24|"
    r"무신사|이마트|홈플러스|아트박스|텐바이텐|GS25|씨유\b|CU\b|"
    r"카카오톡|원화|만원|천원|\d\s*원|₩"
)
JAPAN_ONLY_RE = re.compile(
    r"엔화|\d\s*엔|일본|도쿄|오사카|하라주쿠|이케부쿠로|시부야|파르코|교토|삿포로|"
    r"치이카와\s*마켓|chiikawa\s*market|직구|배대지"
)

PROMO_RE = re.compile(
    r"예약\s*판매|판매\s*안내|입고\s*(?:안내|완료|되었|됐습니다)|재입고|"
    r"판매\s*링크|스마트스토어|수요조사|증정|특전|발매|오픈\s*카톡|"
    r"폼\s*(?:업로드|작성|열)|구매\s*링크|예약\s*접수|신상\s*공구|"
    r"RT\s*이벤트|알티\s*이벤트|팔로우\s*\+\s*RT|추첨하여"
)
TRADE_RE = re.compile(
    r"양도|급처|교환\s*합니다|교환해요|팝니다|판매합니다|반택|"
    r"(?<![가-힣])구합니다|구함|삽니다|구매합니다|구해요"
)
GIFT_PROMO_RE = re.compile(r"선물\s*드립|나눠\s*드립|나눔\s*이벤트|증정")

# 구매 완료. 삿포로·샀을·사서·구매링크는 넣지 않는다.
BUY_DONE_RE = re.compile(
    r"(?:구매|구입)했|결제\s*했|결제\s*완료(?!되지|하지)|(?<![가-힣소리])질렀|"
    r"사버렸|사왔|사옴|"
    r"(?<![가-힣])샀(?:다|어|어요|음|네|지|고|는데|더니|더|던|습|당|구|따|어용|어욤)"
)
BUY_WISH_RE = re.compile(r"사고\s*싶|사고싶|사야지|사야겠|살\s*예정|살\s*거(?:다|예|야)")
BUY_THINK_RE = re.compile(r"살까|살래|살지")
BUY_NONE_RE = re.compile(r"(?:아예|하나도|한\s*개도)\s*안\s*샀|(?:안|못)\s*샀|사지\s*않|안\s*사(?:요|고|서)|못\s*사(?:서|요|고)")
BUY_FEW_RE = re.compile(r"몇\s*개\s*안\s*샀|별로\s*안\s*샀")
BUY_GIVEUP_RE = re.compile(r"사기\s*포기|구매\s*포기|포기(?:했|함|한다)")
OWN_WISH_RE = re.compile(r"갖고\s*싶|가지고\s*싶|소장하고\s*싶|갖고싶|가지고싶")
GET_RE = re.compile(r"(?<![가-힣])겟(?:했|함|했어|했다|한|!)|득템")
BRING_RE = re.compile(r"데려왔|데려온|델꾸")
DRAW_GOODS_RE = re.compile(r"뽑(?:았|음|아|아서)|뽑아\s*봤")
STORY_DRAW_RE = re.compile(r"풀뽑기|뽑기\s*자격|자격증")
RAFFLE_RE = re.compile(r"추첨|당첨자|분을\s*뽑|명\s*뽑")
WATCH_DONE_RE = re.compile(r"(?:애니|애니메이션|영화|만화|에피소드|정주행).{0,16}(?:봤|보는\s*중|정주행)|(?:봤|보고\s*있).{0,16}(?:애니|영화|만화)")
WATCH_WISH_RE = re.compile(r"(?:애니|영화|만화).{0,12}보고\s*싶|보고\s*싶.{0,12}(?:애니|영화|만화)")
REWATCH_RE = re.compile(r"(?:또|다시|여러\s*번|몇\s*번).{0,8}(?:봤|봄)|돌려\s*봤|무한\s*재생")
VISIT_RE = re.compile(r"(?:팝업|스토어|카페|매장).{0,12}(?:갔|다녀|방문)|(?:갔|다녀왔).{0,12}(?:팝업|스토어)")
GROUP_JOIN_RE = re.compile(r"공구\s*탑승(?:했|한|함)|(?<![가-힣])탑승했|공구\s*참여(?:했|한)|입금했")
GROUP_OPEN_RE = re.compile(r"공구.{0,12}(?:폼|오픈|진행|1차금)|폼\s*(?:업로드|열)|수요조사")
IMAGINE_RE = re.compile(r"꿈에서|꿈에|상상\s*속|하면\s*좋겠")
OTHER_PERSON_RE = re.compile(r"(?:친구|룸메|남친|여친|엄마|아빠|언니|오빠|동생)(?:가|는|이)\s*.{0,16}(?:샀|구매|겟)")
TEMPLATE_PAY_RE = re.compile(
    r"배송비|결제일|결제창|구매\s*링크|구매자|구매\s*제한|구매\s*시|구입하면|"
    r"결제완료되지|결제\s*완료되지|나중에\s*결제|무통보"
)
QUOTE_SAY_RE = re.compile(r"[\"“”「」].{0,40}(?:라고|하고)")

USE_RES = [
    ("휴대", re.compile(r"들고\s*다|가지고\s*다|매일\s*챙")),
    ("가방 부착", re.compile(r"가방에\s*(?:달|착|붙)|키링으로\s*달|달고\s*다")),
    ("전시", re.compile(r"진열|전시해|올려\s*두|책상에\s*두")),
    ("보관", re.compile(r"보관|넣어\s*두|상자\s*안")),
    ("실사용", re.compile(r"쓰다듬|사용해\s*봤|써\s*봤|실제로\s*쓰|먹어\s*봤|입고\s*다녔")),
    ("선물 수령", re.compile(r"선물(?:로)?\s*받|선물\s*주심|선물\s*해\s*주")),
    ("선물 증여", re.compile(r"선물(?:로)?\s*(?:줬|함|했다|할)")),
    ("꾸미기", re.compile(r"꾸몄|코디|붙여\s*봤|다꾸")),
    ("아껴서 미사용", re.compile(r"아까워(?:서)?\s*못|못\s*쓰겠|아껴\s*두|미개봉으로\s*둘")),
    ("단순 보유", re.compile(r"가지고\s*있|소장\s*중|보유\s*중")),
]
USE_WISH_RE = re.compile(r"하고\s*싶|쓰고\s*싶|달고\s*싶|꾸미고\s*싶")

COLLECT_RES = [
    ("같은 캐릭터의 여러 버전", re.compile(r"버전\s*별|표정\s*별|같은\s*(?:애|캐릭터).{0,8}(?:여러|또)|시리즈\s*버전")),
    ("여러 캐릭터 조합", re.compile(r"(?:셋|세트)으로|친구들?\s*(?:같이|한\s*세트)|조합|나란히\s*모")),
    ("세트·시리즈 완성", re.compile(r"세트\s*맞|다\s*모으|컬렉|시리즈\s*모|종류\s*별로\s*모")),
    ("함께 사용할 때의 재미·기능", re.compile(r"같이\s*(?:두|놓)(?:니까|면)|나란히\s*두|같이\s*쓰")),
    ("이미 있는데 추가", re.compile(r"또\s*(?:샀|사고|겟)|하나\s*더|이미\s*있는데")),
]

FIRST_RE = re.compile(
    r"입덕|처음\s*접|첨엔|처음엔|처음에는|추천\s*받|보여\s*줘서|보여\s*주길래|알게\s*된\s*계기"
)
NOT_FIRST_RE = re.compile(r"직구\s*입문|입문하기에|카드.{0,6}입문|입문\s*카드|입덕했나|입덕했니|솔드?\s*아웃")
CARD_ENTRY_RE = re.compile(r"카드.{0,6}입문|입문\s*카드")

SCENE_QUOTE_RE = re.compile(r"[\"“”「」]|야하|우라~|하악")
FAN_RE = re.compile(r"팬아트|팬\s*아트|그렸(?:다|어|음)|그려\s*봤|자작|코스프레|번역(?:했|해\s*봤|하고\s*있)")
FAN_WISH_RE = re.compile(r"그려\s*줬으면|만들어\s*주|내\s*줬으면|발매해\s*주")
RECO_RE = re.compile(r"추천(?:해|드|합니다|해요)|꼭\s*보|봐\s*보세요|강추")
SHARE_RE = re.compile(r"공유합니다|공유해|퍼가요")

BARRIER_RES = [
    ("원하는 대상 부재", re.compile(r"없나|안\s*나와|안\s*나옴|재고\s*없|품절|구할\s*수\s*없|국내에\s*없")),
    ("가격·예산", re.compile(r"비싸|부담|예산|돈이\s*없|가격\s*때문|창렬|너무\s*비")),
    ("품절·재고", re.compile(r"품절|재고\s*없|솔드\s*아웃|매진")),
    ("구매 경로", re.compile(r"어디서\s*사|국내에\s*(?:없|안\s*팔)|직구\s*뿐|배대지\s*없")),
    ("품질", re.compile(r"마감\s*별로|품질\s*별로|하자|부실")),
    ("크기·보관", re.compile(r"둘\s*곳|자리\s*없|너무\s*커서|보관\s*공간")),
]
WANT_GAP_RE = re.compile(r"있었으면|나왔으면|만들어\s*주|출시해\s*주|재입고\s*해")
BLOCK_RE = re.compile(r"못\s*샀|안\s*샀|포기|살\s*수\s*없|구매\s*못")

# 아서/어서는 음절 둘로 드러나기도 하고(좋아서, 없어서), ㅂ·ㅎ 불규칙이면 워서·뻐서·싸서로 붙는다.
REASON_SPLIT_RE = re.compile(
    r"(?P<left>.{2,90}?)(?:(?<=[가-힣])(?:아서|어서|해서|여서|워서|라서|이어서|뻐서|겨서|싸서)|때문에|(?<!습)니까|길래)(?P<right>.{1,90})"
)
NOT_REASON_RE = re.compile(r"지만|는데|ㄴ데")

VA_RE = re.compile(r"성우|더빙|목소리\s*배우")
CELEB_RE = re.compile(r"아이돌|연예인")


@dataclass
class Ev:
    axis: str
    label: str
    quote: str
    quote_start: int
    quote_end: int
    target: str = "언급 없음"
    target_type: str = "언급 없음"
    speaker: str = "작성자"
    emotion: str = "해당없음"
    action_type: str = "해당없음"
    action_status: str = "해당없음"
    acquisition: str = "해당없음"
    aspect: str = "해당없음"
    selection_reason: str = "해당없음"
    use_mode: str = "해당없음"
    use_status: str = "해당없음"
    collection_type: str = "해당없음"
    content_use: str = "해당없음"
    barrier_type: str = "해당없음"
    barrier_role: str = "해당없음"
    certainty: str = "확정"
    judgment_note: str = ""
    about_ip: str = "예"
    clause_id: int = -1
    extra: dict = field(default_factory=dict)


def mask_keep_len(text: str) -> str:
    chars = list(text)
    for m in URL_RE.finditer(text):
        for i in range(m.start(), m.end()):
            chars[i] = " "
    for m in MENTION_RE.finditer(text):
        for i in range(m.start(), m.end()):
            chars[i] = " "
    return "".join(chars)


def analysis_text(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = re.sub(r"#", "", t)
    return t


def split_clauses(masked: str) -> list[tuple[int, int, str]]:
    parts = []
    start = 0
    for m in re.finditer(r"[.!?\n。！？]+", masked):
        end = m.end()
        chunk = masked[start:end]
        if chunk.strip():
            parts.append((start, end, chunk))
        start = end
    if start < len(masked) and masked[start:].strip():
        parts.append((start, len(masked), masked[start:]))
    if not parts and masked.strip():
        parts.append((0, len(masked), masked))
    return parts


def exact_span(original: str, start: int, end: int) -> tuple[int, int, str]:
    end = min(end, len(original))
    start = max(0, start)
    while start < end and original[start] in " \t\r":
        start += 1
    while end > start and original[end - 1] in " \t\r":
        end -= 1
    return start, end, original[start:end]


def find_names(text: str, strong_only: bool = False) -> dict[str, list[tuple[int, int]]]:
    found: dict[str, list[tuple[int, int]]] = {}
    res = STRONG_NAME_RES + PAREN_ALIAS_RES
    if not strong_only:
        res = res + AMBIGUOUS_NAME_RES
    for name, rx in res:
        for m in rx.finditer(text):
            found.setdefault(name, []).append((m.start(), m.end()))
    return found


def other_ips(text: str) -> list[str]:
    return [name for name, rx in OTHER_IP_RES if rx.search(text)]


def has_strong(text: str) -> bool:
    return any(rx.search(text) for _, rx in STRONG_NAME_RES + PAREN_ALIAS_RES)


def script_counts(text: str) -> tuple[int, int, int]:
    return len(HANGUL.findall(text)), len(KANA.findall(text)) + len(KANJI.findall(text)), len(LATIN.findall(text))


def strip_hashtags_for_count(masked: str) -> tuple[str, str]:
    tags = " ".join(HASHTAG_RE.findall(masked))
    body = HASHTAG_RE.sub(" ", masked)
    return body, tags


def language_of(masked: str) -> str:
    body, tags = strip_hashtags_for_count(masked)
    bk, bj, bl = script_counts(body)
    tk, tj, tl = script_counts(tags)
    ko, ja, lat = bk + tk, bj + tj, bl + tl
    if ko + ja + lat < 4:
        return "판단 불가"
    # 본문 우선. 해시태그의 일본어 이름만으로 혼합으로 올리지 않는다.
    if bj >= 12 and bk <= 8 and bk <= bj * 0.45:
        return "다른 언어 중심"
    if bk >= 8 and bj >= 12:
        return "혼합"
    if bk >= 8 and bj < 12:
        # 본문 라틴 문장이 길면 혼합. 이름·해시태그 영문은 제외하려고 본문만 본다.
        latin_words = re.findall(r"[A-Za-z]{4,}", body)
        if len(latin_words) >= 8 and bk < 20:
            return "혼합"
        return "한국어 중심"
    if bj >= 8 and bk < 8:
        return "다른 언어 중심"
    if bk >= 4 and bk >= bj:
        return "한국어 중심"
    if ja > ko and ja >= 6:
        return "다른 언어 중심"
    if ko >= 4:
        return "한국어 중심"
    return "판단 불가"


def domestic_context(masked: str, language: str) -> tuple[str, str]:
    if DOMESTIC_RE.search(masked):
        return "명시적 단서 있음", ""
    if language in {"다른 언어 중심", "판단 불가"}:
        return "판단 불가", "한국어가 아닌 본문은 번역하지 않았다. 국내 단서가 없다고 확정하지 않는다."
    if language == "혼합" and script_counts(strip_hashtags_for_count(masked)[0])[1] >= 12:
        return "판단 불가", "한국어 구간에서 국내 단서가 없고, 다른 언어 구간은 번역하지 않았다."
    return "명시적 단서 없음", ""


def negated(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - 8):match_start]
    return bool(NEGATOR_RE.search(window))


def is_promo_clause(clause: str) -> bool:
    return bool(PROMO_RE.search(clause) or GIFT_PROMO_RE.search(clause))


def is_trade_clause(clause: str) -> bool:
    return bool(TRADE_RE.search(clause))


def speaker_for(clause: str, anchor: int | None = None) -> str:
    # 구절 전체가 아니라 표현 근처만 본다. 멀리 있는 특전·입고 안내가 작성자 반응을 홍보로 바꾸지 않게 한다.
    if anchor is None:
        window = clause
    else:
        window = clause[max(0, anchor - 45): min(len(clause), anchor + 45)]
    if IMAGINE_RE.search(window):
        return "작성자"
    if PROMO_RE.search(window) or GIFT_PROMO_RE.search(window):
        return "홍보 문구"
    if TRADE_RE.search(window) and POS_EVAL_RE.search(window):
        return "홍보 문구"
    if OTHER_PERSON_RE.search(window):
        return "인용된 타인"
    if QUOTE_SAY_RE.search(window) and not POS_EVAL_RE.search(window):
        return "작중 캐릭터"
    return "작성자"


def product_forms(clause: str) -> list[str]:
    forms = []
    for name, rx in FORM_RES:
        if not rx.search(clause):
            continue
        if name == "식품":
            merch = any(r.search(clause) for n, r in FORM_RES if n in {"인형", "마스코트", "피규어", "키링"})
            if merch and not EAT_RE.search(clause):
                continue
        if name == "의류" and re.search(r"옷\s*입", clause) and not re.search(r"티셔츠|후드|파자마|양말|의류|굿즈", clause):
            # 작중 의상은 상품 형태가 아니다.
            continue
        if name == "기타 상품" and len(forms) > 0:
            continue
        forms.append(name)
    # 굿즈·상품만 있고 구체 형태가 없으면 기타로 남긴다.
    return forms


def channels(clause: str) -> list[str]:
    return [name for name, rx in CHANNEL_RES if rx.search(clause)]


def contents(clause: str) -> list[str]:
    return [name for name, rx in CONTENT_RES if rx.search(clause)]


def functions(clause: str) -> list[str]:
    return [name for name, rx in FUNCTION_RES if rx.search(clause)]


def target_from_names(names: list[str], clause: str, forms: list[str]) -> tuple[str, str]:
    if VA_RE.search(clause):
        return "성우", "성우·연예인 등 다른 대상"
    if forms and (POS_EVAL_RE.search(clause) or HUMOR_RE.search(clause) or "샀" in clause or "구매" in clause):
        who = ",".join(names[:3]) if names else "언급 없음"
        return (who + " 상품") if who != "언급 없음" else "상품", "상품"
    if len(names) >= 2 or REL_RE.search(clause):
        return ",".join(names[:4]), "관계·장면"
    if names:
        if "먼작귀" in names and WORK_CUE_RE.search(clause):
            return "먼작귀", "작품"
        if names == ["치이카와"] and WORK_CUE_RE.search(clause):
            return "치이카와", "작품"
        if names == ["치이카와"] and not CHARACTER_CUE_WORDS.search(clause) and not ACTION_VERB_RE.search(clause):
            return "치이카와", "이름·작품 구분 불가"
        return ",".join(names[:4]), "개별 캐릭터"
    if "가격" in clause or re.search(r"비싸|원|엔", clause):
        return "가격·구매", "가격·구매 과정"
    return "언급 없음", "언급 없음"


def aspect_labels(clause: str, forms: list[str]) -> list[str]:
    labels = []
    texture = bool(TEXTURE_RE.search(clause) or PRODUCT_QUALITY_RE.search(clause))
    if forms and texture:
        labels.append("상품의 디자인·재질·품질·기능")
    appear = bool(APPEAR_RE.search(clause) or EYE_FORM_RE.search(clause))
    if appear and not (forms and texture and not APPEAR_RE.search(clause)):
        labels.append("외형")
    if PERSONALITY_RE.search(clause):
        labels.append("행동·말투·성격")
    elif ACTION_VERB_RE.search(clause) and not re.search(r"싶", clause[max(0, ACTION_VERB_RE.search(clause).start()):ACTION_VERB_RE.search(clause).end() + 3] if ACTION_VERB_RE.search(clause) else ""):
        labels.append("행동·말투·성격")
    if REL_RE.search(clause) or (len(find_names(clause)) >= 2 and ACTION_VERB_RE.search(clause)):
        labels.append("관계·조합·이야기·장면")
    if HUMOR_RE.search(clause):
        labels.append("유머")
    if COMFORT_RE.search(clause):
        labels.append("위로·공감·일상과의 연결")
    # 귀엽다·좋다·최고만 있으면 세부 이유를 만들지 않는다.
    return list(dict.fromkeys(labels))


def reason_content(left: str) -> str:
    forms = product_forms(left)
    aspects = aspect_labels(left, forms)
    if "상품의 디자인·재질·품질·기능" in aspects:
        return "재질·품질·기능"
    if re.search(r"표정|포즈|의상|옷", left):
        return "표정·의상·포즈"
    if "외형" in aspects:
        return "외형"
    if "행동·말투·성격" in aspects or "관계·조합·이야기·장면" in aspects:
        return "행동·관계·장면"
    if "유머" in aspects:
        return "유머"
    if "위로·공감·일상과의 연결" in aspects:
        return "위로·공감"
    if re.search(r"비싸|싸서|저렴|가성비|가격", left):
        return "가격·조건"
    if re.search(r"품절|없", left):
        return "재고·부재"
    if POS_EVAL_RE.search(left) or HUMOR_RE.search(left):
        return "호감 표현만 제시(세부 특징 불명)"
    if find_names(left, strong_only=False) and re.search(r"최애|좋아|때문|골라", left) and len(left) <= 40:
        return "선호 대상으로 이름을 밝힘"
    return "기타 명시"


def commerce_false(clause: str, start: int, end: int) -> str | None:
    frag = clause[max(0, start - 6):min(len(clause), end + 6)]
    if "샀을" in frag or "삿포" in frag:
        return "샀을·삿포로는 구매 완료가 아니다"
    if TEMPLATE_PAY_RE.search(clause):
        return "안내 문안의 구매·결제 단어"
    if STORY_DRAW_RE.search(clause) and "뽑" in frag:
        return "작중 풀뽑기"
    if RAFFLE_RE.search(clause) and "뽑" in frag:
        return "추첨 이벤트"
    if IMAGINE_RE.search(clause):
        return "꿈·상상"
    return None


def add_ev(bucket: list[Ev], **kwargs) -> None:
    bucket.append(Ev(**kwargs))


def analyze_clause(clause: str, cstart: int, original: str, cid: int, post_has_strong: bool) -> list[Ev]:
    out: list[Ev] = []
    if not clause.strip():
        return out
    qs, qe, quote = exact_span(original, cstart, cstart + len(clause))
    if not quote.strip():
        return out
    names_map = find_names(clause) if post_has_strong else find_names(clause, strong_only=True)
    # 강한 단서가 게시물에 있으면 모호 이름도 포함한다. 절 단위가 아니라 게시물 단위 단서다.
    if post_has_strong:
        names_map = find_names(clause, strong_only=False)
    names = list(names_map)
    forms = product_forms(clause)
    chans = channels(clause)
    conts = contents(clause)
    speaker = "작성자"
    about = "예" if (post_has_strong or names) else "아니오"
    if names == [] and not has_strong(clause) and OTHER_FRANCHISE_RE.search(clause):
        about = "아니오"
    tgt, tgt_type = target_from_names(names, clause, forms)

    for form in forms:
        add_ev(
            out, axis="상품형태", label=form, quote=quote, quote_start=qs, quote_end=qe,
            target=form, target_type="상품", speaker="해당없음", about_ip=about,
            clause_id=cid, judgment_note="형태 단어가 구절에 있다. 선택 이유는 아니다.",
        )
    for ch in chans:
        note = "판매·획득 방식 단어다. 물건 형태가 아니다."
        if ch == "공동구매" and GROUP_OPEN_RE.search(clause) and not GROUP_JOIN_RE.search(clause):
            note += " 모집·폼 안내로 보인다. 참여 경험이 아니다."
        add_ev(
            out, axis="판매획득방식", label=ch, quote=quote, quote_start=qs, quote_end=qe,
            target=ch, target_type="판매·획득 방식", speaker=speaker, about_ip=about,
            clause_id=cid, judgment_note=note,
        )
    for ct in conts:
        add_ev(
            out, axis="콘텐츠행사", label=ct, quote=quote, quote_start=qs, quote_end=qe,
            target=ct, target_type="콘텐츠·행사", speaker="해당없음", about_ip=about,
            clause_id=cid, judgment_note="콘텐츠·행사 단어다. 상품 형태 순위에 넣지 않는다.",
        )

    # 호감
    pos_m = POS_EVAL_RE.search(clause)
    neg_m = NEG_EVAL_RE.search(clause)
    humor_m = HUMOR_RE.search(clause)
    va_praise = bool(VA_RE.search(clause) and re.search(r"잘하|잘함|대단|멋지", clause))
    if pos_m or neg_m or humor_m or va_praise:
        aspects = aspect_labels(clause, forms)
        if va_praise and "행동·말투·성격" not in aspects:
            aspects.append("기타 구체적 이유")
        if not aspects:
            aspects = ["호감은 있으나 세부 이유 불명확"]
        emotion = "긍정"
        if pos_m and negated(clause, pos_m.start()):
            emotion = "부정"
        if neg_m and emotion == "긍정":
            emotion = "부정"
        if (pos_m and emotion == "긍정") and neg_m:
            emotion = "복합"
        if humor_m and emotion == "부정":
            emotion = "복합"
        elif humor_m and not pos_m and not neg_m:
            emotion = "긍정"
        # 가격 불만은 캐릭터 비호감으로 옮기지 않는다.
        if emotion == "부정" and re.search(r"비싸|가격|돈", clause) and not re.search(r"싫|별로|못생겼", clause):
            tgt, tgt_type = "가격·구매", "가격·구매 과정"
        if VA_RE.search(clause):
            tgt, tgt_type = "성우", "성우·연예인 등 다른 대상"
        anchor = pos_m.start() if pos_m else humor_m.start() if humor_m else neg_m.start() if neg_m else 0
        spk = speaker_for(clause, anchor)
        if spk == "홍보 문구":
            note = "판매·안내·거래 문안의 평가다. 개인 호감 집계에서 뺀다."
        elif spk == "인용된 타인":
            note = "다른 사람의 말로 보인다."
        else:
            note = "평가 단어가 있다. 귀엽다만으로 외형으로 올리지 않는다."
            if "호감은 있으나 세부 이유 불명확" in aspects:
                note += " 같은 구절에 부위·행동·관계·재질 단어가 없다."
        for aspect in aspects:
            add_ev(
                out, axis="호감", label=aspect, quote=quote, quote_start=qs, quote_end=qe,
                target=tgt, target_type=tgt_type, speaker=spk, emotion=emotion, aspect=aspect,
                about_ip=about, clause_id=cid, judgment_note=note, certainty="확정",
            )

    # 행동. 동사 근처의 안내 문안만 홍보로 본다.
    action_anchor = None
    for rx in (BUY_DONE_RE, BUY_NONE_RE, BUY_WISH_RE, GET_RE, GROUP_JOIN_RE, OWN_WISH_RE, VISIT_RE):
        found_act = rx.search(clause)
        if found_act:
            action_anchor = found_act.start()
            break
    speaker = speaker_for(clause, action_anchor)
    actions = extract_actions(clause, speaker)
    for act in actions:
        false = commerce_false(clause, 0, len(clause)) if act["action_type"] in {"구매", "획득"} else None
        certainty = "확정"
        note = act["note"]
        status = act["status"]
        spk = speaker
        if false:
            certainty = "확인 필요"
            note += " " + false
            if false.startswith("꿈"):
                status = "판단 불가"
            if false.startswith("안내"):
                spk = "홍보 문구"
                certainty = "확정"
                status = "해당없음"
                act["action_type"] = "판매"
                note += " 작성자 구매가 아니다."
        if spk == "인용된 타인":
            certainty = "확인 필요"
            note += " 작성자 행동으로 집계하지 않는다."
        if spk == "홍보 문구" and act["action_type"] == "구매":
            certainty = "확인 필요"
            note += " 홍보 문안 안의 구매 동사다."
        add_ev(
            out, axis="행동", label=f"{act['action_type']}:{status}", quote=quote,
            quote_start=qs, quote_end=qe, target=tgt, target_type=tgt_type, speaker=spk,
            action_type=act["action_type"], action_status=status, acquisition=act["acquisition"],
            about_ip=about, clause_id=cid, certainty=certainty, judgment_note=note,
        )

    # 사용
    for mode, rx in USE_RES:
        m = rx.search(clause)
        if not m:
            continue
        if speaker == "홍보 문구" or GIFT_PROMO_RE.search(clause):
            spk = "홍보 문구"
            note = "안내·증정 문안이다. 작성자 사용 경험이 아니다."
        else:
            spk = "작성자"
            note = "사용·소장 표현이다. 단순 보유는 실사용이 아니다."
        status = "희망" if USE_WISH_RE.search(clause) and mode not in {"선물 수령"} else "완료·경험"
        if mode == "단순 보유":
            note += " 보유만으로 실사용을 만들지 않는다."
        add_ev(
            out, axis="사용", label=mode, quote=quote, quote_start=qs, quote_end=qe,
            target=tgt if forms else "상품", target_type="상품", speaker=spk,
            use_mode=mode, use_status=status, about_ip=about, clause_id=cid,
            judgment_note=note, certainty="확정" if spk == "작성자" else "확정",
        )

    # 수집. 이름이 여러 개이거나 '한정'만으로는 만들지 않는다.
    for label, rx in COLLECT_RES:
        if rx.search(clause) and speaker != "홍보 문구":
            add_ev(
                out, axis="수집", label=label, quote=quote, quote_start=qs, quote_end=qe,
                target=tgt, target_type=tgt_type if tgt_type != "언급 없음" else "상품",
                speaker=speaker, collection_type=label, about_ip=about, clause_id=cid,
                judgment_note="수집·추가 소유의 표현이 있다. 한정이라는 단어만으로는 만들지 않는다.",
            )

    # 콘텐츠 이용
    if WATCH_DONE_RE.search(clause):
        add_ev(out, axis="콘텐츠이용", label="시청", quote=quote, quote_start=qs, quote_end=qe,
               target="작품", target_type="작품", speaker=speaker, content_use="시청",
               action_type="시청", action_status="완료·경험", about_ip=about, clause_id=cid,
               judgment_note="이 글에서 시청을 말했다.")
    if WATCH_WISH_RE.search(clause):
        add_ev(out, axis="콘텐츠이용", label="시청 희망", quote=quote, quote_start=qs, quote_end=qe,
               target="작품", target_type="작품", speaker=speaker, content_use="시청 희망",
               action_type="시청", action_status="희망", about_ip=about, clause_id=cid,
               judgment_note="시청 희망이다. 시청 경험으로 올리지 않는다.")
    if REWATCH_RE.search(clause):
        add_ev(out, axis="콘텐츠이용", label="다시 보기", quote=quote, quote_start=qs, quote_end=qe,
               target="작품", target_type="작품", speaker=speaker, content_use="다시 보기",
               action_type="시청", action_status="완료·경험", about_ip=about, clause_id=cid,
               judgment_note="이 글에서 반복 시청을 말했다. 다른 글의 같은 대사로 추정하지 않는다.")
    if ACTION_VERB_RE.search(clause) and names and speaker != "홍보 문구":
        add_ev(out, axis="콘텐츠이용", label="장면·대사 인용", quote=quote, quote_start=qs, quote_end=qe,
               target=tgt, target_type="관계·장면" if len(names) >= 2 else tgt_type,
               speaker="작성자", content_use="장면·대사 인용", about_ip=about, clause_id=cid,
               judgment_note="장면을 서술했다. 시청 완료나 반복 소비로 올리지 않는다.")
    if COMFORT_RE.search(clause) and re.search(r"나|저|우리집|회사|시험|현실", clause):
        add_ev(out, axis="콘텐츠이용", label="일상 비유", quote=quote, quote_start=qs, quote_end=qe,
               target=tgt, target_type=tgt_type, speaker=speaker, content_use="일상 비유",
               about_ip=about, clause_id=cid, judgment_note="자기 일상과 겹친다고 말했다.")
    if RECO_RE.search(clause) and speaker != "홍보 문구":
        add_ev(out, axis="콘텐츠이용", label="공유·추천", quote=quote, quote_start=qs, quote_end=qe,
               target=tgt, target_type=tgt_type, speaker="작성자", content_use="공유·추천",
               action_type="추천", action_status="완료·경험", about_ip=about, clause_id=cid,
               judgment_note="추천 표현이 있다. 추천 의향만 있는 문장과 구분한다.")
    if SHARE_RE.search(clause) and speaker != "홍보 문구":
        add_ev(out, axis="콘텐츠이용", label="공유", quote=quote, quote_start=qs, quote_end=qe,
               speaker="작성자", content_use="공유·추천", action_type="추천", action_status="완료·경험",
               about_ip=about, clause_id=cid, target=tgt, target_type=tgt_type,
               judgment_note="공유한다고 말했다.")
    if FAN_RE.search(clause):
        add_ev(out, axis="콘텐츠이용", label="팬 창작 경험", quote=quote, quote_start=qs, quote_end=qe,
               speaker="작성자", content_use="팬 창작·번역·패러디", action_type="제작",
               action_status="완료·경험", about_ip=about, clause_id=cid, target=tgt, target_type=tgt_type,
               judgment_note="만들거나 번역한 경험이다.")
    if FAN_WISH_RE.search(clause):
        add_ev(out, axis="콘텐츠이용", label="제작 희망", quote=quote, quote_start=qs, quote_end=qe,
               speaker=speaker, content_use="제작 희망", action_type="제작", action_status="희망",
               about_ip=about, clause_id=cid, target=tgt, target_type=tgt_type,
               judgment_note="만들어 달라는 희망이다. 제작 경험이 아니다.")

    # 장벽·미충족
    for btype, rx in BARRIER_RES:
        if not rx.search(clause):
            continue
        if speaker == "홍보 문구" and btype in {"품절·재고", "원하는 대상 부재"}:
            role = "판매 문안"
            spk = "홍보 문구"
            note = "품절·한정 안내다. 작성자가 구매를 포기한 원인으로 세지 않는다."
        elif BLOCK_RE.search(clause):
            role = "행동 장벽"
            spk = speaker
            note = "사지 못하거나 포기했다고 말한 구절과 같이 있다."
        elif WANT_GAP_RE.search(clause):
            role = "원하는 개선"
            spk = speaker
            note = "나오거나 만들어지기를 바랐다. 포기로 세지 않는다."
        else:
            role = "일반 언급"
            spk = speaker
            note = "단어가 있다. 그것만으로 구매 포기의 원인으로 세지 않는다."
        add_ev(
            out, axis="장벽", label=btype, quote=quote, quote_start=qs, quote_end=qe,
            target=tgt, target_type="가격·구매 과정" if btype == "가격·예산" else tgt_type,
            speaker=spk, barrier_type=btype, barrier_role=role, about_ip=about, clause_id=cid,
            judgment_note=note, certainty="확정" if role != "판매 문안" else "확정",
        )

    # 명시적 이유. 지만·는데 앞부분은 이유로 쓰지 않는다.
    for m in REASON_SPLIT_RE.finditer(clause):
        left, right = m.group("left"), m.group("right")
        conn = m.group(0)[len(left):len(m.group(0)) - len(right)]
        left_core = re.split(r"지만|는데|ㄴ데", left)[-1].strip()
        # 비싸서·예뻐서·웃겨서·귀여워서의 앞 음절은 어간의 일부다.
        if conn in {"싸서", "뻐서", "겨서", "워서"}:
            left_core = (left_core + conn[0]).strip()
        if len(left_core) < 2:
            continue
        content = reason_content(left_core)
        if content == "기타 명시" and not POS_EVAL_RE.search(left_core) and not PRODUCT_QUALITY_RE.search(left_core):
            # 니까·해서만으로는 이유를 확정하지 않는다. 때문·길래이고 왼쪽이 비어 있지 않을 때만 남긴다.
            if not re.search(r"때문|길래", m.group(0)):
                continue
        right_actions = extract_actions(right, speaker)
        rs, re_, rq = exact_span(original, cstart + m.start(), cstart + m.end())
        if right_actions and speaker == "작성자":
            act = right_actions[0]
            choosing = act["status"] in {"완료·경험", "희망", "고민"}
            blocking = act["status"] in {"미수행", "포기", "실패"} and content in {"가격·조건", "재고·부재"}
            sel = content if choosing and act["action_type"] in {"구매", "획득", "소유"} else "해당없음"
            add_ev(
                out, axis="명시이유", label=content, quote=rq, quote_start=rs, quote_end=re_,
                target=tgt, target_type=tgt_type, speaker="작성자",
                action_type=act["action_type"], action_status=act["status"],
                acquisition=act["acquisition"], selection_reason=sel, aspect=content,
                barrier_type=("가격·예산" if content == "가격·조건" and blocking else "품절·재고" if content == "재고·부재" and blocking else "해당없음"),
                barrier_role=("행동 장벽" if blocking else "해당없음"),
                about_ip=about, clause_id=cid, certainty="확정",
                judgment_note="연결어 앞을 이유, 뒤를 행동으로 봤다. 지만·는데 앞은 잘라 냈다.",
            )
        elif (POS_EVAL_RE.search(right) or HUMOR_RE.search(right)) and speaker == "작성자":
            add_ev(
                out, axis="명시이유", label=content, quote=rq, quote_start=rs, quote_end=re_,
                target=tgt, target_type=tgt_type, speaker="작성자", emotion="긍정",
                aspect=content, selection_reason="해당없음", about_ip=about, clause_id=cid,
                judgment_note="특징 때문에 호감이 든다고 말했다. 구매 선택 이유는 아니다.",
            )
    return out


def extract_actions(clause: str, speaker: str) -> list[dict]:
    found = []
    acq = "불명확"
    if re.search(r"가챠|랜덤|뽑", clause) and not STORY_DRAW_RE.search(clause):
        acq = "뽑기"
    elif GROUP_JOIN_RE.search(clause):
        acq = "공동구매 참여"
    elif re.search(r"선물(?:로)?\s*받", clause):
        acq = "선물"
    elif re.search(r"나눔\s*받|무료\s*나눔", clause):
        acq = "나눔"
    elif re.search(r"교환했|교환으로\s*받", clause):
        acq = "교환"
    elif BUY_DONE_RE.search(clause) or BUY_WISH_RE.search(clause):
        acq = "직접 구매"

    if BUY_FEW_RE.search(clause):
        found.append(dict(action_type="구매", status="완료·경험", acquisition=acq if acq != "불명확" else "직접 구매",
                          note="몇 개 안 샀다는 소량 구매다. 아예 안 샀다가 아니다."))
    elif BUY_GIVEUP_RE.search(clause) and re.search(r"사|구매|품절|비싸", clause):
        found.append(dict(action_type="구매", status="포기", acquisition=acq, note="포기를 말했다."))
    elif BUY_NONE_RE.search(clause):
        found.append(dict(action_type="구매", status="미수행", acquisition=acq, note="사지 않았다고 말했다. 구매 완료가 아니다."))
    else:
        m = BUY_DONE_RE.search(clause)
        if m and not negated(clause, m.start()) and "샀을" not in clause[m.start():m.end() + 2]:
            found.append(dict(action_type="구매", status="완료·경험", acquisition="직접 구매" if acq == "불명확" else acq,
                              note="작성자의 구매 완료 동사다. 겟·데려오다·살까·갖고 싶다와 구분한다."))
        if BUY_WISH_RE.search(clause):
            found.append(dict(action_type="구매", status="희망", acquisition="직접 구매", note="구매 희망이다. 소장 희망과 구분한다."))
        if BUY_THINK_RE.search(clause):
            found.append(dict(action_type="구매", status="고민", acquisition="직접 구매", note="구매 고민이다. 구매 희망 합계에 넣지 않는다."))
    if OWN_WISH_RE.search(clause):
        found.append(dict(action_type="소유", status="희망", acquisition="불명확", note="소장 희망이다. 사고 싶다와 구분한다."))
    if GET_RE.search(clause):
        found.append(dict(action_type="획득", status="완료·경험", acquisition=acq, note="겟·득템은 획득이다. 결제 완료로 올리지 않는다."))
    if BRING_RE.search(clause):
        found.append(dict(action_type="획득", status="판단 불가", acquisition="불명확", note="데려오다는 비유일 수 있어 확정 구매가 아니다."))
    if DRAW_GOODS_RE.search(clause) and not STORY_DRAW_RE.search(clause) and not RAFFLE_RE.search(clause):
        found.append(dict(action_type="획득", status="완료·경험", acquisition="뽑기", note="상품 뽑기다. 작중 풀뽑기와 추첨과 구분한다."))
    if GROUP_JOIN_RE.search(clause):
        found.append(dict(action_type="구매", status="완료·경험", acquisition="공동구매 참여", note="공구 참여·탑승이다. 모집 글이 아니다."))
    if VISIT_RE.search(clause):
        found.append(dict(action_type="방문", status="완료·경험", acquisition="불명확", note="장소 방문이다."))
    if re.search(r"교환합니다|교환해요", clause):
        found.append(dict(action_type="교환", status="희망", acquisition="교환", note="교환 제안이다. 교환 완료가 아니다."))
    elif re.search(r"교환했", clause):
        found.append(dict(action_type="교환", status="완료·경험", acquisition="교환", note="교환했다고 말했다."))
    if TRADE_RE.search(clause) and re.search(r"팝니다|판매합니다|양도|급처", clause):
        found.append(dict(action_type="판매", status="희망", acquisition="불명확", note="개인 거래 문안이다. 작성자 구매가 아니다."))
    # 중복 제거
    uniq = []
    seen = set()
    for item in found:
        key = (item["action_type"], item["status"], item["acquisition"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def first_interest(original: str, masked: str, post_has_strong: bool) -> list[Ev]:
    if not FIRST_RE.search(masked) or CARD_ENTRY_RE.search(masked):
        # 카드 입문 상품 안내는 팬 유입이 아니다. 다른 회고 단서가 있으면 아래가 잡는다.
        if not re.search(r"입덕|처음\s*접|첨엔|처음엔|처음에는", masked):
            return []
    if CARD_ENTRY_RE.search(masked) and not re.search(r"입덕|처음\s*접|첨엔|처음엔", masked):
        return []
    out = []
    # 회고가 있는 구절만
    for cid, (a, b, clause) in enumerate(split_clauses(masked)):
        if not FIRST_RE.search(clause) or NOT_FIRST_RE.search(clause):
            continue
        if re.search(r"처음\s*봄|처음\s*봐|처음\s*보|처음\s*봤", clause) and not re.search(r"입덕|접할|첨엔|처음엔|처음에는|알게", clause):
            # 특정 대상을 처음 본 것이지, 작품에 들어온 계기로 단정하지 않는다.
            continue
        qs, qe, quote = exact_span(original, a, b)
        forms = product_forms(clause)
        aspects = aspect_labels(clause, forms)
        labels = []
        if "애니메이션" in contents(clause) or re.search(r"애니", clause):
            labels.append("애니메이션")
        if re.search(r"추천|보여\s*주", clause):
            labels.append("추천·소개")
        if re.search(r"농담곰|다른\s*작품|나가노", clause) and re.search(r"입덕|처음|알", clause):
            labels.append("작가의 다른 작품")
        if forms and re.search(r"보고|보고|사", clause):
            labels.append("상품·굿즈를 봄")
        if "외형" in aspects:
            labels.append("외형")
        elif POS_EVAL_RE.search(clause):
            labels.append("처음 인상 호감(세부 특징 불명)")
        if "위로·공감·일상과의 연결" in aspects or re.search(r"힐링", clause):
            labels.append("위로·힐링으로 밝힌 처음 인상")
        if re.search(r"장면|편|화", clause) and "애니메이션" not in labels:
            labels.append("특정 장면")
        if not labels:
            labels.append("기타 명시")
        for lab in labels:
            add_ev(
                out, axis="관심계기", label=lab, quote=quote, quote_start=qs, quote_end=qe,
                speaker="작성자", about_ip="예" if post_has_strong else "아니오", clause_id=cid,
                judgment_note="처음·입덕·첨엔처럼 시간을 되짚은 표현이 있다. 현재 호감만으로 추정하지 않는다.",
                target="작품·캐릭터", target_type="이름·작품 구분 불가", aspect=lab,
            )
    return out


def purposes(evs: list[Ev], masked: str) -> list[str]:
    labels = []
    author_feel = any(e.axis == "호감" and e.speaker == "작성자" for e in evs)
    author_exp = any(
        e.axis == "행동" and e.speaker == "작성자" and e.certainty == "확정"
        and e.action_status in {"완료·경험", "미수행", "실패"}
        for e in evs
    ) or any(e.axis == "사용" and e.speaker == "작성자" and e.use_status == "완료·경험" for e in evs)
    promo = any(e.speaker == "홍보 문구" for e in evs) or bool(PROMO_RE.search(masked) or GROUP_OPEN_RE.search(masked))
    # 양도·급처·교환은 개인 거래. 판매합니다는 매장 안내가 없을 때만 개인 거래로 둔다.
    trade = bool(re.search(r"양도|급처|반택|교환\s*합니다|교환해요", masked)) or (
        bool(re.search(r"팝니다|판매합니다", masked)) and not promo
    )
    if re.search(r"구합니다|구해요|(?<![가-힣])구함", masked) and "수요조사" not in masked:
        trade = True
    info = bool(re.search(r"소식|공지|번역|보는\s*곳|업로드\s*되니|안내합니다|타래", masked)) and not promo
    fan = any(e.content_use == "팬 창작·번역·패러디" for e in evs) or bool(FAN_RE.search(masked))
    if author_feel:
        labels.append("개인 감상")
    if author_exp:
        labels.append("개인 경험")
    if promo:
        labels.append("판매·홍보")
    if trade:
        labels.append("개인 거래")
    if info:
        labels.append("정보 공유")
    if fan:
        labels.append("팬 창작")
    if not labels:
        labels.append("기타·판단 불가")
    return labels


def judgment_scope(masked: str, original: str, evs: list[Ev]) -> str:
    substantive = any(
        e.axis in {"호감", "행동", "사용", "관심계기", "명시이유", "콘텐츠이용"} and e.certainty == "확정"
        for e in evs
    )
    if substantive:
        return "본문으로 판단 가능"
    ko = len(HANGUL.findall(masked))
    has_media = bool(URL_RE.search(original) or re.search(r"사진|영상|움짤|gif|GIF", original))
    if has_media and ko < 18:
        return "이미지나 영상 확인 필요"
    if ko < 12:
        return "기타 정보 부족"
    return "이미지나 영상 확인 필요" if has_media else "기타 정보 부족"


def relevance(masked: str) -> tuple[str, str]:
    strong = has_strong(masked)
    amb = find_names(masked, strong_only=False)
    amb_only_keys = [k for k in amb if k in {n for n, _ in AMBIGUOUS_NAME_RES}]
    others = other_ips(masked)
    if strong:
        return "관련", "본문에 치이카와·먼작귀 또는 확인된 등장인물 표기가 있다."
    if amb_only_keys and not others:
        return "판단 불가", "우사기·시사·카니·아노코·데카츠요만 있어 작품 단서가 부족하다."
    if others and not strong:
        return "무관", "다른 작품·IP 표기이고 치이카와 단서는 없다."
    if not amb and not others:
        return "무관", "본문에 작품 단서가 없다. 검색 키워드로 관련을 만들지 않는다."
    return "판단 불가", "작품 단서를 확정하지 못했다."


def build_connections(evs: list[Ev]) -> list[dict]:
    conns = []
    # 구절 안
    by_clause: dict[int, list[Ev]] = {}
    for e in evs:
        by_clause.setdefault(e.clause_id, []).append(e)
    for cid, items in by_clause.items():
        reasons = [e for e in items if e.axis == "명시이유" and e.speaker == "작성자"]
        for r in reasons:
            conns.append(dict(
                evidence_local=r,
                target=r.target,
                reason=r.label,
                action_type=r.action_type,
                action_status=r.action_status,
                evidence_level="작성자가 이유 명시",
                speaker=r.speaker,
                quote=r.quote,
                note=r.judgment_note,
            ))
        affections = [e for e in items if e.axis == "호감" and e.speaker == "작성자"]
        actions = [e for e in items if e.axis == "행동" and e.speaker == "작성자" and e.certainty == "확정"]
        forms = [e for e in items if e.axis == "상품형태"]
        # 이유가 이미 있으면 같은 구절의 느슨한 연결은 만들지 않는다.
        if reasons:
            continue
        if affections and actions and (len(forms) <= 1) and (len(actions) <= 2):
            for af in affections:
                for ac in actions:
                    conns.append(dict(
                        evidence_local=af,
                        evidence_local2=ac,
                        target=af.target if af.target != "언급 없음" else ac.target,
                        reason=af.aspect,
                        action_type=ac.action_type,
                        action_status=ac.action_status,
                        evidence_level="문맥상 연결",
                        speaker="작성자",
                        quote=af.quote,
                        note="같은 구절에서 평가와 행동이 확인된다. 이유 연결어는 없다.",
                    ))
        elif forms and actions and len(forms) == 1 and len(actions) == 1 and not affections:
            conns.append(dict(
                evidence_local=forms[0],
                evidence_local2=actions[0],
                target=forms[0].label,
                reason="언급 없음",
                action_type=actions[0].action_type,
                action_status=actions[0].action_status,
                evidence_level="문맥상 연결",
                speaker=actions[0].speaker,
                quote=actions[0].quote,
                note="같은 구절의 상품 형태와 행동이다. 선택 이유를 만들지 않는다.",
            ))
        elif len(forms) > 1 and len(actions) >= 1:
            conns.append(dict(
                evidence_local=actions[0],
                target="복수 상품",
                reason="언급 없음",
                action_type=actions[0].action_type,
                action_status=actions[0].action_status,
                evidence_level="연결 불명확",
                speaker=actions[0].speaker,
                quote=actions[0].quote,
                note="같은 구절에 상품이 여럿이라 어느 상품의 행동인지 묶지 않는다.",
            ))
    # 게시글 공존: 형태 1개, 작성자 확정 행동 1개, 서로 다른 구절, 이미 연결 없음
    forms = [e for e in evs if e.axis == "상품형태"]
    actions = [e for e in evs if e.axis == "행동" and e.speaker == "작성자" and e.certainty == "확정"]
    if len({e.label for e in forms}) == 1 and len(actions) == 1:
        if forms[0].clause_id != actions[0].clause_id and not any(
            c["evidence_level"] in {"문맥상 연결", "작성자가 이유 명시"} and c["action_type"] == actions[0].action_type
            for c in conns
        ):
            conns.append(dict(
                evidence_local=forms[0],
                evidence_local2=actions[0],
                target=forms[0].label,
                reason="언급 없음",
                action_type=actions[0].action_type,
                action_status=actions[0].action_status,
                evidence_level="게시글 내 공존",
                speaker="작성자",
                quote=actions[0].quote,
                note="게시물에 형태와 행동이 하나씩이라 공존만 기록한다. 원인으로 보지 않는다.",
            ))
    return conns


def analyze_post(original: str) -> dict:
    # 인용 오프셋은 읽어 들인 원문 기준이다. CRLF를 지우지 않는다.
    text = original
    masked = mask_keep_len(text)
    at = analysis_text(text)
    lang = language_of(masked)
    dom, dom_note = domestic_context(masked, lang)
    rel, rel_note = relevance(masked)
    post_strong = rel == "관련"
    clauses = split_clauses(masked)
    evs: list[Ev] = []
    for cid, (a, b, clause) in enumerate(clauses):
        evs.extend(analyze_clause(clause, a, text, cid, post_strong))
    evs.extend(first_interest(text, masked, post_strong))
    # 모호 이름만 있는 글의 근거는 작품 밖으로 둔다.
    if rel != "관련":
        for e in evs:
            if e.about_ip == "예" and not post_strong:
                e.about_ip = "아니오"
    conns = build_connections(evs)
    pur = purposes(evs, masked)
    scope = judgment_scope(masked, text, evs)
    speakers = sorted({e.speaker for e in evs if e.speaker not in {"해당없음", ""}})
    if not speakers:
        speakers = ["판단 불가"] if scope != "본문으로 판단 가능" else ["작성자"]
    eval_targets = sorted({e.target_type for e in evs if e.axis == "호감" and e.target_type not in {"언급 없음", "해당없음"}})
    if not eval_targets:
        # 행동 대상이라도 평가 대상이 아니면 비운다.
        eval_targets = ["언급 없음"]
    reviews = []
    if rel == "판단 불가":
        reviews.append("작품 관련성 판단 불가")
    if any(e.certainty == "확인 필요" and e.axis == "행동" for e in evs):
        reviews.append("행동 주체·완료 여부 확인 필요")
    if any(e.extra.get("multi_product") for e in evs):
        reviews.append("복수 상품 연결 확인 필요")
    if any(c["evidence_level"] == "연결 불명확" for c in conns):
        reviews.append("대상-행동 연결 불명확")
    return {
        "analysis_text": at,
        "work_relevance": rel,
        "relevance_note": rel_note,
        "language": lang,
        "domestic_context": dom,
        "domestic_note": dom_note,
        "purpose_labels": pur,
        "purpose_mixed": "예" if len([p for p in pur if p != "기타·판단 불가"]) >= 2 else "아니오",
        "eval_targets": eval_targets,
        "speakers": speakers,
        "judgment_scope": scope,
        "evidence": evs,
        "connections": conns,
        "reviews": reviews,
        "text_lf": text,
    }


def pipe(items) -> str:
    vals = []
    for x in items:
        if x and x not in vals and x not in {"해당없음"}:
            vals.append(x)
    return "|".join(vals) if vals else "언급 없음"


FIXTURES = [
    ("치이카와 너무 귀엽다", "unclear", "no_buy"),
    ("눈이 동그래 보여서 귀엽다", "appear_reason", None),
    ("귀엽긴 하지만 비싸서 안 샀다", "not_done", "price_block"),
    ("삿포로에서 치이카와 팝업을 걸었다", "no_buy", None),
    ("하치와레가 닮았다 하고 샀을 생각에 귀엽다", "no_buy", None),
    ("치이카와 인형을 몇 개 안 샀는데 귀엽다", "few", None),
    ("치이카와 아예 안 샀다", "none", None),
    ("치이카와가 풀뽑기 시험을 준비한다", "no_gacha", None),
    ("하치와레 인형 갖고 싶다", "own", None),
    ("하치와레 인형 사고 싶다", "buywish", None),
    ("랏코 마스코트는 부들부들하고 귀여워", "mascot", None),
    ("치이카와 미니인형 예약 판매합니다 너무 귀여워요", "promo", None),
    ("친구 생겼네 치이카와", "no_rel", None),
    ("오늘 시사하는 뉴스다", "unrelated_or_unclear", None),
    ("치이카와 인형 겟했다", "get", None),
    ("치이카와 신상 공구 폼 업로드됩니다", "recruit", None),
    ("공구 탑승한 치이카와 인형이 왔다", "join", None),
    ("꿈에서 치이카와 인형을 샀다", "dream", None),
    ("파자마 파티즈 너무 좋다", "other", None),
    ("치이카와 처음 접할때 너무 기엽고 힐링물이었다", "first", None),
    ("이렇게 귀여운 쿠리만쥬 처음 봄", "not_first", None),
    ("가격은 4800엔이네요", "no_barrier_author", None),
    ("품절시 재입고 불가합니다", "shop_stock", None),
    ("성우가 너무 잘하심", "va", None),
    ("하치와레 키링을 가방에 달고 다닌다", "bag", None),
    ("귀여워서 하치와레 키링을 샀다", "explicit_buy", None),
    ("나중에 결제완료되지 않은 주문은 취소된다", "no_buy", None),
    ("치이카와 공구 탑승 원하시는 분", "no_join", None),
    ("치이카와 너무 귀여워" + ("요" * 40) + " 특전 클리어파일도 있다", "author_cute", None),
    ("직구 입문하기에 좋은 사이트", "not_first", None),
]


def run_fixtures() -> list[str]:
    errors = []
    for text, kind, _ in FIXTURES:
        r = analyze_post(text)
        evs = r["evidence"]
        def has(axis, label_sub=None, **kw):
            for e in evs:
                if e.axis != axis:
                    continue
                if label_sub and label_sub not in e.label and label_sub not in e.aspect:
                    continue
                ok = True
                for k, v in kw.items():
                    if getattr(e, k) != v:
                        ok = False
                if ok:
                    return True
            return False
        if kind == "unclear":
            if has("호감", "외형", speaker="작성자"):
                errors.append(text + " :: cute became appearance")
            if any(e.action_type == "구매" and e.action_status == "완료·경험" for e in evs):
                errors.append(text + " :: cute became purchase")
        elif kind == "appear_reason":
            if not any(e.axis == "명시이유" and "외형" in e.label for e in evs):
                errors.append(text + " :: missing appearance reason " + str([(e.axis, e.label) for e in evs]))
        elif kind == "not_done":
            if any(e.action_status == "완료·경험" and e.action_type == "구매" for e in evs):
                errors.append(text + " :: blocked buy counted done")
            if not any(e.action_status == "미수행" for e in evs):
                errors.append(text + " :: missing 미수행")
            if not any(e.axis == "명시이유" and e.barrier_role == "행동 장벽" for e in evs):
                errors.append(text + " :: price not linked as barrier " + str([(e.axis, e.label, e.action_status, e.barrier_role) for e in evs]))
            if any(e.selection_reason not in {"해당없음", ""} and e.action_status == "미수행" for e in evs):
                errors.append(text + " :: non-buy stored as selection reason")
        elif kind == "no_buy":
            if any(e.action_type == "구매" and e.action_status == "완료·경험" and e.certainty == "확정" and e.speaker == "작성자" for e in evs):
                errors.append(text + " :: false purchase")
        elif kind == "few":
            if not any(e.action_status == "완료·경험" and e.action_type == "구매" for e in evs):
                errors.append(text + " :: few should be purchase done")
        elif kind == "none":
            if any(e.action_status == "완료·경험" and e.action_type == "구매" for e in evs):
                errors.append(text + " :: none counted done")
            if not any(e.action_status == "미수행" for e in evs):
                errors.append(text + " :: none missing")
        elif kind == "no_gacha":
            if any(e.acquisition == "뽑기" and e.certainty == "확정" for e in evs):
                errors.append(text + " :: story draw became gacha")
        elif kind == "own":
            if not any(e.action_type == "소유" and e.action_status == "희망" for e in evs):
                errors.append(text + " :: own wish missing")
            if any(e.action_type == "구매" for e in evs):
                errors.append(text + " :: own wish became buy")
        elif kind == "buywish":
            if not any(e.action_type == "구매" and e.action_status == "희망" for e in evs):
                errors.append(text + " :: buy wish missing")
        elif kind == "mascot":
            if not any(e.axis == "상품형태" and e.label == "마스코트" for e in evs):
                errors.append(text + " :: mascot missing")
            if any(e.axis == "상품형태" and e.label == "인형" for e in evs):
                errors.append(text + " :: mascot forced to doll")
        elif kind == "promo":
            if any(e.axis == "호감" and e.speaker == "작성자" for e in evs):
                errors.append(text + " :: promo cute as author")
        elif kind == "no_rel":
            if any(e.aspect == "관계·조합·이야기·장면" for e in evs):
                errors.append(text + " :: friend became relationship")
        elif kind == "unrelated_or_unclear":
            if r["work_relevance"] == "관련":
                errors.append(text + " :: news marked related")
        elif kind == "get":
            if any(e.action_type == "구매" and e.action_status == "완료·경험" for e in evs):
                errors.append(text + " :: get became purchase")
            if not any(e.action_type == "획득" for e in evs):
                errors.append(text + " :: get missing")
        elif kind == "recruit":
            if any(e.acquisition == "공동구매 참여" and e.action_status == "완료·경험" for e in evs):
                errors.append(text + " :: recruit became join")
            if "판매·홍보" not in r["purpose_labels"]:
                errors.append(text + " :: recruit purpose " + str(r["purpose_labels"]))
        elif kind == "join":
            if not any(e.acquisition == "공동구매 참여" for e in evs):
                errors.append(text + " :: join missing")
        elif kind == "dream":
            if any(e.action_type == "구매" and e.action_status == "완료·경험" and e.certainty == "확정" for e in evs):
                errors.append(text + " :: dream purchase confirmed")
        elif kind == "other":
            if r["work_relevance"] == "관련":
                errors.append(text + " :: pajama parties marked chiikawa")
        elif kind == "first":
            if not any(e.axis == "관심계기" for e in evs):
                errors.append(text + " :: first interest missing")
        elif kind == "not_first":
            if any(e.axis == "관심계기" for e in evs):
                errors.append(text + " :: first sighting became entry")
        elif kind == "no_barrier_author":
            if any(e.axis == "장벽" and e.barrier_role == "행동 장벽" and e.speaker == "작성자" for e in evs):
                errors.append(text + " :: yen price became barrier")
        elif kind == "shop_stock":
            if any(e.barrier_role == "행동 장벽" and e.speaker == "작성자" for e in evs):
                errors.append(text + " :: shop soldout became author barrier")
        elif kind == "va":
            if any(e.axis == "호감" and e.target_type == "개별 캐릭터" for e in evs):
                errors.append(text + " :: VA became character")
        elif kind == "bag":
            if not any(e.use_mode == "가방 부착" for e in evs):
                errors.append(text + " :: bag use missing")
        elif kind == "no_join":
            if any(e.acquisition == "공동구매 참여" for e in evs):
                errors.append(text + " :: recruit counted as join")
        elif kind == "author_cute":
            if not any(e.axis == "호감" and e.speaker == "작성자" for e in evs):
                errors.append(text + " :: distant promo ate author cute " + str([(e.speaker, e.label) for e in evs if e.axis == "호감"]))
        elif kind == "explicit_buy":
            if not any(e.axis == "명시이유" and e.action_type == "구매" and e.selection_reason not in {"해당없음", ""} for e in evs):
                errors.append(text + " :: explicit buy reason missing " + str([(e.axis, e.label, e.action_type, e.selection_reason) for e in evs]))
            if any(e.axis == "명시이유" and e.label == "외형" for e in evs):
                errors.append(text + " :: cute-because became appearance")
    return errors


if __name__ == "__main__":
    errs = run_fixtures()
    print("fixture_errors", len(errs))
    for e in errs:
        print(" -", e)
