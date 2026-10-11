from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dash import Dash, Input, Output, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
CAPRATIO_PATH = REPO_ROOT / "Data" / "capratio.parquet"
CLAIMS_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"


DATA_CACHE = {
    "capratio_df": None,
    "claims_df": None,
    "loaded_at": None,
    "load_error": None,
}


def ensure_data_loaded() -> None:
    if DATA_CACHE["load_error"] is not None:
        return

    if DATA_CACHE["capratio_df"] is not None and DATA_CACHE["claims_df"] is not None:
        return

    if not CAPRATIO_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {CAPRATIO_PATH}"
        return

    if not CLAIMS_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {CLAIMS_PATH}"
        return

    capratio_df = pd.read_parquet(CAPRATIO_PATH)
    claims_df = pd.read_parquet(CLAIMS_PATH)

    if "cap_ratio" not in capratio_df.columns and {"capital", "value", "ratio"}.issubset(capratio_df.columns):
        capratio_df["cap_ratio"] = 100 * capratio_df["capital"] / (capratio_df["value"] / (capratio_df["ratio"] / 100))

    if (
        "cap_ratio_unamort" not in capratio_df.columns
        and "iif_unamort" in capratio_df.columns
        and "ratio" in capratio_df.columns
        and "capital" in capratio_df.columns
    ):
        capratio_df["cap_ratio_unamort"] = 100 * capratio_df["capital"] / (capratio_df["iif_unamort"] / (capratio_df["ratio"] / 100))

    claims_df = claims_df.copy()
    if "metric" in claims_df.columns:
        claims_df = claims_df[claims_df["metric"] == "cum_clm_rate"].copy()

    claims_df["cohort"] = pd.to_numeric(claims_df["cohort"], errors="coerce")
    claims_df["year"] = pd.to_numeric(claims_df["year"], errors="coerce")
    claims_df["sourcefy"] = pd.to_numeric(claims_df["sourcefy"], errors="coerce")
    claims_df["value"] = pd.to_numeric(claims_df["value"], errors="coerce")

    DATA_CACHE["capratio_df"] = capratio_df
    DATA_CACHE["claims_df"] = claims_df
    DATA_CACHE["loaded_at"] = datetime.now(timezone.utc)


def apply_figure_layout(fig: go.Figure, *, title: str, y_axis_title: str, legend_title: str | None = None, height: int = 360) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.03},
        height=height,
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
        legend_title_text=legend_title,
    )
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text=y_axis_title)
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
            "cap_ratio": "Capital Ratio",
            "cap_ratio_unamort": "Capital Ratio (Unamortized)",
        }
    )

    fig = px.line(
        plot_df.sort_values(["source", "metric", "year"]),
        x="year",
        y="value",
        color="source",
        line_dash="metric",
        markers=True,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b")
    fig.update_traces(hovertemplate="Year=%{x}<br>Value=%{y:,.2f}<br>Source=%{fullData.name}<extra></extra>")
    return apply_figure_layout(fig, title="Capital Ratios by Source", y_axis_title="Percent")


def build_adjusted_figure(capratio_df: pd.DataFrame, metric_column: str, title: str) -> go.Figure | None:
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
        markers=True,
    )
    fig.update_traces(hovertemplate="Year=%{x}<br>Value=%{y:,.0f}<br>Source=%{fullData.name}<extra></extra>")
    return apply_figure_layout(fig, title=title, y_axis_title="Value (latest dollars)")


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
    fig.update_xaxes(title_text="Cohort", tickangle=90)
    fig.update_yaxes(title_text="Cumulative Claim Rate")
    fig.update_layout(
        title={"text": "Observed and Forecasted Cumulative Claim Rate by Cohort", "x": 0.03},
        height=420,
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 60, "b": 100},
        legend_title_text=None,
    )
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

    fig = px.line(
        observed_df,
        x="year",
        y="value",
        color="cohort_label",
        markers=True,
    )
    fig.update_traces(hovertemplate="Year=%{x}<br>Rate=%{y:,.2f}<br>Cohort=%{fullData.name}<extra></extra>")
    return apply_figure_layout(
        fig,
        title="Observed Cumulative-Claim Paths by Cohort",
        y_axis_title="Cumulative Claim Rate",
        legend_title="Cohort",
        height=420,
    )


