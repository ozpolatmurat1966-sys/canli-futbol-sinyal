import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
from datetime import date
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

st.set_page_config(page_title="Futbol Analiz Merkezi", page_icon="⚽", layout="wide")

st.markdown("""
<style>
:root { color-scheme: light; }
.stApp { background: #f4f6f8; color: #202a35; }
[data-testid="stHeader"] { background: rgba(255,255,255,.96); border-bottom: 1px solid #e5e9ee; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e2e7ec; }
[data-testid="stSidebar"] * { color: #263443; }
h1, h2, h3, h4 { color: #172b3a !important; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #344454; }
div[data-testid="stMetric"] {
  background: #ffffff; border: 1px solid #e1e7ec; border-top: 3px solid #e53238;
  border-radius: 8px; padding: .75rem; box-shadow: 0 1px 3px rgba(20,35,50,.04);
}
div[data-testid="stExpander"] { background: #ffffff; border: 1px solid #e1e7ec; border-radius: 8px; }
div[data-testid="stTabs"] button[role="tab"] { color: #4b5967; font-weight: 600; }
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color: #d9212b; border-bottom-color: #d9212b;
}
.stButton > button {
  border-radius: 7px; border: 1px solid #d9212b; background: #d9212b;
  color: #ffffff; font-weight: 650; min-height: 2.5rem;
}
.stButton > button:hover { background: #b91c25; border-color: #b91c25; color: #ffffff; }
.stButton > button:focus { box-shadow: 0 0 0 .2rem rgba(217,33,43,.18); }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  background: #ffffff; border: 1px solid #e1e7ec; border-radius: 8px;
}
input, textarea, [data-baseweb="select"] > div {
  background-color: #ffffff !important; color: #202a35 !important; border-color: #d7dfe6 !important;
}
[data-testid="stAlert"] { border-radius: 8px; }
hr { border-color: #e1e7ec; }
</style>
""", unsafe_allow_html=True)


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

API_KEY = ""  # Eski API sağlayıcısı devre dışı; dış istek yapılmaz.
FIVE_DOLLAR_FOOTBALL_API_KEY = str(secret("FIVE_DOLLAR_FOOTBALL_API_KEY", "")).strip()
FOOTBALL_DATA_TOKEN = str(secret("FOOTBALL_DATA_TOKEN", "")).strip()
SPORTMONKS_API_TOKEN = str(secret("SPORTMONKS_API_TOKEN", "")).strip()
BSD_API_TOKEN = str(secret("BSD_API_TOKEN", "")).strip()
THESPORTSDB_API_KEY = str(secret("THESPORTSDB_API_KEY", "123")).strip() or "123"
APIFOOTBALL_API_KEY = str(secret("APIFOOTBALL_API_KEY", "")).strip()
API_FOOTBALL_V3_KEY = ""  # Askıya alınan API-Football v3 hesabına bağımlılık kaldırıldı.

# Provider health is session-local; never display credentials.
def set_provider_status(name, configured, ok=None, detail=None):
    statuses = st.session_state.setdefault("provider_statuses", {})
    previous = statuses.get(name, {})
    statuses[name] = {
        "configured": bool(configured),
        "ok": ok if ok is not None else previous.get("ok"),
        "detail": detail if detail is not None else previous.get("detail", "Henüz test edilmedi"),
        "checked_at": datetime.now().strftime("%H:%M:%S") if ok is not None or detail is not None else previous.get("checked_at", "—"),
    }

def provider_status_table():
    statuses = st.session_state.get("provider_statuses", {})
    rows = []
    for name, configured in [
        ("API-Football", bool(API_KEY)),
        ("APIFootball.com", bool(APIFOOTBALL_API_KEY)),
        ("5DollarFootballAPI", bool(FIVE_DOLLAR_FOOTBALL_API_KEY)),
        ("Sportmonks", bool(SPORTMONKS_API_TOKEN)),
        ("football-data.org", bool(FOOTBALL_DATA_TOKEN)),
        ("Bzzoiro Sports Data", bool(BSD_API_TOKEN)),
        ("SportScore", True),
        ("OpenFootAPI", True),
        ("TheSportsDB", True),
        ("ESPN", True),
        ("OpenLigaDB", True),
    ]:
        item = statuses.get(name, {})
        ok = item.get("ok")
        state = ("Hazır — henüz test edilmedi" if configured and ok is None else
                 "Yanıt veriyor" if ok is True else
                 "Hata / kota" if ok is False else "Anahtar gerekli")
        rows.append({"Kaynak": name, "Durum": state, "Son kontrol": item.get("checked_at", "—"),
                     "Ayrıntı": item.get("detail", "Henüz test edilmedi")})
    st.dataframe(rows, use_container_width=True, hide_index=True)

for _name, _configured in [
    ("API-Football", bool(API_KEY)), ("APIFootball.com", bool(APIFOOTBALL_API_KEY)), ("5DollarFootballAPI", bool(FIVE_DOLLAR_FOOTBALL_API_KEY)), ("Sportmonks", bool(SPORTMONKS_API_TOKEN)),
    ("football-data.org", bool(FOOTBALL_DATA_TOKEN)), ("Bzzoiro Sports Data", bool(BSD_API_TOKEN)), ("ESPN", True), ("OpenLigaDB", True)
]:
    set_provider_status(_name, _configured)

st.title("⚽ Futbol Analiz Merkezi")
st.caption("Canlı maçlar • Fikstür • İstatistikler • Oranlar • Veri temelli değerlendirme")
st.warning("Bu uygulama otomatik bahis oynamaz ve kazancı garanti etmez. Yalnızca veri temelli değerlendirme sunar. Veriler eksikse doğru karar 'Pas geç' olabilir.")

if not SPORTMONKS_API_TOKEN:
    st.info("Sportmonks anahtarı tanımlı değil. ESPN, OpenLigaDB ve TheSportsDB gibi ücretsiz/açık kaynaklar denenir; canlı maç ve lig kapsamı sınırlı olabilir.")

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
            message = f"HTTP {r.status_code}{quota_note}: {r.text[:220]}"
            set_provider_status("API-Football", True, False, message)
            return None, message, None
        payload = r.json()
        if payload.get("errors"):
            message = f"API hatası{quota_note}: {payload['errors']}"
            set_provider_status("API-Football", True, False, message[:180])
            return None, message, payload
        set_provider_status("API-Football", True, True, f"HTTP 200{quota_note}; yanıt alındı.")
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
            message = f"football-data.org HTTP {response.status_code}: {response.text[:180]}"
            set_provider_status("football-data.org", True, False, message)
            return None, message
        payload = response.json()
        set_provider_status("football-data.org", True, True, "HTTP 200; yanıt alındı.")
        return payload, None
    except (requests.RequestException, ValueError) as exc:
        message = f"football-data.org bağlantı hatası: {exc}"
        set_provider_status("football-data.org", True, False, message[:180])
        return None, message


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

@st.cache_data(ttl=1800, show_spinner=False)
def thesportsdb_matches_for_date(date_text):
    """Free TheSportsDB schedule supplement; fixture metadata only, not live advanced stats."""
    try:
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}/eventsday.php",
            params={"d": date_text, "s": "Soccer"}, timeout=12
        )
        if response.status_code != 200:
            message = f"TheSportsDB HTTP {response.status_code}"
            set_provider_status("TheSportsDB", True, False, message)
            return [], message
        payload = response.json()
        events = payload.get("events") or []
        out = []
        for item in events:
            home, away = item.get("strHomeTeam"), item.get("strAwayTeam")
            if not home or not away:
                continue
            status_raw = (item.get("strStatus") or "").strip()
            try:
                gh = int(item.get("intHomeScore")) if item.get("intHomeScore") not in (None, "") else None
            except (TypeError, ValueError):
                gh = None
            try:
                ga = int(item.get("intAwayScore")) if item.get("intAwayScore") not in (None, "") else None
            except (TypeError, ValueError):
                ga = None
            status_lower = status_raw.lower()
            if any(x in status_lower for x in ("finished", "ft", "match over")):
                short, long_status = "FT", "Maç Bitti"
            elif any(x in status_lower for x in ("live", "in progress", "1h", "2h", "half")):
                short, long_status = ("HT", "Devre Arası") if "half" in status_lower else ("LIVE", "Canlı")
            elif any(x in status_lower for x in ("postponed", "cancelled", "canceled")):
                short, long_status = "PST", "Ertelendi / İptal"
            else:
                short, long_status = "NS", "Başlamadı"
            event_date = item.get("strTimestamp") or item.get("dateEvent") or date_text
            if item.get("strTime") and "T" not in str(event_date):
                event_date = f"{event_date}T{item.get('strTime')}"
            out.append({
                "fixture": {"id": f"tsdb-{item.get('idEvent')}", "date": event_date,
                            "timestamp": None, "status": {"long": long_status, "short": short, "elapsed": None}},
                "league": {"id": item.get("idLeague"), "name": item.get("strLeague") or "TheSportsDB", "country": item.get("strCountry") or ""},
                "teams": {"home": {"id": item.get("idHomeTeam"), "name": home, "logo": item.get("strHomeTeamBadge")},
                          "away": {"id": item.get("idAwayTeam"), "name": away, "logo": item.get("strAwayTeamBadge")}},
                "goals": {"home": gh, "away": ga},
                "_source": "TheSportsDB", "_raw_supplemental": item
            })
        set_provider_status("TheSportsDB", True, True, f"HTTP 200; {len(out)} maç kaydı.")
        return out, None if out else "TheSportsDB yanıt verdi ancak bu tarihte futbol maçı döndürmedi."
    except (requests.RequestException, ValueError) as exc:
        message = f"TheSportsDB bağlantı hatası: {exc}"
        set_provider_status("TheSportsDB", True, False, message[:180])
        return [], message

@st.cache_data(ttl=900, show_spinner=False)
def thesportsdb_event_detail(event_id, endpoint):
    """Fetch a selected TheSportsDB event's available stats, lineup, or timeline."""
    allowed = {"lookupeventstats.php", "lookuplineup.php", "lookuptimeline.php"}
    if endpoint not in allowed or not str(event_id).isdigit():
        return None, "Geçersiz TheSportsDB maç kimliği veya uç noktası."
    try:
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}/{endpoint}",
            params={"id": str(event_id)}, timeout=12
        )
        if response.status_code != 200:
            message = f"TheSportsDB HTTP {response.status_code}"
            set_provider_status("TheSportsDB", True, False, message)
            return None, message
        payload = response.json()
        set_provider_status("TheSportsDB", True, True, "Maç detay uç noktası yanıt verdi.")
        return payload, None
    except (requests.RequestException, ValueError) as exc:
        message = f"TheSportsDB bağlantı hatası: {exc}"
        set_provider_status("TheSportsDB", True, False, message[:180])
        return None, message

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

@st.cache_data(ttl=45, show_spinner=False)
def openligadb_live_matches():
    """Detect plausibly active German Bundesliga matches from the public OpenLigaDB feed."""
    now_utc = datetime.now(timezone.utc)
    today_text = now_utc.date().isoformat()
    season = now_utc.year if now_utc.month >= 7 else now_utc.year - 1
    out, errors, successful = [], [], 0
    for shortcut, league_name in (("bl1", "Almanya Bundesliga"), ("bl2", "Almanya 2. Bundesliga")):
        try:
            response = requests.get(
                f"https://api.openligadb.de/getmatchdata/{shortcut}/{season}",
                timeout=12, headers={"User-Agent": "FutbolAnalizMerkezi/1.0"}
            )
            if response.status_code != 200:
                errors.append(f"{shortcut}: HTTP {response.status_code}")
                continue
            matches = response.json()
            successful += 1
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{shortcut}: {exc}")
            continue
        for item in matches if isinstance(matches, list) else []:
            if item.get("matchIsFinished") is True:
                continue
            kickoff_text = item.get("matchDateTimeUTC") or item.get("matchDateTime")
            if not kickoff_text:
                continue
            try:
                kickoff = datetime.fromisoformat(str(kickoff_text).replace("Z", "+00:00"))
                if kickoff.tzinfo is None:
                    from zoneinfo import ZoneInfo
                    kickoff = kickoff.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                kickoff = kickoff.astimezone(timezone.utc)
                elapsed = int((now_utc - kickoff).total_seconds() // 60)
            except (TypeError, ValueError):
                continue
            # Never promote future or old unfinished fixtures to live.
            if elapsed < 0 or elapsed > 125:
                continue
            t1, t2 = item.get("team1") or {}, item.get("team2") or {}
            home, away = t1.get("teamName"), t2.get("teamName")
            if not home or not away:
                continue
            goals_home = goals_away = 0
            for goal in item.get("goals") or []:
                try:
                    goals_home = max(goals_home, int(goal.get("scoreTeam1") or 0))
                    goals_away = max(goals_away, int(goal.get("scoreTeam2") or 0))
                except (TypeError, ValueError):
                    pass
            results = item.get("matchResults") or []
            if results:
                current_result = max(results, key=lambda r: int(r.get("resultOrderID") or 0))
                try:
                    goals_home = int(current_result.get("pointsTeam1", goals_home) or 0)
                    goals_away = int(current_result.get("pointsTeam2", goals_away) or 0)
                except (TypeError, ValueError):
                    pass
            short = "HT" if 45 <= elapsed < 60 else "LIVE"
            out.append({
                "fixture": {"id": f"openligadb-live-{item.get('matchID')}", "date": kickoff.isoformat(),
                            "status": {"long": "Devre Arası" if short == "HT" else "Canlı (dakika tahmini)",
                                       "short": short, "elapsed": min(elapsed, 90)}},
                "teams": {"home": {"id": t1.get("teamId"), "name": str(home)},
                          "away": {"id": t2.get("teamId"), "name": str(away)}},
                "goals": {"home": goals_home, "away": goals_away},
                "league": {"name": league_name, "country": "Almanya"},
                "_source": "OpenLigaDB", "_raw_openligadb": item
            })
    if successful == 0:
        message = "OpenLigaDB canlı sorgusu başarısız: " + "; ".join(errors)
        set_provider_status("OpenLigaDB", True, False, message[:180])
        return None, message
    set_provider_status("OpenLigaDB", True, True, f"HTTP 200; {len(out)} olası canlı Bundesliga maçı.")
    return out, None


@st.cache_data(ttl=90, show_spinner=False)
def espn_scoreboard_for_date(date_text, league_code):
    """Public ESPN scoreboard fallback; coverage is limited to selected competitions."""
    try:
        response = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard",
            params={"dates": (str(date_text) if len(str(date_text)) == 17 and str(date_text)[8] == "-" else str(date_text).replace("-", "")), "limit": 500},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15
        )
        if response.status_code != 200:
            message = f"ESPN HTTP {response.status_code}"
            set_provider_status("ESPN", True, False, message)
            return [], message
        payload = response.json()
        out = []
        for event in payload.get("events", []):
            competitions = event.get("competitions") or []
            if not competitions:
                continue
            comp = competitions[0]
            competitors = comp.get("competitors") or []
            home = next((x for x in competitors if x.get("homeAway") == "home"), None)
            away = next((x for x in competitors if x.get("homeAway") == "away"), None)
            if not home and competitors:
                home = competitors[0]
            if not away and len(competitors) > 1:
                away = competitors[1]
            if not home or not away:
                continue
            status = (comp.get("status") or {}).get("type") or {}
            status_name = status.get("name", "STATUS_SCHEDULED")
            status_map = {"STATUS_SCHEDULED":"NS", "STATUS_IN_PROGRESS":"LIVE",
                          "STATUS_HALFTIME":"HT", "STATUS_FINAL":"FT",
                          "STATUS_FULL_TIME":"FT", "STATUS_POSTPONED":"PST",
                          "STATUS_CANCELED":"CANC"}
            short = status_map.get(status_name, "NS")
            period = (comp.get("status") or {}).get("period", 0)
            # ESPN status can use newer / alternate names; retain the provider's
            # state rather than silently converting unknown active states to scheduled.
            if status_name in ("STATUS_IN_PROGRESS", "STATUS_FIRST_HALF", "STATUS_SECOND_HALF", "STATUS_EXTRA_TIME", "STATUS_PENALTY_SHOOTOUT"):
                short = "LIVE"
            elif status_name in ("STATUS_HALFTIME", "STATUS_END_PERIOD"):
                short = "HT"
            elif status_name in ("STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"):
                short = "FT"
            elif status_name in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED"):
                short = "PST" if "POSTPONED" in status_name else "CANC"
            # ESPN may leave a stale in-progress name on a completed event.
            # Its explicit completed flag / final description takes precedence.
            status_description = str(status.get("description") or "").strip().lower()
            status_detail = str(status.get("shortDetail") or "").strip().lower()
            if status.get("completed") is True or status_description in ("final", "full time", "after extra time", "after penalties") or status_detail in ("ft", "aet", "pen"):
                short = "FT"
            period = (comp.get("status") or {}).get("period", 0)
            display_clock = str((comp.get("status") or {}).get("displayClock") or "").strip()
            # Prefer ESPN's own clock where possible; do not label a completed
            # 90-minute match as live merely because period=2.
            minute = None
            if short == "LIVE":
                if display_clock and ":" in display_clock:
                    try:
                        elapsed_in_period = max(0, 45 - int(display_clock.split(":")[0]))
                        minute = int((period - 1) * 45 + elapsed_in_period) if period else elapsed_in_period
                    except (ValueError, TypeError):
                        minute = int(period * 45) if period else None
                else:
                    minute = int(period * 45) if period else None
            def score(team):
                value = team.get("score")
                try:
                    return int(value) if value not in (None, "") else None
                except (TypeError, ValueError):
                    return None
            home_score, away_score = score(home), score(away)
            out.append({
                "fixture": {"id": event.get("id"), "date": event.get("date"),
                            "timestamp": None, "status": {"long": status.get("description", status_name),
                            "short": short, "elapsed": minute}},
                "league": {"id": None, "name": (payload.get("leagues") or [{}])[0].get("name", league_code),
                           "country": "", "logo": None, "round": ""},
                "teams": {"home": {"id": None, "name": home.get("team", {}).get("displayName", "Ev Sahibi"),
                                   "logo": home.get("team", {}).get("logo")},
                          "away": {"id": None, "name": away.get("team", {}).get("displayName", "Deplasman"),
                                   "logo": away.get("team", {}).get("logo")}},
                "goals": {"home": home_score, "away": away_score},
                "score": {"halftime": {"home": None, "away": None},
                          "fulltime": {"home": home_score, "away": away_score}},
                "source": "ESPN", "_source": "ESPN"
            })
        set_provider_status("ESPN", True, True, f"{league_code}: {len(out)} maç kaydı.")
        return out, None
    except (requests.RequestException, ValueError, TypeError) as exc:
        message = f"ESPN bağlantı hatası: {exc}"
        set_provider_status("ESPN", True, False, message[:180])
        return [], message

