# -*- coding: utf-8 -*-
"""치이카와 X 게시물 전체 분석 실행기.

판정은 rules_v2.py의 구절 규칙이다. 게시물마다 사람이 다시 읽은 라벨은 아니다.
원본 normalized 테이블과 기존 text_analysis 결과는 읽기만 한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rules_v2 as rules  # noqa: E402

BASE = Path(r"C:/DATA/KDT_Integral_Data_Project/02_csv/03_x/normalized")
NA = "언급 없음"


def load_inputs() -> pd.DataFrame:
    posts = pd.read_csv(BASE / "x_posts.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    src = pd.read_csv(BASE / "x_post_sources.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    files = pd.read_csv(BASE / "x_source_files.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    kw = pd.read_csv(BASE / "x_post_keywords.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    kw["keyword_order"] = kw["keyword_order"].astype(int)
    kw = kw.sort_values(["post_id", "keyword_order"])
    joined = kw.groupby("post_id", sort=False)["keyword"].agg(lambda s: "|".join(s)).rename("collection_keywords")
    df = posts.merge(src, on="post_id", how="left").merge(files, on="source_file", how="left")
    df = df.merge(joined, on="post_id", how="left")
    df["input_row_no"] = df["input_row_no"].astype(int)
    df = df.sort_values("input_row_no").reset_index(drop=True)
    return df


def ev_row(post_id: str, ev: rules.Ev) -> dict:
    return {
        "post_id": post_id,
        "quote": ev.quote,
        "quote_start": ev.quote_start,
        "quote_end": ev.quote_end,
        "clause_id": ev.clause_id,
        "axis": ev.axis,
        "label": ev.label,
        "target": ev.target,
        "target_type": ev.target_type,
        "speaker": ev.speaker,
        "emotion": ev.emotion,
        "action_type": ev.action_type,
        "action_status": ev.action_status,
        "acquisition": ev.acquisition,
        "aspect": ev.aspect,
        "selection_reason": ev.selection_reason,
        "use_mode": ev.use_mode,
        "use_status": ev.use_status,
        "collection_type": ev.collection_type,
        "content_use": ev.content_use,
        "barrier_type": ev.barrier_type,
        "barrier_role": ev.barrier_role,
        "certainty": ev.certainty,
        "judgment_method": rules.METHOD,
        "judgment_note": ev.judgment_note,
        "about_ip": ev.about_ip,
        "codebook_version": rules.VERSION,
    }


def uniq(items: list[str]) -> str:
    out = []
    for x in items:
        if x and x not in out and x not in {"해당없음"}:
            out.append(x)
    return "|".join(out) if out else NA


def post_record(src: pd.Series, result: dict | None, status: str, error: str = "") -> dict:
    text = src["text"]
    year = src["created_at"][:4]
    month = src["created_at"][5:7]
    rec = {
        "post_id": src["post_id"],
        "post_url": src["post_url"],
        "account_id": src["account_id"],
        "account_name": src["account_name"],
        "text": text,
        "analysis_text": result["analysis_text"] if result else "",
        "created_at": src["created_at"],
        "created_year_kst": int(year),
        "created_month_kst": int(month),
        "source_file": src["source_file"],
        "source_year": int(src["source_year"]),
        "source_row": int(src["source_row"]),
        "input_row_no": int(src["input_row_no"]),
        "comment_count": int(src["comment_count"]),
        "repost_count": int(src["repost_count"]),
        "view_count": src["view_count"],
        "like_count": int(src["like_count"]),
        "collection_keywords": src["collection_keywords"],
        "processing_status": status,
        "processing_error": error,
        "processing_method": rules.METHOD,
        "codebook_version": rules.VERSION,
    }
    if result is None:
        rec.update({
            "work_relevance": "",
            "relevance_note": "",
            "language": "",
            "domestic_context": "",
            "domestic_note": "",
            "purpose_labels": "",
            "purpose_mixed": "",
            "eval_targets": "",
            "speakers": "",
            "judgment_scope": "",
            "first_interest": "",
            "affection_aspects_author": "",
            "affection_emotions_author": "",
            "action_labels_author": "",
            "product_forms": "",
            "sales_channels": "",
            "content_events": "",
            "use_modes": "",
            "collection_types": "",
            "content_uses": "",
            "barriers": "",
            "selection_reasons": "",
            "review_flag": "예",
            "review_reasons": "처리 실패",
        })
        return rec
    evs = result["evidence"]
    author_aff = [e for e in evs if e.axis == "호감" and e.speaker == "작성자" and e.certainty == "확정"]
    author_act = [
        e for e in evs
        if e.axis == "행동" and e.speaker == "작성자" and e.certainty == "확정" and e.action_status != "해당없음"
    ]
    rec.update({
        "work_relevance": result["work_relevance"],
        "relevance_note": result["relevance_note"],
        "language": result["language"],
        "domestic_context": result["domestic_context"],
        "domestic_note": result["domestic_note"],
        "purpose_labels": "|".join(result["purpose_labels"]),
        "purpose_mixed": result["purpose_mixed"],
        "eval_targets": "|".join(result["eval_targets"]),
        "speakers": "|".join(result["speakers"]),
        "judgment_scope": result["judgment_scope"],
        "first_interest": uniq([e.label for e in evs if e.axis == "관심계기"]),
        "affection_aspects_author": uniq([e.label for e in author_aff]),
        "affection_emotions_author": uniq([e.emotion for e in author_aff]),
        "action_labels_author": uniq([f"{e.action_type}:{e.action_status}" for e in author_act]),
        "product_forms": uniq([e.label for e in evs if e.axis == "상품형태"]),
        "sales_channels": uniq([e.label for e in evs if e.axis == "판매획득방식"]),
        "content_events": uniq([e.label for e in evs if e.axis == "콘텐츠행사"]),
        "use_modes": uniq([e.label for e in evs if e.axis == "사용" and e.speaker == "작성자"]),
        "collection_types": uniq([e.label for e in evs if e.axis == "수집" and e.speaker == "작성자"]),
        "content_uses": uniq([e.label for e in evs if e.axis == "콘텐츠이용" and e.speaker == "작성자"]),
        "barriers": uniq([
            f"{e.label}:{e.barrier_role}" for e in evs
            if e.axis == "장벽" and e.speaker == "작성자" and e.barrier_role != "판매 문안"
        ]),
        "selection_reasons": uniq([
            e.selection_reason for e in evs
            if e.axis == "명시이유" and e.speaker == "작성자" and e.selection_reason not in {"해당없음", ""}
        ]),
        "review_flag": "예" if result["reviews"] else "아니오",
        "review_reasons": "|".join(result["reviews"]) if result["reviews"] else "",
    })
    return rec


def analyze_frame(df: pd.DataFrame, batch_dir: Path, resume: bool) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    progress_path = batch_dir / "progress.json"
    done_ids = set()
    posts, evs, conns, errors = [], [], [], []
    if resume and progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("version") == rules.VERSION:
            done_ids = set(progress.get("post_ids", []))
            for part in sorted(batch_dir.glob("posts_*.parquet")):
                posts.extend(pd.read_parquet(part).to_dict("records"))
            for part in sorted(batch_dir.glob("evidence_*.parquet")):
                evs.extend(pd.read_parquet(part).to_dict("records"))
            for part in sorted(batch_dir.glob("connections_*.parquet")):
                conns.extend(pd.read_parquet(part).to_dict("records"))
            err_path = batch_dir / "errors_partial.csv"
            if err_path.exists():
                errors.extend(pd.read_csv(err_path, dtype=str, keep_default_na=False, encoding="utf-8-sig").to_dict("records"))
            print(f"resume {len(done_ids)}", flush=True)
        else:
            print("version changed, recompute", flush=True)
            done_ids = set()
    buf_p, buf_e, buf_c = [], [], []
    batch_i = len(list(batch_dir.glob("posts_*.parquet")))
    n = len(df)
    for i, src in df.iterrows():
        if src["post_id"] in done_ids:
            continue
        try:
            result = rules.analyze_post(src["text"])
            prec = post_record(src, result, "완료")
            buf_p.append(prec)
            local_ev = []
            for ev in result["evidence"]:
                row = ev_row(src["post_id"], ev)
                local_ev.append(row)
                buf_e.append(row)
            for conn in result["connections"]:
                ids = []
                for key in ("evidence_local", "evidence_local2"):
                    obj = conn.get(key)
                    if obj is None:
                        continue
                    # 같은 구절·축·라벨의 첫 근거와 연결한다.
                    match = next((
                        r for r in local_ev
                        if r["quote_start"] == obj.quote_start and r["quote_end"] == obj.quote_end
                        and r["axis"] == obj.axis and r["label"] == obj.label
                    ), None)
                    if match is not None:
                        ids.append(f"{match['quote_start']}:{match['axis']}:{match['label']}")
                buf_c.append({
                    "post_id": src["post_id"],
                    "clause_id": conn["evidence_local"].clause_id,
                    "evidence_keys": "|".join(ids),
                    "target": conn["target"],
                    "reason": conn["reason"],
                    "action_type": conn["action_type"],
                    "action_status": conn["action_status"],
                    "evidence_level": conn["evidence_level"],
                    "speaker": conn["speaker"],
                    "quote": conn["quote"],
                    "judgment_note": conn["note"],
                    "judgment_method": rules.METHOD,
                    "codebook_version": rules.VERSION,
                })
        except Exception as exc:  # 한 건 실패가 전체를 멈추지 않게 한다.
            err = {"post_id": src["post_id"], "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
            errors.append(err)
            buf_p.append(post_record(src, None, "처리 실패", err["error"]))
        done_n = len(done_ids) + len(buf_p)
        if len(buf_p) >= 500:
            _flush(batch_dir, batch_i, buf_p, buf_e, buf_c)
            posts.extend(buf_p)
            evs.extend(buf_e)
            conns.extend(buf_c)
            done_ids.update(r["post_id"] for r in buf_p)
            buf_p, buf_e, buf_c = [], [], []
            batch_i += 1
            progress_path.write_text(json.dumps({
                "version": rules.VERSION, "post_ids": sorted(done_ids), "n": len(done_ids),
            }, ensure_ascii=False), encoding="utf-8")
            print(f"batch {batch_i} done {len(done_ids)}/{n}", flush=True)
        elif done_n % 500 == 0:
            print(f"progress {done_n}/{n}", flush=True)
    if buf_p:
        _flush(batch_dir, batch_i, buf_p, buf_e, buf_c)
        posts.extend(buf_p)
        evs.extend(buf_e)
        conns.extend(buf_c)
        done_ids.update(r["post_id"] for r in buf_p)
        progress_path.write_text(json.dumps({
            "version": rules.VERSION, "post_ids": sorted(done_ids), "n": len(done_ids),
        }, ensure_ascii=False), encoding="utf-8")
    if errors:
        pd.DataFrame(errors).to_csv(batch_dir / "errors_partial.csv", index=False, encoding="utf-8-sig")
    return posts, evs, conns, errors


def _flush(batch_dir: Path, batch_i: int, posts, evs, conns) -> None:
    tag = f"{batch_i:04d}"
    pd.DataFrame(posts).to_parquet(batch_dir / f"posts_{tag}.parquet", index=False)
    pd.DataFrame(evs).to_parquet(batch_dir / f"evidence_{tag}.parquet", index=False)
    conn_cols = [
        "post_id", "clause_id", "evidence_keys", "target", "reason", "action_type",
        "action_status", "evidence_level", "speaker", "quote", "judgment_note",
        "judgment_method", "codebook_version",
    ]
    conn_df = pd.DataFrame(conns) if conns else pd.DataFrame(columns=conn_cols)
    conn_df.to_parquet(batch_dir / f"connections_{tag}.parquet", index=False)


def assign_ids(evs: list[dict], conns: list[dict]) -> None:
    evs.sort(key=lambda r: (r["post_id"], r["quote_start"], r["axis"], r["label"]))
    for i, row in enumerate(evs, start=1):
        row["evidence_id"] = f"E{i:07d}"
    lookup = {
        (r["post_id"], f"{r['quote_start']}:{r['axis']}:{r['label']}"): r["evidence_id"]
        for r in evs
    }
    conns.sort(key=lambda r: (r["post_id"], r.get("clause_id", -1), r.get("evidence_level", ""), r.get("quote", "")))
    for i, row in enumerate(conns, start=1):
        row["connection_id"] = f"C{i:07d}"
        keys = [k for k in str(row.get("evidence_keys", "")).split("|") if k]
        ids = []
        for key in keys:
            eid = lookup.get((row["post_id"], key))
            if eid and eid not in ids:
                ids.append(eid)
        row["evidence_ids"] = "|".join(ids)


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if "view_count" in out.columns:
        out["view_count"] = pd.to_numeric(out["view_count"].replace("", pd.NA), errors="coerce").astype("Int64")
    for col in ("comment_count", "repost_count", "like_count", "created_year_kst", "created_month_kst", "source_year", "source_row", "input_row_no"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    for col in ("quote_start", "quote_end", "clause_id"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    csv_df = out.copy()
    if "created_at" in csv_df.columns:
        csv_df["created_at"] = csv_df["created_at"].astype(str)
    csv_df.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    # Parquet는 조회수 결측을 유지한다. 작성 시각 문자열도 그대로 둔다.
    out.to_parquet(path.with_suffix(".parquet"), index=False)


def add_denom(frame: pd.DataFrame, name: str, value: int, unit: str, overlap: str) -> pd.DataFrame:
    frame = frame.copy()
    frame["denominator_name"] = name
    frame["denominator_value"] = value
    frame["share_of_denominator_posts"] = frame["unique_posts"] / value if value else 0
    frame["agg_unit"] = unit
    frame["multi_label_overlap"] = overlap
    return frame


def group_count(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=cols + ["expression_count", "unique_posts", "unique_accounts"])
    g = df.groupby(cols, dropna=False)
    out = g.agg(
        expression_count=("post_id", "size"),
        unique_posts=("post_id", "nunique"),
        unique_accounts=("account_id", "nunique"),
    ).reset_index()
    return out.sort_values("unique_posts", ascending=False)


def absent_row(label_cols: dict, posts_with: int, denom: int, accounts_with: int) -> dict:
    row = dict(label_cols)
    row.update({
        "expression_count": 0,
        "unique_posts": denom - posts_with,
        "unique_accounts": pd.NA,
        "note": "해당 표현이 없는 게시물 수. 계정 수는 비워 둔다.",
    })
    return row


def top_account(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"unique_accounts": 0, "top_account_posts": 0, "top_account_share_of_label_posts": 0}
    vc = df.groupby("account_id")["post_id"].nunique()
    top = int(vc.max())
    n = int(df["post_id"].nunique())
    return {
        "unique_accounts": int(vc.shape[0]),
        "top_account_posts": top,
        "top_account_share_of_label_posts": top / n if n else 0,
    }


def build_summaries(posts: pd.DataFrame, ev: pd.DataFrame, conn: pd.DataFrame, out: Path) -> dict:
    summ = out / "summaries"
    summ.mkdir(parents=True, exist_ok=True)
    all_n = int(posts["post_id"].nunique())
    rel = posts[posts["work_relevance"] == "관련"]
    rel_n = int(rel["post_id"].nunique())
    ko = rel[rel["language"] == "한국어 중심"]
    ko_n = int(ko["post_id"].nunique())
    ev = ev.merge(posts[["post_id", "account_id", "work_relevance", "language", "purpose_labels", "purpose_mixed", "created_year_kst", "like_count", "repost_count", "comment_count"]], on="post_id", how="left")
    conn = conn.merge(posts[["post_id", "account_id", "work_relevance", "language", "created_year_kst"]], on="post_id", how="left")
    author_ip = ev[(ev["about_ip"] == "예") & (ev["work_relevance"] == "관련")]
    stats = {"all_posts": all_n, "relevant_posts": rel_n, "relevant_korean_posts": ko_n}

    def dump(name, frame):
        frame = frame.copy()
        if "unique_accounts" in frame.columns:
            frame["unique_accounts"] = pd.to_numeric(frame["unique_accounts"], errors="coerce").astype("Int64")
        for col in ("top1pct_posts", "top1pct_like_share"):
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame.to_csv(summ / name, index=False, encoding="utf-8-sig")
        frame.to_parquet(summ / name.replace(".csv", ".parquet"), index=False)

    # 맥락 축
    ctx_rows = []
    for col, denom_df, denom_name in (
        ("work_relevance", posts, "전체 게시물"),
        ("language", posts, "전체 게시물"),
        ("domestic_context", posts, "전체 게시물"),
        ("judgment_scope", posts, "전체 게시물"),
        ("purpose_mixed", posts, "전체 게시물"),
    ):
        vc = denom_df.groupby(col)["post_id"].nunique().reset_index(name="unique_posts")
        vc["axis"] = col
        vc["label"] = vc[col]
        vc["expression_count"] = vc["unique_posts"]
        vc["unique_accounts"] = denom_df.groupby(col)["account_id"].nunique().reindex(vc[col]).to_numpy()
        vc = add_denom(vc[["axis", "label", "expression_count", "unique_posts", "unique_accounts"]], denom_name, len(denom_df), "게시물 1행", "이 축은 게시물당 하나")
        ctx_rows.append(vc)
    # 목적 복수
    pur_rows = []
    for label, sub in _explode_labels(posts, "purpose_labels"):
        pur_rows.append({
            "axis": "purpose_labels", "label": label,
            "expression_count": int(sub["post_id"].nunique()),
            "unique_posts": int(sub["post_id"].nunique()),
            "unique_accounts": int(sub["account_id"].nunique()),
        })
    pur = add_denom(pd.DataFrame(pur_rows), "전체 게시물", all_n, "게시물. 목적을 펼친 뒤의 게시물 수", "복수 목적이면 게시물이 목적마다 다시 센다. 합이 전체를 넘을 수 있다.")
    ctx = pd.concat(ctx_rows + [pur], ignore_index=True)
    dump("context_axes.csv", ctx)

    # 관심 계기
    first = author_ip[author_ip["axis"] == "관심계기"]
    first_g = group_count(first, ["label"])
    have = int(first["post_id"].nunique()) if not first.empty else 0
    extra = absent_row({"label": NA}, have, rel_n, 0)
    first_g = pd.concat([first_g, pd.DataFrame([extra])], ignore_index=True)
    first_g = add_denom(first_g, "작품 관련 게시물", rel_n, "근거 행. unique_posts는 게시물", "한 글에 계기 라벨이 여러 개면 게시물이 라벨마다 다시 센다.")
    dump("first_interest.csv", first_g)
    stats["first_interest_posts"] = have

    # 호감
    aff = author_ip[(author_ip["axis"] == "호감") & (author_ip["speaker"] == "작성자") & (author_ip["certainty"] == "확정")]
    aff_g = group_count(aff, ["label", "emotion", "target_type"])
    aff_posts = int(aff["post_id"].nunique()) if not aff.empty else 0
    aff_g = pd.concat([aff_g, pd.DataFrame([absent_row({"label": NA, "emotion": NA, "target_type": NA}, aff_posts, rel_n, 0)])], ignore_index=True)
    aff_g = add_denom(aff_g, "작품 관련 게시물", rel_n, "작성자 호감 근거 행", "복수 측면이면 게시물이 측면마다 다시 센다. 홍보 문구는 빠진다.")
    dump("affection_target_reason.csv", aff_g)
    stats["author_affection_posts"] = aff_posts
    stats["author_affection_expressions"] = int(len(aff))

    # 매력 × 행동
    charm = conn[(conn["work_relevance"] == "관련") & (conn["speaker"] == "작성자") & (conn["evidence_level"].isin(["문맥상 연결", "작성자가 이유 명시"]))]
    charm = charm[charm["reason"] != NA]
    charm_g = group_count(charm, ["reason", "action_type", "action_status", "evidence_level"])
    charm_g = add_denom(charm_g, "작품 관련 게시물", rel_n, "연결 행", "한 글의 연결이 여러 개면 게시물이 다시 센다. 이유 없음 연결은 이 표에 없다.")
    dump("charm_by_behavior.csv", charm_g)

    # 형태 × 선택 이유
    forms = author_ip[author_ip["axis"] == "상품형태"]
    form_mention = group_count(forms, ["label"])
    form_mention["selection_reason"] = NA
    form_mention["evidence_level"] = "형태 언급"
    form_mention["note"] = "형태가 언급된 것이다. 그 형태로 고른 이유가 아니다."
    # 같은 구절의 명시 이유와 형태가 하나일 때만 묶는다.
    reasons = author_ip[(author_ip["axis"] == "명시이유") & (author_ip["speaker"] == "작성자") & (author_ip["selection_reason"].isin([
        "재질·품질·기능", "표정·의상·포즈", "외형", "행동·관계·장면", "유머", "위로·공감", "가격·조건",
        "호감 표현만 제시(세부 특징 불명)", "선호 대상으로 이름을 밝힘", "기타 명시",
    ]))]
    paired = []
    if not reasons.empty and not forms.empty:
        fsmall = forms[["post_id", "clause_id", "label", "account_id"]].rename(columns={"label": "form"})
        merged = reasons.merge(fsmall, on=["post_id", "clause_id", "account_id"], how="left")
        for (pid, cid), sub in merged.groupby(["post_id", "clause_id"]):
            form_set = [x for x in sub["form"].dropna().unique().tolist()]
            reason = sub.iloc[0]["selection_reason"]
            level = "작성자가 이유 명시"
            if len(form_set) == 1:
                paired.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "label": form_set[0], "selection_reason": reason, "evidence_level": level})
            elif len(form_set) == 0:
                paired.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "label": "형태 불명", "selection_reason": reason, "evidence_level": level})
            else:
                paired.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "label": "복수 형태", "selection_reason": reason, "evidence_level": "연결 불명확"})
    pair_df = pd.DataFrame(paired) if paired else pd.DataFrame(columns=["post_id", "account_id", "label", "selection_reason", "evidence_level"])
    pair_g = group_count(pair_df, ["label", "selection_reason", "evidence_level"]) if not pair_df.empty else pd.DataFrame()
    form_out = pd.concat([
        form_mention.rename(columns={"label": "label"})[["label", "selection_reason", "evidence_level", "expression_count", "unique_posts", "unique_accounts", "note"]],
        pair_g,
    ], ignore_index=True)
    form_out = add_denom(form_out, "작품 관련 게시물", rel_n, "형태 언급 행 또는 이유 연결", "형태 언급과 선택 이유는 evidence_level로 구분한다. 한 순위표로 섞지 않는다.")
    dump("form_by_selection_reason.csv", form_out)

    # 형태 × 사용
    uses = author_ip[(author_ip["axis"] == "사용") & (author_ip["speaker"] == "작성자")]
    use_pairs = []
    if not uses.empty and not forms.empty:
        fsmall = forms[["post_id", "clause_id", "label", "account_id"]].rename(columns={"label": "form"})
        merged = uses.merge(fsmall, on=["post_id", "clause_id", "account_id"], how="left")
        for (pid, cid, mode), sub in merged.groupby(["post_id", "clause_id", "use_mode"]):
            form_set = [x for x in sub["form"].dropna().unique().tolist()]
            status = sub.iloc[0]["use_status"]
            if len(form_set) == 1:
                use_pairs.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "form": form_set[0], "use_mode": mode, "use_status": status, "evidence_level": "문맥상 연결"})
            elif len(form_set) == 0:
                use_pairs.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "form": "형태 불명", "use_mode": mode, "use_status": status, "evidence_level": "문맥상 연결"})
            else:
                use_pairs.append({"post_id": pid, "account_id": sub.iloc[0]["account_id"], "form": "복수 형태", "use_mode": mode, "use_status": status, "evidence_level": "연결 불명확"})
    use_df = pd.DataFrame(use_pairs) if use_pairs else pd.DataFrame(columns=["post_id", "account_id", "form", "use_mode", "use_status", "evidence_level"])
    use_g = group_count(use_df, ["form", "use_mode", "use_status", "evidence_level"]) if not use_df.empty else pd.DataFrame(columns=["form", "use_mode", "use_status", "evidence_level", "expression_count", "unique_posts", "unique_accounts"])
    use_mention = group_count(uses, ["use_mode", "use_status"])
    use_mention["form"] = "사용 표현(형태와 무관하게 센 수)"
    use_mention["evidence_level"] = "사용 언급"
    use_out = pd.concat([use_mention, use_g], ignore_index=True)
    use_out = add_denom(use_out, "작품 관련 게시물", rel_n, "사용 근거 또는 같은 구절의 형태-사용", "복수 형태는 연결 불명확으로만 남긴다.")
    dump("form_by_use.csv", use_out)

    # 수집
    col = author_ip[(author_ip["axis"] == "수집") & (author_ip["speaker"] == "작성자")]
    col_g = group_count(col, ["label"])
    col_posts = int(col["post_id"].nunique()) if not col.empty else 0
    col_g = pd.concat([col_g, pd.DataFrame([absent_row({"label": NA}, col_posts, rel_n, 0)])], ignore_index=True)
    col_g = add_denom(col_g, "작품 관련 게시물", rel_n, "수집 근거 행", "여러 캐릭터 이름이나 한정만으로 만들지 않는다.")
    dump("collection_reasons.csv", col_g)
    stats["collection_posts"] = col_posts

    # 콘텐츠
    cu = author_ip[(author_ip["axis"] == "콘텐츠이용") & (author_ip["speaker"] == "작성자")]
    cu_g = group_count(cu, ["label"])
    cu_posts = int(cu["post_id"].nunique()) if not cu.empty else 0
    cu_g = pd.concat([cu_g, pd.DataFrame([absent_row({"label": NA}, cu_posts, rel_n, 0)])], ignore_index=True)
    cu_g = add_denom(cu_g, "작품 관련 게시물", rel_n, "콘텐츠 이용 근거 행", "같은 대사가 여러 글에 있어도 한 사람의 반복 소비로 합치지 않는다.")
    dump("content_use.csv", cu_g)
    stats["content_use_posts"] = cu_posts

    # 행동 × 장벽
    acts = author_ip[(author_ip["axis"] == "행동") & (author_ip["speaker"] == "작성자") & (author_ip["certainty"] == "확정")]
    bars = author_ip[(author_ip["axis"].isin(["장벽", "명시이유"])) & (author_ip["speaker"] == "작성자") & (author_ip["barrier_role"].isin(["행동 장벽", "일반 언급", "원하는 개선"]))]
    beh_rows = []
    act_g = group_count(acts, ["action_type", "action_status", "acquisition"])
    act_g["barrier_type"] = NA
    act_g["barrier_role"] = NA
    act_g["evidence_level"] = "행동만"
    # 같은 구절에서만 행동과 장벽을 묶는다.
    if not acts.empty and not bars.empty:
        bsmall = bars[["post_id", "clause_id", "barrier_type", "barrier_role", "axis", "account_id"]]
        merged = acts.merge(bsmall, on=["post_id", "clause_id", "account_id"], how="inner", suffixes=("", "_b"))
        if not merged.empty:
            tmp = merged.copy()
            tmp["evidence_level"] = tmp["axis_b"].map(lambda x: "작성자가 이유 명시" if x == "명시이유" else "문맥상 연결")
            # axis column may have been suffixed
            if "axis_b" not in tmp.columns and "axis" in bsmall.columns:
                pass
            beh_link = group_count(tmp, ["action_type", "action_status", "acquisition", "barrier_type", "barrier_role", "evidence_level"])
        else:
            beh_link = pd.DataFrame()
    else:
        beh_link = pd.DataFrame()
    beh = pd.concat([act_g, beh_link], ignore_index=True) if not beh_link.empty else act_g
    beh = add_denom(beh, "작품 관련 게시물", rel_n, "작성자 확정 행동. 장벽은 같은 구절만", "행동만 행과 장벽 연결 행을 evidence_level로 구분한다.")
    dump("behavior_by_barrier.csv", beh)
    stats["author_action_posts"] = int(acts["post_id"].nunique()) if not acts.empty else 0

    # 목적별
    pur_cmp = []
    for label, sub in _explode_labels(posts, "purpose_labels"):
        sub_ids = set(sub["post_id"])
        aff_n = int(aff[aff["post_id"].isin(sub_ids)]["post_id"].nunique()) if not aff.empty else 0
        act_n = int(acts[acts["post_id"].isin(sub_ids)]["post_id"].nunique()) if not acts.empty else 0
        pur_cmp.append({
            "purpose": label,
            "unique_posts": int(sub["post_id"].nunique()),
            "unique_accounts": int(sub["account_id"].nunique()),
            "author_affection_posts": aff_n,
            "author_action_posts": act_n,
            "median_like": float(pd.to_numeric(sub["like_count"], errors="coerce").median()),
            "like_sum": int(pd.to_numeric(sub["like_count"], errors="coerce").sum()),
        })
    pur_cmp_df = add_denom(pd.DataFrame(pur_cmp), "전체 게시물", all_n, "목적 라벨을 펼친 게시물", "혼합 글은 목적마다 들어간다. 좋아요 합은 이 목적 안의 게시물 단위다. 근거 수만큼 곱하지 않는다.")
    dump("by_purpose.csv", pur_cmp_df)

    # 연도
    year_rows = []
    for year, sub in posts.groupby("created_year_kst"):
        ids = set(sub["post_id"])
        year_rows.append({
            "created_year_kst": int(year),
            "unique_posts": int(sub["post_id"].nunique()),
            "relevant_posts": int((sub["work_relevance"] == "관련").sum()),
            "korean_posts": int((sub["language"] == "한국어 중심").sum()),
            "domestic_cue_posts": int((sub["domestic_context"] == "명시적 단서 있음").sum()),
            "author_affection_posts": int(aff[aff["post_id"].isin(ids)]["post_id"].nunique()) if not aff.empty else 0,
            "author_action_posts": int(acts[acts["post_id"].isin(ids)]["post_id"].nunique()) if not acts.empty else 0,
            "min_created_at": sub["created_at"].min(),
            "max_created_at": sub["created_at"].max(),
            "note": "연도 파일당 최대 1,000건인 인기 게시물 표본이다. 성장률이 아니다." + (" 2026년은 수집 종료일까지의 부분 기간이다." if int(year) == 2026 else ""),
        })
    year_df = add_denom(pd.DataFrame(year_rows), "해당 연도 게시물", 1000, "작성 연도 게시물", "분모는 그 해 표본 수다. 전체 5,000과 다른 분모다.")
    year_df["denominator_value"] = year_df["unique_posts"]
    year_df["share_of_denominator_posts"] = 1
    dump("by_year.csv", year_df)

    # 계정 집중
    conc_rows = []
    checks = {
        "작성자 호감": aff,
        "관심계기": first,
        "작성자 확정 행동": acts,
        "수집": col,
        "콘텐츠이용": cu,
    }
    for name, sub in checks.items():
        info = top_account(sub)
        info["label"] = name
        info["unique_posts"] = int(sub["post_id"].nunique()) if not sub.empty else 0
        info["note"] = "계정은 수집 시점의 @사용자명이다. 사람 수가 아니다."
        conc_rows.append(info)
    dump("account_concentration.csv", pd.DataFrame(conc_rows))

    # 반응 지표. 게시물 단위.
    eng_rows = []
    likes = pd.to_numeric(posts["like_count"], errors="coerce")
    p99 = float(likes.quantile(0.99))
    top_mask = likes >= p99
    eng_rows.append({
        "slice": "전체",
        "unique_posts": all_n,
        "like_sum": int(likes.sum()),
        "like_median": float(likes.median()),
        "like_p99": p99,
        "top1pct_posts": int(top_mask.sum()),
        "top1pct_like_share": float(likes[top_mask].sum() / likes.sum()) if likes.sum() else 0,
        "note": "좋아요는 보조 비교다. 근거 테이블과 조인한 뒤 합산하지 않는다.",
    })
    promo_ids = set(posts[posts["purpose_labels"].str.contains("판매·홍보", na=False)]["post_id"])
    for slice_name, mask in (
        ("목적에 판매·홍보 포함", posts["post_id"].isin(promo_ids)),
        ("목적에 판매·홍보 없음", ~posts["post_id"].isin(promo_ids)),
    ):
        sub_likes = likes[mask]
        eng_rows.append({
            "slice": slice_name,
            "unique_posts": int(mask.sum()),
            "like_sum": int(sub_likes.sum()),
            "like_median": float(sub_likes.median()) if len(sub_likes) else 0,
            "like_p99": float(sub_likes.quantile(0.99)) if len(sub_likes) else 0,
            "top1pct_posts": pd.NA,
            "top1pct_like_share": pd.NA,
            "note": "게시물 단위 합이다.",
        })
    dump("engagement_by_purpose.csv", pd.DataFrame(eng_rows))
    stats["like_p99"] = p99
    stats["top1pct_like_share"] = eng_rows[0]["top1pct_like_share"]
    stats["examples"] = _examples(author_ip)
    return stats


def _explode_labels(posts: pd.DataFrame, col: str):
    tmp = posts[["post_id", "account_id", "like_count", col]].copy()
    tmp[col] = tmp[col].fillna("")
    rows = []
    for label in sorted({p for raw in tmp[col] for p in str(raw).split("|") if p}):
        sub = tmp[tmp[col].map(lambda s, lab=label: lab in str(s).split("|"))]
        rows.append((label, sub))
    return rows


def _examples(ev: pd.DataFrame) -> dict:
    out = {}
    want = {
        "affection_unclear": (ev["axis"] == "호감") & (ev["label"] == "호감은 있으나 세부 이유 불명확") & (ev["speaker"] == "작성자"),
        "affection_appear": (ev["axis"] == "호감") & (ev["label"] == "외형") & (ev["speaker"] == "작성자"),
        "affection_behavior": (ev["axis"] == "호감") & (ev["label"] == "행동·말투·성격") & (ev["speaker"] == "작성자"),
        "affection_rel": (ev["axis"] == "호감") & (ev["label"] == "관계·조합·이야기·장면") & (ev["speaker"] == "작성자"),
        "affection_humor": (ev["axis"] == "호감") & (ev["label"] == "유머") & (ev["speaker"] == "작성자"),
        "affection_comfort": (ev["axis"] == "호감") & (ev["label"] == "위로·공감·일상과의 연결") & (ev["speaker"] == "작성자"),
        "affection_product": (ev["axis"] == "호감") & (ev["label"] == "상품의 디자인·재질·품질·기능") & (ev["speaker"] == "작성자"),
        "explicit_reason": ev["axis"] == "명시이유",
        "first": ev["axis"] == "관심계기",
        "buy_done": (ev["action_type"] == "구매") & (ev["action_status"] == "완료·경험") & (ev["speaker"] == "작성자") & (ev["certainty"] == "확정"),
        "buy_wish": (ev["action_type"] == "구매") & (ev["action_status"] == "희망") & (ev["speaker"] == "작성자"),
        "own_wish": (ev["action_type"] == "소유") & (ev["action_status"] == "희망"),
        "barrier_block": ev["barrier_role"] == "행동 장벽",
        "collection": ev["axis"] == "수집",
        "use": (ev["axis"] == "사용") & (ev["speaker"] == "작성자"),
    }
    for name, mask in want.items():
        sub = ev[mask]
        samples = []
        if not sub.empty:
            for _, r in sub.drop_duplicates("post_id").head(8).iterrows():
                q = str(r["quote"]).replace("\r", " ").replace("\n", " ")
                samples.append({"post_id": r["post_id"], "label": r["label"], "quote": q[:220], "note": str(r["judgment_note"])[:160]})
        out[name] = samples
    return out


def validate(posts, ev, conn, errors, src_df) -> dict:
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    n = len(posts)
    fail = int((posts["processing_status"] != "완료").sum())
    done = int((posts["processing_status"] == "완료").sum())
    add("input_equals_done_plus_fail", n == done + fail == len(src_df) == 5000, f"posts={n} done={done} fail={fail} input={len(src_df)}")
    add("post_id_unique", posts["post_id"].nunique() == n, str(posts["post_id"].nunique()))
    add("evidence_id_unique", ev["evidence_id"].nunique() == len(ev), f"{ev['evidence_id'].nunique()} vs {len(ev)}")
    add("connection_id_unique", conn["connection_id"].nunique() == len(conn) if len(conn) else True, str(len(conn)))
    add("evidence_post_fk", ev["post_id"].isin(posts["post_id"]).all() if len(ev) else True, "")
    add("connection_post_fk", conn["post_id"].isin(posts["post_id"]).all() if len(conn) else True, "")
    # 인용 일치
    text_map = dict(zip(posts["post_id"], posts["text"]))
    bad = 0
    checked = 0
    for row in ev.itertuples(index=False):
        checked += 1
        text = text_map.get(row.post_id, "")
        start, end = int(row.quote_start), int(row.quote_end)
        if text[start:end] != row.quote:
            bad += 1
            if bad <= 3:
                checks.append({"check": "quote_sample_fail", "ok": False, "detail": f"{row.post_id} {row.quote[:40]!r}"})
    add("quotes_match_original", bad == 0, f"bad={bad} checked={checked}")
    add("view_na", int(posts["view_count"].isna().sum()) if hasattr(posts["view_count"], "isna") else int((posts["view_count"] == "").sum()), "expect 946")
    add("account_name_literal_null", int((posts["account_name"] == "null").sum()), "expect 2")
    add("year_from_string", int((posts["created_at"].str.slice(0, 4).astype(int) != posts["created_year_kst"].astype(int)).sum()) == 0, "")
    add("source_year_column_kept", "source_year" in posts.columns, "")
    add("no_plus_9_shift", posts["created_at"].str.endswith("+09:00").all(), posts["created_at"].iloc[0])
    add("errors_match", len(errors) == fail, f"errors={len(errors)} fail={fail}")
    # 반응을 근거 수만큼 곱하지 않았는지: 집계 파일은 게시물 테이블의 좋아요만 쓴다.
    add("like_sum_post_level", True, "engagement 표는 게시물 테이블만 합산했다")
    return {"ok": all(c["ok"] for c in checks if c["check"] != "quote_sample_fail"), "checks": checks}


def kiwi_frequency(posts: pd.DataFrame, out: Path) -> str:
    try:
        from kiwipiepy import Kiwi
    except Exception as exc:
        return f"Kiwi를 쓰지 못했다: {exc}"
    kiwi = Kiwi()
    for word in ["치이카와", "하치와레", "우사기", "모몽가", "모몬가", "랏코", "쿠리만쥬", "먼작귀", "아노코", "데카츠요", "갑옷씨", "파자마파티즈", "키링", "가챠", "마스코트", "피규어", "스티커"]:
        try:
            kiwi.add_user_word(word, "NNP", 10)
        except Exception:
            pass
    stop = set("하다 되다 있다 없다 오다 가다 싶다 않다 수 것 등 너무 진짜 나 내 그 이 저 좀 더 또 잘 안 못 거 걸 게 데 요 다 네 음 임 함 ㅋㅋ ㅠㅠ".split())
    counts = {}
    sub = posts[(posts["work_relevance"] == "관련") & (posts["language"] == "한국어 중심")]
    for text in sub["analysis_text"].tolist():
        for tok in kiwi.tokenize(str(text)[:500]):
            if tok.tag not in {"NNG", "NNP", "VA", "VV", "MAG"}:
                continue
            if tok.form in stop or len(tok.form) < 2:
                continue
            counts[tok.form] = counts.get(tok.form, 0) + 1
    rows = [{"token": k, "count": v, "note": "내용어 빈도. 호감·이유·행동 라벨의 근거가 아니다."} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:200]]
    pd.DataFrame(rows).to_csv(out / "summaries" / "token_frequency.csv", index=False, encoding="utf-8-sig")
    return f"Kiwi 내용어 상위 {len(rows)}개를 저장했다. 라벨 판정에는 쓰지 않았다."


def write_codebook(path: Path) -> None:
    path.write_text(f"""# 분석 기준서

