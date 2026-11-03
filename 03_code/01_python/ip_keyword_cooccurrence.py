from __future__ import annotations

import argparse
import html
import json
import math
import platform
import re
import sys
import unicodedata
import warnings
from collections import Counter
from pathlib import Path
import pandas as pd


# 실제 CSV 구조: post_id, description, media_type_id, post_url, created_at,
# like_count, comment_count. 이 분석에는 post_id와 description을 사용합니다.
ID_COLUMN = "post_id"
TEXT_COLUMN = "description"

# 상위 IP 단위로 묶는 기본 별칭 사전입니다. 프로젝트 기준에 맞게 수정하거나
# --ip-aliases JSON 파일로 교체할 수 있습니다.
DEFAULT_IP_ALIASES: dict[str, list[str]] = {
    "치이카와": [
        "치이카와", "먼작귀", "ちいかわ", "chiikawa", "吉伊卡哇",
        "하치와레", "ハチワレ", "hachiware",
        "우사기", "모몽가", "モモンガ", "momonga",
        "쿠리만쥬", "くりまんじゅう", "kurimanju",
        "랏코", "ラッコ",
    ],
    "산리오": [
        "산리오", "sanrio", "쿠로미", "kuromi", "시나모롤", "시나몬롤",
        "cinnamoroll", "마이멜로디", "my melody", "mymelody",
        "헬로키티", "hello kitty", "hellokitty", "폼폼푸린", "pompompurin",
        "포차코", "pochacco", "케로케로케로피", "keroppi",
    ],
    "라부부": ["라부부", "labubu"],
    "망그러진 곰": ["망그러진 곰", "망그러진곰", "망곰"],
    "춘식이": ["춘식이", "choonsik"],
    "농담곰": ["농담곰", "나가노의 곰", "나가노곰", "nagano bear", "ナガノのくま"],
}

DEFAULT_STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "그래서", "정말", "너무", "진짜",
    "오늘", "이번", "요즘", "지금", "여기", "저기", "우리", "제가", "저는",
    "있는", "없는", "하는", "되는", "같은", "위한", "통한", "대한", "관련",
    "있다", "없다", "하다", "되다", "같다", "주다", "보다",
    "합니다", "했습니다", "입니다", "있습니다", "있어요", "없어요", "해주세요",
    "드립니다", "보세요", "주세요", "문의", "확인", "가능", "포함", "모든",
    "함께", "바로", "가장", "많은", "하루", "링크", "프로필", "팔로우", "디엠",
    "the", "and", "for", "with", "this", "that", "from", "your", "you", "are",
    "was", "were", "have", "has", "will", "instagram", "repost", "http", "https",
}

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9._]+")
SPACE_RE = re.compile(r"\s+")
REGEX_TOKEN_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}|[一-龥]{2,}|[ぁ-んァ-ヶ]{2,}")
NON_TEXT_RE = re.compile(r"[^0-9A-Za-z가-힣一-龥ぁ-んァ-ヶ\s#]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="캐릭터 IP별 description 키워드 빈도·동시출현율·lift 분석"
    )
    parser.add_argument("csv_path", type=Path, help="원본 CSV 경로")
    parser.add_argument("--output-dir", type=Path, default=Path("ip_keyword_output"))
    parser.add_argument("--encoding", default="auto", help="auto, utf-8-sig, cp949 등")
    parser.add_argument(
        "--tokenizer", choices=("kiwi", "regex"), default="kiwi",
        help="kiwi 권장. regex는 설치 없이 파이프라인 점검용",
    )
    parser.add_argument("--ip-aliases", type=Path, help="{표준 IP: [별칭...]} JSON")
    parser.add_argument("--stopwords", type=Path, help="한 줄에 하나인 추가 불용어 파일")
    parser.add_argument("--min-keyword-df", type=int, default=10)
    parser.add_argument("--min-co-count", type=int, default=3)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument(
        "--dedupe-text", action=argparse.BooleanOptionalAction, default=True,
        help="공백·대소문자·URL을 정규화한 동일 description 중복 제거(기본: 켬)",
    )
    parser.add_argument("--no-plots", action="store_true", help="PNG 시각화 생략")
    parser.add_argument("--save-post-map", action="store_true", help="게시글별 IP·키워드 CSV 저장")
    return parser.parse_args()


