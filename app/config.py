import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.environ.get("MARKET_DB") or os.path.join(PROJECT_DIR, "data", "market.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

SECRET_KEY = "moamarket-dev-2024-secret"
SITE_NAME = "모아마켓"
ADMIN_BOOTSTRAP = {"username": "admin", "password": "admin123", "email": "admin@moamarket.co.kr"}
