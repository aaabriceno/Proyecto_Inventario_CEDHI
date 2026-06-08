# Sistema de Inventario CEDHI Nueva Arequipa

Aplicacion Frappe/ERPNext para gestionar el inventario del CEDHI Nueva Arequipa. El MVP organiza articulos por modulo:

- TI
- Gastronomia
- General

El proyecto incluye carga inicial desde Excel/CSV, roles del PRD, permisos por modulo, reportes iniciales y un workspace de trabajo dentro de Frappe.

## Que se sube a este repo

Este repositorio contiene solo la app custom:

```text
apps/inventario_cedhi
```

No se debe subir todo `my-bench`. Las carpetas `env`, `sites`, `logs`, `config`, `apps/frappe` y `apps/erpnext` son parte de la instalacion local o dependencias externas.

## Que NO viene incluido al clonar

Al clonar este repositorio no se obtiene la base de datos local de Anthony ni el contenido ya cargado en su sitio `inventario.local`.

Este repo SI incluye:

- Codigo de la app `inventario_cedhi`.
- Scripts para crear/configurar campos, roles, permisos, reportes y workspace.
- Excel originales y CSV preparados para importacion.
- Documentacion del proyecto.

Este repo NO incluye:

- Usuarios creados en la maquina de Anthony.
- Contrasenas.
- Sesiones iniciadas.
- Articulos ya importados dentro de MariaDB.
- Archivos cargados en `sites/inventario.local/private/files`.
- Backups o configuracion local de `sites`.

Cada integrante debe crear su propio sitio local, instalar la app, ejecutar los scripts de configuracion y luego importar los CSV.

## Requisitos

- Frappe Bench instalado
- ERPNext instalado en el bench
- Python, Node, Redis y MariaDB configurados segun la guia oficial de Frappe/ERPNext

## Instalacion en un bench existente

Desde la carpeta del bench:

```bash
cd ~/frappe/my-bench
bench get-app https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git --branch develop
bench --site inventario.local install-app inventario_cedhi
```

Si el sitio todavia no existe, primero crear e instalar ERPNext:

```bash
bench new-site inventario.local
bench --site inventario.local install-app erpnext
bench --site inventario.local install-app inventario_cedhi
```

## Instalacion con Docker en Windows + WSL

Esta opcion es la recomendada para integrantes que usan Windows o macOS y no quieren instalar manualmente Python, Node, Redis, MariaDB, Bench, Frappe y ERPNext.

### Requisitos

En Windows:

- Docker Desktop instalado.
- WSL2 habilitado.
- Una distribucion Linux en WSL, por ejemplo Ubuntu.

En WSL/Ubuntu:

- Git instalado.
- Acceso al repositorio del proyecto.

No descargar el proyecto como ZIP. Se recomienda clonar con Git dentro de WSL para poder usar `git pull`, ramas y commits correctamente.

### 1. Clonar el repositorio dentro de WSL

Abrir Ubuntu/WSL y ejecutar:

```bash
mkdir -p ~/proyectos
cd ~/proyectos
git clone -b develop https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git
cd Proyecto_Inventario_CEDHI
```

Si se usa SSH:

```bash
git clone -b develop git@github.com:aaabriceno/Proyecto_Inventario_CEDHI.git
cd Proyecto_Inventario_CEDHI
```

### 2. Preparar variables locales de Docker

Entrar a la carpeta Docker y crear el `.env` local:

```bash
cd ./docker_setup/
cp .env.example .env
```

El archivo `.env` no se sube a GitHub. Cada integrante tiene el suyo. Si se cambia `DB_PASSWORD`, se debe usar el mismo valor al crear el sitio.

### 3. Construir y levantar los contenedores

```bash
docker compose up -d --build
```

Esto levanta los servicios de Frappe/ERPNext, MariaDB, Redis, workers, scheduler, websocket y frontend.

### 4. Crear el sitio e instalar las apps

Crear el sitio:

```bash
docker compose exec backend bench new-site inventario.localhost --mariadb-root-password admin --admin-password admin
```

Instalar ERPNext:

```bash
docker compose exec backend bench --site inventario.localhost install-app erpnext
```

Instalar la app del proyecto:

```bash
docker compose exec backend bench --site inventario.localhost install-app inventario_cedhi
```

Si cambiaste `DB_PASSWORD` en `.env`, usa ese mismo valor en `--mariadb-root-password`.

### 5. Ejecutar la configuracion inicial del MVP

```bash
docker compose exec backend bench --site inventario.localhost execute inventario_cedhi.setup_inventory.setup_inventory_mvp
```

Este comando crea/configura DocTypes, campos, roles, permisos, reportes, workspace y usuarios iniciales de prueba.

### 6. Definir el sitio por defecto y limpiar cache

```bash
docker compose exec backend bench use inventario.localhost
docker compose exec backend bench --site inventario.localhost clear-cache
```

### 7. Abrir el sistema

Desde el navegador de Windows o del sistema anfitrion:

```text
http://inventario.localhost:8080
```

