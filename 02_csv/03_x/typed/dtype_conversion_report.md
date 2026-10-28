# X CSV 자료형 변환 보고서

- 생성 시각: 2026-10-28T21:12:33
- Python: 3.11.9
- pandas: 3.0.3
- 입력: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated\x_chiikawa_2022_2026_merged_raw.csv`
- 검증: 통과

이번 작업은 자료형 확인과 분석용 변환이다. 행 삭제, 중복 제거, 관련성 판단, 본문 수정, 캐릭터·소비 형태 분류는 하지 않았다.

## 1. 보고서와 실제 데이터

통합 보고서는 5,000행, 13개 컬럼, 전부 문자열, pandas 결측 0건, 조회수 빈 문자열 946건(2022년), 계정 이름 문자열 `null` 2건, 게시물 ID 5,000개 고유를 기록했다. 실제 컬럼은 `댓글 개수`가 있고 `계정 소개글`은 없다.

| 항목 | 보고서 | 실제 | 결과 |
| --- | --- | --- | --- |
| 행 수 | 5000 | 5000 | 일치 |
| 컬럼 수 | 13 | 13 | 일치 |
| pandas 결측 | 0 | 0 | 일치 |
| 조회수 빈 문자열 | 946 | 946 | 일치 |
| 조회수 빈 문자열 중 2022년 | 946 | 946 | 일치 |
| 계정 이름 문자열 null | 2 | 2 | 일치 |
| 게시물 ID 고유 | 5000 | 5000 | 일치 |
| 댓글 개수 컬럼 | 있음 | 있음 | 일치 |
| 계정 소개글 컬럼 | 없음 | 없음 | 일치 |

실제 확인 결과가 보고서와 같다. `계정 소개글` 컬럼은 만들지 않았다.

## 2. 변환 전

읽기 옵션은 `dtype='string'`, `na_filter=False`, `keep_default_na=False`, `encoding='utf-8-sig'`, `on_bad_lines='error'` 이다. pandas 결측과 빈 문자열은 따로 센다.

```text
<class 'pandas.DataFrame'>
RangeIndex: 5000 entries, 0 to 4999
Data columns (total 13 columns):
 #   Column       Non-Null Count  Dtype 
---  ------       --------------  ----- 
 0   게시물 링크       5000 non-null   string
 1   계정 ID        5000 non-null   string
 2   댓글 개수        5000 non-null   string
 3   리포스트 개수      5000 non-null   string
 4   본문           5000 non-null   string
 5   계정 이름        5000 non-null   string
 6   작성 시각        5000 non-null   string
 7   조회수          5000 non-null   string
 8   좋아요 수        5000 non-null   string
 9   키워드          5000 non-null   string
 10  source_file  5000 non-null   string
 11  source_row   5000 non-null   string
 12  source_year  5000 non-null   string
