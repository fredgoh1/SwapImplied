#!/usr/bin/env python3
"""
Historical Swap Implied Rate Builder
=====================================
Builds output_historical_1m/3m/6m.xlsx by combining:
  - Term SOFR fixings from Barchart CSV files (1M, 3M, 6M)
  - USDSGD forward points from FWD_Points_Actual_Historical.xlsx
  - USDSGD spot FX rates fetched via yfinance

Uses the same CIP formula and business day conventions as the existing
calculate_swap_implied_rates.py script.

Usage:
    python3 build_historical_dataset.py
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Allow importing from calc_swap_implied subpackage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'calc_swap_implied'))
from calculate_swap_implied_rates import HolidayCalendar, SwapImpliedRateCalculator

# ---------------------------------------------------------------------------
# File paths (relative to this script)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOFR_FILES = {
    '1M': os.path.join(BASE_DIR, 'sofermm1rt_daily_historical-data-03-24-2026.csv'),
    '3M': os.path.join(BASE_DIR, 'sofermm3rt_daily_historical-data-03-24-2026.csv'),
    '6M': os.path.join(BASE_DIR, 'sofermm6rt_daily_historical-data-03-24-2026.csv'),
}

FWD_POINTS_FILE = os.path.join(BASE_DIR, 'FWD_Points_Actual_Historical.xlsx')

OUTPUT_FILES = {
    '1M': os.path.join(BASE_DIR, 'output_historical_1m.xlsx'),
    '3M': os.path.join(BASE_DIR, 'output_historical_3m.xlsx'),
    '6M': os.path.join(BASE_DIR, 'output_historical_6m.xlsx'),
}

HISTORY_START = '2025-01-01'

# ---------------------------------------------------------------------------
# Step 1: Load Term SOFR CSV files
# ---------------------------------------------------------------------------

def load_sofr_data():
    """
    Load 1M, 3M, 6M Term SOFR from Barchart CSVs.
    Rates are in decimal format (e.g. 0.03679 = 3.679%) — multiply by 100.
    Returns a dict: {'1M': df, '3M': df, '6M': df} each with Date + rate column.
    """
    sofr = {}
    for tenor, path in SOFR_FILES.items():
        print(f"  Loading {tenor} SOFR from {os.path.basename(path)}...")
        df = pd.read_csv(path)
        # Barchart columns: Time, Open, High, Low, Latest, Change, %Change, Volume
        # Last row is a Barchart footer — drop non-date rows
        df = df[['Time', 'Latest']].copy()
        df.columns = ['Date', f'{tenor[0].lower()}mSOFR']
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        # Convert decimal to percentage
        df[f'{tenor[0].lower()}mSOFR'] = df[f'{tenor[0].lower()}mSOFR'] * 100
        # Filter to history start
        df = df[df['Date'] >= HISTORY_START].copy()
        df = df.sort_values('Date').reset_index(drop=True)
        sofr[tenor] = df
        print(f"    {len(df)} rows from {df['Date'].min().date()} to {df['Date'].max().date()}")
    return sofr


# ---------------------------------------------------------------------------
# Step 2: Load forward points
# ---------------------------------------------------------------------------

def load_forward_points():
    """
    Load USDSGD forward points from FWD_Points_Actual_Historical.xlsx.
    Columns expected: Date, 1-Month, 3-Month, 6-Month (pips, e.g. -30.34).
    Returns a DataFrame with Date, FP_1M, FP_3M, FP_6M.
    """
    print(f"  Loading forward points from {os.path.basename(FWD_POINTS_FILE)}...")
    df = pd.read_excel(FWD_POINTS_FILE)
    # Normalise column names
    df = df.rename(columns={
        'Date': 'Date',
        '1-Month': 'FP_1M',
        '3-Month': 'FP_3M',
        '6-Month': 'FP_6M',
    })
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()  # Strip time/footer rows
    df = df[['Date', 'FP_1M', 'FP_3M', 'FP_6M']].copy()
    df = df.dropna(subset=['Date'])
    df = df[df['Date'] >= HISTORY_START].copy()
    df = df.sort_values('Date').reset_index(drop=True)
    print(f"    {len(df)} rows from {df['Date'].min().date()} to {df['Date'].max().date()}")
    return df


# ---------------------------------------------------------------------------
# Step 3: Fetch USDSGD spot FX via yfinance
# ---------------------------------------------------------------------------

def load_spot_fx():
    """
    Download historical USDSGD spot rates from Yahoo Finance via yfinance.
    Returns a DataFrame with Date, USDSGD_FX.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("\nERROR: yfinance is not installed. Run: pip install yfinance")
        sys.exit(1)

    print("  Fetching USDSGD spot FX from Yahoo Finance (yfinance)...")
    end_date = datetime.today().strftime('%Y-%m-%d')
    raw = yf.download('USDSGD=X', start=HISTORY_START, end=end_date,
                      auto_adjust=True, progress=False)
    if raw.empty:
        print("ERROR: yfinance returned no data for USDSGD=X")
        sys.exit(1)

    # Handle MultiIndex columns that yfinance sometimes returns
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    fx = raw[['Close']].copy()
    fx.index.name = 'Date'
    fx = fx.reset_index()
    fx.columns = ['Date', 'USDSGD_FX']
    fx['Date'] = pd.to_datetime(fx['Date']).dt.normalize()
    fx = fx[fx['Date'] >= HISTORY_START].copy()
    fx = fx.sort_values('Date').reset_index(drop=True)
    print(f"    {len(fx)} rows from {fx['Date'].min().date()} to {fx['Date'].max().date()}")
    return fx


