import streamlit as st
import requests
from datetime import date
import math

st.set_page_config(page_title="Futbol Analiz Merkezi", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"

STAT_TR = {
    "Shots on Goal": "İsabetli Şut", "Shots off Goal": "İsabetsiz Şut",
    "Total Shots": "Toplam Şut", "Blocked Shots": "Engellenen Şut",
    "Shots insidebox": "Ceza Sahası İçinden Şut", "Shots inside box": "Ceza Sahası İçinden Şut",
    "Shots outsidebox": "Ceza Sahası Dışından Şut", "Shots outside box": "Ceza Sahası Dışından Şut",
    "Fouls": "Faul", "Corner Kicks": "Korner", "Offsides": "Ofsayt",
    "Ball Possession": "Topla Oynama", "Yellow Cards": "Sarı Kart",
    "Red Cards": "Kırmızı Kart", "Goalkeeper Saves": "Kaleci Kurtarışı",
    "Total passes": "Toplam Pas", "Passes accurate": "İsabetli Pas",
    "Passes %": "Pas İsabeti", "Expected Goals": "Beklenen Gol (xG)",
    "expected_goals": "Beklenen Gol (xG)", "Throw-ins": "Taç", "Tackles": "Müdahale",
    "Interceptions": "Araya Girme", "Hit Woodwork": "Direkten Dönen Şut",
    "Duels Won": "Kazanılan İkili Mücadele", "Total duels": "Toplam İkili Mücadele",
}
STATUS_TR = {
    "First Half": "İlk Yarı", "Halftime": "Devre Arası", "Second Half": "İkinci Yarı",
    "Match Finished": "Maç Bitti", "Not Started": "Başlamadı", "Extra Time": "Uzatmalar",
    "Penalty": "Penaltılar", "Postponed": "Ertelendi", "Cancelled": "İptal",
    "Match Suspended": "Durduruldu", "Live": "Canlı", "In Progress": "Devam Ediyor",
    "1st Half": "İlk Yarı", "2nd Half": "İkinci Yarı", "BT": "Devre Arası", "FT": "Maç Bitti",
    "NS": "Başlamadı", "PST": "Ertelendi", "CANC": "İptal", "SUSP": "Durduruldu",
}
MARKET_TR = {
    "Match Winner": "Maç Sonucu (1X2)", "Home/Away": "Ev Sahibi / Deplasman",
    "Second Half Winner": "İkinci Yarı Sonucu", "Goals Over/Under": "Toplam Gol Alt/Üst",
    "Goals Over/Under First Half": "İlk Yarı Gol Alt/Üst", "Both Teams Score": "Karşılıklı Gol",
    "Asian Handicap": "Asya Handikap", "Corners Over Under": "Korner Alt/Üst",
    "Exact Score": "Doğru Skor", "Double Chance": "Çifte Şans",
    "Draw No Bet": "Beraberlikte İade", "Odd/Even": "Tek / Çift Gol",
    "Cards Over/Under": "Kart Alt/Üst", "Total": "Toplam", "Asian Handicap (2nd Half)": "Asya Handikap (İkinci Yarı)",
    "Asian Handicap (1st Half)": "Asya Handikap (İlk Yarı)", "Team Total": "Takım Gol Toplamı",
    "Goals Over/Under (2nd Half)": "İkinci Yarı Gol Alt/Üst",
    "Corners Over Under": "Korner Alt/Üst", "Player Shots": "Oyuncu Şutları",
}
OPTION_TR = {
    "Home": "Ev Sahibi (1)", "Draw": "Beraberlik (X)", "Away": "Deplasman (2)",
    "Yes": "Evet", "No": "Hayır", "Over": "Üst", "Under": "Alt",
    "Home/Draw": "1X", "Draw/Away": "X2", "Home/Away": "12",
    "1st Half": "İlk Yarı", "2nd Half": "İkinci Yarı", "Home +0": "Ev Sahibi +0", "Away +0": "Deplasman +0",
    "Home -0.5": "Ev Sahibi -0,5", "Away -0.5": "Deplasman -0,5",
}

# Sağlayıcı pazar adlarını, ek açıklamalar (ör. "(2nd Half)") içerse bile Türkçeleştir.
def translate_market(value):
    raw = str(value or "Pazar")
    replacements = [
        ("Asian Handicap", "Asya Handikap"), ("Match Winner", "Maç Sonucu (1X2)"),
        ("Home/Away", "Ev Sahibi / Deplasman"), ("Second Half Winner", "İkinci Yarı Sonucu"),
        ("First Half Winner", "İlk Yarı Sonucu"), ("Goals Over/Under", "Gol Alt/Üst"),
        ("Both Teams Score", "Karşılıklı Gol"), ("Double Chance", "Çifte Şans"),
        ("Draw No Bet", "Beraberlikte İade"), ("Exact Score", "Doğru Skor"),
        ("Corners Over Under", "Korner Alt/Üst"), ("Cards Over/Under", "Kart Alt/Üst"),
        ("Over/Under", "Alt/Üst"), ("Odd/Even", "Tek/Çift"),
        ("Total Goals", "Toplam Gol"), ("1st Half", "İlk Yarı"), ("2nd Half", "İkinci Yarı"),
        ("Half Time", "Devre Arası"), ("Full Time", "Maç Sonu"),
    ]
    for en, tr in replacements:
        raw = raw.replace(en, tr)
    raw = raw.replace("Corners", "Korner").replace("Cards", "Kart")
    raw = raw.replace("Goals", "Goller").replace("Goal", "Gol")
    raw = raw.replace("Player", "Oyuncu").replace("Shots", "Şut")
    raw = raw.replace(" (2nd Half)", " (İkinci Yarı)").replace(" (1st Half)", " (İlk Yarı)")
    raw = raw.replace(" (Second Half)", " (İkinci Yarı)").replace(" (First Half)", " (İlk Yarı)")
    return raw

def translate_option(value):
    raw = str(value or "—")
    exact = OPTION_TR.get(raw)
    if exact:
        return exact
    raw = raw.replace("Home", "Ev Sahibi").replace("Away", "Deplasman")
    raw = raw.replace("Draw", "Beraberlik").replace("Over", "Üst").replace("Under", "Alt")
    raw = raw.replace("Yes", "Evet").replace("No", "Hayır")
    raw = raw.replace("1st Half", "İlk Yarı").replace("2nd Half", "İkinci Yarı")
    return raw

def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

APP_PASSWORD = str(secret("APP_PASSWORD", "")).strip()
if APP_PASSWORD and not st.session_state.get("authenticated", False):
    st.title("⚽ Futbol Analiz Merkezi")
    pw = st.text_input("Uygulama şifresi", type="password")
    if st.button("Giriş yap"):
        if pw == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Şifre yanlış.")
    st.stop()

API_KEY = str(secret("API_FOOTBALL_KEY", "")).strip()
FOOTBALL_DATA_TOKEN = str(secret("FOOTBALL_DATA_TOKEN", "")).strip()
st.title("⚽ Futbol Analiz Merkezi")
st.caption("Canlı maçlar • Fikstür • İstatistikler • Oranlar • Veri temelli değerlendirme")
st.warning("Bu uygulama otomatik bahis oynamaz ve kazancı garanti etmez. Yalnızca veri temelli değerlendirme sunar. Veriler eksikse doğru karar 'Pas geç' olabilir.")

if not API_KEY:
    st.error("API anahtarı bulunamadı. Streamlit uygulama ayarlarında Secrets bölümüne API_FOOTBALL_KEY ve gerekiyorsa APP_PASSWORD ekleyin.")
    st.code('API_FOOTBALL_KEY = "API_ANAHTARINIZ"\nAPP_PASSWORD = "KENDI_SIFRENIZ"')
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def api_get(endpoint, params=None):
    """Cache API responses briefly so Streamlit reruns do not waste free calls."""
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}",
                         headers={"x-apisports-key": API_KEY},
                         params=params or {}, timeout=20)
        remaining = r.headers.get("x-ratelimit-requests-remaining")
        limit = r.headers.get("x-ratelimit-requests-limit")
        quota_note = f" (günlük kalan istek: {remaining}/{limit})" if remaining and limit else ""
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}{quota_note}: {r.text[:300]}", None
        payload = r.json()
        if payload.get("errors"):
            return None, f"API hatası{quota_note}: {payload['errors']}", payload
        return payload.get("response", []), None, payload
    except requests.Timeout:
        return None, "İstek zaman aşımına uğradı.", None
    except (requests.RequestException, ValueError) as e:
        return None, f"Bağlantı hatası: {e}", None

