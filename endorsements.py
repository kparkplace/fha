from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "endorsements.parquet"


def load_endorsements_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    return pd.read_parquet(data_path).copy()


def build_endorsements_figure(endorsements_df: pd.DataFrame | None) -> go.Figure | None:
    if endorsements_df is None or endorsements_df.empty:
        return None

    plot_df = endorsements_df.copy()
    plot_df = plot_df.dropna(subset=["year", "count"]).sort_values(["source", "year"])

    # Group by year, take max count per year, then sum
    max_by_year = plot_df.groupby("year")["count"].max().reset_index()
    total_count = max_by_year["count"].sum()
    max_year = max_by_year["year"].max()

    # Color map: capratio-inspired with FHA sources in two shades
    color_map = {
        "Statistical Yearbook 1979": "#1f77b4",  # Blue
        "US Housing Market Conditions Historical Data Winter 2001": "#ff7f0e",  # Orange
        "FHA-Insured Single-Family Mortgage Originations and Market Share Report 2019Q4": "#d62728",  # Red (darker)
        "FHA-Insured Single-Family Mortgage Originations and Market Share Report 2025Q4": "#ff9999",  # Red (lighter shade)
    }

    # Extract year from source name and sort
    def extract_year(source: str) -> int:
        import re
        match = re.search(r"\b(19|20)\d{2}\b", source)
        return int(match.group()) if match else 9999

    sorted_sources = sorted(plot_df["source"].unique(), key=extract_year)

    fig = go.Figure()

    for source in sorted_sources:
        df_source = plot_df[plot_df["source"] == source]
        fig.add_trace(
            go.Scatter(
                x=df_source["year"],
                y=df_source["count"],
                mode="lines",
                name=source,
                line={"color": color_map[source], "width": 2},
                hovertemplate="Year=%{x}<br>Count=%{y:,}<br>Source=%{fullData.name}<extra></extra>",
            )
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
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text="Number of Endorsements")
    fig.add_hline(y=0, line_dash="solid", line_color="#374151", line_width=1.25)
    
    # Add text annotation in top left corner
    fig.add_annotation(
        text=f"{total_count:,} through {max_year}",
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.98,
        showarrow=False,
        font={"size": 12, "color": "#1e293b"},
        xanchor="left",
        yanchor="top",
    )
    
    return fig



if __name__ == "__main__":
    endorsements_df = load_endorsements_data()
    fig = build_endorsements_figure(endorsements_df)
    if fig is not None:
        fig.show()
