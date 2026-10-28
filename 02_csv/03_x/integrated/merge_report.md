# X CSV 원본 통합 보고서

- 생성 시각: 2026-10-28T19:48:26
- Python: 3.11.9
- pandas: 3.0.3
- 대상 폴더: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x`
- 결과 폴더: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated`
- 검증: 통과

이번 단계는 원본 통합과 현황 확인이다. 관련성 판단, 중복 제거, 결측 보정, 본문 수정, 숫자·날짜 정규화, 소비 형태 분류는 하지 않았다.

## 1. 파일 확인

행 수는 CSV 파서가 읽은 레코드 수이다. 물리 줄 수는 본문 안의 줄바꿈까지 포함한 줄 수라서 레코드 수와 다르다.

| 파일 | 존재 | 인코딩 | UTF-8 BOM | 크기(byte) | 물리 줄 수 | CSV 레코드 수 | 컬럼 수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| x_chiikawa_2022.csv | 있음 | utf-8-sig | 있음 | 295572 | 3863 | 1000 | 10 |
| x_chiikawa_2023.csv | 있음 | utf-8-sig | 있음 | 296310 | 4136 | 1000 | 10 |
| x_chiikawa_2024.csv | 있음 | utf-8-sig | 있음 | 298936 | 3626 | 1000 | 10 |
| x_chiikawa_2025.csv | 있음 | utf-8-sig | 있음 | 296123 | 3365 | 1000 | 10 |
| x_chiikawa_2026.csv | 있음 | utf-8-sig | 있음 | 287837 | 2799 | 1000 | 10 |

파일 지문 (실행 시작 시점, 실행 후와 동일):

| 파일 | 수정 시각 | SHA-256 |
| --- | --- | --- |
| x_chiikawa_2022.csv | 2026-10-28T14:38:43 | 0cc30471f233479368ce997d3eb903549e5ab5f92ae1f1cd2cec84aede8b4929 |
| x_chiikawa_2023.csv | 2026-10-26T19:03:35 | f4319806984dfc9db3555164edd046a7b040575f778704ad0574f80fb79aae42 |
| x_chiikawa_2024.csv | 2026-10-28T14:38:43 | 0273ee09a8635b689801e7fcb2770aca51483bbded321e734a9ed2240d36a684 |
| x_chiikawa_2025.csv | 2026-10-26T20:53:22 | e8c82f85942276c5f9d4b09cabb6afac8541083e34aaf2d88b53293b2eb1a36f |
| x_chiikawa_2026.csv | 2026-10-26T19:56:43 | b1f306c7424aa221492c965e064ff7c53d760fc70fb36c1e61beb04f5cbf8514 |

## 2. 로딩

- 입력은 위에 적은 연도별 파일 5개만 사용했다. `integrated` 안의 기존 결과는 입력에 넣지 않았다.
- 인코딩은 BOM과 strict 디코딩으로 확인했다. 디코딩 실패 문자를 대체 문자로 바꾸지 않았다.
- `csv` 모듈로 레코드를 읽고, pandas `read_csv` 결과와 셀 단위로 대조했다.
- pandas 로딩 옵션은 `dtype='string'`, `na_filter=False`, `keep_default_na=False`, `skipinitialspace=False`, `skip_blank_lines=False`, `on_bad_lines='error'` 이다.
- 빈 문자열과 `NA`, `NULL` 같은 원문을 결측값으로 바꾸지 않았다.
- 재실행 시 통합 파일을 이어 붙이지 않고, 원본 5개에서 결과 파일을 다시 쓴다.

## 3. 컬럼

다섯 파일의 컬럼명과 컬럼 순서가 같다.
이름 기준으로 같은 컬럼을 같은 위치에 맞춰 세로로 결합했고, 컬럼 순서는 원본 순서를 유지했다.
파일마다 컬럼 구성이 같아, 없는 컬럼을 빈칸으로 채운 셀은 없다.
공백이나 대소문자만 다른 별도 컬럼명은 없다.

공통 기준 컬럼 순서:
1. `게시물 링크`
2. `계정 ID`
3. `댓글 개수`
4. `리포스트 개수`
5. `본문`
6. `계정 이름`
7. `작성 시각`
8. `조회수`
9. `좋아요 수`
10. `키워드`

원본에 `source_file`, `source_row`, `source_year` 컬럼이 없어 그 이름으로 추적 컬럼을 추가했다.

추가된 추적 컬럼: `source_file`, `source_row`, `source_year`

## 4. 통합 행 수

