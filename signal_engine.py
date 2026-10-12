"""Pure helpers for transparent football trend summaries; no predictive claims."""
from datetime import datetime, timezone


def _dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _number(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_trend_rows(fixture, snapshots):
    """Compare the newest snapshot to a prior observation near 5/10/15-minute cutoffs."""
    if len(snapshots or []) < 2:
        return []
    ordered = sorted(
        [dict(s) for s in snapshots if _dt(s.get("observed_at")) is not None],
        key=lambda item: _dt(item.get("observed_at"))
    )
    if len(ordered) < 2:
        return []
    current = ordered[-1]
    current_time = _dt(current.get("observed_at"))
    home = fixture.get("home") or "Ev sahibi"
    away = fixture.get("away") or "Deplasman"
    league = fixture.get("league") or "Lig bilinmiyor"
    result = []
    for minutes in (5, 10, 15):
        cutoff = current_time.timestamp() - minutes * 60
        eligible = [s for s in ordered[:-1] if _dt(s.get("observed_at")).timestamp() <= cutoff]
        if not eligible:
            continue
        baseline = eligible[-1]
        age = (current_time - _dt(baseline.get("observed_at"))).total_seconds() / 60
        # Avoid labelling a very old observation as a 5/10/15-minute comparison.
        if age > minutes * 2.25:
            continue
        def score(s):
            h, a = _number(s.get("home_goals")), _number(s.get("away_goals"))
            return (h + a) if h is not None and a is not None else None
        def corners(s):
            h, a = _number(s.get("corners_home")), _number(s.get("corners_away"))
            return (h + a) if h is not None and a is not None else None
        before_score, after_score = score(baseline), score(current)
        before_corners, after_corners = corners(baseline), corners(current)
        result.append({
            "Maç": f"{home} - {away}",
            "Lig": league,
            "Pencere": f"Son {minutes} dk. (kayıt aralığı {age:.1f} dk.)",
            "Önceki skor": (
                f'{baseline.get("home_goals")} - {baseline.get("away_goals")}'
                if baseline.get("home_goals") is not None and baseline.get("away_goals") is not None else "—"
            ),
            "Son skor": (
                f'{current.get("home_goals")} - {current.get("away_goals")}'
                if current.get("home_goals") is not None and current.get("away_goals") is not None else "—"
            ),
            "Gol değişimi": int(after_score - before_score) if before_score is not None and after_score is not None else None,
            "Korner önce/sonra": (
                f"{before_corners:g} → {after_corners:g}"
                if before_corners is not None and after_corners is not None else "Veri yok"
            ),
            "Korner değişimi": int(after_corners - before_corners) if before_corners is not None and after_corners is not None else None,
            "Son gözlem (UTC)": current.get("observed_at"),
        })
    return result



def _pressure_stats(raw_stats, home_name, away_name):
    """Extract only explicitly present cumulative pressure statistics by side."""
    import json
    if isinstance(raw_stats, str):
        try:
            raw_stats = json.loads(raw_stats)
        except (TypeError, ValueError):
            return {"home": {}, "away": {}}
    result = {"home": {}, "away": {}}
    if not isinstance(raw_stats, (dict, list)):
        return result

    aliases = {
        "shots_on_target": ("shots on target", "shots on goal", "isabetli sut", "shots on target"),
        "total_shots": ("total shots", "shots total", "sut", "shots"),
        "corners": ("corner kicks", "corners", "corner", "korner"),
        "dangerous_attacks": ("dangerous attacks", "tehlikeli atak"),
        "red_cards": ("red cards", "kirmizi kart"),
    }

    def canon(label):
        import unicodedata
        text = unicodedata.normalize("NFKD", str(label or "")).encode("ascii", "ignore").decode("ascii").lower()
        text = " ".join(text.replace("_", " ").replace("-", " ").split())
        if any(term in text for term in ("shots on target", "shots on goal", "isabetli sut")):
            return "shots_on_target"
        if "dangerous attack" in text or "tehlikeli atak" in text:
            return "dangerous_attacks"
        if "red card" in text or "kirmizi kart" in text:
            return "red_cards"
        if "corner" in text or "korner" in text:
            return "corners"
        if "total shots" in text or text == "shots" or "shots total" in text or text == "sut":
            return "total_shots"
        return None

    def number(value):
        if value is None:
            return None
        try:
            text = str(value).replace("%", "").strip()
            return float(text) if text not in ("", "-", "—", "None") else None
        except (TypeError, ValueError):
            return None

    home_key = "".join(ch for ch in str(home_name or "").lower() if ch.isalnum())
    away_key = "".join(ch for ch in str(away_name or "").lower() if ch.isalnum())

    def walk(node, side=None):
        if isinstance(node, list):
            for item in node:
                walk(item, side)
        elif isinstance(node, dict):
            next_side = side
            for side_key in ("home", "home_rows", "home_stats", "local"):
                if side_key in node and isinstance(node[side_key], (dict, list)):
                    walk(node[side_key], "home")
            for side_key in ("away", "away_rows", "away_stats", "visitor"):
                if side_key in node and isinstance(node[side_key], (dict, list)):
                    walk(node[side_key], "away")
            label = node.get("type") or node.get("name") or node.get("statistic") or node.get("label")
            val = number(node.get("value", node.get("total")))
            if label is not None and val is not None:
                metric = canon(label)
                if metric and side in ("home", "away"):
                    result[side][metric] = val
                team = node.get("team")
                if metric and isinstance(team, dict):
                    team_name = "".join(ch for ch in str(team.get("name") or "").lower() if ch.isalnum())
                    target_side = "home" if team_name and team_name == home_key else "away" if team_name and team_name == away_key else None
                    if target_side:
                        result[target_side][metric] = val
            # Handle API payloads with a list of team objects containing statistics.
            team = node.get("team")
            team_name = team.get("name") if isinstance(team, dict) else None
            if team_name:
                normalized = "".join(ch for ch in str(team_name).lower() if ch.isalnum())
                if normalized == home_key:
                    next_side = "home"
                elif normalized == away_key:
                    next_side = "away"
            for key, value in node.items():
                if key in ("home", "home_rows", "home_stats", "local", "away", "away_rows", "away_stats", "visitor"):
                    continue
                if isinstance(value, (dict, list)):
                    walk(value, next_side)

    walk(raw_stats)
    return result


def build_pressure_rows(fixture, snapshots):
    """Summarize observed change in shots/corners/attacks; this is not a goal probability."""
    if len(snapshots or []) < 2:
        return []
    ordered = sorted(
        [dict(s) for s in snapshots if _dt(s.get("observed_at")) is not None],
        key=lambda item: _dt(item.get("observed_at"))
    )
    if len(ordered) < 2:
        return []
    current = ordered[-1]
    current_time = _dt(current.get("observed_at"))
    home_name = fixture.get("home") or (fixture.get("teams") or {}).get("home", {}).get("name") or "Ev sahibi"
    away_name = fixture.get("away") or (fixture.get("teams") or {}).get("away", {}).get("name") or "Deplasman"
    current_stats = _pressure_stats(current.get("stats_json"), home_name, away_name)
    result = []
    weights = {"shots_on_target": 3.0, "total_shots": 1.5, "corners": 1.2, "dangerous_attacks": 0.08}
    for minutes in (5, 10, 15):
        cutoff = current_time.timestamp() - minutes * 60
        eligible = [s for s in ordered[:-1] if _dt(s.get("observed_at")).timestamp() <= cutoff]
        if not eligible:
            continue
        baseline = eligible[-1]
        age = (current_time - _dt(baseline.get("observed_at"))).total_seconds() / 60
        if age > minutes * 2.25:
            continue
        baseline_stats = _pressure_stats(baseline.get("stats_json"), home_name, away_name)
        row = {"Maç": f"{home_name} - {away_name}", "Pencere": f"Son {minutes} dk. (kayıt aralığı {age:.1f} dk.)"}
        scores = {}
        observed = {}
        for side in ("home", "away"):
            deltas = {}
            for metric in weights:
                before = baseline_stats[side].get(metric)
                after = current_stats[side].get(metric)
                if before is not None and after is not None and after >= before:
                    deltas[metric] = after - before
            if deltas:
                scores[side] = round(sum(deltas[name] * weights[name] for name in deltas), 2)
                observed[side] = ", ".join(f"{name.replace('_', ' ')} +{value:g}" for name, value in deltas.items())
        if scores:
            row["Ev sahibi baskı göstergesi"] = scores.get("home")
            row["Deplasman baskı göstergesi"] = scores.get("away")
            details = []
            if "home" in observed:
                details.append(f'{home_name}: {observed["home"]}')
            if "away" in observed:
                details.append(f'{away_name}: {observed["away"]}')
            row["Gözlenen değişimler"] = " | ".join(details)
            if "home" not in scores or "away" not in scores:
                row["Karşılaştırma"] = "Bir taraf için yeterli istatistik yok"
            else:
                row["Karşılaştırma"] = "Ev sahibi daha yüksek" if scores["home"] > scores["away"] else "Deplasman daha yüksek" if scores["away"] > scores["home"] else "Benzer"
            result.append(row)
    return result


def summarize_odds_movements(conn=None, rows=None):
    """Normalize already-computed movement records to plain dictionaries."""
    if rows is not None:
        return [dict(row) for row in rows]
    if conn is None:
        return []
    records = conn.execute("""
        SELECT a.fixture_key, a.market, a.option_name, a.bookmaker,
               a.odd AS latest_odd, b.odd AS previous_odd, a.observed_at,
               f.home, f.away, f.league
        FROM odds_history a JOIN fixtures f ON f.fixture_key=a.fixture_key
        LEFT JOIN odds_history b ON b.id=(
          SELECT z.id FROM odds_history z
          WHERE z.fixture_key=a.fixture_key AND z.market=a.market
            AND z.option_name=a.option_name AND z.bookmaker=a.bookmaker AND z.id<a.id
          ORDER BY z.id DESC LIMIT 1)
        WHERE a.id=(SELECT MAX(z2.id) FROM odds_history z2
          WHERE z2.fixture_key=a.fixture_key AND z2.market=a.market
            AND z2.option_name=a.option_name AND z2.bookmaker=a.bookmaker)
          AND b.odd IS NOT NULL AND ABS(a.odd-b.odd)>0.0001
        ORDER BY a.observed_at DESC LIMIT 100
    """).fetchall()
    return [dict(row) for row in records]


def format_telegram_message(lines):
    clean = [str(line).strip() for line in (lines or []) if str(line).strip()]
    return "⚽ Futbol Analiz Merkezi — gözlenen sinyaller\n\n" + "\n".join(f"• {line}" for line in clean[:20]) + (
        "\n\nNot: Bunlar geçmiş veri hareketleridir, bahis tavsiyesi veya kazanma garantisi değildir."
    )
