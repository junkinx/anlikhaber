#!/usr/bin/env python
"""
Gereksiz görselleri temizleyen betik
"""

import os
import sqlite3
import glob
import shutil

# Klasör yolları
PROJE_KLASORU = os.path.dirname(os.path.abspath(__file__))
IMAGES_KLASORU = os.path.join(PROJE_KLASORU, 'anlikhaber', 'static', 'images')
PROCESSED_KLASORU = os.path.join(IMAGES_KLASORU, 'processed')
ORIGINAL_KLASORU = os.path.join(IMAGES_KLASORU, 'original')
TEMP_KLASORU = os.path.join(IMAGES_KLASORU, 'temp')
DATABASE_PATH = os.path.join(PROJE_KLASORU, 'anlikhaber', 'data', 'anlikhaber.db')
UNUSED_KLASORU = os.path.join(PROJE_KLASORU, 'backup', 'unused_images')

# Log dosyası
log_file = os.path.join(PROJE_KLASORU, 'cleanup_log.txt')

def log(message):
    """Log mesajını ekrana ve dosyaya yazar"""
    print(message)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def get_db_images():
    """Veritabanında kayıtlı görsellerin yollarını alır"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # İşlenmiş görsellerin yollarını al
    cursor.execute("SELECT islenmis_gorsel_path FROM haber WHERE islenmis_gorsel_path IS NOT NULL AND islenmis_gorsel_path != ''")
    processed_images = [os.path.basename(path[0]) if path[0] else None for path in cursor.fetchall()]
    processed_images = [p for p in processed_images if p]  # None değerleri temizle
    
    # Orijinal görsellerin yollarını al
    cursor.execute("SELECT orijinal_gorsel_path FROM haber WHERE orijinal_gorsel_path IS NOT NULL AND orijinal_gorsel_path != ''")
    original_images = [os.path.basename(path[0]) if path[0] else None for path in cursor.fetchall()]
    original_images = [p for p in original_images if p]  # None değerleri temizle
    
    conn.close()
    
    return processed_images, original_images

def cleanup_images():
    """Gereksiz görselleri temizler"""
    # Veritabanında referans edilen görselleri al
    processed_images_db, original_images_db = get_db_images()
    
    # Klasörleri oluştur
    os.makedirs(UNUSED_KLASORU, exist_ok=True)
    os.makedirs(os.path.join(UNUSED_KLASORU, 'processed'), exist_ok=True)
    os.makedirs(os.path.join(UNUSED_KLASORU, 'original'), exist_ok=True)
    
    # İşlenmiş görsel dosyalarını kontrol et
    processed_files = glob.glob(os.path.join(PROCESSED_KLASORU, '*.*'))
    unused_processed = []
    
    for file_path in processed_files:
        filename = os.path.basename(file_path)
        if filename == '.gitkeep':
            continue
        
        if filename not in processed_images_db:
            unused_processed.append(file_path)
    
    # Orijinal görsel dosyalarını kontrol et
    original_files = glob.glob(os.path.join(ORIGINAL_KLASORU, '*.*'))
    unused_original = []
    
    for file_path in original_files:
        filename = os.path.basename(file_path)
        if filename == '.gitkeep':
            continue
        
        if filename not in original_images_db:
            unused_original.append(file_path)
    
    # Gereksiz görselleri taşı
    for file_path in unused_processed:
        filename = os.path.basename(file_path)
        target_path = os.path.join(UNUSED_KLASORU, 'processed', filename)
        shutil.move(file_path, target_path)
        log(f"Taşındı: {file_path} -> {target_path}")
    
    for file_path in unused_original:
        filename = os.path.basename(file_path)
        target_path = os.path.join(UNUSED_KLASORU, 'original', filename)
        shutil.move(file_path, target_path)
        log(f"Taşındı: {file_path} -> {target_path}")
    
    # Temp klasörünü temizle
    if os.path.exists(TEMP_KLASORU):
        shutil.rmtree(TEMP_KLASORU)
        os.makedirs(TEMP_KLASORU, exist_ok=True)
        log(f"Temp klasörü temizlendi: {TEMP_KLASORU}")
    
    # Özet
    log(f"\nÖzet:")
    log(f"İşlenmiş görsellerin toplam sayısı: {len(processed_files)}")
    log(f"Veritabanında referans edilen işlenmiş görseller: {len(processed_images_db)}")
    log(f"Taşınan gereksiz işlenmiş görseller: {len(unused_processed)}")
    log(f"Orijinal görsellerin toplam sayısı: {len(original_files)}")
    log(f"Veritabanında referans edilen orijinal görseller: {len(original_images_db)}")
    log(f"Taşınan gereksiz orijinal görseller: {len(unused_original)}")

if __name__ == "__main__":
    log(f"Temizlik işlemi başlatılıyor...")
    cleanup_images()
    log(f"Temizlik işlemi tamamlandı.") 