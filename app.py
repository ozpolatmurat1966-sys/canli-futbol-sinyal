import streamlit as st
import requests
from datetime import date
import math
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

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
        ("15 minutes", "İlk 15 Dakika"), ("30 minutes", "İlk 30 Dakika"),
        ("60 minutes", "İlk 60 Dakika"), ("Next Goal", "Sonraki Gol"),
        ("To Score", "Gol Atar"), ("No Goal", "Gol Olmaz"),
        ("1X2", "Maç Sonucu"), ("Winner", "Kazanan"),
        ("Corners", "Korner"), ("Offsides", "Ofsayt"),
    ]
    for en, tr in replacements:
        raw = raw.replace(en, tr)
    raw = raw.replace("Corners", "Korner").replace("Corner", "Korner").replace("Cards", "Kart")
    raw = raw.replace("Goals", "Goller").replace("Goal", "Gol")
    raw = raw.replace("Player", "Oyuncu").replace("Shots", "Şut")
    raw = raw.replace("Away", "Deplasman").replace("Home", "Ev Sahibi")
    raw = raw.replace("Over/Under", "Alt/Üst").replace("Over Under", "Alt/Üst")
    raw = raw.replace(" (2nd Half)", " (İkinci Yarı)").replace(" (1st Half)", " (İlk Yarı)")
    raw = raw.replace(" (Second Half)", " (İkinci Yarı)").replace(" (First Half)", " (İlk Yarı)")
    raw = raw.replace("First Half", "İlk Yarı").replace("Second Half", "İkinci Yarı")
    raw = raw.replace("15m", "15 dakika").replace("30m", "30 dakika").replace("45m", "45 dakika")
    raw = raw.replace("1x2 - İlk 15 Dakika", "Maç Sonucu - İlk 15 Dakika")
    raw = raw.replace("1x2 - İlk 30 Dakika", "Maç Sonucu - İlk 30 Dakika")
    raw = raw.replace("1x2 - İlk 60 Dakika", "Maç Sonucu - İlk 60 Dakika")
    # Tidy common mixed-language provider labels
    raw = raw.replace("Deplasman Korner Alt/Üst", "Deplasman Korner Alt/Üst")
    raw = raw.replace("Ev Sahibi Korner Alt/Üst", "Ev Sahibi Korner Alt/Üst")
    raw = raw.replace("Alt/Üst 15m-30m", "15–30. Dakika Alt/Üst")
    raw = raw.replace("Alt/Üst 30m-45m", "30–45. Dakika Alt/Üst")
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
    raw = raw.replace("Away", "Deplasman").replace("Home", "Ev Sahibi")
    raw = raw.replace("Corners", "Korner").replace("Corner", "Korner")
    raw = raw.replace("Cards", "Kart").replace("Offsides", "Ofsayt")
    raw = raw.replace("15 minutes", "İlk 15 dakika").replace("30 minutes", "İlk 30 dakika")
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
SPORTMONKS_API_TOKEN = str(secret("SPORTMONKS_API_TOKEN", "")).strip()
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


@st.cache_data(ttl=45, show_spinner=False)
def sportmonks_live_matches():
    """Optional Sportmonks fallback. Free coverage is limited to selected leagues."""
    if not SPORTMONKS_API_TOKEN:
        return None, "Sportmonks token eklenmedi."
    try:
        response = requests.get(
            "https://api.sportmonks.com/v3/football/livescores",
            params={
                "api_token": SPORTMONKS_API_TOKEN,
                "include": "participants;statistics.type;lineups.player"
            },
            timeout=20,
        )
        if response.status_code != 200:
            return None, f"Sportmonks HTTP {response.status_code}: {response.text[:250]}"
        payload = response.json()
        return payload.get("data", []), None
    except (requests.RequestException, ValueError) as exc:
        return None, f"Sportmonks bağlantı hatası: {exc}"

