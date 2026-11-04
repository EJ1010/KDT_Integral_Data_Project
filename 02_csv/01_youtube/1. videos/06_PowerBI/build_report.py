# -*- coding: utf-8 -*-
"""검증된 CSV로 Power BI 프로젝트(PBIP)를 만든다. 데이터는 절대 경로로 읽는다."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

ROOT = Path(
    r"c:\Users\user\DATA_MKT_260920\03.data.project\KDT_Integral_Data_Project"
    r"\02_csv\01_youtube\1. videos\06_PowerBI"
)
DATA = ROOT / "data"
PBIP = ROOT / "치이카와_YouTube.pbip"
REPORT = ROOT / "치이카와_YouTube.Report"
MODEL = ROOT / "치이카와_YouTube.SemanticModel"

VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json"
PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"
PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
REPORT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.0.0/schema.json"

MAIN_AREAS = [
    "작품 전체·스토리·세계관",
    "캐릭터 관계·복수 캐릭터",
    "캐릭터 음성·더빙",
    "굿즈·상품",
]
AREAS = [
    "작품 전체·스토리·세계관",
    "캐릭터 관계·복수 캐릭터",
    "캐릭터 음성·더빙",
    "굿즈·상품",
    "성우·커버 가수",
    "제작자·편집",
]
NAVY = "'#3D5A80'"
INK = "'#1D2430'"
PAPER = "'#F4F1EB'"
WHITE = "'#FFFFFF'"
LINE = "'#E4DDD2'"


def uid() -> str:
    return str(uuid.uuid4())


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def col_field(entity: str, prop: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
        "active": True,
    }


def measure_field(entity: str, prop: str, label: str | None = None) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": label or prop,
        "active": True,
    }


def bucket(items: list[dict]) -> dict:
    return {"projections": items}


def container(title: str, subtitle: str | None = None) -> dict:
    title_props = {
        "show": lit("true"),
        "text": lit(f"'{title}'"),
        "fontSize": lit("12D"),
        "fontFamily": lit("'Malgun Gothic'"),
        "fontColor": {"solid": {"color": lit(INK)}},
    }
    out = {
        "title": [{"properties": title_props}],
        "background": [{
            "properties": {
                "show": lit("true"),
                "color": {"solid": {"color": lit(WHITE)}},
                "transparency": lit("0D"),
            }
        }],
        "border": [{
            "properties": {
                "show": lit("true"),
                "color": {"solid": {"color": lit(LINE)}},
                "radius": lit("4D"),
            }
        }],
        "padding": [{"properties": {"top": lit("4D"), "bottom": lit("4D"), "left": lit("6D"), "right": lit("6D")}}],
    }
    if subtitle:
        out["subTitle"] = [{
            "properties": {
                "show": lit("true"),
                "text": lit(f"'{subtitle}'"),
                "fontSize": lit("9D"),
                "fontFamily": lit("'Malgun Gothic'"),
                "fontColor": {"solid": {"color": lit("'#52606D'")}},
            }
        }]
    return out


def visual_shell(name: str, x: float, y: float, w: float, h: float, visual: dict, filters=None, z: int = 1) -> dict:
    obj = {
        "$schema": VIS,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": visual,
    }
    if filters:
        obj["filterConfig"] = {"filters": filters}
    return obj


def save_visual(page: str, item: dict) -> None:
    write_json(REPORT / "definition" / "pages" / page / "visuals" / item["name"] / "visual.json", item)


def filter_in(name: str, entity: str, prop: str, values: list[str]) -> dict:
    return {
        "name": name,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "type": "Categorical",
        "howCreated": "User",
        "filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": entity, "Type": 0}],
            "Where": [{
                "Condition": {
                    "In": {
                        "Expressions": [{
                            "Column": {
                                "Expression": {"SourceRef": {"Source": "s"}},
                                "Property": prop,
                            }
                        }],
                        "Values": [[{"Literal": {"Value": "'" + value.replace("'", "''") + "'"}}] for value in values],
                    }
                }
            }],
        },
    }


def filter_not_blank(name: str, entity: str, prop: str) -> dict:
    return {
        "name": name,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "type": "Advanced",
        "howCreated": "User",
        "filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": entity, "Type": 0}],
            "Where": [{
                "Condition": {
                    "Not": {
                        "Expression": {
                            "Comparison": {
                                "ComparisonKind": 0,
                                "Left": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": "s"}},
                                        "Property": prop,
                                    }
                                },
                                "Right": {"Literal": {"Value": "null"}},
                            }
                        }
                    }
                }
            }],
        },
    }


def clone_filters(filters: list[dict], suffix: str) -> list[dict]:
    copied = json.loads(json.dumps(filters, ensure_ascii=False))
    for item in copied:
        item["name"] = f"{item['name']}_{suffix}"
    return copied


def filter_topn(name: str, entity: str, category: str, value_column: str, count: int) -> dict:
    column = {
        "Column": {
            "Expression": {"SourceRef": {"Source": "f"}},
            "Property": category,
        }
    }
    return {
        "name": name,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": category}},
        "type": "TopN",
        "howCreated": "User",
        "filter": {
            "Version": 2,
            "From": [
                {
                    "Name": "subquery",
                    "Expression": {
                        "Subquery": {
                            "Query": {
                                "Version": 2,
                                "From": [{"Name": "f", "Entity": entity, "Type": 0}],
                                "Select": [{**column, "Name": "field"}],
                                "OrderBy": [{
                                    "Direction": 2,
                                    "Expression": {
                                        "Aggregation": {
                                            "Expression": {
                                                "Column": {
                                                    "Expression": {"SourceRef": {"Source": "f"}},
                                                    "Property": value_column,
                                                }
                                            },
                                            "Function": 0,
                                        }
                                    },
                                }],
                                "Top": count,
                            }
                        }
                    },
                    "Type": 2,
                },
                {"Name": "f", "Entity": entity, "Type": 0},
            ],
            "Where": [{
                "Condition": {
                    "In": {
                        "Expressions": [column],
                        "Table": {"SourceRef": {"Source": "subquery"}},
                    }
                }
            }],
        },
    }


def sort_measure(entity: str, measure: str, direction: str = "Descending") -> dict:
    return {
        "sort": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": measure}},
            "direction": direction,
        }],
        "isDefaultSort": True,
    }


def sort_column(entity: str, prop: str, direction: str = "Ascending") -> dict:
    return {
        "sort": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "direction": direction,
        }],
        "isDefaultSort": True,
    }


def message_card(name: str, measure: str, x, y, w, h) -> dict:
    visual = {
        "visualType": "card",
        "query": {"queryState": {"Values": bucket([measure_field("안내", measure)])}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit("12D"), "fontFamily": lit("'Malgun Gothic'"), "color": {"solid": {"color": lit(INK)}}}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {"show": lit("false")}}],
            "background": [{"properties": {"show": lit("true"), "color": {"solid": {"color": lit(PAPER)}}, "transparency": lit("0D")}}],
            "border": [{"properties": {"show": lit("false")}}],
        },
        "drillFilterOtherVisuals": True,
    }
    return visual_shell(name, x, y, w, h, visual, z=0)


def number_card(name, entity, measure, title, subtitle, x, y, w, h, font="22D", show_title=True, tooltips=None) -> dict:
    state = {"Values": bucket([measure_field(entity, measure)])}
    if tooltips:
        state["Tooltips"] = bucket(tooltips)
    visual = {
        "visualType": "card",
        "query": {"queryState": state},
        "objects": {
            "labels": [{"properties": {
                "fontSize": lit(font),
                "fontFamily": lit("'Malgun Gothic'"),
                "labelDisplayUnits": lit("1D"),
            }}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    item = visual_shell(name, x, y, w, h, visual, z=2)
    if not show_title:
        item["visual"]["visualContainerObjects"]["title"][0]["properties"]["show"] = lit("false")
        if subtitle:
            item["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]["show"] = lit("false")
    return item


def slicer(name, entity, prop, title, x, y, w, h, mode="Dropdown", filters=None, sort_prop=None, horizontal=False, single=False) -> dict:
    visual = {
        "visualType": "slicer",
        "query": {
            "queryState": {"Values": bucket([col_field(entity, prop)])},
            "sortDefinition": sort_column(entity, sort_prop or prop, "Ascending"),
        },
        "objects": {
            "data": [{"properties": {"mode": lit(f"'{mode}'")}}],
            "header": [{"properties": {
                "show": lit("true"),
                "text": lit(f"'{title}'"),
                "fontFamily": lit("'Malgun Gothic'"),
                "fontSize": lit("11D"),
            }}],
            "items": [{"properties": {"fontFamily": lit("'Malgun Gothic'"), "fontSize": lit("11D")}}],
        },
        "visualContainerObjects": container(title),
        "drillFilterOtherVisuals": True,
    }
    if horizontal:
        visual["objects"]["general"] = [{"properties": {"orientation": lit("0D")}}]
    if single:
        visual["objects"]["selection"] = [{"properties": {"singleSelect": lit("true"), "selectAllCheckboxEnabled": lit("false")}}]
    visual["visualContainerObjects"]["title"][0]["properties"]["show"] = lit("false")
    return visual_shell(name, x, y, w, h, visual, filters, z=3)


def line_chart(name, entity, category, measures, title, subtitle, x, y, w, h, filters=None, tooltips=None) -> dict:
    state = {"Category": bucket([col_field(entity, category)]), "Y": bucket(measures)}
    if tooltips:
        state["Tooltips"] = bucket(tooltips)
    visual = {
        "visualType": "lineChart",
        "query": {"queryState": state, "sortDefinition": sort_column(entity, category, "Ascending")},
        "objects": {
            "labels": [{"properties": {"show": lit("false")}}],
            "categoryAxis": [{"properties": {
                "fontSize": lit("9D"),
                "fontFamily": lit("'Malgun Gothic'"),
                "labelDensity": lit("20D"),
            }}],
            "valueAxis": [{"properties": {"fontSize": lit("9D"), "fontFamily": lit("'Malgun Gothic'")}}],
            "legend": [{"properties": {"show": lit("false")}}],
            "dataPoint": [{"properties": {"fill": {"solid": {"color": lit(NAVY)}}}}],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    return visual_shell(name, x, y, w, h, visual, filters, z=4)


def column_chart(name, entity, category, measures, title, subtitle, x, y, w, h, filters=None, tooltips=None) -> dict:
    state = {
        "Category": bucket([col_field(entity, category)]),
        "Y": bucket(measures),
    }
    if tooltips:
        state["Tooltips"] = bucket(tooltips)
    visual = {
        "visualType": "clusteredColumnChart",
        "query": {"queryState": state, "sortDefinition": sort_column(entity, category, "Ascending")},
        "objects": {
            "labels": [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "fontFamily": lit("'Malgun Gothic'")}}],
            "categoryAxis": [{"properties": {"fontSize": lit("9D"), "fontFamily": lit("'Malgun Gothic'")}}],
            "valueAxis": [{"properties": {"fontSize": lit("9D"), "fontFamily": lit("'Malgun Gothic'")}}],
            "legend": [{"properties": {"show": lit("false")}}],
            "dataPoint": [{"properties": {"fill": {"solid": {"color": lit(NAVY)}}}}],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    return visual_shell(name, x, y, w, h, visual, filters, z=4)


def bar_chart(name, entity, category, measure, title, subtitle, x, y, w, h, filters=None, tooltips=None, sort_entity=None, sort_by=None) -> dict:
    state = {
        "Category": bucket([col_field(entity, category)]),
        "Y": bucket([measure]),
    }
    if tooltips:
        state["Tooltips"] = bucket(tooltips)
    visual = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": state,
            "sortDefinition": sort_measure(sort_entity or entity, sort_by or measure["field"]["Measure"]["Property"], "Descending"),
        },
        "objects": {
            "labels": [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "fontFamily": lit("'Malgun Gothic'")}}],
            "categoryAxis": [{"properties": {
                "fontSize": lit("10D"),
                "fontFamily": lit("'Malgun Gothic'"),
                "labelDensity": lit("100D"),
                "maxMargin": lit("45D"),
            }}],
            "valueAxis": [{"properties": {"show": lit("true"), "fontSize": lit("9D")}}],
            "legend": [{"properties": {"show": lit("false")}}],
            "dataPoint": [{"properties": {"fill": {"solid": {"color": lit(NAVY)}}}}],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    return visual_shell(name, x, y, w, h, visual, filters, z=4)


def table_visual(name, entity, columns, title, subtitle, x, y, w, h, filters=None, sort=None) -> dict:
    visual = {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": bucket(columns)}},
        "objects": {
            "grid": [{"properties": {"gridVertical": lit("true"), "gridHorizontal": lit("true")}}],
            "columnHeaders": [{"properties": {"fontFamily": lit("'Malgun Gothic'"), "fontSize": lit("9D"), "fontColor": {"solid": {"color": lit(WHITE)}}, "backColor": {"solid": {"color": lit(NAVY)}}}}],
            "values": [{"properties": {"fontFamily": lit("'Malgun Gothic'"), "fontSize": lit("9D")}}],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    if sort:
        visual["query"]["sortDefinition"] = sort
    return visual_shell(name, x, y, w, h, visual, filters, z=5)


def matrix_visual(name, row_entity, row, col, measure, title, subtitle, x, y, w, h, filters=None) -> dict:
    visual = {
        "visualType": "pivotTable",
        "query": {
            "queryState": {
                "Rows": bucket([col_field(row_entity, row)]),
                "Columns": bucket([col_field(row_entity, col)]),
                "Values": bucket([measure]),
            }
        },
        "objects": {
            "rowHeaders": [{"properties": {"fontFamily": lit("'Malgun Gothic'"), "fontSize": lit("9D"), "wordWrap": lit("false")}}],
            "columnHeaders": [{"properties": {"fontFamily": lit("'Malgun Gothic'"), "fontSize": lit("8D"), "wordWrap": lit("true")}}],
            "values": [{
                "properties": {
                    "fontFamily": lit("'Malgun Gothic'"),
                    "fontSize": lit("9D"),
                }
            }],
        },
        "visualContainerObjects": container(title, subtitle),
        "drillFilterOtherVisuals": True,
    }
    return visual_shell(name, x, y, w, h, visual, filters, z=4)


def action_button(name, text, action, x, y, w, h, destination=None) -> dict:
    link = {"show": lit("true"), "type": lit(f"'{action}'")}
    if destination:
        link["navigationSection"] = lit(f"'{destination}'")
    visual = {
        "visualType": "actionButton",
        "objects": {
            "text": [{"properties": {
                "text": lit(f"'{text}'"),
                "fontFamily": lit("'Malgun Gothic'"),
                "fontSize": lit("11D"),
                "fontColor": {"solid": {"color": lit(WHITE)}},
            }}],
            "icon": [{"properties": {"show": lit("false")}}],
            "fill": [{"properties": {"fillColor": {"solid": {"color": lit(NAVY)}}}}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {"show": lit("false")}}],
            "background": [{"properties": {"show": lit("false")}}],
            "border": [{"properties": {"show": lit("false")}}],
            "visualLink": [{"properties": link}],
        },
        "drillFilterOtherVisuals": True,
    }
    item = visual_shell(name, x, y, w, h, visual, z=8)
    item["howCreated"] = "InsertVisualButton"
    return item


def page_json(name, display, visuals, interactions=None, filters=None, height=720, fit="FitToPage") -> None:
    obj = {
        "$schema": PAGE,
        "name": name,
        "displayName": display,
        "displayOption": fit,
        "height": height,
        "width": 1280,
        "objects": {
            "background": [{"properties": {"color": {"solid": {"color": lit(PAPER)}}, "transparency": lit("0D")}}],
            "displayArea": [{"properties": {"verticalAlignment": lit("'Top'")}}],
        },
    }
    if filters:
        obj["filterConfig"] = {"filters": filters}
    if interactions:
        obj["visualInteractions"] = interactions
    write_json(REPORT / "definition" / "pages" / name / "page.json", obj)
    for item in visuals:
        save_visual(name, item)


def build_pages() -> None:
    views = measure_field("영상", "관측 누적조회수")
    median = measure_field("영상", "조회수 중앙값")
    valid = measure_field("영상", "조회수 유효 영상 수")
    video_n = measure_field("영상", "영상 수")
    share = measure_field("영상", "길이 비중", "길이 비중")
    scoped = measure_field("연결", "한 범위 댓글 수")
    vids = measure_field("연결", "한 범위 영상 수")
    chans = measure_field("연결", "한 범위 채널 수")
    reason = measure_field("연결", "직접 이유 댓글 수")
    specific = measure_field("연결", "구체적 긍정 댓글 수")
    p1 = [
        message_card("p1q", "질문 1", 16, 6, 1248, 28),
        message_card("p1msg", "문구 1", 16, 34, 1248, 24),
        slicer("p1year", "영상", "게시연도", "게시 연도", 16, 64, 400, 68),
        slicer("p1len", "영상", "길이구간", "길이 구간", 432, 64, 400, 68),
        slicer("p1ch", "영상", "채널명", "채널", 848, 64, 416, 68, filters=[filter_not_blank("p1chBlank", "영상", "채널명")]),
        number_card("p1v", "영상", "영상 수", "A 영상 수", "댓글이 달린 영상만으로 줄이지 않음", 16, 140, 400, 84),
        number_card("p1c", "영상", "채널 수", "채널 수", "계정 정보가 있는 채널", 432, 140, 400, 84),
        number_card(
            "p1s", "영상", "조회수 표시", "관측 누적조회수", "정확한 횟수와 중앙값은 마우스를 올리세요",
            848, 140, 416, 84, tooltips=[views, median, valid],
        ),
        line_chart(
            "p1month", "영상", "게시월", [video_n],
            "월별 업로드",
            "2022-01~2026-10. 숫자 라벨은 점 위에 올리면 보입니다. 게시 시각 없는 8편은 제외. 성장률은 계산하지 않음",
            16, 232, 1248, 230,
            filters=[filter_not_blank("p1monthBlank", "영상", "게시월")],
        ),
        bar_chart(
            "p1dur", "영상", "길이구간", share,
            "길이 구간 비중",
            "60초 이하를 Shorts로 부르지 않음. 마우스를 올리면 영상 수",
            16, 472, 620, 188,
            tooltips=[video_n],
            sort_entity="영상",
            sort_by="길이 비중",
        ),
        bar_chart(
            "p1top", "영상", "채널명", views,
            "조회수 상위 5개 채널",
            "TOP 5. 6위 이하는 제외. 이 채널의 전체 영상 성과가 아님",
            652, 472, 612, 188,
            filters=[filter_not_blank("p1topBlank", "영상", "채널명"), filter_topn("p1topN", "영상", "채널명", "조회수", 5)],
            sort_entity="영상",
            sort_by="관측 누적조회수",
        ),
        message_card("p1foot", "바닥 1", 16, 668, 1248, 28),
    ]
    p1[9]["visual"]["query"]["sortDefinition"] = sort_column("영상", "길이구간", "Ascending")
    page_json("p1", "1. 콘텐츠 현황", p1)

    theme_m = measure_field("제목소재", "제목 출현 영상 수")
    mention_m = measure_field("댓글언급", "언급 댓글 수")
    eval_m = measure_field("댓글평가", "평가 언급 댓글 수")
    p2 = [
        message_card("p2q", "질문 2", 16, 8, 1248, 28),
        message_card("p2msg", "문구 2", 16, 36, 1248, 28),
        bar_chart(
            "p2theme", "제목소재", "키워드", theme_m,
            "제목 소재 TOP 7",
            "단위: 영상 수. 분모 6,462편. 8위 이하·제목 구절·해시태그는 상세조회",
            16, 76, 400, 560,
            filters=[
                filter_in("p2themePos", "제목소재", "위치", ["제목 본문"]),
                filter_in("p2themeKind", "제목소재", "종류", ["소재"]),
                filter_topn("p2themeN", "제목소재", "키워드", "출현영상수", 7),
            ],
            sort_entity="제목소재", sort_by="제목 출현 영상 수",
        ),
        bar_chart(
            "p2char", "댓글언급", "캐릭터", mention_m,
            "캐릭터 언급 TOP 7",
            "단위: 댓글 수. 한국어·혼합. 작품명과 겹치는 치이카와·먼작귀는 제외",
            432, 76, 400, 560,
            filters=[
                filter_in("p2charKind", "댓글언급", "종류", ["캐릭터"]),
                filter_topn("p2charN", "댓글언급", "캐릭터", "한국어혼합", 7),
            ],
            sort_entity="댓글언급", sort_by="언급 댓글 수",
        ),
        bar_chart(
            "p2eval", "댓글평가", "키워드", eval_m,
            "평가 표현 TOP 5",
            "분모 23,624건. 귀엽다 45.5%는 이 집단의 포함 비율. 팬 전체 비율이 아님",
            848, 76, 416, 560,
            filters=[filter_topn("p2evalN", "댓글평가", "키워드", "언급댓글수", 5)],
            sort_entity="댓글평가", sort_by="평가 언급 댓글 수",
        ),
        message_card("p2foot", "바닥 2", 16, 668, 1000, 36),
        action_button("p2go", "상세조회", "PageNavigation", 1040, 676, 220, 32, "p5"),
    ]
    page_json(
        "p2",
        "2. 소재와 캐릭터",
        p2,
        interactions=[
            {"source": "p2theme", "target": "p2char", "type": "NoFilter"},
            {"source": "p2theme", "target": "p2eval", "type": "NoFilter"},
            {"source": "p2char", "target": "p2theme", "type": "NoFilter"},
            {"source": "p2char", "target": "p2eval", "type": "NoFilter"},
            {"source": "p2eval", "target": "p2theme", "type": "NoFilter"},
            {"source": "p2eval", "target": "p2char", "type": "NoFilter"},
        ],
    )

    charm_filters = [
        filter_in("p3inc", "연결", "매력집계", ["포함"]),
        filter_in("p3who", "연결", "평가대상", ["특정 캐릭터"]),
        filter_in("p3show", "연결", "본문우선", ["본문"]),
    ]
    p3 = [
        message_card("p3q", "질문 3", 16, 6, 860, 28),
        action_button("p3go", "상세조회", "PageNavigation", 900, 8, 170, 32, "p5"),
        action_button("p3reset", "선택 초기화", "ClearAllSlicers", 1084, 8, 180, 32),
        slicer(
            "p3char", "연결", "표시대상", "캐릭터 한 명",
            16, 46, 420, 64, single=True,
        ),
        message_card("p3msg", "문구 3", 452, 46, 812, 64),
        bar_chart(
            "p3bar", "연결", "매력", scoped,
            "구체적 매력 TOP 5",
            "고유 댓글. 특징을 특정하지 않은 항목은 상세조회. 5개 미만이면 있는 만큼만",
            16, 122, 620, 400,
            filters=[filter_topn("p3barN", "연결", "매력", "댓글대표행", 5)],
            tooltips=[reason, specific],
            sort_entity="연결", sort_by="한 범위 댓글 수",
        ),
        number_card("p3c1", "연결", "대표 댓글 1", "대표 댓글", "막대를 고르면 바뀝니다", 652, 122, 612, 128, font="12D"),
        number_card("p3c2", "연결", "대표 댓글 2", "대표 댓글", None, 652, 258, 612, 128, font="12D"),
        number_card("p3c3", "연결", "대표 댓글 3", "대표 댓글", None, 652, 394, 612, 128, font="12D"),
        number_card("p3n", "연결", "한 범위 댓글 수", "고유 댓글", "같은 댓글은 한 번", 16, 534, 400, 92),
        number_card("p3v", "연결", "한 범위 영상 수", "영상", "이 매력이 나온 영상", 432, 534, 400, 92),
        number_card("p3h", "연결", "한 범위 채널 수", "채널", "영상을 올린 채널", 848, 534, 416, 92),
        message_card("p3foot", "바닥 3", 16, 668, 1248, 36),
    ]
    interactions = []
    for target in ("p3c1", "p3c2", "p3c3", "p3n", "p3v", "p3h"):
        interactions.append({"source": "p3bar", "target": target, "type": "DataFilter"})
    interactions.append({"source": "p3bar", "target": "p3char", "type": "NoFilter"})
    for source in ("p3c1", "p3c2", "p3c3", "p3n", "p3v", "p3h"):
        interactions.append({"source": source, "target": "p3bar", "type": "NoFilter"})
        interactions.append({"source": source, "target": "p3char", "type": "NoFilter"})
    page_json("p3", "3. 캐릭터 매력", p3, interactions=interactions, filters=charm_filters)

    area_filters = [
        filter_in("p4inc", "연결", "매력집계", ["포함"]),
        filter_in("p4show", "연결", "본문우선", ["본문"]),
    ]
    p4 = [
        message_card("p4q", "질문 4", 16, 6, 860, 28),
        action_button("p4go", "상세조회", "PageNavigation", 900, 8, 170, 32, "p5"),
        action_button("p4reset", "선택 초기화", "ClearAllSlicers", 1084, 8, 180, 32),
        slicer(
            "p4area", "영역", "짧은이름", "영역",
            16, 44, 900, 56, horizontal=True, single=True,
        ),
        message_card("p4msg", "문구 4", 16, 104, 1248, 28),
        bar_chart(
            "p4bar", "연결", "매력", scoped,
            "이 영역의 구체적 매력",
            "TOP 5를 채우지 않음. 특정하지 않은 항목·성우·제작은 상세조회",
            16, 140, 620, 300,
            filters=[filter_topn("p4barN", "연결", "매력", "댓글대표행", 5)],
            tooltips=[reason, specific],
            sort_entity="연결", sort_by="한 범위 댓글 수",
        ),
        number_card("p4c1", "연결", "대표 댓글 1", "대표 댓글", "막대를 고르면 바뀝니다", 652, 140, 612, 96, font="12D"),
        number_card("p4c2", "연결", "대표 댓글 2", "대표 댓글", None, 652, 242, 612, 96, font="12D"),
        number_card("p4c3", "연결", "대표 댓글 3", "대표 댓글", None, 652, 344, 612, 96, font="12D"),
        number_card("p4n", "연결", "한 범위 댓글 수", "고유 댓글", "선택 영역 또는 매력", 16, 450, 400, 78),
        number_card("p4v", "연결", "한 범위 영상 수", "영상", "이 조건의 영상", 432, 450, 400, 78),
        number_card("p4h", "연결", "한 범위 채널 수", "채널", "영상을 올린 채널", 848, 450, 416, 78),
        table_visual(
            "p4note", "발견가설",
            [col_field("발견가설", "구분"), col_field("발견가설", "짧은문장")],
            "확인된 내용과 제안",
            "제안은 효과나 매출이 검증된 결과가 아님. 영역을 고르면 그 문장만 남음",
            16, 538, 1248, 128,
            filters=[filter_in("p4noteArea", "발견가설", "화면", MAIN_AREAS)],
            sort=sort_column("발견가설", "순번", "Ascending"),
        ),
        message_card("p4foot", "바닥 4", 16, 676, 1248, 32),
    ]
    p4_interactions = []
    for target in ("p4c1", "p4c2", "p4c3", "p4n", "p4v", "p4h"):
        p4_interactions.append({"source": "p4bar", "target": target, "type": "DataFilter"})
    p4_interactions.append({"source": "p4bar", "target": "p4area", "type": "NoFilter"})
    p4_interactions.append({"source": "p4bar", "target": "p4note", "type": "NoFilter"})
    for source in ("p4c1", "p4c2", "p4c3", "p4note"):
        p4_interactions.append({"source": source, "target": "p4bar", "type": "NoFilter"})
        p4_interactions.append({"source": source, "target": "p4area", "type": "NoFilter"})
    page_json("p4", "4. 작품과 소비", p4, interactions=p4_interactions, filters=area_filters)

    p5 = [
        message_card("p5q", "질문 5", 16, 8, 1000, 32),
        action_button("p5back", "발표 화면으로", "PageNavigation", 1040, 8, 220, 32, "p3"),
        slicer("p5scope", "영상", "채널구분", "채널 범위. 영상과 매력 표만 다시 계산", 16, 48, 420, 64),
        table_visual(
            "p5limit", "한계",
            [col_field("한계", "항목"), col_field("한계", "내용")],
            "범위·계산·한계",
            "본문에서 반복하지 않은 주의",
            452, 48, 812, 180,
        ),
        table_visual(
            "p5theme", "제목소재",
            [col_field("제목소재", "키워드"), col_field("제목소재", "종류"), col_field("제목소재", "위치"), col_field("제목소재", "출현영상수"), col_field("제목소재", "출현채널수")],
            "제목 소재·구절 전체",
            "고정. 분모 6,462편. 채널 범위 슬라이서로 바뀌지 않음",
            16, 244, 620, 280,
            sort=sort_column("제목소재", "출현영상수", "Descending"),
        ),
        table_visual(
            "p5tag", "제목해시태그",
            [col_field("제목해시태그", "키워드"), col_field("제목해시태그", "종류"), col_field("제목해시태그", "출현영상수"), col_field("제목해시태그", "출현채널수")],
            "해시태그",
            "제목 본문과 별도. 고정 집계",
            652, 244, 612, 280,
            sort=sort_column("제목해시태그", "출현영상수", "Descending"),
        ),
        table_visual(
            "p5name", "제목표기",
            [col_field("제목표기", "키워드"), col_field("제목표기", "종류"), col_field("제목표기", "출현영상수"), col_field("제목표기", "출현채널수")],
            "제목의 작품·캐릭터 표기",
            "치이카와의 작품·캐릭터 불명확 표기는 특정 캐릭터와 다름",
            16, 536, 620, 220,
            sort=sort_column("제목표기", "출현영상수", "Descending"),
        ),
        table_visual(
            "p5mention", "댓글언급",
            [
                col_field("댓글언급", "캐릭터"), col_field("댓글언급", "종류"), col_field("댓글언급", "한국어혼합"),
                col_field("댓글언급", "영상"), col_field("댓글언급", "채널"), col_field("댓글언급", "작품캐릭터불명확"),
                col_field("댓글언급", "판단불가_이름만"),
            ],
            "댓글 언급 전체",
            "언급량은 선호도 순위가 아님. 이름만 있는 판단 불가는 한국어 분모에 넣지 않음",
            652, 536, 612, 220,
            sort=sort_column("댓글언급", "한국어혼합", "Descending"),
        ),
        table_visual(
            "p5eval", "댓글평가",
            [
                col_field("댓글평가", "키워드"), col_field("댓글평가", "언급댓글수"), col_field("댓글평가", "언급댓글비율"),
                col_field("댓글평가", "출현영상수"), col_field("댓글평가", "출현채널수"), col_field("댓글평가", "주의"),
            ],
            "평가 표현 전체",
            "분모 23,624건. 45.5%는 이 집단의 포함 비율",
            16, 768, 1248, 200,
            sort=sort_column("댓글평가", "언급댓글수", "Descending"),
        ),
        matrix_visual(
            "p5matrix", "연결", "표시대상", "매력", measure_field("연결", "고유 댓글 수"),
            "캐릭터 × 세부 매력",
            "빈 칸은 0이 아님. 특정하지 않은 항목도 보존. 고유 댓글 수",
            16, 980, 1248, 360,
            filters=[
                filter_in("p5mxInc", "연결", "매력집계", ["포함"]),
                filter_in("p5mxWho", "연결", "평가대상", ["특정 캐릭터"]),
            ],
        ),
        table_visual(
            "p5text", "연결",
            [
                col_field("연결", "표시대상"), col_field("연결", "매력"), col_field("연결", "본문우선"),
                col_field("연결", "근거문구"), col_field("연결", "댓글원문"), col_field("연결", "호감근거_수준"),
                col_field("연결", "발췌표시"), col_field("연결", "영상제목"),
            ],
            "댓글 원문",
            "한 행은 대상–특징–평가 연결. 댓글 수와 같지 않음",
            16, 1352, 1248, 320,
            filters=[filter_in("p5textInc", "연결", "매력집계", ["포함"])],
        ),
        table_visual(
            "p5status", "판정현황",
            [
                col_field("판정현황", "평가대상"), col_field("판정현황", "수"),
                col_field("판정현황", "직접 밝힌 이유"), col_field("판정현황", "구체적 긍정 평가"),
                col_field("판정현황", "포괄적 호감"), col_field("판정현황", "호감 근거 없음"),
            ],
            "평가 대상 × 근거 수준",
            "포괄 포함. 대상이 겹치면 합이 912보다 큼. 고정 집계",
            16, 1684, 760, 240,
            sort=sort_column("판정현황", "수", "Descending"),
        ),
        table_visual(
            "p5side", "연결",
            [col_field("연결", "평가대상"), col_field("연결", "보조_간접관심"), measure_field("연결", "고유 댓글 수", "고유 댓글")],
            "보조 간접관심",
            "구매·의향·질문을 합치지 않음. 성우·제작 행도 여기 남음",
            792, 1684, 472, 240,
            filters=[filter_not_blank("p5sideBlank", "연결", "보조_간접관심")],
            sort=sort_measure("연결", "고유 댓글 수", "Descending"),
        ),
        table_visual(
            "p5find", "발견가설",
            [col_field("발견가설", "구분"), col_field("발견가설", "화면"), col_field("발견가설", "상세문장")],
            "발견과 제안 원문",
            "성우·제작 구분은 음성 문장에 적혀 있다. 제안의 효과는 검증되지 않음",
            16, 1936, 1248, 280,
            sort=sort_column("발견가설", "순번", "Ascending"),
        ),
        bar_chart(
            "p5other", "연결", "평가대상", measure_field("연결", "고유 댓글 수"),
            "성우·제작 등 본문 밖 대상",
            "핵심 네 영역과 구분. 고유 댓글. 포괄은 제외",
            16, 2228, 1248, 220,
            filters=[
                filter_in("p5otherInc", "연결", "매력집계", ["포함"]),
                filter_in("p5otherWho", "연결", "평가대상", ["성우·커버 가수", "제작자·편집", "작품·캐릭터 불명확", "기타·대상 불명확"]),
            ],
            sort_entity="연결", sort_by="고유 댓글 수",
        ),
    ]
    page_json("p5", "5. 상세조회", p5, height=2480, fit="FitToWidth")


def tmdl_name(name: str) -> str:
    if re.fullmatch(r"[0-9A-Za-z_\u0080-\uffff]+", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def tmdl_col(name, data_type, hidden=False, fmt=None, sort_by=None) -> str:
    ident = tmdl_name(name)
    sort_ident = tmdl_name(sort_by) if sort_by else None
    lines = [
        f"\tcolumn {ident}",
        f"\t\tdataType: {data_type}",
        f"\t\tlineageTag: {uid()}",
        "\t\tsummarizeBy: none",
        f"\t\tsourceColumn: {ident}",
    ]
    if fmt:
        lines.append(f'\t\tformatString: "{fmt}"')
    if hidden:
        lines.append("\t\tisHidden")
    if sort_ident:
        lines.append(f"\t\tsortByColumn: {sort_ident}")
    lines.extend(["", "\t\tannotation SummarizationSetBy = None"])
    return "\n".join(lines)


def tmdl_measure(name, expression, fmt, folder) -> str:
    body = expression.strip("\n")
    if "\n" in body:
        rendered = "\n".join("\t\t\t" + line if line else "" for line in body.splitlines())
        expr = "```\n" + rendered + "\n\t\t```"
    else:
        expr = body
    return (
        f"\tmeasure '{name}' = {expr}\n"
        f"\t\tformatString: \"{fmt}\"\n"
        f"\t\tdisplayFolder: {folder}\n"
        f"\t\tlineageTag: {uid()}\n"
    )


def m_source(filename: str, columns: list[tuple[str, str]]) -> str:
    path = (DATA / filename).as_posix()
    type_lines = ", ".join(
        '{"%s", %s}' % (name, "Int64.Type" if kind == "int64" else "type number" if kind == "double" else "type text")
        for name, kind in columns
    )
    listed = ", ".join(f'"{name}"' for name, _kind in columns)
    body = (
        "let\n"
        f"    Source = Csv.Document(File.Contents(\"{path}\"), [Delimiter=\",\", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n"
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n"
        f"    Replaced = Table.ReplaceValue(Promoted, \"\", null, Replacer.ReplaceValue, {{{listed}}}),\n"
        f"    ChangedTypes = Table.TransformColumnTypes(Replaced, {{{type_lines}}})\n"
        "in\n"
        "    ChangedTypes"
    )
    return "```\n" + body + "\n```"


def write_table(name: str, filename: str, columns: list[tuple[str, str]], measures: list[str], hidden=None, sorts=None, formats=None) -> None:
    hidden = set(hidden or [])
    sorts = sorts or {}
    formats = formats or {}
    parts = [f"table {name}", f"\tlineageTag: {uid()}", ""]
    for col_name, data_type in columns:
        fmt = formats.get(col_name)
        if fmt is None and data_type == "int64" and col_name not in hidden:
            fmt = "#,0"
        if fmt is None and data_type == "double":
            fmt = "0.0%"
        parts.append(tmdl_col(col_name, data_type, col_name in hidden, fmt, sorts.get(col_name)))
        parts.append("")
    parts.extend(measures)
    parts.append(f"\tpartition {name} = m")
    parts.append("\t\tmode: import")
    parts.append(f"\t\tsource =\n{m_source(filename, columns)}")
    parts.append("")
    parts.append(f"\t\tannotation PBI_ResultType = Table")
    text = "\n".join(parts) + "\n"
    (MODEL / "definition" / "tables" / f"{name}.tmdl").write_text(text, encoding="utf-8")


def build_model() -> None:
    definition = MODEL / "definition"
    if MODEL.exists():
        shutil.rmtree(MODEL)
    (definition / "tables").mkdir(parents=True)
    measures_video = [
        tmdl_measure("영상 수", "DISTINCTCOUNT('영상'[post_id])", "#,0", "영상"),
        tmdl_measure(
            "채널 수",
            """
