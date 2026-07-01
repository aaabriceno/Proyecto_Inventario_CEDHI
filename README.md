# Sistema de Inventario CEDHI Nueva Arequipa

Sistema de gestion de inventario para el CEDHI Nueva Arequipa, construido sobre Frappe/ERPNext v15.

---

## Instalacion en Windows (para el CEDHI)

Esta es la forma recomendada. No requiere instalar Python, Node, MariaDB ni nada tecnico manualmente. Solo necesitas Docker Desktop.

### Requisitos previos

**1. Docker Desktop**

Descargalo e instalalo desde:
```
https://www.docker.com/products/docker-desktop/
```

Durante la instalacion, acepta todas las opciones por defecto. Cuando termine, reinicia Windows si te lo pide.

Verifica que Docker este corriendo: debe aparecer el icono de la ballena en la barra de tareas (abajo a la derecha). Si no aparece, abre Docker Desktop manualmente desde el menu Inicio.

**2. Git para Windows** (solo para la instalacion inicial)

Descargalo desde:
```
https://git-scm.com/download/win
```

Instala con todas las opciones por defecto. Esto te permite descargar el proyecto y actualizarlo despues.

---

### Paso 1 — Descargar el proyecto

Abre una ventana de **Simbolo del sistema** (cmd) o **PowerShell** y ejecuta:

```cmd
cd %USERPROFILE%
git clone -b develop https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git
cd Proyecto_Inventario_CEDHI\docker_setup
```

Esto descarga todo el proyecto en la carpeta `C:\Users\TuUsuario\Proyecto_Inventario_CEDHI\`.

---

### Paso 2 — Crear el archivo de configuracion

Dentro de la carpeta `docker_setup`, copia el archivo de ejemplo:

```cmd
copy .env.example .env
```

El archivo `.env` tiene la configuracion basica lista para usar. No necesitas cambiar nada para una instalacion estandar.

> **Nota:** Si quieres cambiar la contrasena del administrador, abre `.env` con el Bloc de notas y cambia el valor de `ADMIN_PASSWORD`. Por defecto es `admin`.

---

### Paso 3 — Permitir ejecucion de scripts en PowerShell (solo la primera vez)

Windows bloquea los scripts `.ps1` por defecto. Hay que habilitarlos una sola vez:

1. Busca **PowerShell** en el menu Inicio.
2. Haz clic derecho → **"Ejecutar como administrador"**.
3. Ejecuta este comando y responde `S` cuando pregunte:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

4. Cierra esa ventana de PowerShell.

---

### Paso 4 — Crear los accesos directos en el escritorio

Haz clic derecho en el archivo `crear_accesos_directos.ps1` (dentro de `docker_setup\windows\`) y selecciona **"Ejecutar con PowerShell"**.

Si Windows pregunta si deseas permitir la ejecucion, acepta.

Esto crea tres iconos en tu escritorio:
- **Iniciar Sistema CEDHI** — para el uso diario
- **Inventario CEDHI** — abre el sistema en el navegador
- **Actualizar Sistema CEDHI** — para cuando haya una version nueva

---

### Paso 5 — Primera instalacion (solo la primera vez)

Haz doble clic en **"Iniciar Sistema CEDHI"** en el escritorio.

La primera vez, Docker descarga e instala todo automaticamente (Frappe, ERPNext, la app del CEDHI, la base de datos). Esto puede tardar **entre 10 y 30 minutos** segun la velocidad de internet. Es normal que la ventana muestre muchos mensajes de texto durante este proceso.

Cuando el proceso termine, el sistema abrira el navegador automaticamente en:
```
http://inventario.localhost:8080
```

> **Si el navegador no abre solo:** espera 2 minutos mas y abre manualmente la direccion de arriba en tu navegador.

---

### Paso 6 — Primer ingreso al sistema

En la pantalla de login:

- **Usuario:** `Administrator`
- **Contrasena:** `admin` (o la que pusiste en `ADMIN_PASSWORD` del `.env`)

Al ingresar por primera vez, el sistema te mostrara el workspace de **Inventario CEDHI** con el menu principal.

---

### Uso diario

Para encender el sistema cada dia:

1. Haz doble clic en **"Iniciar Sistema CEDHI"** en el escritorio.
2. Espera que aparezca el mensaje de que el sistema esta listo (tarda unos 30-60 segundos).
3. El navegador abre automaticamente en `http://inventario.localhost:8080`.
4. Inicia sesion con tu usuario y contrasena.

Para apagar el sistema al final del dia, simplemente cierra la ventana del comando o deja Docker Desktop corriendo (no consume recursos importantes cuando no lo estan usando).

---

### Acceso desde otras computadoras de la misma red

Si la PC del CEDHI esta encendida con Docker corriendo, cualquier otra PC de la misma red wifi/cable puede entrar al sistema desde su navegador usando la **direccion IP** de la PC servidor.

Para saber la IP de la PC servidor:
1. Abre el Simbolo del sistema (cmd).
2. Escribe `ipconfig` y presiona Enter.
3. Busca el campo **"Direccion IPv4"** (ejemplo: `192.168.1.15`).

Desde otra PC de la red, abre el navegador y entra a:
```
http://192.168.1.15:8080
```
(cambia `192.168.1.15` por la IP real que encontraste)

> **Importante:** La IP puede cambiar si el router reasigna direcciones. Para que sea estable, configura una IP fija en Windows o una reserva DHCP en el router. Consulta con el administrador de red si esto ocurre.

---

### Actualizar el sistema cuando hay una version nueva

Cuando el equipo de desarrollo suba mejoras al sistema:

