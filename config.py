import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Seeded on first run if no Super Admin exists yet.
    DEFAULT_SUPER_ADMIN_USERNAME = os.environ.get("SUPER_ADMIN_USERNAME", "admin")
    DEFAULT_SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "admin123ankita987898098")
    DEFAULT_SUPER_ADMIN_NAME = "Super Admin"
    DEFAULT_SUPER_ADMIN_EMAIL = "admin@example.com"

    QR_CODE_PATH = os.path.join(BASE_DIR, "static", "qr_code.png")
    DEFAULT_PRICE_PER_SESSION = 500.0
