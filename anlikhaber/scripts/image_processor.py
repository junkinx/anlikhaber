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

# Klasörlerin var olduğundan emin ol
os.makedirs(os.path.dirname(FONT_DOSYASI), exist_ok=True)
os.makedirs(ISLENMIS_GORSEL_KLASORU, exist_ok=True)
os.makedirs(ORIJINAL_GORSEL_KLASORU, exist_ok=True)

def gorsel_url_isle(gorsel_url, baslik, kaynak=None, odak_x=None, odak_y=None, haber=None):
    """
    Görsel URL'sini işler ve üzerine metin ekler
    
    Args:
        gorsel_url (str): İşlenecek görsel URL'si
        baslik (str): Görsele eklenecek başlık
        kaynak (str, optional): Haber kaynağı
        odak_x (float, optional): Görsel kırpma için x odak noktası (0-1 arası)
        odak_y (float, optional): Görsel kırpma için y odak noktası (0-1 arası)
        haber (Haber, optional): Haber nesnesi
        
    Returns:
        tuple: İşlenmiş görsel URL'si, orijinal görsel URL'si
    """
    if not gorsel_url:
        logger.warning(f"Görsel URL'si bulunamadı: {baslik}")
        return None, None
    
    try:
        # URL'deki soru işareti ve parametreleri temizle
        temiz_url = gorsel_url.split('?')[0] if '?' in gorsel_url else gorsel_url
        
        # Sabah gazetesi için özel işlem
        if 'iasbh.tmgrup.com.tr' in temiz_url:
            # URL'deki "u=" parametresini bul ve gerçek URL'yi çıkar
            if 'u=' in gorsel_url:
                try:
                    gercek_url = gorsel_url.split('u=')[1]
                    # Eğer URL'de başka parametreler varsa temizle
                    if '?' in gercek_url:
                        gercek_url = gercek_url.split('?')[0]
                    temiz_url = gercek_url
                except:
                    logger.warning(f"Sabah URL'si işlenirken hata oluştu: {gorsel_url}")
        
        # Geçici dosya yolu
        temp_image_path = os.path.join(ISLENMIS_GORSEL_KLASORU, 'temp_image.jpg')
        
        # Görseli indir
        logger.info(f"Görsel indiriliyor: {gorsel_url}")
        if not gorsel_indir(gorsel_url, temp_image_path):
            logger.error(f"Görsel indirilemedi: {gorsel_url}")
            return None, None
        
        # PIL ile görseli aç
        try:
            img = Image.open(temp_image_path)
            logger.info(f"Görsel açıldı: {img.format}, {img.size}, {img.mode}")
        except Exception as e:
            logger.error(f"Görsel açılırken hata oluştu: {str(e)}")
            
            # Alternatif yöntem deneyelim - BytesIO ile
            try:
                logger.info("BytesIO ile görsel açma deneniyor...")
                img = Image.open(BytesIO(response.content))
                logger.info(f"BytesIO ile görsel açıldı: {img.format}, {img.size}, {img.mode}")
            except Exception as e2:
                logger.error(f"BytesIO ile görsel açılırken hata oluştu: {str(e2)}")
                raise Exception(f"Görsel açılamadı: {str(e2)}")
        
        try:
            # Orijinal görseli kaydet
            zaman_damgasi = int(time.time())
            orijinal_dosya_adi = f"original_{zaman_damgasi}.jpg"
            orijinal_dosya_yolu = os.path.join(ORIJINAL_GORSEL_KLASORU, orijinal_dosya_adi)
            img.save(orijinal_dosya_yolu, quality=95)
            logger.info(f"Orijinal görsel kaydedildi: {orijinal_dosya_yolu}")
            
            # Görseli boyutlandır ve kırp
            img_width, img_height = img.size
            
            # Hedef en-boy oranı
            hedef_oran = HEDEF_GENISLIK / HEDEF_YUKSEKLIK
            
            # Görsel en-boy oranı
            gorsel_oran = img_width / img_height
            
            logger.info(f"Görsel oranı: {gorsel_oran}, Hedef oran: {hedef_oran}")
            
            # Yatay görsel (görsel oranı > hedef oran)
            if gorsel_oran > hedef_oran:
                logger.info("Yatay görsel tespit edildi, odak noktasını koruyarak kırpılacak")
                
                # Yeni yaklaşım: Alt kısımda boşluk bırakarak daha fazla görsel içeriği koruyalım
                # Boşluk miktarı - hedef yüksekliğin %15'i kadar alt kısımda boşluk bırakalım
                alt_bosluk_orani = 0.15
                alt_bosluk = int(HEDEF_YUKSEKLIK * alt_bosluk_orani)
                efektif_yukseklik = HEDEF_YUKSEKLIK - alt_bosluk
                
                # Önce görseli efektif yüksekliğe göre ölçeklendir
                yeni_yukseklik = efektif_yukseklik
                yeni_genislik = int(img_width * (efektif_yukseklik / img_height))
                
                # Görseli yeniden boyutlandır
                img_resized = img.resize((yeni_genislik, yeni_yukseklik), Image.Resampling.LANCZOS)
                logger.info(f"Görsel yeniden boyutlandırıldı: {yeni_genislik}x{yeni_yukseklik}")
                
                # Odak noktasını kullanarak kırp
                if odak_x is not None:
                    # Manuel odak noktası kullanılıyor
                    odak_piksel_x = int(yeni_genislik * odak_x)
                    # Odak noktasını merkez alarak kırp
                    sol_kenar = max(0, odak_piksel_x - HEDEF_GENISLIK // 2)
                    # Sağ kenarın görsel sınırlarını aşmamasını sağla
                    if sol_kenar + HEDEF_GENISLIK > yeni_genislik:
                        sol_kenar = yeni_genislik - HEDEF_GENISLIK
                    sag_kenar = sol_kenar + HEDEF_GENISLIK
                    logger.info(f"Manuel odak noktası kullanılıyor: x={odak_x}, piksel={odak_piksel_x}")
                else:
                    # Otomatik odak noktası (ortadan)
                    sol_kenar = (yeni_genislik - HEDEF_GENISLIK) // 2
                    sag_kenar = sol_kenar + HEDEF_GENISLIK
                    logger.info("Otomatik odak noktası kullanılıyor (ortadan)")
                
                # Kırpma işlemi
                img_cropped = img_resized.crop((sol_kenar, 0, sag_kenar, yeni_yukseklik))
                logger.info(f"Görsel kırpıldı: {img_cropped.size}")
                
                # Hedef boyutlarda boş bir görsel oluştur (siyah arka plan)
                img = Image.new('RGB', (HEDEF_GENISLIK, HEDEF_YUKSEKLIK), (0, 0, 0))
                
                # Kırpılmış görseli üst kısma yerleştir
                img.paste(img_cropped, (0, 0))
                logger.info(f"Görsel alt boşluk bırakılarak yerleştirildi, toplam boyut: {img.size}")
            
            # Dikey görsel (görsel oranı < hedef oran)
            elif gorsel_oran < hedef_oran:
                logger.info("Dikey görsel tespit edildi, odak noktasını koruyarak kırpılacak")
                
                # Önce görseli genişliğe göre ölçeklendir
                yeni_genislik = HEDEF_GENISLIK
                yeni_yukseklik = int(img_height * (HEDEF_GENISLIK / img_width))
                
                # Görseli yeniden boyutlandır
                img = img.resize((yeni_genislik, yeni_yukseklik), Image.Resampling.LANCZOS)
                logger.info(f"Görsel yeniden boyutlandırıldı: {yeni_genislik}x{yeni_yukseklik}")
                
                # Odak noktasını kullanarak kırp
                if odak_y is not None:
                    # Manuel odak noktası kullanılıyor
                    odak_piksel_y = int(yeni_yukseklik * odak_y)
                    # Odak noktasını merkez alarak kırp
                    ust_kenar = max(0, odak_piksel_y - HEDEF_YUKSEKLIK // 2)
                    # Alt kenarın görsel sınırlarını aşmamasını sağla
                    if ust_kenar + HEDEF_YUKSEKLIK > yeni_yukseklik:
                        ust_kenar = yeni_yukseklik - HEDEF_YUKSEKLIK
                    alt_kenar = ust_kenar + HEDEF_YUKSEKLIK
                    logger.info(f"Manuel odak noktası kullanılıyor: y={odak_y}, piksel={odak_piksel_y}")
                else:
                    # Otomatik odak noktası (üstten 1/3)
                    ust_kenar = (yeni_yukseklik - HEDEF_YUKSEKLIK) // 3  # Üstten 1/3 oranında kırp
                    alt_kenar = ust_kenar + HEDEF_YUKSEKLIK
                    logger.info("Otomatik odak noktası kullanılıyor (üstten 1/3)")
                
                # Kırpma işlemi
                img = img.crop((0, ust_kenar, yeni_genislik, alt_kenar))
                logger.info(f"Görsel kırpıldı: {img.size}")
            
            # Tam orana sahip görsel
            else:
                logger.info("Görsel oranı hedef orana uygun, doğrudan boyutlandırılacak")
                img = img.resize((HEDEF_GENISLIK, HEDEF_YUKSEKLIK), Image.Resampling.LANCZOS)
                logger.info(f"Görsel yeniden boyutlandırıldı: {HEDEF_GENISLIK}x{HEDEF_YUKSEKLIK}")
            
            # Metin eklemek için
            draw = ImageDraw.Draw(img)
            logger.info("ImageDraw nesnesi oluşturuldu")
            
            # Font yükleme
            try:
                # Özel font dosyasını yüklemeyi dene
                baslik_font_boyutu = 120  # Başlangıç font boyutu
                kaynak_font_boyutu = 40
                
                # PIL'in kendi içindeki varsayılan fontlardan birini kullan
                from PIL.ImageFont import truetype
                try:
                    # Sistem fontlarından birini kullan
                    baslik_font = truetype("Arial", baslik_font_boyutu)
                    kaynak_font = truetype("Arial", kaynak_font_boyutu)
                    logger.info(f"Arial font yüklendi, boyut: {baslik_font_boyutu}")
                except:
                    try:
                        # Alternatif olarak başka bir sistem fontu dene
                        baslik_font = truetype("DejaVuSans", baslik_font_boyutu)
                        kaynak_font = truetype("DejaVuSans", kaynak_font_boyutu)
                        logger.info(f"DejaVuSans font yüklendi, boyut: {baslik_font_boyutu}")
                    except:
                        # Son çare olarak PIL'in kendi içindeki varsayılan fontu kullan
                        logger.info("Sistem fontları bulunamadı, PIL'in kendi fontunu kullanıyoruz")
                        from PIL import ImageFont
                        baslik_font = ImageFont.load_default()
                        kaynak_font = ImageFont.load_default()
                        logger.info("PIL varsayılan fontu yüklendi")
            except Exception as e:
                logger.error(f"Font yüklenirken hata oluştu: {str(e)}")
                # Varsayılan font kullan
                baslik_font = ImageFont.load_default()
                kaynak_font = ImageFont.load_default()
                logger.info("Hata nedeniyle varsayılan font kullanılıyor")
            
            # Maksimum satır sayısı
            MAX_SATIR_SAYISI = 3
            
            # Başlık için uygun font boyutunu ve satır genişliğini bul
            def uygun_font_boyutu_bul(baslik, max_satir_sayisi, baslangic_boyutu, min_boyutu=40):
                mevcut_boyut = baslangic_boyutu
                uygun_boyut = None
                uygun_satirlar = None
                
                while mevcut_boyut >= min_boyutu:
                    try:
                        # Mevcut font boyutu ile font oluştur
                        try:
                            font = truetype("Arial", mevcut_boyut)
                        except:
                            try:
                                font = truetype("DejaVuSans", mevcut_boyut)
                            except:
                                # Varsayılan font kullan
                                font = ImageFont.load_default()
                        
                        # Görsel genişliğinin %90'ını kullan
                        max_genislik = int(HEDEF_GENISLIK * 0.9)
                        
                        # Başlığı satırlara böl
                        # Karakter sayısı yerine piksel genişliğine göre hesaplama yap
                        kelimeler = baslik.split()
                        satirlar = []
                        mevcut_satir = ""
                        
                        for kelime in kelimeler:
                            test_satir = mevcut_satir + " " + kelime if mevcut_satir else kelime
                            satir_genislik = draw.textlength(test_satir, font=font)
                            
                            if satir_genislik <= max_genislik:
                                mevcut_satir = test_satir
                            else:
                                satirlar.append(mevcut_satir)
                                mevcut_satir = kelime
                        
                        if mevcut_satir:
                            satirlar.append(mevcut_satir)
                        
                        # Satır sayısı kontrolü
                        if len(satirlar) <= max_satir_sayisi:
                            uygun_boyut = mevcut_boyut
                            uygun_satirlar = satirlar
                            break
                    except Exception as e:
                        logger.error(f"Font boyutu hesaplanırken hata: {str(e)}")
                    
                    # Font boyutunu azalt
                    mevcut_boyut -= 10
                
                # Eğer uygun boyut bulunamadıysa minimum boyutu kullan
                if uygun_boyut is None:
                    uygun_boyut = min_boyutu
                    # Minimum boyutta tekrar satırlara böl
                    try:
                        font = truetype("Arial", uygun_boyut)
                    except:
                        try:
                            font = truetype("DejaVuSans", uygun_boyut)
                        except:
                            font = ImageFont.load_default()
                    
                    max_genislik = int(HEDEF_GENISLIK * 0.9)
                    kelimeler = baslik.split()
                    satirlar = []
                    mevcut_satir = ""
                    
                    for kelime in kelimeler:
                        test_satir = mevcut_satir + " " + kelime if mevcut_satir else kelime
                        satir_genislik = draw.textlength(test_satir, font=font)
                        
                        if satir_genislik <= max_genislik:
                            mevcut_satir = test_satir
                        else:
                            satirlar.append(mevcut_satir)
                            mevcut_satir = kelime
                            
                            # Maksimum satır sayısına ulaşıldıysa
                            if len(satirlar) >= max_satir_sayisi - 1:
                                break
                    
                    if mevcut_satir:
                        satirlar.append(mevcut_satir)
                    
                    # Son satırı kısalt ve "..." ekle
                    if len(satirlar) > max_satir_sayisi:
                        son_satir = satirlar[max_satir_sayisi - 1]
                        while draw.textlength(son_satir + "...", font=font) > max_genislik:
                            son_satir = son_satir[:-1]
                        
                        satirlar = satirlar[:max_satir_sayisi - 1]
                        satirlar.append(son_satir + "...")
                    
                    uygun_satirlar = satirlar
                
                return uygun_boyut, uygun_satirlar
            
            # Uygun font boyutunu ve satırları bul
            baslik_font_boyutu, baslik_satirlari = uygun_font_boyutu_bul(baslik, MAX_SATIR_SAYISI, baslik_font_boyutu)
            
            # Font'u güncelle
            try:
                baslik_font = truetype("Arial", baslik_font_boyutu)
            except:
                try:
                    baslik_font = truetype("DejaVuSans", baslik_font_boyutu)
                except:
                    baslik_font = ImageFont.load_default()
            
            logger.info(f"Başlık için uygun font boyutu: {baslik_font_boyutu}, Satır sayısı: {len(baslik_satirlari)}")
            
            # Başlık için toplam yükseklik hesapla
            baslik_yukseklik = len(baslik_satirlari) * baslik_font_boyutu * 1.2
            
            # Overlay görseli ekle
            try:
                if os.path.exists(OVERLAY_GORSEL_YOLU):
                    overlay_img = Image.open(OVERLAY_GORSEL_YOLU).convert("RGBA")
                    
                    # Overlay görselini ana görselin tam boyutuna göre yeniden boyutlandır
                    overlay_width = HEDEF_GENISLIK
                    overlay_height = HEDEF_YUKSEKLIK
                    # Overlay yükseklik sınırlamasını kaldırıyoruz, tam oturması için
                    overlay_img = overlay_img.resize((overlay_width, overlay_height), Image.Resampling.LANCZOS)
                    
                    # Overlay görselini tam görselin üzerine yerleştir
                    overlay_y = 0
                    
                    logger.info(f"Overlay görseli ekleniyor: {OVERLAY_GORSEL_YOLU}, boyut: {overlay_width}x{overlay_height}, pozisyon: (0, {overlay_y})")
                    
                    # Overlay görselini ana görsele ekle
                    if overlay_img.mode == 'RGBA':
                        # RGBA modundaki görseli eklemek için
                        img_rgba = img.convert("RGBA")
                        img_rgba.paste(overlay_img, (0, int(overlay_y)), overlay_img)
                        img = img_rgba.convert("RGB")
                        draw = ImageDraw.Draw(img)  # Draw nesnesini yeniden oluştur
                    else:
                        # RGB modundaki görseli eklemek için
                        img.paste(overlay_img, (0, int(overlay_y)))
                    
                    logger.info(f"Overlay görseli eklendi: {OVERLAY_GORSEL_YOLU}")
                    
                    # Haber özetini ekle (eğer varsa)
                    if haber and haber.ozet:
                        ozet_font_boyutu = 40  # Özet için font boyutu
                        try:
                            ozet_font = truetype("Arial", ozet_font_boyutu)
                        except:
                            try:
                                ozet_font = truetype("DejaVuSans", ozet_font_boyutu)
                            except:
                                ozet_font = ImageFont.load_default()
                        
                        # Özet için maksimum satır sayısı
                        MAX_OZET_SATIR_SAYISI = 5
                        
                        # Görsel genişliğinin %80'ini kullan
                        max_genislik = int(HEDEF_GENISLIK * 0.8)
                        
                        # Özeti satırlara böl
                        kelimeler = haber.ozet.split()
                        satirlar = []
                        mevcut_satir = ""
                        
                        for kelime in kelimeler:
                            test_satir = mevcut_satir + " " + kelime if mevcut_satir else kelime
                            satir_genislik = draw.textlength(test_satir, font=ozet_font)
                            
                            if satir_genislik <= max_genislik:
                                mevcut_satir = test_satir
                            else:
                                satirlar.append(mevcut_satir)
                                mevcut_satir = kelime
                                
                                # Maksimum satır sayısına ulaşıldıysa
                                if len(satirlar) >= MAX_OZET_SATIR_SAYISI - 1:
                                    break
                        
                        if mevcut_satir:
                            satirlar.append(mevcut_satir)
                        
                        # Son satırı kısalt ve "..." ekle
                        if len(satirlar) > MAX_OZET_SATIR_SAYISI:
                            son_satir = satirlar[MAX_OZET_SATIR_SAYISI - 1]
                            while draw.textlength(son_satir + "...", font=ozet_font) > max_genislik:
                                son_satir = son_satir[:-1]
                            
                            satirlar = satirlar[:MAX_OZET_SATIR_SAYISI - 1]
                            satirlar.append(son_satir + "...")
                        
                        # Özeti overlay'in alt kısmına yerleştir
                        ozet_y_pozisyon = HEDEF_YUKSEKLIK - (len(satirlar) * ozet_font_boyutu * 1.2) - 200  # Alt kenardan 200 piksel yukarı
                        
                        # Özeti ekle
                        for satir in satirlar:
                            # Satırı sola yasla (sol kenardan 100 piksel içeri)
                            x_pozisyon = 100
                            
                            # Metin gölgesi
                            for i in range(1, 4):  # Gölge için
                                draw.text((x_pozisyon+i, ozet_y_pozisyon+i), satir, font=ozet_font, fill=(0, 0, 0))
                            
                            # Asıl metin
                            draw.text((x_pozisyon, ozet_y_pozisyon), satir, font=ozet_font, fill=(255, 255, 255))
                            
                            # Bir sonraki satır için y pozisyonunu güncelle
                            ozet_y_pozisyon += ozet_font_boyutu * 1.2
                        
                        logger.info("Haber özeti eklendi")
                else:
                    logger.warning(f"Overlay görseli bulunamadı: {OVERLAY_GORSEL_YOLU}")
            except Exception as e:
                logger.error(f"Overlay görseli eklenirken hata oluştu: {str(e)}")
                logger.error(traceback.format_exc())
            
            # Kaynak bilgisini ekle (eğer varsa)
            if kaynak:
                kaynak_metni = f"Kaynak: {kaynak}"
                
                # Kaynağı sağ alt köşeye yerleştir
                x_pozisyon = HEDEF_GENISLIK - 400  # Sağ kenardan 400 piksel içeri
                y_pozisyon = HEDEF_YUKSEKLIK - 100  # Alt kenardan 100 piksel yukarı
                
                # Metin gölgesi
                for i in range(1, 4):  # Daha kalın gölge için
                    draw.text((x_pozisyon+i, y_pozisyon+i), kaynak_metni, font=kaynak_font, fill=(0, 0, 0))
                
                # Asıl metin
                draw.text((x_pozisyon, y_pozisyon), kaynak_metni, font=kaynak_font, fill=(255, 255, 255))
                
                logger.info("Kaynak bilgisi eklendi")
            
            # Tarih bilgisini ekle
            tarih_metni = datetime.now().strftime("%d.%m.%Y")
            
            # Tarihi sol alt köşeye yerleştir
            x_pozisyon = 50
            y_pozisyon = HEDEF_YUKSEKLIK - 100  # Alt kenardan 100 piksel yukarı
            
            # Metin gölgesi
            for i in range(1, 4):  # Daha kalın gölge için
                draw.text((x_pozisyon+i, y_pozisyon+i), tarih_metni, font=kaynak_font, fill=(0, 0, 0))
            
            # Asıl metin
            draw.text((x_pozisyon, y_pozisyon), tarih_metni, font=kaynak_font, fill=(255, 255, 255))
            
            logger.info("Tarih bilgisi eklendi")
            
            # Dosya adı oluştur
            dosya_adi = f"haber_{zaman_damgasi}.jpg"
            dosya_yolu = os.path.join(ISLENMIS_GORSEL_KLASORU, dosya_adi)
            
            # Görseli kaydet
            logger.info(f"İşlenmiş görsel kaydediliyor: {dosya_yolu}")
            img.save(dosya_yolu, quality=95)
            logger.info("İşlenmiş görsel başarıyla kaydedildi")
            
            # Geçici dosyayı sil
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                logger.info("Geçici dosya silindi")
            
            # Web URL yolunu döndür
            web_url_yolu = f"{ISLENMIS_GORSEL_URL_YOLU}/{dosya_adi}"
            orijinal_web_url_yolu = f"{ORIJINAL_GORSEL_URL_YOLU}/{orijinal_dosya_adi}"
            
            logger.info(f"İşlenmiş görsel URL yolu: {web_url_yolu}")
            logger.info(f"Orijinal görsel URL yolu: {orijinal_web_url_yolu}")
            
            # İşlenmiş görsel URL'si ve orijinal görsel URL'sini içeren bir sözlük döndür
            return {
                "islenmis_gorsel_url": web_url_yolu,
                "orijinal_gorsel_url": orijinal_web_url_yolu,
                "zaman_damgasi": zaman_damgasi
            }
        except Exception as e:
            logger.error(f"Görsel işleme sırasında hata oluştu: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    except Exception as e:
        logger.error(f"Görsel işlenirken hata oluştu: {gorsel_url} - {str(e)}")
        logger.error(traceback.format_exc())
        return None, None

def islenmemis_haberleri_isle():
    """Veritabanındaki işlenmemiş görselleri olan haberleri işler"""
    try:
        # İşlenmemiş görselleri olan haberleri al
        islenmemis_haberler = Haber.query.filter(
            Haber.gorsel_url.isnot(None),
            (Haber.islenmis_gorsel_path.is_(None)) | (Haber.islenmis_gorsel_path == '')
        ).all()
        
        if not islenmemis_haberler:
            logger.info("İşlenecek görsel bulunamadı.")
            return 0
        
        islenen_gorsel_sayisi = 0
        
        for haber in islenmemis_haberler:
            try:
                logger.info(f"Haber görseli işleniyor: {haber.baslik}")
                
                # Eğer haberin özeti yoksa, örnek bir özet ekle
                if not haber.ozet:
                    logger.info(f"Haber ID {haber.id} için özet ekleniyor...")
                    haber.ozet = f"Bu haber için otomatik oluşturulmuş örnek bir özet metnidir. Gerçek özet, AI tarafından oluşturulacaktır. Haber başlığı: {haber.baslik}"
                    db.session.commit()
                    logger.info(f"Özet eklendi: {haber.ozet}")
                
                # Görsel URL'sini kontrol et
                if not gorsel_url_gecerli_mi(haber.gorsel_url):
                    logger.warning(f"Geçersiz görsel URL'si: {haber.gorsel_url}")
                    continue
                
                # Görseli işle
                sonuc = gorsel_url_isle(haber.gorsel_url, haber.baslik, haber.kaynak, haber=haber)
                
                if sonuc:
                    # İşlenmiş görsel yolunu kaydet
                    haber.islenmis_gorsel_path = sonuc["islenmis_gorsel_url"]
                    haber.orijinal_gorsel_path = sonuc["orijinal_gorsel_url"]
                    db.session.commit()
                    
                    islenen_gorsel_sayisi += 1
                    logger.info(f"Haber görseli işlendi: {haber.baslik}")
                else:
                    logger.warning(f"Haber görseli işlenemedi: {haber.baslik}")
                
            except Exception as e:
                logger.error(f"Haber görseli işlenirken hata oluştu (ID: {haber.id}): {str(e)}")
                db.session.rollback()
        
        return islenen_gorsel_sayisi
    
    except Exception as e:
        logger.error(f"Haberler işlenirken genel hata oluştu: {str(e)}")
        return 0

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

if __name__ == "__main__":
    # Bu script doğrudan çalıştırıldığında test amaçlı çalışır
    from app import create_app
    app = create_app()
    with app.app_context():
        islenen_gorsel_sayisi = islenmemis_haberleri_isle()
        print(f"Toplam {islenen_gorsel_sayisi} haber görseli işlendi.") 