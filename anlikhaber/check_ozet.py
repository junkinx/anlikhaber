from app import create_app
from models import db, Haber

app = create_app()

with app.app_context():
    # Belirli haberleri kontrol et
    for haber_id in [245, 246, 247, 260, 261, 262, 263]:
        haber = Haber.query.get(haber_id)
        if haber:
            print(f"Haber ID: {haber.id}, Başlık: {haber.baslik}")
            print(f"Özet: {haber.ozet}")
            
            # Eğer özet yoksa, örnek bir özet ekle
            if not haber.ozet:
                print(f"Haber ID {haber.id} için özet ekleniyor...")
                haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
                db.session.commit()
                print(f"Özet eklendi: {haber.ozet}")
            print("-" * 50) 