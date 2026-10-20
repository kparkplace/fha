from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dash import Dash, Input, Output, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from creditsubsidy import load_credit_subsidy_data


REPO_ROOT = Path(__file__).resolve().parent
CAPRATIO_PATH = REPO_ROOT / "Data" / "capratio.parquet"
CLAIMS_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"


DATA_CACHE = {
    "capratio_df": None,
    "claims_df": None,
    "creditsubsidy_df": None,
    "loaded_at": None,
    "load_error": None,
    "creditsubsidy_error": None,
}


def ensure_data_loaded() -> None:
    if DATA_CACHE["load_error"] is not None:
        return

    if (
        DATA_CACHE["capratio_df"] is not None
        and DATA_CACHE["claims_df"] is not None
        and (DATA_CACHE["creditsubsidy_df"] is not None or DATA_CACHE["creditsubsidy_error"] is not None)
    ):
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

    if DATA_CACHE["creditsubsidy_df"] is None and DATA_CACHE["creditsubsidy_error"] is None:
        try:
            DATA_CACHE["creditsubsidy_df"] = load_credit_subsidy_data()
        except Exception as exc:
            DATA_CACHE["creditsubsidy_error"] = str(exc)


def get_adjusted_y_axis_title() -> str:
    return f"{datetime.now(timezone.utc).year} Dollars"


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


