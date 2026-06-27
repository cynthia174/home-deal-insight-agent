from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insight_agent.parser import ChineseQuestionParser


def sample_df():
    return pd.DataFrame(
        {
            "城市": ["上海", "杭州"],
            "设计风格": ["现代简约", "奶油风"],
            "获客渠道": ["小红书", "老客转介绍"],
            "合同状态": ["已完工", "已取消"],
        }
    )


def test_parses_year_rank_and_dimension():
    parser = ChineseQuestionParser(reference_date=date(2026, 6, 27))
    intent = parser.parse("去年签约额最高的前三种设计风格", sample_df())
    assert intent.year == 2025
    assert intent.metric == "签约额"
    assert intent.group_by == ["设计风格"]
    assert intent.top_n == 3


def test_parses_city_filter():
    parser = ChineseQuestionParser(reference_date=date(2026, 6, 27))
    intent = parser.parse("2025年上海的平均签约额", sample_df())
    assert intent.filters == {"城市": ["上海"]}
    assert intent.aggregation == "mean"

