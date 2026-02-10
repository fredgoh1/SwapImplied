#!/usr/bin/env python3
"""
End-to-end pipeline for USD/SGD FX swap implied SGD interest rates.

Steps:
    1. Extract SOFR rates & FX spot rate
    2. Run Browse AI table bot to extract forward points (auto-parse bid/ask)
    3. User confirms parsed values (or enters manually if rejected/failed)
    4. Update master input files
    5. Calculate implied rates for each tenor
    6. Post latest rates to Roam Research

Usage:
    python run_pipeline.py                         # Full pipeline (table bot, auto-parse)
    python run_pipeline.py --browse-ai-screenshot  # Old screenshot bot + manual input
    python run_pipeline.py --no-browse-ai          # Scrape forward points instead
    python run_pipeline.py --no-roam               # Skip Roam posting
    python run_pipeline.py --no-browse-ai --no-roam
    python run_pipeline.py --skip-calc             # Only update input files
    python run_pipeline.py --selenium              # Use Selenium for scraping
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

# Add project root to path so we can import from sibling packages
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "extract_all_rates"))
sys.path.insert(0, str(PROJECT_ROOT / "extract_fwd_points"))
sys.path.insert(0, str(PROJECT_ROOT / "calc_swap_implied"))

from extract_all_rates.update_swap_implied_data import (
    DataExtractor,
    DataUpdater,
    manual_forward_points_input,
)
from extract_fwd_points.browse_ai_extractor import (
    BrowseAIClient,
    load_credentials as load_browse_ai_credentials,
    download_screenshot,
    parse_forward_points_from_table,
)
from calc_swap_implied.calculate_swap_implied_rates import process_excel_file
from post_to_roam import (
    load_credentials as load_roam_credentials,
    get_latest_rates,
    date_to_roam_title,
    date_to_roam_uid,
    ensure_daily_note,
    post_rates_to_roam,
)


TENORS = ["1M", "3M", "6M"]
INPUT_DIR = PROJECT_ROOT / "swap_implied_input"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"


def step_extract_sofr_and_fx(use_selenium=False):
    """Step 1: Extract SOFR rates and FX spot rate."""
    print()
    print("=" * 70)
    print("STEP 1: EXTRACT SOFR RATES & FX SPOT")
    print("=" * 70)

    extractor = DataExtractor(use_selenium=use_selenium)
    sofr_rates = extractor.extract_sofr_rates()
    fx_rate = extractor.extract_usdsgd_fx()

    if not sofr_rates:
        print("\nFailed to extract SOFR rates.")
        return None, None
    if not fx_rate:
        print("\nFailed to extract FX rate.")
        return None, None

    return sofr_rates, fx_rate


def step_browse_ai_table():
    """Step 2: Run Browse AI table bot and parse forward points automatically."""
    print()
    print("=" * 70)
    print("STEP 2: RUN BROWSE AI TABLE BOT")
    print("=" * 70)

    credentials_path = PROJECT_ROOT / "Browse_AI"
    if not credentials_path.exists():
        print(f"Browse AI credentials file not found: {credentials_path}")
        return None

    api_key, workspace_id, robot_id, _ = load_browse_ai_credentials(str(credentials_path))
    client = BrowseAIClient(api_key, robot_id)

    # Fetch robot info
    robot_info = client.get_robot_info()
    if robot_info:
        print(f"  Robot Name: {robot_info.get('name', 'Unknown')}")

    # Run task with required input parameters
    task_result = client.run_task(input_parameters={
        "originUrl": "https://www.investing.com/currencies/usd-sgd-forward-rates",
        "usd_sgd_forward_rates_limit": 12,
    })
    task_id = task_result.get("id")

    # Wait for completion (10 min timeout — table extraction can be slow)
    task = client.wait_for_completion(task_id, max_wait=600)

    # Parse table data
    parsed = parse_forward_points_from_table(task)
    if not parsed:
        print("\nNo forward points found in table data.")
        return None

    # Display parsed values
    print()
    print("  Parsed forward points from Browse AI table:")
    print(f"  {'Tenor':<8} {'Bid':>10} {'Ask':>10} {'Mid':>10}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
    for tenor in ["1M", "3M", "6M"]:
        if tenor in parsed:
            d = parsed[tenor]
            print(f"  {tenor:<8} {d['bid']:>10.2f} {d['ask']:>10.2f} {d['mid']:>10.2f}")

    return parsed


def step_browse_ai_screenshot():
    """Step 2: Run Browse AI screenshot robot and download screenshots."""
    print()
    print("=" * 70)
    print("STEP 2: RUN BROWSE AI SCREENSHOT ROBOT")
    print("=" * 70)

    credentials_path = PROJECT_ROOT / "Browse_AI"
    if not credentials_path.exists():
        print(f"Browse AI credentials file not found: {credentials_path}")
        return False

    api_key, workspace_id, robot_id, screenshot_robot_id = load_browse_ai_credentials(
        str(credentials_path)
    )
    if not screenshot_robot_id:
        print("No screenshot_robot_id found in credentials.")
        return False

    client = BrowseAIClient(api_key, screenshot_robot_id)

    # Fetch robot info
    robot_info = client.get_robot_info()
    if robot_info:
        print(f"  Robot Name: {robot_info.get('name', 'Unknown')}")

    # Run task
    task_result = client.run_task()
    task_id = task_result.get("id")

    # Wait for completion
    task = client.wait_for_completion(task_id)

    # Download screenshots
    captured_screenshots = task.get("capturedScreenshots", {})
    if captured_screenshots:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if isinstance(captured_screenshots, dict):
            screenshots_list = [
                {"name": name, **data}
                for name, data in captured_screenshots.items()
            ]
        else:
            screenshots_list = captured_screenshots

        for screenshot in screenshots_list:
            name = screenshot.get("name", "screenshot")
            url = screenshot.get("src") or screenshot.get("url")
            if url:
                safe_name = "".join(
                    c if c.isalnum() or c in "._-" else "_" for c in name
                )
                filename = f"{timestamp}_{safe_name}.png"
                output_path = SCREENSHOTS_DIR / filename
                print(f"  Downloading: {name}")
                try:
                    download_screenshot(url, output_path)
                except Exception as e:
                    print(f"    Error: {e}")

        print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")

        # Open screenshots in Preview.app so user can read bid/ask values
        saved_files = list(SCREENSHOTS_DIR.glob(f"{timestamp}_*.png"))
        if saved_files:
            print("Opening screenshots in Preview...")
            subprocess.run(["open"] + [str(f) for f in saved_files])
    else:
        print("\nNo screenshots captured.")

    return True


def step_forward_points(use_browse_ai=True, use_browse_ai_screenshot=False,
                        use_selenium=False):
    """Step 2+3: Get forward points (Browse AI table, screenshot, or scrape)."""
    if use_browse_ai and not use_browse_ai_screenshot:
        # Default: table bot with automatic parsing
        parsed = step_browse_ai_table()

        if parsed:
            # Ask user for confirmation
            print()
            confirm = input("  Accept these values? [Y/n]: ").strip().lower()
            if confirm in ("", "y", "yes"):
                # Use mid values as forward points
                forward_points = {}
                for tenor in ["1M", "3M", "6M"]:
                    if tenor in parsed:
                        forward_points[tenor] = parsed[tenor]["mid"]
                print("  Using parsed forward points.")
                return forward_points
            else:
                print("  Rejected. Falling back to manual input.")

        # Fall back to manual input
        print()
        print("=" * 70)
        print("STEP 3: ENTER FORWARD POINTS MANUALLY")
        print("=" * 70)
        forward_points = manual_forward_points_input()

    elif use_browse_ai_screenshot:
        # Old screenshot flow
        success = step_browse_ai_screenshot()
        if not success:
            print("\nBrowse AI screenshot failed. Falling back to manual input.")

        # Prompt user for bid/ask from screenshots
        print()
        print("=" * 70)
        print("STEP 3: ENTER FORWARD POINTS FROM SCREENSHOTS")
        print("=" * 70)
        forward_points = manual_forward_points_input()

    else:
        # Scrape from investing.com
        print()
        print("=" * 70)
        print("STEP 2-3: SCRAPE FORWARD POINTS")
        print("=" * 70)
        extractor = DataExtractor(use_selenium=use_selenium)
        forward_points = extractor.extract_forward_points()

        if not forward_points:
            print("\nAutomated extraction failed. Falling back to manual input.")
            forward_points = manual_forward_points_input()

    return forward_points


def step_update_master_files(sofr_rates, fx_rate, forward_points):
    """Step 4: Update master input files."""
    print()
    print("=" * 70)
    print("STEP 4: UPDATE MASTER INPUT FILES")
    print("=" * 70)

    updater = DataUpdater(input_dir=str(INPUT_DIR))

    if not updater.validate_files():
        print("\nMaster files not found. Run with --create-sample first:")
        print("  python extract_all_rates/update_swap_implied_data.py --create-sample")
        return False

    results = updater.update_files(sofr_rates, fx_rate, forward_points)

    success_count = sum(1 for r in results.values() if r == "success")
    skipped_count = sum(1 for r in results.values() if r == "skipped")
    print(f"\nUpdated: {success_count}/3 | Skipped: {skipped_count}/3")

    return success_count > 0 or skipped_count > 0


def step_calculate_implied_rates():
    """Step 5: Calculate implied rates for each tenor."""
    print()
    print("=" * 70)
    print("STEP 5: CALCULATE IMPLIED RATES")
    print("=" * 70)

    for tenor in TENORS:
        input_file = INPUT_DIR / f"input_master_{tenor.lower()}.xlsx"
        output_file = PROJECT_ROOT / f"output_master_{tenor.lower()}.xlsx"

        if not input_file.exists():
            print(f"\nSkipping {tenor}: {input_file} not found")
            continue

        print(f"\nProcessing {tenor}...")
        try:
            process_excel_file(
                str(input_file), str(output_file), tenor=tenor, verbose=False
            )
            print(f"  Output: {output_file}")
        except Exception as e:
            print(f"  Error processing {tenor}: {e}")


def step_post_to_roam():
    """Step 6: Post latest rates to Roam Research."""
    print()
    print("=" * 70)
    print("STEP 6: POST TO ROAM RESEARCH")
    print("=" * 70)

    try:
        token, graph = load_roam_credentials()
    except SystemExit:
        print("Roam credentials not found. Skipping.")
        return

    latest_date, rates = get_latest_rates()

    page_title = date_to_roam_title(latest_date)
    page_uid = date_to_roam_uid(latest_date)

    print(f"Latest date: {latest_date}")
    print(f"Roam page: {page_title} (uid: {page_uid})")
    for tenor in ["1m", "3m", "6m"]:
        if tenor in rates:
            print(f"  {tenor.upper()}: {rates[tenor]:.4f}%")

    ensure_daily_note(token, graph, page_title, page_uid)
    post_rates_to_roam(token, graph, page_uid, rates)

    print(f"\nSuccessfully posted rates to Roam daily note: {page_title}")


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end pipeline for USD/SGD swap implied SGD rates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                          # Full pipeline (Browse AI table bot)
  python run_pipeline.py --browse-ai-screenshot   # Use old screenshot bot + manual input
  python run_pipeline.py --no-browse-ai           # Scrape forward points
  python run_pipeline.py --no-roam                # Skip Roam posting
  python run_pipeline.py --no-browse-ai --no-roam # Scrape, no Roam
  python run_pipeline.py --skip-calc              # Only update input files
  python run_pipeline.py --selenium               # Use Selenium for scraping
        """,
    )
    parser.add_argument(
        "--no-browse-ai",
        action="store_true",
        help="Skip Browse AI; scrape forward points from investing.com instead",
    )
    parser.add_argument(
        "--browse-ai-screenshot",
        action="store_true",
        help="Use Browse AI screenshot bot + manual input (old workflow)",
    )
    parser.add_argument(
        "--selenium",
        action="store_true",
        help="Use Selenium mode for web scraping (more reliable but slower)",
    )
    parser.add_argument(
        "--no-roam",
        action="store_true",
        help="Skip posting to Roam Research",
    )
    parser.add_argument(
        "--skip-calc",
        action="store_true",
        help="Skip calculation step (only update input files)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("USD/SGD SWAP IMPLIED RATE PIPELINE")
    print("=" * 70)
    if args.no_browse_ai:
        browse_mode = "OFF (scraping)"
    elif args.browse_ai_screenshot:
        browse_mode = "SCREENSHOT (manual input)"
    else:
        browse_mode = "TABLE (auto-parse)"
    print(f"  Browse AI:  {browse_mode}")
    print(f"  Selenium:   {'ON' if args.selenium else 'OFF'}")
    print(f"  Calculate:  {'OFF' if args.skip_calc else 'ON'}")
    print(f"  Post Roam:  {'OFF' if args.no_roam else 'ON'}")

    # Step 1: Extract SOFR & FX
    sofr_rates, fx_rate = step_extract_sofr_and_fx(use_selenium=args.selenium)
    if not sofr_rates or not fx_rate:
        print("\nPipeline aborted: failed to extract SOFR rates or FX rate.")
        return 1

    # Step 2+3: Forward points
    use_browse_ai = not args.no_browse_ai
    forward_points = step_forward_points(
        use_browse_ai=use_browse_ai,
        use_browse_ai_screenshot=args.browse_ai_screenshot,
        use_selenium=args.selenium,
    )
    if not forward_points:
        print("\nPipeline aborted: failed to get forward points.")
        return 1

    # Step 4: Update master files
    ok = step_update_master_files(sofr_rates, fx_rate, forward_points)
    if not ok:
        print("\nPipeline aborted: failed to update master files.")
        return 1

    # Step 5: Calculate implied rates
    if not args.skip_calc:
        step_calculate_implied_rates()

    # Step 6: Post to Roam
    if not args.no_roam:
        step_post_to_roam()

    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
