#%%
from io import BytesIO
from pathlib import Path
import re

import camelot
import pandas as pd
import pdfplumber
import requests

#%%
REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = REPO_ROOT / '_ActuarialReview'
OUTPUT_PATH = REPO_ROOT / 'Data' / 'cum_claims.parquet'

PAGE_METRICS = {
    1: 'survivorship',
    2: 'cond_clm_rate',
    3: 'cond_prepay_rate',
    4: 'cum_clm_count',
    5: 'cum_prepay_count',
    6: 'cum_clm_rate',
    7: 'cum_prepay_rate',
}
#%%

def build_text_metric_configs(sourcefy, source, metric_pages, *, row_gt=2, split_n=30, **extra_config):
    return [
        {
            'sourcefy': sourcefy,
            'source': source,
            'page_index': page_index,
            'row_gt': row_gt,
            'split_n': split_n,
            'metric': metric,
            **extra_config,
        }
        for metric, page_index in metric_pages.items()
    ]


def build_spilled_text_metric_configs(sourcefy, source, metric_page_pairs, *, row_gt=2, split_n=29, **extra_config):
    return [
        {
            'sourcefy': sourcefy,
            'source': source,
            'page_index': page_index,
            'row_gt': row_gt,
            'split_n': split_n,
            'extra_page_index': extra_page_index,
            'extra_skip_lines': 1,
            'extra_column_name': '30',
            'metric': metric,
            **extra_config,
        }
        for metric, (page_index, extra_page_index) in metric_page_pairs.items()
    ]