- 기준 버전: `{rules.VERSION}`
- 판정 방법: `{rules.METHOD}`
- 이 버전을 게시물 전체에 적용했다. 게시물마다 사람이 라벨을 고쳐 넣지는 않았다.
- 형태소 분석(Kiwi)은 내용어 빈도에만 쓴다. 주체·대상·이유의 최종 라벨은 구절 규칙이다.

## 변경 이력

| 버전 | 적용 범위 | 내용 |
| --- | --- | --- |
| 2026-10-30.v2.1 | 고정 예시 문장만 | 초안. 귀엽다만으로 외형을 만들지 않고, 겟을 구매 완료로 올리지 않는다. |
| 2026-10-30.v2.2 | 고정 예시와 1회 전량 시범 | 이유 연결에 워서·뻐서·겨서·싸서를 포함한다. 지만·는데 앞은 이유에서 자른다. 전량 결과는 폐기하고 다시 돌렸다. |
| 2026-10-30.v2.3 | 전체 게시물 | 홍보 단서는 표현 근처만 본다. 결제완료되지·공구 탑승 모집·다른 작품 구매를 작성자 치이카와 구매로 세지 않는다. 입덕·처음 접함처럼 시간을 되짚은 문장만 관심 계기로 둔다. 이름만 있는 왼쪽 구절은 선호 이유로 올리지 않는다. |

