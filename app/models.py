from datetime import datetime
from app import db

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False, default="General")
    title = db.Column(db.String(200), default="Unknown Feed")
    last_fetched = db.Column(db.DateTime, default=datetime.min)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'))
    title = db.Column(db.String(500))
    link = db.Column(db.String(500), unique=True) # Unique prevents duplicate articles
    summary = db.Column(db.Text)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)