def sportmonks_to_api_football(matches):
    """Normalize Sportmonks livescores to the small schema used by show_matches."""
    normalized = []
    for m in matches or []:
        participants = m.get("participants") or []
        home = away = None
        for part in participants:
            meta = part.get("meta") or {}
            location = str(meta.get("location", "")).lower()
            if location == "home":
                home = part.get("name")
            elif location == "away":
                away = part.get("name")
        if not home and len(participants) > 0:
            home = participants[0].get("name")
        if not away and len(participants) > 1:
            away = participants[1].get("name")

        scores = m.get("scores") or []
        hg = ag = None
        for score in scores:
            description = str(score.get("description", "")).lower()
            participant_id = score.get("participant_id")
            score_value = (score.get("score") or {}).get("goals")
            if score_value is None:
                continue
            participant = next((x for x in participants if x.get("id") == participant_id), {})
            location = str((participant.get("meta") or {}).get("location", "")).lower()
            if location == "home" and (description in ("current", "2nd-half", "1st-half", "live") or hg is None):
                hg = score_value
            elif location == "away" and (description in ("current", "2nd-half", "1st-half", "live") or ag is None):
                ag = score_value
        state = m.get("state") or {}
        state_name = state.get("name") or state.get("short_name") or "Canlı"
        minute = m.get("minute")
        normalized.append({
            "fixture": {"id": m.get("id"), "date": m.get("starting_at"),
                        "status": {"long": state_name, "short": state.get("short_name"), "elapsed": minute}},
            "teams": {"home": {"name": home or "Ev sahibi"}, "away": {"name": away or "Deplasman"}},
            "goals": {"home": hg, "away": ag},
            "league": {"name": (m.get("league") or {}).get("name", "Sportmonks ligi"),
                       "country": (m.get("league") or {}).get("country", {}).get("name", "") if isinstance((m.get("league") or {}).get("country"), dict) else ""},
            "_source": "Sportmonks"
        })
    return normalized

def sportmonks_find_match(home_name, away_name):
    matches, err = sportmonks_live_matches()
    if err or not matches:
        return None, err or "Sportmonks canlı maç döndürmedi."
    def norm(txt):
        return "".join(ch.lower() for ch in str(txt or "") if ch.isalnum())
    target_home, target_away = norm(home_name), norm(away_name)
    for match in matches:
        participants = match.get("participants") or []
        names = [norm(p.get("name")) for p in participants]
        # The feed can order participants differently, so match both directions.
        if len(names) >= 2 and (
            (target_home in names[0] or names[0] in target_home) and
            (target_away in names[1] or names[1] in target_away) or
            (target_home in names[1] or names[1] in target_home) and
            (target_away in names[0] or names[0] in target_away)
        ):
            return match, None
    return None, "Sportmonks ücretsiz kapsamındaki canlı maçlar arasında bu karşılaşma bulunamadı."

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
    if not data or len(data) < 2:
        teams = match.get("teams", {})
        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        sm_match, sm_err = sportmonks_find_match(home_name, away_name) if SPORTMONKS_API_TOKEN else (None, "Sportmonks token eklenmedi.")
        if sm_match:
            sm_stats = sm_match.get("statistics") or []
            # Convert Sportmonks statistic rows into the app's two-team display format.
            by_team = {}
            for item in sm_stats:
                participant_id = item.get("participant_id")
                participant = item.get("participant") or {}
                team_name = participant.get("name") or str(participant_id or "Takım")
                by_team.setdefault(team_name, []).append({
                    "type": (item.get("type") or {}).get("name", "İstatistik"),
                    "value": (item.get("data") or {}).get("value")
                })
            if len(by_team) >= 2:
                names = list(by_team.keys())[:2]
                data = [
                    {"team": {"name": names[0]}, "statistics": by_team[names[0]]},
                    {"team": {"name": names[1]}, "statistics": by_team[names[1]]},
                ]
                st.info("İstatistikler yedek kaynak Sportmonks üzerinden alındı.")
            else:
                st.warning("API-Football veri döndürmedi; Sportmonks da bu maç için iki takımın istatistiğini sunmadı.")
                if sm_err: st.caption(sm_err)
                return None
        else:
            if err:
                st.error(f"API-Football isteği başarısız: {err}")
            st.warning("İstatistik kaydı API-Football'da boş.")
            if SPORTMONKS_API_TOKEN:
                st.caption(sm_err or "Sportmonks bu maçı yedek kaynakta bulamadı. Ücretsiz plan yalnızca Danimarka Superliga ve İskoçya Premiership kapsamındadır.")
            else:
                st.caption("Yedek kaynak için Streamlit Secrets bölümüne SPORTMONKS_API_TOKEN eklenmelidir. Ücretsiz kapsam yalnızca seçili liglerle sınırlıdır.")
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