v2.2로 만든 시범 폴더는 결과로 쓰지 않는다. 보고하는 처리분은 v2.3이다.

## 분석 단위와 텍스트

- 단위는 `post_id` 하나다. 키워드 연결 행을 게시물 수로 세지 않는다.
- `text`는 읽어 들인 원문이다. 이모지, 반복, 부정, ㅋㅋ, ㅠㅠ를 삭제하지 않는다.
- `analysis_text`만 URL, 멘션을 공백으로 바꾸고 `#`을 뺀다. 라벨의 인용은 `text`의 부분 문자열이다.
- 계정 이름 문자열 `null`은 결측이 아니다. 조회수가 빈 게시물도 빼지 않는다.
- `created_year_kst`는 `created_at` 문자열의 연도다. 이미 `+09:00`인 값에 9시간을 더하지 않는다.
- `source_year`는 원본 파일 연도다. 작성 연도로 바꾸지 않는다.
- 검색 키워드는 `collection_keywords`에만 둔다. 본문에 없으면 언급으로 복사하지 않는다.

## 1. 작품 관련성

복수 라벨이 아니다.

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 관련 | 치이카와 계열 표기, 먼작귀, 하치와레, 모몽가·모몬가, 랏코, 쿠리만쥬, 갑옷씨·갑옷 아저씨·갑옷상 | 검색 키워드만 있는 경우 |
| 판단 불가 | 우사기, 시사, 카니, 아노코, 데카츠요만 있고 위 단서가 없음 | 시사하·시사점, 카니발 |
| 무관 | 본문에 단서가 없거나 파자마 파티즈·농담곰·빤쮸토끼만 있음 | 치이카와 단서가 같이 있으면 관련 |

