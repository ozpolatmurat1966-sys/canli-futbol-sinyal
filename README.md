# Futbol Analiz Merkezi — başlangıç sürümü

## İçerik
- Canlı maç ve tarihe göre fikstür sorgulama
- Sağlayıcı verisi varsa maç istatistiklerini gösterme
- Hosting Secrets üzerinden uygulama şifresi
- Manuel analiz kontrol listesi

## Ücretsiz veri sınırları
API-Football ücretsiz katmanında kota ve kapsam sınırlamaları vardır. Bütün dünya ligleri, tüm bahis pazarları ve kesintisiz canlı veri ücretsiz olarak garanti edilemez. Ücretsiz kotayla sınırlı kalabiliriz; ücretli plana geçmek zorunlu değildir.

## Güvenlik
Hosting platformunun Secrets bölümüne `APP_PASSWORD` (size özel güçlü bir şifre) ve `API_FOOTBALL_KEY` (API-Football anahtarı) ekleyin. Anahtarları bu depoya veya kod dosyalarına yazmayın. Şifre ayarlanmadan uygulamayı yayımlamayın. Bu giriş kontrolü temel korumadır; hosting sağlayıcısına mutlak gizlilik garantisi vermez.

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
