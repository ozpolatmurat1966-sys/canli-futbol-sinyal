import streamlit as st
import requests
from datetime import date
import math
import sqlite3
from datetime import datetime, timezone
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

if not API_KEY and not SPORTMONKS_API_TOKEN:
    st.error("Canlı veri için en az bir sağlayıcı anahtarı gerekli. API_FOOTBALL_KEY veya SPORTMONKS_API_TOKEN ekleyin.")
    st.code('API_FOOTBALL_KEY = "API_ANAHTARINIZ"\nSPORTMONKS_API_TOKEN = "SPORTMONKS_TOKENINIZ"\nAPP_PASSWORD = "KENDI_SIFRENIZ"')
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def api_get(endpoint, params=None):
    """Cache API responses briefly so Streamlit reruns do not waste free calls."""
    if not API_KEY:
        return None, "API-Football anahtarı tanımlı değil.", None
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


@st.cache_data(ttl=900, show_spinner=False)
def football_data_matches_for_date(date_text):
    """Supplementary fixtures/results from football-data.org; coverage depends on token/plan."""
    if not FOOTBALL_DATA_TOKEN:
        return [], "football-data.org tokenı ekli değil"
    payload, err = football_data_get("matches", {"dateFrom": date_text, "dateTo": date_text})
    if err or not isinstance(payload, dict):
        return [], err or "football-data.org yanıtı okunamadı"
    out = []
    for item in payload.get("matches", []):
        home = (item.get("homeTeam") or {}).get("name")
        away = (item.get("awayTeam") or {}).get("name")
        if not home or not away:
            continue
        score = item.get("score") or {}
        full = score.get("fullTime") or {}
        competition = item.get("competition") or {}
        status_raw = item.get("status") or "Scheduled"
        status_map = {"FINISHED": "Maç Bitti", "IN_PLAY": "Canlı", "PAUSED": "Devre Arası", "SCHEDULED": "Başlamadı", "TIMED": "Başlamadı", "POSTPONED": "Ertelendi", "CANCELLED": "İptal"}
        out.append({
            "fixture": {"id": f"fd-{item.get('id')}", "date": item.get("utcDate"), "status": {"long": status_map.get(status_raw, status_raw), "short": status_raw, "elapsed": None}},
            "teams": {"home": {"name": home}, "away": {"name": away}},
            "goals": {"home": full.get("home"), "away": full.get("away")},
            "league": {"name": competition.get("name", "football-data.org"), "country": ""},
            "_source": "football-data.org", "_raw_supplemental": item
        })
    return out, None

@st.cache_data(ttl=3600, show_spinner=False)
def openligadb_matches_for_date(date_text):
    """Free public OpenLigaDB supplement for German football only; not a global live-data source."""
    from datetime import datetime as _dt
    try:
        chosen = _dt.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return [], "Geçersiz tarih"
    season = chosen.year if chosen.month >= 7 else chosen.year - 1
    out = []
    errors = []
    successful_competitions = 0
    # Bundesliga and 2. Bundesliga are separate competitions; requests are cached for an hour.
    for shortcut, league_name in (("bl1", "Almanya Bundesliga"), ("bl2", "Almanya 2. Bundesliga")):
        try:
            response = requests.get(f"https://api.openligadb.de/getmatchdata/{shortcut}/{season}", timeout=12)
            if response.status_code != 200:
                errors.append(f"{shortcut}: HTTP {response.status_code}")
                continue
            matches = response.json()
            successful_competitions += 1
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{shortcut}: {exc}")
            continue
        for item in matches if isinstance(matches, list) else []:
            match_date = (item.get("matchDateTimeUTC") or item.get("matchDateTime") or "")
            if not match_date or not str(match_date).startswith(date_text):
                continue
            t1 = item.get("team1") or {}
            t2 = item.get("team2") or {}
            home, away = t1.get("teamName"), t2.get("teamName")
            if not home or not away:
                continue
            results = item.get("matchResults") or []
            goals_home = goals_away = None
            if results:
                final_result = next((r for r in reversed(results) if r.get("resultTypeID") == 1), results[-1])
                goals_home = final_result.get("pointsTeam1")
                goals_away = final_result.get("pointsTeam2")
            finished = item.get("matchIsFinished") is True
            out.append({
                "fixture": {"id": f"oldb-{item.get('matchID')}", "date": match_date, "status": {"long": "Maç Bitti" if finished else "Başlamadı", "short": "FT" if finished else "NS", "elapsed": None}},
                "teams": {"home": {"name": home}, "away": {"name": away}},
                "goals": {"home": goals_home, "away": goals_away},
                "league": {"name": league_name, "country": "Almanya"},
                "_source": "OpenLigaDB", "_raw_supplemental": item
            })
    if successful_competitions == 0:
        return out, "OpenLigaDB iki lig isteğinde de yanıt alınamadı: " + "; ".join(errors)
    if not out:
        return out, "OpenLigaDB bağlantısı çalıştı ancak seçilen tarihte Bundesliga / 2. Bundesliga maçı bulunmadı."
    return out, ("; ".join(errors) if errors else None)

