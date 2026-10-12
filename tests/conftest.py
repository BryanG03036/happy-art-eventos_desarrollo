# Fixtures de la suite: Firebase en memoria y reloj fijo.
import warnings

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from tests import fake_firebase

warnings.filterwarnings("ignore", category=DeprecationWarning, module="weasyprint")

_FAKE = fake_firebase.instalar()

from app.main import app  # noqa: E402

# 12:00 Bogotá
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
    import re

    r = cliente.get(ruta)
    m = re.search(r'alert alert-(\w+)[^>]*>(.*?)<button', r.text, re.S)
    return (m.group(1), m.group(2).strip()) if m else (None, None)
