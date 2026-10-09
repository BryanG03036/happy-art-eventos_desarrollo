import copy
import datetime as dt

from app import firebase

PASSWORD_PRUEBA = "prueba123"

USUARIOS = {
    "admin": "admin@happyarteventos.com",
    "asesor": "brayang@asesoreventos.com",
    "asesor2": "eduardv@asesoreventos.com",
    "bodega": "jennyer@happyarteventos.com",
}


# Colombia no tiene horario de verano: UTC-5 fijo.
BOGOTA = dt.timezone(dt.timedelta(hours=-5))


def _ms(y, m, d, h=10):
    return int(dt.datetime(y, m, d, h, 0, tzinfo=BOGOTA).timestamp() * 1000)


def _prod(id_, sku, nombre, cat, stock, minimo, precio=10000, unidad="Unidad"):
    return {
        "id": id_, "sku": sku, "nombre": nombre, "cat": cat, "evento": "Ambos",
        "precio": precio, "stock": stock, "min": minimo, "unidad": unidad,
        "proveedor": "Proveedor de prueba", "ubicacion": "Bodega 1", "desc": "",
    }


def _contrato(id_, empresa, asesor, fecha, valor, registro, transporte=0, paquete="Happy Básica",
              cliente="Cliente", hora="15:00", hora_deco="", req=None, asign=None, items=None,
              descontados=None, extras=None):
    return {
        "id": id_, "empresa": empresa, "fecha": fecha, "hora": hora, "horaDecoracion": hora_deco,
        "cliente": cliente, "tel1": "3102112655", "tel2": "", "direccion": "Calle 1 # 2-3",
        "barrio": "Centro", "localidad": "Suba", "festejado": "Ana", "paquete": paquete,
        "valor": valor, "transporte": transporte, "valorCatalogo": valor,
        "items": items or ["2 recreadores de alto nivel", "3 horas de animación"],
        "extras": extras or [], "descontadosPaquete": descontados or [],
        "fechaRegistro": registro, "asesor": asesor,
        "personalRequerido": req or {"logistico": 0, "recreador": 0, "coordinador": 0, "operario": 0},
        "personalAsignado": asign or {"logistico": [], "recreador": [], "coordinador": [], "operario": []},
    }


