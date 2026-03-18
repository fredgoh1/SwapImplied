"""
Notion fallback for forward points when Browse AI fails.

Functions:
  load_credentials        — read Notion/email creds from credentials file
  write_failure_code_to_notion — create a row with today's date (blank bid/ask)
  read_forward_points_from_notion — read bid/ask row and return mid dict
  send_failure_email      — send Gmail alert with instructions
"""

import json
import smtplib
import ssl
from email.mime.text import MIMEText
from datetime import date

import urllib.request
import urllib.error


def load_credentials(credentials_file="Notion"):
    """
    Read credentials from file.  Expected format (one per line):
        NOTION_API_TOKEN=secret_xxxx
        NOTION_DATABASE_ID=xxxx-xxxx-xxxx-xxxx
        EMAIL_FROM=youraddress@gmail.com
        EMAIL_TO=youraddress@gmail.com
        EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

    Returns (notion_token, database_id, email_from, email_to, email_app_password).
    Raises FileNotFoundError / ValueError on missing file or missing fields.
    """
    from pathlib import Path

    path = Path(credentials_file)
    if not path.exists():
        # Try relative to this file's parent-parent (project root)
        project_root = Path(__file__).resolve().parent.parent
        path = project_root / credentials_file
    if not path.exists():
        raise FileNotFoundError(f"Notion credentials file not found: {credentials_file}")

    creds = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                creds[key.strip()] = value.strip()

    required = [
        "NOTION_API_TOKEN",
        "NOTION_DATABASE_ID",
        "EMAIL_FROM",
        "EMAIL_TO",
        "EMAIL_APP_PASSWORD",
    ]
    missing = [k for k in required if not creds.get(k)]
    if missing:
        raise ValueError(f"Missing fields in Notion credentials file: {missing}")

    return (
        creds["NOTION_API_TOKEN"],
        creds["NOTION_DATABASE_ID"],
        creds["EMAIL_FROM"],
        creds["EMAIL_TO"],
        creds["EMAIL_APP_PASSWORD"],
    )


def _notion_request(method, url, notion_token, body=None):
    """Low-level Notion API call using urllib (no requests dependency)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise RuntimeError(f"Notion API error {e.code}: {body_text}") from e


def write_failure_code_to_notion(notion_token, database_id, date_str):
    """
    Create a new row in the Notion database with Name = date_str and
    all bid/ask fields left blank (user fills them in manually).

    Returns the created page object.
    """
    url = "https://api.notion.com/v1/pages"
    body = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [{"text": {"content": date_str}}]
            }
        },
    }
    result = _notion_request("POST", url, notion_token, body)
    return result


def read_forward_points_from_notion(notion_token, database_id, date_str):
    """
    Query the Notion database for the row where Name = date_str.
    Reads properties: 1m_Bid, 1m_Ask, 3m_Bid, 3m_Ask, 6m_Bid, 6m_Ask.
    Calculates mid = (bid + ask) / 2 for each tenor.

    Returns {'1M': mid_1m, '3M': mid_3m, '6M': mid_6m}.
    Raises ValueError if row not found or any bid/ask field is empty.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    body = {
        "filter": {
            "property": "Name",
            "title": {"equals": date_str},
        }
    }
    result = _notion_request("POST", url, notion_token, body)
    results = result.get("results", [])

    if not results:
        raise ValueError(
            f"No row found in Notion database for date '{date_str}'. "
            "Please add a row with the bid/ask values and rerun."
        )

    props = results[0].get("properties", {})

    def _get_number(props, field_name):
        prop = props.get(field_name)
        if prop is None:
            raise ValueError(f"Property '{field_name}' not found in Notion row.")
        num = prop.get("number")
        if num is None:
            raise ValueError(
                f"Property '{field_name}' is empty in Notion. "
                "Please fill in all bid/ask values before rerunning."
            )
        return num

    mid_1m = (_get_number(props, "1m_Bid") + _get_number(props, "1m_Ask")) / 2
    mid_3m = (_get_number(props, "3m_Bid") + _get_number(props, "3m_Ask")) / 2
    mid_6m = (_get_number(props, "6m_Bid") + _get_number(props, "6m_Ask")) / 2

    return {"1M": mid_1m, "3M": mid_3m, "6M": mid_6m}


def send_failure_email(email_from, email_to, app_password, error_message):
    """
    Send a Gmail alert (SSL, port 465) notifying that the pipeline stopped
    and forward points need to be entered in Notion.
    """
    today = date.today().isoformat()

    body = f"""\
The SwapImplied pipeline stopped on {today} because Browse AI failed to extract
forward points automatically.

Error: {error_message}

--- Action required ---
1. Open the Notion database and find the row for {today}.
2. Fill in the 6 bid/ask fields (1m_Bid, 1m_Ask, 3m_Bid, 3m_Ask, 6m_Bid, 6m_Ask)
   with today's USD/SGD forward points from investing.com.
3. Rerun the pipeline with the --notion-fallback flag:

       python run_pipeline.py --notion-fallback

The pipeline will read the values from Notion and complete normally.
"""

    msg = MIMEText(body)
    msg["Subject"] = "[SwapImplied] Pipeline stopped \u2014 forward points needed"
    msg["From"] = email_from
    msg["To"] = email_to

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(email_from, app_password)
        server.sendmail(email_from, email_to, msg.as_string())