@st.cache_data(ttl=300, show_spinner=False)
def football_data_get(path, params=None):
    """Optional second source: football-data.org. Its free tier is mainly fixtures/results/tables, not detailed live stats or odds."""
    if not FOOTBALL_DATA_TOKEN:
        return None, "İkinci kaynak bağlı değil. football-data.org token'ını Streamlit Secrets bölümüne FOOTBALL_DATA_TOKEN adıyla ekleyebilirsin."
    try:
        response = requests.get(
            f"https://api.football-data.org/v4/{path.lstrip('/')}",
            headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN},
            params=params or {}, timeout=20
        )
        if response.status_code != 200:
            return None, f"İkinci kaynak HTTP {response.status_code}: {response.text[:250]}"
        payload = response.json()
        return payload, None
    except (requests.RequestException, ValueError) as exc:
        return None, f"İkinci kaynak bağlantı hatası: {exc}"

def num(value):
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").replace(",", "."))
    except (ValueError, TypeError):
        return None

def stat_value(rows, names):
    for row in rows:
        if row.get("type") in names:
            return num(row.get("value"))
    return None

def tr_status(status):
    return STATUS_TR.get(status or "", status or "Bilinmiyor")

def show_stats(fixture_id, match):
    data, err, _ = api_get("fixtures/statistics", {"fixture": fixture_id})
    if err:
        st.error(f"İstatistik isteği başarısız: {err}")
        return None
    if not data or len(data) < 2:
        st.warning("İstatistik isteği gönderildi ancak API kullanılabilir istatistik döndürmedi. Bu durum genellikle maç/lig kapsamı, maçın durumu veya henüz yayımlanmamış veriden kaynaklanır. Aynı maçın oranlarının gelmesi, istatistiklerin de mevcut olduğu anlamına gelmez.")
        st.caption("Kontrol: API-Football panelindeki günlük istek hakkını ve ilgili ligin Coverage bölümünü kontrol edin. Uygulama eksik istatistiği tahmin ederek doldurmaz.")
        return None

    teams = match.get("teams", {})
    home_name = teams.get("home", {}).get("name", data[0].get("team", {}).get("name", "Ev sahibi"))
    away_name = teams.get("away", {}).get("name", data[1].get("team", {}).get("name", "Deplasman"))
    rows_for_table = []
    for team in data:
        for item in team.get("statistics", []):
            rows_for_table.append({
                "İstatistik": STAT_TR.get(item.get("type", ""), item.get("type", "Diğer")),
                team.get("team", {}).get("name", "Takım"): item.get("value") if item.get("value") is not None else "—"
            })
    if rows_for_table:
        st.subheader("Maç istatistikleri")
        st.dataframe(rows_for_table, use_container_width=True, hide_index=True)

    return {
        "home_name": home_name, "away_name": away_name,
        "home_rows": data[0].get("statistics", []),
        "away_rows": data[1].get("statistics", []),
    }

