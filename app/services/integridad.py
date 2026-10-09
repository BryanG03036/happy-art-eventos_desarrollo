from app.models import ROLES_PERSONAL, esta_disponible, get_persona


def _asignaciones(contrato):
    asign = contrato.get("personalAsignado") or {}
    for rol in ROLES_PERSONAL:
        for pid in asign.get(rol["id"]) or []:
            yield rol["id"], pid


def verificar(state):
    problemas = []
    productos = state.get("productos") or []
    contratos = state.get("contratos") or []
    personal = state.get("personal") or []

    for p in productos:
        if (p.get("stock") or 0) < 0:
            problemas.append({"tipo": "stock", "mensaje": f"Stock negativo en {p.get('nombre')} ({p.get('stock')})"})

    por_fecha = {}
    for c in contratos:
        fecha = c.get("fecha")
        cliente = c.get("cliente") or f"contrato {c.get('id')}"
        req = c.get("personalRequerido") or {}
        asign = c.get("personalAsignado") or {}
        for rol in ROLES_PERSONAL:
            if len(asign.get(rol["id"]) or []) > int(req.get(rol["id"]) or 0):
                problemas.append({
                    "tipo": "personal",
                    "mensaje": f"{cliente}: hay más {rol['labelPlural'].lower()} asignados que los solicitados",
                })
        for _rol, pid in _asignaciones(c):
            persona = get_persona(personal, pid)
            if persona is None:
                problemas.append({"tipo": "personal", "mensaje": f"{cliente}: tiene asignada una persona que ya no existe (id {pid})"})
                continue
            if not esta_disponible(persona, fecha):
                problemas.append({"tipo": "disponibilidad", "mensaje": f"{persona['nombre']} está asignado a {cliente} el {fecha}, pero figura como no disponible"})
            por_fecha.setdefault((pid, fecha), []).append(cliente)

    for (pid, fecha), clientes in por_fecha.items():
        if len(clientes) > 1:
            persona = get_persona(personal, pid)
            nombre = persona["nombre"] if persona else f"id {pid}"
            problemas.append({"tipo": "disponibilidad", "mensaje": f"{nombre} está programado en {len(clientes)} eventos el {fecha}: {', '.join(clientes)}"})

    contadores = (
        ("nextId", productos, "productos"),
        ("nextContratoId", contratos, "contratos"),
        ("nextPersonalId", personal, "personal"),
    )
    for clave, lista, nombre in contadores:
        ids = [x.get("id") for x in lista if isinstance(x.get("id"), int)]
        if ids and state.get(clave, 0) <= max(ids):
            problemas.append({"tipo": "contador", "mensaje": f"El contador {clave} ({state.get(clave)}) no supera el id más alto de {nombre} ({max(ids)})"})

    return problemas
