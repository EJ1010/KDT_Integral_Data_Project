# -*- coding: utf-8 -*-
"""연도별 X 수집 CSV를 원본 손실 없이 통합하고 현황을 기록한다.

입력은 이 스크립트 상위 폴더의 연도별 파일 5개만 사용한다.
재실행하면 기존 통합 결과를 이어 붙이지 않고 원본에서 다시 만든다.
원본 CSV는 읽기만 한다.

실행:
    py -3.11 merge_x_csv.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:
    print("PANDAS_MISSING: run this script with Python 3.11 (py -3.11), which has pandas.")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent

INPUT_FILES = [
    "x_chiikawa_2022.csv",
    "x_chiikawa_2023.csv",
    "x_chiikawa_2024.csv",
    "x_chiikawa_2025.csv",
    "x_chiikawa_2026.csv",
]

OUTPUT_MERGED = "x_chiikawa_2022_2026_merged_raw.csv"
OUTPUT_REPORT = "merge_report.md"
OUTPUT_DICTIONARY = "column_dictionary.csv"

TRACKING_BASES = ("source_file", "source_row", "source_year")
YEAR_PATTERN = re.compile(r"^x_chiikawa_(\d{4})\.csv$")
STATUS_ID_PATTERN = re.compile(r"/status/(\d+)")
SENTINEL_TOKENS = ("NA", "NULL", "N/A", "NaN", "nan", "None", "null")

COLUMN_MEANINGS = {
    "게시물 링크": "X 게시물 URL",
    "계정 ID": "게시 계정 ID",
    "댓글 개수": "댓글 수",
    "리포스트 개수": "리포스트 수",
    "본문": "게시물 본문",
    "계정 이름": "계정 표시 이름",
    "작성 시각": "게시 작성 시각",
    "조회수": "조회수",
    "좋아요 수": "좋아요 수",
    "키워드": "수집 키워드",
    "source_file": "원본 파일명",
    "source_row": "헤더를 제외한 원본 CSV 레코드 순번. 1부터 시작하며 본문 줄바꿈이 들어 있는 물리 줄 번호가 아니다",
    "source_year": "원본 파일명에서 추출한 연도",
}


class DataIntegrityError(Exception):
    def __init__(self, message: str, location: str, suggestion: str):
        super().__init__(message)
        self.message = message
        self.location = location
        self.suggestion = suggestion


@dataclass
class LoadedFile:
    name: str
    path: Path
    encoding: str
    has_bom: bool
    size: int
    sha256: str
    mtime_iso: str
    physical_lines: int
    header: list[str]
    rows: list[list[str]]
    df: pd.DataFrame


def configure_csv_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime_ns / 1_000_000_000).isoformat(timespec="seconds")
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mtime_iso": mtime,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def describe_decode_error(raw: bytes, exc: UnicodeDecodeError) -> str:
    start = exc.start
    line = raw[:start].count(b"\n") + 1
    last_nl = raw.rfind(b"\n", 0, start)
    column = start + 1 if last_nl < 0 else start - last_nl
    snippet = raw[max(0, start - 8) : start + 8]
    return (
        f"byte offset {start}, physical line {line}, column {column}, "
        f"reason {exc.reason}, nearby bytes {snippet!r}"
    )


def detect_encoding(path: Path) -> tuple[str, bool, bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DataIntegrityError(
                "UTF-8 BOM은 있으나 본문을 UTF-8로 디코딩하지 못했다.",
                f"{path.name}: {describe_decode_error(raw, exc)}",
                "해당 위치의 바이트를 확인한 뒤 UTF-8로 다시 저장할지 결정해 주세요. "
                "확인 전에는 파일을 수정하지 않습니다.",
            ) from exc
        return "utf-8-sig", True, raw

    decoded: dict[str, str] = {}
    errors: list[str] = []
    for encoding in ("utf-8", "cp949"):
        try:
            decoded[encoding] = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {describe_decode_error(raw, exc)}")
    if not decoded:
        raise DataIntegrityError(
            "utf-8과 cp949로 모두 디코딩하지 못했다.",
            f"{path.name}: " + " | ".join(errors),
            "인코딩을 확인한 뒤 변환 여부를 결정해 주세요. 확인 전에는 파일을 수정하지 않습니다.",
        )
    if "utf-8" in decoded and "cp949" in decoded and decoded["utf-8"] != decoded["cp949"]:
        raise DataIntegrityError(
            "utf-8과 cp949가 모두 디코딩되지만 문자열이 서로 다르다.",
            path.name,
            "어떤 인코딩이 원본인지 알려 주세요. 확인 전에는 파일을 읽지 않고 통합하지 않습니다.",
        )
    encoding = "utf-8" if "utf-8" in decoded else "cp949"
    return encoding, False, raw


def read_records(path: Path, encoding: str) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.reader(
            handle,
            delimiter=",",
            quotechar='"',
            doublequote=True,
            strict=True,
        )
        try:
            header = next(reader)
        except StopIteration as exc:
            raise DataIntegrityError(
                "헤더가 없는 빈 파일이다.",
                path.name,
                "헤더와 데이터 유무를 확인해 주세요. 확인 전에는 파일을 수정하지 않습니다.",
            ) from exc
        except csv.Error as exc:
            raise DataIntegrityError(
                "헤더 파싱에 실패했다.",
                f"{path.name}: csv line {reader.line_num}: {exc}",
                "따옴표와 쉼표가 깨진 위치를 확인해 주세요. 확인 전에는 파일을 수정하거나 행을 건너뛰지 않습니다.",
            ) from exc

        rows: list[list[str]] = []
        record_no = 0
        try:
            for row in reader:
                record_no += 1
                if len(row) != len(header):
                    raise DataIntegrityError(
                        "레코드의 필드 수가 헤더와 다르다.",
                        (
                            f"{path.name}: CSV record {record_no}, "
                            f"physical line {reader.line_num}, "
                            f"fields {len(row)}, header fields {len(header)}"
                        ),
                        "해당 레코드의 따옴표가 닫혔는지 확인해 주세요. "
                        "확인 전에는 파일을 수정하거나 행을 건너뛰지 않습니다.",
                    )
                rows.append(row)
        except csv.Error as exc:
            raise DataIntegrityError(
                "CSV 레코드 파싱에 실패했다.",
                f"{path.name}: around CSV record {record_no + 1}, csv line {reader.line_num}: {exc}",
                "오류가 난 레코드의 따옴표와 줄바꿈을 확인해 주세요. "
                "확인 전에는 파일을 수정하거나 행을 건너뛰지 않습니다.",
            ) from exc
    return header, rows


def read_with_pandas(path: Path, encoding: str) -> pd.DataFrame:
    try:
        return pd.read_csv(
            path,
            dtype="string",
            encoding=encoding,
            sep=",",
            quotechar='"',
            doublequote=True,
            escapechar=None,
            keep_default_na=False,
            na_filter=False,
            skipinitialspace=False,
            skip_blank_lines=False,
            header=0,
            index_col=None,
            on_bad_lines="error",
            engine="c",
        )
    except Exception as exc:
        raise DataIntegrityError(
            "pandas CSV 파서가 실패했다.",
            f"{path.name}: {type(exc).__name__}: {exc}",
            "csv 모듈 오류 위치와 함께 해당 파일을 확인해 주세요. "
            "확인 전에는 행을 건너뛰거나 파일을 수정하지 않습니다.",
        ) from exc


def assert_no_duplicate_header(name: str, header: list[str]) -> None:
    if len(header) == len(set(header)):
        return
    duplicated = sorted({column for column in header if header.count(column) > 1})
    raise DataIntegrityError(
        "헤더에 같은 컬럼명이 두 번 이상 있다.",
        f"{name}: {duplicated}",
        "어떤 컬럼을 유지할지 알려 주세요. 확인 전에는 컬럼명을 바꾸지 않습니다.",
    )


def frames_match(left: pd.DataFrame, right: pd.DataFrame) -> tuple[bool, str]:
    if list(left.columns) != list(right.columns):
        return False, f"columns differ: {list(left.columns)!r} vs {list(right.columns)!r}"
    if len(left) != len(right):
        return False, f"row counts differ: {len(left)} vs {len(right)}"
    if int(left.isna().to_numpy().sum()) != 0 or int(right.isna().to_numpy().sum()) != 0:
        return False, "NA values appeared during comparison"
    for column in left.columns:
        left_values = left[column].tolist()
        right_values = right[column].tolist()
        for index, (left_value, right_value) in enumerate(zip(left_values, right_values), start=1):
            if left_value != right_value:
                return (
                    False,
                    f"record {index}, column {column!r}: values differ "
                    f"(lengths {len(str(left_value))} and {len(str(right_value))})",
                )
    return True, "cell values match"


def dataframe_from_rows(header: list[str], rows: list[list[str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=header).astype("string")
    if int(frame.isna().to_numpy().sum()) != 0:
        raise DataIntegrityError(
            "문자열 로딩 과정에서 결측값이 만들어졌다.",
            "in-memory dataframe",
            "로딩 설정을 확인해야 한다. 원본은 수정하지 않았다.",
        )
    return frame


def resolve_tracking_names(existing: list[str]) -> tuple[dict[str, str], list[str]]:
    used = set(existing)
    resolved: dict[str, str] = {}
    notes: list[str] = []
    for base in TRACKING_BASES:
        if base not in used:
            resolved[base] = base
            used.add(base)
            continue
        candidate = f"{base}__merge"
        suffix = 2
        while candidate in used:
            candidate = f"{base}__merge{suffix}"
            suffix += 1
        resolved[base] = candidate
        used.add(candidate)
        notes.append(
            f"원본에 '{base}' 컬럼이 있어 추적 값을 '{candidate}' 컬럼에 기록했다. 원본 컬럼은 그대로 두었다."
        )
    return resolved, notes


def year_from_name(name: str) -> str:
    matched = YEAR_PATTERN.fullmatch(name)
    if not matched:
        raise DataIntegrityError(
            "파일명에서 연도를 추출하지 못했다.",
            name,
            "파일명이 x_chiikawa_YYYY.csv 형식인지 확인해 주세요.",
        )
    return matched.group(1)


def build_merged(
    loaded: list[LoadedFile],
) -> tuple[pd.DataFrame, list[str], dict[str, str], list[str]]:
    union: list[str] = []
    for item in loaded:
        for column in item.header:
            if column not in union:
                union.append(column)
    tracking, notes = resolve_tracking_names(union)
    tracking_columns = [tracking[base] for base in TRACKING_BASES]
    merged_rows: list[list[str]] = []
    for item in loaded:
        year = year_from_name(item.name)
        index_by_name = {column: position for position, column in enumerate(item.header)}
        for record_no, row in enumerate(item.rows, start=1):
            aligned = [
                row[index_by_name[column]] if column in index_by_name else ""
                for column in union
            ]
            aligned.extend([item.name, str(record_no), year])
            merged_rows.append(aligned)
    merged = dataframe_from_rows(union + tracking_columns, merged_rows)
    return merged, union, tracking, notes


def rows_from_frame(frame: pd.DataFrame) -> tuple[list[str], list[list[str]]]:
    if int(frame.isna().to_numpy().sum()) != 0:
        raise DataIntegrityError(
            "검증 중 결측값이 있다.",
            "in-memory dataframe",
            "문자열로 유지되어야 한다. 원본은 수정하지 않았다.",
        )
    header = [str(column) for column in frame.columns]
    series_list = []
    for column in frame.columns:
        values = frame[column].tolist()
        for index, value in enumerate(values, start=1):
            if not isinstance(value, str):
                raise DataIntegrityError(
                    "문자열이 아닌 값이 있다.",
                    f"column {column!r}, record {index}, type {type(value).__name__}",
                    "자동 형변환이 들어갔는지 확인해 주세요. 원본은 수정하지 않았다.",
                )
        series_list.append(values)
    rows = [list(record) for record in zip(*series_list)] if series_list else []
    return header, rows


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        writer.writerows(rows)


def read_output_records(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=",", quotechar='"', doublequote=True, strict=True)
        header = next(reader)
        rows = list(reader)
    return header, rows


def info_text(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.info(buf=buffer)
    return buffer.getvalue().rstrip("\n")


def empty_profile(frame: pd.DataFrame) -> list[dict[str, object]]:
    row_count = len(frame)
    profile = []
    for column in frame.columns:
        values = frame[column]
        empty = int((values == "").sum())
        whitespace = int(((values != "") & (values.str.strip() == "")).sum())
        profile.append(
            {
                "column": str(column),
                "empty": empty,
                "whitespace": whitespace,
                "rows": row_count,
            }
        )
    return profile


def sentinel_total(frame: pd.DataFrame) -> int:
    total = 0
    for column in frame.columns:
        values = frame[column]
        for token in SENTINEL_TOKENS:
            total += int((values == token).sum())
    return total


def sentinel_details(frame: pd.DataFrame) -> list[tuple[str, str, int]]:
    found = []
    for column in frame.columns:
        values = frame[column]
        for token in SENTINEL_TOKENS:
            count = int((values == token).sum())
            if count:
                found.append((str(column), token, count))
    return found


def extract_status_id(url: str) -> str:
    if not url:
        return ""
    matched = STATUS_ID_PATTERN.search(url)
    if not matched:
        return ""
    return matched.group(1)


def duplicate_status(frame: pd.DataFrame, file_column: str) -> dict[str, object]:
    if "게시물 링크" not in frame.columns:
        return {"available": False}
    links = frame["게시물 링크"].tolist()
    ids = [extract_status_id(link) for link in links]
    files = frame[file_column].tolist()
    texts = frame["본문"].tolist() if "본문" in frame.columns else [""] * len(frame)
    extracted = sum(1 for value in ids if value)
    empty_link = sum(1 for value in links if value == "")
    unparsed_examples = []
    for link, status_id in zip(links, ids):
        if link and not status_id:
            collapsed = " ".join(link.split())
            unparsed_examples.append(collapsed[:120])
            if len(unparsed_examples) == 5:
                break
    unparsed = sum(1 for link, status_id in zip(links, ids) if link and not status_id)

    valid_rows = [
        (status_id, file_name, text, link)
        for status_id, file_name, text, link in zip(ids, files, texts, links)
        if status_id
    ]
    counts: dict[str, int] = defaultdict(int)
    files_by_id: dict[str, set[str]] = defaultdict(set)
    texts_by_id: dict[str, set[str]] = defaultdict(set)
    links_by_id: dict[str, set[str]] = defaultdict(set)
    per_file_ids: dict[str, list[str]] = defaultdict(list)
    for status_id, file_name, text, link in valid_rows:
        counts[status_id] += 1
        files_by_id[status_id].add(file_name)
        texts_by_id[status_id].add(text)
        links_by_id[status_id].add(link)
        per_file_ids[file_name].append(status_id)

    frequency: dict[int, int] = defaultdict(int)
    for count in counts.values():
        frequency[count] += 1
    freq_table = [
        (times, id_count, times * id_count)
        for times, id_count in sorted(frequency.items())
    ]
    duplicate_ids = [status_id for status_id, count in counts.items() if count >= 2]
    rows_in_duplicate = sum(counts[status_id] for status_id in duplicate_ids)
    cross_file = sum(1 for status_id in counts if len(files_by_id[status_id]) >= 2)
    within_file = 0
    within_and_cross = 0
    per_file_counter: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for file_name, id_list in per_file_ids.items():
        for status_id in id_list:
            per_file_counter[file_name][status_id] += 1
    ids_within = set()
    for file_counts in per_file_counter.values():
        for status_id, count in file_counts.items():
            if count >= 2:
                ids_within.add(status_id)
    within_file = len(ids_within)
    within_and_cross = sum(1 for status_id in ids_within if len(files_by_id[status_id]) >= 2)
    different_text = sum(1 for status_id in duplicate_ids if len(texts_by_id[status_id]) > 1)
    different_link = sum(1 for status_id in duplicate_ids if len(links_by_id[status_id]) > 1)

    per_file = []
    for name in INPUT_FILES:
        file_counts = per_file_counter.get(name, {})
        dup_ids = sum(1 for count in file_counts.values() if count >= 2)
        dup_rows = sum(count for count in file_counts.values() if count >= 2)
        per_file.append(
            {
                "file": name,
                "extracted": len(per_file_ids.get(name, [])),
                "unique": len(file_counts),
                "dup_ids": dup_ids,
                "dup_rows": dup_rows,
                "surplus": dup_rows - dup_ids,
            }
        )

    return {
        "available": True,
        "rows": len(frame),
        "extracted": extracted,
        "empty_link": empty_link,
        "unparsed": unparsed,
        "unparsed_examples": unparsed_examples,
        "unique_ids": len(counts),
        "duplicate_id_count": len(duplicate_ids),
        "rows_in_duplicate_ids": rows_in_duplicate,
        "surplus_rows": rows_in_duplicate - len(duplicate_ids),
        "max_repeat": max(counts.values()) if counts else 0,
        "freq_table": freq_table,
        "cross_file_ids": cross_file,
        "within_file_ids": within_file,
        "within_and_cross_ids": within_and_cross,
        "different_text": different_text,
        "different_link": different_link,
        "per_file": per_file,
    }


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    head = "| " + " | ".join(cell(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join([head, separator, *body])


def ratio(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{part / whole * 100:.1f}%"


def column_difference_lines(loaded: list[LoadedFile]) -> list[str]:
    names = [item.header for item in loaded]
    sets = [set(header) for header in names]
    union = set.union(*sets)
    shared = set.intersection(*sets)
    lines = []
    if all(header == names[0] for header in names):
        lines.append("다섯 파일의 컬럼명과 컬럼 순서가 같다.")
        lines.append("이름 기준으로 같은 컬럼을 같은 위치에 맞춰 세로로 결합했고, 컬럼 순서는 원본 순서를 유지했다.")
    else:
        lines.append("파일별 컬럼명 또는 순서가 다르다. 컬럼명 기준으로 맞추고, 순서는 2022 파일에서 처음 나온 순서를 유지했다.")
        lines.append("이후 파일에만 있는 컬럼은 처음 등장한 순서대로 뒤에 붙인다.")
    if union == shared:
        lines.append("파일마다 컬럼 구성이 같아, 없는 컬럼을 빈칸으로 채운 셀은 없다.")
    else:
        lines.append("일부 파일에만 있는 컬럼은 남기고, 그 파일에 없는 칸만 빈 문자열로 두었다.")
        for item, columns in zip(loaded, sets):
            missing = [column for column in union if column not in columns]
            extra = [column for column in item.header if column not in shared]
            lines.append(
                f"- {item.name}: 이 파일에만 더 있는 컬럼 {extra or '없음'}, "
                f"다른 파일에만 있어 빈칸이 된 컬럼 {missing or '없음'}"
            )
    normalized: dict[str, list[str]] = defaultdict(list)
    for column in union:
        key = re.sub(r"\s+", "", column).casefold()
        normalized[key].append(column)
    similar = [group for group in normalized.values() if len(set(group)) > 1]
    if similar:
        lines.append("공백이나 대소문자만 다르고 이름이 다른 컬럼이 있다. 이 컬럼들은 합치지 않고 각각 유지했다.")
        for group in similar:
            lines.append(f"- {group}")
    else:
        lines.append("공백이나 대소문자만 다른 별도 컬럼명은 없다.")
    lines.append("")
    lines.append("공통 기준 컬럼 순서:")
    for index, column in enumerate(names[0], start=1):
        lines.append(f"{index}. `{column}`")
    if any(header != names[0] for header in names):
        lines.append("")
        lines.append("파일별 컬럼 순서:")
        for item in loaded:
            joined = ", ".join(item.header)
            lines.append(f"- {item.name}: {joined}")
    return lines


def render_report(context: dict[str, object]) -> str:
    loaded: list[LoadedFile] = context["loaded"]  # type: ignore[assignment]
    merged: pd.DataFrame = context["merged"]  # type: ignore[assignment]
    checks: list[tuple[str, bool, str]] = context["checks"]  # type: ignore[assignment]
    tracking: dict[str, str] = context["tracking"]  # type: ignore[assignment]
    notes: list[str] = context["notes"]  # type: ignore[assignment]
    duplicates: dict[str, object] = context["duplicates"]  # type: ignore[assignment]
    passed = all(ok for _, ok, _ in checks)

    lines: list[str] = []
    lines.append("# X CSV 원본 통합 보고서")
    lines.append("")
    lines.append(f"- 생성 시각: {context['generated_at']}")
    lines.append(f"- Python: {context['python_version']}")
    lines.append(f"- pandas: {context['pandas_version']}")
    lines.append(f"- 대상 폴더: `{context['data_dir']}`")
    lines.append(f"- 결과 폴더: `{context['output_dir']}`")
    lines.append(f"- 검증: {'통과' if passed else '실패'}")
    lines.append("")
    lines.append("이번 단계는 원본 통합과 현황 확인이다. 관련성 판단, 중복 제거, 결측 보정, 본문 수정, 숫자·날짜 정규화, 소비 형태 분류는 하지 않았다.")
    lines.append("")
    lines.append("## 1. 파일 확인")
    lines.append("")
    lines.append("행 수는 CSV 파서가 읽은 레코드 수이다. 물리 줄 수는 본문 안의 줄바꿈까지 포함한 줄 수라서 레코드 수와 다르다.")
    lines.append("")
    file_rows = []
    for item in loaded:
        file_rows.append(
            [
                item.name,
                "있음",
                item.encoding,
                "있음" if item.has_bom else "없음",
                item.size,
                item.physical_lines,
                len(item.rows),
                len(item.header),
            ]
        )
    lines.append(
        md_table(
            ["파일", "존재", "인코딩", "UTF-8 BOM", "크기(byte)", "물리 줄 수", "CSV 레코드 수", "컬럼 수"],
            file_rows,
        )
    )
    lines.append("")
    lines.append("파일 지문 (실행 시작 시점, 실행 후와 동일):")
    lines.append("")
    lines.append(
        md_table(
            ["파일", "수정 시각", "SHA-256"],
            [[item.name, item.mtime_iso, item.sha256] for item in loaded],
        )
    )
    lines.append("")
    lines.append("## 2. 로딩")
    lines.append("")
    lines.append("- 입력은 위에 적은 연도별 파일 5개만 사용했다. `integrated` 안의 기존 결과는 입력에 넣지 않았다.")
    lines.append("- 인코딩은 BOM과 strict 디코딩으로 확인했다. 디코딩 실패 문자를 대체 문자로 바꾸지 않았다.")
    lines.append("- `csv` 모듈로 레코드를 읽고, pandas `read_csv` 결과와 셀 단위로 대조했다.")
    lines.append("- pandas 로딩 옵션은 `dtype='string'`, `na_filter=False`, `keep_default_na=False`, `skipinitialspace=False`, `skip_blank_lines=False`, `on_bad_lines='error'` 이다.")
    lines.append("- 빈 문자열과 `NA`, `NULL` 같은 원문을 결측값으로 바꾸지 않았다.")
    lines.append("- 재실행 시 통합 파일을 이어 붙이지 않고, 원본 5개에서 결과 파일을 다시 쓴다.")
    lines.append("")
    lines.append("## 3. 컬럼")
    lines.append("")
    lines.extend(column_difference_lines(loaded))
    lines.append("")
    if notes:
        lines.append("추적 컬럼 이름 충돌:")
        for note in notes:
            lines.append(f"- {note}")
    else:
        lines.append(
            "원본에 `source_file`, `source_row`, `source_year` 컬럼이 없어 그 이름으로 추적 컬럼을 추가했다."
        )
    lines.append("")
    lines.append(
        "추가된 추적 컬럼: "
        + ", ".join(f"`{tracking[base]}`" for base in TRACKING_BASES)
    )
    lines.append("")
    lines.append("## 4. 통합 행 수")
    lines.append("")
    count_rows = [[item.name, len(item.rows)] for item in loaded]
    source_sum = sum(len(item.rows) for item in loaded)
    count_rows.append(["합계", source_sum])
    count_rows.append(["통합 파일", len(merged)])
    lines.append(md_table(["구분", "CSV 레코드 수"], count_rows))
    lines.append("")
    file_column = tracking["source_file"]
    year_column = tracking["source_year"]
    count_check = (
        merged.groupby(file_column, sort=False)[year_column]
        .size()
        .rename("rows")
        .reset_index()
    )
    lines.append("통합 파일의 `source_file` 별 행 수:")
    lines.append("")
    lines.append(
        md_table(
            ["source_file", "행 수"],
            [[row[file_column], int(row["rows"])] for _, row in count_check.iterrows()],
        )
    )
    lines.append("")
    lines.append("## 5. 검증")
    lines.append("")
    lines.append(
        md_table(
            ["항목", "결과", "내용"],
            [[name, "통과" if ok else "실패", detail] for name, ok, detail in checks],
        )
    )
    lines.append("")
    lines.append("## 6. df.info()")
    lines.append("")
    lines.append("빈 문자열은 결측으로 바꾸지 않았으므로 `Non-Null Count`는 레코드 수와 같다. 빈칸 수는 다음 절의 빈값 현황이 기준이다.")
    lines.append("")
    for item in loaded:
        lines.append(f"### {item.name}")
        lines.append("")
        lines.append("```text")
        lines.append(info_text(item.df))
        lines.append("```")
        lines.append("")
    lines.append("### 통합 데이터")
    lines.append("")
    lines.append("```text")
    lines.append(info_text(merged))
    lines.append("```")
    lines.append("")
    lines.append("## 7. 빈값 현황")
    lines.append("")
    lines.append("빈 문자열은 셀 값이 비어 있는 경우이다. 공백만 있는 값은 빈 문자열과 따로 세었고 내용을 자르지 않았다.")
    lines.append("")
    profiles = [("통합", merged)] + [(item.name, item.df) for item in loaded]
    for label, frame in profiles:
        lines.append(f"### {label}")
        lines.append("")
        profile = empty_profile(frame)
        lines.append(
            md_table(
                ["컬럼", "행 수", "빈 문자열", "빈 문자열 비율", "공백만 있는 값"],
                [
                    [
                        item["column"],
                        item["rows"],
                        item["empty"],
                        ratio(int(item["empty"]), int(item["rows"])),
                        item["whitespace"],
                    ]
                    for item in profile
                ],
            )
        )
        lines.append("")
    lines.append("## 8. 결측으로 바꾸지 않은 원문")
    lines.append("")
    lines.append(
        "아래 토큰과 셀 전체가 정확히 같은 값은 문자열로 유지했다: "
        + ", ".join(f"`{token}`" for token in SENTINEL_TOKENS)
        + "."
    )
    lines.append("")
    sentinel_rows = [[item.name, sentinel_total(item.df)] for item in loaded]
    sentinel_rows.append(["통합", sentinel_total(merged)])
    lines.append(md_table(["자료", "토큰과 정확히 같은 셀 수"], sentinel_rows))
    lines.append("")
    details = sentinel_details(merged)
    if details:
        lines.append("통합 데이터에서 토큰과 정확히 같은 셀:")
        lines.append("")
        lines.append(md_table(["컬럼", "토큰", "셀 수"], details))
        lines.append("")
    lines.append("## 9. 게시물 ID 중복 현황")
    lines.append("")
    lines.append("게시물 ID는 `게시물 링크`에서 `/status/` 뒤의 숫자를 임시로 추출해 센 것이다. 중복 행은 삭제하지 않았고, 추출한 ID 컬럼은 통합 파일에 넣지 않았다.")
    lines.append("")
    if not duplicates.get("available"):
        lines.append("`게시물 링크` 컬럼이 없어 게시물 ID 중복을 계산하지 못했다.")
    else:
        lines.append(
            md_table(
                ["항목", "값"],
                [
                    ["통합 행 수", duplicates["rows"]],
                    ["ID를 추출한 행", duplicates["extracted"]],
                    ["게시물 링크가 빈 행", duplicates["empty_link"]],
                    ["링크는 있으나 ID를 추출하지 못한 행", duplicates["unparsed"]],
                    ["고유 ID", duplicates["unique_ids"]],
                    ["2회 이상 등장한 ID", duplicates["duplicate_id_count"]],
                    ["중복 ID에 속한 행", duplicates["rows_in_duplicate_ids"]],
                    ["고유 ID보다 많은 행(잉여 행)", duplicates["surplus_rows"]],
                    ["한 ID의 최대 등장 횟수", duplicates["max_repeat"]],
                    ["두 개 이상 파일에 등장한 ID", duplicates["cross_file_ids"]],
                    ["한 파일 안에서 2회 이상 등장한 ID", duplicates["within_file_ids"]],
                    ["파일 간 중복이면서 파일 안에서도 중복인 ID", duplicates["within_and_cross_ids"]],
                    ["같은 ID인데 본문이 다른 ID", duplicates["different_text"]],
                    ["같은 ID인데 게시물 링크 문자열이 다른 ID", duplicates["different_link"]],
                ],
            )
        )
        lines.append("")
        lines.append("등장 횟수 분포:")
        lines.append("")
        lines.append(
            md_table(
                ["등장 횟수", "ID 수", "행 수"],
                duplicates["freq_table"],  # type: ignore[arg-type]
            )
        )
        lines.append("")
        lines.append("파일 내부 중복:")
        lines.append("")
        per_file = duplicates["per_file"]
        lines.append(
            md_table(
                ["파일", "ID 추출 행", "고유 ID", "2회 이상 ID", "그 ID에 속한 행", "파일 내부 잉여 행"],
                [
                    [
                        item["file"],
                        item["extracted"],
                        item["unique"],
                        item["dup_ids"],
                        item["dup_rows"],
                        item["surplus"],
                    ]
                    for item in per_file  # type: ignore[union-attr]
                ],
            )
        )
        lines.append("")
        examples = duplicates["unparsed_examples"]
        if examples:
            lines.append("ID를 추출하지 못한 링크 예:")
            for example in examples:
                lines.append(f"- `{example}`")
            lines.append("")
    lines.append("## 10. 오류와 처리")
    lines.append("")
    if passed:
        lines.append("파싱 오류, 인코딩 오류, 필드 수 불일치는 없었다.")
        lines.append("원본 파일은 열기만 했고, 실행 전후의 크기·수정 시각·SHA-256이 같다.")
        lines.append("통합 결과는 원본 5개를 다시 읽어 덮어썼다.")
    else:
        lines.append("아래 검증 실패 항목을 확인해 주세요. 실패한 통합 파일은 남기지 않았다.")
        for name, ok, detail in checks:
            if not ok:
                lines.append(f"- {name}: {detail}")
    lines.append("")
    lines.append("## 11. 결과물")
    lines.append("")
    lines.append(f"- 스크립트: `{SCRIPT_DIR / 'merge_x_csv.py'}`")
    lines.append(f"- 통합 CSV: `{context['merged_path']}` ({context['merged_size']} bytes, SHA-256 `{context['merged_sha256']}`)")
    lines.append(f"- 이 보고서: `{context['report_path']}`")
    lines.append(f"- 컬럼 사전: `{context['dictionary_path']}`")
    lines.append("")
    lines.append("통합 CSV는 UTF-8 BOM이다.")
    lines.append("")
    return "\n".join(lines)


def write_dictionary(path: Path, merged: pd.DataFrame, original_columns: set[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["컬럼명", "의미", "현재_자료형", "원본_추가_구분"])
        for column in merged.columns:
            name = str(column)
            role = "원본" if name in original_columns else "추가"
            if name in COLUMN_MEANINGS:
                meaning = COLUMN_MEANINGS[name]
            elif role == "추가" and name.startswith("source_"):
                meaning = "통합 추적을 위해 추가한 컬럼. 원본에 같은 이름이 있어 이름을 바꿨다"
            else:
                meaning = "확인 필요"
            writer.writerow([name, meaning, str(merged.dtypes[column]), role])


def render_failure(
    message: str,
    location: str,
    suggestion: str,
    loaded: list[LoadedFile],
    extra: str = "",
) -> str:
    lines = [
        "# X CSV 원본 통합 보고서",
        "",
        f"- 생성 시각: {datetime.now().isoformat(timespec='seconds')}",
        "- 검증: 실패",
        "- 통합 CSV는 저장하지 않았다.",
        "",
        "## 문제",
        "",
        message,
        "",
        "## 위치",
        "",
        location,
        "",
        "## 필요한 확인",
        "",
        suggestion,
        "",
        "원본 CSV는 수정하지 않았다. 확인 후에 스크립트를 다시 실행하면 원본에서 결과를 다시 만든다.",
        "",
    ]
    if loaded:
        lines.append("## 문제 전에 읽은 파일")
        lines.append("")
        lines.append(
            md_table(
                ["파일", "인코딩", "CSV 레코드 수", "컬럼 수"],
                [[item.name, item.encoding, len(item.rows), len(item.header)] for item in loaded],
            )
        )
        lines.append("")
    if extra:
        lines.append("## 상세")
        lines.append("")
        lines.append("```text")
        lines.append(extra.rstrip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def remove_generated_data() -> None:
    for name in (OUTPUT_MERGED, OUTPUT_DICTIONARY):
        path = SCRIPT_DIR / name
        if path.exists():
            path.unlink()


def memory_checks(
    loaded: list[LoadedFile],
    merged: pd.DataFrame,
    union: list[str],
    tracking: dict[str, str],
    before: dict[str, dict[str, object]],
) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    source_sum = sum(len(item.rows) for item in loaded)
    checks.append(("입력 파일 5개", len(loaded) == 5, f"{len(loaded)} files"))
    checks.append(("레코드 수 합계와 통합 행 수", source_sum == len(merged), f"{source_sum} == {len(merged)}"))
    na_count = int(merged.isna().to_numpy().sum())
    checks.append(("통합 데이터에 결측값 없음", na_count == 0, f"NA cells {na_count}"))

    file_column = tracking["source_file"]
    row_column = tracking["source_row"]
    year_column = tracking["source_year"]
    file_match = True
    row_match = True
    year_match = True
    value_match = True
    fill_match = True
    value_detail = "원본 컬럼 값 유지"
    fill_detail = "다른 파일에만 있는 컬럼의 빈칸 유지"
    filled_cells = 0
    for item in loaded:
        part = merged.loc[merged[file_column] == item.name].reset_index(drop=True)
        if len(part) != len(item.rows):
            file_match = False
        expected_rows = [str(number) for number in range(1, len(item.rows) + 1)]
        if part[row_column].tolist() != expected_rows:
            row_match = False
        if part[year_column].tolist() != [year_from_name(item.name)] * len(item.rows):
            year_match = False
        for column in union:
            if column in item.header:
                if part[column].tolist() != item.df[column].tolist():
                    value_match = False
                    value_detail = f"{item.name} column {column!r} differs"
                    break
            else:
                filled_cells += int((part[column] == "").sum())
                if not bool((part[column] == "").all()):
                    fill_match = False
                    fill_detail = f"{item.name} missing column {column!r} is not blank"
        if not value_match:
            break
    if fill_match and filled_cells == 0:
        fill_detail = "모든 파일의 컬럼이 같아 빈칸으로 채운 셀은 없다"
    checks.append(("source_file 행 수", file_match, "파일별 레코드 수와 같다" if file_match else "불일치"))
    checks.append(("source_row 레코드 순번", row_match, "파일별로 1부터 레코드 수까지" if row_match else "불일치"))
    checks.append(("source_year", year_match, "파일명의 연도와 같다" if year_match else "불일치"))
    checks.append(("원본 컬럼 값 유지", value_match, value_detail))
    checks.append(("없는 컬럼의 빈칸", fill_match, fill_detail))

    original_names = set(union)
    overwritten = [base for base, actual in tracking.items() if base in original_names and actual == base]
    checks.append(
        (
            "추적 컬럼이 원본 컬럼을 덮어쓰지 않음",
            not overwritten,
            "충돌 없음" if not overwritten else f"덮어쓴 이름 {overwritten}",
        )
    )
    unchanged = True
    for item in loaded:
        current = fingerprint(item.path)
        if current != before[item.name]:
            unchanged = False
            break
    checks.append(("원본 파일 미변경", unchanged, "크기, 수정 시각, SHA-256 동일" if unchanged else "원본 지문이 달라졌다"))
    return checks


def load_files(before: dict[str, dict[str, object]]) -> list[LoadedFile]:
    loaded: list[LoadedFile] = []
    for name in INPUT_FILES:
        path = DATA_DIR / name
        encoding, has_bom, raw = detect_encoding(path)
        header, rows = read_records(path, encoding)
        assert_no_duplicate_header(name, header)
        csv_frame = dataframe_from_rows(header, rows)
        pandas_frame = read_with_pandas(path, encoding)
        matched, detail = frames_match(csv_frame, pandas_frame)
        if not matched:
            raise DataIntegrityError(
                "csv 모듈과 pandas의 파싱 결과가 다르다.",
                f"{name}: {detail}",
                "두 파서 중 어느 쪽을 기준으로 할지 확인해 주세요. 확인 전에는 통합 파일을 만들지 않습니다.",
            )
        text = raw.decode(encoding)
        finger = before[name]
        loaded.append(
            LoadedFile(
                name=name,
                path=path,
                encoding=encoding,
                has_bom=has_bom,
                size=int(finger["size"]),
                sha256=str(finger["sha256"]),
                mtime_iso=str(finger["mtime_iso"]),
                physical_lines=len(text.splitlines()),
                header=header,
                rows=rows,
                df=csv_frame,
            )
        )
    return loaded


def write_failure_report(text: str) -> None:
    remove_generated_data()
    (SCRIPT_DIR / OUTPUT_REPORT).write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    configure_csv_limit()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if DATA_DIR.name != "03_x":
        write_failure_report(
            render_failure(
                "스크립트 위치가 예상한 대상 폴더가 아니다.",
                str(DATA_DIR),
                "merge_x_csv.py를 `02_csv/03_x/integrated`에 두고 다시 실행해 주세요.",
            )
        )
        print("VALIDATION=FAIL")
        print(f"REPORT={SCRIPT_DIR / OUTPUT_REPORT}")
        return 1

    missing = [name for name in INPUT_FILES if not (DATA_DIR / name).is_file()]
    if missing:
        write_failure_report(
            render_failure(
                "필수 원본 CSV가 없다.",
                ", ".join(str(DATA_DIR / name) for name in missing),
                "누락된 파일을 대상 폴더에 둔 뒤 다시 실행해 주세요. 있는 파일만으로 통합하지 않습니다.",
            )
        )
        print("VALIDATION=FAIL")
        print(f"REPORT={SCRIPT_DIR / OUTPUT_REPORT}")
        return 1

    before = {name: fingerprint(DATA_DIR / name) for name in INPUT_FILES}
    loaded: list[LoadedFile] = []
    merged_path = SCRIPT_DIR / OUTPUT_MERGED
    try:
        loaded = load_files(before)
        merged, union, tracking, notes = build_merged(loaded)
        header, rows = rows_from_frame(merged)
        write_csv(merged_path, header, rows)

        reread_header, reread_rows = read_output_records(merged_path)
        reread_ok = reread_header == header and reread_rows == rows
        reread_detail = (
            f"rows {len(reread_rows)}, columns {len(reread_header)}"
            if reread_ok
            else "재읽기 결과와 메모리의 통합 데이터가 다르다"
        )
        pandas_back = read_with_pandas(merged_path, "utf-8-sig")
        pandas_ok, pandas_detail = frames_match(merged, pandas_back)

        checks = memory_checks(loaded, merged, union, tracking, before)
        checks.append(("통합 파일 재읽기", reread_ok, reread_detail))
        checks.append(("pandas로 통합 파일 재읽기", pandas_ok, pandas_detail))
        if not all(ok for _, ok, _ in checks):
            failed = "; ".join(name for name, ok, _ in checks if not ok)
            raise DataIntegrityError(
                "통합 결과 검증에 실패했다.",
                failed,
                "저장된 통합 파일은 삭제했다. 검증 내용을 확인한 뒤 다시 실행해 주세요.",
            )

        merged_bytes = merged_path.read_bytes()
        dictionary_path = SCRIPT_DIR / OUTPUT_DICTIONARY
        report_path = SCRIPT_DIR / OUTPUT_REPORT
        write_dictionary(dictionary_path, merged, set(union))
        duplicates = duplicate_status(merged, tracking["source_file"])
        report = render_report(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "python_version": sys.version.split()[0],
                "pandas_version": pd.__version__,
                "data_dir": str(DATA_DIR),
                "output_dir": str(SCRIPT_DIR),
                "loaded": loaded,
                "merged": merged,
                "checks": checks,
                "tracking": tracking,
                "notes": notes,
                "duplicates": duplicates,
                "merged_path": str(merged_path),
                "report_path": str(report_path),
                "dictionary_path": str(dictionary_path),
                "merged_size": len(merged_bytes),
                "merged_sha256": hashlib.sha256(merged_bytes).hexdigest(),
            }
        )
        report_path.write_text(report, encoding="utf-8", newline="\n")
    except DataIntegrityError as exc:
        write_failure_report(render_failure(exc.message, exc.location, exc.suggestion, loaded))
        print("VALIDATION=FAIL")
        print(f"LOCATION={exc.location}")
        print(f"REPORT={SCRIPT_DIR / OUTPUT_REPORT}")
        return 1
    except Exception:
        write_failure_report(
            render_failure(
                "스크립트 실행 중 예외가 발생했다.",
                "merge_x_csv.py",
                "아래 오류를 확인해 주세요. 원본은 수정하지 않았고, 이번 실행의 통합 CSV와 컬럼 사전은 남기지 않는다.",
                loaded,
                traceback.format_exc(),
            )
        )
        print("VALIDATION=FAIL")
        print(f"REPORT={SCRIPT_DIR / OUTPUT_REPORT}")
        return 1

    print(f"INPUT_FILES={len(loaded)}")
    print(f"SOURCE_ROWS_SUM={sum(len(item.rows) for item in loaded)}")
    print(f"MERGED_ROWS={len(merged)}")
    print("VALIDATION=PASS")
    print(f"SCRIPT={SCRIPT_DIR / 'merge_x_csv.py'}")
    print(f"MERGED={merged_path}")
    print(f"REPORT={SCRIPT_DIR / OUTPUT_REPORT}")
    print(f"DICTIONARY={SCRIPT_DIR / OUTPUT_DICTIONARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
