import sys

print("Test başladı", flush=True)

try:
    from PIL import Image
    print("PIL import edildi", flush=True)
    
    # Basit bir görsel oluştur
    img = Image.new('RGB', (100, 100), color='blue')
    print("Görsel oluşturuldu", flush=True)
    
    # Görseli kaydet
    img.save('test3.jpg')
    print("Görsel kaydedildi: test3.jpg", flush=True)
    
except Exception as e:
    print(f"Hata oluştu: {str(e)}", flush=True)
    import traceback
    traceback.print_exc()

print("Test tamamlandı", flush=True) 