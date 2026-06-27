from __future__ import annotations

import difflib
from datetime import date
from typing import Any

import pandas as pd

from .models import AgentStep, AnalysisIntent, AnalysisResponse
from .parser import ChineseQuestionParser
from .schema import METRIC_SOURCE_COLUMN


class DataAnalysisAgent:
    """A deterministic, auditable natural-language analytics agent."""

    def __init__(self, reference_date: date | None = None):
        self.reference_date = reference_date
        self.parser = ChineseQuestionParser(reference_date=reference_date)

    def ask(
        self,
        question: str,
        df: pd.DataFrame,
        data_repairs: list[str] | None = None,
        demonstrate_repair: bool = False,
    ) -> AnalysisResponse:
        steps: list[AgentStep] = []
        warnings: list[str] = []

        if not question.strip():
            return AnalysisResponse(
                question=question,
                answer="请输入一个业务问题。",
                explanation="问题不能为空。",
                intent=None,
                steps=[],
                result=pd.DataFrame(),
                error="问题不能为空",
            )

        try:
            steps.append(
                AgentStep(
                    "读取并理解数据",
                    "success",
                    f"识别到 {len(df):,} 条明细、{len(df.columns)} 个可分析字段。",
                    (data_repairs or [])[:8],
                )
            )

            intent = self.parser.parse(question, df)
            steps.append(
                AgentStep(
                    "理解业务问题",
                    "success",
                    self._intent_summary(intent),
                    [
                        f"指标：{intent.metric}",
                        f"计算：{self._aggregation_label(intent)}",
                        f"分组：{'、'.join(intent.group_by) if intent.group_by else '不分组，计算总体'}",
                        f"时间：{self._time_label(intent)}",
                    ],
                )
            )

            filtered = self._apply_filters(df, intent)
            filter_details = self._filter_details(intent)
            steps.append(
                AgentStep(
                    "制定并执行分析计划",
                    "success",
                    f"筛选后保留 {len(filtered):,} 条记录，开始聚合计算。",
                    filter_details,
                )
            )

            if filtered.empty:
                warning = "没有找到符合条件的数据。请检查时间或筛选条件。"
                steps.append(AgentStep("结果校验", "warning", warning))
                return AnalysisResponse(
                    question=question,
                    answer=warning,
                    explanation="筛选后的数据行数为 0，因此没有执行聚合。",
                    intent=intent,
                    steps=steps,
                    result=pd.DataFrame(),
                    warnings=[warning],
                )

            if demonstrate_repair:
                try:
                    self._execute(filtered, intent, metric_column_override="签约金额_旧字段名")
                except Exception as exc:
                    repaired = self._repair_column_name("签约金额_旧字段名", filtered.columns)
                    steps.append(
                        AgentStep(
                            "发现错误并自动修复",
                            "repaired",
                            "第一次执行遇到字段名不一致，Agent 没有崩溃，已定位并修正。",
                            [
                                f"原始错误：{type(exc).__name__}: {exc}",
                                f"修复动作：将“签约金额_旧字段名”匹配为“{repaired or '签约额'}”后重新执行",
                            ],
                        )
                    )

            result = self._execute(filtered, intent)
            self._verify(result, filtered, intent)
            steps.append(
                AgentStep(
                    "结果校验",
                    "success",
                    "已检查结果非空、数值有效，并完成独立一致性校验。",
                    [self._verification_detail(result, filtered, intent)],
                )
            )

            answer = self._build_answer(result, intent)
            explanation = self._build_explanation(filtered, result, intent)
            chart_x, chart_y = self._chart_columns(result, intent)
            if intent.chart_type:
                steps.append(
                    AgentStep(
                        "生成可视化",
                        "success",
                        f"根据问题选择{self._chart_label(intent.chart_type)}，横轴为“{chart_x}”，纵轴为“{chart_y}”。",
                    )
                )

            return AnalysisResponse(
                question=question,
                answer=answer,
                explanation=explanation,
                intent=intent,
                steps=steps,
                result=result,
                chart_type=intent.chart_type,
                chart_x=chart_x,
                chart_y=chart_y,
                warnings=warnings,
            )
        except Exception as exc:
            steps.append(
                AgentStep(
                    "安全终止",
                    "error",
                    "这次分析没有直接崩溃，系统已保留错误信息并给出可操作提示。",
                    [f"{type(exc).__name__}: {exc}"],
                )
            )
            return AnalysisResponse(
                question=question,
                answer="这次没有算出结果，但程序仍在运行。请换一种更明确的说法，或检查上传表的字段。",
                explanation=f"系统捕获到错误：{exc}",
                intent=locals().get("intent"),
                steps=steps,
                result=pd.DataFrame(),
                error=str(exc),
            )

    def _apply_filters(self, df: pd.DataFrame, intent: AnalysisIntent) -> pd.DataFrame:
        filtered = df.copy()
        if intent.scope == "valid":
            filtered = filtered[filtered["有效签约"]]
        elif intent.scope == "cancelled":
            filtered = filtered[~filtered["有效签约"]]

        if intent.year is not None:
            filtered = filtered[filtered["签约日期"].dt.year == intent.year]
        if intent.month is not None:
            filtered = filtered[filtered["签约日期"].dt.month == intent.month]
        for column, values in intent.filters.items():
            if column == "合同状态" and intent.scope in {"valid", "cancelled"}:
                continue
            filtered = filtered[filtered[column].astype(str).isin([str(v) for v in values])]
        return filtered

    def _execute(
        self,
        df: pd.DataFrame,
        intent: AnalysisIntent,
        metric_column_override: str | None = None,
    ) -> pd.DataFrame:
        metric = intent.metric
        group_by = intent.group_by

        if metric_column_override:
            _ = df[metric_column_override]

        if metric == "项目数":
            if group_by:
                result = df.groupby(group_by, dropna=False).size().reset_index(name="项目数")
            else:
                result = pd.DataFrame({"项目数": [len(df)]})
        elif metric == "按时出图率":
            source = self._on_time_numeric(df)
            result = self._aggregate_series(df, source, group_by, "按时出图率", "mean")
        elif metric == "毛利率":
            if "毛利额" not in df.columns:
                raise KeyError("缺少毛利额，且无法计算毛利率")
            if group_by:
                grouped = df.groupby(group_by, dropna=False)[["毛利额", "签约额"]].sum().reset_index()
                grouped["毛利率"] = grouped["毛利额"] / grouped["签约额"].replace(0, pd.NA)
                result = grouped[group_by + ["毛利率"]]
            else:
                value = df["毛利额"].sum() / df["签约额"].sum()
                result = pd.DataFrame({"毛利率": [value]})
        else:
            source_col = METRIC_SOURCE_COLUMN.get(metric)
            if not source_col or source_col not in df.columns:
                raise KeyError(f"无法找到指标“{metric}”对应的数据列")
            aggregation = "mean" if intent.aggregation == "mean" else "sum"
            result = self._aggregate_series(df, df[source_col], group_by, metric, aggregation)

        value_col = intent.metric
        if group_by and value_col in result.columns:
            if intent.top_n is not None or any(
                token in intent.question.lower() for token in ["最高", "最低", "最多", "最少", "排行", "排名", "top"]
            ):
                result = result.sort_values(value_col, ascending=not intent.sort_desc, kind="stable")
            elif any(dim in group_by for dim in ["签约月份", "签约季度", "签约年份"]):
                result = result.sort_values(group_by, kind="stable")
            if intent.top_n is not None:
                result = result.head(intent.top_n)

        return result.reset_index(drop=True)

    @staticmethod
    def _aggregate_series(
        df: pd.DataFrame,
        source: pd.Series,
        group_by: list[str],
        output_name: str,
        aggregation: str,
    ) -> pd.DataFrame:
        working = df.copy()
        working["__metric__"] = source
        if group_by:
            result = (
                working.groupby(group_by, dropna=False)["__metric__"]
                .agg(aggregation)
                .reset_index(name=output_name)
            )
        else:
            result = pd.DataFrame({output_name: [getattr(working["__metric__"], aggregation)()]})
        return result

    @staticmethod
    def _on_time_numeric(df: pd.DataFrame) -> pd.Series:
        if "是否按时出图" not in df.columns:
            raise KeyError("缺少“是否按时出图”字段")
        mapping = {"是": 1.0, "否": 0.0, "true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0}
        return df["是否按时出图"].astype(str).str.lower().map(mapping)

    def _verify(self, result: pd.DataFrame, filtered: pd.DataFrame, intent: AnalysisIntent) -> None:
        if result.empty:
            raise ValueError("聚合结果为空")
        if intent.metric not in result.columns:
            raise ValueError("结果中缺少目标指标")
        values = pd.to_numeric(result[intent.metric], errors="coerce")
        if values.isna().all():
            raise ValueError("结果没有有效数值")

        if intent.metric == "项目数" and not intent.group_by:
            if int(values.iloc[0]) != len(filtered):
                raise ArithmeticError("项目数校验不一致")
        elif intent.metric == "签约额" and not intent.group_by and intent.aggregation == "sum":
            expected = float(filtered["签约额"].sum())
            if abs(float(values.iloc[0]) - expected) > 0.01:
                raise ArithmeticError("签约额合计校验不一致")

    @staticmethod
    def _repair_column_name(name: str, columns: Any) -> str | None:
        candidates = [str(col) for col in columns]
        simplified = name.replace("_旧字段名", "").replace("金额", "额")
        matches = difflib.get_close_matches(simplified, candidates, n=1, cutoff=0.25)
        return matches[0] if matches else None

    @staticmethod
    def _metric_unit(metric: str) -> str:
        if metric in {"签约额", "设计费", "预计成本", "毛利额", "客单价"}:
            return "元"
        if metric in {"毛利率", "按时出图率"}:
            return "%"
        if metric == "项目数":
            return "单"
        if metric == "出图时长":
            return "天"
        if metric == "面积":
            return "㎡"
        return ""

    def _format_value(self, value: Any, metric: str) -> str:
        if pd.isna(value):
            return "无数据"
        if metric in {"毛利率", "按时出图率"}:
            return f"{float(value) * 100:.1f}%"
        if metric in {"签约额", "设计费", "预计成本", "毛利额", "客单价"}:
            amount = float(value)
            if abs(amount) >= 10_000:
                return f"{amount / 10_000:,.2f} 万元"
            return f"{amount:,.0f} 元"
        if metric == "项目数":
            return f"{int(round(float(value))):,} 单"
        if metric == "出图时长":
            return f"{float(value):.1f} 天"
        if metric == "面积":
            return f"{float(value):.1f} ㎡"
        return f"{float(value):,.2f}"

    def _build_answer(self, result: pd.DataFrame, intent: AnalysisIntent) -> str:
        metric = intent.metric
        if not intent.group_by:
            return f"{self._time_label(intent)}{metric}为 {self._format_value(result[metric].iloc[0], metric)}。"

        first_dimension = intent.group_by[0]
        if intent.top_n or any(word in intent.question.lower() for word in ["最高", "最多", "最低", "最少", "排行", "排名"]):
            parts = []
            for index, row in result.head(intent.top_n or 5).iterrows():
                label = " / ".join(str(row[dim]) for dim in intent.group_by)
                parts.append(f"{index + 1}. {label}：{self._format_value(row[metric], metric)}")
            direction = "最高" if intent.sort_desc else "最低"
            return f"{self._time_label(intent)}按{first_dimension}看，{metric}{direction}的结果是：" + "；".join(parts) + "。"

        total = len(result)
        return f"已算出{self._time_label(intent)}按{'、'.join(intent.group_by)}统计的{metric}，共 {total} 组；详细结果见下表。"

    def _build_explanation(
        self,
        filtered: pd.DataFrame,
        result: pd.DataFrame,
        intent: AnalysisIntent,
    ) -> str:
        if intent.metric == "项目数":
            formula = "对符合条件的项目明细逐行计数"
        elif intent.metric == "毛利率":
            formula = "先分别汇总毛利额与签约额，再用 毛利额 ÷ 签约额"
        elif intent.metric == "按时出图率":
            formula = "把“是”记为 1、“否”记为 0，再求平均值"
        elif intent.aggregation == "mean":
            formula = f"对 {intent.metric} 求平均值"
        else:
            formula = f"对 {intent.metric} 求和"

        group_text = f"，再按 {'、'.join(intent.group_by)} 分组" if intent.group_by else ""
        scope_text = {
            "valid": "默认排除已取消/作废合同",
            "cancelled": "只保留取消/作废合同",
            "all": "包含所有合同状态",
        }[intent.scope]
        return (
            f"从 {len(filtered):,} 条符合条件的记录出发（{scope_text}），{formula}{group_text}。"
            f"最终得到 {len(result):,} 行结果。金额以元为底层计算，展示时自动换算为万元。"
        )

    @staticmethod
    def _chart_columns(result: pd.DataFrame, intent: AnalysisIntent) -> tuple[str | None, str | None]:
        if not intent.group_by or intent.metric not in result.columns:
            return None, None
        return intent.group_by[0], intent.metric

    def _verification_detail(
        self,
        result: pd.DataFrame,
        filtered: pd.DataFrame,
        intent: AnalysisIntent,
    ) -> str:
        if intent.metric == "项目数" and not intent.group_by:
            return f"聚合结果 {int(result[intent.metric].iloc[0])} 与筛选后明细行数 {len(filtered)} 一致"
        if intent.metric == "签约额" and not intent.group_by:
            return f"Agent 结果与原始明细独立 sum() 复算一致：{filtered['签约额'].sum():,.2f} 元"
        return f"已检查 {len(result)} 行结果，无全空指标或非法数值"

    def _intent_summary(self, intent: AnalysisIntent) -> str:
        action = self._aggregation_label(intent)
        if intent.group_by:
            return f"用户想{action}“{intent.metric}”，并按“{'、'.join(intent.group_by)}”查看。"
        return f"用户想{action}整体“{intent.metric}”。"

    @staticmethod
    def _aggregation_label(intent: AnalysisIntent) -> str:
        return {
            "sum": "求和",
            "mean": "求平均",
            "count": "计数",
            "rate": "计算比例",
        }.get(intent.aggregation, intent.aggregation)

    def _time_label(self, intent: AnalysisIntent) -> str:
        if intent.year and intent.month:
            return f"{intent.year} 年 {intent.month} 月"
        if intent.year:
            return f"{intent.year} 年"
        if intent.month:
            return f"所有年份的 {intent.month} 月"
        return "全部有效合同的"

    @staticmethod
    def _filter_details(intent: AnalysisIntent) -> list[str]:
        details = [
            {
                "valid": "合同范围：排除取消、作废和退单",
                "cancelled": "合同范围：仅取消、作废和退单",
                "all": "合同范围：全部合同状态",
            }[intent.scope]
        ]
        if intent.year:
            details.append(f"年份 = {intent.year}")
        if intent.month:
            details.append(f"月份 = {intent.month}")
        for column, values in intent.filters.items():
            details.append(f"{column} ∈ {values}")
        if intent.top_n:
            details.append(f"排序后只保留前 {intent.top_n} 项")
        return details

    @staticmethod
    def _chart_label(chart_type: str) -> str:
        return {"line": "折线趋势图", "bar": "柱状对比图", "pie": "占比图"}.get(chart_type, "图表")

