"""Fecha y hora "de negocio" de EventStock: siempre en la zona horaria de
Colombia, sin importar dónde corra el servidor.

En Render (y en casi cualquier hosting) el servidor está en UTC: de 7:00
p. m. a medianoche, date.today() ya devuelve el día siguiente. Eso movía la
semana de las comisiones, marcaba como "realizados" eventos que aún no
pasaban, cambiaba el "hoy" del calendario y desplazaba las fechas de
retorno de los préstamos. Toda fecha de negocio debe salir de aquí.
"""
import datetime as _dt
from zoneinfo import ZoneInfo

from app import config

ZONA = ZoneInfo(config.TIMEZONE)


def ahora() -> _dt.datetime:
    return _dt.datetime.now(ZONA)


def hoy() -> _dt.date:
    return ahora().date()


def desde_ms(ms) -> _dt.datetime:
    """Timestamp en milisegundos (como se guarda en Firebase) -> hora de Colombia."""
    return _dt.datetime.fromtimestamp(ms / 1000, tz=ZONA)


def ms_de_fecha(fecha_iso: str) -> int:
    """'2026-10-10' -> timestamp en ms de esa fecha a las 00:00 en Colombia."""
    d = _dt.date.fromisoformat(fecha_iso)
    return int(_dt.datetime(d.year, d.month, d.day, tzinfo=ZONA).timestamp() * 1000)
