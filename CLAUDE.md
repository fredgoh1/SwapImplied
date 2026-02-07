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
```

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
- Alternative forward points extraction via Browse.AI robot
- Triggers robot tasks and downloads captured screenshots
- Uses Browse.AI API v2 with credentials from `Browse_AI` file

### Day Count Conventions
- **USD (SOFR)**: ACT/360
- **SGD**: ACT/365

### Master File Format
Each `input_master_{tenor}.xlsx` must have columns: `Date`, `{x}mSOFR`, `USDSGD_FX`, `ForwardPoints`

## Data Sources
- **Term SOFR**: global-rates.com (CME Term SOFR)
- **Forward Points**: investing.com (USD/SGD forward rates) or Browse.AI screenshot capture
- **FX Spot**: exchangerate-api.com (free, no API key)
- **US Holidays**: NY SIFMA calendar
- **Singapore Holidays**: Ministry of Manpower (MOM)
