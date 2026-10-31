from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dash import Dash, Input, Output, dcc, html

from capratio import (
    build_adjusted_figure,
    build_capital_ratio_figure,
    get_adjusted_y_axis_title,
    get_adjusted_y_range,
    load_capratio_data,
)
from claimsrate import build_claims_line_figure, build_claims_stack_figure, load_claims_data
from creditrisk import build_creditrisk_figure, load_creditrisk_data
from creditsubsidy import build_creditsubsidy_figure, load_credit_subsidy_data
from endorsements import build_endorsements_figure, load_endorsements_data


REPO_ROOT = Path(__file__).resolve().parent
CAPRATIO_PATH = REPO_ROOT / "Data" / "capratio.parquet"
CLAIMS_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"
CREDITRISK_PATH = REPO_ROOT / "Data" / "creditrisk.parquet"
ENDORSEMENTS_PATH = REPO_ROOT / "Data" / "endorsements.parquet"


DATA_CACHE = {
    "capratio_df": None,
    "claims_df": None,
    "creditrisk_df": None,
    "creditsubsidy_df": None,
    "endorsements_df": None,
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
        and DATA_CACHE["creditrisk_df"] is not None
        and DATA_CACHE["endorsements_df"] is not None
        and (DATA_CACHE["creditsubsidy_df"] is not None or DATA_CACHE["creditsubsidy_error"] is not None)
    ):
        return

    if not CAPRATIO_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {CAPRATIO_PATH}"
        return

    if not CLAIMS_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {CLAIMS_PATH}"
        return

    if not CREDITRISK_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {CREDITRISK_PATH}"
        return

    if not ENDORSEMENTS_PATH.exists():
        DATA_CACHE["load_error"] = f"Missing parquet input: {ENDORSEMENTS_PATH}"
        return

    capratio_df = load_capratio_data(CAPRATIO_PATH)
    claims_df = load_claims_data(CLAIMS_PATH)
    creditrisk_df = load_creditrisk_data(CREDITRISK_PATH)
    endorsements_df = load_endorsements_data(ENDORSEMENTS_PATH)

    DATA_CACHE["capratio_df"] = capratio_df
    DATA_CACHE["claims_df"] = claims_df
    DATA_CACHE["creditrisk_df"] = creditrisk_df
    DATA_CACHE["endorsements_df"] = endorsements_df
    DATA_CACHE["loaded_at"] = datetime.now(timezone.utc)

    if DATA_CACHE["creditsubsidy_df"] is None and DATA_CACHE["creditsubsidy_error"] is None:
        try:
            DATA_CACHE["creditsubsidy_df"] = load_credit_subsidy_data()
        except Exception as exc:
            DATA_CACHE["creditsubsidy_error"] = str(exc)


def build_section_header(title: str, description: str | list | None = None) -> html.Div:
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