def read_csv_auto(path: Path, requested: str) -> tuple[pd.DataFrame, str]:
    encodings = [requested] if requested != "auto" else ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    errors: list[str] = []
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False), encoding
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeError("CSV 인코딩을 판별하지 못했습니다. " + " | ".join(errors))


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", html.unescape(str(value))).lower()
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = text.replace("#", " ")  # 해시태그 단어는 남기고 #만 제거
    text = NON_TEXT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def load_ip_aliases(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        source = DEFAULT_IP_ALIASES
    else:
        source = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(source, dict):
            raise ValueError("IP 별칭 JSON의 최상위 값은 객체여야 합니다.")

    result: dict[str, list[str]] = {}
    for canonical, aliases in source.items():
        if not isinstance(canonical, str) or not isinstance(aliases, list):
            raise ValueError("IP 별칭 JSON은 {문자열: [문자열...]} 형식이어야 합니다.")
        values = [clean_text(canonical), *(clean_text(x) for x in aliases)]
        result[canonical.strip()] = sorted({x for x in values if x}, key=len, reverse=True)
    return result


def load_stopwords(path: Path | None) -> set[str]:
    words = {clean_text(x) for x in DEFAULT_STOPWORDS}
    if path:
        words.update(clean_text(x) for x in path.read_text(encoding="utf-8-sig").splitlines())
    return {x for x in words if x}


def compile_alias_patterns(ip_aliases: dict[str, list[str]]) -> dict[str, re.Pattern[str]]:
    patterns: dict[str, re.Pattern[str]] = {}
    for canonical, aliases in ip_aliases.items():
        pieces = []
        for alias in aliases:
            # 별칭 내부 공백은 원문에서 0개 이상의 공백으로 대응합니다.
            pieces.append(re.escape(alias).replace(r"\ ", r"\s*"))
        patterns[canonical] = re.compile("(?:" + "|".join(pieces) + ")", re.I)
    return patterns


def find_ips(text: str, patterns: dict[str, re.Pattern[str]]) -> list[str]:
    return [canonical for canonical, pattern in patterns.items() if pattern.search(text)]


class Tokenizer:
    def __init__(
        self,
        method: str,
        stopwords: set[str],
        ip_aliases: dict[str, list[str]],
    ) -> None:
        self.method = method
        self.stopwords = stopwords
        self.alias_fragments = sorted(
            {
                token
                for aliases in ip_aliases.values()
                for alias in aliases
                for token in REGEX_TOKEN_RE.findall(alias)
                if len(token) >= 2
            },
            key=len,
            reverse=True,
        )
        self.kiwi = None
        if method == "kiwi":
            try:
                from kiwipiepy import Kiwi
            except ImportError as exc:
                raise RuntimeError(
                    "kiwipiepy가 필요합니다. `python -m pip install kiwipiepy` 후 다시 실행하거나 "
                    "점검용으로 `--tokenizer regex`를 사용하세요."
                ) from exc
            self.kiwi = Kiwi()
            # 별칭이 조사와 잘못 결합되어 일부만 일반 키워드로 새는 현상을 줄입니다.
            for aliases in ip_aliases.values():
                for alias in aliases:
                    if " " not in alias and len(alias) >= 2:
                        self.kiwi.add_user_word(alias, tag="NNP")

    def _remove_ip_fragment(self, token: str) -> str:
        result = token.lower()
        for alias in self.alias_fragments:
            if alias in result:
                result = result.replace(alias, "")
        return result.strip()

    def _keep(self, token: str) -> str | None:
        token = self._remove_ip_fragment(token)
        if len(token) < 2 or token in self.stopwords or token.isdigit():
            return None
        return token

    def tokenize(self, text: str) -> list[str]:
        if self.method == "regex":
            return [kept for raw in REGEX_TOKEN_RE.findall(text) if (kept := self._keep(raw))]

        assert self.kiwi is not None
        result: list[str] = []
        for token in self.kiwi.tokenize(text):
            # 일반/고유명사, 어근, 동사, 형용사, 외국어만 사용합니다.
            if token.tag.startswith(("NN", "XR")) or token.tag in {"SL", "SH"}:
                candidate = token.form.lower()
            elif token.tag.startswith(("VV", "VA")):
                candidate = token.form.lower() + "다"
            else:
                continue
            kept = self._keep(candidate)
            if kept:
                result.append(kept)
        return result


def prepare_posts(
    raw: pd.DataFrame,
    dedupe_text: bool,
) -> tuple[pd.DataFrame, dict[str, int]]:
    required = {ID_COLUMN, TEXT_COLUMN}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}. 실제 컬럼: {raw.columns.tolist()}")

    audit = {
        "raw_rows": int(len(raw)),
        "source_columns": "|".join(map(str, raw.columns)),
        "null_description": int(raw[TEXT_COLUMN].isna().sum()),
        "missing_or_blank_description": 0,
        "duplicate_post_id_removed": 0,
        "duplicate_description_removed": 0,
        "analysis_rows": 0,
    }
    posts = raw.copy()
    posts["clean_description"] = posts[TEXT_COLUMN].map(clean_text)
    blank = posts["clean_description"].eq("")
    audit["missing_or_blank_description"] = int(blank.sum())
    posts = posts.loc[~blank].copy()

    before = len(posts)
    posts = posts.drop_duplicates(subset=[ID_COLUMN], keep="first")
    audit["duplicate_post_id_removed"] = before - len(posts)

    if dedupe_text:
        before = len(posts)
        posts = posts.drop_duplicates(subset=["clean_description"], keep="first")
        audit["duplicate_description_removed"] = before - len(posts)

    audit["analysis_rows"] = int(len(posts))
    return posts.reset_index(drop=True), audit


