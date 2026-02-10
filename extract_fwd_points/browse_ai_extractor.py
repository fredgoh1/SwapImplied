#!/usr/bin/env python3
"""
Browse.AI Forward Points Screenshot Extractor

Triggers a Browse.AI robot to capture forward points data.
Supports both table extraction (default) and screenshot capture modes.

Usage:
    python browse_ai_extractor.py                    # Run and download screenshots
    python browse_ai_extractor.py --output-dir ./screenshots
    python browse_ai_extractor.py --task-id <id>     # Check existing task status
"""

import argparse
import requests
import time
import os
from datetime import datetime
from pathlib import Path


class BrowseAIClient:
    """Client for interacting with Browse.AI API v2"""

    BASE_URL = "https://api.browse.ai/v2"

    def __init__(self, api_key, robot_id):
        """
        Initialize the Browse.AI client.

        Args:
            api_key: Browse.AI API key (format: key_id:key_secret)
            robot_id: ID of the robot to run
        """
        self.api_key = api_key
        self.robot_id = robot_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def run_task(self, input_parameters=None):
        """
        Trigger a robot task execution.

        Args:
            input_parameters: Optional dict of input parameters for the robot

        Returns:
            dict: Task response containing task_id and status
        """
        url = f"{self.BASE_URL}/robots/{self.robot_id}/tasks"

        payload = {}
        if input_parameters:
            payload["inputParameters"] = input_parameters

        print(f"Triggering robot task...")
        print(f"  Robot ID: {self.robot_id}")

        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("statusCode") == 200:
            result = data.get("result", {})
            task_id = result.get("id")
            status = result.get("status")
            print(f"  Task created successfully!")
            print(f"  Task ID: {task_id}")
            print(f"  Status: {status}")
            return result
        else:
            raise Exception(f"Failed to create task: {data}")

    def get_task_status(self, task_id):
        """
        Get the status and results of a task.

        Args:
            task_id: ID of the task to check

        Returns:
            dict: Task details including status and captured data
        """
        url = f"{self.BASE_URL}/robots/{self.robot_id}/tasks/{task_id}"

        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("statusCode") == 200:
            return data.get("result", {})
        else:
            raise Exception(f"Failed to get task status: {data}")

    def wait_for_completion(self, task_id, poll_interval=5, max_wait=300):
        """
        Wait for a task to complete.

        Args:
            task_id: ID of the task to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            dict: Completed task details
        """
        print(f"\nWaiting for task to complete...")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Task did not complete within {max_wait} seconds")

            task = self.get_task_status(task_id)
            status = task.get("status")

            print(f"  [{int(elapsed)}s] Status: {status}")

            if status == "successful":
                print(f"\n  Task completed successfully!")
                return task
            elif status == "failed":
                error = task.get("userFriendlyError", "Unknown error")
                video_url = task.get("videoUrl", "")
                raise Exception(f"Task failed: {error}\nDebug video: {video_url}")

            time.sleep(poll_interval)

    def get_robot_info(self):
        """Get information about the robot."""
        url = f"{self.BASE_URL}/robots/{self.robot_id}"

        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        if data.get("statusCode") == 200:
            return data.get("robot", {})
        return None


