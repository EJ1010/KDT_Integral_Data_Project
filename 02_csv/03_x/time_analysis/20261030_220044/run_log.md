# 실행 기록

- 실행 시각: 2026-10-30T22:00:44
- Python: 3.0.3 pandas on 3.11.9
- pandas: 3.0.3
- matplotlib: 3.11.1
- 글꼴: Malgun Gothic (C:\Windows\Fonts\malgun.ttf)
- 분석 버전: 2026-10-30.v2.3
- 방법: clause_context_rules
- 결과 폴더: C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\time_analysis\20261030_220044

## 입력

- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_posts.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_keywords.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\x_posts_analysis.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\x_analysis_evidence.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\x_analysis_connections.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\review_required.csv`
- 기준서 `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\analysis_codebook.md`
- 실행 기록 `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\text_analysis_v2\20261030_211145\run_log.md`

`text_analysis`와 `text_analysis_deep`의 라벨은 읽어서 버전을 비교하는 데만 쓰고, 집계에 합치지 않았다.

## 기간과 집계 규칙

- 작성 시각 문자열의 연·월·일을 쓴다. `+09:00`에 9시간을 더하지 않는다.
- `source_year`는 파일 연도라 기간 축으로 쓰지 않는다.
- 기본 단위는 고유 게시물이다. 근거 행 수와 연결 행 수는 `tables/unit_counts_yearly.csv`에만 둔다.
- 확정 비중은 `review_flag=예` 27건을 분모와 분자에서 뺀다. 월별 건수 그림만 5,000건이다.
- 작품 내용 축의 분모는 작품 관련이며 확인 필요를 뺀 게시물이다.
- 복수 라벨은 게시물당 한 번만 센다. 좋아요를 라벨 수만큼 더하지 않는다.
- 라벨이 0건이면 비율 0이다. 게시물이 없는 2026-11, 2026-12는 표를 만들지 않아 0과 구분된다.
- 월 게시물 50건 미만은 `small_sample=예`다. 연간 15건 미만 라벨은 선그래프로 잇지 않는다. 두 기준은 눈금 규칙이지 유의성 기준이 아니다.
- 이동평균은 쓰지 않았다.
- 동일 달력 비교는 매년 1월 1일~10월 22일이다.
- 조회수 결측은 그대로 둔다.

## 도구

- 집계와 그림은 로컬 Python이다.
- 공개 일정 확인에 웹 검색을 썼다. 게시물 원문은 외부로 보내지 않았다.
- 분류용 MCP는 없다. 기존 v2 라벨을 유지했다.
- MySQL, 스프레드시트, Notion, Firecrawl은 이 집계에 필요 없어 쓰지 않았다.
- 수행하지 않은 것: 전면 재분류, 유의성 검정, 계절성 모형, 예측, 판매량 추정, 경과 시간 보정, 이미지 판독.

## 검증

- exclusive_purpose_sums_to_denom: 통과 bad_periods=0
- post_id_unique: 통과 5000
- no_time_mismatch: 통과 
- text_match: 통과 5000
- view_na_2022: 통과 기대 946
- view_present_2022: 통과 기대 54
- view_na_later: 통과 
- barrier_action_zero: 통과 0
- review_excluded_from_confirmed: 통과 
- evidence_rows: 통과 31
- charts_written: 통과 n=13 small=[]
- no_missing_share_on_zero_label: 통과 없는 달은 행을 만들지 않음
