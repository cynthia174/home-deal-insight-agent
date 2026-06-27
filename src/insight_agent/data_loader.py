from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO
import warnings

import pandas as pd

from .schema import COLUMN_ALIASES, DATE_COLUMNS, NUMERIC_COLUMNS, REQUIRED_COLUMNS


class DataValidationError(ValueError):
    """A friendly, user-facing data validation error."""


def _read_tabular(source: str | Path | bytes | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    inferred_name = filename or (str(source) if isinstance(source, (str, Path)) else "")
    suffix = Path(inferred_name).suffix.lower()
    payload = BytesIO(source) if isinstance(source, bytes) else source

    if suffix in {".csv", ".tsv"}:
        separator = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(payload, sep=separator, encoding="utf-8-sig")
    if suffix in {".xlsx", ".xls"}:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unknown extension is not supported.*")
            warnings.filterwarnings("ignore", message="Conditional Formatting extension is not supported.*")
            book = pd.ExcelFile(payload)
            sheet = "签约明细" if "签约明细" in book.sheet_names else book.sheet_names[0]
            return pd.read_excel(book, sheet_name=sheet)
    raise DataValidationError("只支持 .xlsx、.xls、.csv 或 .tsv 文件。")


def normalize_business_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if raw.empty:
        raise DataValidationError("数据表是空的，请换一份包含业务明细的文件。")

    df = raw.copy()
    df.columns = [str(col).strip() for col in df.columns]
    repairs: list[str] = []

    rename_map = {
        col: COLUMN_ALIASES[col]
        for col in df.columns
        if col in COLUMN_ALIASES and COLUMN_ALIASES[col] not in df.columns
    }
    if rename_map:
        df = df.rename(columns=rename_map)
        repairs.extend([f"识别字段别名：{old} → {new}" for old, new in rename_map.items()])

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(
            "数据缺少关键字段："
            + "、".join(missing)
            + "。可接受常见别名，例如“合同金额”会自动识别为“签约额”。"
        )

    for col in DATE_COLUMNS:
        if col in df.columns:
            before = int(df[col].notna().sum())
            df[col] = pd.to_datetime(df[col], errors="coerce")
            lost = before - int(df[col].notna().sum())
            if lost:
                repairs.append(f"{col} 有 {lost} 个无法识别的日期，已安全置为空值")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            original_non_null = int(df[col].notna().sum())
            if df[col].dtype == object:
                cleaned = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("¥", "", regex=False)
                    .str.replace("￥", "", regex=False)
                    .str.replace("元", "", regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(cleaned, errors="coerce")
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            lost = original_non_null - int(df[col].notna().sum())
            if lost:
                repairs.append(f"{col} 有 {lost} 个异常数字，已忽略并继续分析")

    if "毛利额" not in df.columns and {"签约额", "预计成本"}.issubset(df.columns):
        df["毛利额"] = df["签约额"] - df["预计成本"]
        repairs.append("缺少毛利额，已按“签约额 - 预计成本”自动补算")

    df["签约年份"] = df["签约日期"].dt.year.astype("Int64")
    df["签约月份"] = df["签约日期"].dt.strftime("%Y-%m")
    df["签约季度"] = (
        df["签约日期"].dt.year.astype("Int64").astype(str)
        + "-Q"
        + df["签约日期"].dt.quarter.astype("Int64").astype(str)
    )
    df["有效签约"] = ~df["合同状态"].astype(str).str.contains("取消|作废|退单", regex=True, na=False)

    return df, repairs


def load_business_data(
    source: str | Path | bytes | BinaryIO,
    filename: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    return normalize_business_data(_read_tabular(source, filename=filename))
