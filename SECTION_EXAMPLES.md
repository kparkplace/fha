# Examples: Adding New Sections to FHA Dashboard

This guide shows concrete examples of how to add new sections to the redesigned dashboard.

## Example 1: Adding a "Premium Revenue" Section

Let's say you want to add a section showing premium revenue trends over time.

### Step 1: Create a figure-building function

Add this to [app.py](/D:/Data/FHA/app.py) (after existing figure functions, before `build_section_header`):

```python
def build_premium_revenue_figure(capratio_df: pd.DataFrame) -> go.Figure:
    """Build premium revenue chart by source."""
    if "premium_revenue_in_latest_dollars" not in capratio_df.columns:
        return None
    
    # Filter and prepare data
    plot_df = capratio_df[["year", "source", "premium_revenue_in_latest_dollars"]].copy()
    plot_df = plot_df.dropna(subset=["premium_revenue_in_latest_dollars"])
    
    # Create figure
    fig = px.line(
        plot_df,
        x="year",
        y="premium_revenue_in_latest_dollars",
        color="source",
        title="Annual Premium Revenue by Source"
    )
    
    # Apply styling
    adjusted_y_axis_title = get_adjusted_y_axis_title()
    return apply_figure_layout(
        fig,
        title="Annual Premium Revenue by Source",
        y_axis_title=f"Revenue ({adjusted_y_axis_title})",
        x_axis_title="Year",
        height=420
    )
```

### Step 2: Add the section to `build_dashboard_sections()`

In [app.py](/D:/Data/FHA/app.py), in the `build_dashboard_sections()` function, add this after the "MMI Fund Capital" section:

```python
    # Premium Revenue Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Premium Revenue",
                    "Premium revenue is collected from borrowers on all FHA-insured mortgages. "
                    "These premiums support the MMI Fund and help cover administrative costs and claim losses. "
                    "Revenue trends reflect both new loan originations and the aging of existing portfolios.",
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Annual Premium Revenue",
                            "Premium revenue collected by FHA, adjusted for inflation to " + adjusted_y_axis_title + ".",
                            build_premium_revenue_figure(capratio_df),
                        ),
                    ],
                    style={"marginBottom": "16px"},
                ),
            ],
            style={"marginBottom": "24px"},
        )
    )
```

### Result

The new "Premium Revenue" section will appear between "MMI Fund Capital" and "Cumulative Claim Rates" sections, with:
- Clear section title
- Explanatory description
- Interactive chart
- Collapsible data table

---

## Example 2: Adding a "Risk Metrics" Section with Multiple Charts

Let's add a section with multiple related risk metrics.

### Step 1: Create figure functions

```python
def build_delinquency_rate_figure(claims_df: pd.DataFrame) -> go.Figure:
    """Build delinquency rates by year."""
    if "delinquency_rate" not in claims_df.columns:
        return None
    
    fig = px.bar(
        claims_df,
        x="year",
        y="delinquency_rate",
        title="Delinquency Rates"
    )
    return apply_figure_layout(
        fig,
        title="Delinquency Rates by Year",
        y_axis_title="Delinquency Rate (%)",
        x_axis_title="Year",
        height=420
    )


def build_default_severity_figure(claims_df: pd.DataFrame) -> go.Figure:
    """Build average loss per default claim."""
    if "avg_loss_per_claim" not in claims_df.columns:
        return None
    
    fig = px.line(
        claims_df,
        x="year",
        y="avg_loss_per_claim",
        title="Average Loss Per Claim"
    )
    return apply_figure_layout(
        fig,
        title="Average Loss Per Claim",
        y_axis_title="Loss Amount ($)",
        x_axis_title="Year",
        height=420
    )
```

### Step 2: Add the section

```python
    # Risk Metrics Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Risk Metrics",
                    "These metrics measure the credit quality of the MMI Fund portfolio and the financial impact of defaults. "
                    "Delinquency rates indicate borrower payment performance, while average loss per claim shows the severity "
                    "of losses when defaults occur.",
                ),
                html.Div(
                    [
                        build_chart_card(
                            "Delinquency Rates",
                            "Percentage of active loans that are 30+ days past due, by year.",
                            build_delinquency_rate_figure(claims_df),
                        ),
                        build_chart_card(
                            "Average Loss Per Claim",
                            "Average amount lost on each claim, reflecting property value trends and recovery rates.",
                            build_default_severity_figure(claims_df),
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
```

### Result

A new "Risk Metrics" section with:
- Clear, multi-part description explaining why these metrics matter
- Two charts in responsive grid (side-by-side on desktop, stacked on mobile)
- Each chart has its own title and description
- Professional styling consistent with existing sections

---

## Example 3: Adding a "Historical Comparison" Section with Advanced Features

A more complex example with multiple years/scenarios.