dtypes: string(13)
memory usage: 2.0 MB
```

변환 전 dtype:

| 컬럼 | dtype |
| --- | --- |
| 게시물 링크 | string |
| 계정 ID | string |
| 댓글 개수 | string |
| 리포스트 개수 | string |
| 본문 | string |
| 계정 이름 | string |
| 작성 시각 | string |
| 조회수 | string |
| 좋아요 수 | string |
| 키워드 | string |
| source_file | string |
| source_row | string |
| source_year | string |

| 컬럼 | dtype | pandas 결측 | 빈 문자열 | 공백만 | 앞뒤 공백이 원문과 다름 |
| --- | --- | --- | --- | --- | --- |
| 게시물 링크 | string | 0 | 0 | 0 | 0 |
| 계정 ID | string | 0 | 0 | 0 | 0 |
| 댓글 개수 | string | 0 | 0 | 0 | 0 |
| 리포스트 개수 | string | 0 | 0 | 0 | 0 |
| 본문 | string | 0 | 0 | 0 | 0 |
| 계정 이름 | string | 0 | 0 | 0 | 1 |
| 작성 시각 | string | 0 | 0 | 0 | 0 |
| 조회수 | string | 0 | 946 | 0 | 0 |
| 좋아요 수 | string | 0 | 0 | 0 | 0 |
| 키워드 | string | 0 | 0 | 0 | 0 |
| source_file | string | 0 | 0 | 0 | 0 |
| source_row | string | 0 | 0 | 0 | 0 |
| source_year | string | 0 | 0 | 0 | 0 |

정확히 일치하는 특수 토큰:

| 컬럼 | 토큰 | 건수 |
| --- | --- | --- |
| 계정 이름 | null | 2 |

확인한 토큰: `NA`, `NULL`, `N/A`, `NaN`, `nan`, `None`, `null`, `<NA>`, `NaT`.

## 3. 변환 규칙

- 문자열 컬럼은 원문을 유지했다. 계정 ID와 게시물 링크는 숫자로 바꾸지 않았다.
- 정수 컬럼은 0과 앞자리 0이 없는 양의 정수만 Int64로 바꿨다. 기존 0은 그대로다.
- 조회수의 빈 문자열 946건만 `pd.NA`로 바꿨다. 0이나 평균으로 채우지 않았다.
- 계정 이름의 문자열 `null` 2건은 원문으로 남겼다. 실제 누락인지는 정하지 않았다.
- 작성 시각 5,000건은 시간대가 없는 `YYYY-MM-DD HH:MM:SS` 였다. 시계의 숫자는 그대로 두고 `Asia/Seoul`을 지정했다.

## 4. 변환 후

```text
<class 'pandas.DataFrame'>
RangeIndex: 5000 entries, 0 to 4999
Data columns (total 13 columns):
 #   Column       Non-Null Count  Dtype                     
---  ------       --------------  -----                     
 0   게시물 링크       5000 non-null   string                    
 1   계정 ID        5000 non-null   string                    
 2   댓글 개수        5000 non-null   Int64                     
 3   리포스트 개수      5000 non-null   Int64                     
 4   본문           5000 non-null   string                    
 5   계정 이름        5000 non-null   string                    
 6   작성 시각        5000 non-null   datetime64[ns, Asia/Seoul]
 7   조회수          4054 non-null   Int64                     
 8   좋아요 수        5000 non-null   Int64                     
 9   키워드          5000 non-null   string                    
 10  source_file  5000 non-null   string                    
 11  source_row   5000 non-null   Int64                     
 12  source_year  5000 non-null   Int64                     