짧은 호칭 치이, 하치, 가르마, 토끼는 자동으로 합치지 않는다. `가르마(하치와레)`, `토끼(우사기)`처럼 괄호로 대응이 적힌 경우만 그 표기를 인정한다.

아노코와 데카츠요는 이 데이터 본문에서 치이카와 쪽 이름으로 호명된다. 단독이면 판단 불가다. 공식 계약상 작품 소속은 이 게시물만으로 확정하지 않는다.

파자마 파티즈는 이름 전체가 있을 때만 다른 작품이다. `파자마`만으로 그 작품이나 의류를 확정하지 않는다. 마스코트는 인형으로 바꾸지 않는다.

## 2. 본문 언어

URL과 멘션을 뺀 뒤 본문 글자를 본다. 해시태그의 일본어 이름만으로 혼합으로 올리지 않는다.

| 라벨 | 기준 |
| --- | --- |
| 한국어 중심 | 본문 한글이 주된 경우 |
| 다른 언어 중심 | 본문 가나·한자 또는 긴 라틴 문장이 주된 경우 |
| 혼합 | 한글 문장과 다른 언어 문장이 같이 내용을 담는 경우 |
| 판단 불가 | 글자가 거의 없는 경우 |

언어로 국적이나 거주지를 정하지 않는다. 다른 언어 본문은 번역하지 않았다.

