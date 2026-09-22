from pathlib import Path

import pandas as pd
from plotnine import aes, element_text, geom_bar, ggplot, guide_legend, labs, scale_fill_manual, theme, theme_classic


REPO_ROOT = Path(__file__).resolve().parent
DATA_PATH = REPO_ROOT / 'cum_claims.parquet'
OUTPUT_PATH = REPO_ROOT / 'cum_claims.png'


def build_plot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'metric' in df.columns:
        df = df[df['metric'] == 'cum_clm_rate'].copy()

    df['cohort'] = pd.to_numeric(df['cohort'], errors='coerce')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['sourcefy'] = pd.to_numeric(df['sourcefy'], errors='coerce')

    idx = df.groupby(['cohort', 'year'])['sourcefy'].idxmax()
    df_latest = df.loc[idx].reset_index(drop=True)

    last_fy = df_latest['sourcefy'].max()
    df_latest['forecast'] = (df_latest['cohort'] + df_latest['year']) > last_fy

    max_values = df_latest.groupby(['cohort', 'forecast'], as_index=False)['value'].max()
    observed = max_values[max_values['forecast'] == False].copy()
    total = max_values.groupby('cohort', as_index=False)['value'].max().rename(columns={'value': 'total_value'})

    plot_df = observed.merge(total, on='cohort', how='left')
    plot_df['forecast_value'] = plot_df['total_value'] - plot_df['value']

    plot_df_long = pd.melt(
        plot_df,
        id_vars=['cohort'],
        value_vars=['value', 'forecast_value'],
        var_name='segment',
        value_name='bar_value',
    )
    plot_df_long['forecast'] = plot_df_long['segment'] == 'forecast_value'
    plot_df_long['forecast'] = pd.Categorical(plot_df_long['forecast'], categories=[True, False], ordered=True)
    return plot_df_long.sort_values(['cohort', 'forecast'])


def build_chart(plot_df_long: pd.DataFrame):
    return (
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
            caption='Created by Kevin Park\nSource: FHA Actuarial Reviews',
        )
        + theme_classic()
        + theme(axis_text_x=element_text(rotation=90, hjust=1), legend_position='top')
    )


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f'Missing parquet input: {DATA_PATH}. Run fha_cum_claims_data.py first.')

    df = pd.read_parquet(DATA_PATH)
    plot_df_long = build_plot_dataframe(df)
    chart = build_chart(plot_df_long)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    chart.save(OUTPUT_PATH, width=10.8, height=10.8, dpi=100)
    print(f'Created {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
