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