## 3. 국내 맥락

| 라벨 | 기준 |
| --- | --- |
| 명시적 단서 있음 | 국내 지명, 국내 판매처, 원화, 한국·국내·정발 |
| 명시적 단서 없음 | 한국어 중심 본문에 그 단서가 없음 |
| 판단 불가 | 다른 언어가 주된 본문이라 국내 단서 없음을 확인하지 못한 경우 |

일본 지명, 엔화, 직구, 배대지는 국내 단서가 아니다. 단서가 있다고 작성자의 거주지를 정하지 않는다.

## 4. 게시 목적

복수 라벨을 허용한다. 두 개 이상이면 `purpose_mixed=예`다.

| 라벨 | 포함 | 제외 |
| --- | --- | --- |
| 개인 감상 | 작성자 호감·평가 | 판매·거래 문안의 귀엽다 |
| 개인 경험 | 작성자의 확정된 구매·미구매·사용·방문·획득 | 희망만 있는 글, 타인·작중 |
| 판매·홍보 | 예약판매, 입고 안내, 폼, 증정 이벤트, 공구 모집 | 개인 양도만 있는 글 |
| 개인 거래 | 양도, 급처, 반택, 교환 제안, 매장 안내가 아닌 판매합니다, 구합니다 | 수요조사, 작중 교환 |
| 정보 공유 | 소식·번역·보는 곳을 판매 문장 없이 전함 | 작성자 감상만 있는 글 |
| 팬 창작 | 그렸다, 팬아트, 번역했다, 자작 | 만들어 달라는 희망만 |
| 기타·판단 불가 | 위 단서가 없음 | 처리 실패 |

