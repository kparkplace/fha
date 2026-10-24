from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "creditrisk.parquet"
df_creditrisk = pd.read_parquet(DATA_PATH).copy()

print(f"Loaded {len(df_creditrisk)} rows")
print(f"Date range: {df_creditrisk['Date'].min()} to {df_creditrisk['Date'].max()}")
print(f"By source:\n{df_creditrisk.groupby('Source')['Date'].agg(['min', 'max', 'count'])}")

df_davis = df_creditrisk[df_creditrisk['Source'] == 'Davis et al. (2023)'].sort_values('Date')
df_aei = df_creditrisk[df_creditrisk['Source'] == 'American Enterprise Institute'].sort_values('Date')

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_davis['Date'], y=df_davis['Risk'],
    mode='lines',
    name='Davis et al. (2023)',
    line=dict(color='#1f77b4'),
    hovertemplate='<b>Davis et al. (2023)</b><br>Year: %{x|%Y}<br>Risk: %{y:.3f}<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=df_aei['Date'], y=df_aei['Risk'],
    mode='lines',
    name='American Enterprise Institute',
    line=dict(color='#ff7f0e'),
    hovertemplate='<b>American Enterprise Institute</b><br>Date: %{x|%b %Y}<br>Risk: %{y:.3f}<extra></extra>'
))

fig.update_layout(
    title='FHA Mortgage Default Risk',
    xaxis=dict(title='Date'),
    yaxis=dict(title='Default Risk'),
    hovermode='x unified',
    legend=dict(x=0.5, y=-0.15, xanchor='center', yanchor='top')
)

fig
