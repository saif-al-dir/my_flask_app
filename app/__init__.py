from flask import Flask  # type: ignore[reportMissingImports]
from flask_sqlalchemy import SQLAlchemy  # type: ignore[reportMissingImports]

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_url_path='', static_folder='../public', template_folder='templates')
    
    # Configure SQLite Database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rss.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize DB
    db.init_app(app)

    # Register routes
    from app.routes import main
    app.register_blueprint(main)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app