# Sistema de Inventario CEDHI Nueva Arequipa

App Frappe/ERPNext v15 para la gestión de inventario del CEDHI (práctica
social UCSP). Lee este archivo al iniciar cualquier sesión nueva sobre este
proyecto antes de asumir contexto.

## Documentos de referencia (no duplicar aqui, solo consultar)

- `PRD_ Sistema de Inventario Integral1.pdf` — requerimientos funcionales
  oficiales (identificadores RF-*).
- `Defincion MVP  Proyecto de Prácticas Sociales ABS 2026-01 (1).pdf` — MVP.
- `Plan de Avances del Proyecto de Sistema de Inventario CEDHI.md` —
  cronograma de las 3 entregas (02/05, 15/05, 22/05/2026) con que RF
  corresponde a cada una y su estado "Realizado".

## Arquitectura

- **Site Docker (produccion/CEDHI):** `inventario.localhost`, puerto 8080.
  Definido en `docker_setup/.env` (`SITE_NAME`). Stack completo en
  `docker_setup/compose.yaml`: backend, frontend (nginx), websocket,
  queue-short/long, scheduler, db (MariaDB 10.6), redis-cache, redis-queue.
  El `Dockerfile` clona la app desde GitHub (`bench get-app --branch develop
  https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git`) — el codigo
  NO se monta desde disco local, hay que pushear a GitHub antes de
  actualizar un despliegue Docker.
- **Site bench local (dev/testing, esta maquina):** `inventario.local`,
  puerto 8000 (`bench start`). Independiente del Docker — sitio distinto,
  sin relacion con el `.env` de docker_setup.
- **Instalador Windows (CEDHI, sin conocimiento tecnico):**
  `docker_setup/windows/`:
  - `iniciar_sistema.bat` — uso diario, prende Docker + espera +
    abre navegador en `inventario.localhost:8080`.
  - `actualizar_sistema.bat` — solo cuando hay version nueva: `docker
    compose build --no-cache` + `up -d` + `bench migrate` dentro del
    container backend. No borra datos.
  - `crear_accesos_directos.ps1` — crea los 3 iconos de escritorio
    (Iniciar / ERPNext CEDHI / Actualizar). Correr de nuevo si se agregan
    accesos nuevos al script.
  - `LEEME.txt` — instrucciones en español para el CEDHI.
  - NUNCA correr `docker compose down -v` para actualizar: el `-v` borra
    los volumes (BD completa). Para actualizar sin perder datos:
    `down` (sin -v) o directamente `up -d --build`.

## Modelo de datos clave

- **Modulo** (nuevo doctype, ya NO Select fijo): cualquier modulo
  (TI/Gastronomia + los que se creen despues, ej. Estilismo, Mobiliaria) es
  un registro de este doctype. "General" NO es un Modulo, ver seccion
  "Modulos dinamicos" abajo. Solo `SuperAdministrador Inventario`/`System
  Manager` puede crear modulos (permisos en `modulo.json`).
  `Modulo.before_insert` (en `.../doctype/modulo/modulo.py`) crea
  automaticamente el Role "Admin {nombre_modulo}" y lo guarda en
  `rol_admin`, ADEMAS de auto-otorgarle permisos base (Custom DocPerm) en
  Articulo de Inventario/Ubicacion/Alerta de Inventario/Movimiento de
  Inventario via `_grant_module_role_permissions` — sin esto, los
  `has_permission` hooks de `permissions.py` no pueden conceder nada a un
  rol nuevo (ver "Gotcha permisos" abajo). Los 2 modulos historicos
  (TI/Gastronomia) se siembran via `ensure_initial_modules()` en
  `setup_inventory.py`, reusando los roles YA EXISTENTES (Admin TI/Admin
  Cocina) en vez de autogenerar unos nuevos con nombre distinto.
