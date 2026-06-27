from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AnalysisIntent:
    question: str
    metric: str = "签约额"
    aggregation: str = "sum"
    group_by: list[str] = field(default_factory=list)
    filters: dict[str, list[Any]] = field(default_factory=dict)
    year: int | None = None
    month: int | None = None
    top_n: int | None = None
    sort_desc: bool = True
    chart_type: str | None = None
    scope: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentStep:
    name: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)


@dataclass
class AnalysisResponse:
    question: str
    answer: str
    explanation: str
    intent: AnalysisIntent | None
    steps: list[AgentStep]
    result: pd.DataFrame
    chart_type: str | None = None
    chart_x: str | None = None
    chart_y: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

