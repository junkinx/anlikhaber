from app import app, db
from models import Haber

with app.app_context():
    haber = Haber.query.get(81)
    haber.gorsel_url = 'https://sozcu01.sozcucdn.com/sozcu/production/uploads/images/2025/3/287jpg-amWxtExKYECfZKc9VAno1g.jpg?w=776&h=436&mode=crop&scale=both'
    db.session.commit()
    print(f"Görsel URL güncellendi: {haber.gorsel_url}") 