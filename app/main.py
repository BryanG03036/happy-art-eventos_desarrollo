"""Punto de entrada de la aplicación FastAPI — reemplaza index.html + js/main.js
del SPA original. Arma el shell Jinja2/Bootstrap, monta los routers de cada
módulo y configura la sesión de servidor que sustituye a onAuthStateChanged."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.deps import get_current_user, pagina_inicio, templates
from app.routers import (
    alertas,
    auth,
    calendario,
    comisiones,
    contratos,
    dashboard,
    inventario,
    movimientos,
    personal,
    prestamos,
    ventas,
)

app = FastAPI(title="EventStock")

app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET_KEY)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(inventario.router)
app.include_router(calendario.router)
app.include_router(personal.router)
app.include_router(movimientos.router)
app.include_router(prestamos.router)
app.include_router(ventas.router)
app.include_router(contratos.router)
app.include_router(alertas.router)
app.include_router(comisiones.router)


@app.get("/")
def index(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    # Antes iba siempre a /dashboard, que es solo de admin: asesor y bodega
    # recibían 403 al abrir la app o al pulsar "Volver" en una página de error.
    return RedirectResponse(url=pagina_inicio(user))


@app.exception_handler(403)
def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse(
        request, "error.html", {"mensaje": str(exc.detail)}, status_code=403
    )


@app.exception_handler(Exception)
def error_inesperado_handler(request: Request, exc: Exception):
    import logging

    logging.getLogger("eventstock").error("Error inesperado en %s", request.url.path, exc_info=exc)
    return templates.TemplateResponse(
        request,
        "error.html",
        {"titulo": "Error inesperado", "mensaje": "Ocurrió un error inesperado. Intenta de nuevo en un momento; si persiste, avisa al administrador."},
        status_code=500,
    )
