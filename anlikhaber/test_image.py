from app import create_app
from scripts.image_processor import haber_gorselini_isle

app = create_app()
with app.app_context():
    # 265 numaralı haberin görselini işleyelim
    result = haber_gorselini_isle(265, force_reprocess=True)
    print(f"İşleme sonucu: {result}") 