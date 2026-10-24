"""Build Data/capratio.parquet from Data/Raw/raw_cap_ratio.xlsx."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
from fredapi import Fred


OUTPUT_PATH = Path(__file__).resolve().parent / "capratio.parquet"


def build_capratio_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    workbook_path = Path(path) if path is not None else Path(__file__).resolve().parent / "Raw" / "raw_cap_ratio.xlsx"
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    xls = pd.ExcelFile(workbook_path)
    parts: list[pd.DataFrame] = []

    for raw_name in xls.sheet_names:
        sheet_key = re.sub(r"_+", "_", re.sub(r"[^0-9a-z]+", "_", raw_name.strip().lower())).strip("_") or "sheet"
        part = pd.read_excel(xls, sheet_name=raw_name).copy()
        part = part.rename(columns=lambda c: re.sub(r"[^0-9A-Za-z_]+", "", re.sub(r"\s+", "_", str(c).strip())))
        part = part.dropna(axis=0, how="all").dropna(axis=1, how="all")
        for col in part.columns:
            if part[col].dtype == "object":
                part[col] = part[col].map(lambda v: pd.NA if isinstance(v, str) and v.strip().lower() in {"na", "n/a", "-", ""} else v)
        part["sheet_name"] = sheet_key
        if "annual" in sheet_key:
            part["source"] = "Annual Reports"
        elif "actuarial" in sheet_key:
            part["source"] = "Actuarial Reviews"
        elif "szymanoski" in sheet_key:
            part["source"] = "Szymanoski et al. (2012)"
        parts.append(part)

    if not parts:
        raise ValueError("No sheets loaded from workbook.")

    df = pd.concat(parts, ignore_index=True, sort=False).rename(columns={"fiscal_year": "year"})
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError("Combined capratio dataframe is empty after cleaning.")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.sort_values(by=["source", "year"], ascending=[True, True]).reset_index(drop=True)

    try:
        fred_api_key = (os.getenv("FRED_API_KEY") or "").strip()
        if not fred_api_key:
            env_candidates = [
                Path(__file__).resolve().parents[1] / ".env",
                Path(__file__).resolve().parents[2] / ".env",
            ]
            for env_path in env_candidates:
                if not env_path.exists():
                    continue
                for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "FRED_API_KEY":
                        fred_api_key = value.strip().strip('"').strip("'")
                        break
                if fred_api_key:
                    break
        if not fred_api_key:
            raise RuntimeError("FRED_API_KEY is not set")

        fred = Fred(api_key=fred_api_key)
        pcepi = fred.get_series("PCEPI").dropna()
        latest_value = float(pcepi.iloc[-1])
        sept = pcepi[pcepi.index.month == 9]
        sept_by_year = sept.groupby(sept.index.year).last().astype(float)
        factor_by_year = (latest_value / sept_by_year).to_dict()

        df["year_int"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["inflation_factor"] = df["year_int"].map(lambda y: factor_by_year.get(int(y)) if pd.notna(y) else pd.NA)
    except Exception as exc:
        exc_text = str(exc).strip()
        if "syntax error: line 1, column 0" in exc_text:
            raise RuntimeError(
                "Failed to fetch PCEPI from FRED because the response was not valid API XML/JSON. "
                "This can happen when the API key is invalid, network access is blocked, or the FRED site is in maintenance mode."
            ) from exc
        if "FRED_API_KEY is not set" in exc_text:
            raise RuntimeError("Failed to fetch PCEPI from FRED because FRED_API_KEY is not set.") from exc
        raise RuntimeError(f"Failed to fetch PCEPI from FRED: {exc_text}") from exc

    if "cashflow_npv" not in df.columns:
        if {"revenue_pv", "loss_pv"}.issubset(df.columns):
            df["cashflow_npv"] = df["revenue_pv"] - df["loss_pv"]
        else:
            df["cashflow_npv"] = pd.NA

    for col in [c for c in ["econ_value", "cap_resources", "cashflow_npv"] if c in df.columns]:
        df[f"{col}_in_latest_dollars"] = df[col] * df["inflation_factor"]

    print(f"Inflation factor missing for {int(df['inflation_factor'].isna().sum())} rows")
    if "year_int" in df.columns:
        df = df.drop(columns=["year_int"])
    return df


def main() -> None:
    df = build_capratio_dataframe()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved capratio parquet to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
