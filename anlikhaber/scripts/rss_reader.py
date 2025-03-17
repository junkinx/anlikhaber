import feedparser
import requests
from bs4 import BeautifulSoup
import logging
import os
import sys
from datetime import datetime
import time
import re
import urllib.parse

# cgi modülü yerine urllib.parse kullanmak için feedparser'ı patch edelim
import feedparser.util
feedparser.util.urllib = urllib

# Feedparser'ın cgi modülünü kullanmasını engellemek için
# parse_header fonksiyonunu monkeypatch edelim
def parse_header(line):
    """Parse a Content-type like header.
    
    Return the main content-type and a dictionary of parameters.
    """
    parts = line.split(';')
    key = parts[0].strip()
    params = {}
    for part in parts[1:]:
        if '=' not in part:
            continue
        name, value = part.strip().split('=', 1)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        params[name.strip().lower()] = value.strip()
    return key, params

# Feedparser'ın parse_header fonksiyonunu monkeypatch et
try:
    import feedparser.encodings
    feedparser.encodings.parse_header = parse_header
except:
    pass

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Haber

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'rss_reader.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# RSS kaynakları
RSS_FEEDS = {
    'Anadolu Ajansı': 'https://www.aa.com.tr/tr/rss/default?cat=guncel',
    'TRT Haber': 'https://www.trthaber.com/sondakika.rss',
    'Sözcü': 'https://www.sozcu.com.tr/rss/gundem.xml',
    'Hürriyet': 'https://www.hurriyet.com.tr/rss/anasayfa',
    'Milliyet': 'https://www.milliyet.com.tr/rss/rssNew/gundemRss.xml',
    'Sabah': 'https://www.sabah.com.tr/rss/anasayfa.xml',
    'NTV': 'https://www.ntv.com.tr/gundem.rss',
    'HaberTürk': 'http://www.haberturk.com/rss'
}

