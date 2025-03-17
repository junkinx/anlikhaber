from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import os
import sys
import threading
from datetime import datetime
import copy

# Ana dizini ekleyelim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Haber
from scripts.image_processor import haber_gorselini_isle

haber_bp = Blueprint('haber', __name__)

# Görsel işleme işlemlerini takip etmek için global değişken
islenen_haberler = {}

def gorsel_isle_thread(app, haber_id, odak_x=None, odak_y=None):
    """Görsel işleme işlemini arka planda çalıştıran fonksiyon"""
    with app.app_context():
        try:
            islenen_haberler[haber_id] = "işleniyor"
            sonuc = haber_gorselini_isle(haber_id, odak_x, odak_y, force_reprocess=True)
            islenen_haberler[haber_id] = "tamamlandı" if sonuc else "hata"
        except Exception as e:
            app.logger.error(f"Görsel işleme hatası: {str(e)}")
            islenen_haberler[haber_id] = "hata"

@haber_bp.route('/<int:haber_id>')
def haber_detay(haber_id):
    haber = Haber.query.get_or_404(haber_id)
    return render_template('haber_detay.html', haber=haber, now=datetime.now())

@haber_bp.route('/isle/<int:haber_id>', methods=['POST'])
def haber_isle(haber_id):
    """Haberin görselini işler"""
    haber = Haber.query.get_or_404(haber_id)
    
    # Odak noktası parametrelerini al
    odak_x = request.form.get('odakX', type=float)
    odak_y = request.form.get('odakY', type=float)
    
    # Uygulama nesnesini al
    app = current_app._get_current_object()
    
    # Görsel işleme işlemini arka planda başlat
    thread = threading.Thread(target=gorsel_isle_thread, args=(app, haber_id, odak_x, odak_y))
    thread.daemon = True
    thread.start()
    
    # Hemen yanıt döndür
    return jsonify({
        'durum': 'başlatıldı',
        'mesaj': 'Görsel işleme başlatıldı. Lütfen bekleyin...'
    })

@haber_bp.route('/isle/durum/<int:haber_id>')
def haber_isle_durum(haber_id):
    """Haberin görsel işleme durumunu kontrol eder"""
    durum = islenen_haberler.get(haber_id, "bilinmiyor")
    
    if durum == "tamamlandı":
        # İşlem tamamlandıysa, haberi veritabanından tekrar al
        haber = Haber.query.get(haber_id)
        return jsonify({
            'durum': durum,
            'islenmis_gorsel_path': haber.islenmis_gorsel_path if haber else None
        })
    
    return jsonify({'durum': durum})

@haber_bp.route('/odakla/<int:haber_id>', methods=['POST'])
def haber_odakla(haber_id):
    """Haberin görselini odak noktasıyla işler"""
    haber = Haber.query.get_or_404(haber_id)
    
    # Odak noktası parametrelerini al
    odak_x = request.form.get('odakX', type=float)
    odak_y = request.form.get('odakY', type=float)
    
    # Uygulama nesnesini al
    app = current_app._get_current_object()
    
    # Görsel işleme işlemini arka planda başlat
    thread = threading.Thread(target=gorsel_isle_thread, args=(app, haber_id, odak_x, odak_y))
    thread.daemon = True
    thread.start()
    
    # Hemen yanıt döndür
    return jsonify({
        'durum': 'başlatıldı',
        'mesaj': 'Görsel odak noktasıyla işleme başlatıldı. Lütfen bekleyin...'
    })

@haber_bp.route('/listesi')
def haberler_listesi():
    """Tüm haberleri listeler"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    haberler = Haber.query.order_by(Haber.olusturulma_zamani.desc()).paginate(page=page, per_page=per_page)
    return render_template('haberler.html', haberler=haberler, now=datetime.now()) 