dtypes: Int64(6), datetime64[ns, Asia/Seoul](1), string(6)
memory usage: 1.8 MB
```

| 컬럼 | 변환 전 | 변환 후 | pandas 결측 |
| --- | --- | --- | --- |
| 게시물 링크 | string | string | 0 |
| 계정 ID | string | string | 0 |
| 댓글 개수 | string | Int64 | 0 |
| 리포스트 개수 | string | Int64 | 0 |
| 본문 | string | string | 0 |
| 계정 이름 | string | string | 0 |
| 작성 시각 | string | datetime64[ns, Asia/Seoul] | 0 |
| 조회수 | string | Int64 | 946 |
| 좋아요 수 | string | Int64 | 0 |
| 키워드 | string | string | 0 |
| source_file | string | string | 0 |
| source_row | string | Int64 | 0 |
| source_year | string | Int64 | 0 |

### 조회수 결측

| source_year | 행 수 | 조회수 결측 |
| --- | --- | --- |
| 2022 | 1000 | 946 |
| 2023 | 1000 | 0 |
| 2024 | 1000 | 0 |
| 2025 | 1000 | 0 |
| 2026 | 1000 | 0 |

조회수 결측 946건은 모두 2022년이다. 변환 전 빈 문자열 건수와 같다. 이 결측은 변환 오류가 아니다.

### 계정 이름 문자열 null

아래 2건의 계정 이름은 문자열 `null` 그대로다. pandas 결측으로 바꾸지 않았다.

| source_file | source_row | 계정 ID | 계정 이름 | 게시물 링크 |
| --- | --- | --- | --- | --- |
| x_chiikawa_2022.csv | 519 | @nulltowdz | null | https://x.com/nulltowdz/status/1563531638285340672 |
| x_chiikawa_2025.csv | 285 | @otoingd | null | https://x.com/otoingd/status/1934246550924132540 |

### 앞뒤 공백이 있는 계정 이름

문자열을 정리하지 않았으므로 앞뒤 공백도 원문 그대로 남겼다.

| source_file | source_row | 계정 ID | 계정 이름 원문 |
| --- | --- | --- | --- |
| x_chiikawa_2022.csv | 179 | @lovemypinkmmm | ' 마쥬 ' |

## 5. 검증

| 항목 | 결과 | 내용 |
| --- | --- | --- |
| 행 수 유지 | 통과 | 5000 -> 5000 |
| 컬럼 13개와 순서 유지 | 통과 | 13 columns |
| 문자열 원문 유지 | 통과 | 6개 문자열 컬럼이 변환 전과 같다 |
| 정수 값 유지 | 통과 | 반응 수치와 추적 정수가 원문 정수와 같다 |
| 기존 0 유지 | 통과 | 댓글 개수 3016->3016, 리포스트 개수 1515->1515, 좋아요 수 33->33 |
| 조회수 빈 문자열을 결측으로 변환 | 통과 | 결측 946건, 2022년 일치 True |
| 조회수 외 결측 없음 | 통과 | 기타 pandas 결측 0건 |
| 계정 이름 문자열 null 유지 | 통과 | 2건을 문자열로 유지 |
| 작성 시각의 시계 유지 | 통과 | Asia/Seoul 지정 후 시·분·초가 원문과 같다 |
| 작성 시각 연도와 source_year | 통과 | 5,000건 일치 |
| 게시물 ID 고유 | 통과 | 추출 5000, 고유 5000, 중복 ID 0 |
| 목표 자료형 | 통과 | 목표 자료형과 같다 |
| CSV 재로딩 | 통과 | 값, 행 수, 자료형이 같다 |
| Parquet 재로딩 | 통과 | 값, 행 수, 자료형이 같다 |
| 입력 파일 미변경 | 통과 | 입력 CSV, 보고서, 컬럼 사전의 지문이 같다 |

## 6. 변환 실패

변환 실패 0건.

조회수 빈 문자열을 결측으로 둔 것은 실패 건수에 넣지 않았다.

## 7. 저장과 재로딩

CSV는 셀 텍스트만 저장하고 Int64, 결측, `Asia/Seoul` 시간대를 자료형으로 저장하지 못한다. 다시 읽을 때는 `load_typed_csv()`가 명시적 dtype과 날짜 규칙을 적용한다.

- 분석용 CSV: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_chiikawa_2022_2026_typed.csv`
- CSV 재로딩: 값, 행 수, 자료형이 같다
- Parquet: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_chiikawa_2022_2026_typed.parquet` 를 pyarrow로 저장하고 다시 읽었다. 값, 행 수, 자료형이 같다

Parquet 저장에는 설치되어 있던 pyarrow를 사용했다. 패키지를 새로 설치하지 않았다.

## 8. 입력 파일

입력 CSV, 통합 보고서, 기존 컬럼 사전은 수정하지 않았다.

| 파일 | SHA-256 | 실행 후 동일 |
| --- | --- | --- |
| x_chiikawa_2022_2026_merged_raw.csv | 4ed1dd655a1a8cd24b9848719fdc0592add1ec7c5fef9f3c5929440ea13f347a | 예 |
| merge_report.md | b90bd7875370dda5b1b499e8fc5cba64514485e4f2cd3bbc43f29472fdf591c1 | 예 |
| column_dictionary.csv | 3664cfc844ebeb1c6ae43808d6b0539563b927b327b799c186e2e1c5f948ce03 | 예 |

## 9. 결과물

- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\convert_x_dtypes.py`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_chiikawa_2022_2026_typed.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_chiikawa_2022_2026_typed.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\dtype_conversion_report.md`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_typed_table_definition.csv`
