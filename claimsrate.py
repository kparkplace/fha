from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"


def load_claims_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path

    claims_df = pd.read_parquet(data_path).copy()
    if "metric" in claims_df.columns:
        claims_df = claims_df[claims_df["metric"] == "cum_clm_rate"].copy()

    claims_df["cohort"] = pd.to_numeric(claims_df["cohort"], errors="coerce")
    claims_df["year"] = pd.to_numeric(claims_df["year"], errors="coerce")
    claims_df["sourcefy"] = pd.to_numeric(claims_df["sourcefy"], errors="coerce")
    claims_df["value"] = pd.to_numeric(claims_df["value"], errors="coerce")
    return claims_df


def _apply_figure_layout(
    fig: go.Figure,
    *,
    y_axis_title: str,
    x_axis_title: str,
    legend_title: str | None = None,
    height: int = 420,
    legend_orientation: str = "h",
    legend_y: float = -0.2,
    legend_x: float = 0.0,
) -> go.Figure:
    fig.update_layout(
        title={"text": "", "x": 0.03},
        height=height,
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
        legend_title_text=legend_title,
        legend={
            "orientation": legend_orientation,
            "yanchor": "top",
            "y": legend_y,
            "xanchor": "left",
            "x": legend_x,
        },
    )
    fig.update_xaxes(title_text=x_axis_title)
    fig.update_yaxes(title_text=y_axis_title)
    fig.add_hline(y=0, line_dash="solid", line_color="#374151", line_width=1.25)
    return fig


def build_claims_stack_figure(claims_df: pd.DataFrame) -> go.Figure | None:
    if claims_df.empty:
        return None

    idx = claims_df.groupby(["cohort", "year"])["sourcefy"].idxmax()
    latest_df = claims_df.loc[idx].dropna(subset=["cohort", "year", "sourcefy", "value"]).reset_index(drop=True)
    if latest_df.empty:
        return None

    last_fy = latest_df["sourcefy"].max()
    latest_df["forecast"] = (latest_df["cohort"] + latest_df["year"]) > last_fy

    max_values = latest_df.groupby(["cohort", "forecast"], as_index=False)["value"].max()
    observed = max_values[max_values["forecast"] == False].copy()
    total = max_values.groupby("cohort", as_index=False)["value"].max().rename(columns={"value": "total_value"})
    plot_df = observed.merge(total, on="cohort", how="left")
    plot_df["forecast_value"] = plot_df["total_value"] - plot_df["value"]
    plot_df = plot_df.sort_values("cohort")
    plot_df["cohort_label"] = plot_df["cohort"].astype("Int64").astype(str)

    fig = go.Figure()
    fig.add_bar(
        x=plot_df["cohort_label"],
        y=plot_df["value"],
        name="Observed",
        marker_color="#4575b4",
        hovertemplate="Cohort=%{x}<br>Observed=%{y:,.2f}<extra></extra>",
    )
    fig.add_bar(
        x=plot_df["cohort_label"],
        y=plot_df["forecast_value"],
        name="Forecasted",
        marker_color="#a6bddb",
        hovertemplate="Cohort=%{x}<br>Forecasted=%{y:,.2f}<extra></extra>",
    )
    fig.update_layout(barmode="stack")
    fig = _apply_figure_layout(
        fig,
        x_axis_title="Cohort",
        y_axis_title="Percent",
        legend_orientation="h",
        legend_y=-0.2,
        legend_x=0.0,
    )
    fig.update_xaxes(tickangle=90)
    return fig


def build_claims_line_figure(claims_df: pd.DataFrame) -> go.Figure | None:
    if claims_df.empty:
        return None

    idx = claims_df.groupby(["cohort", "year"])["sourcefy"].idxmax()
    latest_df = claims_df.loc[idx].dropna(subset=["cohort", "year", "sourcefy", "value"]).reset_index(drop=True)
    if latest_df.empty:
        return None

    last_fy = latest_df["sourcefy"].max()
    latest_df["forecast"] = (latest_df["cohort"] + latest_df["year"]) > last_fy
    observed_df = latest_df[latest_df["forecast"] == False].copy()
    if observed_df.empty:
        return None

    observed_df = observed_df.sort_values(["cohort", "year"])
    observed_df["cohort_label"] = observed_df["cohort"].astype("Int64").astype(str)
    cohort_order = [str(int(cohort)) for cohort in sorted(observed_df["cohort"].dropna().unique())]

    blue_scale = [
        "#dbeafe",
        "#bfdbfe",
        "#93c5fd",
        "#60a5fa",
        "#3b82f6",
        "#2563eb",
        "#1d4ed8",
        "#1e40af",
        "#1e3a8a",
    ]
    if cohort_order:
        if len(cohort_order) == 1:
            color_map = {cohort_order[0]: blue_scale[-1]}
        else:
            color_positions = [round(index * (len(blue_scale) - 1) / (len(cohort_order) - 1)) for index in range(len(cohort_order))]
            color_map = {label: blue_scale[position] for label, position in zip(cohort_order, color_positions)}
    else:
        color_map = {}

    fig = px.line(
        observed_df,
        x="year",
        y="value",
        color="cohort_label",
        category_orders={"cohort_label": cohort_order},
        color_discrete_map=color_map,
    )
    fig.update_traces(hovertemplate="Year=%{x}<br>Rate=%{y:,.2f}<br>Cohort=%{fullData.name}<extra></extra>")
    return _apply_figure_layout(
        fig,
        y_axis_title="Percent",
        x_axis_title="Years Since Origination",
        legend_title="Cohort",
        legend_orientation="v",
        legend_y=1.0,
        legend_x=1.02,
    )


if __name__ == "__main__":
    claims_df = load_claims_data()
    claims_line_fig = build_claims_line_figure(claims_df)
    claims_stack_fig = build_claims_stack_figure(claims_df)