| 구분 | CSV 레코드 수 |
| --- | --- |
| x_chiikawa_2022.csv | 1000 |
| x_chiikawa_2023.csv | 1000 |
| x_chiikawa_2024.csv | 1000 |
| x_chiikawa_2025.csv | 1000 |
| x_chiikawa_2026.csv | 1000 |
| 합계 | 5000 |
| 통합 파일 | 5000 |

통합 파일의 `source_file` 별 행 수:

| source_file | 행 수 |
| --- | --- |
| x_chiikawa_2022.csv | 1000 |
| x_chiikawa_2023.csv | 1000 |
| x_chiikawa_2024.csv | 1000 |
| x_chiikawa_2025.csv | 1000 |
| x_chiikawa_2026.csv | 1000 |

## 5. 검증

| 항목 | 결과 | 내용 |
| --- | --- | --- |
| 입력 파일 5개 | 통과 | 5 files |
| 레코드 수 합계와 통합 행 수 | 통과 | 5000 == 5000 |
| 통합 데이터에 결측값 없음 | 통과 | NA cells 0 |
| source_file 행 수 | 통과 | 파일별 레코드 수와 같다 |
| source_row 레코드 순번 | 통과 | 파일별로 1부터 레코드 수까지 |
| source_year | 통과 | 파일명의 연도와 같다 |
| 원본 컬럼 값 유지 | 통과 | 원본 컬럼 값 유지 |
| 없는 컬럼의 빈칸 | 통과 | 모든 파일의 컬럼이 같아 빈칸으로 채운 셀은 없다 |
| 추적 컬럼이 원본 컬럼을 덮어쓰지 않음 | 통과 | 충돌 없음 |
| 원본 파일 미변경 | 통과 | 크기, 수정 시각, SHA-256 동일 |
| 통합 파일 재읽기 | 통과 | rows 5000, columns 13 |
| pandas로 통합 파일 재읽기 | 통과 | cell values match |

## 6. df.info()

빈 문자열은 결측으로 바꾸지 않았으므로 `Non-Null Count`는 레코드 수와 같다. 빈칸 수는 다음 절의 빈값 현황이 기준이다.

### x_chiikawa_2022.csv

```text
<class 'pandas.DataFrame'>
RangeIndex: 1000 entries, 0 to 999
Data columns (total 10 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   게시물 링크   1000 non-null   string
 1   계정 ID    1000 non-null   string
 2   댓글 개수    1000 non-null   string
 3   리포스트 개수  1000 non-null   string
 4   본문       1000 non-null   string
 5   계정 이름    1000 non-null   string
 6   작성 시각    1000 non-null   string
 7   조회수      1000 non-null   string
 8   좋아요 수    1000 non-null   string
 9   키워드      1000 non-null   string
dtypes: string(10)
memory usage: 354.8 KB
```

### x_chiikawa_2023.csv

```text
<class 'pandas.DataFrame'>
RangeIndex: 1000 entries, 0 to 999
Data columns (total 10 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   게시물 링크   1000 non-null   string
 1   계정 ID    1000 non-null   string
 2   댓글 개수    1000 non-null   string
 3   리포스트 개수  1000 non-null   string
 4   본문       1000 non-null   string
 5   계정 이름    1000 non-null   string
 6   작성 시각    1000 non-null   string
 7   조회수      1000 non-null   string
 8   좋아요 수    1000 non-null   string
 9   키워드      1000 non-null   string
dtypes: string(10)
memory usage: 355.5 KB
```

### x_chiikawa_2024.csv

```text
<class 'pandas.DataFrame'>
RangeIndex: 1000 entries, 0 to 999
Data columns (total 10 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   게시물 링크   1000 non-null   string
 1   계정 ID    1000 non-null   string
 2   댓글 개수    1000 non-null   string
 3   리포스트 개수  1000 non-null   string
 4   본문       1000 non-null   string
 5   계정 이름    1000 non-null   string
 6   작성 시각    1000 non-null   string
 7   조회수      1000 non-null   string
 8   좋아요 수    1000 non-null   string
 9   키워드      1000 non-null   string
dtypes: string(10)
memory usage: 358.1 KB
```

### x_chiikawa_2025.csv

```text
<class 'pandas.DataFrame'>
RangeIndex: 1000 entries, 0 to 999
Data columns (total 10 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   게시물 링크   1000 non-null   string
 1   계정 ID    1000 non-null   string
 2   댓글 개수    1000 non-null   string
 3   리포스트 개수  1000 non-null   string
 4   본문       1000 non-null   string
 5   계정 이름    1000 non-null   string
 6   작성 시각    1000 non-null   string
 7   조회수      1000 non-null   string
 8   좋아요 수    1000 non-null   string
 9   키워드      1000 non-null   string
dtypes: string(10)
memory usage: 355.4 KB
```

