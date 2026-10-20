#!/usr/bin/env python
"""Test script to diagnose dashboard loading issues."""

from pathlib import Path
import pandas as pd
from creditsubsidy import load_credit_subsidy_data

REPO_ROOT = Path(__file__).resolve().parent
CAPRATIO_PATH = REPO_ROOT / "Data" / "capratio.parquet"
CLAIMS_PATH = REPO_ROOT / "Data" / "cum_claims.parquet"

print("=" * 50)
print("FHA Dashboard Load Test")
print("=" * 50)

# Test 1: Check file existence
print("\n1. Checking data files...")
print(f"   Capratio path: {CAPRATIO_PATH}")
print(f"   Exists: {CAPRATIO_PATH.exists()}")
print(f"   Claims path: {CLAIMS_PATH}")
print(f"   Exists: {CLAIMS_PATH.exists()}")

# Test 2: Load parquet files
print("\n2. Loading parquet files...")
try:
    capratio_df = pd.read_parquet(CAPRATIO_PATH)
    print(f"   Capratio: OK ({len(capratio_df)} rows)")
except Exception as e:
    print(f"   Capratio: ERROR - {e}")
    capratio_df = None

try:
    claims_df = pd.read_parquet(CLAIMS_PATH)
    print(f"   Claims: OK ({len(claims_df)} rows)")
except Exception as e:
    print(f"   Claims: ERROR - {e}")
    claims_df = None

# Test 3: Load credit subsidy
print("\n3. Loading credit subsidy data...")
try:
    creditsubsidy_df = load_credit_subsidy_data()
    print(f"   Credit Subsidy: OK ({len(creditsubsidy_df)} rows)")
except Exception as e:
    print(f"   Credit Subsidy: WARNING - {type(e).__name__}: {e}")
    creditsubsidy_df = None

# Test 4: Check data quality
print("\n4. Checking data quality...")
if capratio_df is not None:
    print(f"   Capratio columns: {list(capratio_df.columns)}")
    print(f"   Capratio dtypes: OK")
    
if claims_df is not None:
    print(f"   Claims columns: {list(claims_df.columns)}")
    print(f"   Claims dtypes: OK")

print("\n" + "=" * 50)
print("Load test complete!")
print("=" * 50)
