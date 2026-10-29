# -*- coding: utf-8 -*-
"""X stage1 데이터를 1NF–3NF 테이블로 분리한다. 원본 CSV는 수정하지 않는다."""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

CLEAN_DIR = Path(__file__).resolve().parent
SRC = CLEAN_DIR / "1차 정제.csv"
OUT_DIR = CLEAN_DIR / "normalized"
XLSX = CLEAN_DIR / "x_정규화.xlsx"
YEAR_RE = re.compile(r"(\d{4})")

POST_COLUMNS = [
    "post_id",
    "게시물 링크",
    "계정 ID",
    "계정 소개글",
    "계정 이름",
    "본문",
    "작성 시각",
    "댓글 개수",
    "리포스트 개수",
    "조회수",
    "좋아요 수",
]


def split_keywords(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def read_rows() -> list[dict[str, str]]:
    with SRC.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_table(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_rows = read_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    posts: dict[str, dict[str, str]] = {}
    post_conflicts: list[str] = []
    keywords: set[str] = set()
    post_keywords: list[dict[str, str]] = []
    source_files: dict[str, str] = {}
    post_sources: list[dict[str, str]] = []
    file_row_no: dict[str, int] = {}
    restore_fail = 0

    for input_no, row in enumerate(source_rows, start=1):
        post_id = (row.get("post_id") or "").strip()
        source_file = (row.get("source_file") or "").strip()
        year_match = YEAR_RE.search(source_file)
        source_year = year_match.group(1) if year_match else ""
        if source_file in source_files and source_files[source_file] != source_year:
            raise SystemExit(f"같은 파일의 기준 연도가 다릅니다: {source_file}")
        source_files[source_file] = source_year

        file_row_no[source_file] = file_row_no.get(source_file, 0) + 1
        post_sources.append(
            {
                "source_file": source_file,
                "source_row": str(file_row_no[source_file]),
                "post_id": post_id,
                "input_row_no": str(input_no),
            }
        )

        post = {column: row.get(column, "") if column != "post_id" else post_id for column in POST_COLUMNS}
        if post_id in posts:
            if posts[post_id] != post:
                post_conflicts.append(post_id)
        else:
            posts[post_id] = post

        parts = split_keywords(row.get("키워드") or "")
        if "|".join(parts) != (row.get("키워드") or "").strip():
            restore_fail += 1
        for order, keyword in enumerate(parts, start=1):
            keywords.add(keyword)
            post_keywords.append(
                {"post_id": post_id, "keyword_order": str(order), "keyword": keyword}
            )

    if post_conflicts:
        raise SystemExit(f"post_id 속성이 서로 다른 중복 {len(set(post_conflicts))}건. 임의 삭제하지 않고 중단합니다.")

    x_posts = list(posts.values())
    x_keywords = [{"keyword": keyword} for keyword in sorted(keywords)]
    x_source_files = [
        {"source_file": name, "source_year": source_files[name]}
        for name in sorted(source_files)
    ]

    pk_posts = {row["post_id"] for row in x_posts}
    pk_kw = {(row["post_id"], row["keyword_order"]) for row in post_keywords}
    pk_src = {(row["source_file"], row["source_row"]) for row in post_sources}
    if len(pk_posts) != len(x_posts):
        raise SystemExit("x_posts.post_id 가 유일하지 않습니다.")
    if len(pk_kw) != len(post_keywords):
        raise SystemExit("x_post_keywords (post_id, keyword_order) 가 유일하지 않습니다.")
    if len(pk_src) != len(post_sources):
        raise SystemExit("x_post_sources (source_file, source_row) 가 유일하지 않습니다.")
    if any(row["keyword"] not in keywords for row in post_keywords):
        raise SystemExit("x_post_keywords.keyword 참조 오류")
    if any(row["post_id"] not in pk_posts for row in post_keywords):
        raise SystemExit("x_post_keywords.post_id 참조 오류")
    if any(row["source_file"] not in source_files for row in post_sources):
        raise SystemExit("x_post_sources.source_file 참조 오류")
    if any(row["post_id"] not in pk_posts for row in post_sources):
        raise SystemExit("x_post_sources.post_id 참조 오류")
    if len(post_sources) != len(source_rows):
        raise SystemExit("원본 행 수가 x_post_sources 와 다릅니다.")
    if restore_fail:
        raise SystemExit(f"키워드 복원 불일치 {restore_fail}건")

    write_table(OUT_DIR / "x_posts.csv", POST_COLUMNS, x_posts)
    write_table(OUT_DIR / "x_keywords.csv", ["keyword"], x_keywords)
    write_table(
        OUT_DIR / "x_post_keywords.csv",
        ["post_id", "keyword_order", "keyword"],
        post_keywords,
    )
    write_table(OUT_DIR / "x_source_files.csv", ["source_file", "source_year"], x_source_files)
    write_table(
        OUT_DIR / "x_post_sources.csv",
        ["source_file", "source_row", "post_id", "input_row_no"],
        post_sources,
    )

    tables = {
        "x_posts": pd.read_csv(OUT_DIR / "x_posts.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False),
        "x_keywords": pd.read_csv(OUT_DIR / "x_keywords.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False),
        "x_post_keywords": pd.read_csv(OUT_DIR / "x_post_keywords.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False),
        "x_source_files": pd.read_csv(OUT_DIR / "x_source_files.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False),
        "x_post_sources": pd.read_csv(OUT_DIR / "x_post_sources.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False),
    }
    views = tables["x_posts"]["조회수"].str.strip()
    invalid_views = ~views.str.fullmatch(r"\d+") & views.ne("")
    if invalid_views.any():
        raise SystemExit(f"정수로 해석할 수 없는 조회수 {int(invalid_views.sum())}건")
    tables["x_posts"]["조회수"] = pd.to_numeric(views.replace("", pd.NA), errors="coerce").astype("Int64")
    with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
        for name, frame in tables.items():
            frame.to_excel(writer, sheet_name=name, index=False)

    print(f"input_rows={len(source_rows)}")
    print(f"x_posts={len(x_posts)} x_keywords={len(x_keywords)} x_post_keywords={len(post_keywords)}")
    print(f"x_source_files={len(x_source_files)} x_post_sources={len(post_sources)}")
    print(f"restore_fail={restore_fail} post_conflicts={len(post_conflicts)}")
    print(XLSX)


if __name__ == "__main__":
    main()