def show_lineups(fixture_id):
    data, err, _ = api_get("fixtures/lineups", {"fixture": fixture_id})
    if err:
        st.error(f"Kadro isteği başarısız: {err}")
        return
    if not data:
        st.warning("Kadro isteği gönderildi ancak API kadro döndürmedi. Kadrolar çoğunlukla maçtan yaklaşık 20–40 dakika önce gelir; bazı liglerde bu veri hiç sunulmayabilir.")
        st.caption("Bu durumda uygulama kadro uydurmaz. İlgili maçın lig kapsamı ve API günlük limitini kontrol edin.")
        return
    st.subheader("Kadro bilgileri")
    cols = st.columns(min(2, len(data)))
    for i, team in enumerate(data):
        with cols[i % len(cols)]:
            st.markdown(f"**{team.get('team', {}).get('name', 'Takım')}**")
            st.write("Diziliş:", team.get("formation") or "Bilinmiyor")
            starters = [p.get("player", {}).get("name", "Oyuncu") for p in team.get("startXI", [])]
            subs = [p.get("player", {}).get("name", "Oyuncu") for p in team.get("substitutes", [])]
            if starters: st.write("**İlk 11:** " + ", ".join(starters))
            if subs: st.write("**Yedekler:** " + ", ".join(subs))