- **Articulo de Inventario**: registro principal. `modulo` es Link a
  Modulo (reqd: 1 — todo articulo pertenece a algun modulo, sin excepcion).
  `ubicacion` es Link a Ubicacion (reqd: 1) — modulo y ubicacion son
  INDEPENDIENTES: un articulo del modulo TI puede estar fisicamente en
  cualquier ubicacion, incluida una sin modulo asignado (ej. Direccion) o
  una de almacenaje temporal (ej. "Almacen Soldadura" guarda PCs de TI sin
  asignar todavia, no tiene nada que ver con soldadura).
  - Identificador permanente: el `name` (hash que Frappe genera, ej.
    "pltnd5mbe2"), NO un campo custom. Decision explicita del usuario: nada
    de ID secuencial 1,2,3... — el hash de Frappe ya es estable de por vida
    y es lo que se muestra en exports/filtros. (Existio un campo
    `id_articulo` secuencial en una sesion anterior; se elimino por completo
    junto a su hook `assign_id_articulo`.)
  - `codigo_interno`: etiqueta legible que SI cambia (`set_internal_code`,
    corre en `validate`, no solo `before_insert`, para reaccionar a updates
    que cambien modulo/ubicacion). Formato `INV-{MODULO}-{UBICACION}-NNNN`
    usando el nombre real de Modulo/Ubicacion como slug (ya NO hay
    `tag_map` fijo de 3 modulos — eso rompia con modulos nuevos).
  - Las secciones de UI ya NO se ocultan por `eval:doc.modulo=="X"` (ver
    mas abajo, "Modulos dinamicos"). Tampoco existen campos `pabellon`/
    `aula` (se quitaron de Ubicacion y Articulo, eran innecesarios/sin uso
    real — decision del usuario, no jerarquia real del CEDHI).
  - Boton "Reasignar" (form y list view, ver `inventory_logic.py:
    reasignar_articulo`): cambia modulo+ubicacion de un articulo sin abrir
    el form completo. Solo valida permiso de escritura sobre el modulo
    ACTUAL (origen) del articulo — el admin de un modulo puede mandar un
    articulo suyo a CUALQUIER modulo destino, sin necesitar permiso ahi
    (decision confirmada: el modulo de un Articulo es su unidad real de
    responsabilidad administrativa, a diferencia de Ubicacion).
- **Movimiento de Inventario**: doc_events en `inventario_cedhi/
  inventory_logic.py`. `tipo_movimiento` en {Entrada, Salida, Ajuste}.
  Entrada/Salida: `cantidad` es delta. Ajuste: `cantidad` es el stock TOTAL
  nuevo (no delta) — 0 es valido (perdida total), negativo no.
  `stock_antes_del_movimiento`/`stock_despues_del_movimiento` son
  snapshots reales (no fetch_from) que `reverse_stock_on_cancel` usa para
  revertir exacto sin recalcular. Campo es `decimal NOT NULL DEFAULT 0`
  (no NULL) — movimientos anteriores a este snapshot se completan via el
  patch `inventario_cedhi/patches/backfill_stock_antes_del_movimiento.py`.
- **Ubicacion** vs **Asignacion**: estructuras casi identicas (nombre +
  modulo opcional + activo). Hipotesis confirmada con el usuario: Ubicacion
  = donde esta FISICAMENTE el bien. Asignacion = a que area/responsable
  administrativo pertenece (puede no coincidir con donde esta fisicamente)
  — esto sigue sin confirmar 100% con el CEDHI, tratar como hipotesis de
  trabajo. `modulo` es OPCIONAL en ambos (Link a Modulo, sin `reqd`) — una
  ubicacion puede no pertenecer a ningun modulo (ej. Direccion, Garita de
  Seguridad).
- **import_excel_articulos.py**: importador REAL vigente, usa la plantilla
  Excel definitiva del encargado del CEDHI (formato con columna Modulo,
  ver `datos_iniciales/INVENTARIO_2026/`). 1 registro por unidad fisica: si
  CANT.=N, crea N Articulo de Inventario (cada uno cantidad=1, su propio
  `name` hash) — decision explicita del usuario, no un solo registro con
  cantidad=N. Idempotente (fuente_datos+hoja_origen+numero_origen).
  Restringido a System Manager/SuperAdministrador Inventario/Administrator
  (`importar_articulos_excel_endpoint`).
- **data_import.py**: importador LEGACY (CSV de `datos_iniciales/csv/`,
  formato "CARITAS" viejo con Select fijo TI/Gastronomia/General). Superado
  por `import_excel_articulos.py`. Confirmado fuera de alcance arreglar
  para modulos dinamicos — sigue ahi, sin uso real, no romper si se toca
  algo cerca.
