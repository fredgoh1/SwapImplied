#!/usr/bin/env python3
"""
USD/SGD FX Swap Implied Rate Calculator - Multi-Tenor Version

This script calculates implied SGD interest rates from USD/SGD FX swap data
using Covered Interest Rate Parity (CIP) with proper business day conventions.

Supports: 1-month, 3-month, and 6-month tenors

Requirements:
    pip install pandas openpyxl requests beautifulsoup4 --break-system-packages

Usage:
    python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 1M
    python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M
    python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 6M

Input Excel Format:
    Columns: Date, SOFR (e.g., 1mSOFR, 3mSOFR, 6mSOFR), USDSGD_FX, Forward Points
    
Output Excel Format:
    All input columns plus calculated fields for specified tenor
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import argparse
import requests
from bs4 import BeautifulSoup
import re


class HolidayCalendar:
    """Manages US and Singapore holiday calendars with automatic fetching"""
    
    def __init__(self, year=2026):
        self.year = year
        self.us_holidays = self._get_us_holidays()
        self.sg_holidays = self._get_sg_holidays()
    
    def _get_us_holidays(self):
        """
        Get US banking holidays for the year
        Source: NY SIFMA recommended calendar
        """
        # Standard US banking holidays for 2026
        holidays = [
            datetime(2026, 1, 1),   # New Year's Day
            datetime(2026, 1, 19),  # MLK Day
            datetime(2026, 2, 16),  # Presidents Day
            datetime(2026, 4, 3),   # Good Friday
            datetime(2026, 5, 25),  # Memorial Day
            datetime(2026, 7, 3),   # Independence Day (observed)
            datetime(2026, 9, 7),   # Labor Day
            datetime(2026, 10, 12), # Columbus Day
            datetime(2026, 11, 11), # Veterans Day
            datetime(2026, 11, 26), # Thanksgiving
            datetime(2026, 12, 25), # Christmas
        ]
        
        print(f"Loaded {len(holidays)} US banking holidays for {self.year}")
        return holidays
    
    def _get_sg_holidays(self):
        """
        Get Singapore public holidays for the year
        Source: Ministry of Manpower (MOM) official calendar
        URL: https://www.mom.gov.sg/employment-practices/public-holidays
        """
        # Official Singapore public holidays for 2026 from MOM
        holidays = [
            datetime(2026, 1, 1),   # New Year's Day
            datetime(2026, 2, 17),  # Chinese New Year
            datetime(2026, 2, 18),  # Chinese New Year
            # Mar 21 (Sat) Hari Raya Puasa - falls on Saturday, no substitute
            datetime(2026, 4, 3),   # Good Friday
            datetime(2026, 5, 1),   # Labour Day
            datetime(2026, 5, 27),  # Hari Raya Haji
            # May 31 (Sun) Vesak Day - observed on Monday
            datetime(2026, 6, 1),   # Vesak Day observed
            # Aug 9 (Sun) National Day - observed on Monday
            datetime(2026, 8, 10),  # National Day observed
            # Nov 8 (Sun) Deepavali - observed on Monday
            datetime(2026, 11, 9),  # Deepavali observed
            datetime(2026, 12, 25), # Christmas Day
        ]
        
        print(f"Loaded {len(holidays)} Singapore public holidays for {self.year}")
        return holidays
    
    def is_business_day(self, date):
        """
        Check if a date is a business day in BOTH USD and SGD markets
        
        Args:
            date: datetime object
            
        Returns:
            bool: True if business day in both markets
        """
        # Weekend check
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Holiday check - must be working day in BOTH markets
        if date in self.us_holidays or date in self.sg_holidays:
            return False
        
        return True
    
    def add_business_days(self, start_date, num_days, verbose=False):
        """
        Add business days where both markets are open
        
        Args:
            start_date: datetime object
            num_days: number of business days to add
            verbose: print debug information
            
        Returns:
            datetime: resulting date
        """
        current = start_date
        added = 0
        
        if verbose:
            print(f"  Starting from: {current.strftime('%Y-%m-%d %A')}")
        
        while added < num_days:
            current += timedelta(days=1)
            if self.is_business_day(current):
                added += 1
                if verbose:
                    print(f"    +{added}: {current.strftime('%Y-%m-%d %A')} ✓")
            elif verbose:
                reason = ""
                if current.weekday() >= 5:
                    reason = "(Weekend)"
                elif current in self.us_holidays and current in self.sg_holidays:
                    reason = "(Holiday in BOTH)"
                elif current in self.us_holidays:
                    reason = "(US Holiday)"
                elif current in self.sg_holidays:
                    reason = "(SG Holiday)"
                print(f"    Skip: {current.strftime('%Y-%m-%d %A')} {reason}")
        
        return current


class SwapImpliedRateCalculator:
    """Calculates implied interest rates from FX swap data using CIP"""
    
    # Tenor to month mapping
    TENOR_MONTHS = {
        '1M': 1,
        '3M': 3,
        '6M': 6
    }
    
    def __init__(self, holiday_calendar, tenor='1M'):
        self.calendar = holiday_calendar
        self.tenor = tenor.upper()
        
        if self.tenor not in self.TENOR_MONTHS:
            raise ValueError(f"Invalid tenor: {tenor}. Must be one of: {list(self.TENOR_MONTHS.keys())}")
        
        self.months = self.TENOR_MONTHS[self.tenor]
        print(f"Calculator initialized for {self.tenor} tenor ({self.months} months)")
    
    def calculate_spot_date(self, trade_date, verbose=False):
        """
        Calculate spot date (T+2 business days)
        
        Args:
            trade_date: datetime object
            verbose: print debug information
            
        Returns:
            datetime: spot value date
        """
        return self.calendar.add_business_days(trade_date, 2, verbose)
    
    def calculate_forward_date(self, spot_date):
        """
        Calculate forward date based on tenor
        Convention: Same day next month(s), adjusted to business day (following)
        
        Args:
            spot_date: datetime object
            
        Returns:
            datetime: forward value date
        """
        # Add specified months (same day N months later)
        year = spot_date.year
        month = spot_date.month + self.months
        day = spot_date.day
        
        # Handle month overflow
        while month > 12:
            month -= 12
            year += 1
        
        # Handle day overflow (e.g., Jan 31 -> Feb 28)
        while True:
            try:
                tentative = datetime(year, month, day)
                break
            except ValueError:
                day -= 1
        
        # Adjust to business day using following business day convention
        while not self.calendar.is_business_day(tentative):
            tentative += timedelta(days=1)
        
        return tentative
    
    @staticmethod
    def calculate_forward_rate(spot_rate, forward_points_pips):
        """
        Calculate forward FX rate from spot and forward points
        
        Args:
            spot_rate: spot FX rate (SGD per USD)
            forward_points_pips: forward points in pips (1 pip = 0.0001)
            
        Returns:
            float: forward FX rate
        """
        return spot_rate + (forward_points_pips / 10000)
    
    @staticmethod
    def calculate_implied_sgd_rate(spot_rate, forward_rate, usd_rate, days):
        """
        Calculate implied SGD interest rate using Covered Interest Parity
        
        Formula:
            F = S × (1 + r_SGD × days/365) / (1 + r_USD × days/360)
        
        Solving for r_SGD:
            r_SGD = [(F/S) × (1 + r_USD × days/360) - 1] × (365/days)
        
        Args:
            spot_rate: spot FX rate (SGD per USD)
            forward_rate: forward FX rate (SGD per USD)
            usd_rate: USD interest rate in percent (e.g., 3.66877)
            days: actual days between spot and forward
            
        Returns:
            float: implied SGD rate in percent
        """
        # Calculate F/S ratio
        fs_ratio = forward_rate / spot_rate
        
        # Calculate USD interest factor (ACT/360)
        usd_factor = 1 + (usd_rate / 100) * (days / 360)
        
        # Calculate SGD interest factor
        sgd_factor = fs_ratio * usd_factor
        
        # Solve for SGD rate (ACT/365)
        sgd_rate = (sgd_factor - 1) * (365 / days)
        
        return sgd_rate * 100  # Convert to percent
    
    def process_row(self, trade_date, sofr_rate, spot_rate, forward_points, verbose=False):
        """
        Process a single row of data and calculate implied SGD rate
        
        Args:
            trade_date: datetime object
            sofr_rate: Term SOFR rate for the tenor (%)
            spot_rate: USD/SGD spot FX rate
            forward_points: Forward points in pips for the tenor
            verbose: print detailed calculation steps
            
        Returns:
            dict: calculated values
        """
        # Calculate value dates
        spot_date = self.calculate_spot_date(trade_date, verbose)
        forward_date = self.calculate_forward_date(spot_date)
        
        # Calculate actual days
        actual_days = (forward_date - spot_date).days
        
        # Calculate forward rate
        forward_rate = self.calculate_forward_rate(spot_rate, forward_points)
        
        # Calculate implied SGD rate
        implied_sgd_rate = self.calculate_implied_sgd_rate(
            spot_rate, forward_rate, sofr_rate, actual_days
        )
        
        # Calculate rate differential
        rate_diff_bps = (implied_sgd_rate - sofr_rate) * 100
        
        if verbose:
            print(f"\nCalculation for Trade Date: {trade_date.strftime('%Y-%m-%d')} [{self.tenor}]")
            print(f"  Spot Date:        {spot_date.strftime('%Y-%m-%d (%A)')}")
            print(f"  Forward Date:     {forward_date.strftime('%Y-%m-%d (%A)')}")
            print(f"  Actual Days:      {actual_days}")
            print(f"  Spot Rate:        {spot_rate:.4f}")
            print(f"  Forward Points:   {forward_points:.2f} pips")
            print(f"  Forward Rate:     {forward_rate:.4f}")
            print(f"  USD SOFR {self.tenor}:    {sofr_rate:.5f}%")
            print(f"  Implied SGD {self.tenor}:  {implied_sgd_rate:.4f}%")
            print(f"  Differential:     {rate_diff_bps:.1f} bps")
        
        return {
            'Spot_Date': spot_date,
            'Forward_Date': forward_date,
            'Actual_Days': actual_days,
            'Forward_Rate': forward_rate,
            'Implied_SGD_Rate_Pct': implied_sgd_rate,
            'Rate_Diff_bps': rate_diff_bps
        }


def detect_tenor_from_columns(df):
    """
    Try to detect tenor from column names in the dataframe
    
    Args:
        df: pandas DataFrame
        
    Returns:
        str: detected tenor ('1M', '3M', or '6M') or None
    """
    columns_str = ' '.join(df.columns).upper()
    
    if '6M' in columns_str or '6 M' in columns_str:
        return '6M'
    elif '3M' in columns_str or '3 M' in columns_str:
        return '3M'
    elif '1M' in columns_str or '1 M' in columns_str:
        return '1M'
    
    return None


def find_sofr_column(df, tenor):
    """
    Find the SOFR column name based on tenor
    
    Args:
        df: pandas DataFrame
        tenor: tenor string ('1M', '3M', '6M')
        
    Returns:
        str: column name or None
    """
    # Try various naming conventions
    possible_names = [
        f'{tenor}SOFR',
        f'{tenor.lower()}SOFR',
        f'{tenor}_SOFR',
        f'SOFR_{tenor}',
        f'{tenor[0]}mSOFR',  # e.g., 1mSOFR
        f'{tenor[0]}MSOFR',
        f'SOFR',  # Generic fallback
    ]
    
    for col in df.columns:
        col_upper = col.upper().replace(' ', '')
        for name in possible_names:
            if name.upper().replace(' ', '') in col_upper:
                return col
    
    return None


def process_excel_file(input_file, output_file, tenor=None, verbose=True):
    """
    Process Excel file with FX swap data and calculate implied rates
    
    Args:
        input_file: path to input Excel file
        output_file: path to output Excel file
        tenor: tenor to use ('1M', '3M', '6M'). If None, will try to auto-detect
        verbose: print progress information
    """
    print("=" * 80)
    print("USD/SGD FX SWAP IMPLIED RATE CALCULATOR - MULTI-TENOR")
    print("=" * 80)
    print()
    
    # Read input file
    print(f"Reading input file: {input_file}")
    df = pd.read_excel(input_file)
    print(f"  Loaded {len(df)} rows")
    print(f"  Columns: {df.columns.tolist()}")
    print()
    
    # Auto-detect tenor if not specified
    if tenor is None:
        detected_tenor = detect_tenor_from_columns(df)
        if detected_tenor:
            tenor = detected_tenor
            print(f"Auto-detected tenor: {tenor}")
        else:
            raise ValueError("Could not auto-detect tenor from column names. Please specify --tenor")
    else:
        tenor = tenor.upper()
        print(f"Using specified tenor: {tenor}")
    
    print()
    
    # Find SOFR column
    sofr_col = find_sofr_column(df, tenor)
    if sofr_col is None:
        raise ValueError(f"Could not find SOFR column for tenor {tenor}. Available columns: {df.columns.tolist()}")
    
    print(f"Using SOFR column: '{sofr_col}'")
    
    # Validate other required columns
    required_base_cols = ['Date', 'USDSGD_FX', 'Forward Points']
    missing_cols = []
    
    if 'Date' not in df.columns:
        missing_cols.append('Date')
    
    # Check for USDSGD_FX or similar
    fx_col = None
    for col in df.columns:
        if 'USDSGD' in col.upper() or 'USD/SGD' in col.upper() or 'FX' in col.upper():
            fx_col = col
            break
    if fx_col is None:
        missing_cols.append('USDSGD_FX (or similar)')
    
    # Check for Forward Points
    fwd_pts_col = None
    for col in df.columns:
        if 'FORWARD' in col.upper() and 'POINT' in col.upper():
            fwd_pts_col = col
            break
    if fwd_pts_col is None:
        missing_cols.append('Forward Points')
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    print(f"Using FX Spot column: '{fx_col}'")
    print(f"Using Forward Points column: '{fwd_pts_col}'")
    print()
    
    # Initialize calculators
    first_year = pd.to_datetime(df['Date'].iloc[0]).year
    print(f"Initializing holiday calendars for year {first_year}...")
    calendar = HolidayCalendar(year=first_year)
    calculator = SwapImpliedRateCalculator(calendar, tenor=tenor)
    print()
    
    # Process each row
    print(f"Processing {len(df)} trades for {tenor} tenor...")
    print("-" * 80)
    
    results = []
    for idx, row in df.iterrows():
        trade_date = pd.to_datetime(row['Date'])
        
        result = calculator.process_row(
            trade_date=trade_date,
            sofr_rate=row[sofr_col],
            spot_rate=row[fx_col],
            forward_points=row[fwd_pts_col],
            verbose=verbose
        )
        
        results.append(result)
        print("-" * 80)
    
    # Create output dataframe
    results_df = pd.DataFrame(results)
    output_df = pd.concat([df, results_df], axis=1)
    
    # Reorder columns for better readability
    output_cols = [
        'Date',
        'Spot_Date',
        'Forward_Date',
        'Actual_Days',
        sofr_col,
        fx_col,
        fwd_pts_col,
        'Forward_Rate',
        'Implied_SGD_Rate_Pct',
        'Rate_Diff_bps'
    ]
    output_df = output_df[output_cols]
    
    # Rename columns for clarity
    rename_dict = {
        'Date': 'Trade_Date',
        sofr_col: f'USD_SOFR_{tenor}_Pct',
        fx_col: 'Spot_Rate',
        fwd_pts_col: 'Forward_Points_pips'
    }
    output_df = output_df.rename(columns=rename_dict)
    
    # Save to Excel
    print()
    print(f"Saving results to: {output_file}")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Write main results
        output_df.to_excel(writer, sheet_name='Results', index=False)
        
        # Write summary statistics
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
                'Average Days'
            ],
            'Value': [
                tenor,
                len(output_df),
                output_df['Implied_SGD_Rate_Pct'].mean(),
                output_df[f'USD_SOFR_{tenor}_Pct'].mean(),
                output_df['Rate_Diff_bps'].mean(),
                output_df['Implied_SGD_Rate_Pct'].min(),
                output_df['Implied_SGD_Rate_Pct'].max(),
                output_df['Actual_Days'].min(),
                output_df['Actual_Days'].max(),
                output_df['Actual_Days'].mean()
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Write methodology
        methodology_text = f"""
