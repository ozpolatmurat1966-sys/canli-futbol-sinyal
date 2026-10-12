"""Additional dashboard tools: league inventory, conservative decision gates and backtest metrics."""
from datetime import datetime, timezone, timedelta
import requests

from backtest_engine import evaluate_paper_bets
from decision_engine import assess_market

API_BASE = "https://api.5dollarfootballapi.com/v1"


def fetch_leagues(api_key, max_pages=10):
    """Fetch provider-listed leagues with bounded pagination and no secret exposure."""
    if not str(api_key or "").strip():
        return [], "FIVE_DOLLAR_FOOTBALL_API_KEY tanımlı değil."
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    rows, seen = [], set()
    try:
        for page in range(1, max(1, min(int(max_pages), 10)) + 1):
            response = requests.get(f"{API_BASE}/leagues",
                                    params={"page": page, "per_page": 100},
                                    headers=headers, timeout=15)
            if response.status_code != 200:
                return rows, f"Lig listesi HTTP {response.status_code}: {response.text[:140]}"
            payload = response.json()
            if payload.get("success") == 0:
                return rows, str((payload.get("error") or {}).get("message") or "Sağlayıcı API hatası")
            data = payload.get("data") or payload.get("response") or []
            if isinstance(data, dict):
                data = data.get("leagues") or data.get("data") or []
            if not isinstance(data, list):
                return rows, "Lig listesi beklenmeyen biçimde döndü."
            for league in data:
                if not isinstance(league, dict):
                    continue
                lid = league.get("id")
                key = str(lid if lid is not None else (league.get("name"), league.get("country")))
                if key in seen:
                    continue
                seen.add(key)
                country = league.get("country") or {}
                rows.append({
                    "provider_league_id": str(lid or ""),
                    "name": str(league.get("name") or league.get("short_name") or "Lig adı yok"),
                    "country": str(country.get("name") if isinstance(country, dict) else country or "Ülke belirtilmemiş"),
                    "last_fixture_utc": league.get("last_fixture_utc") or "",
                    "is_popular": bool(league.get("is_popular", False)),
                })
            pagination = payload.get("pagination") or {}
            if not pagination.get("has_more", False):
                break
        return rows, None
    except requests.RequestException as exc:
        return rows, f"Lig listesi bağlantı hatası: {str(exc)[:140]}"
    except (ValueError, TypeError) as exc:
        return rows, f"Lig listesi okunamadı: {str(exc)[:140]}"


