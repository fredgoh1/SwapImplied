# Swap-Implied Rate Data Updater

Automated tool to extract SOFR rates, USD/SGD FX rates, and forward points from multiple sources and append them to master Excel files for swap-implied rate analysis.

## Overview

This script automates the daily data collection process for swap-implied rate calculations by:

1. **Extracting 1M, 3M, and 6M SOFR rates** from global-rates.com
2. **Extracting 1M, 3M, and 6M USD/SGD forward points** from investing.com (computing mid rates from bid/ask)
3. **Extracting current USD/SGD FX spot rate** from multiple free API sources
4. **Appending data** to period-specific master Excel files

## Data Sources

| Data Type | Source | URL |
|-----------|--------|-----|
| SOFR Rates | Global-Rates.com | https://www.global-rates.com/en/interest-rates/cme-term-sofr/ |
| Forward Points | Investing.com | https://www.investing.com/currencies/usd-sgd-forward-rates |
| FX Spot Rate | ExchangeRate-API (primary) | https://open.er-api.com/v6/latest/USD |
| FX Spot Rate | XE.com (fallback) | https://www.xe.com/currencyconverter/ |

## Installation

### Required Python Packages

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pandas` - Excel file handling
- `openpyxl` - Excel file manipulation

**Optional (for Selenium mode):**
- `selenium` - Browser automation
- `webdriver-manager` - Automatic ChromeDriver management

### Complete Installation Command

```bash
pip install requests beautifulsoup4 pandas openpyxl selenium webdriver-manager
```

## File Structure

### Expected Directory Layout

```
project/
├── update_swap_implied_data.py    # Main script
├── requirements_swap.txt           # Python dependencies
├── README_swap_implied.md          # This file
└── ../swap_implied_input/         # Input directory (sibling folder in parent)
    ├── input_master_1m.xlsx       # 1-month data
    ├── input_master_3m.xlsx       # 3-month data
    └── input_master_6m.xlsx       # 6-month data
```

### Master File Format

Each master file (`input_master_1m.xlsx`, `input_master_3m.xlsx`, `input_master_6m.xlsx`) must have the following columns:

| Date | xmSOFR | USDSGD_FX | ForwardPoints |
|------|---------|-----------|---------------|
| 2025-02-01 | 4.50 | 1.3450 | -25.50 |
| 2025-02-02 | 4.51 | 1.3455 | -25.60 |
| 2025-02-06 | 4.52 | 1.3460 | -25.65 |

**Where:**
- `xmSOFR` is `1mSOFR`, `3mSOFR`, or `6mSOFR` depending on the file
- All forward points are **mid rates** (average of bid and ask)

## Usage

### Basic Usage

```bash
python update_swap_implied_data.py
```

This runs the script in normal mode using the fast `requests` method.

### With Selenium (More Reliable)

```bash
python update_swap_implied_data.py --selenium
```

Uses Selenium for web scraping, which is slower but more reliable against anti-bot measures.

### Custom Input Directory

```bash
python update_swap_implied_data.py --input-dir /path/to/your/data
```

Specify a different directory containing the master Excel files.

### Create Sample Files

```bash
python update_swap_implied_data.py --create-sample
```

Creates sample master files in `/swap_implied_input/` for testing.

### Combined Options

```bash
python update_swap_implied_data.py --selenium --input-dir ./my_data
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--selenium` | Use Selenium instead of requests (more reliable but slower) |
| `--input-dir PATH` | Directory containing master files (default: `/swap_implied_input`) |
| `--create-sample` | Create sample master files for testing |
| `--help` | Show help message |

## How It Works

### Data Extraction Process

1. **SOFR Rates Extraction**
   - Scrapes the CME Term SOFR table from global-rates.com
   - Identifies 1-month, 3-month, and 6-month tenors
   - Extracts percentage rates

2. **Forward Points Extraction**
   - Scrapes USD/SGD forward rates table from investing.com
   - Identifies USDSGD 1M FWD, 3M FWD, and 6M FWD rows
   - Extracts bid and ask prices
   - Computes mid rate: `(bid + ask) / 2`
   - Returns forward points in pips

3. **FX Spot Rate Extraction**
   - Tries multiple free API sources in order:
     1. ExchangeRate-API (no key required)
     2. XE.com (web scraping fallback)
   - Returns USD/SGD spot rate (e.g., 1.3450)

### File Update Process

1. Reads each master file (1M, 3M, 6M)
2. Validates column structure
3. Checks if today's data already exists (prevents duplicates)
4. Appends new row with:
   - Today's date (YYYY-MM-DD format)
   - Corresponding SOFR rate
   - Current USD/SGD FX rate
   - Corresponding forward points (mid rate)
5. Saves updated file

## Example Output

```
======================================================================
SWAP-IMPLIED RATE DATA UPDATER
======================================================================

