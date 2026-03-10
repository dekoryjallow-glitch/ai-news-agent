import feedparser
from datetime import datetime, timezone, timedelta
import re


def _snippet(entry) -> str:
    for field in ("summary", "description"):
        val = getattr(entry, field, None)
        if val:
            text = re.sub(r"<[^>]+>", " ", str(val))
            text = re.sub(r"\s+", " ", text).strip()
            return text[:300]
    return ""


def _parse_date(entry) -> str:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _is_recent(date_str: str, days: int = 7) -> bool:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return dt >= cutoff
    except Exception:
        return True


def fetch_google_news(competitor_name: str, query: str, max_items: int = 10) -> list[dict]:
    encoded_query = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=de&gl=DE&ceid=DE:de"

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[competitor_collector] Failed to fetch news for {competitor_name}: {e}")
        return []

    items = []
    for entry in feed.entries[:max_items]:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue

        date_str = _parse_date(entry)
        if not _is_recent(date_str, days=7):
            continue

        items.append({
            "title": title.strip(),
            "url": link.strip(),
            "snippet": _snippet(entry),
            "source": f"Google News: {competitor_name}",
            "date": date_str,
            "competitor": competitor_name,
            "type": "news",
        })

    return items


def collect_competitor_signals(config: dict) -> list[dict]:
    import os
    from agent.web_search import search as tavily_search, search_reviews

    competitor_config = config.get("competitor_intel", {})
    competitors = competitor_config.get("competitors", {})
    use_tavily = bool(os.environ.get("TAVILY_API_KEY"))

    if not use_tavily:
        print("[competitor_collector] TAVILY_API_KEY not set — using Google News only")

    all_signals = []
    seen_urls = set()

    for tier, tier_competitors in competitors.items():
        for comp in tier_competitors:
            name = comp["name"]
            query = comp.get("google_news_query", name)
            comp_signals = []

            # 1. Google News RSS (always)
            news_items = fetch_google_news(name, query, max_items=8)
            comp_signals.extend(news_items)

            # 2. Tavily web search for broader news (Tier 1 only)
            if use_tavily and tier == "tier1":
                web_items = tavily_search(
                    query=f"{name} Handwerkersoftware News 2025 2026",
                    max_results=4,
                )
                for item in web_items:
                    item["competitor"] = name
                    item["type"] = "news"
                comp_signals.extend(web_items)

                # 3. Review / unhappy customer search (Tier 1 only)
                review_items = search_reviews(name, max_results=4)
                comp_signals.extend(review_items)

            # Deduplicate by URL, attach tier
            for item in comp_signals:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    item["tier"] = tier
                    all_signals.append(item)

            news_count = len([s for s in comp_signals if s.get("type") == "news"])
            review_count = len([s for s in comp_signals if s.get("type") == "review"])
            print(f"[competitor_collector] {name} ({tier}): {news_count} news, {review_count} reviews")

    all_signals.sort(key=lambda x: x.get("date", ""), reverse=True)
    print(f"[competitor_collector] Total signals: {len(all_signals)}")
    return all_signals
