"""Conservative parser for player-prop prices when a provider explicitly returns them."""
import re


PLAYER_TERMS = ("player", "oyuncu", "shots on target", "player shots", "player goals",
                "player assists", "player cards", "player fouls", "to score", "anytime scorer")

PLAYER_MARKET_NAMES = {
    "player_shots": "Player Shots", "player_goals": "Player Goals",
    "player_assists": "Player Assists", "player_cards": "Player Cards",
    "player_fouls": "Player Fouls", "player_shots_on_target": "Player Shots on Target",
    "anytime_scorer": "Anytime Goalscorer", "to_score": "Player to Score",
}


def extract_player_prop_rows(payload):
    """Only extracts rows explicitly marked as player markets; does not infer missing prices."""
    results = []
    seen = set()

    def walk(node, context=None):
        if isinstance(node, list):
            for item in node:
                walk(item, context)
            return
        if not isinstance(node, dict):
            return
        merged = dict(context or {})
        for key in ("player", "player_name", "playerName", "market", "market_name", "marketName",
                    "name", "label", "selection", "outcome", "bookmaker", "bookmaker_name",
                    "stage", "line", "handicap"):
            value = node.get(key)
            if isinstance(value, (str, int, float)) and value not in ("", None):
                merged[key] = value
        market = str(node.get("market") or node.get("market_name") or node.get("marketName") or
                     merged.get("market") or "")
        if isinstance(node.get("odds"), (dict, list)) and node.get("name"):
            merged["bookmaker"] = node.get("name")
        context_text = " ".join(str(merged.get(k, "")) for k in ("market", "market_name", "marketName", "name", "label")).lower()
        player = node.get("player_name") or node.get("playerName") or node.get("player")
        if isinstance(player, dict):
            player = player.get("name") or player.get("display_name")
        player = player or merged.get("player_name") or merged.get("playerName")
        is_player_market = any(term in context_text for term in PLAYER_TERMS) or bool(node.get("player_id") or node.get("playerId"))
        price = None
        for key in ("odd", "odds", "price", "decimal_odds", "decimalOdds", "value"):
            value = node.get(key)
            if isinstance(value, (int, float, str)):
                try:
                    candidate = float(str(value).strip())
                    if candidate > 1:
                        price = candidate
                        break
                except (ValueError, TypeError):
                    pass
        if is_player_market and price is not None:
            selection = node.get("selection") or node.get("outcome") or node.get("label") or node.get("name") or "Seçenek"
            market_label = market or merged.get("market") or "Oyuncu pazarı"
            player_label = str(player or node.get("name") or merged.get("player") or "Oyuncu adı belirtilmemiş")
            bookmaker = node.get("bookmaker") or node.get("bookmaker_name") or merged.get("bookmaker") or "Sağlayıcı"
            stage = node.get("stage") or merged.get("stage") or "Mevcut"
            line = node.get("line") or node.get("handicap") or merged.get("line") or ""
            key = (player_label, str(market_label), str(selection), str(bookmaker), str(stage), str(line), price)
            if key not in seen:
                seen.add(key)
                results.append({
                    "Oyuncu": player_label, "Pazar": str(market_label), "Seçenek": str(selection),
                    "Oran": price, "Şirket": str(bookmaker), "Aşama": str(stage),
                    "Çizgi": str(line) if line != "" else "—",
                })
        # Prop markets often use nested odds/outcomes maps; preserve the nearest market context.
        next_context = dict(merged)
        if market:
            next_context["market"] = market
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                child_context = dict(next_context)
                key_lower = str(key).lower()
                if key_lower in ("player", "player_name", "playername") and isinstance(value, dict):
                    child_context["player"] = value.get("name") or value.get("display_name") or child_context.get("player")
                elif any(term in key_lower for term in PLAYER_TERMS) or key_lower.startswith("player_"):
                    child_context["market"] = PLAYER_MARKET_NAMES.get(key_lower, key_lower.replace("_", " ").title())
                elif key_lower in ("opening", "closing", "inplay", "live"):
                    child_context["stage"] = key_lower.title()
                walk(value, child_context)

    walk(payload)
    return results