- **setup_inventory.py**: crea workspaces, number cards, charts, reportes,
  y usuarios iniciales de prueba (`create_initial_users()`, password fija
  `cedhi123` para todos: andree@cedhi.local [SuperAdmin], luis@/angie@cedhi.
  local [Admin Cocina], manuel@cedhi.local [Revisor]). Administrator
  real usa `ADMIN_PASSWORD` del `.env` (`admin` por defecto).

## Modulos dinamicos (implementado, sesion 2026-06-24)

Antes: `modulo` era un Select fijo con 3 opciones hardcodeadas en 4
doctypes, y controlaba que secciones de UI se mostraban
(`eval:doc.modulo=="TI"` etc, ~20 reglas) y que rol podia escribir que
modulo (`MODULE_WRITE_ACCESS` dict fijo en `permissions.py`). El CEDHI
pidio (ver `docs/requerimientosNuevos.md`) poder crear modulos nuevos
(Estilismo, Mobiliaria, etc) sin que alguien tenga que tocar codigo cada
vez. Cambios:

- Las ~20 reglas `eval:doc.modulo==X` se eliminaron: todos los modulos
  comparten el mismo set de campos fisicos (marca, modelo, cantidad,
  estado_conservacion), siempre visibles. Los campos de insumos perecibles
  (stock_actual, stock_critico, grupo, categoria, presentacion,
  proveedor_referencia, medida, porcentaje_desperdicio, cantidad_minima,
  precio_referencial, es_perecible, fecha_vencimiento) quedan con
  `hidden: 1`, sin uso por ahora — NO se borraron, Gastronomia perecible se
  retoma despues, fuera de alcance de este cambio.
  - OJO: `configure_module_specific_article_form()` en `setup_inventory.py`
    escribe estos campos en cada `bench migrate`/`setup_inventory_mvp()` —
    si se edita el JSON del doctype a mano sin tocar tambien esta funcion,
    el proximo migrate revierte la edicion. Asignar `field.depends_on = ""`
    (string vacio), NO `None` — Frappe no limpia el campo con `None` en
    `doc.save()`, queda con el valor viejo silenciosamente.
- `permissions.py`: `MODULE_WRITE_ACCESS` (dict fijo rol->modulo) se
  reemplazo por `_module_write_access()`, que lee `Modulo.rol_admin` de la
  BD en cada llamada. `LIMITED_USER_ROLES`/`INVENTORY_USER_ROLES`/
  `READ_ALL_ROLES` (constantes fijas) se volvieron funciones
  `_limited_user_roles()`/`_inventory_user_roles()`/`_read_all_roles()`
  que incluyen todos los roles "Admin {modulo}" existentes dinamicamente.
- **Gotcha de permisos importante**: un `has_permission` hook custom (los
  de `permissions.py`, registrados en `hooks.py`) solo puede RESTRINGIR
  acceso que un permiso base (DocPerm/Custom DocPerm) ya concede — NO puede
  CONCEDER nada de la nada. Por eso `Modulo.before_insert` ademas de crear
  el Role "Admin {modulo}" llama `_grant_module_role_permissions` (en
  `modulo.py`), que crea Custom DocPerm base en los 4 doctypes del
  inventario para ese rol nuevo. Sin esto, un Modulo creado por UI quedaba
  con un rol inservible (bug real pisado y arreglado esta sesion: Admin
  Estilismo/Admin Mobiliaria tenian 0 permisos hasta el backfill).
- Workspace "Configuracion" tiene el link "Gestion de Modulos" (Link a
  Modulo) junto a "Espacios Fisicos".
- Verificado end-to-end: crear Modulo "Estilismo" -> Role "Admin
  Estilismo" se autogenera con permisos reales -> un usuario con ese rol
  puede crear/editar articulos de modulo Estilismo y NO puede tocar
  TI/Gastronomia. Usuarios historicos (luis@/manuel@/andree@cedhi.local)
  probados sin regresion tras el cambio.

## "General" como vista agregada, no modulo (requerimientosNuevos.md #5)

"General" NO es un Modulo — es la vista agregada de TODOS los modulos
juntos (Reporte Maestro de Inventario con `article_report_condition`
devolviendo `1=1` para roles de lectura total). El rol "Admin General" que
administraba ese modulo ficticio se ELIMINO y se fusiono con "Revisor"
(ver seccion siguiente) — ya no existe ningun Modulo llamado "General" en
la tabla `Modulo`, solo TI/Gastronomia + los dinamicos (Estilismo,
Mobiliaria, etc).

