"""Importador de Articulo de Inventario desde la plantilla Excel real del
CEDHI (formato "CARITAS" con columna Modulo, ver datos_iniciales/).

Header en la fila 11 (B/R/M en fila 12), datos desde la fila 13. El
importador detecta automaticamente las columnas leyendo los nombres del
header en fila 11, por lo que funciona aunque distintos Excel tengan las
columnas en posiciones ligeramente distintas. Si no encuentra el header,
cae a las posiciones por defecto de "1. DIRECCION.xlsx":

  A=N  C=CANT.  E=DESCRIPCION  K=Identificador Unico  L=Modelo  M=SERIE
  N=MARCA  O=UBICACION  R=Modulo  S=Benefactor  T=FECHA ADQUISICION
  U/V/W=ESTADO (B/R/M)  X=OBSERVACIONES

Cada bien es individualizable (sillas, focos, equipos): si CANT.=N, se crea
N Articulo de Inventario por fila, cada uno con su propio `name` (hash
permanente que Frappe genera de por vida, cantidad=1 en cada uno) -- no un
solo registro con cantidad=N. Asi se puede trasladar/dar de baja una unidad
sin afectar las demas.

Idempotente: usa fuente_datos+hoja_origen+numero_origen+secuencia_unidad
para no duplicar si se re-ejecuta sobre el mismo archivo/fila.
"""

import os

import frappe
import openpyxl

DATOS_INICIALES_DIR = "datos_iniciales"

HEADER_ROW = 11
FIRST_DATA_ROW = 13

# Posiciones por defecto (fallback si el header no se detecta automaticamente).
# Confirmadas en "1. DIRECCION.xlsx".
COL_CANTIDAD = 3
COL_DESCRIPCION = 5
COL_IDENTIFICADOR_UNICO = 11
COL_MODELO = 12
COL_SERIE = 13
COL_MARCA = 14
COL_UBICACION = 15
COL_MODULO = 18
COL_BENEFACTOR = 19
COL_FECHA_ADQUISICION = 20
COL_ESTADO_B = 21
COL_ESTADO_R = 22
COL_ESTADO_M = 23
COL_OBSERVACIONES = 24

# Mapeo de columna_name -> lista de palabras clave (se prueban en orden,
# se asigna la primera columna del header que contenga alguna de ellas).
# Mas especifico primero para evitar falsos positivos.
_HEADER_MAP = [
    ("COL_CANTIDAD",           ["cant."]),
    ("COL_DESCRIPCION",        ["descripci"]),
    ("COL_IDENTIFICADOR_UNICO",["identificador"]),
    ("COL_UBICACION",          ["ubicaci"]),
    ("COL_MODULO",             ["modulo"]),
    ("COL_BENEFACTOR",         ["benefactor", "venefactor"]),
    ("COL_FECHA_ADQUISICION",  ["adquisici"]),
    ("COL_OBSERVACIONES",      ["observaci"]),
    ("COL_MARCA",              ["marca"]),
    # MODELO y SERIE son ambiguos (en algunos Excel el orden se invierte),
    # se asignan al primer match que NO sea ya "MARCA".
    ("COL_MODELO",             ["modelo"]),
    ("COL_SERIE",              ["serie"]),
]


def _detect_columns(ws):
    """Lee el header en HEADER_ROW y devuelve un dict col_name -> numero_columna.

    Si no puede detectar las columnas criticas (UBICACION, MODULO, CANTIDAD),
    devuelve None para que el llamador use las constantes por defecto.
    """
    # Recopilar todos los valores del header una sola vez.
    header = {}
    for col in range(1, ws.max_column + 1):
        val = ws.cell(row=HEADER_ROW, column=col).value
        if val:
            header[col] = str(val).lower().strip()

    cols = {}
    for col_name, keywords in _HEADER_MAP:
        for col, val_lower in header.items():
            if any(kw in val_lower for kw in keywords):
                if col_name not in cols and col not in cols.values():
                    cols[col_name] = col
                    break

    # Las 3 criticas deben estar presentes para confiar en la deteccion.
    if all(k in cols for k in ("COL_UBICACION", "COL_MODULO", "COL_CANTIDAD")):
        return cols
    return None

ESTADO_MAP = {
	"b": "Activo",
	"r": "En reparación",
	"m": "De baja",
}


