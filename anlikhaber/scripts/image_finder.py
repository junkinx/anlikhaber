import os
import sys
import logging
import requests
from dotenv import load_dotenv
import json
import re
from urllib.parse import urlparse

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Haber

# .env dosyasını yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'image_finder.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Pexels API anahtarını al
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
if not PEXELS_API_KEY:
    logger.warning("PEXELS_API_KEY bulunamadı. .env dosyasını kontrol edin. Pexels API kullanılamayacak.")

def gorsel_url_gecerli_mi(url):
    """Görsel URL'sinin geçerli olup olmadığını kontrol eder."""
    if not url:
        return False
    
    # Bazı URL'ler geçersiz olabilir veya görsel içermeyebilir
    gecersiz_uzantilar = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']
    for uzanti in gecersiz_uzantilar:
        if url.lower().endswith(uzanti):
            return False
    
    # Habertürk küçük görselleri için özel işlem
    if 'im.haberturk.com' in url and '_htufak.jpg' in url:
        # Küçük görsel URL'sini büyük görsel URL'sine dönüştür
        url = url.replace('_htufak.jpg', '.jpg')
        logger.info(f"Habertürk küçük görsel büyük görsele dönüştürüldü: {url}")
    
    return True

def gorsel_indir(url, dosya_yolu):
    """Belirtilen URL'den görseli indirir ve belirtilen dosya yoluna kaydeder."""
    try:
        # Dosya yolunun dizininin var olduğundan emin ol
        os.makedirs(os.path.dirname(dosya_yolu), exist_ok=True)
        
        # Habertürk küçük görselleri için özel işlem
        if 'im.haberturk.com' in url and '_htufak.jpg' in url:
            # Küçük görsel URL'sini büyük görsel URL'sine dönüştür
            url = url.replace('_htufak.jpg', '.jpg')
            logger.info(f"Habertürk küçük görsel büyük görsele dönüştürüldü: {url}")
        
        # Görsel indirme işlemi
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        
        if response.status_code == 200:
            with open(dosya_yolu, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            logger.error(f"Görsel indirilirken hata oluştu: {url} - {response.status_code} {response.reason}")
            return False
    except Exception as e:
        logger.error(f"Görsel indirilirken hata oluştu: {url} - {str(e)}")
        return False

def pexels_gorsel_ara(arama_terimi, min_genislik=1350, min_yukseklik=1920):
    """Pexels API kullanarak görsel arar"""
    if not PEXELS_API_KEY:
        return None
    
    try:
        # Arama terimini temizle
        arama_terimi = re.sub(r'[^\w\s]', '', arama_terimi)
        arama_terimi = arama_terimi.strip()
        
        # API isteği gönder
        headers = {
            'Authorization': PEXELS_API_KEY
        }
        params = {
            'query': arama_terimi,
            'per_page': 10,
            'size': 'large'
        }
        
        response = requests.get('https://api.pexels.com/v1/search', headers=headers, params=params, timeout=15)  # Zaman aşımını artırdık
        response.raise_for_status()
        
        data = response.json()
        
        # Sonuçları kontrol et
        if 'photos' not in data or not data['photos']:
            return None
        
        # Uygun boyutta görsel ara
        for photo in data['photos']:
            if photo['width'] >= min_genislik and photo['height'] >= min_yukseklik:
                return photo['src']['original']
        
        # Uygun boyutta görsel bulunamazsa, en büyük görseli döndür
        return data['photos'][0]['src']['original']
    
    except Exception as e:
        logger.error(f"Pexels'ten görsel aranırken hata oluştu: {arama_terimi} - {str(e)}")
        return None

def gorselsiz_haberlere_gorsel_bul():
    """Veritabanındaki görseli olmayan haberlere görsel bulur"""
    try:
        # Görseli olmayan haberleri al
        gorselsiz_haberler = Haber.query.filter(
            (Haber.gorsel_url.is_(None)) | 
            (Haber.gorsel_url == '')
        ).all()
        
        if not gorselsiz_haberler:
            logger.info("Görsel eklenecek haber bulunamadı.")
            return 0
        
        eklenen_gorsel_sayisi = 0
        
        for haber in gorselsiz_haberler:
            try:
                logger.info(f"Haber için görsel aranıyor: {haber.baslik}")
                
                # Pexels'ten görsel ara
                gorsel_url = pexels_gorsel_ara(haber.baslik)
                
                if gorsel_url and gorsel_url_gecerli_mi(gorsel_url):
                    # Görseli kaydet
                    haber.gorsel_url = gorsel_url
                    db.session.commit()
                    
                    eklenen_gorsel_sayisi += 1
                    logger.info(f"Haber için görsel bulundu: {haber.baslik}")
                else:
                    logger.warning(f"Haber için uygun görsel bulunamadı: {haber.baslik}")
                
            except Exception as e:
                logger.error(f"Haber için görsel bulunurken hata oluştu (ID: {haber.id}): {str(e)}")
                db.session.rollback()
        
        return eklenen_gorsel_sayisi
    
    except Exception as e:
        logger.error(f"Haberlere görsel bulunurken genel hata oluştu: {str(e)}")
        return 0

def gorsel_url_kontrol_et(haber_id):
    """Belirli bir haberin görsel URL'sini kontrol eder ve geçerli değilse Pexels'ten yeni görsel bulur"""
    try:
        # Haberi al
        haber = Haber.query.get(haber_id)
        
        if not haber:
            logger.error(f"Haber bulunamadı: ID {haber_id}")
            return False
        
        # Görsel URL'sini kontrol et
        if not haber.gorsel_url or not gorsel_url_gecerli_mi(haber.gorsel_url):
            logger.info(f"Haber için geçerli görsel URL'si bulunamadı, yeni görsel aranıyor: {haber.baslik}")
            
            # Pexels'ten görsel ara
            gorsel_url = pexels_gorsel_ara(haber.baslik)
            
            if gorsel_url and gorsel_url_gecerli_mi(gorsel_url):
                # Görseli kaydet
                haber.gorsel_url = gorsel_url
                db.session.commit()
                
                logger.info(f"Haber için yeni görsel bulundu: {haber.baslik}")
                return True
            else:
                logger.warning(f"Haber için uygun görsel bulunamadı: {haber.baslik}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Haber görseli kontrol edilirken hata oluştu (ID: {haber_id}): {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        eklenen_gorsel_sayisi = gorselsiz_haberlere_gorsel_bul()
        print(f"Toplam {eklenen_gorsel_sayisi} habere görsel eklendi.") 