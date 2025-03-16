import os
import sys
import logging
import time
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
from dotenv import load_dotenv
import random

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Haber, Ayarlar

# .env dosyasını yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'instagram_poster.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Instagram bilgilerini al
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

# Instagram oturum dosyası
SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_session.json')

# Hashtag listesi
DEFAULT_HASHTAGS = [
    "#sondakika", "#haber", "#gündem", "#türkiye", "#haberler", 
    "#güncel", "#son", "#dakika", "#güncelhaberler", "#haberinolsun"
]

def instagram_client_olustur():
    """Instagram istemcisi oluşturur ve oturum açar"""
    try:
        # Klasörün var olduğundan emin ol
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        
        # Instagram istemcisi oluştur
        cl = Client()
        
        # Daha önce kaydedilmiş oturum var mı kontrol et
        if os.path.exists(SESSION_FILE):
            try:
                # Oturumu yükle
                cl.load_settings(SESSION_FILE)
                
                # Oturumun geçerli olup olmadığını kontrol et
                cl.get_timeline_feed()
                logger.info("Instagram oturumu başarıyla yüklendi.")
                return cl
            
            except (LoginRequired, ClientError) as e:
                logger.warning(f"Kaydedilmiş oturum geçersiz, yeniden giriş yapılıyor: {str(e)}")
        
        # Kullanıcı adı ve şifre kontrolü
        if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
            logger.error("INSTAGRAM_USERNAME veya INSTAGRAM_PASSWORD bulunamadı. .env dosyasını kontrol edin.")
            return None
        
        # Giriş yap
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        
        # Oturumu kaydet
        cl.dump_settings(SESSION_FILE)
        
        logger.info("Instagram'a başarıyla giriş yapıldı.")
        return cl
    
    except Exception as e:
        logger.error(f"Instagram istemcisi oluşturulurken hata oluştu: {str(e)}")
        return None

def hashtag_olustur(baslik, kaynak, ekstra_hashtags=None):
    """Haber başlığına ve kaynağına göre hashtag oluşturur"""
    hashtags = DEFAULT_HASHTAGS.copy()
    
    # Kaynak hashtag'i ekle
    if kaynak:
        kaynak_hashtag = f"#{kaynak.lower().replace(' ', '').replace('ı', 'i')}"
        hashtags.append(kaynak_hashtag)
    
    # Ekstra hashtag'leri ekle
    if ekstra_hashtags:
        hashtags.extend(ekstra_hashtags)
    
    # Başlıktan anahtar kelimeleri çıkar
    anahtar_kelimeler = [kelime.lower() for kelime in baslik.split() if len(kelime) > 4]
    
    # En fazla 5 anahtar kelime seç
    secilen_kelimeler = random.sample(anahtar_kelimeler, min(5, len(anahtar_kelimeler)))
    
    # Anahtar kelimeleri hashtag'e dönüştür
    for kelime in secilen_kelimeler:
        # Türkçe karakterleri değiştir
        kelime = kelime.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        
        # Özel karakterleri temizle
        kelime = ''.join(c for c in kelime if c.isalnum())
        
        if kelime and len(kelime) > 2:
            hashtags.append(f"#{kelime}")
    
    # Hashtag'leri karıştır ve en fazla 15 tanesini seç
    random.shuffle(hashtags)
    secilen_hashtags = hashtags[:15]
    
    return ' '.join(secilen_hashtags)

def haber_paylasim_metni_olustur(haber):
    """Haber için Instagram paylaşım metnini oluşturur"""
    try:
        # Başlık
        metin = f"📰 {haber.baslik}\n\n"
        
        # Özet
        if haber.ozet:
            metin += f"{haber.ozet}\n\n"
        
        # Kaynak
        metin += f"📌 Kaynak: {haber.kaynak}\n\n"
        
        # Hashtag'ler
        metin += hashtag_olustur(haber.baslik, haber.kaynak)
        
        return metin
    
    except Exception as e:
        logger.error(f"Paylaşım metni oluşturulurken hata oluştu: {str(e)}")
        return f"📰 {haber.baslik}\n\n📌 Kaynak: {haber.kaynak}\n\n#sondakika #haber"

