import os

FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyAQXPTHj5d03-87vSd-v1B3HTL2yFEU-Mk")
FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "inventario-4c0fd.firebaseapp.com")
FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL", "https://inventario-4c0fd-default-rtdb.firebaseio.com/")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "inventario-4c0fd")

FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
FIREBASE_SERVICE_ACCOUNT_FILE = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE", "")

# Ruta dentro de la Realtime Database donde vive todo el estado de la app —
# la misma que usaba el SPA (DB_PATH="eventstock_v2" en js/operations.js).
DB_PATH = os.environ.get("DB_PATH", "eventstock_v2")

# Clave para firmar la cookie de sesión de FastAPI (SessionMiddleware).
# En producción SIEMPRE debe configurarse por variable de entorno.
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-me-in-production")

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Segundos que se reutiliza el estado leído de Firebase antes de volver a
# consultarlo (0 desactiva la caché). Todo guardado actualiza la caché.
STATE_CACHE_TTL = float(os.environ.get("STATE_CACHE_TTL", "10"))
