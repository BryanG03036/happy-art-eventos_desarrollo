import copy
import json
import threading
import time

import firebase_admin
import httpx
from firebase_admin import credentials, db

from app import config

_lock = threading.Lock()
_app = None


class FirebaseAuthError(Exception):
    """Credenciales inválidas o error al verificar con Firebase Authentication."""


def _init_app():
    global _app
    if _app is not None:
        return _app
    with _lock:
        if _app is not None:
            return _app
        if config.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred_info = json.loads(config.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(cred_info)
        elif config.FIREBASE_SERVICE_ACCOUNT_FILE:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_FILE)
        else:
            raise RuntimeError(
                "Falta configurar la cuenta de servicio de Firebase. Define "
                "FIREBASE_SERVICE_ACCOUNT_JSON (contenido del JSON) o "
                "FIREBASE_SERVICE_ACCOUNT_FILE (ruta al archivo) como variable "
                "de entorno. Se genera desde la consola de Firebase: "
                "Configuración del proyecto → Cuentas de servicio → Generar "
                "nueva clave privada."
            )
        _app = firebase_admin.initialize_app(
            cred, {"databaseURL": config.FIREBASE_DATABASE_URL}
        )
        return _app


def get_root_ref():
    _init_app()
    return db.reference(config.DB_PATH)


_cache = {"estado": None, "ts": 0.0}
_cache_lock = threading.Lock()


def invalidar_cache() -> None:
    with _cache_lock:
        _cache["estado"] = None


def get_state() -> dict:
    ttl = config.STATE_CACHE_TTL
    with _cache_lock:
        vigente = (
            ttl > 0
            and _cache["estado"] is not None
            and time.monotonic() - _cache["ts"] < ttl
        )
        if vigente:
            return copy.deepcopy(_cache["estado"])
    estado = _leer_estado_remoto()
    with _cache_lock:
        _cache["estado"] = copy.deepcopy(estado)
        _cache["ts"] = time.monotonic()
    return estado


def _leer_estado_remoto() -> dict:
    raw = get_root_ref().get() or {}

    def as_list(key):
        val = raw.get(key)
        if val is None:
            return []
        if isinstance(val, dict):
            return list(val.values())
        return list(val)

    return {
        "productos": as_list("productos"),
        "movimientos": as_list("movimientos"),
        "prestamos": as_list("prestamos"),
        "contratos": as_list("contratos"),
        "personal": as_list("personal"),
        "encuestas": as_list("encuestas"),
        "contabAjustes": raw.get("contabAjustes") or {},
        "nextId": raw.get("nextId", 27),
        "nextMovId": raw.get("nextMovId", 17),
        "nextPrestId": raw.get("nextPrestId", 8),
        "nextContratoId": raw.get("nextContratoId", 1),
        "nextPersonalId": raw.get("nextPersonalId", 1),
        "nextEncuestaId": raw.get("nextEncuestaId", 1),
    }


def save_state(state: dict) -> None:
    
    try:
        get_root_ref().set(state)
    except Exception:
        invalidar_cache()
        raise
    with _cache_lock:
        _cache["estado"] = copy.deepcopy(state)
        _cache["ts"] = time.monotonic()


def sign_in_with_password(email: str, password: str) -> str:
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={config.FIREBASE_API_KEY}"
    )
    try:
        resp = httpx.post(
            url,
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise FirebaseAuthError("No se pudo contactar el servicio de autenticación.") from exc

    data = resp.json()
    if resp.status_code == 200:
        return data["idToken"]

    code = (data.get("error", {}) or {}).get("message", "")
    mensajes = {
        "EMAIL_NOT_FOUND": "Usuario no encontrado.",
        "INVALID_PASSWORD": "Contraseña incorrecta.",
        "INVALID_EMAIL": "Correo inválido.",
        "INVALID_LOGIN_CREDENTIALS": "Correo o contraseña incorrectos.",
        "USER_DISABLED": "Este usuario está deshabilitado.",
    }
    if code.startswith("TOO_MANY_ATTEMPTS_TRY_LATER"):
        raise FirebaseAuthError("Demasiados intentos. Espera un momento.")
    raise FirebaseAuthError(mensajes.get(code, "Error al iniciar sesión. Intenta de nuevo."))


def verify_id_token(id_token: str) -> dict:
    _init_app()
    from firebase_admin import auth as fb_auth

    return fb_auth.verify_id_token(id_token)
