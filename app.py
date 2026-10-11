
import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="Futbol Analiz Merkezi", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"

STAT_TR = {
    "Shots on Goal": "İsabetli Şut",
    "Shots off Goal": "İsabetsiz Şut",
    "Total Shots": "Toplam Şut",
    "Blocked Shots": "Engellenen Şut",
    "Shots insidebox": "Ceza Sahası İçinden Şut",
    "Shots inside box": "Ceza Sahası İçinden Şut",
    "Shots outsidebox": "Ceza Sahası Dışından Şut",
    "Shots outside box": "Ceza Sahası Dışından Şut",
    "Fouls": "Faul",
    "Corner Kicks": "Korner",
    "Offsides": "Ofsayt",
    "Ball Possession": "Topla Oynama",
    "Yellow Cards": "Sarı Kart",
    "Red Cards": "Kırmızı Kart",
    "Goalkeeper Saves": "Kaleci Kurtarışı",
    "Total passes": "Toplam Pas",
    "Passes accurate": "İsabetli Pas",
    "Passes %": "Pas İsabeti",
    "Expected Goals": "Beklenen Gol (xG)",
    "expected_goals": "Beklenen Gol (xG)",
    "Throw-ins": "Taç",
    "Tackles": "Müdahale",
    "Interceptions": "Araya Girme",
    "Hit Woodwork": "Direkten Dönen Şut",
}

STATUS_TR = {
    "First Half": "İlk Yarı",
    "Halftime": "Devre Arası",
    "Second Half": "İkinci Yarı",
    "Match Finished": "Maç Bitti",
    "Not Started": "Başlamadı",
    "Extra Time": "Uzatmalar",
    "Penalty": "Penaltılar",
    "Postponed": "Ertelendi",
    "Cancelled": "İptal",
    "Match Suspended": "Durduruldu",
    "Live": "Canlı",
}


def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


APP_PASSWORD = secret("APP_PASSWORD", "").strip()

if APP_PASSWORD and not st.session_state.get("authenticated", False):
    st.title("⚽ Futbol Analiz Merkezi")
    password = st.text_input("Uygulama şifresi", type="password")

    if st.button("Giriş yap"):
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Şifre yanlış.")

    st.stop()


API_KEY = secret("API_FOOTBALL_KEY", "").strip()

st.title("⚽ Futbol Analiz Merkezi")
st.caption(
    "Canlı maçlar • Fikstür • İstatistik • Oran karşılaştırma • Analiz"
)
st.warning(
    "Tahminler garanti değildir. Veriler eksik veya gecikmeli olabilir. "
    "Veri yetersizse bahis yapmamak da bir seçenektir."
)

if not API_KEY:
    st.error("API anahtarı bulunamadı.")
    st.code(
        'API_FOOTBALL_KEY = "API_ANAHTARINIZ"\n'
        'APP_PASSWORD = "KENDI_SIFRENIZ"'
    )
    st.stop()


def api_get(endpoint, params=None):
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={"x-apisports-key": API_KEY},
            params=params or {},
            timeout=20,
        )

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}", None

        payload = response.json()

        if payload.get("errors"):
            return None, f"API hatası: {payload['errors']}", payload

        return payload.get("response", []), None, payload

    except requests.Timeout:
        return None, "İstek zaman aşımına uğradı.", None
    except (requests.RequestException, ValueError) as error:
        return None, f"Bağlantı hatası: {error}", None