def show_odds(fixture_id):
    data, err, _ = api_get("odds", {"fixture": fixture_id})
    if err:
        st.error(f'Oran isteği başarısız: {err}')
        return []
    if not data:
        st.info("Bu maç için oran bulunamadı. Ücretsiz API her maçın ve pazarın oranını sağlamayabilir.")
        return []
    all_rows = []
    for item in data:
        for bookmaker in item.get("bookmakers", []):
            st.markdown(f"**Oran sağlayıcısı: {bookmaker.get('name', 'Bilinmiyor')}**")
            for bet in bookmaker.get("bets", []):
                market_name = bet.get("name", "Pazar")
                market_tr = translate_market(MARKET_TR.get(market_name, market_name))
                rows = []
                for option in bet.get("values", []):
                    odd = num(option.get("odd"))
                    implied = 100 / odd if odd and odd > 0 else None
                    raw_option = option.get("value", "—")
                    translated_option = translate_option(raw_option)
                    row = {
                        "Pazar": market_tr, "Seçenek": translated_option,
                        "Oran": option.get("odd", "—"),
                        "Oranın ham olasılığı (%)": round(implied, 1) if implied is not None else "—",
                        "_odd": odd, "_market": market_tr, "_option": translated_option,
                        "_bookmaker": bookmaker.get("name", "Bilinmiyor"),
                    }
                    rows.append(row)
                    all_rows.append(row)
                if rows:
                    with st.expander(market_tr):
                        st.dataframe([{k:v for k,v in row.items() if not k.startswith("_")} for row in rows],
                                     use_container_width=True, hide_index=True)
    return all_rows