1. Haz doble clic en **"Actualizar Sistema CEDHI"** en el escritorio.
2. Espera que el proceso termine (puede tardar 5-15 minutos).
3. El sistema se reinicia con la version nueva sin perder los datos.

> **Nunca cierres la ventana a la mitad** de una actualizacion. Si algo falla, contacta al equipo de soporte.

---

## Primeros pasos dentro del sistema

### Crear usuarios

1. Ve al workspace **Configuracion** (menu principal > Configuracion).
2. Haz clic en **Usuarios**.
3. Crea un nuevo usuario con correo y contrasena.
4. Asignale un rol segun su funcion:

| Rol | Para quien |
|-----|-----------|
| SuperAdministrador Inventario | El encargado principal del sistema |
| Admin TI | Quien gestiona el inventario de TI |
| Admin Cocina | Quien gestiona el inventario de Gastronomia |
| Admin {Modulo} | Quien gestiona cualquier otro modulo |
| Revisor | Quien solo consulta, sin poder editar |
| Reportante | Quien solo reporta incidencias |

### Crear modulos

Si el CEDHI necesita un modulo nuevo (por ejemplo "Estilismo" o "Mobiliaria"):

1. Ve a **Configuracion > Gestion de Modulos**.
2. Crea un nuevo Modulo con el nombre.
3. El sistema autogenera automaticamente el rol `Admin {nombre}` con todos los permisos necesarios.

### Cargar ubicaciones

Las ubicaciones son los espacios fisicos del CEDHI (aulas, almacenes, oficinas, etc.).

**Opcion A — Subir un Excel** (recomendado para cargar muchas de una vez):
1. Ve a **Configuracion > Cargar Ubicaciones**.
2. En la seccion "Subir un archivo nuevo", selecciona tu archivo `.xlsx`.
   - El archivo debe tener una sola columna llamada `Nombre Ubicacion`, una ubicacion por fila.
3. Haz clic en **"Ver preview"** — el sistema te muestra cuantas ubicaciones se crearian sin tocar la base de datos.
4. Si el preview es correcto, haz clic en **"Confirmar importacion"**.

**Opcion B — Crear una por una**:
1. Ve a **Configuracion > Espacios Fisicos**.
2. Crea una nueva Ubicacion con el nombre.

### Cargar articulos

**Opcion A — Subir un Excel** (recomendado):
1. Ve a **Configuracion > Cargar Catalogo Excel**.
2. Selecciona tu archivo `.xlsx` con el formato de plantilla del CEDHI.
3. Haz clic en **"Ver preview"** — muestra cuantos articulos se crearian y cuales tienen error (ubicacion o modulo no encontrado).
4. Si el preview es correcto, confirma la importacion.

> **Importante:** Las ubicaciones y modulos que aparezcan en el Excel deben existir previamente en el sistema. Si el preview muestra errores de "ubicacion no encontrada", primero carga esa ubicacion y vuelve a intentarlo.

**Formato de la plantilla:**
- Header en la fila 11.
- Datos desde la fila 13.
- Columnas principales: N° (A), CANT. (C), DESCRIPCION (E), MODELO (L), SERIE (M), MARCA (N), UBICACION (O), MODULO (R), ESTADO B/R/M (U/V/W).

**Opcion B — Crear uno por uno**:
1. Ve a **Operaciones > Catalogo de Inventario**.
2. Crea un nuevo Articulo de Inventario llenando el formulario.

### Consultar un articulo por QR o codigo

Desde cualquier dispositivo (PC, celular, tablet) con el navegador:
```
http://<IP-del-servidor>:8080/consultar_articulo
```

Puedes pegar el codigo manualmente o usar la camara del celular para escanear el codigo QR de la etiqueta impresa.

### Registrar movimientos (Kardex)

1. Ve a **Operaciones > Kardex de Movimientos**.
2. Crea un nuevo Movimiento de Inventario.
3. Elige el tipo:
   - **Entrada**: suma cantidad al stock.
   - **Salida**: resta cantidad al stock.
   - **Ajuste**: fija el stock al valor exacto que indiques.

---

## Roles del sistema — resumen

| Rol | Ve todo | Edita articulos | Carga masiva | Crea modulos/usuarios |
|-----|---------|-----------------|--------------|----------------------|
| SuperAdministrador | Si | Si (todos) | Si | Si |
| Admin {Modulo} | Solo su modulo | Solo su modulo | No | No |
| Revisor | Si | No (solo Kardex) | No | No |
| Reportante | No | No | No | No |

---

## Solucionar problemas comunes

**El navegador no abre el sistema:**
- Verifica que Docker Desktop este corriendo (icono de ballena en la barra de tareas).
- Espera 1-2 minutos mas y recarga la pagina.
- Si el problema persiste, cierra y vuelve a ejecutar "Iniciar Sistema CEDHI".

**No puedo iniciar sesion:**
- Verifica que la contrasena sea correcta.
- Si olvidaste la contrasena del Administrator, contacta al equipo de soporte.

**El sistema va lento:**
- Cierra otras aplicaciones que esten usando mucha memoria.
- Reinicia Docker Desktop.

**La IP del servidor cambio y otras PCs no pueden conectar:**
- Confirma la IP actual con `ipconfig` en la PC servidor.
- Actualiza la direccion en el navegador de las otras PCs.
- Para evitar que cambie, configura IP fija o reserva DHCP en el router.

---

## Para desarrolladores

Ver `docs/guia_inicio_proyecto.md` para arquitectura, modelo de datos, convenciones del repo y flujo de desarrollo.

Repo: `https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git` — rama `develop`.
