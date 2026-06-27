from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from insight_agent import load_business_data


DATA_PATH = ROOT / "outputs" / "home-deal-insight-agent" / "家装业务演示数据.xlsx"
OUTPUT_PATH = ROOT / "evaluation" / "golden_questions.json"


CASE_SPECS = [
    {"id": "total_last_year", "question": "去年总签约额是多少？", "metric": "签约额", "year": 2025},
    {"id": "total_2024", "question": "2024年总签约额是多少？", "metric": "签约额", "year": 2024},
    {"id": "total_all", "question": "全部有效合同的总签约额", "metric": "签约额"},
    {"id": "count_last_year", "question": "去年一共签了多少单？", "metric": "项目数", "year": 2025},
    {"id": "avg_deal_2025", "question": "2025年的平均客单价是多少？", "metric": "客单价", "aggregation": "mean", "year": 2025},
    {"id": "avg_design_fee_2024", "question": "2024年平均设计费是多少？", "metric": "设计费", "aggregation": "mean", "year": 2024},
    {"id": "gross_profit_2025", "question": "2025年总毛利额是多少？", "metric": "毛利额", "year": 2025},
    {
        "id": "city_revenue",
        "question": "各城市的签约额分别是多少？",
        "metric": "签约额",
        "group_by": ["城市"],
    },
    {
        "id": "top3_style",
        "question": "签约额最高的前三种设计风格是什么？",
        "metric": "签约额",
        "group_by": ["设计风格"],
        "top_n": 3,
        "sort_desc": True,
    },
    {
        "id": "top3_style_2025",
        "question": "2025年签约额最高的前三种设计风格",
        "metric": "签约额",
        "group_by": ["设计风格"],
        "year": 2025,
        "top_n": 3,
        "sort_desc": True,
    },
    {
        "id": "monthly_trend",
        "question": "帮我画一张每个月签约额变化图",
        "metric": "签约额",
        "group_by": ["签约月份"],
        "chart_type": "line",
    },
    {
        "id": "monthly_trend_2025",
        "question": "去年每个月的签约额趋势图",
        "metric": "签约额",
        "group_by": ["签约月份"],
        "year": 2025,
        "chart_type": "line",
    },
    {
        "id": "channel_count",
        "question": "各获客渠道的签约单数",
        "metric": "项目数",
        "group_by": ["获客渠道"],
    },
    {
        "id": "top_channel",
        "question": "哪个获客渠道带来的签约单数最多？",
        "metric": "项目数",
        "group_by": ["获客渠道"],
        "sort_desc": True,
        "compare": "first",
    },
    {
        "id": "shanghai_2025",
        "question": "2025年上海的总签约额",
        "metric": "签约额",
        "year": 2025,
        "filters": {"城市": ["上海"]},
    },
    {
        "id": "modern_style",
        "question": "现代简约风格的总签约额",
        "metric": "签约额",
        "filters": {"设计风格": ["现代简约"]},
    },
    {
        "id": "avg_by_house",
        "question": "各房屋类型的平均签约额",
        "metric": "签约额",
        "aggregation": "mean",
        "group_by": ["房屋类型"],
    },
    {
        "id": "margin_by_style",
        "question": "各设计风格的毛利率柱状图",
        "metric": "毛利率",
        "aggregation": "rate",
        "group_by": ["设计风格"],
        "chart_type": "bar",
    },
    {
        "id": "on_time_rate_2025",
        "question": "2025年的按时出图率是多少？",
        "metric": "按时出图率",
        "aggregation": "rate",
        "year": 2025,
    },
    {
        "id": "rating_by_designer",
        "question": "各设计师的平均客户评分",
        "metric": "客户评分",
        "aggregation": "mean",
        "group_by": ["设计师"],
    },
    {
        "id": "bottom3_city",
        "question": "签约额最低的三个城市",
        "metric": "签约额",
        "group_by": ["城市"],
        "top_n": 3,
        "sort_desc": False,
    },
    {
        "id": "nanjing_last_year",
        "question": "去年南京的总签约额",
        "metric": "签约额",
        "year": 2025,
        "filters": {"城市": ["南京"]},
    },
    {
        "id": "may_all_years",
        "question": "所有年份5月的总签约额",
        "metric": "签约额",
        "month": 5,
    },
    {
        "id": "cancelled_count",
        "question": "已取消的合同有多少单？",
        "metric": "项目数",
        "scope": "cancelled",
    },
]


def oracle(df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    scope = spec.get("scope", "valid")
    working = df.copy()
    if scope == "valid":
        working = working[working["有效签约"]]
    elif scope == "cancelled":
        working = working[~working["有效签约"]]

    if spec.get("year"):
        working = working[working["签约日期"].dt.year == spec["year"]]
    if spec.get("month"):
        working = working[working["签约日期"].dt.month == spec["month"]]
    for column, values in spec.get("filters", {}).items():
        working = working[working[column].isin(values)]

    metric = spec["metric"]
    groups = spec.get("group_by", [])
    aggregation = spec.get("aggregation", "sum")

    if metric == "项目数":
        if groups:
            result = working.groupby(groups, dropna=False).size().reset_index(name=metric)
        else:
            result = pd.DataFrame({metric: [len(working)]})
    elif metric == "毛利率":
        if groups:
            totals = working.groupby(groups, dropna=False)[["毛利额", "签约额"]].sum().reset_index()
            totals[metric] = totals["毛利额"] / totals["签约额"]
            result = totals[groups + [metric]]
        else:
            result = pd.DataFrame({metric: [working["毛利额"].sum() / working["签约额"].sum()]})
    elif metric == "按时出图率":
        on_time = working["是否按时出图"].map({"是": 1.0, "否": 0.0})
        if groups:
            temp = working.assign(_value=on_time)
            result = temp.groupby(groups, dropna=False)["_value"].mean().reset_index(name=metric)
        else:
            result = pd.DataFrame({metric: [on_time.mean()]})
    else:
        source = {
            "客单价": "签约额",
            "客户评分": "客户评分",
            "设计费": "设计费",
            "毛利额": "毛利额",
            "签约额": "签约额",
        }[metric]
        agg = "mean" if aggregation == "mean" or metric == "客单价" else "sum"
        if groups:
            result = working.groupby(groups, dropna=False)[source].agg(agg).reset_index(name=metric)
        else:
            result = pd.DataFrame({metric: [getattr(working[source], agg)()]})

    if groups and (spec.get("top_n") or "sort_desc" in spec):
        result = result.sort_values(metric, ascending=not spec.get("sort_desc", True), kind="stable")
    if spec.get("top_n"):
        result = result.head(spec["top_n"])
    return result.reset_index(drop=True)


def main() -> None:
    df, _ = load_business_data(DATA_PATH)
    cases = []
    for spec in CASE_SPECS:
        result = oracle(df, spec)
        expected_rows = json.loads(result.to_json(orient="records", force_ascii=False, double_precision=12))
        case = {
            "id": spec["id"],
            "question": spec["question"],
            "metric": spec["metric"],
            "group_by": spec.get("group_by", []),
            "chart_type": spec.get("chart_type"),
            "compare": spec.get("compare", "all"),
            "expected": expected_rows,
        }
        cases.append(case)
    OUTPUT_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(cases)} golden cases: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

