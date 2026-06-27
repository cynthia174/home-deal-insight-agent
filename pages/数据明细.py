from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from insight_agent import load_business_data


SAMPLE_FILE = ROOT / "outputs" / "home-deal-insight-agent" / "家装业务演示数据.xlsx"
RAW_COLUMNS = [
    "项目编号", "签约日期", "城市", "门店", "客户经理", "设计师", "房屋类型", "面积㎡",
    "设计风格", "获客渠道", "签约额", "设计费", "预计成本", "毛利额", "合同状态",
    "交付状态", "出图日期", "出图时长(天)", "客户评分", "是否按时出图",
]

st.set_page_config(page_title="完整业务数据表", page_icon="▦", layout="wide")

st.markdown(
    """
    <style>
    .block-container { max-width: 1540px; padding-top: 1.4rem; padding-bottom: 3rem; }
    .table-hero {
        padding: 22px 26px; border-radius: 18px; color: white;
        background: linear-gradient(130deg, #0B4F48, #0F766E);
        margin-bottom: 18px;
    }
    .table-hero h1 { color: white !important; margin: 0 0 6px; font-size: 30px; }
    .table-hero p { color: rgba(255,255,255,.84) !important; margin: 0; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #DDE7E2; padding: 10px 14px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_sample(path: str) -> pd.DataFrame:
    data, _ = load_business_data(path)
    return data


if "active_business_data" in st.session_state:
    df = st.session_state["active_business_data"].copy()
    source_label = st.session_state.get("active_source_label", "当前数据")
else:
    df = load_sample(str(SAMPLE_FILE))
    source_label = SAMPLE_FILE.name

visible_columns = [column for column in RAW_COLUMNS if column in df.columns]

st.markdown(
    f"""
    <div class="table-hero">
      <h1>完整业务数据表</h1>
      <p>{source_label} · 像多维表格一样筛选、排序、搜索和浏览全部明细</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.page_link("app.py", label="← 返回分析 Agent")

with st.form("table_filters", border=True):
    search = st.text_input(
        "全表搜索",
        placeholder="输入项目编号、门店、人员、风格或渠道…",
    )
    filter_columns = st.columns(5)
    with filter_columns[0]:
        years = st.multiselect(
            "签约年份",
            sorted(df["签约日期"].dropna().dt.year.unique().astype(int).tolist()),
            placeholder="全部年份",
        )
    with filter_columns[1]:
        cities = st.multiselect(
            "城市",
            sorted(df["城市"].dropna().astype(str).unique().tolist()) if "城市" in df.columns else [],
            placeholder="全部城市",
        )
    with filter_columns[2]:
        styles = st.multiselect(
            "设计风格",
            sorted(df["设计风格"].dropna().astype(str).unique().tolist()) if "设计风格" in df.columns else [],
            placeholder="全部风格",
        )
    with filter_columns[3]:
        statuses = st.multiselect(
            "合同状态",
            sorted(df["合同状态"].dropna().astype(str).unique().tolist()),
            placeholder="全部状态",
        )
    with filter_columns[4]:
        channels = st.multiselect(
            "获客渠道",
            sorted(df["获客渠道"].dropna().astype(str).unique().tolist()) if "获客渠道" in df.columns else [],
            placeholder="全部渠道",
        )
    st.form_submit_button("应用筛选", type="primary", use_container_width=True)

filtered = df.copy()
if years:
    filtered = filtered[filtered["签约日期"].dt.year.isin(years)]
if cities:
    filtered = filtered[filtered["城市"].astype(str).isin(cities)]
if styles:
    filtered = filtered[filtered["设计风格"].astype(str).isin(styles)]
if statuses:
    filtered = filtered[filtered["合同状态"].astype(str).isin(statuses)]
if channels:
    filtered = filtered[filtered["获客渠道"].astype(str).isin(channels)]
if search.strip():
    searchable = filtered[visible_columns].astype(str).agg(" ".join, axis=1)
    filtered = filtered[searchable.str.contains(search.strip(), case=False, na=False, regex=False)]

valid_filtered = filtered[filtered["有效签约"]]
m1, m2, m3, m4 = st.columns(4)
m1.metric("当前显示", f"{len(filtered):,} / {len(df):,} 行")
m2.metric("有效合同", f"{len(valid_filtered):,} 单")
m3.metric("有效签约额", f"{valid_filtered['签约额'].sum() / 10_000:,.1f} 万")
m4.metric("字段数量", f"{len(visible_columns)} 列")

st.caption("提示：点击列名可排序；拖动列边界可调整宽度；表格支持横向和纵向滚动。")
st.dataframe(
    filtered[visible_columns],
    use_container_width=True,
    hide_index=True,
    height=620,
    column_config={
        "签约日期": st.column_config.DateColumn("签约日期", format="YYYY-MM-DD"),
        "出图日期": st.column_config.DateColumn("出图日期", format="YYYY-MM-DD"),
        "项目编号": st.column_config.TextColumn("项目编号"),
        "面积㎡": st.column_config.NumberColumn("面积㎡", format="%d ㎡"),
        "签约额": st.column_config.NumberColumn("签约额（元）", format="¥ %d"),
        "设计费": st.column_config.NumberColumn("设计费（元）", format="¥ %d"),
        "预计成本": st.column_config.NumberColumn("预计成本（元）", format="¥ %d"),
        "毛利额": st.column_config.NumberColumn("毛利额（元）", format="¥ %d"),
        "客户评分": st.column_config.NumberColumn("客户评分", format="%.1f"),
    },
)

download_left, download_right, _ = st.columns([1, 1, 4])
with download_left:
    csv_bytes = filtered[visible_columns].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载筛选结果 CSV",
        data=csv_bytes,
        file_name="家装业务筛选结果.csv",
        mime="text/csv",
        use_container_width=True,
    )
with download_right:
    if SAMPLE_FILE.exists():
        st.download_button(
            "下载原始 Excel",
            data=SAMPLE_FILE.read_bytes(),
            file_name="家装业务演示数据.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