def temizle_html(html_text):
    """HTML etiketlerini ve fazla boşlukları temizler"""
    if not html_text:
        return ""
    
    # BeautifulSoup ile HTML etiketlerini temizle
    soup = BeautifulSoup(html_text, 'html5lib')
    text = soup.get_text(separator=' ')
    
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def haber_icerigi_cek(url):
    """Verilen URL'den haber içeriğini çeker"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # BeautifulSoup ile HTML'i parse et
        soup = BeautifulSoup(response.content, 'html5lib')
        
        # Farklı haber sitelerine göre içerik çekme stratejileri
        if 'aa.com.tr' in url:
            content_div = soup.select_one('.detay-icerik')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'trthaber.com' in url:
            content_div = soup.select_one('.news-detail__content')
            if content_div:
                return content_div.get_text(strip=True)
        
        elif 'dha.com.tr' in url:
            content_div = soup.select_one('.article-body')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'sozcu.com.tr' in url:
            content_div = soup.select_one('.news-content')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'hurriyet.com.tr' in url:
            content_div = soup.select_one('.news-content')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'milliyet.com.tr' in url:
            content_div = soup.select_one('.article__content')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'sabah.com.tr' in url:
            content_div = soup.select_one('.newsDetailText')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'ntv.com.tr' in url:
            content_div = soup.select_one('.article-body')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        elif 'haberturk.com' in url:
            content_div = soup.select_one('.news-detail-content')
            if content_div:
                paragraphs = content_div.find_all('p')
                return ' '.join([p.get_text() for p in paragraphs])
        
        # Genel strateji (yukarıdakiler çalışmazsa)
        paragraphs = soup.find_all('p')
        if paragraphs:
            return ' '.join([p.get_text() for p in paragraphs])
        
        return "İçerik çekilemedi."
    
    except Exception as e:
        logger.error(f"Haber içeriği çekilirken hata oluştu: {url} - {str(e)}")
        return "İçerik çekilemedi."

def gorsel_url_cek(entry, feed_url):
    """RSS girdisinden görsel URL'sini çeker"""
    try:
        # Önce entry içinde media_content veya enclosures var mı kontrol et
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and media['url'].lower().endswith(('.jpg', '.jpeg', '.png')):
                    return media['url']
        
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'url' in enclosure and enclosure['url'].lower().endswith(('.jpg', '.jpeg', '.png')):
                    return enclosure['url']
        
        # Entry içeriğinde görsel var mı kontrol et
        if hasattr(entry, 'content') and entry.content:
            for content in entry.content:
                if 'value' in content:
                    soup = BeautifulSoup(content['value'], 'html5lib')
                    img = soup.find('img')
                    if img and img.get('src'):
                        return img['src']
        
        # Entry özetinde görsel var mı kontrol et
        if hasattr(entry, 'summary') and entry.summary:
            soup = BeautifulSoup(entry.summary, 'html5lib')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']
        
        # Eğer entry içinde bulamazsak, link'e gidip sayfadan çekmeyi deneyelim
        if hasattr(entry, 'link'):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(entry.link, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html5lib')
            
            # Meta og:image kontrolü
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']
            
            # İlk büyük resmi bul
            images = soup.find_all('img')
            for img in images:
                src = img.get('src')
                if src and src.lower().endswith(('.jpg', '.jpeg', '.png')):
                    # Görselin boyutunu kontrol et (küçük ikonları atla)
                    width = img.get('width')
                    height = img.get('height')
                    if (width and int(width) > 300) or (height and int(height) > 200):
                        return src
            
            # Eğer boyut belirtilmemiş ama src varsa, ilk resmi döndür
            for img in images:
                src = img.get('src')
                if src and src.lower().endswith(('.jpg', '.jpeg', '.png')):
                    return src
    
    except Exception as e:
        logger.error(f"Görsel URL çekilirken hata oluştu: {entry.link if hasattr(entry, 'link') else 'Bilinmeyen URL'} - {str(e)}")
    
    return None

def haberleri_cek(kaynak=None, limit=5):
    """RSS kaynaklarından haberleri çeker ve veritabanına kaydeder
    
    Args:
        kaynak (str, optional): Belirli bir kaynak adı. None ise tüm kaynaklar kullanılır.
        limit (int, optional): Her kaynaktan çekilecek maksimum haber sayısı. Varsayılan 5.
    
    Returns:
        int: Eklenen toplam haber sayısı
    """
    toplam_eklenen = 0
    
    # Eğer belirli bir kaynak belirtilmişse, sadece o kaynağı kullan
    if kaynak:
        if kaynak in RSS_FEEDS:
            kaynaklar = {kaynak: RSS_FEEDS[kaynak]}
        else:
            logger.warning(f"{kaynak} geçerli bir kaynak değil.")
            return 0
    else:
        kaynaklar = RSS_FEEDS
    
    for kaynak_adi, feed_url in kaynaklar.items():
        logger.info(f"{kaynak_adi} kaynağından haberler çekiliyor...")
        
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                logger.warning(f"{kaynak_adi} için hiç haber bulunamadı.")
                continue
            
            for entry in feed.entries[:limit]:  # Belirtilen sayıda haber al
                try:
                    # Haber URL'si
                    if not hasattr(entry, 'link'):
                        continue
                    
                    # Veritabanında bu URL ile kayıtlı haber var mı kontrol et
                    mevcut_haber = Haber.query.filter_by(url=entry.link).first()
                    if mevcut_haber:
                        continue
                    
                    # Haber başlığı
                    baslik = entry.title if hasattr(entry, 'title') else "Başlık bulunamadı"
                    
                    # Haber içeriği
                    if hasattr(entry, 'content') and entry.content:
                        icerik = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        icerik = entry.summary
                    else:
                        icerik = haber_icerigi_cek(entry.link)
                    
                    icerik = temizle_html(icerik)
                    
                    # Görsel URL'si
                    gorsel_url = gorsel_url_cek(entry, feed_url)
                    
                    # Yeni haber oluştur
                    yeni_haber = Haber(
                        baslik=baslik,
                        icerik=icerik,
                        kaynak=kaynak_adi,
                        url=entry.link,
                        gorsel_url=gorsel_url,
                        olusturulma_zamani=datetime.now()
                    )
                    
                    # Veritabanına kaydet
                    db.session.add(yeni_haber)
                    db.session.commit()
                    
                    toplam_eklenen += 1
                    logger.info(f"Yeni haber eklendi: {baslik} ({kaynak_adi})")
                
                except Exception as e:
                    logger.error(f"Haber işlenirken hata oluştu: {str(e)}")
                    db.session.rollback()
        
        except Exception as e:
            logger.error(f"{kaynak_adi} kaynağından haberler çekilirken hata oluştu: {str(e)}")
    
    return toplam_eklenen

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        yeni_haber_sayisi = haberleri_cek()
        print(f"Toplam {yeni_haber_sayisi} yeni haber eklendi.") 