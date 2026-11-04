# -*- coding: utf-8 -*-
"""외형 호감 결과 파일을 만든다.

규칙 후보는 extract_candidates.py가 골랐다.
아래 EV는 그 본문을 읽고 확정한 모델 판단이다. 기존 분석 라벨은 쓰지 않는다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\DATA\KDT_Integral_Data_Project\02_csv\03_x")
OUT = ROOT / "appearance_analysis" / "20261103_105724"
POSTS = ROOT / "normalized" / "x_posts.csv"
CAND = OUT / "working" / "candidates.csv"

# 모델이 본문을 읽고 확정한 근거. quote는 원문의 부분 문자열이어야 한다.
EV = [
    # 얼굴·머리
    dict(post_id="2020171308567601359", feature="얼굴·머리 형태", detail="볼록한 주둥이, 두 가지 옆모습", polarity="긍정",
         quote="개인적으로도 볼록한 주둥이가 더 귀여운듯", target="기본 외형", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="중단 전 보이는 Chrome 창. 첨부 1장",
         image="도안 1장. 옆모습 두 개. 왼쪽은 입이 납작하고 오른쪽은 주둥이가 더 튀어나옴. 제목은 가로 방향이 두 종류.",
         why="작성자가 두 옆모습 중 볼록한 주둥이를 더 귀엽다고 고름. 그림에 둥근 머리가 보여서 둥근 얼굴을 좋아한다고 보지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2108901582838661630", feature="얼굴·머리 형태", detail="주둥이", polarity="긍정",
         quote="수영하는 하치와레 너무 귀여움ㅜㅜ 저 주둥이 좀봐", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 동영상 재생 안 함",
         image="0초 근처 프레임. 하치와레가 물속에서 가로로 떠 있고 주둥이가 앞쪽으로 보임. 꼬리 움직임은 정지 화면으로 확정하지 않음.",
         why="귀엽다는 말과 주둥이를 보라는 말이 같이 있음. 수영은 장면이고 호감 포인트로 짚은 부위는 주둥이.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1877408972023460269", feature="얼굴·머리 형태", detail="옆모습", polarity="긍정",
         quote="갠적으로 랏코 옆모습을 조와해여", target="기본 외형", chars="랏코",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="랏코 옆얼굴 확대. 둥근 머리, 작은 귀, 분홍 볼, 파란 귀가 일부 보임.",
         why="옆모습을 좋아한다고 직접 말함. 다음 줄의 복실한 털은 별도 근거.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1877408972023460269", feature="색상·무늬", detail="복실한 털", polarity="긍정",
         quote="털이 복실복실", target="기본 외형", chars="랏코",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="같은 옆얼굴. 털의 촉감은 그림만으로 확인하지 않음.",
         why="옆모습을 좋아하는 이유로 털이 복실하다고 이어서 말함. 상품 재질이 아니라 생긴 것에 대한 말.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1759765157285404916", feature="얼굴·머리 형태", detail="일자 앞머리", polarity="긍정",
         quote="일자앞머리 하치와레 생각보다 더 귀엽잖아", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 1초 프레임, 재생 안 함",
         image="하치와레 정면. 파란 앞머리가 이마를 일자로 덮음. 눈은 감겨 있음.",
         why="일자 앞머리 상태를 생각보다 더 귀엽다고 함. 같은 계정의 다른 글은 장면 설명이라 이 문장과 합치지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2039621341972979740", feature="얼굴·머리 형태", detail="노란 털공처럼 생긴 형태", polarity="긍정",
         quote="랏코 생긴것도 노란색 털공처럼 부들부들인게", target="기본 외형", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단. 이번 사진 확인 대상 아님",
         image="",
         why="생긴 것을 노란 털공에 비유해 좋게 말함. 같은 문장의 목소리는 외형이 아니라 따로 둠.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1899751571908685985", feature="얼굴·머리 형태", detail="매우 둥근 형태", polarity="긍정",
         quote="사진은 너무 동그란 하치와레 가챠입니다", target="상품 구현", chars="하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="손에 들린 하치와레 인형. 머리가 몸보다 크고 전체 실루엣이 둥글다. 가챠 기계는 안 보임.",
         why="귀엽다는 단어는 없으나 사진의 특징으로 너무 동그랗다고 짚음. 정도 표현으로 읽고 강한 선호 순위로는 쓰지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1958532856785031652", feature="신체 형태·비율", detail="얼굴과 몸의 비율, 귀 크기", polarity="혼합",
         quote="얼굴을 더 크게 만들거나 몸이 더 작아야 베이비같을것같아요", target="팬 창작", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="귀여워서 만들었다고 한 뒤, 지금 비율은 베이비처럼 보이지 않는다고 함. 큰 얼굴·작은 몸을 그 조건으로 말함.",
         behavior="제작 경험", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1910683993890316493", feature="얼굴·머리 형태", detail="인형의 머리 크기", polarity="부정",
         quote="대가리가 왤캐 커", target="상품 구현", chars="하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="머리띠를 쓴 하치와레 인형. 머리가 몸통보다 크게 보임. 사람 얼굴은 없음.",
         why="머리띠는 귀엽다고 한 뒤 인형 머리가 너무 커 테무 제품 같다고 함. 캐릭터 원래 비율이 아니라 받은 인형의 구현.",
         behavior="소유 경험", link="같은 글의 평가", speaker="작성자"),
    dict(post_id="1910683993890316493", feature="의상·소품", detail="인형 머리띠", polarity="긍정",
         quote="미미치 인형머리띠 들어왓길래 귀여워", target="의상·소품", chars="하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="같은 사진의 파란 귀 머리띠.",
         why="머리띠를 보고 귀엽다고 한 말과, 인형 머리가 크다는 불만을 나눔.",
         behavior="사용", link="같은 글의 평가", speaker="작성자"),
    dict(post_id="1959281741073387638", feature="얼굴·머리 형태", detail="인형 머리 실루엣과 털 소재", polarity="부정",
         quote="머리부분이 산 ⛰️ 같다", target="상품 구현", chars="하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 상품 사진 1장",
         image="하치와레 아기 인형. 머리 위가 두 봉우리로 솟아 있음.",
         why="산처럼 생긴 머리보다 가운데 털을 모몽가 꼬리 같은 소재로 만드는 편이 나았을 것이라고 함.",
         behavior="단순 감상", link="원하는 개선", speaker="작성자"),
    dict(post_id="1521657940088070145", feature="얼굴·머리 형태", detail="만두 형태", polarity="긍정",
         quote="만두 치이카와 하치와레 우사기 너무 귀엽다", target="특정 장면", chars="치이카와,하치와레,우사기",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 그림 2장 중 1장이 크게 보임",
         image="1장: 주름 잡힌 만두 머리에 치이카와 얼굴. 2장: 같은 계열 그림의 일부.",
         why="만두로 바뀐 모습을 귀엽다고 하고 만쥬 상품으로 내 달라고 함. 식품을 먹었다는 말은 아님.",
         behavior="제작·출시 희망", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1593962423849222146", feature="얼굴·머리 형태", detail="만두형 인형", polarity="긍정",
         quote="귀엽다 치이카와 만두봐", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="만두처럼 둥근 인형 여러 개와 실제 빵. 화면 속 사람은 외형 판단에 쓰지 않음.",
         why="만두 인형을 보라고 하며 귀엽다고 함. 빵을 맛있다고 한 것은 아님.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1507668678770257920", feature="얼굴·머리 형태", detail="머리에 그린 작은 곰 얼굴", polarity="긍정",
         quote="머리에 그려진 깨알 담곰이 얼굴", target="의상·소품", chars="치이카와,하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 2장",
         image="1장: 곰 후드를 쓴 두 인형과 작은 곰 그림. 2장: 후드 위에 작게 그려진 곰 얼굴.",
         why="후드가 아니라 그 위에 그린 작은 얼굴을 귀엽다고 짚음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1797300694581727443", feature="신체 형태·비율", detail="둥근 엉덩이", polarity="긍정",
         quote="넘 좋다 이 동그란 엉덩이를 봐", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 인용된 GIF 2장",
         image="인용 1: 치이카와 정면 전신. 인용 2: 옆·뒤 실루엣과 분홍 볼. 작성자 첨부가 아니라 인용.",
         why="순하고 말랑하다는 성격 말과 따로, 둥근 엉덩이를 보라고 함. 성격 칭찬을 체형 호감으로 바꾸지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    # 눈
    dict(post_id="1609191102707560449", feature="눈·눈매", detail="지나치게 반짝이는 눈", polarity="부정",
         quote="눈이 너무 반짝 거려", target="기본 외형", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="화면 없는 Chrome. 첨부 없음",
         image="",
         why="처음에는 눈이 너무 반짝이고 찡그려서 별로 안 귀엽다고 함. 나중 구매 욕구는 이 특징 때문이 아니라고 적음.",
         behavior="소장 희망", link="연결하지 않음", speaker="작성자"),
    dict(post_id="1609191102707560449", feature="표정", detail="찡그린 표정", polarity="부정",
         quote="쟤는 왜케 찡그리지", target="기본 외형", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="첨부 없음",
         image="",
         why="찡그림 자체를 덜 귀엽다고 함. 뒤에 하나만 갖고 싶었다고 한 이유는 인기 이후의 마음이라 이 표정과 잇지 않음.",
         behavior="소장 희망", link="연결하지 않음", speaker="작성자"),
    dict(post_id="1719560164460876150", feature="눈·눈매", detail="초롱초롱한 눈", polarity="긍정",
         quote="이거딘쨔귀엽네요 초롱초롱 치이카와", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="4탄을 귀엽다고 하면서 초롱초롱한 치이카와를 짚음. 상품 사진이 어떤 눈인지는 이번엔 열지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1990818793946231187", feature="눈·눈매", detail="초롱한 눈, 순정만화 눈", polarity="긍정",
         quote="초롱 우사기 진짜 순정만화눈이라 드레스류 잘 어울려", target="의상·소품", chars="우사기",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="드레스가 어울리는 이유로 눈 종류를 말함. 옷 자체만 귀엽다는 말과 다름.",
         behavior="구매 경험", link="같은 글의 평가", speaker="작성자"),
    dict(post_id="1996459696027513149", feature="눈·눈매", detail="인형 눈동자 방향", polarity="부정",
         quote="모몽가 눈동자 위아래 반대로 끼워진게 왔네요", target="상품 구현", chars="모몽가",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 2장",
         image="1장: 파란 눈동자. 2장: 검은 눈동자와 다른 눈 위치. 어느 쪽이 정품 기준인지는 단정하지 않음.",
         why="캐릭터 눈이 싫다는 말이 아니라 조립이 반대로 온 상품 불만.",
         behavior="수령 경험", link="작성자가 이유를 설명", speaker="작성자"),
    # 볼
    dict(post_id="1568057505842102273", feature="입·볼", detail="볼살", polarity="긍정",
         quote="치이카와 볼살 실화?", target="특정 장면", chars="치이카와,하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="기존 Chrome 캡처 PNG를 다시 봄. 재생 안 함",
         image="이불 속 치이카와와 하치와레. 둘 다 분홍 볼. 0:00 프레임.",
         why="귀엽다는 단어 없이 볼살이 실화냐며 놀람. 둥근 얼굴 전체를 좋아한다고 확장하지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1568559174396805121", feature="입·볼", detail="볼살", polarity="긍정",
         quote="볼살대회 치이카와 압승일 수도", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 그림 2장",
         image="1장: 볼이 도드라진 치이카와. 2장: 하치와레 일부.",
         why="대회에서 치이카와가 이길 수도 있다는 농담. 볼살을 비교 대상으로 봄.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2089617238383051149", feature="입·볼", detail="눌리는 볼살", polarity="긍정",
         quote="푹하면서 볼살눌리는게 개처귀여움", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="기존 Chrome 캡처 PNG를 다시 봄. 재생 안 함",
         image="얼굴이 눌린 치이카와. 볼에 음영, 눈이 일그러짐. 들어 올리는 손은 이 프레임에 없음.",
         why="몸이 말랑해 볼이 눌리는 장면을 귀엽다고 함. 말랑함은 상품 촉감이 아니라 장면의 작화.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1651983324230090753", feature="입·볼", detail="하트 모양이라고 한 볼터치", polarity="긍정",
         quote="치이카와 볼터치가 하트모양이야", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="흰색 인형의 볼은 세로 분홍 선으로 보임. 하트 형태는 이 장에서 확인되지 않음.",
         why="작성자는 하트 볼터치를 깜찍하다고 함. 사진이 다르게 보여도 선호 이유를 사진 속 선으로 바꾸지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2095779596545442160", feature="입·볼", detail="볼", polarity="긍정",
         quote="볼따구 어떡할거야", target="특정 장면", chars="우사기",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 장면 1장",
         image="누운 우사기. 볼에 분홍 선, 혀가 보임.",
         why="말랑한 아기 토끼라는 말과 볼을 어쩌냐는 말이 같이 있음. 누운 자세 전체를 볼 호감으로 바꾸지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2107782470808826265", feature="입·볼", detail="볼을 누르는 소리", polarity="긍정",
         quote="하치와레 말랑말랑 쫀득쫀득 볼따구 소리", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 동영상 재생 안 함",
         image="하치와레가 볼 쪽에 손을 댐. 소리는 듣지 않음.",
         why="볼의 말랑한 소리를 들어 보라고 함. 인형 재질 후기가 아니라 영상 장면.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1599047909324247041", feature="입·볼", detail="볼터치", polarity="긍정",
         quote="볼터치도 예쁘고", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="산타 치이카와의 볼터치가 예쁘다고 함. 부들부들함은 재질 근거로 분리.",
         behavior="구매 경험", link="같은 글에 공존", speaker="작성자"),
    dict(post_id="1599047909324247041", feature="상품 재질·마감", detail="부들부들한 촉감", polarity="긍정",
         quote="엄청 부들부들 해", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="인형의 촉감. 캐릭터 작화의 말랑함으로 옮기지 않음. 후회 없는 소비는 이유 연결어 없이 뒤에 있음.",
         behavior="구매 경험", link="같은 글에 공존", speaker="작성자"),
    # 신체
    dict(post_id="1560849222798151680", feature="신체 형태·비율", detail="짧은 팔다리", polarity="긍정",
         quote="저 짧은 팔다리로 야무지게 춤추는데 이렇게까지 귀여울 일임", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="기존 Chrome 캡처 PNG를 다시 봄. 재생 안 함",
         image="2:19 프레임은 눈 감고 웃는 치이카와. 팔은 짧아 보이나 춤 동작은 이 프레임에 없음.",
         why="짧은 팔다리와 그 몸으로 추는 춤을 같이 귀엽다고 함. 형태만의 호감으로 줄이지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2090813740510023857", feature="자세·실루엣", detail="걸어가는 뒷모습, 통실한 몸", polarity="긍정",
         quote="걸어가는 뒷모습이 통실통실해서 커여워", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 0:00은 카메라뿐",
         image="재생 전 화면은 벽의 카메라. 하치와레 뒷모습은 보이지 않음.",
         why="본문이 뒷모습과 통실함을 이유로 듦. 썸네일이 그 몸을 보여 주지 않아도 문장 판단은 유지.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1697619073587454385", feature="자세·실루엣", detail="앉은 자세", polarity="긍정",
         quote="앉은 치이카와 생각보다 진짜 진 짜 귀여움", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 2장",
         image="1장: 선반 위 작은 앉은 치이카와 피규어. 2장: 버섯 모양 과자. 2장은 본문의 앉은 치이카와로 보지 않음.",
         why="앉은 형태를 생각보다 귀엽다고 함. 사진에 물건이 있어도 구매 완료로 쓰지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2091425273355149615", feature="상품 재질·마감", detail="만지면 보들하고 파우더 같을 것이라는 상상", polarity="긍정",
         quote="치이카와 만지면 엄청 보들하고 겉에 파우더 묻힌거처럼", target="기본 외형", chars="치이카와",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 재생 안 함",
         image="사탕을 든 치이카와. 손의 촉감은 화면에 없음.",
         why="상품을 만진 후기가 아니라 캐릭터를 만지면 이럴 것이라는 상상. 인형 재질 평가로 옮기지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    # 표정
    dict(post_id="1519817339356598273", feature="표정", detail="미소", polarity="긍정",
         quote="하치와레 미소 어떻게할꺼야", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="애니의 미소를 귀엽다고 함. 울고 싶다는 말은 작성자 반응.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1548260243435843584", feature="표정", detail="시무룩", polarity="긍정",
         quote="시무룩 치이카와 기여워", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="확인 실패", photo_how="화면 없는 Chrome. 현재 화면에 첨부 없음",
         image="",
         why="그 사진을 고른 이유로 시무룩함을 말함. 지금 화면에서는 그 표정을 보지 못함.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1535067039521738753", feature="표정", detail="표정 변화", polarity="긍정",
         quote="하치와레 표정 변화 왜 이리 좋지", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="화면 없는 Chrome. 2초 프레임, 재생 안 함",
         image="입을 벌린 얼굴 한 장. 변화 과정은 보이지 않음.",
         why="변화 자체를 좋다고 함. 한 프레임의 입을 그 이유로 대체하지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1571131866656407554", feature="표정", detail="인형의 표정, 종류는 미명시", polarity="긍정",
         quote="이 인형 표정이 너무 취향으로 귀여워서", target="상품 구현", chars="구분 어려움",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="베이지색 작은 인형. 분홍 볼, 이마의 엑스, 얇은 눈. 캐릭터 이름은 본문이 확정하지 않음.",
         why="표정이 취향이라 구매를 걸어 두었다고 함. 사진의 볼이나 엑스를 추가 이유로 올리지 않음.",
         behavior="구매 희망", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1593857972157165568", feature="표정", detail="화났다고 부른 표정", polarity="긍정",
         quote="이 표정의 먼작귀 ..인형 없나", target="상품 구현", chars="쿠리만쥬",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 그림 1장",
         image="쿠리만쥬가 눈을 감고 크게 웃으며 음식을 먹음. 작성자 말의 화남과 그림의 웃음이 그대로 같지는 않음.",
         why="이 표정의 인형을 갖고 싶다고 함. 그림이 웃는 얼굴로 보여도 작성자 표현은 빡친·화난 표정.",
         behavior="소장 희망", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1639224175914258432", feature="표정", detail="힘이 풀린 표정", polarity="긍정",
         quote="마음 약해지거나 흔들리면", target="기본 외형", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="평소 표정과 마음이 약해질 때의 표정 차이를 귀여운 점으로 설명.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1644330283863523328", feature="표정", detail="풀리는 표정", polarity="긍정",
         quote="표정 풀어지는 거 봐", target="특정 장면", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="표정 변화를 귀엽다고 함. 같은 글의 목소리는 외형에 넣지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1740151252963762270", feature="표정", detail="모몽가 표정, 종류는 미명시", polarity="긍정",
         quote="모몽가 표정봐ㅠㅠ ㄱ귀여워", target="상품 구현", chars="모몽가",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 인용된 상품 도안 1장",
         image="랍스터 옷을 입은 여러 캐릭터 도안. 모몽가는 작은 그림으로 섞여 있음. 어느 표정을 가리키는지는 문장이 더 좁히지 않음.",
         why="표정을 보라고 함. 도안의 옷 색깔을 선호 이유로 바꾸지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1741168037334794430", feature="표정", detail="넘어질 때 표정이 안 변함", polarity="긍정",
         quote="넘어질때 표정변화없이", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="표정이 그대로인 채 미끄러지는 행동을 귀엽다고 함. 행동과 표정을 둘 다 적음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1762682498897871320", feature="표정", detail="랏코 표정, 종류는 미명시", polarity="긍정",
         quote="미춋나 랏코 표정 귀야워", target="구분 불가", chars="랏코",
         etype="직접적인 특징 평가", photo="확인 실패", photo_how="화면 없는 Chrome. 삭제된 게시물",
         image="",
         why="표정을 귀엽다고 한 문장은 저장 본문에 있음. 지금 페이지는 삭제되어 어떤 표정인지는 못 봄.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1799648824262320492", feature="표정", detail="상품으로 보고 싶은 표정들", polarity="긍정",
         quote="다음 랏코 마코로 나왔으면 하는 표정들", target="상품 구현", chars="랏코",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 그림 2장",
         image="1장: 물 위에 뜬 얼굴, 이마의 별. 2장: 눈이 풀리고 볼이 붉은 확대.",
         why="이 표정들이 마코 상품으로 나왔으면 한다고 함. 두 장의 눈 모양을 문장에 없는 선호로 이름 붙이지 않음.",
         behavior="출시 희망", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1849800192142475389", feature="표정", detail="구워진 얼굴에 보이는 표정", polarity="긍정",
         quote="표정 보이는 게 너무 너무 귀여워", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="팬케이크 메이커가 구워지며 표정이 보이는 점을 귀엽다고 함. 기계 성능 전체가 이유는 아님.",
         behavior="단순 감상", link="문맥상 연결", speaker="작성자"),
    dict(post_id="1951140824043098584", feature="표정", detail="인형 표정, 종류는 미명시", polarity="긍정",
         quote="표정이 내 심장을 울림", target="상품 구현", chars="하치와레",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 인용 사진 1장",
         image="정면은 빨간 모자의 우사기 인형. 하치와레로 보이는 흰색 인형은 뒷모습. 칭찬한 표정은 이 장에서 안 보임.",
         why="하치와레 표정이 좋아 사고 싶다고 함. 화면에 보인 우사기 얼굴을 그 이유로 바꾸지 않음.",
         behavior="구매 희망", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="2037759934197387522", feature="표정", detail="이 모몽가 표정, 종류는 미명시", polarity="긍정",
         quote="이 모몽가 표정이 너무.맘에들어요", target="상품 구현", chars="모몽가",
         etype="직접적인 특징 평가", photo="예", photo_how="화면 없는 Chrome. 정지 사진 1장",
         image="유리 안 모몽가 인형. 눈이 크고 입이 작음. 작성자는 표정이 마음에 든다고만 함.",
         why="표정을 마음에 든다고 함. 눈 크기나 입 모양은 작성자가 말하지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2090450515369046251", feature="표정", detail="한 입 먹은 뒤 표정", polarity="긍정",
         quote="딸기 파르페 한 입 먹구 나오는 표정이 사랑스러워", target="특정 장면", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="먹는 행동 다음의 표정을 사랑스럽다고 함.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1757244491571036529", feature="표정", detail="우는 얼굴", polarity="긍정",
         quote="우는 치이카와 들어올려서 같ગ 사진찍는거 넘 기여움", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="이번 목록에서는 다시 열지 않음",
         image="",
         why="우는 표정과 들어 올린 포즈를 같이 귀엽다고 함. 기존 검토 폴더의 캡처가 이 분석의 사진 확인은 아님.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1558450530523160577", feature="표정", detail="굳은 표정", polarity="긍정",
         quote="표정 싹 굳은것봐", target="특정 장면", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="굳은 표정을 압도적으로 웃기다고 함. 호감이라기보다 유머. 행동 설명과 분리해 표정도 남김.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1531858610703466496", feature="표정", detail="이 표정", polarity="긍정",
         quote="치이카와 이표정너무 웃긴", target="구분 불가", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="표정을 웃기다고만 함. 어떤 표정인지는 문장에 없음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1950894435874877559", feature="표정", detail="유니크한 표정", polarity="긍정",
         quote="유니크한 표정이라 너무 웃기고 귀여워", target="상품 구현", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="피타를 산 이유로는 귀엽다를 말하고, 표정의 평가로는 웃기고 귀엽다를 말함. 구매 이유를 표정으로 단정하지 않음.",
         behavior="구매 경험", link="같은 글에 공존", speaker="작성자"),
    # 색
    dict(post_id="1630824656805724162", feature="색상·무늬", detail="머리 색", polarity="긍정",
         quote="하치와레 머리 색을 좋아한다", target="기본 외형", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="좋아하는 색으로 머리 색을 말함. 받은 실링왁스는 그 말을 듣고 온 물건이라 작성자의 구매 이유는 아님.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1604496038668423169", feature="색상·무늬", detail="팬 작업의 색감", polarity="긍정",
         quote="색감이 러블리해져버린", target="팬 창작", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="자기 블렌더 작업의 색감이 러블리해졌다고 함. 공식 디자인의 색은 아님.",
         behavior="제작 경험", link="문맥상 연결", speaker="작성자"),
    dict(post_id="2037039194250633416", feature="색상·무늬", detail="호피 무늬 리본", polarity="긍정",
         quote="호피무늬 리본이 왕 귀여움", target="의상·소품", chars="구분 어려움",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="갸루 버전의 리본 무늬를 귀엽다고 함.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1800393742530310578", feature="신체 형태·비율", detail="귀의 존재감", polarity="긍정",
         quote="우사기는 귀때문에 존재감이 더 확실할듯", target="기본 외형", chars="우사기",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="스티커 세트의 귀여움 안에서 우사기 귀를 존재감의 이유로 말함.",
         behavior="단순 감상", link="문맥상 연결", speaker="작성자"),
    # 의상
    dict(post_id="1559028246888722433", feature="의상·소품", detail="오징어 옷", polarity="긍정",
         quote="치이카와 오징어 옷 입는거 개기여움", target="의상·소품", chars="치이카와",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="기존 Chrome 캡처 PNG를 다시 봄. 재생 안 함",
         image="흰색 캐릭터가 오징어 옷을 뒤집어씀. 노란 우사기는 그 옷을 입지 않음. 0:03.",
         why="옷 입은 장면이 귀엽다고 함. 판매 의류가 아니라 작품 장면.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1514745121572814849", feature="의상·소품", detail="오징어 옷", polarity="긍정",
         quote="오징어 옷 뒤집어 쓴 치이카와 귀여워", target="의상·소품", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="애니 장면의 의상. 같은 글의 우사기 평가는 먹는 행동이라 의상으로 넣지 않음.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1524403251084677121", feature="의상·소품", detail="칭찬 리본", polarity="긍정",
         quote="칭찬 리본 하치와레랑 치이카와 너무 귀여워서", target="의상·소품", chars="하치와레,치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="리본을 한 모습을 귀엽다고 함. 눈물은 작성자의 반응.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1737510978693345569", feature="의상·소품", detail="모몽가 모자", polarity="긍정",
         quote="완전 찰떡임 개귀여움", target="의상·소품", chars="모몽가",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="모자 상품을 쓴 모습이 잘 어울리고 귀엽다고 함. 쓴 사람의 외모는 기록하지 않음.",
         behavior="사용", link="문맥상 연결", speaker="작성자"),
    dict(post_id="1911347712949403800", feature="의상·소품", detail="잠옷에 밴드를 붙인 모습", polarity="부정",
         quote="하치와레 잠옷에 밴드 붙였는데 왜 귀엽지가 않고 피폐한거지?", target="의상·소품", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="잠옷과 밴드 조합이 귀엽지 않고 피폐하다고 함.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="1651850411513618432", feature="의상·소품", detail="안경을 쓴 모습", polarity="긍정",
         quote="치이카와들 안경 씀", target="의상·소품", chars="치이카와,하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="안경 쓴 모습을 웃기다고 함. 디자인이 예쁘다는 말은 아님.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    # 자세 동작
    dict(post_id="2084849568458604838", feature="자세·실루엣", detail="꼬리로 박자를 맞추는 동작", polarity="긍정",
         quote="꼬리로 박자맞추는 하치와레 너무커여워", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="썸네일", photo_how="기존 Chrome 캡처 PNG를 다시 봄. 재생 안 함",
         image="0:18. 하치와레의 줄무늬 꼬리가 보임. 박자를 맞추는 움직임은 정지 화면으로 확인하지 않음.",
         why="꼬리 모양이 아니라 꼬리로 박자를 맞추는 동작을 귀엽다고 함.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2089224822249370002", feature="자세·실루엣", detail="꼬리 춤", polarity="긍정",
         quote="모몽가 꼬리 춤", target="특정 장면", chars="모몽가",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="귀엽기로 유명하다는 말은 모몽가 일반이고, 이 글이 보여주는 대상은 꼬리 춤.",
         behavior="단순 감상", link="연결 없음", speaker="작성자"),
    dict(post_id="2102200775149806020", feature="특징 조합", detail="변할 때 꼬리, 귀, 크기, 눈의 순서", polarity="긍정",
         quote="꼬리 &gt; 귀 &gt; 크기 &gt; 눈 &gt;목소리", target="특정 장면", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="변신 연출에서 꼬리·귀·크기·눈이 마음을 움직인다고 순서를 적음. 목소리도 있어 외형만은 아님.",
         behavior="단순 감상", link="문맥상 연결", speaker="작성자"),
    dict(post_id="2095511040884883646", feature="특징 조합", detail="꽈배기처럼 꼬인 귀와 몸, 붙은 볼", polarity="긍정",
         quote="꽈배기 도넛 보고 귀랑 몸도 꽈배기한 우사기", target="특정 장면", chars="우사기,치이카와,하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="콜라보 그림을 귀엽다고 한 뒤 귀·몸·볼이 어떻게 그려졌는지 장면으로 짚음.",
         behavior="단순 감상", link="문맥상 연결", speaker="작성자"),
    # 재질. 디자인 순위에는 넣지 않음
    dict(post_id="1495963452627693573", feature="상품 재질·마감", detail="크고 말랑한 촉감", polarity="긍정",
         quote="짱 크고 말랑말랑해서 귀여웟", target="상품 구현", chars="치이카와,하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="스쿠트의 크기와 말랑함을 귀엽다고 함. 캐릭터 체형으로 옮기지 않음.",
         behavior="수령 경험", link="작성자가 이유를 설명", speaker="작성자"),
    dict(post_id="1576575622390087680", feature="상품 재질·마감", detail="부들부들한 마스코트", polarity="긍정",
         quote="랏코 마스코트는 정말 부들부들하고 귀여워", target="상품 구현", chars="랏코",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="마스코트 인형의 촉감. 쓰다듬는 행동은 재질 평가와 같이 있음.",
         behavior="사용", link="문맥상 연결", speaker="작성자"),
    dict(post_id="1538821759537156096", feature="상품 재질·마감", detail="무드등의 말랑함", polarity="긍정",
         quote="너무 귀여워ㅠㅠㅠㅠ말랑말랑해", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="무드등을 귀엽고 말랑하다고 함.",
         behavior="수령 경험", link="같은 글에 공존", speaker="작성자"),
    dict(post_id="1557240802656800769", feature="상품 재질·마감", detail="무드등이 생각보다 말랑함", polarity="긍정",
         quote="치이카와 무드등 생각보다 너무 말랑해서 놀람", target="상품 구현", chars="치이카와",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="예상보다 말랑해 놀랐다고 함. 긍정인지 불만인지는 놀람까지만 적음.",
         behavior="사용 경험", link="문맥상 연결", speaker="작성자"),
    dict(post_id="1583728655611883520", feature="상품 재질·마감", detail="잠옷 원단", polarity="긍정",
         quote="진짜 보들보들하고 귀여워요", target="의상·소품", chars="하치와레",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="도착한 잠옷의 촉감과 귀여움. 캐릭터 털이 아님.",
         behavior="수령 경험", link="같은 글에 공존", speaker="작성자"),
    dict(post_id="1652871907883257856", feature="상품 재질·마감", detail="끈적이고 먼지 묻는 마감", polarity="부정",
         quote="퀄리티 왜케 구림", target="상품 구현", chars="구분 어려움",
         etype="직접적인 특징 평가", photo="아니오", photo_how="본문으로 판단",
         image="",
         why="귀엽다는 말과 별도로 마감이 나쁘다고 함.",
         behavior="단순 감상", link="같은 글에 공존", speaker="작성자"),
]

PROMO_HINT = re.compile(r"입고|예약|팝니다|판매|이벤트|발매|증정|추첨|공구|신제품|신상")
CUTE_RE = re.compile(r"귀엽|귀여|기여|기엽|커여|카와이|かわいい|可愛|조와|좋아|좋지|귀야")


def main() -> None:
    posts = pd.read_csv(POSTS, dtype=str, keep_default_na=False)
    posts = posts.set_index("post_id", drop=False)
    cand = pd.read_csv(CAND, dtype=str, keep_default_na=False)
    reviewed = cand[cand.priority != "특징단어만"].copy()

    ev = pd.DataFrame(EV)
    missing = []
    for row in ev.itertuples(index=False):
        text = posts.at[row.post_id, "text"]
        if row.quote not in text:
            missing.append((row.post_id, row.quote))
    if missing:
        raise SystemExit("quote mismatch:\n" + "\n".join(f"{a} :: {b}" for a, b in missing))

    ev["evidence_id"] = [f"E{i:03d}" for i in range(1, len(ev) + 1)]
    ev["post_url"] = ev.post_id.map(posts.post_url)
    ev["account_id"] = ev.post_id.map(posts.account_id)
    ev["like_count"] = ev.post_id.map(posts.like_count)
    ev["judgment_by"] = "모델 문맥 판단"
    ev["design_tally"] = ev.feature.map(lambda x: "아니오" if x == "상품 재질·마감" else "예")
    # 유머만인 표정은 디자인 호감 핵심에서 분리
    humor_ids = {"1558450530523160577", "1531858610703466496", "1651850411513618432"}
    ev.loc[ev.post_id.isin(humor_ids), "design_tally"] = "유머"
    ev["full_text"] = ev.post_id.map(posts.text)

    direct_ids = set(ev.loc[ev.design_tally.eq("예"), "post_id"])
    material_ids = set(ev.loc[ev.feature.eq("상품 재질·마감"), "post_id"])
    humor_post_ids = set(ev.loc[ev.design_tally.eq("유머"), "post_id"])

    rows = []
    for rec in reviewed.itertuples(index=False):
        pid = rec.post_id
        if pid in direct_ids:
            kinds = sorted(set(ev.loc[ev.post_id.eq(pid) & ev.design_tally.eq("예"), "etype"]))
            targets = sorted(set(ev.loc[ev.post_id.eq(pid) & ev.design_tally.eq("예"), "target"]))
            feats = sorted(set(ev.loc[ev.post_id.eq(pid) & ev.design_tally.eq("예"), "feature"]))
            photos = "|".join(sorted(set(ev.loc[ev.post_id.eq(pid), "photo"])))
            status = "직접 특징 평가"
            etype = "|".join(kinds)
            target = "|".join(targets)
            feat = "|".join(feats)
        elif pid in material_ids:
            status = "상품 재질·마감"
            etype = "직접적인 특징 평가"
            target = "상품 구현"
            feat = "상품 재질·마감"
            photos = "아니오"
        elif pid in humor_post_ids:
            status = "표정·모습 유머"
            etype = "직접적인 특징 평가"
            target = "특정 장면"
            feat = "표정 또는 의상"
            photos = "아니오"
        elif rec.promo_flag == "예" or PROMO_HINT.search(rec.text[:80]):
            status = "판매·홍보 문구"
            etype = "판단 불가·다른 대상"
            target = "홍보"
            feat = ""
            photos = "아니오"
        elif str(rec.priority).startswith("사진지시"):
            status = "포괄적 호감"
            etype = "포괄적 호감"
            target = "구분 불가"
            feat = ""
            photos = "아니오"
        elif str(rec.priority).startswith("비교"):
            status = "비교·취향 단어, 외형 특징 아님"
            etype = "판단 불가·다른 대상"
            target = "구분 불가"
            feat = ""
            photos = "아니오"
        else:
            status = "특징 단어는 있으나 부위 호감으로 확정하지 않음"
            etype = "판단 불가·다른 대상"
            target = "구분 불가"
            feat = rec.feature_groups
            photos = "아니오"
        rows.append(
            {
                "post_id": pid,
                "post_url": rec.post_url,
                "account_id": rec.account_id,
                "like_count": rec.like_count,
                "text": rec.text,
                "candidate_priority": rec.priority,
                "promo_flag": rec.promo_flag,
                "characters": "|".join(sorted(set(ev.loc[ev.post_id.eq(pid), "chars"]))) if pid in set(ev.post_id) else "",
                "features": feat,
                "evaluation_target": target,
                "evidence_type": etype,
                "photo_checked": photos,
                "processing": "규칙 후보 후 모델이 본문을 읽음",
                "review_status": status,
            }
        )

    # 후보 273 밖에 있는 확정 글
    have = {r["post_id"] for r in rows}
    for pid in sorted(set(ev.post_id) - have):
        sub = ev[ev.post_id.eq(pid)]
        rows.append(
            {
                "post_id": pid,
                "post_url": posts.at[pid, "post_url"],
                "account_id": posts.at[pid, "account_id"],
                "like_count": posts.at[pid, "like_count"],
                "text": posts.at[pid, "text"],
                "candidate_priority": "추가 탐색",
                "promo_flag": "아니오",
                "characters": "|".join(sorted(set(sub.chars))),
                "features": "|".join(sorted(set(sub.loc[sub.design_tally.eq("예"), "feature"]))),
                "evaluation_target": "|".join(sorted(set(sub.target))),
                "evidence_type": "직접적인 특징 평가",
                "photo_checked": "|".join(sorted(set(sub.photo))),
                "processing": "규칙의 평가 단어를 비껴 가 추가 검색 후 모델이 읽음",
                "review_status": "직접 특징 평가",
            }
        )

    post_df = pd.DataFrame(rows)
    post_df.to_csv(OUT / "post_appearance_analysis.csv", index=False, encoding="utf-8-sig")

    ev_out = ev.rename(columns={
        "detail": "feature_detail",
        "polarity": "polarity",
        "quote": "quote",
        "target": "target",
        "chars": "characters",
        "etype": "evidence_type",
        "photo": "photo_checked",
        "photo_how": "photo_method",
        "image": "image_observation",
        "why": "judgment_reason",
        "behavior": "behavior",
        "link": "behavior_link",
        "speaker": "speaker",
        "feature": "feature",
    })
    cols = [
        "evidence_id", "post_id", "post_url", "account_id", "like_count", "speaker",
        "characters", "target", "feature", "feature_detail", "polarity", "evidence_type",
        "design_tally", "quote", "image_observation", "photo_checked", "photo_method",
        "behavior", "behavior_link", "judgment_reason", "judgment_by",
    ]
    ev_out[cols].to_csv(OUT / "appearance_evidence.csv", index=False, encoding="utf-8-sig")

    # 확인 필요
    review_rows = [
        dict(post_id="1762682498897871320", issue="게시물이 삭제되어 표정을 보지 못함", quote="미춋나 랏코 표정 귀야워"),
        dict(post_id="1548260243435843584", issue="시무룩하다는 문장은 있으나 현재 화면에 사진이 없음", quote="시무룩 치이카와 기여워"),
        dict(post_id="1951140824043098584", issue="하치와레 표정을 사고 싶다고 했으나 보이는 정면은 우사기 인형", quote="표정이 내 심장을 울림"),
        dict(post_id="2090813740510023857", issue="뒷모습이 통실하다고 했으나 썸네일은 카메라", quote="걸어가는 뒷모습이 통실통실해서 커여워"),
        dict(post_id="1651983324230090753", issue="하트 볼터치라고 했으나 사진의 볼은 세로 선", quote="볼터치가 하트모양이야"),
        dict(post_id="2100229868646797669", issue="위에서 보면 동그랗다는 공유. 좋아한다는 문장은 없음", quote="위에서 보면 진짜 동그란거 아는 사람"),
        dict(post_id="2082783391464964454", issue="하치끼의 꼬리일 수 있고 실제 고양이일 수 있음", quote="꼬리 탁탁 치는 거 너무 귀 여 워"),
        dict(post_id="1558660234566316032", issue="짧은 다리는 장면 서술. 그 비율을 좋아한다는 말은 없음", quote="그 짧은 다리로 열심히 기어올라가서"),
        dict(post_id="1571131866656407554", issue="표정 취향으로 구매한다고 했으나 인형 이름을 본문이 확정하지 않음", quote="이 인형 표정이 너무 취향"),
    ]
    rr = pd.DataFrame(review_rows)
    rr["post_url"] = rr.post_id.map(lambda x: posts.at[x, "post_url"] if x in posts.index else "")
    rr["text"] = rr.post_id.map(lambda x: posts.at[x, "text"] if x in posts.index else "")
    rr.to_csv(OUT / "review_required.csv", index=False, encoding="utf-8-sig")

    # 집계
    design = ev[ev.design_tally.eq("예")].copy()
    n_design_posts = design.post_id.nunique()
    n_design_ev = len(design)
    reviewed_n = len(post_df)
    tables = OUT / "tables"
    tables.mkdir(exist_ok=True)

    def uniq_table(frame, col, denom_name, denom):
        g = frame.groupby(col)["post_id"].nunique().reset_index(name="unique_posts")
        g["evidence_rows"] = frame.groupby(col).size().values
        g["denominator_name"] = denom_name
        g["denominator_value"] = denom
        g["share_of_denominator"] = (g.unique_posts / denom).round(4)
        g["multi_label"] = "한 게시물이 여러 칸에 들어갈 수 있음"
        return g.sort_values("unique_posts", ascending=False)

    feat = uniq_table(design, "feature", "직접 외형 평가 게시물", n_design_posts)
    # evidence_rows alignment bug if sort differs. recompute safely
    feat = design.groupby("feature").agg(unique_posts=("post_id", "nunique"), evidence_rows=("post_id", "size")).reset_index()
    feat["denominator_name"] = "직접 외형 평가 게시물(상품 재질·유머 제외)"
    feat["denominator_value"] = n_design_posts
    feat["share"] = (feat.unique_posts / n_design_posts).round(4)
    feat["note"] = "복수 특징 게시물은 각 행에 다시 들어감"
    feat.to_csv(tables / "feature_unique_posts.csv", index=False, encoding="utf-8-sig")

    tgt = design.groupby("target").agg(unique_posts=("post_id", "nunique"), evidence_rows=("post_id", "size")).reset_index()
    tgt["denominator_name"] = "직접 외형 평가 게시물"
    tgt["denominator_value"] = n_design_posts
    tgt["share"] = (tgt.unique_posts / n_design_posts).round(4)
    tgt.to_csv(tables / "target_unique_posts.csv", index=False, encoding="utf-8-sig")

    ch = design.assign(character=design.chars.str.split(",")).explode("character")
    ch["character"] = ch.character.str.strip()
    cross = ch.groupby(["character", "feature"])["post_id"].nunique().reset_index(name="unique_posts")
    cross["denominator_name"] = "직접 외형 평가 게시물"
    cross["denominator_value"] = n_design_posts
    cross["note"] = "한 글의 여러 캐릭터는 각 칸에 들어감. 건수가 작아 순위가 아님"
    cross.to_csv(tables / "character_by_feature.csv", index=False, encoding="utf-8-sig")

    beh = design.groupby(["feature", "link"]).agg(unique_posts=("post_id", "nunique"), evidence_rows=("evidence_id", "size")).reset_index()
    beh = beh.rename(columns={"link": "behavior_link"})
    beh["denominator_name"] = "직접 외형 평가 근거 행이 아니라 그 칸의 게시물"
    beh["note"] = "이유 연결어가 있는 경우만 작성자 이유. 공존은 원인이 아님"
    beh.to_csv(tables / "feature_by_behavior_link.csv", index=False, encoding="utf-8-sig")

    form = design.groupby(["feature", "target"]).agg(unique_posts=("post_id", "nunique")).reset_index()
    form["denominator_value"] = n_design_posts
    form["denominator_name"] = "직접 외형 평가 게시물"
    form.to_csv(tables / "feature_by_target.csv", index=False, encoding="utf-8-sig")

    status_counts = post_df.review_status.value_counts().rename_axis("review_status").reset_index(name="unique_posts")
    status_counts["denominator_name"] = "모델이 본문을 읽은 게시물"
    status_counts["denominator_value"] = reviewed_n
    status_counts["share"] = (status_counts.unique_posts / reviewed_n).round(4)
    status_counts.to_csv(tables / "review_status_counts.csv", index=False, encoding="utf-8-sig")

    # 귀엽다 단어 규모. 외형 집계의 분모가 아님
    cute_n = int(posts.text.map(lambda t: bool(CUTE_RE.search(t))).sum())
    acct = design.groupby("account_id").post_id.nunique().reset_index(name="direct_posts")
    acct = acct.sort_values("direct_posts", ascending=False)
    acct["denominator_name"] = "직접 외형 평가 게시물"
    acct["denominator_value"] = n_design_posts
    acct["share"] = (acct.direct_posts / n_design_posts).round(4)
    acct.to_csv(tables / "account_concentration.csv", index=False, encoding="utf-8-sig")

    mat = ev[ev.feature.eq("상품 재질·마감")]
    mat_n = mat.post_id.nunique()
    summary = pd.DataFrame([
        dict(item="전체 게시물", value=len(posts), note="normalized/x_posts.csv"),
        dict(item="규칙 후보", value=len(cand), note="특징 단어 또는 사진 지시·비교"),
        dict(item="모델이 읽은 우선 후보", value=int((cand.priority != "특징단어만").sum()), note="특징+평가, 사진지시, 비교"),
        dict(item="게시물 표 행", value=len(post_df), note="우선 후보와 추가 확정 글"),
        dict(item="직접 외형 평가 게시물", value=n_design_posts, note="상품 재질과 유머 전용 글을 뺀 고유 게시물"),
        dict(item="직접 외형 평가 근거 행", value=n_design_ev, note="한 글의 특징마다 1행"),
        dict(item="상품 재질 게시물", value=mat_n, note="캐릭터 디자인 집계에 넣지 않음"),
        dict(item="귀엽다류 단어가 있는 게시물", value=cute_n, note="외형 호감 분모가 아님"),
    ])
    summary.to_csv(tables / "scope_counts.csv", index=False, encoding="utf-8-sig")

    # 개인 vs 홍보: 후보 중 홍보로 뺀 글
    promo_n = int((post_df.review_status == "판매·홍보 문구").sum())
    pd.DataFrame([
        dict(group="개인 직접 외형 평가", unique_posts=n_design_posts, denominator=len(posts), note="5,000 대비"),
        dict(group="모델 검토에서 홍보로 뺀 글", unique_posts=promo_n, denominator=reviewed_n, note="읽은 글 대비"),
        dict(group="포괄적 호감", unique_posts=int((post_df.review_status == "포괄적 호감").sum()), denominator=reviewed_n, note="사진 지시+귀여움 위주. 특징 없음"),
    ]).to_csv(tables / "personal_vs_promo.csv", index=False, encoding="utf-8-sig")

    # 사진 확인 범위
    photo_tbl = design.groupby("photo").post_id.nunique().reset_index(name="unique_posts")
    photo_tbl = photo_tbl.rename(columns={"photo": "photo_checked"})
    photo_tbl["denominator_value"] = n_design_posts
    photo_tbl.to_csv(tables / "photo_check_of_direct.csv", index=False, encoding="utf-8-sig")

    make_charts(feat, status_counts, tgt, n_design_posts, reviewed_n)
    write_codebook()
    write_report(posts, design, ev, post_df, feat, tgt, acct, cute_n, n_design_posts, n_design_ev, mat_n, reviewed_n, promo_n)
    write_log(n_design_posts, len(post_df), len(ev))
    print("design posts", n_design_posts, "evidence", n_design_ev, "post rows", len(post_df))
    print(feat.to_string(index=False))
    print(acct.head(8).to_string(index=False))


def make_charts(feat, status_counts, tgt, n_design, reviewed_n) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    charts = OUT / "charts"
    charts.mkdir(exist_ok=True)

    f = feat.sort_values("unique_posts")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(f["feature"], f["unique_posts"], color="#4C78A8")
    ax.set_xlabel("고유 게시물 수")
    ax.set_title(f"직접 말한 외형 특징 (게시물 {n_design}건, 중복 허용)")
    for y, v in enumerate(f["unique_posts"]):
        ax.text(v + 0.05, y, str(v), va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(charts / "01_feature_posts.png", dpi=140)
    plt.close()

    t = tgt.sort_values("unique_posts")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(t["target"], t["unique_posts"], color="#F58518")
    ax.set_xlabel("고유 게시물 수")
    ax.set_title(f"평가가 가리킨 대상 (게시물 {n_design}건, 중복 허용)")
    for y, v in enumerate(t["unique_posts"]):
        ax.text(v + 0.05, y, str(v), va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(charts / "02_target_posts.png", dpi=140)
    plt.close()

    s = status_counts.sort_values("unique_posts")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(s["review_status"], s["unique_posts"], color="#54A24B")
    ax.set_xlabel("고유 게시물 수")
    ax.set_title(f"읽은 글의 판단 (분모 {reviewed_n}건)")
    fig.tight_layout()
    fig.savefig(charts / "03_review_status.png", dpi=140)
    plt.close()


def write_codebook() -> None:
    text = """# 외형 호감 분류 기준