def _clean(value):
	if value is None:
		return ""
	return str(value).strip()



def _resolve_ubicacion(nombre):
	nombre = _clean(nombre)
	if not nombre:
		return None
	existing = frappe.db.get_value("Ubicacion", {"nombre_ubicacion": nombre})
	if existing:
		return existing
	# Busqueda case-insensitive antes de crear, para no duplicar por
	# diferencias de mayusculas/espacios entre el Excel y la Ubicacion ya creada.
	candidatos = frappe.get_all("Ubicacion", filters={"nombre_ubicacion": ["like", nombre]}, pluck="name")
	for c in candidatos:
		if c.strip().upper() == nombre.upper():
			return c
	return None


def _resolve_modulo(nombre):
	nombre = _clean(nombre)
	if not nombre:
		return None
	if frappe.db.exists("Modulo", nombre):
		return nombre
	candidatos = frappe.get_all("Modulo", pluck="name")
	for c in candidatos:
		if c.strip().upper() == nombre.upper():
			return c
	return None


def importar_articulos_excel(filename, sheet_name=None, dry_run=False, full_path=None):
	"""Importa los articulos de una hoja del Excel `filename` (dentro de
	datos_iniciales/, salvo que se pase `full_path`). Si `sheet_name` es
	None, usa la primera hoja.

	`full_path`: ruta absoluta a usar en vez de buscar `filename` dentro de
	DATOS_INICIALES_DIR -- usado por la subida desde la UI
	(importar_excel_subido_endpoint), donde el archivo vive como adjunto
	Frappe File fuera del repo, no en datos_iniciales/. `filename` sigue
	usandose como fuente_datos/trazabilidad aunque se use full_path.

	Devuelve un resumen: creados, saltados (ya existian), errores (fila ->
	motivo, ej. ubicacion/modulo no encontrado). Ademas de los counts (para
	no romper a quien ya consume `creados`/`saltados` como `len()`), incluye
	`detalle_creados`/`detalle_saltados`/`detalle_errores`: listas de dict
	con los datos de cada fila (nombre, ubicacion, modulo, motivo de error)
	-- usado por la pagina de subida con preview (www/importar_articulos)
	para mostrar una tabla legible antes de tocar la BD, no solo un conteo.
	"""
	if full_path:
		path = full_path
	else:
		# os.path.basename evita path traversal (ej. filename="../../etc/passwd"):
		# sin esto, un filename con ".." podria escapar de DATOS_INICIALES_DIR.
		app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
		path = os.path.join(app_path, DATOS_INICIALES_DIR, os.path.basename(filename))
	if not os.path.isfile(path):
		frappe.throw(f"No se encontro el archivo {path}")

	wb = openpyxl.load_workbook(path, data_only=True)
	sheet_name = sheet_name or wb.sheetnames[0]
	ws = wb[sheet_name]

	# Detectar columnas por nombre de header (robusto ante columnas desplazadas).
	# Si la deteccion falla, usar las constantes por defecto.
	detected = _detect_columns(ws)
	col_cantidad          = detected.get("COL_CANTIDAD", COL_CANTIDAD) if detected else COL_CANTIDAD
	col_descripcion       = detected.get("COL_DESCRIPCION", COL_DESCRIPCION) if detected else COL_DESCRIPCION
	col_id_unico          = detected.get("COL_IDENTIFICADOR_UNICO", COL_IDENTIFICADOR_UNICO) if detected else COL_IDENTIFICADOR_UNICO
	col_modelo            = detected.get("COL_MODELO", COL_MODELO) if detected else COL_MODELO
	col_serie             = detected.get("COL_SERIE", COL_SERIE) if detected else COL_SERIE
	col_marca             = detected.get("COL_MARCA", COL_MARCA) if detected else COL_MARCA
	col_ubicacion         = detected.get("COL_UBICACION", COL_UBICACION) if detected else COL_UBICACION
	col_modulo            = detected.get("COL_MODULO", COL_MODULO) if detected else COL_MODULO
	col_fecha_adquisicion = detected.get("COL_FECHA_ADQUISICION", COL_FECHA_ADQUISICION) if detected else COL_FECHA_ADQUISICION
	col_observaciones     = detected.get("COL_OBSERVACIONES", COL_OBSERVACIONES) if detected else COL_OBSERVACIONES

	# Las columnas de ESTADO B/R/M estan en la fila 12 (sub-header), no en la
	# fila 11 del header principal -- no se detectan por nombre, se calculan
	# a partir de la columna ESTADO detectada o se usan las constantes fijas.
	# En todos los Excel vistos, B/R/M siempre estan justo despues de FECHA
	# ADQUISICION, asi que si detectamos col_fecha_adquisicion podemos derivarlas.
	if detected and "COL_FECHA_ADQUISICION" in detected:
		col_estado_b = col_fecha_adquisicion + 1
		col_estado_r = col_fecha_adquisicion + 2
		col_estado_m = col_fecha_adquisicion + 3
	else:
		col_estado_b = COL_ESTADO_B
		col_estado_r = COL_ESTADO_R
		col_estado_m = COL_ESTADO_M

	creados = []
	saltados = []
	errores = []
	detalle_creados = []
	detalle_saltados = []
	detalle_errores = []

	for row in range(FIRST_DATA_ROW, ws.max_row + 1):
		numero_origen = ws.cell(row=row, column=1).value
		descripcion = _clean(ws.cell(row=row, column=col_descripcion).value)
		if numero_origen is None and not descripcion:
			continue

		cantidad_raw = ws.cell(row=row, column=col_cantidad).value
		try:
			cantidad = int(float(cantidad_raw)) if cantidad_raw not in (None, "") else 0
		except (ValueError, TypeError):
			cantidad = 0
		if cantidad <= 0:
			motivo = f"cantidad invalida ({cantidad_raw!r}), fila saltada"
			errores.append((row, motivo))
			detalle_errores.append({"row": row, "nombre_articulo": descripcion, "motivo": motivo})
			continue

		ubicacion_nombre = _clean(ws.cell(row=row, column=col_ubicacion).value)
		ubicacion = _resolve_ubicacion(ubicacion_nombre)
		if not ubicacion:
			motivo = f"ubicacion '{ubicacion_nombre}' no encontrada en el sistema"
			errores.append((row, motivo))
			detalle_errores.append({"row": row, "nombre_articulo": descripcion, "motivo": motivo})
			continue

		modulo_nombre = _clean(ws.cell(row=row, column=col_modulo).value)
		modulo = _resolve_modulo(modulo_nombre)
		if not modulo:
			motivo = f"modulo '{modulo_nombre}' no encontrado en el sistema"
			errores.append((row, motivo))
			detalle_errores.append({"row": row, "nombre_articulo": descripcion, "motivo": motivo})
			continue

		# Estado B/R/M usando columnas detectadas dinamicamente.
		estado, estado_conservacion = None, None
		for col_e, codigo in ((col_estado_b, "b"), (col_estado_r, "r"), (col_estado_m, "m")):
			marca_estado = _clean(ws.cell(row=row, column=col_e).value).lower()
			if marca_estado:
				estado = ESTADO_MAP[codigo]
				estado_conservacion = codigo.upper()
				break
		if not estado:
			estado, estado_conservacion = "Activo", None

		marca = _clean(ws.cell(row=row, column=col_marca).value)
		modelo = _clean(ws.cell(row=row, column=col_modelo).value)
		serie = _clean(ws.cell(row=row, column=col_serie).value)
		if serie:
			modelo = f"{modelo} / Serie {serie}".strip(" /")
		observaciones = _clean(ws.cell(row=row, column=col_observaciones).value)
		fecha_adquisicion = ws.cell(row=row, column=col_fecha_adquisicion).value

		fuente_datos = filename
		hoja_origen = sheet_name

		for unidad in range(1, cantidad + 1):
			numero_origen_unidad = f"{numero_origen}-{unidad}" if cantidad > 1 else str(numero_origen)
			fila_detalle = {
				"row": row,
				"unidad": unidad,
				"nombre_articulo": descripcion,
				"ubicacion": ubicacion,
				"modulo": modulo,
				"marca": marca,
				"estado": estado,
			}

			ya_existe = frappe.db.exists("Articulo de Inventario", {
				"fuente_datos": fuente_datos,
				"hoja_origen": hoja_origen,
				"numero_origen": numero_origen_unidad,
			})
			if ya_existe:
				saltados.append((row, unidad))
				detalle_saltados.append(fila_detalle)
				continue

			if dry_run:
				creados.append((row, unidad))
				detalle_creados.append(fila_detalle)
				continue

			doc = frappe.get_doc({
				"doctype": "Articulo de Inventario",
				"nombre_articulo": descripcion,
				"descripcion": observaciones,
				"modulo": modulo,
				"ubicacion": ubicacion,
				"estado": estado,
				"estado_conservacion": estado_conservacion,
				# RF-C03 (require_estado_change_reason) exige motivo si estado != Activo.
				# El Excel no tiene un campo de "motivo" propio: se usa OBSERVACIONES si
				# la trae (ej. "inoperativo"), o un texto generico de importacion si no.
				"motivo_cambio_estado": (
					(observaciones or "Estado importado del inventario fisico del CEDHI; revisar motivo real.")
					if estado != "Activo" else ""
				),
				"marca": marca,
				"modelo": modelo,
				"cantidad": 1,
				"fecha_adquisicion": fecha_adquisicion if hasattr(fecha_adquisicion, "year") else None,
				"fuente_datos": fuente_datos,
				"hoja_origen": hoja_origen,
				"numero_origen": numero_origen_unidad,
			})
			doc.insert(ignore_permissions=True)
			creados.append((row, unidad))
			detalle_creados.append(fila_detalle)

	if not dry_run:
		frappe.db.commit()

	return {
		"archivo": filename,
		"hoja": sheet_name,
		"creados": len(creados),
		"saltados": len(saltados),
		"errores": errores,
		"detalle_creados": detalle_creados,
		"detalle_saltados": detalle_saltados,
		"detalle_errores": detalle_errores,
	}