def build_data_sources(sources_content: list | str) -> html.Details:
    """Build a collapsible Data Sources section with bullet points."""
    # Convert single items to list
    if not isinstance(sources_content, list):
        sources_content = [sources_content]
    
    # Wrap items in list items if they're not already
    list_items = [
        html.Li(item) if not isinstance(item, html.Li) else item
        for item in sources_content
    ]
    
    return html.Details(
        [
            html.Summary(
                "Data Sources",
                style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "500", "fontSize": "0.95rem", "marginBottom": "8px"}
            ),
            html.Ul(
                list_items,
                style={"lineHeight": "1.6", "fontSize": "0.9rem", "color": "#64748b", "marginTop": "8px", "marginBottom": "0"}
            ),
        ],
        style={"marginTop": "12px", "padding": "12px", "backgroundColor": "#f8fafc", "borderRadius": "8px", "border": "1px solid #e2e8f0"}
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
    creditrisk_df = DATA_CACHE["creditrisk_df"]
    endorsements_df = DATA_CACHE["endorsements_df"]
    creditsubsidy_df = DATA_CACHE["creditsubsidy_df"]
    if capratio_df is None or claims_df is None or creditrisk_df is None or endorsements_df is None:
        return html.Div()

    adjusted_y_axis_title = get_adjusted_y_axis_title()
    adjusted_y_axis_range = get_adjusted_y_range(capratio_df)

    sections = []

    # 1) Endorsements Section
    endorsements_fig, endorsements_subtitle = build_endorsements_figure(endorsements_df)
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Originations",
                    [
                        "In December 1934, Amos and Elise Herbert applied to refinance their home in the Del Ray neighborhood of Alexandria, Virginia. "
                        "Amos was a 45-year-old clerk making $137 per month for the Southern Railway Company, where he had worked for 28 years. "
                        "He was described as, 'a steady, industrious type and seems to be a good type of citizen. Anxious to keep his home, and interested in his family's welfare.' "
                        "But his pay had been cut 10 percent over the previous four years, and he was struggling to pay his property taxes and second mortgage. "
                        "With the help of a new federal insurance program, Amos and Elise were able to get a $3,500 loan from Alexandria National Bank "
                        "to be paid back at $25.07 per month for the next 19 1/2 years.",
                        html.Br(),
                        "This was the first home mortgage insured by the Federal Housing Administration. "
                        "Since then, FHA has helped over 55 million American households, many struggling financially like the Herberts, to achieve and sustain the American Dream.",
                    ],
                ),
                build_chart_card(
                    "Endorsements by Year",
                    endorsements_subtitle,
                    endorsements_fig,
                ),
                build_data_sources([
                    [
                        "1979 Statistical Yearbook, US Department of Housing and Urban Development. Available at ",
                        html.A("https://www.huduser.gov/portal/sites/default/files/publications/pdf/HUD-4033.pdf", 
                               href="https://www.huduser.gov/portal/sites/default/files/publications/pdf/HUD-4033.pdf",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                    [
                        "U.S. Housing Market Conditions Historical Data, US Department of Housing and Urban Development. Available via Wayback Machine at ",
                        html.A("https://web.archive.org/web/20250331171045/https://www.huduser.gov/periodicals/ushmc/winter2001/histdat16.htm", 
                               href="https://web.archive.org/web/20250331171045/https://www.huduser.gov/periodicals/ushmc/winter2001/histdat16.htm",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                    [
                        "FHA-Insured Single-Family Mortgage Originations and Market Share Reports. Available at ",
                        html.A("https://www.hud.gov/hud-partners/single-family-mortgage-market-share", 
                               href="https://www.hud.gov/hud-partners/single-family-mortgage-market-share",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                ]),
            ],
            id="section-originations",
            style={"marginBottom": "24px"},
        )
    )

    # 2) Mortgage Default Risk Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Credit Risk",
                    [
                        "Underwriting quality can be assessed by combining borrower and loan characteristics with historical loan performance. "
                        "Davis et al. (2023) compute the mortgage default rate on loans originated in 2006 and 2007 by credit score, debt-to-income (DTI) ratio, and loan-to-value (LTV) ratio. "
                        "Then they estimate the probability of default for each annual cohort based on the composition of borrower and loan characteristics. "
                        "The American Enterprise Institute's National Mortgage Default Rate metric extends that estimate to the present on a monthly basis.",
                        html.Br(),
                        "However, the average default probability of FHA-insured loans does not necessarily reflect changes in FHA underwriting. "
                        "Many lenders apply credit overlays, restricting the risk profile of borrowers beyond FHA's minimum standards. "
                        "So the number of high-risk FHA borrowers is impacted by the implementation and relaxation of these overlays. "
                        "At the same time, conventional lenders compete for lower risk borrowers. "
                        "The combination of FHA underwriting standards, lender overlays, and conventional market competition determine FHA's average risk.",
                        html.Br(),
                        "Nevertheless, there is an obvious reduction in default risk among FHA-insured loans during the Great Financial Crisis, and the average risk has remained well below that of the 1990s.",
                    ],
                ),
                build_chart_card(
                    "Estimated Stressed Default Rate",
                    "Based on 2006-07 loan performance.",
                    build_creditrisk_figure(creditrisk_df),
                ),
                build_data_sources([
                    [
                        "Morris A. Davis, William D. Larson, Stephen D. Oliner, Benjamin R. Smith. 2023. "
                        "\"A Quarter Century of Mortgage Risk.\" Federal Housing Finance Agency, Working Paper 19-02. "
                        "Data supplement available at ",
                        html.A("https://www.fhfa.gov/research/papers/wp1902", 
                               href="https://www.fhfa.gov/research/papers/wp1902",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                    [
                        "American Enterprise Institute, National Mortgage Default Rate. Available at ",
                        html.A("https://www.aei.org/housing/mortgage-risk-index/",
                               href="https://www.aei.org/housing/mortgage-risk-index/",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                ]),
            ],
            id="section-credit-risk",
            style={"marginBottom": "24px"},
        )
    )

    # 3) Cumulative Claim Rates Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Claims",
                    "The annual actuarial reviews of the MMI Fund include the loan performance of prior cohorts and project their future performance. "
                    "By compiling historical actuarial reviews, the data below show 50 years of claim terminations as a share of insured loans."
                    "FHA loans insured since 2012 are on pace to experience the lowest claim rates since at least 1974.",
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
                            "Cumulative claims by cohort with projections for future years.",
                            build_claims_stack_figure(claims_df),
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(min(420px, 100%), 1fr))",
                        "gap": "14px",
                        "alignItems": "start",
                    },
                ),
                build_data_sources([
                    [
                        "FHA annual actuarial reviews. Available at ",
                        html.A("https://www.hud.gov/stat/sfh/mortgage-insurance-fund", 
                               href="https://www.hud.gov/stat/sfh/mortgage-insurance-fund",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        ". Each actuarial review provides the observed and projected performance by cohort for the previous 30 years, reported in an appendix."
                    ]
                ]),
            ],
            id="section-claim-rates",
            style={"marginBottom": "24px"},
        )
    )

    # 4) Credit Subsidy Rates Section
    if creditsubsidy_df is not None:
        creditsubsidy_fig, creditsubsidy_subtitle = build_creditsubsidy_figure(creditsubsidy_df)
        sections.append(
            html.Div(
                [
                    build_section_header(
                        "Credit Subsidy by Cohort",
                        [
                            "The Federal Credit Reform Act of 1990 requires the Office of Management and Budget to estimate the lifetime cost "
                            "of federal direct loans and loan guarantees, rather than only budgeting on a cash-flow basis. "
                            "These estimates are revised every year as part of the federal budget process.",
                            html.Br(),
                            "Although FHA lost money on loans originated prior to the Great Financial Crisis, "
                            "it generally takes in more in premiums than it pays out in claims, resulting in an average negative credit subsidy since estimates began in 1992.",
                            html.Br(),
                            "However, profitability does not justify the existence of the program. "
                            "As former FHA Commissioner John Weicher (1995) wrote, \u201c[T]he fact that FHA does not lose money on its home mortgage insurance is not a justification "
                            "for its existence; the justification is that it serves a public purpose. Serving that purpose without "
                            "losing money is an indication that FHA home mortgage insurance works reasonably well\u2014not perfectly, but reasonably well.\u201d",
                        ],
                    ),
                    build_chart_card(
                        "Credit Subsidy Rates",
                        creditsubsidy_subtitle,
                        creditsubsidy_fig,
                    ),
                    build_data_sources([
                        [
                            "Federal Credit Supplement. Table 2 and Table 8. Office of Management and Budget. Available at ",
                            html.A("https://www.whitehouse.gov/omb/information-resources/budget/supplemental-materials/",
                                   href="https://www.whitehouse.gov/omb/information-resources/budget/supplemental-materials/",
                                   target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                            "."
                        ]
                    ]),
                ],
                id="section-credit-subsidy",
                style={"marginBottom": "24px"},
            )
        )

    # 5) MMI Fund Capital Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "MMI Fund Capital",
                    [
                        "The National Affordable Housing Act of 1990 requires an annual independent actuarial review "
                        "of the Mutual Mortgage Insurance Fund and a 2 percent minimum capital ratio, "
                        "defined as the economic net worth of the Fund relative to the insurance-in-force.",
                        html.Details(
                            [
                                html.Summary(
                                    "*",
                                    style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "bold", "display": "inline", "marginLeft": "2px", "marginRight": "2px"},
                                ),
                                html.P(
                                    "The Act specifically states 'unamortized' insurance-in-force but then defines 'unamortized' "
                                    "in a way that includes some amortized loans.",
                                    style={"color": "#64748b", "fontSize": "0.85rem", "marginTop": "8px", "marginBottom": "0"},
                                ),
                            ],
                            style={"display": "inline"},
                        ),
                        "Two percent is substantially lower than the capital requirements for private mortgage insurers laid out "
                        "by Fannie Mae and Freddie Mac's Private Mortgage Insurers Eligibility Requirements (PMIERS), "
                        "which varies by portfolio risk but has a floor of 5.6 percent of risk-in-force.",
                        html.Br(),
                        "However, as noted, the profitability of FHA is not the justification for its existence.",
                        "The economic value of the MMI Fund has turned negative twice since 1990, meaning it was technically insolvent.",
                        "Yet the full faith and credit of the U.S. government means FHA insurance is still valued by investors.",
                        "That allows FHA to perform a counter-cyclical role, increasing lending while private insurers are retreating.",
                        "The first actuarial review of the Fund in 1990 concluded: 'The value of the Fund need not be sufficient to withstand all conceivable future economic conditions. We do not believe it is possible to build MMI's equity to a level needed to cover catastrophic risk. To do so would require premiums at levels that would impair MMI's social purposes. Catastrophic risk is implicitly covered through the backing of the U.S. Treasury.'",
                        html.Br(),
                        "The MMI Fund today has ample capital resources, well exceeding its statutory minimum requirements.",
                    ],
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Capital Ratio",
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
                            "Sum of capital resources and net present value of cash flows.",
                            build_adjusted_figure(
                                capratio_df,
                                "econ_value_in_latest_dollars",
                                adjusted_y_axis_title,
                                adjusted_y_axis_range,
                            ),
                        ),
                        build_chart_card(
                            "Existing Capital Resources",
                            " ",
                            build_adjusted_figure(
                                capratio_df,
                                "cap_resources_in_latest_dollars",
                                adjusted_y_axis_title,
                                adjusted_y_axis_range,
                            ),
                        ),
                        build_chart_card(
                            "Cashflows",
                            "Net present value of expected premium revenue minus claim losses on existing books of business.",
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
                        "gridTemplateColumns": "repeat(auto-fit, minmax(min(420px, 100%), 1fr))",
                        "gap": "14px",
                        "alignItems": "start",
                    },
                ),
                build_data_sources([
                    [
                        "FHA Annual Reports to Congress and independent actuarial reviews. Available at ",
                        html.A("https://www.hud.gov/stat/sfh/mortgage-insurance-fund",
                               href="https://www.hud.gov/stat/sfh/mortgage-insurance-fund",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        ". "
                    ],
                    ["Edward Szymanoski, William Reeder, Padmasini Raman and John Comeau. \"The FHA Single Family Insurance Program: Performing a Needed "
                     "Role in the Housing Finance Market\". US Department of Housing and Urban Development, 2012."
                     " Available at: ",
                        html.A("https://www.huduser.gov/publications/pdf/FHA_SingleFamilyIns_dec2012.pdf",
                               href="https://www.huduser.gov/publications/pdf/FHA_SingleFamilyIns_dec2012.pdf",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        ". "
                    ],
                    ["Values are adjusted for inflation using the personal consumption expenditures (PCE) price index, retrieved from ",
                        html.A("FRED, Federal Reserve Bank of St. Louis",
                               href="https://fred.stlouisfed.org/",
                               target="_blank", rel="noopener noreferrer", style={"color": "#3b82f6", "textDecoration": "underline"}),
                        "."
                    ],
                ]),
            ],
            id="section-mmi-capital",
            style={"marginBottom": "24px"},
        )
    )

    return html.Div(sections)