버전: 2026-11-03 외형 분석. 입력은 `normalized/x_posts.csv` 5,000건이다. 기존 `text_analysis_v2` 라벨은 정답으로 쓰지 않았다.

판단은 두 층이다.

- 규칙: 특징 단어, 평가 단어, 사진 지시, 비교 표현으로 후보를 골랐다. 띄어쓰기를 없애고 세 번 이상 늘어난 글자를 줄여 검색했다. 이 층은 라벨이 아니다.
- 모델 문맥 판단: 우선 후보 본문을 읽고, 아래 포함·제외를 적용했다. 사람 검토자는 따로 없다. 사진을 본 경우만 이미지 확인으로 적는다.

## 외형 특징

‘귀엽다’만으로 둥근 얼굴이나 작은 몸을 넣지 않는다. 단어가 나온 것과, 그 특징을 좋게 또는 나쁘게 말한 것을 구분한다.

| 분류 | 포함 | 제외 | 예시 |
| --- | --- | --- | --- |
| 얼굴·머리 형태 | 주둥이, 옆모습, 앞머리, 만두형, 머리 실루엣, 인형의 머리 크기 | 얼굴이 걸려 있다는 상황, 위에서 보면 동그랗다는 사실 공유 | 볼록한 주둥이가 더 귀엽다 |
| 눈·눈매 | 반짝임, 초롱함, 순정만화 눈, 눈동자 조립 | 눈을 뜬다는 동작, 판매 문안의 눈망울 | 눈이 너무 반짝여서 별로 |
| 입·볼 | 볼살, 볼터치, 볼을 누르는 소리 | 작성자가 운다는 말의 눈물 | 볼살 실화 |
| 신체 형태·비율 | 짧은 팔다리, 둥근 엉덩이, 얼굴과 몸의 비율 | 짧은 다리로 기어오른다는 장면 서술 | 짧은 팔다리로 춤을 춘다 |
| 표정 | 미소, 시무룩, 굳은 얼굴, 표정 변화, 이 표정 | 뿌듯해하는 마음만 있고 얼굴 이야기가 없는 문장 | 표정 변화가 좋다 |
| 자세·실루엣 | 앉은 형태, 뒷모습, 꼬리로 박자를 맞추는 동작 | 안내 문안의 ‘자세하게’ | 앉은 치이카와가 더 귀엽다 |
| 색상·무늬 | 머리 색, 털의 복슬함, 호피 리본, 작업물의 색감 | 파스텔이라는 상품 카피 | 하치와레 머리 색을 좋아한다 |
| 의상·소품 | 작중 오징어 옷, 리본, 모자, 안경, 잠옷과 밴드 | 파자마 판매 공지, 옷 입히라는 작중 행동만 있는 문장 | 오징어 옷이 귀엽다 |
| 특징 조합 | 한 문장에서 귀·몸·볼 또는 변신 순서를 같이 말함 | 이름만 여러 개 | 귀와 몸이 꽈배기 |
| 상품 재질·마감 | 인형·잠옷·무드등의 말랑함, 끈적임, 마감 | 장면 속 몸이 말랑하게 눌리는 작화 | 마스코트가 부들부들하다 |
| 세부 불명확 | 귀엽다, 실물이 귀엽다, 이 사진이 귀엽다 | 위 특징이 같이 있는 문장 | 실물 너무 귀여워 |