USD/SGD FX SWAP IMPLIED RATE CALCULATION METHODOLOGY
TENOR: {tenor} ({SwapImpliedRateCalculator.TENOR_MONTHS[tenor]} months)

1. BUSINESS DAY CALCULATION (T+2)
   - Both US and Singapore markets must be open
   - US holidays: NY SIFMA banking calendar
   - Singapore holidays: MOM official public holidays
   - Spot Date = Trade Date + 2 business days

2. FORWARD DATE CALCULATION ({tenor})
   - Convention: Same day {SwapImpliedRateCalculator.TENOR_MONTHS[tenor]} month(s) later, adjusted to business day
   - Following business day convention if falls on holiday/weekend
   - Handles month-end adjustments (e.g., Jan 31 → Feb 28)

3. DAY COUNT CONVENTIONS
   - USD (SOFR): ACT/360 (Actual days / 360)
   - SGD: ACT/365 (Actual days / 365)

4. COVERED INTEREST PARITY (CIP) FORMULA
   
   F = S × (1 + r_SGD × days/365) / (1 + r_USD × days/360)
   
   Solving for implied SGD rate:
   r_SGD = [(F/S) × (1 + r_USD × days/360) - 1] × (365/days)
   
   Where:
   - F = Forward FX rate (SGD per USD)
   - S = Spot FX rate (SGD per USD)
   - r_SGD = Singapore Dollar interest rate (solving for)
   - r_USD = US Dollar interest rate ({tenor} Term SOFR)
   - days = Actual calendar days between spot and forward