def estado_inicial():
    productos = [
        _prod(1, "TEA-01", "TEATRINO", "Decoración", 2, 1),
        _prod(2, "TIT-01", "TITERES", "Decoración", 10, 2),
        _prod(3, "SON-01", "CABINA DE SONIDO", "Audio / Video", 3, 1),
        _prod(4, "DISF-MICKEY", "DISFRAZ MICKEY", "Otros", 1, 0),
        _prod(5, "DISF-SPIDER", "DISFRAZ SPIDERMAN", "Otros", 1, 0),
        _prod(6, "GIG-STITCH", "PERSONAJE GIGANTE STITCH", "Otros", 1, 0),
        _prod(7, "LUMINOSA A", "LETRA LUMINOSA A", "Iluminación", 2, 0),
        _prod(8, "LUMINOSA N", "LETRA LUMINOSA N", "Iluminación", 1, 0),
        _prod(9, "LUMINOSO 5", "NUMERO LUMINOSO 5", "Iluminación", 1, 0),
        _prod(10, "SIL-01", "SILLA PLASTICA", "Mobiliario", 50, 20),
        _prod(11, "MAN-01", "MANTEL BLANCO", "Mobiliario", 3, 5),
        _prod(12, "BUR-01", "MAQUINA DE BURBUJAS", "Otros", 0, 1),
        _prod(13, "MES-01", "MESA REDONDA", "Mobiliario", 10, 10),
    ]
    personal = [
        {"id": 1, "nombre": "Ana Logística", "rol": "logistico", "edad": 25, "telefono": "3001112233",
         "cuentaTipo": "nequi", "cuentaNumero": "3001112233", "direccion": "", "noDisponible": [], "fechaRegistro": _ms(2026, 9, 1)},
        {"id": 2, "nombre": "Carlos Recreador", "rol": "recreador", "edad": 22, "telefono": "3002223344",
         "cuentaTipo": "nequi", "cuentaNumero": "", "direccion": "", "noDisponible": ["2026-10-20"], "fechaRegistro": _ms(2026, 9, 1)},
        {"id": 3, "nombre": "Diana Recreadora", "rol": "recreador", "edad": 24, "telefono": "3003334455",
         "cuentaTipo": "daviplata", "cuentaNumero": "", "direccion": "", "noDisponible": [], "fechaRegistro": _ms(2026, 9, 1)},
        {"id": 4, "nombre": "Felipe Coordinador", "rol": "coordinador", "edad": 30, "telefono": "3004445566",
         "cuentaTipo": "nequi", "cuentaNumero": "", "direccion": "", "noDisponible": [], "fechaRegistro": _ms(2026, 9, 1)},
        {"id": 5, "nombre": "Gloria Operaria", "rol": "operario", "edad": 28, "telefono": "",
         "cuentaTipo": "nequi", "cuentaNumero": "", "direccion": "", "noDisponible": [], "fechaRegistro": _ms(2026, 9, 1)},
        {"id": 6, "nombre": "Héctor Asesor", "rol": "asesor", "edad": 35, "telefono": "",
         "cuentaTipo": "nequi", "cuentaNumero": "", "direccion": "", "noDisponible": [], "fechaRegistro": _ms(2026, 9, 1)},
    ]
    contratos = [
        _contrato(1, "happy", "brayang@asesoreventos.com", "2026-10-03", 179000, _ms(2026, 9, 20),
                  cliente="Laura Gómez", hora="15:00", hora_deco="13:00",
                  req={"logistico": 1, "recreador": 1, "coordinador": 0, "operario": 0},
                  asign={"logistico": [1], "recreador": [3], "coordinador": [], "operario": []}),
        _contrato(2, "conde", "eduardv@asesoreventos.com", "2026-10-20", 290000, _ms(2026, 10, 6),
                  transporte=50000, paquete="Happy Chiquiteka", cliente="Pedro Ruiz", hora="16:00",
                  req={"logistico": 0, "recreador": 2, "coordinador": 0, "operario": 0}),
        _contrato(3, "happy", "brayang@asesoreventos.com", "2026-10-14", 229000, _ms(2026, 10, 5),
                  paquete="Happy Personaje", cliente="Marta Díaz", hora="10:00"),
        _contrato(4, "happy", "paulal@asesoreventos.com", "2026-09-12", 120000, _ms(2026, 9, 1),
                  paquete="Happy Day", cliente="Sofía Peña"),
        _contrato(5, "happy", "eduardv@asesoreventos.com", "2026-10-15", 395000, _ms(2026, 10, 7),
                  paquete="Pequeños Saltos", cliente="Jorge Mora", hora="14:00"),
    ]
    return {
        "productos": productos, "movimientos": [], "prestamos": [], "contratos": contratos,
        "personal": personal, "encuestas": [], "contabAjustes": {},
        "nextId": 14, "nextMovId": 1, "nextPrestId": 1, "nextContratoId": 6,
        "nextPersonalId": 7, "nextEncuestaId": 1,
    }


class FirebaseFalso:
    def __init__(self):
        self.estado = estado_inicial()

    def reiniciar(self):
        self.estado = estado_inicial()

    def get_state(self):
        return copy.deepcopy(self.estado)

    def save_state(self, state):
        self.estado = copy.deepcopy(state)

    @staticmethod
    def sign_in_with_password(email, password):
        if password != PASSWORD_PRUEBA:
            raise firebase.FirebaseAuthError("Correo o contraseña incorrectos.")
        return "token-falso::" + email

    @staticmethod
    def verify_id_token(token):
        return {"email": token.split("::", 1)[1]}


def instalar(fake=None):
    fake = fake or FirebaseFalso()
    firebase.get_state = fake.get_state
    firebase.save_state = fake.save_state
    firebase.sign_in_with_password = fake.sign_in_with_password
    firebase.verify_id_token = fake.verify_id_token
    return fake
