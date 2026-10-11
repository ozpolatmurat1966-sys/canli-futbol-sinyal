import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="Futbol Analiz Merkezi", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

# --- Private app password ---
APP_PASSWORD = get_secret("APP_PASSWORD", "")
if APP_PASSWORD and not st.session_state.get("authenticated", False):
    st.title("⚽ Futbol Analiz Merkezi")
    st.caption("Özel kullanım")
    entered = st.text_input("Giriş şifresi", type="password")
    if st.button("Giriş yap"):
        if entered == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Şifre yanlış.")
    st.stop()

API_KEY = get_secret("API_FOOTBALL_KEY", "").strip()

st.title("⚽ Futbol Analiz Merkezi")
st.caption("Canlı maçlar • Fikstür • Maç istatistikleri • Kadro bilgileri")
st.warning("Veriler sağlayıcının kapsamına ve gecikmesine bağlıdır. Hiçbir tahmin veya bahis sonucu garanti değildir.")

if not API_KEY:
    st.error("API anahtarı bulunamadı.")
    st.markdown("Streamlit uygulama ayarları → **Secrets** bölümüne şu satırı ekleyin:")
    st.code('API_FOOTBALL_KEY = "API_ANAHTARINIZ"')
    st.stop()

def api_get(endpoint, params=None):
    """Return (response_list, error_text, api_payload_info)."""
    headers = {"x-apisports-key": API_KEY}
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            params=params or {},
            timeout=25,
        )
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.text[:500]}", None

        try:
            payload = response.json()
        except ValueError:
            return None, "API geçerli JSON yanıtı döndürmedi.", None

        errors = payload.get("errors")
        if errors:
            return None, f"API hata yanıtı: {errors}", payload

        data = payload.get("response")
        if data is None:
            return None, "API yanıtında 'response' alanı bulunamadı.", payload

        return data, None, payload
    except requests.Timeout:
        return None, "API isteği zaman aşımına uğradı. Biraz sonra tekrar deneyin.", None
    except requests.RequestException as exc:
        return None, f"Bağlantı hatası: {exc}", None

def render_api_meta(payload):
    if not isinstance(payload, dict):
        return
    meta = payload.get("paging")
    if meta:
        st.caption(f"Sayfalama bilgisi: {meta}")
    if payload.get("results") == 0:
        st.caption("Sağlayıcı bu istekte 0 kayıt döndürdü.")
    if payload.get("errors"):
        st.caption(f"Sağlayıcı hata ayrıntısı: {payload['errors']}")