IMPORT_ALLOWED_ROLES = {"System Manager", "SuperAdministrador Inventario", "Administrator"}


def _require_import_role():
	roles = set(frappe.get_roles())
	if not roles & IMPORT_ALLOWED_ROLES:
		frappe.throw("No tiene permiso para importar articulos.")


@frappe.whitelist()
def importar_articulos_excel_endpoint(filename, sheet_name=None, dry_run=False):
	_require_import_role()
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")
	return importar_articulos_excel(filename, sheet_name=sheet_name, dry_run=dry_run)


@frappe.whitelist()
def subir_excel_y_previsualizar():
	"""Recibe un .xlsx subido desde el navegador (www/importar_articulos),
	lo guarda como Frappe File privado (huerfano, sin doctype padre -- solo
	vive mientras el SuperAdmin decide confirmar o no), y corre el
	importador en `dry_run=True` sobre ese archivo para armar el preview.

	Devuelve el `file_name` (id del File) para que el paso de confirmar
	(`confirmar_importacion_excel_endpoint`) lo reutilice sin volver a
	subirlo, mas el resumen del dry_run (detalle_creados/saltados/errores).
	"""
	_require_import_role()

	if "file" not in frappe.request.files:
		frappe.throw("No se recibio ningun archivo.")
	upload = frappe.request.files["file"]
	if not upload.filename.lower().endswith(".xlsx"):
		frappe.throw("Solo se aceptan archivos .xlsx.")

	from frappe.utils.file_manager import save_file

	content = upload.stream.read()
	file_doc = save_file(upload.filename, content, None, None, is_private=1)

	sheet_name = None
	wb = openpyxl.load_workbook(file_doc.get_full_path(), data_only=True)
	sheet_name = wb.sheetnames[0]

	resultado = importar_articulos_excel(
		upload.filename,
		sheet_name=sheet_name,
		dry_run=True,
		full_path=file_doc.get_full_path(),
	)
	resultado["file_name"] = file_doc.name
	return resultado