@st.cache_data(ttl=900, show_spinner=False)
def espn_team_last_matches(team_query, league_code, days_back=120):
    """Best-effort recent team form from ESPN's public scoreboard date-range response."""
    try:
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=int(days_back))
        range_text = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
        matches, err = espn_scoreboard_for_date(range_text, league_code)
        if err:
            return [], err
        wanted = normalize_team_key(team_query)
        found = []
        for item in matches or []:
            teams = item.get("teams") or {}
            home = (teams.get("home") or {}).get("name") or ""
            away = (teams.get("away") or {}).get("name") or ""
            if wanted not in normalize_team_key(home) and wanted not in normalize_team_key(away):
                continue
            status = (item.get("fixture") or {}).get("status") or {}
            goals = item.get("goals") or {}
            gh, ga = goals.get("home"), goals.get("away")
            if status.get("short") != "FT" or gh is None or ga is None:
                continue
            fixture_date = (item.get("fixture") or {}).get("date") or ""
            found.append({"date": str(fixture_date)[:10], "home": home, "away": away,
                          "home_goals": int(gh), "away_goals": int(ga),
                          "timestamp": str(fixture_date)})
        found.sort(key=lambda x: x["timestamp"], reverse=True)
        return found[:5], None
    except (TypeError, ValueError, KeyError) as exc:
        return [], f"ESPN takım formu verisi işlenemedi: {exc}"


def espn_matches_for_date(date_text):
    """ESPN public scoreboards for selected major leagues; odds are never fabricated."""
    # Best-effort Turkish league probes; ESPN coverage is not guaranteed.
    leagues = [
        "tur.1", "tur.2", "eng.1", "eng.2", "eng.3", "eng.4", "eng.5",
        "esp.1", "esp.2", "ita.1", "ita.2", "ger.1", "ger.2",
        "fra.1", "fra.2", "por.1", "ned.1", "bel.1", "sco.1",
        "usa.1", "mex.1", "arg.1", "bra.1", "par.1", "chi.1", "col.1", "per.1", "uru.1", "aus.1", "jpn.1",
        "ksa.1", "chn.1", "ind.1", "tha.1", "mys.1", "idn.1",
        "afc.champions", "uefa.champions", "uefa.europa", "uefa.europa.conf"
    ]
    combined, errors = [], []
    successful_sources = 0
    for league_code in leagues:
        matches, error = espn_scoreboard_for_date(date_text, league_code)
        combined.extend(matches or [])
        if error:
            errors.append(league_code + ": " + error)
        else:
            successful_sources += 1
    # A successful scoreboard with zero events is a valid empty result, not an API failure.
    if successful_sources:
        return combined, None
    return combined, ("; ".join(errors) if errors else "ESPN kaynaklarından yanıt alınamadı.")

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

def find_other_source_matches(match):
    """Find the same fixture in other configured live feeds and a date-scoped ESPN scoreboard."""
    teams = match.get("teams") or {}
    home = (teams.get("home") or {}).get("name") or ""
    away = (teams.get("away") or {}).get("name") or ""
    wanted = {normalize_team_key(home), normalize_team_key(away)}
    if not all(wanted):
        return [], "Takım adları eşleştirme için eksik."

    def team_matches(left, right):
        # Ignore common club prefixes/suffixes; only use conservative matches.
        import difflib
        a = normalize_team_key(left)
        b = normalize_team_key(right)
        if not a or not b:
            return False
        if a == b:
            return True
        generic = ("club", "fc", "cf", "sc", "sportclub", "deportivo", "atletico")
        for word in generic:
            if a.startswith(word) and len(a) - len(word) >= 4:
                a = a[len(word):]
            if b.startswith(word) and len(b) - len(word) >= 4:
                b = b[len(word):]
        if a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a)):
            return True
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.88

    def same_fixture(candidate):
        candidate_teams = candidate.get("teams") or {}
        ch = (candidate_teams.get("home") or {}).get("name") or ""
        ca = (candidate_teams.get("away") or {}).get("name") or ""
        # Team order can differ across providers; both names must independently match.
        return (team_matches(home, ch) and team_matches(away, ca)) or (team_matches(home, ca) and team_matches(away, ch))

    candidates = merge_live_match_feeds([])
    original_source = match.get("_source") or match.get("source")
    fixture = match.get("fixture") or {}
    kickoff = str(fixture.get("date") or "")
    date_text = ""
    try:
        from datetime import datetime
        parsed = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        date_text = parsed.strftime("%Y%m%d")
    except (ValueError, TypeError):
        date_text = ""

    # OpenFootAPI IDs often include the competition code. Probe ESPN's Paraguay scoreboard
    # for the fixture date because the generic OpenFootAPI source label doesn't reveal league.
    fixture_id_text = str(fixture.get("id") or "").lower()
    league = match.get("league") or {}
    league_meta = normalize_team_key(str(league.get("name") or "") + " " + str(league.get("country") or ""))
    espn_leagues = []
    if "par1" in fixture_id_text or "paraguay" in league_meta or "paraguay" in fixture_id_text:
        espn_leagues.append("par.1")
    # Add the ESPN event only if the scoreboard has a date-scoped candidate.
    if date_text:
        for league_code in espn_leagues:
            espn_items, espn_error = espn_scoreboard_for_date(date_text, league_code)
            if not espn_error:
                candidates.extend(espn_items or [])

    found = []
    seen = set()
    for candidate in candidates or []:
        source = candidate.get("_source") or candidate.get("source")
        if not source or source == original_source or not same_fixture(candidate):
            continue
        fixture_id = (candidate.get("fixture") or {}).get("id")
        if fixture_id in (None, ""):
            continue

        # ESPN team-name equality alone is not enough: reject a different kickoff,
        # a non-live ESPN event for a live source match, or conflicting live scores.
        if source == "ESPN":
            original_date = str((match.get("fixture") or {}).get("date") or "")
            candidate_date = str((candidate.get("fixture") or {}).get("date") or "")
            try:
                from datetime import datetime
                original_dt = datetime.fromisoformat(original_date.replace("Z", "+00:00"))
                candidate_dt = datetime.fromisoformat(candidate_date.replace("Z", "+00:00"))
                if original_dt.tzinfo is None or candidate_dt.tzinfo is None:
                    continue
                if abs((original_dt - candidate_dt).total_seconds()) > 6 * 60 * 60:
                    continue
            except (ValueError, TypeError):
                continue

            original_status = str(((match.get("fixture") or {}).get("status") or {}).get("short") or "").upper()
            candidate_status = str(((candidate.get("fixture") or {}).get("status") or {}).get("short") or "").upper()
            original_live = original_status in ("LIVE", "1H", "2H", "HT", "ET", "P")
            candidate_live = candidate_status in ("LIVE", "1H", "2H", "HT", "ET", "P")
            if original_live and not candidate_live:
                continue
            if original_live and candidate_live:
                original_goals = match.get("goals") or {}
                candidate_goals = candidate.get("goals") or {}
                oh, oa = original_goals.get("home"), original_goals.get("away")
                ch, ca = candidate_goals.get("home"), candidate_goals.get("away")
                if None not in (oh, oa, ch, ca) and (int(oh), int(oa)) != (int(ch), int(ca)):
                    continue

        key = (source, str(fixture_id))
        if key in seen:
            continue
        seen.add(key)
        found.append(candidate)
    return found, None


def merge_live_match_feeds(base_matches):
    """Combine configured live feeds and deduplicate by team names without inventing scores."""
    combined = list(base_matches or [])
    diagnostics = []
    feeds = []
    if FIVE_DOLLAR_FOOTBALL_API_KEY:
        items, err = five_dollar_live_matches()
        feeds.append(("5DollarFootballAPI", items, err))
    if SPORTMONKS_API_TOKEN:
        items, err = sportmonks_live_matches()
        feeds.append(("Sportmonks", sportmonks_to_api_football(items or []) if not err else None, err))
    if APIFOOTBALL_API_KEY:
        items, err = apifootball_com_live_matches()
        feeds.append(("APIFootball.com", items, err))
    # Public feeds are supplementary and short-cached; provider coverage is not global.
    items, err = openfootapi_live_matches()
    feeds.append(("OpenFootAPI", items, err))
    items, err = sportscore_live_matches()
    feeds.append(("SportScore", items, err))
    items, err = openligadb_live_matches()
    feeds.append(("OpenLigaDB", items, err))
    for name, items, err in feeds:
        diagnostics.append({"Kaynak": name, "Eklenen kayıt": len(items or []) if not err else "—",
                            "Durum": (err or f"{len(items or [])} kayıt")[:180]})
        if not err and items:
            combined = merge_fixture_sources(combined, items)
    st.session_state["live_engine_diagnostics"] = diagnostics
    return combined


def normalize_team_key(value):
    """Normalize team names for a conservative text match."""
    import unicodedata
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return "".join(ch for ch in value if ch.isalnum())

def espn_league_code_for_match(match):
    """Map known competition metadata (or a recognized fixture-ID code) to ESPN scoreboard leagues."""
    league = (match or {}).get("league") or {}
    name = normalize_team_key(league.get("name", ""))
    country = normalize_team_key(league.get("country", ""))
    mappings = [
        (("turkeysuperlig", "superlig", "turkey"), ("turkey", "turkiye"), "tur.1"),
        (("englishpremierleague", "premierleague", "england"), ("england", "unitedkingdom"), "eng.1"),
        (("laliga", "spanishlaliga", "spain"), ("spain",), "esp.1"),
        (("seriea", "italianseriea", "italy"), ("italy",), "ita.1"),
        (("bundesliga", "germanbundesliga", "germany"), ("germany",), "ger.1"),
        (("ligue1", "frenchligue1", "france"), ("france",), "fra.1"),
        (("primeiraliga", "portugal"), ("portugal",), "por.1"),
        (("eredivisie", "netherlands"), ("netherlands",), "ned.1"),
        (("scottishpremiership", "scotland"), ("scotland",), "sco.1"),
        (("mls", "majorleaguesoccer", "usa"), ("usa", "unitedstates"), "usa.1"),
        (("chileprimera", "primeradivision", "chile"), ("chile",), "chi.1"),
        (("argentinaprimera", "argentina"), ("argentina",), "arg.1"),
        (("brasileirao", "brazilseriea", "brazil"), ("brazil",), "bra.1"),
    ]
    for name_terms, country_terms, code in mappings:
        if any(term in name for term in name_terms) or any(term in country for term in country_terms):
            return code
    fixture_id = str(((match or {}).get("fixture") or {}).get("id") or "").lower()
    # Some feeds encode their competition slug in IDs (e.g. fmb_chi1_...).
    id_codes = {
        "chi1": "chi.1", "arg1": "arg.1", "bra1": "bra.1",
        "eng1": "eng.1", "esp1": "esp.1", "ita1": "ita.1",
        "ger1": "ger.1", "fra1": "fra.1", "tur1": "tur.1",
        "usa1": "usa.1", "ned1": "ned.1", "por1": "por.1",
    }
    for marker, code in id_codes.items():
        if marker in fixture_id:
            return code
    return None


def show_team_form_for_match(match):
    """Fetch recent ESPN results on demand and display actual W/D/L records, never predicted form."""
    teams = (match or {}).get("teams") or {}
    home = (teams.get("home") or {}).get("name") or ""
    away = (teams.get("away") or {}).get("name") or ""
    league_code = espn_league_code_for_match(match)
    if not home or not away:
        st.info("Takım isimleri eksik olduğu için form sorgulanamadı.")
        return
    if not league_code:
        st.info("Bu maçın lig kodu eşleştirilemedi. Takım formu sekmesinden ESPN destekli ligi seçerek sorgulayabilirsin.")
        return
    st.caption(f"Form kaynağı: ESPN · Lig kodu: {league_code} · Son 5 tamamlanmış maç")
    columns = st.columns(2)
    for idx, team_name in enumerate((home, away)):
        with st.spinner(f"{team_name} son maçları alınıyor..."):
            recent, err = espn_team_last_matches(team_name, league_code)
        with columns[idx]:
            st.markdown(f"**{team_name}**")
            if err:
                st.warning(f"Form alınamadı: {err}")
                continue
            if not recent:
                st.info("ESPN bu takım için son 5 tamamlanmış maçı döndürmedi.")
                continue
            rows = []
            form = []
            goals_for = goals_against = 0
            for game in recent:
                is_home = normalize_team_key(team_name) in normalize_team_key(game.get("home", ""))
                gf = game.get("home_goals", 0) if is_home else game.get("away_goals", 0)
                ga = game.get("away_goals", 0) if is_home else game.get("home_goals", 0)
                result = "G" if gf > ga else ("B" if gf == ga else "M")
                form.append(result)
                goals_for += gf
                goals_against += ga
                rows.append({"Tarih": game.get("date", "—"), "Rakip": game.get("away") if is_home else game.get("home"),
                             "Skor": f"{game.get('home_goals')} - {game.get('away_goals')}", "Sonuç": result})
            st.metric("Form (yeniden eskiye)", " · ".join(form), f"{len(recent)} maç")
            st.caption(f"Gol: {goals_for} · Yenilen: {goals_against}")
            st.dataframe(rows, use_container_width=True, hide_index=True)