## Roles: Revisor (fusion de "Revisor" + "Admin General", sesion 2026-06-28)

Existian dos roles casi identicos: "Revisor" (solo lectura total) y "Admin
General" (lectura total + escritura manager en Articulo/Alerta/Movimiento
+ Kardex en cualquier modulo, por ser el admin del Modulo ficticio
"General"). El usuario pidio fusionarlos por redundancia. Decision: el rol
fusionado queda **solo lectura** (nivel del Revisor viejo) + conserva la
capacidad de registrar Movimientos (Kardex) en cualquier modulo
(`movement_has_permission` en `permissions.py`, caso especial
`GENERAL_ADMIN_ROLE`).

Mecanica de la fusion (irrepetible, ya ejecutada, solo para contexto si
hace falta repetir algo similar):
1. Se borro el Role "Revisor" viejo (0 usuarios reales).
2. `frappe.rename_doc("Role", "Admin General", "Revisor", force=True)` —
   Frappe propaga el rename a Has Role/Custom DocPerm/Report.roles
   automaticamente. Los 3 usuarios reales (manuel@cedhi.local,
   admin.general@cedhi.local, anthony.briceno@ucsp.edu.pe) quedaron con
   "Revisor".
3. `permissions.py`: `GENERAL_ADMIN_ROLE = "Revisor"` (antes
   `"Admin General"` — es un string literal, NO sigue un rename de Role
   automaticamente, hubo que actualizarlo a mano). Sets redundantes
   `{GENERAL_ADMIN_ROLE, "Revisor"}` colapsados a `{GENERAL_ADMIN_ROLE}`.
4. **Trampa real que costo deteccion**: los JSON versionados de varios
   doctypes (Articulo de Inventario, Ubicacion, Alerta de Inventario,
   Movimiento de Inventario, Asignacion, Modulo) y de los 3 reportes
   genericos (Reporte Maestro, Bandeja de Alertas CEDHI, Kardex de
   Movimientos) todavia tenian un permission/role row literal `"Admin
   General"` ademas del de `"Revisor"`. `bench migrate` sincroniza
   permisos desde esos JSON, y Frappe RECREA el Role si el nombre referido
   en un permission row no existe — asi que cada migrate resucitaba un
   Role "Admin General" disabled=1 + duplicaba Custom DocPerm/Report.roles
   para "Revisor". Fix: borrar el permission row de "Admin General" de
   cada JSON (quedando solo el de "Revisor", ya de antes solo-lectura) y
   actualizar `setup_inventory.py` (`configure_inventory_role_permissions`,
   listas de reportes/workspaces/role profiles) para no mencionar mas
   "Admin General". Si algun dia un migrate vuelve a mostrar un Role
   "Admin General" disabled, es señal de que quedo un JSON sin arreglar.

## Workspaces (filtrado por rol)

- **Inventario CEDHI** (padre): KPIs/graficos (todos los roles) + card
  "Operaciones" (Catalogo/Kardex/Incidencias, visible a los 7 roles).
- **Operaciones, Reportes, Configuracion** (hijos, `parent_page`): cada uno
  tiene su propio `workspace.roles` — Frappe SI filtra correctamente a
  nivel de workspace completo. Reportes excluye Reportante. Configuracion
  excluye Revisor y Reportante (ahi viven los shortcuts de carga de
  catalogo/plantillas, solo roles admin).
- Una "card" de Workspace (`type: card` con `card_name`) renderiza los
  links de su propio Card Break EN EL MISMO workspace — no es un boton de
  navegacion a otra pagina. Si se quita el Card Break/links de un workspace
  pero se deja la referencia a la card, la card sale vacia/invisible (bug
  ya pisado una vez, cuidado al tocar `create_inventory_workspace`/
  `create_child_workspaces` en `setup_inventory.py`).

## Datos reales del CEDHI (no son solo prueba)

`datos_iniciales/INVENTARIO_2026/` tiene 30 Excel reales (uno por
ubicacion, nombrados "N. NOMBRE.xlsx" — el usuario los reordeno/renombro a
mitad de sesion, confirmar conteo si difiere) + `Copia de FORMATO DE
INVENTARIOS - CEDHI.xlsx` (plantilla oficial "CARITAS") + un Excel de
Cosmetologia en subcarpeta separada con formato distinto. ~830 filas de
datos reales en total. Hallazgos del analisis:

