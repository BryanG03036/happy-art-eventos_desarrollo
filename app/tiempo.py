import datetime as _dt
from zoneinfo import ZoneInfo

from app import config

ZONA = ZoneInfo(config.TIMEZONE)


def ahora() -> _dt.datetime:
    return _dt.datetime.now(ZONA)


def hoy() -> _dt.date:
    return ahora().date()


def desde_ms(ms) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(ms / 1000, tz=ZONA)


def ms_de_fecha(fecha_iso: str) -> int:
    d = _dt.date.fromisoformat(fecha_iso)
    return int(_dt.datetime(d.year, d.month, d.day, tzinfo=ZONA).timestamp() * 1000)
