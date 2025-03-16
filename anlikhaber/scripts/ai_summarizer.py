import os
import sys
import logging
from openai import OpenAI
from dotenv import load_dotenv

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
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'ai_summarizer.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# OpenAI API anahtarını al
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY bulunamadı. .env dosyasını kontrol edin.")
    sys.exit(1)

# OpenAI istemcisini oluştur
client = OpenAI(api_key=OPENAI_API_KEY)

def haber_ozetle(haber_metni, baslik=None, max_tokens=250):
    """
    OpenAI API kullanarak haber metnini özetler
    
    Args:
        haber_metni (str): Özetlenecek haber metni
        baslik (str, optional): Haber başlığı
        max_tokens (int, optional): Maksimum token sayısı
        
    Returns:
        str: Özetlenmiş haber metni
    """
    try:
        # Metni kısalt (API token limitlerini aşmamak için)
        if len(haber_metni) > 15000:
            haber_metni = haber_metni[:15000] + "..."
        
        # Prompt oluştur
        prompt = f"Aşağıdaki haberi 3-4 cümle ile özetle. Özet akıcı ve anlaşılır olmalı.\n\n"
        
        if baslik:
            prompt += f"Başlık: {baslik}\n\n"
            
        prompt += f"Haber: {haber_metni}\n\nÖzet:"
        
        # API isteği gönder
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen profesyonel bir haber editörüsün. Haberleri kısa, öz ve nesnel bir şekilde özetliyorsun."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.5
        )
        
        # Yanıtı al
        ozet = response.choices[0].message.content.strip()
        
        return ozet
    
    except Exception as e:
        logger.error(f"Haber özetlenirken hata oluştu: {str(e)}")
        return "Özet oluşturulamadı."

def ozetsiz_haberleri_ozetle():
    """Veritabanındaki özeti olmayan haberleri özetler"""
    try:
        # Özeti olmayan haberleri al
        ozetsiz_haberler = Haber.query.filter(Haber.ozet.is_(None)).all()
        
        if not ozetsiz_haberler:
            logger.info("Özetlenecek haber bulunamadı.")
            return 0
        
        ozetlenen_haber_sayisi = 0
        
        for haber in ozetsiz_haberler:
            try:
                logger.info(f"Haber özetleniyor: {haber.baslik}")
                
                # Haberi özetle
                ozet = haber_ozetle(haber.icerik, haber.baslik)
                
                # Özeti kaydet
                haber.ozet = ozet
                db.session.commit()
                
                ozetlenen_haber_sayisi += 1
                logger.info(f"Haber özetlendi: {haber.baslik}")
                
            except Exception as e:
                logger.error(f"Haber özetlenirken hata oluştu (ID: {haber.id}): {str(e)}")
                db.session.rollback()
        
        return ozetlenen_haber_sayisi
    
    except Exception as e:
        logger.error(f"Haberler özetlenirken genel hata oluştu: {str(e)}")
        return 0

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        ozetlenen_haber_sayisi = ozetsiz_haberleri_ozetle()
        print(f"Toplam {ozetlenen_haber_sayisi} haber özetlendi.") 