def render_stats(fixture_id):
    with st.spinner("İstatistikler kontrol ediliyor..."):
        stats, err, payload = api_get("fixtures/statistics", {"fixture": fixture_id})

    if err:
        st.error("İstatistik isteği başarısız oldu.")
        st.code(err)
        render_api_meta(payload)
        return

    if not stats:
        st.info(
            "API bağlantısı çalıştı ancak bu maç için istatistik kaydı dönmedi. "
            "Bu, ücretsiz plan/kapsam kısıtı, ilgili ligde istatistik sağlanmaması "
            "veya verinin henüz yayımlanmaması nedeniyle olabilir. Kod hatası olduğunu tek başına göstermez."
        )
        st.caption(f"Kontrol edilen maç ID'si: {fixture_id}")
        if payload is not None:
            st.caption(f"API'nin bildirdiği kayıt sayısı: {payload.get('results', 'bilinmiyor')}")
        return

    for team_stats in stats:
        st.subheader(team_stats.get("team", {}).get("name", "Takım"))
        rows = [
            {"İstatistik": item.get("type", "—"), "Değer": item.get("value", "—")}
            for item in team_stats.get("statistics", [])
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("API bu takım için istatistik satırı döndürmedi.")

def render_lineups(fixture_id):
    with st.spinner("Kadro bilgileri kontrol ediliyor..."):
        lineups, err, payload = api_get("fixtures/lineups", {"fixture": fixture_id})

    if err:
        st.error("Kadro isteği başarısız oldu.")
        st.code(err)
        render_api_meta(payload)
        return

    if not lineups:
        st.info(
            "Bu maç için kadro bilgisi dönmedi. İlk 11'ler henüz açıklanmamış "
            "veya ilgili lig/maç için kadro verisi sağlanmıyor olabilir."
        )
        st.caption(f"Kontrol edilen maç ID'si: {fixture_id}")
        return

    for lineup in lineups:
        st.subheader(lineup.get("team", {}).get("name", "Takım"))
        st.write("Diziliş:", lineup.get("formation", "Bilinmiyor"))
        start_xi = lineup.get("startXI", [])
        if start_xi:
            st.write("**İlk 11:** " + ", ".join(
                player.get("player", {}).get("name", "Oyuncu") for player in start_xi
            ))
        else:
            st.info("İlk 11 listesi henüz bulunmuyor.")
        substitutes = lineup.get("substitutes", [])
        if substitutes:
            st.write("**Yedekler:** " + ", ".join(
                player.get("player", {}).get("name", "Oyuncu") for player in substitutes
            ))

def show_matches(matches, label, key_prefix):
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
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        status = fixture.get("status", {})
        elapsed = status.get("elapsed")
        status_short = status.get("short", "")
        status_text = f"{elapsed}'" if elapsed is not None else status.get("long", "Durum bilinmiyor")
        fixture_id = fixture.get("id")
        score_home = "—" if home_goals is None else home_goals
        score_away = "—" if away_goals is None else away_goals
        league_name = league.get("name", "Lig bilgisi yok")

        with st.expander(
            f"{home} {score_home} - {score_away} {away} | {league_name} | {status_text}"
        ):
            st.write(f"**Maç ID:** {fixture_id}")
            st.write(f"**Başlama:** {fixture.get('date', 'Bilinmiyor')}")
            st.write(f"**Durum:** {status.get('long', status_short or 'Bilinmiyor')}")
            st.write(f"**Lig/ülke:** {league_name} / {league.get('country', 'Bilinmiyor')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Maç istatistiklerini getir", key=f"{key_prefix}_stats_{fixture_id}"):
                    st.session_state[f"show_stats_{fixture_id}"] = True
            with col2:
                if st.button("Kadro bilgilerini getir", key=f"{key_prefix}_lineups_{fixture_id}"):
                    st.session_state[f"show_lineups_{fixture_id}"] = True

            if st.session_state.get(f"show_stats_{fixture_id}", False):
                render_stats(fixture_id)
            if st.session_state.get(f"show_lineups_{fixture_id}", False):
                render_lineups(fixture_id)

tab_live, tab_date, tab_health, tab_help = st.tabs([
    "🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "🧪 API kontrolü", "ℹ️ Bilgi"
])

with tab_live:
    st.subheader("Şu anda oynanan maçlar")
    if st.button("Canlı maçları yükle / yenile", key="load_live"):
        with st.spinner("Canlı maçlar yükleniyor..."):
            matches, err, payload = api_get("fixtures", {"live": "all"})
        if err:
            st.error("Canlı maçlar alınamadı.")
            st.code(err)
            render_api_meta(payload)
        else:
            st.session_state["live_matches"] = matches
            st.session_state["live_loaded"] = True

    if st.session_state.get("live_loaded"):
        show_matches(st.session_state.get("live_matches", []), "Canlı maçlar", "live")
    else:
        st.info("Canlı maçları görmek için yukarıdaki düğmeye basın.")

with tab_date:
    st.subheader("Tarihe göre fikstür")
    match_date = st.date_input("Maç tarihi", value=date.today())
    if st.button("Fikstürü getir", key="load_date"):
        with st.spinner("Fikstür yükleniyor..."):
            matches, err, payload = api_get("fixtures", {"date": match_date.isoformat()})
        if err:
            st.error("Fikstür alınamadı.")
            st.code(err)
            render_api_meta(payload)
        else:
            st.session_state["date_matches"] = matches
            st.session_state["date_matches_day"] = match_date.isoformat()
            st.session_state["date_loaded"] = True

    if st.session_state.get("date_loaded"):
        st.caption(f"Tarih: {st.session_state.get('date_matches_day', '')}")
        show_matches(st.session_state.get("date_matches", []), "Seçilen tarih", "date")

with tab_health:
    st.subheader("API bağlantısını ve ücretsiz erişimi kontrol et")
    st.write("Bu test yalnızca API anahtarının çalışıp çalışmadığını ve fikstür isteğinin yanıt verip vermediğini kontrol eder.")
    if st.button("API bağlantısını test et", key="test_api"):
        with st.spinner("API bağlantısı test ediliyor..."):
            result, err, payload = api_get("fixtures", {"date": date.today().isoformat()})
        if err:
            st.error("API kontrolü başarısız.")
            st.code(err)
            render_api_meta(payload)
        else:
            st.success("API anahtarıyla bağlantı kuruldu.")
            st.write(f"Bugün için dönen fikstür sayısı: {len(result)}")
            if payload:
                st.write("API kullanım bilgisi:")
                st.json(payload.get("get", ""))
                st.json(payload.get("parameters", {}))
                st.json(payload.get("errors", {}))
                st.json(payload.get("results", 0))
                st.json(payload.get("paging", {}))
                if payload.get("response"):
                    st.info("Fikstür verisi erişilebilir. İstatistik/kadro verisi her maç ve lig için ayrıca sağlanmayabilir.")

with tab_help:
    st.subheader("Kapsam ve sınırlamalar")
    st.markdown("""
- Canlı maç listesi ve tarih bazlı fikstür.
- API'nin gerçekten sağladığı maç istatistikleri ve kadro bilgileri.
- İstatistik/kadro isteğinde boş yanıt ile API/bağlantı hatasını ayrı gösterme.
- API anahtarı ve uygulama şifresi Streamlit Secrets üzerinden okunur.

**Ücretsiz planın sınırı:** Ücretsiz API erişimi bütün liglerde canlı istatistik, kadro, oyuncu verisi veya bahis oranı sağlamayı garanti etmez. Bazı maçlarda fikstür ve skor görünürken istatistik bulunmayabilir. Bu durumda uygulama olmayan veriyi uydurmaz.

Bu uygulama kesin tahmin veya kâr garantisi vermez.
""")
