import os

# Config pública del proyecto Firebase
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyAQXPTHj5d03-87vSd-v1B3HTL2yFEU-Mk")
FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "inventario-4c0fd.firebaseapp.com")
FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL", "https://inventario-4c0fd-default-rtdb.firebaseio.com/")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "inventario-4c0fd")

# Cuenta de servicio para el SDK de administrador de Firebase
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
FIREBASE_SERVICE_ACCOUNT_FILE = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE", "")


DB_PATH = os.environ.get("DB_PATH", "eventstock_v2")

SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-me-in-production")

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

TIMEZONE = os.environ.get("TIMEZONE", "America/Bogota")

STATE_CACHE_TTL = float(os.environ.get("STATE_CACHE_TTL", "10"))