def build_chart_cards() -> list[html.Div]:
    capratio_df = DATA_CACHE["capratio_df"]
    claims_df = DATA_CACHE["claims_df"]
    if capratio_df is None or claims_df is None:
        return []

    chart_specs = [
        (
            "Capital Ratios",
            "Capital ratio and unamortized capital ratio by source.",
            build_capital_ratio_figure(capratio_df),
        ),
        (
            "Inflation-Adjusted Econ Value",
            "Latest-dollar econ value by source.",
            build_adjusted_figure(capratio_df, "econ_value_in_latest_dollars", "Inflation-Adjusted Econ Value (latest dollars)"),
        ),
        (
            "Inflation-Adjusted Cap Resources",
            "Latest-dollar capital resources by source.",
            build_adjusted_figure(capratio_df, "cap_resources_in_latest_dollars", "Inflation-Adjusted Cap Resources (latest dollars)"),
        ),
        (
            "Inflation-Adjusted Cashflow NPV",
            "Latest-dollar cashflow NPV by source.",
            build_adjusted_figure(capratio_df, "cashflow_npv_in_latest_dollars", "Inflation-Adjusted Cashflow NPV (latest dollars)"),
        ),
        (
            "Claims Stack",
            "Observed and forecasted cumulative claim-rate totals by cohort.",
            build_claims_stack_figure(claims_df),
        ),
        (
            "Observed Cohort Paths",
            "Observed cumulative claim-rate paths by cohort over policy year.",
            build_claims_line_figure(claims_df),
        ),
    ]

    cards: list[html.Div] = []
    for title, description, figure in chart_specs:
        if figure is None:
            cards.append(
                html.Div(
                    [
                        html.H3(title, style={"marginBottom": "8px"}),
                        html.P(description, style={"color": "#475569", "marginTop": "0"}),
                        html.Div(
                            "No data available for this chart.",
                            style={
                                "backgroundColor": "#fff7ed",
                                "border": "1px solid #fdba74",
                                "padding": "14px 16px",
                                "borderRadius": "10px",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "border": "1px solid #dbe2ea",
                        "borderRadius": "12px",
                        "boxShadow": "0 2px 8px rgba(16, 24, 40, 0.06)",
                        "padding": "16px",
                    },
                )
            )
            continue

        cards.append(
            html.Div(
                [
                    html.H3(title, style={"marginBottom": "6px"}),
                    html.P(description, style={"color": "#475569", "marginTop": "0", "marginBottom": "10px"}),
                    dcc.Graph(figure=figure, config={"displaylogo": False, "responsive": True}),
                ],
                style={
                    "backgroundColor": "#ffffff",
                    "border": "1px solid #dbe2ea",
                    "borderRadius": "12px",
                    "boxShadow": "0 2px 8px rgba(16, 24, 40, 0.06)",
                    "padding": "16px",
                },
            )
        )

    return cards


def render_stats_items() -> list[html.Li]:
    if DATA_CACHE["load_error"]:
        return [
            html.Li("Capratio rows: 0"),
            html.Li("Claims rows: 0"),
            html.Li("Loaded at: Failed"),
        ]

    loaded_at = DATA_CACHE["loaded_at"]
    loaded_at_text = loaded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if loaded_at else "Loading..."
    capratio_rows = len(DATA_CACHE["capratio_df"]) if DATA_CACHE["capratio_df"] is not None else 0
    claims_rows = len(DATA_CACHE["claims_df"]) if DATA_CACHE["claims_df"] is not None else 0
    return [
        html.Li(f"Capratio rows: {capratio_rows:,}"),
        html.Li(f"Claims rows: {claims_rows:,}"),
        html.Li("Charts: 6"),
        html.Li(f"Loaded at: {loaded_at_text}"),
    ]


app = Dash(__name__)
server = app.server
app.title = "FHA Plot Dashboard"


@server.route("/healthz")
def healthz() -> tuple[str, int]:
    return "ok", 200


app.layout = html.Div(
    [
        html.H1("FHA Plot Dashboard"),
        html.P("Browser-rendered versions of the FHA cap ratio and claims charts."),
        html.Ul(id="summary-stats", children=render_stats_items()),
        html.Div(
            id="status-box",
            children="Loading chart data...",
            style={
                "backgroundColor": "#eff6ff",
                "border": "1px solid #93c5fd",
                "padding": "10px 12px",
                "borderRadius": "10px",
                "marginBottom": "14px",
            },
        ),
        html.Div(
            id="chart-grid",
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))",
                "gap": "14px",
                "alignItems": "start",
            },
        ),
        dcc.Interval(id="initial-load", interval=300, n_intervals=0, max_intervals=1),
    ],
    style={
        "fontFamily": "Segoe UI, sans-serif",
        "padding": "18px",
        "maxWidth": "1440px",
        "margin": "0 auto",
        "backgroundColor": "#f8fafc",
    },
)


@app.callback(
    Output("status-box", "children"),
    Output("status-box", "style"),
    Output("summary-stats", "children"),
    Output("chart-grid", "children"),
    Input("initial-load", "n_intervals"),
)
def load_and_render(_n_intervals: int):
    ensure_data_loaded()

    if DATA_CACHE["load_error"]:
        return (
            [html.Strong("Unable to load dashboard data."), html.Div(DATA_CACHE["load_error"])],
            {
                "backgroundColor": "#fef2f2",
                "border": "1px solid #fca5a5",
                "padding": "10px 12px",
                "borderRadius": "10px",
                "marginBottom": "14px",
            },
            render_stats_items(),
            [],
        )

    return (
        "Data loaded successfully.",
        {
            "backgroundColor": "#ecfdf3",
            "border": "1px solid #86efac",
            "padding": "10px 12px",
            "borderRadius": "10px",
            "marginBottom": "14px",
        },
        render_stats_items(),
        build_chart_cards(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=8050)