### Actualizar cambios del proyecto dentro de Docker

Cuando se suban cambios a `develop`, la forma mas segura de actualizar Docker es bajando los cambios en local y reconstruyendo la imagen:

```bash
cd ~/proyectos/Proyecto_Inventario_CEDHI
git pull origin develop
cd docker_setup
docker compose up -d --build
```

Si necesitas descargar los últimos cambios de GitHub inmediatamente dentro del contenedor, sin esperar a reconstruir toda la imagen, ejecuta este comando:
```bash
docker compose exec backend bash -c "cd apps/inventario_cedhi && git fetch https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git develop && git reset --hard FETCH_HEAD"

Si se crearon nuevas tablas, campos, reportes o cambios de modelo, sincronizar la base local:

```bash
docker compose exec backend bench --site inventario.localhost migrate
docker compose exec backend bench --site inventario.localhost execute inventario_cedhi.setup_inventory.setup_inventory_mvp
```

Limpiar cache:

```bash
docker compose exec backend bench --site inventario.localhost clear-cache
```

### Trabajar en una rama propia

Si un integrante va a programar cambios, debe crear una rama:

```bash
git checkout -b feature/nombre-del-cambio
```

Tambien puede entrar al contenedor si necesita revisar el bench:

```bash
docker compose exec -it backend bash
cd apps/inventario_cedhi
```

Ejemplo de commit desde el repo local:

```bash
git add .
git commit -m "Agregado modulo de reportes"
git push origin mi-rama
```

## Configuracion inicial del MVP

Ejecutar este comando desde la raiz del bench:

```bash
bench --site inventario.local execute inventario_cedhi.setup_inventory.setup_inventory_mvp
bench --site inventario.local clear-cache
```

Si `bench start` estaba corriendo, reiniciarlo despues de cambios en `hooks.py`.

Este comando crea primero los DocTypes base (`Ubicacion`, `Asignacion`, `Articulo de Inventario`) y despues configura campos, alertas, roles, permisos, reportes y workspace. Por eso es el comando recomendado para una instalacion nueva.

Al terminar esta configuracion, el sitio tendra la estructura del MVP:

- DocTypes y campos necesarios.
- Roles y permisos del PRD.
- Reportes iniciales.
- Workspace `Inventario CEDHI`.

Pero todavia no tendra los articulos cargados. Los articulos se cargan importando los CSV.

## Datos iniciales

Los Excel originales estan en:

```text
datos_iniciales/
```

Los CSV preparados para importar estan en:

```text
datos_iniciales/csv/
```

Archivos principales:

- `import_articulos_gastronomia.csv`
- `import_articulos_gastronomia_licores.csv`
- `import_articulos_ti_sala_computo.csv`

La importacion se realiza desde Frappe en:

```text
Importacion de Datos
```

Tipo de documento:

```text
Articulo de Inventario
```

Tipo de importacion:

```text
Insertando nuevos registros
```

No usar archivos dentro de `sites/inventario.local/private/files` como fuente del repo. Esos son archivos locales cargados en un sitio.

### Carga de articulos

Despues de ejecutar la configuracion inicial, importar los CSV desde Frappe:

1. Abrir `Importacion de Datos`.
2. Crear una nueva importacion.
3. En `Tipo de Documento`, elegir `Articulo de Inventario`.
4. En `Tipo de importacion`, elegir `Insertando nuevos registros`.
5. Subir uno de los CSV de `datos_iniciales/csv/`.
6. Revisar la vista previa.
7. Iniciar importacion.

Repetir el proceso para:

- `datos_iniciales/csv/import_articulos_gastronomia.csv`
- `datos_iniciales/csv/import_articulos_gastronomia_licores.csv`
- `datos_iniciales/csv/import_articulos_ti_sala_computo.csv`

Estos CSV son la fuente compartida del equipo. La importacion que ya existe en la maquina de Anthony no se copia automaticamente al clonar GitHub.

## Roles del sistema

Roles definidos para el MVP:

- `SuperAdministrador Inventario`: acceso total al inventario y usuarios del proyecto.
- `Admin TI`: gestiona solo articulos del modulo TI.
- `Admin Cocina`: gestiona solo articulos del modulo Gastronomia.
- `Admin General`: edita General y puede visualizar los otros modulos.
- `Revisor`: solo lectura.
- `Reportante`: crea alertas/incidencias y ve solo sus propios reportes.

Las reglas por modulo estan en:

```text
inventario_cedhi/permissions.py
```

Los hooks de permisos estan en:

```text
inventario_cedhi/hooks.py
```

## Usuarios de prueba

Los usuarios tambien viven en la base local de cada sitio. Por eso, al clonar el repo no apareceran automaticamente los usuarios de Anthony.

Cada integrante puede crear usuarios de prueba desde Frappe y asignarles roles. Ejemplos:

```text
superadmin@cedhi.local    -> SuperAdministrador Inventario
admin.ti@cedhi.local      -> Admin TI
admin.cocina@cedhi.local  -> Admin Cocina
admin.general@cedhi.local -> Admin General
revisor@cedhi.local       -> Revisor
profesor@cedhi.local      -> Reportante
```

Como los correos `@cedhi.local` no existen realmente, la contrasena temporal se puede establecer desde consola:

```bash
bench --site inventario.local execute frappe.utils.password.update_password --args '["usuario@cedhi.local", "Cedhi12345"]'
```

No guardar contrasenas reales en codigo ni en documentacion.

## Autenticacion con Google (OAuth) en Desarrollo

Para el MVP, el inicio de sesion con Google esta configurado en un entorno de pruebas en la cuenta de Google Cloud de un integrante del equipo.

**IMPORTANTE:** Nunca subir el `Client ID` ni el `Client Secret` a GitHub. Estas credenciales deben compartirse por un canal privado (WhatsApp, Discord, etc.).

Para que cualquier integrante pueda probar el inicio de sesion con Google en su entorno local (ya sea `http://localhost:8000` nativo o `http://inventario.localhost:8080` en Docker), debe seguir este flujo:

