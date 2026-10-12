import io
import re

import openpyxl
import pytest

from app.models import PAQUETES
from tests.conftest import flash

ARTICULO_BASE = dict(nombre="Artículo de prueba", cat="Otros", evento="Ambos", precio="0", stock="1",
                     min="0", unidad="Unidad")


def _texto(html):
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# CP-01: login
@pytest.mark.parametrize("rol,destino", [
    ("admin", "/dashboard"), ("asesor", "/ventas"), ("bodega", "/inventario"),
])
def test_cp01_login_redirige_a_vista_del_rol(login, rol, destino):
    from fastapi.testclient import TestClient
    from app.main import app
    from tests import fake_firebase

    cliente = TestClient(app)
    r = cliente.post("/login", data={"email": fake_firebase.USUARIOS[rol], "password": "prueba123"},
                     follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == destino
    assert cliente.get(destino).status_code == 200


@pytest.mark.parametrize("rol,destino", [
    ("admin", "/dashboard"), ("asesor", "/ventas"), ("bodega", "/inventario"),
])
def test_cp01_con_sesion_abierta_la_raiz_lleva_a_la_vista_del_rol(login, rol, destino):
    cliente = login(rol)
    for ruta in ("/", "/login"):
        r = cliente.get(ruta)
        assert r.status_code == 200, f"{ruta} terminó en {r.status_code} para {rol}"
        assert str(r.url).endswith(destino)


def test_cp01_login_con_clave_incorrecta_se_rechaza(fake):
    from fastapi.testclient import TestClient
    from app.main import app

    r = TestClient(app).post("/login", data={"email": "admin@happyarteventos.com", "password": "mala"})
    assert r.status_code == 400
    assert "incorrectos" in r.text


# CP-02: acceso por rol
@pytest.mark.parametrize("ruta", ["/inventario", "/movimientos", "/prestamos", "/personal", "/dashboard", "/alertas"])
def test_cp02_asesor_recibe_403_fuera_de_su_rol(login, ruta):
    r = login("asesor").get(ruta, follow_redirects=False)
    assert r.status_code == 403


@pytest.mark.parametrize("ruta", ["/ventas", "/contratos", "/comisiones", "/personal", "/dashboard"])
def test_cp02_bodega_recibe_403_fuera_de_su_rol(login, ruta):
    assert login("bodega").get(ruta, follow_redirects=False).status_code == 403


@pytest.mark.parametrize("ruta", ["/contratos/1/pdf", "/contratos/descargar-fecha?fecha=2026-10-03"])
def test_cp02_bodega_no_descarga_contratos(login, ruta):
    r = login("bodega").get(ruta, follow_redirects=False)
    assert r.status_code == 403
    assert not r.content.startswith(b"%PDF") and not r.content.startswith(b"PK")


def test_cp02_asesor_no_descarga_pdf_de_contrato_ajeno(login):
    assert login("asesor").get("/contratos/2/pdf").status_code == 403


# CP-03: SKU duplicado
def test_cp03_crear_articulo_con_sku_duplicado_se_rechaza(login, fake):
    admin = login("admin")
    antes = len(fake.estado["productos"])
    admin.post("/inventario/nuevo", data={**ARTICULO_BASE, "sku": "TEA-01"}, follow_redirects=False)
    assert flash(admin, "/inventario") == ("danger", "Ese código ya existe")
    assert len(fake.estado["productos"]) == antes


@pytest.mark.parametrize("sku", ["tea-01", " Tea-01 "])
def test_cp03_sku_duplicado_sin_importar_mayusculas_ni_espacios(login, fake, sku):
    admin = login("admin")
    admin.post("/inventario/nuevo", data={**ARTICULO_BASE, "sku": sku}, follow_redirects=False)
    assert flash(admin, "/inventario") == ("danger", "Ese código ya existe")
    assert len(fake.estado["productos"]) == 13


def test_cp03_bodega_no_puede_dar_de_alta_articulos(login, fake):
    bodega = login("bodega")
    antes = len(fake.estado["productos"])
    bodega.post("/inventario/nuevo", data={**ARTICULO_BASE, "sku": "TEA-01"}, follow_redirects=False)
    assert flash(bodega, "/inventario")[0] == "danger"
    assert len(fake.estado["productos"]) == antes


# CP-04: stock insuficiente
@pytest.mark.parametrize("rol", ["admin", "bodega"])
def test_cp04_salida_mayor_al_stock_se_rechaza(login, fake, rol):
    cliente = login(rol)
    cliente.post("/movimientos/nuevo", data={"prodId": "1", "tipo": "salida", "qty": "5"}, follow_redirects=False)
    tipo, texto = flash(cliente, "/movimientos")
    assert tipo == "danger" and texto.startswith("Stock insuficiente")
    assert fake.estado["productos"][0]["stock"] == 2
    assert fake.estado["movimientos"] == []


# CP-05: préstamo
@pytest.mark.parametrize("rol", ["admin", "bodega"])
def test_cp05_wizard_de_prestamo_descuenta_stock_y_crea_movimiento(login, fake, rol):
    cliente = login(rol)
    assert cliente.post("/prestamos/wizard/seleccionar", data={"pkId": "happy_basica"},
                        follow_redirects=False).headers["location"] == "/prestamos/wizard/paso2"
    assert cliente.get("/prestamos/wizard/paso2").status_code == 200
    r = cliente.post("/prestamos/wizard/confirmar", data={
        "coordinador": "Felipe Coordinador", "cliente": "Familia Rojas", "retorno": "2026-10-10"},
        follow_redirects=False)
    assert r.headers["location"] == "/prestamos"
    st = fake.estado
    stock = {p["nombre"]: p["stock"] for p in st["productos"]}
    assert stock["TEATRINO"] == 1 and stock["TITERES"] == 9 and stock["CABINA DE SONIDO"] == 2
    assert len(st["prestamos"]) == 3
    assert {m["tipo"] for m in st["movimientos"]} == {"prestamo"}
    assert all(m["qty"] < 0 for m in st["movimientos"])


# CP-06: paquete personalizado
@pytest.mark.parametrize("rol", ["asesor", "admin"])
def test_cp06_contrato_paquete_personalizado(login, fake, rol):
    cliente = login(rol)
    r = cliente.post("/ventas/registrar", data={
        "empresa": "happy", "pkId": "paquete_personalizado", "currentPkId": "paquete_personalizado",
        "fecha": "2026-11-02", "hora": "15:00", "cliente": "Cliente Personalizado", "tel1": "3102112655",
        "valorPaquete": "450.000", "extra_prodId": ["1", "10"], "extra_qty": ["1", "20"],
    }, follow_redirects=False)
    assert r.headers["location"].startswith("/contratos?recien_creado=")
    c = fake.estado["contratos"][-1]
    assert c["paquete"] == "Paquete Personalizado"
    assert c["valor"] == 450000
    assert c["items"].count("SILLA PLASTICA") == 20 and "TEATRINO" in c["items"]


def test_cp06_personalizado_sin_valor_se_rechaza(login, fake):
    asesor = login("asesor")
    asesor.post("/ventas/registrar", data={
        "empresa": "happy", "pkId": "paquete_personalizado", "fecha": "2026-11-02",
        "cliente": "Sin valor", "tel1": "3102112655", "valorPaquete": ""}, follow_redirects=False)
    assert flash(asesor, "/contratos") == ("danger", "Ingresa el valor acordado para el paquete personalizado")
    assert len(fake.estado["contratos"]) == 5


# CP-07: transporte
@pytest.mark.parametrize("rol", ["asesor", "admin"])
def test_cp07_valor_total_es_paquete_mas_transporte(login, fake, rol):
    from app.models import valor_total_contrato

    pk = next(p for p in PAQUETES if p["id"] == "happy_basica")
    cliente = login(rol)
    cliente.post("/ventas/registrar", data={
        "empresa": "conde", "pkId": "happy_basica", "fecha": "2026-11-03", "cliente": "Cliente Transporte",
        "tel1": "3102112655", "valorPaquete": "179.000", "transporte": "60.000", "item_texto": pk["items"],
    }, follow_redirects=False)
    c = fake.estado["contratos"][-1]
    assert (c["valor"], c["transporte"]) == (179000, 60000)
    assert valor_total_contrato(c) == 239000  # 179.000 + 60.000
    assert "$239.000" in cliente.get("/contratos").text


# CP-08: editar contrato ajeno
def test_cp08_asesor_no_puede_editar_contrato_ajeno(login, fake):
    asesor = login("asesor")  # contrato 2 es de otro asesor
    r = asesor.get("/contratos/2/editar", follow_redirects=False)
    assert r.headers["location"] == "/contratos"
    asesor.post("/contratos/2/guardar", data={"fecha": "2026-10-21", "cliente": "Cambiado", "tel1": "3102112655"},
                follow_redirects=False)
    assert flash(asesor, "/contratos") == ("danger", "Solo el asesor que creó este contrato puede editarlo")
    asesor.post("/contratos/2/eliminar", follow_redirects=False)
    assert fake.estado["contratos"][1]["cliente"] == "Pedro Ruiz"
    assert len(fake.estado["contratos"]) == 5
    assert "/contratos/2/editar" not in asesor.get("/contratos").text


def test_cp08_asesor_titular_y_admin_si_pueden_editar(login):
    assert login("asesor").get("/contratos/1/editar").status_code == 200
    assert login("admin").get("/contratos/2/editar").status_code == 200


# CP-09: PDF
@pytest.mark.parametrize("rol,contrato_id", [
    ("admin", 1), ("admin", 2),  # Happy Art y Conde
    ("asesor", 1), ("asesor2", 2),  # contratos propios
])
def test_cp09_descarga_pdf_de_contrato(login, rol, contrato_id):
    r = login(rol).get(f"/contratos/{contrato_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def _capturar_html_pdf(monkeypatch):
    from app.services import pdf

    capturado = {}

    class HTMLFalso:
        def __init__(self, string):
            capturado["html"] = string

        def write_pdf(self):
            return b"%PDF-1.7 prueba"

    monkeypatch.setattr(pdf, "HTML", HTMLFalso)
    return capturado


def test_cp09_pdf_con_caracteres_especiales_en_el_cliente(login, fake):
    fake.estado["contratos"][0]["cliente"] = "Ana O’Neil Gómez"
    r = login("admin").get("/contratos/1/pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    disp = r.headers["content-disposition"]
    assert "filename*=UTF-8''CONTRATO%203%20DE%20OCTUBRE%20ANA%20O%E2%80%99NEIL%20G%C3%93MEZ.pdf" in disp


def test_cp09_pdf_de_conde_muestra_el_nombre_comercial_de_conde(login, monkeypatch):
    capturado = _capturar_html_pdf(monkeypatch)
    login("admin").get("/contratos/2/pdf")  # Conde Eventos
    pk = next(p for p in PAQUETES if p["nombre"] == "Happy Chiquiteka")
    texto = _texto(capturado["html"])
    assert f"Tipo de Paquete {pk['nombreConde']}" in texto
    assert f"Contenido del Paquete: {pk['nombreConde']}" in texto
    assert "Happy Chiquiteka" not in texto


# CP-10: personal no disponible
def test_cp10_persona_no_disponible_no_es_asignable(login, fake):
    admin = login("admin")
    asesor = login("asesor")
    admin.post("/personal/2/disponibilidad/agregar", data={"fecha": "2026-11-05"}, follow_redirects=False)
    assert "2026-11-05" in fake.estado["personal"][1]["noDisponible"]
    asesor.post("/ventas/registrar", data={"empresa": "happy", "pkId": "happy_day", "fecha": "2026-11-05",
                                            "cliente": "Evento CP10", "tel1": "3102112655", "pers_recreador": "2"})
    cid = fake.estado["contratos"][-1]["id"]
    html = admin.get(f"/contratos/{cid}/programar-personal").text
    assert re.search(r'name="sel__recreador" value="2"\s+disabled', html)  # no disponible
    assert "Marcado como no disponible esta fecha" in html
    admin.post(f"/contratos/{cid}/programar-personal", data={"sel__recreador": ["2", "3"]}, follow_redirects=False)
    assert fake.estado["contratos"][-1]["personalAsignado"]["recreador"] == []


def test_cp10_al_cambiar_la_fecha_no_queda_asignado_personal_no_disponible(login, fake):
    fake.estado["personal"][2]["noDisponible"] = ["2026-10-25"]
    asesor = login("asesor")
    asesor.post("/contratos/1/guardar", data={
        "fecha": "2026-10-25", "hora": "15:00", "cliente": "Laura Gómez", "tel1": "3102112655",
        "pers_logistico": "1", "pers_recreador": "1"}, follow_redirects=False)
    c = fake.estado["contratos"][0]
    assert c["fecha"] == "2026-10-25"
    assert 3 not in c["personalAsignado"]["recreador"]
    assert c["personalAsignado"]["logistico"] == [1]  # disponible


# CP-11: hora en bodega
@pytest.mark.parametrize("rol", ["admin", "asesor", "bodega"])
def test_cp11_hora_en_bodega_es_3h_antes_de_la_hora_mas_temprana(login, rol):
    # 1:00 PM - 3h = 10:00 AM
    html = login(rol).get("/calendario?anio=2026&mes=10&dia=2026-10-03").text
    assert re.search(r'text-nowrap">10:00 AM<', html)


def test_cp11_hora_en_bodega_calculos():
    from app.models import fmt_hora_bodega

    assert fmt_hora_bodega({"hora": "10:00", "horaDecoracion": ""}) == "7:00 AM"
    assert fmt_hora_bodega({"hora": "15:00", "horaDecoracion": "13:00"}) == "10:00 AM"
    assert fmt_hora_bodega({"hora": "02:00", "horaDecoracion": ""}) == "11:00 PM (día anterior)"


# CP-12: encuestas
def _excel_encuestas(filas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Id", "Nombre", "Teléfono o celular", "Fecha del evento",
               "¿Qué tan probable es que nos recomiende?", "¿Qué tan satisfecho quedó?",
               "¿Cómo califica el desempeño del coordinador?", "¿El equipo fue puntual?",
               "¿Qué haría diferente la próxima ocasión?", "¿Qué podemos mejorar?"])
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_cp12_carga_de_encuestas_se_refleja_en_la_tabla(login, fake):
    import datetime

    admin = login("admin")
    archivo = _excel_encuestas([
        [1, "Laura", "3102112655", datetime.datetime(2026, 10, 3), 10, 5, 5, 5, "", ""],
        [2, "Pedro", "3100000000", "2026-10-03", 8, 4, 4, 3, "", ""],
        [3, "Sofía", "3100000001", "27/09/2026", 9, 5, 4, 4, "", ""],
    ])
    admin.post("/dashboard/encuestas/cargar", files={"archivo": ("encuestas.xlsx", archivo)}, follow_redirects=False)
    assert flash(admin, "/dashboard") == ("success", "✅ 3 encuesta(s) importada(s)")
    texto = _texto(admin.get("/dashboard").text)
    # 3 oct: promedio 9.0 y 4.5
    assert "03 oct 2026 (Sábado) 2 9.0 4.5 4.5 4.0" in texto
    assert "27 sep 2026 (Domingo) 1 9.0 5.0 4.0 4.0" in texto


@pytest.mark.parametrize("fecha_texto", ["3/10/2026 14:30:22", "2026-10-03 14:30:00"])
def test_cp12_fechas_con_hora_no_rompen_el_dashboard(login, fake, fecha_texto):
    admin = login("admin")
    archivo = _excel_encuestas([[1, "Ana", "3102112655", fecha_texto, 10, 5, 5, 5, "", ""]])
    admin.post("/dashboard/encuestas/cargar", files={"archivo": ("e.xlsx", archivo)}, follow_redirects=False)
    assert fake.estado["encuestas"][0]["fecha"] == "2026-10-03"
    r = admin.get("/dashboard")
    assert r.status_code == 200
    assert "03 oct 2026 (Sábado) 1 10.0 5.0 5.0 5.0" in _texto(r.text)


# CP-13: alertas
@pytest.mark.parametrize("rol", ["admin", "bodega"])
def test_cp13_productos_bajo_minimo_aparecen_en_alertas(login, rol):
    html = login(rol).get("/alertas").text
    texto = _texto(html)
    assert "MAQUINA DE BURBUJAS" in texto and "MANTEL BLANCO" in texto and "MESA REDONDA" in texto
    assert "SILLA PLASTICA" not in texto and "TITERES" not in texto
    # Agotado rojo, bajo amarillo
    tarjetas = re.findall(r'<div class="card h-100 (border-\w+).*?<div class="fw-bold">([^<]+)<', html, re.S)
    colores = {nombre: borde for borde, nombre in tarjetas}
    assert colores["MAQUINA DE BURBUJAS"] == "border-danger"
    assert colores["MANTEL BLANCO"] == "border-warning"


# CP-14: comisión semanal
def test_cp14_comision_semanal_es_10_por_ciento_sin_transporte(login):
    texto = _texto(login("asesor").get("/comisiones").text)
    # 10% de 229.000
    assert re.search(r"Esta semana \$22\.900 1 evento", texto)
    assert "5 – 11 Oct 2026 esta semana" in texto


def test_cp14_comision_excluye_transporte(login):
    # Sin transporte: 29.000 + 39.500
    texto = _texto(login("asesor2").get("/comisiones").text)
    assert re.search(r"Esta semana \$68\.500 2 evento", texto)


# CP-15: ranking y quincenas
def test_cp15_ranking_ordenado_y_quincenas(login):
    texto = _texto(login("admin").get("/comisiones?mes=2026-10").text)
    i_ed, i_br, i_pa = texto.find("eduardv 2"), texto.find("brayang 2"), texto.find("paulal 0")
    assert -1 not in (i_ed, i_br, i_pa) and i_ed < i_br < i_pa  # orden por comisión
    assert "Del 1 al 14 · 1/2 realizados · 1 pendiente(s)" in texto
    assert "Del 15 al fin de mes · 0/2 realizados · 2 pendiente(s)" in texto
    assert "3 Oct Laura Gómez brayang $17.900 ✅ Realizado" in texto
    assert "14 Oct Marta Díaz brayang $22.900 ⏳ Pendiente" in texto