def merge_fixture_sources(primary, supplemental):
    """Merge fixtures by normalized team names so one match is not shown twice."""
    def norm(text):
        return "".join(ch.lower() for ch in str(text or "") if ch.isalnum())
    merged = list(primary or [])
    seen = set()
    for item in merged:
        teams = item.get("teams") or {}
        names = sorted([norm((teams.get("home") or {}).get("name")), norm((teams.get("away") or {}).get("name"))])
        if all(names):
            seen.add(tuple(names))
    for item in supplemental or []:
        teams = item.get("teams") or {}
        names = sorted([norm((teams.get("home") or {}).get("name")), norm((teams.get("away") or {}).get("name"))])
        key = tuple(names)
        if all(names) and key not in seen:
            merged.append(item)
            seen.add(key)
    return merged

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
                "include": "participants;statistics.type;lineups.player;periods;state;scores;league"
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
        # Sportmonks livescores often expose the clock through periods rather than fixture.minute.
        minute = m.get("minute")
        periods = m.get("periods") or []
        active_periods = [p for p in periods if p.get("ticking") is True]
        if minute is None and active_periods:
            current_period = max(active_periods, key=lambda p: (p.get("sort_order") or 0))
            minute = current_period.get("minutes")
        if minute is None and periods:
            # Last resort: use the most recently ordered period only if it has a current minute.
            ordered_periods = sorted(periods, key=lambda p: (p.get("sort_order") or 0))
            for period in reversed(ordered_periods):
                if period.get("minutes") is not None and period.get("ended") is None:
                    minute = period.get("minutes")
                    break
        normalized.append({
            "fixture": {"id": m.get("id"), "date": m.get("starting_at"),
                        "status": {"long": state_name, "short": state.get("short_name"), "elapsed": minute}},
            "teams": {"home": {"name": home or "Ev sahibi"}, "away": {"name": away or "Deplasman"}},
            "goals": {"home": hg, "away": ag},
            "league": {"name": (m.get("league") or {}).get("name", "Sportmonks ligi"),
                       "country": (m.get("league") or {}).get("country", {}).get("name", "") if isinstance((m.get("league") or {}).get("country"), dict) else ""},
            "_source": "Sportmonks", "_sportmonks_raw": m
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

@st.cache_data(ttl=90, show_spinner=False)
def sportmonks_fixture_detail(fixture_id):
    """Fetch a fixture detail response; unlike livescores, fixture endpoints support full includes."""
    if not SPORTMONKS_API_TOKEN:
        return None, "Sportmonks token eklenmedi."
    try:
        response = requests.get(
            f"https://api.sportmonks.com/v3/football/fixtures/{fixture_id}",
            params={"api_token": SPORTMONKS_API_TOKEN,
                    "include": "participants;scores;events;lineups.player;statistics.type;periods;state;league"},
            timeout=18,
        )
        if response.status_code != 200:
            return None, f"Sportmonks maç ayrıntısı HTTP {response.status_code}: {response.text[:220]}"
        payload = response.json()
        return payload.get("data"), None
    except (requests.RequestException, ValueError) as exc:
        return None, f"Sportmonks maç ayrıntısı bağlantı hatası: {exc}"

@st.cache_data(ttl=60, show_spinner=False)
def sportmonks_live_odds(fixture_id):
    """Use the dedicated in-play odds endpoint, never the livescores include parameter."""
    if not SPORTMONKS_API_TOKEN:
        return None, "Sportmonks token eklenmedi."
    try:
        response = requests.get(
            f"https://api.sportmonks.com/v3/football/odds/inplay/fixtures/{fixture_id}",
            params={"api_token": SPORTMONKS_API_TOKEN, "include": "market;bookmaker"},
            timeout=18,
        )
        if response.status_code in (401, 403, 402):
            return None, "Sportmonks canlı oran erişimi hesabınızın paketinde açık değil. Ücretsiz plan canlı oranları kapsamıyor; gerçek oran olmadan bahis seçimi üretilemez."
        if response.status_code != 200:
            return None, f"Sportmonks canlı oranları HTTP {response.status_code}: {response.text[:220]}"
        payload = response.json()
        return payload.get("data", []), None
    except (requests.RequestException, ValueError) as exc:
        return None, f"Sportmonks canlı oran bağlantı hatası: {exc}"

def num(value):
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").replace(",", "."))
    except (ValueError, TypeError):
        return None

def stat_value(rows, names):
    """Read provider stat labels with common API-Football/Sportmonks aliases."""
    aliases = {
        "Shots on Goal": {"shots on goal", "shots on target", "on target", "isabetli şut"},
        "Total Shots": {"total shots", "shots", "şutlar", "toplam şut"},
        "Corner Kicks": {"corner kicks", "corners", "korner", "kornerler"},
        "Ball Possession": {"ball possession", "ball possession %", "possession", "topla oynama"},
        "Expected Goals": {"expected goals", "expected_goals", "xg", "beklenen gol (xg)"},
        "Shots off Goal": {"shots off goal", "shots off target", "off target"},
        "Fouls": {"fouls", "fauls", "faul"},
        "Yellow Cards": {"yellow cards", "yellowcard", "sarı kart"},
        "Red Cards": {"red cards", "redcard", "kırmızı kart"},
    }
    targets = set()
    for name in names:
        targets.add(str(name).strip().lower())
        targets.update(aliases.get(name, set()))
    for row in rows or []:
        label = str(row.get("type", "")).strip().lower()
        if label in targets:
            value = num(row.get("value"))
            if value is not None:
                return value
    return None

def tr_status(status):
    return STATUS_TR.get(status or "", status or "Bilinmiyor")

def show_stats(fixture_id, match):
    if match.get("_source") == "Sportmonks":
        raw = match.get("_sportmonks_raw") or {}
        if not raw.get("statistics"):
            raw_detail, detail_err = sportmonks_fixture_detail(fixture_id)
            if raw_detail:
                raw = raw_detail
        participants = raw.get("participants") or []
        team_names = {}
        for part in participants:
            meta = part.get("meta") or {}
            loc = str(meta.get("location", "")).lower()
            team_names[part.get("id")] = part.get("name") or ("Ev sahibi" if loc == "home" else "Deplasman")
        grouped = {}
        for item in raw.get("statistics") or []:
            pid = item.get("participant_id")
            team_name = team_names.get(pid)
            if not team_name:
                team_name = (item.get("participant") or {}).get("name") or str(pid or "Takım")
            dtype = item.get("type") or {}
            value_obj = item.get("data") or {}
            value = value_obj.get("value", item.get("value"))
            grouped.setdefault(team_name, []).append({"type": dtype.get("name", "İstatistik"), "value": value})
        if len(grouped) < 2:
            st.warning("Sportmonks bu maç için iki takımın istatistiklerini henüz döndürmedi.")
            return None
        names = list(grouped.keys())
        data = [{"team": {"name": name}, "statistics": grouped[name]} for name in names[:2]]
        home_name = match.get("teams", {}).get("home", {}).get("name", names[0])
        away_name = match.get("teams", {}).get("away", {}).get("name", names[1])
        # Keep home/away order based on participant metadata, not API response order.
        home_part = next((p.get("name") for p in participants if str((p.get("meta") or {}).get("location", "")).lower()=="home"), home_name)
        away_part = next((p.get("name") for p in participants if str((p.get("meta") or {}).get("location", "")).lower()=="away"), away_name)
        by_name = {d["team"]["name"]: d for d in data}
        data = [by_name.get(home_part, data[0]), by_name.get(away_part, data[1])]
        st.info("İstatistikler Sportmonks maç verisinden alındı.")
    else:
        data, err, _ = api_get("fixtures/statistics", {"fixture": fixture_id})
        if not data or len(data) < 2:
            if err: st.error(f"API-Football istatistik isteği: {err}")
            st.warning("Bu maç için istatistik sağlayıcıdan gelmedi; veri uydurulmadı.")
            return None
        teams = match.get("teams", {})
        home_name = teams.get("home", {}).get("name", data[0].get("team", {}).get("name", "Ev sahibi"))
        away_name = teams.get("away", {}).get("name", data[1].get("team", {}).get("name", "Deplasman"))
    rows_for_table = []
    for team in data:
        for item in team.get("statistics", []):
            label = item.get("type", "Diğer")
            rows_for_table.append({"İstatistik": STAT_TR.get(label, label), team.get("team", {}).get("name", "Takım"): item.get("value") if item.get("value") is not None else "—"})
    if rows_for_table:
        st.subheader("Maç istatistikleri")
        st.dataframe(rows_for_table, use_container_width=True, hide_index=True)
    return {"home_name": home_name, "away_name": away_name,
            "home_rows": data[0].get("statistics", []), "away_rows": data[1].get("statistics", [])}

def show_lineups(fixture_id, match=None):
    if match and match.get("_source") == "Sportmonks":
        raw = match.get("_sportmonks_raw") or {}
        if not raw.get("lineups"):
            detail, err = sportmonks_fixture_detail(fixture_id)
            if detail: raw = detail
        participants = raw.get("participants") or []
        names = {p.get("id"): p.get("name", "Takım") for p in participants}
        grouped = {}
        for entry in raw.get("lineups") or []:
            pid = entry.get("participant_id") or entry.get("team_id")
            team_name = names.get(pid) or (entry.get("team") or {}).get("name") or "Takım"
            player = entry.get("player") or {}
            pname = player.get("display_name") or player.get("name")
            if not pname: continue
            kind = str((entry.get("type") or {}).get("name", "")).lower()
            slot = grouped.setdefault(team_name, {"team":{"name":team_name}, "formation":None, "startXI":[], "substitutes":[]})
            player_obj = {"player":{"name":pname}}
            if any(word in kind for word in ("substitute", "bench", "yedek")):
                slot["substitutes"].append(player_obj)
            else:
                slot["startXI"].append(player_obj)
        data = list(grouped.values())
        if not data:
            st.warning("Sportmonks bu maç için kadroyu henüz döndürmedi. Kadro açıklanmamış olabilir.")
            return
        st.info("Kadro verisi Sportmonks üzerinden alındı.")
    else:
        data, err, _ = api_get("fixtures/lineups", {"fixture": fixture_id})
        if not data and err: st.error(f"Kadro isteği: {err}")
        if not data:
            st.warning("Kadro verisi bu maç için henüz mevcut değil.")
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

def show_odds(fixture_id, match=None):
    if match and match.get("_source") == "Sportmonks":
        data, err = sportmonks_live_odds(fixture_id)
        if err:
            st.warning(err)
            return []
        rows = []
        for item in data or []:
            odd = num(item.get("value", item.get("dp3")))
            if odd is None or odd <= 1 or item.get("stopped") or item.get("suspended"):
                continue
            market = (item.get("market") or {}).get("name") or item.get("market_description") or "Pazar"
            bookmaker = (item.get("bookmaker") or {}).get("name") or f"Sağlayıcı #{item.get('bookmaker_id', '—')}"
            option = item.get("label") or item.get("name") or "Seçenek"
            market_tr = translate_market(market)
            option_tr = translate_option(option)
            rows.append({"Pazar": market_tr, "Seçenek": option_tr, "Oran": odd,
                         "Oranın ham olasılığı (%)": round(100/odd, 1),
                         "_odd": odd, "_market": market_tr, "_option": option_tr, "_bookmaker": bookmaker})
        if not rows:
            st.info("Sportmonks canlı oran uç noktası yanıt verdi ancak bu maç için kullanılabilir oran yok. Ücretsiz hesapta canlı oran erişimi olmayabilir.")
            return []
        st.subheader("Sportmonks canlı oranları")
        st.dataframe([{k:v for k,v in row.items() if not k.startswith('_')} for row in rows], use_container_width=True, hide_index=True)
        show_odds_comparison(rows)
        return rows
    data, err, _ = api_get("odds", {"fixture": fixture_id})
    if err:
        st.error(f'Oran isteği başarısız: {err}')
        return []
    if not data:
        st.info("Bu maç için API-Football oranı bulunamadı. Ücretsiz günlük kota ve pazar kapsamı sınırlı olabilir.")
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
                    row = {"Pazar": market_tr, "Seçenek": translated_option, "Oran": option.get("odd", "—"),
                           "Oranın ham olasılığı (%)": round(implied, 1) if implied is not None else "—",
                           "_odd": odd, "_market": market_tr, "_option": translated_option,
                           "_bookmaker": bookmaker.get("name", "Bilinmiyor")}
                    rows.append(row); all_rows.append(row)
                if rows:
                    with st.expander(market_tr):
                        st.dataframe([{k:v for k,v in row.items() if not k.startswith("_")} for row in rows], use_container_width=True, hide_index=True)
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


def poisson_at_least_one(lam):
    """Probability of one or more events under a Poisson approximation."""
    return 1 - math.exp(-max(0.0, lam))


def estimate_live_signals(match, stats):
    """Transparent experimental estimates; not calibrated probabilities or betting advice."""
    status = match.get("fixture", {}).get("status", {})
    minute = num(status.get("elapsed"))
    if minute is None:
        return {"note": "Dakika verisi yok; canlı kısa-vade tahmini üretilemedi."}
    minute = min(120.0, max(1.0, minute))
    hr = stats.get("home_rows", []) if stats else []
    ar = stats.get("away_rows", []) if stats else []
    h_on, a_on = stat_value(hr, ["Shots on Goal"]), stat_value(ar, ["Shots on Goal"])
    h_sh, a_sh = stat_value(hr, ["Total Shots"]), stat_value(ar, ["Total Shots"])
    h_cor, a_cor = stat_value(hr, ["Corner Kicks"]), stat_value(ar, ["Corner Kicks"])
    h_xg, a_xg = stat_value(hr, ["Expected Goals"]), stat_value(ar, ["Expected Goals"])

    # Shrink observed corner pace toward a conservative generic prior to reduce small-sample noise.
    corner_total = (h_cor + a_cor) if h_cor is not None and a_cor is not None else None
    if corner_total is not None:
        observed_rate = corner_total / minute
        weight = minute / (minute + 30.0)
        blended_rate = (0.09 * (1 - weight)) + (observed_rate * weight)
        next10_corner = poisson_at_least_one(blended_rate * 10.0)
    else:
        next10_corner = None

    # Baseline short-window goal hazard, with only a modest adjustment from pressure signals.
    pressure_home = 0.0
    pressure_away = 0.0
    pressure_count = 0
    if h_xg is not None and a_xg is not None:
        pressure_home += max(0.0, h_xg) + 0.25
        pressure_away += max(0.0, a_xg) + 0.25
        pressure_count += 1
    if h_on is not None and a_on is not None:
        pressure_home += max(0.0, h_on) * 0.45 + 0.5
        pressure_away += max(0.0, a_on) * 0.45 + 0.5
        pressure_count += 1
    if h_sh is not None and a_sh is not None:
        pressure_home += max(0.0, h_sh) * 0.08 + 0.5
        pressure_away += max(0.0, a_sh) * 0.08 + 0.5
        pressure_count += 1
    if pressure_count:
        total_pressure = pressure_home + pressure_away
        home_share = pressure_home / total_pressure if total_pressure else 0.5
        away_share = 1 - home_share
        # Strong shrinkage toward even chances; the provider stats are noisy and not calibrated.
        home_share = 0.5 + (home_share - 0.5) * 0.65
        away_share = 1 - home_share
    else:
        home_share = away_share = 0.5

    # Heuristic short-horizon chance of any goal; not learned from historical matches.
    goal_rate_per_minute = 0.025
    if h_xg is not None and a_xg is not None:
        xg_rate = (h_xg + a_xg) / minute
        goal_rate_per_minute = 0.018 + min(0.025, max(0.0, xg_rate) * 0.20)
    next10_goal = poisson_at_least_one(goal_rate_per_minute * 10.0)
    home_next_goal = next10_goal * home_share
    away_next_goal = next10_goal * away_share
    return {
        "minute": int(minute), "corner_total": corner_total,
        "next10_corner_pct": round(next10_corner * 100) if next10_corner is not None else None,
        "next10_goal_pct": round(next10_goal * 100),
        "home_next_goal_pct": round(home_next_goal * 100),
        "away_next_goal_pct": round(away_next_goal * 100),
        "home_share_pct": round(home_share * 100), "away_share_pct": round(away_share * 100),
        "data_points": pressure_count,
    }


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

    st.markdown("### ⏱️ Kısa vadeli olasılık tahminleri")
    live_est = estimate_live_signals(match, stats)
    if live_est.get("next10_goal_pct") is not None:
        p1, p2, p3 = st.columns(3)
        p1.metric("Önümüzdeki 10 dk. en az 1 gol", f"%{live_est['next10_goal_pct']}")
        p2.metric(f"Ev sahibinin sonraki gol payı", f"%{live_est['home_share_pct']}")
        p3.metric(f"Deplasmanın sonraki gol payı", f"%{live_est['away_share_pct']}")
        if live_est.get("next10_corner_pct") is not None:
            st.metric("Önümüzdeki 10 dk. en az 1 korner", f"%{live_est['next10_corner_pct']}")
        st.caption("Deneysel başlangıç tahmini: genel oran varsayımı ve mevcut maç istatistikleri kullanılır. Geçmiş maçlarda kalibre edilmediği için gerçek kazanma olasılığı veya bahis tavsiyesi değildir. Korner tahmini için iki takımın korner sayısı gerekir.")
    else:
        st.info(live_est.get("note", "Canlı tahmin için yeterli veri yok."))

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
    """Fetch public RSS headlines for both teams; never claims to read all websites/social media."""
    query = quote_plus(f'("{home_name}" OR "{away_name}") (football OR futbol OR injury OR lineup OR sakatlık OR kadro)')
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 FutbolAnalizMerkezi/1.0"}, timeout=12)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            pub = item.findtext("pubDate", default="")
            source = item.findtext("source", default="Google Haberler")
            if title and link:
                items.append({"title": title, "source": source, "published": pub, "link": link})
        return items, None
    except Exception as exc:
        return [], f"Haber akışı şu an alınamadı: {exc}"

def summarize_news_headlines(items):
    """Explain headline-only signals with transparent keyword rules; no full-article or social scraping."""
    if not items:
        return {"tone":"Veri yok", "summary":"Erişilebilir başlık bulunamadı; haber etkisi hesaplanamadı.", "count":0}
    text_all = " ".join(i.get("title", "") for i in items).lower()
    groups = {
        "Olumsuz takım haberi": ["injury", "injured", "ruled out", "out for", "suspended", "sakat", "sakatlık", "cezalı", "oynamayacak", "ameliyat", "misses", "doubt", "şüpheli"],
        "Olumlu takım haberi": ["returns", "return to", "back in training", "fit again", "geri döndü", "takımla çalıştı", "kadrodaki yerini aldı", "ready to play"],
        "Kadro/teknik haber": ["lineup", "starting xi", "team news", "formation", "ilk 11", "kadrosu", "teknik direktör", "manager", "coach", "press conference", "basın toplantısı"],
        "Olağandışı/inceleme haberi": ["investigation", "match-fixing", "fixing", "betting probe", "şike", "soruşturma", "disiplin soruşturması", "integrity"],
    }
    found = {label: sum(1 for key in keys if key in text_all) for label, keys in groups.items()}
    active = [label for label, count in found.items() if count]
    if "Olağandışı/inceleme haberi" in active:
        tone = "İnceleme gerekli"
    elif "Olumsuz takım haberi" in active and "Olumlu takım haberi" in active:
        tone = "Karışık"
    elif "Olumsuz takım haberi" in active:
        tone = "Olumsuz haber işareti"
    elif "Olumlu takım haberi" in active:
        tone = "Olumlu haber işareti"
    elif "Kadro/teknik haber" in active:
        tone = "Kadro/teknik gündem"
    else:
        tone = "Belirgin sinyal yok"
    summary = "; ".join(active) if active else "Başlıklarda belirlenen anahtar sözcüklerle net kadro/sakatlık sinyali bulunmadı."
    return {"tone":tone, "summary":summary, "count":len(items), "counts":found}

def show_match_news(home_name, away_name, fixture_id):
    st.markdown("**📰 Haber ve gündem analizi**")
    st.caption("Takım adlarıyla eşleşen herkese açık Google Haberler RSS başlıkları arka planda taranır; başlıklar sana liste olarak dökülmez, kısa sinyal özeti gösterilir. Bu, tüm interneti veya özel sosyal medya yorumlarını kapsamaz.")
    with st.spinner("Maç haber başlıkları arka planda inceleniyor..."):
        items, err = fetch_team_news(home_name, away_name)
    if err:
        st.warning(err)
        return
    summary = summarize_news_headlines(items)
    c1, c2 = st.columns(2)
    c1.metric("Eşleşen başlık", summary["count"])
    c2.metric("Haber sinyali", summary["tone"])
    st.write("**Algoritmik özet:** " + summary["summary"])
    if summary.get("counts") and summary["counts"].get("Olağandışı/inceleme haberi"):
        st.warning("Bazı başlıklarda soruşturma/şike anahtar sözcükleri var. Bu bir iddia veya kanıt değildir; kaynak doğrulaması gerekir.")
    st.caption("Özet yalnızca RSS başlıklarına dayalı anahtar-sözcük sınıflandırmasıdır; tam haber metni ve sosyal medya duygu analizi değildir.")

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
            if c3.button("Oranları getir", key=f"{prefix}_odds_{fid}"):
                st.session_state[f"odds_{fid}"] = True
            if c4.button("Maçı analiz et", key=f"{prefix}_analyze_{fid}"):
                st.session_state[f"stats_{fid}"] = True
                st.session_state[f"odds_{fid}"] = True
                st.session_state[f"analyze_{fid}"] = True
            if is_sportmonks:
                st.caption("Sportmonks maçı: istatistik/kadro maç kimliğiyle doğrudan istenir. Canlı oranlar ayrı uç noktadan denenir; ücretsiz hesapta canlı oran erişimi kapalı olabilir.")
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
                odds = show_odds(fid, match)
            if st.session_state.get(f"analyze_{fid}"):
                if stats is None:
                    stats = show_stats(fid, match)
                if not odds:
                    odds = show_odds(fid, match)
                analyze_match(match, stats, odds)

live_tab, date_tab, info_tab = st.tabs(["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "ℹ️ Program hakkında"])
with live_tab:
    st.subheader("Şu anda oynanan maçlar")
    if st.button("Canlı maçları yükle / yenile"):
        with st.spinner("Canlı maçlar yükleniyor..."):
            if API_KEY:
                data, err, _ = api_get("fixtures", {"live": "all"})
            else:
                data, err = None, "API-Football anahtarı tanımlı değil."
            source = "API-Football"
            # Providers phrase exhausted quotas differently (e.g. "request limit for the day").
            err_text = str(err or "").lower()
            quota_exhausted = any(term in err_text for term in (
                "429", "ratelimit", "rate limit", "request limit", "daily limit",
                "limit for the day", "too many requests", "reached the request limit"
            ))
            if err and (quota_exhausted or not API_KEY):
                if SPORTMONKS_API_TOKEN:
                    sm_data, sm_err = sportmonks_live_matches()
                    if not sm_err and sm_data:
                        data = sportmonks_to_api_football(sm_data)
                        err = None
                        source = "Sportmonks (ücretsiz lig kapsamı sınırlı)"
                    elif sm_err:
                        err = f"API-Football kotası dolu. Sportmonks yedeği de kullanılamadı: {sm_err}"
                    else:
                        err = "API-Football kotası dolu; Sportmonks şu anda canlı maç döndürmedi. Ücretsiz kapsam sınırlıdır."
            elif not err and API_KEY and SPORTMONKS_API_TOKEN:
                # Merge additional Sportmonks live matches when API-Football is available.
                sm_data, sm_err = sportmonks_live_matches()
                if not sm_err and sm_data:
                    extra = sportmonks_to_api_football(sm_data)
                    def match_key(item):
                        ts = item.get("teams", {})
                        norm = lambda v: "".join(ch.lower() for ch in str(v or "") if ch.isalnum())
                        return tuple(sorted((norm((ts.get("home") or {}).get("name")), norm((ts.get("away") or {}).get("name")))))
                    seen = {match_key(m) for m in (data or [])}
                    merged = list(data or [])
                    for item in extra:
                        if match_key(item) not in seen:
                            merged.append(item); seen.add(match_key(item))
                    data = merged
                    source = "API-Football + Sportmonks (Sportmonks ücretsiz lig kapsamı sınırlı)"
                else:
                    err = "API-Football kotası dolu ve SPORTMONKS_API_TOKEN tanımlı değil. Streamlit Secrets bölümündeki anahtar adını kontrol et."
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
        with st.spinner("Fikstür kaynakları birleştiriliyor..."):
            primary, api_err, _ = api_get("fixtures", {"date": chosen.isoformat()}) if API_KEY else (None, "API-Football anahtarı tanımlı değil", None)
            primary = primary or []
            fd_matches, fd_err = football_data_matches_for_date(chosen.isoformat())
            oldb_matches, oldb_err = openligadb_matches_for_date(chosen.isoformat())
            combined = merge_fixture_sources(primary, (fd_matches or []) + (oldb_matches or []))
            st.session_state["date_matches"] = combined
            st.session_state["date_label"] = chosen.isoformat()
            st.session_state["date_sources"] = {
                "API-Football": len(primary), "football-data.org": len(fd_matches or []), "OpenLigaDB": len(oldb_matches or [])
            }
            st.session_state["date_errors"] = {
                "API-Football": api_err,
                "football-data.org": fd_err,
                "OpenLigaDB": oldb_err,
            }
    if "date_matches" in st.session_state:
        st.caption("Seçilen tarih: " + st.session_state.get("date_label", ""))
        counts = st.session_state.get("date_sources", {})
        st.caption("Kaynak katkıları: " + " · ".join(f"{name}: {count}" for name, count in counts.items()))
        errs = st.session_state.get("date_errors", {})
        if errs:
            with st.expander("Kaynak kontrolü — hangi kaynak neden veri vermedi?", expanded=True):
                for name, message in errs.items():
                    count = counts.get(name, 0)
                    if message:
                        st.warning(f"{name}: {count} maç. Ayrıntı: {message}")
                    else:
                        st.success(f"{name}: bağlantı yanıt verdi; {count} maç bulundu.")
                st.caption("Not: Bağlantının yanıt vermesi, o kaynağın tüm ligleri kapsadığı anlamına gelmez. API kotası doluysa kod bunu yükseltemez.")
        show_matches(st.session_state["date_matches"], "date")
with info_tab:
    st.subheader("Program hakkında")
    st.markdown("""
- Canlı maçlar ve tarih seçimine göre fikstür.
- Sağlayıcının sunduğu istatistiklerin Türkçe gösterimi.
- Mevcutsa kadro ve bahis oranları.
- Oranın ham olasılığı: 100 / oran. Bu, gerçek kazanma olasılığı değildir ve şirket marjını içerebilir.
- **Maçı analiz et** düğmesi mevcut istatistikleri ve oranları bir araya getirir; ayrıca kalibre edilmemiş deneysel kısa-vade gol/korner olasılığı gösterir.
- API çağrıları kısa süre önbelleğe alınır; sayfa yenilenince ücretsiz günlük limit gereksiz yere tüketilmez.
- İstatistik/kadro butonları API'nin veri döndürdüğü maçlarda sonuç gösterir; kapsama girmeyen maçlarda uygulama veri üretemez.
- Veri eksikse sistem bunu açıkça söyler; veri uydurmaz.
- Bu sürüm otomatik bahis yapmaz. Doğrulanmış tahmin modeli, açılış oranı geçmişi ve tüm liglerde son dakika hareketleri henüz mevcut değildir.
- Ek fikstür kaynakları: football-data.org (token ve plan kapsamına bağlı) ve OpenLigaDB (Almanya Bundesliga / 2. Bundesliga). Bu kaynaklar tarih fikstürünü genişletir; küresel canlı istatistik veya bahis oranı sağlamaz.
- Sportmonks ücretsiz planı sınırlı lig kapsamındadır; API-Football ücretsiz paketi günlük 100 istekle sınırlıdır. Kaynakları birleştirmek bu limitleri kaldırmaz. Sportmonks canlı oran erişimi ücretsiz planda açık olmayabilir. Haber özeti, herkese açık RSS başlıklarını anahtar-sözcüklerle sınıflandırır; tüm interneti veya sosyal medyayı kapsamaz. API anahtarlarını kodun içine yazmayın; Secrets bölümünde saklayın.
""")

# --- 10 kaynak için birleşik kaynak merkezi (yetkili veri erişimi esaslı) ---
st.divider()
st.header("🌐 Türkiye + Dünya Futbol Kaynak Merkezi")
st.caption("Nesine, Misli, Bilyoner, Oley, Tuttur, Maçkolik, Sahadan, Flashscore, Sofascore ve FotMob bağlantılarını tek yerde toplar. Bir web bağlantısının bulunması, sitenin canlı verisinin otomatik çekildiği anlamına gelmez.")

SOURCE_CATALOG = [
    {"Kaynak": "Nesine", "Tür": "Türkiye bahis/oran", "url": "https://www.nesine.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Misli", "Tür": "Türkiye bahis/oran", "url": "https://www.misli.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Bilyoner", "Tür": "Türkiye bahis/oran", "url": "https://www.bilyoner.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Oley", "Tür": "Türkiye bahis/oran", "url": "https://www.oley.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Tuttur", "Tür": "Türkiye bahis/oran", "url": "https://www.tuttur.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Maçkolik", "Tür": "Skor/istatistik/oran", "url": "https://www.mackolik.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Sahadan", "Tür": "Skor/istatistik", "url": "https://www.sahadan.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Flashscore", "Tür": "Canlı skor/istatistik", "url": "https://www.flashscore.com/", "access": "Resmî otomatik veri erişimi ayrıca doğrulanmalı"},
    {"Kaynak": "Sofascore", "Tür": "Canlı skor/istatistik", "url": "https://www.sofascore.com/", "access": "Genel kullanıma açık resmî API varsayılmamalı"},
    {"Kaynak": "FotMob", "Tür": "Canlı skor/istatistik", "url": "https://www.fotmob.com/", "access": "Otomatik erişim yöntemi ve izin durumu doğrulanmalı"},
]

with st.expander("10 kaynağın bağlantı ve erişim durumu", expanded=True):
    for _src in SOURCE_CATALOG:
        _c1, _c2, _c3 = st.columns([1.15, 1.45, 3.4])
        _c1.markdown(f"**[{_src['Kaynak']}]({_src['url']})**")
        _c2.write(_src["Tür"])
        _c3.caption(_src["access"])

st.subheader("Oranları tek tabloda birleştirmek için veri içe aktar")
st.write("Kaynaklardan izinli olarak dışa aktardığın oranları aşağıdaki sütunlarla CSV biçiminde yapıştırabilirsin. Bu alan, site verisini kendiliğinden çekmez; girilen kayıtları normalize edip aynı tabloda gösterir.")
st.code("kaynak,mac,market,secim,oran,zaman\\nNesine,Galatasaray - Fenerbahçe,1X2,1,2.10,2026-10-11 20:00", language="csv")
_odds_text = st.text_area("CSV oran verisi", key="source_hub_odds_csv", height=130, placeholder="kaynak,mac,market,secim,oran,zaman\nNesine,Ev Sahibi - Deplasman,1X2,1,2.10,2026-10-11 20:00")
if st.button("Oran tablosunu oluştur", key="source_hub_parse_odds"):
    import pandas as _pd
    from io import StringIO as _StringIO
    try:
        _df = _pd.read_csv(_StringIO(_odds_text.strip()))
        _required = {"kaynak", "mac", "market", "secim", "oran"}
        _missing = _required - {str(c).strip().lower() for c in _df.columns}
        if _missing:
            st.error("Eksik sütunlar: " + ", ".join(sorted(_missing)) + ". Gerekli sütunlar: kaynak, mac, market, secim, oran.")
        else:
            _df.columns = [str(c).strip().lower() for c in _df.columns]
            _df["oran"] = _pd.to_numeric(_df["oran"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            _df = _df.dropna(subset=["oran"])
            _df = _df[_df["oran"] > 1.0]
            if _df.empty:
                st.warning("Geçerli oran kaydı bulunamadı. Oranlar 1.00'dan büyük sayısal değer olmalı.")
            else:
                st.session_state["source_hub_odds_table"] = _df
                st.success(f"{len(_df)} geçerli oran kaydı tabloya alındı.")
    except Exception as _e:
        st.error(f"CSV okunamadı: {_e}")

if "source_hub_odds_table" in st.session_state:
    _odds_df = st.session_state["source_hub_odds_table"]
    st.dataframe(_odds_df, use_container_width=True, hide_index=True)
    if {"mac", "market", "secim", "oran"}.issubset(set(_odds_df.columns)):
        st.caption("Aynı maç/market/seçim için en yüksek girilmiş oran:")
        _best_df = _odds_df.sort_values("oran", ascending=False).drop_duplicates(["mac", "market", "secim"])
        st.dataframe(_best_df, use_container_width=True, hide_index=True)

st.info("Bu merkez ilk entegrasyon katmanıdır. 10 sitenin tamamından otomatik canlı veri alındığı iddiasında bulunmaz. Otomatik bağlantılar ancak resmî API, izinli veri akışı veya doğrulanmış erişim sağlandığında etkinleştirilmelidir. Mevcut Sportmonks, API-Football, football-data.org ve OpenLigaDB bağlantıları uygulamanın önceki bölümlerinde ayrı çalışır.")
