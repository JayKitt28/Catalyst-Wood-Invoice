import os
from flask import Flask
from sqlalchemy import text

# Load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using system environment variables")

from routes import register_routes
from api import api_bp
from models import db


app = Flask(__name__, static_folder='static')

register_routes(app)
app.register_blueprint(api_bp)

# Database configuration for production
if os.environ.get('DATABASE_URL'):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')
else:
    db_path = os.path.join(os.path.dirname(__file__), "database.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

db.init_app(app)

with app.app_context():
    db.create_all()

    try:
        cols = db.session.execute(text("PRAGMA table_info('budget_items')")).all()
        has_sku = any((c[1] == "sku") for c in cols)
        if not has_sku:
            db.session.execute(text("ALTER TABLE budget_items ADD COLUMN sku VARCHAR(50) NOT NULL DEFAULT ''"))
            db.session.commit()
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host="0.0.0.0", port=port, debug=debug)