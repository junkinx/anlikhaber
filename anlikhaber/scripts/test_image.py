import os
import sys
import logging

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.image_processor import haber_gorselini_isle

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        # 265 numaralı haberin görselini işle
        sonuc = haber_gorselini_isle(265, force_reprocess=True)
        print(f"İşleme sonucu: {sonuc}") 