CALCULATE(
    DISTINCTCOUNT('영상'[account_id]),
    '영상'[account_id] <> ""
)
""".strip(),
            "#,0",
            "영상",
        ),
        tmdl_measure("관측 누적조회수", "SUM('영상'[조회수])", "#,0", "영상"),
        tmdl_measure(
            "조회수 표시",
            """
FORMAT(
    DIVIDE([관측 누적조회수], 100000000),
    "0.00"
) & "억 회"
""".strip(),
            "@",
            "영상",
        ),
        tmdl_measure("조회수 중앙값", "MEDIAN('영상'[조회수])", "#,0", "영상"),
        tmdl_measure("조회수 유효 영상 수", "COUNT('영상'[조회수])", "#,0", "영상"),
        tmdl_measure(
            "길이 비중",
            """
DIVIDE(
    [영상 수],
    CALCULATE([영상 수], REMOVEFILTERS('영상'[길이구간], '영상'[길이순서]))
)
""".strip(),
            "0.0%",
            "영상",
        ),
    ]
    write_table(
        "영상",
        "영상.csv",
        [
            ("post_id", "string"), ("account_id", "string"), ("채널명", "string"), ("채널구분", "string"),
            ("영상제목", "string"), ("게시연도", "string"), ("연도순서", "int64"), ("게시월", "string"),
            ("게시월순서", "int64"), ("길이구간", "string"), ("길이순서", "int64"), ("조회수", "int64"),
        ],
        measures_video,
        hidden={"연도순서", "게시월순서", "길이순서"},
        sorts={"게시연도": "연도순서", "게시월": "게시월순서", "길이구간": "길이순서"},
        formats={"조회수": "#,0"},
    )
    write_table(
        "댓글",
        "댓글.csv",
        [("comment_id", "string"), ("post_id", "string")],
        [tmdl_measure("수집 댓글 수", "DISTINCTCOUNT('댓글'[comment_id])", "#,0", "댓글")],
    )
    write_table(
        "문맥",
        "문맥.csv",
        [("comment_id", "string"), ("post_id", "string"), ("순번", "int64"), ("대표근거", "string"), ("대표대상", "string"), ("프롬프트", "string")],
        [tmdl_measure("문맥 판정 댓글 수", "DISTINCTCOUNT('문맥'[comment_id])", "#,0", "문맥")],
        formats={"순번": "0"},
    )
    link_measures = [
        tmdl_measure("고유 댓글 수", "DISTINCTCOUNT('연결'[comment_id])", "#,0", "연결"),
        tmdl_measure("연결 행 수", "COUNTROWS('연결')", "#,0", "연결"),
        tmdl_measure("출현 영상 수", "DISTINCTCOUNT('연결'[post_id])", "#,0", "연결"),
        tmdl_measure("출현 채널 수", "DISTINCTCOUNT('연결'[account_id])", "#,0", "연결"),
        tmdl_measure(
            "직접 이유 댓글 수",
            'CALCULATE([고유 댓글 수], \'연결\'[호감근거_수준] = "직접 밝힌 이유")',
            "#,0",
            "연결",
        ),
        tmdl_measure(
            "구체적 긍정 댓글 수",
            'CALCULATE([고유 댓글 수], \'연결\'[호감근거_수준] = "구체적 긍정 평가")',
            "#,0",
            "연결",
        ),
        tmdl_measure(
            "대상 안 비중",
            """