# ---------------------------------------------------------------------------
# Step 4 & 5: Merge data and run CIP calculation for one tenor
# ---------------------------------------------------------------------------

def build_tenor(tenor, sofr_df, fwd_df, fx_df, calendar):
    """
    Merge data sources, run the swap implied rate calculation for one tenor,
    and return the output DataFrame.
    """
    sofr_col = f'{tenor[0].lower()}mSOFR'
    fp_col = f'FP_{tenor}'

    # Build per-tenor input frame
    merged = sofr_df.merge(fwd_df[['Date', fp_col]], on='Date', how='inner')
    merged = merged.merge(fx_df, on='Date', how='inner')
    merged = merged.rename(columns={fp_col: 'ForwardPoints'})
    merged = merged.dropna(subset=[sofr_col, 'ForwardPoints', 'USDSGD_FX'])
    merged = merged.sort_values('Date').reset_index(drop=True)

    print(f"\n  {tenor}: {len(merged)} common dates "
          f"({merged['Date'].min().date()} – {merged['Date'].max().date()})")

    calc = SwapImpliedRateCalculator(calendar, tenor=tenor)

    rows = []
    for _, row in merged.iterrows():
        result = calc.process_row(
            trade_date=row['Date'].to_pydatetime(),
            sofr_rate=row[sofr_col],
            spot_rate=row['USDSGD_FX'],
            forward_points=row['ForwardPoints'],
        )
        rows.append(result)

    results_df = pd.DataFrame(rows)

    output_df = pd.DataFrame({
        'Trade_Date':           merged['Date'].values,
        'Spot_Date':            results_df['Spot_Date'].values,
        'Forward_Date':         results_df['Forward_Date'].values,
        'Actual_Days':          results_df['Actual_Days'].values,
        f'USD_SOFR_{tenor}_Pct': merged[sofr_col].values,
        'Spot_Rate':            merged['USDSGD_FX'].values,
        'Forward_Points_pips':  merged['ForwardPoints'].values,
        'Forward_Rate':         results_df['Forward_Rate'].values,
        'Implied_SGD_Rate_Pct': results_df['Implied_SGD_Rate_Pct'].values,
        'Rate_Diff_bps':        results_df['Rate_Diff_bps'].values,
    })
    return output_df


