# Quick Start Guide - Swap-Implied Rate Data Updater

This guide will get you up and running in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Internet connection
- Excel files with proper format (or use sample creation)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install -r requirements_swap.txt
```

This installs all required packages:
- requests, beautifulsoup4, pandas, openpyxl (required)
- selenium, webdriver-manager (optional, for --selenium mode)

### 2. Verify Installation

Run the test script to check everything is working:

```bash
python test_swap_updater.py
```

This will:
- ✓ Verify all packages are installed
- ✓ Create sample test files
- ✓ Test the update functionality

### 3. Create Sample Master Files

```bash
python update_swap_implied_data.py --create-sample
```

This creates three Excel files in `../swap_implied_input/` (a sibling folder in the parent directory):
- `input_master_1m.xlsx`
- `input_master_3m.xlsx`
- `input_master_6m.xlsx`

Each file has sample data and the correct column structure.

### 4. Run Your First Update

```bash
python update_swap_implied_data.py
```

This will:
1. Extract latest SOFR rates from global-rates.com
2. Extract latest USD/SGD forward points from investing.com
3. Extract current USD/SGD FX rate
4. Append today's data to all three master files

### 5. Verify Results

Open any of the master files and check the last row - it should have today's date and the extracted data.

## Usage Modes

### Normal Mode (Fast)
```bash
python update_swap_implied_data.py
```
Uses HTTP requests. Fast but may be blocked occasionally.

### Selenium Mode (Reliable)
```bash
python update_swap_implied_data.py --selenium
```
Uses browser automation. Slower but more reliable.

### Custom Directory
```bash
python update_swap_implied_data.py --input-dir /path/to/your/files
```
Use a different directory for your master files.

## Quick Reference - File Format

Each master file must have these exact columns:

**For input_master_1m.xlsx:**
```
Date       | 1mSOFR | USDSGD_FX | ForwardPoints
2025-02-01 | 4.50   | 1.3450    | -25.50
2025-02-02 | 4.51   | 1.3455    | -25.60
```

**For input_master_3m.xlsx:**
```
Date       | 3mSOFR | USDSGD_FX | ForwardPoints
2025-02-01 | 4.55   | 1.3450    | -77.50
```

**For input_master_6m.xlsx:**
```
Date       | 6mSOFR | USDSGD_FX | ForwardPoints
2025-02-01 | 4.60   | 1.3450    | -148.50
```

## Scheduling Daily Updates

### Windows

**Method 1: Double-click**
Just double-click `run_swap_updater.bat`

**Method 2: Task Scheduler**
1. Open Task Scheduler
2. Create Basic Task → Daily at 9:00 AM
3. Action: Start `run_swap_updater.bat`

### Linux/Mac

**Method 1: Run manually**
```bash
./run_swap_updater.sh
```

**Method 2: Cron (automatic)**
```bash
crontab -e
```
Add line:
```
0 9 * * 1-5 cd /path/to/script && ./run_swap_updater.sh
```

## Troubleshooting Quick Fixes

### Error: "Missing files"
**Fix:** Run with `--create-sample` first
```bash
python update_swap_implied_data.py --create-sample
```

### Error: "Could not extract..."
**Fix:** Use Selenium mode
```bash
python update_swap_implied_data.py --selenium
```

### Error: "Module not found"
**Fix:** Install missing package
```bash
pip install <package-name>
```

### Chrome/ChromeDriver issues
**Fix:** Install webdriver-manager
```bash
pip install webdriver-manager
```

## Expected Output

When successful, you'll see:

```
======================================================================
SWAP-IMPLIED RATE DATA UPDATER
======================================================================

✓ All master files found

EXTRACTING DATA FROM SOURCES
----------------------------------------------------------------------
✓ SOFR rates extracted: 1M=4.50%, 3M=4.55%, 6M=4.60%
✓ USD/SGD FX rate: 1.3450
✓ Forward points extracted: 1M=-27.47, 3M=-77.73, 6M=-148.97

UPDATING MASTER FILES
----------------------------------------------------------------------
✓ Successfully appended: Date=2025-02-06, SOFR=4.50%, FX=1.3450, FP=-27.47
✓ Successfully appended: Date=2025-02-06, SOFR=4.55%, FX=1.3450, FP=-77.73
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

## Next Steps

1. **Review the data** - Open the Excel files and verify
2. **Set up automation** - Schedule daily runs
3. **Monitor logs** - Check for any extraction failures
4. **Customize** - Modify the script for your specific needs

## Getting Help

- Read the full README: `README_swap_implied.md`
- Run tests: `python test_swap_updater.py`
- Check sample files: Open `../swap_implied_input/input_master_*.xlsx`

## Common Workflows

### Daily Production Use
```bash
# Morning routine (9:00 AM)
python update_swap_implied_data.py

# If it fails, retry with Selenium
python update_swap_implied_data.py --selenium
```

### First Time Setup
```bash
# 1. Install packages
pip install -r requirements_swap.txt

# 2. Test installation
python test_swap_updater.py

# 3. Create master files
python update_swap_implied_data.py --create-sample

# 4. Run first update
python update_swap_implied_data.py
```

### After a Website Change
```bash
# Try Selenium mode (more robust)
python update_swap_implied_data.py --selenium

# If still failing, website structure may have changed
# Check the source code and update parsing logic
```

---

**You're all set!** 🎉

Run `python update_swap_implied_data.py` daily to keep your data current.
