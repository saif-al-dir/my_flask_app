from app import db

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False, default="General")

    def __repr__(self):
        return f'<Feed {self.url}>'