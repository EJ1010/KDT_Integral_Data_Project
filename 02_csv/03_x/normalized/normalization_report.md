# X 게시물 관계형 정규화 보고서

- 생성 시각: 2026-10-29T15:08:22+09:00
- Python: 3.11.9
- pandas: 3.0.3
- pyarrow: 24.0.0
- 입력: `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\typed\x_chiikawa_2022_2026_typed.parquet`
- 검증: 통과

이번 작업은 현재 컬럼을 게시물, 원본 파일, 원본 레코드, 검색 키워드로 나누는 관계형 정규화다. 콘텐츠를 분류하거나 반응 수치를 스케일링하지 않았다.

## 1. 입력 확인

참고한 파일은 `typed/dtype_conversion_report.md`와 `typed/x_typed_table_definition.csv`다. 데이터는 Parquet 하나만 읽었다. `classification` 폴더는 읽지 않았다.

| 항목 | 값 |
| --- | --- |
| 행 수 | 5000 |
| 컬럼 수 | 13 |
| post_id 고유 | 5000 |
| 조회수 결측 | 946 |
| 키워드 원문 고유 | 195 |
| 원본 파일 수 | 5 |

입력 자료형:

```text
게시물 링크                             string
계정 ID                              string
댓글 개수                               Int64
리포스트 개수                             Int64
본문                                 string
계정 이름                              string
작성 시각          datetime64[ns, Asia/Seoul]
조회수                                 Int64
좋아요 수                               Int64
키워드                                string
source_file                        string
source_row                          Int64
source_year                         Int64
```

## 2. 확인한 함수 종속성

| 종속성 | 확인 | 결과 |
| --- | --- | --- |
| post_id → 게시물 속성 | post_id 고유값과 행 수가 같다 | 성립 |
| 게시물 링크 ↔ post_id | 링크와 추출 ID가 각각 행마다 고유하다 | 성립 |
| source_file → source_year | 파일 5개의 source_year 고유값 최대 1 | 성립 |
| (source_file, source_row) → post_id | 복합키 중복 0, 키별 게시물 최대 1 | 성립 |
| post_id → 출처 레코드 | 게시물당 출처 레코드 최대 1 | 이번 데이터에서 성립. 스키마의 기본키로 강제하지 않음 |
| 계정 ID → 계정 이름 | 표시 이름이 둘 이상인 계정 22개 | 성립하지 않음 |
| 계정 이름 → 계정 ID | 계정이 둘 이상인 표시 이름 79개 | 성립하지 않음 |
| post_id → 키워드 목록 | 한 칸에 여러 키워드가 순서대로 들어 있다 | 다치 종속. 원소 테이블로 분리 |
| source_year와 작성 시각의 연도 | 불일치 0건 | 이번 데이터는 값이 같다. 의미는 다르므로 서로 대체하지 않음 |

계정 ID는 바꿀 수 있는 `@사용자명`이다. 계정 ID 2,503개 중 22개는 표시 이름이 둘 이상이고, 표시 이름 79개는 계정 ID가 둘 이상이다. 계정 정보를 게시물의 수집 시점 속성으로 뒀다.

반응 수치는 게시물 1개에 수집 값이 하나다. 일대일 테이블로 다시 나누지 않았다. 작성 시각에서 연도나 월 컬럼을 만들지 않았다.

## 3. 분리 근거

- `x_posts`는 게시물 ID가 결정하는 주소, 계정 스냅샷, 본문, 작성 시각, 반응이다.
- `x_source_files`는 `source_file → source_year`를 파일 단위로 둔다. `source_year`는 원본 파일의 연도다.
- `x_post_sources`의 기본키는 `(source_file, source_row)`다. 이번 5,000건은 게시물과 일대일이지만, 기본키를 게시물 ID로 바꾸지 않았다.
- `input_row_no`는 통합 Parquet의 1부터 시작하는 행 순번이다. 분석 속성이 아니라 원본 행 순서를 복원하는 관리 컬럼이다.
- `x_keywords`와 `x_post_keywords`는 한 칸에 들어 있던 키워드 목록을 원소로 나눈다. 순서는 `keyword_order`에 둔다.