def number(value):
    if value is None:
        return None

    try:
        return float(str(value).replace("%", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def find_stat(rows, names):
    for row in rows:
        if row.get("type") in names:
            return number(row.get("value"))
    return None


def render_stats(fixture_id):
    stats, error, _ = api_get(
        "fixtures/statistics",
        {"fixture": fixture_id},
    )

    if error:
        st.error(f"İstatistik isteği başarısız: {error}")
        return

    if not stats:
        st.info(
            "Bu maç için istatistik bulunamadı. "
            "Lig kapsamı veya ücretsiz plan sınırı etkili olabilir."
        )
        return

    for team in stats:
        st.subheader(team.get("team", {}).get("name", "Takım"))

        rows = [
            {
                "İstatistik": STAT_TR.get(
                    item.get("type", ""),
                    item.get("type", "Bilinmiyor"),
                ),
                "Değer": (
                    item.get("value")
                    if item.get("value") is not None
                    else "—"
                ),
            }
            for item in team.get("statistics", [])
        ]

        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
            )

    if len(stats) < 2:
        return

    home_rows = stats[0].get("statistics", [])
    away_rows = stats[1].get("statistics", [])

    home_name = stats[0].get("team", {}).get("name", "Ev sahibi")
    away_name = stats[1].get("team", {}).get("name", "Deplasman")

    home_on = find_stat(home_rows, ["Shots on Goal"])
    away_on = find_stat(away_rows, ["Shots on Goal"])
    home_shots = find_stat(home_rows, ["Total Shots"])
    away_shots = find_stat(away_rows, ["Total Shots"])
    home_corners = find_stat(home_rows, ["Corner Kicks"])
    away_corners = find_stat(away_rows, ["Corner Kicks"])
    home_poss = find_stat(home_rows, ["Ball Possession"])
    away_poss = find_stat(away_rows, ["Ball Possession"])

    st.subheader("İstatistiklere göre ön değerlendirme")
    st.caption(
        "Bunlar basit göstergelerdir; geçmiş verilerle doğrulanmış "
        "bir tahmin modeli değildir."
    )

    signals = []

    if None not in (home_on, away_on, home_shots, away_shots):
        if home_on + away_on >= 5 and home_shots + away_shots >= 14:
            signals.append(
                "Şut hacmi yüksek. Bu durum tek başına gol garantisi değildir."
            )

        if abs(home_on - away_on) >= 3:
            superior = home_name if home_on > away_on else away_name
            signals.append(f"İsabetli şut üstünlüğü: {superior}.")

    if None not in (home_corners, away_corners):
        if home_corners + away_corners >= 7:
            signals.append(
                "Toplam korner sayısı yüksek. Kalan süreyi ve maç akışını kontrol edin."
            )

    if None not in (home_poss, away_poss):
        if abs(home_poss - away_poss) >= 20:
            superior = home_name if home_poss > away_poss else away_name
            signals.append(
                f"Topla oynama üstünlüğü: {superior}. "
                "Bu tek başına galibiyet olasılığı değildir."
            )

    if signals:
        for signal in signals:
            st.write("• " + signal)
    else:
        st.info(
            "Yeterli gösterge yok. Bu verilerle tahmin üretmek yerine "
            "pas geçmek daha doğru olabilir."
        )


def render_lineups(fixture_id):
    lineups, error, _ = api_get(
        "fixtures/lineups",
        {"fixture": fixture_id},
    )

    if error:
        st.error(f"Kadro isteği başarısız: {error}")
        return

    if not lineups:
        st.info(
            "Kadro bilgisi henüz açıklanmamış veya "
            "bu maç için sağlanmıyor olabilir."
        )
        return

    for team in lineups:
        st.subheader(team.get("team", {}).get("name", "Takım"))
        st.write("Diziliş:", team.get("formation") or "Bilinmiyor")

        starters = [
            p.get("player", {}).get("name", "Oyuncu")
            for p in team.get("startXI", [])
        ]
        substitutes = [
            p.get("player", {}).get("name", "Oyuncu")
            for p in team.get("substitutes", [])
        ]

        if starters:
            st.write("**İlk 11:** " + ", ".join(starters))

        if substitutes:
            st.write("**Yedekler:** " + ", ".join(substitutes))


def render_odds(fixture_id):
    odds, error, _ = api_get(
        "odds",
        {"fixture": fixture_id},
    )

    if error:
        st.error(f"Oran isteği başarısız: {error}")
        return

    if not odds:
        st.info(
            "Bu maç için oran verisi bulunamadı. "
            "Ücretsiz plan tüm maç ve bahis pazarlarını kapsamayabilir."
        )
        return

    for item in odds:
        for bookmaker in item.get("bookmakers", []):
            st.markdown(
                f"**Oran sağlayıcısı: {bookmaker.get('name', 'Bilinmiyor')}**"
            )

            for bet in bookmaker.get("bets", []):
                rows = []

                for option in bet.get("values", []):
                    odd = number(option.get("odd"))

                    implied_probability = (
                        f"{100 / odd:.1f}%"
                        if odd is not None and odd > 0
                        else "—"
                    )

                    rows.append(
                        {
                            "Pazar": bet.get("name", "Pazar"),
                            "Seçenek": option.get("value", "—"),
                            "Oran": option.get("odd", "—"),
                            "Oranın ima ettiği olasılık": implied_probability,
                        }
                    )

                if rows:
                    with st.expander(bet.get("name", "Bahis pazarı")):
                        st.dataframe(
                            rows,
                            use_container_width=True,
                            hide_index=True,
                        )


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
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        elapsed = status.get("elapsed")

        match_state = (
            f"{elapsed}'"
            if elapsed is not None
            else STATUS_TR.get(
                status.get("long", ""),
                status.get("long", "Durum bilinmiyor"),
            )
        )

        fixture_id = fixture.get("id")

        with st.expander(
            f"{home} {home_goals if home_goals is not None else '—'} - "
            f"{away_goals if away_goals is not None else '—'} {away} | "
            f"{league.get('name', 'Lig bilinmiyor')} | {match_state}"
        ):
            st.write(f"**Maç ID:** {fixture_id}")
            st.write(
                "**Lig/ülke:** "
                f"{league.get('name', '—')} / {league.get('country', '—')}"
            )
            st.write(f"**Başlama:** {fixture.get('date', 'Bilinmiyor')}")
            st.write(
                "**Durum:** "
                + STATUS_TR.get(
                    status.get("long", ""),
                    status.get("long", status.get("short", "Bilinmiyor")),
                )
            )

            col1, col2, col3 = st.columns(3)

            if col1.button(
                "İstatistikleri getir",
                key=f"{prefix}_stats_{fixture_id}",
            ):
                st.session_state[f"stats_{fixture_id}"] = True

            if col2.button(
                "Kadroyu getir",
                key=f"{prefix}_lineup_{fixture_id}",
            ):
                st.session_state[f"lineup_{fixture_id}"] = True

            if col3.button(
                "Bahis oranlarını getir",
                key=f"{prefix}_odds_{fixture_id}",
            ):
                st.session_state[f"odds_{fixture_id}"] = True

            if st.session_state.get(f"stats_{fixture_id}"):
                render_stats(fixture_id)

            if st.session_state.get(f"lineup_{fixture_id}"):
                render_lineups(fixture_id)

            if st.session_state.get(f"odds_{fixture_id}"):
                render_odds(fixture_id)


live_tab, date_tab, info_tab = st.tabs(
    ["🔴 Canlı maçlar", "📅 Tarihe göre maçlar", "ℹ️ Bilgi"]
)

with live_tab:
    st.subheader("Şu anda oynanan maçlar")

    if st.button("Canlı maçları yükle / yenile"):
        with st.spinner("Canlı maçlar yükleniyor..."):
            data, error, _ = api_get("fixtures", {"live": "all"})

        if error:
            st.error(error)
        else:
            st.session_state["live_matches"] = data

    if "live_matches" in st.session_state:
        show_matches(st.session_state["live_matches"], "live")
    else:
        st.info("Canlı maçları görmek için yukarıdaki düğmeye basın.")

with date_tab:
    st.subheader("Tarihe göre fikstür")
    selected_date = st.date_input("Maç tarihi", value=date.today())

    if st.button("Fikstürü getir"):
        with st.spinner("Fikstür yükleniyor..."):
            data, error, _ = api_get(
                "fixtures",
                {"date": selected_date.isoformat()},
            )

        if error:
            st.error(error)
        else:
            st.session_state["date_matches"] = data
            st.session_state["date_label"] = selected_date.isoformat()

    if "date_matches" in st.session_state:
        st.caption("Seçilen tarih: " + st.session_state.get("date_label", ""))
        show_matches(st.session_state["date_matches"], "date")

with info_tab:
    st.subheader("Program hakkında")

    st.markdown("""
- Canlı maçlar ve tarihe göre fikstür.
- Sağlayıcının sunduğu istatistiklerin Türkçe gösterimi.
- Mevcutsa kadro bilgileri ve bahis oranları.
- Oranların ima ettiği olasılık hesabı: **100 / oran**.
- Basit, açıklanabilir istatistik göstergeleri.
- Eksik veride uyarı; veri uydurma yok.

**Önemli:** Oranın ima ettiği olasılık, gerçek kazanma olasılığı değildir.
Bahis şirketi marjını içerebilir. Bu uygulamada henüz doğrulanmış bir
tahmin modeli veya otomatik bahis oynama özelliği bulunmamaktadır.

Ücretsiz API planı tüm ligleri, canlı istatistikleri, oyuncu verilerini
ve bahis pazarlarını garanti etmez. API anahtarınızı kodun içine yazmayın;
Streamlit Secrets bölümünde saklayın.
""")
