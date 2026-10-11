# Futbol Analiz Merkezi — başlangıç sürümü

## İçerik
- Birden fazla kaynaktan canlı maç takibi ve tekrarları ayıklama
- İsteğe bağlı 30 saniyelik otomatik canlı yenileme
- Takımların son 5 maç formu ve oyuncu sezon istatistikleri (API-Football v3 anahtarıyla)
- Sağlayıcı verisi varsa maç istatistikleri, kadro ve oranları gösterme
- Hosting Secrets üzerinden uygulama şifresi
- Manuel analiz kontrol listesi

## Ücretsiz veri sınırları
API-Football ücretsiz katmanında kota ve kapsam sınırlamaları vardır. Bütün dünya ligleri, tüm bahis pazarları ve kesintisiz canlı veri ücretsiz olarak garanti edilemez. Ücretsiz kotayla sınırlı kalabiliriz; ücretli plana geçmek zorunlu değildir.

## Güvenlik
Hosting platformunun Secrets bölümüne `APP_PASSWORD` (size özel güçlü bir şifre) ve `API_FOOTBALL_KEY` (API-Sports / API-Football v3 anahtarı; takım ve oyuncu analizi için) ekleyin. Bu anahtar `APIFOOTBALL_API_KEY` adlı ayrı sağlayıcı anahtarıyla karıştırılmamalıdır. Anahtarları bu depoya veya kod dosyalarına yazmayın. Şifre ayarlanmadan uygulamayı yayımlamayın. Bu giriş kontrolü temel korumadır; hosting sağlayıcısına mutlak gizlilik garantisi vermez.

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