상품 재질은 표로 남기되 캐릭터 디자인 집계에는 넣지 않는다. 유머만 있는 안경·굳은 표정은 근거에는 남기고 디자인 호감 집계에서는 뺀다.

초기 후보에 없던 의상·소품과 상품 재질을 더한 이유: 본문이 옷, 리본, 모자, 말랑한 인형을 따로 칭찬했다. 이것을 얼굴 형태로 합치면 평가 대상이 바뀐다.

## 평가 대상

| 대상 | 의미 |
| --- | --- |
| 기본 외형 | 장면이나 상품을 특정하지 않고 캐릭터가 원래 그렇게 생겼다고 말함 |
| 특정 장면 | 애니, 만화, 움짤의 한 표정·포즈·행동 |
| 의상·소품 | 옷, 모자, 리본, 안경을 적용한 모습. 판매 옷과 작중 옷을 문장으로 구분 |
| 상품 구현 | 인형, 가챠, 키링, 팬케이크 메이커처럼 만든 물건 |
| 팬 창작 | 직접 그리거나 모델링한 결과 |
| 구분 불가 | 문장만으로 장면인지 상품인지 모르겠거나 사진이 없음 |

인형이 말랑하다는 말을 원작 디자인의 매력으로 바꾸지 않는다.

## 근거 유형

