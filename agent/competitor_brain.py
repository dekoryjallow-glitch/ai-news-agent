import os
import json
import anthropic


SIGNAL_EMOJIS = {
    "pricing_change": "💰",
    "new_feature": "🚀",
    "negative_review": "😤",
    "press_release": "📣",
    "hiring_signal": "👥",
    "blog_post": "📝",
    "positive_review": "⭐",
    "funding": "💶",
    "partnership": "🤝",
    "general": "📰",
}

TIER_EMOJIS = {
    "tier1": "🟢",
    "tier2": "🔴",
    "tier3": "🟡",
}


def _build_competitor_prompt(signals: list[dict], config: dict) -> str:
    signal_weights = config.get("competitor_intel", {}).get("signal_weights", {})

    signals_json = json.dumps(
        [{"id": i, "competitor": s["competitor"], "tier": s["tier"],
          "title": s["title"], "snippet": s["snippet"]}
         for i, s in enumerate(signals)],
        ensure_ascii=False,
        indent=2
    )

    weights_info = "\n".join([f"- {k}: {v} Punkte" for k, v in signal_weights.items()])

    return f"""Du analysierst Competitor-Signale fuer Plancraft (SaaS fuer Handwerksbetriebe in Deutschland).

Plancraft ist Marktfuehrer bei SEO-Visibility (29,3%), HERO Software ist #2 (25%), Tooltime #3 (20,4%).

SIGNAL-GEWICHTUNG:
{weights_info}

COMPETITOR-SIGNALE:
{signals_json}

Analysiere jedes Signal und erstelle ein JSON-Array mit folgenden Feldern pro Item:
- id: die id aus dem Input
- signal_type: einer von [pricing_change, new_feature, negative_review, press_release, hiring_signal, blog_post, positive_review, funding, partnership, general]
- relevance_score: Zahl 1-10 (wie relevant ist das fuer Plancrafts Outbound/Positioning)
- summary: 1-2 Saetze was passiert ist (Deutsch)
- sales_implication: Was bedeutet das konkret fuer Plancrafts Outbound oder Positionierung? (1 Satz, direkt und umsetzbar)
- customer_pain: Falls es sich um eine Review oder Beschwerde handelt — welcher konkrete Schmerzpunkt wird genannt? (kurz, oder null)
- is_hot: true wenn das Signal sofortige Aufmerksamkeit braucht (Preisaenderung, grosses Feature, schlechte Reviews, Funding)

Bei Signalen vom Typ "review": Fokus auf konkrete Beschwerden (Support, Preis, fehlende Features, Bugs).
Bei negativen Reviews: sales_implication sollte einen konkreten Outbound-Pitch-Baustein liefern.

Antworte NUR mit dem JSON-Array, kein Text darum.
"""


def analyze_competitor_signals(signals: list[dict], config: dict) -> list[dict]:
    if not signals:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")

    client = anthropic.Anthropic(api_key=api_key)
    ai_config = config.get("ai", {})

    batch_size = 15
    enriched = []

    for batch_start in range(0, len(signals), batch_size):
        batch = signals[batch_start: batch_start + batch_size]
        print(f"[competitor_brain] Analyzing batch {batch_start // batch_size + 1} ({len(batch)} signals)...")

        prompt = _build_competitor_prompt(batch, config)

        try:
            message = client.messages.create(
                model=ai_config.get("model", "claude-sonnet-4-6"),
                max_tokens=4096,
                system=ai_config.get("system_prompt", ""),
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()

            if "```" in response_text:
                import re
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
                if match:
                    response_text = match.group(1).strip()

            scored_batch = json.loads(response_text)
            score_map = {item["id"]: item for item in scored_batch}

            for i, original in enumerate(batch):
                ai_data = score_map.get(i, {})
                enriched.append({**original, **ai_data})

        except Exception as e:
            print(f"[competitor_brain] Error in batch: {e}")
            for s in batch:
                enriched.append({**s, "relevance_score": 1, "signal_type": "general",
                                  "summary": s.get("snippet", ""), "sales_implication": "", "is_hot": False})

    enriched.sort(key=lambda x: (x.get("is_hot", False), x.get("relevance_score", 0)), reverse=True)
    print(f"[competitor_brain] Analysis complete. Hot signals: {sum(1 for s in enriched if s.get('is_hot'))}")
    return enriched