def build_analysis(
    posts: pd.DataFrame,
    ip_patterns: dict[str, re.Pattern[str]],
    tokenizer: Tokenizer,
    min_keyword_df: int,
    min_co_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    posts["ips"] = posts["clean_description"].map(lambda x: find_ips(x, ip_patterns))
    posts["keywords"] = posts["clean_description"].map(lambda x: sorted(set(tokenizer.tokenize(x))))

    total_posts = len(posts)
    ip_df = Counter(ip for values in posts["ips"] for ip in set(values))
    keyword_df_all = Counter(keyword for values in posts["keywords"] for keyword in set(values))
    allowed_keywords = {k for k, count in keyword_df_all.items() if count >= min_keyword_df}

    co_count: Counter[tuple[str, str]] = Counter()
    for ips, keywords in zip(posts["ips"], posts["keywords"]):
        for ip in set(ips):
            for keyword in set(keywords) & allowed_keywords:
                co_count[(ip, keyword)] += 1

    ip_frequency = pd.DataFrame(
        [
            {
                "ip": ip,
                "post_count": count,
                "post_rate_pct": count / total_posts * 100 if total_posts else 0,
            }
            for ip, count in ip_df.items()
        ],
        columns=["ip", "post_count", "post_rate_pct"],
    ).sort_values(["post_count", "ip"], ascending=[False, True], ignore_index=True)

    keyword_frequency = pd.DataFrame(
        [
            {
                "keyword": keyword,
                "post_count": count,
                "post_rate_pct": count / total_posts * 100 if total_posts else 0,
            }
            for keyword, count in keyword_df_all.items()
            if keyword in allowed_keywords
        ],
        columns=["keyword", "post_count", "post_rate_pct"],
    ).sort_values(["post_count", "keyword"], ascending=[False, True], ignore_index=True)

    rows = []
    for (ip, keyword), count in co_count.items():
        if count < min_co_count:
            continue
        ip_total = ip_df[ip]
        keyword_total = keyword_df_all[keyword]
        expected = ip_total * keyword_total / total_posts if total_posts else math.nan
        rows.append(
            {
                "ip": ip,
                "keyword": keyword,
                "co_count": count,
                "ip_post_count": ip_total,
                "keyword_post_count": keyword_total,
                "total_posts": total_posts,
                "co_rate_pct": count / ip_total * 100,
                "keyword_rate_pct": keyword_total / total_posts * 100,
                "support_pct": count / total_posts * 100,
                "expected_count": expected,
                "lift": count / expected if expected else math.nan,
            }
        )
    cooccurrence = pd.DataFrame(
        rows,
        columns=[
            "ip", "keyword", "co_count", "ip_post_count", "keyword_post_count",
            "total_posts", "co_rate_pct", "keyword_rate_pct", "support_pct",
            "expected_count", "lift",
        ],
    )
    if not cooccurrence.empty:
        cooccurrence = cooccurrence.sort_values(
            ["ip", "co_count", "lift", "keyword"],
            ascending=[True, False, False, True],
            ignore_index=True,
        )
        cooccurrence["rank_by_co_count"] = (
            cooccurrence.groupby("ip")["co_count"].rank(method="first", ascending=False).astype(int)
        )
    return posts, ip_frequency, keyword_frequency, cooccurrence


def save_csvs(
    output_dir: Path,
    posts: pd.DataFrame,
    ip_frequency: pd.DataFrame,
    keyword_frequency: pd.DataFrame,
    cooccurrence: pd.DataFrame,
    audit: dict[str, object],
    save_post_map: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ip_frequency.to_csv(output_dir / "ip_frequency.csv", index=False, encoding="utf-8-sig")
    keyword_frequency.to_csv(output_dir / "keyword_frequency.csv", index=False, encoding="utf-8-sig")
    cooccurrence.to_csv(output_dir / "ip_keyword_cooccurrence.csv", index=False, encoding="utf-8-sig")

    if not cooccurrence.empty:
        for value, filename in [
            ("co_count", "matrix_co_count.csv"),
            ("co_rate_pct", "matrix_co_rate_pct.csv"),
            ("lift", "matrix_lift.csv"),
        ]:
            matrix = cooccurrence.pivot(index="ip", columns="keyword", values=value).fillna(0)
            matrix.to_csv(output_dir / filename, encoding="utf-8-sig")

    if save_post_map:
        post_map = posts[[ID_COLUMN, "ips", "keywords"]].copy()
        post_map["ips"] = post_map["ips"].map(lambda x: "|".join(x))
        post_map["keywords"] = post_map["keywords"].map(lambda x: "|".join(x))
        post_map.to_csv(output_dir / "post_ip_keywords.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([audit]).to_csv(output_dir / "analysis_audit.csv", index=False, encoding="utf-8-sig")


def configure_korean_font() -> None:
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    candidates = {
        "Windows": ["Malgun Gothic"],
        "Darwin": ["AppleGothic"],
        "Linux": ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"],
    }.get(platform.system(), ["DejaVu Sans"])
    installed = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((name for name in candidates if name in installed), "DejaVu Sans")
    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False
    if selected == "DejaVu Sans":
        warnings.warn("한글 글꼴을 찾지 못했습니다. 그래프의 한글이 깨지면 나눔고딕을 설치하세요.")


def top_keywords_for_plot(cooccurrence: pd.DataFrame, top_n: int) -> list[str]:
    if cooccurrence.empty:
        return []
    selected = (
        cooccurrence.sort_values(["ip", "co_count"], ascending=[True, False])
        .groupby("ip", group_keys=False)
        .head(top_n)
    )
    return selected.groupby("keyword")["co_count"].sum().nlargest(top_n).index.tolist()


def save_plots(output_dir: Path, cooccurrence: pd.DataFrame, top_n: int) -> None:
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
        import seaborn as sns
    except ImportError as exc:
        raise RuntimeError(
            "시각화에는 matplotlib, seaborn, networkx가 필요합니다. "
            "설치하거나 --no-plots를 사용하세요."
        ) from exc

    if cooccurrence.empty:
        warnings.warn("시각화할 동시출현 결과가 없습니다.")
        return

    configure_korean_font()
    sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"][0])
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    keywords = top_keywords_for_plot(cooccurrence, top_n)
    subset = cooccurrence[cooccurrence["keyword"].isin(keywords)]

    for value, title, filename, fmt, center in [
        ("co_rate_pct", "캐릭터 IP별 키워드 동시출현율 (%)", "heatmap_co_rate.png", ".1f", None),
        ("lift", "캐릭터 IP별 키워드 Lift", "heatmap_lift.png", ".2f", 1.0),
    ]:
        matrix = subset.pivot(index="ip", columns="keyword", values=value).fillna(0)
        width = max(11, min(24, 0.6 * len(matrix.columns) + 4))
        height = max(4, 0.65 * len(matrix.index) + 2)
        plt.figure(figsize=(width, height))
        sns.heatmap(matrix, annot=True, fmt=fmt, cmap="YlGnBu", center=center)
        plt.title(title)
        plt.xlabel("키워드")
        plt.ylabel("캐릭터 IP")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(plot_dir / filename, dpi=200, bbox_inches="tight")
        plt.close()

    # IP별 상위 키워드 막대그래프
    for ip, group in cooccurrence.groupby("ip"):
        top = group.nlargest(top_n, "co_count").sort_values("co_count")
        plt.figure(figsize=(9, max(4, 0.34 * len(top) + 1.5)))
        sns.barplot(data=top, x="co_count", y="keyword", color="#4C78A8")
        plt.title(f"{ip}: 동시출현 상위 키워드")
        plt.xlabel("동시출현 게시글 수")
        plt.ylabel("키워드")
        plt.tight_layout()
        safe_name = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", ip)
        plt.savefig(plot_dir / f"bar_{safe_name}.png", dpi=200, bbox_inches="tight")
        plt.close()

    # 해석 가능한 간결한 네트워크: IP별 co_count 상위 10개 중 lift >= 1만 표시
    edges = (
        cooccurrence[cooccurrence["lift"] >= 1]
        .sort_values(["ip", "co_count", "lift"], ascending=[True, False, False])
        .groupby("ip", group_keys=False)
        .head(min(10, top_n))
    )
    if not edges.empty:
        graph = nx.Graph()
        for row in edges.itertuples(index=False):
            graph.add_node(row.ip, kind="ip")
            graph.add_node(row.keyword, kind="keyword")
            graph.add_edge(row.ip, row.keyword, weight=row.co_count, lift=row.lift)
        pos = nx.spring_layout(graph, seed=42, k=1.2 / math.sqrt(max(len(graph), 1)))
        ip_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "ip"]
        keyword_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "keyword"]
        max_weight = max(data["weight"] for _, _, data in graph.edges(data=True))
        widths = [1 + 5 * data["weight"] / max_weight for _, _, data in graph.edges(data=True)]
        plt.figure(figsize=(16, 12))
        nx.draw_networkx_nodes(graph, pos, nodelist=ip_nodes, node_color="#F58518", node_size=1800)
        nx.draw_networkx_nodes(graph, pos, nodelist=keyword_nodes, node_color="#72B7B2", node_size=850)
        nx.draw_networkx_edges(graph, pos, width=widths, alpha=0.45, edge_color="#777777")
        nx.draw_networkx_labels(graph, pos, font_size=9)
        plt.title("캐릭터 IP-키워드 네트워크 (Lift ≥ 1)")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(plot_dir / "network_ip_keyword.png", dpi=220, bbox_inches="tight")
        plt.close()


def print_summary(
    output_dir: Path,
    audit: dict[str, object],
    ip_frequency: pd.DataFrame,
    cooccurrence: pd.DataFrame,
) -> None:
    print("\n[분석 완료]")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"결과 폴더: {output_dir.resolve()}")
    print("\n[IP별 게시글 수]")
    print(ip_frequency.to_string(index=False) if not ip_frequency.empty else "탐지된 IP 없음")
    if not cooccurrence.empty:
        print("\n[IP별 상위 5개 동시출현 키워드]")
        columns = ["ip", "keyword", "co_count", "co_rate_pct", "lift"]
        print(cooccurrence.groupby("ip", group_keys=False).head(5)[columns].to_string(index=False))


