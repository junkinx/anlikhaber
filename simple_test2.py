from PIL import Image, ImageDraw, ImageFont
import os
import traceback

print("Script başladı")

try:
    print("Klasör oluşturuluyor...")
    os.makedirs('test_images', exist_ok=True)
    print("Klasör oluşturuldu")

    print("Görsel oluşturuluyor...")
    img = Image.new('RGB', (400, 300), color='red')
    print("Görsel oluşturuldu")
    
    print("Çizim yapılıyor...")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 250], outline='white', width=5)
    print("Çizim tamamlandı")
    
    print("Metin ekleniyor...")
    font = ImageFont.load_default()
    draw.text((150, 150), "Test", fill='white', font=font)
    print("Metin eklendi")
    
    print("Görsel kaydediliyor...")
    img.save('test_images/simple_test2.jpg', quality=95)
    print("Görsel kaydedildi: test_images/simple_test2.jpg")
    
    # Görseli yükle ve bilgilerini göster
    loaded_img = Image.open('test_images/simple_test2.jpg')
    print(f"Yüklenen görsel boyutu: {loaded_img.size}")
    print(f"Yüklenen görsel formatı: {loaded_img.format}")
    print(f"Yüklenen görsel modu: {loaded_img.mode}")
    
except Exception as e:
    print(f"Hata oluştu: {str(e)}")
    traceback.print_exc()

print("Script tamamlandı") 