# Quick Start Guide - Multi-Tenor USD/SGD Swap Calculator

## 1. Installation (30 seconds)

```bash
pip install pandas openpyxl --break-system-packages
```

## 2. Prepare Your Input (1 minute)

### For 1-Month Calculations

| Date       | 1mSOFR  | USDSGD_FX | Forward Points |
|------------|---------|-----------|----------------|
| 2026-01-30 | 3.66877 | 1.2669    | -24.68         |

### For 3-Month Calculations

| Date       | 3mSOFR | USDSGD_FX | Forward Points |
|------------|--------|-----------|----------------|
| 2026-01-30 | 3.75   | 1.2669    | -75.50         |

### For 6-Month Calculations

| Date       | 6mSOFR | USDSGD_FX | Forward Points |
|------------|--------|-----------|----------------|
| 2026-01-30 | 3.85   | 1.2669    | -152.30        |

**Column names are flexible!** The script accepts variations like:
- `1mSOFR`, `3M_SOFR`, `6 month SOFR`, `SOFR_1M`
- `USDSGD_FX`, `USD/SGD`, `FX`, `Spot Rate`

## 3. Run the Calculator (10 seconds)

### Option A: Auto-Detect Tenor (Easiest!)

```bash
python calculate_swap_implied_rates.py input.xlsx output.xlsx
```

The script will automatically detect whether you have 1M, 3M, or 6M data!

### Option B: Specify Tenor Explicitly

```bash
# For 1-month
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 1M

# For 3-month  
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M

# For 6-month
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 6M
```

## 4. View Results

Open the output Excel file. You'll see 3 sheets:

### Sheet 1: Results
Your calculated implied SGD rates are in the **Implied_SGD_Rate_Pct** column.

### Sheet 2: Summary  
Quick statistics like average rates, differentials, and day counts.

### Sheet 3: Methodology
Detailed explanation of how calculations were performed for your tenor.

## Quick Results Comparison

Using the same trade date (Jan 30, 2026):

| Tenor | Days | Spot Date  | Forward Date | Implied SGD | USD SOFR | Diff    |
|-------|------|------------|--------------|-------------|----------|---------|
| **1M**| 28   | 2026-02-03 | 2026-03-03   | **1.17%**   | 3.67%    | -250 bps|
| **3M**| 90   | 2026-02-03 | 2026-05-04   | **1.36%**   | 3.75%    | -239 bps|
| **6M**| 181  | 2026-02-03 | 2026-08-03   | **1.43%**   | 3.85%    | -242 bps|

## Command Cheat Sheet

```bash
# Auto-detect (recommended)
python calculate_swap_implied_rates.py input.xlsx output.xlsx

# Specify 1M
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 1M

# Specify 3M
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M

# Specify 6M  
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 6M

# Quiet mode (less output)
python calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M --quiet

# Help
python calculate_swap_implied_rates.py --help
```

## What Each Tenor Calculates

### 1-Month (1M)
- **Forward Date:** ~1 month after spot date
- **Typical Days:** 28-31 days
- **Use For:** Short-term rate comparisons, monthly hedging

### 3-Month (3M)
- **Forward Date:** ~3 months after spot date
- **Typical Days:** 89-92 days  
- **Use For:** Quarterly planning, standard swap tenors

### 6-Month (6M)
- **Forward Date:** ~6 months after spot date
- **Typical Days:** 181-184 days
- **Use For:** Semi-annual hedging, longer-term rate views

## Troubleshooting

### "Could not auto-detect tenor"
**Fix:** Add `--tenor 3M` to your command

### "Could not find SOFR column"  
**Fix:** Make sure your SOFR column includes the tenor (e.g., "3mSOFR" or "SOFR_3M")

### Different days than expected
**Explanation:** Business day adjustments and month-end rules can vary the exact day count

### All rates seem wrong
**Check:** 
- Forward points are in **pips** (not decimal)
- Spot rate is **SGD per USD** (e.g., 1.2669, not 0.789)
- SOFR is in **percent** (e.g., 3.75, not 0.0375)

## Where to Get Data

### Term SOFR
- **1M:** https://www.global-rates.com/en/interest-rates/cme-term-sofr/1/
- **3M:** https://www.global-rates.com/en/interest-rates/cme-term-sofr/2/
- **6M:** https://www.global-rates.com/en/interest-rates/cme-term-sofr/3/

### USD/SGD Spot & Forward Points
- Bloomberg: `USDSGD Curncy`, `USDSGD3M Curncy`
- Investing.com: https://www.investing.com/currencies/usdforward-rates
- MAS: https://www.mas.gov.sg/statistics

## Expected Forward Points

Typical ranges (negative = SGD appreciation expected):

| Tenor | Typical Range (pips) |
|-------|---------------------|
| 1M    | -20 to -30          |
| 3M    | -70 to -80          |
| 6M    | -145 to -160        |

## Next Steps

1. ✅ Run your first calculation
2. 📊 Check the Summary sheet for statistics  
3. 📖 Read the Methodology sheet to understand the math
4. 🔄 Process multiple dates to track rate changes over time
5. 📈 Compare implied rates across tenors to see the SGD yield curve

## Advanced Tips

### Batch Processing
Run the same script on multiple files:
```bash
python calculate_swap_implied_rates.py jan_data.xlsx jan_results.xlsx --tenor 3M
python calculate_swap_implied_rates.py feb_data.xlsx feb_results.xlsx --tenor 3M
python calculate_swap_implied_rates.py mar_data.xlsx mar_results.xlsx --tenor 3M
```

### Mix and Match  
You can have different tenors in different files. The auto-detection will handle each correctly!

---

**You're ready to calculate swap implied rates for any tenor!** 🚀

For detailed documentation, see README.md
