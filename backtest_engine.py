"""Transparent metrics for settled paper bets; never infer missing odds or outcomes."""


def evaluate_paper_bets(rows):
    usable = []
    for row in rows or []:
        get = row.get if hasattr(row, "get") else lambda k, d=None: row[k] if k in row.keys() else d
        try:
            odds = float(get("odds"))
            stake = float(get("stake", 0))
            result = int(get("settled_result"))
        except (TypeError, ValueError):
            continue
        if odds <= 1 or stake <= 0 or result not in (0, 1):
            continue
        usable.append((odds, stake, result))
    if not usable:
        return {"ready": False, "bets": 0, "reason": "Sonuçlanmış ve oranı kaydedilmiş sanal bahis yok."}
    stake_total = sum(stake for _, stake, _ in usable)
    profit = sum((stake * (odds - 1)) if result == 1 else -stake for odds, stake, result in usable)
    wins = sum(result for _, _, result in usable)
    peak, equity, max_drawdown = 0.0, 0.0, 0.0
    for odds, stake, result in usable:
        equity += (stake * (odds - 1)) if result == 1 else -stake
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "ready": True, "bets": len(usable), "wins": wins, "win_rate": wins / len(usable),
        "stake_total": stake_total, "profit": profit, "roi": profit / stake_total,
        "max_drawdown": max_drawdown,
    }