@st.cache_data(ttl=1800, show_spinner=False)
def thesportsdb_search_player(query):
    """Search player metadata through TheSportsDB's public V1 endpoint."""
    try:
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}/searchplayers.php",
            params={"p": query}, timeout=12
        )
        if response.status_code != 200:
            return [], f"TheSportsDB oyuncu araması HTTP {response.status_code}"
        payload = response.json()
        players = payload.get("player") or []
        if isinstance(players, dict):
            players = [players]
        set_provider_status("TheSportsDB", True, True, f"Oyuncu araması: {len(players)} kayıt.")
        return players, None
    except (requests.RequestException, ValueError, TypeError) as exc:
        message = f"TheSportsDB oyuncu arama hatası: {exc}"
        set_provider_status("TheSportsDB", True, False, message[:180])
        return [], message


@st.cache_data(ttl=3600, show_spinner=False)
def thesportsdb_player_stats(player_id):
    """Return provider-reported player stats without assuming a fixed schema."""
    try:
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}/lookupplayerstats.php",
            params={"id": player_id}, timeout=12
        )
        if response.status_code != 200:
            return None, f"TheSportsDB oyuncu istatistikleri HTTP {response.status_code}"
        return response.json(), None
    except (requests.RequestException, ValueError, TypeError) as exc:
        return None, f"TheSportsDB oyuncu istatistikleri bağlantı/JSON hatası: {exc}"


@st.cache_data(ttl=45, show_spinner=False)
def five_dollar_live_matches():
    """Fetch live fixtures from 5DollarFootballAPI."""
    if not FIVE_DOLLAR_FOOTBALL_API_KEY:
        return None, "FIVE_DOLLAR_FOOTBALL_API_KEY tanımlı değil."
    try:
        response = requests.get("https://api.5dollarfootballapi.com/v1/fixtures", params={"status": "live", "per_page": 500}, headers={"Authorization": f"Bearer {FIVE_DOLLAR_FOOTBALL_API_KEY}"}, timeout=20)
        if response.status_code != 200:
            message = f"5DollarFootballAPI HTTP {response.status_code}: {response.text[:160]}"
            set_provider_status("5DollarFootballAPI", True, False, message)
            return None, message
        payload = response.json()
        if payload.get("success") == 0:
            error = payload.get("error") or {}
            message = str(error.get("message") or "API isteği başarısız.")[:160]
            set_provider_status("5DollarFootballAPI", True, False, message)
            return None, message
        normalized = []
        for item in payload.get("data") or payload.get("response") or []:
            teams = item.get("teams") or {}
            home_obj, away_obj = teams.get("home") or {}, teams.get("away") or {}
            home = home_obj.get("name") if isinstance(home_obj, dict) else home_obj
            away = away_obj.get("name") if isinstance(away_obj, dict) else away_obj
            if not home or not away:
                continue
            goals = item.get("goals") or {}
            raw_status = str(item.get("status") or item.get("state") or "in_play").lower()
            short = "HT" if "half" in raw_status else ("FT" if raw_status in ("finished", "full_time", "ft") else "LIVE")
            minute = item.get("minute", item.get("elapsed"))
            try:
                minute = int(minute) if minute is not None else None
            except (TypeError, ValueError):
                minute = None
            league = item.get("league") or {}
            if not isinstance(league, dict): league = {"name": str(league)}
            kickoff = item.get("kickoff_utc") or item.get("date") or item.get("starting_at")
            normalized.append({"fixture": {"id": item.get("id"), "date": kickoff, "status": {"long": raw_status, "short": short, "elapsed": minute}}, "league": {"id": league.get("id"), "name": league.get("name", "Lig bilinmiyor"), "country": (item.get("country") or {}).get("name", "") if isinstance(item.get("country"), dict) else str(item.get("country") or ""), "round": item.get("round")}, "teams": {"home": {"id": home_obj.get("id") if isinstance(home_obj, dict) else None, "name": home, "logo": home_obj.get("logo") if isinstance(home_obj, dict) else None}, "away": {"id": away_obj.get("id") if isinstance(away_obj, dict) else None, "name": away, "logo": away_obj.get("logo") if isinstance(away_obj, dict) else None}}, "goals": {"home": goals.get("home"), "away": goals.get("away")}, "corners": item.get("corners") or {}, "_source": "5DollarFootballAPI", "source": "5DollarFootballAPI", "_raw_5dollar": item})
        set_provider_status("5DollarFootballAPI", True, True, f"HTTP 200; {len(normalized)} canlı maç.")
        return normalized, None
    except (requests.RequestException, ValueError) as exc:
        message = f"5DollarFootballAPI bağlantı hatası: {exc}"
        set_provider_status("5DollarFootballAPI", True, False, message[:160])
        return None, message



@st.cache_data(ttl=60, show_spinner=False)
def five_dollar_fixture_statistics(fixture_id):
    """Fetch real match statistics from the free-tier-supported 5DollarFootballAPI fixture endpoint."""
    if not FIVE_DOLLAR_FOOTBALL_API_KEY:
        return None, "FIVE_DOLLAR_FOOTBALL_API_KEY tanımlı değil."
    fixture_id = str(fixture_id or "").strip()
    if not fixture_id.isdigit():
        return None, "5DollarFootballAPI maç kimliği geçersiz."
    try:
        response = requests.get(
            f"https://api.5dollarfootballapi.com/v1/fixtures/{fixture_id}/statistics",
            headers={"Authorization": f"Bearer {FIVE_DOLLAR_FOOTBALL_API_KEY}"},
            timeout=15,
        )
        if response.status_code != 200:
            return None, f"5DollarFootballAPI istatistik HTTP {response.status_code}: {response.text[:160]}"
        payload = response.json()
        if payload.get("success") == 0:
            return None, str((payload.get("error") or {}).get("message") or "İstatistik isteği başarısız.")[:180]
        data = payload.get("data") or {}
        return data.get("statistics") or {}, None
    except (requests.RequestException, ValueError, TypeError) as exc:
        return None, f"5DollarFootballAPI istatistik bağlantı/JSON hatası: {exc}"


@st.cache_data(ttl=60, show_spinner=False)
def five_dollar_fixture_odds(fixture_id):
    """Fetch per-fixture Bet365 odds; the free plan exposes this endpoint for supported leagues."""
    if not FIVE_DOLLAR_FOOTBALL_API_KEY:
        return None, "FIVE_DOLLAR_FOOTBALL_API_KEY tanımlı değil."
    fixture_id = str(fixture_id or "").strip()
    if not fixture_id.isdigit():
        return None, "5DollarFootballAPI maç kimliği geçersiz."
    try:
        response = requests.get(
            f"https://api.5dollarfootballapi.com/v1/fixtures/{fixture_id}/odds",
            headers={"Authorization": f"Bearer {FIVE_DOLLAR_FOOTBALL_API_KEY}"},
            timeout=15,
        )
        if response.status_code != 200:
            return None, f"5DollarFootballAPI oran HTTP {response.status_code}: {response.text[:160]}"
        payload = response.json()
        if payload.get("success") == 0:
            return None, str((payload.get("error") or {}).get("message") or "Oran isteği başarısız.")[:180]
        return payload.get("data") or {}, None
    except (requests.RequestException, ValueError, TypeError) as exc:
        return None, f"5DollarFootballAPI oran bağlantı/JSON hatası: {exc}"


@st.cache_data(ttl=45, show_spinner=False)
def bsd_live_matches():
    """Optional Bzzoiro Sports Data live-score provider; requires BSD_API_TOKEN."""
    if not BSD_API_TOKEN:
        return None, "BSD_API_TOKEN tanımlı değil; Bzzoiro kayıt anahtarı gerekiyor."
    try:
        response = requests.get(
            "https://sports.bzzoiro.com/api/v2/events/live/",
            headers={"Authorization": f"Token {BSD_API_TOKEN}"},
            params={"limit": 100}, timeout=15
        )
        if response.status_code != 200:
            message = f"Bzzoiro HTTP {response.status_code}: {response.text[:160]}"
            set_provider_status("Bzzoiro Sports Data", True, False, message)
            return None, message
        payload = response.json()
        items = payload.get("results", payload.get("data", [])) if isinstance(payload, dict) else payload
        if isinstance(items, dict):
            items = items.get("results", items.get("events", []))
        normalized = []
        for item in items or []:
            home_obj = item.get("home_team") or item.get("home") or item.get("homeTeam") or {}
            away_obj = item.get("away_team") or item.get("away") or item.get("awayTeam") or {}
            home = home_obj.get("name") or home_obj.get("team_name") or home_obj.get("display_name") if isinstance(home_obj, dict) else home_obj
            away = away_obj.get("name") or away_obj.get("team_name") or away_obj.get("display_name") if isinstance(away_obj, dict) else away_obj
            if not home or not away:
                participants = item.get("participants") or []
                for part in participants:
                    role = str(part.get("role") or part.get("location") or part.get("position") or "").lower()
                    name = part.get("name") or part.get("team_name")
                    if name and role in ("home", "1", "local"):
                        home = name
                    elif name and role in ("away", "2", "visitor"):
                        away = name
            if not home or not away:
                continue
            score = item.get("score") or item.get("scores") or {}
            if isinstance(score, list):
                score_map = {str(x.get("side") or x.get("team") or x.get("role") or "").lower(): x.get("score", x.get("goals")) for x in score if isinstance(x, dict)}
                gh = score_map.get("home", score_map.get("1"))
                ga = score_map.get("away", score_map.get("2"))
            else:
                gh = score.get("home", score.get("home_score", score.get("home_goals")))
                ga = score.get("away", score.get("away_score", score.get("away_goals")))
            status = str(item.get("status") or item.get("state") or "LIVE").lower()
            short = "HT" if "half" in status else ("FT" if "finish" in status else "LIVE")
            normalized.append({
                "fixture": {"id": f"bsd-{item.get('id', item.get('event_id', len(normalized)))}",
                            "date": item.get("start_time") or item.get("kickoff") or item.get("date"),
                            "status": {"long": status, "short": short, "elapsed": item.get("current_minute") or item.get("minute")}},
                "teams": {"home": {"name": str(home)}, "away": {"name": str(away)}},
                "goals": {"home": gh, "away": ga},
                "league": {"name": (item.get("league") or {}).get("name", "Bzzoiro") if isinstance(item.get("league"), dict) else str(item.get("league") or "Bzzoiro"), "country": ""},
                "_source": "Bzzoiro Sports Data"
            })
        set_provider_status("Bzzoiro Sports Data", True, True, f"HTTP 200; {len(normalized)} canlı maç normalize edildi.")
        return normalized, None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        message = f"Bzzoiro bağlantı/yanıt hatası: {exc}"
        set_provider_status("Bzzoiro Sports Data", True, False, message[:180])
        return None, message

@st.cache_data(ttl=45, show_spinner=False)
def sportscore_live_matches():
    """Free live football feed from SportScore; attribution link is shown in the UI."""
    try:
        response = requests.get(
            "https://sportscore.com/api/v1/fixtures/",
            params={"sport": "football", "status": "live", "limit": 200},
            headers={"User-Agent": "FutbolAnalizMerkezi/1.0"}, timeout=15
        )
        if response.status_code != 200:
            message = f"SportScore HTTP {response.status_code}: {response.text[:140]}"
            set_provider_status("SportScore", True, False, message)
            return None, message
        payload = response.json()
        items = payload.get("data", payload.get("fixtures", payload.get("matches", []))) if isinstance(payload, dict) else payload
        if isinstance(items, dict):
            items = items.get("matches", items.get("fixtures", items.get("data", [])))
        normalized = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            home_obj = item.get("home") or item.get("homeTeam") or item.get("home_team") or {}
            away_obj = item.get("away") or item.get("awayTeam") or item.get("away_team") or {}
            home = home_obj.get("name") or home_obj.get("team_name") or home_obj.get("displayName") if isinstance(home_obj, dict) else home_obj
            away = away_obj.get("name") or away_obj.get("team_name") or away_obj.get("displayName") if isinstance(away_obj, dict) else away_obj
            if not home or not away:
                continue
            raw_status = str(item.get("status") or item.get("status_text") or item.get("state") or "live").strip()
            status_lower = raw_status.lower()
            if any(x in status_lower for x in ("finish", "full time", "completed", "ended")):
                short = "FT"
            elif any(x in status_lower for x in ("half", "halftime", "half-time")):
                short = "HT"
            elif any(x in status_lower for x in ("live", "in progress", "in_progress", "playing", "1st", "2nd")):
                short = "LIVE"
            else:
                # Endpoint is requested with status=live, but do not silently
                # promote an unknown status to live.
                continue
            home_score = item.get("home_score", item.get("homeScore"))
            away_score = item.get("away_score", item.get("awayScore"))
            time_text = item.get("time") or item.get("kickoff") or item.get("date") or item.get("start_time")
            league = item.get("competition") or item.get("league") or item.get("tournament") or "SportScore"
            league_name = league.get("name") if isinstance(league, dict) else str(league)
            normalized.append({
                "fixture": {"id": item.get("id") or item.get("slug"), "date": time_text,
                            "status": {"long": raw_status, "short": short, "elapsed": item.get("minute", item.get("elapsed"))}},
                "teams": {"home": {"id": None, "name": str(home), "logo": (home_obj.get("logo") or home_obj.get("image")) if isinstance(home_obj, dict) else None},
                          "away": {"id": None, "name": str(away), "logo": (away_obj.get("logo") or away_obj.get("image")) if isinstance(away_obj, dict) else None}},
                "goals": {"home": home_score, "away": away_score},
                "league": {"name": league_name, "country": ""},
                "_source": "SportScore", "source": "SportScore", "_raw_sportscore": item
            })
        set_provider_status("SportScore", True, True, f"HTTP 200; {len(items or [])} kayıt, {len(normalized)} canlı kayıt normalize edildi.")
        return normalized, None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        message = f"SportScore bağlantı/yanıt hatası: {exc}"
        set_provider_status("SportScore", True, False, message[:180])
        return None, message



