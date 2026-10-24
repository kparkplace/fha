"""Build Data/creditsubsidy.parquet from the OMB credit supplement workbook."""

from __future__ import annotations

import io
import re
import urllib.request
from pathlib import Path

import pandas as pd


URL = "https://www.whitehouse.gov/wp-content/uploads/2026/04/cr_supp_fy2027.xlsx"
OUTPUT_PATH = Path(__file__).resolve().parent / "creditsubsidy.parquet"


def build_credit_subsidy_dataframe(url: str = URL) -> pd.DataFrame:
    with urllib.request.urlopen(url) as response:
        raw_bytes = response.read()

    bio = io.BytesIO(raw_bytes)
    xls = pd.ExcelFile(bio)
    sheet_name = "Table8" if "Table8" in xls.sheet_names else next(
        (name for name in xls.sheet_names if "table8" in name.lower().replace(" ", "")),
        xls.sheet_names[0],
    )
    bio.seek(0)
    table8 = pd.read_excel(bio, sheet_name=sheet_name, header=None, dtype=str)

    header_row = 3
    field_labels = [str(value).strip() if value is not None else "" for value in table8.iloc[header_row].tolist()]
    mmif_row = next(
        (i for i, row in enumerate(table8.values) if any("mmi fund" in str(cell).lower() for cell in row)),
        None,
    )
    if mmif_row is None:
        raise ValueError(f"Could not find 'MMI Fund' in sheet {sheet_name}")

    rows = []
    for row_index in range(mmif_row + 1, len(table8)):
        row_values = table8.iloc[row_index].tolist()
        if any("mmi hecm" in str(cell).lower() for cell in row_values):
            break
        if str(row_values[0]).strip().upper().startswith("FY"):
            rows.append([None if value is None else str(value).strip() for value in row_values])

    if not rows:
        raise ValueError("No FY rows found in Table8")

    table8_df = pd.DataFrame(rows)
    column_count = max(table8_df.shape[1], len(field_labels))
    cleaned_labels = [str(label).replace("\n", "_").replace(" ", "_") for label in field_labels]
    cleaned_labels = [re.sub(r"_+", "_", label).strip("_") or "col" for label in cleaned_labels]
    cleaned_labels = cleaned_labels[:column_count]
    if len(cleaned_labels) < column_count:
        cleaned_labels = cleaned_labels + [f"col_{i}" for i in range(len(cleaned_labels), column_count)]
    table8_df = table8_df.reindex(columns=range(column_count), fill_value=None)
    table8_df.columns = cleaned_labels
    table8_df = table8_df.rename(columns={table8_df.columns[0]: "fiscal_year"})

    for col in table8_df.columns[1:]:
        table8_df[col] = pd.to_numeric(
            table8_df[col].astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
            errors="coerce",
        )

    table8_df["fiscal_year"] = table8_df["fiscal_year"].astype(str)
    fy_digits = table8_df["fiscal_year"].str.findall(r"\d+").str.join("")
    has_digits = fy_digits != ""
    table8_df.loc[has_digits, "fiscal_year"] = fy_digits.loc[has_digits].astype(int).astype(str) 

    original_pattern = re.compile(r"original.*subsidy.*rate|subsidy.*rate", re.I)
    current_pattern = re.compile(r"current.*re-?estimated.*rate|re-?estimated.*rate|current.*rate", re.I)
    original_column = next((col for col in table8_df.columns if original_pattern.search(str(col))), None)
    current_column = next((col for col in table8_df.columns if current_pattern.search(str(col))), None)
    if original_column is None:
        original_column = next((col for col in table8_df.columns if "subsid" in str(col).lower() and "rate" in str(col).lower()), None)
    if current_column is None:
        current_column = next((col for col in table8_df.columns if "estim" in str(col).lower() and "rate" in str(col).lower()), None)
    if original_column is None or current_column is None:
        raise ValueError(f"Could not locate subsidy rate columns in Table8: {list(table8_df.columns)}")

    table8_df = table8_df[["fiscal_year", original_column, current_column]].rename(
        columns={original_column: "original_subsidy_rate", current_column: "current_reestimated_rate"}
    )

    bio = io.BytesIO(raw_bytes)
    xls = pd.ExcelFile(bio)
    sheet_name = "Table2" if "Table2" in xls.sheet_names else next(
        (name for name in xls.sheet_names if "table2" in name.lower().replace(" ", "")),
        None,
    )
    table2_df = pd.DataFrame(columns=["fiscal_year", "original_subsidy_rate", "current_reestimated_rate"])
    if sheet_name is not None:
        bio.seek(0)
        table2 = pd.read_excel(bio, sheet_name=sheet_name, header=None, dtype=str)
        mmif_row = next(
            (i for i, row in enumerate(table2.values) if any("mmi fund" in str(cell).lower() for cell in row)),
            None,
        )
        if mmif_row is not None:
            table2_rows = []
            for column_index in [5, 2]:
                if column_index >= table2.shape[1]:
                    continue
                found_value = None
                for offset in range(0, 11):
                    candidates = (mmif_row + offset, mmif_row - offset) if offset > 0 else (mmif_row,)
                    for row_index in candidates:
                        if 0 <= row_index < len(table2):
                            text = str(table2.iat[row_index, column_index]).strip()
                            if not text:
                                continue
                            match = re.search(r"-?\d+\.?\d*", text.replace(",", "").replace("%", ""))
                            if match:
                                found_value = float(match.group(0))
                                break
                    if found_value is not None:
                        break
                if found_value is None:
                    continue

                year_value = None
                for row_index in [2, 3, 0, 1]:
                    if 0 <= row_index < len(table2):
                        cell = table2.iat[row_index, column_index]
                        if cell and re.search(r"\d{4}", str(cell)):
                            year_value = str(cell).strip()
                            break

                if year_value is not None:
                    table2_rows.append(
                        {
                            "fiscal_year": year_value,
                            "original_subsidy_rate": found_value,
                            "current_reestimated_rate": found_value,
                        }
                    )
            if table2_rows:
                table2_df = pd.DataFrame(table2_rows)

    combined_df = pd.concat([table8_df, table2_df], ignore_index=True)
    combined_df = combined_df[combined_df["fiscal_year"].notnull()].copy()
    combined_df["fiscal_year"] = combined_df["fiscal_year"].astype(str).str.strip()
    combined_df = combined_df.dropna(subset=["fiscal_year"]).copy()
    combined_df["fiscal_year_sort"] = combined_df["fiscal_year"].str.replace(r" \(P\)$", "", regex=True)
    combined_df["fiscal_year_sort"] = pd.to_numeric(combined_df["fiscal_year_sort"], errors="coerce")
    combined_df = combined_df.sort_values("fiscal_year_sort").drop_duplicates(subset=["fiscal_year"], keep="first").reset_index(drop=True)
    combined_df = combined_df.drop(columns=["fiscal_year_sort"])
    combined_df["original_subsidy_rate"] = pd.to_numeric(combined_df["original_subsidy_rate"], errors="coerce")
    combined_df["current_reestimated_rate"] = pd.to_numeric(combined_df["current_reestimated_rate"], errors="coerce")
    return combined_df


def main() -> None:
    combined_df = build_credit_subsidy_dataframe()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved credit subsidy data to {OUTPUT_PATH}")
    print(combined_df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
