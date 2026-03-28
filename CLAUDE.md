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
pip install pandas openpyxl requests beautifulsoup4 numpy selenium webdriver-manager yfinance matplotlib
```

### Calculate implied rates (main calculation)
```bash
# Auto-detect tenor from column names
python3 calc_swap_implied/calculate_swap_implied_rates.py input.xlsx output.xlsx

# Specify tenor explicitly
python3 calc_swap_implied/calculate_swap_implied_rates.py input.xlsx output.xlsx --tenor 3M
```

### Update master data files (daily data collection)
```bash
# Fast mode using HTTP requests
python3 extract_all_rates/update_swap_implied_data.py

# Reliable mode using Selenium (when requests are blocked)
python3 extract_all_rates/update_swap_implied_data.py --selenium

# Create sample master files
python3 extract_all_rates/update_swap_implied_data.py --create-sample
```

### Extract forward points only
```bash
python3 extract_fwd_points/extract_forward_points_selenium.py
python3 extract_fwd_points/extract_forward_points_selenium.py --selenium  # More reliable
```

### Extract forward points via Browse.AI (screenshot capture)
```bash
# Run robot and download screenshots
python3 extract_fwd_points/browse_ai_extractor.py

# Save to custom directory
python3 extract_fwd_points/browse_ai_extractor.py --output-dir ./my_screenshots

# Start task without waiting
python3 extract_fwd_points/browse_ai_extractor.py --no-wait

# Check status of existing task
python3 extract_fwd_points/browse_ai_extractor.py --task-id <task_id>
```
Credentials stored in `Browse_AI` file (api key, workspace_id, robot_id).

### Run full pipeline (recommended daily workflow)
```bash
# Full pipeline: Browse AI table bot → auto-parse bid/ask → calculate → post to Roam
python3 run_pipeline.py

# Use old screenshot bot + manual input instead of table bot
python3 run_pipeline.py --browse-ai-screenshot

# Skip Browse AI, scrape forward points from investing.com instead
python3 run_pipeline.py --no-browse-ai

# Use Selenium for more reliable scraping
python3 run_pipeline.py --selenium

# Skip Roam Research posting
python3 run_pipeline.py --no-roam

# Only update input files, skip calculation
python3 run_pipeline.py --skip-calc

