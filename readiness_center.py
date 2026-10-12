"""Operational readiness, provider smoke tests and cross-source data quality checks."""
from datetime import datetime, timezone
import os
import json
import re
import unicodedata

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE = "https://api.5dollarfootballapi.com/v1"
SESSION = requests.Session()
RETRY = Retry(total=2, connect=2, read=1, status=2, backoff_factor=0.4,
              status_forcelist=(429, 500, 502, 503, 504),
              allowed_methods=frozenset({"GET"}), respect_retry_after_header=True)
ADAPTER = HTTPAdapter(max_retries=RETRY)
SESSION.mount("https://", ADAPTER)
SESSION.mount("http://", ADAPTER)


def _payload_list(payload):
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or payload.get("response") or []
    if isinstance(data, dict):
        for key in ("fixtures", "leagues", "data", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def smoke_test_5dollar(api_key):
    """Check provider reachability and response shape; do not claim coverage from HTTP 200 alone."""
    if not str(api_key or "").strip():
        return [
            {"provider": "5DollarFootballAPI /leagues", "ok": False, "detail": "API anahtarı tanımlı değil."},
            {"provider": "5DollarFootballAPI /fixtures", "ok": False, "detail": "API anahtarı tanımlı değil."},
        ]
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    checks = []
    for label, path, params in (
        ("5DollarFootballAPI /status", "/status", {}),
        ("5DollarFootballAPI /leagues", "/leagues", {"page": 1, "per_page": 1}),
        ("5DollarFootballAPI /fixtures", "/fixtures", {"status": "live", "per_page": 1}),
    ):
        try:
            response = SESSION.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=12)
            if response.status_code != 200:
                checks.append({"provider": label, "ok": False, "detail": f"HTTP {response.status_code}: {response.text[:120]}"})
                continue
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("success") == 0:
                error = (payload.get("error") or {}).get("message", "Yanıt başarı durumunu doğrulamadı.") if isinstance(payload, dict) else "JSON nesnesi bekleniyordu."
                checks.append({"provider": label, "ok": False, "detail": str(error)[:160]})
                continue
            rows = _payload_list(payload)
            checks.append({"provider": label, "ok": True, "detail": f"HTTP 200; yanıt biçimi geçerli; bu örnek istekte {len(rows)} kayıt."})
        except (requests.RequestException, ValueError, TypeError) as exc:
            checks.append({"provider": label, "ok": False, "detail": f"{type(exc).__name__}: {str(exc)[:140]}"})
    return checks


def save_provider_checks(db_connect, checks):
    conn = db_connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        for check in checks:
            conn.execute("""INSERT INTO provider_health (provider, ok, detail, checked_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET ok=excluded.ok, detail=excluded.detail, checked_at=excluded.checked_at""",
                (check["provider"], int(bool(check["ok"])), str(check["detail"])[:500], now))
        conn.commit()
    finally:
        conn.close()