@frappe.whitelist()
def confirmar_importacion_excel_endpoint(file_name, sheet_name=None):
	"""Confirma la importacion real (dry_run=False) sobre el File ya subido
	y previsualizado en `subir_excel_y_previsualizar`. No vuelve a recibir
	el archivo -- usa el mismo File guardado en el paso anterior.
	"""
	_require_import_role()

	file_doc = frappe.get_doc("File", file_name)
	full_path = file_doc.get_full_path()
	if not os.path.isfile(full_path):
		frappe.throw("El archivo subido ya no esta disponible, vuelva a subirlo.")

	resultado = importar_articulos_excel(
		file_doc.file_name or file_name,
		sheet_name=sheet_name,
		dry_run=False,
		full_path=full_path,
	)

	# El File temporal ya cumplio su proposito (se confirmo la importacion):
	# se borra para no acumular adjuntos huerfanos en el sistema.
	frappe.delete_doc("File", file_name, ignore_permissions=True, delete_permanently=True)
	frappe.db.commit()
	return resultado


UBICACIONES_MAESTRO_FILENAME = "UBICACIONES.xlsx"


def importar_ubicaciones_reales(full_path=None, dry_run=False):
	"""Crea (idempotente) las Ubicaciones reales del CEDHI a partir de la
	lista maestra `datos_iniciales/UBICACIONES.xlsx` (1 columna "Nombre
	Ubicacion", 1 fila por ubicacion).

	Antes esto escaneaba los nombres de archivo de la carpeta de Excel de
	articulos (INVENTARIO_2026/), lo cual mezclaba "que ubicaciones existen"
	con "que archivos de carga hay" -- una carpeta con archivos que no son
	ubicaciones (ej. INVENTARIO DE LICORES.xlsx) rompia esa inferencia. La
	lista maestra es la fuente de verdad explicita: agregar una ubicacion
	nueva es agregar una fila a este Excel y volver a cargar (las que ya
	existen se saltan, no se duplican).

	El modulo queda vacio: el CEDHI aun no ha definido a que modulo
	pertenece cada ubicacion (ej. Direccion no pertenece a ningun modulo),
	asi que no se fuerza un valor.

	`full_path`/`dry_run`: igual patron que `importar_articulos_excel` --
	permite subir un archivo nuevo desde el navegador
	(subir_ubicaciones_y_previsualizar) y previsualizar antes de tocar la BD.
	"""
	if full_path:
		path = full_path
	else:
		app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
		path = os.path.join(app_path, DATOS_INICIALES_DIR, UBICACIONES_MAESTRO_FILENAME)
	if not os.path.isfile(path):
		frappe.throw(f"No se encontro el archivo maestro de ubicaciones: {path}")

	wb = openpyxl.load_workbook(path, data_only=True)
	ws = wb[wb.sheetnames[0]]

	creadas = []
	saltadas = []
	for row in range(2, ws.max_row + 1):
		nombre = _clean(ws.cell(row=row, column=1).value)
		if not nombre:
			continue
		if frappe.db.exists("Ubicacion", {"nombre_ubicacion": nombre}):
			saltadas.append(nombre)
			continue
		if dry_run:
			creadas.append(nombre)
			continue
		doc = frappe.get_doc({
			"doctype": "Ubicacion",
			"nombre_ubicacion": nombre,
			"activo": "Si",
		})
		doc.insert(ignore_permissions=True)
		creadas.append(nombre)

	if not dry_run:
		frappe.db.commit()
	return {"creadas": creadas, "saltadas": saltadas}


