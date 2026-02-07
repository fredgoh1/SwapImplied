# USD/SGD FX Swap Implied Rate Calculator - Multi-Tenor Version

## Overview

This Python tool calculates implied Singapore Dollar (SGD) interest rates from USD/SGD FX swap market data using Covered Interest Rate Parity (CIP) for **multiple tenors: 1-month, 3-month, and 6-month**.

**NEW in v2.0:** Support for 1M, 3M, and 6M tenors with automatic column detection!

## Key Features

✅ **Multi-tenor support**: 1M, 3M, and 6M  
✅ **Automatic tenor detection** from column names  
✅ **Flexible column naming** (e.g., 1mSOFR, 3M_SOFR, 6 month SOFR)  
✅ **Proper T+2 settlement** with both US and Singapore market holidays  
✅ **Business day conventions** for FX spot and forward dates  
✅ **Precise day count conventions** (ACT/360 for USD, ACT/365 for SGD)  
✅ **Official holiday calendars** from NY SIFMA and Singapore MOM  
✅ **Command-line interface** with arguments  

## Quick Start

```bash
# Install
pip install pandas openpyxl requests beautifulsoup4 --break-system-packages

# Run with automatic tenor detection
python calculate_swap_implied_rates.py input.xlsx output.xlsx

# Or specify tenor explicitly
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M
```

## Usage Examples

```bash
# 1-month calculation
python calculate_swap_implied_rates.py data_1m.xlsx results_1m.xlsx --tenor 1M

# 3-month calculation  
python calculate_swap_implied_rates.py data_3m.xlsx results_3m.xlsx --tenor 3M

# 6-month calculation
python calculate_swap_implied_rates.py data_6m.xlsx results_6m.xlsx --tenor 6M

# Auto-detect tenor from column names
python calculate_swap_implied_rates.py data.xlsx results.xlsx
```

## Input File Format

Your Excel file should have these columns (column names are flexible):

| Column          | Variations Accepted           | Example Values |
|-----------------|-------------------------------|----------------|
| Date            | Date, Trade Date              | 2026-01-30     |
| [Tenor]SOFR     | 1mSOFR, 3M_SOFR, 6 month SOFR| 3.75000        |
| USDSGD_FX       | USD/SGD, FX, Spot Rate        | 1.2669         |
| Forward Points  | Fwd Pts, Forward_Points       | -75.50         |

**The script will automatically detect which tenor you're using!**

## Expected Results by Tenor

| Tenor | Typical Days | Example Implied SGD | Example USD SOFR | Differential |
|-------|--------------|---------------------|------------------|--------------|
| **1M**| 28-31        | ~1.17%              | ~3.67%           | -250 bps     |
| **3M**| 89-92        | ~1.37%              | ~3.75%           | -238 bps     |
| **6M**| 181-184      | ~1.43%              | ~3.85%           | -242 bps     |

## Output

The output Excel file contains 3 sheets:

1. **Results** - All calculations including Implied_SGD_Rate_Pct (your key output)
2. **Summary** - Statistics (averages, min/max, count)
3. **Methodology** - Detailed calculation explanation for the tenor

## Command-Line Options

```
python calculate_swap_implied_rates.py INPUT OUTPUT [OPTIONS]

Arguments:
  INPUT                 Input Excel file
  OUTPUT                Output Excel file (optional, defaults to swap_implied_rates_output.xlsx)
  --tenor {1M,3M,6M}   Specify tenor (optional, will auto-detect if not specified)
  --quiet              Suppress verbose output
  --help               Show help message
```

## Sample Results

### 1M Tenor (28 days)
- Trade: Jan 30, 2026
- Spot: Feb 3, 2026  
- Forward: Mar 3, 2026
- **Implied SGD: 1.17%** vs USD SOFR: 3.67%

### 3M Tenor (90 days)
- Trade: Jan 30, 2026
- Spot: Feb 3, 2026
- Forward: May 4, 2026
- **Implied SGD: 1.36%** vs USD SOFR: 3.75%

### 6M Tenor (181 days)
- Trade: Jan 30, 2026
- Spot: Feb 3, 2026
- Forward: Aug 3, 2026
- **Implied SGD: 1.43%** vs USD SOFR: 3.85%

## Methodology

All tenors use the same **Covered Interest Parity (CIP)** formula:

```
r_SGD = [(F/S) × (1 + r_USD × days/360) - 1] × (365/days)
```

The key differences:
- **1M:** Forward = Spot + 1 month
- **3M:** Forward = Spot + 3 months  
- **6M:** Forward = Spot + 6 months

All calculations use:
- **T+2 settlement** (both markets must be open)
- **Official holidays** (US NY SIFMA + Singapore MOM)
- **Day counts:** ACT/360 (USD), ACT/365 (SGD)
- **Business day adjustment:** Following convention

## Data Sources

- **Term SOFR:** https://www.cmegroup.com/markets/interest-rates/sofr.html
- **USD/SGD Rates:** Bloomberg, Refinitiv, or https://www.mas.gov.sg/statistics
- **Forward Points:** Bloomberg or https://www.investing.com/currencies/usd-sgd-forward-rates
- **Holidays:** 
  - US: NY SIFMA calendar
  - Singapore: https://www.mom.gov.sg/employment-practices/public-holidays

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not auto-detect tenor" | Add `--tenor 3M` to specify tenor |
| "Could not find SOFR column" | Rename column to include tenor (e.g., "3mSOFR") |
| Wrong implied rates | Check forward points are in pips, not decimal |
| Unexpected days | Month-end and holiday adjustments can vary days |

## Advanced: Adding New Tenors

To add 9M or 12M support, just update the `TENOR_MONTHS` dictionary in the code:

```python
TENOR_MONTHS = {
    '1M': 1,
    '3M': 3,
    '6M': 6,
    '9M': 9,    # Add this
    '12M': 12   # Add this
}
```

Everything else works automatically!

## Files Included

- `calculate_swap_implied_rates.py` - Main script
- `README.md` - This file
- `QUICKSTART.md` - Quick reference guide
- `requirements.txt` - Python dependencies

## Version

**Version:** 2.0.0  
**Date:** February 6, 2026  
**Python:** 3.7+

---

For detailed methodology and technical documentation, see the Methodology sheet in the output Excel file.