TEXT_PDF_CONFIGS = [
    *build_text_metric_configs(
        2004,
        'ActuarialAppendix/FY2004_AppendixE.pdf',
        {
            'cond_clm_rate': 1,
            'cond_prepay_rate': 2,
            'cum_clm_rate': 3,
            'cum_prepay_rate': 4,
        },
    ),
    *build_spilled_text_metric_configs(
        2005,
        'ActuarialAppendix/FY2005_AppendixE.pdf',
        {
            'cond_clm_rate': (0, 1),
            'cond_prepay_rate': (2, 3),
            'cum_clm_rate': (4, 5),
            'cum_prepay_rate': (6, 7),
        },
    ),
    *build_text_metric_configs(
        2006,
        'ActuarialAppendix/FY2006_AppendixE.pdf',
        {
            'cond_clm_rate': 1,
            'cond_prepay_rate': 2,
            'cum_clm_rate': 3,
            'cum_prepay_rate': 4,
        },
    ),
    *build_text_metric_configs(
        2007,
        'ActuarialAppendix/FY2007_AppendixE.pdf',
        {
            'cond_clm_rate': 0,
            'cond_prepay_rate': 1,
            'cum_clm_rate': 2,
            'cum_prepay_rate': 3,
        },
    ),
    *build_text_metric_configs(
        2008,
        'ActuarialAppendix/FY2008_AppendixE.pdf',
        {
            'cond_clm_rate': 1,
            'cond_prepay_rate': 2,
            'cum_clm_rate': 3,
            'cum_prepay_rate': 4,
        },
    ),
    *build_text_metric_configs(
        2009,
        'ActuarialAppendix/FY2009_Forward.pdf',
        {
            'cond_clm_rate': 144,
            'cond_prepay_rate': 145,
            'cum_clm_rate': 146,
            'cum_prepay_rate': 147,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2010,
        'https://www.hud.gov/sites/documents/doc_16569.pdf',
        {
            'cum_clm_rate': 160,
            'cum_prepay_rate': 161,
            'cond_clm_rate': 162,
            'cond_prepay_rate': 163,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2011,
        'ActuarialAppendix/FY2011_Forward.pdf',
        {
            'cum_clm_rate': 151,
            'cum_prepay_rate': 152,
            'cond_clm_rate': 153,
            'cond_prepay_rate': 154,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2012,
        'ActuarialAppendix/FY2012_Forward.pdf',
        {
            'cum_clm_rate': 201,
            'cum_prepay_rate': 202,
            'cond_clm_rate': 203,
            'cond_prepay_rate': 204,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2013,
        'ActuarialAppendix/FY2013_Forward.pdf',
        {
            'cum_clm_rate': 218,
            'cum_prepay_rate': 219,
            'cond_clm_rate': 220,
            'cond_prepay_rate': 221,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2014,
        'ActuarialAppendix/FY2014_Forward.pdf',
        {
            'cum_clm_rate': 212,
            'cum_prepay_rate': 213,
            'cond_clm_rate': 214,
            'cond_prepay_rate': 215,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2015,
        'ActuarialAppendix/FY2015_Forward.pdf',
        {
            'cum_clm_rate': 212,
            'cum_prepay_rate': 213,
            'cond_clm_rate': 214,
            'cond_prepay_rate': 215,
        },
        row_lt=40,
    ),
    *build_text_metric_configs(
        2016,
        'ActuarialAppendix/FY2016_Forward.pdf',
        {
            'cum_clm_rate': 208,
            'cum_prepay_rate': 209,
            'cond_clm_rate': 210,
            'cond_prepay_rate': 211,
        },
        row_lt=40,
        projection_cutoff=2018,
    ),
    *build_text_metric_configs(
        2018,
        'ActuarialAppendix/FY2018_Forward.pdf',
        {
            'cond_clm_rate': 182,
            'cond_prepay_rate': 183,
            'loss_rate': 184,
        },
        row_gt=7,
        row_lt=39,
        value_multiplier=100,
    ),
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 326,
        'row_gt': 6,
        'row_lt': 37,
        'split_n': 31,
        'metric': 'incremental_clm_count',
    },
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 326,
        'row_gt': 38,
        'split_n': 30,
        'metric': 'cond_clm_rate',
    },
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 326,
        'row_gt': 38,
        'split_n': 30,
        'metric': 'cum_clm_rate',
        'cumulative_by_cohort': True,
    },
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 327,
        'row_gt': 6,
        'row_lt': 37,
        'split_n': 30,
        'metric': 'incremental_prepay_count',
    },
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 327,
        'row_gt': 38,
        'split_n': 30,
        'metric': 'cond_prepay_rate',
    },
    {
        'sourcefy': 2019,
        'source': 'ActuarialAppendix/FY2019_Forward.pdf',
        'page_index': 327,
        'row_gt': 38,
        'split_n': 30,
        'metric': 'cum_prepay_rate',
        'cumulative_by_cohort': True,
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 321,
        'row_gt': 9,
        'split_n': 31,
        'metric': 'survivorship',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 322,
        'row_gt': 9,
        'row_lt': 41,
        'split_n': 30,
        'metric': 'incremental_clm_count',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 322,
        'row_gt': 44,
        'split_n': 30,
        'metric': 'cond_clm_rate',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 323,
        'row_gt': 10,
        'row_lt': 42,
        'split_n': 30,
        'metric': 'cum_clm_count',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 323,
        'row_gt': 45,
        'split_n': 30,
        'metric': 'cum_clm_rate',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 324,
        'row_gt': 9,
        'row_lt': 41,
        'split_n': 30,
        'metric': 'incremental_prepay_count',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 324,
        'row_gt': 44,
        'split_n': 30,
        'metric': 'cond_prepay_rate',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 325,
        'row_gt': 10,
        'row_lt': 42,
        'split_n': 30,
        'metric': 'cum_prepay_count',
    },
    {
        'sourcefy': 2020,
        'source': 'ActuarialAppendix/FY2020_Forward.pdf',
        'page_index': 325,
        'row_gt': 45,
        'split_n': 30,
        'metric': 'cum_prepay_rate',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 261,
        'row_gt': 8,
        'split_n': 31,
        'metric': 'survivorship',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 262,
        'row_gt': 8,
        'row_lt': 42,
        'split_n': 30,
        'metric': 'incremental_clm_count',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 262,
        'row_gt': 45,
        'split_n': 30,
        'metric': 'cond_clm_rate',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 263,
        'row_gt': 9,
        'row_lt': 43,
        'split_n': 30,
        'metric': 'cum_clm_count',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 263,
        'row_gt': 46,
        'split_n': 30,
        'metric': 'cum_clm_rate',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 264,
        'row_gt': 9,
        'row_lt': 42,
        'split_n': 30,
        'metric': 'incremental_prepay_count',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'page_index': 264,
        'row_gt': 45,
        'split_n': 30,
        'metric': 'cond_prepay_rate',
    },
]

CAMELLOT_CONFIGS = [
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '1',
        'table_index': 0,
        'start_row': 3,
        'metric': 'survivorship',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '2',
        'table_index': 0,
        'start_row': 9,
        'metric': 'incremental_clm_count',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '3',
        'table_index': 0,
        'start_row': 4,
        'metric': 'cond_clm_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '4',
        'table_index': 0,
        'start_row': 6,
        'end_row': 39,
        'metric': 'cum_clm_count',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '4',
        'table_index': 0,
        'start_row': 45,
        'metric': 'cum_clm_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '5',
        'table_index': 0,
        'start_row': 5,
        'end_row': 38,
        'metric': 'incremental_prepay_count',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '5',
        'table_index': 0,
        'start_row': 42,
        'metric': 'cond_prepay_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'pages': '266',
        'table_index': 1,
        'start_row': 3,
        'end_row': 36,
        'metric': 'cum_prepay_count',
    },
    {
        'sourcefy': 2021,
        'source': 'ActuarialAppendix/FY2021_Forward.pdf',
        'pages': '266',
        'table_index': 0,
        'start_row': 3,
        'metric': 'cum_prepay_rate',
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '6',
        'table_index': 0,
        'start_row': 6,
        'end_row': 39,
        'metric': 'cum_prepay_count',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2022,
        'source': 'ActuarialAppendix/FY2022_Forward_AppendixG.pdf',
        'pages': '6',
        'table_index': 0,
        'start_row': 43,
        'metric': 'cum_prepay_rate',
        'apply_projection_filter': False,
    },
]

