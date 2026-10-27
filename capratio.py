from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "capratio.parquet"


def load_capratio_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    df = pd.read_parquet(data_path).copy()

    if "cap_ratio" not in df.columns and {"capital", "value", "ratio"}.issubset(df.columns):
        df["cap_ratio"] = 100 * df["capital"] / (df["value"] / (df["ratio"] / 100))

    if (
        "cap_ratio_unamort" not in df.columns
        and "iif_unamort" in df.columns
        and "ratio" in df.columns
        and "capital" in df.columns
    ):
        df["cap_ratio_unamort"] = 100 * df["capital"] / (df["iif_unamort"] / (df["ratio"] / 100))

    return df


def get_adjusted_y_axis_title() -> str:
    return f"{datetime.now(timezone.utc).year} Dollars, Billions"


def get_adjusted_y_range(capratio_df: pd.DataFrame) -> list[float] | None:
    adjusted_columns = [
        column
        for column in [
            "econ_value_in_latest_dollars",
            "cap_resources_in_latest_dollars",
            "cashflow_npv_in_latest_dollars",
        ]
        if column in capratio_df.columns
    ]
    if not adjusted_columns:
        return None

    values = pd.to_numeric(
        capratio_df[adjusted_columns].stack(),
        errors="coerce",
    ).dropna()
    if values.empty:
        return None

    min_value = min(float(values.min()), 0.0)
    max_value = max(float(values.max()), 0.0)
    span = max_value - min_value
    padding = span * 0.05 if span else 1.0
    return [min_value - padding, max_value + padding]


def _apply_figure_layout(
    fig: go.Figure,
    *,
    y_axis_title: str,
    x_axis_title: str = "Year",
    y_axis_range: list[float] | None = None,
    height: int = 360,
) -> go.Figure:
    fig.update_layout(
        title={"text": "", "x": 0.03},
        height=height,
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
    fig.update_xaxes(title_text=x_axis_title)
    fig.update_yaxes(title_text=y_axis_title)
    if y_axis_range is not None:
        fig.update_yaxes(range=y_axis_range)
    fig.add_hline(y=0, line_dash="solid", line_color="#374151", line_width=1.25)
    return fig


def build_capital_ratio_figure(capratio_df: pd.DataFrame) -> go.Figure | None:
    metrics = [column for column in ["cap_ratio", "cap_ratio_unamort"] if column in capratio_df.columns]
    if not metrics:
        return None

    plot_df = capratio_df.melt(
        id_vars=["year", "source"],
        value_vars=metrics,
        var_name="metric",
        value_name="value",
    ).dropna(subset=["year", "value"])

    plot_df["metric"] = plot_df["metric"].replace(
        {
            "cap_ratio": "Amortized IIF",
            "cap_ratio_unamort": "Unamortized IIF",
        }
    )
    plot_df["value"] = plot_df["value"] * 100

    fig = px.line(
        plot_df.sort_values(["source", "metric", "year"]),
        x="year",
        y="value",
        color="source",
        line_dash="metric",
        line_dash_map={
            "Amortized IIF": "solid",
            "Unamortized IIF": "dash",
        }
    )
    
    # Hide metric traces from legend, keep only source
    for trace in fig.data:
        trace.showlegend = True
        # Extract source name (it's the trace name)
        # Plotly creates names like "source_value, metric_value"
        # We want to keep only the source part
        parts = trace.name.split(", ")
        if len(parts) == 2:
            trace.name = parts[0]
    
    fig.update_traces(hovertemplate="Year=%{x}<br>Value=%{y:,.2f}<extra></extra>")
    return _apply_figure_layout(fig, y_axis_title="Percent", height=560)


def build_adjusted_figure(
    capratio_df: pd.DataFrame,
    metric_column: str,
    y_axis_title: str,
    y_axis_range: list[float] | None,
) -> go.Figure | None:
    if metric_column not in capratio_df.columns:
        return None

    plot_df = capratio_df[["year", "source", metric_column]].dropna().rename(columns={metric_column: "value"})
    if plot_df.empty:
        return None

    fig = px.line(
        plot_df.sort_values(["source", "year"]),
        x="year",
        y="value",
        color="source",
    )
    fig.update_traces(hovertemplate="Year=%{x}<br>Value=%{y:,.0f}<br>Source=%{fullData.name}<extra></extra>")
    return _apply_figure_layout(
        fig,
        y_axis_title=y_axis_title,
        y_axis_range=y_axis_range,
    )


if __name__ == "__main__":
    capratio_df = load_capratio_data()
    adjusted_y_axis_title = get_adjusted_y_axis_title()
    adjusted_y_axis_range = get_adjusted_y_range(capratio_df)

    capital_ratio_fig = build_capital_ratio_figure(capratio_df)
    econ_value_fig = build_adjusted_figure(
        capratio_df,
        "econ_value_in_latest_dollars",
        adjusted_y_axis_title,
        adjusted_y_axis_range,
    )
    cap_resources_fig = build_adjusted_figure(
        capratio_df,
        "cap_resources_in_latest_dollars",
        adjusted_y_axis_title,
        adjusted_y_axis_range,
    )
    cashflow_fig = build_adjusted_figure(
        capratio_df,
        "cashflow_npv_in_latest_dollars",
        adjusted_y_axis_title,
        adjusted_y_axis_range,
    )

