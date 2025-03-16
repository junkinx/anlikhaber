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
    """Görsel URL'sinin geçerli olup olmadığını kontrol eder"""
    if not url:
        return False
    
    try:
        # URL'deki soru işareti ve parametreleri temizle
        temiz_url = url.split('?')[0] if '?' in url else url
        
        # Sabah gazetesi için özel işlem
        if 'iasbh.tmgrup.com.tr' in temiz_url:
            # URL'deki "u=" parametresini bul ve gerçek URL'yi çıkar
            if 'u=' in url:
                try:
                    gercek_url = url.split('u=')[1]
                    # Eğer URL'de başka parametreler varsa temizle
                    if '?' in gercek_url:
                        gercek_url = gercek_url.split('?')[0]
                    temiz_url = gercek_url
                except:
                    logger.warning(f"Sabah URL'si işlenirken hata oluştu: {url}")
        
        # URL formatını kontrol et
        parsed = urlparse(temiz_url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
        
        # Görsel uzantısını kontrol et
        if temiz_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            # Uzantı doğruysa, doğrudan geçerli kabul et
            return True
        
        try:
            # Uzantı yoksa, HEAD isteği ile MIME tipini kontrol et
            # Zaman aşımı süresini 15 saniyeye çıkaralım
            response = requests.head(url, timeout=15)
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/'):
                return True
        except requests.exceptions.Timeout:
            # Zaman aşımı durumunda, URL'nin görünümüne göre karar ver
            # Yaygın görsel sunucularını kontrol et
            if any(host in parsed.netloc.lower() for host in ['img', 'image', 'photo', 'pic', 'cdn', 'media', 'iasbh', 'isbh']):
                logger.warning(f"Zaman aşımı oluştu ancak URL görsel sunucusuna benziyor, geçerli kabul ediliyor: {url}")
                return True
            
            # URL'de görsel uzantısı benzeri bir yapı var mı kontrol et
            if re.search(r'\.(jpe?g|png|gif|webp)', parsed.path.lower()):
                logger.warning(f"Zaman aşımı oluştu ancak URL görsel uzantısı içeriyor, geçerli kabul ediliyor: {url}")
                return True
            
            # Yine de geçersiz kabul et
            return False
        
        return False
    
    except Exception as e:
        logger.error(f"Görsel URL'si kontrol edilirken hata oluştu: {url} - {str(e)}")
        
        # Hata durumunda, URL'nin görünümüne göre karar ver
        try:
            parsed = urlparse(url)
            # Yaygın görsel sunucularını kontrol et
            if any(host in parsed.netloc.lower() for host in ['img', 'image', 'photo', 'pic', 'cdn', 'media', 'iasbh', 'isbh']):
                logger.warning(f"Hata oluştu ancak URL görsel sunucusuna benziyor, geçerli kabul ediliyor: {url}")
                return True
            
            # URL'de görsel uzantısı benzeri bir yapı var mı kontrol et
            if re.search(r'\.(jpe?g|png|gif|webp)', parsed.path.lower()):
                logger.warning(f"Hata oluştu ancak URL görsel uzantısı içeriyor, geçerli kabul ediliyor: {url}")
                return True
        except:
            pass
        
        return False

def gorsel_indir(url, dosya_yolu):
    """Verilen URL'den görseli indirir ve belirtilen dosya yoluna kaydeder"""
    try:
        # Klasörün var olduğundan emin ol
        os.makedirs(os.path.dirname(dosya_yolu), exist_ok=True)
        
        # Görseli indir
        response = requests.get(url, stream=True, timeout=15)  # Zaman aşımını artırdık
        response.raise_for_status()
        
        # Dosyaya kaydet
        with open(dosya_yolu, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
        
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