| 유형 | 집계 |
| --- | --- |
| 직접적인 특징 평가 | 호감 포인트의 핵심. 작성자가 부위와 평가를 같이 말함 |
| 이미지로 대상 보완 | 이번 핵심 집계에 넣지 않음. 사진은 대상을 보여줄 뿐 이유를 대신하지 않음 |
| 포괄적 호감 | 귀엽다뿐. 별도 집계 |
| 판단 불가·다른 대상 | 홍보, 장면 서술, 다른 사람, 맛, 목소리 |

부정은 그 특징을 싫다고 한 문장만 부정이다. 처음에는 싫었다가 나중에 하나만 사고 싶었다는 글은 특징 평가와 구매 희망을 잇지 않는다.

## 행동과 연결

| 연결 | 의미 |
| --- | --- |
| 작성자가 이유를 설명 | 표정이 취향이라 산다, 이 표정으로 나와 달라, 만쥬로 내 달라 |
| 문맥상 연결 | 같은 문장에서 특징과 평가가 이어지지만 구매 동사는 없음 |
| 같은 글에 공존 | 구매했다는 말과 특징이 한 글에 있으나 이유 연결어가 없음 |
| 연결하지 않음 | 싫어한 특징과 나중 구매가 다른 이유 |
| 연결 없음 | 감상만 있음 |

