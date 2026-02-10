# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository calculates **USD/SGD FX swap implied SGD interest rates** using Covered Interest Rate Parity (CIP). It consists of three main components that work together in a data pipeline:

1. **extract_fwd_points/** - Extracts forward points from investing.com
2. **extract_all_rates/** - Aggregates SOFR rates, FX spot rates, and forward points into master files
3. **calc_swap_implied/** - Calculates implied SGD rates from the aggregated data

## Build & Run Commands

### Install dependencies
```bash
pip install pandas openpyxl requests beautifulsoup4 numpy selenium webdriver-manager
```

### Calculate implied rates (main calculation)
```bash
# Auto-detect tenor from column names
python calc_swap_implied/calculate_swap_implied_rates.py input.xlsx output.xlsx

# Specify tenor explicitly
python calc_swap_implied/calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M
```

### Update master data files (daily data collection)
```bash
# Fast mode using HTTP requests
python extract_all_rates/update_swap_implied_data.py

# Reliable mode using Selenium (when requests are blocked)
python extract_all_rates/update_swap_implied_data.py --selenium

# Create sample master files
python extract_all_rates/update_swap_implied_data.py --create-sample
```

### Extract forward points only
```bash
python extract_fwd_points/extract_forward_points_selenium.py
python extract_fwd_points/extract_forward_points_selenium.py --selenium  # More reliable
```

### Extract forward points via Browse.AI (screenshot capture)
```bash
# Run robot and download screenshots
python extract_fwd_points/browse_ai_extractor.py

# Save to custom directory
python extract_fwd_points/browse_ai_extractor.py --output-dir ./my_screenshots

# Start task without waiting
python extract_fwd_points/browse_ai_extractor.py --no-wait

# Check status of existing task
python extract_fwd_points/browse_ai_extractor.py --task-id <task_id>
```
Credentials stored in `Browse_AI` file (api key, workspace_id, robot_id).

### Run full pipeline (recommended daily workflow)
```bash
# Full pipeline: Browse AI table bot → auto-parse bid/ask → calculate → post to Roam
python run_pipeline.py

# Use old screenshot bot + manual input instead of table bot
python run_pipeline.py --browse-ai-screenshot

# Skip Browse AI, scrape forward points from investing.com instead
python run_pipeline.py --no-browse-ai

# Use Selenium for more reliable scraping
python run_pipeline.py --selenium

# Skip Roam Research posting
python run_pipeline.py --no-roam

# Only update input files, skip calculation
python run_pipeline.py --skip-calc
```

### Post latest rates to Roam Research
```bash
python post_to_roam.py
```
Credentials stored in `Roam_Research` file (ROAM_API_TOKEN, ROAM_GRAPH_NAME).

## Architecture

### Data Flow
```
Web Sources (SOFR, FX, Forward Points)
         ↓
extract_all_rates/update_swap_implied_data.py
         ↓
swap_implied_input/input_master_{1m,3m,6m}.xlsx
         ↓
calc_swap_implied/calculate_swap_implied_rates.py
         ↓
Output Excel with implied SGD rates
         ↓
post_to_roam.py → Roam Research daily notes
```

**`run_pipeline.py`** orchestrates the entire flow above in a single command.
By default it uses the Browse AI table bot to automatically parse forward points
bid/ask values. Use `--browse-ai-screenshot` for the old screenshot + manual input
flow, or `--no-browse-ai` to scrape from investing.com instead.

### Key Classes

**`HolidayCalendar`** (`calc_swap_implied/calculate_swap_implied_rates.py`):
- Manages US (NY SIFMA) and Singapore (MOM) holiday calendars
- Determines T+2 spot settlement dates where both markets are open

**`SwapImpliedRateCalculator`** (`calc_swap_implied/calculate_swap_implied_rates.py`):
- Implements CIP formula: `r_SGD = [(F/S) × (1 + r_USD × days/360) - 1] × (365/days)`
- Handles business day conventions for forward date calculation
- Supports 1M, 3M, 6M tenors

**`DataExtractor`** (`extract_all_rates/update_swap_implied_data.py`):
- Scrapes SOFR rates from global-rates.com
- Scrapes forward points from investing.com (calculates mid from bid/ask)
- Gets FX spot rate from exchangerate-api.com with fallbacks
- Supports both requests and Selenium modes

**`DataUpdater`** (`extract_all_rates/update_swap_implied_data.py`):
- Appends daily data to period-specific master Excel files
- Prevents duplicate entries for the same date

**`BrowseAIClient`** (`extract_fwd_points/browse_ai_extractor.py`):
- Forward points extraction via Browse.AI robots (table bot or screenshot bot)
- Table bot (default): returns structured bid/ask data via `capturedLists`, parsed by `parse_forward_points_from_table()`
- Screenshot bot (`--browse-ai-screenshot`): captures screenshots for manual reading
- Uses Browse.AI API v2 with credentials from `Browse_AI` file

### Day Count Conventions
- **USD (SOFR)**: ACT/360
- **SGD**: ACT/365

### Master File Format
Each `input_master_{tenor}.xlsx` must have columns: `Date`, `{x}mSOFR`, `USDSGD_FX`, `ForwardPoints`

### Output File Format
Each `output_master_{tenor}.xlsx` has columns: `Trade_Date`, `Spot_Date`, `Forward_Date`, `Actual_Days`, `USD_SOFR_{x}M_Pct`, `Spot_Rate`, `Forward_Points_pips`, `Forward_Rate`, `Implied_SGD_Rate_Pct`, `Rate_Diff_bps`

## Data Sources
- **Term SOFR**: global-rates.com (CME Term SOFR)
- **Forward Points**: investing.com (USD/SGD forward rates) or Browse.AI (table bot auto-parse / screenshot capture)
- **FX Spot**: exchangerate-api.com (free, no API key)
- **US Holidays**: NY SIFMA calendar
- **Singapore Holidays**: Ministry of Manpower (MOM)
