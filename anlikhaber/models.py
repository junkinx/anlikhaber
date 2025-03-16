from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Haber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(255), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    ozet = db.Column(db.Text, nullable=True)
    kaynak = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False, unique=True)
    gorsel_url = db.Column(db.String(500), nullable=True)
    islenmis_gorsel_path = db.Column(db.String(500), nullable=True)
    orijinal_gorsel_path = db.Column(db.String(500), nullable=True)
    paylasildi = db.Column(db.Boolean, default=False)
    paylasima_hazir = db.Column(db.Boolean, default=False)
    paylasilma_zamani = db.Column(db.DateTime, nullable=True)
    instagram_post_id = db.Column(db.String(100), nullable=True)
    olusturulma_zamani = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Haber {self.baslik}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'baslik': self.baslik,
            'icerik': self.icerik,
            'ozet': self.ozet,
            'kaynak': self.kaynak,
            'url': self.url,
            'gorsel_url': self.gorsel_url,
            'islenmis_gorsel_path': self.islenmis_gorsel_path,
            'orijinal_gorsel_path': self.orijinal_gorsel_path,
            'paylasildi': self.paylasildi,
            'paylasima_hazir': self.paylasima_hazir,
            'paylasilma_zamani': self.paylasilma_zamani.isoformat() if self.paylasilma_zamani else None,
            'instagram_post_id': self.instagram_post_id,
            'olusturulma_zamani': self.olusturulma_zamani.isoformat()
        }

class Ayarlar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anahtar = db.Column(db.String(100), nullable=False, unique=True)
    deger = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Ayarlar {self.anahtar}>' 