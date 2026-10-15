
from __future__ import annotations

from pathlib import Path

import pandas as pd

#%%
REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "creditsubsidy.parquet"

#%%
def load_credit_subsidy_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    df = pd.read_parquet(data_path)
    df = df.copy()
    df["fiscal_year"] = df["fiscal_year"].astype(str).str.replace(r" \(P\)$", "", regex=True)
    df["original_subsidy_rate"] = pd.to_numeric(df["original_subsidy_rate"], errors="coerce")
    df["current_reestimated_rate"] = pd.to_numeric(df["current_reestimated_rate"], errors="coerce")
    df["fiscal_year_sort"] = df["fiscal_year"].str.replace(r" \(P\)$", "", regex=True)
    df["fiscal_year_sort"] = pd.to_numeric(df["fiscal_year_sort"], errors="coerce")
    df = df.sort_values("fiscal_year_sort").drop_duplicates(subset=["fiscal_year"], keep="first").reset_index(drop=True)
    return df.drop(columns=["fiscal_year_sort"])

#%%
combined_df = load_credit_subsidy_data()

#%%
plot_df = combined_df.copy()
plot_df["fiscal_year"] = plot_df["fiscal_year"].astype(str).str.replace(r" \(P\)$", "", regex=True)
plot_df["fiscal_year_sort"] = pd.to_numeric(plot_df["fiscal_year"], errors="coerce")
plot_df = plot_df.sort_values("fiscal_year_sort").copy()
plot_df = plot_df[plot_df["current_reestimated_rate"].notnull()].reset_index(drop=True)
plot_df["fy_str"] = plot_df["fiscal_year"].astype(str)
plot_df["_x"] = plot_df.index.astype(float)
plot_df["estimate_type"] = "current"

marks_df = plot_df[plot_df["original_subsidy_rate"].notnull()].copy()
marks_df["estimate_type"] = "original"
marks_df["_x_min"] = marks_df["_x"] - 0.2
marks_df["_x_max"] = marks_df["_x"] + 0.2

#%%
try:
    from plotnine import (
        aes,
        element_blank,
        element_text,
        geom_col,
        geom_segment,
        ggplot,
        labs,
        scale_color_manual,
        scale_fill_manual,
        scale_x_continuous,
        theme,
        theme_classic,
    )

    combined_plot = (
        ggplot(plot_df, aes(x="_x", y="current_reestimated_rate"))
        + geom_col(aes(fill="estimate_type"), width=0.8)
        + geom_segment(
            data=marks_df,
            mapping=aes(
                x="_x_min",
                xend="_x_max",
                y="original_subsidy_rate",
                yend="original_subsidy_rate",
                color="estimate_type",
            ),
            size=1.25,
            show_legend=True,
        )
        + scale_fill_manual(
            values={"current": "#4c72b0", "original": "#add8e6"},
            labels={"current": "Current Estimate", "original": "Original Estimate"},
        )
        + scale_color_manual(
            values={"current": "#4c72b0", "original": "#add8e6"},
            labels={"current": "Current Estimate", "original": "Original Estimate"},
        )
        + scale_x_continuous(breaks=plot_df["_x"].tolist(), labels=plot_df["fy_str"].tolist())
        + labs(x="Book of Business", y="Credit Subsidy Rate (%)", caption="Source: Office of Management and Budget")
        + theme_classic()
        + theme(
            axis_text_x=element_text(rotation=90, hjust=1),
            legend_position="bottom",
            legend_title=element_blank(),
        )
    )
except Exception:
    combined_plot = None

#%%
if __name__ == "__main__":
    print(combined_df.head().to_string(index=False))
    if combined_plot is not None:
        print(combined_plot)
