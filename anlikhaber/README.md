# Anlık Haber Instagram Otomasyonu

Bu proje, çeşitli haber kaynaklarından en güncel haberleri otomatik olarak çeken, özetleyen, görselleştiren ve Instagram'da paylaşan bir otomasyon sistemidir.

## Özellikler

- **Haber Kaynakları**: Anadolu Ajansı, TRT Haber, DHA ve Sözcü gibi kaynaklardan RSS feed'leri aracılığıyla haberleri çeker.
- **Yapay Zeka ile Özetleme**: OpenAI API kullanarak haberleri kısa ve öz bir şekilde özetler.
- **Görsel Bulma**: Haber başlığına en uygun görseli bulur veya Pexels API'den temin eder.
- **Görsel İşleme**: Habere uygun görseli işler, overlay ekler ve metin yerleştirir.
- **Instagram Paylaşımı**: Hazırlanan görseli ve özeti Instagram'da otomatik olarak paylaşır.
- **Web Arayüzü**: Tüm bu işlemleri yönetebileceğiniz kullanıcı dostu bir web arayüzü sunar.
- **Otomatik Çalışma**: Belirli aralıklarla haberleri kontrol eder ve işler.

## Kurulum

### Gereksinimler

- Python 3.8 veya üzeri
- Pip paket yöneticisi
- SQLite veritabanı
- OpenAI API anahtarı
- Pexels API anahtarı
- Instagram hesabı

### Adımlar

1. Projeyi klonlayın:
   ```
   git clone https://github.com/kullanici/anlikhaber.git
   cd anlikhaber
   ```

2. Gerekli paketleri yükleyin:
   ```
   pip install -r requirements.txt
   ```

3. `.env` dosyasını düzenleyin:
   ```
   # API Anahtarları
   OPENAI_API_KEY=your_openai_api_key_here
   PEXELS_API_KEY=your_pexels_api_key_here

   # Instagram Bilgileri
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password

   # Uygulama Ayarları
   CHECK_INTERVAL=600  # 10 dakika (saniye cinsinden)
   DEBUG=True
   ```

4. Uygulamayı başlatın:
   ```
   python app.py
   ```

5. Tarayıcınızda `http://localhost:5000` adresine gidin.

## Kullanım

### Web Arayüzü

Web arayüzü üzerinden şunları yapabilirsiniz:

- Haberleri manuel olarak çekme
- Haberleri özetleme
- Görselleri bulma ve işleme
- Instagram'da paylaşım yapma
- Otomatik çalışma zamanlamasını ayarlama
- Sistem ayarlarını yapılandırma

### Otomatik Çalışma

Otomatik çalışma için:

1. Web arayüzünde "Scheduler'ı Başlat" butonuna tıklayın.
2. Sistem, `.env` dosyasında belirtilen `CHECK_INTERVAL` süresine göre haberleri kontrol edecek ve işleyecektir.

## Klasör Yapısı

```
anlikhaber/
├── app.py                  # Ana Flask uygulaması
├── models.py               # Veritabanı modelleri
├── requirements.txt        # Gerekli paketler
├── .env                    # Çevre değişkenleri
├── scripts/                # İşlem scriptleri
│   ├── rss_reader.py       # Haber çekme
│   ├── ai_summarizer.py    # Haber özetleme
│   ├── image_finder.py     # Görsel bulma
│   ├── image_processor.py  # Görsel işleme
│   ├── instagram_poster.py # Instagram paylaşımı
│   └── scheduler.py        # Otomatik çalışma
├── static/                 # Statik dosyalar
│   ├── css/                # CSS dosyaları
│   ├── js/                 # JavaScript dosyaları
│   ├── images/             # Görsel dosyaları
│   └── fonts/              # Font dosyaları
├── templates/              # HTML şablonları
│   ├── base.html           # Ana şablon
│   ├── index.html          # Ana sayfa
│   ├── haberler.html       # Haberler sayfası
│   ├── haber_detay.html    # Haber detay sayfası
│   └── ayarlar.html        # Ayarlar sayfası
├── data/                   # Veritabanı ve oturum dosyaları
└── logs/                   # Log dosyaları
```

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.

## Katkıda Bulunma

Katkıda bulunmak için lütfen bir issue açın veya bir pull request gönderin.

## İletişim

Sorularınız veya önerileriniz için [email@example.com](mailto:email@example.com) adresine e-posta gönderebilirsiniz. 