@frappe.whitelist()
def importar_ubicaciones_reales_endpoint():
	"""Endpoint llamable desde la UI (boton del workspace Configuracion).

	Solo SuperAdministrador/System Manager pueden ejecutarlo, igual que la
	importacion de articulos. Es rapido (~30 registros): no necesita
	encolarse en background.
	"""
	_require_import_role()
	return importar_ubicaciones_reales()


@frappe.whitelist()
def subir_ubicaciones_y_previsualizar():
	"""Sube un .xlsx nuevo de ubicaciones desde el navegador y devuelve un
	preview (dry_run) sin tocar la BD -- mismo patron de 2 pasos que
	`subir_excel_y_previsualizar` (articulos).
	"""
	_require_import_role()

	if "file" not in frappe.request.files:
		frappe.throw("No se recibio ningun archivo.")
	upload = frappe.request.files["file"]
	if not upload.filename.lower().endswith(".xlsx"):
		frappe.throw("Solo se aceptan archivos .xlsx.")

	from frappe.utils.file_manager import save_file

	content = upload.stream.read()
	file_doc = save_file(upload.filename, content, None, None, is_private=1)

	resultado = importar_ubicaciones_reales(full_path=file_doc.get_full_path(), dry_run=True)
	resultado["file_name"] = file_doc.name
	return resultado


