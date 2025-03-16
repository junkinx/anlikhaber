import os
import sys
import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env dosyasını yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Kontrol aralığını al (saniye cinsinden)
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 600))  # Varsayılan: 10 dakika

def otomatik_paylasim_aktif_mi():
    """Otomatik paylaşımın aktif olup olmadığını kontrol eder"""
    try:
        from models import Ayarlar
        
        ayar = Ayarlar.query.filter_by(anahtar='otomatik_paylasim_aktif').first()
        
        if ayar and ayar.deger.lower() in ['true', 'evet', '1', 'on']:
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Otomatik paylaşım durumu kontrol edilirken hata oluştu: {str(e)}")
        return False

def haber_islem_pipeline():
    """Haber işleme pipeline'ını çalıştırır"""
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # 1. Haberleri çek
            from scripts.rss_reader import haberleri_cek
            yeni_haber_sayisi = haberleri_cek()
            logger.info(f"Toplam {yeni_haber_sayisi} yeni haber eklendi.")
            
            if yeni_haber_sayisi > 0:
                # 2. Haberleri özetle
                from scripts.ai_summarizer import ozetsiz_haberleri_ozetle
                ozetlenen_haber_sayisi = ozetsiz_haberleri_ozetle()
                logger.info(f"Toplam {ozetlenen_haber_sayisi} haber özetlendi.")
                
                # 3. Görselleri bul
                from scripts.image_finder import gorselsiz_haberlere_gorsel_bul
                eklenen_gorsel_sayisi = gorselsiz_haberlere_gorsel_bul()
                logger.info(f"Toplam {eklenen_gorsel_sayisi} habere görsel eklendi.")
                
                # 4. Görselleri işle
                from scripts.image_processor import islenmemis_haberleri_isle
                islenen_gorsel_sayisi = islenmemis_haberleri_isle()
                logger.info(f"Toplam {islenen_gorsel_sayisi} haber görseli işlendi.")
                
                # İşlenen haberleri paylaşıma hazır olarak işaretle
                from models import db, Haber
                islenmis_haberler = Haber.query.filter(
                    Haber.islenmis_gorsel_path.isnot(None),
                    Haber.ozet.isnot(None),
                    Haber.paylasildi == False,
                    Haber.paylasima_hazir == False
                ).all()
                
                for haber in islenmis_haberler:
                    haber.paylasima_hazir = True
                    logger.info(f"Haber paylaşıma hazır olarak işaretlendi: {haber.baslik}")
                
                db.session.commit()
                
                # 5. Otomatik paylaşım aktifse Instagram'da paylaş
                if otomatik_paylasim_aktif_mi():
                    from scripts.instagram_poster import paylasilmamis_haberleri_paylas
                    paylasilan_haber_sayisi = paylasilmamis_haberleri_paylas(max_paylasim=1)
                    logger.info(f"Toplam {paylasilan_haber_sayisi} haber Instagram'da paylaşıldı.")
                else:
                    logger.info("Otomatik paylaşım devre dışı, haberler paylaşılmadı.")
            
            else:
                logger.info("Yeni haber bulunamadı, işlem yapılmadı.")
    
    except Exception as e:
        logger.error(f"Haber işleme pipeline'ı çalıştırılırken hata oluştu: {str(e)}")

def scheduler_baslat():
    """Scheduler'ı başlatır"""
    try:
        # Scheduler oluştur
        scheduler = BackgroundScheduler()
        
        # Haber işleme görevini ekle
        scheduler.add_job(
            haber_islem_pipeline,
            IntervalTrigger(seconds=CHECK_INTERVAL),
            id='haber_islem_pipeline',
            name='Haber İşleme Pipeline',
            replace_existing=True
        )
        
        # Scheduler'ı başlat
        scheduler.start()
        logger.info(f"Scheduler başlatıldı. Kontrol aralığı: {CHECK_INTERVAL} saniye.")
        
        return scheduler
    
    except Exception as e:
        logger.error(f"Scheduler başlatılırken hata oluştu: {str(e)}")
        return None

if __name__ == "__main__":
    # İlk çalıştırmada hemen işlem yap
    logger.info("İlk haber işleme pipeline'ı çalıştırılıyor...")
    haber_islem_pipeline()
    
    # Scheduler'ı başlat
    scheduler = scheduler_baslat()
    
    if scheduler:
        try:
            # Ana thread'i canlı tut
            while True:
                time.sleep(1)
        
        except (KeyboardInterrupt, SystemExit):
            # Scheduler'ı durdur
            scheduler.shutdown()
            logger.info("Scheduler durduruldu.")
    
    else:
        logger.error("Scheduler başlatılamadı.") 