## 4. 키워드 구분과 복원

저장 형태를 확인한 결과, 키워드 원문을 나누는 명시적 구분자는 세로줄(`|`)뿐이다. 쉼표, 빗금, 세미콜론, 줄바꿈, 겹세로줄은 없다. 공백으로 나누지 않았다.

복원 규칙은 `keyword_order` 오름차순의 `keyword`를 `|`로 연결하는 것이다. 앞뒤 공백을 제거하지 않고, 반복된 원소를 지우지 않는다. 이번 데이터에는 한 게시물 안에서 반복된 원소가 없었다. 없어도 삭제 로직은 넣지 않았다.

예시:

```text
단일 원소: 치이카와
여러 원소: 치이카와|우사기
공백을 포함한 원문: 우사기|파자마 파티즈 → ['우사기', '파자마 파티즈']
공백을 포함한 원문: 치이카와|파자마 파티즈 → ['치이카와', '파자마 파티즈']
공백을 포함한 원문: 치이카와|하치와레|우사기|파자마 파티즈 → ['치이카와', '하치와레', '우사기', '파자마 파티즈']
```

키워드 원소 등장 횟수다. 게시물 수가 아니다. 한 게시물에 원소가 여러 개면 원소마다 한 행이다.

| keyword | 원소 등장 횟수 |
| --- | --- |
| 갑옷씨 | 44 |
| 데카츠요 | 28 |
| 랏코 | 726 |
| 먼작귀 | 1153 |
| 모몽가 | 411 |
| 시사 | 83 |
| 아노코 | 26 |
| 우사기 | 518 |
| 치이카와 | 3009 |
| 카니 | 38 |
| 쿠리만쥬 | 210 |
| 파자마 파티즈 | 13 |
| 하치와레 | 1207 |

## 5. 행 수

| 테이블 | 한 행의 단위 | 행 수 |
| --- | --- | --- |
| 입력 | 게시물 1개 | 5000 |
| x_posts | 게시물 1개 | 5000 |
| x_source_files | 원본 파일 1개 | 5 |
| x_post_sources | 원본 파일의 레코드 1개 | 5000 |
| x_keywords | 검색 키워드 1개 | 13 |
| x_post_keywords | 게시물에 기록된 키워드 원소 1개 | 7466 |

키워드 연결 행은 7466개다. 게시물 수 5000개로 세지 않는다.

## 6. 기본키, 외래키, 보존 검증

