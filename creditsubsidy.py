from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "creditsubsidy.parquet"


def load_credit_subsidy_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    df = pd.read_parquet(data_path).copy()

    df["fiscal_year"] = df["fiscal_year"].astype(str).str.replace(r" \(P\)$", "", regex=True)
    df["original_subsidy_rate"] = pd.to_numeric(df["original_subsidy_rate"], errors="coerce")
    df["current_reestimated_rate"] = pd.to_numeric(df["current_reestimated_rate"], errors="coerce")
    df["fiscal_year_sort"] = pd.to_numeric(df["fiscal_year"], errors="coerce")
    df = df.sort_values("fiscal_year_sort").drop_duplicates(subset=["fiscal_year"], keep="first").reset_index(drop=True)
    return df.drop(columns=["fiscal_year_sort"])


def build_creditsubsidy_figure(creditsubsidy_df: pd.DataFrame | None) -> go.Figure | None:
    if creditsubsidy_df is None or creditsubsidy_df.empty:
        return None

    plot_df = creditsubsidy_df.copy()
    plot_df["fiscal_year"] = plot_df["fiscal_year"].map(
        lambda value: str(value).strip() if pd.notna(value) and str(value).strip() else None
    )
    plot_df = plot_df.dropna(subset=["fiscal_year"]).copy()
    plot_df["fiscal_year_sort"] = pd.to_numeric(
        plot_df["fiscal_year"].str.replace(r" \(P\)$", "", regex=True),
        errors="coerce",
    )
    plot_df["current_reestimated_rate"] = pd.to_numeric(plot_df["current_reestimated_rate"], errors="coerce")
    plot_df["original_subsidy_rate"] = pd.to_numeric(plot_df["original_subsidy_rate"], errors="coerce")
    plot_df = plot_df.sort_values("fiscal_year_sort")
    plot_df = plot_df.dropna(subset=["current_reestimated_rate"])
    if plot_df.empty:
        return None

    fig = go.Figure()
    fig.add_bar(
        x=[str(value) for value in plot_df["fiscal_year"].tolist()],
        y=plot_df["current_reestimated_rate"].tolist(),
        name="Current Estimate",
        marker_color="#4c72b0",
        hovertemplate="FY=%{x}<br>Current=%{y:,.2f}%<extra></extra>",
    )

    original_mask = plot_df["original_subsidy_rate"].notna()
    if original_mask.any():
        fig.add_scatter(
            x=[str(value) for value in plot_df.loc[original_mask, "fiscal_year"].tolist()],
            y=plot_df.loc[original_mask, "original_subsidy_rate"].tolist(),
            mode="markers",
            name="Original Estimate",
            marker={"color": "#93c5fd", "size": 8, "symbol": "circle"},
            hovertemplate="FY=%{x}<br>Original=%{y:,.2f}%<extra></extra>",
        )

    fig.update_layout(
        title={"text": "", "x": 0.03},
        height=420,
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "left",
            "x": 0,
        },
    )
    fig.update_xaxes(title_text="Book of Business", tickangle=90)
    fig.update_yaxes(title_text="Percent")
    fig.add_hline(y=0, line_dash="solid", line_color="#374151", line_width=1.25)
    return fig


if __name__ == "__main__":
    creditsubsidy_df = load_credit_subsidy_data()
    creditsubsidy_fig = build_creditsubsidy_figure(creditsubsidy_df)

