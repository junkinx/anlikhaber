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

def check_haberturk_images():
    """HaberTürk kaynağından gelen haberlerin görsel URL'lerini kontrol eder"""
    app = create_app()
    with app.app_context():
        # HaberTürk haberlerini al
        haberler = Haber.query.filter_by(kaynak='HaberTürk').all()
        
        logger.info(f"HaberTürk haberlerinin sayısı: {len(haberler)}")
        
        for haber in haberler:
            logger.info(f"ID: {haber.id}, Başlık: {haber.baslik}")
            logger.info(f"Görsel URL: {haber.gorsel_url}")
            logger.info("-" * 50)

if __name__ == "__main__":
    check_haberturk_images() 