"""Loader and validator for raw cap ratio Excel workbook.

Reads each sheet from Data/Raw/raw_cap_ratio.xlsx into a cleaned
in-memory pandas DataFrame and returns a dict of DataFrames.

This module intentionally does not persist outputs; set `persist=True`
behavior can be added later if desired.
"""
#%%
from __future__ import annotations
from typing import Dict, Any
import re
from pathlib import Path
import pandas as pd
import numpy as np
import os
from fredapi import Fred

#%%

_SENTINEL_STRINGS = {"na", "n/a", "-", ""}


def _sanitize_sheet_name(name: str) -> str:
    name = name.strip()
    name = name.lower()
    name = re.sub(r"[^0-9a-z]+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name or "sheet"


def _sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: re.sub(r"\s+", "_", str(c).strip()))
    df = df.rename(columns=lambda c: re.sub(r"[^0-9A-Za-z_]+", "", c))
    return df


def _standardize_missing(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace({None: pd.NA})
    # Replace common sentinel strings (case-insensitive)
    df = df.applymap(lambda v: pd.NA if isinstance(v, str) and v.strip().lower() in _SENTINEL_STRINGS else v)
    return df


def _coerce_column_types(df: pd.DataFrame) -> pd.DataFrame:
    # Try to coerce obvious numeric columns
    for col in df.columns:
        ser = df[col]
        # Skip if already numeric or datetime
        if pd.api.types.is_numeric_dtype(ser) or pd.api.types.is_datetime64_any_dtype(ser):
            continue

        # Heuristic: if >75% of non-null values parse as numeric, coerce
        non_null = ser.dropna().astype(str).str.strip()
        if len(non_null) == 0:
            continue
        num_parsable = non_null.str.match(r"^-?\d+(?:\.\d+)?$").sum()
        if num_parsable / len(non_null) >= 0.75:
            df[col] = pd.to_numeric(ser, errors="coerce")
            continue

        # Heuristic: column name contains date
        if "date" in col.lower() or "year" in col.lower():
            try:
                df[col] = pd.to_datetime(ser, errors="coerce")
            except Exception:
                pass

    return df


def load_raw_cap_ratio(path: str | Path | None = None) -> Dict[str, pd.DataFrame]:
    """Read all sheets from the workbook and return a dict of cleaned DataFrames.

    Parameters
    - path: path to the workbook (default: Data/Raw/raw_cap_ratio.xlsx)

    Returns a dict mapping sanitized sheet names to pandas DataFrames.
    """
    if path is None:
        # Default to the workbook located in the same Data folder as this module
        path = Path(__file__).resolve().parent / "Raw" / "raw_cap_ratio.xlsx"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    xls = pd.ExcelFile(path)
    sheets = xls.sheet_names

    dfs: Dict[str, pd.DataFrame] = {}
    for raw_name in sheets:
        key = _sanitize_sheet_name(raw_name)
        df = pd.read_excel(xls, sheet_name=raw_name)

        # Clean structure
        df = df.copy()
        df = _sanitize_columns(df)
        df = df.dropna(axis=0, how="all")
        df = df.dropna(axis=1, how="all")
        df = _standardize_missing(df)
        df = _coerce_column_types(df)

        dfs[key] = df

    return dfs


def validate_sheets(dfs: Dict[str, pd.DataFrame]) -> None:
    """Run quick validations and raise ValueError on critical failures.

    Current checks:
    - At least one sheet present
    - No sheet is completely empty
    """
    if not dfs:
        raise ValueError("No sheets loaded from workbook (empty or missing file).")

    empty_sheets = [k for k, v in dfs.items() if v.shape[0] == 0 or v.shape[1] == 0]
    if empty_sheets:
        raise ValueError(f"The following sheets are empty after cleaning: {empty_sheets}")


def summarize_sheets(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Return a compact summary (counts and dtypes) for each sheet."""
    summary: Dict[str, Any] = {}
    for k, df in dfs.items():
        summary[k] = {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "sample_head": df.head(3).to_dict(orient="records"),
        }
    return summary


def combine_sheets(dfs: Dict[str, pd.DataFrame], sheet_col: str = "sheet_name") -> pd.DataFrame:
    """Concatenate all sheet DataFrames into one DataFrame.

    - Adds a column (default `sheet_name`) containing the source sheet key.
    - Preserves all columns (union) and fills missing cells with NA.
    """
    if not dfs:
        return pd.DataFrame()

    def _map_source_from_sheet(sheet_key: str) -> str | None:
        k = sheet_key.lower()
        if "annual" in k:
            return "Annual Reports"
        if "actuarial" in k:
            return "Actuarial Reviews"
        if "szymanoski" in k:
            return "Szymanoski et al. (2012)"
        return None

    parts = []
    for name, df in dfs.items():
        # shallow copy to avoid mutating original
        part = df.copy()
        part[sheet_col] = name
        src = _map_source_from_sheet(name)
        if src is not None:
            part["source"] = src
        parts.append(part)

    combined = pd.concat(parts, ignore_index=True, sort=False)
    return combined


try:
    get_ipython  # type: ignore
    _in_ipython = True
except NameError:
    _in_ipython = False

# When run in an interactive IPython session (Interactive Window) or as a script,
# perform an inline load so `dfs` is available in the session namespace.
if _in_ipython or __name__ == "__main__":
    try:
        dfs = load_raw_cap_ratio()
    except FileNotFoundError as e:
        print(e)
        dfs = {}
    else:
        try:
            validate_sheets(dfs)
        except ValueError as e:
            print(f"Validation warning/failure: {e}")

    if dfs:
        s = summarize_sheets(dfs)
        for k, v in s.items():
            print(f"Sheet: {k} — rows={v['rows']} cols={v['cols']}")

df=combine_sheets(dfs).rename(columns={'fiscal_year': 'year'})
df['year'] = pd.to_numeric(df['year'], errors='coerce')
df = df.sort_values(by=['source', 'year'], ascending=[True, True]).reset_index(drop=True)

#%%

# Fetch CPI-like series (PCEPI) from FRED and build year->factor mapping
try:
    fred = Fred(api_key=os.getenv("FRED_API_KEY"))  # requires FRED_API_KEY env var
    s = fred.get_series("PCEPI")
    s = s.dropna()
    latest_value = float(s.iloc[-1])

    # use September observation for each year
    sept = s[s.index.month == 9]
    sept_by_year = sept.groupby(sept.index.year).last().astype(float)

    factor_by_year = (latest_value / sept_by_year).to_dict()
    # Map factors to dataframe years (keep NA where year missing or unmatched)
    df['year_int'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
    df['inflation_factor'] = df['year_int'].map(lambda y: factor_by_year.get(int(y)) if pd.notna(y) else pd.NA)
except Exception as e:
    # If FRED fetch fails, leave inflation_factor null and report
    df['inflation_factor'] = pd.NA
    print(f"Warning: failed to fetch PCEPI from FRED: {e}")

# Ensure `cashflow_npv` exists where possible
if 'cashflow_npv' not in df.columns:
    if {'revenue_pv', 'loss_pv'}.issubset(df.columns):
        df['cashflow_npv'] = df['revenue_pv'] - df['loss_pv']
    else:
        df['cashflow_npv'] = pd.NA

# Adjust numeric columns into latest-dollar equivalents using the inflation factor
to_adjust = [c for c in ['econ_value', 'cap_resources', 'cashflow_npv'] if c in df.columns]
for col in to_adjust:
    df[f"{col}_in_latest_dollars"] = df[col] * df['inflation_factor']

# Data-quality summary
n_missing = int(df['inflation_factor'].isna().sum())
print(f"Inflation factor missing for {n_missing} rows")
if to_adjust:
    created = [f"{c}_in_latest_dollars" for c in to_adjust]
    print(f"Created adjusted columns: {created}")

# tidy helper column
if 'year_int' in df.columns:
    df = df.drop(columns=['year_int'])

#%%
# persist combined result to Data/capratio.parquet
out_path = Path(__file__).resolve().parent / "capratio.parquet"
try:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"Saved capratio parquet to {out_path}")
except Exception as e:
    print(f"Failed to save capratio.parquet: {e}")

# %%