def apply_figure_layout(
    fig: go.Figure,
    *,
    title: str,
    y_axis_title: str,
    x_axis_title: str = "Year",
    y_axis_range: list[float] | None = None,
    legend_title: str | None = None,
    height: int = 360,
    legend_orientation: str = "h",
    legend_y: float = -0.2,
    legend_x: float = 0,
) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.03},
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
            "cap_ratio": "Capital Ratio",
            "cap_ratio_unamort": "Capital Ratio (Unamortized)",
        }
    )
    
    plot_df["value"] = plot_df["value"] * 100

    fig = px.line(
        plot_df.sort_values(["source", "metric", "year"]),
        x="year",
        y="value",
        color="source",
        line_dash="metric",
    )
    fig.update_traces(hovertemplate="Year=%{x}<br>Value=%{y:,.2f}<br>Source=%{fullData.name}<extra></extra>")
    return apply_figure_layout(fig, title="", y_axis_title="Percent", height=560)


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
    return apply_figure_layout(
        fig,
        title="",
        y_axis_title=y_axis_title,
        y_axis_range=y_axis_range,
    )


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
    fig = apply_figure_layout(
        fig,
        title="",
        x_axis_title="Cohort",
        y_axis_title="Percent",
        height=420,
        legend_title=None,
        legend_orientation="h",
        legend_y=-0.2,
        legend_x=0,
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
    return apply_figure_layout(
        fig,
        title="",
        y_axis_title="Percent",
        x_axis_title="Years Since Origination",
        legend_title="Cohort",
        height=420,
        legend_orientation="v",
        legend_y=1,
        legend_x=1.02,
    )


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

    bar_years = [str(value) for value in plot_df["fiscal_year"].tolist()]
    bar_values = plot_df["current_reestimated_rate"].tolist()
    original_years = [str(value) for value in plot_df["fiscal_year"].dropna().tolist()]
    original_values = plot_df["original_subsidy_rate"].dropna().tolist()

    fig = go.Figure()
    fig.add_bar(
        x=bar_years,
        y=bar_values,
        name="Current Estimate",
        marker_color="#4c72b0",
        hovertemplate="FY=%{x}<br>Current=%{y:,.2f}%<extra></extra>",
    )

    if len(original_years) > 0 and len(original_values) > 0:
        original_mask = plot_df["original_subsidy_rate"].notna()
        fig.add_scatter(
            x=[str(value) for value in plot_df.loc[original_mask, "fiscal_year"].tolist()],
            y=plot_df.loc[original_mask, "original_subsidy_rate"].tolist(),
            mode="markers",
            name="Original Estimate",
            marker={"color": "#93c5fd", "size": 8, "symbol": "circle"},
            hovertemplate="FY=%{x}<br>Original=%{y:,.2f}%<extra></extra>",
        )

    fig = apply_figure_layout(
        fig,
        title="",
        x_axis_title="Book of Business",
        y_axis_title="Percent",
        height=420,
    )
    fig.update_xaxes(tickangle=90)
    return fig


def build_section_header(title: str, description: str | None = None) -> html.Div:
    """Build a section header with title and optional description."""
    return html.Div(
        [
            html.H2(title, style={"marginBottom": "6px", "marginTop": "24px", "color": "#1e293b"}),
            html.P(
                description,
                style={"color": "#64748b", "marginTop": "0", "marginBottom": "16px", "lineHeight": "1.6", "fontSize": "0.95rem"},
            ) if description else None,
        ],
        style={"borderBottom": "2px solid #e2e8f0", "paddingBottom": "12px"},
    )


def build_chart_card(title: str, description: str, figure: go.Figure | None, *, featured: bool = False) -> html.Div:
    """Build a chart card with title, description, and optional figure."""
    card_style = {
        "backgroundColor": "#ffffff",
        "border": "1px solid #dbe2ea",
        "borderRadius": "12px",
        "boxShadow": "0 2px 8px rgba(16, 24, 40, 0.06)",
        "padding": "16px",
    }
    if featured:
        card_style["marginBottom"] = "18px"

    if figure is None:
        return html.Div(
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
            style=card_style,
        )

    return html.Div(
        [
            html.H3(title, style={"marginBottom": "6px"}),
            html.P(description, style={"color": "#475569", "marginTop": "0", "marginBottom": "10px"}),
            dcc.Graph(figure=figure, config={"displaylogo": False, "responsive": True}),
        ],
        style=card_style,
    )


def build_dashboard_sections() -> html.Div:
    """Build all dashboard sections organized by module."""
    capratio_df = DATA_CACHE["capratio_df"]
    claims_df = DATA_CACHE["claims_df"]
    creditsubsidy_df = DATA_CACHE["creditsubsidy_df"]
    if capratio_df is None or claims_df is None:
        return html.Div()

    adjusted_y_axis_title = get_adjusted_y_axis_title()
    adjusted_y_axis_range = get_adjusted_y_range(capratio_df)

    sections = []

    # MMI Fund Capital Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "MMI Fund Capital",
                    "The National Affordable Housing Act of 1990 requires an annual independent actuarial review"
                    "of the Mutual Mortgage Insurance Fund and a 2 percent minimum capital ratio." \
                    "The capital ratio is defined the economic net worth of the Fund relative to the insurance-in-force."
                    "The Act specifically states 'unamortized' insurance-in-force but then defines 'unamortized'"
                    "as the 'remaining obligation on outstanding mortgages.' Current practice uses the amortized value that better meets this definition."  \
                    "Economic net worth includes both existing capital resources and the net present value of future cash flows."
                    "The capital ratio has turned negative twice in the last 35 years."
                    "Losses during the Great Financial Crisis prompted a $1.7 billionh infusion from the US Treasury in 2013.",
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Capital Ratios",
                            "Economic net worth as a share of insurance-in-force.",
                            build_capital_ratio_figure(capratio_df),
                        ),
                    ],
                    style={"marginBottom": "16px"},
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Economic Net Worth",
                            "The sum of capital resources and net present value of cash flows.",
                            build_adjusted_figure(
                                capratio_df,
                                "econ_value_in_latest_dollars",
                                adjusted_y_axis_title,
                                adjusted_y_axis_range,
                            ),
                        ),
                        build_chart_card(
                            "Capital Resources",
                            build_adjusted_figure(
                                capratio_df,
                                "cap_resources_in_latest_dollars",
                                adjusted_y_axis_title,
                                adjusted_y_axis_range,
                            ),
                        ),
                        build_chart_card(
                            "Cashflow Net Present Value",
                            build_adjusted_figure(
                                capratio_df,
                                "cashflow_npv_in_latest_dollars",
                                adjusted_y_axis_title,
                                adjusted_y_axis_range,
                            ),
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))",
                        "gap": "14px",
                        "alignItems": "start",
                    },
                ),
            ],
            style={"marginBottom": "24px"},
        )
    )

    # Cumulative Claim Rates Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Cumulative Claim Rates",
                    "The annual actuarial reviews of the MMI Fund include the loan performance of the book of business"
                    "over the previous 30 years and project their future performance.",
                    "By compiling historical actuarial reviews, the data below show 50 years of"
                    "claim terminations as a share of insured loans.",
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Observed Cumulative Claim Rates",
                            "Cumulative claims by cohort and years since origination.",
                            build_claims_line_figure(claims_df),
                        ),
                        build_chart_card(
                            "Observed and Forecasted Cumulative Claim Rates",
                            "Cumulative claims by cohort.",
                            build_claims_stack_figure(claims_df),
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))",
                        "gap": "14px",
                        "alignItems": "start",
                    },
                ),
            ],
            style={"marginBottom": "24px"},
        )
    )

    # Credit Subsidy Rates Section
    if creditsubsidy_df is not None:
        sections.append(
            html.Div(
                [
                    build_section_header(
                        "Credit Subsidy by Cohort",
                        "The Federal Credit Reform Act of 1990 requires the Office of Management and Budget to estimate the lifetime cost"
                        "of federal direct loans and loan guarantees, rather than only budgeting on a cash-flow basis." \
                        "A negative credit subsidy indicates a book of business is projected to bring in more revenue than it costs the government."
                        "These estimates are revised every year as part of the federal budget process." \
                    ),
                    build_chart_card(
                        "Credit Subsidy Rates",
                        build_creditsubsidy_figure(creditsubsidy_df),
                    ),
                ],
                style={"marginBottom": "24px"},
            )
        )

    return html.Div(sections)


