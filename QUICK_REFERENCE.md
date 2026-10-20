# Quick Reference: Adding Sections to FHA Dashboard

## The Two-Step Process

### Step 1: Create Your Figure Function
```python
def build_my_chart_figure(df: pd.DataFrame) -> go.Figure:
    """Build my custom chart."""
    # ... prepare data ...
    fig = px.line(plot_df, x="x_col", y="y_col")
    return apply_figure_layout(
        fig,
        title="My Chart Title",
        y_axis_title="Y Label",
        height=420
    )
```

### Step 2: Add to `build_dashboard_sections()`
```python
# In build_dashboard_sections(), add to sections list:
sections.append(
    html.Div(
        [
            build_section_header(
                "Section Title",
                "One or two sentences describing what this section shows.",
            ),
            html.Div(
                [
                    build_chart_card(
                        "Chart Title",
                        "Description of chart",
                        build_my_chart_figure(my_df),
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

That's it! The chart will automatically appear in the dashboard.

---

## Component Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `build_section_header(title, desc)` | Section title + description | `html.Div` |
| `build_chart_card(title, desc, fig)` | Chart card with title, chart, collapsible table | `html.Div` |
| `apply_figure_layout(fig, ...)` | Add styling to plotly figure | `go.Figure` |

---

## Current Sections

1. **MMI Fund Capital** — 4 charts (Capital Ratios, Economic Value, Capital Resources, Cashflow)
2. **Cumulative Claim Rates** — 2 charts (Observed, Forecasted)
3. **Credit Subsidy by Cohort** — 1 chart (Current vs. Original)

---

## Styling Quick Reference

```python
# Single chart section
html.Div(
    [build_chart_card(...)],
    style={"marginBottom": "16px"},
)

# Grid of multiple charts
html.Div(
    [
        build_chart_card(...),
        build_chart_card(...),
    ],
    style={
        "display": "grid",
        "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))",
        "gap": "14px",
        "alignItems": "start",
    },
)

# Section wrapper
html.Div(
    [...],
    style={"marginBottom": "24px"},  # Space after section
)
```

---

## Common Figure Types

```python
# Line chart
fig = px.line(df, x="year", y="value", color="category")

# Bar chart
fig = px.bar(df, x="category", y="value")

# Scatter with trend
fig = px.scatter(df, x="x", y="y")
fig.add_trendline(y="y", method="ols")

# Multiple lines
fig = px.line(df, x="year", y=["value1", "value2"])

# Chart with reference line
fig = px.line(...)
fig.add_hline(y=2.0, line_dash="dash", line_color="red")

# Stacked bar
fig = px.bar(df, x="year", y="value", color="category", 
             barmode="stack")
```

---

## Styling Your Chart Card Description

```python
# Short description (one line)
build_chart_card("Title", "This chart shows...", fig)

# Longer description (multiple lines)
build_chart_card(
    "Title",
    "The first part of the description. "
    "This continues on multiple lines "
    "to provide more context.",
    fig
)

# Description with technical details
build_chart_card(
    "Title",
    "Description. "
    "Data source: White House OMB Credit Supplement. "
    "Updated annually.",
    fig
)
```

---

## Chart Height Reference

- **Small chart**: `height=360`
- **Standard chart**: `height=420` (recommended)
- **Large chart**: `height=500`
- **Very large chart**: `height=600`

Use consistent heights within a section for visual balance.

---

## Example: Two-Chart Section

```python
# Add to sections list in build_dashboard_sections()
sections.append(
    html.Div(
        [
            build_section_header(
                "Portfolio Analysis",
                "These charts show the composition and trends of the FHA portfolio.",
            ),
            html.Div(
                [
                    build_chart_card(
                        "Loan Distribution by Year",
                        "Count of active loans by origination year.",
                        build_portfolio_by_cohort(df),
                    ),
                    build_chart_card(
                        "Average Loan Balance Trend",
                        "Average unpaid principal balance over time.",
                        build_avg_balance_trend(df),
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

---

## Collapsible Data Table (Ready for Implementation)

Each chart card automatically includes this HTML:

```html
<details>
  <summary>Show data table</summary>
  <div>Data table generation coming soon</div>
</details>
```

To add actual table rendering:

1. Create a function to convert figure data to HTML table
2. Replace "Data table generation coming soon" with actual table HTML
3. Add styling to match card theme

---

## Testing Your New Section

1. **Syntax check**: `python -m py_compile app.py`
2. **Run dashboard**: `python app.py`
3. **Visit**: `http://localhost:8050`
4. **Check**:
   - Section appears in correct order
   - Title and description display correctly
   - Chart loads and is interactive
   - Responsive on mobile/tablet

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Chart doesn't appear | Check that figure function doesn't return `None` |
| Section in wrong place | Move `sections.append()` to different line |
| Styling looks off | Verify you used correct `style=` dict |
| Colors not consistent | Use hex colors from palette (see LAYOUT_GUIDE.md) |
| Mobile layout broken | Check `gridTemplateColumns` has `repeat(auto-fit, ...)` |

---

## Need More Help?

- **See working examples**: Open [SECTION_EXAMPLES.md](/D:/Data/FHA/SECTION_EXAMPLES.md)
- **Full layout reference**: Open [LAYOUT_GUIDE.md](/D:/Data/FHA/LAYOUT_GUIDE.md)
- **Current sections**: See `build_dashboard_sections()` in [app.py](/D:/Data/FHA/app.py)
- **Design philosophy**: See [DASHBOARD_REDESIGN.md](/C:/Users/kevin/.copilot/session-state/35e7435b-a525-4ff1-9346-34850a767c59/files/DASHBOARD_REDESIGN.md)

---

**That's all you need to know to add new sections!** 🎉
