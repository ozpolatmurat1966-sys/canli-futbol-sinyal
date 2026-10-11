import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="Futbol Analiz Merkezi", page_icon="⚽", layout="wide")

def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

APP_PASSWORD = secret("APP_PASSWORD", "")
if APP_PASSWORD and not st.session_state.get("authenticated", False):
    st.title("⚽ Futbol Analiz Merkezi")
    entered = st.text_input("Giriş şifresi", type="password")
    if st.button("Giriş yap"):
        if entered == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Şifre yanlış.")
    st.stop()

API_KEY = secret("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"

st.title("⚽ Futbol Analiz Merkezi")
st.caption("Canlı maçlar, fikstür ve mevcut maç istatistikleri")
st.warning("Tahminler garanti değildir. Veriler API planına göre eksik olabilir; bahis yapmamak da bir seçenektir.")

if not API_KEY:
    st.error("API anahtarı bulunamadı. Streamlit uygulama ayarları → Secrets bölümüne API_FOOTBALL_KEY ekleyin.")
    st.code('API_FOOTBALL_KEY = "API_ANAHTARINIZ"')
    st.stop()

def api_get(endpoint, params=None):
    headers = {"x-apisports-key": API_KEY}
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers, params=params or {}, timeout=20)
        if response.status_code != 200:
            return None, f"API HTTP hatası: {response.status_code} — {response.text[:300]}"
        payload = response.json()
        if payload.get("errors"):
            return None, f"API hata yanıtı: {payload['errors']}"
        return payload.get("response", []), None
    except requests.Timeout:
        return None, "API isteği zaman aşımına uğradı. Biraz sonra tekrar deneyin."
    except requests.RequestException as exc:
        return None, f"Bağlantı hatası: {exc}"
    except ValueError:
        return None, "API geçerli JSON yanıtı döndürmedi."

def show_matches(matches, label):
    if not matches:
        st.info(f"{label} için maç bulunamadı.")
        return
    st.caption(f"Bulunan maç sayısı: {len(matches)}")
    for match in matches:
        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        league = match.get("league", {})
        home = teams.get("home", {}).get("name", "Ev sahibi")
        away = teams.get("away", {}).get("name", "Deplasman")
        hg = goals.get("home")
        ag = goals.get("away")
        status = fixture.get("status", {})
        elapsed = status.get("elapsed")
        status_text = f"{elapsed}'" if elapsed is not None else status.get("long", "Başlamadı")
        score_home = "-" if hg is None else hg
        score_away = "-" if ag is None else ag
        fixture_id = fixture.get("id")
        with st.expander(f"{home} {score_home} - {score_away} {away} | {league.get('name', 'Lig')} | {status_text}"):
            st.write(f"**Başlama:** {fixture.get('date', 'Bilinmiyor')}")
            st.write(f"**Durum:** {status.get('long', 'Bilinmiyor')}")
            if st.button("Maç istatistiklerini getir", key=f"stats_{fixture_id}"):
                stats, err = api_get("fixtures/statistics", {"fixture": fixture_id})
                if err:
                    st.error(err)
                elif not stats:
                    st.info("İstatistik verisi dönmedi. Maç başlamamış olabilir veya API planınız bu veriyi kapsamıyor olabilir.")
                else:
                    for team_stats in stats:
                        st.subheader(team_stats.get("team", {}).get("name", "Takım"))
                        rows = [{"İstatistik": r.get("type", "—"), "Değer": r.get("value", "—")} for r in team_stats.get("statistics", [])]
                        if rows:
                            st.dataframe(rows, use_container_width=True, hide_index=True)
                        else:
                            st.info("Bu takım için istatistik satırı yok.")
            if st.button("Kadro bilgilerini getir", key=f"lineups_{fixture_id}"):
                lineups, err = api_get("fixtures/lineups", {"fixture": fixture_id})
                if err:
                    st.error(err)
                elif not lineups:
                    st.info("Kadro bulunamadı; maç başlamamış olabilir veya API planınızda olmayabilir.")
                else:
                    for lineup in lineups:
                        st.subheader(lineup.get("team", {}).get("name", "Takım"))
                        st.write("Diziliş:", lineup.get("formation", "Bilinmiyor"))
                        players = lineup.get("startXI", [])
                        if players:
                            st.write(", ".join(p.get("player", {}).get("name", "Oyuncu") for p in players))
                        else:
                            st.info("İlk 11 verisi bulunamadı.")

tab_live, tab_date, tab_help = st.tabs(["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "ℹ️ Bilgi"])

with tab_live:
    st.subheader("Şu anda oynanan maçlar")
    if st.button("Canlı maçları yükle / yenile", key="load_live"):
        with st.spinner("Canlı maçlar yükleniyor..."):
            matches, err = api_get("fixtures", {"live": "all"})
        if err:
            st.error(err)
        else:
            st.session_state["live_matches"] = matches
    if "live_matches" in st.session_state:
        show_matches(st.session_state["live_matches"], "Canlı maçlar")
    else:
        st.info("Canlı maçları görmek için yukarıdaki düğmeye basın.")

with tab_date:
    st.subheader("Tarihe göre fikstür")
    match_date = st.date_input("Maç tarihi", value=date.today())
    if st.button("Fikstürü getir", key="load_date"):
        with st.spinner("Fikstür yükleniyor..."):
            matches, err = api_get("fixtures", {"date": match_date.isoformat()})
        if err:
            st.error(err)
        else:
            st.session_state["date_matches"] = matches
            st.session_state["date_matches_day"] = match_date.isoformat()
    if "date_matches" in st.session_state:
        st.caption(f"Tarih: {st.session_state.get('date_matches_day', '')}")
        show_matches(st.session_state["date_matches"], "Seçilen tarih")

with tab_help:
    st.subheader("Bu sürümün kapsamı")
    st.markdown("""
- Canlı maçlar ve tarih bazlı fikstür
- API'nin sağladığı maç istatistikleri ve kadrolar
- Bağlantı, API yanıtı ve erişim planı sorunları için görünür hata mesajları
- API anahtarı ve uygulama şifresi Streamlit Secrets üzerinden okunur

**Önemli:** Ücretsiz API erişimi tüm ligleri, canlı istatistikleri, oyuncu verilerini veya bahis oranlarını garanti etmez. Bu sürüm kâr ya da tahmin garantisi vermez.
""")