def show_lineups(fixture_id, match=None):
    data, err, _ = api_get("fixtures/lineups", {"fixture": fixture_id})
    if not data and match and SPORTMONKS_API_TOKEN:
        teams = match.get("teams", {})
        sm_match, sm_err = sportmonks_find_match(
            teams.get("home", {}).get("name", ""),
            teams.get("away", {}).get("name", "")
        )
        if sm_match:
            sm_lineups = sm_match.get("lineups") or []
            converted = []
            for lineup in sm_lineups:
                player = lineup.get("player") or {}
                converted.append({
                    "team": {"name": (lineup.get("team") or {}).get("name", "Takım")},
                    "formation": lineup.get("formation_position"),
                    "startXI": [{"player": {"name": player.get("display_name") or player.get("name") or "Oyuncu"}}]
                              if lineup.get("type", {}).get("name", "").lower() in ("starting XI", "starter") else [],
                    "substitutes": []
                })
            if converted:
                data = converted
                st.info("Kadro bilgisi yedek kaynak Sportmonks üzerinden alındı; oyuncu sınıflaması sağlayıcının sunduğu alanlarla sınırlı olabilir.")
        elif sm_err:
            st.caption(sm_err)
    if err and not data:
        st.error(f"Kadro isteği başarısız: {err}")
    if not data:
        st.warning("Kadro verisi API-Football'da bulunamadı; yedek kaynak da bu maç için kadro döndürmedi. Kadro verisi olmayan maçlarda oyuncu listesi uydurulmaz.")
        st.caption("Kadrolar maçtan önce açıklanabilir; ayrıca Sportmonks ücretsiz kapsamı yalnızca seçili liglerle sınırlıdır.")
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
    show_odds_comparison(all_rows)
    return all_rows

