import os
import json
import anthropic
from datetime import datetime


CLUSTER_EMOJIS = {
    "sales_plancraft": "🎯",
    "builder": "🛠️",
    "health": "🏥",
    "macro": "🌍",
    "general_ai": "🤖",
    "unknown": "📌",
}

ACTION_LABELS = {
    "heute_testen": "Heute testen",
    "auf_dem_radar": "Auf dem Radar",
    "einbauen": "Einbauen",
    "beobachten": "Beobachten",
}


def _build_prompt(items: list[dict], config: dict) -> str:
    clusters = config.get("clusters", {})
    cluster_info = []
    for cluster_id, cluster_data in clusters.items():
        keywords = ", ".join(cluster_data.get("keywords", [])[:10])
        cluster_info.append(f"- {cluster_id} (Gewicht {cluster_data['weight']}): {keywords}")

    items_json = json.dumps(
        [{"id": i, "title": item["title"], "snippet": item["snippet"], "source": item["source"]}
         for i, item in enumerate(items)],
        ensure_ascii=False,
        indent=2
    )

    return f"""Analysiere die folgenden News-Items und bewerte sie fuer Deko.

CLUSTER-DEFINITIONEN:
{chr(10).join(cluster_info)}

NEWS-ITEMS:
{items_json}

Erstelle fuer JEDES Item ein JSON-Objekt mit folgenden Feldern:
- id: die id aus dem Input
- cluster: einer von [sales_plancraft, builder, health, macro, general_ai, unknown]
- score: Zahl von 1-10 (Relevanz fuer Deko)
- summary: 1-2 praegnante Saetze auf Deutsch, was wirklich wichtig ist
- use_case: konkrete Idee was Deko damit machen koennte (1 Satz, direkt und umsetzbar)
- project_ref: welches Projekt/Bereich betroffen ist (z.B. "DiaAgent", "Plancraft Outbound", "Personal / Markets", "Allgemein")
- action: einer von [heute_testen, einbauen, auf_dem_radar, beobachten]
- is_breaking: true wenn das Item weniger als 24h alt erscheint oder exklusiv wirkt

Antworte NUR mit einem JSON-Array, kein erklaerende Text darum.
Beispiel-Format:
[
  {{
    "id": 0,
    "cluster": "builder",
    "score": 8,
    "summary": "Anthropic hat Tool Use verbessert...",
    "use_case": "Koennte die Tool-Orchestrierung in DiaAgent vereinfachen.",
    "project_ref": "DiaAgent",
    "action": "einbauen",
    "is_breaking": false
  }}
]"""


def score_and_enrich(items: list[dict], config: dict) -> list[dict]:
    if not items:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")

    client = anthropic.Anthropic(api_key=api_key)
    ai_config = config.get("ai", {})

    # Process in batches of 20 to stay within token limits
    batch_size = 20
    enriched = []

    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start : batch_start + batch_size]
        print(f"[brain] Scoring batch {batch_start // batch_size + 1} ({len(batch)} items)...")

        prompt = _build_prompt(batch, config)

        try:
            message = client.messages.create(
                model=ai_config.get("model", "claude-sonnet-4-6"),
                max_tokens=ai_config.get("max_tokens", 4096),
                system=ai_config.get("system_prompt", ""),
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()

            # Extract JSON if wrapped in markdown code block
            if "```" in response_text:
                import re
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
                if match:
                    response_text = match.group(1).strip()

            scored_batch = json.loads(response_text)

            # Merge AI scores back into original items
            score_map = {item["id"]: item for item in scored_batch}
            for i, original_item in enumerate(batch):
                ai_data = score_map.get(i, {})
                enriched_item = {**original_item, **ai_data}
                # Apply project bonus to score
                enriched_item["score"] = _apply_bonuses(enriched_item, config)
                enriched.append(enriched_item)

        except Exception as e:
            print(f"[brain] Error processing batch: {e}")
            # Fallback: add items without enrichment
            for item in batch:
                enriched.append({**item, "score": 1, "cluster": "unknown",
                                  "summary": item.get("snippet", ""), "use_case": "", "project_ref": ""})

    # Sort by score descending
    enriched.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"[brain] Enrichment complete. Top score: {enriched[0]['score'] if enriched else 0}")
    return enriched


def _apply_bonuses(item: dict, config: dict) -> float:
    base_score = float(item.get("score", 1))
    cluster = item.get("cluster", "unknown")
    cluster_config = config.get("clusters", {}).get(cluster, {})

    # Project bonus: check if item references known projects
    project_bonuses = cluster_config.get("project_bonus", [])
    title_lower = (item.get("title", "") + " " + item.get("snippet", "")).lower()
    for project in project_bonuses:
        if project.lower().replace("-", " ") in title_lower or project.lower() in title_lower:
            base_score += 3
            break

    # Breaking news bonus
    if item.get("is_breaking"):
        base_score += 1

    return round(base_score, 1)