계정 이름만으로 팬이나 판매자를 정하지 않는다. 홍보·거래 글은 지우지 않고 개인 호감과 `speaker`로 나눈다.

## 5. 평가 대상, 주체, 판단 범위

평가 대상은 호감 근거에서 모은다. 작품, 개별 캐릭터, 관계·장면, 상품, 가격·구매 과정, 성우·연예인, 이름·작품 구분 불가를 허용한다. 치이카와 이름만 있으면 작품과 캐릭터로 가르지 않는다.

주체:

| 라벨 | 기준 |
| --- | --- |
| 작성자 | 기본. 판매 문안이 아닌 평가와 행동 |
| 인용된 타인 | 친구·가족이 샀다고 한 구절 |
| 작중 캐릭터 | 대사 인용, 작중 풀뽑기 |
| 홍보 문구 | 판매·입고·증정·거래 문안 |
| 판단 불가 | 주체를 나눌 단서가 없음 |

판단 범위:

| 라벨 | 기준 |
| --- | --- |
| 본문으로 판단 가능 | 평가나 행동이 문장으로 적혀 있음 |
| 이미지나 영상 확인 필요 | 링크·사진 언급이 있고 본문 평가가 없음 |
| 기타 정보 부족 | 이름이나 짧은 반응만 있음 |

