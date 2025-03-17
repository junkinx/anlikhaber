import os
import sys

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from scripts.image_processor import haber_gorselini_isle

def main():
    # Uygulama bağlamını oluştur
    app = create_app()
    
    with app.app_context():
        # 77 numaralı haberin görselini yeniden işle
        print("77 numaralı haberin görseli yeniden işleniyor...")
        result = haber_gorselini_isle(77, force_reprocess=True)
        print(f"İşleme sonucu: {result}")

if __name__ == "__main__":
    main() 