def analyze_match(match, stats, odds_rows):
    st.subheader("🤖 Otomatik maç değerlendirmesi")
    goals = match.get("goals", {})
    status = match.get("fixture", {}).get("status", {})
    elapsed = status.get("elapsed")
    home_goals, away_goals = goals.get("home"), goals.get("away")
    hr, ar = [], []
    metrics = []
    h_on = a_on = h_sh = a_sh = h_cor = a_cor = h_pos = a_pos = h_xg = a_xg = None
    if not stats:
        st.warning("Bu maçta istatistik verisi API tarafından döndürülmedi. Aşağıda skor, dakika ve mevcut oranlar ayrıca incelenecek; istatistik varmış gibi varsayım yapılmayacak.")
    else:
        hr, ar = stats["home_rows"], stats["away_rows"]
        h_on, a_on = stat_value(hr, ["Shots on Goal"]), stat_value(ar, ["Shots on Goal"])
        h_sh, a_sh = stat_value(hr, ["Total Shots"]), stat_value(ar, ["Total Shots"])
        h_cor, a_cor = stat_value(hr, ["Corner Kicks"]), stat_value(ar, ["Corner Kicks"])
        h_pos, a_pos = stat_value(hr, ["Ball Possession"]), stat_value(ar, ["Ball Possession"])
        h_xg, a_xg = stat_value(hr, ["Expected Goals", "expected_goals"]), stat_value(ar, ["Expected Goals", "expected_goals"])
        if h_on is not None and a_on is not None: metrics.append(("İsabetli şut", h_on, a_on))
        if h_sh is not None and a_sh is not None: metrics.append(("Toplam şut", h_sh, a_sh))
        if h_cor is not None and a_cor is not None: metrics.append(("Korner", h_cor, a_cor))
        if h_pos is not None and a_pos is not None: metrics.append(("Topla oynama (%)", h_pos, a_pos))
        if h_xg is not None and a_xg is not None: metrics.append(("Beklenen gol (xG)", h_xg, a_xg))
    if metrics and stats:
        st.dataframe([{"Gösterge": name, stats["home_name"]: hv, stats["away_name"]: av}
                      for name, hv, av in metrics], use_container_width=True, hide_index=True)

    notes = []
    if stats and h_on is not None and a_on is not None:
        if h_on + a_on >= 5: notes.append(f"İki takım toplam {int(h_on+a_on)} isabetli şuta ulaştı.")
        if abs(h_on-a_on) >= 3: notes.append(f"İsabetli şut üstünlüğü: {stats['home_name'] if h_on>a_on else stats['away_name']}.")
    if stats and h_sh is not None and a_sh is not None and h_sh+a_sh >= 14:
        notes.append(f"Toplam şut sayısı yüksek ({int(h_sh+a_sh)}).")
    if stats and h_cor is not None and a_cor is not None and h_cor+a_cor >= 7:
        notes.append(f"Toplam korner {int(h_cor+a_cor)}; korner pazarını değerlendirirken kalan süre ve skor da gerekir.")
    if stats and h_xg is not None and a_xg is not None:
        notes.append(f"xG toplamı {h_xg+a_xg:.2f}. Bu değer yalnızca sağlayıcı verisi varsa gösterilir.")
    if elapsed is not None:
        notes.append(f"Maç dakikası: {elapsed}'. Son 5/10/15 dakika ayrıntısı API tarafından ayrı olay zaman serisi olarak sunulmadıkça hesaplanamaz.")
    if elapsed is not None:
        st.write(f"**Mevcut skor:** {home_goals if home_goals is not None else '—'} - {away_goals if away_goals is not None else '—'} | **Dakika:** {elapsed}'")
    if notes:
        for n in notes: st.write("• " + n)
    elif stats:
        st.info("İstatistiklerden güçlü bir sinyal çıkmadı.")

    # Conservative recommendation: do not claim a proven predictive model.
    selected = []
    for row in odds_rows:
        odd = row.get("_odd")
        if odd is not None and odd > 1:
            # odds alone cannot establish value; use only for candidate display
            selected.append(row)
    if selected:
        st.markdown("**Oran ve veri birlikte değerlendirilirken dikkat edilecek adaylar**")
        st.caption("Bu bölüm filtreleme desteğidir, doğrulanmış kazanma tahmini değildir. İstatistik ve oran tek başına yeterli değildir.")
        selected.sort(key=lambda r: (r.get("_market",""), r.get("_odd", 999)))
        st.dataframe([{
            "Pazar": r["_market"], "Seçenek": r["_option"], "Oran": r["_odd"],
            "Oranın ham olasılığı (%)": round(100/r["_odd"],1),
            "Sağlayıcı": r["_bookmaker"]
        } for r in selected[:20]], use_container_width=True, hide_index=True)
    else:
        st.info("Oran verisi olmadığı için oran bazlı aday listesi oluşturulamadı.")

    if not stats:
        st.warning("**Karar: PAS GEÇ.** Bu maç için istatistik verisi olmadığı ve oran geçmişi bulunmadığı için güvenilir bir 'oyna' sinyali üretilemiyor. Oranları gösterebiliriz ancak tek başına oran, avantaj kanıtı değildir.")
    else:
        st.warning("**Karar: Şimdilik PAS GEÇ / ek veri bekle.** Bu sürümde açılış oranı geçmişi ve geçmiş maçlarla doğrulanmış olasılık modeli yok. İstatistikler gösterilir; fakat bunlar tek başına güvenilir bahis önerisi sayılmaz.")