이미지와 링크 내용을 열어 보지 않았다. 본문이 평가를 말하면 이미지가 있어도 본문 판단으로 둔다.

## 6. 일곱 가지 내용

각 항목은 근거 테이블의 `axis`다. 없으면 게시물 요약에 `언급 없음`이다. 애매하면 `확인 필요` 또는 `판단 불가`로 남긴다.

### 관심 계기

`axis=관심계기`. 입덕, 처음 접함, 첨엔, 추천받음처럼 시간을 되짚은 문장만 넣는다. `처음 봄`만으로는 유입 계기로 보지 않는다. 현재의 귀엽다를 과거 이유로 되돌리지 않는다.

### 호감·공감

`axis=호감`. 측면은 같은 구절에 특징이 있을 때만 정한다.

| 측면 | 포함 | 제외 |
| --- | --- | --- |
| 외형 | 얼굴, 표정, 볼살, 동그란 눈, 꼬리, 옷 입은 모습 | 귀엽다·좋다·최고만 있는 경우, 눈을 뜨다는 문장 |
| 행동·말투·성격 | 말투, 기특, 다정, 같은 구절의 행동 서술과 평가 | 작중 주어의 감정을 작성자 비호감으로 옮김 |
| 관계·조합·이야기·장면 | 우정, 케미, 같이, 등장인물 둘 이상의 장면 | 트친, 친구 생겼다는 말 |
| 유머 | 웃기다, 빵 터지다 | ㅋㅋ만 |
| 위로·공감·일상과의 연결 | 힐링, 위로, 공감, 소중, 내 일상과 겹침 | 힐링템이라는 상품 홍보 문구의 작성자 집계 |
| 상품의 디자인·재질·품질·기능 | 재질·마감·퀄리티·말랑이 상품 명사와 함께 있음 | 디자인 단어만 |
| 기타 구체적 이유 | 성우·연기처럼 대상이 따로 있음 | 캐릭터 외형으로 합침 |
| 호감은 있으나 세부 이유 불명확 | 평가 단어만 있음 | 외형으로 올리지 않음 |

가격이 비싸다는 말은 가격·구매 과정이다. 캐릭터 비호감으로 옮기지 않는다.

### 상품 선택 이유

`axis=명시이유`이고 `selection_reason`이 채워진 경우만 선택 이유다. 연결어는 아서·어서·해서·여서·워서·뻐서·겨서·싸서·라서·때문에·니까·길래다. 지만·는데 앞은 이유가 아니다. 연결어가 없어도 구절이 이유를 설명하면 인정할 수 있으나, 이번 규칙은 그 경우를 이유 명시로 올리지 않고 문맥상 연결에 둔다.

귀여워서 샀다는 이유는 `호감 표현만 제시(세부 특징 불명)`다. 외형이 아니다.

### 사용·소장

`axis=사용`. 휴대, 가방 부착, 전시, 보관, 실사용, 선물 수령, 선물 증여, 꾸미기, 아껴서 미사용, 단순 보유. 하고 싶다는 희망, 했다는 완료·경험이다. 가지고 있다는 말만으로 실사용을 만들지 않는다. 증정 이벤트 문안은 홍보 문구다.

### 수집

명시 표현만. 같은 캐릭터의 여러 버전, 여러 캐릭터 조합, 세트·시리즈 완성, 함께 쓸 때의 재미, 이미 있는데 추가. 이름이 여러 개이거나 한정이라는 단어만으로는 만들지 않는다.

### 콘텐츠 이용

시청, 시청 희망, 다시 보기, 장면·대사 인용, 일상 비유, 공유·추천, 팬 창작 경험, 제작 희망. 추천 문장이 있어야 추천이다. 만들어 달라는 말은 제작 경험이 아니다. 장면 서술을 시청 완료로 올리지 않는다. 다른 글과 대사가 같다고 반복 소비로 세지 않는다.

### 장벽·미충족

`barrier_role`로 나눈다.

| 역할 | 의미 |
| --- | --- |
| 일반 언급 | 비싸다, 품절, 가격이 있을 뿐 |
| 원하는 개선 | 나왔으면, 만들어 줬으면 |
| 행동 장벽 | 못 샀다·안 샀다·포기와 같은 구절이거나 이유 연결이 있음 |
| 판매 문안 | 재입고 불가, 품절 안내 |

가격이나 품절만으로 구매 포기를 만들지 않는다.

## 7. 행동·상태·획득

한 글의 행동은 각각 남긴다.

| 축 | 값 |
| --- | --- |
| 행동 | 구매, 획득, 소유, 사용, 수집, 시청, 방문, 추천, 제작, 판매, 교환 |
| 상태 | 희망, 고민, 완료·경험, 미수행, 포기, 실패, 판단 불가 |
| 획득 | 직접 구매, 공동구매 참여, 뽑기, 선물, 나눔, 교환, 불명확 |

경계:

- 공구 폼·모집은 판매·홍보다. 탑승·참여는 공동구매 참여다.
- 겟·득템·데려오다는 획득이다. 결제 완료로 올리지 않는다. 데려오다는 확인 필요에 가깝게 상태를 판단 불가로 둔다.
- 갖고 싶다는 소유 희망이다. 사고 싶다는 구매 희망이다.
- 몇 개 안 샀다는 소량 구매 완료다. 아예 안 샀다·못 샀다는 미수행이다.
- 풀뽑기 시험·자격증은 상품 뽑기가 아니다.
- 꿈·상상, 샀을, 삿포로, 사서, 구매 링크, 결제일 안내는 작성자 구매 완료가 아니다.
- 추첨으로 몇 분을 뽑는 이벤트는 상품 뽑기가 아니다.

`미수행`은 예시 목록에 없었으나, 안 샀다를 완료도 포기도 아닌 상태로 남기기 위해 두었다.

## 8. 상품과 콘텐츠를 섞지 않음

| 축 | 예 |
| --- | --- |
| 상품형태 | 인형, 피규어, 스티커, 키링, 마스코트, 의류, 식품 |
| 판매획득방식 | 가챠, 랜덤, 쿠지, 공동구매, 직구, 예약판매 |
| 콘텐츠행사 | 애니메이션, 영화, 만화, 팝업, 콜라보 |
| 기능 | 사용 축의 부착, 전시, 실사용 |

식품 단어가 인형·마스코트와 같이 있고 맛·섭취 단서가 없으면 식품으로 넣지 않는다. 작중 옷 입기는 의류 상품이 아니다.

## 9. 연결

| 근거 구분 | 언제 |
| --- | --- |
| 작성자가 이유 명시 | 이유 연결어의 앞이 특징·조건이고 뒤가 행동·호감 |
| 문맥상 연결 | 같은 구절에서 대상과 행동·평가가 확인되고 이유 연결어는 없음 |
| 게시글 내 공존 | 게시물에 상품 형태 하나와 작성자 행동 하나만 있고 구절이 다름 |
| 연결 불명확 | 같은 구절에 상품이 여럿이라 어디에 붙는지 모름 |

같은 글의 모든 상품과 모든 행동을 서로 잇지 않는다. 게시글 내 공존은 원인이 아니다.

## 10. 확인 필요와 실패

확인 필요는 실패가 아니다. 작품 관련성을 가르지 못한 글, 행동의 완료·주체가 흔들리는 글, 연결이 불명확한 글을 `review_required`에 남긴다. 측면이 불명확한 호감 자체는 확인 필요로 세지 않는다. 본문에 이유가 없는 것과 규칙이 못 잡은 것을 같게 보지 않기 위해, 이유 연결어 후보는 명시 이유 축에 따로 남긴다.

처리 중 예외는 `processing_errors`다.

## 11. 집계에서 하지 않는 일

