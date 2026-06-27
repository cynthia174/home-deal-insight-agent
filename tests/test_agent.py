from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insight_agent import DataAnalysisAgent, load_business_data
from insight_agent.data_loader import DataValidationError, normalize_business_data


DATA_PATH = ROOT / "outputs" / "home-deal-insight-agent" / "家装业务演示数据.xlsx"


@pytest.fixture(scope="module")
def dataset():
    return load_business_data(DATA_PATH)


@pytest.fixture(scope="module")
def agent():
    return DataAnalysisAgent(reference_date=date(2026, 6, 27))


def test_demo_data_is_complete(dataset):
    df, repairs = dataset
    assert len(df) == 720
    assert df["签约日期"].min().year == 2024
    assert df["签约日期"].max().year == 2025
    assert df["毛利额"].notna().all()
    assert df["有效签约"].sum() > 650
    assert isinstance(repairs, list)


def test_last_year_total_matches_pandas(dataset, agent):
    df, repairs = dataset
    response = agent.ask("去年总签约额是多少？", df, repairs)
    expected = df[df["有效签约"] & (df["签约日期"].dt.year == 2025)]["签约额"].sum()
    assert response.ok
    assert response.intent.year == 2025
    assert response.result["签约额"].iloc[0] == expected


def test_top_three_styles(dataset, agent):
    df, repairs = dataset
    response = agent.ask("签约额最高的前三种设计风格是什么？", df, repairs)
    assert response.ok
    assert response.intent.top_n == 3
    assert len(response.result) == 3
    assert response.result["签约额"].is_monotonic_decreasing


def test_monthly_chart_intent(dataset, agent):
    df, repairs = dataset
    response = agent.ask("帮我画一张每个月签约额变化图", df, repairs)
    assert response.ok
    assert response.chart_type == "line"
    assert response.chart_x == "签约月份"
    assert len(response.result) == 24


def test_repair_step_continues(dataset, agent):
    df, repairs = dataset
    response = agent.ask("去年总签约额是多少？", df, repairs, demonstrate_repair=True)
    assert response.ok
    assert any(step.status == "repaired" for step in response.steps)
    assert not response.result.empty


def test_column_alias_is_repaired():
    raw = pd.DataFrame(
        {
            "项目ID": ["P1"],
            "签单日期": ["2025-01-02"],
            "合同金额": ["¥100,000"],
            "装修风格": ["现代简约"],
            "订单状态": ["已完工"],
            "成本": ["60,000"],
        }
    )
    normalized, repairs = normalize_business_data(raw)
    assert normalized["签约额"].iloc[0] == 100000
    assert normalized["毛利额"].iloc[0] == 40000
    assert len(repairs) >= 5


def test_missing_required_columns_has_friendly_error():
    with pytest.raises(DataValidationError, match="缺少关键字段"):
        normalize_business_data(pd.DataFrame({"金额": [1]}))

