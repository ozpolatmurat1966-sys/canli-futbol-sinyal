# Futbol Analiz Merkezi — başlangıç sürümü

## İçerik
- Birden fazla kaynaktan canlı maç takibi ve tekrarları ayıklama
- İsteğe bağlı 30 saniyelik otomatik canlı yenileme
- ESPN'in kapsadığı liglerde son 5 tamamlanmış maçtan takım formu
- TheSportsDB yanıt verirse oyuncu profili ve sağlayıcının döndürdüğü istatistik alanları
- Sağlayıcı verisi varsa maç istatistikleri, kadro ve oranları gösterme
- Hosting Secrets üzerinden uygulama şifresi
- Manuel analiz kontrol listesi
- 📡 Kaydedilmiş gözlemler üzerinden son 5/10/15 dakikalık skor/korner trendleri
- Aynı pazar/şirket için kaydedilmiş oran hareketleri ve lig/kaynak kapsamı tablosu
- İsteğe bağlı Telegram sinyal bildirimi
- `signal_engine.py` için birim testleri ve GitHub Actions Python sözdizimi/test kontrolü

## Ücretsiz veri sınırları
Askıya alınan API-Football v3 ve hata veren FootyStats entegrasyonları kaldırıldı. Takım formu ESPN'in herkese açık skor panosuna dayanır ve seçilen lig/tarih kapsamıyla sınırlıdır. TheSportsDB ücretsiz arama/istatistik uç noktaları da sınırlı kapsam sunabilir. Veri sağlayıcıları bütün dünya liglerini, tüm bahis pazarlarını veya kesintisiz canlı veriyi garanti etmez. Veri yoksa uygulama istatistik uydurmaz.

## Veri kaynakları ve atıf
- İsteğe bağlı `FIVE_DOLLAR_FOOTBALL_API_KEY` anahtarı, 5DollarFootballAPI üzerinden ücretsiz plandaki ilk 5 lig için canlı maç istatistikleri ve Bet365 maç oranlarını sorgulamak üzere kullanılabilir. Ücretsiz planın kapsamı ve istek limiti sağlayıcıya bağlıdır; kadro/oyuncu maç istatistiği bu entegrasyonla garanti edilmez.
- Bu veri kullanıldığında uygulamada görünür atıf gösterilir: [Football data by 5DollarFootballAPI](https://5dollarfootballapi.com).

## Güvenlik
Hosting platformunun Secrets bölümüne istersen `APP_PASSWORD` (size özel güçlü bir şifre) ve kullandığın diğer sağlayıcıların ilgili anahtarlarını ekle. API-Football v3 ve FootyStats anahtarları artık gerekli değildir. `APIFOOTBALL_API_KEY` ayrı bir sağlayıcı olan APIFootball.com'a aittir. Anahtarları bu depoya veya kod dosyalarına yazmayın. Şifre ayarlanmadan uygulamayı yayımlamayın. Bu giriş kontrolü temel korumadır; hosting sağlayıcısına mutlak gizlilik garantisi vermez.

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```


## Yeni canlı sinyal özellikleri
- **Trendler:** Son 5/10/15 dakika kıyaslaması yalnızca uygulamanın daha önce kaydettiği zaman damgalı skor/korner kayıtlarıyla hesaplanır. Yeterli kayıt yoksa satır gösterilmez.
- **Oran hareketi:** Aynı maç/pazar/seçenek/şirket için farklı zamanlarda en az iki gözlem kaydedilmesi gerekir. Oranları maç ekranından tekrar yüklemek yeni gözlem oluşturabilir.
- **Telegram:** Streamlit Secrets içine `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` eklenirse Canlı sinyaller sekmesindeki buton seçilen gözlenen sinyalleri gönderir. Bu, arka planda sürekli çalışan bir bildirim servisi değildir; kullanıcı butona basar.
- **Kalıcı geçmiş:** `FOOTBALL_HISTORY_DB_PATH` değişkenini hosting sağlayıcısındaki kalıcı disk üzerinde yazılabilir bir dosya yoluna ayarla. Geçici dosya sistemi sıfırlanırsa varsayılan SQLite geçmişi kaybolabilir.
- **Otomatik testler:** GitHub Actions, `tests/test_signal_engine.py` testlerini ve Python derleme kontrolünü çalıştırır.

## Bilinen sınırlar
- Streamlit oturumu dışında bağımsız arka plan toplayıcısı henüz yoktur. Otomatik yenileme için uygulama sekmesinin açık olması ve canlı yenilemenin etkinleştirilmesi gerekir.
- Lig/kaynak kapsam tablosu uygulamanın gözlemlediği ligleri listeler; bütün dünyadaki liglerin tarandığı anlamına gelmez.
- Oyuncu bahis pazarları yalnızca veri sağlayıcısı oran döndürürse gösterilebilir; oyuncu prop piyasalarının eksiksiz kapsaması garanti edilmez.
- Deneysel 10 dakikalık sinyaller kalibre edilmiş tahmin modeli değildir. Geçmiş performans metrikleri yalnızca sonuçla eşleştirilebilen kayıtlar için hesaplanır.
