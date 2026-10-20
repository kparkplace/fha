
#%%
from plotnine import ggplot, aes, geom_line, geom_hline, theme_classic, labs, theme_minimal, element_blank, theme
import pandas as pd

from pathlib import Path
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
     + labs(x='Year', y='Percent')
     + theme(
         legend_title=element_blank(),
     )
)
p
# %%
# Inflation-adjusted data prep for separate charts
adj_metrics = ("econ_value", "cap_resources", "cashflow_npv")
adj_cols = [f"{c}_in_latest_dollars" for c in adj_metrics]
available = [c for c in adj_cols if c in df.columns]

if not available:
    print("No inflation-adjusted columns found; skipping adjusted-values plots")
else:
    m_adj = df.melt(
        id_vars=["year", "source"],
        value_vars=available,
        var_name="metric",
        value_name="value",
    )
    m_adj = m_adj.dropna(subset=["value"])
    m_adj["metric"] = (
        m_adj["metric"]
        .str.replace("_in_latest_dollars", "", regex=False)
        .str.replace("_", " ")
        .str.title()
    )

# %%
if "econ_value_in_latest_dollars" in available:
    econ_value_adj = m_adj[m_adj["metric"] == "Econ Value"].copy()

    p_adj_econ_value = (
        ggplot(econ_value_adj, aes(x="year", y="value", color="source", group="source"))
        + geom_line()
        + labs(
            y="Inflation-Adjusted",
            x="Fiscal Year",
        )
        + theme_minimal()
        + theme(
            legend_title=element_blank(),
        )
    )

p_adj_econ_value

# %%
if "cap_resources_in_latest_dollars" in available:
    cap_resources_adj = m_adj[m_adj["metric"] == "Cap Resources"].copy()

    p_adj_cap_resources = (
        ggplot(cap_resources_adj, aes(x="year", y="value", color="source", group="source"))
        + geom_line()
        + labs(
            y="Inflation-Adjusted",
            x="Fiscal Year",
        )
        + theme_minimal()
    )

p_adj_cap_resources

# %%
if "cashflow_npv_in_latest_dollars" in available:
    cashflow_npv_adj = m_adj[m_adj["metric"] == "Cashflow Npv"].copy()

    p_adj_cashflow_npv = (
        ggplot(cashflow_npv_adj, aes(x="year", y="value", color="source", group="source"))
        + geom_line()
        + labs(
            y="Inflation-Adjusted",
            x="Fiscal Year",
        )
        + theme_minimal()
    )

p_adj_cashflow_npv




# %%
