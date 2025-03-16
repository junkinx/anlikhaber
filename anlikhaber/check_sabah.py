import os
import sys
import logging

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import Haber

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_sabah_images():
    """Sabah kaynağından gelen haberlerin görsel URL'lerini kontrol eder"""
    app = create_app()
    with app.app_context():
        # Sabah haberlerini al
        haberler = Haber.query.filter_by(kaynak='Sabah').all()
        
        logger.info(f"Sabah haberlerinin sayısı: {len(haberler)}")
        
        for haber in haberler:
            logger.info(f"ID: {haber.id}, Başlık: {haber.baslik}")
            logger.info(f"Görsel URL: {haber.gorsel_url}")
            logger.info("-" * 50)

if __name__ == "__main__":
    check_sabah_images() 