def show_odds_comparison(odds_rows):
    """Compare the best available price across providers for the same market/selection."""
    if not odds_rows:
        return
    groups = {}
    for row in odds_rows:
        odd = row.get("_odd")
        market = row.get("_market", "Pazar")
        option = row.get("_option", "—")
        if odd is None or odd <= 1:
            continue
        key = (market, option)
        groups.setdefault(key, []).append(row)
    comparison = []
    for (market, option), rows in groups.items():
        best = max(rows, key=lambda r: r.get("_odd", 0))
        worst = min(rows, key=lambda r: r.get("_odd", 999999))
        implied = 100 / best["_odd"]
        comparison.append({
            "Pazar": market,
            "Seçenek": option,
            "En iyi oran": best["_odd"],
            "En iyi sağlayıcı": best.get("_bookmaker", "—"),
            "En düşük oran": worst["_odd"],
            "Oran farkı": round(best["_odd"] - worst["_odd"], 2),
            "En iyi oranın ham olasılığı (%)": round(implied, 1),
            "_market": market,
            "_option": option,
            "_best": best["_odd"],
        })
    if comparison:
        st.markdown("**Bahis şirketleri arasında oran karşılaştırması**")
        st.caption("Aynı pazar ve seçenek eşleştirildiğinde gösterilir. En yüksek oran tek başına bahis avantajı veya kazanma olasılığı anlamına gelmez.")
        comparison.sort(key=lambda r: (r["Pazar"], -r["_best"]))
        st.dataframe([{k: v for k, v in r.items() if not k.startswith("_")} for r in comparison],
                     use_container_width=True, hide_index=True)
        # A basic 1X2 market margin estimate only when all three outcomes exist in one bookmaker.
        one_x_two = {}
        for row in odds_rows:
            market = str(row.get("_market", "")).lower()
            option = str(row.get("_option", "")).lower()
            if "1x2" not in market and "maç sonucu" not in market:
                continue
            if row.get("_odd") and row["_odd"] > 1:
                outcome = "1" if ("ev sahibi" in option or option.strip() == "1") else (
                    "x" if ("beraberlik" in option or option.strip() == "x") else (
                    "2" if ("deplasman" in option or option.strip() == "2") else None))
                if outcome:
                    one_x_two.setdefault(row.get("_bookmaker", "—"), {})[outcome] = row["_odd"]
        margin_rows = []
        for book, outcomes in one_x_two.items():
            if all(k in outcomes for k in ("1", "x", "2")):
                total = sum(1 / outcomes[k] for k in ("1", "x", "2"))
                margin_rows.append({"Sağlayıcı": book, "1X2 toplam ham olasılık (%)": round(total * 100, 1),
                                    "Yaklaşık marj (%)": round((total - 1) * 100, 1)})
        if margin_rows:
            st.markdown("**1X2 oran marjı (yaklaşık)**")
            st.dataframe(margin_rows, use_container_width=True, hide_index=True)


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

    # Compare providers and explain evidence quality without presenting an unvalidated bet as a prediction.
    show_odds_comparison(odds_rows)
    valid_odds = [r for r in odds_rows if r.get("_odd") and r["_odd"] > 1]
    if valid_odds:
        # Group markets into understandable families and keep correct-score/long-shot
        # markets out of the shortlist so huge prices are not mistaken for value.
        def market_family(name):
            m = str(name or "").lower()
            if "doğru skor" in m or "correct score" in m or "exact score" in m:
                return "Doğru skor"
            if "maç sonucu" in m or "match winner" in m or "1x2" in m:
                return "Maç sonucu"
            if "çifte şans" in m or "double chance" in m:
                return "Çifte şans"
            if "beraberlikte iade" in m or "draw no bet" in m:
                return "Beraberlikte iade"
            if "karşılıklı gol" in m or "both teams" in m:
                return "Karşılıklı gol"
            if "alt/üst" in m or "over/under" in m or "gol alt" in m or "toplam gol" in m:
                return "Gol alt/üst"
            if "korner" in m or "corner" in m:
                return "Korner"
            if "kart" in m or "card" in m:
                return "Kart"
            if "ilk yarı" in m or "first half" in m or "devre" in m:
                return "İlk yarı"
            return "Diğer pazarlar"

        family_rows = {}
        for row in valid_odds:
            family_rows.setdefault(market_family(row.get("_market")), []).append(row)
        st.markdown("**Pazar gruplarına göre oran özeti**")
        st.caption("Doğru skor gibi yüksek riskli pazarlar ayrı tutulur. Bu özet oran karşılaştırmasıdır; tek başına bahis tavsiyesi değildir.")
        family_summary = []
        for family, rows in sorted(family_rows.items()):
            family_summary.append({
                "Pazar grubu": family,
                "Oran kaydı": len(rows),
                "En düşük oran": min(r["_odd"] for r in rows),
                "En yüksek oran": max(r["_odd"] for r in rows),
                "Sağlayıcı sayısı": len(set(r.get("_bookmaker", "—") for r in rows)),
            })
        st.dataframe(family_summary, use_container_width=True, hide_index=True)

        main_families = {"Maç sonucu", "Çifte şans", "Beraberlikte iade",
                         "Karşılıklı gol", "Gol alt/üst", "Korner", "Kart", "İlk yarı"}
        shortlist = {}
        for row in valid_odds:
            family = market_family(row.get("_market"))
            if family not in main_families:
                continue
            key = (row.get("_market", "Pazar"), row.get("_option", "—"))
            if key not in shortlist or row["_odd"] > shortlist[key]["_odd"]:
                shortlist[key] = row
        if shortlist:
            st.markdown("**Karşılaştırılabilir ana pazarlar**")
            st.dataframe([{
                "Pazar": r["_market"], "Seçenek": r["_option"], "En iyi oran": r["_odd"],
                "Ham olasılık (%)": round(100/r["_odd"], 1),
                "Sağlayıcı": r["_bookmaker"]
            } for r in sorted(shortlist.values(), key=lambda r: (market_family(r.get("_market")), r["_market"], r["_option"]))[:30]],
                use_container_width=True, hide_index=True)
        else:
            st.info("Mevcut oranlar arasında ana pazarlar eşleştirilemedi. Diğer pazarlar ayrı oran tablosunda kalıyor.")
        correct_score_count = sum(1 for r in valid_odds if market_family(r.get("_market")) == "Doğru skor")
        if correct_score_count:
            st.caption(f"Doğru skor pazarında {correct_score_count} oran kaydı ayrıca mevcut; bu oranlar ana pazar kısa listesine alınmadı.")
    else:
        st.info("Oran verisi olmadığı için karşılaştırma yapılamadı.")

    show_bet_candidates(stats, odds_rows, elapsed)

    # Show evidence for/against broad live-game tendencies; this is descriptive, not a probability model.
    supporting = []
    opposing = []
    if stats and h_on is not None and a_on is not None:
        total_on = h_on + a_on
        if total_on >= 5:
            supporting.append(f"Maçta toplam {int(total_on)} isabetli şut var; hücum etkinliği mevcut.")
        elif total_on <= 2:
            opposing.append(f"Toplam isabetli şut yalnızca {int(total_on)}; gol/üst beklentisini destekleyen veri zayıf.")
        if abs(h_on - a_on) >= 3:
            leader = stats["home_name"] if h_on > a_on else stats["away_name"]
            supporting.append(f"{leader} isabetli şutta belirgin üstün ({max(h_on,a_on)}–{min(h_on,a_on)}).")
    if stats and h_cor is not None and a_cor is not None:
        total_corners = h_cor + a_cor
        if total_corners >= 7:
            supporting.append(f"Toplam korner {int(total_corners)}; korner pazarı için hareketlilik işareti.")
        elif total_corners <= 2:
            opposing.append(f"Toplam korner {int(total_corners)}; yüksek korner çizgilerini destekleyen veri yok.")
    if stats and h_xg is not None and a_xg is not None:
        total_xg = h_xg + a_xg
        if total_xg >= 1.5:
            supporting.append(f"Toplam xG {total_xg:.2f}; gol beklentisini destekleyebilir.")
        elif total_xg < 0.7:
            opposing.append(f"Toplam xG {total_xg:.2f}; gol beklentisi şu ana kadar düşük.")
    if elapsed is not None and elapsed < 20:
        opposing.append("Maç henüz erken dakikalarda; canlı istatistik örneklemi küçük olabilir.")
    if supporting or opposing:
        st.markdown("**Verilerin desteklediği ve zayıflattığı işaretler**")
        if supporting:
            st.write("**Destekleyen:** " + " ".join(supporting))
        if opposing:
            st.write("**Zayıflatan:** " + " ".join(opposing))
        st.caption("Bunlar betimleyici göstergelerdir; olasılık modeli veya doğrulanmış bahis tavsiyesi değildir.")

    evidence = []
    if elapsed is not None:
        evidence.append("maç dakikası mevcut")
    if home_goals is not None and away_goals is not None:
        evidence.append("skor mevcut")
    if metrics:
        evidence.append(f"{len(metrics)} istatistik göstergesi mevcut")
    if valid_odds:
        evidence.append(f"{len(valid_odds)} oran kaydı mevcut")
    st.markdown("**Veri yeterliliği kontrolü**")
    st.write(" • ".join(evidence) if evidence else "Bu maç için kullanılabilir veri çok sınırlı.")
    if not stats or not valid_odds or len(metrics) < 2:
        st.warning("**Karar: PAS GEÇ / veri bekle.** İstatistik, oran veya karşılaştırılabilir gösterge eksik. Eksik veriler tamamlanmadan güvenilir bir seçim çıkarılamaz.")
    else:
        st.warning("**Karar: Şimdilik PAS GEÇ / ek doğrulama bekle.** İstatistik ve oranlar karşılaştırıldı; ancak açılış oranı geçmişi ve geçmiş maçlarda test edilmiş olasılık modeli olmadığı için bu sürüm doğrulanmış 'oyna' sinyali vermez.")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_team_news(home_name, away_name):
    """Public Google News RSS headlines only; not full articles or social-media comments."""
    query = quote_plus(f'("{home_name}" OR "{away_name}") football')
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    try:
        response = requests.get(url, headers={"User-Agent": "FutbolAnalizMerkezi/1.0"}, timeout=12)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", default="Haber başlığı yok")
            link = item.findtext("link", default="")
            pub = item.findtext("pubDate", default="")
            source = item.findtext("source", default="Google Haberler")
            if title and link:
                items.append({"Başlık": title, "Kaynak": source, "Yayın zamanı": pub, "Bağlantı": link})
        return items, None
    except Exception as exc:
        return [], f"Haber akışına erişilemedi: {exc}"

