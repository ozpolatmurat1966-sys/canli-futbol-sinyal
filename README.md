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
- **Telegram:** Streamlit Secrets içindeki `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` ile Canlı sinyaller sekmesindeki manuel gönderim çalışır. Aynı iki değer GitHub Actions secrets içine eklenirse bağımsız collector gözlenen skor/korner değişimlerini otomatik bildirebilir.
- **Kalıcı geçmiş:** `FOOTBALL_HISTORY_DB_PATH` değişkenini hosting sağlayıcısındaki kalıcı disk üzerinde yazılabilir bir dosya yoluna ayarla. Geçici dosya sistemi sıfırlanırsa varsayılan SQLite geçmişi kaybolabilir.
- **Otomatik testler:** GitHub Actions, `tests/test_signal_engine.py` testlerini ve Python derleme kontrolünü çalıştırır.

## Bilinen sınırlar
- Streamlit oturumundan bağımsız `background_collector.py` ve 5 dakikalık GitHub Actions denemesi vardır. Bunun çalışması için `DATABASE_URL` ve `FIVE_DOLLAR_FOOTBALL_API_KEY` Actions secrets içinde tanımlı olmalı; GitHub zamanlanmış işleri gecikebilir.
- Lig/kaynak kapsam tablosu uygulamanın gözlemlediği ligleri listeler; bütün dünyadaki liglerin tarandığı anlamına gelmez.
- Oyuncu bahis pazarları yalnızca veri sağlayıcısı oran döndürürse gösterilebilir; oyuncu prop piyasalarının eksiksiz kapsaması garanti edilmez.
- Deneysel 10 dakikalık sinyaller kalibre edilmiş tahmin modeli değildir. Geçmiş performans metrikleri yalnızca sonuçla eşleştirilebilen kayıtlar için hesaplanır.


## Bağımsız veri toplama ve kalıcı veritabanı
Bu proje artık Streamlit oturumundan bağımsız bir toplayıcı içerir:
- `background_collector.py` sürekli worker olarak `python background_collector.py` ile çalıştırılabilir.
- `.github/workflows/football-collector.yml` GitHub Actions üzerinden yaklaşık 5 dakikada bir tek toplama turu çalıştırmayı dener. Zamanlanmış işler GitHub tarafından geciktirilebilir; gerçek zamanlılık garantisi değildir.
- Kalıcı ortak geçmiş için bir PostgreSQL veritabanı oluştur ve aynı `DATABASE_URL` bağlantı adresini Streamlit Secrets'e ve GitHub deposunun **Settings → Secrets and variables → Actions** bölümüne ekle.
- Aynı bölüme `FIVE_DOLLAR_FOOTBALL_API_KEY` secret'ını da ekle. Secret eklenmezse zamanlanmış collector güvenli biçimde veri toplama adımını atlar.
- Streamlit Secrets örneği: `DATABASE_URL = "postgresql://..."` ve `FIVE_DOLLAR_FOOTBALL_API_KEY = "..."`. Gerçek değerleri kaynak koda veya README'ye yazma.
- Toplayıcı ilk etapta 5DollarFootballAPI kaynağını kullanır. Kaynak anahtarı/ücretsiz plan kapsamı, API kotası ve oran endpoint'i izinleri hâlâ geçerlidir. Lig veya oyuncu pazarı kaynakta yoksa başka bir kaynaktan varmış gibi üretilmez.
- Zamanlanmış iş sınırlı sayıda canlı maça bakar; varsayılan iş akışı en fazla 8 maç işler, canlı maç + desteklenen istatistik/olayları tek toplu istekle alır ve oranları her altıncı turda sorgular. Kota/masrafı izleyerek bu değerleri değiştir.

## Tarihsel kalibrasyon
- Geçmişte sonucu değerlendirilebilen 10 dakikalık deneysel tahminler yeterli sayıya ulaştığında benzer geçmiş olasılıkların gerçekleşme oranından düzeltilmiş olasılık üretilebilir.
- En az 50 değerlendirilmiş örnek olmadan kalibre edilmiş yüzde gösterilmez.
- Geçmiş / performans sekmesi kronolojik eğitim/test ayrımıyla ham ve kalibre Brier skorlarını karşılaştırır. Bu ölçüm küçük/yanlı örneklemden etkilenebilir ve gelecekteki kârlılığı kanıtlamaz.
- Kalibrasyon şu anda yalnızca mevcut deneysel **sonraki 10 dakika gol/korner** tahminleri içindir; maç sonucu veya oyuncu prop pazarları için kalibre edilmiş model anlamına gelmez.