def render_advanced_features(st, db_connect, api_key):
    st.markdown("---")
    st.subheader("🌍 Küresel lig envanteri")
    st.caption("Bu tarama, 5DollarFootballAPI hesabının listelediği ligleri kaydeder; tüm dünya liglerinde her maç veya bahis pazarının bulunduğu anlamına gelmez.")
    conn = db_connect()
    try:
        inventory_count = conn.execute("SELECT COUNT(*) AS n FROM league_inventory").fetchone()["n"]
        latest = conn.execute("SELECT MAX(observed_at) AS t FROM league_inventory").fetchone()["t"]
        if st.button("🌐 Sağlayıcının lig listesini tara / güncelle", key="scan_global_leagues",
                     disabled=not bool(str(api_key or "").strip())):
            with st.spinner("Lig envanteri alınıyor..."):
                leagues, err = fetch_leagues(api_key)
                if err:
                    st.error(err)
                elif leagues:
                    observed = datetime.now(timezone.utc).isoformat()
                    for league in leagues:
                        conn.execute("""INSERT INTO league_inventory
                            (provider, provider_league_id, name, country, last_fixture_utc, is_popular, observed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(provider, provider_league_id) DO UPDATE SET
                            name=excluded.name, country=excluded.country, last_fixture_utc=excluded.last_fixture_utc,
                            is_popular=excluded.is_popular, observed_at=excluded.observed_at""",
                            ("5DollarFootballAPI", league["provider_league_id"], league["name"], league["country"],
                             league["last_fixture_utc"], int(league["is_popular"]), observed))
                    conn.commit()
                    st.success(f"{len(leagues)} lig kaydı güncellendi.")
                    inventory_count = conn.execute("SELECT COUNT(*) AS n FROM league_inventory").fetchone()["n"]
                    latest = conn.execute("SELECT MAX(observed_at) AS t FROM league_inventory").fetchone()["t"]
                else:
                    st.warning("Sağlayıcı lig listesi boş döndü; kayıt uydurulmadı.")
        st.metric("Kayıtlı lig", inventory_count)
        if latest:
            st.caption(f"Son tarama: {latest} (UTC)")
        league_rows = conn.execute("""SELECT provider_league_id, name, country, last_fixture_utc, is_popular, observed_at
            FROM league_inventory ORDER BY is_popular DESC, country, name LIMIT 1000""").fetchall()
        if league_rows:
            st.dataframe([{
                "Sağlayıcı ID": r["provider_league_id"], "Lig": r["name"], "Ülke": r["country"],
                "Son maç (UTC)": r["last_fixture_utc"] or "Veri yok",
                "Popüler": "Evet" if r["is_popular"] else "Hayır",
            } for r in league_rows], use_container_width=True, hide_index=True)
        elif not api_key:
            st.info("Lig envanteri için Streamlit Secrets'e FIVE_DOLLAR_FOOTBALL_API_KEY eklenmeli.")
        else:
            st.info("Henüz lig envanteri yok. Yukarıdaki tarama düğmesini kullan.")
    finally:
        conn.close()

    st.markdown("### 🧭 Oyna / Pas geç karar kapısı")
    st.caption("Karar kapısı model olasılığı, geçmiş örnek sayısı, gerçek oran, veri tamlığı ve güncellik arar. Mevcut genel maç analizi, tüm pazarlar için doğrulanmış olasılık modeli değildir.")
    gate = assess_market(probability=None, odds=None, sample_count=0,
                         data_age_seconds=None, data_complete=False)
    st.warning(f'{gate["decision"]}: {gate["reason"]} Şu anda bu kapı üzerinden otomatik “Oyna” sinyali üretilmez.')
    st.dataframe([
        {"Pazar grubu": "Maç sonucu (1X2)", "Gerçek oran geçmişi": "Kayıt varsa", "Doğrulanmış pazar modeli": "Henüz yok", "Karar": "Pas geç"},
        {"Pazar grubu": "Gol alt/üst ve KG var", "Gerçek oran geçmişi": "Kayıt varsa", "Doğrulanmış pazar modeli": "Henüz yok", "Karar": "Pas geç"},
        {"Pazar grubu": "Korner / kart", "Gerçek oran geçmişi": "Sağlayıcı döndürürse", "Doğrulanmış pazar modeli": "Henüz yok", "Karar": "Pas geç"},
        {"Pazar grubu": "Oyuncu bahisleri", "Gerçek oran geçmişi": "Sağlayıcı döndürürse", "Doğrulanmış pazar modeli": "Henüz yok", "Karar": "Pas geç"},
    ], use_container_width=True, hide_index=True)

    st.markdown("### 🧾 Sanal kupon kayıt defteri")
    st.caption("Bu alan yalnızca senin manuel kaydettiğin sanal seçimleri izler; sistem bahis önerisi üretmez ve gerçek para hareketi yapmaz.")
    conn = db_connect()
    try:
        with st.form("paper_bet_add_form"):
            paper_match = st.text_input("Maç / referans", placeholder="Örn. Takım A - Takım B")
            paper_market = st.selectbox("Pazar", ["1X2", "Gol alt/üst", "Korner", "Kart", "Oyuncu bahisleri", "Diğer"])
            paper_selection = st.text_input("Seçim", placeholder="Örn. Ev sahibi veya 2.5 üst")
            paper_odds = st.number_input("Gözlenen oran", min_value=1.01, max_value=1000.0, value=2.0, step=0.05)
            paper_stake = st.number_input("Sanal birim", min_value=0.1, max_value=100000.0, value=10.0, step=1.0)
            add_paper = st.form_submit_button("Sanal seçimi kaydet")
        if add_paper:
            if not paper_match.strip() or not paper_selection.strip():
                st.error("Maç ve seçim alanlarını doldur.")
            else:
                conn.execute("""INSERT INTO paper_bets
                    (fixture_key, market, selection, odds, stake, placed_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'open')""",
                    (paper_match.strip(), paper_market, paper_selection.strip(), float(paper_odds),
                     float(paper_stake), datetime.now(timezone.utc).isoformat()))
                conn.commit()
                st.success("Sanal seçim kaydedildi. Sonucunu aşağıdan işaretleyebilirsin.")
        open_bets = conn.execute("SELECT id, fixture_key, market, selection, odds, stake, placed_at FROM paper_bets WHERE status='open' ORDER BY id DESC LIMIT 100").fetchall()
        if open_bets:
            st.dataframe([{
                "ID": r["id"], "Maç": r["fixture_key"], "Pazar": r["market"],
                "Seçim": r["selection"], "Oran": r["odds"], "Sanal birim": r["stake"],
                "Kayıt zamanı": r["placed_at"]
            } for r in open_bets], use_container_width=True, hide_index=True)
            with st.form("paper_bet_settle_form"):
                selected_id = st.selectbox("Sonuçlandırılacak sanal seçim", [int(r["id"]) for r in open_bets],
                                           format_func=lambda value: next(
                                               f'#{r["id"]} {r["fixture_key"]} · {r["selection"]} @ {r["odds"]}'
                                               for r in open_bets if int(r["id"]) == value))
                settled_as = st.radio("Sonuç", ["Kazandı", "Kaybetti", "İptal"], horizontal=True)
                settle_paper = st.form_submit_button("Sanal seçimi sonuçlandır")
            if settle_paper:
                if settled_as == "İptal":
                    conn.execute("UPDATE paper_bets SET status='void', settled_at=? WHERE id=? AND status='open'",
                                 (datetime.now(timezone.utc).isoformat(), selected_id))
                else:
                    conn.execute("UPDATE paper_bets SET status='settled', settled_result=?, settled_at=? WHERE id=? AND status='open'",
                                 (1 if settled_as == "Kazandı" else 0, datetime.now(timezone.utc).isoformat(), selected_id))
                conn.commit()
                st.success("Sanal seçim sonucu kaydedildi.")
        else:
            st.info("Açık sanal seçim yok. Gerçek bahis değil, performans takibi için kayıt ekleyebilirsin.")
    finally:
        conn.close()

    st.markdown("### 📊 Sanal bahis performansı: ROI / düşüş")
    conn = db_connect()
    try:
        rows = conn.execute("SELECT odds, stake, settled_result FROM paper_bets WHERE status='settled' ORDER BY settled_at, id").fetchall()
        metrics = evaluate_paper_bets([dict(r) for r in rows])
        if metrics["ready"]:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sanal bahis", metrics["bets"])
            c2.metric("ROI", f'{metrics["roi"]:+.1%}')
            c3.metric("Net kâr/zarar", f'{metrics["profit"]:+.2f}')
            c4.metric("Maks. düşüş", f'{metrics["max_drawdown"]:.2f}')
            st.caption(f'Kazanma oranı: {metrics["win_rate"]:.1%}. Bu yalnızca kaydedilmiş sanal bahislerin geçmiş sonucudur; gerçek para performansı değildir.')
        else:
            st.info("ROI henüz hesaplanamaz: sistemde sonuçlanmış sanal bahis kaydı yok. Eksik oran veya sonuçlardan kârlılık tahmini üretilmez.")
    finally:
        conn.close()

    st.markdown("### 🧪 Pazar bazlı model ve veri hazırlığı")
    conn = db_connect()
    try:
        rows = conn.execute("""SELECT market, COUNT(*) AS odds_rows, COUNT(DISTINCT fixture_key) AS fixtures,
            COUNT(DISTINCT bookmaker) AS bookmakers FROM odds_history GROUP BY market ORDER BY odds_rows DESC""").fetchall()
        observed = {str(r["market"]).lower(): dict(r) for r in rows}
        groups = [
            ("1X2 / maç sonucu", ("1x2", "match winner", "maç sonucu")),
            ("Gol alt/üst", ("goal", "gol", "goalline")),
            ("Korner", ("corner", "korner")),
            ("Kart", ("card", "kart")),
            ("Oyuncu bahisleri", ("player", "oyuncu")),
        ]
        readiness = []
        for label, terms in groups:
            matched = [v for k, v in observed.items() if any(term in k for term in terms)]
            readiness.append({
                "Pazar": label,
                "Oran gözlemi": sum(x["odds_rows"] for x in matched),
                "Maç sayısı": len({x["market"] for x in matched}),
                "Şirket sayısı": max([x["bookmakers"] for x in matched], default=0),
                "Model durumu": "Veri birikimi / doğrulama gerekli",
            })
        st.dataframe(readiness, use_container_width=True, hide_index=True)
        st.caption("Bir pazarın oranının bulunması, o pazar için modelin eğitildiği veya doğrulandığı anlamına gelmez.")
    finally:
        conn.close()