def show_match_news(home_name, away_name, fixture_id):
    st.markdown("**📰 Maç haberleri**")
    st.caption("Google Haberler'in herkese açık RSS başlıkları gösterilir. Bu bölüm sosyal medya yorumlarını taramaz; başlıklar tek başına bahis sinyali değildir.")
    if st.button("Haber başlıklarını getir", key=f"news_{fixture_id}"):
        with st.spinner("Haber başlıkları aranıyor..."):
            items, err = fetch_team_news(home_name, away_name)
        st.session_state[f"news_items_{fixture_id}"] = items
        st.session_state[f"news_error_{fixture_id}"] = err
    items = st.session_state.get(f"news_items_{fixture_id}")
    err = st.session_state.get(f"news_error_{fixture_id}")
    if err:
        st.warning(err)
    if items:
        for item in items:
            st.markdown(f"- [{item['Başlık']}]({item['Bağlantı']})")
            st.caption(f"Kaynak: {item['Kaynak']} · {item['Yayın zamanı']}")
    elif items == [] and not err:
        st.info("Bu aramada haber başlığı bulunamadı.")

def show_bet_candidates(stats, odds_rows, elapsed=None):
    """Rank available odds using transparent descriptive signals; never fabricate calibrated probabilities."""
    st.markdown("### 🎯 Bahis adayları — veri sinyali")
    st.caption("Bu bölüm kesin bahis tavsiyesi değildir. Kazanma olasılığı modeliyle doğrulanmamıştır; yalnızca mevcut maç istatistiğiyle uyumlu olabilecek pazarları ve en iyi görünen oranı listeler.")
    if not odds_rows:
        st.info("Oran verisi yok; seçenek ve oran önerisi üretilemez. PAS GEÇ.")
        return
    hr = stats.get("home_rows", []) if stats else []
    ar = stats.get("away_rows", []) if stats else []
    h_on, a_on = stat_value(hr, ["Shots on Goal"]), stat_value(ar, ["Shots on Goal"])
    h_sh, a_sh = stat_value(hr, ["Total Shots"]), stat_value(ar, ["Total Shots"])
    h_cor, a_cor = stat_value(hr, ["Corner Kicks"]), stat_value(ar, ["Corner Kicks"])
    h_xg, a_xg = stat_value(hr, ["Expected Goals", "expected_goals"]), stat_value(ar, ["Expected Goals", "expected_goals"])
    candidates = {}
    for row in odds_rows:
        odd = row.get("_odd")
        if not odd or odd <= 1:
            continue
        market = str(row.get("_market", ""))
        option = str(row.get("_option", ""))
        low = (market + " " + option).lower()
        family, reason, against = None, None, None
        if ("korner" in low or "corner" in low) and h_cor is not None and a_cor is not None:
            total = h_cor + a_cor
            if total >= 7 and ("üst" in low or "over" in low):
                family, reason, against = "Korner", f"Şu ana kadar toplam {int(total)} korner", "Kalan süre ve mevcut çizgi mutlaka kontrol edilmeli"
            elif total <= 2 and ("alt" in low or "under" in low):
                family, reason, against = "Korner", f"Şu ana kadar yalnızca {int(total)} korner", "Korner temposu sonradan artabilir"
        elif ("gol alt/üst" in low or "toplam gol" in low or "goals over" in low) and h_on is not None and a_on is not None:
            total_on = h_on + a_on
            if total_on >= 5 and ("üst" in low or "over" in low):
                family, reason, against = "Gol alt/üst", f"Toplam {int(total_on)} isabetli şut", "İsabetli şut gol garantisi değildir; skor ve çizgiye bakılmalı"
            elif total_on <= 2 and ("alt" in low or "under" in low):
                family, reason, against = "Gol alt/üst", f"Toplam isabetli şut {int(total_on)}", "Erken dakika veya düşük örneklem yanıltabilir"
        elif ("karşılıklı gol" in low or "both teams score" in low) and h_on is not None and a_on is not None:
            if h_on >= 2 and a_on >= 2 and ("evet" in low or "yes" in low):
                family, reason, against = "Karşılıklı gol", f"İki takımın da en az 2 isabetli şutu var ({int(h_on)}–{int(a_on)})", "Şutlar gol anlamına gelmez; skor ve kalan süre önemli"
        if family:
            key = (market, option)
            if key not in candidates or odd > candidates[key]["odd"]:
                candidates[key] = {"Pazar": market, "Seçenek": option, "En iyi oran": odd, "Sağlayıcı": row.get("_bookmaker", "—"), "Veri sinyali": reason, "Dikkat": against, "odd": odd}
    if not stats:
        st.warning("Maç istatistiği yok. Oranlar görülebilir ama istatistikle desteklenen aday listesi üretmek doğru olmaz: PAS GEÇ.")
    elif not candidates:
        st.info("Mevcut istatistiklerle uyumlu ve yeterince açık bir aday bulunamadı. Maç sonucu/uzun oranlı seçenekleri rastgele önermiyorum: PAS GEÇ.")
    else:
        rows = sorted(candidates.values(), key=lambda x: x["odd"], reverse=True)[:8]
        st.dataframe([{k:v for k,v in row.items() if k != "odd"} for row in rows], use_container_width=True, hide_index=True)
        st.warning("Bunlar sadece izlemeye değer adaylardır; modelle doğrulanmış ‘oyna’ sinyali değildir. Bankroll/zarar sınırı belirlemeden işlem yapma.")


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
            show_match_news(home, away, fid)
            c1, c2, c3, c4 = st.columns(4)
            is_sportmonks = match.get("_source") == "Sportmonks"
            if c1.button("İstatistikleri getir", key=f"{prefix}_stats_{fid}"):
                st.session_state[f"stats_{fid}"] = True
            if c2.button("Kadroyu getir", key=f"{prefix}_lineup_{fid}"):
                st.session_state[f"lineup_{fid}"] = True
            if c3.button("Oranları getir", key=f"{prefix}_odds_{fid}", disabled=is_sportmonks):
                st.session_state[f"odds_{fid}"] = True
            if c4.button("Maçı analiz et", key=f"{prefix}_analyze_{fid}", disabled=is_sportmonks):
                st.session_state[f"stats_{fid}"] = True
                st.session_state[f"odds_{fid}"] = True
                st.session_state[f"analyze_{fid}"] = True
            if is_sportmonks:
                st.caption("Bu maç Sportmonks yedek kaynağından geldi. İstatistik/kadro denenebilir; API-Football maç ID'si olmadığı için oran ve birleşik analiz düğmeleri kapalıdır.")
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
                show_lineups(fid, match)
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
            source = "API-Football"
            if err and ("429" in err or "rateLimit" in err or "daily request limit" in err.lower()):
                if SPORTMONKS_API_TOKEN:
                    sm_data, sm_err = sportmonks_live_matches()
                    if not sm_err and sm_data:
                        data = sportmonks_to_api_football(sm_data)
                        err = None
                        source = "Sportmonks (ücretsiz lig kapsamı sınırlı)"
                    elif sm_err:
                        err = f"API-Football günlük limitini doldurdu. Sportmonks yedeği de kullanılamadı: {sm_err}"
                    else:
                        err = "API-Football günlük limiti dolu; Sportmonks şu anda canlı maç döndürmedi. Ücretsiz kapsam sınırlıdır."
        if err:
            st.error(err)
        else:
            st.session_state["live_matches"] = data
            st.session_state["live_source"] = source
    if "live_matches" in st.session_state:
        st.caption("Canlı veri kaynağı: " + st.session_state.get("live_source", "API-Football"))
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
    st.markdown("- [Google Haberler – Futbol haberleri](https://news.google.com/search?q=futbol)")
    st.info("Maç kartlarının içindeki ‘Haber başlıklarını getir’ düğmesi, takımlar için herkese açık Google Haberler RSS başlıklarını ve bağlantılarını getirir. X/Instagram/diğer sosyal medya yorumları otomatik taranmıyor; bu sürümde sosyal duygu analizi yok.")
    st.markdown("**Sonraki entegrasyon için:** Resmî/izinli oran akışı veya erişilebilir RSS haber akışı bağlandığında kaynak, tarih ve bağlantı bilgileriyle havuz oluşturulabilir. Sosyal medya yorumları ayrı bir bölümde, kaynak ve zaman damgasıyla tutulmalı; tek başına bahis sinyali sayılmamalıdır.")
    st.divider()
    st.subheader("Yedek canlı veri kaynağı: Sportmonks")
    st.write("Sportmonks canlı maç, olay, istatistik ve kadro alanlarını tek yanıtta sağlayabilir. Ancak ücretsiz planı yalnızca Danimarka Superliga ve İskoçya Premiership ile sınırlıdır; diğer ligler için ücretsiz yedek garanti edilmez.")
    if not SPORTMONKS_API_TOKEN:
        st.info("Sportmonks ücretsiz token'ını aldıktan sonra Streamlit Secrets bölümüne şu satırı ekle: SPORTMONKS_API_TOKEN = \"TOKENIN\"")
    else:
        st.success("Sportmonks token'ı tanımlı. İstatistik/kadro boşsa uygulama önce bu kaynağı da kontrol edecek.")
    st.markdown("[Sportmonks ücretsiz plan ve token](https://www.sportmonks.com/football-api/free-plan/)")
    st.divider()
    st.subheader("Ek fikstür kaynağı: football-data.org")
    st.write("football-data.org bazı liglerde fikstür, sonuç ve puan durumu için yedek olabilir. Ücretsiz katman ayrıntılı canlı istatistik, tüm kadrolar veya bahis oranları sağlamaz.")
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
- İstatistik/kadro için Sportmonks yedek bağlantısı isteğe bağlıdır; ücretsiz kapsam Danimarka Superliga ve İskoçya Premiership ile sınırlıdır. football-data.org yalnızca desteklediği yarışmaların fikstür/sonuç verilerine yardımcı olur. API anahtarlarını kodun içine yazmayın; Secrets bölümünde saklayın.
""")