def download_screenshot(url, output_path):
    """
    Download a screenshot from a URL.

    Args:
        url: URL of the screenshot
        output_path: Path to save the screenshot
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with open(output_path, 'wb') as f:
        f.write(response.content)

    print(f"    Saved: {output_path}")


def parse_forward_points_from_table(task):
    """
    Parse forward points bid/ask from Browse AI table bot capturedLists data.

    Args:
        task: Completed task dict from Browse AI API

    Returns:
        dict: {'1M': mid, '3M': mid, '6M': mid} or empty dict on failure
    """
    captured_lists = task.get("capturedLists", {})

    # capturedLists is a dict of list_name -> list of row dicts
    rows = []
    for list_name, list_rows in captured_lists.items():
        if isinstance(list_rows, list):
            rows.extend(list_rows)

    if not rows:
        print("  No table data found in capturedLists.")
        return {}

    # Match both "USDSGD 1M FWD" style and "USD/SGD - 1 Month" style names
    tenor_patterns = {
        "1M": ["1M", "1 Month"],
        "3M": ["3M", "3 Months"],
        "6M": ["6M", "6 Months"],
    }
    results = {}

    for row in rows:
        # Column is "Pair Name" (not "Name"); normalize non-breaking spaces
        name = row.get("Pair Name", row.get("Name", "")).replace("\xa0", " ")
        for tenor, patterns in tenor_patterns.items():
            if any(p in name for p in patterns):
                try:
                    bid = float(row.get("Bid", "").replace(",", ""))
                    ask = float(row.get("Ask", "").replace(",", ""))
                    mid = (bid + ask) / 2.0
                    results[tenor] = {"bid": bid, "ask": ask, "mid": mid}
                except (ValueError, TypeError) as e:
                    print(f"  Warning: Could not parse bid/ask for {tenor}: {e}")
                break

    return results


def load_credentials(credentials_file):
    """
    Load Browse.AI credentials from file.

    Args:
        credentials_file: Path to credentials file

    Returns:
        tuple: (api_key, workspace_id, robot_id, screenshot_robot_id)
    """
    credentials = {}

    with open(credentials_file, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                credentials[key] = value

    api_key = credentials.get('browse_ai_api')
    workspace_id = credentials.get('workspace_id')
    robot_id = credentials.get('robot_id')
    screenshot_robot_id = credentials.get('screenshot_robot_id')

    if not api_key or not robot_id:
        raise ValueError("Missing required credentials (browse_ai_api and robot_id)")

    return api_key, workspace_id, robot_id, screenshot_robot_id


def main():
    parser = argparse.ArgumentParser(
        description='Extract forward points screenshots using Browse.AI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--credentials',
        default='../Browse_AI',
        help='Path to credentials file (default: ../Browse_AI)'
    )
    parser.add_argument(
        '--output-dir',
        default='./screenshots',
        help='Directory to save screenshots (default: ./screenshots)'
    )
    parser.add_argument(
        '--task-id',
        help='Check status of existing task instead of running new one'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Start task but do not wait for completion'
    )
    parser.add_argument(
        '--max-wait',
        type=int,
        default=300,
        help='Maximum seconds to wait for task completion (default: 300)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Seconds between status checks (default: 5)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("BROWSE.AI FORWARD POINTS SCREENSHOT EXTRACTOR")
    print("=" * 70)
    print()

    # Load credentials
    credentials_path = Path(args.credentials)
    if not credentials_path.is_absolute():
        credentials_path = Path(__file__).parent / credentials_path

    print(f"Loading credentials from: {credentials_path}")
    api_key, workspace_id, robot_id, screenshot_robot_id = load_credentials(credentials_path)
    print(f"  Workspace ID: {workspace_id}")
    print(f"  Robot ID: {robot_id}")
    if screenshot_robot_id:
        print(f"  Screenshot Robot ID: {screenshot_robot_id}")
    print()

    # Initialize client
    client = BrowseAIClient(api_key, robot_id)

    # Get robot info
    print("Fetching robot information...")
    robot_info = client.get_robot_info()
    if robot_info:
        print(f"  Robot Name: {robot_info.get('name', 'Unknown')}")
        print()

    # Run or check task
    if args.task_id:
        # Check existing task
        print(f"Checking existing task: {args.task_id}")
        task = client.get_task_status(args.task_id)
    else:
        # Run new task
        print("-" * 70)
        task_result = client.run_task()
        task_id = task_result.get("id")

        if args.no_wait:
            print(f"\nTask started. Check status later with:")
            print(f"  python browse_ai_extractor.py --task-id {task_id}")
            return 0

        # Wait for completion
        print("-" * 70)
        task = client.wait_for_completion(
            task_id,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait
        )

    # Process results
    print()
    print("-" * 70)
    print("TASK RESULTS")
    print("-" * 70)

    # Display captured texts (forward points data)
    captured_texts = task.get("capturedTexts", {})
    if captured_texts:
        print("\nCaptured Data:")
        for field_name, value in captured_texts.items():
            print(f"  {field_name}: {value}")

    # Download screenshots
    captured_screenshots = task.get("capturedScreenshots", {})
    if captured_screenshots:
        print(f"\nCaptured Screenshots: {len(captured_screenshots)}")

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Handle both dict format (name -> screenshot_data) and list format
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
                # Create filename with timestamp
                safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
                filename = f"{timestamp}_{safe_name}.png"
                output_path = output_dir / filename

                print(f"  Downloading: {name}")
                try:
                    download_screenshot(url, output_path)
                except Exception as e:
                    print(f"    Error: {e}")

                # Also download diff image if available
                diff_url = screenshot.get("diffImageSrc")
                if diff_url:
                    diff_filename = f"{timestamp}_{safe_name}_diff.png"
                    diff_path = output_dir / diff_filename
                    print(f"  Downloading diff: {name}")
                    try:
                        download_screenshot(diff_url, diff_path)
                    except Exception as e:
                        print(f"    Error downloading diff: {e}")
    else:
        print("\nNo screenshots captured.")

    # Display video URL if available
    video_url = task.get("videoUrl")
    if video_url:
        print(f"\nDebug Video: {video_url}")

    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
