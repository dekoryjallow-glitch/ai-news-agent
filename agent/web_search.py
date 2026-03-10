import os
from datetime import datetime, timezone, timedelta


def _get_client():
    from tavily import TavilyClient
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY nicht gesetzt")
    return TavilyClient(api_key=api_key)


def search(query: str, max_results: int = 5, days: int = 7) -> list[dict]:
    """General Tavily web search. Returns normalized items."""
    client = _get_client()

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
    except Exception as e:
        print(f"[web_search] Tavily error for '{query}': {e}")
        return []

    items = []
    for result in response.get("results", []):
        url = result.get("url", "")
        title = result.get("title", "")
        snippet = result.get("content", "")[:300]
        if not url or not title:
            continue
        items.append({
            "title": title.strip(),
            "url": url.strip(),
            "snippet": snippet.strip(),
            "source": "Web Search",
            "date": datetime.now(timezone.utc).isoformat(),
        })

    return items


def search_social(competitor_name: str, max_results: int = 4) -> list[dict]:
    """Search for social media signals: LinkedIn posts, Reddit, Facebook public pages."""
    queries = [
        f'"{competitor_name}" site:linkedin.com',
        f'"{competitor_name}" Handwerk site:reddit.com OR site:facebook.com',
        f'"{competitor_name}" Handwerkersoftware Meinung Erfahrung forum',
    ]

    all_items = []
    seen_urls = set()
    client = _get_client()

    for query in queries:
        try:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
            )
        except Exception as e:
            print(f"[web_search] Social search error for {competitor_name}: {e}")
            continue

        for result in response.get("results", []):
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("content", "")[:400]
            if not url or not title or url in seen_urls:
                continue

            # Determine platform
            platform = "Social"
            if "linkedin.com" in url:
                platform = "LinkedIn"
            elif "reddit.com" in url:
                platform = "Reddit"
            elif "facebook.com" in url:
                platform = "Facebook"
            elif "xing.com" in url:
                platform = "Xing"

            seen_urls.add(url)
            all_items.append({
                "title": title.strip(),
                "url": url.strip(),
                "snippet": snippet.strip(),
                "source": f"{platform}: {competitor_name}",
                "date": datetime.now(timezone.utc).isoformat(),
                "competitor": competitor_name,
                "type": "social",
                "platform": platform,
            })

    return all_items


def search_reviews(competitor_name: str, max_results: int = 5) -> list[dict]:
    """Search for negative reviews and unhappy customer signals for a competitor."""
    queries = [
        f'"{competitor_name}" Erfahrungen Probleme Kritik',
        f'"{competitor_name}" schlechter Support Bewertung',
        f'"{competitor_name}" site:trustpilot.com OR site:omr.com',
    ]

    all_items = []
    seen_urls = set()

    client = _get_client()

    for query in queries[:2]:  # 2 queries per competitor to save API budget
        try:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
            )
        except Exception as e:
            print(f"[web_search] Review search error for {competitor_name}: {e}")
            continue

        for result in response.get("results", []):
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("content", "")[:400]
            if not url or not title or url in seen_urls:
                continue
            seen_urls.add(url)
            all_items.append({
                "title": title.strip(),
                "url": url.strip(),
                "snippet": snippet.strip(),
                "source": f"Review: {competitor_name}",
                "date": datetime.now(timezone.utc).isoformat(),
                "competitor": competitor_name,
                "type": "review",
            })

    return all_items