def main() -> None:
    args = parse_args()
    if args.min_keyword_df < 1 or args.min_co_count < 1 or args.top_n < 1:
        raise ValueError("min-keyword-df, min-co-count, top-n은 1 이상이어야 합니다.")

    raw, encoding = read_csv_auto(args.csv_path, args.encoding)
    posts, audit = prepare_posts(raw, args.dedupe_text)
    ip_aliases = load_ip_aliases(args.ip_aliases)
    ip_patterns = compile_alias_patterns(ip_aliases)
    tokenizer = Tokenizer(args.tokenizer, load_stopwords(args.stopwords), ip_aliases)
    posts, ip_frequency, keyword_frequency, cooccurrence = build_analysis(
        posts,
        ip_patterns,
        tokenizer,
        min_keyword_df=args.min_keyword_df,
        min_co_count=args.min_co_count,
    )

    audit.update(
        {
            "source_file": str(args.csv_path.resolve()),
            "encoding": encoding,
            "tokenizer": args.tokenizer,
            "dedupe_text": args.dedupe_text,
            "detected_ip_posts": int(posts["ips"].map(bool).sum()),
            "posts_without_detected_ip": int((~posts["ips"].map(bool)).sum()),
            "min_keyword_df": args.min_keyword_df,
            "min_co_count": args.min_co_count,
        }
    )
    save_csvs(
        args.output_dir,
        posts,
        ip_frequency,
        keyword_frequency,
        cooccurrence,
        audit,
        args.save_post_map,
    )
    if not args.no_plots:
        save_plots(args.output_dir, cooccurrence, args.top_n)
    print_summary(args.output_dir, audit, ip_frequency, cooccurrence)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise

