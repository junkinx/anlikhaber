import os
import sys
import logging
import traceback
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import textwrap
import time
from datetime import datetime

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Haber
from scripts.image_finder import gorsel_indir, gorsel_url_gecerli_mi
from scripts.openai_utils import haber_ozetle, hashtag_olustur

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

# Sabit değerler
HEDEF_GENISLIK = 1080
HEDEF_YUKSEKLIK = 1350
FONT_DOSYASI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts', 'Roboto-Bold.ttf')
ISLENMIS_GORSEL_KLASORU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'processed')
ORIJINAL_GORSEL_KLASORU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'original')
ISLENMIS_GORSEL_URL_YOLU = '/static/images/processed'  # Web URL yolu
ORIJINAL_GORSEL_URL_YOLU = '/static/images/original'  # Orijinal görseller için URL yolu
OVERLAY_GORSEL_YOLU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'overlay.png')  # Overlay görsel yolu

"""
FONT ÖNERİLERİ:

Şu anda kullanılan fontlar:
1. Montserrat-ExtraBold.ttf - Özet metni için kullanılıyor (şu anda hata veriyor, Arial Bold'a düşüyor)
2. Roboto-Bold.ttf - Kaynak metni için kullanılıyor (şu anda boş dosya)

Alternatif modern font önerileri (Türkçe karakter desteği olan):
1. Raleway - Montserrat ile mükemmel uyum sağlayan modern, temiz bir font
2. Open Sans - Temiz, okunaklı ve modern bir font
3. Poppins - Yuvarlak, modern ve şık bir font
4. Nunito - Yumuşak köşeli, modern ve okunaklı
5. Lato - Profesyonel ve modern görünüm
6. PT Sans - Temiz ve modern, Kiril alfabesi desteği de var
7. Source Sans Pro - Temiz ve profesyonel görünüm
8. Overpass - Modern ve okunaklı
9. Work Sans - Modern ve minimal
10. Rubik - Yumuşak köşeli, modern ve şık

Bu fontları kullanmak için:
1. Google Fonts'tan indirin: https://fonts.google.com/
2. TTF dosyasını anlikhaber/static/fonts/ klasörüne kopyalayın
3. Aşağıdaki kodda font yolunu güncelleyin:
   - montserrat_font_path değişkenini yeni font dosyasının yoluna güncelleyin
   - Veya kaynak_font için truetype fonksiyonunda yolu değiştirin

Örnek:
montserrat_font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   'static', 'fonts', 'Raleway-ExtraBold.ttf')
"""

# Klasörlerin var olduğundan emin ol
os.makedirs(os.path.dirname(FONT_DOSYASI), exist_ok=True)
os.makedirs(ISLENMIS_GORSEL_KLASORU, exist_ok=True)
os.makedirs(ORIJINAL_GORSEL_KLASORU, exist_ok=True)

def gorsel_url_isle(gorsel_url, baslik, kaynak=None, odak_x=None, odak_y=None, haber=None):
    """
    Görsel URL'sini işleyerek Instagram için 4:5 oranında görsel oluşturur
    
    Args:
        gorsel_url (str): İşlenecek görselin URL'si
        baslik (str): Haberin başlığı
        kaynak (str, optional): Haber kaynağı
        odak_x (float, optional): Yatay odak noktası (0-1 arası)
        odak_y (float, optional): Dikey odak noktası (0-1 arası)
        haber (Haber, optional): Haber nesnesi
        
    Returns:
        dict: İşlenmiş görsel ve orijinal görsel URL yollarını içeren sözlük
    """
    try:
        # Instagram için 4:5 oranında görsel boyutları
        INSTAGRAM_GENISLIK = 1080
        INSTAGRAM_YUKSEKLIK = 1350  # 4:5 oranı
        
        # İçerik görseli için 13:14 oranında boyutlar
        ICERIK_GENISLIK = 1080
        ICERIK_YUKSEKLIK = 1163  # 13:14 oranı
        
        # Görsel URL'sini kontrol et
        if not gorsel_url_gecerli_mi(gorsel_url):
            logger.warning(f"Geçersiz görsel URL'si: {gorsel_url}")
            return None
        
        # Geçici dosya yolu
        temp_image_path = os.path.join(ISLENMIS_GORSEL_KLASORU, 'temp_image.jpg')
        
        # Görseli indir
        logger.info(f"Görsel indiriliyor: {gorsel_url}")
        if not gorsel_indir(gorsel_url, temp_image_path):
            logger.error(f"Görsel indirilemedi: {gorsel_url}")
            return None
        
        # PIL ile görseli aç
        try:
            img = Image.open(temp_image_path)
            logger.info(f"Görsel açıldı: {img.format}, {img.size}, {img.mode}")
        except Exception as e:
            logger.error(f"Görsel açılırken hata oluştu: {str(e)}")
            return None
        
        # Orijinal görseli kaydet
        zaman_damgasi = int(time.time())
        orijinal_dosya_adi = f"original_{zaman_damgasi}.jpg"
        orijinal_dosya_yolu = os.path.join(ORIJINAL_GORSEL_KLASORU, orijinal_dosya_adi)
        img.save(orijinal_dosya_yolu, quality=95)
        logger.info(f"Orijinal görsel kaydedildi: {orijinal_dosya_yolu}")
        
        # Orijinal görsel boyutları
        img_width, img_height = img.size
        
        # Odak noktasını belirle (varsayılan olarak merkez)
        if odak_x is None:
            odak_x = 0.5
        if odak_y is None:
            odak_y = 0.5
        
        # Odak noktasını piksel koordinatlarına dönüştür
        focus_x = int(odak_x * img_width)
        focus_y = int(odak_y * img_height)
        
        # 13:14 oranında kırpma alanı hesapla
        target_ratio = ICERIK_GENISLIK / ICERIK_YUKSEKLIK  # 13:14 oranı
        
        # Orijinal görselin oranına göre kırpma stratejisi belirle
        if img_width / img_height > target_ratio:  # Görsel daha yatay
            # Yüksekliğe göre genişliği hesapla
            crop_height = min(img_height, ICERIK_YUKSEKLIK)
            crop_width = int(crop_height * target_ratio)
            
            # Odak noktasına göre kırpma alanını hesapla
            crop_left = max(0, min(focus_x - crop_width // 2, img_width - crop_width))
            crop_top = max(0, min(focus_y - crop_height // 2, img_height - crop_height))
        else:  # Görsel daha dikey
            # Genişliğe göre yüksekliği hesapla
            crop_width = min(img_width, ICERIK_GENISLIK)
            crop_height = int(crop_width / target_ratio)
            
            # Odak noktasına göre kırpma alanını hesapla
            crop_left = max(0, min(focus_x - crop_width // 2, img_width - crop_width))
            crop_top = max(0, min(focus_y - crop_height // 2, img_height - crop_height))
        
        # Kırpma alanının sağ alt köşesini hesapla
        crop_right = crop_left + crop_width
        crop_bottom = crop_top + crop_height
        
        logger.info(f"Kırpma alanı: ({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")
        logger.info(f"Kırpma boyutları: {crop_width}x{crop_height}")
        
        # Görseli kırp
        img_cropped = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        logger.info(f"Görsel kırpıldı: {img_cropped.size}")
        
        # Kırpılan görseli 13:14 oranında (1080x1163) boyutlandır
        img_cropped = img_cropped.resize((ICERIK_GENISLIK, ICERIK_YUKSEKLIK), Image.Resampling.LANCZOS)
        logger.info(f"Kırpılmış görsel yeniden boyutlandırıldı: {ICERIK_GENISLIK}x{ICERIK_YUKSEKLIK}")
        
        # 4:5 oranında (1080x1350) siyah arka plan oluştur
        final_img = Image.new('RGB', (INSTAGRAM_GENISLIK, INSTAGRAM_YUKSEKLIK), (0, 0, 0))
        
        # İçerik görselini üst kısma yerleştir
        final_img.paste(img_cropped, (0, 0))
        logger.info(f"Görsel alt boşluk bırakılarak yerleştirildi, toplam boyut: {final_img.size}")
        
        # ImageDraw nesnesi oluştur
        draw = ImageDraw.Draw(final_img)
        logger.info("ImageDraw nesnesi oluşturuldu")
        
        # Font dosyalarını kontrol et ve yükle
        raleway_bold_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts', 'Rubik-SemiBold.ttf')
        raleway_thin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts', 'Rubik-Light.ttf')
        
        logger.info(f"Rubik SemiBold font dosyası yolu: {raleway_bold_path}")
        logger.info(f"Rubik SemiBold font dosyası mevcut mu: {os.path.exists(raleway_bold_path)}")
        logger.info(f"Rubik Light font dosyası yolu: {raleway_thin_path}")
        logger.info(f"Rubik Light font dosyası mevcut mu: {os.path.exists(raleway_thin_path)}")
        
        try:
            # Overlay görseli ekle
            try:
                if os.path.exists(OVERLAY_GORSEL_YOLU) and os.path.getsize(OVERLAY_GORSEL_YOLU) > 1000:
                    overlay_img = Image.open(OVERLAY_GORSEL_YOLU).convert("RGBA")
                    final_img.paste(overlay_img, (0, 0), overlay_img)
                    logger.info(f"Overlay görseli eklendi: {OVERLAY_GORSEL_YOLU}")
                else:
                    logger.warning(f"Overlay görsel dosyası bulunamadı veya geçersiz: {OVERLAY_GORSEL_YOLU}")
            except Exception as e:
                logger.error(f"Overlay görseli eklenirken hata: {str(e)}")
            
            # Özet metni için font
            ozet_font_size = 40
            ozet_font = ImageFont.truetype(raleway_bold_path, ozet_font_size) if os.path.exists(raleway_bold_path) else ImageFont.load_default()
            logger.info(f"Özet font yüklendi: {'Rubik-SemiBold' if os.path.exists(raleway_bold_path) else 'Default'}, boyut: {ozet_font_size}")
            
            # Kaynak ve tarih için font
            kaynak_font_size = 30
            kaynak_font = ImageFont.truetype(raleway_thin_path, kaynak_font_size) if os.path.exists(raleway_thin_path) else ImageFont.load_default()
            logger.info(f"Kaynak ve tarih font yüklendi: {'Rubik-Light' if os.path.exists(raleway_thin_path) else 'Default'}, boyut: {kaynak_font_size}")
            
            # Özet metnini ekle
            try:
                ozet_text = haber.ozet if haber.ozet else f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Haber başlığı: {baslik}"
                
                # Metni görsel üzerinde nasıl görüneceğini hesaplamak için
                # Önce metnin genişliğini ve yüksekliğini hesaplayalım
                max_width = INSTAGRAM_GENISLIK - 200  # Kenarlardan 100px boşluk
                
                # Metni satırlara böl (manuel olarak)
                lines = []
                
                # Satır boşluklarını kontrol et
                if '\n' in ozet_text:
                    # Her satırı ayrı ayrı işle
                    raw_lines = ozet_text.split('\n')
                    
                    for raw_line in raw_lines:
                        if not raw_line.strip():
                            # Boş satır ise direkt ekle
                            lines.append("")
                        else:
                            # Normal satırı kelime kelime işle
                            words_in_line = raw_line.split()
                            line_current = []
                            
                            for word in words_in_line:
                                # Mevcut satıra kelimeyi ekleyip genişliği kontrol et
                                test_line = ' '.join(line_current + [word])
                                if ozet_font.getbbox(test_line)[2] <= max_width:
                                    line_current.append(word)
                                else:
                                    # Satır doldu, yeni satıra geç
                                    if line_current:  # Boş satır eklemeyi önle
                                        lines.append(' '.join(line_current))
                                    line_current = [word]
                            
                            # Son satırı ekle
                            if line_current:
                                lines.append(' '.join(line_current))
                else:
                    # Satır içermeyen metinler için normal satır bölme işlemi
                    words = ozet_text.split()
                    current_line = []
                    
                    for word in words:
                        # Mevcut satıra kelimeyi ekleyip genişliği kontrol et
                        test_line = ' '.join(current_line + [word])
                        if ozet_font.getbbox(test_line)[2] <= max_width:
                            current_line.append(word)
                        else:
                            # Satır doldu, yeni satıra geç
                            if current_line:  # Boş satır eklemeyi önle
                                lines.append(' '.join(current_line))
                            current_line = [word]
                    
                    # Son satırı ekle
                    if current_line:
                        lines.append(' '.join(current_line))
                
                # Satır sayısını hesapla
                satir_sayisi = len(lines)
                logger.info(f"Özet metni satır sayısı: {satir_sayisi}")
                
                # Satır sayısına göre Y pozisyonunu ayarla
                if satir_sayisi <= 5:
                    ozet_y = 950  # 5 satır veya daha az
                elif satir_sayisi == 6:
                    ozet_y = 900   # 6 satır
                elif satir_sayisi == 7:
                    ozet_y = 850   # 7 satır
                elif satir_sayisi == 8:
                    ozet_y = 800   # 8 satır
                elif satir_sayisi == 9:
                    ozet_y = 750   # 9 satır
                else:
                    ozet_y = 700   # 10 satır veya daha fazla
                
                # Metni görsel üzerine yerleştir
                # Boş satırları özel işle
                spacing = 10  # Satırlar arası mesafe (15'ten 10'a düşürüldü)
                
                # Her satırı ayrı ayrı çiz, boş satırlar için daha fazla boşluk bırak
                current_y = ozet_y
                for line in lines:
                    if line.strip() == "":  # Boş satır kontrolü
                        # Boş satır için sadece boşluk bırak, ekstra boşluk için 0.75*spacing
                        current_y += ozet_font.getbbox("A")[3] + int(0.75*spacing)
                    else:
                        # Normal satırı çiz
                        draw.text((100, current_y), line, font=ozet_font, fill=(255, 255, 255))
                        current_y += ozet_font.getbbox("A")[3] + spacing
                
                logger.info("Özet metni eklendi")
                
                # Sadece kaynak bilgisini ekle
                kaynak_text = f"Kaynak: {haber.kaynak}" if haber.kaynak else ""
                
                # Kaynak bilgisini en alta ekle
                kaynak_y = INSTAGRAM_YUKSEKLIK - 100  # Alt kenardan 100px yukarıda (50px yerine)
                draw.text((100, kaynak_y), kaynak_text, font=kaynak_font, fill=(150, 150, 150))
                logger.info("Kaynak bilgisi eklendi")
                
            except Exception as e:
                logger.error(f"Metin eklenirken hata: {str(e)}")
                logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Font yüklenirken hata: {str(e)}")
        
        # İşlenmiş görseli kaydet
        islenmis_dosya_adi = f"haber_{zaman_damgasi}.jpg"
        islenmis_dosya_yolu = os.path.join(ISLENMIS_GORSEL_KLASORU, islenmis_dosya_adi)
        logger.info(f"İşlenmiş görsel kaydediliyor: {islenmis_dosya_yolu}")
        final_img.save(islenmis_dosya_yolu, quality=95)
        logger.info("İşlenmiş görsel başarıyla kaydedildi")
        
        # Geçici dosyayı sil
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            logger.info("Geçici dosya silindi")
        
        # Web URL yolunu döndür
        web_url_yolu = f"{ISLENMIS_GORSEL_URL_YOLU}/{islenmis_dosya_adi}"
        orijinal_web_url_yolu = f"{ORIJINAL_GORSEL_URL_YOLU}/{orijinal_dosya_adi}"
        
        logger.info(f"İşlenmiş görsel URL yolu: {web_url_yolu}")
        logger.info(f"Orijinal görsel URL yolu: {orijinal_web_url_yolu}")
        
        return {
            "islenmis_gorsel_url": web_url_yolu,
            "orijinal_gorsel_url": orijinal_web_url_yolu
        }
        
    except Exception as e:
        logger.error(f"Görsel işlenirken hata oluştu: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def islenmemis_haberleri_isle():
    """
    Veritabanındaki işlenmemiş görselleri işler
    """
    try:
        haberler = Haber.query.filter(
            (Haber.islenmis_gorsel_path.is_(None)) &
            (Haber.gorsel_url.isnot(None)) &
            (Haber.gorsel_url != '')
        ).all()
        
        if not haberler:
            logger.info("İşlenecek görsel bulunamadı.")
            return "İşlenecek görsel bulunamadı."
        
        sonuclar = []
        for haber in haberler:
            if not haber.ozet or haber.ozet == "":
                # OpenAI ile özet oluştur
                try:
                    logger.info(f"Haber ID {haber.id} için OpenAI ile özet oluşturuluyor...")
                    ozet = haber_ozetle(haber.icerik, haber.baslik)
                    if ozet:
                        haber.ozet = ozet
                        db.session.commit()
                        logger.info(f"Haber ID {haber.id} için özet oluşturuldu.")
                    else:
                        # Özet oluşturulamadıysa default bir özet ata
                        haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
                        db.session.commit()
                        logger.info(f"Haber ID {haber.id} için default özet atandı.")
                except Exception as e:
                    logger.error(f"Özet oluşturma hatası: {str(e)}")
                    haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
                    db.session.commit()
            
            # Görseli işle
            try:
                sonuc = haber_gorselini_isle(haber.id)
                sonuclar.append(f"ID: {haber.id}, Sonuç: {sonuc}")
            except Exception as e:
                logger.error(f"Görsel işleme hatası (ID: {haber.id}): {str(e)}")
                sonuclar.append(f"ID: {haber.id}, Hata: {str(e)}")
        
        return "\n".join(sonuclar)
    except Exception as e:
        error_msg = f"İşlenmemiş haberleri işleme hatası: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return error_msg

def haber_gorselini_isle(haber_id, odak_x=None, odak_y=None, force_reprocess=False):
    """
    Belirli bir haberin görselini işler
    
    Args:
        haber_id (int): Haberin ID'si
        odak_x (float, optional): Yatay odak noktası (0-1 arası)
        odak_y (float, optional): Dikey odak noktası (0-1 arası)
        force_reprocess (bool, optional): True ise, görsel zaten işlenmiş olsa bile yeniden işler
        
    Returns:
        str: İşlenmiş görselin URL yolu
    """
    try:
        # Haberi al
        haber = Haber.query.get(haber_id)
        
        if not haber:
            logger.error(f"Haber bulunamadı: ID {haber_id}")
            return None
        
        # Eğer haberin özeti yoksa, örnek bir özet ekle
        if not haber.ozet:
            logger.info(f"Haber ID {haber_id} için özet ekleniyor...")
            haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
            db.session.commit()
            logger.info(f"Özet eklendi: {haber.ozet}")
        
        # Görsel URL'sini kontrol et
        if not haber.gorsel_url or not gorsel_url_gecerli_mi(haber.gorsel_url):
            logger.warning(f"Geçersiz görsel URL'si: {haber.gorsel_url}")
            return None
        
        # Eğer zorla yeniden işleme seçeneği aktif değilse ve zaten işlenmiş bir görsel varsa
        if not force_reprocess and haber.islenmis_gorsel_path:
            logger.info(f"Haber görseli zaten işlenmiş: {haber.baslik}")
            return haber.islenmis_gorsel_path
        
        logger.info(f"Haber görseli işleniyor: {haber.baslik}")
        logger.info(f"Odak noktası: x={odak_x}, y={odak_y}")
        
        # Görseli işle
        sonuc = gorsel_url_isle(haber.gorsel_url, haber.baslik, haber.kaynak, odak_x, odak_y, haber)
        
        if sonuc:
            # İşlenmiş görsel yolunu kaydet
            haber.islenmis_gorsel_path = sonuc["islenmis_gorsel_url"]
            haber.orijinal_gorsel_path = sonuc["orijinal_gorsel_url"]
            db.session.commit()
            
            logger.info(f"Haber görseli işlendi: {haber.baslik}")
            return sonuc["islenmis_gorsel_url"]
        else:
            logger.warning(f"Haber görseli işlenemedi: {haber.baslik}")
            return None
    
    except Exception as e:
        logger.error(f"Haber görseli işlenirken hata oluştu (ID: {haber_id}): {str(e)}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return None

def haber_gorselini_kirp(haber_id, crop_x, crop_y, crop_width, crop_height):
    """
    Belirli bir haberin görselini kırparak işler
    
    Args:
        haber_id (int): Haberin ID'si
        crop_x (int): Kırpma başlangıç X koordinatı
        crop_y (int): Kırpma başlangıç Y koordinatı
        crop_width (int): Kırpma genişliği
        crop_height (int): Kırpma yüksekliği
        
    Returns:
        str: İşlenmiş görselin URL yolu
    """
    try:
        # Instagram için 4:5 oranında görsel boyutları
        INSTAGRAM_GENISLIK = 1080
        INSTAGRAM_YUKSEKLIK = 1350  # 4:5 oranı
        
        # İçerik görseli için 13:14 oranında boyutlar
        ICERIK_GENISLIK = 1080
        ICERIK_YUKSEKLIK = 1163  # 13:14 oranı
        
        # Haberi al
        haber = Haber.query.get(haber_id)
        
        if not haber:
            logger.error(f"Haber bulunamadı: ID {haber_id}")
            return None
        
        # Eğer haberin özeti yoksa, örnek bir özet ekle
        if not haber.ozet:
            logger.info(f"Haber ID {haber_id} için özet ekleniyor...")
            haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
            db.session.commit()
            logger.info(f"Özet eklendi: {haber.ozet}")
        
        logger.info(f"Haber görseli kırpılarak işleniyor: {haber.baslik}")
        logger.info(f"Kırpma parametreleri: X={crop_x}, Y={crop_y}, Genişlik={crop_width}, Yükseklik={crop_height}")
        
        # Orijinal görseli indir
        temp_image_path = os.path.join(ISLENMIS_GORSEL_KLASORU, 'temp_image.jpg')
        
        if not gorsel_indir(haber.gorsel_url, temp_image_path):
            logger.error(f"Görsel indirilemedi: {haber.gorsel_url}")
            return None
        
        # PIL ile görseli aç
        try:
            img = Image.open(temp_image_path)
            logger.info(f"Görsel açıldı: {img.format}, {img.size}, {img.mode}")
        except Exception as e:
            logger.error(f"Görsel açılırken hata oluştu: {str(e)}")
            return None
        
        # Orijinal görseli kaydet
        zaman_damgasi = int(time.time())
        orijinal_dosya_adi = f"original_{zaman_damgasi}.jpg"
        orijinal_dosya_yolu = os.path.join(ORIJINAL_GORSEL_KLASORU, orijinal_dosya_adi)
        img.save(orijinal_dosya_yolu, quality=95)
        logger.info(f"Orijinal görsel kaydedildi: {orijinal_dosya_yolu}")
        
        # Görseli kırp
        try:
            # Kırpma alanının görsel sınırları içinde olduğundan emin ol
            img_width, img_height = img.size
            
            # Kırpma alanını sınırla
            crop_x = max(0, min(int(crop_x), img_width - 1))
            crop_y = max(0, min(int(crop_y), img_height - 1))
            crop_width = max(1, min(int(crop_width), img_width - crop_x))
            crop_height = max(1, min(int(crop_height), img_height - crop_y))
            
            # Görseli kırp
            img_cropped = img.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
            logger.info(f"Görsel kırpıldı: {img_cropped.size}")
            
            # Kırpılmış görselin oranını hesapla
            cropped_ratio = crop_width / crop_height
            target_ratio = ICERIK_GENISLIK / ICERIK_YUKSEKLIK  # 13:14 oranı
            
            logger.info(f"Kırpılmış görsel oranı: {cropped_ratio}, Hedef oran: {target_ratio}")
            
            # 13:14 oranında (1080x1163) siyah arka plan oluştur
            content_img = Image.new('RGB', (ICERIK_GENISLIK, ICERIK_YUKSEKLIK), (0, 0, 0))
            
            # Kırpılmış görseli içerik görselinin içine sığdır (oranını koruyarak)
            # Kırpılmış görselin boyutlarını hesapla
            if cropped_ratio > target_ratio:  # Kırpılmış görsel daha yatay
                # Genişliğe göre ölçeklendir
                new_width = ICERIK_GENISLIK
                new_height = int(new_width / cropped_ratio)
            else:  # Kırpılmış görsel daha dikey
                # Yüksekliğe göre ölçeklendir
                new_height = ICERIK_YUKSEKLIK
                new_width = int(new_height * cropped_ratio)
            
            # Kırpılmış görseli yeniden boyutlandır
            img_cropped = img_cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Kırpılmış görsel yeniden boyutlandırıldı: {new_width}x{new_height}")
            
            # Kırpılmış görseli içerik görselinin ortasına yerleştir
            paste_x = (ICERIK_GENISLIK - new_width) // 2
            paste_y = (ICERIK_YUKSEKLIK - new_height) // 2
            content_img.paste(img_cropped, (paste_x, paste_y))
            logger.info(f"Kırpılmış görsel içerik görselinin ortasına yerleştirildi: {paste_x}, {paste_y}")
            
            # 4:5 oranında (1080x1350) siyah arka plan oluştur
            final_img = Image.new('RGB', (INSTAGRAM_GENISLIK, INSTAGRAM_YUKSEKLIK), (0, 0, 0))
            
            # İçerik görselini üst kısma yerleştir
            final_img.paste(content_img, (0, 0))
            logger.info(f"Görsel alt boşluk bırakılarak yerleştirildi, toplam boyut: {final_img.size}")
            
            # ImageDraw nesnesi oluştur
            draw = ImageDraw.Draw(final_img)
            logger.info("ImageDraw nesnesi oluşturuldu")
            
            # Font dosyalarını kontrol et ve yükle
            raleway_bold_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts', 'Rubik-SemiBold.ttf')
            raleway_thin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts', 'Rubik-Light.ttf')
            
            logger.info(f"Rubik SemiBold font dosyası yolu: {raleway_bold_path}")
            logger.info(f"Rubik SemiBold font dosyası mevcut mu: {os.path.exists(raleway_bold_path)}")
            logger.info(f"Rubik Light font dosyası yolu: {raleway_thin_path}")
            logger.info(f"Rubik Light font dosyası mevcut mu: {os.path.exists(raleway_thin_path)}")
            
            try:
                # Overlay görseli ekle
                try:
                    if os.path.exists(OVERLAY_GORSEL_YOLU) and os.path.getsize(OVERLAY_GORSEL_YOLU) > 1000:
                        overlay_img = Image.open(OVERLAY_GORSEL_YOLU).convert("RGBA")
                        final_img.paste(overlay_img, (0, 0), overlay_img)
                        logger.info(f"Overlay görseli eklendi: {OVERLAY_GORSEL_YOLU}")
                    else:
                        logger.warning(f"Overlay görsel dosyası bulunamadı veya geçersiz: {OVERLAY_GORSEL_YOLU}")
                except Exception as e:
                    logger.error(f"Overlay görseli eklenirken hata: {str(e)}")
                
                # Özet metni için font
                ozet_font_size = 40
                ozet_font = ImageFont.truetype(raleway_bold_path, ozet_font_size) if os.path.exists(raleway_bold_path) else ImageFont.load_default()
                logger.info(f"Özet font yüklendi: {'Rubik-SemiBold' if os.path.exists(raleway_bold_path) else 'Default'}, boyut: {ozet_font_size}")
                
                # Kaynak ve tarih için font
                kaynak_font_size = 30
                kaynak_font = ImageFont.truetype(raleway_thin_path, kaynak_font_size) if os.path.exists(raleway_thin_path) else ImageFont.load_default()
                logger.info(f"Kaynak ve tarih font yüklendi: {'Rubik-Light' if os.path.exists(raleway_thin_path) else 'Default'}, boyut: {kaynak_font_size}")
                
                # Özet metnini ekle
                try:
                    ozet_text = haber.ozet if haber.ozet else f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Haber başlığı: {haber.baslik}"
                    
                    # Metni görsel üzerinde nasıl görüneceğini hesaplamak için
                    # Önce metnin genişliğini ve yüksekliğini hesaplayalım
                    max_width = INSTAGRAM_GENISLIK - 200  # Kenarlardan 100px boşluk
                    
                    # Metni satırlara böl (manuel olarak)
                    lines = []
                    
                    # Satır boşluklarını kontrol et
                    if '\n' in ozet_text:
                        # Her satırı ayrı ayrı işle
                        raw_lines = ozet_text.split('\n')
                        
                        for raw_line in raw_lines:
                            if not raw_line.strip():
                                # Boş satır ise direkt ekle
                                lines.append("")
                            else:
                                # Normal satırı kelime kelime işle
                                words_in_line = raw_line.split()
                                line_current = []
                                
                                for word in words_in_line:
                                    # Mevcut satıra kelimeyi ekleyip genişliği kontrol et
                                    test_line = ' '.join(line_current + [word])
                                    if ozet_font.getbbox(test_line)[2] <= max_width:
                                        line_current.append(word)
                                    else:
                                        # Satır doldu, yeni satıra geç
                                        if line_current:  # Boş satır eklemeyi önle
                                            lines.append(' '.join(line_current))
                                        line_current = [word]
                                
                                # Son satırı ekle
                                if line_current:
                                    lines.append(' '.join(line_current))
                    else:
                        # Satır içermeyen metinler için normal satır bölme işlemi
                        words = ozet_text.split()
                        current_line = []
                        
                        for word in words:
                            # Mevcut satıra kelimeyi ekleyip genişliği kontrol et
                            test_line = ' '.join(current_line + [word])
                            if ozet_font.getbbox(test_line)[2] <= max_width:
                                current_line.append(word)
                            else:
                                # Satır doldu, yeni satıra geç
                                if current_line:  # Boş satır eklemeyi önle
                                    lines.append(' '.join(current_line))
                                current_line = [word]
                        
                        # Son satırı ekle
                        if current_line:
                            lines.append(' '.join(current_line))
                
                    # Satır sayısını hesapla
                    satir_sayisi = len(lines)
                    logger.info(f"Özet metni satır sayısı: {satir_sayisi}")
                    
                    # Satır sayısına göre Y pozisyonunu ayarla
                    if satir_sayisi <= 5:
                        ozet_y = 950  # 5 satır veya daha az
                    elif satir_sayisi == 6:
                        ozet_y = 900   # 6 satır
                    elif satir_sayisi == 7:
                        ozet_y = 850   # 7 satır
                    elif satir_sayisi == 8:
                        ozet_y = 800   # 8 satır
                    elif satir_sayisi == 9:
                        ozet_y = 750   # 9 satır
                    else:
                        ozet_y = 700   # 10 satır veya daha fazla
                    
                    # Metni görsel üzerine yerleştir
                    # Boş satırları özel işle
                    spacing = 10  # Satırlar arası mesafe (15'ten 10'a düşürüldü)
                    
                    # Her satırı ayrı ayrı çiz, boş satırlar için daha fazla boşluk bırak
                    current_y = ozet_y
                    for line in lines:
                        if line.strip() == "":  # Boş satır kontrolü
                            # Boş satır için sadece boşluk bırak, ekstra boşluk için 0.75*spacing
                            current_y += ozet_font.getbbox("A")[3] + int(0.75*spacing)
                        else:
                            # Normal satırı çiz
                            draw.text((100, current_y), line, font=ozet_font, fill=(255, 255, 255))
                            current_y += ozet_font.getbbox("A")[3] + spacing
                
                    logger.info("Özet metni eklendi")
                    
                    # Sadece kaynak bilgisini ekle
                    kaynak_text = f"Kaynak: {haber.kaynak}" if haber.kaynak else ""
                    
                    # Kaynak bilgisini en alta ekle
                    kaynak_y = INSTAGRAM_YUKSEKLIK - 100  # Alt kenardan 100px yukarıda (50px yerine)
                    draw.text((100, kaynak_y), kaynak_text, font=kaynak_font, fill=(150, 150, 150))
                    logger.info("Kaynak bilgisi eklendi")
                    
                except Exception as e:
                    logger.error(f"Metin eklenirken hata: {str(e)}")
                    logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Font yüklenirken hata: {str(e)}")
            
            # İşlenmiş görseli kaydet
            islenmis_dosya_adi = f"haber_{zaman_damgasi}.jpg"
            islenmis_dosya_yolu = os.path.join(ISLENMIS_GORSEL_KLASORU, islenmis_dosya_adi)
            final_img.save(islenmis_dosya_yolu, quality=95)
            logger.info(f"İşlenmiş görsel kaydedildi: {islenmis_dosya_yolu}")
            
            # Haberi güncelle
            haber.islenmis_gorsel_path = os.path.join(ISLENMIS_GORSEL_URL_YOLU, islenmis_dosya_adi)
            haber.orijinal_gorsel_path = os.path.join(ORIJINAL_GORSEL_URL_YOLU, orijinal_dosya_adi)
            db.session.commit()
            
            # Geçici dosyayı sil
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                logger.info("Geçici dosya silindi")
            
            return haber.islenmis_gorsel_path
            
        except Exception as e:
            logger.error(f"Görsel işlenirken hata oluştu: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    except Exception as e:
        logger.error(f"Haber görseli kırpılırken genel hata oluştu: {str(e)}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return None

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        islenen_gorsel_sayisi = islenmemis_haberleri_isle()
        print(f"Toplam {islenen_gorsel_sayisi} haber görseli işlendi.") 