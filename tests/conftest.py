"""Fixtures compartidas de la suite de pruebas de EventStock.

- Todas las pruebas corren contra el Firebase en memoria (tests/fake_firebase.py),
  nunca contra el proyecto real.
- La fecha "de hoy" se congela en el miércoles 7 de octubre de 2026 a mediodía
  (hora de Bogotá), dentro del ciclo de pruebas del plan (4 al 10 de octubre),
  para que los cálculos de comisiones, quincenas y calendario sean
  reproducibles sin importar cuándo se ejecute la suite.
"""
import warnings

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from tests import fake_firebase

warnings.filterwarnings("ignore", category=DeprecationWarning, module="weasyprint")

_FAKE = fake_firebase.instalar()

from app.main import app  # noqa: E402

# 12:00 en Bogotá = 17:00 UTC
HOY_PRUEBAS = "2026-10-07 17:00:00"


@pytest.fixture(autouse=True)
def fecha_congelada():
    with freeze_time(HOY_PRUEBAS, tz_offset=-5):
        yield


@pytest.fixture
def fake():
    _FAKE.reiniciar()
    return _FAKE


@pytest.fixture
def login(fake):
    """login("admin" | "asesor" | "asesor2" | "bodega") -> TestClient con sesión."""
    def _login(rol):
        cliente = TestClient(app, raise_server_exceptions=False)
        r = cliente.post(
            "/login",
            data={"email": fake_firebase.USUARIOS[rol], "password": fake_firebase.PASSWORD_PRUEBA},
            follow_redirects=False,
        )
        assert r.status_code == 303, f"No se pudo iniciar sesión como {rol}"
        return cliente
    return _login


def flash(cliente, ruta="/"):
    """Devuelve (tipo, texto) del mensaje flash pendiente, leyendo una página."""
    import re

    r = cliente.get(ruta)
    m = re.search(r'alert alert-(\w+)[^>]*>(.*?)<button', r.text, re.S)
    return (m.group(1), m.group(2).strip()) if m else (None, None)
