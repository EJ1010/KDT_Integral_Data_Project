# X 정규화 테이블 정의서

- 입력: `typed/x_chiikawa_2022_2026_typed.parquet`
- x_posts의 원본 컬럼은 영어 저장명으로 둔다. 값, 결측, 문자열 null은 바꾸지 않는다.
- CSV는 기본키와 외래키를 강제하지 않는다. `normalize_x_tables.py`가 검증한다.
- 조회수만 NULL을 허용한다. 계정 이름의 문자열 `null`은 NULL이 아니다.

## 컬럼명 매핑

x_posts에 남기는 원본 컬럼만 영어 저장명을 쓴다. 나머지 저장명은 원래 영문이다.

| 원본 또는 출처 | 저장 컬럼 | 설명 |
| --- | --- | --- |
| 게시물 링크 | post_id | 새로 추출한 식별자. 링크 컬럼도 그대로 둔다. 정수로 변환하지 않는다. |
| 게시물 링크 | post_url | 저장명만 post_url이다. 링크 문자열은 바꾸지 않는다. |
| 계정 ID | account_id | 저장명만 account_id다. 계정 테이블로 분리하지 않는다. |
| 계정 이름 | account_name | 저장명만 account_name이다. 계정 ID와 일대일로 가정하지 않는다. |
| 본문 | text | 저장명만 text다. 내용을 수정하지 않는다. |
| 작성 시각 | created_at | 저장명만 created_at이다. 연·월 컬럼을 추가하지 않는다. |
| 댓글 개수 | comment_count | 저장명만 comment_count다. 반응 지표를 별도 테이블로 분리하지 않는다. |
| 리포스트 개수 | repost_count | 저장명만 repost_count다. |
| 조회수 | view_count | 저장명만 view_count다. 0이나 평균으로 채우지 않는다. |
| 좋아요 수 | like_count | 저장명만 like_count다. |
| source_file | source_file | 컬럼명을 바꾸지 않는다. |
| source_year | source_year | 파일 테이블에만 둔다. 작성 시각의 연도로 대체하지 않는다. |
| source_row | source_row | 컬럼명을 바꾸지 않는다. (source_file, source_row)가 기본키다. |
| 통합 입력의 행 위치 | input_row_no | 새로 둔 관리 컬럼. 기본키가 아니다. 원본 13개 컬럼의 순서를 복원할 때 사용한다. |
| 키워드 | keyword | 원소 단위로 저장한다. 공백을 포함한 원소도 한 키워드다. 별칭을 합치지 않는다. |
| 키워드 | keyword_order | 새로 둔 순서 컬럼. (post_id, keyword_order)가 기본키다. |

## x_posts

- 목적: 게시물 1개의 주소, 수집 시점 계정 속성, 본문, 작성 시각, 수집 시점 반응을 보관한다.
- 한 행의 단위: 게시물 1개
- 실제 행 수: 5000
- 기본키: post_id
- 외래키: 없음

| 컬럼 | 설명 | pandas 자료형 | SQL 대응 | NULL |
| --- | --- | --- | --- | --- |
| post_id | 게시물 링크의 /status/ 뒤에 있는 숫자 식별자. 문자열로 둔다. | string | TEXT | 비허용 |
| post_url | X 게시물 URL 원문. | string | TEXT | 비허용 |
| account_id | 수집 시점에 기록된 @사용자명. 숫자형 사용자 고유 ID가 아니다. | string | TEXT | 비허용 |
| account_name | 수집 시점에 기록된 표시 이름. 문자열 null과 앞뒤 공백을 유지한다. | string | TEXT | 비허용 |
| text | 게시물 본문 원문. 줄바꿈과 기호를 유지한다. | string | TEXT | 비허용 |
| created_at | 게시 작성 시각. 한국시간(Asia/Seoul)이다. | datetime64[ns, Asia/Seoul] | TIMESTAMP WITH TIME ZONE | 비허용 |
| comment_count | 수집 시점의 댓글 수. 기존 0을 유지한다. | Int64 | BIGINT | 비허용 |
| repost_count | 수집 시점의 리포스트 수. 기존 0을 유지한다. | Int64 | BIGINT | 비허용 |
| view_count | 수집 시점의 조회수. 결측은 그대로 둔다. | Int64 | BIGINT | 허용 |
| like_count | 수집 시점의 좋아요 수. 기존 0을 유지한다. | Int64 | BIGINT | 비허용 |

| 컬럼 | 실제 결측 |
| --- | --- |
| post_id | 0 |
| post_url | 0 |
| account_id | 0 |
| account_name | 0 |
| text | 0 |
| created_at | 0 |
| comment_count | 0 |
| repost_count | 0 |
| view_count | 946 |
| like_count | 0 |