def render_stats_items() -> list[html.Li]:
    if DATA_CACHE["load_error"]:
        return [
            html.Li("Capratio rows: 0"),
            html.Li("Claims rows: 0"),
            html.Li("Credit subsidy rows: 0"),
            html.Li("Loaded at: Failed"),
        ]

    loaded_at = DATA_CACHE["loaded_at"]
    loaded_at_text = loaded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if loaded_at else "Loading..."
    capratio_rows = len(DATA_CACHE["capratio_df"]) if DATA_CACHE["capratio_df"] is not None else 0
    claims_rows = len(DATA_CACHE["claims_df"]) if DATA_CACHE["claims_df"] is not None else 0
    creditsubsidy_rows = len(DATA_CACHE["creditsubsidy_df"]) if DATA_CACHE["creditsubsidy_df"] is not None else 0
    chart_count = 7 if DATA_CACHE["creditsubsidy_df"] is not None else 6
    return [
        html.Li(f"Capratio rows: {capratio_rows:,}"),
        html.Li(f"Claims rows: {claims_rows:,}"),
        html.Li(f"Credit subsidy rows: {creditsubsidy_rows:,}"),
        html.Li(f"Charts: {chart_count}"),
        html.Li(
            "Credit subsidy data: Unavailable (check network access to White House OMB file)"
            if DATA_CACHE["creditsubsidy_error"]
            else "Credit subsidy data: Loaded"
        ),
        html.Li(f"Loaded at: {loaded_at_text}"),
    ]


app = Dash(__name__)
server = app.server
app.title = "FHA Dashboard"


@server.route("/healthz")
def healthz() -> tuple[str, int]:
    return "ok", 200