def render_stats_items() -> list[html.Li]:
    if DATA_CACHE["load_error"]:
        return [
            html.Li("Endorsements rows: 0"),
            html.Li("Capratio rows: 0"),
            html.Li("Claims rows: 0"),
            html.Li("Credit risk rows: 0"),
            html.Li("Credit subsidy rows: 0"),
            html.Li("Loaded at: Failed"),
        ]

    loaded_at = DATA_CACHE["loaded_at"]
    loaded_at_text = loaded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if loaded_at else "Loading..."
    endorsements_rows = len(DATA_CACHE["endorsements_df"]) if DATA_CACHE["endorsements_df"] is not None else 0
    capratio_rows = len(DATA_CACHE["capratio_df"]) if DATA_CACHE["capratio_df"] is not None else 0
    claims_rows = len(DATA_CACHE["claims_df"]) if DATA_CACHE["claims_df"] is not None else 0
    creditrisk_rows = len(DATA_CACHE["creditrisk_df"]) if DATA_CACHE["creditrisk_df"] is not None else 0
    creditsubsidy_rows = len(DATA_CACHE["creditsubsidy_df"]) if DATA_CACHE["creditsubsidy_df"] is not None else 0
    chart_count = 9 if DATA_CACHE["creditsubsidy_df"] is not None else 8
    return [
        html.Li(f"Endorsements rows: {endorsements_rows:,}"),
        html.Li(f"Capratio rows: {capratio_rows:,}"),
        html.Li(f"Claims rows: {claims_rows:,}"),
        html.Li(f"Credit risk rows: {creditrisk_rows:,}"),
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
app.title = "FHA"

# Add Font Awesome for social icons
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


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
                            html.Div(
                                [
                                    html.H1("FHA History", style={"marginBottom": "4px", "display": "inline"}),
                                    html.Span("*", style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "bold", "marginLeft": "4px"}),
                                ],
                                style={"display": "flex", "alignItems": "baseline"}
                            ),
                            html.Div(
                                [
                                    html.Span(f"© {datetime.now().year} Kevin Park", style={"color": "#64748b", "fontSize": "0.9rem", "marginRight": "12px"}),
                                    
                                ],
                                style={"display": "flex", "alignItems": "center"}
                            ),
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
            className="site-header",
        ),
        # Section jump navigation
        html.Nav(
            html.Div(
                [
                    html.A("Originations", href="#section-originations", className="nav-link"),
                    html.A("Credit Risk", href="#section-credit-risk", className="nav-link"),
                    html.A("Claim Rates", href="#section-claim-rates", className="nav-link"),
                    html.A("Credit Subsidy", href="#section-credit-subsidy", className="nav-link"),
                    html.A("MMI Capital", href="#section-mmi-capital", className="nav-link"),
                ],
                className="nav-inner",
            ),
            className="section-nav",
        ),
        # Main content
        html.Div(
            [
                # Intro text
                html.Div(
                    [
                        html.P(
                            "The Federal Housing Administration (FHA) was created by the National Housing Act of 1934."
                            "Title II of the Act creates 'a system of mutual mortgage insurance. in which borrowers pay"
                            "insurance premiums into a fund to compensate lenders in case of default. The role of the federal"
                            "government was not to displace the private market, but 'to establish the conditions under"
                            "which private initiative could feed itself and multiply its own benefits. (Eccles 1951). The"
                            "Mutual Mortgage Insurance Fund currently guarantees $1.6 trillion in home loans to"
                            "households who might not otherwise be able to own their home."
                        ),
                        html.Details(
                            [
                                html.Summary(
                                    "*",
                                    style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "bold", "display": "inline", "marginLeft": "2px", "marginRight": "2px"}
                                ),
                                html.P(
                                    "A 'mutual' insurance company is one owned by its policyholders and where surplus profits are redistributed back to customers"
                                    "FHA paid such dividends between 1943 and 1991 to borrowers who paid off their loans"
                                    "but payments were suspended due to the financial conditional of the Fund. However, FHA is still authorized"
                                    "to pay distributive shares 'in such manner and amount' determined 'to be equitable and in accordance"
                                    "with sound actuarial and accounting practice.'",
                                    style={"color": "#64748b", "fontSize": "0.85rem", "marginTop": "8px", "marginBottom": "0"}
                                ),
                            ],
                            style={"display": "inline"}
                        )
                        html.P(
                            "This website provides an historical overview of FHA's single-family forward mortgage program."
                        ),
                        html.Details(
                            [
                                html.Summary(
                                    "*",
                                    style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "bold", "display": "inline", "marginLeft": "2px", "marginRight": "2px"}
                                ),
                                html.P(
                                    "Forward loans exclude FHA's Home Equity Conversion Mortgage (HECM), or reverse mortgage, program in which senior homeowners extract equity from their properties.",
                                    style={"color": "#64748b", "fontSize": "0.85rem", "marginTop": "8px", "marginBottom": "0"}
                                ),
                            ],
                            style={"display": "inline"}
                        )
                        html.P(
                            "The analysis and views shown here are those of the author and do not represent any current or former employer. "
                            "The website is not affiliated with FHA or any government agency.",
                            style={"display": "inline"}
                        ),

                    ],
                ),
                # Dashboard sections
                html.Div(
                    id="sections-container",
                    children=[],
                ),
                # Status box and Load summary - moved to bottom
                html.Div(
                    id="status-box",
                    children="Loading chart data...",
                    style={
                        "backgroundColor": "#eff6ff",
                        "border": "1px solid #93c5fd",
                        "padding": "12px 14px",
                        "borderRadius": "8px",
                        "marginTop": "32px",
                        "marginBottom": "24px",
                        "fontSize": "0.95rem",
                    },
                ),
                # About section
                html.Details(
                    [
                        html.Summary(
                            "About Me",
                            style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "500", "fontSize": "1.1rem", "marginBottom": "12px"}
                        ),
                        html.Div(
                            [
                                # Left column: Image and caption
                                html.Div(
                                    [
                                        html.Img(
                                            src="assets/IMG_20250531_125826.jpg",
                                            style={
                                                "width": "180px",
                                                "height": "auto",
                                                "borderRadius": "8px",
                                                "marginBottom": "12px",
                                                "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)",
                                            }
                                        ),
                                        html.Figcaption(
                                            "Dr. Park in front of the first existing house to be bought with an FHA-insured home loan. "
                                            "The 1940 Census reports Amos and Elsie Herbert owned the house located at 319 East Howell Ave in Alexandria, VA.",
                                            style={
                                                "width": "180px",
                                                "fontSize": "0.75rem",
                                                "color": "#64748b",
                                                "fontStyle": "italic",
                                                "textAlign": "center",
                                            }
                                        ),
                                    ],
                                    style={"flex": "0 0 auto", "marginRight": "24px", "minWidth": "180px"},
                                    className="about-image-col",
                                ),
                                # Right column: Text and connect icons
                                html.Div(
                                    [
                                        html.P(
                                            "Kevin Park is an economist specializing in mortgage insurance and housing finance policy. "
                                            "He has a PhD in City and Regional Planning from UNC-Chapel Hill, writing his dissertation on mortgage insurance during the Great Financial Crisis. "
                                            "He led work on FHA's TOTAL Mortgage Scorecard underwriting algorithm from 2015 to 2022 and currently works in the private mortgage insurance industry.",
                                            style={"marginBottom": "16px", "lineHeight": "1.6"},
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Connect: ", style={"fontWeight": "500", "marginRight": "8px"}),
                                                html.A(
                                                    html.I(className="fab fa-linkedin", style={"fontSize": "1.2rem", "color": "#0A66C2"}),
                                                    href="https://www.linkedin.com/in/kevinapark/",
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    style={"marginRight": "12px", "textDecoration": "none", "transition": "transform 0.2s", "cursor": "pointer"},
                                                    title="LinkedIn"
                                                ),
                                                html.A(
                                                    html.I(className="fas fa-graduation-cap", style={"fontSize": "1.2rem", "color": "#4285F4"}),
                                                    href="https://scholar.google.com/citations?user=4mUgOuMAAAAJ&hl=en",
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    style={"marginRight": "12px", "textDecoration": "none", "transition": "transform 0.2s", "cursor": "pointer"},
                                                    title="Google Scholar"
                                                ),
                                                html.A(
                                                    html.I(className="fas fa-envelope", style={"fontSize": "1.2rem", "color": "#EA4335"}),
                                                    href="mailto:kevinapark@gmail.com",
                                                    style={"textDecoration": "none", "transition": "transform 0.2s", "cursor": "pointer"},
                                                    title="Email"
                                                ),
                                            ],
                                            style={"display": "flex", "alignItems": "center"}
                                        ),
                                    ],
                                    style={"flex": "1 1 auto"}
                                )
                            ],
                            style={"display": "flex", "gap": "24px", "alignItems": "flex-start"},
                            className="about-flex",
                        ),
                    ],
                    style={"marginBottom": "24px"}
                ),
                # Summary stats
                html.Details(
                    [
                        html.Summary(
                            "Load summary",
                            style={"cursor": "pointer", "color": "#3b82f6", "fontWeight": "500", "marginBottom": "12px", "fontSize": "0.9rem"},
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
                                "fontSize": "0.85rem",
                            },
                        ),
                    ],
                    style={"marginBottom": "24px"},
                ),
                dcc.Interval(id="initial-load", interval=300, n_intervals=0, max_intervals=1),
            ],
            style={
                "maxWidth": "1440px",
                "margin": "0 auto",
                "padding": "0 18px 24px 18px",
            },
            className="main-content",
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