def _norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"\b(fc|cf|sc|afc|club|the)\b", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def inspect_database(db_connect):
    """Summarize actual saved coverage and conservatively flag same-day cross-source score conflicts."""
    conn = db_connect()
    try:
        def count(sql, params=()):
            row = conn.execute(sql, params).fetchone()
            return int(row["n"] if row and row["n"] is not None else 0)
        fixtures = count("SELECT COUNT(*) AS n FROM fixtures")
        live = count("SELECT COUNT(*) AS n FROM fixtures WHERE UPPER(status) IN ('LIVE','1H','2H','HT','INPLAY','IN_PLAY')")
        completed = count("SELECT COUNT(*) AS n FROM fixtures WHERE finished=1")
        snapshots = count("SELECT COUNT(*) AS n FROM snapshots")
        odds_count = count("SELECT COUNT(*) AS n FROM odds_history WHERE odd > 1")
        inventory = count("SELECT COUNT(*) AS n FROM league_inventory")
        paper_settled = count("SELECT COUNT(*) AS n FROM paper_bets WHERE status='settled'")
        stale_cutoff_text = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 3600, timezone.utc).isoformat()
        stale_live = count("""SELECT COUNT(*) AS n FROM fixtures
            WHERE UPPER(status) IN ('LIVE','1H','2H','HT','INPLAY','IN_PLAY')
            AND (last_seen IS NULL OR last_seen < ?)""", (stale_cutoff_text,))
        finished_missing_score = count("""SELECT COUNT(*) AS n FROM fixtures
            WHERE finished=1 AND (home_goals IS NULL OR away_goals IS NULL)""")
        invalid_odds = count("SELECT COUNT(*) AS n FROM odds_history WHERE odd IS NULL OR odd <= 1")
        duplicate_odds = conn.execute("""SELECT COUNT(*) AS n FROM (
            SELECT fixture_key, market, option_name, bookmaker, stage, line
            FROM odds_history GROUP BY fixture_key, market, option_name, bookmaker, stage, line
            HAVING COUNT(*) > 1
        ) duplicate_groups""").fetchone()["n"]
        latest = conn.execute("SELECT MAX(last_seen) AS t FROM fixtures").fetchone()["t"]
        heartbeat = conn.execute("SELECT run_at, status, detail FROM collector_runs ORDER BY id DESC LIMIT 1").fetchone()
        sources = conn.execute("""SELECT source, COUNT(*) AS fixtures, MAX(last_seen) AS last_seen
            FROM fixtures GROUP BY source ORDER BY fixtures DESC""").fetchall()
        markets = conn.execute("""SELECT COALESCE(market, 'Pazar belirtilmemiş') AS market,
            COUNT(*) AS observations, COUNT(DISTINCT fixture_key) AS fixtures,
            COUNT(DISTINCT bookmaker) AS bookmakers, MAX(observed_at) AS latest
            FROM odds_history WHERE odd > 1 GROUP BY market ORDER BY observations DESC""").fetchall()
        fixture_rows = conn.execute("""SELECT fixture_key, source, match_date, league, home, away, status,
            home_goals, away_goals, last_seen FROM fixtures
            WHERE home IS NOT NULL AND away IS NOT NULL ORDER BY last_seen DESC LIMIT 3000""").fetchall()
        groups = {}
        for row in fixture_rows:
            day = str(row["match_date"] or "")[:10]
            home, away = _norm(row["home"]), _norm(row["away"])
            if not day or not home or not away:
                continue
            key = (day, tuple(sorted((home, away))))
            groups.setdefault(key, []).append(dict(row))
        conflicts = []
        for (day, teams), rows in groups.items():
            if len({r["source"] for r in rows}) < 2:
                continue
            scored = {(r["home_goals"], r["away_goals"]) if _norm(r["home"]) == teams[0] else (r["away_goals"], r["home_goals"])
                      for r in rows if r["home_goals"] is not None and r["away_goals"] is not None}
            if len(scored) > 1:
                conflicts.append({
                    "Tarih": day, "Maç": " / ".join(sorted({f'{r["home"]} - {r["away"]}' for r in rows})),
                    "Farklı skorlar": ", ".join(sorted({f'{a}-{b}' for a, b in scored})),
                    "Kaynaklar": ", ".join(sorted({str(r["source"]) for r in rows})),
                })
        return {
            "fixtures": fixtures, "live": live, "completed": completed, "snapshots": snapshots,
            "odds": odds_count, "leagues": inventory, "paper_settled": paper_settled,
            "stale_live": stale_live, "finished_missing_score": finished_missing_score,
            "invalid_odds": invalid_odds, "duplicate_odds_groups": int(duplicate_odds or 0),
            "latest_fixture_seen": latest, "collector_heartbeat": dict(heartbeat) if heartbeat else None,
            "sources": [dict(r) for r in sources],
            "markets": [dict(r) for r in markets], "conflicts": conflicts[:100],
        }
    finally:
        conn.close()