@frappe.whitelist()
def confirmar_importacion_ubicaciones_endpoint(file_name):
	"""Confirma la importacion real de Ubicaciones sobre el File ya subido
	y previsualizado en `subir_ubicaciones_y_previsualizar`.
	"""
	_require_import_role()

	file_doc = frappe.get_doc("File", file_name)
	full_path = file_doc.get_full_path()
	if not os.path.isfile(full_path):
		frappe.throw("El archivo subido ya no esta disponible, vuelva a subirlo.")

	resultado = importar_ubicaciones_reales(full_path=full_path, dry_run=False)

	frappe.delete_doc("File", file_name, ignore_permissions=True, delete_permanently=True)
	frappe.db.commit()
	return resultado


MODULOS_MAESTRO_FILENAME = "MODULOS.xlsx"


def importar_modulos_reales(full_path=None, dry_run=False):
	"""Crea (idempotente) los Modulo reales del CEDHI a partir de la lista
	maestra `datos_iniciales/MODULOS.xlsx` (1 columna "Nombre Modulo", 1 fila
	por modulo) -- mismo patron que `importar_ubicaciones_reales`.

	Insertar un Modulo dispara `Modulo.before_insert` (ver modulo.py), que
	autogenera el Role "Admin {nombre}" y sus permisos base -- no hace falta
	nada mas aqui.

	`full_path`/`dry_run`: igual patron que `importar_articulos_excel` --
	permite subir un archivo nuevo desde el navegador
	(subir_modulos_y_previsualizar) y previsualizar antes de tocar la BD.
	"""
	if full_path:
		path = full_path
	else:
		app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
		path = os.path.join(app_path, DATOS_INICIALES_DIR, MODULOS_MAESTRO_FILENAME)
	if not os.path.isfile(path):
		frappe.throw(f"No se encontro el archivo maestro de modulos: {path}")

	wb = openpyxl.load_workbook(path, data_only=True)
	ws = wb[wb.sheetnames[0]]

	creados = []
	saltados = []
	for row in range(2, ws.max_row + 1):
		nombre = _clean(ws.cell(row=row, column=1).value)
		if not nombre:
			continue
		if frappe.db.exists("Modulo", nombre):
			saltados.append(nombre)
			continue
		if dry_run:
			creados.append(nombre)
			continue
		doc = frappe.get_doc({
			"doctype": "Modulo",
			"nombre_modulo": nombre,
			"activo": "Si",
		})
		doc.insert(ignore_permissions=True)
		creados.append(nombre)

	if not dry_run:
		frappe.db.commit()
	return {"creados": creados, "saltados": saltados}


@frappe.whitelist()
def importar_modulos_reales_endpoint():
	"""Endpoint llamable desde la UI (boton del workspace Configuracion).

	Solo SuperAdministrador/System Manager pueden ejecutarlo, igual que el
	resto de importadores -- crear un Modulo ya esta restringido a esos roles
	en modulo.json, esto solo agrega el flujo masivo via Excel.
	"""
	_require_import_role()
	return importar_modulos_reales()


@frappe.whitelist()
def subir_modulos_y_previsualizar():
	"""Sube un .xlsx nuevo de modulos desde el navegador y devuelve un
	preview (dry_run) sin tocar la BD -- mismo patron de 2 pasos que
	`subir_excel_y_previsualizar` (articulos).
	"""
	_require_import_role()

	if "file" not in frappe.request.files:
		frappe.throw("No se recibio ningun archivo.")
	upload = frappe.request.files["file"]
	if not upload.filename.lower().endswith(".xlsx"):
		frappe.throw("Solo se aceptan archivos .xlsx.")

	from frappe.utils.file_manager import save_file

	content = upload.stream.read()
	file_doc = save_file(upload.filename, content, None, None, is_private=1)

	resultado = importar_modulos_reales(full_path=file_doc.get_full_path(), dry_run=True)
	resultado["file_name"] = file_doc.name
	return resultado


@frappe.whitelist()
def confirmar_importacion_modulos_endpoint(file_name):
	"""Confirma la importacion real de Modulos sobre el File ya subido y
	previsualizado en `subir_modulos_y_previsualizar`.
	"""
	_require_import_role()

	file_doc = frappe.get_doc("File", file_name)
	full_path = file_doc.get_full_path()
	if not os.path.isfile(full_path):
		frappe.throw("El archivo subido ya no esta disponible, vuelva a subirlo.")

	resultado = importar_modulos_reales(full_path=full_path, dry_run=False)

	frappe.delete_doc("File", file_name, ignore_permissions=True, delete_permanently=True)
	frappe.db.commit()
	return resultado


