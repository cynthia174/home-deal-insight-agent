from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


TEAL = "#0F766E"
ORANGE = "#D97706"


def build_chart(
    result: pd.DataFrame,
    chart_type: str,
    x: str,
    y: str,
    title: str,
) -> go.Figure:
    plot_data = result.copy()
    if y in {"毛利率", "按时出图率"}:
        plot_data[y] = plot_data[y] * 100
        y_label = f"{y}（%）"
    elif y in {"签约额", "设计费", "预计成本", "毛利额", "客单价"}:
        plot_data[y] = plot_data[y] / 10_000
        y_label = f"{y}（万元）"
    else:
        y_label = y

    if chart_type == "line":
        fig = px.line(plot_data, x=x, y=y, markers=True, title=title)
        fig.update_traces(line_color=TEAL, line_width=3, marker_size=8)
    elif chart_type == "pie":
        fig = px.pie(plot_data, names=x, values=y, title=title, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent+label")
    else:
        fig = px.bar(plot_data, x=x, y=y, title=title, text_auto=".3s")
        fig.update_traces(marker_color=TEAL)

    fig.update_layout(
        height=430,
        margin=dict(l=30, r=30, t=65, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Microsoft YaHei, Arial", color="#17211D"),
        title=dict(font=dict(size=18)),
        xaxis_title=x,
        yaxis_title=y_label,
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#DDE5E1")
    return fig

