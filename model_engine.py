"""Historical probability calibration with strict sample-size and chronology guards."""
from math import isfinite


def _safe_probability(value):
    try:
        value = float(value)
        return min(1.0, max(0.0, value)) if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def calibrate_probability(rows, target, probability, min_samples=50, neighbors=30):
    """Return (calibrated_probability, sample_count); None until enough evaluated history exists."""
    probability = _safe_probability(probability)
    if probability is None:
        return None, 0
    usable = []
    for row in rows or []:
        get = row.get if hasattr(row, "get") else lambda k, d=None: row[k] if k in row.keys() else d
        if get("target") != target or get("evaluated_result") not in (0, 1, False, True):
            continue
        p = _safe_probability(get("probability"))
        if p is None:
            continue
        usable.append((abs(p - probability), p, int(get("evaluated_result"))))
    if len(usable) < min_samples:
        return None, len(usable)
    usable.sort(key=lambda item: item[0])
    chosen = usable[:min(neighbors, len(usable))]
    # Beta(1,1) smoothing avoids unjustified 0% or 100% estimates in a local neighborhood.
    successes = sum(item[2] for item in chosen)
    return (successes + 1.0) / (len(chosen) + 2.0), len(chosen)


def evaluate_calibration(rows, target, min_samples=50, test_fraction=0.30):
    """Chronological holdout comparison; calibration is evaluated only on later observations."""
    usable = []
    for row in rows or []:
        get = row.get if hasattr(row, "get") else lambda k, d=None: row[k] if k in row.keys() else d
        if get("target") != target or get("evaluated_result") not in (0, 1, False, True):
            continue
        p = _safe_probability(get("probability"))
        if p is None:
            continue
        usable.append((str(get("created_at") or ""), p, int(get("evaluated_result"))))
    usable.sort(key=lambda item: item[0])
    if len(usable) < min_samples:
        return {"ready": False, "samples": len(usable), "reason": f"En az {min_samples} değerlendirilmiş geçmiş örnek gerekli."}
    split = int(len(usable) * (1.0 - test_fraction))
    train, test = usable[:split], usable[split:]
    if len(train) < 30 or len(test) < 10:
        return {"ready": False, "samples": len(usable), "reason": "Zaman sıralı eğitim/test ayrımı için yeterli örnek yok."}
    brier_raw = sum((p - y) ** 2 for _, p, y in test) / len(test)
    brier_cal = []
    for _, p, y in test:
        nearest = sorted(train, key=lambda item: abs(item[1] - p))[:min(30, len(train))]
        pred = (sum(item[2] for item in nearest) + 1.0) / (len(nearest) + 2.0)
        brier_cal.append((pred - y) ** 2)
    return {
        "ready": True, "samples": len(usable), "train_samples": len(train), "test_samples": len(test),
        "brier_raw": brier_raw, "brier_calibrated": sum(brier_cal) / len(brier_cal),
        "calibrated_better": sum(brier_cal) / len(brier_cal) < brier_raw,
    }