EXCEL_CONFIGS = [
    {
        'sourcefy': 2023,
        'source': 'ActuarialAppendix/FY2023_Forward_AppendixE.xlsx',
        'sheet_name': 'cond_clm_rate ',
        'skiprows': 1,
        'header': 1,
        'metric': 'cond_clm_rate',
        'apply_projection_filter': True,
    },
    {
        'sourcefy': 2023,
        'source': 'ActuarialAppendix/FY2023_Forward_AppendixE.xlsx',
        'sheet_name': 'cum_clm_rate ',
        'skiprows': 1,
        'header': 1,
        'metric': 'cum_clm_rate',
        'apply_projection_filter': True,
    },
    {
        'sourcefy': 2023,
        'source': 'ActuarialAppendix/FY2023_Forward_AppendixE.xlsx',
        'sheet_name': 'cond_prepay_tot_rate ',
        'skiprows': 1,
        'header': 1,
        'metric': 'cond_prepay_rate',
        'apply_projection_filter': True,
    },
    {
        'sourcefy': 2023,
        'source': 'ActuarialAppendix/FY2023_Forward_AppendixE.xlsx',
        'sheet_name': 'cum_prepay_tot_rate ',
        'skiprows': 1,
        'header': 1,
        'metric': 'cum_prepay_rate',
        'apply_projection_filter': True,
    },
    {
        'sourcefy': 2024,
        'source': 'ActuarialAppendix/FY2024_Forward_AppendixE.xlsx',
        'sheet_name': 'COND_CLM_RATE_product_all',
        'skiprows': 1,
        'header': 1,
        'metric': 'cond_clm_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2024,
        'source': 'ActuarialAppendix/FY2024_Forward_AppendixE.xlsx',
        'sheet_name': 'CUM_CLM_RATE_product_all',
        'skiprows': 1,
        'header': 1,
        'metric': 'cum_clm_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2024,
        'source': 'ActuarialAppendix/FY2024_Forward_AppendixE.xlsx',
        'sheet_name': 'COND_PREPAY_TOT_RATE_product_al',
        'skiprows': 1,
        'header': 1,
        'metric': 'cond_prepay_rate',
        'apply_projection_filter': False,
    },
    {
        'sourcefy': 2024,
        'source': 'ActuarialAppendix/FY2024_Forward_AppendixE.xlsx',
        'sheet_name': 'CUM_PREPAY_TOT_RATE_product_all',
        'skiprows': 1,
        'header': 1,
        'metric': 'cum_prepay_rate',
        'apply_projection_filter': False,
    },
]


def resolve_source(source):
    if str(source).startswith('http'):
        return source
    return REFERENCE_DIR / source


def add_metric(df, metric='cum_clm_rate'):
    df = df.copy()
    df['metric'] = metric
    return df


def read_pdf_text(source, page_index):
    resolved_source = resolve_source(source)
    if str(resolved_source).startswith('http'):
        response = requests.get(resolved_source, timeout=120)
        response.raise_for_status()
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            return pdf.pages[page_index].extract_text() or ''

    with pdfplumber.open(str(resolved_source)) as pdf:
        return pdf.pages[page_index].extract_text() or ''


def build_text_page_frame(source, page_index):
    lines = read_pdf_text(source, page_index).splitlines()
    df = pd.DataFrame({'text': lines})
    df['row'] = range(1, len(df) + 1)
    df['ref'] = df['text'].str.strip().apply(lambda value: re.sub(r'\s+', ' ', value))
    df['ref'] = df['ref'].str.replace('B', 'b', regex=False)
    return df


