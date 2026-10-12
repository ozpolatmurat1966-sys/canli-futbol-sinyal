"""Transparent odds calculations. These are market-implied estimates, not independent predictions."""
from collections import defaultdict
from math import isfinite


def normalize_implied_probabilities(odds_by_selection):
    """Remove bookmaker overround by normalizing 1/decimal-odds across outcomes."""
    raw = {}
    for selection, value in (odds_by_selection or {}).items():
        try:
            price = float(value)
        except (TypeError, ValueError):
            continue
        if not isfinite(price) or price <= 1:
            continue
        raw[str(selection)] = 1.0 / price
    total = sum(raw.values())
    if not raw or total <= 0:
        return {"raw_probabilities": {}, "fair_probabilities": {}, "overround": None}
    return {
        "raw_probabilities": raw,
        "fair_probabilities": {key: value / total for key, value in raw.items()},
        "overround": total - 1.0,
    }


def detect_odds_movements(rows, min_abs_change=0.20, min_relative_change=0.12):
    """Flag notable recorded price changes within the same fixture/market/selection/stage."""
    grouped = defaultdict(list)
    for row in rows or []:
        get = row.get if hasattr(row, "get") else lambda key, default=None: row[key] if key in row.keys() else default
        try:
            price = float(get("odd"))
        except (TypeError, ValueError):
            continue
        if not isfinite(price) or price <= 1:
            continue
        timestamp = str(get("observed_at") or "")
        if not timestamp:
            continue
        key = (
            str(get("fixture_key") or ""), str(get("market") or ""),
            str(get("option_name") or ""), str(get("bookmaker") or ""),
            str(get("stage") or ""), str(get("line") or ""),
        )
        grouped[key].append({
            "observed_at": timestamp, "odd": price,
            "home": get("home") or "Ev sahibi", "away": get("away") or "Deplasman",
            "league": get("league") or "Lig bilinmiyor",
        })

    movements = []
    for key, observations in grouped.items():
        by_time = {}
        for item in sorted(observations, key=lambda item: item["observed_at"]):
            by_time[item["observed_at"]] = item
        ordered = list(by_time.values())
        if len(ordered) < 2:
            continue
        previous, latest = ordered[-2], ordered[-1]
        change = latest["odd"] - previous["odd"]
        relative = change / previous["odd"]
        if abs(change) < min_abs_change and abs(relative) < min_relative_change:
            continue
        movements.append({
            "fixture_key": key[0], "market": key[1], "option_name": key[2],
            "bookmaker": key[3], "stage": key[4], "line": key[5],
            "home": latest["home"], "away": latest["away"], "league": latest["league"],
            "previous_odd": previous["odd"], "latest_odd": latest["odd"],
            "change": change, "relative_change": relative,
            "observed_at": latest["observed_at"],
            "direction": "Oran yükseldi" if change > 0 else "Oran düştü",
        })
    return sorted(movements, key=lambda row: abs(row["relative_change"]), reverse=True)
