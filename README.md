# EventStock — FastAPI + Jinja2 + Bootstrap

Sistema de inventario, ventas/contratos y gestión de personal para Happy Art
Eventos / Conde Eventos.

Esta es la versión reconstruida en **FastAPI** (backend Python) + **Jinja2**
(plantillas renderizadas en el servidor) + **Bootstrap 5** (frontend), que
reemplaza a la SPA original en JavaScript/Firebase (conservada en
[`legacy/`](legacy/) como referencia). La funcionalidad es la misma; lo que
cambia es la arquitectura:

- **Antes**: SPA 100% en el navegador, un único `state` en memoria
  sincronizado en vivo con Firebase Realtime Database (`onValue`).
- **Ahora**: cada página se renderiza en el servidor. Cada request lee el
  estado completo desde Firebase (`firebase.get_state()`) y, si hay cambios,
  los vuelve a guardar completos (`firebase.save_state()`) — el mismo patrón
  de "leer todo / escribir todo" que ya tenía el original (ver RNF3 en los
  requerimientos no funcionales), solo que ahora ocurre en el servidor en
  vez del navegador.

## Despliegue en AWS (infraestructura como código)

El despliegue en producción se hace con Terraform, en la carpeta
[`infra/`](infra/) (ver su propio README para el detalle completo). En
resumen, Terraform crea:

- Una instancia EC2 `t3.micro` (Ubuntu 22.04) con Nginx como reverse proxy
  delante de la app FastAPI (Uvicorn + systemd).
- Un bucket S3 privado donde se sube el `.zip` con el código de la app, que
  la instancia descarga y despliega sola al arrancar.
- Un Security Group que solo abre los puertos 80 y 443 — no hay SSH
  abierto; el acceso administrativo es por AWS Systems Manager (SSM Session
  Manager).
- Una IP elástica fija, para que no cambie si la instancia se reinicia.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# editar terraform.tfvars con los valores reales (nunca subirlo a git)

terraform init
terraform plan
terraform apply
```

Al terminar, `terraform output public_ip` da la IP pública para abrir
`http://<public_ip>/login`.

### Limitaciones conocidas de este despliegue

- Todavía no hay HTTPS: mientras no haya un dominio apuntando a la IP
  elástica, no se puede emitir un certificado y la app queda accesible solo
  por `http://`.
- No hay redeploy automático: un cambio de código requiere generar de
  nuevo el `.zip` y volver a aplicar Terraform (ver `infra/README.md`).
- Sigue aplicando la limitación ya mencionada de que **no hay
  sincronización en tiempo real** entre usuarios — cada quien ve los
  cambios de los demás al recargar.

## Pruebas

No hay una base de datos Firebase real disponible en este entorno de
desarrollo — para probar los flujos completos (login, CRUD, generación de
PDF, etc.) sin depender de credenciales reales, se puede sustituir
`app.firebase.get_state`/`save_state`/`sign_in_with_password`/
`verify_id_token` por versiones en memoria, como se hizo durante el
desarrollo de este puerto. La lógica de negocio pura vive en `app/services/`
y `app/models.py`, sin dependencias de FastAPI ni Firebase, por lo que
también se puede probar de forma aislada.

### Zona horaria

Las fechas de negocio (semana de comisiones, quincenas, "hoy" del calendario,
retorno de préstamos) se calculan en `TIMEZONE` (por defecto
`America/Bogota`) aunque el servidor esté en UTC, como en Render.
