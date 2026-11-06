from flask import Flask

from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from app import models  # noqa: F401
    from app.routes import main

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        with app.app_context():
            db.create_all()

    app.register_blueprint(main)
    return app