| 항목 | 결과 | 내용 |
| --- | --- | --- |
| x_posts PK ('post_id',) | 통과 | 결측 칸 0, 중복 행 0, 행 5000 |
| x_source_files PK ('source_file',) | 통과 | 결측 칸 0, 중복 행 0, 행 5 |
| x_post_sources PK ('source_file', 'source_row') | 통과 | 결측 칸 0, 중복 행 0, 행 5000 |
| x_keywords PK ('keyword',) | 통과 | 결측 칸 0, 중복 행 0, 행 13 |
| x_post_keywords PK ('post_id', 'keyword_order') | 통과 | 결측 칸 0, 중복 행 0, 행 7466 |
| x_post_sources.source_file → x_source_files.source_file | 통과 | 연결 누락 0 |
| x_post_sources.post_id → x_posts.post_id | 통과 | 연결 누락 0 |
| x_post_keywords.post_id → x_posts.post_id | 통과 | 연결 누락 0 |
| x_post_keywords.keyword → x_keywords.keyword | 통과 | 연결 누락 0 |
| 모든 게시물에 출처 레코드 | 통과 | 출처 없는 게시물 0 |
| 모든 게시물에 키워드 원소 | 통과 | 키워드 없는 게시물 0 |
| 사용되지 않은 원본 파일 | 통과 | 0 |
| 사용되지 않은 키워드 | 통과 | 0 |
| 키워드 순서 연속 | 통과 | 게시물 5000, 원소 7466, 순서 연속 True |
| input_row_no 1..N 고유 | 통과 | 최소 1, 최대 5000 |
| 조회수 결측 유지 | 통과 | x_posts 결측 946 |
| 계정 이름 문자열 null 유지 | 통과 | 2건 |
| 계정 이름 앞뒤 공백 유지 | 통과 | 1건 |
| 댓글 0 유지 | 통과 | 3016건 |
| 리포스트 0 유지 | 통과 | 1515건 |
| 좋아요 0 유지 | 통과 | 33건 |
| 작성 시각 시간대 | 통과 | Asia/Seoul |
| 반응 합계는 게시물 단위 | 통과 | 게시물 테이블의 합이 입력과 같다 |
| post_id 문자열 | 통과 | string |
| 메모리에서 원본 13컬럼 복원 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_posts parquet 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_source_files parquet 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_post_sources parquet 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_keywords parquet 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_post_keywords parquet 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| parquet 재로딩 후 원본 복원 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_posts csv 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_source_files csv 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_post_sources csv 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_keywords csv 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| x_post_keywords csv 재로딩 | 통과 | 값, 행 순서, 자료형이 같다 |
| csv 재로딩 후 원본 복원 | 통과 | 값, 행 순서, 자료형이 같다 |
| 입력 파일 미변경 | 통과 | Parquet, 보고서, 정의서의 지문이 같다 |

## 7. 원본 복원

출처 레코드에 게시물과 파일 연도를 연결하고, 키워드 원소를 순서대로 이어 입력 13개 컬럼을 만들었다. 정렬 기준은 `input_row_no`다. 키워드 연결로 늘어난 행에 반응 수치를 붙이거나 합산하지 않았다.

## 8. 재로딩

각 테이블을 Parquet과 UTF-8 BOM CSV로 저장한 뒤 다시 읽어 자료형과 값을 비교했다. CSV의 작성 시각은 오프셋을 해석한 뒤 Asia/Seoul로 맞춘다. 조회수의 빈 칸만 결측이다.

## 9. 미해결 사항

관계 충돌과 모호한 키워드 구분자는 없었다. 대표값을 고르는 단계는 없었다.

아래는 고치지 않고 그대로 둔 값이다.

- 계정 이름 문자열 `null` 2건은 결측이 아니다.
- 계정 이름 앞뒤 공백 1건은 원문이다.
- 조회수 결측 946건은 비워 두었다.
- 작성 시각의 연도와 `source_year`는 이번 5,000건에서 같았지만 의미가 다르다. 어느 한쪽으로 대체하지 않았다.

## 10. 재실행

```text
py -3.11 normalize_x_tables.py
```

작업 디렉터리와 무관하게 스크립트 위치 `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized` 기준으로 입력과 결과를 찾는다. 다시 실행하면 `normalized`의 결과 파일만 덮어쓴다.

## 11. 입력 파일

입력 Parquet, 자료형 보고서, 자료형 정의서는 수정하지 않았다.

| 파일 | SHA-256 | 실행 후 동일 |
| --- | --- | --- |
| x_chiikawa_2022_2026_typed.parquet | 3bc26b04d91e499fd54799e9599251029b846b200094fdc15b00e315ffd3bbec | 예 |
| dtype_conversion_report.md | dc570dfdc3b18db80bba196212c2ee9443035fd7263040bd0578cb2be39a674e | 예 |
| x_typed_table_definition.csv | 05aa246245c205f0569d09c1829923de5084350cfade865aa5dcd512a68720a1 | 예 |

## 12. 결과물

- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_posts.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_posts.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_source_files.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_source_files.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_sources.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_sources.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_keywords.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_keywords.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_keywords.parquet`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\x_post_keywords.csv`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\normalize_x_tables.py`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\normalized_table_definitions.md`
- `C:\DATA\KDT_Integral_Data_Project\02_csv\03_x\normalized\normalization_report.md`
