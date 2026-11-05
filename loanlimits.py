"""FHA Loan Limits visualization."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "loanlimits.parquet"


def load_loanlimits_data(path: str | Path | None = None) -> pd.DataFrame:
    """Load loan limits data from parquet."""
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    return pd.read_parquet(data_path).copy()


def build_loanlimits_figure(loanlimits_df: pd.DataFrame | None) -> go.Figure | None:
    """Build interactive line chart of FHA loan limits over time.
    
    Shows maximum single-family loan limits by:
    - Year (x-axis)
    - Loan limit in dollars (y-axis)
    - Source (color - different data sources)
    - Type (linestyle - S=Standard, H=High Cost)
    """
    if loanlimits_df is None or loanlimits_df.empty:
        return None

    # Define line styles for S and H types
    linestyle_map = {
        'S': 'solid',      # Standard
        'H': 'dash',       # High Cost (dashed to distinguish)
    }
    
    limit_type_labels = {
        'S': 'Standard Limit',
        'H': 'High Cost Limit'
    }
    
    # Define source order and colors
    source_order = ['Vandell (1995)', 'FHA Mortgagee Letters', 'CHUMS', 'HPI-adjusted 1938 limit', 'Standard Limit', 'High Cost Limit']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {src: colors[i % len(colors)] for i, src in enumerate(source_order)}
    
    # Make HPI-adjusted line light gray
    color_map['HPI-adjusted 1938 limit'] = '#d3d3d3'
    
    fig = go.Figure()
    seen_pairs: set[tuple[str, str]] = set()
    
    # Add traces in source order
    for source in source_order:
        if source not in loanlimits_df['source'].unique():
            continue
            
        for loan_type in ['S', 'H']:
            mask = (loanlimits_df['source'] == source) & (loanlimits_df['type'] == loan_type)
            rows = loanlimits_df.loc[mask].sort_values('year')
            
            if rows.empty:
                continue
            
            pair = (source, loan_type)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            # Create legend name with source only (type shown separately via linestyle)
            linestyle = linestyle_map[loan_type]
            
            fig.add_trace(
                go.Scatter(
                    x=rows['year'].tolist(),
                    y=rows['value'].tolist(),
                    mode='lines',
                    name=source,
                    line={'color': color_map[source], 'dash': linestyle, 'width': 2},
                    legendgroup=source,
                    showlegend=(loan_type == 'S'),  # Only show source once (on S type)
                    hovertemplate=(
                        f"<b>{source}</b><br>"
                        f"{limit_type_labels[loan_type]}: $%{{y:,.0f}}<extra></extra>"
                    ),
                )
            )
    
    # Add dummy traces for limit type legend (Standard and High Cost)
    for loan_type in ['S', 'H']:
        linestyle = linestyle_map[loan_type]
        label = limit_type_labels[loan_type]
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='lines',
                name=label,
                line={'color': '#374151', 'dash': linestyle, 'width': 2},
                showlegend=True,
            )
        )
    
    # Apply consistent styling
    fig.update_layout(
        height=500,
        template='plotly_white',
        margin={'l': 50, 'r': 20, 't': 40, 'b': 80},
        legend={
            'orientation': 'h',
            'yanchor': 'top',
            'y': -0.15,
            'xanchor': 'left',
            'x': 0.01,
        },
        hovermode='x unified',
    )
    
    fig.update_xaxes(title_text='')
    fig.update_yaxes(
        title_text='Loan Limit ($) (Log Scale)', 
        type='log',
        ticktext=['$10K', '$100K', '$1M'],
        tickvals=[10000, 100000, 1000000]
    )
    
    return fig


if __name__ == "__main__":
    loanlimits_df = load_loanlimits_data()
    fig = build_loanlimits_figure(loanlimits_df)
    
    if fig:
        fig.show()
