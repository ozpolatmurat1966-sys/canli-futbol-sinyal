# Futbol Analiz Merkezi — başlangıç sürümü

## İçerik
- Birden fazla kaynaktan canlı maç takibi ve tekrarları ayıklama
- İsteğe bağlı 30 saniyelik otomatik canlı yenileme
- ESPN'in kapsadığı liglerde son 5 tamamlanmış maçtan takım formu
- TheSportsDB yanıt verirse oyuncu profili ve sağlayıcının döndürdüğü istatistik alanları
- Sağlayıcı verisi varsa maç istatistikleri, kadro ve oranları gösterme
- Hosting Secrets üzerinden uygulama şifresi
- Manuel analiz kontrol listesi

## Ücretsiz veri sınırları
Askıya alınan API-Football v3 ve hata veren FootyStats entegrasyonları kaldırıldı. Takım formu ESPN'in herkese açık skor panosuna dayanır ve seçilen lig/tarih kapsamıyla sınırlıdır. TheSportsDB ücretsiz arama/istatistik uç noktaları da sınırlı kapsam sunabilir. Veri sağlayıcıları bütün dünya liglerini, tüm bahis pazarlarını veya kesintisiz canlı veriyi garanti etmez. Veri yoksa uygulama istatistik uydurmaz.

## Güvenlik
Hosting platformunun Secrets bölümüne istersen `APP_PASSWORD` (size özel güçlü bir şifre) ve kullandığın diğer sağlayıcıların ilgili anahtarlarını ekle. API-Football v3 ve FootyStats anahtarları artık gerekli değildir. `APIFOOTBALL_API_KEY` ayrı bir sağlayıcı olan APIFootball.com'a aittir. Anahtarları bu depoya veya kod dosyalarına yazmayın. Şifre ayarlanmadan uygulamayı yayımlamayın. Bu giriş kontrolü temel korumadır; hosting sağlayıcısına mutlak gizlilik garantisi vermez.

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