DIVIDE(
    [고유 댓글 수],
    CALCULATE([고유 댓글 수], REMOVEFILTERS('연결'[매력], '연결'[특징_범주], '연결'[구체적_특징]))
)
""".strip(),
            "0.0%",
            "연결",
        ),
        tmdl_measure(
            "AniBox 댓글 수",
            'CALCULATE([고유 댓글 수], \'연결\'[채널구분] = "AniBox")',
            "#,0",
            "연결",
        ),
        tmdl_measure(
            "AniBox 외 댓글 수",
            'CALCULATE([고유 댓글 수], \'연결\'[채널구분] = "AniBox 외")',
            "#,0",
            "연결",
        ),
        tmdl_measure(
            "결과 상태",
            'IF(ISBLANK([고유 댓글 수]), "이 조건에 해당하는 댓글이 없습니다", "수집·선별된 댓글에서 확인된 매력")',
            "@",
            "연결",
        ),
        tmdl_measure("한 범위 댓글 수", "IF(HASONEVALUE('연결'[표시대상]), [고유 댓글 수], BLANK())", "#,0", "연결"),
        tmdl_measure("한 범위 영상 수", "IF(HASONEVALUE('연결'[표시대상]), [출현 영상 수], BLANK())", "#,0", "연결"),
        tmdl_measure("한 범위 채널 수", "IF(HASONEVALUE('연결'[표시대상]), [출현 채널 수], BLANK())", "#,0", "연결"),
    ]
    for rank in (1, 2, 3):
        link_measures.append(tmdl_measure(
            f"대표 댓글 {rank}",
            f"""
