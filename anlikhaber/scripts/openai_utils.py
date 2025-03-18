import os
import sys
import logging
import openai
from dotenv import load_dotenv

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env dosyasını yükle
load_dotenv()

# OpenAI API anahtarını ayarla
openai.api_key = os.getenv("OPENAI_API_KEY")

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def haber_ozetle(haber_metni, haber_basligi, max_length=250):
    """
    OpenAI API'sini kullanarak haber metnini özetler
    
    Args:
        haber_metni (str): Özetlenecek haber içeriği
        haber_basligi (str): Haber başlığı
        max_length (int): Maksimum özet uzunluğu (karakter sayısı)
        
    Returns:
        str: Özetlenmiş haber metni
    """
    try:
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OpenAI API anahtarı bulunamadı. Lütfen .env dosyasına OPENAI_API_KEY ekleyin.")
            return None
            
        logger.info(f"'{haber_basligi}' başlıklı haber OpenAI ile özetleniyor...")
        
        # Metin çok uzunsa kısalt
        if len(haber_metni) > 4000:
            haber_metni = haber_metni[:4000]
        
        # OpenAI ile özet oluştur
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen bir haber editörüsün. Haberleri kısa, öz ve etkileyici şekilde özetliyorsun. Özet Instagram'da paylaşılacak ve görselin üzerine yazılacak."},
                {"role": "user", "content": f"Şu haberi Instagram paylaşımı için 250 karakterden kısa, çarpıcı ve ilgi çekici şekilde özetle. Başlık: {haber_basligi}\n\nİçerik: {haber_metni}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Özeti al
        ozet = response.choices[0].message.content.strip()
        
        # Özeti maksimum uzunluğa kısalt
        if len(ozet) > max_length:
            # Son cümleyi tamamlayarak kısalt
            son_nokta = ozet[:max_length].rfind('.')
            if son_nokta != -1:
                ozet = ozet[:son_nokta+1]
            else:
                ozet = ozet[:max_length]
        
        logger.info(f"Haber başarıyla özetlendi: {ozet[:50]}...")
        return ozet
        
    except Exception as e:
        logger.error(f"Haber özetleme hatası: {str(e)}")
        return None
        
def hashtag_olustur(haber_metni, haber_basligi, adet=5):
    """
    OpenAI API'sini kullanarak haber için hashtag'ler oluşturur
    
    Args:
        haber_metni (str): Haber içeriği
        haber_basligi (str): Haber başlığı
        adet (int): Oluşturulacak hashtag sayısı
        
    Returns:
        str: Hashtag'ler (örn: #haber #gündem #politika)
    """
    try:
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OpenAI API anahtarı bulunamadı. Lütfen .env dosyasına OPENAI_API_KEY ekleyin.")
            return os.getenv("DEFAULT_HASHTAGS", "#haber #gündem #sondakika")
            
        logger.info(f"'{haber_basligi}' başlıklı haber için hashtag'ler oluşturuluyor...")
        
        # Metin çok uzunsa kısalt
        if len(haber_metni) > 1000:
            haber_metni = haber_metni[:1000]
        
        # OpenAI ile hashtag oluştur
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen bir sosyal medya uzmanısın. Haberler için etkili hashtag'ler oluşturuyorsun."},
                {"role": "user", "content": f"Şu haber için {adet} adet Türkçe hashtag oluştur. Başlık: {haber_basligi}\n\nİçerik: {haber_metni}\n\nHashtag'leri sadece '#' işaretiyle başlayacak şekilde boşluklarla ayrılmış halde listele, başka açıklama ekleme."}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        # Hashtag'leri al
        hashtags = response.choices[0].message.content.strip()
        
        logger.info(f"Hashtag'ler başarıyla oluşturuldu: {hashtags}")
        return hashtags
        
    except Exception as e:
        logger.error(f"Hashtag oluşturma hatası: {str(e)}")
        return os.getenv("DEFAULT_HASHTAGS", "#haber #gündem #sondakika") 