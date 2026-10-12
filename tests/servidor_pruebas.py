# Servidor manual con datos de prueba: python -m tests.servidor_pruebas
import argparse

import uvicorn

from tests import fake_firebase

_fake = fake_firebase.instalar()

from app.main import app  # noqa: E402


@app.post("/__pruebas/reiniciar", include_in_schema=False)
def _reiniciar_datos():
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
