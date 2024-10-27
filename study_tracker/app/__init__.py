from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from app.models import UserSettings
        from app.utils import initialize_lessons
        db.create_all()
        initialize_lessons(db)

        if UserSettings.query.first() is None:
            user_settings = UserSettings()
            db.session.add(user_settings)
            db.session.commit()

    # Register blueprints and other setup
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