## x_source_files

- 목적: 원본 CSV 파일 1개와 그 파일 기준 연도를 보관한다. 작성 시각의 연도와 다른 의미다.
- 한 행의 단위: 원본 파일 1개
- 실제 행 수: 5
- 기본키: source_file
- 외래키: 없음

| 컬럼 | 설명 | pandas 자료형 | SQL 대응 | NULL |
| --- | --- | --- | --- | --- |
| source_file | 원본 CSV 파일명. | string | TEXT | 비허용 |
| source_year | 원본 파일 기준 연도. 작성 시각에서 계산한 연도가 아니다. | Int64 | BIGINT | 비허용 |

| 컬럼 | 실제 결측 |
| --- | --- |
| source_file | 0 |
| source_year | 0 |

## x_post_sources

- 목적: 원본 파일의 레코드 1개가 어느 게시물에서 왔는지와 통합 입력 순번을 보관한다.
- 한 행의 단위: 원본 파일의 레코드 1개
- 실제 행 수: 5000
- 기본키: source_file, source_row
- 외래키: source_file → x_source_files.source_file, post_id → x_posts.post_id

| 컬럼 | 설명 | pandas 자료형 | SQL 대응 | NULL |
| --- | --- | --- | --- | --- |
| source_file | 원본 CSV 파일명. | string | TEXT | 비허용 |
| source_row | 헤더를 제외한 원본 CSV 레코드 순번. 1부터 시작한다. | Int64 | BIGINT | 비허용 |
| post_id | 게시물 링크의 /status/ 뒤에 있는 숫자 식별자. 문자열로 둔다. | string | TEXT | 비허용 |
| input_row_no | 통합 입력 Parquet의 물리 순서. 1부터 시작하는 관리용 순번이다. | Int64 | BIGINT | 비허용 |

| 컬럼 | 실제 결측 |
| --- | --- |
| source_file | 0 |
| source_row | 0 |
| post_id | 0 |
| input_row_no | 0 |

## x_keywords

- 목적: 검색 키워드 원소 1개를 보관한다. 작품 별칭을 합치거나 분류 라벨을 만들지 않는다.
- 한 행의 단위: 검색 키워드 1개
- 실제 행 수: 13
- 기본키: keyword
- 외래키: 없음

| 컬럼 | 설명 | pandas 자료형 | SQL 대응 | NULL |
| --- | --- | --- | --- | --- |
| keyword | 세로줄(\|)로 나눈 검색 키워드 원소 하나. 원문과 같은 문자열이다. | string | TEXT | 비허용 |

| 컬럼 | 실제 결측 |
| --- | --- |
| keyword | 0 |

## x_post_keywords

- 목적: 한 게시물에 기록된 키워드 원소 1개와 원문에서의 순서를 보관한다.
- 한 행의 단위: 게시물에 기록된 키워드 원소 1개
- 실제 행 수: 7466
- 기본키: post_id, keyword_order
- 외래키: post_id → x_posts.post_id, keyword → x_keywords.keyword

| 컬럼 | 설명 | pandas 자료형 | SQL 대응 | NULL |
| --- | --- | --- | --- | --- |
| post_id | 게시물 링크의 /status/ 뒤에 있는 숫자 식별자. 문자열로 둔다. | string | TEXT | 비허용 |
| keyword_order | 한 게시물 안에서 키워드 원소의 왼쪽부터 순서. 1부터 시작한다. | Int64 | BIGINT | 비허용 |
| keyword | 세로줄(\|)로 나눈 검색 키워드 원소 하나. 원문과 같은 문자열이다. | string | TEXT | 비허용 |

| 컬럼 | 실제 결측 |
| --- | --- |
| post_id | 0 |
| keyword_order | 0 |
| keyword | 0 |

## 키워드 복원

한 게시물의 `x_post_keywords` 행을 `keyword_order` 오름차순으로 두고 `keyword`를 세로줄(`|`)로 연결하면 입력 `키워드`와 같다.
원소의 앞뒤 공백을 지우지 않고, 같은 게시물에 같은 원소가 여러 번 있어도 삭제하지 않는다.

## 저장

- Parquet: 자료형 보존용. `index=False`, pyarrow.
- CSV: 공유용 UTF-8 BOM. 조회수 결측은 빈 칸이다. 작성 시각은 `YYYY-MM-DD HH:MM:SS+09:00`이다.
- CSV를 다시 읽을 때는 식별자와 계정 이름, 본문, 키워드를 문자열로 지정한다. 기본 결측 추론을 켜면 문자열 `null`이 사라진다.