def show_matches(matches, prefix):
    if not matches:
        st.info("Bu seçim için maç bulunamadı.")
        return
    st.caption(f"Bulunan maç sayısı: {len(matches)}")
    for match in matches:
        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        league = match.get("league", {})
        status = fixture.get("status", {})
        home = teams.get("home", {}).get("name", "Ev sahibi")
        away = teams.get("away", {}).get("name", "Deplasman")
        hg, ag = goals.get("home"), goals.get("away")
        elapsed = status.get("elapsed")
        state = f"{elapsed}'" if elapsed is not None else tr_status(status.get("long"))
        fid = fixture.get("id")
        title = f"{home} {hg if hg is not None else '—'} - {ag if ag is not None else '—'} {away} | {league.get('name','Lig bilinmiyor')} | {state}"
        with st.expander(title):
            st.write(f"**Maç ID:** {fid}")
            st.write(f"**Lig/ülke:** {league.get('name','—')} / {league.get('country','—')}")
            st.write(f"**Başlama:** {fixture.get('date','Bilinmiyor')}")
            st.write(f"**Durum:** {tr_status(status.get('long', status.get('short')))}")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("İstatistikleri getir", key=f"{prefix}_stats_{fid}"):
                st.session_state[f"stats_{fid}"] = True
            if c2.button("Kadroyu getir", key=f"{prefix}_lineup_{fid}"):
                st.session_state[f"lineup_{fid}"] = True
            if c3.button("Oranları getir", key=f"{prefix}_odds_{fid}"):
                st.session_state[f"odds_{fid}"] = True
            if c4.button("Maçı analiz et", key=f"{prefix}_analyze_{fid}"):
                st.session_state[f"stats_{fid}"] = True
                st.session_state[f"odds_{fid}"] = True
                st.session_state[f"analyze_{fid}"] = True
            if st.button("API yanıtını kontrol et", key=f"{prefix}_diag_{fid}"):
                with st.spinner("İstatistik API yanıtı kontrol ediliyor..."):
                    diag_data, diag_err, diag_payload = api_get("fixtures/statistics", {"fixture": fid})
                if diag_err:
                    st.error(diag_err)
                else:
                    st.write(f"İstatistik uç noktası yanıt verdi. Dönen takım kaydı: {len(diag_data or [])}.")
                    if not diag_data:
                        st.warning("API hata bildirmedi ancak bu maç için istatistik kaydı boş.")
                    if diag_payload:
                        st.json({"results": diag_payload.get("results"), "errors": diag_payload.get("errors"), "response_count": len(diag_data or [])})
            stats = None
            odds = []
            if st.session_state.get(f"stats_{fid}"):
                stats = show_stats(fid, match)
            if st.session_state.get(f"lineup_{fid}"):
                show_lineups(fid)
            if st.session_state.get(f"odds_{fid}"):
                odds = show_odds(fid)
            if st.session_state.get(f"analyze_{fid}"):
                if stats is None:
                    stats = show_stats(fid, match)
                if not odds:
                    odds = show_odds(fid)
                analyze_match(match, stats, odds)