1. **Solicitar acceso de prueba:** El integrante debe enviar su correo de Gmail real al administrador de la cuenta de Google Cloud del proyecto, para que este lo agregue a la lista de **Usuarios de prueba** en la *Pantalla de consentimiento de OAuth*. Si no esta en esta lista, Google mostrara un error de "Acceso bloqueado".
2. **Obtener las claves:** Recibir por privado el `Client ID` y `Client Secret`.
3. **Registrar el usuario localmente:** 
   - Iniciar sesion en Frappe con un administrador local (ej. `superadmin@cedhi.local`).
   - Ir a la lista de **Usuarios** y cambiar el correo del SuperAdministrador por el correo de Gmail real, o crear un usuario nuevo con ese Gmail.
4. **Configurar el Social Login:**
   - Buscar **Social Login Key** en la barra superior de Frappe y configurar el proveedor **Google**.
   - Marcar **Enable Social Login**.
   - Pegar el `Client ID` y `Client Secret`.
   - Guardar (el sistema configurara automaticamente la URL base segun el puerto que esten usando).
5. **Probar:** Cerrar sesion local y utilizar el boton de Google.

## Reportes y workspace

Workspace:

```text
Inventario CEDHI
```

Reportes iniciales:

- `Resumen Inventario por Modulo`
- `Stock Critico Gastronomia`
- `Inventario TI por Ubicacion`
- `Gastronomia sin Stock Critico`

## Flujo de alertas

Las alertas no nacen principalmente desde los administradores. El flujo esperado del MVP es:

```text
Profesor o usuario reportante
-> crea una Alerta de Inventario
-> el sistema toma modulo y ubicacion desde el articulo
-> Admin TI / Admin Cocina / Admin General revisa segun su modulo
-> SuperAdministrador Inventario puede ver todas las alertas
```

Permisos principales:

- `Reportante`: puede crear alertas y ver sus propias alertas.
- `Admin TI`: recibe y gestiona alertas del modulo TI.
- `Admin Cocina`: recibe y gestiona alertas del modulo Gastronomia.
- `Admin General`: recibe y gestiona alertas del modulo General.
- `Revisor`: puede leer alertas, sin resolverlas.
- `SuperAdministrador Inventario`: ve y gestiona todas.

Al crear una alerta, el sistema completa automaticamente:

- `Reportado por`
- `Fecha de reporte`
- `Modulo`
- `Ubicacion`

Los usuarios con rol `Reportante` deben tener configurado en su ficha de usuario:

- `Modulo asignado`
- `Ubicacion asignada`

Esto permite representar PCs o usuarios de reporte ubicados en un laboratorio, cocina o ambiente especifico. Por ejemplo:

```text
profesor.lab01@cedhi.local
Rol: Reportante
Modulo asignado: TI
Ubicacion asignada: Laboratorio 1
```

Con esa configuracion, el reportante solo puede seleccionar articulos de su ubicacion asignada al crear alertas.

## Flujo de trabajo con Git

La rama compartida principal del proyecto es:

```bash
develop
```

Antes de trabajar:

```bash
git checkout develop
git pull
```

Crear una rama por tarea:

```bash
git checkout -b feature/nombre-de-la-tarea
```

Ejemplos:

```text
feature/dashboard-inventario
feature/alertas-stock
feature/reportes-gastronomia
feature/documentacion-video
```

Al terminar:

```bash
git add .
git commit -m "Descripcion breve del cambio"
git push -u origin feature/nombre-de-la-tarea
```

Luego abrir un Pull Request hacia `develop`.

## Documentacion del proyecto

- `docs/guia_inicio_proyecto.md`
- `docs/analisis_datos_iniciales.md`
- `docs/arquitectura_base_datos.md`
- `PRD_ Sistema de Inventario Integral1.pdf`
- `Defincion MVP  Proyecto de Prácticas Sociales ABS 2026-01 (1).pdf`

## Licencia

MIT