- Formato oficial CARITAS: N°, CANT., DESCRIPCION DEL BIEN, MODELO Y/O
  SERIE, MARCA, UBICACION, FECHA DE ADQUISICION, ESTADO (B/R/M, distinto
  del `estado` actual del sistema que es Activo/De baja/En reparacion —
  falta mapear), OBSERVACIONES (incluye financiador/proyecto en texto
  libre — pista para el filtro "por proyecto" pedido, aun sin implementar).
- Algunos archivos tienen las columnas MODELO/MARCA desalineadas cuando el
  item no tiene modelo/marca (el dato se corre una celda a la izquierda).
- Varios archivos tienen MULTIPLES HOJAS, no solo la primera:
  - `8. AULA 11-ESTILISMO.xlsx` (Aula 11 / Estilismo): 6 hojas, son
    CONTINUACION numerica del mismo inventario (hoja 1 items 1-24, hoja 2
    items 25+, etc) — una sola ubicacion real, hay que concatenar todas
    las hojas al importar, no solo la primera.
  - `20.GASTRONOMIA.xlsx`: 8 hojas, cada una es una SUB-ubicacion distinta
    (B.Docentes, B.Gastronomia, Bar y Comedor, Almacen, Cocina I/II,
    Pasteleria, Almacen Pasteleria) — NO es 1 sola ubicacion.
  - `21.BAÑOS DE GASTRONOMIA.xlsx`: 2 hojas, son DUPLICADO EXACTO de 2 de
    las hojas de `20.GASTRONOMIA.xlsx` (mismos items, misma cantidad) —
    ignorar este archivo o deduplicar al importar.
  - `3. SALA DE COMPUTO.xlsx`: 2 hojas, "Copia de CEDHI" tiene items reales
    pero en columna UBICACION = "Almacen Soldadura", no Sala de Computo.
    CONFIRMADO con el usuario: esto NO es error de captura — Almacen
    Soldadura es zona de bodega real para PCs del modulo TI sin asignar
    todavia, listas para ponerse a disposicion en cualquier ubicacion.
  - `STREAMING.xlsx`: 2 hojas, "CEDHI" esta vacia/obsoleta (solo
    numeracion), "Copia de CEDHI" tiene los 35 items reales.
  - **Conclusion aplicada en `import_excel_articulos.py`**: la fuente de
    verdad de la ubicacion de cada FILA es la columna UBICACION de esa
    fila, NUNCA el nombre del archivo — un archivo puede contener items de
    varias ubicaciones distintas. (El importador real vigente usa la
    plantilla NUEVA del encargado, ya con columna Modulo propia — ver
    seccion `import_excel_articulos.py` arriba. Los hallazgos de arriba
    sobre hojas multiples/duplicadas son del analisis de la plantilla
    "CARITAS" vieja, contexto historico, confirmar si aun aplican a la
    plantilla nueva antes de asumirlos.)
- ~9 de las 30 ubicaciones estan vacias (solo encabezado, sin items).
- Cosmetologia usa formato distinto: N° CAJA, CANT. con unidad embebida en
  texto ("24 und", "8 pq"), sin UBICACION/ESTADO fijos, con FECHA DE
  VENCIMIENTO en su lugar (insumo perecible). El enfoque actual del CEDHI
  (confirmado en reunion) es objetos fisicos NO perecibles (sillas, PCs,
  ollas, cuchillos, focos) — perecibles/Cosmetologia quedan en pausa.

## Pendiente / en discusion (NO implementar sin confirmar)

Pedido del CEDHI tras la presentacion + `docs/requerimientosNuevos.md`.
Plazo original: lunes madrugada / martes temprano (puede haber cambiado,
confirmar fecha vigente).

Comparado contra `docs/requerimientosNuevos.md` (9 puntos pedidos por el
CEDHI), estado real punto por punto:

1. ~~Filtrar por area (aula 10, aula 2)~~ — **IMPLEMENTADO**. `ubicacion`
   es Link con `in_standard_filter:1` en Articulo de Inventario.
2. ~~Modulo independiente para Estilismo~~ — **IMPLEMENTADO** (Modulo
   dinamico, ver seccion "Modulos dinamicos" arriba).
3. ~~Modulo independiente para Gastronomia~~ — **IMPLEMENTADO** (historico,
   ya existia).
