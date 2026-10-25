"""Load and process FHA endorsements data from fha_endorsements.xlsx tabs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = REPO_ROOT / "Data" / "Raw" / "fha_endorsements.xlsx"


def load_endorsements_data() -> dict[str, pd.DataFrame]:
    """Load all sheets from fha_endorsements.xlsx and return as a dict of DataFrames."""
    sheet_data = {}
    
    # Load each sheet by name
    excel_file = pd.ExcelFile(RAW_DATA_PATH)
    
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(RAW_DATA_PATH, sheet_name=sheet_name)
        sheet_data[sheet_name] = df
    
    return sheet_data


def prepare_endorsements_data() -> pd.DataFrame:
    """Load all endorsement sheets, standardize columns, and concatenate."""
    data = load_endorsements_data()
    dfs = []
    
    # yearbook1979: year, number -> count, source
    df_yearbook = data["yearbook1979"].copy()
    df_yearbook = df_yearbook.rename(columns={"number": "count"})
    df_yearbook = df_yearbook[["year", "count", "source"]]
    dfs.append(df_yearbook)
    
    # usmc2001: Unnamed: 0 -> year, count, source
    df_usmc = data["usmc2001"].copy()
    df_usmc = df_usmc.rename(columns={"Unnamed: 0": "year"})
    df_usmc = df_usmc[["year", "count", "source"]]
    dfs.append(df_usmc)
    
    # fha_marketshare: year, count, source
    df_market = data["fha_marketshare"].copy()
    df_market = df_market[["year", "count", "source"]]
    dfs.append(df_market)
    
    # Concatenate all sheets
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values("year").reset_index(drop=True)
    
    return combined


if __name__ == "__main__":
    combined_df = prepare_endorsements_data()
    
    print(f"\n{'='*60}")
    print("Combined Endorsements Data")
    print(f"{'='*60}")
    print(f"Shape: {combined_df.shape}")
    print(f"Year range: {combined_df['year'].min()} - {combined_df['year'].max()}")
    print(f"\nFirst 10 rows:")
    print(combined_df.head(10))
    print(f"\nLast 10 rows:")
    print(combined_df.tail(10))
    print(f"\nData types:")
    print(combined_df.dtypes)
    print(f"\nMissing values:")
    print(combined_df.isnull().sum())
    
    # Save to parquet
    output_path = REPO_ROOT / "Data" / "endorsements.parquet"
    combined_df.to_parquet(output_path, index=False)
    print(f"\nSaved to: {output_path}")


