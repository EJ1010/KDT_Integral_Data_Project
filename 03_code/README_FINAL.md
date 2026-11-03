# 치이카와 인기 요소 분석 최종 정리본

이 폴더만 Power BI 최종 모델과 발표 자료에 사용한다. 이전 전달본은 작업 과정과 검증용으로 남겨두되 새 모델에는 함께 불러오지 않는다.

## 분석 기준

- 원본 게시물: 12,534건
- 정제 분석 표본: 7,795건 (`fact_posts[is_analysis_included] = 1`)
- 굿즈·소장 심층분석 분모: 2,875건
- 시각적 매력 심층분석 분모: 2,091건
- 다중 분류이므로 분포 비율의 합은 100%를 초과할 수 있다.

## Power BI 필수 테이블

1. `model/fact_posts.csv`
2. `model/dim_date.csv`
3. `model/dim_keyword.csv`
4. `model/bridge_post_keyword.csv`
5. `model/dim_label.csv`
6. `model/bridge_post_label.csv`

기본 페이지 필터는 `fact_posts[is_analysis_included] = 1`로 설정한다. 관계는 `docs/model_relationships.csv`를 따른다.

## 결과 테이블

- `analysis/summary_axis_distribution.csv`: 프로젝트 평가영역, 굿즈, 소비행동, 시각 요소, 반응 분포 통합
- `analysis/analysis_cross_pairs.csv`: 평가영역·굿즈·시각 매력 교차분석 통합
- `model/fact_keyword_pairs.csv`: 형태소 키워드 동시출현과 향상도

## 발표 흐름

1. 프로젝트 평가영역별 언급률
2. 굿즈·소장 → 굿즈 유형과 소비·소장 행동
3. 시각적 매력 → 시각 요소와 반응
4. 교차관계를 차기 IP 선정 기준으로 전환

## 주의

- 2026년 게시물 비중이 높아 수집량을 보정하기 전에는 시계열 급증을 인기 상승으로 단정하지 않는다.
- 계정 ID가 없어 반복 게시자 영향을 완전히 통제할 수 없다.
- 키워드 규칙 기반 분류이므로 최종 발표 전 각 주요 분류에서 표본을 수작업 검수한다.
