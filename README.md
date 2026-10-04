# FHA Data & Analysis

This repository gathers, cleans, and visualizes FHA-related datasets used for actuarial review and reporting.

Quick start

1. Create and activate your Python environment (example):

```powershell
python -m venv env_fha
env_fha\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables:

- `FRED_API_KEY` — your FRED API key (required for inflation adjustments). On Windows PowerShell:

```powershell
$env:FRED_API_KEY = 'your_api_key_here'
```

3. Data locations

- Raw inputs: `Data/Raw/` (Excel, PDFs, etc.)
- Outputs: `Data/` (parquet files such as `capratio.parquet`, `cum_claims.parquet`)

Notes

- Camelot (used for PDF table extraction) requires Ghostscript on Windows. Install Ghostscript from https://www.ghostscript.com/ and ensure it's on your PATH.
- If you don't have a FRED API key or prefer to skip inflation adjustments, some scripts will continue but will not produce inflation-adjusted columns.

Useful scripts

- `Data/data_capratio.py`: load and combine capratio sheets, compute inflation adjustments, write `Data/capratio.parquet`.
- `Data/data_claims.py`: extract cumulative claims and write `Data/cum_claims.parquet`.
- `capratio.py`: plotting and analysis utilities; reads `Data/capratio.parquet`.

Further questions or preferences (pinning dependencies, CI, GitHub actions)? Open an issue or ask here.
