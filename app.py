from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from insight_agent import DataAnalysisAgent, load_business_data
from insight_agent.charts import build_chart
from insight_agent.data_loader import DataValidationError


APP_TITLE = "家装经营洞察 Agent"
SAMPLE_FILE = ROOT / "outputs" / "home-deal-insight-agent" / "家装业务演示数据.xlsx"

st.set_page_config(page_title=APP_TITLE, page_icon="⌂", layout="wide")

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 1.7rem; padding-bottom: 4rem; }
    .hero {
        padding: 28px 30px; border-radius: 22px;
        background: linear-gradient(130deg, #0B4F48 0%, #0F766E 68%, #169383 100%);
        color: white; box-shadow: 0 16px 40px rgba(15, 118, 110, .16);
        margin-bottom: 22px;
    }
    .hero .eyebrow { opacity: .72; font-size: 13px; letter-spacing: .12em; }
    .hero h1 { margin: 6px 0 8px; font-size: 34px; letter-spacing: -.03em; color: #FFFFFF !important; }
    .hero p, .hero .eyebrow { margin: 0; opacity: .88; font-size: 16px; color: #FFFFFF !important; }
    .trust-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }
    .trust-pill {
        background: rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);
        border-radius:999px; padding:7px 12px; font-size:13px;
    }
    .answer-card {
        padding: 22px 24px; background: white; border: 1px solid #DCE6E1;
        border-left: 5px solid #0F766E; border-radius: 16px; font-size: 20px;
        line-height: 1.65; box-shadow: 0 7px 24px rgba(27, 62, 52, .06);
    }
    .step-success, .step-repaired, .step-warning, .step-error {
        border-radius: 10px; padding: 5px 10px; font-size: 12px; font-weight: 700;
    }
    .step-success { background:#DCFCE7; color:#166534; }
    .step-repaired { background:#FEF3C7; color:#92400E; }
    .step-warning { background:#FFF7ED; color:#9A3412; }
    .step-error { background:#FEE2E2; color:#991B1B; }
    .table-open-button {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 10px 16px; margin-top: 8px; border-radius: 10px;
        background: #0F766E; color: #FFFFFF !important;
        text-decoration: none !important; font-weight: 700;
    }
    .table-open-button:hover { background: #0B5F58; }
    [data-testid="stSidebar"] { border-right: 1px solid #DDE5E1; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #E1E8E4; padding: 12px 15px;
        border-radius: 14px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_sample(path: str) -> tuple[pd.DataFrame, list[str]]:
    return load_business_data(path)


def render_steps(response) -> None:
    status_icons = {"success": "✓", "repaired": "↻", "warning": "!", "error": "×"}
    with st.container(border=True):
        st.subheader("Agent 工作过程")
        st.caption("每一步都可追溯：它理解了什么、筛了哪些数据、如何计算、怎样校验。")
        for index, step in enumerate(response.steps, start=1):
            icon = status_icons.get(step.status, "•")
            badge = f'<span class="step-{step.status}">{icon} {step.status.upper()}</span>'
            with st.expander(f"{index}. {step.name} — {step.summary}", expanded=step.status in {"repaired", "error"}):
                st.markdown(badge, unsafe_allow_html=True)
                for detail in step.details:
                    st.markdown(f"- {detail}")


with st.sidebar:
    st.markdown("### 数据工作台")
    data_mode = st.radio("选择数据来源", ["使用演示数据", "上传自己的表"], label_visibility="collapsed")
    uploaded = None
    if data_mode == "上传自己的表":
        uploaded = st.file_uploader("上传 Excel / CSV", type=["xlsx", "xls", "csv", "tsv"])
        st.caption("系统会自动识别常见字段别名，并提示缺失字段。")

    st.divider()
    st.markdown("### 演示开关")
    demonstrate_repair = st.toggle(
        "演示一次自动纠错",
        value=False,
        help="让第一次执行遇到一个模拟字段错误，展示 Agent 如何捕获、修复并继续。",
    )
    st.divider()
    st.markdown("### 支持的问题")
    st.caption("总额 / 平均值 / 数量 / 排名 / 趋势 / 毛利率 / 按时出图率 / 多维筛选")


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">HOME DEAL · DECISION INTELLIGENCE</div>
      <h1>家装经营洞察 Agent</h1>
      <p>用一句业务问题，直接得到可核验的数字、图表与计算过程。</p>
      <div class="trust-row">
        <span class="trust-pill">中文自然语言</span>
        <span class="trust-pill">真实数据计算</span>
        <span class="trust-pill">过程透明可追溯</span>
        <span class="trust-pill">错误自动恢复</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    if data_mode == "使用演示数据":
        if not SAMPLE_FILE.exists():
            st.error("演示数据尚未生成。请先运行 `python scripts/build_project_data.py`。")
            st.stop()
        df, repairs = load_sample(str(SAMPLE_FILE))
        source_label = "家装业务演示数据.xlsx"
    elif uploaded is not None:
        df, repairs = load_business_data(uploaded.getvalue(), filename=uploaded.name)
        source_label = uploaded.name
    else:
        st.info("请先在左侧上传一份 Excel 或 CSV；也可以切回“使用演示数据”。")
        st.stop()
except DataValidationError as exc:
    st.error(f"数据检查未通过：{exc}")
    st.stop()
except Exception as exc:
    st.error(f"文件读取失败，但程序没有崩溃：{exc}")
    st.stop()

valid_df = df[df["有效签约"]]
st.session_state["active_business_data"] = df
st.session_state["active_source_label"] = source_label
st.session_state["active_data_repairs"] = repairs

k1, k2, k3, k4 = st.columns(4)
k1.metric("当前数据", f"{len(df):,} 条")
k2.metric("有效签约", f"{len(valid_df):,} 单")
k3.metric("有效签约额", f"{valid_df['签约额'].sum() / 10_000:,.1f} 万")
k4.metric("覆盖月份", f"{df['签约月份'].nunique()} 个月")
st.caption(
    f"正在分析：{source_label}　·　数据范围：{df['签约日期'].min():%Y-%m} 至 {df['签约日期'].max():%Y-%m}"
    "　·　默认口径：排除已取消/作废合同"
)

if repairs:
    with st.expander(f"数据已自动清洗（{len(repairs)} 项）"):
        for repair in repairs:
            st.write(f"✓ {repair}")

raw_columns = [
    "项目编号", "签约日期", "城市", "门店", "客户经理", "设计师", "房屋类型", "面积㎡",
    "设计风格", "获客渠道", "签约额", "设计费", "预计成本", "毛利额", "合同状态",
    "交付状态", "出图日期", "出图时长(天)", "客户评分", "是否按时出图",
]
visible_raw_columns = [column for column in raw_columns if column in df.columns]
with st.expander(f"原始业务数据表｜{len(df):,} 条明细｜点击展开预览"):
    preview_left, preview_middle, preview_right = st.columns(3)
    preview_left.metric("数据行", f"{len(df):,}")
    preview_middle.metric("业务字段", f"{len(visible_raw_columns)}")
    preview_right.metric("有效合同", f"{int(df['有效签约'].sum()):,}")
    st.caption("这里展示前 50 条缩略预览；表格支持横向滚动、列排序和列宽调整。")
    st.dataframe(
        df[visible_raw_columns].head(50),
        use_container_width=True,
        hide_index=True,
        height=340,
        column_config={
            "签约日期": st.column_config.DateColumn("签约日期", format="YYYY-MM-DD"),
            "出图日期": st.column_config.DateColumn("出图日期", format="YYYY-MM-DD"),
            "签约额": st.column_config.NumberColumn("签约额（元）", format="¥ %d"),
            "设计费": st.column_config.NumberColumn("设计费（元）", format="¥ %d"),
            "预计成本": st.column_config.NumberColumn("预计成本（元）", format="¥ %d"),
            "毛利额": st.column_config.NumberColumn("毛利额（元）", format="¥ %d"),
        },
    )
    st.markdown(
        '<a class="table-open-button" href="/数据明细" target="_blank">'
        "↗ 在新窗口打开完整数据表工作台</a>",
        unsafe_allow_html=True,
    )

st.markdown("### 想知道什么？")
examples = [
    "去年总签约额是多少？",
    "签约额最高的前三种设计风格是什么？",
    "帮我画一张每个月签约额变化图",
    "2025年各城市的平均客单价",
    "哪个获客渠道带来的签约单数最多？",
    "各设计风格的毛利率柱状图",
]
cols = st.columns(3)
selected_example = None
for i, example in enumerate(examples):
    if cols[i % 3].button(example, key=f"example_{i}", use_container_width=True):
        selected_example = example

question = st.chat_input("例如：去年总签约额是多少？")
question = selected_example or question

if "history" not in st.session_state:
    st.session_state.history = []

if question:
    agent = DataAnalysisAgent(reference_date=date.today())
    with st.spinner("Agent 正在理解问题、计算并校验结果…"):
        response = agent.ask(question, df, repairs, demonstrate_repair=demonstrate_repair)
    st.session_state.history.insert(0, response)
    st.session_state.history = st.session_state.history[:5]

if st.session_state.history:
    response = st.session_state.history[0]
    st.markdown("### 分析结论")
    st.markdown(f'<div class="answer-card">{response.answer}</div>', unsafe_allow_html=True)
    st.caption(f"计算说明：{response.explanation}")

    if response.ok and not response.result.empty:
        left, right = st.columns([1.08, 0.92], gap="large")
        with left:
            render_steps(response)
        with right:
            if response.chart_type and response.chart_x and response.chart_y:
                fig = build_chart(
                    response.result,
                    response.chart_type,
                    response.chart_x,
                    response.chart_y,
                    response.question,
                )
                st.plotly_chart(fig, use_container_width=True)
            st.subheader("计算结果明细")
            display = response.result.copy()
            if response.intent and response.intent.metric in {"毛利率", "按时出图率"}:
                display[response.intent.metric] = display[response.intent.metric].map(lambda x: f"{x:.1%}")
            st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        render_steps(response)

if len(st.session_state.history) > 1:
    with st.expander("最近问题"):
        for old in st.session_state.history[1:]:
            st.markdown(f"**问：** {old.question}")
            st.markdown(f"**答：** {old.answer}")
            st.divider()

st.divider()
with st.expander("产品能力验证｜24 道黄金题自动评测"):
    st.write(
        "题库覆盖总额、平均值、计数、排名、时间趋势、城市/渠道/风格筛选、毛利率和按时出图率。"
        "每道题都与预先固化的正确答案逐项比对。"
    )
    if st.button("运行完整准确率评测", type="primary"):
        cases_path = ROOT / "evaluation" / "golden_questions.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        evaluator = DataAnalysisAgent(reference_date=date(2026, 6, 27))
        rows = []
        progress = st.progress(0, text="正在运行评测…")
        for index, case in enumerate(cases, start=1):
            candidate = evaluator.ask(case["question"], df, repairs)
            actual = json.loads(
                candidate.result.to_json(orient="records", force_ascii=False, double_precision=12)
            )
            expected = case["expected"]
            if case["compare"] == "first":
                actual, expected = actual[:1], expected[:1]
            values_ok = len(actual) == len(expected)
            if values_ok:
                for actual_row, expected_row in zip(actual, expected):
                    if set(actual_row) != set(expected_row):
                        values_ok = False
                        break
                    for key, expected_value in expected_row.items():
                        actual_value = actual_row[key]
                        if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                            if not math.isclose(
                                float(actual_value), float(expected_value), rel_tol=1e-8, abs_tol=1e-6
                            ):
                                values_ok = False
                                break
                        elif str(actual_value) != str(expected_value):
                            values_ok = False
                            break
            intent_ok = (
                candidate.intent is not None
                and candidate.intent.metric == case["metric"]
                and candidate.intent.group_by == case["group_by"]
            )
            passed = candidate.ok and values_ok and intent_ok
            rows.append({"题目": case["question"], "结果": "通过" if passed else "未通过"})
            progress.progress(index / len(cases), text=f"已完成 {index}/{len(cases)}")
        passed_count = sum(row["结果"] == "通过" for row in rows)
        progress.empty()
        c1, c2, c3 = st.columns(3)
        c1.metric("通过题数", f"{passed_count}/{len(rows)}")
        c2.metric("准确率", f"{passed_count / len(rows):.1%}")
        c3.metric("覆盖能力", "10 类")
        if passed_count == len(rows):
            st.success("全部通过：自然语言理解和数值结果均与黄金答案一致。")
        else:
            st.warning("有题目未通过，请展开明细检查。")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