live_tab, date_tab, tr_sources_tab, info_tab = st.tabs(["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "🇹🇷 Türkiye kaynakları", "ℹ️ Program hakkında"])
with live_tab:
    st.subheader("Şu anda oynanan maçlar")
    if st.button("Canlı maçları yükle / yenile"):
        with st.spinner("Canlı maçlar yükleniyor..."):
            data, err, _ = api_get("fixtures", {"live": "all"})
        if err: st.error(err)
        else: st.session_state["live_matches"] = data
    if "live_matches" in st.session_state:
        show_matches(st.session_state["live_matches"], "live")
    else:
        st.info("Canlı maçları görmek için yukarıdaki düğmeye basın.")
with date_tab:
    st.subheader("Tarihe göre fikstür")
    chosen = st.date_input("Maç tarihi", value=date.today())
    if st.button("Fikstürü getir"):
        with st.spinner("Fikstür yükleniyor..."):
            data, err, _ = api_get("fixtures", {"date": chosen.isoformat()})
        if err: st.error(err)
        else:
            st.session_state["date_matches"] = data
            st.session_state["date_label"] = chosen.isoformat()
    if "date_matches" in st.session_state:
        st.caption("Seçilen tarih: " + st.session_state.get("date_label", ""))
        show_matches(st.session_state["date_matches"], "date")
with tr_sources_tab:
    st.subheader("Türkiye oran ve haber kaynakları")
    st.warning("Bu bölüm kaynaklara erişim sağlar; şu an Nesine/İddaa oranlarını otomatik içeri aktardığını veya sosyal medya yorumlarını taradığını iddia etmez. Bunun için izinli/veri sağlayan bir bağlantı kurulması gerekir.")
    st.markdown("- [Nesine – İddaa ve canlı oranlar](https://www.nesine.com/)")
    st.markdown("- [TFF – Resmî futbol haberleri ve duyurular](https://www.tff.org/)")
    st.markdown("- [Google Haberler – Futbol haberleri](https://news.google.com/search?q= futbol)")
    st.markdown("**Sonraki entegrasyon için:** Resmî/izinli oran akışı veya erişilebilir RSS haber akışı bağlandığında kaynak, tarih ve bağlantı bilgileriyle havuz oluşturulabilir. Sosyal medya yorumları ayrı bir bölümde, kaynak ve zaman damgasıyla tutulmalı; tek başına bahis sinyali sayılmamalıdır.")
    st.divider()
    st.subheader("İkinci ücretsiz veri kaynağı: football-data.org")
    st.write("Bu kaynak bazı liglerde fikstür, sonuç ve puan durumu için yedek olabilir. Ücretsiz katman ayrıntılı canlı istatistik, tüm kadrolar veya bahis oranları sağlamaz; bu nedenle mevcut API-Football'ın tam yerine geçmez.")
    if not FOOTBALL_DATA_TOKEN:
        st.info("Bağlamak için football-data.org sitesinden ücretsiz token alıp Streamlit uygulama ayarları → Secrets bölümüne şu satırı ekle: FOOTBALL_DATA_TOKEN = \"TOKENIN\"")
    else:
        comp_code = st.selectbox("İkinci kaynak lig kodu", ["PL", "PD", "BL1", "SA", "FL1", "DED", "PPL", "BSA"], format_func=lambda x: {"PL":"İngiltere Premier League", "PD":"İspanya La Liga", "BL1":"Almanya Bundesliga", "SA":"İtalya Serie A", "FL1":"Fransa Ligue 1", "DED":"Hollanda Eredivisie", "PPL":"Portekiz Primeira Liga", "BSA":"Brezilya Serie A"}.get(x, x))
        if st.button("İkinci kaynaktan fikstür/sonuç getir"):
            with st.spinner("İkinci kaynak sorgulanıyor..."):
                second_data, second_err = football_data_get(f"competitions/{comp_code}/matches", {"dateFrom": date.today().isoformat(), "dateTo": date.today().isoformat()})
            if second_err:
                st.error(second_err)
            else:
                matches2 = second_data.get("matches", []) if second_data else []
                if matches2:
                    st.dataframe([{
                        "Tarih": m.get("utcDate", "") ,
                        "Ev sahibi": m.get("homeTeam", {}).get("name", "—"),
                        "Deplasman": m.get("awayTeam", {}).get("name", "—"),
                        "Skor": f"{m.get('score', {}).get('fullTime', {}).get('home') if m.get('score', {}).get('fullTime', {}).get('home') is not None else '—'} - {m.get('score', {}).get('fullTime', {}).get('away') if m.get('score', {}).get('fullTime', {}).get('away') is not None else '—'}",
                        "Durum": m.get("status", "—")
                    } for m in matches2], use_container_width=True, hide_index=True)
                else:
                    st.info("İkinci kaynak bu lig/tarih için maç döndürmedi.")
with info_tab:
    st.subheader("Program hakkında")
    st.markdown("""
- Canlı maçlar ve tarih seçimine göre fikstür.
- Sağlayıcının sunduğu istatistiklerin Türkçe gösterimi.
- Mevcutsa kadro ve bahis oranları.
- Oranın ham olasılığı: 100 / oran. Bu, gerçek kazanma olasılığı değildir ve şirket marjını içerebilir.
- **Maçı analiz et** düğmesi mevcut istatistikleri ve oranları bir araya getirir.
- API çağrıları kısa süre önbelleğe alınır; sayfa yenilenince ücretsiz günlük limit gereksiz yere tüketilmez.
- İstatistik/kadro butonları API'nin veri döndürdüğü maçlarda sonuç gösterir; kapsama girmeyen maçlarda uygulama veri üretemez.
- Veri eksikse sistem bunu açıkça söyler; veri uydurmaz.
- Bu sürüm otomatik bahis yapmaz. Doğrulanmış tahmin modeli, açılış oranı geçmişi ve tüm liglerde son dakika hareketleri henüz mevcut değildir.
- İkinci kaynak football-data.org opsiyoneldir; ücretsiz token ile yalnızca desteklediği yarışmaların fikstür/sonuç verilerini yedekler. Ayrıntılı istatistik ve oranları ikame etmez. API anahtarlarını kodun içine yazmayın; Secrets bölümünde saklayın.
""")
