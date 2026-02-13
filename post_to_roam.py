#!/usr/bin/env python3
"""
Post latest swap-implied SGD rates to Roam Research daily notes.

Reads the latest row (by date) from output_master_{1m,3m,6m}.xlsx and
creates a block on the corresponding Roam Research daily note page.

Usage:
    python post_to_roam.py

Credentials:
    Reads ROAM_API_TOKEN and ROAM_GRAPH_NAME from the 'Roam_Research'
    file in the project root (one key=value per line), or from
    environment variables of the same name.
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(SCRIPT_DIR, "Roam_Research")
ROAM_API_BASE = "https://api.roamresearch.com"

TENORS = ["1m", "3m", "6m"]


def load_credentials():
    """Load Roam Research credentials from file or environment."""
    token = os.environ.get("ROAM_API_TOKEN")
    graph = os.environ.get("ROAM_GRAPH_NAME")

    if not (token and graph) and os.path.exists(CREDS_FILE):
        with open(CREDS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip("'\"")
                if key == "ROAM_API_TOKEN":
                    token = value
                elif key == "ROAM_GRAPH_NAME":
                    graph = value

    if not token or not graph:
        print("Error: Missing credentials.")
        print(f"Set ROAM_API_TOKEN and ROAM_GRAPH_NAME in '{CREDS_FILE}' or as environment variables.")
        sys.exit(1)

    return token, graph


def get_latest_rates():
    """Read the latest row from each output_master file.

    Returns (date, dict) where dict maps tenor to rate percentage.
    All files must share the same latest date.
    """
    rates = {}
    latest_date = None

    for tenor in TENORS:
        filepath = os.path.join(SCRIPT_DIR, f"output_master_{tenor}.xlsx")
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping {tenor.upper()}")
            continue

        df = pd.read_excel(filepath)
        date_col = "Trade_Date" if "Trade_Date" in df.columns else "Date"
        df[date_col] = pd.to_datetime(df[date_col])
        row = df.loc[df[date_col].idxmax()]

        row_date = row[date_col].date()
        rate = row["Implied_SGD_Rate_Pct"]
        rates[tenor] = rate

        if latest_date is None:
            latest_date = row_date
        elif row_date != latest_date:
            print(f"Warning: {tenor.upper()} latest date ({row_date}) differs from others ({latest_date}). Using {row_date}.")
            if row_date > latest_date:
                latest_date = row_date

    if not rates:
        print("Error: No output files found.")
        sys.exit(1)

    return latest_date, rates


def date_to_roam_title(d):
    """Convert a date to Roam daily note page title format.

    Example: date(2026, 2, 7) -> 'February 7th, 2026'
    """
    day = d.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{d.strftime('%B')} {day}{suffix}, {d.year}"


def date_to_roam_uid(d):
    """Convert a date to Roam daily note UID format.

    Example: date(2026, 2, 7) -> '02-07-2026'
    """
    return d.strftime("%m-%d-%Y")


def roam_write(token, graph, actions):
    """Execute write actions against the Roam Research API."""
    url = f"{ROAM_API_BASE}/api/graph/{graph}/write"
    headers = {
        "X-Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"action": "batch-actions", "actions": actions}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json() if resp.text else None


def roam_query(token, graph, query, args=None):
    """Execute a Datalog query against the Roam Research API."""
    url = f"{ROAM_API_BASE}/api/graph/{graph}/q"
    headers = {
        "X-Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if args:
        payload["args"] = args
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_page_uid(token, graph, page_title):
    """Query for the UID of a page by title. Returns None if not found."""
    query = '[:find ?uid :in $ ?title :where [?e :node/title ?title] [?e :block/uid ?uid]]'
    response = roam_query(token, graph, query, args=[page_title])
    # Response format: {"result": [["uid-value"]]} or just [["uid-value"]]
    result = response.get("result", response) if isinstance(response, dict) else response
    if result and len(result) > 0:
        row = result[0]
        return row[0] if isinstance(row, list) else row
    return None


def ensure_daily_note(token, graph, page_title, page_uid):
    """Create the daily note page if it doesn't already exist.

    Returns the actual UID of the page (which may differ from page_uid
    if the page was previously created with a different UID).
    """
    # Check if page exists and get its actual UID
    actual_uid = get_page_uid(token, graph, page_title)

    if actual_uid:
        print(f"Daily note page already exists: {page_title} (uid: {actual_uid})")
        return actual_uid

    # Page doesn't exist — create it
    actions = [{"action": "create-page", "page": {"title": page_title, "uid": page_uid}}]
    try:
        roam_write(token, graph, actions)
        print(f"Created daily note page: {page_title}")
        return page_uid
    except requests.HTTPError:
        # Page may have been created concurrently — query for its UID
        actual_uid = get_page_uid(token, graph, page_title)
        if actual_uid:
            print(f"Page already exists (created concurrently): {page_title} (uid: {actual_uid})")
            return actual_uid
        # If we still can't find it, fall back to the expected UID
        print(f"Warning: create-page failed but page not found. Using expected uid: {page_uid}")
        return page_uid


def post_rates_to_roam(token, graph, page_uid, rates):
    """Post swap-implied rates as a block on the daily note page."""
    parts = ["Swap-Implied SGD Rates -"]
    for tenor in TENORS:
        if tenor in rates:
            parts.append(f"{tenor.upper()}: {rates[tenor]:.4f}%")

    block_string = " | ".join(parts)

    actions = [
        {
            "action": "create-block",
            "location": {"parent-uid": page_uid, "order": "last"},
            "block": {"string": block_string},
        }
    ]

    roam_write(token, graph, actions)


def main():
    token, graph = load_credentials()
    latest_date, rates = get_latest_rates()

    page_title = date_to_roam_title(latest_date)
    page_uid = date_to_roam_uid(latest_date)

    print(f"Latest date: {latest_date}")
    print(f"Roam page: {page_title} (uid: {page_uid})")
    for tenor in TENORS:
        if tenor in rates:
            print(f"  {tenor.upper()}: {rates[tenor]:.4f}%")

    actual_uid = ensure_daily_note(token, graph, page_title, page_uid)
    post_rates_to_roam(token, graph, actual_uid, rates)

    print(f"\nSuccessfully posted rates to Roam daily note: {page_title}")


if __name__ == "__main__":
    main()
