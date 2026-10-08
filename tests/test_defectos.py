"""Pruebas de regresión de los defectos encontrados durante la ejecución del
plan (pruebas exploratorias alrededor de cada caso). Los defectos que caen
dentro del alcance literal de un caso CP-xx se prueban en
test_casos_prueba.py; aquí quedan los demás. Cada prueba lleva el ID del
defecto (DEF-xx) del registro de defectos."""
import re

import pytest
from freezegun import freeze_time

from app.models import PAQUETES
from tests.conftest import flash

ARTICULO = dict(nombre="TITERES", cat="Decoración", evento="Ambos", precio="0", stock="10", min="2", unidad="Unidad")


def _texto(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# DEF-04 · Disponibilidad por fecha ignora variantes y letras/números ───────
def test_def04_disponibilidad_cuenta_variantes_y_letras(login, fake):
    pk = next(p for p in PAQUETES if p["id"] == "happy_personaje")
    asesor = login("asesor")
    asesor.post("/ventas/registrar", data={
        "empresa": "happy", "pkId": "happy_personaje", "fecha": "2026-11-07", "cliente": "Familia Vargas",
        "tel1": "3102112655", "item_texto": pk["items"],
        "variante__Personaje gigante::disfraz_o_gigante::0": "4",  # DISFRAZ MICKEY (stock 1)
        "extra_prodId": ["8"], "extra_qty": ["1"],                  # LETRA LUMINOSA N (stock 1)
    }, follow_redirects=False)
    from app.services.calculos import calc_stock_separado_por_fecha

    separado, _ = calc_stock_separado_por_fecha(fake.estado["contratos"], fake.estado["productos"], "2026-11-07")
    assert separado.get(4) == 1, "El disfraz elegido como variante no quedó separado"
    assert separado.get(8) == 1, "La letra luminosa agregada no quedó separada"
    html = login("admin").get("/inventario?fecha=2026-11-07&q=DISFRAZ MICKEY").text
    assert "Agotado" in html


# DEF-06 · Editar contrato permite dejarlo sin fecha ─────────────────────────
@pytest.mark.parametrize("fecha", ["", "no-es-fecha"])
def test_def06_editar_contrato_exige_fecha_valida(login, fake, fecha):
    asesor = login("asesor")
    asesor.post("/contratos/1/guardar", data={"fecha": fecha, "cliente": "Laura Gómez", "tel1": "3102112655"},
                follow_redirects=False)
    assert fake.estado["contratos"][0]["fecha"] == "2026-10-03"
    assert flash(asesor, "/contratos/1/editar")[0] == "danger"


# DEF-08 · Editar artículo permite duplicar el SKU de otro ──────────────────
def test_def08_editar_articulo_con_sku_de_otro_se_rechaza(login, fake):
    admin = login("admin")
    admin.post("/inventario/2/editar", data={**ARTICULO, "sku": "TEA-01"}, follow_redirects=False)
    assert flash(admin, "/inventario") == ("danger", "Ese código ya existe")
    assert fake.estado["productos"][1]["sku"] == "TIT-01"


def test_def08_editar_articulo_conservando_su_propio_sku_funciona(login, fake):
    admin = login("admin")
    admin.post("/inventario/2/editar", data={**ARTICULO, "sku": "TIT-01", "stock": "12"}, follow_redirects=False)
    assert flash(admin, "/inventario")[0] == "success"
    assert fake.estado["productos"][1]["stock"] == 12


# DEF-10 · Tipo de movimiento no validado en el servidor ────────────────────
@pytest.mark.parametrize("tipo", ["prestamo", "devolucion", "regalo"])
def test_def10_tipo_de_movimiento_invalido_se_rechaza(login, fake, tipo):
    bodega = login("bodega")
    bodega.post("/movimientos/nuevo", data={"prodId": "2", "tipo": tipo, "qty": "5"}, follow_redirects=False)
    assert flash(bodega, "/movimientos")[0] == "danger"
    assert fake.estado["productos"][1]["stock"] == 10


# DEF-11 · El ajuste de inventario solo permite sumar ───────────────────────
def test_def11_ajuste_negativo_resta_stock(login, fake):
    bodega = login("bodega")
    bodega.post("/movimientos/nuevo", data={"prodId": "2", "tipo": "ajuste", "qty": "-3", "nota": "Conteo físico"},
                follow_redirects=False)
    assert fake.estado["productos"][1]["stock"] == 7
    assert fake.estado["movimientos"][-1]["qty"] == -3


def test_def11_ajuste_no_deja_stock_negativo(login, fake):
    bodega = login("bodega")
    bodega.post("/movimientos/nuevo", data={"prodId": "1", "tipo": "ajuste", "qty": "-5"}, follow_redirects=False)
    assert flash(bodega, "/movimientos")[1].startswith("Stock insuficiente")
    assert fake.estado["productos"][0]["stock"] == 2


# DEF-12 · Números no válidos producen error 500 ────────────────────────────
@pytest.mark.parametrize("ruta,datos,volver", [
    ("/movimientos/nuevo", {"prodId": "1", "tipo": "entrada", "qty": "1e2"}, "/movimientos"),
    ("/prestamos/nuevo", {"prodId": "1", "qty": "1e2", "cliente": "Prueba"}, "/prestamos"),
    ("/personal/nuevo", {"nombre": "Nueva Persona", "rol": "logistico", "edad": "2e1"}, "/personal"),
    ("/dashboard/contabilidad/ajuste", {"anio": "2026", "mes": "10", "happyV": "1.500.000"}, "/dashboard"),
])
def test_def12_numeros_no_validos_dan_mensaje_y_no_error_500(login, ruta, datos, volver):
    admin = login("admin")
    r = admin.post(ruta, data=datos, follow_redirects=False)
    assert r.status_code == 303, f"{ruta} respondió {r.status_code}"
    assert flash(admin, volver)[0] in ("danger", "success")


def test_def12_personal_por_evento_no_acepta_negativos(login, fake):
    asesor = login("asesor")
    asesor.post("/ventas/registrar", data={"empresa": "happy", "pkId": "happy_day", "fecha": "2026-11-20",
                                            "cliente": "Prueba", "tel1": "3102112655", "pers_recreador": "-2"},
                follow_redirects=False)
    assert len(fake.estado["contratos"]) == 5
    assert flash(asesor, "/contratos")[0] == "danger"


# DEF-14 · Calendario con mes fuera de rango produce error 500 ───────────────
@pytest.mark.parametrize("query", ["anio=2026&mes=13", "anio=2026&mes=-1", "anio=99999&mes=1"])
def test_def14_calendario_mes_fuera_de_rango(login, query):
    assert login("admin").get(f"/calendario?{query}").status_code == 200


# DEF-15 · Hora entre 12:00 y 12:59 AM se muestra como "0:xx AM" ───────────
def test_def15_formato_de_hora_medianoche():
    from app.models import fmt_hora, fmt_hora_evento

    assert fmt_hora("00:30") == "12:30 AM"
    assert fmt_hora("12:15") == "12:15 PM"
    assert fmt_hora_evento({"hora": "00:00"}) == "12:00 AM"


# DEF-16 · Fechas calculadas con la zona horaria del servidor (UTC en Render)
# freeze_time(..., tz_offset=0) simula un servidor configurado en UTC.
def test_def16_quincena_usa_hora_de_colombia(login):
    """13 oct 2026, 8:00 p. m. en Bogotá = 14 oct 01:00 UTC. El evento del 14
    de octubre (contrato 3) todavía NO se ha realizado."""
    with freeze_time("2026-10-14 01:00:00", tz_offset=0):
        texto = _texto(login("admin").get("/comisiones?mes=2026-10").text)
    assert "14 Oct Marta Díaz brayang $22.900 ⏳ Pendiente" in texto


def test_def16_semana_de_venta_usa_hora_de_colombia():
    """Venta registrada el domingo 11 oct a las 9:00 p. m. (Bogotá) pertenece
    a la semana del 5 al 11, aunque en UTC ya sea lunes 12."""
    import datetime as dt

    from app.models import fecha_venta_contrato

    ms = int(dt.datetime(2026, 10, 11, 21, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5))).timestamp() * 1000)
    with freeze_time("2026-10-12 03:00:00", tz_offset=0):
        assert fecha_venta_contrato({"fechaRegistro": ms}) == dt.date(2026, 10, 11)