✓ All master files found

EXTRACTING DATA FROM SOURCES
----------------------------------------------------------------------
Extracting SOFR rates...
✓ SOFR rates extracted: 1M=4.50%, 3M=4.55%, 6M=4.60%
Extracting USD/SGD FX rate...
✓ USD/SGD FX rate: 1.3450
Extracting forward points...
✓ Forward points extracted: 1M=-27.47, 3M=-77.73, 6M=-148.97

UPDATING MASTER FILES
----------------------------------------------------------------------

Updating input_master_1m.xlsx...
  ✓ Successfully appended: Date=2025-02-06, SOFR=4.50%, FX=1.3450, FP=-27.47

Updating input_master_3m.xlsx...
  ✓ Successfully appended: Date=2025-02-06, SOFR=4.55%, FX=1.3450, FP=-77.73

Updating input_master_6m.xlsx...
  ✓ Successfully appended: Date=2025-02-06, SOFR=4.60%, FX=1.3450, FP=-148.97

======================================================================
SUMMARY
======================================================================
Successfully updated: 3/3 files
  ✓ 1M: success
  ✓ 3M: success
  ✓ 6M: success
======================================================================
```

## Scheduling Automatic Updates

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 9:00 AM (after market open)
4. Action: Start a program
   - Program: `python` or `C:\Python311\python.exe`
   - Arguments: `C:\path\to\update_swap_implied_data.py`
   - Start in: `C:\path\to\`

### Linux/Mac (cron)

Add to crontab (`crontab -e`):

```bash
# Run daily at 9:00 AM SGT (after market open)
0 9 * * 1-5 cd /path/to/script && /usr/bin/python3 update_swap_implied_data.py >> /path/to/logs/update.log 2>&1
```

**Note:** The `1-5` restricts execution to weekdays only.

### Advanced: Retry Logic with Selenium Fallback

Create a wrapper script (`run_with_fallback.sh`):

```bash
#!/bin/bash
# Try requests first, fallback to Selenium if it fails

python3 update_swap_implied_data.py

if [ $? -ne 0 ]; then
    echo "First attempt failed, trying with Selenium..."
    python3 update_swap_implied_data.py --selenium
fi
```

## Error Handling

### Duplicate Prevention

The script automatically checks if data for today's date already exists in each file and skips that file if found:

```
Updating input_master_1m.xlsx...
  ⚠ Data for 2025-02-06 already exists. Skipping...
```

### Network Errors

If the script can't reach a data source, it will:
1. Try alternative sources (for FX rates)
2. Suggest using `--selenium` flag
3. Exit with error code 1

### Missing Files

If master files are missing:

```
✗ Missing files: ../swap_implied_input/input_master_1m.xlsx

Run with --create-sample to create sample master files
```

## Troubleshooting

### "Could not extract all SOFR rates"

**Cause:** Website structure changed or blocking requests

**Solutions:**
1. Try with `--selenium` flag
2. Check if website is accessible in browser
3. Update table parsing logic if website structure changed

### "Forward rates table not found"

**Cause:** Investing.com may be blocking automated requests

**Solutions:**
1. Use `--selenium` flag (simulates real browser)
2. Add delay between requests
3. Check if website requires login

### "Could not extract FX rate from any source"

**Cause:** All FX API sources failed

**Solutions:**
1. Check internet connectivity
2. Verify API endpoints are still active
3. Consider adding API key for premium FX sources

### "Column mismatch" Warning

**Cause:** Master file has different column structure

**Solution:** Ensure columns are exactly:
```
Date | xmSOFR | USDSGD_FX | ForwardPoints
```

where `x` is 1, 3, or 6.

### Selenium Issues

**Chrome not found:**
```bash
# Install Chrome browser first
# Ubuntu/Debian:
sudo apt-get install google-chrome-stable

# MacOS:
brew install --cask google-chrome
```

**ChromeDriver issues:**
```bash
pip install webdriver-manager  # Auto-downloads ChromeDriver
```

## Data Validation

### Manual Verification

After running the script, verify the data:

```python
import pandas as pd

