from datetime import datetime
from agent.brain import CLUSTER_EMOJIS, ACTION_LABELS


def _emoji(cluster: str) -> str:
    return CLUSTER_EMOJIS.get(cluster, "📌")


def _action_label(action: str) -> str:
    return ACTION_LABELS.get(action, action)


def format_daily(items: list[dict], config: dict) -> list[dict]:
    max_items = config.get("agent", {}).get("output", {}).get("daily_max_items", 8)
    radar_max = config.get("agent", {}).get("output", {}).get("radar_max_items", 5)

    date_str = datetime.now().strftime("%d.%m.%Y")
    top = items[0] if items else None
    picks = items[1:max_items] if len(items) > 1 else []
    radar = items[max_items : max_items + radar_max] if len(items) > max_items else []

    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Deko's Daily Intel — {date_str}",
            "emoji": True,
        },
    })
    blocks.append({"type": "divider"})

    # Top Pick
    if top:
        cluster_emoji = _emoji(top.get("cluster", "unknown"))
        action = _action_label(top.get("action", ""))
        project_ref = top.get("project_ref", "")
        use_case = top.get("use_case", "")
        summary = top.get("summary", top.get("snippet", ""))

        top_text = f"*{cluster_emoji} TOP PICK*\n\n"
        top_text += f"*<{top['url']}|{top['title']}>*\n"
        top_text += f"{summary}\n\n"
        if use_case:
            top_text += f"💡 *Idee:* {use_case}\n"
        if project_ref:
            top_text += f"🔗 *Bezug:* {project_ref}"
        if action:
            top_text += f"  |  ⚡ *Action:* {action}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": top_text},
        })
        blocks.append({"type": "divider"})

    # Further picks
    if picks:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📌 WEITERE PICKS*"},
        })

        for i, item in enumerate(picks, 1):
            cluster_emoji = _emoji(item.get("cluster", "unknown"))
            use_case = item.get("use_case", "")
            project_ref = item.get("project_ref", "")
            summary = item.get("summary", item.get("snippet", ""))

            text = f"*{i}. {cluster_emoji} <{item['url']}|{item['title']}>*\n"
            text += f"{summary}\n"
            if use_case:
                text += f"💡 {use_case}"
            if project_ref:
                text += f"  |  🔗 {project_ref}"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            })

        blocks.append({"type": "divider"})

    # Radar
    if radar:
        radar_lines = ["*📡 RADAR*\n"]
        for item in radar:
            radar_lines.append(f"• <{item['url']}|{item['title']}> _{item.get('source', '')}_")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(radar_lines)},
        })

    return blocks


def format_weekly(items_by_day: list[dict], week_num: int, config: dict) -> list[dict]:
    top_n = config.get("agent", {}).get("output", {}).get("weekly_top_items", 3)

    blocks = []

    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Deko's Weekly Wrap — KW {week_num}",
            "emoji": True,
        },
    })
    blocks.append({"type": "divider"})

    # Top 3 of the week
    top_items = sorted(items_by_day, key=lambda x: x.get("score", 0), reverse=True)[:top_n]
    if top_items:
        top_text = "*🏆 Top 3 der Woche*\n\n"
        for i, item in enumerate(top_items, 1):
            cluster_emoji = _emoji(item.get("cluster", "unknown"))
            top_text += f"*{i}. {cluster_emoji} <{item['url']}|{item['title']}>*\n"
            top_text += f"{item.get('summary', '')}\n\n"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": top_text},
        })
        blocks.append({"type": "divider"})

    # Stats
    total_sources = len(set(i.get("source", "") for i in items_by_day))
    stats_text = f"📊 *Stats:* {total_sources} Quellen gescannt | {len(items_by_day)} Items bewertet"
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": stats_text},
    })

    return blocks
