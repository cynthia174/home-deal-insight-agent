from __future__ import annotations

import re
from datetime import date

import pandas as pd

from .models import AnalysisIntent
from .schema import CATEGORICAL_COLUMNS, DIMENSION_ALIASES, METRIC_ALIASES


CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _parse_small_number(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    if token in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[token]
    if len(token) == 2 and token.startswith("十") and token[1] in CHINESE_NUMBERS:
        return 10 + CHINESE_NUMBERS[token[1]]
    return None


class ChineseQuestionParser:
    def __init__(self, reference_date: date | None = None):
        self.reference_date = reference_date or date.today()

    def parse(self, question: str, df: pd.DataFrame) -> AnalysisIntent:
        q = re.sub(r"\s+", "", question.strip().lower())
        intent = AnalysisIntent(question=question)

        metric_candidates = sorted(
            (
                (alias.lower(), metric)
                for metric, aliases in METRIC_ALIASES.items()
                for alias in aliases
            ),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for alias, metric in metric_candidates:
            if alias in q:
                intent.metric = metric
                break

        if intent.metric == "项目数":
            intent.aggregation = "count"
        elif intent.metric in {"毛利率", "按时出图率"}:
            intent.aggregation = "rate"
        elif intent.metric == "客单价":
            intent.aggregation = "mean"
        elif any(word in q for word in ["平均", "均值", "人均", "单均"]):
            intent.aggregation = "mean"
        else:
            intent.aggregation = "sum"

        for dimension, aliases in DIMENSION_ALIASES.items():
            if any(alias.lower() in q for alias in aliases):
                intent.group_by.append(dimension)

        if any(word in q for word in ["每个月", "各月", "按月", "月度", "月份", "月变化", "月趋势"]):
            intent.group_by.append("签约月份")
        elif any(word in q for word in ["每季度", "各季度", "按季度", "季度"]):
            intent.group_by.append("签约季度")
        elif any(word in q for word in ["每年", "各年", "按年", "年度趋势"]):
            intent.group_by.append("签约年份")

        intent.group_by = list(dict.fromkeys(intent.group_by))

        explicit_year = re.search(r"(20\d{2})年", q)
        if explicit_year:
            intent.year = int(explicit_year.group(1))
        elif "去年" in q:
            intent.year = self.reference_date.year - 1
        elif "今年" in q:
            intent.year = self.reference_date.year
        elif "前年" in q:
            intent.year = self.reference_date.year - 2

        explicit_month = re.search(r"(?<!\d)(1[0-2]|0?[1-9])月", q)
        if explicit_month:
            intent.month = int(explicit_month.group(1))

        top_match = re.search(r"(?:前|top)([一二两三四五六七八九十\d]+)", q)
        if not top_match:
            top_match = re.search(r"(?:最高|最多|最低|最少)的?([一二两三四五六七八九十\d]+)(?:个|种|名|家)?", q)
        if top_match:
            intent.top_n = _parse_small_number(top_match.group(1))

        if any(word in q for word in ["最低", "最少", "倒数"]):
            intent.sort_desc = False
        elif any(word in q for word in ["最高", "最多", "排行", "排名", "前", "top"]):
            intent.sort_desc = True

        if any(word in q for word in ["画一张", "图表", "趋势图", "变化图", "走势图", "可视化", "柱状图", "条形图", "折线图", "饼图", "构成图"]):
            if any(dim in intent.group_by for dim in ["签约月份", "签约季度", "签约年份"]):
                intent.chart_type = "line"
            else:
                intent.chart_type = "bar"

        if any(word in q for word in ["饼图", "占比图", "构成图"]):
            intent.chart_type = "pie"
        elif "柱状图" in q or "条形图" in q:
            intent.chart_type = "bar"
        elif "折线图" in q or "趋势图" in q:
            intent.chart_type = "line"

        if any(word in q for word in ["取消", "作废", "退单"]):
            intent.scope = "cancelled"
        elif any(word in q for word in ["全部合同", "包含取消", "所有合同"]):
            intent.scope = "all"

        for column in CATEGORICAL_COLUMNS:
            if column not in df.columns:
                continue
            matches: list[str] = []
            values = df[column].dropna().astype(str).unique().tolist()
            for value in values:
                if len(value.strip()) >= 2 and value.lower() in q:
                    matches.append(value)
            if matches:
                intent.filters[column] = matches

        grouping_cues = ["各", "每", "按", "分别", "不同", "排名", "排行", "最高", "最低", "最多", "最少", "top", "图"]
        for dimension in list(intent.group_by):
            if dimension in intent.filters and not any(cue in q for cue in grouping_cues):
                intent.group_by.remove(dimension)

        return intent