IF(
    NOT (HASONEVALUE('연결'[표시대상]) && HASONEVALUE('연결'[매력])),
    "캐릭터 또는 영역을 고르고, 매력 막대를 선택하세요",
    VAR body = CALCULATE(MAX('연결'[댓글발췌]), '연결'[카드순] = {rank})
    VAR note = CALCULATE(MAX('연결'[매력]) & " · " & MAX('연결'[호감근거_수준]) & " · " & MAX('연결'[발췌표시]), '연결'[카드순] = {rank})
    RETURN IF(ISBLANK(body), "이 순위에는 댓글이 없습니다", note & " | " & body)
)
""".strip(),
            "@",
            "연결",
        ))
    write_table(
        "연결",
        "연결.csv",
        [
            ("연결키", "string"), ("comment_id", "string"), ("post_id", "string"), ("account_id", "string"),
            ("채널구분", "string"), ("평가대상", "string"), ("대상_상세", "string"), ("표시대상", "string"),
            ("평가_방향", "string"), ("호감근거_수준", "string"), ("특징_범주", "string"), ("구체적_특징", "string"),
            ("매력", "string"), ("매력집계", "string"), ("근거문구", "string"), ("댓글발췌", "string"),
            ("발췌표시", "string"), ("댓글원문", "string"), ("영상제목", "string"), ("대표", "int64"),
            ("비고", "string"), ("보조_간접관심", "string"), ("본문우선", "string"),
            ("댓글대표행", "int64"), ("카드순", "int64"),
        ],
        link_measures,
        hidden={"연결키", "댓글대표행", "카드순"},
        formats={"대표": "0", "댓글대표행": "0", "카드순": "0"},
    )
    write_table(
        "제목소재",
        "제목소재.csv",
        [
            ("키워드", "string"), ("종류", "string"), ("위치", "string"), ("총출현횟수", "int64"),
            ("출현영상수", "int64"), ("출현영상비율", "double"), ("출현채널수", "int64"), ("출현채널비율", "double"),
            ("분모_영상", "int64"), ("분모_채널", "int64"), ("주의", "string"), ("자료", "string"), ("정렬", "int64"),
        ],
        [tmdl_measure("제목 출현 영상 수", "SUM('제목소재'[출현영상수])", "#,0", "제목")],
        hidden={"정렬"},
    )
    write_table(
        "제목표기",
        "제목표기.csv",
        [
            ("키워드", "string"), ("종류", "string"), ("위치", "string"), ("총출현횟수", "int64"),
            ("출현영상수", "int64"), ("출현영상비율", "double"), ("출현채널수", "int64"), ("출현채널비율", "double"),
            ("분모_영상", "int64"), ("분모_채널", "int64"), ("주의", "string"), ("자료", "string"), ("정렬", "int64"),
        ],
        [],
        hidden={"정렬"},
    )
    write_table(
        "제목해시태그",
        "제목해시태그.csv",
        [
            ("키워드", "string"), ("종류", "string"), ("위치", "string"), ("총출현횟수", "int64"),
            ("출현영상수", "int64"), ("출현영상비율", "double"), ("출현채널수", "int64"), ("출현채널비율", "double"),
            ("분모_영상", "int64"), ("분모_채널", "int64"), ("주의", "string"), ("자료", "string"),
            ("분모_해시태그있는영상", "int64"), ("출현영상비율_해시태그있는영상", "double"), ("정렬", "int64"),
        ],
        [tmdl_measure("해시태그 출현 영상 수", "SUM('제목해시태그'[출현영상수])", "#,0", "제목")],
        hidden={"정렬"},
    )
    write_table(
        "댓글언급",
        "댓글언급.csv",
        [
            ("캐릭터", "string"), ("종류", "string"), ("한국어혼합", "int64"), ("영상", "int64"), ("채널", "int64"),
            ("개인_또는_캐릭터", "int64"), ("작품캐릭터불명확", "int64"), ("판단불가_이름만", "int64"),
            ("외국어_언급", "int64"), ("자료", "string"), ("분모설명", "string"),
        ],
        [tmdl_measure("언급 댓글 수", "SUM('댓글언급'[한국어혼합])", "#,0", "댓글언급")],
    )
    write_table(
        "댓글평가",
        "댓글평가.csv",
        [
            ("키워드", "string"), ("종류", "string"), ("언급댓글수", "int64"), ("언급댓글비율", "double"),
            ("출현영상수", "int64"), ("출현채널수", "int64"), ("분모_댓글", "int64"), ("분모_영상", "int64"),
            ("분모_채널", "int64"), ("주의", "string"), ("자료", "string"), ("분모설명", "string"), ("정렬", "int64"),
        ],
        [tmdl_measure("평가 언급 댓글 수", "SUM('댓글평가'[언급댓글수])", "#,0", "댓글평가")],
        hidden={"정렬"},
    )
    write_table(
        "판정현황",
        "판정현황_고정.csv",
        [
            ("집계단위", "string"), ("평가대상", "string"), ("수", "int64"), ("영상", "int64"), ("채널", "int64"),
            ("직접 밝힌 이유", "int64"), ("구체적 긍정 평가", "int64"), ("포괄적 호감", "int64"),
            ("호감 근거 없음", "int64"), ("자료", "string"), ("설명", "string"),
        ],
        [],
    )
    write_table(
        "발견가설",
        "발견가설.csv",
        [("순번", "int64"), ("구분", "string"), ("화면", "string"), ("짧은문장", "string"), ("상세문장", "string"), ("자료", "string")],
        [],
        formats={"순번": "0"},
    )
    write_table(
        "안내",
        "안내.csv",
        [("구분", "string")],
        [
            tmdl_measure("질문 1", '"한국어 제목으로 선별한 치이카와 영상은 얼마나 있고, 어떤 콘텐츠 환경을 이루는가?"', "@", "문구"),
            tmdl_measure("문구 1", '"A 영상 전체입니다. 댓글이 있는 영상만 보지 않습니다."', "@", "문구"),
            tmdl_measure("바닥 1", '"조회수는 2026-10-26~27 수집 시점의 누적값이며, 한국 내 조회수가 아닙니다."', "@", "문구"),
            tmdl_measure("질문 2", '"어떤 소재와 캐릭터가 이야기되는가?"', "@", "문구"),
            tmdl_measure("문구 2", '"제목은 영상 수, 댓글은 댓글 수입니다. 언급량은 선호도 순위가 아닙니다."', "@", "문구"),
            tmdl_measure("바닥 2", '"세 차트의 분모가 다릅니다. 고정 집계라 슬라이서가 없습니다."', "@", "문구"),
            tmdl_measure("질문 3", '"캐릭터의 어떤 모습이 매력적인가?"', "@", "문구"),
            tmdl_measure("문구 3", '"수집·선별된 댓글에서 확인된 매력입니다. 캐릭터는 한 명씩 보고, 막대는 다시 누르면 해제됩니다."', "@", "문구"),
            tmdl_measure("바닥 3", '"긍정이고 직접 이유 또는 구체적 긍정만 셉니다. 같은 댓글은 한 번입니다. 전체 팬의 비율이 아닙니다."', "@", "문구"),
            tmdl_measure("질문 4", '"캐릭터를 넘어 어떤 매력이 확인되었는가?"', "@", "문구"),
            tmdl_measure("문구 4", '"관계, 세계관·스토리, 음성·더빙, 굿즈입니다. 표본이 작으면 탐색적 확인입니다."', "@", "문구"),
            tmdl_measure("바닥 4", '"제안은 가설입니다. 캠페인 효과나 매출 증가가 확인된 결과가 아닙니다."', "@", "문구"),
            tmdl_measure("질문 5", '"상세조회. 본문에서 뺀 순위, 원문, 검증, AniBox 비교를 보존합니다."', "@", "문구"),
        ],
    )
    write_table(
        "영역",
        "영역.csv",
        [("영역명", "string"), ("짧은이름", "string"), ("정렬", "int64")],
        [],
        hidden={"정렬"},
        sorts={"짧은이름": "정렬"},
        formats={"정렬": "0"},
    )
    write_table(
        "한계",
        "한계.csv",
        [("항목", "string"), ("내용", "string")],
        [],
    )
    tables = [
        "영상", "댓글", "문맥", "연결", "영역", "제목소재", "제목표기", "제목해시태그",
        "댓글언급", "댓글평가", "판정현황", "발견가설", "한계", "안내",
    ]
    refs = "\n".join(f"ref table {name}" for name in tables)
    rels = "\n".join([
        "ref relationship 댓글_영상",
        "ref relationship 연결_영상",
        "ref relationship 연결_문맥",
        "ref relationship 연결_영역",
        "ref relationship 발견_영역",
    ])
    order = json.dumps(tables, ensure_ascii=False)
    model = f"""model Model
