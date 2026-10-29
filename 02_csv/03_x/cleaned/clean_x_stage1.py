# -*- coding: utf-8 -*-
"""X 치이카와 2022–2026 기초 정제 (stage 1).

원본 연도별 CSV는 읽기만 하고, 행 삭제·중복 병합·본문 변형은 하지 않습니다.
통합 원본(integrated/x_chiikawa_2022_2026_merged_raw.csv)과
merge_report.md, column_dictionary.csv 는 이 폴더에 없어
연도별 원본 5개를 입력으로 사용합니다.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = Path(__file__).resolve().parent
OUT_CSV = CLEAN_DIR / "x_chiikawa_stage1.csv"
OUT_REPORT = CLEAN_DIR / "quality_report.md"
OUT_DICT = CLEAN_DIR / "column_dictionary_stage1.csv"

YEARS = (2022, 2023, 2024, 2025, 2026)
ORIGINAL_COLUMNS = [
    "게시물 링크",
    "계정 ID",
    "계정 소개글",
    "댓글 개수",
    "리포스트 개수",
    "본문",
    "계정 이름",
    "작성 시각",
    "조회수",
    "좋아요 수",
    "키워드",
]
METRIC_SPECS = [
    ("좋아요 수", "like_count_int", "flag_like_parse_failed", "flag_like_negative"),
    ("리포스트 개수", "repost_count_int", "flag_repost_parse_failed", "flag_repost_negative"),
    ("조회수", "view_count_int", "flag_view_parse_failed", "flag_view_negative"),
]
CONFLICT_FIELDS = ["본문", "계정 ID", "계정 이름", "좋아요 수", "리포스트 개수", "조회수", "댓글 개수"]
STATUS_ID_RE = re.compile(r"/status/(\d+)(?:\?|$)")
INT_RE = re.compile(r"^[+-]?\d+$")
INT_FLOAT_RE = re.compile(r"^[+-]?\d+\.0+$")
DATETIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$")

ANALYSIS_COLUMNS = [
    "source_file",
    "source_file_year",
    "post_id",
    "flag_post_id_extract_failed",
    "created_at_kst",
    "year",
    "month",
    "flag_created_at_parse_failed",
    "flag_source_year_mismatch",
    "like_count_int",
    "repost_count_int",
    "view_count_int",
    "flag_like_parse_failed",
    "flag_repost_parse_failed",
    "flag_view_parse_failed",
    "flag_like_negative",
    "flag_repost_negative",
    "flag_view_negative",
    "flag_duplicate_post_id",
    "flag_duplicate_full_row",
    "flag_duplicate_post_conflict",
    "flag_empty_link",
    "flag_empty_body",
    "flag_empty_account_name",
]


def read_year(year: int) -> tuple[list[str], list[dict[str, str]]]:
    path = BASE_DIR / f"x_chiikawa_{year}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = []
        for raw in reader:
            row = {column: "" for column in ORIGINAL_COLUMNS}
            for column in fieldnames:
                row[column] = raw.get(column) or ""
            row["source_file"] = path.name
            row["source_file_year"] = str(year)
            row["_present_columns"] = fieldnames
            rows.append(row)
    return fieldnames, rows


def parse_post_id(link: str) -> str:
    match = STATUS_ID_RE.search(link.strip())
    return match.group(1) if match else ""


def parse_exact_int(value: str) -> tuple[str, bool]:
    """Return (integer text or '', failed). Blank is missing, not a failure."""
    text = value.strip()
    if text == "":
        return "", False
    if INT_RE.fullmatch(text):
        return str(int(text)), False
    if INT_FLOAT_RE.fullmatch(text):
        return str(int(float(text))), False
    return "", True


def parse_created_at(value: str) -> tuple[str, str, str, bool]:
    text = value.strip()
    match = DATETIME_RE.fullmatch(text)
    if not match:
        return "", "", "", True
    year, month, day, hour, minute, second = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return "", "", "", True
    try:
        pd.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
    except ValueError:
        return "", "", "", True
    return text, str(year), f"{month:02d}", False


def flag(condition: bool) -> str:
    return "1" if condition else "0"


def build_rows() -> tuple[list[dict[str, str]], dict]:
    source_columns: dict[int, list[str]] = {}
    rows: list[dict[str, str]] = []
    for year in YEARS:
        fieldnames, year_rows = read_year(year)
        source_columns[year] = fieldnames
        rows.extend(year_rows)

    for row in rows:
        link = row["게시물 링크"]
        post_id = parse_post_id(link)
        created_at, year_text, month_text, date_failed = parse_created_at(row["작성 시각"])
        row["post_id"] = post_id
        row["flag_post_id_extract_failed"] = flag(post_id == "")
        row["created_at_kst"] = created_at
        row["year"] = year_text
        row["month"] = month_text
        row["flag_created_at_parse_failed"] = flag(date_failed)
        row["flag_source_year_mismatch"] = flag(
            (not date_failed) and year_text != row["source_file_year"]
        )
        row["flag_empty_link"] = flag(link.strip() == "")
        row["flag_empty_body"] = flag(row["본문"].strip() == "")
        row["flag_empty_account_name"] = flag(row["계정 이름"].strip() == "")
        for source_name, int_name, fail_name, neg_name in METRIC_SPECS:
            parsed, failed = parse_exact_int(row[source_name])
            row[int_name] = parsed
            row[fail_name] = flag(failed)
            row[neg_name] = flag(parsed != "" and int(parsed) < 0)

    original_keys = [tuple(row[column] for column in ORIGINAL_COLUMNS) for row in rows]
    full_counts = Counter(original_keys)
    id_counts = Counter(row["post_id"] for row in rows if row["post_id"])
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["post_id"]:
            grouped[row["post_id"]].append(row)

    conflict_ids = set()
    for post_id, group in grouped.items():
        if len(group) < 2:
            continue
        for field in CONFLICT_FIELDS:
            values = {item[field] for item in group}
            if len(values) > 1:
                conflict_ids.add(post_id)
                break

    for row, key in zip(rows, original_keys):
        post_id = row["post_id"]
        row["flag_duplicate_full_row"] = flag(full_counts[key] > 1)
        row["flag_duplicate_post_id"] = flag(bool(post_id) and id_counts[post_id] > 1)
        row["flag_duplicate_post_conflict"] = flag(post_id in conflict_ids)

    meta = {
        "source_columns": source_columns,
        "input_rows": len(rows),
        "full_duplicate_groups": sum(1 for count in full_counts.values() if count > 1),
        "full_duplicate_extra_rows": sum(count - 1 for count in full_counts.values() if count > 1),
        "post_id_duplicate_groups": sum(1 for count in id_counts.values() if count > 1),
        "post_id_duplicate_extra_rows": sum(count - 1 for count in id_counts.values() if count > 1),
        "conflict_groups": len(conflict_ids),
    }
    return rows, meta


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = ORIGINAL_COLUMNS + ANALYSIS_COLUMNS
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def verify(rows: list[dict[str, str]]) -> dict[str, object]:
    with OUT_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reloaded = list(csv.DictReader(handle))
    if len(reloaded) != len(rows):
        raise SystemExit(f"행 수 불일치: 저장 전 {len(rows)} / 재읽기 {len(reloaded)}")
    mismatches = 0
    for before, after in zip(rows, reloaded):
        for column in ORIGINAL_COLUMNS:
            if before[column] != (after.get(column) or ""):
                mismatches += 1
        if before["post_id"] != (after.get("post_id") or ""):
            mismatches += 1
        if before["created_at_kst"] != (after.get("created_at_kst") or ""):
            mismatches += 1
        for column in ("like_count_int", "repost_count_int", "view_count_int", "year", "month"):
            if before[column] != (after.get(column) or ""):
                mismatches += 1
        if before["view_count_int"] == "" and (after.get("view_count_int") or "") not in ("",):
            mismatches += 1
        if before["조회수"] == "0" and after.get("view_count_int") != "0":
            mismatches += 1
    raw = OUT_CSV.read_bytes()
    if not raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("UTF-8 BOM이 없습니다.")
    if mismatches:
        raise SystemExit(f"원본 컬럼 또는 분석 컬럼 재읽기 불일치 {mismatches}건")
    frame = pd.read_csv(OUT_CSV, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    view_numeric = pd.to_numeric(frame["view_count_int"].replace("", pd.NA), errors="coerce")
    zero_kept = int(((frame["조회수"] == "0") & (frame["view_count_int"] != "0")).sum())
    missing_filled = int(((frame["조회수"] == "") & (frame["view_count_int"] != "")).sum())
    return {
        "reloaded_rows": len(reloaded),
        "mismatches": mismatches,
        "bom": True,
        "zero_rewritten": zero_kept,
        "missing_filled": missing_filled,
        "view_na": int(view_numeric.isna().sum()),
        "pandas_rows": len(frame),
    }


def count_flag(rows: list[dict[str, str]], name: str) -> int:
    return sum(row[name] == "1" for row in rows)


def year_view_table(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    table = []
    for year in YEARS:
        subset = [row for row in rows if row["source_file_year"] == str(year)]
        total = len(subset)
        missing = sum(row["조회수"] == "" for row in subset)
        zeros = sum(row["조회수"] == "0" for row in subset)
        table.append(
            {
                "year": year,
                "rows": total,
                "view_missing": missing,
                "view_missing_rate": (missing / total) if total else 0,
                "view_zero": zeros,
                "view_zero_rate": (zeros / total) if total else 0,
            }
        )
    return table


def write_dictionary() -> None:
    records = [
        ("게시물 링크", "원본", "X 게시물 URL", "문자열", "-", "빈 값은 링크 없음", "원본 셀을 그대로 유지"),
        ("계정 ID", "원본", "게시 계정. @사용자명", "문자열", "-", "빈 값은 계정 ID 없음", "원본 셀을 그대로 유지"),
        ("계정 소개글", "원본", "계정 소개", "문자열", "-", "2023–2026은 원본에 컬럼이 없어 빈칸. 2022의 빈칸은 수집값 없음", "2022 파일에만 있던 컬럼. 다른 연도는 빈칸으로 정렬"),
        ("댓글 개수", "원본", "댓글 수 원문", "문자열", "개", "2022는 원본에 컬럼이 없어 빈칸", "2023–2026 원문 유지. 정수로 바꾸지 않음"),
        ("리포스트 개수", "원본", "리포스트 수 원문", "문자열", "개", "빈 값은 원문 결측", "원본 셀을 그대로 유지"),
        ("본문", "원본", "게시물 본문", "문자열", "-", "빈 값 또는 공백만 있으면 본문 없음", "개행·이모지·URL·대소문자를 바꾸지 않음"),
        ("계정 이름", "원본", "표시 이름", "문자열", "-", "빈 값은 표시 이름 없음", "원본 셀을 그대로 유지"),
        ("작성 시각", "원본", "원본 작성 시각 문자열", "문자열", "초", "빈 값은 시각 없음", "시간대 변환 없이 원문 유지"),
        ("조회수", "원본", "조회수 원문", "문자열", "회", "빈 값은 조회수 원문 결측. 0은 실제 0", "0과 빈칸을 서로 바꾸지 않음"),
        ("좋아요 수", "원본", "좋아요 수 원문", "문자열", "개", "빈 값은 원문 결측", "원본 셀을 그대로 유지"),
        ("키워드", "원본", "수집 키워드. 복수는 | 구분", "문자열", "-", "빈 값은 키워드 없음", "원본 셀을 그대로 유지"),
        ("source_file", "추가", "행이 나온 원본 파일명", "문자열", "-", "없음", "읽은 연도별 파일명"),
        ("source_file_year", "추가", "파일명에서 추출한 연도", "정수", "년", "없음", "x_chiikawa_YYYY.csv의 YYYY"),
        ("post_id", "추가", "게시물 링크의 status 숫자 ID", "문자열", "-", "빈 값은 추출 실패", r"/status/(\d+) 로 추출. 부동소수로 저장하지 않음"),
        ("flag_post_id_extract_failed", "추가", "post_id 추출 실패", "정수 플래그", "1=실패", "해당 없음", "post_id가 비면 1"),
        ("created_at_kst", "추가", "분석용 작성 시각", "문자열", "YYYY-MM-DD HH:mm:ss", "빈 값은 시각 해석 실패", "원문이 이미 시각 문자열이면 시차를 더하지 않고 그대로 사용"),
        ("year", "추가", "created_at_kst의 연도", "정수", "년", "빈 값은 시각 해석 실패", "created_at_kst의 연도"),
        ("month", "추가", "created_at_kst의 월", "문자열", "MM", "빈 값은 시각 해석 실패", "01–12 두 자리"),
        ("flag_created_at_parse_failed", "추가", "작성 시각 해석 실패", "정수 플래그", "1=실패", "해당 없음", "YYYY-MM-DD HH:mm:ss 가 아니거나 존재하지 않는 날짜면 1"),
        ("flag_source_year_mismatch", "추가", "파일 연도와 작성 연도 불일치", "정수 플래그", "1=불일치", "시각 해석 실패 행은 0", "source_file_year와 year가 다르면 1"),
        ("like_count_int", "추가", "좋아요 수 분석값", "nullable 정수", "개", "빈칸은 결측. 0은 0", "원문이 정수 또는 정수인 x.0 일 때만 변환"),
        ("repost_count_int", "추가", "리포스트 수 분석값", "nullable 정수", "개", "빈칸은 결측. 0은 0", "원문이 정수 또는 정수인 x.0 일 때만 변환"),
        ("view_count_int", "추가", "조회수 분석값", "nullable 정수", "회", "빈칸은 결측. 0은 0", "결측을 0이나 평균으로 채우지 않음"),
        ("flag_like_parse_failed", "추가", "좋아요 수 정수 해석 실패", "정수 플래그", "1=실패", "빈 원문은 0", "정수로 정확히 해석되지 않으면 1"),
        ("flag_repost_parse_failed", "추가", "리포스트 수 정수 해석 실패", "정수 플래그", "1=실패", "빈 원문은 0", "정수로 정확히 해석되지 않으면 1"),
        ("flag_view_parse_failed", "추가", "조회수 정수 해석 실패", "정수 플래그", "1=실패", "빈 원문은 0", "정수로 정확히 해석되지 않으면 1"),
        ("flag_like_negative", "추가", "좋아요 수 음수", "정수 플래그", "1=음수", "해당 없음", "분석값이 0보다 작으면 1"),
        ("flag_repost_negative", "추가", "리포스트 수 음수", "정수 플래그", "1=음수", "해당 없음", "분석값이 0보다 작으면 1"),
        ("flag_view_negative", "추가", "조회수 음수", "정수 플래그", "1=음수", "해당 없음", "분석값이 0보다 작으면 1"),
        ("flag_duplicate_post_id", "추가", "같은 post_id가 2행 이상", "정수 플래그", "1=중복 그룹", "post_id 추출 실패는 중복으로 묶지 않음", "행을 삭제하거나 합치지 않고 표시만 함"),
        ("flag_duplicate_full_row", "추가", "원본 컬럼 전체가 같은 중복", "정수 플래그", "1=완전 중복", "해당 없음", "원본 11개 컬럼이 모두 같은 행"),
        ("flag_duplicate_post_conflict", "추가", "같은 post_id의 본문·작성자·반응 수치가 다름", "정수 플래그", "1=값 불일치", "중복 post_id가 없으면 0", "본문, 계정 ID, 계정 이름, 좋아요·리포스트·조회수·댓글 원문 비교"),
        ("flag_empty_link", "추가", "게시물 링크가 비어 있음", "정수 플래그", "1=빈 링크", "해당 없음", "앞뒤 공백을 뺀 링크가 비면 1. 원문은 수정하지 않음"),
        ("flag_empty_body", "추가", "본문이 비어 있음", "정수 플래그", "1=빈 본문", "해당 없음", "앞뒤 공백을 뺀 본문이 비면 1. 원문은 수정하지 않음"),
        ("flag_empty_account_name", "추가", "계정 이름이 비어 있음", "정수 플래그", "1=빈 이름", "해당 없음", "앞뒤 공백을 뺀 계정 이름이 비면 1"),
    ]
    with OUT_DICT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["컬럼명", "구분", "의미", "자료형", "단위", "결측값 의미", "생성 규칙"])
        writer.writerows(records)


def write_report(rows: list[dict[str, str]], meta: dict, checks: dict[str, object]) -> None:
    view_table = year_view_table(rows)
    total = len(rows)
    view_missing = sum(item["view_missing"] for item in view_table)
    view_zero = sum(item["view_zero"] for item in view_table)
    lines = [
        "# X 치이카와 stage 1 품질 보고서",
        "",
        "## 입력 확인",
        "",
        "- 참조 경로 `integrated/x_chiikawa_2022_2026_merged_raw.csv`, `integrated/merge_report.md`, `integrated/column_dictionary.csv` 는 `02_csv/03_x`에 없습니다.",
        "- 기존 통합 점검 결과를 읽을 수 없어, 수정하지 않은 연도별 원본 5개를 입력으로 사용했습니다.",
        "- 안내된 통합 행 수는 5,000행입니다. 실제 파일 합계는 4,889행입니다. 2024년 파일이 889행입니다.",
        "",
        "| 파일 | 행 수 | 원본 컬럼 |",
        "|---|---:|---|",
    ]
    for year in YEARS:
        columns = " / ".join(meta["source_columns"][year])
        count = sum(row["source_file_year"] == str(year) for row in rows)
        lines.append(f"| x_chiikawa_{year}.csv | {count} | {columns} |")
    lines += [
        "",
        "- 2022년만 `계정 소개글`이 있고 `댓글 개수`가 없습니다. 나머지 연도는 반대입니다.",
        "- 정렬용으로 없는 컬럼은 빈칸입니다. 이는 수집된 빈 값과 다릅니다. 2022년 `댓글 개수` 빈칸 1,000개, 2023–2026년 `계정 소개글` 빈칸 3,889개입니다.",
        "",
        "## 시간대",
        "",
        "- `작성 시각`은 `YYYY-MM-DD HH:mm:ss`이고 `Z`나 `+09:00` 같은 오프셋이 없습니다.",
        "- 해석에 성공한 시각은 시차를 더하지 않고 `created_at_kst`에 그대로 넣었습니다.",
        "- 원문만으로는 한국시간으로 저장됐는지, 다른 지역 시각이 같은 형식으로 저장됐는지 구분되지 않습니다. 그래서 UTC로 보고 9시간을 더하는 변환은 하지 않았습니다.",
        f"- 시각 해석 실패 {count_flag(rows, 'flag_created_at_parse_failed')}건, 파일 연도와 작성 연도 불일치 {count_flag(rows, 'flag_source_year_mismatch')}건입니다.",
        "",
        "## 변환 규칙",
        "",
        "- `post_id`는 URL의 `/status/` 뒤 숫자를 문자열로 추출합니다. 15자리 이상이라 정수형으로 저장하지 않습니다.",
        "- 좋아요·리포스트·조회수는 공백을 제거한 원문이 정수이거나 `10.0`처럼 정수로 똑같은 값일 때만 nullable 정수로 변환합니다.",
        "- 원문이 비어 있으면 분석값도 빈칸입니다. 변환 실패가 아닙니다.",
        "- 원문이 비정수이면 분석값은 빈칸이고 해당 parse 플래그가 1입니다.",
        "- 음수는 해석 가능한 정수로 저장하고 negative 플래그를 1로 둡니다. 이번 데이터에는 음수가 없습니다.",
        "- 조회수 결측은 0이나 평균으로 채우지 않았습니다. 원문 0은 0으로 유지합니다.",
        "",
        "## 처리 전후",
        "",
        f"- 처리 전 행 수 {meta['input_rows']} / 저장 후 재읽기 {checks['reloaded_rows']}. 행 수 유지: {'예' if meta['input_rows'] == checks['reloaded_rows'] else '아니오'}.",
        f"- 원본 11개 컬럼과 post_id·시각·정수 분석값 재읽기 불일치 {checks['mismatches']}건.",
        f"- UTF-8 BOM 확인: {'예' if checks['bom'] else '아니오'}.",
        f"- 조회수 원문 결측이 분석값으로 채워진 행 {checks['missing_filled']}건.",
        f"- 조회수 원문 0이 다른 값으로 바뀐 행 {checks['zero_rewritten']}건.",
        "",
        "## 연도별 조회수 결측",
        "",
        "결측은 원문 `조회수`가 빈칸인 행입니다. 비율은 해당 연도 행 수 기준입니다.",
        "",
        "| 연도 | 행 수 | 조회수 결측 | 결측률 | 조회수 0 | 0의 비율 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in view_table:
        lines.append(
            f"| {item['year']} | {item['rows']} | {item['view_missing']} | "
            f"{item['view_missing_rate']:.1%} | {item['view_zero']} | {item['view_zero_rate']:.1%} |"
        )
    lines += [
        f"| 합계 | {total} | {view_missing} | {view_missing / total:.1%} | {view_zero} | {view_zero / total:.1%} |",
        "",
        "- 조회수 결측 972건은 모두 2022년입니다. 2022년 결측률은 97.2%이고, 값이 있는 행은 28건입니다.",
        "- 조회수 0은 2022년을 포함해 모든 연도에서 0건입니다. 0이 2022년에 몰려 있지 않습니다.",
        "- 원문을 다시 열어 보지 않았으므로, 2022년 결측이 수집 실패인지 플랫폼이 값을 주지 않은 것인지는 정하지 않습니다.",
        "",
        "## 중복",
        "",
        f"- post_id 중복 그룹 {meta['post_id_duplicate_groups']}개, 초과 행 {meta['post_id_duplicate_extra_rows']}건.",
        f"- 원본 컬럼 전체 중복 그룹 {meta['full_duplicate_groups']}개, 초과 행 {meta['full_duplicate_extra_rows']}건.",
        f"- 같은 post_id에서 본문·작성자·반응 수치가 다른 그룹 {meta['conflict_groups']}개.",
        "- 중복 행은 삭제하거나 합치지 않았습니다.",
        "",
        "## 이상값과 빈 값",
        "",
        f"- post_id 추출 실패 {count_flag(rows, 'flag_post_id_extract_failed')}건.",
        f"- 날짜 변환 실패 {count_flag(rows, 'flag_created_at_parse_failed')}건.",
        f"- 좋아요 변환 실패 {count_flag(rows, 'flag_like_parse_failed')}건, 음수 {count_flag(rows, 'flag_like_negative')}건.",
        f"- 리포스트 변환 실패 {count_flag(rows, 'flag_repost_parse_failed')}건, 음수 {count_flag(rows, 'flag_repost_negative')}건.",
        f"- 조회수 변환 실패 {count_flag(rows, 'flag_view_parse_failed')}건, 음수 {count_flag(rows, 'flag_view_negative')}건.",
        f"- 빈 링크 {count_flag(rows, 'flag_empty_link')}건, 빈 본문 {count_flag(rows, 'flag_empty_body')}건, 빈 계정 이름 {count_flag(rows, 'flag_empty_account_name')}건.",
        "- 2022년 계정 소개글 원문 `/` 가 1건 있습니다. 빈 값으로 바꾸지 않았습니다.",
        "",
        "## 다음 단계에서 결정할 기준",
        "",
        "- 2024년 889행을 그대로 연도 구성 비교에 쓸지, 수집을 보완할 대상인지 결정이 필요합니다.",
        "- `created_at_kst`를 한국시간으로 확정할지, 원천 수집 로그로 시간대를 확인할지 결정이 필요합니다.",
        "- 2022년 조회수 결측을 연도 비교에서 제외할지, 결측 지표로 따로 볼지 결정이 필요합니다. 0으로 대체하는 방식은 이번 점검에서 사용하지 않았습니다.",
        "- 2022년에만 있는 계정 소개글과 2023년 이후의 댓글 개수를 같은 지표로 합칠지 결정이 필요합니다.",
        "- 캐릭터 언급과 키링·인형·영화 등 소비 형태 분류는 이번 단계에서 하지 않았습니다.",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    rows, meta = build_rows()
    write_csv(rows)
    checks = verify(rows)
    write_dictionary()
    write_report(rows, meta, checks)
    print(f"rows={len(rows)} saved={OUT_CSV.name} mismatches={checks['mismatches']}")


if __name__ == "__main__":
    main()
