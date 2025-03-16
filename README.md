# Anlık Haber

Anlık Haber, Türkçe haber kaynaklarından haberleri çeken, işleyen ve Instagram'da paylaşmaya hazır hale getiren bir Flask uygulamasıdır.

## Özellikler

- Çeşitli Türkçe haber kaynaklarından (Anadolu Ajansı, TRT Haber, Sözcü, Hürriyet, Milliyet, Sabah, NTV, HaberTürk) RSS beslemeleri aracılığıyla haberleri otomatik olarak çeker
- Haberleri veritabanında saklar
- Haberleri özetler (OpenAI API kullanarak)
- Haber görsellerini bulur ve işler (Instagram için 1080x1350 formatına uygun hale getirir)
- İşlenmiş haberleri Instagram'da paylaşmaya hazır hale getirir
- Kullanıcı dostu bir arayüz sunar

## Kurulum

### Gereksinimler

- Python 3.8+
- SQLite
- Pip

### Adımlar

1. Repoyu klonlayın:
   ```
   git clone https://github.com/junkinx/anlikhaber.git
   cd anlikhaber
   ```

2. Sanal ortam oluşturun ve etkinleştirin:
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # veya
   venv\Scripts\activate  # Windows
   ```

3. Gerekli paketleri yükleyin:
   ```
   pip install -r anlikhaber/requirements.txt
   ```

4. `.env.example` dosyasını `.env` olarak kopyalayın ve gerekli API anahtarlarını ekleyin:
   ```
   cp anlikhaber/.env.example anlikhaber/.env
   ```

5. Veritabanını oluşturun:
   ```
   cd anlikhaber
   python app.py
   ```

## Kullanım

1. Uygulamayı başlatın:
   ```
   cd anlikhaber
   python app.py
   ```

2. Tarayıcınızda `http://localhost:8080` adresine gidin

3. Ana sayfada son haberleri görebilirsiniz

4. `/haberler` sayfasında tüm haberleri listeleyebilirsiniz

5. Bir habere tıklayarak detaylarını görebilir ve aşağıdaki işlemleri yapabilirsiniz:
   - Haberi özetleme
   - Haber görseli bulma
   - Görseli işleme (Instagram formatına uygun hale getirme)
   - Haberi paylaşıma hazırlama
   - Instagram'da paylaşma

## Proje Yapısı

```
anlikhaber/
├── app.py                  # Ana uygulama dosyası
├── models.py               # Veritabanı modelleri
├── requirements.txt        # Gerekli paketler
├── .env                    # Ortam değişkenleri
├── scripts/                # Yardımcı scriptler
│   ├── ai_summarizer.py    # Haber özetleme
│   ├── image_finder.py     # Görsel bulma
│   ├── image_processor.py  # Görsel işleme
│   ├── instagram_poster.py # Instagram paylaşımı
│   ├── rss_reader.py       # RSS okuyucu
│   └── scheduler.py        # Zamanlanmış görevler
├── static/                 # Statik dosyalar
│   ├── css/                # CSS dosyaları
│   ├── js/                 # JavaScript dosyaları
│   ├── fonts/              # Fontlar
│   └── images/             # Görseller
│       ├── original/       # Orijinal görseller
│       └── processed/      # İşlenmiş görseller
└── templates/              # HTML şablonları
    ├── base.html           # Ana şablon
    ├── index.html          # Ana sayfa
    ├── haberler.html       # Haberler listesi
    ├── haber_detay.html    # Haber detayı
    └── ayarlar.html        # Ayarlar sayfası
```

## Özel Durumlar

### Sabah ve HaberTürk Görselleri

Sabah ve HaberTürk gibi bazı haber kaynaklarından gelen görsel URL'leri özel bir yapıya sahiptir. Bu URL'ler şu şekilde işlenir:

- Sabah: `https://iasbh.tmgrup.com.tr/[hash]/[boyutlar]?u=[gerçek_görsel_url]` formatındaki URL'lerden gerçek görsel URL'si çıkarılır.
- HaberTürk: URL'deki soru işareti ve parametreler temizlenir.

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın. 