@st.cache_data(ttl=45, show_spinner=False)
def apifootball_com_live_matches():
    """APIFootball.com (apiv2) livescore feed; uses APIkey query parameter, not API-Sports headers."""
    if not APIFOOTBALL_API_KEY:
        set_provider_status("APIFootball.com", False, False, "APIFOOTBALL_API_KEY tanımlı değil.")
        return None, "APIFOOTBALL_API_KEY tanımlı değil."
    today_text = date.today().isoformat()
    # Filter stale live flags using the kickoff time in Istanbul.
    from zoneinfo import ZoneInfo
    now_local = datetime.now(ZoneInfo("Europe/Istanbul"))
    try:
        response = requests.get(
            "https://apiv3.apifootball.com/",
            params={"action": "get_events", "from": today_text, "to": today_text,
                    "match_live": "1", "timezone": "Europe/Istanbul", "APIkey": APIFOOTBALL_API_KEY},
            headers={"Accept": "application/json"},
            timeout=18,
        )
        if response.status_code != 200:
            message = f"APIFootball.com HTTP {response.status_code}: {response.text[:160]}"
            set_provider_status("APIFootball.com", True, False, message)
            return None, message
        payload = response.json()
        if isinstance(payload, dict):
            # Some API errors are returned as objects instead of event arrays.
            message = str(payload.get("error") or payload.get("message") or payload)[:180]
            set_provider_status("APIFootball.com", True, False, message)
            return None, message
        if not isinstance(payload, list):
            set_provider_status("APIFootball.com", True, False, "Beklenmeyen JSON yanıt biçimi.")
            return None, "Beklenmeyen JSON yanıt biçimi."
        normalized = []
        active_terms = ("live", "1st half", "2nd half", "half time", "halftime", "extra time", "penalty")
        for item in payload:
            if not isinstance(item, dict):
                continue
            live_flag = str(item.get("match_live", "")).strip().lower()
            raw_status = str(item.get("match_status") or "").strip()
            status_lower = raw_status.lower()
            if live_flag not in ("1", "true", "yes") and not any(term in status_lower for term in active_terms):
                continue
            if any(term in status_lower for term in ("finished", "full time", "after penalties", "cancelled", "postponed")):
                continue
            home = item.get("match_hometeam_name")
            away = item.get("match_awayteam_name")
            if not home or not away:
                continue
            if "half time" in status_lower or "halftime" in status_lower or status_lower == "ht":
                short, long_status = "HT", "Devre Arası"
            else:
                short, long_status = "LIVE", raw_status or "Canlı"
            def score_value(value):
                try:
                    return int(str(value).strip())
                except (TypeError, ValueError):
                    return None
            home_score = score_value(item.get("match_hometeam_score"))
            away_score = score_value(item.get("match_awayteam_score"))
            minute = None
            if raw_status.isdigit():
                minute = int(raw_status)
            elif "+" in raw_status:
                try:
                    minute = int(raw_status.split("+", 1)[0].strip())
                except ValueError:
                    minute = None
            match_date = item.get("match_date") or today_text
            match_time = item.get("match_time")
            kickoff = f"{match_date}T{match_time}:00" if match_time and len(str(match_time)) == 5 else match_date
            try:
                kickoff_dt = datetime.fromisoformat(kickoff)
                if kickoff_dt.tzinfo is None:
                    kickoff_dt = kickoff_dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
                age_minutes = (now_local - kickoff_dt.astimezone(ZoneInfo("Europe/Istanbul"))).total_seconds() / 60
                if age_minutes < -20 or age_minutes > 180:
                    continue
                if minute is not None and minute >= 90 and age_minutes > 155:
                    continue
            except (TypeError, ValueError, OverflowError):
                continue
            normalized.append({
                "fixture": {"id": f"apifootballcom-{item.get('match_id')}", "date": kickoff,
                            "status": {"long": long_status, "short": short, "elapsed": minute}},
                "teams": {"home": {"id": item.get("match_hometeam_id"), "name": str(home), "logo": item.get("team_home_badge")},
                          "away": {"id": item.get("match_awayteam_id"), "name": str(away), "logo": item.get("team_away_badge")}},
                "goals": {"home": home_score, "away": away_score},
                "league": {"id": item.get("league_id"), "name": item.get("league_name") or "APIFootball.com", "country": item.get("country_name") or ""},
                "_source": "APIFootball.com", "source": "APIFootball.com", "_raw_apifootball_com": item
            })
        set_provider_status("APIFootball.com", True, True, f"HTTP 200; {len(payload)} kayıt, {len(normalized)} canlı maç.")
        return normalized, None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        message = f"APIFootball.com bağlantı/yanıt hatası: {exc}"
        set_provider_status("APIFootball.com", True, False, message[:180])
        return None, message

def is_fresh_live_fixture(match, max_age_hours=4):
    """Reject stale live labels when kickoff is too old or implausibly in the future."""
    fixture = match.get("fixture") or {}
    raw_date = fixture.get("date")
    if not raw_date:
        return False
    try:
        value = str(raw_date).strip().replace("Z", "+00:00")
        kickoff = datetime.fromisoformat(value)
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        kickoff = kickoff.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return False
    now = datetime.now(timezone.utc)
    age = (now - kickoff).total_seconds()
    return -3 * 3600 <= age <= max_age_hours * 3600