# DEF-17 · PDF repite ítems iguales en líneas separadas ──────────────────────
def test_def17_pdf_agrupa_items_repetidos(login, fake, monkeypatch):
    from tests.test_casos_prueba import _capturar_html_pdf

    capturado = _capturar_html_pdf(monkeypatch)
    fake.estado["contratos"][0]["items"] = ["2 recreadores de alto nivel"] + ["SILLA PLASTICA"] * 20
    login("admin").get("/contratos/1/pdf")
    texto = _texto(capturado["html"])
    assert texto.count("SILLA PLASTICA") == 1
    assert "SILLA PLASTICA × 20" in texto


# DEF-18 · Alertas: el estado solo se distingue por color ───────────────────
def test_def18_alertas_muestran_etiqueta_de_estado(login):
    texto = _texto(login("bodega").get("/alertas").text)
    assert re.search(r"MAQUINA DE BURBUJAS .*?Agotado", texto)
    assert re.search(r"MANTEL BLANCO .*?Stock bajo", texto)


# DEF-19 · Comisiones usa la firma obsoleta de TemplateResponse ─────────────
def test_def19_comisiones_sin_advertencias_de_obsolescencia(login):
    import warnings

    asesor = login("asesor")
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        asesor.get("/comisiones")
    assert not [a for a in avisos if "TemplateResponse" in str(a.message)]
