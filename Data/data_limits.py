"""
Download and combine FHA loan limits data from multiple sources.

Sources:
1. HUD Computerized Home Underwriting Management System (CHUMS) - 2008-2025
   Downloaded from https://apps.hud.gov/pub/chums/cy{YYYY}-forward-limits.txt
2. Vandell historical data (1934-1994) from vandell_loanlimit.xlsx
3. FHA Mortgagee Letters (ML) 1994-2008 from vandell_loanlimit.xlsx
4. Philadelphia Fed HPI-adjusted 1938 limit (1890-2025)

Output:
- loanlimits_county.parquet: Full county-level CHUMS data (2008-2025)
- loanlimits.parquet: Combined dataset with all sources, years 1930-2025, schema:
  year (int), type (str: S/H), value (float), source (str)
"""

import pandas as pd
import requests
from io import BytesIO
from pathlib import Path

DATA_PATH = Path(__file__).parent


def parse_loan_limits_line(line, year):
    """Parse a fixed-width line according to HUD specification.
    
    Field layout is consistent across all years (2008-2025):
    - Positions 001-163 are standard across all years
    - Positions 164-175 (median price determining limit and year) only in 2015+
    """
    
    if len(line) < 163:
        return None
    
    record = {
        'msa_code': line[0:5].strip(),
        'metro_division_code': line[5:10].strip(),
        'msa_name': line[10:60].strip(),
        'soa_code': line[60:65].strip(),
        'limit_type': line[65:66].strip(),
        'median_price': line[66:73].strip(),
        'limit_1_unit': line[73:80].strip(),
        'limit_2_units': line[80:87].strip(),
        'limit_3_units': line[87:94].strip(),
        'limit_4_units': line[94:101].strip(),
        'state_abbr': line[101:103].strip(),
        'county_code': line[103:106].strip(),
        'state_name': line[106:132].strip(),
        'county_name': line[132:147].strip(),
        'county_transaction_date': line[147:155].strip(),
        'limit_transaction_date': line[155:163].strip(),
    }
    
    if len(line) >= 175:
        record['median_price_determining_limit'] = line[163:170].strip()
        record['year_median_limit'] = line[170:175].strip()
    else:
        record['median_price_determining_limit'] = ''
        record['year_median_limit'] = ''
    
    record['year'] = year
    return record


def download_chums_data():
    """Download HUD CHUMS forward loan limits for years 2008-2025."""
    
    base_url = "https://apps.hud.gov/pub/chums/cy{}-forward-limits.txt"
    all_records = []
    
    for year in range(2008, 2026):
        url = base_url.format(year)
        
        try:
            print(f"Downloading CHUMS {year}...", end=" ", flush=True)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            records = [r for line in lines if (r := parse_loan_limits_line(line, year))]
            all_records.extend(records)
            print(f"OK ({len(records)} records)")
            
        except requests.exceptions.RequestException as e:
            print(f"FAILED ({e})")
            continue
        except Exception as e:
            print(f"FAILED (parse: {e})")
            continue
    
    if not all_records:
        raise ValueError("No CHUMS data was successfully downloaded.")
    
    df_county = pd.DataFrame(all_records)
    numeric_cols = ['median_price', 'limit_1_unit', 'limit_2_units', 'limit_3_units', 
                    'limit_4_units', 'median_price_determining_limit']
    for col in numeric_cols:
        df_county[col] = pd.to_numeric(df_county[col], errors='coerce')
    
    county_path = DATA_PATH / "loanlimits_county.parquet"
    df_county.to_parquet(county_path, index=False)
    print(f"Saved county data: {county_path} ({len(df_county):,} records)")
    
    return df_county


def load_hud_summary(df_county):
    """Create summary of max single-family limits by year and type from CHUMS."""
    excluded_states = {'AK', 'HI', 'GU', 'VI', ''}
    df_filtered = df_county[
        (~df_county['state_abbr'].isin(excluded_states)) & 
        (df_county['state_abbr'].notna())
    ].copy()
    
    df_filtered['limit_1_unit_num'] = pd.to_numeric(df_filtered['limit_1_unit'], errors='coerce')
    df_summary = df_filtered[df_filtered['limit_type'].isin(['S', 'H'])].groupby(
        ['year', 'limit_type']
    ).agg({'limit_1_unit_num': 'max'}).reset_index()
    
    df_summary.columns = ['year', 'type', 'value']
    df_summary['source'] = 'CHUMS'
    
    return df_summary[['year', 'type', 'value', 'source']]


def load_vandell_limits():
    """Load Vandell historical loan limits (1934-1994)."""
    excel_file = DATA_PATH / "Raw" / "vandell_loanlimit.xlsx"
    df_vandell = pd.read_excel(excel_file, sheet_name='vandell')
    
    records = []
    for _, row in df_vandell.iterrows():
        year = int(row['year'])
        for limit_type in ['S', 'H']:
            value = row[limit_type]
            if pd.notna(value):
                records.append({
                    'year': year,
                    'type': limit_type,
                    'value': value,
                    'source': 'Vandell (1995)'
                })
    
    return pd.DataFrame(records)


