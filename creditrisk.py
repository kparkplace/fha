from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "creditrisk.parquet"

def load_creditrisk_data(path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(path) if path is not None else DATA_PATH
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    return pd.read_parquet(data_path).copy()


def build_creditrisk_figure(creditrisk_df: pd.DataFrame | None) -> go.Figure | None:
    if creditrisk_df is None or creditrisk_df.empty:
        return None

    df_davis = creditrisk_df[creditrisk_df["Source"] == "Davis et al. (2023)"].sort_values("Date")
    df_aei = creditrisk_df[creditrisk_df["Source"] == "American Enterprise Institute"].sort_values("Date")
    if df_davis.empty and df_aei.empty:
        return None

    fig = go.Figure()

    if not df_davis.empty:
        fig.add_trace(
            go.Scatter(
                x=df_davis["Date"],
                y=df_davis["Risk"],
                mode="lines",
                name="Davis et al. (2023)",
                line={"color": "#1f77b4"},
                hovertemplate="<b>Davis et al. (2023)</b><br>Year: %{x|%Y}<br>Risk: %{y:.3f}<extra></extra>",
            )
        )

    if not df_aei.empty:
        fig.add_trace(
            go.Scatter(
                x=df_aei["Date"],
                y=df_aei["Risk"],
                mode="lines",
                name="American Enterprise Institute",
                line={"color": "#ff7f0e"},
                hovertemplate="<b>American Enterprise Institute</b><br>Date: %{x|%b %Y}<br>Risk: %{y:.3f}<extra></extra>",
            )
        )

    fig.update_layout(
        yaxis={"title": "Default Risk", "range": [20, 40]},
        hovermode="x unified",
        legend={"x": 0.5, "y": -0.15, "xanchor": "center", "yanchor": "top"},
        height=420,
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
    )
    fig.add_hline(y=0, line_dash="solid", line_color="#374151", line_width=1.25)
    return fig


if __name__ == "__main__":
    df_creditrisk = load_creditrisk_data()
    fig = build_creditrisk_figure(df_creditrisk)
    if fig is not None:
        fig.show()