# Recovery: read forward points from Notion table (after Browse AI failure)
python3 run_pipeline.py --notion-fallback
```

#### Browse AI failure flow
If Browse AI fails to parse forward points, the pipeline automatically:
1. Creates a row in the Notion database with today's date (bid/ask fields blank)
2. Sends a failure alert email
3. Aborts with instructions

Recovery: fill in the 6 bid/ask fields in Notion, then rerun with `--notion-fallback`.

Credentials stored in `Notion` file (NOTION_API_TOKEN, NOTION_DATABASE_ID, EMAIL_FROM, EMAIL_TO, EMAIL_APP_PASSWORD).

### Post latest rates to Roam Research
```bash
python3 post_to_roam.py
```
Credentials stored in `Roam_Research` file (ROAM_API_TOKEN, ROAM_GRAPH_NAME).

Roam block format (single block, soft line breaks):
```
> [!Summary]+ **Swap Implied SGD Rates**  - | 1M: X.XXXX% | 3M: X.XXXX% | 6M: X.XXXX%
SOFR |1m: X.XXXX% | 3m: X.XXXX% |6m: X.XXXX%
Hedging Costs|1m: XX.XX | 3m: XX.XX | 6m: XX.XX
```

### Retrofit output_master files with Hedging_Cost_bps (one-time / idempotent)
```bash
python3 add_hedging_cost.py
```
Adds `Hedging_Cost_bps` column immediately after `Rate_Diff_bps` in each `output_master_*m.xlsx`. Safe to re-run.

### Build historical dataset (one-time backfill)
```bash
python3 build_historical_dataset.py
```
Reads Barchart SOFR CSVs + `FWD_Points_Actual_Historical.xlsx`, fetches USDSGD spot via
yfinance, runs the full CIP calculation, and writes `output_historical_1m/3m/6m.xlsx`
covering Jan 2025 – Feb 2026.

Required source files (placed at project root):
- `sofermm1rt_daily_historical-data-03-24-2026.csv` — 1M CME Term SOFR (Barchart)
- `sofermm3rt_daily_historical-data-03-24-2026.csv` — 3M CME Term SOFR (Barchart)
- `sofermm6rt_daily_historical-data-03-24-2026.csv` — 6M CME Term SOFR (Barchart)
- `FWD_Points_Actual_Historical.xlsx` — USDSGD forward points 1M/3M/6M (columns: Date, 1-Month, 3-Month, 6-Month)

### Moving average breakout analysis and charts
```bash
python3 plot_ma_analysis.py
```
Merges `output_historical_*.xlsx` + `output_master_*.xlsx` into `output_combined_*.xlsx`,
computes a 60-day MA on `Implied_SGD_Rate_Pct`, and produces 8 PNG charts:

| File | Description |
|------|-------------|
| `swap_implied_ma_analysis_recent.png` | 3-panel combined, Oct 2025 – present |
| `swap_implied_ma_1m_recent.png` | 1M only, Oct 2025 – present |
| `swap_implied_ma_3m_recent.png` | 3M only, Oct 2025 – present |
| `swap_implied_ma_6m_recent.png` | 6M only, Oct 2025 – present |
| `swap_implied_ma_analysis_full.png` | 3-panel combined, full history |
| `swap_implied_ma_1m_full.png` | 1M only, full history |
| `swap_implied_ma_3m_full.png` | 3M only, full history |
| `swap_implied_ma_6m_full.png` | 6M only, full history |

Also prints a console breakout summary (latest rate vs MA60).

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
bid/ask values (no confirmation prompt — values are auto-accepted). On failure it
writes today's date to Notion and sends an email alert. Use `--notion-fallback` to
recover by reading manually-entered values from Notion. Use `--browse-ai-screenshot`
for the old screenshot + manual input flow, or `--no-browse-ai` to scrape from
investing.com instead.

### Key Classes

**`HolidayCalendar`** (`calc_swap_implied/calculate_swap_implied_rates.py`):
- Manages US (NY SIFMA) and Singapore (MOM) holiday calendars
- Determines T+2 spot settlement dates where both markets are open
- Supports multiple years: `HolidayCalendar(years=[2025, 2026])` — holidays hardcoded for 2025 and 2026
- Backward-compatible: `HolidayCalendar()` defaults to 2026; `HolidayCalendar(year=2025)` also works

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

**`notion_fallback`** (`extract_fwd_points/notion_fallback.py`):
- `write_failure_code_to_notion()`: creates a Notion row with today's date when Browse AI fails
- `read_forward_points_from_notion()`: reads bid/ask values entered manually and returns mid dict
- `send_failure_email()`: sends Gmail SMTP alert with recovery instructions
- Credentials from `Notion` file

### Day Count Conventions
- **USD (SOFR)**: ACT/360
- **SGD**: ACT/365

### Master File Format
Each `input_master_{tenor}.xlsx` must have columns: `Date`, `{x}mSOFR`, `USDSGD_FX`, `ForwardPoints`

### Output File Format
Each `output_master_{tenor}.xlsx` has columns: `Trade_Date`, `Spot_Date`, `Forward_Date`, `Actual_Days`, `USD_SOFR_{x}M_Pct`, `Spot_Rate`, `Forward_Points_pips`, `Forward_Rate`, `Implied_SGD_Rate_Pct`, `Rate_Diff_bps`, `Hedging_Cost_bps`

| Column | Formula | Purpose |
|---|---|---|
| `Rate_Diff_bps` | `(SGD_implied − SOFR_ACT360) × 100` | Legacy / backward compatibility |
| `Hedging_Cost_bps` | `(SGD_implied − SOFR×365/360) × 100` | Correct p.a. hedging cost (consistent ACT/365 day count) |

## Data Sources
- **Term SOFR (daily)**: global-rates.com (CME Term SOFR) — scraped by daily pipeline
- **Term SOFR (historical)**: Barchart.com tickers `SOFERMM1.RT`, `SOFERMM3.RT`, `SOFERMM6.RT` — manual CSV download
- **Forward Points (daily)**: investing.com or Browse.AI (table bot auto-parse / screenshot capture)
- **Forward Points (historical)**: `FWD_Points_Actual_Historical.xlsx` — manually sourced from Bloomberg/ABS
- **FX Spot (daily)**: exchangerate-api.com (free, no API key)
- **FX Spot (historical)**: Yahoo Finance via yfinance (ticker `USDSGD=X`)
- **US Holidays**: NY SIFMA calendar (hardcoded for 2025–2026)
- **Singapore Holidays**: Ministry of Manpower (MOM) (hardcoded for 2025–2026)

## Historical Data Files (project root)
| File | Contents | Date range |
|------|----------|------------|
| `sofermm1rt_daily_historical-data-03-24-2026.csv` | 1M CME Term SOFR fixings | 2019–2026-03-23 |
| `sofermm3rt_daily_historical-data-03-24-2026.csv` | 3M CME Term SOFR fixings | 2019–2026-03-23 |
| `sofermm6rt_daily_historical-data-03-24-2026.csv` | 6M CME Term SOFR fixings | 2019–2026-03-23 |
| `FWD_Points_Actual_Historical.xlsx` | USDSGD 1M/3M/6M forward points (pips) | 2025-01-01–2026-02-27 |
| `output_historical_1m/3m/6m.xlsx` | Calculated implied SGD rates (historical) | 2025-01-02–2026-02-27 |
| `output_combined_1m/3m/6m.xlsx` | Historical + master merged, deduplicated | 2025-01-02–present |