@st.cache_data(ttl=45, show_spinner=False)
def openfootapi_live_matches():
    """OpenFootAPI live fixtures. Uses a private Streamlit secret when configured, public demo key otherwise."""
    token = str(st.secrets.get("OPENFOOT_API_KEY", "") or "").strip()
    if not token:
        token = "of_demo_openfootapi_docs"
    try:
        response = requests.get(
            "https://openfootapi.com/v1/matches",
            params={"date": date.today().isoformat(), "status": "live"},
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if response.status_code != 200:
            payload_text = response.text[:160]
            message = f"OpenFootAPI HTTP {response.status_code}: {payload_text}"
            set_provider_status("OpenFootAPI", True, False, message)
            return None, message
        payload = response.json()
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            items = []
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            status_raw = str(item.get("status") or "unknown").strip()
            status_lower = status_raw.lower()
            if status_lower == "live":
                short = "LIVE"
            elif status_lower in ("ht", "half-time", "halftime", "paused"):
                short = "HT"
            else:
                continue
            home_obj = item.get("homeTeam") or {}
            away_obj = item.get("awayTeam") or {}
            home = home_obj.get("name") if isinstance(home_obj, dict) else str(home_obj)
            away = away_obj.get("name") if isinstance(away_obj, dict) else str(away_obj)
            if not home or not away:
                continue
            score = item.get("score") or item.get("scores") or {}
            if not isinstance(score, dict):
                score = {}
            home_score = score.get("home", score.get("homeScore", item.get("homeScore")))
            away_score = score.get("away", score.get("awayScore", item.get("awayScore")))
            if home_score is None and isinstance(item.get("home"), dict):
                home_score = item["home"].get("score", item["home"].get("goals"))
            if away_score is None and isinstance(item.get("away"), dict):
                away_score = item["away"].get("score", item["away"].get("goals"))
            competition = item.get("competition") or {}
            competition_name = competition.get("name") if isinstance(competition, dict) else str(competition)
            normalized.append({
                "fixture": {"id": item.get("id"), "date": item.get("kickoffAt"),
                            "status": {"long": status_raw, "short": short,
                                       "elapsed": item.get("minute", item.get("elapsedMinute"))}},
                "teams": {"home": {"id": home_obj.get("id") if isinstance(home_obj, dict) else None, "name": str(home), "logo": home_obj.get("logo") if isinstance(home_obj, dict) else None},
                          "away": {"id": away_obj.get("id") if isinstance(away_obj, dict) else None, "name": str(away), "logo": away_obj.get("logo") if isinstance(away_obj, dict) else None}},
                "goals": {"home": home_score, "away": away_score},
                "league": {"id": item.get("competitionId"), "name": competition_name or "OpenFootAPI", "country": ""},
                "_source": "OpenFootAPI", "source": "OpenFootAPI", "_raw_openfootapi": item
            })
        received_count = len(normalized)
        normalized = [match for match in normalized if is_fresh_live_fixture(match)]
        dropped_count = received_count - len(normalized)
        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
        plan = ((meta.get("access") or {}).get("plan") if isinstance(meta, dict) else None) or "bilinmiyor"
        status_note = f"HTTP 200; {len(items)} kayıt, {len(normalized)} güncel canlı kayıt; plan: {plan}."
        if dropped_count:
            status_note += f" Eski/saati doğrulanamayan {dropped_count} kayıt elendi."
        set_provider_status("OpenFootAPI", True, True, status_note)
        return normalized, None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        message = f"OpenFootAPI bağlantı/yanıt hatası: {exc}"
        set_provider_status("OpenFootAPI", True, False, message[:180])
        return None, message


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
            message = f"Sportmonks HTTP {response.status_code}: {response.text[:180]}"
            set_provider_status("Sportmonks", True, False, message)
            return None, message
        payload = response.json()
        set_provider_status("Sportmonks", True, True, f"HTTP 200; {len(payload.get('data', []))} canlı kayıt.")
        return payload.get("data", []), None
    except (requests.RequestException, ValueError) as exc:
        message = f"Sportmonks bağlantı hatası: {exc}"
        set_provider_status("Sportmonks", True, False, message[:180])
        return None, message

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


@st.cache_data(ttl=45, show_spinner=False)
def apifootball_com_detail(action, match_id):
    """Fetch match detail using APIFootball.com match IDs."""
    if not APIFOOTBALL_API_KEY:
        return None, "APIFOOTBALL_API_KEY tanımlı değil."
    match_id = str(match_id or "").replace("apifootballcom-", "").strip()
    if not match_id:
        return None, "APIFootball.com maç kimliği bulunamadı."
    try:
        response = requests.get("https://apiv3.apifootball.com/",
            params={"action": action, "match_id": match_id, "APIkey": APIFOOTBALL_API_KEY},
            headers={"Accept": "application/json"}, timeout=18)
        if response.status_code != 200:
            return None, f"APIFootball.com HTTP {response.status_code}: {response.text[:160]}"
        payload = response.json()
        if isinstance(payload, dict) and (payload.get("error") or payload.get("message")) and not payload.get(match_id):
            return None, str(payload.get("error") or payload.get("message"))[:180]
        return payload, None
    except (requests.RequestException, ValueError, TypeError) as exc:
        return None, f"APIFootball.com bağlantı/JSON hatası: {exc}"

def show_stats(fixture_id, match):
    source = match.get("_source") or match.get("source")
    if source == "5DollarFootballAPI":
        payload, err = five_dollar_fixture_statistics(fixture_id)
        if err:
            st.warning(err)
            return None
        stats = payload or {}
        teams = (match or {}).get("teams", {})
        home_name = (teams.get("home") or {}).get("name", "Ev sahibi")
        away_name = (teams.get("away") or {}).get("name", "Deplasman")
        label_map = {
            "attacks": "Attacks", "dangerous_attacks": "Dangerous Attacks",
            "shots_on_target": "Shots on Goal", "shots_off_target": "Shots off Goal",
            "possession": "Ball Possession",
        }
        home_rows, away_rows, table_rows = [], [], []
        def append_pair(label, pair, prefix=""):
            if not isinstance(pair, dict) or ("home" not in pair and "away" not in pair):
                return
            raw_label = label_map.get(label, label.replace("_", " ").title())
            home_value, away_value = pair.get("home"), pair.get("away")
            display_label = f"{prefix}{STAT_TR.get(raw_label, raw_label)}"
            table_rows.append({"İstatistik": display_label,
                               home_name: home_value if home_value is not None else "—",
                               away_name: away_value if away_value is not None else "—"})
            home_rows.append({"type": raw_label, "value": num(home_value)})
            away_rows.append({"type": raw_label, "value": num(away_value)})
        for key, value in stats.items():
            if key == "first_half" and isinstance(value, dict):
                for subkey, pair in value.items():
                    append_pair(subkey, pair, "İlk yarı — ")
            else:
                append_pair(key, value)
        # Some fixture feeds carry corners/cards on the fixture record, not statistics endpoint.
        for key, label in (("corners", "Corner Kicks"),):
            pair = (match or {}).get(key) or {}
            if isinstance(pair, dict) and ("home" in pair or "away" in pair):
                append_pair(label, pair)
        if not table_rows:
            st.info("5DollarFootballAPI bu maç için henüz istatistik döndürmedi.")
            return None
        # Derive total shots only where both on-target and off-target values are numeric.
        h_on, h_off = stat_value(home_rows, ["Shots on Goal"]), stat_value(home_rows, ["Shots off Goal"])
        a_on, a_off = stat_value(away_rows, ["Shots on Goal"]), stat_value(away_rows, ["Shots off Goal"])
        if h_on is not None and h_off is not None:
            home_rows.append({"type": "Total Shots", "value": h_on + h_off})
            away_rows.append({"type": "Total Shots", "value": (a_on + a_off) if a_on is not None and a_off is not None else None})
        st.subheader("Maç istatistikleri")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
        st.caption("Kaynak: 5DollarFootballAPI. Kapsam ücretsiz planda ilk 5 ligle sınırlıdır; eksik alanlar gösterilmez.")
        return {"home_name": home_name, "away_name": away_name, "home_rows": home_rows, "away_rows": away_rows}
    if source == "TheSportsDB":
        event_id = str(fixture_id or "").replace("tsdb-", "").strip()
        if not event_id.isdigit():
            st.info("TheSportsDB istatistikleri için geçerli etkinlik kimliği bulunamadı.")
            return None
        payload, err = thesportsdb_event_detail(event_id, "lookupeventstats.php")
        if err:
            st.warning(f"TheSportsDB istatistik isteği: {err}")
            return None
        stats = (payload or {}).get("eventstats") or []
        if not stats:
            st.info("TheSportsDB bu maç için istatistik döndürmedi. Bu, maç/lig verisinin eksik olduğu anlamına gelebilir.")
            return None
        teams = (match or {}).get("teams", {})
        home_name = (teams.get("home") or {}).get("name", "Ev sahibi")
        away_name = (teams.get("away") or {}).get("name", "Deplasman")
        rows = []
        home_rows, away_rows = [], []
        for item in stats:
            label = item.get("strStat") or item.get("name") or "İstatistik"
            home_value = item.get("intHome", item.get("home"))
            away_value = item.get("intAway", item.get("away"))
            rows.append({"İstatistik": STAT_TR.get(label, label), home_name: home_value if home_value not in (None, "") else "—",
                         away_name: away_value if away_value not in (None, "") else "—"})
            home_rows.append({"type": label, "value": num(home_value)})
            away_rows.append({"type": label, "value": num(away_value)})
        st.subheader("Maç istatistikleri")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Kaynak: TheSportsDB. Yalnızca sağlayıcının bu maç için döndürdüğü alanlar gösterilir.")
        return {"home_name": home_name, "away_name": away_name, "home_rows": home_rows, "away_rows": away_rows}
    if source == "APIFootball.com":
        payload, err = apifootball_com_detail("get_statistics", fixture_id)
        if err:
            st.warning(f"APIFootball.com istatistik isteği: {err}")
            return None
        match_id = str(fixture_id).replace("apifootballcom-", "")
        block = payload.get(match_id, {}) if isinstance(payload, dict) else {}
        stats = block.get("statistics") or []
        if not stats:
            st.info("APIFootball.com bu maç için istatistik döndürmedi. Paket kapsamı veya maç verisi henüz hazır olmayabilir.")
            return None
        home_name = match.get("teams", {}).get("home", {}).get("name", "Ev sahibi")
        away_name = match.get("teams", {}).get("away", {}).get("name", "Deplasman")
        st.subheader("Maç istatistikleri")
        st.dataframe([{"İstatistik": STAT_TR.get(x.get("type", ""), x.get("type", "İstatistik")), home_name: x.get("home", "—"), away_name: x.get("away", "—")} for x in stats], use_container_width=True, hide_index=True)
        st.caption("Kaynak: APIFootball.com")
        return {"home_name": home_name, "away_name": away_name, "home_rows": stats, "away_rows": stats}
    if source not in ("Sportmonks", "API-Football"):
        st.info(f"{source or 'Bu maçın kaynağı'} bu maç için istatistik sağlamıyor; bu kaynak için uygun maç kimliği bulunamadı.")
        return None
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
            if err: st.error(f"İstatistik isteği: {err}")
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

def show_player_statistics(fixture_id, match=None):
    source = (match or {}).get("_source") or (match or {}).get("source")
    if source == "APIFootball.com":
        payload, err = apifootball_com_detail("get_statistics", fixture_id)
        if err:
            st.warning(f"APIFootball.com oyuncu istatistiği isteği: {err}")
            return
        match_id = str(fixture_id).replace("apifootballcom-", "")
        block = payload.get(match_id, {}) if isinstance(payload, dict) else {}
        players = block.get("player_statistics") or []
        if not players:
            st.info("Bu maç için oyuncu istatistikleri dönmedi. Sağlayıcı bu alanı maç/paket bazında sunuyor olabilir.")
            return
        st.subheader("Oyuncu bazında maç istatistikleri")
        st.dataframe([{
            "Takım": "Ev sahibi" if str(p.get("team_name", "")).lower() == "home" else ("Deplasman" if str(p.get("team_name", "")).lower() == "away" else p.get("team_name", "—")),
            "Oyuncu": p.get("player_name", "—"), "Pozisyon": p.get("player_position", "—"),
            "Dakika": p.get("player_minutes_played", "—"), "Puan": p.get("player_rating", "—"),
            "Gol": p.get("player_goals", "—"), "Asist": p.get("player_assists", "—"),
            "Şut": p.get("player_shots_total", "—"), "İsabetli şut": p.get("player_shots_on_goal", "—"),
            "Pas": p.get("player_passes", "—"), "İsabetli pas": p.get("player_passes_acc", "—"),
            "Müdahale": p.get("player_tackles", "—"), "Faul": p.get("player_fouls_commited", "—"),
            "Sarı kart": p.get("player_yellowcards", "—"), "Kırmızı kart": p.get("player_redcards", "—")
        } for p in players], use_container_width=True, hide_index=True)
        st.caption("Kaynak: APIFootball.com; alanlar sağlayıcının döndürdüğü kayıtlarla sınırlıdır.")
        return
    if source not in ("Sportmonks", "API-Football"):
        st.info(f"{source or 'Bu maçın kaynağı'} oyuncu istatistiği sağlamıyor; bu kaynak için oyuncu verisi uç noktası tanımlı değil.")
        return
    """Player-level match statistics from API-Football; never invent missing values."""
    if match and (match.get("_source") not in (None, "API-Football")):
        st.info(f"Oyuncu istatistikleri bu fikstür kaynağında doğrudan desteklenmiyor ({match.get('_source')}). API-Football kaynaklı eşleşmiş maçı kullan.")
        return
    if not str(fixture_id or "").isdigit():
        st.info("Oyuncu istatistikleri için API-Football maç kimliği gerekiyor.")
        return
    data, err, _ = api_get("fixtures/players", {"fixture": int(fixture_id)})
    if err:
        st.warning(f"Oyuncu istatistikleri alınamadı: {err}")
        return
    rows = []
    for team_block in data or []:
        team_name = (team_block.get("team") or {}).get("name", "Takım")
        for player_block in team_block.get("players") or []:
            player = player_block.get("player") or {}
            stat_list = player_block.get("statistics") or []
            stat = stat_list[0] if stat_list else {}
            games = stat.get("games") or {}
            shots = stat.get("shots") or {}
            goals = stat.get("goals") or {}
            passes = stat.get("passes") or {}
            tackles = stat.get("tackles") or {}
            duels = stat.get("duels") or {}
            dribbles = stat.get("dribbles") or {}
            fouls = stat.get("fouls") or {}
            cards = stat.get("cards") or {}
            rows.append({
                "Takım": team_name, "Oyuncu": player.get("name", "Bilinmiyor"),
                "Pozisyon": games.get("position"), "Dakika": games.get("minutes"),
                "Puan": games.get("rating"), "Gol": goals.get("total"),
                "Asist": goals.get("assists"), "Şut": shots.get("total"),
                "İsabetli şut": shots.get("on"), "Pas": passes.get("total"),
                "Pas isabeti": passes.get("accuracy"), "Müdahale": tackles.get("total"),
                "Düello": duels.get("total"), "Başarılı çalım": dribbles.get("success"),
                "Faul": fouls.get("committed"), "Sarı kart": cards.get("yellow"),
                "Kırmızı kart": cards.get("red")
            })
    if not rows:
        st.info("Sağlayıcı bu maç için oyuncu istatistiği döndürmedi. Maç başlamamış veya lig/plan kapsam dışında olabilir.")
        return
    st.subheader("Oyuncu bazında maç istatistikleri")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("Alanlar sağlayıcının yanıtına göre doldurulur; eksik alanlar boş bırakılır.")

def show_lineups(fixture_id, match=None):
    source = (match or {}).get("_source") or (match or {}).get("source")
    if source == "TheSportsDB":
        event_id = str(fixture_id or "").replace("tsdb-", "").strip()
        if not event_id.isdigit():
            st.info("TheSportsDB kadrosu için geçerli etkinlik kimliği bulunamadı.")
            return
        payload, err = thesportsdb_event_detail(event_id, "lookuplineup.php")
        if err:
            st.warning(f"TheSportsDB kadro isteği: {err}")
            return
        lineup = (payload or {}).get("lineup") or []
        if not lineup:
            st.info("TheSportsDB bu maç için kadro döndürmedi. İlk 11 verisi hiç girilmemiş veya henüz yayımlanmamış olabilir.")
            return
        teams = (match or {}).get("teams", {})
        home_name = (teams.get("home") or {}).get("name", "Ev sahibi")
        away_name = (teams.get("away") or {}).get("name", "Deplasman")
        cols = st.columns(2)
        for idx, is_home in enumerate((True, False)):
            team_name = home_name if is_home else away_name
            team_rows = []
            for player in lineup:
                raw_home = str(player.get("strHome", "")).strip().lower()
                player_is_home = raw_home in ("yes", "true", "1", "home")
                if player_is_home != is_home:
                    continue
                substitute = str(player.get("strSubstitute", "")).strip().lower() in ("yes", "true", "1", "true")
                team_rows.append({
                    "Oyuncu": player.get("strPlayer") or "—",
                    "Forma": player.get("intSquadNumber") or "—",
                    "Pozisyon": player.get("strPosition") or "—",
                    "Rol": "Yedek" if substitute else "İlk 11",
                })
            with cols[idx]:
                st.markdown(f"**{team_name}**")
                starters = [row for row in team_rows if row["Rol"] == "İlk 11"]
                substitutes = [row for row in team_rows if row["Rol"] == "Yedek"]
                if starters:
                    st.write("**İlk 11 / bildirilen oyuncular**")
                    st.dataframe(starters, use_container_width=True, hide_index=True)
                else:
                    st.info("İlk 11 kaydı bulunamadı.")
                if substitutes:
                    st.write("**Yedekler**")
                    st.dataframe(substitutes, use_container_width=True, hide_index=True)
        st.caption("Kaynak: TheSportsDB. Kadro yalnızca sağlayıcıda mevcutsa gösterilir; bu canlı kadro garantisi değildir.")
        return
    if source == "APIFootball.com":
        payload, err = apifootball_com_detail("get_lineups", fixture_id)
        if err:
            st.warning(f"APIFootball.com kadro isteği: {err}")
            return
        match_id = str(fixture_id).replace("apifootballcom-", "")
        block = payload.get(match_id, {}) if isinstance(payload, dict) else {}
        lineup = block.get("lineup") or {}
        if not lineup:
            st.info("APIFootball.com bu maç için kadro döndürmedi. Kadro henüz açıklanmamış veya paket kapsamı dışında olabilir.")
            return
        st.subheader("Kadro bilgileri")
        cols = st.columns(2)
        for idx, side in enumerate(("home", "away")):
            team_name = (match or {}).get("teams", {}).get(side, {}).get("name", "Ev sahibi" if side == "home" else "Deplasman")
            side_data = lineup.get(side) or {}
            starters = side_data.get("starting_lineups") or []
            subs = side_data.get("substitutes") or []
            with cols[idx]:
                st.markdown(f"**{team_name}**")
                st.write("Diziliş:", (match or {}).get("teams", {}).get(side, {}).get("formation") or "Bilinmiyor")
                st.write("**İlk 11**")
                if starters:
                    st.dataframe([{"Oyuncu": p.get("lineup_player", "—"), "Forma": p.get("lineup_number", "—"), "Pozisyon": p.get("lineup_position", "—")} for p in starters], use_container_width=True, hide_index=True)
                else:
                    st.write("İlk 11 bilgisi yok.")
                if subs:
                    st.write("**Yedekler:** " + ", ".join(p.get("lineup_player", "—") for p in subs))
        st.caption("Kaynak: APIFootball.com")
        return
    if source not in ("Sportmonks", "API-Football"):
        st.info(f"{source or 'Bu maçın kaynağı'} kadro verisi sağlamıyor; bu kaynak için kadro uç noktası tanımlı değil.")
        return
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
    source = (match or {}).get("_source") or (match or {}).get("source")
    if source == "5DollarFootballAPI":
        payload, err = five_dollar_fixture_odds(fixture_id)
        if err:
            st.warning(err)
            return []
        bookmakers = (payload or {}).get("bookmakers") or []
        if not bookmakers:
            st.info("5DollarFootballAPI bu maç için oran kaydı döndürmedi.")
            return []
        status = ((match or {}).get("fixture") or {}).get("status") or {}
        is_live = str(status.get("short", "")).upper() in ("LIVE", "HT", "1H", "2H", "IN_PLAY")
        stage_order = ("inplay", "closing", "opening") if is_live else ("closing", "opening", "inplay")
        rows = []
        def add_price(market, option, price, bookmaker, stage, line=None):
            odd = num(price)
            if odd is None or odd <= 1:
                return
            label = f"{market} ({line})" if line is not None and market in ("Gol Alt/Üst", "Korner Alt/Üst", "Kart Alt/Üst", "Asya Handikap") else market
            rows.append({"Pazar": label, "Seçenek": option, "Oran": odd,
                         "Oran aşaması": stage, "Oranın ham olasılığı (%)": round(100 / odd, 1),
                         "_odd": odd, "_market": label, "_option": option, "_bookmaker": bookmaker})
        for book in bookmakers:
            bookmaker = book.get("name") or book.get("slug") or "Bet365"
            markets = book.get("odds") or {}
            one_x_two = markets.get("1x2") or {}
            for stage in stage_order:
                quote = one_x_two.get(stage)
                if isinstance(quote, dict) and any(quote.get(k) is not None for k in ("home", "draw", "away")):
                    for key, option in (("home", "Ev Sahibi (1)"), ("draw", "Beraberlik (X)"), ("away", "Deplasman (2)")):
                        add_price("Maç Sonucu (1X2)", option, quote.get(key), bookmaker, stage.title())
                    break
            for market_key, market_label in (("goal_line", "Gol Alt/Üst"), ("corner_line", "Korner Alt/Üst"), ("card_line", "Kart Alt/Üst")):
                market_data = markets.get(market_key) or {}
                for stage in stage_order:
                    quote = market_data.get(stage)
                    if isinstance(quote, dict) and any(quote.get(k) is not None for k in ("over", "under")):
                        line = quote.get("line")
                        add_price(market_label, "Üst", quote.get("over"), bookmaker, stage.title(), line)
                        add_price(market_label, "Alt", quote.get("under"), bookmaker, stage.title(), line)
                        break
            asian = markets.get("asian_handicap") or {}
            for stage in stage_order:
                quote = asian.get(stage)
                if isinstance(quote, dict) and any(quote.get(k) is not None for k in ("home", "away")):
                    line = quote.get("line")
                    add_price("Asya Handikap", "Ev Sahibi", quote.get("home"), bookmaker, stage.title(), line)
                    add_price("Asya Handikap", "Deplasman", quote.get("away"), bookmaker, stage.title(), line)
                    break
            btts = markets.get("btts") or {}
            for stage in stage_order:
                quote = btts.get(stage)
                if isinstance(quote, dict) and any(quote.get(k) is not None for k in ("yes", "no")):
                    add_price("Karşılıklı Gol", "Evet", quote.get("yes"), bookmaker, stage.title())
                    add_price("Karşılıklı Gol", "Hayır", quote.get("no"), bookmaker, stage.title())
                    break
            for fixed in markets.get("goal_line_fixed") or []:
                if not isinstance(fixed, dict):
                    continue
                line = fixed.get("line")
                for stage in stage_order:
                    quote = fixed.get(stage)
                    if isinstance(quote, dict) and any(quote.get(k) is not None for k in ("over", "under")):
                        add_price("Gol Alt/Üst", "Üst", quote.get("over"), bookmaker, stage.title(), line)
                        add_price("Gol Alt/Üst", "Alt", quote.get("under"), bookmaker, stage.title(), line)
                        break
        if not rows:
            st.info("5DollarFootballAPI yanıt verdi ancak bu maçta kullanılabilir oran bulunamadı.")
            return []
        st.subheader("5DollarFootballAPI gerçek oranları")
        st.caption("Her pazar için maç durumuna uygun en güncel mevcut aşama gösterilir: canlı maçta önce canlı oran, değilse kapanış/açılış. Oranlar sağlayıcıdan gelir; tahmin değildir.")
        st.dataframe([{k: v for k, v in row.items() if not k.startswith("_")} for row in rows], use_container_width=True, hide_index=True)
        show_odds_comparison(rows)
        return rows
    if source == "APIFootball.com":
        payload, err = apifootball_com_detail("get_odds", fixture_id)
        if err:
            st.warning(f"APIFootball.com oran isteği: {err}")
            return []
        match_id = str(fixture_id).replace("apifootballcom-", "")
        items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
        items = [x for x in items if str(x.get("match_id", "")) == match_id]
        if not items:
            st.info("APIFootball.com bu maç için oran döndürmedi. Paket kapsamında olmayabilir veya maç için oran yayınlanmamış olabilir.")
            return []
        all_rows = []
        label_map = {"odd_1":("Maç Sonucu (1X2)","Ev Sahibi (1)"),"odd_x":("Maç Sonucu (1X2)","Beraberlik (X)"),"odd_2":("Maç Sonucu (1X2)","Deplasman (2)"),"odd_1x":("Çifte Şans","1X"),"odd_12":("Çifte Şans","12"),"odd_x2":("Çifte Şans","X2"),"bts_yes":("Karşılıklı Gol","Evet"),"bts_no":("Karşılıklı Gol","Hayır")}
        for item in items:
            bookmaker = item.get("odd_bookmakers", "APIFootball.com")
            for key, (market, option) in label_map.items():
                odd = num(item.get(key))
                if odd and odd > 1:
                    all_rows.append({"Pazar":market,"Seçenek":option,"Oran":odd,"Oranın ham olasılığı (%)":round(100/odd,1),"_odd":odd,"_market":market,"_option":option,"_bookmaker":bookmaker})
            for key, market, option in [("o+1.5","Gol Alt/Üst 1,5","Üst 1,5"),("u+1.5","Gol Alt/Üst 1,5","Alt 1,5"),("o+2.5","Gol Alt/Üst 2,5","Üst 2,5"),("u+2.5","Gol Alt/Üst 2,5","Alt 2,5"),("o+3.5","Gol Alt/Üst 3,5","Üst 3,5"),("u+3.5","Gol Alt/Üst 3,5","Alt 3,5")]:
                odd = num(item.get(key))
                if odd and odd > 1:
                    all_rows.append({"Pazar":market,"Seçenek":option,"Oran":odd,"Oranın ham olasılığı (%)":round(100/odd,1),"_odd":odd,"_market":market,"_option":option,"_bookmaker":bookmaker})
        if not all_rows:
            st.info("Bu maç için kullanılabilir oran alanı yok.")
            return []
        st.subheader("APIFootball.com oranları")
        st.dataframe([{k:v for k,v in row.items() if not k.startswith("_")} for row in all_rows], use_container_width=True, hide_index=True)
        show_odds_comparison(all_rows)
        return all_rows
    if source not in ("Sportmonks", "API-Football"):
        st.info(f"{source or 'Bu maçın kaynağı'} bahis oranı sağlamıyor; bu kaynak için oran uç noktası tanımlı değil.")
        return []
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
        st.info("Bu maç için kullanılabilir oran verisi bulunamadı.")
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
    fixture_id_for_prediction = match.get("fixture", {}).get("id")
    if False and str(fixture_id_for_prediction or "").isdigit():
        with st.expander("📊 API-Football model tahmini ve takım karşılaştırması", expanded=False):
            prediction_data, prediction_err, _ = api_get("predictions", {"fixture": int(fixture_id_for_prediction)})
            if prediction_err:
                st.caption(f"Model tahmini alınamadı: {prediction_err}")
            elif not prediction_data:
                st.info("Bu maç için sağlayıcı model tahmini döndürülmedi.")
            else:
                prediction = prediction_data[0] if isinstance(prediction_data, list) else {}
                comparison = prediction.get("comparison") or {}
                predictions = prediction.get("predictions") or {}
                winner = predictions.get("winner") or {}
                winner_name = winner.get("name") if isinstance(winner, dict) else winner
                if winner_name:
                    st.markdown(f"**Sağlayıcı modelinin favorisi:** {winner_name}")
                advice = predictions.get("advice")
                if advice:
                    st.write(f"**Model yorumu:** {advice}")
                percent = predictions.get("percent") or {}
                if percent:
                    st.dataframe([{"Sonuç": key, "Model yüzdesi": value} for key, value in percent.items()], use_container_width=True, hide_index=True)
                if comparison:
                    st.markdown("**Takım karşılaştırması**")
                    st.dataframe([{"Gösterge": key, "Ev sahibi": (value or {}).get("home") if isinstance(value, dict) else None,
                                   "Deplasman": (value or {}).get("away") if isinstance(value, dict) else None}
                                  for key, value in comparison.items()], use_container_width=True, hide_index=True)
                st.caption("Bu, veri sağlayıcısının tahminidir; garanti veya kesin olasılık değildir. Kota tüketebilir.")
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
        team_keys = [normalize_team_key(name) for name in (home_name, away_name) if normalize_team_key(name)]
        now = datetime.now(timezone.utc)
        for item in root.findall(".//item"):
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="")
            pub = item.findtext("pubDate", default="")
            source = item.findtext("source", default="Google Haberler")
            if not title or not link:
                continue
            # Search queries can return loosely related stories. Require a team name
            # in the actual headline and a parseable, recent publication date.
            title_key = normalize_team_key(title)
            if not any(key in title_key for key in team_keys):
                continue
            try:
                published_at = parsedate_to_datetime(pub)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                age_seconds = (now - published_at.astimezone(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                continue
            if age_seconds < -24 * 3600 or age_seconds > 14 * 24 * 3600:
                continue
            items.append({"title": title, "source": source, "published": pub, "link": link})
            if len(items) >= 20:
                break
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
    st.caption("Google Haberler RSS sonuçlarında yalnızca başlığında takım adı geçen ve son 14 günde yayımlanmış kayıtlar sayılır. Başlıklar kısa sinyal özeti için kullanılır; bu tarama tüm interneti veya özel sosyal medya yorumlarını kapsamaz.")
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
    # Filter again at render time so stale results already held in Streamlit session
    # state cannot bypass the provider-level freshness check.
    if prefix == "live" and matches:
        matches = [
            match for match in matches
            if not (
                match.get("_source") == "OpenFootAPI"
                and not is_fresh_live_fixture(match)
            )
        ]
    if not matches:
        if prefix == "live":
            st.info("Şu anda kontrol edilen kaynaklarda canlı maç bulunamadı. Bu, bağlantının bozuk olduğu anlamına gelmez. Günün maçları için Tarihe göre maçlar sekmesinden bugünün tarihini seçip fikstürü getir.")
        else:
            st.info("Bu tarih ve kaynak kombinasyonunda maç bulunamadı. Başka bir tarih deneyebilir veya kaynak durumunu kontrol edebilirsin.")
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
            is_sportmonks = match.get("_source") == "Sportmonks"
            is_thesportsdb = match.get("_source") == "TheSportsDB"
            is_openfootapi = match.get("_source") == "OpenFootAPI"
            source_name = match.get("_source") or match.get("source") or ""
            capabilities = {
                "Sportmonks": {"stats", "lineup", "odds"},
                "APIFootball.com": {"stats", "lineup", "odds", "players"},
                "TheSportsDB": {"stats", "lineup"},
                "5DollarFootballAPI": {"stats", "odds"},
                "API-Football": {"stats", "lineup", "odds", "players"} if API_KEY else set(),
            }.get(source_name, set())
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            # Render only actions that this source actually supports; form is a separate ESPN lookup.
            for capability, state_key in (("stats", f"stats_{fid}"), ("lineup", f"lineup_{fid}"),
                                           ("odds", f"odds_{fid}"), ("players", f"players_{fid}")):
                if capability not in capabilities:
                    st.session_state.pop(state_key, None)
            if "stats" in capabilities and c1.button("İstatistikleri getir", key=f"{prefix}_stats_{fid}"):
                st.session_state[f"stats_{fid}"] = True
            if "lineup" in capabilities and c2.button("Kadroyu getir", key=f"{prefix}_lineup_{fid}"):
                st.session_state[f"lineup_{fid}"] = True
            if "odds" in capabilities and c3.button("Oranları getir", key=f"{prefix}_odds_{fid}"):
                st.session_state[f"odds_{fid}"] = True
            if {"stats", "odds"}.issubset(capabilities) and c4.button("Maçı analiz et", key=f"{prefix}_analyze_{fid}"):
                st.session_state[f"stats_{fid}"] = True
                st.session_state[f"odds_{fid}"] = True
                st.session_state[f"analyze_{fid}"] = True
            if "players" in capabilities and c5.button("Oyuncu istatistikleri", key=f"{prefix}_players_{fid}"):
                st.session_state[f"players_{fid}"] = True
            if c6.button("Takım formu", key=f"{prefix}_form_{fid}"):
                st.session_state[f"form_{fid}"] = True
            if is_openfootapi:
                if st.button("🔎 Maçı diğer kaynaklarda ara", key=f"{prefix}_cross_source_{fid}"):
                    with st.spinner("Aynı maç diğer canlı veri kaynaklarında aranıyor..."):
                        alternatives, match_error = find_other_source_matches(match)
                    st.session_state[f"cross_source_matches_{fid}"] = alternatives or []
                    st.session_state[f"cross_source_error_{fid}"] = match_error
                if st.session_state.get(f"cross_source_matches_{fid}") is not None:
                    alternatives = st.session_state.get(f"cross_source_matches_{fid}") or []
                    match_error = st.session_state.get(f"cross_source_error_{fid}")
                    if match_error:
                        st.warning(match_error)
                    elif alternatives:
                        st.success(f"Aynı iki takımı eşleştiren {len(alternatives)} alternatif kayıt bulundu.")
                        for alternative in alternatives:
                            alt_source = alternative.get("_source") or alternative.get("source") or "Bilinmeyen kaynak"
                            alt_fixture = alternative.get("fixture") or {}
                            alt_status = alt_fixture.get("status") or {}
                            alt_teams = alternative.get("teams") or {}
                            alt_goals = alternative.get("goals") or {}
                            st.markdown(
                                f"**{alt_source}:** "
                                f"{(alt_teams.get('home') or {}).get('name', 'Ev sahibi')} "
                                f"{alt_goals.get('home', '—')}–{alt_goals.get('away', '—')} "
                                f"{(alt_teams.get('away') or {}).get('name', 'Deplasman')} · "
                                f"{alt_status.get('elapsed') or '—'}'"
                            )
                            st.caption("Takım adları eşleştirildi; maç tarihi, canlı durumu ve skor tutarlılığı ayrıca kontrol edilir. Maç kimliği ilgili sağlayıcıya aittir.")
                            if st.button(f"{alt_source} verilerini aç", key=f"{prefix}_cross_open_{fid}_{alt_source}_{alt_fixture.get('id')}"):
                                st.session_state[f"cross_source_selected_{fid}"] = alternative
                        selected_alternative = st.session_state.get(f"cross_source_selected_{fid}")
                        if selected_alternative:
                            selected_source = selected_alternative.get("_source") or selected_alternative.get("source")
                            selected_id = (selected_alternative.get("fixture") or {}).get("id")
                            if selected_source in ("5DollarFootballAPI", "Sportmonks", "APIFootball.com", "API-Football", "TheSportsDB"):
                                selected_capabilities = {
                                    "5DollarFootballAPI": ("stats", "odds"),
                                    "Sportmonks": ("stats", "lineup", "odds"),
                                    "APIFootball.com": ("stats", "lineup", "odds", "players"),
                                    "API-Football": ("stats", "lineup", "odds", "players"),
                                    "TheSportsDB": ("stats", "lineup"),
                                }.get(selected_source, ())
                                actions = st.columns(4)
                                if "stats" in selected_capabilities and actions[0].button("Eşleşen maç: istatistik", key=f"{prefix}_cross_stats_{fid}"):
                                    st.session_state[f"cross_stats_{fid}"] = True
                                if "lineup" in selected_capabilities and actions[1].button("Eşleşen maç: kadro", key=f"{prefix}_cross_lineup_{fid}"):
                                    st.session_state[f"cross_lineup_{fid}"] = True
                                if "odds" in selected_capabilities and actions[2].button("Eşleşen maç: oran", key=f"{prefix}_cross_odds_{fid}"):
                                    st.session_state[f"cross_odds_{fid}"] = True
                                if {"stats", "odds"}.issubset(selected_capabilities) and actions[3].button("Eşleşen maçı analiz et", key=f"{prefix}_cross_analyze_{fid}"):
                                    st.session_state[f"cross_analyze_{fid}"] = True
                                if st.session_state.get(f"cross_stats_{fid}"):
                                    show_stats(selected_id, selected_alternative)
                                if st.session_state.get(f"cross_lineup_{fid}"):
                                    show_lineups(selected_id, selected_alternative)
                                if st.session_state.get(f"cross_odds_{fid}"):
                                    show_odds(selected_id, selected_alternative)
                                if st.session_state.get(f"cross_analyze_{fid}"):
                                    cross_stats = show_stats(selected_id, selected_alternative)
                                    cross_odds = show_odds(selected_id, selected_alternative)
                                    analyze_match(selected_alternative, cross_stats, cross_odds)
                            else:
                                st.info(f"{selected_source} bu uygulamada bu maç için istatistik/oran uç noktası sağlamıyor. Eşleşen kaynak kaydı yalnızca kimlik doğrulaması için gösterildi.")
                    else:
                        st.info("Diğer etkin canlı kaynaklarda iki takımın adları tam eşleşen bir kayıt bulunamadı. Bu, maçın başka bir sağlayıcıda kesinlikle bulunmadığı anlamına gelmez.")
                st.caption("OpenFootAPI bu maçta yalnızca canlı skor/fikstür alanlarını sağlar. Diğer kaynakta tam takım eşleşmesi bulunursa o kaynağın kendi maç kimliğiyle desteklenen veriler denenir.")
            elif is_sportmonks:
                st.caption("Sportmonks maçı: istatistik/kadro maç kimliğiyle doğrudan istenir. Canlı oranlar ayrı uç noktadan denenir; ücretsiz hesapta canlı oran erişimi kapalı olabilir.")
            elif is_thesportsdb:
                tsdb_event_id = str(fid).replace("tsdb-", "", 1)
                st.caption("TheSportsDB fikstürü: aşağıdaki ek düğmeler bu sağlayıcının sunduğu maç istatistiklerini, kadroyu ve olay akışını sorgular. Ücretsiz uç noktalarda veri alanları/limitleri sınırlı olabilir.")
                if st.button("TheSportsDB olay akışı", key=f"{prefix}_tsdb_timeline_{fid}"):
                    with st.spinner("Maç olayları alınıyor..."):
                        payload, err = thesportsdb_event_detail(tsdb_event_id, "lookuptimeline.php")
                    if err:
                        st.warning(err)
                    elif payload and any(payload.values()):
                        st.json(payload)
                    else:
                        st.info("Bu maç için TheSportsDB olay akışı yok.")
            elif match.get("_source") not in (None, "API-Football", "Sportmonks", "OpenFootAPI", "5DollarFootballAPI", "APIFootball.com"):
                st.caption(f"Bu maçın fikstür kaynağı: {match.get('_source')}. Bu kaynağın maç ID'si API-Football ID'si olmadığı için API-Football istatistik/oran uç noktalarıyla sorgulanmaz. Gelişmiş istatistik için destekleyen bir sağlayıcıdaki eşleşmiş maçı kullan.")
            if not is_openfootapi and st.button("Kaynak uygunluğunu kontrol et", key=f"{prefix}_diag_{fid}"):
                current_source = match.get("_source") or match.get("source") or "Bilinmeyen kaynak"
                if current_source == "Sportmonks":
                    st.info("Sportmonks istatistikleri/kadrosu maç kimliğiyle, oranları ayrı canlı oran uç noktasıyla sorgulanır; paket kapsamı geçerlidir.")
                elif current_source == "5DollarFootballAPI":
                    st.info("5DollarFootballAPI bu uygulamada istatistik ve Bet365 oranları için kullanılır. Ücretsiz kapsam ilk 5 ligle sınırlıdır; kadro ve oyuncu maç istatistiği bağlı değil.")
                elif current_source == "TheSportsDB":
                    st.info("TheSportsDB istatistik ve kadro uç noktaları bağlandı; veri yalnızca sağlayıcıda ilgili maç için varsa döner. Bu kaynak oran sağlamaz.")
                elif current_source == "APIFootball.com":
                    st.info("APIFootball.com istatistik, kadro, oran ve oyuncu maç istatistiği uç noktaları sorgulanabilir; sonuç hesap kapsamına bağlıdır.")
                else:
                    st.info(f"{current_source} için maç istatistiği/kadro/oran uç noktası uygulamaya bağlı değil; form için ESPN eşleştirmesi denenebilir.")
            if st.session_state.get(f"form_{fid}"):
                show_team_form_for_match(match)
            stats = None
            odds = []
            if st.session_state.get(f"players_{fid}"):
                show_player_statistics(fid, match)
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

live_tab, date_tab, source_tab, analytics_tab, info_tab = st.tabs(["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "🛰️ Kaynak durumu", "📈 Takım / oyuncu analizi", "ℹ️ Program hakkında"])
with live_tab:
    st.subheader("Şu anda oynanan maçlar")
    auto_refresh = st.checkbox("Canlı maçları otomatik yenile (30 saniye)", value=False, key="live_auto_refresh")
    refresh_tick = st_autorefresh(interval=30_000, key="live_refresh_tick") if auto_refresh else None
    refresh_due = bool(auto_refresh and refresh_tick is not None and refresh_tick != st.session_state.get("_last_live_refresh_tick"))
    if refresh_due:
        st.session_state["_last_live_refresh_tick"] = refresh_tick
    if st.button("Canlı maçları yükle / yenile") or refresh_due:
        with st.spinner("Canlı maçlar yükleniyor..."):
            live_diagnostics = []
            data, err = five_dollar_live_matches() if FIVE_DOLLAR_FOOTBALL_API_KEY else (None, "5DollarFootballAPI anahtarı tanımlı değil; açık kaynaklar deneniyor.")
            live_diagnostics.append({"Kaynak": "5DollarFootballAPI", "Alınan kayıt": len(data or []) if data is not None else "—", "Canlı filtresinden geçen": len(data or []) if data is not None else "—", "Not": err or ("HTTP 200" if data is not None else "Anahtar tanımlı değil")})
            source = "5DollarFootballAPI" if data is not None else "Ücretsiz/açık skor kaynakları"
            five_dollar_error = err
            five_dollar_returned = data is not None
            # Providers phrase exhausted quotas differently (e.g. "request limit for the day").
            err_text = str(err or "").lower()
            quota_exhausted = any(term in err_text for term in (
                "429", "ratelimit", "rate limit", "request limit", "daily limit",
                "limit for the day", "too many requests", "reached the request limit"
            ))
            if err:
                # Any primary-provider failure (including account suspension) must trigger fallback.
                if SPORTMONKS_API_TOKEN:
                    sm_data, sm_err = sportmonks_live_matches()
                    if not sm_err:
                        data = sportmonks_to_api_football(sm_data or [])
                        err = None
                        source = "Sportmonks (lig kapsamı plana bağlı)"
                    else:
                        err = f"Birincil kaynak kullanılamadı. Sportmonks yedeği: {sm_err}"
            elif not err and API_KEY and SPORTMONKS_API_TOKEN:
                # A failed supplement must never invalidate a successful primary result.
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
                    source = "API-Football + Sportmonks (ek maçlar birleştirildi)"
                elif sm_err:
                    set_provider_status("Sportmonks", True, False, "Tamamlayıcı kaynak kullanılamadı; ana kaynak korunuyor.")
            # Empty primary response is also a fallback trigger: a successful HTTP 200 with zero fixtures must not hide other providers.
            # Sportmonks must be tried here too: a successful but empty 5Dollar response is not a reason to skip it.
            sportmonks_live_count = None
            sportmonks_normalized_count = None
            if not data and SPORTMONKS_API_TOKEN:
                sm_data, sm_err = sportmonks_live_matches()
                sportmonks_live_count = len(sm_data or []) if not sm_err else None
                live_diagnostics.append({"Kaynak": "Sportmonks", "Alınan kayıt": len(sm_data or []) if not sm_err else "—", "Canlı filtresinden geçen": len(sm_data or []) if not sm_err else "—", "Not": sm_err or "Canlı skor uç noktası"})
                if not sm_err and sm_data:
                    data = sportmonks_to_api_football(sm_data)
                    sportmonks_normalized_count = len(data or [])
                    set_provider_status("Sportmonks", True, True, f"Canlı sorgu: {sportmonks_live_count} kayıt; uygulamaya aktarılan: {sportmonks_normalized_count}.")
                    if data:
                        err = None
                        source = "Sportmonks canlı skorları (lig kapsamı plana bağlı)"
                elif not sm_err:
                    sportmonks_normalized_count = 0
                    set_provider_status("Sportmonks", True, True, "Canlı sorgu: 0 kayıt döndü.")
                else:
                    set_provider_status("Sportmonks", True, False, str(sm_err)[:180])
            if not data and FOOTBALL_DATA_TOKEN:
                # Check today's fixtures for live statuses within the competitions covered by this plan.
                fd_today, fd_err = football_data_matches_for_date(date.today().isoformat())
                fd_live = [
                    item for item in (fd_today or [])
                    if str(((item.get("fixture") or {}).get("status") or {}).get("short") or "").upper()
                    in ("IN_PLAY", "PAUSED", "LIVE", "HT")
                ]
                live_diagnostics.append({"Kaynak": "football-data.org", "Alınan kayıt": len(fd_today or []) if not fd_err else "—", "Canlı filtresinden geçen": len(fd_live) if not fd_err else "—", "Not": fd_err or "Bugünün fikstüründe canlı/devre arası durumu"})
                if fd_live:
                    data = fd_live
                    err = None
                    source = "football-data.org canlı maçları (kapsam plana bağlı)"
                    set_provider_status("football-data.org", True, True, f"Bugün {len(fd_today or [])} maç; canlı/devre arası: {len(fd_live)}.")
                elif not fd_err:
                    set_provider_status("football-data.org", True, True, f"Bugün {len(fd_today or [])} maç; canlı/devre arası: 0.")
            if not data:
                if BSD_API_TOKEN:
                    bsd_data, bsd_err = bsd_live_matches()
                    live_diagnostics.append({"Kaynak": "Bzzoiro Sports Data", "Alınan kayıt": len(bsd_data or []) if not bsd_err else "—", "Canlı filtresinden geçen": len(bsd_data or []) if not bsd_err else "—", "Not": bsd_err or "Canlı skor uç noktası"})
                    if not bsd_err:
                        data = bsd_data or []
                        err = None
                        source = "Bzzoiro Sports Data"
                if not data:
                    today_text = date.today().isoformat()
                    # Check TheSportsDB today-events as another public fallback before ESPN.
                    tsdb_live, tsdb_err = thesportsdb_matches_for_date(today_text)
                    live_tsdb = []
                    now_utc = datetime.now(timezone.utc)
                    for item in tsdb_live or []:
                        fixture = item.get("fixture") or {}
                        status_short = (fixture.get("status") or {}).get("short")
                        if status_short not in ("LIVE", "HT"):
                            continue
                        try:
                            kickoff = datetime.fromisoformat(str(fixture.get("date")).replace("Z", "+00:00"))
                            if kickoff.tzinfo is None:
                                kickoff = kickoff.replace(tzinfo=timezone.utc)
                            age_hours = (now_utc - kickoff.astimezone(timezone.utc)).total_seconds() / 3600
                            if age_hours < -0.25 or age_hours > 5:
                                continue
                        except (TypeError, ValueError):
                            continue
                        item["_source"] = "TheSportsDB"
                        live_tsdb.append(item)
                    live_diagnostics.append({"Kaynak": "TheSportsDB", "Alınan kayıt": len(tsdb_live or []) if not tsdb_err else "—", "Canlı filtresinden geçen": len(live_tsdb) if not tsdb_err else "—", "Not": tsdb_err or "LIVE/HT ve başlama zamanı filtresi"})
                    if live_tsdb:
                        data = live_tsdb
                        err = None
                        source = "TheSportsDB açık maç listesi (kapsam sınırlı; oran yok)"
                    if not data:
                        sportscore_data, sportscore_err = sportscore_live_matches()
                        live_diagnostics.append({"Kaynak": "SportScore", "Alınan kayıt": len(sportscore_data or []) if not sportscore_err else "—", "Canlı filtresinden geçen": len(sportscore_data or []) if not sportscore_err else "—", "Not": sportscore_err or "Canlı fikstür uç noktası"})
                        st.session_state["live_diagnostics"] = live_diagnostics
                        if sportscore_data:
                            data = sportscore_data
                            err = None
                            source = "SportScore canlı skorları"
                            st.session_state["live_notice"] = "Canlı skorlar SportScore üzerinden gösteriliyor. Kaynak kapsamı ve güncelleme sıklığı sağlayıcıya bağlıdır."
                    if not data:
                        apifc_data, apifc_err = apifootball_com_live_matches()
                        live_diagnostics.append({"Kaynak": "APIFootball.com", "Alınan kayıt": len(apifc_data or []) if not apifc_err else "—", "Canlı filtresinden geçen": len(apifc_data or []) if not apifc_err else "—", "Not": apifc_err or "match_live=1 / aktif durum filtresi"})
                        st.session_state["live_diagnostics"] = live_diagnostics
                        if apifc_data:
                            data = apifc_data
                            err = None
                            source = "APIFootball.com canlı skorları"
                            st.session_state["live_notice"] = "APIFootball.com canlı skorları gösteriliyor. Kapsam hesabınızın paketine bağlıdır."
                    if not data:
                        of_data, of_err = openfootapi_live_matches()
                        live_diagnostics.append({"Kaynak": "OpenFootAPI", "Alınan kayıt": len(of_data or []) if not of_err else "—", "Canlı filtresinden geçen": len(of_data or []) if not of_err else "—", "Not": of_err or "Bugünün fikstüründe status=live"})
                        st.session_state["live_diagnostics"] = live_diagnostics
                        if of_data:
                            data = of_data
                            err = None
                            source = "OpenFootAPI canlı skorları"
                            st.session_state["live_notice"] = "OpenFootAPI canlı maçları gösteriliyor. Ücretsiz demo erişimi sınırlıdır; daha geniş erişim için OPENFOOT_API_KEY sırrı eklenebilir."
                    if not data:
                        oldb_live, oldb_live_err = openligadb_live_matches()
                        live_diagnostics.append({"Kaynak": "OpenLigaDB", "Alınan kayıt": len(oldb_live or []) if not oldb_live_err else "—", "Canlı filtresinden geçen": len(oldb_live or []) if not oldb_live_err else "—", "Not": oldb_live_err or "Almanya Bundesliga / 2. Bundesliga; başlama saati penceresi"})
                        st.session_state["live_diagnostics"] = live_diagnostics
                        if oldb_live:
                            data = oldb_live
                            err = None
                            source = "OpenLigaDB canlı maçları (Almanya; dakika tahmini)"
                            st.session_state["live_notice"] = "OpenLigaDB canlı maçı gösteriliyor. Dakika başlama saatinden tahmin edilir; skor güncellemesi topluluk verisine bağlıdır."
                    if not data:
                        espn_data, espn_err = espn_matches_for_date(today_text)
                        # ESPN can occasionally leave an old event marked as in progress.
                        # Only show plausible live matches kicked off within the last five hours.
                        now_utc = datetime.now(timezone.utc)
                        live_espn = []
                        for item in espn_data or []:
                            fixture = item.get("fixture") or {}
                            status_obj = fixture.get("status") or {}
                            status_short = str(status_obj.get("short") or "").upper()
                            # Only accept explicit active states; stale ESPN event statuses
                            # are not enough if the event has a final/full-time marker.
                            status_long = str(status_obj.get("long") or "").strip().lower()
                            if status_short not in ("LIVE", "HT"):
                                continue
                            if any(term in status_long for term in ("final", "full time", "match finished", "after penalties", "after extra time")):
                                continue
                            try:
                                kickoff = datetime.fromisoformat(str(fixture.get("date")).replace("Z", "+00:00"))
                                if kickoff.tzinfo is None:
                                    kickoff = kickoff.replace(tzinfo=timezone.utc)
                                age_hours = (now_utc - kickoff.astimezone(timezone.utc)).total_seconds() / 3600
                                if age_hours < -0.25 or age_hours > 5:
                                    continue
                            except (TypeError, ValueError):
                                continue
                            # ESPN status/clock is stale in some feeds; don't label a
                            # match as live if its own clock is at/after 90 minutes and
                            # it has no active clock update.
                            elapsed = status_obj.get("elapsed")
                            if status_short == "LIVE" and elapsed is not None and int(elapsed) >= 90:
                                continue
                            live_espn.append(item)
                        espn_status_counts = {}
                        espn_age_rejected = 0
                        espn_missing_kickoff = 0
                        for candidate in espn_data or []:
                            f = candidate.get("fixture") or {}
                            s = str(((f.get("status") or {}).get("short") or "UNKNOWN")).upper()
                            espn_status_counts[s] = espn_status_counts.get(s, 0) + 1
                            if s in ("LIVE", "HT"):
                                try:
                                    ko = datetime.fromisoformat(str(f.get("date")).replace("Z", "+00:00"))
                                    if ko.tzinfo is None:
                                        ko = ko.replace(tzinfo=timezone.utc)
                                    age = (now_utc - ko.astimezone(timezone.utc)).total_seconds() / 3600
                                    if age < -0.25 or age > 5:
                                        espn_age_rejected += 1
                                except (TypeError, ValueError):
                                    espn_missing_kickoff += 1
                        live_diagnostics.append({"Kaynak": "ESPN", "Alınan kayıt": len(espn_data or []) if not espn_err else "—", "Canlı filtresinden geçen": len(live_espn) if not espn_err else "—", "Not": (espn_err or f"Durumlar: {espn_status_counts}; saat filtresinden elenen: {espn_age_rejected}; saati eksik: {espn_missing_kickoff}")})
                        st.session_state["live_diagnostics"] = live_diagnostics
                        if live_espn:
                            data = live_espn
                            err = None
                            source = "ESPN açık skor panoları (lig kapsamı sınırlı; oran yok)"
                            st.session_state["live_notice"] = "ESPN'de canlı olarak işaretlenen maçlar gösteriliyor; durum ve dakika sağlayıcıya bağlıdır."
                        elif not espn_err:
                            data = []
                            err = None
                            source = "Canlı maç bulunamadı"
                            if FIVE_DOLLAR_FOOTBALL_API_KEY and five_dollar_error:
                                st.session_state["live_notice"] = "5DollarFootballAPI başarısız oldu: " + str(five_dollar_error)[:220]
                            elif FIVE_DOLLAR_FOOTBALL_API_KEY and five_dollar_returned:
                                sm_note = ""
                                if SPORTMONKS_API_TOKEN and sportmonks_live_count is not None:
                                    sm_note = f" Sportmonks canlı sorgusu {sportmonks_live_count} kayıt döndürdü; uygulamaya aktarılan {sportmonks_normalized_count or 0} maç."
                                elif SPORTMONKS_API_TOKEN:
                                    sm_note = " Sportmonks canlı sorgusu da başarısız oldu; ayrıntı Kaynak durumu bölümünde."
                                st.session_state["live_notice"] = "5DollarFootballAPI HTTP 200 verdi ancak canlı maç listesi boş döndü. ESPN de uygun canlı maç bulamadı." + sm_note + " Bu kaynakların yanıt vermesi, şu anda maç bulunduğu anlamına gelmez."
                            else:
                                st.session_state["live_notice"] = "Ücretsiz kaynaklar yanıt verdi ancak kontrol edilen liglerde şu an canlı maç bulunamadı. Tarihe göre maçlar sekmesini kullanabilirsin."
                        elif err:
                            err = str(err) + " | ESPN yedeği de kullanılamadı: " + espn_err
        if err:
            st.error(err)
        else:
            with st.spinner("Ek canlı kaynaklar birleştiriliyor ve tekrarlar ayıklanıyor..."):
                data = merge_live_match_feeds(data or [])
            st.session_state["live_matches"] = data
            st.session_state["live_source"] = f"{source} + ek kaynak birleştirme"
            if data:
                st.session_state.pop("live_notice", None)
            elif not st.session_state.get("live_notice"):
                st.session_state["live_notice"] = "Kontrol edilen kaynaklarda canlı maç bulunamadı."

    if st.session_state.get("live_notice"):
        st.info(st.session_state["live_notice"])
    st.markdown('Veri sağlayıcıları: <a href="https://sportscore.com/" target="_blank" rel="dofollow">SportScore</a> · <a href="https://openfootapi.com/docs" target="_blank" rel="dofollow">OpenFootAPI</a>', unsafe_allow_html=True)
    if st.session_state.get("live_diagnostics"):
        with st.expander("🔎 Canlı veri teşhisi — kaynak kaynak kayıt sayıları", expanded=True):
            st.dataframe(st.session_state["live_diagnostics"], use_container_width=True, hide_index=True)
            st.caption("Alınan kayıt = kaynağın döndürdüğü maç/kayıt sayısı. Canlı filtresinden geçen = uygulamanın canlı kabul ettiği maç sayısı.")
    if st.session_state.get("live_engine_diagnostics"):
        with st.expander("🧩 Birleştirilmiş canlı kaynaklar", expanded=False):
            st.dataframe(st.session_state["live_engine_diagnostics"], use_container_width=True, hide_index=True)
    if "live_matches" in st.session_state:
        st.caption("Canlı veri kaynağı: " + st.session_state.get("live_source", "Ücretsiz/açık skor kaynakları"))
        show_matches(st.session_state["live_matches"], "live")
    else:
        st.info("Canlı maçları görmek için yukarıdaki düğmeye basın.")
with date_tab:
    st.subheader("Tarihe göre fikstür")
    chosen = st.date_input("Maç tarihi", value=date.today())
    if st.button("Fikstürü getir"):
        with st.spinner("Fikstür kaynakları birleştiriliyor..."):
            # Eski API-Football devre dışı; ücretsiz kaynaklar kullanılır.
            primary = []
            fd_matches, fd_err = football_data_matches_for_date(chosen.isoformat())
            oldb_matches, oldb_err = openligadb_matches_for_date(chosen.isoformat())
            tsdb_matches, tsdb_err = thesportsdb_matches_for_date(chosen.isoformat())
            espn_matches, espn_err = espn_matches_for_date(chosen.isoformat())
            combined = merge_fixture_sources(primary, (fd_matches or []) + (oldb_matches or []) + (tsdb_matches or []) + (espn_matches or []))
            st.session_state["date_matches"] = combined
            st.session_state["date_label"] = chosen.isoformat()
            st.session_state["date_sources"] = {
                "football-data.org": len(fd_matches or []), "OpenLigaDB": len(oldb_matches or []), "TheSportsDB": len(tsdb_matches or []), "ESPN": len(espn_matches or [])
            }
            st.session_state["date_errors"] = {
                "football-data.org": fd_err,
                "OpenLigaDB": oldb_err,
                "TheSportsDB": tsdb_err,
                "ESPN": espn_err,
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
with source_tab:
    st.subheader("Veri sağlayıcıları ve kota yönetimi")
    st.caption("API anahtarları gösterilmez. Durumlar uygulamanın son gözlemlediği yanıtları yansıtır; tüm liglerin kapsandığını garanti etmez.")
    if st.button("🧪 Bağlantıları şimdi test et", key="test_all_providers"):
        test_rows = []
        with st.spinner("Her kaynağa birer hafif test isteği gönderiliyor..."):
            # Eski API-Football devre dışı; bu kaynağa istek gönderilmez.
            if SPORTMONKS_API_TOKEN:
                _, test_err = sportmonks_live_matches()
                set_provider_status("Sportmonks", True, not bool(test_err), (test_err or "Canlı skor uç noktası yanıt verdi.")[:180])
            else:
                set_provider_status("Sportmonks", False, False, "SPORTMONKS_API_TOKEN tanımlı değil.")
            if FOOTBALL_DATA_TOKEN:
                _, test_err = football_data_get("matches", {"dateFrom": date.today().isoformat(), "dateTo": date.today().isoformat()})
                set_provider_status("football-data.org", True, not bool(test_err), (test_err or "Maç uç noktası yanıt verdi.")[:180])
            else:
                set_provider_status("football-data.org", False, False, "FOOTBALL_DATA_TOKEN tanımlı değil.")
            if BSD_API_TOKEN:
                _, test_err = bsd_live_matches()
                if test_err:
                    set_provider_status("Bzzoiro Sports Data", True, False, test_err[:180])
            else:
                set_provider_status("Bzzoiro Sports Data", False, None, "BSD_API_TOKEN yok; ücretsiz kayıt sonrası eklenebilir.")
            if APIFOOTBALL_API_KEY:
                _, test_err = apifootball_com_live_matches()
                if test_err:
                    set_provider_status("APIFootball.com", True, False, test_err[:180])
            else:
                set_provider_status("APIFootball.com", False, False, "APIFOOTBALL_API_KEY tanımlı değil.")
            # Test OpenFootAPI with the configured secret without exposing it.
            _, of_test_err = openfootapi_live_matches()
            if of_test_err:
                set_provider_status("OpenFootAPI", bool(str(secret("OPENFOOT_API_KEY", "")).strip()), False, of_test_err[:180])
            # TheSportsDB free schedule endpoint; no secret required for public key 123.
            _, test_err = thesportsdb_matches_for_date(date.today().isoformat())
            if test_err and "bu tarihte futbol maçı döndürmedi" not in test_err:
                set_provider_status("TheSportsDB", True, False, test_err[:180])
            elif test_err:
                set_provider_status("TheSportsDB", True, True, "HTTP 200; bugün maç kaydı yok.")
            # Public endpoints: test one ESPN competition and one OpenLigaDB competition.
            _, test_err = espn_scoreboard_for_date(date.today().isoformat(), "eng.1")
            if test_err:
                set_provider_status("ESPN", True, False, test_err[:180])
            else:
                set_provider_status("ESPN", True, True, "Premier League skor panosu yanıt verdi.")
            try:
                test_response = requests.get("https://api.openligadb.de/getmatchdata/bl1/2026", timeout=10)
                if test_response.status_code == 200:
                    try:
                        test_count = len(test_response.json())
                    except ValueError:
                        test_count = 0
                    set_provider_status("OpenLigaDB", True, True, f"HTTP 200; {test_count} Bundesliga kayıt satırı.")
                else:
                    set_provider_status("OpenLigaDB", True, False, f"HTTP {test_response.status_code}")
            except requests.RequestException as exc:
                set_provider_status("OpenLigaDB", True, False, f"Bağlantı hatası: {exc}"[:180])
        st.success("Bağlantı testleri tamamlandı. Sonuçları aşağıdaki tabloda görebilirsin.")
    provider_status_table()
    st.markdown("### Veri kapsamı denetimi")
    st.caption("Bu tablo kodda gerçekten bağlı olan veri yollarını gösterir; yeşil bir bağlantı testi tek başına o maç için veri bulunduğunu kanıtlamaz.")
    coverage_rows = [
        {"Veri türü": "Fikstür / skor", "Bağlı kaynaklar": "5DollarFootballAPI (anahtar; ücretsiz planda ilk 5 lig), OpenFootAPI, ESPN (seçili ligler), TheSportsDB, OpenLigaDB, SportScore; anahtara bağlı Sportmonks / APIFootball.com / football-data.org", "Sınır": "Lig kapsamı, canlı güncelleme ve kimlik eşleşmesi kaynağa göre değişir."},
        {"Veri türü": "Son maçlar / form", "Bağlı kaynaklar": "ESPN takım son maçları; football-data.org sonuçları", "Sınır": "ESPN yalnızca seçili lig kodlarında sorgulanıyor; formun tüm liglerde otomatik hesaplanması henüz yok."},
        {"Veri türü": "Maç istatistikleri", "Bağlı kaynaklar": "5DollarFootballAPI (anahtar; canlı atak/şut/topa sahip olma), Sportmonks, APIFootball.com; TheSportsDB maç istatistikleri", "Sınır": "5Dollar ücretsiz planda ilk 5 lig; TheSportsDB yalnızca etkinlikte kayıtlı alanları verir."},
        {"Veri türü": "İlk 11 / kadro", "Bağlı kaynaklar": "Sportmonks, APIFootball.com; TheSportsDB maç kadrosu", "Sınır": "Kadro yayınlanmamışsa veya kaynakta yoksa gösterilemez."},
        {"Veri türü": "Oyuncu maç istatistikleri", "Bağlı kaynaklar": "APIFootball.com; eski API-Football yolu devre dışı", "Sınır": "TheSportsDB kadro/oyuncu profili, oyuncu başına canlı maç istatistiği yerine geçmez."},
        {"Veri türü": "Bahis oranları", "Bağlı kaynaklar": "5DollarFootballAPI (anahtar; ücretsiz planda Bet365 ve ilk 5 lig), Sportmonks canlı oran uç noktası (paket erişimine bağlı), APIFootball.com", "Sınır": "5Dollar oranları için sağlayıcıda o maç/lig oranı bulunmalı; OpenFootAPI, ESPN, OpenLigaDB, football-data.org ücretsiz kapsamı ve TheSportsDB oran kaynağı değil."},
        {"Veri türü": "Haber", "Bağlı kaynaklar": "Google Haberler RSS", "Sınır": "Başlık eşleşmesi; haber doğrulama veya sosyal medya duygu analizi değil."},
    ]
    st.dataframe(coverage_rows, use_container_width=True, hide_index=True)
    st.markdown("Football data by [5DollarFootballAPI](https://5dollarfootballapi.com) · Ücretsiz planın lig ve istek sınırları geçerlidir.")
    st.markdown("**Kota koruması ve kapsam**")
    st.write("- Tekrarlanan çağrılar Streamlit önbelleğinden karşılanır; canlı skor ve fikstür verileri farklı sürelerde önbelleğe alınır.")
    st.write("- APIFootball.com ayrı bir sağlayıcıdır; APIFOOTBALL_API_KEY ile apiv2 endpointine bağlanır. Anahtar yoksa devre dışı kalır.")
    st.write("- API-Football kota/bağlantı hatasında Sportmonks, BSD_API_TOKEN tanımlıysa Bzzoiro, ardından seçili liglerde ESPN denenir.")
    st.write("- football-data.org, OpenLigaDB, ESPN ve TheSportsDB tamamlayıcı kaynaklardır. TheSportsDB ücretsiz uç noktası fikstür/maç metaverisi sağlar; gelişmiş canlı istatistik kaynağı değildir. Bzzoiro Sports Data için BSD_API_TOKEN gerekir. Hiçbir kaynak tek başına tüm lig ve veri türlerini garanti etmez.")
    st.write("- Sağlayıcı kotası kodla artırılamaz. Tüm kaynaklar sınırına ulaşırsa veri gecikebilir veya bulunamayabilir.")
    if st.button("Kaynak durumlarını sıfırla", key="reset_provider_status"):
        st.session_state["provider_statuses"] = {}
        st.rerun()

with analytics_tab:
    st.subheader("Takım formu ve oyuncu analizi")
    st.caption("API-Football v3 ve FootyStats kaldırıldı. Takım formu ESPN skor panosundan; oyuncu profili ve varsa istatistikleri TheSportsDB üzerinden sorgulanır. Eksik alanlar tahmin edilmez.")

    team_col, player_col = st.columns(2)
    with team_col:
        st.markdown("### 🛡️ Takım formu")
        st.caption("Takımın son maçları ESPN'in herkese açık skor panosundan sorgulanır. Kapsam lig ve tarih aralığına bağlıdır.")
        league_choices = {
            "Türkiye Süper Lig": "tur.1",
            "İngiltere Premier League": "eng.1",
            "İspanya La Liga": "esp.1",
            "İtalya Serie A": "ita.1",
            "Almanya Bundesliga": "ger.1",
            "Fransa Ligue 1": "fra.1",
            "Portekiz Primeira Liga": "por.1",
            "Hollanda Eredivisie": "ned.1",
            "İskoçya Premiership": "sco.1",
            "ABD MLS": "usa.1",
        }
        selected_league = st.selectbox("Lig", list(league_choices.keys()), key="analytics_espn_league")
        team_query = st.text_input("Takım adı", placeholder="Örn. Galatasaray", key="analytics_team_query")
        if st.button("Son 5 maçı ve formu bul", key="analytics_team_analyze") and team_query.strip():
            with st.spinner("ESPN'den son maçlar sorgulanıyor..."):
                recent, recent_err = espn_team_last_matches(team_query.strip(), league_choices[selected_league])
            st.session_state["analytics_team_form"] = recent or []
            st.session_state["analytics_team_form_error"] = recent_err
            st.session_state["analytics_team_form_label"] = f"{team_query.strip()} · {selected_league}"
            st.session_state["analytics_team_form_team_query"] = team_query.strip()
        if st.session_state.get("analytics_team_form_error"):
            st.warning(st.session_state["analytics_team_form_error"])
        elif st.session_state.get("analytics_team_form_label") and st.session_state.get("analytics_team_form"):
            form = st.session_state["analytics_team_form"]
            st.caption(st.session_state["analytics_team_form_label"])
            wins = draws = losses = gf = ga = 0
            rows = []
            team_norm = normalize_team_key(st.session_state.get("analytics_team_form_team_query", ""))
            for item in form:
                is_home = team_norm in normalize_team_key(item["home"])
                own, opp = (item["home_goals"], item["away_goals"]) if is_home else (item["away_goals"], item["home_goals"])
                if own > opp:
                    wins += 1; result = "G"
                elif own == opp:
                    draws += 1; result = "B"
                else:
                    losses += 1; result = "M"
                gf += own; ga += opp
                rows.append({"Tarih": item["date"], "Ev sahibi": item["home"],
                             "Skor": f'{item["home_goals"]} - {item["away_goals"]}',
                             "Deplasman": item["away"], "Takım sonucu": result})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Galibiyet", wins); c2.metric("Beraberlik", draws)
            c3.metric("Mağlubiyet", losses); c4.metric("Atılan / yenilen", f"{gf} / {ga}")
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption("G = galibiyet, B = beraberlik, M = mağlubiyet. Yalnızca ESPN'in tamamlandı olarak işaretlediği ve skoru bulunan maçlar sayılır.")
        elif st.session_state.get("analytics_team_form_label"):
            st.info("ESPN seçilen takım için bu tarih aralığında tamamlanmış maç bulamadı. Takım adını veya ligi kontrol et.")

    with player_col:
        st.markdown("### 👤 Oyuncu profili / istatistikleri")
        st.caption("TheSportsDB ücretsiz uç noktaları oyuncu araması ve profil/istatistik yanıtı sağlayabilir; kapsam ve alanlar değişebilir.")
        player_query = st.text_input("Oyuncu adı", placeholder="Örn. Danny Welbeck", key="analytics_player_query")
        if st.button("Oyuncuyu TheSportsDB'de ara", key="analytics_player_search") and player_query.strip():
            with st.spinner("Oyuncu aranıyor..."):
                player_rows, player_err = thesportsdb_search_player(player_query.strip())
            st.session_state["analytics_players_found"] = player_rows or []
            st.session_state["analytics_players_error"] = player_err
            st.session_state.pop("analytics_player_stats", None)
        if st.session_state.get("analytics_players_error"):
            st.warning(st.session_state["analytics_players_error"])
        players = st.session_state.get("analytics_players_found", [])
        if players:
            player_labels = {}
            for p in players:
                label = f'{p.get("strPlayer") or "Oyuncu"} · {p.get("strTeam") or "Takım bilinmiyor"} · ID {p.get("idPlayer") or "—"}'
                player_labels[label] = p
            selected_label = st.selectbox("Oyuncu seç", list(player_labels.keys()), key="analytics_selected_player")
            player = player_labels[selected_label]
            st.write(f'**Oyuncu:** {player.get("strPlayer", "—")}')
            st.write(f'**Takım:** {player.get("strTeam", "—")} · **Uyruk:** {player.get("strNationality", "—")} · **Pozisyon:** {player.get("strPosition", "—")}')
            if player.get("strDescriptionEN"):
                with st.expander("Oyuncu profili"):
                    st.write(player.get("strDescriptionEN"))
            player_id = player.get("idPlayer")
            if player_id and st.button("Mevcut oyuncu istatistiklerini sorgula", key="analytics_player_stats_button"):
                with st.spinner("TheSportsDB istatistik uç noktası sorgulanıyor..."):
                    stats_payload, stats_err = thesportsdb_player_stats(str(player_id))
                st.session_state["analytics_player_stats"] = stats_payload
                st.session_state["analytics_player_stats_error"] = stats_err
            if st.session_state.get("analytics_player_stats_error"):
                st.info(st.session_state["analytics_player_stats_error"])
            elif st.session_state.get("analytics_player_stats") is not None:
                payload = st.session_state["analytics_player_stats"]
                # Preserve provider fields rather than guessing a season-stat schema.
                if isinstance(payload, list) and payload:
                    st.dataframe(payload, use_container_width=True, hide_index=True)
                elif isinstance(payload, dict) and payload:
                    data = payload.get("playerstats") or payload.get("stats") or payload.get("statistics") or payload.get("players")
                    if isinstance(data, list) and data:
                        st.dataframe(data, use_container_width=True, hide_index=True)
                    elif isinstance(data, dict) and data:
                        st.json(data)
                    else:
                        st.json(payload)
                else:
                    st.info("TheSportsDB bu oyuncu için istatistik kaydı döndürmedi. Maç, dakika, gol veya asist değeri uydurulmadı.")
        elif "analytics_players_found" in st.session_state and not st.session_state.get("analytics_players_error"):
            st.info("Oyuncu bulunamadı. İsmi farklı yazmayı deneyebilirsin.")
    st.caption("Bu ekran otomatik bahis tahmini üretmez. API-Football v3 ve FootyStats anahtarı kullanılmaz; kaynak veri döndürmezse sonuç açıkça belirtilir.")

with info_tab:
    st.subheader("Program hakkında")
    st.markdown("""
- Canlı maçlar ve tarih seçimine göre fikstür.
- Sağlayıcının sunduğu istatistiklerin Türkçe gösterimi.
- Mevcutsa kadro ve bahis oranları.
- Oranın ham olasılığı: 100 / oran. Bu, gerçek kazanma olasılığı değildir ve şirket marjını içerebilir.
- **Maçı analiz et** düğmesi mevcut istatistikleri ve oranları bir araya getirir; ayrıca kalibre edilmemiş deneysel kısa-vade gol/korner olasılığı gösterir.
- API çağrıları uç noktaya göre önbelleğe alınır; Kaynak durumu sekmesi sağlayıcıların son yanıt durumunu gösterir.
- İstatistik/kadro butonları API'nin veri döndürdüğü maçlarda sonuç gösterir; kapsama girmeyen maçlarda uygulama veri üretemez.
- Veri eksikse sistem bunu açıkça söyler; veri uydurmaz.
- Bu sürüm otomatik bahis yapmaz. Doğrulanmış tahmin modeli, açılış oranı geçmişi ve tüm liglerde son dakika hareketleri henüz mevcut değildir.
- Ek kaynaklar: football-data.org, OpenLigaDB, ESPN ve isteğe bağlı Bzzoiro Sports Data (BSD_API_TOKEN). Bu kaynaklar tarih fikstürünü genişletir; küresel canlı istatistik veya bahis oranı sağlamaz.
- Sportmonks ücretsiz planı sınırlı lig kapsamındadır; API-Football ücretsiz paketi günlük 100 istekle sınırlıdır. Kaynakları birleştirmek bu limitleri kaldırmaz. Sportmonks canlı oran erişimi ücretsiz planda açık olmayabilir. Haber özeti, herkese açık RSS başlıklarını anahtar-sözcüklerle sınıflandırır; tüm interneti veya sosyal medyayı kapsamaz. API anahtarlarını kodun içine yazmayın; Secrets bölümünde saklayın.
""")
