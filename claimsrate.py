#%%
from pathlib import Path

import pandas as pd
from plotnine import (
    aes,
    element_text,
    geom_bar,
    geom_line,
    geom_point,
    ggplot,
    guide_legend,
    labs,
    scale_fill_manual,
    theme,
    theme_classic,
)


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"

#%%
# Load input data (will raise if missing)
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Missing parquet input: {DATA_PATH}. Run data_claims.py first.")

df = pd.read_parquet(DATA_PATH)

#%%
# Prepare plotting dataframe (flattened from previous helper functions)
plot_df = df.copy()
if 'metric' in plot_df.columns:
    plot_df = plot_df[plot_df['metric'] == 'cum_clm_rate'].copy()

plot_df['cohort'] = pd.to_numeric(plot_df['cohort'], errors='coerce')
plot_df['year'] = pd.to_numeric(plot_df['year'], errors='coerce')
plot_df['sourcefy'] = pd.to_numeric(plot_df['sourcefy'], errors='coerce')

# pick most recent sourcefy for each cohort/year
idx = plot_df.groupby(['cohort', 'year'])['sourcefy'].idxmax()
plot_df_latest = plot_df.loc[idx].reset_index(drop=True)

last_fy = plot_df_latest['sourcefy'].max()
plot_df_latest['forecast'] = (plot_df_latest['cohort'] + plot_df_latest['year']) > last_fy

max_values = plot_df_latest.groupby(['cohort', 'forecast'], as_index=False)['value'].max()
observed = max_values[max_values['forecast'] == False].copy()
total = max_values.groupby('cohort', as_index=False)['value'].max().rename(columns={'value': 'total_value'})

plot_df_combined = observed.merge(total, on='cohort', how='left')
plot_df_combined['forecast_value'] = plot_df_combined['total_value'] - plot_df_combined['value']

plot_df_long = pd.melt(
    plot_df_combined,
    id_vars=['cohort'],
    value_vars=['value', 'forecast_value'],
    var_name='segment',
    value_name='bar_value',
)
plot_df_long['forecast'] = plot_df_long['segment'] == 'forecast_value'
plot_df_long['forecast'] = pd.Categorical(plot_df_long['forecast'], categories=[True, False], ordered=True)
plot_df_long = plot_df_long.sort_values(['cohort', 'forecast']).reset_index(drop=True)

#%%
# Build and display chart inline
chart = (
    ggplot(plot_df_long, aes(x='factor(cohort)', y='bar_value', fill='forecast'))
    + geom_bar(stat='identity', position='stack')
    + scale_fill_manual(
        values={False: '#4575b4', True: '#a6bddb'},
        labels=['Forecasted', 'Observed'],
        guide=guide_legend(reverse=True),
    )
    + labs(
        x='Cohort',
        y='Cumulative Claim Rate',
        fill='',
        caption='Source: FHA Actuarial Reviews',
    )
    + theme_classic()
    + theme(axis_text_x=element_text(rotation=90, hjust=1), legend_position='top')
)

chart

#%%
# Line plot: observed cumulative claim-rate paths by cohort (x=year, y=value)
obs_ts = plot_df_latest[plot_df_latest['forecast'] == False].copy()
if obs_ts.empty:
    print('No observed time-series rows available to plot.')
else:
    # ensure numeric year and sort
    obs_ts['year'] = pd.to_numeric(obs_ts['year'], errors='coerce')
    obs_ts = obs_ts.dropna(subset=['year', 'value'])
    obs_ts = obs_ts.sort_values(['cohort', 'year'])

    line_chart = (
        ggplot(obs_ts, aes(x='year', y='value', color='factor(cohort)', group='cohort'))
        + geom_line()
        + labs(x='Years Since Origination', y='Cumulative Claim Rate (%)', color='Cohort', caption='Source: FHA Actuarial Reviews',)
        + theme_classic()
        + theme(axis_text_x=element_text(rotation=0, hjust=0.5), legend_position='right')
    )

line_chart

# %%
