# 기존 산출물 중복 정리

## 확인된 중복 또는 파생 관계

- `keyword_cooccurrence_clean.csv`와 `powerbi/fact_keyword_pairs.csv`는 내용이 동일한 파일이다. 최종본에는 `fact_keyword_pairs.csv`만 유지했다.
- `keyword_frequency_clean.csv`는 `dim_keyword.csv`의 상위 일부 요약이다. 최종본에는 전체 키워드를 담은 `dim_keyword.csv`만 유지했다.
- 굿즈 및 시각적 매력의 히트맵용 넓은 행렬은 긴 형식 교차표와 같은 수치를 반복한다. 최종본에는 `analysis_cross_pairs.csv`만 유지했다.
- `visual_appeal_posts.csv`는 `fact_posts.csv`에서 시각적 매력 게시물만 추린 부분집합이다. 최종본에는 `fact_posts.csv`만 유지했다.
- 개별 `bridge_post_category`, `bridge_post_goods_type`, `bridge_post_visual_element` 파일은 `bridge_post_label.csv` 하나로 통합했다.
- 여러 `classification_rules.csv`는 `dim_label.csv`의 `keyword_rule` 컬럼으로 통합했다.
- ZIP 파일과 그 내부 폴더는 배포본과 작업본 관계이므로 내용이 반복된다.

## 최종본에서 제외한 분석

- 캐릭터별 시각적 매력 표는 작품명 `치이카와`와 캐릭터명 `치이카와`를 본문만으로 구분하기 어려워 최종 의사결정용 모델에서 제외했다.