사진에 물건이 있어도 구매나 소유로 확정하지 않는다.

## 사진

- 화면 없는 Chrome(Playwright, 설치되어 있는 Chrome)으로 연 화면을 이번 확인으로 본다.
- 바탕화면 Chrome은 사용자가 작업을 위해 중단을 요청한 뒤 쓰지 않았다. 중단 전에 연 옆모습 글 1건만 보이는 창 확인으로 남긴다.
- `C:/DATA/image_review/20261102_194106/evidence`의 PNG는 그 보고서가 말한 Chrome 캡처다. 이번 분석에서 그 파일을 다시 본 6건만 재사용한다. 대체 텍스트만 읽은 것은 확인이 아니다.
- 재생 버튼이 있으면 썸네일이다. 영상을 재생하지 않았다.
- 로그인 벽이 댓글을 가려도 본문 사진이 보이면 그 장만 기록한다.
"""
    (OUT / "appearance_codebook.md").write_text(text, encoding="utf-8")


def write_report(posts, design, ev, post_df, feat, tgt, acct, cute_n, n_posts, n_ev, mat_n, reviewed_n, promo_n) -> None:
    top_acct = acct.iloc[0]
    lines = []
    a = lines.append
    a("# 치이카와 외형 호감")
    a("")
    a("사람들은 둥근 얼굴이나 작은 몸을 자주 이름 붙이지 않았다. 문장으로 남은 호감은 표정, 볼, 옆모습·주둥이, 작중 옷, 그리고 인형으로 만들었을 때의 비율·눈·촉감이다. 건수가 적어 순위보다 사례로 읽는 것이 맞다.")
    a("")
    a("## 범위")
    a("")
    a(f"전체는 5,000게시물이다. 귀엽다·좋아한다 계열 단어가 있는 글은 {cute_n}건이지만, 이것은 외형 호감의 분모가 아니다. 규칙이 고른 후보 610건 가운데 평가·사진 지시·비교가 있는 273건을 읽고, 평가 단어를 비껴 간 볼·주둥이·앞머리·표정 글을 추가했다. 상품 재질과 유머만 있는 글을 뺀 직접 외형 평가는 **{n_posts}게시물, 근거 {n_ev}행**이다. 한 글이 여러 특징에 들어갈 수 있어 특징별 게시물 합은 {n_posts}보다 크다.")
    a("")
    a(f"읽은 글 {reviewed_n}건 가운데 판매·홍보로 뺀 글은 {promo_n}건, 귀엽다는 말만 있는 포괄적 호감은 {int((post_df.review_status=='포괄적 호감').sum())}건이다. 직접 평가 {n_posts}건은 전체 5,000의 {n_posts/5000:.1%}다.")
    a("")
    a("## 직접 말한 포인트")
    a("")
    a("분모는 직접 외형 평가 게시물이다. 상품 재질과 유머 전용 글은 빠진다.")
    a("")
    a("| 특징 | 고유 게시물 | 분모 대비 |")
    a("| --- | --- | --- |")
    for r in feat.sort_values("unique_posts", ascending=False).itertuples(index=False):
        a(f"| {r.feature} | {r.unique_posts} | {r.unique_posts}/{n_posts} |")
    a("")
    a("### 표정")
    a("")
    a("가장 자주 이름 붙은 것은 표정이다. 미소, 시무룩, 굳은 얼굴, 풀리는 얼굴, 표정 변화처럼 종류를 말한 글과, ‘이 표정’이라고만 한 글이 섞여 있다.")
    a("")
    a("- “하치와레 표정 변화 왜 이리 좋지” ([1535067039521738753](https://x.com/cheese_6091/status/1535067039521738753)). 썸네일은 입을 벌린 한 프레임이라 변화 자체는 못 봤다.")
    a("- “이 인형 표정이 너무 취향으로 귀여워서 … 구매걸어놓고” ([1571131866656407554](https://x.com/To_Dot_/status/1571131866656407554)). 구매 이유를 표정이라 했고, 사진의 볼이나 이마 표시를 이유로 더하지 않았다. 인형 이름은 본문이 확정하지 않는다.")
    a("- “이 표정의 먼작귀 ..인형 없나 … 갖고싶다” ([1593857972157165568](https://x.com/hey_tinsel/status/1593857972157165568)). 작성자는 화난 표정이라 했고, 그림은 눈을 감고 크게 웃는 쿠리만쥬다. 두 기록을 합치지 않았다.")
    a("- “다음 랏코 마코로 나왔으면 하는 표정들” ([1799648824262320492](https://x.com/goldengyul/status/1799648824262320492)). 그림 2장을 상품 표정으로 요청했다.")
    a("")
    a("### 볼과 옆모습")
    a("")
    a("볼은 귀엽다는 단어 없이 나오는 경우가 있다. “치이카와 볼살 실화?” ([1568057505842102273](https://x.com/vvvewww/status/1568057505842102273))는 이불 속 장면에서 볼을 짚는다. “푹하면서 볼살눌리는게 개처귀여움” ([2089617238383051149](https://x.com/Wo4s6q2/status/2089617238383051149))는 장면의 작화가 눌리는 것이지 인형 촉감이 아니다.")
    a("")
    a("옆모습은 취향을 직접 고른 문장이다. “치이카와 아기들은 두가지 옆모습 가지고 있음. 개인적으로도 볼록한 주둥이가 더 귀여운듯” ([2020171308567601359](https://x.com/oi_oi_s/status/2020171308567601359)). 도안은 납작한 입과 튀어나온 주둥이를 나란히 보여 준다. “갠적으로 랏코 옆모습을 조와해여. 털이 복실복실” ([1877408972023460269](https://x.com/goldengyul/status/1877408972023460269)). “일자앞머리 하치와레 생각보다 더 귀엽잖아” ([1759765157285404916](https://x.com/zzeeiiikk/status/1759765157285404916)).")
    a("")
    a("반대 사례도 있다. “눈이 너무 반짝 거려 … 찡그리지 … 별로 안 귀여운 것 같은데” ([1609191102707560449](https://x.com/moomyongx/status/1609191102707560449)). 뒤에 하나만 갖고 싶었다고 했으나, 그 이유를 눈이나 표정으로 되돌리지 않았다.")
    a("")
    a("“볼터치가 하트모양이야” ([1651983324230090753](https://x.com/i_melody_you/status/1651983324230090753))는 작성자 평가로 남긴다. 같은 글의 인형 사진은 세로 분홍 선이라, 하트를 사진이 증명한다고 쓰지 않는다.")
    a("")
    a("### 비율, 옷, 상품으로 만들었을 때")
    a("")
    a("“저 짧은 팔다리로 야무지게 춤추는데” ([1560849222798151680](https://x.com/vvvewww/status/1560849222798151680))는 짧은 몸과 춤이 같이 있다. 썸네일은 웃는 정지 화면이라 춤은 확인하지 못했다. “그 짧은 다리로 열심히 기어올라가서”는 장면 서술이라 호감에서 뺐다.")
    a("")
    a("오징어 옷은 판매 옷이 아니다. “치이카와 오징어 옷 입는거 개기여움” ([1559028246888722433](https://x.com/vvvewww/status/1559028246888722433)). 썸네일에서 흰색 캐릭터만 그 옷을 뒤집어썼고 우사기는 입지 않았다.")
    a("")
    a("상품 구현의 불만은 원형 디자인과 다르다. “대가리가 왤캐 커 … 테무에서온하치와레” ([1910683993890316493](https://x.com/seoLY_ovo/status/1910683993890316493)). “모몽가 눈동자 위아래 반대로 끼워진게 왔네요” ([1996459696027513149](https://x.com/gumbanut/status/1996459696027513149)), 사진 2장에서 눈 위치가 다르다. “머리부분이 산 같다 … 모몽가 꼬리털 같은 소재로” ([1959281741073387638](https://x.com/daggu_zzang/status/1959281741073387638)).")
    a("")
    a("말랑하고 부들부들하다는 인형·잠옷·무드등 평가는 상품 재질이다. 이 글은 디자인 집계 밖이고, 고유 게시물 " + str(mat_n) + "건이다. 예: “짱 크고 말랑말랑해서 귀여웟” ([1495963452627693573](https://x.com/oxxvva_/status/1495963452627693573)).")
    a("")
    a("팬 작업에서는 비율이 조건으로 나온다. “얼굴을 더 크게 만들거나 몸이 더 작아야 베이비같을것같아요” ([1958532856785031652](https://x.com/ckkro__u/status/1958532856785031652)).")
    a("")
    a("## 대상과 캐릭터")
    a("")
    a("대상도 한 글이 여러 칸에 들어갈 수 있다. 분모는 같은 " + str(n_posts) + "건이다.")
    a("")
    a("| 대상 | 고유 게시물 |")
    a("| --- | --- |")
    for r in tgt.sort_values("unique_posts", ascending=False).itertuples(index=False):
        a(f"| {r.target} | {r.unique_posts} |")
    a("")
    a("캐릭터를 한 줄로 고정하지 않는다. 하치와레는 앞머리, 주둥이, 표정 변화, 인형 머리 크기처럼 글마다 포인트가 다르다. 랏코는 옆모습·털·표정 요청이 있고, 치이카와는 볼이 눌리는 장면과 짧은 팔다리, 우사기는 볼과 귀가 남아 있다. 모몽가와 쿠리만쥬는 특정 표정 상품을 원하는 글이 있다. 이 차이는 표본 안 문장의 차이이지, 캐릭터 성공 공식의 차이가 아니다.")
    a("")
    a("계정은 한곳에 몰리지 않는다. 직접 평가 " + str(n_posts) + f"건 중 가장 많은 계정은 {top_acct.account_id} {int(top_acct.direct_posts)}건({top_acct.share:.1%})이다. 좋아요가 큰 글도 전체 소비자 의견으로 쓰지 않는다. 볼이 눌린다는 글의 좋아요가 높아도 그 문장이 표본의 대표는 아니다.")
    a("")
    a("## 상품 행동과 연결")
    a("")
    a("특징을 구매 이유로 직접 말한 경우는 적다. 인형 표정이 취향이라 구매를 걸어 둔 글, 화난 표정 인형을 갖고 싶다는 글, 하치와레 표정 때문에 사고 싶다는 글, 랏코 표정을 마코로 내 달라는 글, 만두 모습을 만쥬로 내 달라는 글이다. “후회없는 소비였따”처럼 구매 완료와 볼터치가 한 글에 있어도 이유 연결어가 없으면 공존으로 남긴다. 앉은 치이카와 사진이 있어도 샀다고 쓰지 않는다.")
    a("")
    a("홍보 문안은 개인 집계에서 뺐다. “초롱초롱 눈망울로 나를 홀려버린” 같은 매장 글, 공식 마켓의 “어딜 봐도 귀여운 인형”은 작성자 호감이 아니다.")
    a("")
    a("## 국내 IP를 볼 때")
    a("")
    a("1. 이용자가 문장으로 남기는 지점은 정지된 둥근 실루엣보다 표정 변화, 특정 표정, 볼의 반응인 경우가 있다. 후보 IP의 시안에서 사람들이 표정과 볼을 말로 짚는지 확인할 필요가 있다.")
    a("2. 옆모습과 주둥이처럼 제작자가 구분한 차이를 소비자가 더 귀엽다고 고른 사례가 있다. 정면 한 장만으로 호감을 설명하기 어려운지 물어 볼 수 있다.")
    a("3. 짧은 팔다리는 그 몸으로 하는 행동과 같이 말해졌다. 비율만 줄인 상품이 같은 반응을 만드는지는 이 데이터로 알 수 없다.")
    a("4. 작중 의상과 판매 의류, 인형의 머리 비율·눈 조립·촉감은 서로 다른 불만과 호감이다. 원형 디자인이 좋다는 말과 상품이 엉성하다는 말을 한 점수로 합치지 않는 편이 낫다.")
    a("5. 귀엽다는 말만 있는 글이 훨씬 많다. 이 IP에서 관찰한 특징을 다른 캐릭터의 필수 조건으로 옮기지 않는다.")
    a("")
    a("추가 확인은 댓글, 표정 차이를 보여 주는 시안 테스트, 그리고 이번에 썸네일만 본 영상의 재생이다.")
    a("")
    a("## 한계")
    a("")
    a("- 5,000건은 연도별 수집 인기 글이다. 전체 이용자 비율이 아니다.")
    a("- 직접 평가의 분모가 작다. 표의 순서는 강조하지 않는다.")
    a("- 모델이 우선 후보와 추가 단서 글을 읽었다. 귀엽다 단어가 있는 모든 글을 한 줄씩 외형으로 재분류하지는 않았다. 사람 검토자는 없다.")
    a("- 사진 확인은 직접 평가 글 가운데 일부다. 동영상과 GIF는 재생하지 않았다. 삭제된 랏코 표정 글과, 시무룩 글의 빠진 사진은 본문만 남겼다.")
    a("- 기존 이미지 검토 보고서의 74건 전체를 다시 보지 않았다. 이번 주제와 겹치고 PNG가 있는 6건만 다시 보았다. 그 파일은 `C:/DATA/image_review/20261102_194106/evidence`에 있다.")
    a("- Firecrawl은 글 1건의 본문만 가져왔고 스크린샷은 지원되지 않았다. 사진 확인은 화면 없는 Chrome이다.")
    a("- 사람 외모, 성별, 나이는 보지 않았다.")
    a("")
    (OUT / "appearance_analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_log(n_posts, n_rows, n_ev) -> None:
    text = f"""# 진행 기록

