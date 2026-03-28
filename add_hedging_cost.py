#!/usr/bin/env python3
"""
Retrofit existing output_master_*m.xlsx files with the Hedging_Cost_bps column.

Formula:
    SOFR_ACT365      = USD_SOFR_{x}M_Pct * (365 / 360)
    Hedging_Cost_bps = (Implied_SGD_Rate_Pct - SOFR_ACT365) * 100

Run once to add the column to existing files. Idempotent — safe to re-run.
"""

import os
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = ["output_master_1m.xlsx", "output_master_3m.xlsx", "output_master_6m.xlsx"]


def process_file(filepath):
    df = pd.read_excel(filepath)

    # Detect SOFR column dynamically
    sofr_col = next((c for c in df.columns if c.startswith("USD_SOFR") and c.endswith("_Pct")), None)
    if sofr_col is None:
        print(f"  ERROR: No USD_SOFR_*_Pct column found. Skipping.")
        return

    # Confirm required columns exist
    for col in ["Implied_SGD_Rate_Pct", "Rate_Diff_bps"]:
        if col not in df.columns:
            print(f"  ERROR: Missing required column '{col}'. Skipping.")
            return

    # Drop existing column if present (idempotent)
    if "Hedging_Cost_bps" in df.columns:
        df = df.drop(columns=["Hedging_Cost_bps"])

    # Compute new column
    sofr_act365 = df[sofr_col] * (365 / 360)
    hedging_cost = (df["Implied_SGD_Rate_Pct"] - sofr_act365) * 100

    # Insert immediately after Rate_Diff_bps
    insert_pos = df.columns.get_loc("Rate_Diff_bps") + 1
    df.insert(insert_pos, "Hedging_Cost_bps", hedging_cost)

    # Overwrite in place
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    # Print summary
    print(f"  Rows processed: {len(df)}")
    print(f"  Last 3 rows:")
    cols = ["Trade_Date", "Rate_Diff_bps", "Hedging_Cost_bps"]
    print(df[cols].tail(3).to_string(index=False))


def main():
    for filename in FILES:
        filepath = os.path.join(SCRIPT_DIR, filename)
        print(f"\n{filename}")
        if not os.path.exists(filepath):
            print(f"  ERROR: File not found: {filepath}")
            continue
        process_file(filepath)
    print()


if __name__ == "__main__":
    main()
