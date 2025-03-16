from PIL import Image

# Test görseli oluştur
img = Image.new('RGB', (1200, 675), color='blue')

# Görseli kaydet
img.save('test_simple.jpg', quality=95)

print("Test görseli başarıyla oluşturuldu ve kaydedildi: test_simple.jpg")




