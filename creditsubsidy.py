"""Utilities to load FHA credit subsidy rates from the OMB credit supplement."""

from __future__ import annotations

import io
import re
import urllib.request

import pandas as pd


DEFAULT_URL = "https://www.whitehouse.gov/wp-content/uploads/2026/04/cr_supp_fy2027.xlsx"


def _to_num(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    text = text.replace(",", "").replace("%", "")
    match = re.search(r"-?\d+\.?\d*", text)
    if not match:
        return None

    numeric_value = float(match.group(0))
    return -numeric_value if negative else numeric_value


def _parse_table8(xls: pd.ExcelFile, bio: io.BytesIO) -> pd.DataFrame:
    sheet_name = "Table8" if "Table8" in xls.sheet_names else next(
        (name for name in xls.sheet_names if "table8" in name.lower().replace(" ", "")),
        xls.sheet_names[0],
    )
    bio.seek(0)
    table_df = pd.read_excel(bio, sheet_name=sheet_name, header=None, dtype=str)

    header_row_index = 3
    if header_row_index >= len(table_df):
        raise ValueError(f"Sheet '{sheet_name}' does not contain row {header_row_index + 1} for headers")
    field_labels = [str(value).strip() if value is not None else "" for value in table_df.iloc[header_row_index].tolist()]

    mmif_row = next(
        (
            row_index
            for row_index in range(len(table_df))
            if any(isinstance(cell, str) and "mmi fund" in cell.lower() for cell in table_df.iloc[row_index].astype(str).tolist())
        ),
        None,
    )
    if mmif_row is None:
        raise ValueError(f"Could not find 'MMI Fund' in sheet {sheet_name}")

    collected_rows = []
    for row_index in range(mmif_row + 1, len(table_df)):
        row_values = table_df.iloc[row_index].astype(str).tolist()
        if any("mmi hecm" in str(cell).lower() for cell in row_values):
            break

        first_value = str(table_df.iat[row_index, 0]).strip() if table_df.shape[1] > 0 else ""
        if first_value.upper().startswith("FY"):
            cleaned_values = [value.strip() if isinstance(value, str) else value for value in table_df.iloc[row_index].tolist()]
            collected_rows.append(cleaned_values)

    if not collected_rows:
        raise ValueError("No 'FY' rows found after 'MMI Fund' in Table8")

    column_count = table_df.shape[1]
    normalized_rows = [
        row + [None] * (column_count - len(row)) if len(row) < column_count else row[:column_count]
        for row in collected_rows
    ]
    parsed_df = pd.DataFrame(normalized_rows)
    for column in parsed_df.columns[1:]:
        parsed_df[column] = pd.to_numeric(parsed_df[column].astype(str).str.replace(",", ""), errors="coerce")

    cleaned_labels = []
    for label in field_labels:
        normalized_label = str(label).replace("\n", "_").replace(" ", "_")
        while "__" in normalized_label:
            normalized_label = normalized_label.replace("__", "_")
        normalized_label = normalized_label.strip("_")
        cleaned_labels.append(normalized_label if normalized_label else "col")

    labels_padded = (
        cleaned_labels[:column_count]
        if len(cleaned_labels) >= column_count
        else cleaned_labels + [f"col_{index}" for index in range(len(cleaned_labels), column_count)]
    )

    parsed_df.columns = labels_padded
    parsed_df = parsed_df.rename(columns={parsed_df.columns[0]: "fiscal_year"})
    for row_index in range(len(parsed_df)):
        year_value = parsed_df.iat[row_index, 0]
        digits = "".join(re.findall(r"\d+", str(year_value))) if year_value is not None else ""
        parsed_df.iat[row_index, 0] = int(digits) if digits else None

    original_pattern = re.compile(r"original.*subsidy.*rate|subsidy.*rate", re.I)
    current_pattern = re.compile(r"current.*re-?estimated.*rate|re-?estimated.*rate|current.*rate", re.I)
    original_column = next((column for column in parsed_df.columns if original_pattern.search(column)), None)
    current_column = next((column for column in parsed_df.columns if current_pattern.search(column)), None)

    if original_column is None:
        original_column = next(
            (column for column in parsed_df.columns if "subsid" in column.lower() and "rate" in column.lower()),
            None,
        )
    if current_column is None:
        current_column = next(
            (column for column in parsed_df.columns if "estim" in column.lower() and "rate" in column.lower()),
            None,
        )

    if not original_column or not current_column:
        raise ValueError(f"Could not locate subsidy rate columns in Table8. Available: {list(parsed_df.columns)}")

    return parsed_df[["fiscal_year", original_column, current_column]].rename(
        columns={original_column: "original_subsidy_rate", current_column: "current_reestimated_rate"}
    )


def _parse_table2(xls: pd.ExcelFile, bio: io.BytesIO) -> pd.DataFrame:
    sheet_name = "Table2" if "Table2" in xls.sheet_names else next(
        (name for name in xls.sheet_names if "table2" in name.lower().replace(" ", "")),
        None,
    )
    if sheet_name is None:
        return pd.DataFrame(columns=["fiscal_year", "original_subsidy_rate", "current_reestimated_rate"])

    bio.seek(0)
    table_df = pd.read_excel(bio, sheet_name=sheet_name, header=None, dtype=str)
    mmif_row = next(
        (
            row_index
            for row_index in range(len(table_df))
            if any("mmi fund" in str(cell).lower() for cell in table_df.iloc[row_index].astype(str).tolist())
        ),
        None,
    )
    if mmif_row is None:
        return pd.DataFrame(columns=["fiscal_year", "original_subsidy_rate", "current_reestimated_rate"])

    rows = []
    for column_index in [5, 2]:
        if column_index >= table_df.shape[1]:
            continue

        found_value = None
        for offset in range(0, 11):
            candidate_rows = (mmif_row + offset, mmif_row - offset) if offset > 0 else (mmif_row,)
            for row_index in candidate_rows:
                if 0 <= row_index < len(table_df):
                    numeric_value = _to_num(table_df.iat[row_index, column_index])
                    if numeric_value is not None:
                        found_value = numeric_value
                        break
            if found_value is not None:
                break

        if found_value is None:
            continue

        fiscal_year_digits = None
        for row_index in [2, 3, 0, 1]:
            if 0 <= row_index < len(table_df):
                cell_value = table_df.iat[row_index, column_index]
                if cell_value and re.search(r"\d{4}", str(cell_value)):
                    fiscal_year_digits = "".join(re.findall(r"\d+", str(cell_value)))
                    break

        if fiscal_year_digits:
            projected_year = f"{int(fiscal_year_digits)} (P)"
            rows.append(
                {
                    "fiscal_year": projected_year,
                    "original_subsidy_rate": found_value,
                    "current_reestimated_rate": found_value,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["fiscal_year", "original_subsidy_rate", "current_reestimated_rate"])
    return pd.DataFrame(rows)


def load_credit_subsidy_data(url: str = DEFAULT_URL) -> pd.DataFrame:
    with urllib.request.urlopen(url) as response:
        raw_bytes = response.read()
    bio = io.BytesIO(raw_bytes)
    xls = pd.ExcelFile(bio)

    table8_df = _parse_table8(xls, bio)
    table2_df = _parse_table2(xls, bio)

    table8_df["fiscal_year"] = table8_df["fiscal_year"].astype(str)
    combined_df = pd.concat(
        [table8_df[["fiscal_year", "original_subsidy_rate", "current_reestimated_rate"]], table2_df],
        ignore_index=True,
    )
    combined_df = combined_df[combined_df["fiscal_year"].notnull()].copy()
    combined_df["fiscal_year"] = combined_df["fiscal_year"].map(
        lambda value: str(value).strip() if pd.notna(value) and str(value).strip() else None
    )
    combined_df = combined_df.dropna(subset=["fiscal_year"]).copy()
    combined_df["fiscal_year_sort"] = combined_df["fiscal_year"].str.replace(r" \(P\)$", "", regex=True)
    combined_df["fiscal_year_sort"] = pd.to_numeric(combined_df["fiscal_year_sort"], errors="coerce")
    combined_df = (
        combined_df.sort_values("fiscal_year_sort")
        .drop_duplicates(subset=["fiscal_year"], keep="first")
        .reset_index(drop=True)
    )
    return combined_df.drop(columns=["fiscal_year_sort"])


if __name__ == "__main__":
    output_df = load_credit_subsidy_data()
    print(output_df.tail(10).to_string(index=False))