@frappe.whitelist()
def exportar_ubicaciones_excel():
	"""Genera un .xlsx con todas las Ubicacion existentes en la BD (nombre,
	modulo, activo) -- respaldo/vista rapida para el SuperAdmin, sin
	depender del export generico de Frappe.
	"""
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para exportar ubicaciones.")

	ubicaciones = frappe.get_all(
		"Ubicacion",
		fields=["nombre_ubicacion", "modulo", "activo"],
		order_by="nombre_ubicacion",
	)

	wb = openpyxl.Workbook()
	ws = wb.active
	ws.title = "Ubicaciones"
	ws.append(["Nombre Ubicacion", "Modulo", "Activo"])
	for u in ubicaciones:
		ws.append([u.nombre_ubicacion, u.modulo or "", u.activo or ""])

	frappe.local.response.filename = "ubicaciones_cedhi.xlsx"
	frappe.local.response.filecontent = _workbook_to_bytes(wb)
	frappe.local.response.type = "binary"


@frappe.whitelist()
def exportar_modulos_excel():
	"""Genera un .xlsx con todos los Modulo existentes en la BD (nombre,
	rol_admin) -- respaldo/vista rapida para el SuperAdmin.
	"""
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para exportar modulos.")

	modulos = frappe.get_all(
		"Modulo",
		fields=["nombre_modulo", "rol_admin"],
		order_by="nombre_modulo",
	)

	wb = openpyxl.Workbook()
	ws = wb.active
	ws.title = "Modulos"
	ws.append(["Nombre Modulo", "Rol Admin"])
	for m in modulos:
		ws.append([m.nombre_modulo, m.rol_admin or ""])

	frappe.local.response.filename = "modulos_cedhi.xlsx"
	frappe.local.response.filecontent = _workbook_to_bytes(wb)
	frappe.local.response.type = "binary"


def _workbook_to_bytes(wb):
	import io
	buffer = io.BytesIO()
	wb.save(buffer)
	return buffer.getvalue()


INSUMOS_GASTRONOMIA_FILENAME = "lista de insumos gastronomia.xlsx"
INSUMOS_GASTRONOMIA_SHEET = "INSUMOS"
INSUMOS_GASTRONOMIA_MODULO = "Gastronomia"
INSUMOS_GASTRONOMIA_UBICACION = "Almacen Gastronomia"

INSUMOS_HEADER_ROW = 1
INSUMOS_FIRST_DATA_ROW = 2

COL_INSUMO_CODIGO = 2
COL_INSUMO_GRUPO = 3
COL_INSUMO_CATEGORIA = 4
COL_INSUMO_MARCA = 5
COL_INSUMO_UNIDAD_MEDIDA = 6
COL_INSUMO_PRESENTACION = 7
COL_INSUMO_PROVEEDOR = 8
COL_INSUMO_NOMBRE = 9
COL_INSUMO_PERECEDERO = 10
COL_INSUMO_MEDIDA = 11
COL_INSUMO_DESPERDICIO = 12
COL_INSUMO_CANTIDAD_MINIMA = 13
COL_INSUMO_PRECIO_PRESENTACION = 18


def _to_float(value):
	try:
		return float(value) if value not in (None, "") else None
	except (ValueError, TypeError):
		return None


