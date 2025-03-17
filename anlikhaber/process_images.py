import sys
import os

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.image_processor import islenmemis_haberleri_isle
from app import create_app

app = create_app()
with app.app_context():
    print("İşlenmemiş haberler işleniyor...")
    islenen_gorsel_sayisi = islenmemis_haberleri_isle()
    print(f"Toplam {islenen_gorsel_sayisi} haber görseli işlendi.") 