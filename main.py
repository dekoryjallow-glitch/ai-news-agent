import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from agent.collector import collect_all
from agent.cache import init_db, filter_new_items, mark_seen, cleanup_old_entries
from agent.brain import score_and_enrich
from agent.formatter import format_daily
from agent.delivery import send_slack
from agent.competitor_collector import collect_competitor_signals
from agent.competitor_brain import analyze_competitor_signals
from agent.competitor_formatter import format_competitor_roundup


def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_daily(config: dict, dry_run: bool = False) -> None:
    print(f"\n=== Deko Intel Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    # 1. Collect
    print("[main] Step 1: Collecting items...")
    all_items = collect_all(config)
    if not all_items:
        print("[main] No items collected. Exiting.")
        return

    # 2. Deduplicate
    print("[main] Step 2: Deduplicating...")
    conn = init_db(config)
    cleanup_old_entries(conn, config.get("cache", {}).get("max_age_days", 7))
    new_items = filter_new_items(conn, all_items)
    print(f"[main] {len(new_items)} new items after dedup (from {len(all_items)} total)")

    if not new_items:
        print("[main] No new items to process. Exiting.")
        conn.close()
        return

    # 3. Score & Enrich
    print("[main] Step 3: Scoring and enriching with Claude...")
    enriched = score_and_enrich(new_items, config)

    # Filter items with score >= 4 for briefing
    relevant = [i for i in enriched if i.get("score", 0) >= 4]
    print(f"[main] {len(relevant)} relevant items (score >= 4)")

    if not relevant:
        print("[main] No relevant items found. Exiting.")
        conn.close()
        return

    # 4. Format
    print("[main] Step 4: Formatting Slack message...")
    blocks = format_daily(relevant, config)

    # 5. Send (or dry run)
    if dry_run:
        import json
        conn.close()
        print("\n[main] DRY RUN — Slack message NOT sent. Blocks:")
        output = json.dumps(blocks, ensure_ascii=True, indent=2)
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    else:
        print("[main] Step 5: Sending to Slack...")
        send_slack(blocks, config)
        mark_seen(conn, new_items)
        conn.close()

    print("\n[main] Done.")


def run_competitor(config: dict, dry_run: bool = False) -> None:
    print(f"\n=== Competitor Intel — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    print("[main] Step 1: Collecting competitor signals...")
    signals = collect_competitor_signals(config)
    if not signals:
        print("[main] No competitor signals found. Exiting.")
        return

    print("[main] Step 2: Analyzing signals with Claude...")
    enriched = analyze_competitor_signals(signals, config)

    print("[main] Step 3: Formatting Slack roundup...")
    blocks = format_competitor_roundup(enriched, config)

    if dry_run:
        import json
        print("\n[main] DRY RUN — Competitor roundup NOT sent. Blocks:")
        output = json.dumps(blocks, ensure_ascii=True, indent=2)
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    else:
        print("[main] Step 4: Sending to Slack...")
        send_slack(blocks, config)

    print("\n[main] Done.")


def main():
    load_dotenv()

    dry_run = "--dry-run" in sys.argv
    competitor_mode = "--competitor" in sys.argv

    if dry_run:
        print("[main] Running in DRY RUN mode (no Slack message will be sent)")

    config = load_config()

    if competitor_mode:
        run_competitor(config, dry_run=dry_run)
    else:
        run_daily(config, dry_run=dry_run)


if __name__ == "__main__":
    main()