# Check 1M file
df = pd.read_excel('../swap_implied_input/input_master_1m.xlsx')
print(df.tail())  # View last 5 rows

# Verify today's data
today = pd.to_datetime('today').strftime('%Y-%m-%d')
today_data = df[df['Date'] == today]
print(today_data)
```

### Expected Data Ranges

- **SOFR Rates:** Typically 0% - 10% (4-5% as of early 2025)
- **USD/SGD FX:** Typically 1.2000 - 1.4000
- **Forward Points:** Typically -200 to +200 pips

## Advanced Usage

### Programmatic Integration

```python
from update_swap_implied_data import DataExtractor, DataUpdater

# Initialize
extractor = DataExtractor(use_selenium=False)
updater = DataUpdater(input_dir='/path/to/data')

# Extract data
sofr_rates = extractor.extract_sofr_rates()
fx_rate = extractor.extract_usdsgd_fx()
forward_points = extractor.extract_forward_points()

# Update files
if all([sofr_rates, fx_rate, forward_points]):
    results = updater.update_files(sofr_rates, fx_rate, forward_points)
    print(f"Updated {sum(1 for r in results.values() if r == 'success')} files")
```

### Custom Data Processing

After updating master files, you can process the data:

```python
import pandas as pd
import numpy as np

# Load all periods
df_1m = pd.read_excel('../swap_implied_input/input_master_1m.xlsx')
df_3m = pd.read_excel('../swap_implied_input/input_master_3m.xlsx')
df_6m = pd.read_excel('../swap_implied_input/input_master_6m.xlsx')

# Calculate implied forward rates
df_1m['Date'] = pd.to_datetime(df_1m['Date'])
df_1m['ImpliedForwardRate'] = df_1m['1mSOFR'] + (df_1m['ForwardPoints'] / 10000)

# Analyze trends
print(df_1m[['Date', '1mSOFR', 'ForwardPoints', 'ImpliedForwardRate']].tail(10))
```

## Technical Details

### Web Scraping Methods

| Method | Speed | Reliability | Browser | Use Case |
|--------|-------|-------------|---------|----------|
| Requests | Fast (5s) | Medium | No | Regular daily updates |
| Selenium | Slow (20s) | High | Yes | When requests fails |

### Rate Calculation: Forward Points Mid Rate

Forward points mid rate is calculated as:

```
Mid Rate = (Bid + Ask) / 2
```

Example:
- Bid: -27.47
- Ask: -27.17
- Mid: (-27.47 + -27.17) / 2 = **-27.32**

### FX Rate Fallback Logic

```
1. Try ExchangeRate-API (free, no key)
   ↓ (if fails)
2. Try XE.com (web scraping)
   ↓ (if fails)
3. Return None (error)
```

## Best Practices

### 1. Run During Market Hours

For most accurate data, run after:
- 9:00 AM SGT (Singapore market open)
- 3:00 PM SGT (after US overnight rates publish)

### 2. Keep Backups

```bash
# Backup before updating
cp -r ../swap_implied_input ../swap_implied_input_backup_$(date +%Y%m%d)
```

### 3. Monitor Logs

Set up logging when running via cron:

```bash
0 9 * * 1-5 cd /path && python3 update_swap_implied_data.py >> logs/update_$(date +\%Y\%m\%d).log 2>&1
```

### 4. Validate Data Quality

Implement data quality checks:
- Check for missing values
- Verify rates are within expected ranges
- Compare with previous day's data for anomalies

## Limitations & Disclaimers

⚠️ **Important Notes:**

1. **Data Accuracy:** This script relies on publicly available data sources which may have delays or inaccuracies
2. **Rate Limiting:** Excessive requests may result in IP blocking
3. **Website Changes:** Source websites may change structure, breaking the scraper
4. **No Warranty:** Use at your own risk for educational/analytical purposes
5. **Compliance:** Ensure usage complies with each website's Terms of Service

## Support & Contributions

### Common Issues Database

See `TROUBLESHOOTING.md` for detailed issue resolution steps.

### Reporting Bugs

When reporting issues, include:
1. Full error message
2. Python version (`python --version`)
3. OS and version
4. Command used
5. Sample output/logs

## License

This tool is provided for educational and analytical purposes. Please respect the Terms of Service of all data sources.

---

**Last Updated:** February 2025  
**Version:** 2.0.0  
**Maintainer:** Financial Data Automation Team
