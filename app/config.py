import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "solo-desarrollo-cambiar-en-produccion")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///arinc429.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
