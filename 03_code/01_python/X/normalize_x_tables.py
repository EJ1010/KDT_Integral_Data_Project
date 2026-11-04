# -*- coding: utf-8 -*-
"""X 게시물 통합 데이터를 게시물·출처·검색 키워드 테이블로 정규화한다.

입력은 typed/x_chiikawa_2022_2026_typed.parquet 하나다.
참고 보고서와 정의서는 읽고 컬럼 계약만 확인한다. 수정하지 않는다.
classification 폴더와 분류 결과는 사용하지 않는다.

키워드는 확인된 구분자 '|'로만 나누고 순서를 보존한다.
공백은 구분자가 아니다. 식별자는 문자열로 둔다.
조회수 결측, 문자열 null, 본문, 기존 0은 바꾸지 않는다.

실행:
    py -3.11 normalize_x_tables.py
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import pandas as pd
except ModuleNotFoundError:
    print("PANDAS_MISSING: run this script with Python 3.11 (py -3.11).")
    sys.exit(1)


NORMALIZED_DIR = Path(__file__).resolve().parent
BASE_DIR = NORMALIZED_DIR.parent
INPUT_PARQUET = BASE_DIR / "typed" / "x_chiikawa_2022_2026_typed.parquet"
REFERENCE_REPORT = BASE_DIR / "typed" / "dtype_conversion_report.md"
REFERENCE_DEFINITION = BASE_DIR / "typed" / "x_typed_table_definition.csv"

OUTPUT_DEFINITION = NORMALIZED_DIR / "normalized_table_definitions.md"
OUTPUT_REPORT = NORMALIZED_DIR / "normalization_report.md"

SEOUL = "Asia/Seoul"
KEYWORD_DELIMITER = "|"
CANONICAL_INT = r"^(?:0|[1-9]\d*)$"
POST_ID_PATTERN = r"/status/(\d+)$"
AMBIGUOUS_DELIMITERS = (",", ";", "\t", "\n", "\r", "/", "｜", "│", "、", "·")

ORIGINAL_COLUMNS = [
    "게시물 링크",
    "계정 ID",
    "댓글 개수",
    "리포스트 개수",
    "본문",
    "계정 이름",
    "작성 시각",
    "조회수",
    "좋아요 수",
    "키워드",
    "source_file",
    "source_row",
    "source_year",
]

POST_INPUT_COLUMNS = [
    "post_id",
    "게시물 링크",
    "계정 ID",
    "계정 이름",
    "본문",
    "작성 시각",
    "댓글 개수",
    "리포스트 개수",
    "조회수",
    "좋아요 수",
]
POST_SOURCE_TO_STORED = {
    "게시물 링크": "post_url",
    "계정 ID": "account_id",
    "계정 이름": "account_name",
    "본문": "text",
    "작성 시각": "created_at",
    "댓글 개수": "comment_count",
    "리포스트 개수": "repost_count",
    "조회수": "view_count",
    "좋아요 수": "like_count",
}
POST_STORED_TO_SOURCE = {stored: source for source, stored in POST_SOURCE_TO_STORED.items()}
POST_COLUMNS = ["post_id", *POST_SOURCE_TO_STORED.values()]
SOURCE_FILE_COLUMNS = ["source_file", "source_year"]
POST_SOURCE_COLUMNS = ["source_file", "source_row", "post_id", "input_row_no"]
KEYWORD_COLUMNS = ["keyword"]
POST_KEYWORD_COLUMNS = ["post_id", "keyword_order", "keyword"]

TABLE_SPECS: dict[str, dict[str, object]] = {
    "x_posts": {
        "purpose": "게시물 1개의 주소, 수집 시점 계정 속성, 본문, 작성 시각, 수집 시점 반응을 보관한다.",
        "grain": "게시물 1개",
        "primary_key": ["post_id"],
        "foreign_keys": [],
        "columns": POST_COLUMNS,
    },
    "x_source_files": {
        "purpose": "원본 CSV 파일 1개와 그 파일 기준 연도를 보관한다. 작성 시각의 연도와 다른 의미다.",
        "grain": "원본 파일 1개",
        "primary_key": ["source_file"],
        "foreign_keys": [],
        "columns": SOURCE_FILE_COLUMNS,
    },
    "x_post_sources": {
        "purpose": "원본 파일의 레코드 1개가 어느 게시물에서 왔는지와 통합 입력 순번을 보관한다.",
        "grain": "원본 파일의 레코드 1개",
        "primary_key": ["source_file", "source_row"],
        "foreign_keys": [
            ("source_file", "x_source_files", "source_file"),
            ("post_id", "x_posts", "post_id"),
        ],
        "columns": POST_SOURCE_COLUMNS,
    },
    "x_keywords": {
        "purpose": "검색 키워드 원소 1개를 보관한다. 작품 별칭을 합치거나 분류 라벨을 만들지 않는다.",
        "grain": "검색 키워드 1개",
        "primary_key": ["keyword"],
        "foreign_keys": [],
        "columns": KEYWORD_COLUMNS,
    },
    "x_post_keywords": {
        "purpose": "한 게시물에 기록된 키워드 원소 1개와 원문에서의 순서를 보관한다.",
        "grain": "게시물에 기록된 키워드 원소 1개",
        "primary_key": ["post_id", "keyword_order"],
        "foreign_keys": [
            ("post_id", "x_posts", "post_id"),
            ("keyword", "x_keywords", "keyword"),
        ],
        "columns": POST_KEYWORD_COLUMNS,
    },
}

COLUMN_DOCS: dict[str, dict[str, str]] = {
    "post_id": {
        "description": "게시물 링크의 /status/ 뒤에 있는 숫자 식별자. 문자열로 둔다.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "게시물 링크",
        "stored": "post_id",
        "note": "새로 추출한 식별자. 링크 컬럼도 그대로 둔다. 정수로 변환하지 않는다.",
    },
    "post_url": {
        "description": "X 게시물 URL 원문.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "게시물 링크",
        "stored": "post_url",
        "note": "저장명만 post_url이다. 링크 문자열은 바꾸지 않는다.",
    },
    "account_id": {
        "description": "수집 시점에 기록된 @사용자명. 숫자형 사용자 고유 ID가 아니다.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "계정 ID",
        "stored": "account_id",
        "note": "저장명만 account_id다. 계정 테이블로 분리하지 않는다.",
    },
    "account_name": {
        "description": "수집 시점에 기록된 표시 이름. 문자열 null과 앞뒤 공백을 유지한다.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "계정 이름",
        "stored": "account_name",
        "note": "저장명만 account_name이다. 계정 ID와 일대일로 가정하지 않는다.",
    },
    "text": {
        "description": "게시물 본문 원문. 줄바꿈과 기호를 유지한다.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "본문",
        "stored": "text",
        "note": "저장명만 text다. 내용을 수정하지 않는다.",
    },
    "created_at": {
        "description": "게시 작성 시각. 한국시간(Asia/Seoul)이다.",
        "sql": "TIMESTAMP WITH TIME ZONE",
        "null_policy": "비허용",
        "origin": "작성 시각",
        "stored": "created_at",
        "note": "저장명만 created_at이다. 연·월 컬럼을 추가하지 않는다.",
    },
    "comment_count": {
        "description": "수집 시점의 댓글 수. 기존 0을 유지한다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "댓글 개수",
        "stored": "comment_count",
        "note": "저장명만 comment_count다. 반응 지표를 별도 테이블로 분리하지 않는다.",
    },
    "repost_count": {
        "description": "수집 시점의 리포스트 수. 기존 0을 유지한다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "리포스트 개수",
        "stored": "repost_count",
        "note": "저장명만 repost_count다.",
    },
    "view_count": {
        "description": "수집 시점의 조회수. 결측은 그대로 둔다.",
        "sql": "BIGINT",
        "null_policy": "허용",
        "origin": "조회수",
        "stored": "view_count",
        "note": "저장명만 view_count다. 0이나 평균으로 채우지 않는다.",
    },
    "like_count": {
        "description": "수집 시점의 좋아요 수. 기존 0을 유지한다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "좋아요 수",
        "stored": "like_count",
        "note": "저장명만 like_count다.",
    },
    "source_file": {
        "description": "원본 CSV 파일명.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "source_file",
        "stored": "source_file",
        "note": "컬럼명을 바꾸지 않는다.",
    },
    "source_year": {
        "description": "원본 파일 기준 연도. 작성 시각에서 계산한 연도가 아니다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "source_year",
        "stored": "source_year",
        "note": "파일 테이블에만 둔다. 작성 시각의 연도로 대체하지 않는다.",
    },
    "source_row": {
        "description": "헤더를 제외한 원본 CSV 레코드 순번. 1부터 시작한다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "source_row",
        "stored": "source_row",
        "note": "컬럼명을 바꾸지 않는다. (source_file, source_row)가 기본키다.",
    },
    "input_row_no": {
        "description": "통합 입력 Parquet의 물리 순서. 1부터 시작하는 관리용 순번이다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "통합 입력의 행 위치",
        "stored": "input_row_no",
        "note": "새로 둔 관리 컬럼. 기본키가 아니다. 원본 13개 컬럼의 순서를 복원할 때 사용한다.",
    },
    "keyword": {
        "description": "세로줄(|)로 나눈 검색 키워드 원소 하나. 원문과 같은 문자열이다.",
        "sql": "TEXT",
        "null_policy": "비허용",
        "origin": "키워드",
        "stored": "keyword",
        "note": "원소 단위로 저장한다. 공백을 포함한 원소도 한 키워드다. 별칭을 합치지 않는다.",
    },
    "keyword_order": {
        "description": "한 게시물 안에서 키워드 원소의 왼쪽부터 순서. 1부터 시작한다.",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "origin": "키워드",
        "stored": "keyword_order",
        "note": "새로 둔 순서 컬럼. (post_id, keyword_order)가 기본키다.",
    },
}

STRING_BY_TABLE = {
    "x_posts": ["post_id", "post_url", "account_id", "account_name", "text"],
    "x_source_files": ["source_file"],
    "x_post_sources": ["source_file", "post_id"],
    "x_keywords": ["keyword"],
    "x_post_keywords": ["post_id", "keyword"],
}
INT_BY_TABLE = {
    "x_posts": ["comment_count", "repost_count", "view_count", "like_count"],
    "x_source_files": ["source_year"],
    "x_post_sources": ["source_row", "input_row_no"],
    "x_keywords": [],
    "x_post_keywords": ["keyword_order"],
}
NULLABLE_INT = {("x_posts", "view_count")}
DATETIME_BY_TABLE = {"x_posts": ["created_at"]}


class NormalizationConflict(Exception):
    """관계 충돌이나 모호한 키워드라서 대표값을 고르지 않고 중단한다."""

    def __init__(self, title: str, detail: str, proposal: str):
        self.title = title
        self.detail = detail
        self.proposal = proposal
        super().__init__(title)


def fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def parquet_engine() -> str:
    try:
        import pyarrow  # noqa: F401
    except ModuleNotFoundError as error:
        raise RuntimeError("pyarrow가 없어 Parquet을 저장할 수 없다. 패키지를 새로 설치하지 않았다.") from error
    return "pyarrow"


def read_reference_contract() -> list[str]:
    if not REFERENCE_REPORT.is_file():
        raise FileNotFoundError(f"참고 보고서가 없다: {REFERENCE_REPORT}")
    if not REFERENCE_DEFINITION.is_file():
        raise FileNotFoundError(f"참고 정의서가 없다: {REFERENCE_DEFINITION}")
    report_text = REFERENCE_REPORT.read_text(encoding="utf-8")
    if "x_chiikawa_2022_2026_typed.parquet" not in report_text:
        raise RuntimeError("참고 보고서에서 입력 Parquet 이름을 확인하지 못했다.")
    definition = pd.read_csv(
        REFERENCE_DEFINITION,
        dtype="string",
        encoding="utf-8-sig",
        na_filter=False,
        keep_default_na=False,
    )
    columns = definition["실제 컬럼명"].tolist()
    if columns != ORIGINAL_COLUMNS:
        raise RuntimeError(f"정의서 컬럼 순서가 예상과 다르다: {columns}")
    return columns


def load_input() -> pd.DataFrame:
    engine = parquet_engine()
    frame = pd.read_parquet(INPUT_PARQUET, engine=engine)
    if list(frame.columns) != ORIGINAL_COLUMNS:
        raise RuntimeError(f"입력 컬럼이 정의서와 다르다: {list(frame.columns)}")
    return frame


def extract_post_id(links: pd.Series) -> pd.Series:
    extracted = links.astype("string").str.extract(POST_ID_PATTERN, expand=False)
    missing = extracted.isna() | (extracted == "")
    if missing.any():
        samples = links.loc[missing].head(5).tolist()
        raise NormalizationConflict(
            "게시물 ID를 추출하지 못한 링크가 있다",
            f"결측 또는 불일치 {int(missing.sum())}건. 예: {samples}",
            "해당 링크를 삭제하거나 다른 패턴으로 잘라 대표 ID를 만들지 않는다. 링크 형식을 확인한 뒤 추출 규칙을 정한다.",
        )
    post_id = extracted.astype("string")
    if post_id.str.fullmatch(r"\d+").eq(False).any():
        raise NormalizationConflict(
            "게시물 ID가 숫자 문자열이 아니다",
            "추출 결과가 숫자만으로 이뤄지지 않았다.",
            "식별자를 숫자형으로 바꾸거나 임의 값을 채우지 않는다.",
        )
    return post_id


def ambiguous_keyword_values(keywords: pd.Series) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    for value in keywords.drop_duplicates().tolist():
        hits = [delimiter for delimiter in AMBIGUOUS_DELIMITERS if delimiter in value]
        if hits:
            found.append((value, hits))
    return found


def split_keywords(keywords: pd.Series) -> list[list[str]]:
    if keywords.isna().any():
        raise NormalizationConflict(
            "키워드 결측이 있다",
            f"pandas 결측 {int(keywords.isna().sum())}건",
            "결측 키워드를 빈 목록으로 바꾸거나 다른 게시물의 키워드로 채우지 않는다.",
        )
    ambiguous = ambiguous_keyword_values(keywords)
    if ambiguous:
        preview = ", ".join(repr(value) for value, _ in ambiguous[:10])
        raise NormalizationConflict(
            "키워드에 세로줄 외의 구분자 후보가 있다",
            f"{len(ambiguous)}개 값. 예: {preview}",
            "세로줄(|)만 확정된 구분자다. 쉼표, 빗금, 가운뎃점 등으로 추가로 나누지 않는다. 해당 값을 확인한 뒤 구분 규칙을 정한다.",
        )
    rows: list[list[str]] = []
    empty_examples: list[str] = []
    for value in keywords.tolist():
        parts = value.split(KEYWORD_DELIMITER)
        if any(part == "" for part in parts):
            if len(empty_examples) < 10:
                empty_examples.append(value)
        rows.append(parts)
    if empty_examples:
        raise NormalizationConflict(
            "키워드를 세로줄로 나누면 빈 원소가 생긴다",
            f"예: {[repr(value) for value in empty_examples]}",
            "빈 원소를 지우면 원문을 복원할 수 있어도 키워드 기본키가 빈 문자열이 된다. 해당 값을 확인한 뒤 처리한다.",
        )
    return rows


def require_unique_post_id(frame: pd.DataFrame) -> None:
    duplicated = frame["post_id"].duplicated(keep=False)
    if not duplicated.any():
        return
    attribute_columns = [column for column in ORIGINAL_COLUMNS if column != "키워드"]
    conflict_rows = frame.loc[duplicated, ["post_id", *attribute_columns]].head(20)
    raise NormalizationConflict(
        "게시물 ID가 중복이고 서로 다른 행이 있다",
        conflict_rows.to_string(index=False),
        "중복 ID 중 대표 행을 고르거나 행을 삭제하지 않는다. 같은 ID의 속성 차이를 확인한 뒤, 수집 이력으로 둘지 결정한다.",
    )


def require_source_dependencies(frame: pd.DataFrame) -> None:
    year_count = frame.groupby("source_file", dropna=False)["source_year"].nunique(dropna=False)
    if (year_count != 1).any():
        failed = year_count[year_count != 1]
        raise NormalizationConflict(
            "한 원본 파일이 여러 source_year를 가진다",
            failed.to_string(),
            "파일별로 최빈 연도를 고르지 않는다. 파일과 연도가 어긋난 행을 확인한 뒤 source_year의 기준을 정한다.",
        )
    file_year = frame["source_file"].astype("string").str.extract(r"(\d{4})", expand=False)
    if file_year.isna().any() or not file_year.astype("Int64").equals(frame["source_year"].astype("Int64")):
        mismatch = frame.loc[file_year.astype("Int64") != frame["source_year"], ["source_file", "source_year"]].head(10)
        raise NormalizationConflict(
            "파일명의 연도와 source_year가 다르다",
            mismatch.to_string(index=False) if len(mismatch) else "파일명에서 연도를 읽지 못한 행이 있다.",
            "파일명 연도와 컬럼값 중 하나를 임의로 선택하지 않는다. 어느 값이 파일 기준 연도인지 확인한다.",
        )
    if frame.duplicated(["source_file", "source_row"]).any():
        duplicated = frame.loc[frame.duplicated(["source_file", "source_row"], keep=False), ["source_file", "source_row", "post_id"]].head(20)
        raise NormalizationConflict(
            "(source_file, source_row)가 서로 다른 게시물을 가리킨다",
            duplicated.to_string(index=False),
            "같은 출처 키의 게시물 중 하나를 고르지 않는다. 원본 레코드 순번이 겹친 원인을 확인한다.",
        )


def build_tables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    working = frame.reset_index(drop=True).copy()
    working["post_id"] = extract_post_id(working["게시물 링크"])
    require_unique_post_id(working)
    require_source_dependencies(working)
    working["input_row_no"] = pd.Series(range(1, len(working) + 1), dtype="Int64")
    parts = split_keywords(working["키워드"])

    posts = working[POST_INPUT_COLUMNS].copy()
    for column in ("post_id", "게시물 링크", "계정 ID", "계정 이름", "본문"):
        posts[column] = posts[column].astype("string")
    posts["댓글 개수"] = posts["댓글 개수"].astype("Int64")
    posts["리포스트 개수"] = posts["리포스트 개수"].astype("Int64")
    posts["조회수"] = posts["조회수"].astype("Int64")
    posts["좋아요 수"] = posts["좋아요 수"].astype("Int64")
    posts = posts.rename(columns=POST_SOURCE_TO_STORED)
    posts = posts.reset_index(drop=True)[POST_COLUMNS]

    source_files = (
        working[["source_file", "source_year"]]
        .drop_duplicates()
        .sort_values("source_file", kind="mergesort")
        .reset_index(drop=True)
    )
    source_files["source_file"] = source_files["source_file"].astype("string")
    source_files["source_year"] = source_files["source_year"].astype("Int64")
    source_files = source_files[SOURCE_FILE_COLUMNS]

    post_sources = working[POST_SOURCE_COLUMNS].copy()
    post_sources["source_file"] = post_sources["source_file"].astype("string")
    post_sources["source_row"] = post_sources["source_row"].astype("Int64")
    post_sources["post_id"] = post_sources["post_id"].astype("string")
    post_sources["input_row_no"] = post_sources["input_row_no"].astype("Int64")
    post_sources = post_sources.sort_values("input_row_no", kind="mergesort").reset_index(drop=True)
    post_sources = post_sources[POST_SOURCE_COLUMNS]

    keyword_rows: list[dict[str, object]] = []
    for post_id, input_row_no, tokens in zip(working["post_id"], working["input_row_no"], parts, strict=True):
        for order, token in enumerate(tokens, start=1):
            keyword_rows.append(
                {
                    "post_id": post_id,
                    "keyword_order": order,
                    "keyword": token,
                    "input_row_no": input_row_no,
                }
            )
    post_keywords = pd.DataFrame(keyword_rows)
    post_keywords["post_id"] = post_keywords["post_id"].astype("string")
    post_keywords["keyword"] = post_keywords["keyword"].astype("string")
    post_keywords["keyword_order"] = post_keywords["keyword_order"].astype("Int64")
    post_keywords["input_row_no"] = post_keywords["input_row_no"].astype("Int64")
    post_keywords = post_keywords.sort_values(["input_row_no", "keyword_order"], kind="mergesort").reset_index(drop=True)
    post_keywords = post_keywords[POST_KEYWORD_COLUMNS]

    keywords = pd.DataFrame({"keyword": post_keywords["keyword"].drop_duplicates().sort_values(kind="mergesort")})
    keywords["keyword"] = keywords["keyword"].astype("string")
    keywords = keywords.reset_index(drop=True)[KEYWORD_COLUMNS]

    return {
        "x_posts": posts,
        "x_source_files": source_files,
        "x_post_sources": post_sources,
        "x_keywords": keywords,
        "x_post_keywords": post_keywords,
    }


def null_count(series: pd.Series) -> int:
    return int(series.isna().sum())


def duplicate_count(frame: pd.DataFrame, columns: list[str]) -> int:
    return int(frame.duplicated(columns).sum())


def validate_primary_keys(tables: dict[str, pd.DataFrame]) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    for name, spec in TABLE_SPECS.items():
        frame = tables[name]
        keys: list[str] = spec["primary_key"]  # type: ignore[assignment]
        missing = sum(null_count(frame[column]) for column in keys)
        duplicates = duplicate_count(frame, keys)
        ok = missing == 0 and duplicates == 0 and len(frame) > 0
        checks.append((f"{name} PK {tuple(keys)}", ok, f"결측 칸 {missing}, 중복 행 {duplicates}, 행 {len(frame)}"))
    return checks


def validate_foreign_keys(tables: dict[str, pd.DataFrame]) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    for name, spec in TABLE_SPECS.items():
        foreign_keys: list[tuple[str, str, str]] = spec["foreign_keys"]  # type: ignore[assignment]
        child = tables[name]
        for column, parent_name, parent_column in foreign_keys:
            parent_values = tables[parent_name][parent_column]
            missing_mask = child[column].isna() | ~child[column].isin(parent_values)
            missing = int(missing_mask.sum())
            checks.append(
                (
                    f"{name}.{column} → {parent_name}.{parent_column}",
                    missing == 0,
                    f"연결 누락 {missing}",
                )
            )
    posts = tables["x_posts"]["post_id"]
    sourced = tables["x_post_sources"]["post_id"]
    tagged = tables["x_post_keywords"]["post_id"]
    missing_source = int((~posts.isin(sourced)).sum())
    missing_keyword = int((~posts.isin(tagged)).sum())
    checks.append(("모든 게시물에 출처 레코드", missing_source == 0, f"출처 없는 게시물 {missing_source}"))
    checks.append(("모든 게시물에 키워드 원소", missing_keyword == 0, f"키워드 없는 게시물 {missing_keyword}"))
    unused_files = int((~tables["x_source_files"]["source_file"].isin(tables["x_post_sources"]["source_file"])).sum())
    unused_keywords = int((~tables["x_keywords"]["keyword"].isin(tables["x_post_keywords"]["keyword"])).sum())
    checks.append(("사용되지 않은 원본 파일", unused_files == 0, f"{unused_files}"))
    checks.append(("사용되지 않은 키워드", unused_keywords == 0, f"{unused_keywords}"))
    return checks


def validate_keyword_order(post_keywords: pd.DataFrame) -> tuple[bool, str]:
    grouped = post_keywords.groupby("post_id", sort=False)["keyword_order"]
    minimum = grouped.min().astype("Int64")
    maximum = grouped.max().astype("Int64")
    size = grouped.size().astype("Int64")
    unique = grouped.nunique().astype("Int64")
    contiguous = bool((minimum == 1).all() and maximum.equals(size) and unique.equals(size))
    return contiguous, f"게시물 {len(size)}, 원소 {len(post_keywords)}, 순서 연속 {contiguous}"


def reconstruct_keywords(post_keywords: pd.DataFrame, post_ids: pd.Series) -> pd.Series:
    ordered = post_keywords.sort_values(["post_id", "keyword_order"], kind="mergesort")
    restored = ordered.groupby("post_id", sort=False)["keyword"].agg(lambda values: KEYWORD_DELIMITER.join(values.tolist()))
    restored = restored.reindex(post_ids.to_numpy())
    return restored.astype("string")


def restore_original(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sources = tables["x_post_sources"].merge(
        tables["x_source_files"],
        on="source_file",
        how="left",
        validate="many_to_one",
    )
    posts = tables["x_posts"].rename(columns=POST_STORED_TO_SOURCE)
    restored = sources.merge(
        posts,
        on="post_id",
        how="left",
        validate="one_to_one",
    )
    restored["키워드"] = reconstruct_keywords(tables["x_post_keywords"], restored["post_id"]).to_numpy()
    restored["키워드"] = restored["키워드"].astype("string")
    restored = restored.sort_values("input_row_no", kind="mergesort").reset_index(drop=True)
    restored = restored[ORIGINAL_COLUMNS]
    for column in ("게시물 링크", "계정 ID", "본문", "계정 이름", "키워드", "source_file"):
        restored[column] = restored[column].astype("string")
    for column in ("댓글 개수", "리포스트 개수", "조회수", "좋아요 수", "source_row", "source_year"):
        restored[column] = restored[column].astype("Int64")
    return restored


def compare_frames(left: pd.DataFrame, right: pd.DataFrame) -> tuple[bool, str]:
    if list(left.columns) != list(right.columns):
        return False, f"컬럼 {list(left.columns)} != {list(right.columns)}"
    if len(left) != len(right):
        return False, f"행 {len(left)} != {len(right)}"
    left_reset = left.reset_index(drop=True)
    right_reset = right.reset_index(drop=True)
    for column in left_reset.columns:
        left_dtype = str(left_reset.dtypes[column])
        right_dtype = str(right_reset.dtypes[column])
        if left_dtype != right_dtype:
            return False, f"{column} 자료형 {left_dtype} != {right_dtype}"
        if not left_reset[column].equals(right_reset[column]):
            mismatch = (left_reset[column] != right_reset[column]) & ~(
                left_reset[column].isna() & right_reset[column].isna()
            )
            position = int(mismatch.to_numpy().nonzero()[0][0]) + 1 if mismatch.any() else 0
            return False, f"{column} 값이 {position}번째 행에서 다르다"
    return True, "값, 행 순서, 자료형이 같다"


def write_csv_table(path: Path, frame: pd.DataFrame) -> None:
    export = frame.copy()
    if "created_at" in export.columns:
        export["created_at"] = frame["created_at"].map(lambda value: value.isoformat(sep=" ", timespec="seconds"))
    export.to_csv(path, index=False, encoding="utf-8-sig", na_rep="", lineterminator="\n")


def parse_int_column(series: pd.Series, nullable: bool, column: str) -> pd.Series:
    text = series.astype("string")
    empty = text == ""
    if not nullable and empty.any():
        raise ValueError(f"{column}: 비어 있는 정수 {int(empty.sum())}건")
    filled = text[~empty]
    invalid = ~filled.str.fullmatch(CANONICAL_INT)
    if invalid.any():
        sample = filled[invalid].head(3).tolist()
        raise ValueError(f"{column}: 정수가 아닌 값 {sample}")
    result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    if (~empty).any():
        result.loc[~empty] = filled.astype("int64").to_numpy()
    return result


def read_csv_table(path: Path, table: str) -> pd.DataFrame:
    raw = pd.read_csv(
        path,
        dtype="string",
        encoding="utf-8-sig",
        na_filter=False,
        keep_default_na=False,
        lineterminator="\n",
    )
    expected: list[str] = TABLE_SPECS[table]["columns"]  # type: ignore[assignment]
    if list(raw.columns) != expected:
        raise ValueError(f"{table} CSV 컬럼이 다르다: {list(raw.columns)}")
    frame = pd.DataFrame(index=raw.index)
    for column in STRING_BY_TABLE[table]:
        frame[column] = raw[column].astype("string")
    for column in INT_BY_TABLE[table]:
        frame[column] = parse_int_column(raw[column], (table, column) in NULLABLE_INT, column)
    for column in DATETIME_BY_TABLE.get(table, []):
        parsed = pd.to_datetime(raw[column], format="%Y-%m-%d %H:%M:%S%z")
        frame[column] = parsed.dt.tz_convert(SEOUL).astype("datetime64[ns, Asia/Seoul]")
    return frame[expected]


def write_tables(tables: dict[str, pd.DataFrame], engine: str) -> None:
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_parquet(NORMALIZED_DIR / f"{name}.parquet", index=False, engine=engine)
        write_csv_table(NORMALIZED_DIR / f"{name}.csv", frame)


def reload_tables(engine: str, kind: str) -> dict[str, pd.DataFrame]:
    loaded: dict[str, pd.DataFrame] = {}
    for name in TABLE_SPECS:
        if kind == "parquet":
            frame = pd.read_parquet(NORMALIZED_DIR / f"{name}.parquet", engine=engine)
            expected: list[str] = TABLE_SPECS[name]["columns"]  # type: ignore[assignment]
            frame = frame[expected]
        elif kind == "csv":
            frame = read_csv_table(NORMALIZED_DIR / f"{name}.csv", name)
        else:
            raise ValueError(kind)
        loaded[name] = frame
    return loaded


def functional_dependency_rows(frame: pd.DataFrame) -> list[tuple[str, str, str]]:
    post_unique = int(frame["post_id"].nunique()) == len(frame)
    link_unique = int(frame["게시물 링크"].nunique()) == len(frame)
    file_years = frame.groupby("source_file")["source_year"].nunique()
    source_key_unique = not frame.duplicated(["source_file", "source_row"]).any()
    posts_per_source = frame.groupby(["source_file", "source_row"])["post_id"].nunique()
    sources_per_post = frame.groupby("post_id", sort=False).size()
    names_per_id = frame.groupby("계정 ID")["계정 이름"].nunique()
    ids_per_name = frame.groupby("계정 이름")["계정 ID"].nunique()
    created_year = frame["작성 시각"].dt.tz_convert(SEOUL).dt.year.astype("Int64")
    year_gap = int((created_year != frame["source_year"]).sum())
    return [
        ("post_id → 게시물 속성", "post_id 고유값과 행 수가 같다", "성립" if post_unique else "성립하지 않음"),
        ("게시물 링크 ↔ post_id", "링크와 추출 ID가 각각 행마다 고유하다", "성립" if post_unique and link_unique else "성립하지 않음"),
        ("source_file → source_year", f"파일 {len(file_years)}개의 source_year 고유값 최대 {int(file_years.max())}", "성립" if (file_years == 1).all() else "성립하지 않음"),
        ("(source_file, source_row) → post_id", f"복합키 중복 {int(frame.duplicated(['source_file', 'source_row']).sum())}, 키별 게시물 최대 {int(posts_per_source.max())}", "성립" if source_key_unique and (posts_per_source == 1).all() else "성립하지 않음"),
        ("post_id → 출처 레코드", f"게시물당 출처 레코드 최대 {int(sources_per_post.max())}", "이번 데이터에서 성립. 스키마의 기본키로 강제하지 않음"),
        ("계정 ID → 계정 이름", f"표시 이름이 둘 이상인 계정 {int((names_per_id > 1).sum())}개", "성립하지 않음"),
        ("계정 이름 → 계정 ID", f"계정이 둘 이상인 표시 이름 {int((ids_per_name > 1).sum())}개", "성립하지 않음"),
        ("post_id → 키워드 목록", "한 칸에 여러 키워드가 순서대로 들어 있다", "다치 종속. 원소 테이블로 분리"),
        ("source_year와 작성 시각의 연도", f"불일치 {year_gap}건", "이번 데이터는 값이 같다. 의미는 다르므로 서로 대체하지 않음"),
    ]


def keyword_examples(frame: pd.DataFrame) -> list[str]:
    single = frame.loc[~frame["키워드"].str.contains(KEYWORD_DELIMITER, regex=False), "키워드"].drop_duplicates().head(1)
    multiple = frame.loc[frame["키워드"].str.count(r"\|") >= 1, "키워드"].drop_duplicates().head(1)
    spaced = frame.loc[frame["키워드"].str.contains(" ", regex=False), "키워드"].drop_duplicates().head(3)
    lines = []
    if len(single):
        lines.append(f"단일 원소: {single.iloc[0]}")
    if len(multiple):
        lines.append(f"여러 원소: {multiple.iloc[0]}")
    for value in spaced.tolist():
        lines.append(f"공백을 포함한 원문: {value} → {value.split(KEYWORD_DELIMITER)}")
    return lines


def preservation_checks(original: pd.DataFrame, posts: pd.DataFrame) -> list[tuple[str, bool, str]]:
    aligned = original.reset_index(drop=True)
    post_aligned = posts.reset_index(drop=True)
    view_na = null_count(post_aligned["view_count"])
    literal_null = int((post_aligned["account_name"] == "null").sum())
    padded_name = int((post_aligned["account_name"] != post_aligned["account_name"].str.strip()).sum())
    zero_comments = int((post_aligned["comment_count"] == 0).sum())
    zero_reposts = int((post_aligned["repost_count"] == 0).sum())
    zero_likes = int((post_aligned["like_count"] == 0).sum())
    timezone_name = str(post_aligned["created_at"].dt.tz)
    like_sum_same = int(post_aligned["like_count"].sum()) == int(aligned["좋아요 수"].sum())
    comment_sum_same = int(post_aligned["comment_count"].sum()) == int(aligned["댓글 개수"].sum())
    repost_sum_same = int(post_aligned["repost_count"].sum()) == int(aligned["리포스트 개수"].sum())
    view_sum_same = int(post_aligned["view_count"].sum(skipna=True)) == int(aligned["조회수"].sum(skipna=True))
    return [
        ("조회수 결측 유지", view_na == null_count(aligned["조회수"]) == 946, f"x_posts 결측 {view_na}"),
        ("계정 이름 문자열 null 유지", literal_null == int((aligned["계정 이름"] == "null").sum()) == 2, f"{literal_null}건"),
        ("계정 이름 앞뒤 공백 유지", padded_name == int((aligned["계정 이름"] != aligned["계정 이름"].str.strip()).sum()), f"{padded_name}건"),
        ("댓글 0 유지", zero_comments == int((aligned["댓글 개수"] == 0).sum()), f"{zero_comments}건"),
        ("리포스트 0 유지", zero_reposts == int((aligned["리포스트 개수"] == 0).sum()), f"{zero_reposts}건"),
        ("좋아요 0 유지", zero_likes == int((aligned["좋아요 수"] == 0).sum()), f"{zero_likes}건"),
        ("작성 시각 시간대", timezone_name == SEOUL, timezone_name),
        ("반응 합계는 게시물 단위", like_sum_same and comment_sum_same and repost_sum_same and view_sum_same, "게시물 테이블의 합이 입력과 같다"),
        ("post_id 문자열", str(post_aligned["post_id"].dtype) == "string", str(post_aligned["post_id"].dtype)),
    ]


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell.replace("\\", "\\\\").replace("\n", " ").replace("|", "\\|") for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def render_definitions(tables: dict[str, pd.DataFrame]) -> str:
    lines = [
        "# X 정규화 테이블 정의서",
        "",
        "- 입력: `typed/x_chiikawa_2022_2026_typed.parquet`",
        "- x_posts의 원본 컬럼은 영어 저장명으로 둔다. 값, 결측, 문자열 null은 바꾸지 않는다.",
        "- CSV는 기본키와 외래키를 강제하지 않는다. `normalize_x_tables.py`가 검증한다.",
        "- 조회수만 NULL을 허용한다. 계정 이름의 문자열 `null`은 NULL이 아니다.",
        "",
        "## 컬럼명 매핑",
        "",
        "x_posts에 남기는 원본 컬럼만 영어 저장명을 쓴다. 나머지 저장명은 원래 영문이다.",
        "",
        markdown_table(
            ["원본 또는 출처", "저장 컬럼", "설명"],
            [[COLUMN_DOCS[column]["origin"], COLUMN_DOCS[column]["stored"], COLUMN_DOCS[column]["note"]] for column in COLUMN_DOCS],
        ),
        "",
    ]
    for name, spec in TABLE_SPECS.items():
        frame = tables[name]
        keys = ", ".join(spec["primary_key"])  # type: ignore[arg-type]
        foreign_keys: list[tuple[str, str, str]] = spec["foreign_keys"]  # type: ignore[assignment]
        foreign_text = ", ".join(f"{column} → {parent}.{parent_column}" for column, parent, parent_column in foreign_keys) or "없음"
        lines.extend(
            [
                f"## {name}",
                "",
                f"- 목적: {spec['purpose']}",
                f"- 한 행의 단위: {spec['grain']}",
                f"- 실제 행 수: {len(frame)}",
                f"- 기본키: {keys}",
                f"- 외래키: {foreign_text}",
                "",
                markdown_table(
                    ["컬럼", "설명", "pandas 자료형", "SQL 대응", "NULL"],
                    [
                        [
                            column,
                            COLUMN_DOCS[column]["description"],
                            str(frame.dtypes[column]),
                            COLUMN_DOCS[column]["sql"],
                            COLUMN_DOCS[column]["null_policy"],
                        ]
                        for column in frame.columns
                    ],
                ),
                "",
                markdown_table(
                    ["컬럼", "실제 결측"],
                    [[column, str(null_count(frame[column]))] for column in frame.columns],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## 키워드 복원",
            "",
            "한 게시물의 `x_post_keywords` 행을 `keyword_order` 오름차순으로 두고 `keyword`를 세로줄(`|`)로 연결하면 입력 `키워드`와 같다.",
            "원소의 앞뒤 공백을 지우지 않고, 같은 게시물에 같은 원소가 여러 번 있어도 삭제하지 않는다.",
            "",
            "## 저장",
            "",
            "- Parquet: 자료형 보존용. `index=False`, pyarrow.",
            "- CSV: 공유용 UTF-8 BOM. 조회수 결측은 빈 칸이다. 작성 시각은 `YYYY-MM-DD HH:MM:SS+09:00`이다.",
            "- CSV를 다시 읽을 때는 식별자와 계정 이름, 본문, 키워드를 문자열로 지정한다. 기본 결측 추론을 켜면 문자열 `null`이 사라진다.",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(context: dict[str, object]) -> str:
    original: pd.DataFrame = context["original"]  # type: ignore[assignment]
    input_view = original[ORIGINAL_COLUMNS]
    tables: dict[str, pd.DataFrame] = context["tables"]  # type: ignore[assignment]
    checks: list[tuple[str, bool, str]] = context["checks"]  # type: ignore[assignment]
    dependencies: list[tuple[str, str, str]] = context["dependencies"]  # type: ignore[assignment]
    passed = all(ok for _, ok, _ in checks)
    before: dict[str, dict[str, object]] = context["before"]  # type: ignore[assignment]
    after: dict[str, dict[str, object]] = context["after"]  # type: ignore[assignment]
    versions: dict[str, str] = context["versions"]  # type: ignore[assignment]
    lines = [
        "# X 게시물 관계형 정규화 보고서",
        "",
        f"- 생성 시각: {context['created_at']}",
        f"- Python: {versions['python']}",
        f"- pandas: {versions['pandas']}",
        f"- pyarrow: {versions['pyarrow']}",
        f"- 입력: `{INPUT_PARQUET}`",
        f"- 검증: {'통과' if passed else '실패'}",
        "",
        "이번 작업은 현재 컬럼을 게시물, 원본 파일, 원본 레코드, 검색 키워드로 나누는 관계형 정규화다. 콘텐츠를 분류하거나 반응 수치를 스케일링하지 않았다.",
        "",
        "## 1. 입력 확인",
        "",
        "참고한 파일은 `typed/dtype_conversion_report.md`와 `typed/x_typed_table_definition.csv`다. 데이터는 Parquet 하나만 읽었다. `classification` 폴더는 읽지 않았다.",
        "",
        markdown_table(
            ["항목", "값"],
            [
                ["행 수", str(len(input_view))],
                ["컬럼 수", str(input_view.shape[1])],
                ["post_id 고유", str(int(original["post_id"].nunique()))],
                ["조회수 결측", str(null_count(input_view["조회수"]))],
                ["키워드 원문 고유", str(int(input_view["키워드"].nunique()))],
                ["원본 파일 수", str(int(input_view["source_file"].nunique()))],
            ],
        ),
        "",
        "입력 자료형:",
        "",
        "```text",
        input_view.dtypes.to_string(),
        "```",
        "",
        "## 2. 확인한 함수 종속성",
        "",
        markdown_table(["종속성", "확인", "결과"], [[*row] for row in dependencies]),
        "",
        "계정 ID는 바꿀 수 있는 `@사용자명`이다. 계정 ID 2,503개 중 22개는 표시 이름이 둘 이상이고, 표시 이름 79개는 계정 ID가 둘 이상이다. 계정 정보를 게시물의 수집 시점 속성으로 뒀다.",
        "",
        "반응 수치는 게시물 1개에 수집 값이 하나다. 일대일 테이블로 다시 나누지 않았다. 작성 시각에서 연도나 월 컬럼을 만들지 않았다.",
        "",
        "## 3. 분리 근거",
        "",
        "- `x_posts`는 게시물 ID가 결정하는 주소, 계정 스냅샷, 본문, 작성 시각, 반응이다.",
        "- `x_source_files`는 `source_file → source_year`를 파일 단위로 둔다. `source_year`는 원본 파일의 연도다.",
        "- `x_post_sources`의 기본키는 `(source_file, source_row)`다. 이번 5,000건은 게시물과 일대일이지만, 기본키를 게시물 ID로 바꾸지 않았다.",
        "- `input_row_no`는 통합 Parquet의 1부터 시작하는 행 순번이다. 분석 속성이 아니라 원본 행 순서를 복원하는 관리 컬럼이다.",
        "- `x_keywords`와 `x_post_keywords`는 한 칸에 들어 있던 키워드 목록을 원소로 나눈다. 순서는 `keyword_order`에 둔다.",
        "",
        "## 4. 키워드 구분과 복원",
        "",
        "저장 형태를 확인한 결과, 키워드 원문을 나누는 명시적 구분자는 세로줄(`|`)뿐이다. 쉼표, 빗금, 세미콜론, 줄바꿈, 겹세로줄은 없다. 공백으로 나누지 않았다.",
        "",
        "복원 규칙은 `keyword_order` 오름차순의 `keyword`를 `|`로 연결하는 것이다. 앞뒤 공백을 제거하지 않고, 반복된 원소를 지우지 않는다. 이번 데이터에는 한 게시물 안에서 반복된 원소가 없었다. 없어도 삭제 로직은 넣지 않았다.",
        "",
        "예시:",
        "",
        "```text",
        *context["keyword_examples"],  # type: ignore[misc]
        "```",
        "",
        "키워드 원소 등장 횟수다. 게시물 수가 아니다. 한 게시물에 원소가 여러 개면 원소마다 한 행이다.",
        "",
        markdown_table(
            ["keyword", "원소 등장 횟수"],
            [[str(row.keyword), str(int(row.appearances))] for row in context["keyword_counts"]],  # type: ignore[union-attr]
        ),
        "",
        "## 5. 행 수",
        "",
        markdown_table(
            ["테이블", "한 행의 단위", "행 수"],
            [["입력", "게시물 1개", str(len(original))], *[[name, str(TABLE_SPECS[name]["grain"]), str(len(frame))] for name, frame in tables.items()]],
        ),
        "",
        f"키워드 연결 행은 {len(tables['x_post_keywords'])}개다. 게시물 수 {len(tables['x_posts'])}개로 세지 않는다.",
        "",
        "## 6. 기본키, 외래키, 보존 검증",
        "",
        markdown_table(["항목", "결과", "내용"], [[name, "통과" if ok else "실패", detail] for name, ok, detail in checks]),
        "",
        "## 7. 원본 복원",
        "",
        "출처 레코드에 게시물과 파일 연도를 연결하고, 키워드 원소를 순서대로 이어 입력 13개 컬럼을 만들었다. 정렬 기준은 `input_row_no`다. 키워드 연결로 늘어난 행에 반응 수치를 붙이거나 합산하지 않았다.",
        "",
        "## 8. 재로딩",
        "",
        "각 테이블을 Parquet과 UTF-8 BOM CSV로 저장한 뒤 다시 읽어 자료형과 값을 비교했다. CSV의 작성 시각은 오프셋을 해석한 뒤 Asia/Seoul로 맞춘다. 조회수의 빈 칸만 결측이다.",
        "",
        "## 9. 미해결 사항",
        "",
        context["unresolved"],  # type: ignore[arg-type]
        "",
        "## 10. 재실행",
        "",
        "```text",
        "py -3.11 normalize_x_tables.py",
        "```",
        "",
        f"작업 디렉터리와 무관하게 스크립트 위치 `{NORMALIZED_DIR}` 기준으로 입력과 결과를 찾는다. 다시 실행하면 `normalized`의 결과 파일만 덮어쓴다.",
        "",
        "## 11. 입력 파일",
        "",
        "입력 Parquet, 자료형 보고서, 자료형 정의서는 수정하지 않았다.",
        "",
        markdown_table(
            ["파일", "SHA-256", "실행 후 동일"],
            [
                [
                    path.name,
                    str(before[str(path)]["sha256"]),
                    "예" if before[str(path)] == after[str(path)] else "아니오",
                ]
                for path in (INPUT_PARQUET, REFERENCE_REPORT, REFERENCE_DEFINITION)
            ],
        ),
        "",
        "## 12. 결과물",
        "",
    ]
    for name in TABLE_SPECS:
        lines.append(f"- `{NORMALIZED_DIR / (name + '.parquet')}`")
        lines.append(f"- `{NORMALIZED_DIR / (name + '.csv')}`")
    lines.append(f"- `{NORMALIZED_DIR / 'normalize_x_tables.py'}`")
    lines.append(f"- `{OUTPUT_DEFINITION}`")
    lines.append(f"- `{OUTPUT_REPORT}`")
    lines.append("")
    return "\n".join(lines)


def render_conflict_report(error: NormalizationConflict, versions: dict[str, str]) -> str:
    return "\n".join(
        [
            "# X 게시물 관계형 정규화 보고서",
            "",
            f"- 생성 시각: {datetime.now(ZoneInfo(SEOUL)).isoformat(timespec='seconds')}",
            f"- Python: {versions['python']}",
            f"- pandas: {versions['pandas']}",
            "- 검증: 중단",
            "",
            "관계를 임의로 고치지 않고 테이블 저장 전에 중단했다.",
            "",
            f"## {error.title}",
            "",
            "```text",
            error.detail,
            "```",
            "",
            "## 처리안",
            "",
            error.proposal,
            "",
            "## 재실행",
            "",
            "```text",
            "py -3.11 normalize_x_tables.py",
            "```",
            "",
        ]
    )


def versions() -> dict[str, str]:
    import pyarrow

    return {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
    }


def print_summary(original_rows: int, tables: dict[str, pd.DataFrame], checks: list[tuple[str, bool, str]], restored_ok: bool) -> None:
    print(f"입력 게시물: {original_rows}")
    for name, frame in tables.items():
        print(f"{name}: {len(frame)}")
    failed = [name for name, ok, _ in checks if not ok]
    print("PK·FK 검증: 통과" if not failed else "PK·FK 검증: 실패 " + ", ".join(failed))
    print("원본 복원: 일치" if restored_ok else "원본 복원: 불일치")
    print(f"결과 경로: {NORMALIZED_DIR}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    info = versions()
    protected = [INPUT_PARQUET, REFERENCE_REPORT, REFERENCE_DEFINITION]
    try:
        before = {str(path): fingerprint(path) for path in protected}
        read_reference_contract()
        loaded = load_input()
        original = loaded[ORIGINAL_COLUMNS].copy()
        tables = build_tables(original)
        keyword_frame = (
            tables["x_post_keywords"].groupby("keyword", sort=False).size().rename("appearances").reset_index().sort_values("keyword", kind="mergesort")
        )
        checks: list[tuple[str, bool, str]] = []
        checks.extend(validate_primary_keys(tables))
        checks.extend(validate_foreign_keys(tables))
        order_ok, order_detail = validate_keyword_order(tables["x_post_keywords"])
        checks.append(("키워드 순서 연속", order_ok, order_detail))
        input_numbers = tables["x_post_sources"]["input_row_no"]
        input_ok = (
            null_count(input_numbers) == 0
            and duplicate_count(tables["x_post_sources"], ["input_row_no"]) == 0
            and int(input_numbers.min()) == 1
            and int(input_numbers.max()) == len(original)
        )
        checks.append(("input_row_no 1..N 고유", input_ok, f"최소 {int(input_numbers.min())}, 최대 {int(input_numbers.max())}"))
        checks.extend(preservation_checks(original.assign(post_id=extract_post_id(original["게시물 링크"])), tables["x_posts"]))
        restored = restore_original(tables)
        memory_ok, memory_detail = compare_frames(original, restored)
        checks.append(("메모리에서 원본 13컬럼 복원", memory_ok, memory_detail))
        if not all(ok for _, ok, _ in checks):
            failed = "\n".join(f"{name}: {detail}" for name, ok, detail in checks if not ok)
            raise RuntimeError(f"저장 전 검증에 실패했다. 테이블 파일을 쓰지 않았다.\n{failed}")

        engine = parquet_engine()
        write_tables(tables, engine)
        for kind in ("parquet", "csv"):
            reloaded = reload_tables(engine, kind)
            for name in TABLE_SPECS:
                same, detail = compare_frames(tables[name], reloaded[name])
                checks.append((f"{name} {kind} 재로딩", same, detail))
            restored_again = restore_original(reloaded)
            again_ok, again_detail = compare_frames(original, restored_again)
            checks.append((f"{kind} 재로딩 후 원본 복원", again_ok, again_detail))

        after = {str(path): fingerprint(path) for path in protected}
        unchanged = all(before[str(path)] == after[str(path)] for path in protected)
        checks.append(("입력 파일 미변경", unchanged, "Parquet, 보고서, 정의서의 지문이 같다" if unchanged else "입력 지문이 달라졌다"))

        unresolved = "\n".join(
            [
                "관계 충돌과 모호한 키워드 구분자는 없었다. 대표값을 고르는 단계는 없었다.",
                "",
                "아래는 고치지 않고 그대로 둔 값이다.",
                "",
                "- 계정 이름 문자열 `null` 2건은 결측이 아니다.",
                "- 계정 이름 앞뒤 공백 1건은 원문이다.",
                "- 조회수 결측 946건은 비워 두었다.",
                "- 작성 시각의 연도와 `source_year`는 이번 5,000건에서 같았지만 의미가 다르다. 어느 한쪽으로 대체하지 않았다.",
            ]
        )
        context = {
            "created_at": datetime.now(ZoneInfo(SEOUL)).isoformat(timespec="seconds"),
            "original": original.assign(post_id=extract_post_id(original["게시물 링크"])),
            "tables": tables,
            "checks": checks,
            "dependencies": functional_dependency_rows(context_frame(original)),
            "keyword_examples": keyword_examples(original),
            "keyword_counts": list(keyword_frame.itertuples(index=False)),
            "before": before,
            "after": after,
            "versions": info,
            "unresolved": unresolved,
        }
        OUTPUT_DEFINITION.write_text(render_definitions(tables), encoding="utf-8", newline="\n")
        OUTPUT_REPORT.write_text(render_report(context), encoding="utf-8", newline="\n")
        restored_flags = [ok for name, ok, _ in checks if "원본" in name and "복원" in name]
        print_summary(len(original), tables, checks, all(restored_flags))
        if not all(ok for _, ok, _ in checks):
            print("검증 실패:")
            for name, ok, detail in checks:
                if not ok:
                    print(f"- {name}: {detail}")
            return 1
        return 0
    except NormalizationConflict as error:
        OUTPUT_REPORT.write_text(render_conflict_report(error, info), encoding="utf-8", newline="\n")
        print(error.title)
        print(error.proposal)
        return 2
    except Exception as error:
        print(f"FAILED: {error}")
        return 1


def context_frame(original: pd.DataFrame) -> pd.DataFrame:
    frame = original.copy()
    frame["post_id"] = extract_post_id(frame["게시물 링크"])
    return frame


if __name__ == "__main__":
    sys.exit(main())