\tculture: ko-KR
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: ko-KR
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation PBI_QueryOrder = {order}

annotation __PBI_TimeIntelligenceEnabled = 0

{refs}

{rels}
"""
    (definition / "model.tmdl").write_text(model, encoding="utf-8")
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")
    relationships = """relationship 댓글_영상
\tfromColumn: 댓글.post_id
\ttoColumn: 영상.post_id

relationship 연결_영상
\tfromColumn: 연결.post_id
\ttoColumn: 영상.post_id

relationship 연결_문맥
\tfromColumn: 연결.comment_id
\ttoColumn: 문맥.comment_id

relationship 연결_영역
\tfromColumn: 연결.평가대상
\ttoColumn: 영역.영역명

relationship 발견_영역
\tfromColumn: 발견가설.화면
\ttoColumn: 영역.영역명
"""
    (definition / "relationships.tmdl").write_text(relationships, encoding="utf-8")
    write_json(MODEL / "definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {},
    })
    write_json(MODEL / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "치이카와 YouTube"},
        "config": {"version": "2.0", "logicalId": uid()},
    })


def build_report_shell() -> None:
    if REPORT.exists():
        shutil.rmtree(REPORT)
    (REPORT / "definition" / "pages").mkdir(parents=True)
    write_json(REPORT / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../치이카와_YouTube.SemanticModel"}},
    })
    write_json(REPORT / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "치이카와 YouTube"},
        "config": {"version": "2.0", "logicalId": uid()},
    })
    write_json(REPORT / "definition" / "version.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    write_json(REPORT / "definition" / "report.json", {
        "$schema": REPORT_SCHEMA,
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU10",
                "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.0.0"},
                "type": "SharedResources",
            }
        },
        "resourcePackages": [{
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}],
        }],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
        },
    })
    write_json(REPORT / "definition" / "pages" / "pages.json", {
        "$schema": PAGES,
        "pageOrder": ["p1", "p2", "p3", "p4", "p5"],
        "activePageName": "p1",
    })
    build_pages()
    write_json(PBIP, {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": "치이카와_YouTube.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })


def main() -> None:
    build_model()
    build_report_shell()
    print(PBIP)


if __name__ == "__main__":
    main()
