# Guia de inicio - Sistema de Inventario CEDHI

> **Este documento es referencia para desarrolladores.**
> Si buscas instalar el sistema en Windows (CEDHI), lee el `README.md` en la raiz del proyecto.

---

## Regla principal de desarrollo

El codigo propio del proyecto vive en:

```
apps/inventario_cedhi/
```

No se editan directamente `apps/frappe` ni `apps/erpnext`.

---

## Arquitectura real (estado actual)

### Entorno de produccion / CEDHI (Windows + Docker)

- Carpeta `docker_setup/` contiene todo lo necesario para levantar el sistema en Windows sin instalar nada manualmente.
- El Dockerfile clona la app desde GitHub rama `develop` al construir la imagen. **El codigo no se monta desde disco local — hay que pushear antes de actualizar.**
- Sitio: `inventario.localhost`, puerto `8080`.
- Acceso LAN: cualquier PC de la misma red puede entrar por `http://<IP-del-servidor>:8080` sin configuracion extra, gracias a `FRAPPE_SITE_NAME_HEADER` en el `.env`.

### Entorno de desarrollo (Ubuntu, este repo)

- Bench local en `~/frappe/my-bench`, sitio `inventario.local`, puerto `8000`.
- Completamente independiente del Docker. No comparten BD ni sesiones.
- Para probar cambios: editar codigo → `bench --site inventario.local migrate` → refrescar navegador.

---

## Modelo de datos clave

### Modulo (doctype dinamico)

Cualquier modulo del CEDHI (TI, Gastronomia, Estilismo, Mobiliaria, etc.) es un registro de este doctype, NO un Select hardcodeado. Al crear un Modulo nuevo:

- Se autogenera el Role `"Admin {nombre}"` con permisos base en los 4 doctypes del inventario.
- El SuperAdministrador puede crear modulos nuevos desde la UI sin tocar codigo.

**"General" NO es un Modulo** — es la vista agregada de todos los modulos (Reporte Maestro para roles de lectura total).

### Articulo de Inventario

- `modulo`: Link a Modulo (obligatorio).
- `ubicacion`: Link a Ubicacion (obligatorio). **Modulo y ubicacion son independientes** — un articulo de TI puede estar en cualquier ubicacion fisica.
- `name`: hash permanente que genera Frappe (ej. `pltnd5mbe2`). Es el identificador de por vida, no cambia nunca.
- `codigo_interno`: etiqueta legible que SI cambia si se reasigna el articulo. Formato `INV-{MODULO}-{UBICACION}-NNNN`.
- `codigo_barras`: campo opcional para codigo de barras fisico. Si esta vacio, el sistema usa `codigo_interno` como fallback en el escaneo.

Campos perecibles (`stock_actual`, `stock_critico`, `es_perecible`, `fecha_vencimiento`, etc.) visibles solo si `es_perecible == "Si"`.

### Ubicacion

Campo `modulo` opcional — una ubicacion puede no pertenecer a ningun modulo (ej. Direccion, Garita de Seguridad). La fuente de verdad del modulo de un articulo es el campo `modulo` del Articulo, no la Ubicacion donde esta fisicamente.

### Movimiento de Inventario (Kardex)

- `tipo_movimiento`: Entrada / Salida / Ajuste.
- Entrada/Salida: `cantidad` es delta.
- Ajuste: `cantidad` es el stock TOTAL nuevo (no delta). Cero es valido.

---

## Roles del sistema

| Rol | Acceso |
|-----|--------|
| SuperAdministrador Inventario | Todo — unico que puede crear modulos, usuarios, cargar catalogos masivos |
| Admin {Modulo} | Solo lectura/escritura en articulos de su modulo (ej. Admin TI, Admin Cocina) |
| Revisor | Solo lectura de todos los modulos + puede registrar Movimientos (Kardex) |
| Reportante | Solo crea alertas y ve sus propios reportes; no ve el catalogo completo |

Cada Modulo nuevo autogenera su propio `Admin {nombre}` automaticamente.

---

## Importacion de datos

### Plantilla correcta

El importador vigente (`import_excel_articulos.py`) usa la **plantilla nueva** del encargado del CEDHI con columna Modulo propia. El formato CARITAS viejo (CSV de `datos_iniciales/csv/`) esta obsoleto — no usar.

Columnas de la plantilla nueva:
```
A=N°  C=CANT.  E=DESCRIPCION  K=Identificador Unico  L=Modelo  M=SERIE
N=MARCA  O=UBICACION  R=Modulo  S=Benefactor  T=FECHA ADQUISICION
U/V/W=ESTADO (B/R/M)  X=OBSERVACIONES
```

Header en fila 11, datos desde fila 13.

### Subida desde la UI (forma recomendada)

No hace falta copiar Excel a ninguna carpeta del servidor. Desde el navegador:

- `/importar_articulos` — sube un .xlsx de articulos, preview, confirmar.
- `/cargar_ubicaciones` — sube un .xlsx de ubicaciones (1 columna: Nombre Ubicacion), preview, confirmar.
- `/cargar_modulos` — sube un .xlsx de modulos (1 columna: Nombre Modulo), preview, confirmar.

Solo accesible para SuperAdministrador Inventario / System Manager / Administrator.

### Idempotencia

El importador no duplica: usa `fuente_datos + hoja_origen + numero_origen` para identificar cada fila. Si se sube el mismo Excel dos veces, la segunda vez todo sale como "ya existia (saltado)".

---

## Usuarios de prueba creados por setup

`setup_inventory.py` crea estos usuarios con password `cedhi123`:

| Usuario | Rol |
|---------|-----|
| andree@cedhi.local | SuperAdministrador Inventario |
| luis@cedhi.local | Admin Cocina |
| angie@cedhi.local | Admin Cocina |
| manuel@cedhi.local | Revisor |

Password de Administrator real: viene de `ADMIN_PASSWORD` en el `.env` (por defecto `admin`).

---

## Convenciones del repo

- Comentarios en español, sin tildes en el codigo. Strings/labels visibles al usuario SI llevan tildes.
- Commits en español, explican el "por que", no el "que".
- Rama de trabajo: `develop`. El Dockerfile de produccion clona esa rama — pushear antes de esperar que un rebuild Docker traiga cambios.
- Antes de commitear cambios en doctypes/workspaces generados por `setup_inventory.py`, correr el setup en bench local y verificar con `git diff` que no sean solo cambios cosmeticos de timestamp.

---

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `inventario_cedhi/setup_inventory.py` | Crea/configura todo: workspaces, roles, permisos, reportes, usuarios, print formats, client scripts. Idempotente. |
| `inventario_cedhi/import_excel_articulos.py` | Importador de articulos/ubicaciones/modulos desde Excel. Endpoints de subida con preview. |
| `inventario_cedhi/inventory_logic.py` | Logica de Kardex, reasignacion, busqueda por codigo escaneado, generacion de codigo interno. |
| `inventario_cedhi/permissions.py` | Hooks de permisos por modulo. |
| `inventario_cedhi/www/` | Paginas web propias: consultar_articulo, importar_articulos, cargar_ubicaciones, cargar_modulos. |
| `docker_setup/` | Todo lo necesario para correr en Windows con Docker. |
| `datos_iniciales/UBICACIONES.xlsx` | Lista maestra de ubicaciones del CEDHI. |
| `datos_iniciales/MODULOS.xlsx` | Lista maestra de modulos del CEDHI. |
