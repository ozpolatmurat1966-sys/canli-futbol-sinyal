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
if APP_PASSWORD:
    if not st.session_state.get("authenticated", False):
        st.title("⚽ Futbol Analiz Merkezi")
        pw = st.text_input("Giriş şifresi", type="password")
        if st.button("Giriş yap"):
            if pw == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Şifre yanlış.")
        st.stop()
else:
    st.warning("APP_PASSWORD ayarlanmamış. Uygulamayı yayımlamadan önce hosting Secrets bölümüne özel bir şifre ekleyin.")

st.title("⚽ Futbol Analiz Merkezi")
st.write("Canlı maç ve fikstür incelemesi için başlangıç sürümü.")
st.warning("Tahminler garanti değildir. Veri eksik veya gecikmeli olabilir; bahis yapmamak da bir seçenektir.")

API_KEY = secret("API_FOOTBALL_KEY", "")
API_BASE = "https://v3.football.api-sports.io"

def api_get(endpoint, params):
    if not API_KEY:
        st.error("Canlı veri için ücretsiz API-Football hesabından API anahtarı alıp hosting Secrets bölümüne API_FOOTBALL_KEY olarak ekleyin. Anahtarı kod içine yazmayın.")
        return None
    try:
        response = requests.get(f"{API_BASE}/{endpoint}", headers={"x-apisports-key": API_KEY}, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            st.error(f"Veri sağlayıcı yanıtı: {payload['errors']}")
            return None
        return payload.get("response", [])
    except requests.RequestException as exc:
        st.error(f"Veri alınamadı: {exc}")
        return None

def show_matches(matches):
    if matches is None:
        return
    if not matches:
        st.info("Bu seçimde maç bulunamadı. Ücretsiz API kotası ve lig kapsamı sınırlı olabilir.")
        return
    for match in matches:
        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        league = match.get("league", {})
        status = fixture.get("status", {})
        home = teams.get("home", {}).get("name", "Ev sahibi")
        away = teams.get("away", {}).get("name", "Deplasman")
        hg, ag = goals.get("home"), goals.get("away")
        score = f"{hg if hg is not None else '-'} : {ag if ag is not None else '-'}"
        minute = status.get("elapsed")
        state = f"{minute}'" if minute is not None else status.get("long", "Bilinmiyor")
        with st.expander(f"{home}  {score}  {away} | {league.get('name', '')} | {state}"):
            st.write(f"**Başlama:** {fixture.get('date', 'Bilinmiyor')}")
            if st.button("Maç istatistiklerini getir", key=f"stats_{fixture.get('id')}"):
                stats = api_get("fixtures/statistics", {"fixture": fixture.get("id")})
                if stats:
                    for team_stats in stats:
                        st.subheader(team_stats.get("team", {}).get("name", "Takım"))
                        st.dataframe([{"İstatistik": row.get("type"), "Değer": row.get("value")} for row in team_stats.get("statistics", [])], use_container_width=True)
                else:
                    st.info("İstatistikler henüz sunulmuyor veya ücretsiz plan kapsamında değil.")

tab_live, tab_date, tab_check = st.tabs(["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "📊 Analiz kontrol listesi"])
with tab_live:
    st.subheader("Şu anda oynanan maçlar")
    if st.button("Canlı maçları yükle / yenile"):
        show_matches(api_get("fixtures", {"live": "all"}))
with tab_date:
    match_date = st.date_input("Maç tarihi", value=date.today())
    if st.button("Fikstürü getir"):
        show_matches(api_get("fixtures", {"date": match_date.isoformat()}))
with tab_check:
    st.subheader("Maç değerlendirme kontrol listesi")
    checklist = ["Son 5–10 maç ve ev/deplasman performansı incelendi.", "Sakatlıklar, cezalılar ve muhtemel kadrolar doğrulandı.", "Açılış ve güncel oran hareketi karşılaştırıldı.", "Veri kalitesi ve örneklem yeterli.", "Piyasa olasılığı ve bahis şirketi marjı dikkate alındı.", "Bahis yapmamak seçeneği de değerlendirildi."]
    for i, item in enumerate(checklist):
        st.checkbox(item, key=f"check_{i}")
    st.caption("Bu başlangıç sürümünde otomatik tahmin modeli, kapsamlı oran geçmişi ve tüm bahis pazarları henüz bulunmuyor.")