def importar_insumos_gastronomia(dry_run=False):
	"""Importa el catalogo de insumos perecibles de Gastronomia desde
	`datos_iniciales/lista de insumos gastronomia.xlsx` (hoja "INSUMOS").

	Formato distinto al de `importar_articulos_excel` (catalogo de insumos,
	no inventario fisico de bienes contados por ubicacion/CANT.): no trae
	columna Ubicacion ni Modulo -- se fija Modulo="Gastronomia" y
	Ubicacion="Almacen Gastronomia" (el area real del Excel de Gastronomia
	donde se almacenan estos insumos, ver datos_iniciales/20.GASTRONOMIA.xlsx
	hoja " ALMACEN ").

	El "Codigo Articulo" del Excel (1..~875) es un codigo de catalogo
	interno del CEDHI, no el identificador del sistema -- se usa solo para
	idempotencia (numero_origen), igual patron que importar_articulos_excel.
	El name/codigo_interno del Articulo los sigue generando el sistema como
	siempre, sin guardar ese codigo de catalogo en ningun campo propio.
	"""
	app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
	path = os.path.join(app_path, DATOS_INICIALES_DIR, INSUMOS_GASTRONOMIA_FILENAME)
	if not os.path.isfile(path):
		frappe.throw(f"No se encontro el archivo {path}")

	modulo = _resolve_modulo(INSUMOS_GASTRONOMIA_MODULO)
	if not modulo:
		frappe.throw(f"Modulo '{INSUMOS_GASTRONOMIA_MODULO}' no encontrado en el sistema")
	ubicacion = _resolve_ubicacion(INSUMOS_GASTRONOMIA_UBICACION)
	if not ubicacion:
		frappe.throw(f"Ubicacion '{INSUMOS_GASTRONOMIA_UBICACION}' no encontrada en el sistema")

	wb = openpyxl.load_workbook(path, data_only=True)
	ws = wb[INSUMOS_GASTRONOMIA_SHEET]

	creados = []
	saltados = []
	errores = []

	for row in range(INSUMOS_FIRST_DATA_ROW, ws.max_row + 1):
		codigo_origen = ws.cell(row=row, column=COL_INSUMO_CODIGO).value
		nombre_insumo = _clean(ws.cell(row=row, column=COL_INSUMO_NOMBRE).value)
		if codigo_origen is None and not nombre_insumo:
			continue
		if not nombre_insumo:
			errores.append((row, "sin Nombre Insumo, fila saltada"))
			continue

		numero_origen = str(codigo_origen)
		ya_existe = frappe.db.exists("Articulo de Inventario", {
			"fuente_datos": INSUMOS_GASTRONOMIA_FILENAME,
			"hoja_origen": INSUMOS_GASTRONOMIA_SHEET,
			"numero_origen": numero_origen,
		})
		if ya_existe:
			saltados.append(row)
			continue

		if dry_run:
			creados.append(row)
			continue

		perecedero_raw = _clean(ws.cell(row=row, column=COL_INSUMO_PERECEDERO).value).upper()
		es_perecible = "Si" if perecedero_raw == "SI" else "No"

		doc = frappe.get_doc({
			"doctype": "Articulo de Inventario",
			"nombre_articulo": nombre_insumo,
			"modulo": modulo,
			"ubicacion": ubicacion,
			"estado": "Activo",
			"marca": _clean(ws.cell(row=row, column=COL_INSUMO_MARCA).value),
			"cantidad": 1,
			"grupo": _clean(ws.cell(row=row, column=COL_INSUMO_GRUPO).value),
			"categoria": _clean(ws.cell(row=row, column=COL_INSUMO_CATEGORIA).value),
			"unidad_medida": _clean(ws.cell(row=row, column=COL_INSUMO_UNIDAD_MEDIDA).value),
			"presentacion": _clean(ws.cell(row=row, column=COL_INSUMO_PRESENTACION).value),
			"proveedor_referencia": _clean(ws.cell(row=row, column=COL_INSUMO_PROVEEDOR).value),
			"es_perecible": es_perecible,
			"medida": _to_float(ws.cell(row=row, column=COL_INSUMO_MEDIDA).value),
			"porcentaje_desperdicio": _to_float(ws.cell(row=row, column=COL_INSUMO_DESPERDICIO).value),
			"cantidad_minima": _to_float(ws.cell(row=row, column=COL_INSUMO_CANTIDAD_MINIMA).value),
			"precio_referencial": _to_float(ws.cell(row=row, column=COL_INSUMO_PRECIO_PRESENTACION).value),
			"fuente_datos": INSUMOS_GASTRONOMIA_FILENAME,
			"hoja_origen": INSUMOS_GASTRONOMIA_SHEET,
			"numero_origen": numero_origen,
		})
		doc.insert(ignore_permissions=True)
		creados.append(row)

	if not dry_run:
		frappe.db.commit()

	return {
		"archivo": INSUMOS_GASTRONOMIA_FILENAME,
		"creados": len(creados),
		"saltados": len(saltados),
		"errores": errores,
	}


@frappe.whitelist()
def importar_insumos_gastronomia_endpoint(dry_run=False):
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para importar insumos de gastronomia.")
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")
	return importar_insumos_gastronomia(dry_run=dry_run)
