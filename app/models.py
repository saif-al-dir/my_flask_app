from datetime import datetime, timezone
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
    link = db.Column(db.String(500), unique=True)
    summary = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=True) # NEW: Store image URL
    is_read = db.Column(db.Boolean, default=False)       # NEW: Track if read
    published_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))