### x_chiikawa_2026.csv

```text
<class 'pandas.DataFrame'>
RangeIndex: 1000 entries, 0 to 999
Data columns (total 10 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   게시물 링크   1000 non-null   string
 1   계정 ID    1000 non-null   string
 2   댓글 개수    1000 non-null   string
 3   리포스트 개수  1000 non-null   string
 4   본문       1000 non-null   string
 5   계정 이름    1000 non-null   string
 6   작성 시각    1000 non-null   string
 7   조회수      1000 non-null   string
 8   좋아요 수    1000 non-null   string
 9   키워드      1000 non-null   string
dtypes: string(10)
memory usage: 347.4 KB
```

### 통합 데이터

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

## 7. 빈값 현황

빈 문자열은 셀 값이 비어 있는 경우이다. 공백만 있는 값은 빈 문자열과 따로 세었고 내용을 자르지 않았다.

### 통합

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 5000 | 0 | 0.0% | 0 |
| 계정 ID | 5000 | 0 | 0.0% | 0 |
| 댓글 개수 | 5000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 5000 | 0 | 0.0% | 0 |
| 본문 | 5000 | 0 | 0.0% | 0 |
| 계정 이름 | 5000 | 0 | 0.0% | 0 |
| 작성 시각 | 5000 | 0 | 0.0% | 0 |
| 조회수 | 5000 | 946 | 18.9% | 0 |
| 좋아요 수 | 5000 | 0 | 0.0% | 0 |
| 키워드 | 5000 | 0 | 0.0% | 0 |
| source_file | 5000 | 0 | 0.0% | 0 |
| source_row | 5000 | 0 | 0.0% | 0 |
| source_year | 5000 | 0 | 0.0% | 0 |

### x_chiikawa_2022.csv

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 1000 | 0 | 0.0% | 0 |
| 계정 ID | 1000 | 0 | 0.0% | 0 |
| 댓글 개수 | 1000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 1000 | 0 | 0.0% | 0 |
| 본문 | 1000 | 0 | 0.0% | 0 |
| 계정 이름 | 1000 | 0 | 0.0% | 0 |
| 작성 시각 | 1000 | 0 | 0.0% | 0 |
| 조회수 | 1000 | 946 | 94.6% | 0 |
| 좋아요 수 | 1000 | 0 | 0.0% | 0 |
| 키워드 | 1000 | 0 | 0.0% | 0 |

### x_chiikawa_2023.csv

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 1000 | 0 | 0.0% | 0 |
| 계정 ID | 1000 | 0 | 0.0% | 0 |
| 댓글 개수 | 1000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 1000 | 0 | 0.0% | 0 |
| 본문 | 1000 | 0 | 0.0% | 0 |
| 계정 이름 | 1000 | 0 | 0.0% | 0 |
| 작성 시각 | 1000 | 0 | 0.0% | 0 |
| 조회수 | 1000 | 0 | 0.0% | 0 |
| 좋아요 수 | 1000 | 0 | 0.0% | 0 |
| 키워드 | 1000 | 0 | 0.0% | 0 |

### x_chiikawa_2024.csv

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 1000 | 0 | 0.0% | 0 |
| 계정 ID | 1000 | 0 | 0.0% | 0 |
| 댓글 개수 | 1000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 1000 | 0 | 0.0% | 0 |
| 본문 | 1000 | 0 | 0.0% | 0 |
| 계정 이름 | 1000 | 0 | 0.0% | 0 |
| 작성 시각 | 1000 | 0 | 0.0% | 0 |
| 조회수 | 1000 | 0 | 0.0% | 0 |
| 좋아요 수 | 1000 | 0 | 0.0% | 0 |
| 키워드 | 1000 | 0 | 0.0% | 0 |

### x_chiikawa_2025.csv

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 1000 | 0 | 0.0% | 0 |
| 계정 ID | 1000 | 0 | 0.0% | 0 |
| 댓글 개수 | 1000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 1000 | 0 | 0.0% | 0 |
| 본문 | 1000 | 0 | 0.0% | 0 |
| 계정 이름 | 1000 | 0 | 0.0% | 0 |
| 작성 시각 | 1000 | 0 | 0.0% | 0 |
| 조회수 | 1000 | 0 | 0.0% | 0 |
| 좋아요 수 | 1000 | 0 | 0.0% | 0 |
| 키워드 | 1000 | 0 | 0.0% | 0 |

