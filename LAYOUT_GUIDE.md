# FHA Dashboard Layout Guide

## New Page Structure

```
┌─────────────────────────────────────────────────────────┐
│  Header (Fixed, white background)                       │
│  FHA Single-Family Forward Loans Dashboard              │
│  Created by Kevin Park (kevinapark@gmail.com)           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Main Content (max-width: 1440px, centered)              │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Intro box (light blue background)                │   │
│ │ The Federal Housing Administration (FHA) was...  │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Status box (green/yellow/red)                    │   │
│ │ Data loaded successfully.                        │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ <details> Data summary                           │   │
│ │   <ul> Stats (collapsible)                       │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ SECTION 1: MMI Fund Capital                      │   │
│ │ ─────────────────────────────────────────────    │   │
│ │ The capital ratio measures the economic...      │   │
│ │                                                  │   │
│ │ ┌──────────────────────────────────────────┐   │   │
│ │ │ Chart Card: Capital Ratios by Source     │   │   │
│ │ │ [Chart]                                  │   │   │
│ │ │ <details> Show data table                │   │   │
│ │ └──────────────────────────────────────────┘   │   │
│ │                                                  │   │
│ │ ┌──────────────┬──────────────┬────────────┐   │   │
│ │ │ Chart Card:  │ Chart Card:  │ Chart Card:│   │   │
│ │ │ Economic     │ Capital      │ Cashflow   │   │   │
│ │ │ Value        │ Resources    │ NPV        │   │   │
│ │ │ [Chart]      │ [Chart]      │ [Chart]    │   │   │
│ │ └──────────────┴──────────────┴────────────┘   │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ SECTION 2: Cumulative Claim Rates               │   │
│ │ ─────────────────────────────────────────────    │   │
│ │ Claims data tracks the rate at which...         │   │
│ │                                                  │   │
│ │ ┌──────────────┬──────────────────────────┐    │   │
│ │ │ Chart Card:  │ Chart Card:              │    │   │
│ │ │ Observed     │ Observed & Forecasted    │    │   │
│ │ │ Claim Rates  │ Claim Rates              │    │   │
│ │ │ [Chart]      │ [Chart]                  │    │   │
│ │ └──────────────┴──────────────────────────┘    │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ SECTION 3: Credit Subsidy by Cohort             │   │
│ │ ─────────────────────────────────────────────    │   │
│ │ The credit subsidy rate represents the...       │   │
│ │                                                  │   │
│ │ ┌──────────────────────────────────────────┐   │   │
│ │ │ Chart Card: Credit Subsidy Rates         │   │   │
│ │ │ [Chart]                                  │   │   │
│ │ │ <details> Show data table                │   │   │
│ │ └──────────────────────────────────────────┘   │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Component Functions

### `build_section_header(title, description)`
Creates a section title with bottom border and description text.

**Returns:** `html.Div` with:
- `<h2>` title
- `<p>` description (optional)
- Bottom border separator

**Example:**
```python
build_section_header(
    "MMI Fund Capital",
    "The capital ratio measures the economic strength..."
)
```

### `build_chart_card(title, description, figure, featured=False)`
Creates a chart card with title, description, interactive chart, and collapsible data table.

**Returns:** `html.Div` with:
- `<h3>` title
- `<p>` description
- `<dcc.Graph>` - interactive Plotly chart
- `<details>` - collapsible data table (placeholder for now)

**Styling:**
- White background
- Subtle border and shadow
- 16px padding
- Responsive to screen size

## Adding a New Section

### Step 1: Create a figure-building function (if needed)
```python
def build_new_chart_figure(df):
    # Create and return a plotly figure
    fig = go.Figure(...)
    return apply_figure_layout(fig, ...)
```

### Step 2: Add section to `build_dashboard_sections()`
```python
sections.append(
    html.Div(
        [
            build_section_header(
                "Section Title",
                "Descriptive text about this section. Explain what data is shown "
                "and why it matters to understanding the MMI Fund.",
            ),
            html.Div(
                [
                    build_chart_card(
                        "Chart 1 Title",
                        "Chart 1 description",
                        build_new_chart_figure(df),
                    ),
                    build_chart_card(
                        "Chart 2 Title", 
                        "Chart 2 description",
                        build_another_figure(df),
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

## Styling Palette

| Element | Color | RGB | Usage |
|---------|-------|-----|-------|
| Heading | `#1e293b` | Slate 900 | Section & chart titles |
| Text | `#475569` | Slate 700 | Chart descriptions |
| Secondary | `#64748b` | Slate 500 | Subtitle, attribution |
| Border | `#e2e8f0` | Slate 200 | Section dividers, card borders |
| Background | `#f8fafc` | Slate 50 | Section backgrounds |
| Success | `#ecfdf3` | Green 50 | Success message background |
| Warning | `#fffbeb` | Amber 50 | Warning message background |
| Error | `#fef2f2` | Red 50 | Error message background |

## Spacing System

- **Between sections**: 24px (`marginBottom`)
- **Between cards in grid**: 14px (`gap`)
- **Card padding**: 16px
- **Section header bottom padding**: 12px
- **Chart bottom margin**: 10px

## Responsive Behavior

- Chart grid uses CSS Grid with `auto-fit` and `minmax(420px, 1fr)`
- Each chart card stretches to fill available space
- On mobile, each card takes full width
- On tablet/desktop, multiple cards per row depending on screen width
- Max width: 1440px (centered)
- Side padding: 18px

## Data Loading

- `dcc.Interval` triggers on page load (300ms, max 1 interval)
- Callback `load_and_render()` populates all sections
- Sections only render after data is successfully loaded
- Status box shows load state (loading, success, warning, error)
