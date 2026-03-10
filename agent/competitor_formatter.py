from datetime import datetime
from agent.competitor_brain import SIGNAL_EMOJIS, TIER_EMOJIS


def format_competitor_roundup(signals: list[dict], config: dict) -> list[dict]:
    week_num = datetime.now().isocalendar()[1]
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Competitor Roundup — KW {week_num}",
            "emoji": True,
        },
    })
    blocks.append({"type": "divider"})

    # Hot signals
    hot_signals = [s for s in signals if s.get("is_hot") and s.get("relevance_score", 0) >= 6][:5]

    if hot_signals:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*HOT SIGNALS*"},
        })

        for signal in hot_signals:
            tier_emoji = TIER_EMOJIS.get(signal.get("tier", "tier2"), "🔵")
            signal_emoji = SIGNAL_EMOJIS.get(signal.get("signal_type", "general"), "📰")
            summary = signal.get("summary", signal.get("snippet", ""))
            sales_impl = signal.get("sales_implication", "")

            text = f"*{tier_emoji} {signal['competitor']}* {signal_emoji}\n"
            text += f"{summary}\n"
            if sales_impl:
                text += f"🎯 *Sales-Implikation:* {sales_impl}\n"
            text += f"→ <{signal['url']}|Quelle>"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            })

        blocks.append({"type": "divider"})

    # Weekly tracker table (top signals by competitor)
    tier1_signals = [s for s in signals if s.get("tier") == "tier1"]

    if tier1_signals:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*WEEKLY TRACKER — Tier 1*"},
        })

        # Group by competitor, take top signal per competitor
        seen_competitors = set()
        tracker_items = []
        for signal in tier1_signals:
            comp = signal["competitor"]
            if comp not in seen_competitors:
                seen_competitors.add(comp)
                tracker_items.append(signal)

        tracker_lines = []
        for s in tracker_items[:6]:
            signal_emoji = SIGNAL_EMOJIS.get(s.get("signal_type", "general"), "📰")
            score = s.get("relevance_score", 0)
            summary = s.get("summary", s.get("title", ""))[:80]
            tracker_lines.append(f"• *{s['competitor']}* {signal_emoji} (Score: {score}) — {summary}")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(tracker_lines)},
        })
        blocks.append({"type": "divider"})

    # Stats
    hot_count = len(hot_signals)
    total_count = len(signals)
    competitors_tracked = len(set(s["competitor"] for s in signals))

    stats = f"📊 *Stats:* {competitors_tracked} Competitors getrackt | {total_count} Signals analysiert | {hot_count} Hot Signals"
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": stats},
    })

    return blocks