### x_chiikawa_2026.csv

| 컬럼 | 행 수 | 빈 문자열 | 빈 문자열 비율 | 공백만 있는 값 |
| --- | --- | --- | --- | --- |
| 게시물 링크 | 1000 | 0 | 0.0% | 0 |
| 계정 ID | 1000 | 0 | 0.0% | 0 |
| 댓글 개수 | 1000 | 0 | 0.0% | 0 |
| 리포스트 개수 | 1000 | 0 | 0.0% | 0 |
| 본문 | 1000 | 0 | 0.0% | 0 |
| 계정 이름 | 1000 | 0 | 0.0% | 0 |
| 작성 시각 | 1000 | 0 | 0.0% | 0 |
| 조회수 | 1000 | 0 | 0.0% | 0 |
| 좋아요 수 | 1000 | 0 | 0.0% | 0 |
| 키워드 | 1000 | 0 | 0.0% | 0 |

## 8. 결측으로 바꾸지 않은 원문

아래 토큰과 셀 전체가 정확히 같은 값은 문자열로 유지했다: `NA`, `NULL`, `N/A`, `NaN`, `nan`, `None`, `null`.

| 자료 | 토큰과 정확히 같은 셀 수 |
| --- | --- |
| x_chiikawa_2022.csv | 1 |
| x_chiikawa_2023.csv | 0 |
| x_chiikawa_2024.csv | 0 |
| x_chiikawa_2025.csv | 1 |
| x_chiikawa_2026.csv | 0 |
| 통합 | 2 |

통합 데이터에서 토큰과 정확히 같은 셀:

| 컬럼 | 토큰 | 셀 수 |
| --- | --- | --- |
| 계정 이름 | null | 2 |

## 9. 게시물 ID 중복 현황

게시물 ID는 `게시물 링크`에서 `/status/` 뒤의 숫자를 임시로 추출해 센 것이다. 중복 행은 삭제하지 않았고, 추출한 ID 컬럼은 통합 파일에 넣지 않았다.

| 항목 | 값 |
| --- | --- |
| 통합 행 수 | 5000 |
| ID를 추출한 행 | 5000 |
| 게시물 링크가 빈 행 | 0 |
| 링크는 있으나 ID를 추출하지 못한 행 | 0 |
| 고유 ID | 5000 |
| 2회 이상 등장한 ID | 0 |
| 중복 ID에 속한 행 | 0 |
| 고유 ID보다 많은 행(잉여 행) | 0 |
| 한 ID의 최대 등장 횟수 | 1 |
| 두 개 이상 파일에 등장한 ID | 0 |
| 한 파일 안에서 2회 이상 등장한 ID | 0 |
| 파일 간 중복이면서 파일 안에서도 중복인 ID | 0 |
| 같은 ID인데 본문이 다른 ID | 0 |
| 같은 ID인데 게시물 링크 문자열이 다른 ID | 0 |

등장 횟수 분포:

| 등장 횟수 | ID 수 | 행 수 |
| --- | --- | --- |
| 1 | 5000 | 5000 |

파일 내부 중복:

| 파일 | ID 추출 행 | 고유 ID | 2회 이상 ID | 그 ID에 속한 행 | 파일 내부 잉여 행 |
| --- | --- | --- | --- | --- | --- |
| x_chiikawa_2022.csv | 1000 | 1000 | 0 | 0 | 0 |
| x_chiikawa_2023.csv | 1000 | 1000 | 0 | 0 | 0 |
| x_chiikawa_2024.csv | 1000 | 1000 | 0 | 0 | 0 |
| x_chiikawa_2025.csv | 1000 | 1000 | 0 | 0 | 0 |
| x_chiikawa_2026.csv | 1000 | 1000 | 0 | 0 | 0 |

## 10. 오류와 처리

파싱 오류, 인코딩 오류, 필드 수 불일치는 없었다.
원본 파일은 열기만 했고, 실행 전후의 크기·수정 시각·SHA-256이 같다.
통합 결과는 원본 5개를 다시 읽어 덮어썼다.

## 11. 결과물

- 스크립트: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated\merge_x_csv.py`
- 통합 CSV: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated\x_chiikawa_2022_2026_merged_raw.csv` (1613741 bytes, SHA-256 `4ed1dd655a1a8cd24b9848719fdc0592add1ec7c5fef9f3c5929440ea13f347a`)
- 이 보고서: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated\merge_report.md`
- 컬럼 사전: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\integrated\column_dictionary.csv`

통합 CSV는 UTF-8 BOM이다.