def render_readiness_center(st, db_connect, api_key):
    st.markdown("---")
    st.subheader("🧰 12 başlık için sistem hazırlık merkezi")
    st.caption("Bu panel gerçek kayıtlara ve isteğe bağlı bağlantı testine dayanır. Yeşil durum yalnızca kontrol edilen kısmın yanıt verdiğini gösterir; tüm ligleri veya tüm bahis pazarlarını garanti etmez.")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        try:
            database_url = str(st.secrets.get("DATABASE_URL", "")).strip()
        except Exception:
            database_url = ""
    if not database_url:
        st.warning("Kalıcı DATABASE_URL bulunamadı. Uygulama yerel SQLite kullanıyor olabilir; barındırma yeniden başlatıldığında geçmiş verilerin korunacağı garanti edilmez ve arka plan toplayıcısı kalıcı veritabanına yazamaz.")
    if not str(api_key or "").strip():
        st.warning("FIVE_DOLLAR_FOOTBALL_API_KEY tanımlı değil. Sağlayıcı canlı verileri, lig envanteri ve oran bağlantıları doğrulanamaz.")
    if st.button("🔎 API bağlantılarını şimdi test et", key="run_readiness_provider_checks"):
        with st.spinner("Sağlayıcı bağlantıları kontrol ediliyor..."):
            checks = smoke_test_5dollar(api_key)
            save_provider_checks(db_connect, checks)
            st.session_state["readiness_provider_checks"] = checks
    checks = st.session_state.get("readiness_provider_checks", [])
    conn = db_connect()
    try:
        stored = conn.execute("SELECT provider, ok, detail, checked_at FROM provider_health ORDER BY provider").fetchall()
        if stored:
            checks_by_name = {r["provider"]: dict(r) for r in stored}
            checks = [{"provider": name, "ok": bool(row["ok"]), "detail": row["detail"], "checked_at": row["checked_at"]}
                      for name, row in checks_by_name.items()]
    finally:
        conn.close()
    # Merge the app's own diagnostics from providers used during live-match loading.
    app_statuses = st.session_state.get("provider_statuses", {})
    check_names = {c.get("provider") for c in checks}
    display_checks = [{
        "Bağlantı": c["provider"], "Durum": "Yanıt verdi" if c["ok"] else "Hata / erişim yok",
        "Ayrıntı": c["detail"], "Kontrol (UTC)": c.get("checked_at", "Bu oturum")
    } for c in checks]
    for name, item in app_statuses.items():
        if name in check_names:
            continue
        configured = bool(item.get("configured"))
        ok = item.get("ok")
        if not configured and ok is None:
            state = "Anahtar gerekli"
        elif ok is True:
            state = "Yanıt verdi"
        elif ok is False:
            state = "Hata / kota"
        else:
            state = "Henüz test edilmedi"
        display_checks.append({
            "Bağlantı": name, "Durum": state,
            "Ayrıntı": item.get("detail", "Henüz test edilmedi"),
            "Kontrol (UTC)": item.get("checked_at", "—"),
        })
    if display_checks:
        st.dataframe(display_checks, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz bağlantı testi yapılmadı. Yukarıdaki düğme sağlayıcının lig ve canlı fikstür uç noktalarını örnek kayıtla kontrol eder.")

    try:
        metrics = inspect_database(db_connect)
    except Exception as exc:
        st.error(f"Veritabanı denetimi başarısız: {type(exc).__name__}: {str(exc)[:180]}")
        return
    cols = st.columns(4)
    cols[0].metric("Kaydedilmiş maç", metrics["fixtures"])
    cols[1].metric("Canlı durumlu kayıt", metrics["live"])
    cols[2].metric("Zaman damgalı gözlem", metrics["snapshots"])
    cols[3].metric("Geçerli oran kaydı", metrics["odds"])
    if metrics["latest_fixture_seen"]:
        st.caption(f'Son maç kaydı: {metrics["latest_fixture_seen"]}')
    else:
        st.caption("Henüz kalıcı maç kaydı yok.")
    heartbeat = metrics.get("collector_heartbeat")
    if heartbeat:
        st.caption(f'Collector son turu: {heartbeat["run_at"]} · durum: {heartbeat["status"]} · {heartbeat["detail"]}')
    else:
        st.caption("Bağımsız collector henüz bu veritabanına çalışma kaydı yazmamış.")

    with st.expander("Veri kalitesi göstergeleri", expanded=False):
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("1 saati aşan canlı kayıt", metrics["stale_live"])
        q2.metric("Skoru eksik tamamlanmış maç", metrics["finished_missing_score"])
        q3.metric("Geçersiz/boş oran kaydı", metrics["invalid_odds"])
        q4.metric("Tekrarlı oran grubu", metrics["duplicate_odds_groups"])
        st.caption("Tekrarlı oran grubu, aynı maç/pazar/seçenek/şirket/aşama/çizgi kombinasyonunun birden fazla kaydedilmesidir. Tekrarlar bazen gerçek zamanlı farklı gözlemlerden kaynaklanabileceği için otomatik silinmez.")

    with st.expander("Kaynaklara göre gerçek veri kapsamı", expanded=False):
        if metrics["sources"]:
            st.dataframe([{"Kaynak": r["source"], "Maç kaydı": r["fixtures"], "Son görülme": r["last_seen"]}
                          for r in metrics["sources"]], use_container_width=True, hide_index=True)
        else:
            st.info("Kaynak bazında kayıt yok.")
    with st.expander("Gerçek oran pazarı kapsamı", expanded=False):
        if metrics["markets"]:
            st.dataframe([{"Pazar": r["market"], "Oran gözlemi": r["observations"],
                           "Maç": r["fixtures"], "Şirket": r["bookmakers"], "Son gözlem": r["latest"]}
                          for r in metrics["markets"]], use_container_width=True, hide_index=True)
        else:
            st.info("Oran geçmişi boş. Oran kaydı bulunmadan pazar kapsamı veya kârlılık varsayılmaz.")
    with st.expander("Kaynaklar arası skor uyuşmazlıkları", expanded=bool(metrics["conflicts"])):
        if metrics["conflicts"]:
            st.warning(f'{len(metrics["conflicts"])} olası skor uyuşmazlığı bulundu. Takım adı benzerliği nedeniyle insan kontrolü gerekebilir.')
            st.dataframe(metrics["conflicts"], use_container_width=True, hide_index=True)
        else:
            st.success("Kaydedilmiş aynı gün / aynı takım eşleşmelerinde skor uyuşmazlığı bulunmadı. Bu, tüm kaynakların doğrulandığı anlamına gelmez.")

    live_api_ok = any(c.get("ok") and "/fixtures" in c.get("provider", "") for c in checks)
    league_api_ok = any(c.get("ok") and "/leagues" in c.get("provider", "") for c in checks)
    odds_ready = metrics["odds"] > 0
    snapshots_ready = metrics["snapshots"] > 1
    conflict_free = not metrics["conflicts"]
    readiness = [
        ("1. API ve gerçek veri bağlantısı", "Doğrulandı (örnek istek)" if live_api_ok and league_api_ok else "Bağlantı testi gerekli / başarısız"),
        ("2. Küresel lig ve fikstür kapsamı", f'{metrics["leagues"]} lig envanteri kaydı; sağlayıcı planıyla sınırlı' if metrics["leagues"] else "Lig taraması ve tarih fikstürü gerekli"),
        ("3. Kadro, sakatlık ve cezalar", "Maç ekranında bazı kaynaklar destekleniyor; bağımsız otomatik toplama doğrulanmadı"),
        ("4. Pazar bazlı tahmin modelleri", "Genel bahis pazarları için doğrulanmış modeller henüz yok"),
        ("5. Açılış / canlı / kapanış oran geçmişi", "Oran kaydı mevcut; tam açılış-kapanış kapsamı doğrulanmadı" if odds_ready else "Gerçek oran gözlemi gerekli"),
        ("6. Türkiye bahis şirketleri", "Nesine/Misli/Bilyoner/Oley/Tuttur otomatik oran erişimi doğrulanmadı"),
        ("7. Haber ve sosyal medya", "Google Haberler RSS başlıkları var; sosyal medya yorumları otomatik toplanmıyor"),
        ("8. Canlı baskı ve son dakika trendi", "Gözlem geçmişi mevcut" if snapshots_ready else "Yeterli canlı gözlem geçmişi gerekli"),
        ("9. Geriye dönük performans", f'{metrics["paper_settled"]} sonuçlanmış sanal bahis; model bazlı backtest ayrı doğrulanmalı'),
        ("10. Veri kalitesi ve kaynak uyuşmazlığı", "Olası skor farkları tespit ediliyor" if metrics["conflicts"] else "Kontrol çalıştı; uyuşmazlık bulunmadı"),
        ("11. Kalıcılık ve otomatik çalışma",
         (f'Collector son durumu: {metrics["collector_heartbeat"]["status"]} ({metrics["collector_heartbeat"]["run_at"]})'
          if metrics.get("collector_heartbeat") else "Collector heartbeat kaydı yok; PostgreSQL/Actions secrets kontrol edilmeli")),
        ("12. iPhone/mobil kullanım", "Streamlit arayüzü mobilde kullanılabilir; cihaz üzerinde kullanılabilirlik testi gerekli"),
    ]
    st.markdown("### 12 maddenin güncel durumu")
    st.dataframe([{"Özellik": name, "Gerçek durum": status} for name, status in readiness],
                 use_container_width=True, hide_index=True)
    st.caption("Kadro/sakatlık, sosyal medya, Türk bahis oranları ve tüm pazar modelleri; kaynak/anahtar ve lisans erişimi olmadan kod tek başına veri sağlayamaz.")
