import feedparser
import httpx
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def _parse_date(entry) -> str:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _snippet(entry) -> str:
    for field in ("summary", "description", "content"):
        val = getattr(entry, field, None)
        if val:
            if isinstance(val, list):
                val = val[0].get("value", "") if val else ""
            # Strip HTML tags roughly
            import re
            text = re.sub(r"<[^>]+>", " ", str(val))
            text = re.sub(r"\s+", " ", text).strip()
            return text[:300]
    return ""


def fetch_rss(source: dict) -> list[dict]:
    url = source["url"]
    name = source["name"]
    max_items = source.get("max_items", 20)

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[collector] Failed to fetch {name}: {e}")
        return []

    items = []
    for entry in feed.entries[:max_items]:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue

        items.append({
            "title": title.strip(),
            "url": link.strip(),
            "snippet": _snippet(entry),
            "source": name,
            "date": _parse_date(entry),
        })

    print(f"[collector] {name}: {len(items)} items fetched")
    return items


def collect_all(config: dict) -> list[dict]:
    sources = config.get("sources", {}).get("tier1", {}).get("rss", [])
    all_items = []

    for source in sources:
        items = fetch_rss(source)
        all_items.extend(items)

    # Sort by date descending (newest first)
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"[collector] Total items collected: {len(all_items)}")
    return all_items
