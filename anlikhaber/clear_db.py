import os
import sys
import logging
from datetime import datetime, timedelta

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    from app import create_app
    from models import db, Haber
    from scripts.rss_reader import haberleri_cek
    
    app = create_app()
    with app.app_context():
        # Mevcut haber sayısını göster
        mevcut_haber_sayisi = Haber.query.count()
        logger.info(f"Mevcut haber sayısı: {mevcut_haber_sayisi}")
        
        # Tüm haberleri sil
        try:
            Haber.query.delete()
            db.session.commit()
            logger.info("Tüm haberler silindi.")
        except Exception as e:
            logger.error(f"Haberler silinirken hata oluştu: {str(e)}")
            db.session.rollback()
        
        # Yeni haberleri çek
        try:
            yeni_haber_sayisi = haberleri_cek()
            logger.info(f"Toplam {yeni_haber_sayisi} yeni haber eklendi.")
        except Exception as e:
            logger.error(f"Haberler çekilirken hata oluştu: {str(e)}")
        
        # Güncel haber sayısını göster
        guncel_haber_sayisi = Haber.query.count()
        logger.info(f"Güncel haber sayısı: {guncel_haber_sayisi}") 