import sys
import os

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from anlikhaber.scripts.rss_reader import RSS_FEEDS, haberleri_cek

def belirli_kaynaktan_haber_cek(kaynak, limit=5):
    """Belirli bir kaynaktan belirli sayıda haber çeker"""
    print(f"{kaynak} kaynağından {limit} haber alınıyor...")
    
    # RSS_FEEDS içinde kaynak var mı kontrol et
    if kaynak not in RSS_FEEDS:
        print(f"Hata: {kaynak} geçerli bir kaynak değil.")
        return 0
    
    # Haberleri çek
    eklenen_haber_sayisi = haberleri_cek(kaynak=kaynak, limit=limit)
    print(f"{kaynak} kaynağından {eklenen_haber_sayisi} haber alındı.")
    return eklenen_haber_sayisi

app = create_app()
with app.app_context():
    belirli_kaynaktan_haber_cek('Milliyet', 5)
    belirli_kaynaktan_haber_cek('Sabah', 5)
    belirli_kaynaktan_haber_cek('NTV', 5)
    belirli_kaynaktan_haber_cek('HaberTürk', 5)
    belirli_kaynaktan_haber_cek('Hürriyet', 5)
    
    print("Her kaynaktan 5'er haber başarıyla alındı.") 