def filter_rows(df, config):
    filtered = df.copy()
    if config.get('row_gt') is not None:
        filtered = filtered[filtered['row'] > config['row_gt']]
    if config.get('row_ge') is not None:
        filtered = filtered[filtered['row'] >= config['row_ge']]
    if config.get('row_lt') is not None:
        filtered = filtered[filtered['row'] < config['row_lt']]
    if config.get('row_le') is not None:
        filtered = filtered[filtered['row'] <= config['row_le']]
    return filtered.reset_index(drop=True)


def build_wide_frame_from_text(df, split_n=None):
    if split_n is None:
        expanded = df['ref'].str.split(r'\s+', expand=True)
    else:
        expanded = df['ref'].str.split(r'\s+', expand=True, n=split_n)
    expanded.columns = ['cohort'] + [str(index) for index in range(1, expanded.shape[1])]
    return expanded


def extract_extra_column(config):
    extra_frame = build_text_page_frame(config['source'], config['extra_page_index'])
    lines = [line for line in extra_frame['text'].tolist() if str(line).strip()]
    skip_lines = config.get('extra_skip_lines', 0)
    return pd.Series(lines[skip_lines:])


def finalize_long_frame(
    long_df,
    *,
    sourcefy,
    metric='cum_clm_rate',
    projection_cutoff=None,
    apply_projection_filter=True,
    value_multiplier=1,
    cumulative_by_cohort=False,
):
    finalized = long_df.copy()
    finalized['cohort'] = finalized['cohort'].astype(str).str.strip().str.replace('B', 'b', regex=False)
    finalized['year'] = finalized['year'].astype(str).str.extract(r'(\d+)')
    finalized['value'] = (
        finalized['value']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.replace('%', '', regex=False)
        .str.strip()
    )
    finalized['value'] = pd.to_numeric(finalized['value'], errors='coerce') * value_multiplier

    if cumulative_by_cohort:
        finalized['value'] = finalized.groupby('cohort')['value'].cumsum()

    finalized['sourcefy'] = sourcefy
    finalized['metric'] = metric
    finalized['cohort_num'] = pd.to_numeric(finalized['cohort'].str.replace('b', '', regex=False), errors='coerce')
    finalized['year_num'] = pd.to_numeric(finalized['year'], errors='coerce')

    required = finalized['value'].notna() & finalized['cohort_num'].notna() & finalized['year_num'].notna()
    finalized = finalized[required].copy()

    if apply_projection_filter:
        cutoff = projection_cutoff if projection_cutoff is not None else sourcefy
        finalized = finalized[finalized['cohort_num'] + finalized['year_num'] - 1 <= cutoff].copy()

    return finalized[['cohort', 'year', 'value', 'sourcefy', 'metric']]


def extract_text_pdf_metric(config):
    base_frame = build_text_page_frame(config['source'], config['page_index'])
    filtered = filter_rows(base_frame, config)
    wide_frame = build_wide_frame_from_text(filtered, split_n=config.get('split_n'))

    if config.get('extra_page_index') is not None:
        extra_column = extract_extra_column(config)
        if len(extra_column) != len(wide_frame):
            raise ValueError(f"Extra column length mismatch for FY{config['sourcefy']}")
        wide_frame[config.get('extra_column_name', str(wide_frame.shape[1]))] = extra_column.values

    long_df = wide_frame.melt(id_vars=['cohort'], var_name='year', value_name='value')
    return finalize_long_frame(
        long_df,
        sourcefy=config['sourcefy'],
        metric=config.get('metric', 'cum_clm_rate'),
        projection_cutoff=config.get('projection_cutoff'),
        apply_projection_filter=config.get('apply_projection_filter', True),
        value_multiplier=config.get('value_multiplier', 1),
        cumulative_by_cohort=config.get('cumulative_by_cohort', False),
    )


def extract_camelot_metric(config):
    resolved_source = resolve_source(config['source'])
    tables = camelot.read_pdf(str(resolved_source), pages=str(config['pages']), flavor=config.get('flavor', 'stream'))
    if tables.n == 0:
        raise ValueError(f"No Camelot tables found for FY{config['sourcefy']}")

    table = tables[config.get('table_index', 0)].df.replace('', pd.NA)
    if config.get('start_row') is not None:
        table = table.iloc[config['start_row'] :].reset_index(drop=True)
    if config.get('end_row') is not None:
        start_row = config.get('start_row', 0)
        table = table.iloc[: config['end_row'] - start_row].reset_index(drop=True)

    table = table.rename(columns={table.columns[0]: 'cohort'}).copy()
    table.columns = ['cohort'] + [str(index) for index in range(1, table.shape[1])]
    long_df = table.melt(id_vars=['cohort'], var_name='year', value_name='value')
    return finalize_long_frame(
        long_df,
        sourcefy=config['sourcefy'],
        metric=config.get('metric', 'cum_clm_rate'),
        projection_cutoff=config.get('projection_cutoff'),
        apply_projection_filter=config.get('apply_projection_filter', True),
        value_multiplier=config.get('value_multiplier', 1),
        cumulative_by_cohort=config.get('cumulative_by_cohort', False),
    )