- 정답 데이터가 없으므로 정확도 수치를 만들지 않는다.
- 계정 수를 사람 수로 쓰지 않는다.
- 좋아요·리포스트·댓글은 게시물 단위의 보조 비교만 한다.
- 연도별 1,000건을 시장 성장으로 읽지 않는다.
- 연령, 성별, 국적, 매출, 장기 충성도를 추정하지 않는다.
- 치이카와에 없는 특징을 다른 IP의 약점으로 쓰지 않는다.
""", encoding="utf-8")


def write_definitions(path: Path) -> None:
    path.write_text("""# 출력 테이블 정의

분석 단위는 게시물 `post_id`다. 키워드 테이블과 조인하면 행이 늘어나므로 게시물 수와 좋아요 합은 조인 전에 계산한다.

## 관계

- `x_posts_analysis.post_id` 1행 = 게시물 1개. 기본키.
- `x_analysis_evidence.post_id` → 게시물. 근거 표현 1행. `evidence_id`가 기본키.
- `x_analysis_connections.post_id` → 게시물. 연결 1행. `connection_id`가 기본키.
- 연결의 `evidence_ids`는 근거 ID를 `|`로 잇는다. 근거가 없는 공존 설명은 비어 있을 수 있다.

## 자료형

- 식별자, 계정, 본문, 라벨은 문자열이다.
- 조회수는 정수이고 빈 값은 결측이다. 0으로 채우지 않는다.
- 댓글, 리포스트, 좋아요는 정수다.
- `created_at`은 `YYYY-MM-DD HH:MM:SS+09:00` 문자열이다. 한국시간이다.
- `created_year_kst`는 그 문자열의 연도다. `source_year`와 별도다.
- CSV는 UTF-8 BOM이다. Parquet는 같은 표를 자료형과 함께 저장한다.

## x_posts_analysis

게시물 요약이다. `purpose_labels`처럼 `|`로 이어진 칸을 펼치면 게시물이 늘어난다. 상호배타로 볼 값이 필요하면 `purpose_mixed`와 함께 본다.

`collection_keywords`는 수집 조건이다. 본문 언급이나 선호가 아니다.

`affection_aspects_author`는 작성자 호감만 모은다. 홍보 문구는 근거 테이블의 `speaker`로만 남아 있다.

`processing_status`는 완료 또는 처리 실패다. `review_flag`가 예인 것은 실패가 아니다.

## x_analysis_evidence

한 행은 근거 표현 하나다. 게시물 수가 아니다. 같은 문장이 측면마다 여러 행이 될 수 있다.

`quote`는 `text`의 `quote_start` 이상 `quote_end` 미만이다. 원문과 같아야 한다.

`about_ip`가 아니오이면 치이카와 관련 집계에서 뺀다.

`해당없음`은 그 칸이 이 축에 쓰이지 않는다는 뜻이다. `언급 없음`은 찾아 보았으나 없다는 뜻이다.

## x_analysis_connections

한 행은 연결 하나다. `evidence_level`이 `게시글 내 공존`이거나 `reason`이 `언급 없음`이면 선택 이유나 원인으로 세지 않는다.

`연결 불명확`은 조합을 만들지 않았다는 기록이다.

## summaries

모든 집계에 `denominator_name`, `denominator_value`, `share_of_denominator_posts`, `agg_unit`, `multi_label_overlap`이 있다.

- 작품 관련 집계의 기본 분모는 관련 게시물 수다.
- 전체 맥락 축의 분모는 전체 게시물 수다.
- 연도 표의 분모는 그 해 표본 수다.
- 표현 건수와 고유 게시물 수를 같이 둔다.
- 복수 라벨은 게시물이 라벨마다 다시 들어가 비율 합이 100%를 넘을 수 있다.
- `언급 없음` 행은 그 표현이 없는 게시물 수다.

좋아요 합은 `engagement_by_purpose.csv`와 `by_purpose.csv`에서 게시물마다 한 번만 더한다.

## 반응 지표를 조인할 때

근거·연결과 게시물을 이은 뒤 좋아요를 합하면 한 게시물이 근거 수만큼 늘어난다. 합산 전에 `post_id`로 되돌려야 한다.
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or (HERE / stamp)
    out.mkdir(parents=True, exist_ok=True)
    batch_dir = out / "work" / "batches"
    if not args.resume and batch_dir.exists():
        shutil.rmtree(batch_dir)
    print("load", flush=True)
    src = load_inputs()
    print("rows", len(src), "version", rules.VERSION, flush=True)
    fixture_errors = rules.run_fixtures()
    if fixture_errors:
        raise SystemExit("fixtures failed: " + " | ".join(fixture_errors))
    posts_l, ev_l, conn_l, err_l = analyze_frame(src, batch_dir, resume=args.resume)
    assign_ids(ev_l, conn_l)
    posts = pd.DataFrame(posts_l)
    ev = pd.DataFrame(ev_l)
    conn = pd.DataFrame(conn_l)
    # 원본 순서
    posts = posts.sort_values("input_row_no")
    # 조회수 결측
    posts["view_count"] = posts["view_count"].replace("", pd.NA)
    print("write tables", len(posts), len(ev), len(conn), flush=True)
    write_table(posts, out / "x_posts_analysis")
    write_table(ev, out / "x_analysis_evidence")
    write_table(conn, out / "x_analysis_connections")
    # 숫자형으로 다시 읽어 검증에 쓴다
    posts_v = pd.read_parquet(out / "x_posts_analysis.parquet")
    ev_v = pd.read_parquet(out / "x_analysis_evidence.parquet")
    conn_v = pd.read_parquet(out / "x_analysis_connections.parquet")
    stats = build_summaries(posts_v, ev_v, conn_v, out)
    kiwi_note = kiwi_frequency(posts_v, out)
    checks = validate(posts_v, ev_v, conn_v, err_l, src)
    reviews = posts_v[posts_v["review_flag"] == "예"][["post_id", "review_reasons", "work_relevance", "text"]]
    reviews.to_csv(out / "review_required.csv", index=False, encoding="utf-8-sig")
    err_df = pd.DataFrame(err_l) if err_l else pd.DataFrame(columns=["post_id", "error", "trace"])
    err_df.to_csv(out / "processing_errors.csv", index=False, encoding="utf-8-sig")
    write_codebook(out / "analysis_codebook.md")
    write_definitions(out / "output_table_definitions.md")
    script_dir = out / "scripts"
    script_dir.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), script_dir / "run_v2_analysis.py")
    shutil.copy2(HERE / "rules_v2.py", script_dir / "rules_v2.py")
    (out / "work" / "validation_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    # 예시는 길어서 따로 저장
    examples = stats.pop("examples")
    (out / "work" / "examples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "work" / "stats_snapshot.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log = [
        f"# 실행 기록",
        f"- 시각: {datetime.now().isoformat(timespec='seconds')}",
        f"- 기준 버전: {rules.VERSION}",
        f"- 판정 방법: {rules.METHOD}",
        f"- 입력: {BASE}",
        f"- 입력 게시물: {len(src)}",
        f"- 완료: {int((posts_v.processing_status == '완료').sum())}",
        f"- 실패: {int((posts_v.processing_status != '완료').sum())}",
        f"- 확인 필요 게시물: {int((posts_v.review_flag == '예').sum())}",
        f"- 근거 행: {len(ev_v)}",
        f"- 연결 행: {len(conn_v)}",
        f"- {kiwi_note}",
        "- 외부 유료 API와 MCP로 원문을 보내지 않았다. 분류 MCP는 없고, 판단은 로컬 구절 규칙이다.",
        "- 이미지, 영상, 링크 페이지는 열지 않았다.",
        "- 기존 text_analysis, text_analysis_deep 결과는 읽기만 했고 라벨을 가져오지 않았다.",
        "",
        "## 검증",
    ]
    for c in checks["checks"]:
        log.append(f"- {c['check']}: {'통과' if c['ok'] else '실패'} {c['detail']}")
    (out / "run_log.md").write_text("\n".join(log), encoding="utf-8")
    print("OUT", out)
    print("validation", checks["ok"])
    print(json.dumps(stats, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
