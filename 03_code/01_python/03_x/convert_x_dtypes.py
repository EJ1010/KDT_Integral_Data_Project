# -*- coding: utf-8 -*-
"""통합 CSV의 자료형을 확인하고 분석용 데이터로 변환한다.

입력은 integrated/x_chiikawa_2022_2026_merged_raw.csv 하나다.
원본 CSV, 통합 보고서, 기존 컬럼 사전은 읽기만 한다.
재실행하면 typed 결과를 원본에서 다시 만든다.

실행:
    py -3.11 convert_x_dtypes.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:
    print("PANDAS_MISSING: run this script with Python 3.11 (py -3.11).")
    sys.exit(1)


TYPED_DIR = Path(__file__).resolve().parent
DATA_DIR = TYPED_DIR.parent
INPUT_CSV = DATA_DIR / "integrated" / "x_chiikawa_2022_2026_merged_raw.csv"
REPORT_REFERENCE = DATA_DIR / "integrated" / "merge_report.md"
DICTIONARY_REFERENCE = DATA_DIR / "integrated" / "column_dictionary.csv"

OUTPUT_CSV = TYPED_DIR / "x_chiikawa_2022_2026_typed.csv"
OUTPUT_PARQUET = TYPED_DIR / "x_chiikawa_2022_2026_typed.parquet"
OUTPUT_REPORT = TYPED_DIR / "dtype_conversion_report.md"
OUTPUT_DEFINITION = TYPED_DIR / "x_typed_table_definition.csv"

EXPECTED_COLUMNS = [
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
STRING_COLUMNS = [
    "게시물 링크",
    "계정 ID",
    "본문",
    "계정 이름",
    "키워드",
    "source_file",
]
REQUIRED_INT_COLUMNS = ["댓글 개수", "리포스트 개수", "좋아요 수", "source_row", "source_year"]
OPTIONAL_INT_COLUMNS = ["조회수"]
INT_COLUMNS = REQUIRED_INT_COLUMNS + OPTIONAL_INT_COLUMNS
DATETIME_COLUMN = "작성 시각"
SEOUL = "Asia/Seoul"
NAIVE_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
EXPLICIT_TIMEZONE = re.compile(r"(?:Z|[+-]\d{2}:\d{2}|[+-]\d{4}|UTC|GMT|KST)$", re.IGNORECASE)
CANONICAL_INT = re.compile(r"^(?:0|[1-9]\d*)$")
STATUS_ID = re.compile(r"/status/(\d+)")
INT64_MAX = 2**63 - 1
SENTINEL_TOKENS = ("NA", "NULL", "N/A", "NaN", "nan", "None", "null", "<NA>", "NaT")

COLUMN_SPECS = {
    "게시물 링크": {
        "description": "X 게시물 URL",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "문자열을 그대로 유지한다. 게시물 ID는 검증 때 임시로만 추출하고 컬럼으로 저장하지 않는다.",
    },
    "계정 ID": {
        "description": "게시 계정 ID",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "문자열을 그대로 유지한다. 계정 식별자를 숫자로 변환하지 않는다.",
    },
    "댓글 개수": {
        "description": "댓글 수",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "rule": "0 또는 앞자리 0이 없는 양의 정수만 Int64로 변환한다. 기존 0은 유지하고, 빈 값·음수·소수·축약 표기는 변환 실패로 기록한다.",
    },
    "리포스트 개수": {
        "description": "리포스트 수",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "rule": "0 또는 앞자리 0이 없는 양의 정수만 Int64로 변환한다. 기존 0은 유지하고, 빈 값·음수·소수·축약 표기는 변환 실패로 기록한다.",
    },
    "본문": {
        "description": "게시물 본문",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "줄바꿈과 기호를 포함한 원문을 그대로 유지한다. 내용을 삭제·치환·정리하지 않는다.",
    },
    "계정 이름": {
        "description": "계정 표시 이름",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "원문을 그대로 유지한다. 문자열 null은 결측으로 바꾸지 않고 확인 필요 사항으로 둔다. 앞뒤 공백도 제거하지 않는다.",
    },
    "작성 시각": {
        "description": "게시 작성 시각. 한국시간",
        "sql": "TIMESTAMP WITH TIME ZONE",
        "null_policy": "비허용",
        "rule": "시간대가 없는 값은 한국시간 문자열로 보고 Asia/Seoul을 지정한다. UTC로 간주해 9시간을 더하지 않는다. 명시적 시간대가 있으면 그 시간대를 해석한 뒤 Asia/Seoul로 변환한다.",
    },
    "조회수": {
        "description": "조회수",
        "sql": "BIGINT",
        "null_policy": "허용",
        "rule": "빈 문자열만 pd.NA로 둔다. 0이나 평균으로 채우지 않는다. 값이 있는 칸은 정확한 정수만 Int64로 변환한다.",
    },
    "좋아요 수": {
        "description": "좋아요 수",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "rule": "0 또는 앞자리 0이 없는 양의 정수만 Int64로 변환한다. 기존 0은 유지하고, 빈 값·음수·소수·축약 표기는 변환 실패로 기록한다.",
    },
    "키워드": {
        "description": "수집 키워드",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "원문을 그대로 유지한다. 구분 기호로 나누거나 내용을 정리하지 않는다.",
    },
    "source_file": {
        "description": "원본 파일명",
        "sql": "TEXT",
        "null_policy": "비허용",
        "rule": "통합 단계에서 추가한 파일명 문자열을 그대로 유지한다.",
    },
    "source_row": {
        "description": "헤더를 제외한 원본 CSV 레코드 순번. 1부터 시작하며 물리 줄 번호가 아니다",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "rule": "정확한 양의 정수를 Int64로 변환한다.",
    },
    "source_year": {
        "description": "원본 파일명에서 추출한 연도",
        "sql": "BIGINT",
        "null_policy": "비허용",
        "rule": "정확한 연도 정수를 Int64로 변환한다. 작성 시각의 한국시간 연도와 같은지 검증한다.",
    },
}


class ConversionError(Exception):
    def __init__(self, message: str, failures: list[dict[str, object]]):
        super().__init__(message)
        self.message = message
        self.failures = failures


def read_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype="string",
        na_filter=False,
        keep_default_na=False,
        encoding="utf-8-sig",
        sep=",",
        quotechar='"',
        doublequote=True,
        skipinitialspace=False,
        skip_blank_lines=False,
        header=0,
        index_col=None,
        on_bad_lines="error",
        engine="c",
    )


def fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def info_text(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.info(buf=buffer)
    return buffer.getvalue().rstrip("\n")


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    head = "| " + " | ".join(cell(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join([head, separator, *body])


def empty_profile(frame: pd.DataFrame) -> list[dict[str, object]]:
    profile = []
    for column in frame.columns:
        values = frame[column]
        if str(values.dtype) == "string":
            empty = int((values == "").sum())
            whitespace = int(((values != "") & (values.str.strip() == "")).sum())
            strip_diff = int((values != values.str.strip()).sum())
        else:
            empty = ""
            whitespace = ""
            strip_diff = ""
        profile.append(
            {
                "column": str(column),
                "dtype": str(values.dtype),
                "pandas_na": int(values.isna().sum()),
                "empty": empty,
                "whitespace": whitespace,
                "strip_diff": strip_diff,
            }
        )
    return profile


def sentinel_hits(frame: pd.DataFrame) -> list[tuple[str, str, int]]:
    found = []
    for column in frame.columns:
        if str(frame[column].dtype) != "string":
            continue
        for token in SENTINEL_TOKENS:
            count = int((frame[column] == token).sum())
            if count:
                found.append((str(column), token, count))
    return found


def failure_row(frame: pd.DataFrame, index: int, column: str, original: str, reason: str) -> dict[str, object]:
    return {
        "index": index + 1,
        "source_file": frame.at[index, "source_file"] if "source_file" in frame.columns else "",
        "source_row": frame.at[index, "source_row"] if "source_row" in frame.columns else "",
        "column": column,
        "original": original,
        "reason": reason,
    }


def convert_integers(frame: pd.DataFrame) -> tuple[dict[str, pd.Series], list[dict[str, object]]]:
    converted: dict[str, pd.Series] = {}
    failures: list[dict[str, object]] = []
    for column in INT_COLUMNS:
        optional_blank = column in OPTIONAL_INT_COLUMNS
        values: list[object] = []
        for index, original in enumerate(frame[column].tolist()):
            if original == "":
                if optional_blank:
                    values.append(pd.NA)
                else:
                    failures.append(failure_row(frame, index, column, original, "필수 정수 컬럼의 빈 문자열"))
                    values.append(pd.NA)
                continue
            if not CANONICAL_INT.fullmatch(original):
                failures.append(
                    failure_row(
                        frame,
                        index,
                        column,
                        original,
                        "정확한 비음수 정수가 아님. 음수·소수·축약 표기·공백·앞자리 0은 변환하지 않음",
                    )
                )
                values.append(pd.NA)
                continue
            number = int(original)
            if number > INT64_MAX:
                failures.append(failure_row(frame, index, column, original, "Int64 범위를 초과"))
                values.append(pd.NA)
                continue
            values.append(number)
        converted[column] = pd.Series(pd.array(values, dtype="Int64"), index=frame.index, name=column)
    return converted, failures


def convert_datetimes(frame: pd.DataFrame) -> tuple[pd.Series, list[dict[str, object]]]:
    originals = frame[DATETIME_COLUMN].tolist()
    parsed: list[pd.Timestamp] = []
    failures: list[dict[str, object]] = []
    for index, original in enumerate(originals):
        try:
            parsed.append(parse_datetime_text(original))
        except ValueError as exc:
            failures.append(failure_row(frame, index, DATETIME_COLUMN, original, str(exc)))
            parsed.append(pd.NaT)
    series = pd.Series(parsed, index=frame.index, name=DATETIME_COLUMN)
    series = series.astype("datetime64[ns, Asia/Seoul]")
    return series, failures


def parse_datetime_text(original: str) -> pd.Timestamp:
    if original == "":
        raise ValueError("작성 시각이 비어 있음")
    if NAIVE_DATETIME.fullmatch(original):
        timestamp = pd.to_datetime(original, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        if pd.isna(timestamp):
            raise ValueError("달력에 없는 날짜이거나 시각 형식이 아님")
        return timestamp.tz_localize(SEOUL)
    if EXPLICIT_TIMEZONE.search(original):
        timestamp = pd.to_datetime(original, errors="coerce", utc=True)
        if pd.isna(timestamp):
            raise ValueError("명시적 시간대를 해석하지 못함")
        return timestamp.tz_convert(SEOUL)
    raise ValueError("시간대 없는 한국시간 형식도 아니고 명시적 시간대도 아님")


def convert_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ConversionError(
            "컬럼 구성이 목표 매핑과 다르다.",
            [
                {
                    "index": "",
                    "source_file": "",
                    "source_row": "",
                    "column": "",
                    "original": str(list(frame.columns)),
                    "reason": f"기대 컬럼 {EXPECTED_COLUMNS}",
                }
            ],
        )
    integers, failures = convert_integers(frame)
    datetimes, datetime_failures = convert_datetimes(frame)
    failures.extend(datetime_failures)
    typed = pd.DataFrame(index=frame.index)
    for column in EXPECTED_COLUMNS:
        if column in STRING_COLUMNS:
            typed[column] = frame[column].astype("string")
        elif column in INT_COLUMNS:
            typed[column] = integers[column]
        else:
            typed[column] = datetimes
    typed = typed[EXPECTED_COLUMNS]
    return typed, failures


def load_typed_csv(path: str | Path) -> pd.DataFrame:
    """저장 CSV를 명시적 자료형으로 다시 읽는다.

    CSV는 pandas 자료형과 시간대를 저장하지 못한다.
    빈 조회수는 결측으로 두고, 시간대 없는 작성 시각은 Asia/Seoul로 지정한다.
    시간대가 적힌 값은 그 시간대를 해석한 뒤 한국시간으로 맞춘다.
    """

    raw = read_raw(Path(path))
    typed, failures = convert_frame(raw)
    if failures:
        first = failures[0]
        raise ValueError(
            f"typed CSV reload failed: {len(failures)} values, "
            f"first row {first['index']} column {first['column']}: {first['reason']}"
        )
    return typed


def parquet_engine() -> str | None:
    try:
        import pyarrow  # noqa: F401
    except ModuleNotFoundError:
        return None
    return "pyarrow"


def write_csv(path: Path, typed: pd.DataFrame) -> None:
    export = typed.copy()
    export[DATETIME_COLUMN] = typed[DATETIME_COLUMN].map(
        lambda value: value.isoformat(sep=" ", timespec="seconds")
    )
    export.to_csv(path, index=False, encoding="utf-8-sig", na_rep="", lineterminator="\n")


def write_definition(path: Path, typed: pd.DataFrame) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "실제 컬럼명",
                "설명",
                "변환 전 타입",
                "변환 후 pandas 타입",
                "SQL 대응 타입",
                "NULL 허용 여부",
                "실제 결측 건수",
                "변환 규칙",
            ]
        )
        for column in EXPECTED_COLUMNS:
            spec = COLUMN_SPECS[column]
            writer.writerow(
                [
                    column,
                    spec["description"],
                    "string",
                    str(typed.dtypes[column]),
                    spec["sql"],
                    spec["null_policy"],
                    int(typed[column].isna().sum()),
                    spec["rule"],
                ]
            )


def post_id_summary(links: pd.Series) -> dict[str, int]:
    extracted = links.map(lambda value: matched.group(1) if (matched := STATUS_ID.search(value)) else "")
    filled = extracted[extracted != ""]
    return {
        "rows": len(links),
        "extracted": int((extracted != "").sum()),
        "missing": int((extracted == "").sum()),
        "unique": int(filled.nunique()),
        "duplicate_ids": int((filled.value_counts() >= 2).sum()),
    }


def clock_text(series: pd.Series) -> pd.Series:
    return series.dt.strftime("%Y-%m-%d %H:%M:%S").astype("string")


def compare_frames(left: pd.DataFrame, right: pd.DataFrame) -> tuple[bool, str]:
    if list(left.columns) != list(right.columns):
        return False, f"columns {list(left.columns)} != {list(right.columns)}"
    if len(left) != len(right):
        return False, f"rows {len(left)} != {len(right)}"
    for column in left.columns:
        left_dtype = str(left.dtypes[column])
        right_dtype = str(right.dtypes[column])
        if left_dtype != right_dtype:
            return False, f"{column} dtype {left_dtype} != {right_dtype}"
        if not left[column].equals(right[column]):
            mismatch = (left[column] != right[column]) & ~(left[column].isna() & right[column].isna())
            position = int(mismatch.to_numpy().nonzero()[0][0]) + 1 if mismatch.any() else 0
            return False, f"{column} value differs at row {position}"
    return True, "값, 행 수, 자료형이 같다"


def render_report(context: dict[str, object]) -> str:
    raw: pd.DataFrame = context["raw"]  # type: ignore[assignment]
    typed: pd.DataFrame = context["typed"]  # type: ignore[assignment]
    checks: list[tuple[str, bool, str]] = context["checks"]  # type: ignore[assignment]
    passed = all(ok for _, ok, _ in checks)
    lines = [
        "# X CSV 자료형 변환 보고서",
        "",
        f"- 생성 시각: {context['generated_at']}",
        f"- Python: {context['python_version']}",
        f"- pandas: {context['pandas_version']}",
        f"- 입력: `{context['input_path']}`",
        f"- 검증: {'통과' if passed else '실패'}",
        "",
        "이번 작업은 자료형 확인과 분석용 변환이다. 행 삭제, 중복 제거, 관련성 판단, 본문 수정, 캐릭터·소비 형태 분류는 하지 않았다.",
        "",
        "## 1. 보고서와 실제 데이터",
        "",
        "통합 보고서는 5,000행, 13개 컬럼, 전부 문자열, pandas 결측 0건, 조회수 빈 문자열 946건(2022년), 계정 이름 문자열 `null` 2건, 게시물 ID 5,000개 고유를 기록했다. 실제 컬럼은 `댓글 개수`가 있고 `계정 소개글`은 없다.",
        "",
        md_table(
            ["항목", "보고서", "실제", "결과"],
            context["reconciliation"],  # type: ignore[arg-type]
        ),
        "",
        "실제 확인 결과가 보고서와 같다. `계정 소개글` 컬럼은 만들지 않았다.",
        "",
        "## 2. 변환 전",
        "",
        "읽기 옵션은 `dtype='string'`, `na_filter=False`, `keep_default_na=False`, `encoding='utf-8-sig'`, `on_bad_lines='error'` 이다. pandas 결측과 빈 문자열은 따로 센다.",
        "",
        "```text",
        context["info_before"],  # type: ignore[arg-type]
        "```",
        "",
        "변환 전 dtype:",
        "",
        md_table(
            ["컬럼", "dtype"],
            [[column, str(raw.dtypes[column])] for column in raw.columns],
        ),
        "",
        md_table(
            ["컬럼", "dtype", "pandas 결측", "빈 문자열", "공백만", "앞뒤 공백이 원문과 다름"],
            [
                [
                    item["column"],
                    item["dtype"],
                    item["pandas_na"],
                    item["empty"],
                    item["whitespace"],
                    item["strip_diff"],
                ]
                for item in context["profile_before"]  # type: ignore[union-attr]
            ],
        ),
        "",
        "정확히 일치하는 특수 토큰:",
        "",
    ]
    tokens = context["tokens"]
    if tokens:
        lines.append(md_table(["컬럼", "토큰", "건수"], tokens))  # type: ignore[arg-type]
    else:
        lines.append("해당 토큰과 같은 셀은 없다.")
    lines.extend(
        [
            "",
            "확인한 토큰: " + ", ".join(f"`{token}`" for token in SENTINEL_TOKENS) + ".",
            "",
            "## 3. 변환 규칙",
            "",
            "- 문자열 컬럼은 원문을 유지했다. 계정 ID와 게시물 링크는 숫자로 바꾸지 않았다.",
            "- 정수 컬럼은 0과 앞자리 0이 없는 양의 정수만 Int64로 바꿨다. 기존 0은 그대로다.",
            "- 조회수의 빈 문자열 946건만 `pd.NA`로 바꿨다. 0이나 평균으로 채우지 않았다.",
            "- 계정 이름의 문자열 `null` 2건은 원문으로 남겼다. 실제 누락인지는 정하지 않았다.",
            "- 작성 시각 5,000건은 시간대가 없는 `YYYY-MM-DD HH:MM:SS` 였다. 시계의 숫자는 그대로 두고 `Asia/Seoul`을 지정했다.",
            "",
            "## 4. 변환 후",
            "",
            "```text",
            context["info_after"],  # type: ignore[arg-type]
            "```",
            "",
            md_table(
                ["컬럼", "변환 전", "변환 후", "pandas 결측"],
                [
                    [column, "string", str(typed.dtypes[column]), int(typed[column].isna().sum())]
                    for column in typed.columns
                ],
            ),
            "",
            "### 조회수 결측",
            "",
            md_table(
                ["source_year", "행 수", "조회수 결측"],
                context["view_by_year"],  # type: ignore[arg-type]
            ),
            "",
            f"조회수 결측 {context['view_na']}건은 모두 2022년이다. 변환 전 빈 문자열 건수와 같다. 이 결측은 변환 오류가 아니다.",
            "",
            "### 계정 이름 문자열 null",
            "",
            "아래 2건의 계정 이름은 문자열 `null` 그대로다. pandas 결측으로 바꾸지 않았다.",
            "",
            md_table(
                ["source_file", "source_row", "계정 ID", "계정 이름", "게시물 링크"],
                context["null_names"],  # type: ignore[arg-type]
            ),
            "",
            "### 앞뒤 공백이 있는 계정 이름",
            "",
            "문자열을 정리하지 않았으므로 앞뒤 공백도 원문 그대로 남겼다.",
            "",
            md_table(
                ["source_file", "source_row", "계정 ID", "계정 이름 원문"],
                context["padded_names"],  # type: ignore[arg-type]
            ),
            "",
            "## 5. 검증",
            "",
            md_table(
                ["항목", "결과", "내용"],
                [[name, "통과" if ok else "실패", detail] for name, ok, detail in checks],
            ),
            "",
            "## 6. 변환 실패",
            "",
            f"변환 실패 {context['failure_count']}건.",
            "",
            "조회수 빈 문자열을 결측으로 둔 것은 실패 건수에 넣지 않았다.",
            "",
            "## 7. 저장과 재로딩",
            "",
            "CSV는 셀 텍스트만 저장하고 Int64, 결측, `Asia/Seoul` 시간대를 자료형으로 저장하지 못한다. 다시 읽을 때는 `load_typed_csv()`가 명시적 dtype과 날짜 규칙을 적용한다.",
            "",
            f"- 분석용 CSV: `{context['csv_path']}`",
            f"- CSV 재로딩: {context['csv_reload']}",
            f"- Parquet: {context['parquet_note']}",
            "",
            "Parquet 저장에는 설치되어 있던 pyarrow를 사용했다. 패키지를 새로 설치하지 않았다.",
            "",
            "## 8. 입력 파일",
            "",
            "입력 CSV, 통합 보고서, 기존 컬럼 사전은 수정하지 않았다.",
            "",
            md_table(
                ["파일", "SHA-256", "실행 후 동일"],
                context["inputs"],  # type: ignore[arg-type]
            ),
            "",
            "## 9. 결과물",
            "",
            f"- `{TYPED_DIR / 'convert_x_dtypes.py'}`",
            f"- `{OUTPUT_CSV}`",
            f"- `{OUTPUT_PARQUET}`",
            f"- `{OUTPUT_REPORT}`",
            f"- `{OUTPUT_DEFINITION}`",
            "",
        ]
    )
    return "\n".join(lines)


def render_failure_report(message: str, failures: list[dict[str, object]], extra: str = "") -> str:
    lines = [
        "# X CSV 자료형 변환 보고서",
        "",
        f"- 생성 시각: {datetime.now().isoformat(timespec='seconds')}",
        "- 검증: 보류",
        "",
        message,
        "",
        "분석용 CSV와 Parquet는 저장하지 않았다. 실패 값을 결측이나 0으로 바꾸지 않았다.",
        "",
        "## 확인이 필요한 값",
        "",
    ]
    if failures:
        lines.append(
            md_table(
                ["행", "source_file", "source_row", "컬럼", "원문", "사유"],
                [
                    [
                        item["index"],
                        item["source_file"],
                        item["source_row"],
                        item["column"],
                        item["original"],
                        item["reason"],
                    ]
                    for item in failures[:50]
                ],
            )
        )
        lines.append("")
        if len(failures) > 50:
            lines.append(f"외 {len(failures) - 50}건이 더 있다.")
            lines.append("")
    lines.extend(
        [
            "## 제안",
            "",
            "해당 원문을 유지한 채 변환 규칙을 어떻게 둘지 확인해 주세요. 확인 전에는 0, 평균, 결측으로 대체하지 않습니다.",
            "",
        ]
    )
    if extra:
        lines.extend(["## 상세", "", "```text", extra.rstrip(), "```", ""])
    return "\n".join(lines)


def remove_partial_outputs() -> None:
    for path in (OUTPUT_CSV, OUTPUT_PARQUET, OUTPUT_DEFINITION):
        if path.exists():
            path.unlink()


def build_checks(raw: pd.DataFrame, typed: pd.DataFrame) -> tuple[list[tuple[str, bool, str]], dict[str, object]]:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("행 수 유지", len(raw) == len(typed) == 5000, f"{len(raw)} -> {len(typed)}"))
    checks.append(
        (
            "컬럼 13개와 순서 유지",
            list(raw.columns) == list(typed.columns) == EXPECTED_COLUMNS,
            f"{len(typed.columns)} columns",
        )
    )
    string_ok = all(raw[column].equals(typed[column]) for column in STRING_COLUMNS)
    checks.append(("문자열 원문 유지", string_ok, "6개 문자열 컬럼이 변환 전과 같다" if string_ok else "불일치"))

    integer_ok = True
    integer_detail = "반응 수치와 추적 정수가 원문 정수와 같다"
    for column in REQUIRED_INT_COLUMNS:
        current = typed[column].astype("string")
        if not current.equals(raw[column]):
            integer_ok = False
            integer_detail = f"{column} 값이 달라졌다"
            break
    view_filled = raw["조회수"] != ""
    view_values_ok = typed.loc[view_filled, "조회수"].astype("string").equals(raw.loc[view_filled, "조회수"])
    if not view_values_ok:
        integer_ok = False
        integer_detail = "조회수 있는 값의 정수가 달라졌다"
    checks.append(("정수 값 유지", integer_ok and view_values_ok, integer_detail))

    zero_ok = True
    zero_bits = []
    for column in ("댓글 개수", "리포스트 개수", "좋아요 수"):
        before = int((raw[column] == "0").sum())
        after = int((typed[column] == 0).sum())
        zero_bits.append(f"{column} {before}->{after}")
        if before != after:
            zero_ok = False
    checks.append(("기존 0 유지", zero_ok, ", ".join(zero_bits)))

    view_na_mask = typed["조회수"].isna()
    view_empty_mask = raw["조회수"] == ""
    same_positions = bool((view_na_mask.to_numpy() == view_empty_mask.to_numpy()).all())
    view_year_ok = bool((typed.loc[view_na_mask.to_numpy(), "source_year"] == 2022).all()) if view_na_mask.any() else False
    checks.append(
        (
            "조회수 빈 문자열을 결측으로 변환",
            same_positions and int(view_na_mask.sum()) == 946 and view_year_ok,
            f"결측 {int(view_na_mask.sum())}건, 2022년 일치 {view_year_ok}",
        )
    )
    other_na = int(typed.drop(columns=["조회수"]).isna().sum().sum())
    checks.append(("조회수 외 결측 없음", other_na == 0, f"기타 pandas 결측 {other_na}건"))

    null_name_ok = int((typed["계정 이름"] == "null").sum()) == 2 and int(typed["계정 이름"].isna().sum()) == 0
    checks.append(("계정 이름 문자열 null 유지", null_name_ok, "2건을 문자열로 유지"))

    clocks = clock_text(typed[DATETIME_COLUMN])
    clock_ok = clocks.equals(raw[DATETIME_COLUMN])
    checks.append(("작성 시각의 시계 유지", clock_ok, "Asia/Seoul 지정 후 시·분·초가 원문과 같다" if clock_ok else "시계가 이동했다"))
    year_ok = typed[DATETIME_COLUMN].dt.year.astype("Int64").equals(typed["source_year"])
    checks.append(("작성 시각 연도와 source_year", year_ok, "5,000건 일치" if year_ok else "불일치"))

    ids = post_id_summary(typed["게시물 링크"])
    id_ok = ids["extracted"] == 5000 and ids["unique"] == 5000 and ids["duplicate_ids"] == 0
    checks.append(
        (
            "게시물 ID 고유",
            id_ok,
            f"추출 {ids['extracted']}, 고유 {ids['unique']}, 중복 ID {ids['duplicate_ids']}",
        )
    )

    dtype_ok = True
    dtype_detail = "목표 자료형과 같다"
    expected_dtype = {column: "string" for column in STRING_COLUMNS}
    expected_dtype.update({column: "Int64" for column in INT_COLUMNS})
    expected_dtype[DATETIME_COLUMN] = "datetime64[ns, Asia/Seoul]"
    for column, expected in expected_dtype.items():
        actual = str(typed.dtypes[column])
        if actual != expected:
            dtype_ok = False
            dtype_detail = f"{column}: {actual} != {expected}"
            break
    checks.append(("목표 자료형", dtype_ok, dtype_detail))
    return checks, {"ids": ids, "view_na": int(view_na_mask.sum())}


def view_year_table(typed: pd.DataFrame) -> list[list[object]]:
    grouped = (
        typed.groupby("source_year", sort=True)
        .agg(rows=("조회수", "size"), missing=("조회수", lambda values: int(values.isna().sum())))
        .reset_index()
    )
    return [[int(row.source_year), int(row.rows), int(row.missing)] for row in grouped.itertuples(index=False)]


def reconciliation_rows(raw: pd.DataFrame) -> list[list[object]]:
    ids = post_id_summary(raw["게시물 링크"])
    view_2022 = int(((raw["조회수"] == "") & (raw["source_year"] == "2022")).sum())
    actual = {
        "행 수": len(raw),
        "컬럼 수": raw.shape[1],
        "pandas 결측": int(raw.isna().sum().sum()),
        "조회수 빈 문자열": int((raw["조회수"] == "").sum()),
        "조회수 빈 문자열 중 2022년": view_2022,
        "계정 이름 문자열 null": int((raw["계정 이름"] == "null").sum()),
        "게시물 ID 고유": ids["unique"],
        "댓글 개수 컬럼": "있음" if "댓글 개수" in raw.columns else "없음",
        "계정 소개글 컬럼": "있음" if "계정 소개글" in raw.columns else "없음",
    }
    expected = {
        "행 수": 5000,
        "컬럼 수": 13,
        "pandas 결측": 0,
        "조회수 빈 문자열": 946,
        "조회수 빈 문자열 중 2022년": 946,
        "계정 이름 문자열 null": 2,
        "게시물 ID 고유": 5000,
        "댓글 개수 컬럼": "있음",
        "계정 소개글 컬럼": "없음",
    }
    rows = []
    for name, report_value in expected.items():
        current = actual[name]
        rows.append([name, report_value, current, "일치" if current == report_value else "차이"])
    return rows


def null_name_rows(frame: pd.DataFrame) -> list[list[object]]:
    subset = frame.loc[frame["계정 이름"] == "null", ["source_file", "source_row", "계정 ID", "계정 이름", "게시물 링크"]]
    return subset.astype("string").values.tolist()


def padded_name_rows(frame: pd.DataFrame) -> list[list[object]]:
    mask = frame["계정 이름"] != frame["계정 이름"].str.strip()
    subset = frame.loc[mask, ["source_file", "source_row", "계정 ID", "계정 이름"]]
    return [[*row[:3], repr(row[3])] for row in subset.astype("string").values.tolist()]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    TYPED_DIR.mkdir(parents=True, exist_ok=True)
    protected = [INPUT_CSV, REPORT_REFERENCE, DICTIONARY_REFERENCE]
    missing = [path for path in protected if not path.is_file()]
    if missing:
        remove_partial_outputs()
        OUTPUT_REPORT.write_text(
            render_failure_report("참고 파일 또는 입력 CSV가 없다.", [], "\n".join(str(path) for path in missing)),
            encoding="utf-8",
            newline="\n",
        )
        print("VALIDATION=FAIL")
        print(f"REPORT={OUTPUT_REPORT}")
        return 1

    before = {path: fingerprint(path) for path in protected}
    try:
        raw = read_raw(INPUT_CSV)
        if list(raw.columns) != EXPECTED_COLUMNS:
            raise ConversionError("실제 컬럼이 목표 13개 컬럼과 다르다.", [])
        typed, failures = convert_frame(raw)
        if failures:
            raise ConversionError(
                "예상하지 않은 값이 있어 분석용 파일을 저장하지 않았다.",
                failures,
            )
        checks, metrics = build_checks(raw, typed)
        write_csv(OUTPUT_CSV, typed)
        reloaded = load_typed_csv(OUTPUT_CSV)
        csv_ok, csv_detail = compare_frames(typed, reloaded)
        checks.append(("CSV 재로딩", csv_ok, csv_detail))

        engine = parquet_engine()
        if engine is None:
            parquet_note = "pyarrow와 fastparquet가 없어 Parquet은 만들지 않았다. 패키지는 설치하지 않았다."
            checks.append(("Parquet 재로딩", False, "지원 패키지 없음"))
        else:
            typed.to_parquet(OUTPUT_PARQUET, index=False, engine=engine)
            parquet_back = pd.read_parquet(OUTPUT_PARQUET, engine=engine)
            parquet_ok, parquet_detail = compare_frames(typed, parquet_back)
            checks.append(("Parquet 재로딩", parquet_ok, parquet_detail))
            parquet_note = f"`{OUTPUT_PARQUET}` 를 {engine}로 저장하고 다시 읽었다. {parquet_detail}"

        after = {path: fingerprint(path) for path in protected}
        unchanged = all(before[path] == after[path] for path in protected)
        checks.append(("입력 파일 미변경", unchanged, "입력 CSV, 보고서, 컬럼 사전의 지문이 같다" if unchanged else "입력 지문이 달라졌다"))
        failed_checks = [f"{name}: {detail}" for name, ok, detail in checks if not ok]
        if failed_checks:
            raise ConversionError("변환 후 검증에 실패했다. " + " | ".join(failed_checks), [])

        write_definition(OUTPUT_DEFINITION, typed)
        input_rows = []
        for path in protected:
            input_rows.append([path.name, before[path]["sha256"], "예"])
        report = render_report(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "python_version": sys.version.split()[0],
                "pandas_version": pd.__version__,
                "input_path": str(INPUT_CSV),
                "raw": raw,
                "typed": typed,
                "checks": checks,
                "reconciliation": reconciliation_rows(raw),
                "info_before": info_text(raw),
                "info_after": info_text(typed),
                "profile_before": empty_profile(raw),
                "tokens": sentinel_hits(raw),
                "view_by_year": view_year_table(typed),
                "view_na": metrics["view_na"],
                "null_names": null_name_rows(raw),
                "padded_names": padded_name_rows(raw),
                "failure_count": 0,
                "csv_path": str(OUTPUT_CSV),
                "csv_reload": csv_detail,
                "parquet_note": parquet_note,
                "inputs": input_rows,
            }
        )
        OUTPUT_REPORT.write_text(report, encoding="utf-8", newline="\n")
    except ConversionError as exc:
        remove_partial_outputs()
        OUTPUT_REPORT.write_text(
            render_failure_report(exc.message, exc.failures),
            encoding="utf-8",
            newline="\n",
        )
        print("VALIDATION=FAIL")
        print(f"FAILURES={len(exc.failures)}")
        print(f"REPORT={OUTPUT_REPORT}")
        return 1
    except Exception:
        remove_partial_outputs()
        OUTPUT_REPORT.write_text(
            render_failure_report(
                "스크립트 실행 중 예외가 발생했다.",
                [],
                traceback.format_exc(),
            ),
            encoding="utf-8",
            newline="\n",
        )
        print("VALIDATION=FAIL")
        print(f"REPORT={OUTPUT_REPORT}")
        return 1

    print(f"ROWS={len(typed)}")
    print("DTYPE_CONVERSION=PASS")
    print(f"VIEW_NA={int(typed['조회수'].isna().sum())}")
    print("CONVERSION_FAILURES=0")
    print("RELOAD_CSV=PASS")
    print("RELOAD_PARQUET=PASS")
    print(f"SCRIPT={TYPED_DIR / 'convert_x_dtypes.py'}")
    print(f"CSV={OUTPUT_CSV}")
    print(f"PARQUET={OUTPUT_PARQUET}")
    print(f"REPORT={OUTPUT_REPORT}")
    print(f"DEFINITION={OUTPUT_DEFINITION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