def extract_excel_metric(config):
    resolved_source = resolve_source(config['source'])
    temp = pd.read_excel(
        resolved_source,
        sheet_name=config['sheet_name'],
        skiprows=config.get('skiprows', 0),
        header=config.get('header', 0),
    )
    temp.columns = temp.columns.str.strip().str.lower().str.replace(' ', '_')
    long_df = temp.melt(id_vars=[config.get('id_var', 'fy_cohort')], var_name='temp', value_name='value')
    long_df = long_df.rename(columns={config.get('id_var', 'fy_cohort'): 'cohort', 'temp': 'year'})
    return finalize_long_frame(
        long_df,
        sourcefy=config['sourcefy'],
        metric=config.get('metric', 'cum_clm_rate'),
        projection_cutoff=config.get('projection_cutoff'),
        apply_projection_filter=config.get('apply_projection_filter', True),
        value_multiplier=config.get('value_multiplier', 1),
        cumulative_by_cohort=config.get('cumulative_by_cohort', False),
    )


def extract_fy2025_page(pdf_path, page_number, metric, sourcefy=2025):
    tables = camelot.read_pdf(str(pdf_path), pages=str(page_number), flavor='stream')
    if tables.n == 0:
        raise ValueError(f'No table found on FY2025 page {page_number}')

    table = tables[0].df.replace('', pd.NA)
    first_column = table.iloc[:, 0].astype(str).str.strip()
    header_candidates = table.index[first_column.str.contains('credit_subsidy_cohort', case=False, na=False)]
    if len(header_candidates) == 0:
        raise ValueError(f'Could not locate header row on FY2025 page {page_number}')

    header_index = header_candidates[0]
    header = table.iloc[header_index].tolist()
    page_df = table.iloc[header_index + 1 :].reset_index(drop=True).copy()
    page_df.columns = header
    page_df = page_df.rename(columns={page_df.columns[0]: 'cohort'})
    page_df['cohort'] = page_df['cohort'].astype(str).str.strip().str.replace('B', 'b', regex=False)
    page_df = page_df[page_df['cohort'].str.match(r'^b?\d{4}$', na=False)].copy()
    long_df = page_df.melt(id_vars=['cohort'], var_name='year', value_name='value')
    return finalize_long_frame(long_df, sourcefy=sourcefy, metric=metric)


def extract_fy2025_all_pages(pdf_path, sourcefy=2025):
    frames = []
    for page_number, metric in PAGE_METRICS.items():
        frames.append(extract_fy2025_page(pdf_path, page_number, metric, sourcefy=sourcefy))
    return pd.concat(frames, ignore_index=True)


def build_cum_claims_dataframe():
    frames = []

    for config in TEXT_PDF_CONFIGS:
        print(f"Processing FY{config['sourcefy']}...")
        frame = extract_text_pdf_metric(config)
        print(frame.head())
        frames.append(frame)

    for config in CAMELLOT_CONFIGS:
        print(f"Processing FY{config['sourcefy']}...")
        frame = extract_camelot_metric(config)
        print(frame.head())
        frames.append(frame)

    for config in EXCEL_CONFIGS:
        print(f"Processing FY{config['sourcefy']}...")
        frame = extract_excel_metric(config)
        print(frame.head())
        frames.append(frame)

    print('Processing FY2025...')
    fy25 = extract_fy2025_all_pages(REFERENCE_DIR / 'ActuarialAppendix/ITDC_FY2025_Q4_Termination_Finger_Tables_All_Products.pdf')
    print(fy25.tail())
    frames.append(fy25)

    df_cum_claims = pd.concat(frames, ignore_index=True)
    df_cum_claims['value'] = pd.to_numeric(df_cum_claims['value'], errors='coerce')
    df_cum_claims['year'] = df_cum_claims['year'].astype(str)
    return df_cum_claims


def main():
    df_cum_claims = build_cum_claims_dataframe()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_cum_claims.to_parquet(OUTPUT_PATH, index=False)
    print(f'Saved {OUTPUT_PATH}')


if __name__ == '__main__':
    main()

