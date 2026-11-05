from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from creditsubsidy import load_credit_subsidy_data


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "Data"
CAPRATIO_PATH = DATA_DIR / "capratio.parquet"
CLAIMS_PATH = DATA_DIR / "cum_claims.parquet"


class TestDataLoadSmoke(unittest.TestCase):
    def test_required_data_files_exist(self) -> None:
        self.assertTrue(CAPRATIO_PATH.exists(), f"Missing file: {CAPRATIO_PATH}")
        self.assertTrue(CLAIMS_PATH.exists(), f"Missing file: {CLAIMS_PATH}")

    def test_capratio_parquet_loads(self) -> None:
        df = pd.read_parquet(CAPRATIO_PATH)
        self.assertGreater(len(df), 0)
        self.assertIn("year", df.columns)

    def test_claims_parquet_loads(self) -> None:
        df = pd.read_parquet(CLAIMS_PATH)
        self.assertGreater(len(df), 0)
        self.assertIn("value", df.columns)

    def test_creditsubsidy_loader_smoke(self) -> None:
        df = load_credit_subsidy_data()
        self.assertGreater(len(df), 0)
        self.assertIn("fiscal_year", df.columns)
        self.assertIn("current_reestimated_rate", df.columns)


if __name__ == "__main__":
    unittest.main()