4. ~~Modulo independiente para Mobiliaria~~ — **IMPLEMENTADO** (Modulo
   dinamico).
5. ~~Inventario general = todos los elementos de todos los modulos~~ —
   **IMPLEMENTADO**: "General" no es un Modulo, es vista agregada
   (`article_report_condition` -> `1=1` para roles de lectura total). Ver
   seccion "General como vista agregada" arriba.
6. ~~Boton de reasignar (modulo/ubicacion) dentro de cada modulo~~ —
   **IMPLEMENTADO**: `reasignar_articulo` (`inventory_logic.py`) + boton
   "Reasignar" en form y list view de Articulo de Inventario.
7. Plantilla Excel con modificaciones — **IMPLEMENTADO**: el encargado del
   CEDHI entrego una plantilla nueva con columna Modulo propia,
   `import_excel_articulos.py` la importa (1 registro por unidad fisica,
   ya probado con 46 articulos reales de "1. DIRECCION.xlsx", idempotente).
8. Codigo de barras — **PARCIAL**, baja prioridad ("segun el tiempo
   disponible", dicho por el CEDHI mismo). Campo `codigo_barras` en
   Articulo, `scan_barcode` en Movimiento, existen pero sin flujo de
   escaneo end-to-end probado.
9. ~~Filtrar por ubicacion dentro de cada modulo~~ — **IMPLEMENTADO**, igual
   mecanismo que el punto 1 (filtro estandar de `ubicacion`), mas
   `_allowed_modules_for_read`/`article_report_condition` ya acotan los
   datos visibles al modulo del Admin que filtra.

Pendientes que NO vienen de `requerimientosNuevos.md` pero quedaron
abiertos en discusiones previas con el usuario (ninguno bloqueante):

A. **Boton "Crear Ubicacion" explicito en la UI** — hoy `Ubicacion` usa
   list/form view estandar de Frappe (link "Espacios Fisicos" en
   Configuracion), sin flujo guiado especifico. Bajo impacto, cosmetico.
B. **Dividir un Articulo entre 2 ubicaciones** (ej. 30 sillas, mover 10 a
   otra aula sin tocar las 20 restantes) — NO implementado. Hoy un
   Articulo = 1 registro = 1 ubicacion completa; el `name` hash da
   trazabilidad estable por registro, pero no hay mecanismo de "split" de
   cantidad entre ubicaciones distintas.
C. Confirmar con el CEDHI la diferencia real Ubicacion vs Asignacion
   (hipotesis: fisica vs administrativa, ver seccion arriba) — dada como
   mayormente confirmada por el usuario pero no 100% verificada con el
   CEDHI.
D. Filtro "por proyecto/financiador" en Reporte Maestro — el dato vive en
   texto libre dentro de OBSERVACIONES del Excel, sin parsear a campo
   estructurado todavia.
E. Entorno de red local multi-PC (una PC corre la BD 24/7, otras se
   conectan por red local) — AUN NO DISEÑADO (requiere IP fija/firewall
   Windows). Pausado por el usuario hasta cerrar features de arriba.
   Cloud/Google Workspace auth tambien en standby por costo (decision de
   la profesora, sesion anterior).
F. Jerarquia Pabellon > Aula — DESCARTADA, no pendiente: los campos
   `pabellon`/`aula` se quitaron del doctype Ubicacion/Articulo por
   decision del usuario ("lo de aula? osea es raro" -> "quitalos"), no era
   una jerarquia real confirmada por el CEDHI.

## Convenciones de este repo

- Comentarios en español, sin tildes en el codigo (consistente con el
  estilo existente) salvo en strings/labels visibles al usuario (esos SI
  llevan tildes correctas).
- Mensajes de commit y PRs: español, explican el "por que", no el "que".
- Antes de comitear cambios en doctypes/workspaces generados por
  `setup_inventory.py`, correr el setup en bench local primero y verificar
  con `git diff` que el JSON auto-exportado no tenga solo cambios
  cosmeticos (`modified` timestamp) antes de decidir si se trackea.
- Repo en GitHub: `git@github.com:aaabriceno/Proyecto_Inventario_CEDHI.git`,
  rama de trabajo `develop`. El Dockerfile de produccion clona esa rama —
  hacer push antes de esperar que un rebuild Docker traiga cambios nuevos.
