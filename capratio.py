
#%%
from plotnine import facet_wrap, ggplot, aes, geom_line, geom_hline, theme_classic, labs, facet_wrap, theme_minimal
import pandas as pd

from pathlib import Path
import os
import numpy as np
df = pd.read_parquet(Path(__file__).resolve().parent / "Data/capratio.parquet")

# %%
# Plot capital ratios by source (plotnine)

# try to compute `cap_ratio` if missing
if 'cap_ratio' not in df.columns and {'capital', 'value', 'ratio'}.issubset(df.columns):
    df['cap_ratio'] = 100 * df['capital'] / (df['value'] / (df['ratio'] / 100))

# try to compute `cap_ratio_unamort` if missing and iif_unamort exists
if 'cap_ratio_unamort' not in df.columns and 'iif_unamort' in df.columns and 'ratio' in df.columns and 'capital' in df.columns:
    df['cap_ratio_unamort'] = 100 * df['capital'] / (df['iif_unamort'] / (df['ratio'] / 100))

metrics = [c for c in ['cap_ratio', 'cap_ratio_unamort'] if c in df.columns]
if not metrics:
    raise RuntimeError("No `cap_ratio` or `cap_ratio_unamort` columns present or derivable.")

m = df.melt(id_vars=['year', 'source'], value_vars=metrics, var_name='metric', value_name='value').dropna(subset=['value'])

p = (ggplot(m, aes('year', 'value', color='source', linetype='metric'))
     + geom_hline(aes(yintercept=0), linetype='dashed')
     + geom_line(size=1)
     + theme_classic()
     + labs(x='Year', y='Percent', title='Capital Ratios by Source', caption='source: combined_df')
)
p
# %%
# Inflation-adjusted faceted plot (inline for Interactive window)
adj_metrics = ("econ_value", "cap_resources", "cashflow_npv")
adj_cols = [f"{c}_in_latest_dollars" for c in adj_metrics]
available = [c for c in adj_cols if c in df.columns]
if not available:
    print("No inflation-adjusted columns found; skipping adjusted-values plot")
else:
    m_adj = df.melt(id_vars=["year", "source"], value_vars=available, var_name="metric", value_name="value")
    m_adj = m_adj.dropna(subset=["value"])
    m_adj["metric"] = m_adj["metric"].str.replace("_in_latest_dollars", "", regex=False).str.replace("_", " ").str.title()

    p_adj = (
        ggplot(m_adj, aes(x="year", y="value", color="source", group="source"))
        + geom_line()
        + facet_wrap("~metric", scales="free_y")
        + labs(title="Inflation-adjusted values (latest dollars)", y="Value (latest dollars)", x="Year")
        + theme_minimal()
    )

p_adj




# %%
