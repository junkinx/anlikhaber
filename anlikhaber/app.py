import os
import logging
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import threading
from datetime import datetime

# .env dosyasını yükle
load_dotenv()

# Modelleri içe aktar
from models import db, Haber, Ayarlar

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Scheduler thread'i
scheduler_thread = None

def create_app():
    """Flask uygulamasını oluşturur ve yapılandırır"""
    app = Flask(__name__)
    
    # Uygulama yapılandırması
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli-anahtar-degistir')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'anlikhaber.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Veritabanını başlat
    db.init_app(app)
    
    # Klasörlerin var olduğundan emin ol
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'processed'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts'), exist_ok=True)
    
    # Veritabanını oluştur
    with app.app_context():
        db.create_all()
        
        # Varsayılan ayarları oluştur
        varsayilan_ayarlar = {
            'otomatik_paylasim_aktif': 'false',
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'pexels_api_key': os.getenv('PEXELS_API_KEY', ''),
            'instagram_username': os.getenv('INSTAGRAM_USERNAME', ''),
            'instagram_password': os.getenv('INSTAGRAM_PASSWORD', ''),
            'check_interval': os.getenv('CHECK_INTERVAL', '600'),
            'max_posts_per_day': os.getenv('MAX_POSTS_PER_DAY', '5'),
            'default_hashtags': os.getenv('DEFAULT_HASHTAGS', '#haber #gündem #sondakika #türkiye #güncel'),
            'blocked_keywords': os.getenv('BLOCKED_KEYWORDS', '')
        }
        
        for anahtar, deger in varsayilan_ayarlar.items():
            ayar = Ayarlar.query.filter_by(anahtar=anahtar).first()
            if not ayar:
                ayar = Ayarlar(anahtar=anahtar, deger=deger)
                db.session.add(ayar)
        
        db.session.commit()
    
    # Ana sayfa
    @app.route('/')
    def index():
        # Otomatik paylaşım durumunu al
        otomatik_paylasim = Ayarlar.query.filter_by(anahtar='otomatik_paylasim_aktif').first()
        otomatik_paylasim_aktif = otomatik_paylasim and otomatik_paylasim.deger.lower() in ['true', 'evet', '1', 'on']
        
        return render_template('index.html', otomatik_paylasim_aktif=otomatik_paylasim_aktif, now=datetime.now())
    
    # Haberler sayfası
    @app.route('/haberler')
    def haberler():
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        haberler = Haber.query.order_by(Haber.olusturulma_zamani.desc()).paginate(page=page, per_page=per_page)
        
        return render_template('haberler.html', haberler=haberler, now=datetime.now())
    
    # Haber detay sayfası
    @app.route('/haber/<int:haber_id>')
    def haber_detay(haber_id):
        haber = Haber.query.get_or_404(haber_id)
        return render_template('haber_detay.html', haber=haber, now=datetime.now())
    
    # Haberleri çek
    @app.route('/haberleri-cek', methods=['POST'])
    def haberleri_cek():
        try:
            from scripts.rss_reader import haberleri_cek as cek
            
            # Arka planda çalıştır
            def arka_planda_cek():
                with app.app_context():
                    yeni_haber_sayisi = cek()
                    logger.info(f"Toplam {yeni_haber_sayisi} yeni haber eklendi.")
            
            thread = threading.Thread(target=arka_planda_cek)
            thread.daemon = True
            thread.start()
            
            flash('Haberler çekiliyor...', 'info')
            return redirect(url_for('haberler'))
        
        except Exception as e:
            logger.error(f"Haberler çekilirken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haberler'))
    
    # Haberi özetle
    @app.route('/haber-ozetle/<int:haber_id>', methods=['POST'])
    def haber_ozetle(haber_id):
        try:
            from scripts.ai_summarizer import haber_ozetle
            
            haber = Haber.query.get_or_404(haber_id)
            
            # Arka planda çalıştır
            def arka_planda_ozetle(haber):
                with app.app_context():
                    ozet = haber_ozetle(haber.icerik, haber.baslik)
                    haber.ozet = ozet
                    db.session.commit()
                    logger.info(f"Haber özetlendi: {haber.baslik}")
            
            thread = threading.Thread(target=arka_planda_ozetle, args=(haber,))
            thread.daemon = True
            thread.start()
            
            flash('Haber özetleniyor...', 'info')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        
        except Exception as e:
            logger.error(f"Haber özetlenirken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haber görseli bul
    @app.route('/haber-gorsel-bul/<int:haber_id>', methods=['POST'])
    def haber_gorsel_bul(haber_id):
        try:
            from scripts.image_finder import gorsel_url_kontrol_et
            
            # Arka planda çalıştır
            def arka_planda_gorsel_bul(haber_id):
                with app.app_context():
                    sonuc = gorsel_url_kontrol_et(haber_id)
                    logger.info(f"Haber için görsel bulma sonucu: {sonuc}")
            
            thread = threading.Thread(target=arka_planda_gorsel_bul, args=(haber_id,))
            thread.daemon = True
            thread.start()
            
            flash('Haber için görsel aranıyor...', 'info')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        
        except Exception as e:
            logger.error(f"Haber görseli bulunurken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haber görselini işle
    @app.route('/haber-gorsel-isle/<int:haber_id>', methods=['POST'])
    def haber_gorselini_isle(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            if not haber.gorsel_url:
                flash('Haberin görseli bulunmuyor', 'warning')
                return redirect(url_for('haber_detay', haber_id=haber_id))
            
            if not haber:
                flash('Haber bulunamadı', 'danger')
                return redirect(url_for('haberler'))
            
            def arka_planda_gorsel_isle(haber_id):
                from scripts.image_processor import haber_gorselini_isle
                with app.app_context():
                    islenmis_gorsel_path = haber_gorselini_isle(haber_id)
                    if islenmis_gorsel_path:
                        logger.info(f"Haber görseli işleme sonucu: {islenmis_gorsel_path}")
                    else:
                        logger.error(f"Haber görseli işlenemedi: ID {haber_id}")
            
            thread = threading.Thread(target=arka_planda_gorsel_isle, args=(haber_id,))
            thread.daemon = True
            thread.start()
            
            flash('Haber görseli işleniyor...', 'info')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        except Exception as e:
            logger.error(f"Haber görseli işlenirken hata oluştu: {str(e)}")
            flash(f'Haber görseli işlenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haber görselini odak noktası ile işle (AJAX)
    @app.route('/haber-gorselini-odakla/<int:haber_id>', methods=['POST'])
    def haber_gorselini_odakla(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            if not haber.gorsel_url and not haber.orijinal_gorsel_path:
                return jsonify({
                    'success': False,
                    'message': 'Haberin görseli bulunmuyor'
                }), 400
            
            # Odak noktası değerlerini al
            odak_x = request.form.get('odakX', 0.5, type=float)
            odak_y = request.form.get('odakY', 0.5, type=float)
            
            # Değerleri 0-1 aralığında sınırla
            odak_x = max(0, min(1, odak_x))
            odak_y = max(0, min(1, odak_y))
            
            logger.info(f"Haber ID {haber_id} için odak noktası ayarlanıyor: X={odak_x}, Y={odak_y}")
            
            def arka_planda_gorsel_odakla(haber_id, odak_x, odak_y):
                from scripts.image_processor import haber_gorselini_isle
                with app.app_context():
                    islenmis_gorsel_path = haber_gorselini_isle(haber_id, odak_x=odak_x, odak_y=odak_y, force_reprocess=True)
                    if islenmis_gorsel_path:
                        logger.info(f"Haber görseli odak noktası ile işleme sonucu: {islenmis_gorsel_path}")
                    else:
                        logger.error(f"Haber görseli odak noktası ile işlenemedi: ID {haber_id}")
            
            thread = threading.Thread(target=arka_planda_gorsel_odakla, args=(haber_id, odak_x, odak_y))
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'message': 'Görsel işleniyor...'
            })
            
        except Exception as e:
            logger.error(f"Haber görseli odak noktası ile işlenirken hata oluştu: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Hata: {str(e)}'
            }), 500
    
    # Haber görselini yeniden işle
    @app.route('/haber-gorselini-yeniden-isle/<int:haber_id>', methods=['POST'])
    def haber_gorselini_yeniden_isle(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            if not haber.gorsel_url:
                flash('Haberin görseli bulunmuyor', 'warning')
                return redirect(url_for('haber_detay', haber_id=haber_id))
            
            # Odak noktası değerlerini al
            odak_x = request.form.get('odakX', 0.5, type=float)
            odak_y = request.form.get('odakY', 0.5, type=float)
            
            # Değerleri 0-1 aralığında sınırla
            odak_x = max(0, min(1, odak_x))
            odak_y = max(0, min(1, odak_y))
            
            def arka_planda_gorsel_yeniden_isle(haber_id, odak_x, odak_y):
                from scripts.image_processor import haber_gorselini_isle
                with app.app_context():
                    islenmis_gorsel_path = haber_gorselini_isle(haber_id, odak_x=odak_x, odak_y=odak_y, force_reprocess=True)
                    if islenmis_gorsel_path:
                        logger.info(f"Haber görseli yeniden işleme sonucu: {islenmis_gorsel_path}")
                    else:
                        logger.error(f"Haber görseli yeniden işlenemedi: ID {haber_id}")
            
            thread = threading.Thread(target=arka_planda_gorsel_yeniden_isle, args=(haber_id, odak_x, odak_y))
            thread.daemon = True
            thread.start()
            
            flash('Haber görseli yeniden işleniyor...', 'info')
            return redirect(url_for('haber_detay', haber_id=haber_id))
            
        except Exception as e:
            logger.error(f"Haber görseli yeniden işlenirken hata oluştu: {str(e)}")
            flash(f'Haber görseli yeniden işlenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haberi paylaşıma hazır olarak işaretle
    @app.route('/haber-paylasima-hazirla/<int:haber_id>', methods=['POST'])
    def haber_paylasima_hazirla(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            if not haber.islenmis_gorsel_path or not haber.ozet:
                flash('Haber paylaşıma hazır değil. Önce özet ve görsel ekleyin.', 'warning')
                return redirect(url_for('haber_detay', haber_id=haber_id))
            
            haber.paylasima_hazir = True
            db.session.commit()
            
            flash('Haber paylaşıma hazır olarak işaretlendi.', 'success')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        
        except Exception as e:
            logger.error(f"Haber paylaşıma hazırlanırken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haberi paylaşıma hazır olmaktan çıkar
    @app.route('/haber-paylasima-hazir-iptal/<int:haber_id>', methods=['POST'])
    def haber_paylasima_hazir_iptal(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            if haber.paylasildi:
                flash('Haber zaten paylaşıldı, paylaşıma hazır durumu değiştirilemez.', 'warning')
                return redirect(url_for('haber_detay', haber_id=haber_id))
            
            haber.paylasima_hazir = False
            db.session.commit()
            
            flash('Haber paylaşıma hazır durumundan çıkarıldı.', 'success')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        
        except Exception as e:
            logger.error(f"Haber paylaşıma hazır durumu iptal edilirken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haberi sil
    @app.route('/haber-sil/<int:haber_id>', methods=['POST'])
    def haber_sil(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            
            # İşlenmiş görsel varsa sil
            if haber.islenmis_gorsel_path:
                islenmis_gorsel_dosyasi = os.path.join(os.path.dirname(os.path.abspath(__file__)), haber.islenmis_gorsel_path.lstrip('/'))
                if os.path.exists(islenmis_gorsel_dosyasi):
                    os.remove(islenmis_gorsel_dosyasi)
                    logger.info(f"İşlenmiş görsel silindi: {islenmis_gorsel_dosyasi}")
            
            # Orijinal görsel varsa sil
            if haber.orijinal_gorsel_path:
                orijinal_gorsel_dosyasi = os.path.join(os.path.dirname(os.path.abspath(__file__)), haber.orijinal_gorsel_path.lstrip('/'))
                if os.path.exists(orijinal_gorsel_dosyasi):
                    os.remove(orijinal_gorsel_dosyasi)
                    logger.info(f"Orijinal görsel silindi: {orijinal_gorsel_dosyasi}")
            
            # Haberi veritabanından sil
            db.session.delete(haber)
            db.session.commit()
            
            flash('Haber başarıyla silindi.', 'success')
            return redirect(url_for('haberler'))
        
        except Exception as e:
            logger.error(f"Haber silinirken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Haberi Instagram'da paylaş
    @app.route('/haber-paylas/<int:haber_id>', methods=['POST'])
    def haber_paylas(haber_id):
        try:
            from scripts.instagram_poster import haber_paylas
            
            # Arka planda çalıştır
            def arka_planda_paylas(haber_id):
                with app.app_context():
                    sonuc = haber_paylas(haber_id)
                    logger.info(f"Haber paylaşım sonucu: {sonuc}")
            
            thread = threading.Thread(target=arka_planda_paylas, args=(haber_id,))
            thread.daemon = True
            thread.start()
            
            flash('Haber Instagram\'da paylaşılıyor...', 'info')
            return redirect(url_for('haber_detay', haber_id=haber_id))
        
        except Exception as e:
            logger.error(f"Haber paylaşılırken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('haber_detay', haber_id=haber_id))
    
    # Otomatik paylaşımı aç/kapat
    @app.route('/otomatik-paylasim-durum', methods=['POST'])
    def otomatik_paylasim_durum():
        try:
            durum = request.form.get('durum', 'false')
            
            ayar = Ayarlar.query.filter_by(anahtar='otomatik_paylasim_aktif').first()
            
            if ayar:
                ayar.deger = durum
            else:
                ayar = Ayarlar(anahtar='otomatik_paylasim_aktif', deger=durum)
                db.session.add(ayar)
            
            db.session.commit()
            
            if durum.lower() in ['true', 'evet', '1', 'on']:
                flash('Otomatik paylaşım aktifleştirildi.', 'success')
            else:
                flash('Otomatik paylaşım devre dışı bırakıldı.', 'success')
            
            return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Otomatik paylaşım durumu değiştirilirken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Scheduler'ı başlat
    @app.route('/scheduler-baslat', methods=['POST'])
    def scheduler_baslat():
        global scheduler_thread
        
        try:
            # Eğer zaten çalışıyorsa, durdur
            if scheduler_thread and scheduler_thread.is_alive():
                flash('Scheduler zaten çalışıyor.', 'warning')
                return redirect(url_for('index'))
            
            # Arka planda çalıştır
            def arka_planda_scheduler():
                from scripts.scheduler import scheduler_baslat as baslat
                scheduler = baslat()
                
                if scheduler:
                    try:
                        # Ana thread'i canlı tut
                        while True:
                            time.sleep(1)
                    
                    except (KeyboardInterrupt, SystemExit):
                        # Scheduler'ı durdur
                        scheduler.shutdown()
                        logger.info("Scheduler durduruldu.")
            
            scheduler_thread = threading.Thread(target=arka_planda_scheduler)
            scheduler_thread.daemon = True
            scheduler_thread.start()
            
            flash('Scheduler başlatıldı.', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Scheduler başlatılırken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Tüm işlem pipeline'ını çalıştır
    @app.route('/pipeline-calistir', methods=['POST'])
    def pipeline_calistir():
        try:
            from scripts.scheduler import haber_islem_pipeline
            
            # Arka planda çalıştır
            def arka_planda_pipeline():
                with app.app_context():
                    haber_islem_pipeline()
                    logger.info("Haber işleme pipeline'ı tamamlandı.")
            
            thread = threading.Thread(target=arka_planda_pipeline)
            thread.daemon = True
            thread.start()
            
            flash('Haber işleme pipeline\'ı çalıştırılıyor...', 'info')
            return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Pipeline çalıştırılırken hata oluştu: {str(e)}")
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Ayarlar sayfası
    @app.route('/ayarlar', methods=['GET', 'POST'])
    def ayarlar():
        if request.method == 'POST':
            try:
                # Ayarları güncelle
                for key, value in request.form.items():
                    if key.startswith('ayar_'):
                        ayar_key = key[5:]  # "ayar_" önekini kaldır
                        
                        # Ayarı veritabanında bul veya oluştur
                        ayar = Ayarlar.query.filter_by(anahtar=ayar_key).first()
                        
                        if ayar:
                            ayar.deger = value
                        else:
                            ayar = Ayarlar(anahtar=ayar_key, deger=value)
                            db.session.add(ayar)
                
                db.session.commit()
                
                # .env dosyasındaki değerleri güncelle
                env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                
                # Mevcut .env dosyasını oku
                env_lines = []
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        env_lines = f.readlines()
                
                # Güncellenecek değerleri belirle
                env_updates = {
                    'OPENAI_API_KEY': request.form.get('ayar_openai_api_key', ''),
                    'PEXELS_API_KEY': request.form.get('ayar_pexels_api_key', ''),
                    'INSTAGRAM_USERNAME': request.form.get('ayar_instagram_username', ''),
                    'INSTAGRAM_PASSWORD': request.form.get('ayar_instagram_password', ''),
                    'CHECK_INTERVAL': request.form.get('ayar_check_interval', '600'),
                    'MAX_POSTS_PER_DAY': request.form.get('ayar_max_posts_per_day', '5'),
                    'DEFAULT_HASHTAGS': request.form.get('ayar_default_hashtags', ''),
                    'BLOCKED_KEYWORDS': request.form.get('ayar_blocked_keywords', '')
                }
                
                # .env dosyasını güncelle
                updated_env = {}
                for line in env_lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        updated_env[key.strip()] = value.strip()
                
                # Yeni değerleri ekle/güncelle
                updated_env.update(env_updates)
                
                # .env dosyasını yeniden yaz
                with open(env_file, 'w') as f:
                    for key, value in updated_env.items():
                        f.write(f"{key}={value}\n")
                
                flash('Ayarlar başarıyla güncellendi.', 'success')
            
            except Exception as e:
                logger.error(f"Ayarlar güncellenirken hata oluştu: {str(e)}")
                flash(f'Hata: {str(e)}', 'danger')
        
        # Ayarları getir
        ayarlar_dict = {}
        for ayar in Ayarlar.query.all():
            ayarlar_dict[ayar.anahtar] = ayar.deger
        
        return render_template('ayarlar.html', ayarlar=ayarlar_dict, now=datetime.now())
    
    # API: Haberleri JSON olarak al
    @app.route('/api/haberler')
    def api_haberler():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # per_page=0 durumunu kontrol et
            if per_page <= 0:
                return jsonify({
                    'haberler': [],
                    'toplam': 0,
                    'sayfa': 1,
                    'toplam_sayfa': 0
                })
            
            haberler = Haber.query.order_by(Haber.olusturulma_zamani.desc()).paginate(page=page, per_page=per_page)
            
            return jsonify({
                'haberler': [haber.to_dict() for haber in haberler.items],
                'toplam': haberler.total,
                'sayfa': haberler.page,
                'toplam_sayfa': haberler.pages
            })
        
        except Exception as e:
            logger.error(f"API haberler alınırken hata oluştu: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # API: Haber detayını JSON olarak al
    @app.route('/api/haber/<int:haber_id>')
    def api_haber_detay(haber_id):
        try:
            haber = Haber.query.get_or_404(haber_id)
            return jsonify(haber.to_dict())
        
        except Exception as e:
            logger.error(f"API haber detayı alınırken hata oluştu: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8080, host='0.0.0.0') 