## Oyuncu bahis pazarları
- Uygulama ve bağımsız toplayıcı, sağlayıcı yanıtında açıkça bulunan oyuncu şut/gol/asist/kart gibi pazarları tanımaya çalışır ve varsa oran geçmişine kaydeder.
- Desteklenen pazar adları ve yanıt şemaları sağlayıcıya göre değişir. Oyuncu istatistiği bulunması, o oyuncu için bahis oranı bulunduğu anlamına gelmez.


## Gelişmiş özellikler (yeni)
- **Küresel lig envanteri:** Canlı sinyaller sekmesindeki tarama düğmesi sağlayıcının `/leagues` listesini sayfalı olarak alır ve kalıcı veritabanına kaydeder. Bu, hesabın erişebildiği lig envanteridir; bütün dünyada her veri türünün kapsandığı anlamına gelmez.
- **Oyna/Pas geç güvenlik kapısı:** Gerçek oran, güncel/tam veri, yeterli örnek ve doğrulanmış pazar olasılığı yoksa otomatik olarak **Pas geç** döndürür. Şimdiki deneysel 10 dakikalık tahminler genel bahis pazarları için model yerine kullanılmaz.
- **Sanal bahis performansı:** Sonuçlanmış sanal bahis kayıtları olduğunda ROI, net sonuç ve maksimum düşüş hesaplanır. Henüz kayıt yoksa ROI uydurulmaz.
- **Otomatik Telegram veri uyarıları:** Collector, skor veya korner değişimini algıladığında `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` ayarlıysa Telegram'a bir kez gönderir. Aynı olay tekrar gönderilmemesi için veritabanında tekilleştirilir.
- **Kota koruması:** Collector canlı maçları ve desteklenen istatistik/olayları tek toplu istekte alır; GET isteklerinde 429/5xx yanıtlarına sınırlı yeniden deneme ve Retry-After desteği uygular. Oran istekleri ayrı ve daha seyrek yapılır.
- **Pazar hazırlık tablosu:** 1X2, gol, korner, kart ve oyuncu pazarları için gözlenen oran verisi ile model doğrulama durumunu birbirinden ayırır.
- Kalıcı lig envanteri ve otomatik Telegram için PostgreSQL `DATABASE_URL` ile Actions secrets içinde `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` ayarla. Anahtarları kod deposuna yazma.


## Sistem hazırlık merkezi
- Canlı sinyaller sekmesinin alt bölümünde **12 başlık için sistem hazırlık merkezi** bulunur.
- **API bağlantılarını şimdi test et** düğmesi, ayarlı 5DollarFootballAPI anahtarıyla lig ve canlı fikstür uç noktalarını örnek isteklerle kontrol eder. Kontrol sonucu ve zamanı veritabanına kaydedilir.
- Veritabanı paneli gerçek maç, gözlem, oran, lig ve sanal bahis kayıtlarını sayar; aynı gün ve aynı takım eşleşmelerinde farklı skor kaydı bulunursa olası uyuşmazlıkları listeler.
- Hazırlık tablosu, var olan özellikleri, yalnızca kısmi desteği olan özellikleri ve harici veri/anahtar gerektiren işleri açıkça ayırır. Bir özelliğin listede görünmesi onun her kaynakta çalıştığını garanti etmez.


## Günlük fikstür toplama
Bağımsız toplayıcı canlı maçlara ek olarak yaklaşık saatte bir İstanbul takvim gününün fikstür listesini sorgular. Böylece maç öncesi kayıtlar ve sonuçlanmış maçlar için veri seti birikmesine yardımcı olur. Bu özellik yalnızca sağlayıcının API anahtarının erişebildiği ve yanıtında döndürdüğü kayıtları toplar; tüm tarihsel sezonları geriye dönük doldurmaz.


## Canlı baskı ve iPhone görünümü
- Canlı sinyaller ekranı kaydedilmiş şut, isabetli şut, korner ve tehlikeli atak istatistiklerinde zaman aralıklı artışları ağırlıklı bir **baskı göstergesi** olarak sunar. Bu değer gol olasılığı değildir; veri yoksa hesaplanmaz.
- Canlı sinyaller sekmesindeki **iPhone için kart görünümü** tablo yerine maç kartlarıyla trend ve baskı göstergelerini gösterir.
- Sanal bahis kayıt defteri, model olasılığı manuel olarak önceden biliniyorsa Brier skorunu da hesaplar; model olasılığı boşsa doldurulmuş gibi varsayılmaz.
- Veri kalite paneli eski canlı kayıtları, skoru eksik tamamlanmış maçları, geçersiz oranları ve tekrarlanan oran gruplarını gösterir.
- Bağımsız collector her başarılı/başarısız tur için PostgreSQL'de heartbeat kaydı tutar; panelde son durum gösterilir.
