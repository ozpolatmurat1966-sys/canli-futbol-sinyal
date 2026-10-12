"""Conservative market decision gates. Missing or unvalidated inputs always produce PASS."""
from math import isfinite


def assess_market(probability, odds, sample_count=0, data_age_seconds=None,
                  data_complete=False, min_samples=200, min_edge=0.05,
                  max_data_age_seconds=120):
    """Assess value only when a validated model probability and fresh complete data exist."""
    def num(value):
        try:
            result = float(value)
            return result if isfinite(result) else None
        except (TypeError, ValueError):
            return None

    p, price = num(probability), num(odds)
    try:
        samples = int(sample_count or 0)
    except (TypeError, ValueError):
        samples = 0
    if p is None or not 0 < p < 1:
        return {"decision": "PAS GEÇ", "reason": "Doğrulanmış model olasılığı yok."}
    if price is None or price <= 1:
        return {"decision": "PAS GEÇ", "reason": "Geçerli gerçek oran yok."}
    if samples < min_samples:
        return {"decision": "PAS GEÇ", "reason": f"Yetersiz geçmiş örnek: {samples}/{min_samples}."}
    if not data_complete:
        return {"decision": "PAS GEÇ", "reason": "Gerekli veri alanları eksik."}
    age = num(data_age_seconds)
    if age is None or age < 0 or age > max_data_age_seconds:
        return {"decision": "PAS GEÇ", "reason": "Veri güncel değil veya zaman damgası yok."}
    implied = 1.0 / price
    edge = p - implied
    ev = p * price - 1.0
    if edge < min_edge or ev <= 0:
        return {"decision": "PAS GEÇ", "reason": f"Değer eşiği karşılanmadı (olasılık farkı {edge:+.1%}, EV {ev:+.1%}).",
                "implied_probability": implied, "edge": edge, "expected_value": ev}
    return {"decision": "ADAY — garanti değil", "reason": "Tüm veri ve değer eşikleri karşılandı; bahis tavsiyesi değildir.",
            "implied_probability": implied, "edge": edge, "expected_value": ev}
