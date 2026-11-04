# 실행 기록

- 시각: 2026-11-03
- 규칙 버전: `2026-11-03.reaction.v3`
- Python: 3.11
- 원본 파일은 수정하지 않았다.

## 순서

1. `normalized`의 게시물, 키워드, 출처 행 수를 확인했다. 게시물 5,000, 키워드 연결 7,466, 조회수 결측 946(모두 2022).
2. `working/mine_surfaces.py`로 표기와 언어를 세고, 연도·목적·이름이 다른 142건을 `working/dev_sample.md`에 뽑아 읽었다. 이 142건으로 규칙을 고쳤다.
3. `working/analyze_reactions.py`를 v1, v2, v3로 고쳐 실행했다. 보고 숫자는 v3다.
4. 특징·직접 이유 107행을 `working/model_review_queue.md`에서 읽었다.
5. 규칙 작성과 ID가 겹치지 않는 점검 표본 56건을 `working/holdout_review.md`에서 확인했다. 짧은 이름 `하치` `치이`가 빠지는 것, `좋아하는 건 아님`이 호감으로 남는 것을 보고에 한계로 적었다.
6. `working/make_charts.py`로 그림 세 장을 만들었다.

사람 검수는 없다. 첨부 이미지와 영상은 열지 않았다.