- 출력 폴더: `appearance_analysis/20261103_105724`
- 입력: `normalized/x_posts.csv` 5,000행. 원본과 기존 분석 CSV는 수정하지 않음.
- `scripts/extract_candidates.py`: 규칙 후보. 다시 실행하면 `working/candidates.csv`를 덮어 씀.
- `scripts/headless_capture.py`: 화면 없는 Chrome. 이미 있는 PNG는 건너뛰어 재개할 수 있음. 로그는 `working/headless_capture_log.csv`.
- `scripts/build_outputs.py`: 모델이 확정한 근거 목록으로 표와 보고서를 다시 씀. 근거 문장이 원문에 없으면 중단함.

## 사진

- 사용자가 바탕화면 창이 작업을 방해한다고 해서 Computer Use를 멈춤.
- 그 전에 보이는 Chrome으로 확인한 글은 `2020171308567601359` 1건.
- 이후는 Playwright headless, 설치되어 있는 Chrome, 창 없음. 요청 사이 8초.
- 로그인 벽이 댓글을 가린 화면이 있으나 본문 사진은 보인 경우가 많음. CAPTCHA와 우회는 없음.
- Firecrawl은 `1877408972023460269` 본문만 확인. 스크린샷은 엔진이 지원하지 않음. 추가 호출은 하지 않음.
- 기존 캡처 재열람: `1568057505842102273`, `1559028246888722433`, `1560849222798151680`, `2084849568458604838`, `2089617238383051149`. 오징어 옷은 상태 화면과 확대 컷.

## 결과 규모

- 게시물 표 {n_rows}행
- 근거 {n_ev}행
- 직접 외형 평가 게시물 {n_posts}건

## 하지 않은 일

- Git 커밋, Notion 게시, 원본 수정 없음.
- 동영상 재생 없음.
- 귀엽다 단어만 있는 글의 사진을 전부 열지는 않음. 특징이 문장에 없거나, 대상이 상품인지 장면인지 문장만으로 갈리지 않는 글 위주로 열었음.
"""
    (OUT / "run_log.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
