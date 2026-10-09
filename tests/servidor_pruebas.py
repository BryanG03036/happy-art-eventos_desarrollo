"""Levanta EventStock con el Firebase en memoria de tests/fake_firebase.py,
para ejecutar los casos de prueba manuales en el navegador sin tocar datos
reales.

Uso (desde la raíz del proyecto):
    python -m tests.servidor_pruebas            # http://127.0.0.1:8000
    python -m tests.servidor_pruebas --port 8100

Credenciales: ver tests/fake_firebase.py (contraseña: prueba123).
"""
import argparse

import uvicorn

from tests import fake_firebase

_fake = fake_firebase.instalar()

from app.main import app  # noqa: E402  (importar después de instalar el fake)

@app.post("/__pruebas/reiniciar", include_in_schema=False)
def _reiniciar_datos():
    """Solo existe en el servidor de pruebas: vuelve a los datos iniciales
    para que cada caso arranque desde el mismo estado."""
    _fake.reiniciar()
    return {"ok": True}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
