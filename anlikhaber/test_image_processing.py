from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
from datetime import datetime

# Sabit değerler
HEDEF_GENISLIK = 1350
HEDEF_YUKSEKLIK = 1920
FONT_DOSYASI = os.path.join('static', 'fonts', 'Roboto-Bold.ttf')
ISLENMIS_GORSEL_KLASORU = os.path.join('static', 'images', 'processed')

# Klasörlerin var olduğundan emin ol
os.makedirs(os.path.dirname(FONT_DOSYASI), exist_ok=True)
os.makedirs(ISLENMIS_GORSEL_KLASORU, exist_ok=True)

def test_gorsel_isle():
    """Test görseli oluştur ve işle"""
    try:
        # Test görseli oluştur
        img = Image.new('RGB', (1200, 675), color='blue')
        
        # Görseli boyutlandır
        img_width, img_height = img.size
        
        # En-boy oranını koru
        if img_width / img_height > HEDEF_GENISLIK / HEDEF_YUKSEKLIK:
            # Genişlik sınırlayıcı
            yeni_genislik = HEDEF_GENISLIK
            yeni_yukseklik = int(img_height * (HEDEF_GENISLIK / img_width))
        else:
            # Yükseklik sınırlayıcı
            yeni_yukseklik = HEDEF_YUKSEKLIK
            yeni_genislik = int(img_width * (HEDEF_YUKSEKLIK / img_height))
        
        # Yeniden boyutlandır
        img = img.resize((yeni_genislik, yeni_yukseklik), Image.Resampling.LANCZOS)
        
        # Hedef boyutlarda boş bir görsel oluştur
        yeni_img = Image.new('RGB', (HEDEF_GENISLIK, HEDEF_YUKSEKLIK), (0, 0, 0))
        
        # Görseli ortala
        y_offset = (HEDEF_YUKSEKLIK - yeni_yukseklik) // 2
        x_offset = (HEDEF_GENISLIK - yeni_genislik) // 2
        
        # Görseli yerleştir
        yeni_img.paste(img, (x_offset, y_offset))
        
        # Metin eklemek için
        draw = ImageDraw.Draw(yeni_img)
        
        # Font yükle (eğer varsa)
        if os.path.exists(FONT_DOSYASI):
            # Başlık için font boyutu (görsel yüksekliğinin %5'i)
            baslik_font_boyutu = int(HEDEF_YUKSEKLIK * 0.05)
            baslik_font = ImageFont.truetype(FONT_DOSYASI, baslik_font_boyutu)
            
            # Kaynak için font boyutu (görsel yüksekliğinin %3'ü)
            kaynak_font_boyutu = int(HEDEF_YUKSEKLIK * 0.03)
            kaynak_font = ImageFont.truetype(FONT_DOSYASI, kaynak_font_boyutu)
        else:
            # Varsayılan font
            baslik_font = ImageFont.load_default()
            kaynak_font = ImageFont.load_default()
        
        # Test başlık
        baslik = "Test Başlık"
        
        # Başlığı satırlara böl (her satır maksimum 30 karakter)
        baslik_satirlari = textwrap.wrap(baslik, width=30)
        
        # Başlık için toplam yükseklik hesapla
        baslik_yukseklik = len(baslik_satirlari) * baslik_font_boyutu * 1.2
        
        # Başlığı görselin alt kısmına yerleştir
        y_pozisyon = HEDEF_YUKSEKLIK - baslik_yukseklik - 100  # Alt kenardan 100 piksel yukarı
        
        # Başlığı ekle
        for satir in baslik_satirlari:
            # Satır genişliğini hesapla
            satir_genislik = draw.textlength(satir, font=baslik_font)
            
            # Satırı ortala
            x_pozisyon = (HEDEF_GENISLIK - satir_genislik) / 2
            
            # Metin gölgesi (okunabilirlik için)
            draw.text((x_pozisyon+2, y_pozisyon+2), satir, font=baslik_font, fill=(0, 0, 0))
            
            # Asıl metin
            draw.text((x_pozisyon, y_pozisyon), satir, font=baslik_font, fill=(255, 255, 255))
            
            # Bir sonraki satır için y pozisyonunu güncelle
            y_pozisyon += baslik_font_boyutu * 1.2
        
        # Kaynak bilgisini ekle
        kaynak_metni = "Kaynak: Test"
        kaynak_genislik = draw.textlength(kaynak_metni, font=kaynak_font)
        
        # Kaynağı sağ alt köşeye yerleştir
        x_pozisyon = HEDEF_GENISLIK - kaynak_genislik - 20
        y_pozisyon = HEDEF_YUKSEKLIK - kaynak_font_boyutu - 20
        
        # Metin gölgesi
        draw.text((x_pozisyon+1, y_pozisyon+1), kaynak_metni, font=kaynak_font, fill=(0, 0, 0))
        
        # Asıl metin
        draw.text((x_pozisyon, y_pozisyon), kaynak_metni, font=kaynak_font, fill=(255, 255, 255))
        
        # Tarih bilgisini ekle
        tarih_metni = datetime.now().strftime("%d.%m.%Y")
        tarih_genislik = draw.textlength(tarih_metni, font=kaynak_font)
        
        # Tarihi sol alt köşeye yerleştir
        x_pozisyon = 20
        y_pozisyon = HEDEF_YUKSEKLIK - kaynak_font_boyutu - 20
        
        # Metin gölgesi
        draw.text((x_pozisyon+1, y_pozisyon+1), tarih_metni, font=kaynak_font, fill=(0, 0, 0))
        
        # Asıl metin
        draw.text((x_pozisyon, y_pozisyon), tarih_metni, font=kaynak_font, fill=(255, 255, 255))
        
        # Görseli kaydet
        dosya_yolu = os.path.join(ISLENMIS_GORSEL_KLASORU, 'test_processed.jpg')
        yeni_img.save(dosya_yolu, quality=95)
        
        print(f"Test görseli başarıyla işlendi ve kaydedildi: {dosya_yolu}")
        return dosya_yolu
    
    except Exception as e:
        print(f"Görsel işlenirken hata oluştu: {str(e)}")
        return None

if __name__ == "__main__":
    test_gorsel_isle()