def load_ml_limits():
    """Load FHA Mortgagee Letters loan limits (1994-2008)."""
    excel_file = DATA_PATH / "Raw" / "vandell_loanlimit.xlsx"
    df_ml = pd.read_excel(excel_file, sheet_name='ML')
    
    records = []
    for _, row in df_ml.iterrows():
        year = int(row['year'])
        for limit_type in ['S', 'H']:
            value = row[limit_type]
            if pd.notna(value):
                records.append({
                    'year': year,
                    'type': limit_type,
                    'value': value,
                    'source': 'FHA Mortgagee Letters'
                })
    
    return pd.DataFrame(records)


def download_hpi_data():
    """Download Philadelphia Fed housing price index data."""
    url = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Data-Visualizations/Historical-Housing-Prices/hhp-national-indices.xlsx'
    
    print("Downloading HPI data from Philadelphia Fed...", end=" ")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    df = pd.read_excel(BytesIO(response.content), sheet_name='hhp_national_v3')
    print(f"OK ({len(df)} years)")
    
    return df[['year', 'pw_hpi_b_1890']].copy()


def create_hpi_adjusted_limits(df_combined):
    """Create HPI-adjusted loan limits for all years using 1938 as base."""
    
    print("Downloading HPI data...", end=" ", flush=True)
    hpi_df = download_hpi_data()
    
    # Find 1938 Standard limit from Vandell
    mask = (df_combined['year'] == 1938) & (df_combined['type'] == 'S') & (df_combined['source'] == 'Vandell (1995)')
    if mask.sum() == 0:
        raise ValueError("Could not find 1938 Standard limit from Vandell")
    
    base_1938_limit = df_combined[mask]['value'].iloc[0]
    hpi_1938 = hpi_df[hpi_df['year'] == 1938]['pw_hpi_b_1890'].iloc[0]
    
    print(f"Creating HPI-adjusted limits (base 1938 Standard: ${base_1938_limit:,.0f})...", end=" ")
    
    records = []
    for _, row in hpi_df.iterrows():
        year = int(row['year'])
        hpi_year = row['pw_hpi_b_1890']
        
        if pd.isna(hpi_year):
            continue
        
        adjusted_value = base_1938_limit * (hpi_year / hpi_1938)
        records.append({
            'year': year,
            'type': 'S',
            'value': adjusted_value,
            'source': 'HPI-adjusted 1938 limit'
        })
    
    print(f"OK ({len(records)} years)")
    return pd.DataFrame(records)


def combine_all_sources():
    """Download and combine all loan limit sources."""
    
    print("\n=== Downloading and Combining FHA Loan Limits ===\n")
    
    # Download CHUMS county data
    print("Step 1: Download CHUMS county-level data (2008-2025)")
    df_county = download_chums_data()
    
    # Create CHUMS summary
    print("\nStep 2: Extract CHUMS summary (max single-family limits)")
    df_hud = load_hud_summary(df_county)
    print(f"  CHUMS summary: {len(df_hud)} records")
    
    # Load Vandell data
    print("\nStep 3: Load Vandell historical limits (1934-1994)")
    df_vandell = load_vandell_limits()
    print(f"  Vandell: {len(df_vandell)} records")
    
    # Load Mortgagee Letters
    print("\nStep 4: Load FHA Mortgagee Letters (1994-2008)")
    df_ml = load_ml_limits()
    print(f"  Mortgagee Letters: {len(df_ml)} records")
    
    # Combine CHUMS, Vandell, and ML
    print("\nStep 5: Combine CHUMS, Vandell, and Mortgagee Letters")
    df_combined = pd.concat([df_hud, df_vandell, df_ml], ignore_index=True)
    df_combined = df_combined.sort_values(['year', 'type']).reset_index(drop=True)
    df_combined['value'] = pd.to_numeric(df_combined['value'], errors='coerce')
    print(f"  Combined: {len(df_combined)} records")
    
    # Add HPI-adjusted limits
    print("\nStep 6: Add HPI-adjusted limits (1890-2025)")
    df_hpi = create_hpi_adjusted_limits(df_combined)
    
    # Final combination
    print("\nStep 7: Final combination with HPI-adjusted limits")
    df_final = pd.concat([df_combined, df_hpi], ignore_index=True)
    df_final = df_final.sort_values(['year', 'type']).reset_index(drop=True)
    
    # Filter to years >= 1930
    print("\nStep 8: Filter to years >= 1930")
    df_final = df_final[df_final['year'] >= 1930].reset_index(drop=True)
    print(f"  Final dataset: {len(df_final)} records, years {df_final['year'].min()}-{df_final['year'].max()}")
    
    # Save final dataset
    output_path = DATA_PATH / "loanlimits.parquet"
    df_final.to_parquet(output_path, index=False)
    print(f"\nSaved to {output_path}")
    
    print(f"\n=== Summary ===")
    print(f"Total records: {len(df_final):,}")
    print(f"Year range: {df_final['year'].min()}-{df_final['year'].max()}")
    print(f"\nRecords by source:")
    for source, count in sorted(df_final['source'].value_counts().items()):
        print(f"  {source}: {count}")
    
    return df_final


if __name__ == "__main__":
    df = combine_all_sources()

