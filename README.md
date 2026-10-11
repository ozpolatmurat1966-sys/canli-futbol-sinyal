# Futbol Analiz Merkezi — başlangıç sürümü

## İçerik
- Birden fazla kaynaktan canlı maç takibi ve tekrarları ayıklama
- İsteğe bağlı 30 saniyelik otomatik canlı yenileme
- FootyStats hesabında erişime açık lig verisi varsa takımın son 5 tamamlanmış maç formu
- TheSportsDB yanıt verirse oyuncu profili ve sağlayıcının döndürdüğü istatistik alanları
- Sağlayıcı verisi varsa maç istatistikleri, kadro ve oranları gösterme
- Hosting Secrets üzerinden uygulama şifresi
- Manuel analiz kontrol listesi

## Ücretsiz veri sınırları
API-Football v3'e bağımlılık kaldırıldı; askıya alınmış API anahtarı kullanılmaz. FootyStats takım formu için gerçek ve erişimi açık bir hesap anahtarı gerekir. TheSportsDB ücretsiz arama/istatistik uç noktaları sınırlı kapsam sunabilir. Veri sağlayıcıları bütün dünya liglerini, tüm bahis pazarlarını veya kesintisiz canlı veriyi garanti etmez. Veri yoksa uygulama istatistik uydurmaz.

## Güvenlik
Hosting platformunun Secrets bölümüne istersen `APP_PASSWORD` (size özel güçlü bir şifre), takım formu için gerçek `FOOTYSTATS_API_KEY` ve diğer sağlayıcıları kullanıyorsan kendi ilgili anahtarlarını ekle. Askıya alınan API-Football v3 için `API_FOOTBALL_KEY` artık gerekli değildir. `APIFOOTBALL_API_KEY` ayrı bir sağlayıcı olan APIFootball.com'a aittir. Anahtarları bu depoya veya kod dosyalarına yazmayın. Şifre ayarlanmadan uygulamayı yayımlamayın. Bu giriş kontrolü temel korumadır; hosting sağlayıcısına mutlak gizlilik garantisi vermez.

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
