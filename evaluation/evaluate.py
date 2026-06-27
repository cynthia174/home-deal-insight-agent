from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from insight_agent import DataAnalysisAgent, load_business_data


DATA_PATH = ROOT / "outputs" / "home-deal-insight-agent" / "家装业务演示数据.xlsx"
CASES_PATH = ROOT / "evaluation" / "golden_questions.json"
REPORT_PATH = ROOT / "evaluation" / "latest_report.json"


def values_close(actual, expected) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-8, abs_tol=1e-6)
    return str(actual) == str(expected)


def compare_rows(actual_rows: list[dict], expected_rows: list[dict], mode: str) -> tuple[bool, str]:
    if mode == "first":
        actual_rows = actual_rows[:1]
        expected_rows = expected_rows[:1]
    if len(actual_rows) != len(expected_rows):
        return False, f"行数不一致：actual={len(actual_rows)}, expected={len(expected_rows)}"
    for index, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
        if set(actual) != set(expected):
            return False, f"第 {index + 1} 行字段不一致：{set(actual)} != {set(expected)}"
        for key in expected:
            if not values_close(actual[key], expected[key]):
                return False, f"第 {index + 1} 行 {key} 不一致：{actual[key]} != {expected[key]}"
    return True, "结果与黄金答案一致"


def main() -> int:
    df, repairs = load_business_data(DATA_PATH)
    agent = DataAnalysisAgent(reference_date=date(2026, 6, 27))
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    details = []
    passed = 0

    print("家装经营洞察 Agent｜自动准确率评测")
    print("=" * 62)
    for case in cases:
        response = agent.ask(case["question"], df, repairs)
        actual_rows = json.loads(
            response.result.to_json(orient="records", force_ascii=False, double_precision=12)
        )
        values_ok, message = compare_rows(actual_rows, case["expected"], case["compare"])
        intent_ok = (
            response.intent is not None
            and response.intent.metric == case["metric"]
            and response.intent.group_by == case["group_by"]
        )
        chart_ok = case["chart_type"] is None or response.chart_type == case["chart_type"]
        ok = response.ok and values_ok and intent_ok and chart_ok
        passed += int(ok)
        details.append(
            {
                "id": case["id"],
                "question": case["question"],
                "passed": ok,
                "intent_ok": intent_ok,
                "values_ok": values_ok,
                "chart_ok": chart_ok,
                "message": message,
            }
        )
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case['question']} — {message}")

    total = len(cases)
    score = passed / total if total else 0
    report = {
        "dataset": DATA_PATH.name,
        "total": total,
        "passed": passed,
        "accuracy": score,
        "details": details,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 62)
    print(f"准确率：{passed}/{total} = {score:.1%}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