app.layout = html.Div(
    [
        # Header
        html.Header(
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("FHA Single-Family Forward Loans Dashboard", style={"marginBottom": "4px"}),
                            html.P("Created by Kevin Park (kevinapark@gmail.com)", style={"marginBottom": "0", "color": "#64748b", "fontSize": "0.9rem"}),
                        ],
                    ),
                ],
                style={"maxWidth": "1440px", "margin": "0 auto"},
            ),
            style={
                "backgroundColor": "#ffffff",
                "borderBottom": "1px solid #e2e8f0",
                "padding": "20px 18px",
                "marginBottom": "24px",
            },
        ),
        # Main content
        html.Div(
            [
                # Intro text
                html.Div(
                    [
                        html.P(
                            "The Federal Housing Administration (FHA) was created in 1934 'to encourage improvement in housing standards and conditions, "
                            "to provide a system of mutual mortgage insurance, and for other purposes.' Since then it has insured over 40 million home loans "
                            "and currently guarantees $1.6 trillion through its Mutual Mortgage Insurance Fund.",
                            style={"marginBottom": "12px"},
                        ),
                        html.P(
                            "This website provides a historical overview of the financial condition of forward loans in the MMI Fund.",
                            style={"marginBottom": "12px"},
                        ),
                    ],
                    style={
                        "backgroundColor": "#f8fafc",
                        "border": "1px solid #e2e8f0",
                        "padding": "16px",
                        "borderRadius": "8px",
                        "marginBottom": "24px",
                        "lineHeight": "1.6",
                    },
                ),
                # Status box
                html.Div(
                    id="status-box",
                    children="Loading chart data...",
                    style={
                        "backgroundColor": "#eff6ff",
                        "border": "1px solid #93c5fd",
                        "padding": "12px 14px",
                        "borderRadius": "8px",
                        "marginBottom": "24px",
                        "fontSize": "0.95rem",
                    },
                ),
                # Summary stats
                html.Details(
                    [
                        html.Summary(
                            "Load summary",
                            style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "500", "marginBottom": "12px"},
                        ),
                        html.Ul(
                            id="summary-stats",
                            children=render_stats_items(),
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
                                "gap": "8px",
                                "listStyle": "none",
                                "paddingLeft": "0",
                                "margin": "0",
                            },
                        ),
                    ],
                    style={"marginBottom": "24px"},
                ),
                # Dashboard sections
                html.Div(
                    id="sections-container",
                    children=[],
                ),
                dcc.Interval(id="initial-load", interval=300, n_intervals=0, max_intervals=1),
            ],
            style={
                "maxWidth": "1440px",
                "margin": "0 auto",
                "padding": "0 18px 24px 18px",
            },
        ),
    ],
    style={
        "fontFamily": "Segoe UI, sans-serif",
        "backgroundColor": "#ffffff",
        "color": "#1e293b",
    },
)


@app.callback(
    Output("status-box", "children"),
    Output("status-box", "style"),
    Output("summary-stats", "children"),
    Output("sections-container", "children"),
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
                "padding": "12px 14px",
                "borderRadius": "8px",
                "marginBottom": "24px",
            },
            render_stats_items(),
            [],
        )

    sections = build_dashboard_sections()

    status_style = {
        "backgroundColor": "#ecfdf3",
        "border": "1px solid #86efac",
        "padding": "12px 14px",
        "borderRadius": "8px",
        "marginBottom": "24px",
        "fontSize": "0.95rem",
    }

    if DATA_CACHE["creditsubsidy_error"]:
        return (
            [
                html.Strong("Core data loaded with warning."),
                html.Div(f"Credit subsidy chart data unavailable: {DATA_CACHE['creditsubsidy_error']}"),
            ],
            {
                "backgroundColor": "#fffbeb",
                "border": "1px solid #fcd34d",
                "padding": "12px 14px",
                "borderRadius": "8px",
                "marginBottom": "24px",
            },
            render_stats_items(),
            sections,
        )

    return (
        "Data loaded successfully.",
        status_style,
        render_stats_items(),
        sections,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8050)