# ---------------------------------------------------------------------------
# Step 6: Write output Excel
# ---------------------------------------------------------------------------

def save_output(output_df, tenor, output_path):
    """Write results to Excel with Results, Summary, and Methodology sheets."""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        output_df.to_excel(writer, sheet_name='Results', index=False)

        sofr_col = f'USD_SOFR_{tenor}_Pct'
        summary_data = {
            'Metric': [
                'Tenor',
                'Number of Trades',
                f'Average Implied SGD Rate {tenor} (%)',
                f'Average USD SOFR {tenor} (%)',
                'Average Rate Differential (bps)',
                f'Min Implied SGD Rate {tenor} (%)',
                f'Max Implied SGD Rate {tenor} (%)',
                'Min Days',
                'Max Days',
                'Average Days',
            ],
            'Value': [
                tenor,
                len(output_df),
                output_df['Implied_SGD_Rate_Pct'].mean(),
                output_df[sofr_col].mean(),
                output_df['Rate_Diff_bps'].mean(),
                output_df['Implied_SGD_Rate_Pct'].min(),
                output_df['Implied_SGD_Rate_Pct'].max(),
                output_df['Actual_Days'].min(),
                output_df['Actual_Days'].max(),
                output_df['Actual_Days'].mean(),
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        methodology_text = (
            f"USD/SGD FX SWAP IMPLIED RATE CALCULATION METHODOLOGY\n"
            f"TENOR: {tenor}\n\n"
            f"CIP Formula: r_SGD = [(F/S) x (1 + r_USD x days/360) - 1] x (365/days)\n"
            f"Day counts: USD ACT/360, SGD ACT/365\n"
            f"Spot date: T+2 business days (both US and Singapore markets open)\n"
            f"Forward date: spot + N months, following business day convention\n"
            f"US holidays: NY SIFMA calendar\n"
            f"SG holidays: MOM official calendar\n"
            f"SOFR source: Barchart CME Term SOFR fixings\n"
            f"Forward points source: FWD_Points_Actual_Historical.xlsx\n"
            f"Spot FX source: Yahoo Finance (USDSGD=X) via yfinance\n"
        )
        pd.DataFrame({'Methodology': [methodology_text]}).to_excel(
            writer, sheet_name='Methodology', index=False)

    print(f"    Saved {len(output_df)} rows → {os.path.basename(output_path)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("HISTORICAL SWAP IMPLIED RATE BUILDER")
    print("=" * 70)

    print("\n[1/4] Loading input data...")
    sofr = load_sofr_data()
    fwd = load_forward_points()
    fx = load_spot_fx()

    # Determine all years across the merged data
    all_dates = pd.concat([sofr['1M']['Date'], fwd['Date'], fx['Date']])
    all_years = sorted(all_dates.dt.year.unique().tolist())
    print(f"\n[2/4] Initialising holiday calendars for years {all_years}...")
    calendar = HolidayCalendar(years=all_years)

    print("\n[3/4] Calculating implied rates...")
    for tenor in ['1M', '3M', '6M']:
        output_df = build_tenor(tenor, sofr[tenor], fwd, fx, calendar)

        print(f"\n[4/4] Saving {tenor} output...")
        save_output(output_df, tenor, OUTPUT_FILES[tenor])

        print(f"  Summary — {tenor}:")
        print(f"    Avg Implied SGD: {output_df['Implied_SGD_Rate_Pct'].mean():.4f}%")
        print(f"    Avg USD SOFR:    {output_df[f'USD_SOFR_{tenor}_Pct'].mean():.4f}%")
        print(f"    Avg Diff:        {output_df['Rate_Diff_bps'].mean():.1f} bps")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    for tenor, path in OUTPUT_FILES.items():
        print(f"  {tenor}: {path}")


if __name__ == '__main__':
    main()