def haber_paylas(haber_id):
    """Belirli bir haberi Instagram'da paylaşır"""
    try:
        # Haberi al
        haber = Haber.query.get(haber_id)
        
        if not haber:
            logger.error(f"Haber bulunamadı: ID {haber_id}")
            return False
        
        # İşlenmiş görsel var mı kontrol et
        if not haber.islenmis_gorsel_path or not os.path.exists(haber.islenmis_gorsel_path):
            logger.error(f"İşlenmiş görsel bulunamadı: {haber.islenmis_gorsel_path}")
            return False
        
        # Instagram istemcisi oluştur
        cl = instagram_client_olustur()
        
        if not cl:
            logger.error("Instagram istemcisi oluşturulamadı.")
            return False
        
        # Paylaşım metnini oluştur
        paylasim_metni = haber_paylasim_metni_olustur(haber)
        
        # Görseli paylaş
        try:
            logger.info(f"Haber Instagram'da paylaşılıyor: {haber.baslik}")
            
            # Görseli paylaş
            media = cl.photo_upload(
                haber.islenmis_gorsel_path,
                caption=paylasim_metni
            )
            
            # Paylaşım bilgilerini güncelle
            haber.instagram_post_id = media.id
            haber.paylasildi = True
            haber.paylasilma_zamani = datetime.now()
            db.session.commit()
            
            logger.info(f"Haber başarıyla paylaşıldı: {haber.baslik}")
            
            # Paylaşımdan sonra biraz bekle (Instagram rate limit'lerini aşmamak için)
            time.sleep(5)
            
            return True
        
        except Exception as e:
            logger.error(f"Haber paylaşılırken hata oluştu: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Haber paylaşılırken genel hata oluştu: {str(e)}")
        db.session.rollback()
        return False

def paylasilmamis_haberleri_paylas(max_paylasim=1):
    """Veritabanındaki paylaşılmamış haberleri Instagram'da paylaşır"""
    try:
        # Paylaşılmamış ve paylaşıma hazır haberleri al
        paylasilmamis_haberler = Haber.query.filter_by(paylasildi=False, paylasima_hazir=True).filter(
            Haber.islenmis_gorsel_path.isnot(None),
            Haber.ozet.isnot(None)
        ).order_by(Haber.olusturulma_zamani.desc()).limit(max_paylasim).all()
        
        if not paylasilmamis_haberler:
            logger.info("Paylaşılacak haber bulunamadı.")
            return 0
        
        paylasilan_haber_sayisi = 0
        
        # Instagram istemcisi oluştur
        cl = instagram_client_olustur()
        
        if not cl:
            logger.error("Instagram istemcisi oluşturulamadı.")
            return 0
        
        for haber in paylasilmamis_haberler:
            try:
                # İşlenmiş görsel var mı kontrol et
                if not haber.islenmis_gorsel_path or not os.path.exists(haber.islenmis_gorsel_path):
                    logger.warning(f"İşlenmiş görsel bulunamadı: {haber.islenmis_gorsel_path}")
                    continue
                
                # Paylaşım metnini oluştur
                paylasim_metni = haber_paylasim_metni_olustur(haber)
                
                # Görseli paylaş
                logger.info(f"Haber Instagram'da paylaşılıyor: {haber.baslik}")
                
                media = cl.photo_upload(
                    haber.islenmis_gorsel_path,
                    caption=paylasim_metni
                )
                
                # Paylaşım bilgilerini güncelle
                haber.instagram_post_id = media.id
                haber.paylasildi = True
                haber.paylasilma_zamani = datetime.now()
                db.session.commit()
                
                logger.info(f"Haber başarıyla paylaşıldı: {haber.baslik}")
                
                paylasilan_haber_sayisi += 1
                
                # Paylaşımlar arasında bekle (Instagram rate limit'lerini aşmamak için)
                if paylasilan_haber_sayisi < len(paylasilmamis_haberler):
                    time.sleep(60)  # 1 dakika bekle
            
            except Exception as e:
                logger.error(f"Haber paylaşılırken hata oluştu (ID: {haber.id}): {str(e)}")
                db.session.rollback()
        
        return paylasilan_haber_sayisi
    
    except Exception as e:
        logger.error(f"Haberler paylaşılırken genel hata oluştu: {str(e)}")
        return 0

def son_paylasimi_sil():
    """Son paylaşılan haberi Instagram'dan siler"""
    try:
        # Son paylaşılan haberi al
        son_paylasilan_haber = Haber.query.filter_by(paylasildi=True).order_by(Haber.paylasilma_zamani.desc()).first()
        
        if not son_paylasilan_haber or not son_paylasilan_haber.instagram_post_id:
            logger.warning("Silinecek paylaşım bulunamadı.")
            return False
        
        # Instagram istemcisi oluştur
        cl = instagram_client_olustur()
        
        if not cl:
            logger.error("Instagram istemcisi oluşturulamadı.")
            return False
        
        # Paylaşımı sil
        try:
            logger.info(f"Instagram paylaşımı siliniyor: {son_paylasilan_haber.baslik}")
            
            cl.media_delete(son_paylasilan_haber.instagram_post_id)
            
            # Paylaşım bilgilerini güncelle
            son_paylasilan_haber.paylasildi = False
            son_paylasilan_haber.instagram_post_id = None
            son_paylasilan_haber.paylasilma_zamani = None
            db.session.commit()
            
            logger.info(f"Instagram paylaşımı başarıyla silindi: {son_paylasilan_haber.baslik}")
            
            return True
        
        except Exception as e:
            logger.error(f"Instagram paylaşımı silinirken hata oluştu: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Son paylaşım silinirken genel hata oluştu: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        paylasilan_haber_sayisi = paylasilmamis_haberleri_paylas(max_paylasim=1)
        print(f"Toplam {paylasilan_haber_sayisi} haber Instagram'da paylaşıldı.") 