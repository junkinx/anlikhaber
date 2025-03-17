from app import create_app
from scripts.image_processor import haber_gorselini_isle

app = create_app()
with app.app_context():
    result = haber_gorselini_isle(71)
    print(f"İşleme sonucu: {result}") 