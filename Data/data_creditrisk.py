import pandas as pd
from pathlib import Path
DATA_DIR = Path(__file__).parent 

#%% FHFA Quarter Century of Mortgage Risk
wp1902_file = DATA_DIR / "Raw" / "wp1902-data-supplement.xlsx"
df_wp1902 = pd.read_excel(wp1902_file, sheet_name="National")
mask = (df_wp1902["Statistic"] == "Average Baseline Stressed Default Rate") & \
    (df_wp1902["Loan purpose"] == "All loans")
df_fhfa = df_wp1902[mask][["Year", "FHA"]].rename(columns={"FHA": "Risk"}).copy()
df_fhfa['Source']='Davis et al. (2023)'
df_fhfa['Date'] = pd.to_datetime(df_fhfa['Year'].astype(str) + '-12-31')

#%% AEI
nmdr_file = DATA_DIR / "RAW" /"NMDR for Federal Housing Administration, All Loans.csv"
# Read and parse NMDR CSV (skip first 3 rows which are metadata)
df_nmdr = pd.read_csv(nmdr_file, skiprows=3)
# Rename first column to 'Series' if needed and transpose to long format
if df_nmdr.shape[0] == 1:
    # NMDR data is in wide format (months as columns)
    # Transpose to get Year-Month and values
    series_name = df_nmdr.iloc[0, 0]
    nmdr_values = df_nmdr.iloc[0, 1:]
    # Create month-value pairs
    months = nmdr_values.index.tolist()
    values = nmdr_values.values
    # Parse month strings and convert to datetime
    date_range = pd.PeriodIndex(months, freq="M").to_timestamp()
    df_aei = pd.DataFrame({
        "Date": date_range,
        "Risk": values
    })
df_aei['Risk']=df_aei['Risk']/100
df_aei['Source'] = 'American Enterprise Institute'

#%% Urban


urban_file = "https://urban-data-catalog.s3.amazonaws.com/drupal-root-live/2026/02/03/hcai_charts_updated_to_2025q2.xlsx"
df_urban = pd.read_excel(urban_file, sheet_name="Gov't", skiprows=3)

df_urban = df_urban[["Year", "Total\nRisk"]].rename(columns={"Total\nRisk": "Risk"}).copy()
df_urban['Source'] = 'Urban Institute'
df_urban['Date'] = pd.to_datetime(df_urban['Year'])
df_urban['Risk'] = df_urban['Risk'] / 100

# %%
df_risk = pd.concat([df_fhfa[['Date', 'Risk', 'Source']],
                     df_aei[['Date', 'Risk', 'Source']],
                     df_urban[['Date', 'Risk', 'Source']]], ignore_index=True)
df_risk.to_parquet(DATA_DIR / "creditrisk.parquet", index=False)