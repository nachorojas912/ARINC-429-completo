import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "solo-desarrollo-cambiar-en-produccion")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///arinc429.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