5. FORWARD RATE CALCULATION
   Forward Rate = Spot Rate + (Forward Points / 10,000)
   Note: 1 pip = 0.0001

6. TENOR-SPECIFIC PARAMETERS
   - 1M: ~28-31 days (spot + 1 month)
   - 3M: ~89-92 days (spot + 3 months)
   - 6M: ~181-184 days (spot + 6 months)
   
   Actual days vary based on:
   - Calendar month lengths
   - Business day adjustments
   - Holiday patterns

7. DATA SOURCES
   - US Holidays: NY SIFMA
   - Singapore Holidays: Ministry of Manpower (MOM)
   - URL: https://www.mom.gov.sg/employment-practices/public-holidays
   - Term SOFR: CME Group

8. RATE DIFFERENTIAL
   Differential (bps) = (Implied SGD Rate - USD SOFR Rate) × 100
   Negative differential indicates SGD rates are lower than USD rates

9. ECONOMIC INTERPRETATION
   - Negative forward points → SGD appreciation expected
   - Lower SGD rates → Reflects MAS exchange rate policy
   - Rate differential → Carry trade opportunity
   - Longer tenors → Larger accumulated differential
        """
        
        methodology_df = pd.DataFrame({
            'Methodology': [methodology_text]
        })
        methodology_df.to_excel(writer, sheet_name='Methodology', index=False)
    
    print(f"  Results sheet: calculated implied rates for {tenor}")
    print(f"  Summary sheet: statistics")
    print(f"  Methodology sheet: calculation details")
    print()
    
    # Print summary
    print("=" * 80)
    print(f"SUMMARY STATISTICS - {tenor} TENOR")
    print("=" * 80)
    print(f"Trades processed:           {len(output_df)}")
    print(f"Avg Implied SGD Rate:       {output_df['Implied_SGD_Rate_Pct'].mean():.4f}%")
    print(f"Avg USD SOFR Rate:          {output_df[f'USD_SOFR_{tenor}_Pct'].mean():.4f}%")
    print(f"Avg Rate Differential:      {output_df['Rate_Diff_bps'].mean():.1f} bps")
    print(f"Implied SGD Rate Range:     {output_df['Implied_SGD_Rate_Pct'].min():.4f}% to {output_df['Implied_SGD_Rate_Pct'].max():.4f}%")
    print(f"Days Range:                 {output_df['Actual_Days'].min():.0f} to {output_df['Actual_Days'].max():.0f} days")
    print(f"Average Days:               {output_df['Actual_Days'].mean():.1f} days")
    print()
    print("=" * 80)
    print("CALCULATION COMPLETE")
    print("=" * 80)


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Calculate USD/SGD FX swap implied rates for various tenors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 1M
  python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M
  python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 6M
  python calculate_swap_implied_rates.py input.xlsx output.xlsx  (auto-detect tenor)

Supported Tenors:
  1M - 1 month
  3M - 3 months
  6M - 6 months

Input File Requirements:
  - Date column (trade date)
  - SOFR column (e.g., 1mSOFR, 3mSOFR, 6mSOFR)
  - USDSGD_FX column (spot FX rate)
  - Forward Points column (forward points in pips)
        """
    )
    
    parser.add_argument('input_file', help='Input Excel file path')
    parser.add_argument('output_file', nargs='?', default='swap_implied_rates_output.xlsx',
                        help='Output Excel file path (default: swap_implied_rates_output.xlsx)')
    parser.add_argument('--tenor', '-t', choices=['1M', '3M', '6M', '1m', '3m', '6m'],
                        help='Tenor to calculate (1M, 3M, or 6M). If not specified, will auto-detect from column names')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress verbose output')
    
    args = parser.parse_args()
    
    try:
        process_excel_file(
            args.input_file, 
            args.output_file, 
            tenor=args.tenor,
            verbose=not args.quiet
        )
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
