import os
import httpx
import json


def send_slack(blocks: list[dict], config: dict) -> bool:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or config.get("slack", {}).get("webhook_url", "")

    if not webhook_url or webhook_url.startswith("${"):
        raise ValueError("SLACK_WEBHOOK_URL nicht gesetzt")

    payload = {"blocks": blocks}

    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        print(f"[delivery] Slack message sent successfully ({response.status_code})")
        return True
    except httpx.HTTPStatusError as e:
        print(f"[delivery] Slack HTTP error: {e.response.status_code} — {e.response.text}")
        raise
    except Exception as e:
        print(f"[delivery] Failed to send Slack message: {e}")
        raise