```python
def build_capital_ratio_history_figure(capratio_df: pd.DataFrame) -> go.Figure:
    """Build historical capital ratio with trend line."""
    plot_df = capratio_df[["year", "cap_ratio", "required_minimum"]].copy()
    plot_df = plot_df.sort_values("year")
    
    fig = go.Figure()
    
    # Add actual capital ratio
    fig.add_scatter(
        x=plot_df["year"],
        y=plot_df["cap_ratio"],
        mode="lines+markers",
        name="Actual Capital Ratio",
        line={"color": "#3b82f6", "width": 3},
        marker={"size": 8}
    )
    
    # Add minimum requirement
    fig.add_hline(
        y=2.0,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text="2% Minimum Requirement",
        annotation_position="right"
    )
    
    return apply_figure_layout(
        fig,
        title="Capital Ratio History with Regulatory Minimum",
        y_axis_title="Capital Ratio (%)",
        x_axis_title="Year",
        height=420
    )
```

Add to sections:

```python
    # Historical Comparison Section
    sections.append(
        html.Div(
            [
                build_section_header(
                    "Capital Ratio History",
                    "This chart shows the MMI Fund's capital ratio over time relative to the 2 percent minimum requirement "
                    "mandated by the National Affordable Housing Act. The Fund exceeded this minimum consistently until 2008-2012, "
                    "recovering thereafter. Understanding this history provides context for current reserve levels and risk management.",
                ),
                build_chart_card(
                    "Capital Ratio Trend",
                    "Actual capital ratio vs. minimum requirement. The red dashed line shows the federally mandated 2% floor.",
                    build_capital_ratio_history_figure(capratio_df),
                ),
                # Add a summary box with key statistics
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Lowest Ratio", style={"fontSize": "0.85rem", "color": "#64748b"}),
                                html.Div(f"{capratio_df['cap_ratio'].min():.2f}%", style={"fontSize": "1.5rem", "fontWeight": "bold", "color": "#1e293b"}),
                            ],
                            style={"flex": 1, "textAlign": "center"}
                        ),
                        html.Div(
                            [
                                html.Div("Current Ratio", style={"fontSize": "0.85rem", "color": "#64748b"}),
                                html.Div(f"{capratio_df['cap_ratio'].iloc[-1]:.2f}%", style={"fontSize": "1.5rem", "fontWeight": "bold", "color": "#1e293b"}),
                            ],
                            style={"flex": 1, "textAlign": "center"}
                        ),
                        html.Div(
                            [
                                html.Div("Years Below 2%", style={"fontSize": "0.85rem", "color": "#64748b"}),
                                html.Div(f"{(capratio_df['cap_ratio'] < 2.0).sum()}", style={"fontSize": "1.5rem", "fontWeight": "bold", "color": "#1e293b"}),
                            ],
                            style={"flex": 1, "textAlign": "center"}
                        ),
                    ],
                    style={
                        "display": "flex",
                        "gap": "16px",
                        "backgroundColor": "#f1f5f9",
                        "padding": "16px",
                        "borderRadius": "8px",
                        "marginTop": "12px",
                    }
                ),
            ],
            style={"marginBottom": "24px"},
        )
    )
```

### Result

A sophisticated "Capital Ratio History" section with:
- Descriptive header explaining historical context
- Interactive chart with actual vs. requirement comparison
- Summary statistics box (lowest ratio, current ratio, years below minimum)
- Professional data visualization with annotations
- Clear connection between visual and context

---

## Adding Sections: Checklist

When adding a new section, make sure you:

- [ ] Create figure-building function(s) if needed
- [ ] Handle `None` or empty dataframes gracefully
- [ ] Add appropriate descriptions to section header
- [ ] Add descriptive text to each chart card
- [ ] Use consistent styling (grid layout, spacing, colors)
- [ ] Test that the section renders correctly
- [ ] Commit changes with descriptive message

## Common Patterns

### Single Chart Section
- One chart per section
- Good for focused explanations

### Grid of Similar Charts
- 2-3 related charts per section
- Grid automatically adjusts to screen size

### Chart with Summary Metrics
- Main chart + summary box below
- Great for showing key statistics

### Multiple Time Series
- Line or scatter plots with multiple series
- Use different colors for each series
- Add legend and hover information

---

## Styling Tips

For consistent appearance:

1. **Section headings** - Always use `build_section_header()`
2. **Charts** - Always wrap in `build_chart_card()`
3. **Spacing** - Use `marginBottom: "24px"` between sections
4. **Grid gaps** - Use `gap: "14px"` between cards
5. **Colors** - Stick to the slate color palette (see [LAYOUT_GUIDE.md](/D:/Data/FHA/LAYOUT_GUIDE.md))

## Questions?

Refer to:
- [LAYOUT_GUIDE.md](/D:/Data/FHA/LAYOUT_GUIDE.md) — Full layout documentation
- [DASHBOARD_REDESIGN.md](/C:/Users/kevin/.copilot/session-state/35e7435b-a525-4ff1-9346-34850a767c59/files/DASHBOARD_REDESIGN.md) — Design summary and component reference
- Existing sections in [app.py](/D:/Data/FHA/app.py) — Working examples
