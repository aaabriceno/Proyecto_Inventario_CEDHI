"""Importador de Articulo de Inventario desde la plantilla Excel real del
CEDHI (formato "CARITAS" con columna Modulo, ver datos_iniciales/INVENTARIO_2026/).

Header en la fila 11 (B/R/M en fila 12), datos desde la fila 13. Columnas
confirmadas en "1. DIRECCION.xlsx" (plantilla definitiva del encargado del
CEDHI, ya no cambia):

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

INVENTARIO_2026_DIR = os.path.join("datos_iniciales", "INVENTARIO_2026")

HEADER_ROW = 11
FIRST_DATA_ROW = 13

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

ESTADO_MAP = {
	"b": "Activo",
	"r": "En reparación",
	"m": "De baja",
}


def _clean(value):
	if value is None:
		return ""
	return str(value).strip()


def _estado_desde_fila(ws, row):
	"""Lee cual de las columnas B/R/M tiene una 'x' y devuelve el estado del sistema."""
	for col, codigo in ((COL_ESTADO_B, "b"), (COL_ESTADO_R, "r"), (COL_ESTADO_M, "m")):
		marca = _clean(ws.cell(row=row, column=col).value).lower()
		if marca:
			return ESTADO_MAP[codigo], codigo.upper()
	return "Activo", None


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


def importar_articulos_excel(filename, sheet_name=None, dry_run=False):
	"""Importa los articulos de una hoja del Excel `filename` (dentro de
	datos_iniciales/INVENTARIO_2026/). Si `sheet_name` es None, usa la primera hoja.

	Devuelve un resumen: creados, saltados (ya existian), errores (fila ->
	motivo, ej. ubicacion/modulo no encontrado).
	"""
	# os.path.basename evita path traversal (ej. filename="../../etc/passwd"):
	# sin esto, un filename con ".." podria escapar de INVENTARIO_2026_DIR.
	app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
	path = os.path.join(app_path, INVENTARIO_2026_DIR, os.path.basename(filename))
	if not os.path.isfile(path):
		frappe.throw(f"No se encontro el archivo {path}")

	wb = openpyxl.load_workbook(path, data_only=True)
	sheet_name = sheet_name or wb.sheetnames[0]
	ws = wb[sheet_name]

	creados = []
	saltados = []
	errores = []

	for row in range(FIRST_DATA_ROW, ws.max_row + 1):
		numero_origen = ws.cell(row=row, column=1).value
		descripcion = _clean(ws.cell(row=row, column=COL_DESCRIPCION).value)
		if numero_origen is None and not descripcion:
			continue

		cantidad_raw = ws.cell(row=row, column=COL_CANTIDAD).value
		try:
			cantidad = int(float(cantidad_raw)) if cantidad_raw not in (None, "") else 0
		except (ValueError, TypeError):
			cantidad = 0
		if cantidad <= 0:
			errores.append((row, f"cantidad invalida ({cantidad_raw!r}), fila saltada"))
			continue

		ubicacion_nombre = _clean(ws.cell(row=row, column=COL_UBICACION).value)
		ubicacion = _resolve_ubicacion(ubicacion_nombre)
		if not ubicacion:
			errores.append((row, f"ubicacion '{ubicacion_nombre}' no encontrada en el sistema"))
			continue

		modulo_nombre = _clean(ws.cell(row=row, column=COL_MODULO).value)
		modulo = _resolve_modulo(modulo_nombre)
		if not modulo:
			errores.append((row, f"modulo '{modulo_nombre}' no encontrado en el sistema"))
			continue

		estado, estado_conservacion = _estado_desde_fila(ws, row)

		marca = _clean(ws.cell(row=row, column=COL_MARCA).value)
		modelo = _clean(ws.cell(row=row, column=COL_MODELO).value)
		serie = _clean(ws.cell(row=row, column=COL_SERIE).value)
		if serie:
			modelo = f"{modelo} / Serie {serie}".strip(" /")
		observaciones = _clean(ws.cell(row=row, column=COL_OBSERVACIONES).value)
		fecha_adquisicion = ws.cell(row=row, column=COL_FECHA_ADQUISICION).value

		fuente_datos = filename
		hoja_origen = sheet_name

		for unidad in range(1, cantidad + 1):
			numero_origen_unidad = f"{numero_origen}-{unidad}" if cantidad > 1 else str(numero_origen)

			ya_existe = frappe.db.exists("Articulo de Inventario", {
				"fuente_datos": fuente_datos,
				"hoja_origen": hoja_origen,
				"numero_origen": numero_origen_unidad,
			})
			if ya_existe:
				saltados.append((row, unidad))
				continue

			if dry_run:
				creados.append((row, unidad))
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

	if not dry_run:
		frappe.db.commit()

	return {
		"archivo": filename,
		"hoja": sheet_name,
		"creados": len(creados),
		"saltados": len(saltados),
		"errores": errores,
	}


@frappe.whitelist()
def importar_articulos_excel_endpoint(filename, sheet_name=None, dry_run=False):
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para importar articulos.")
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")
	return importar_articulos_excel(filename, sheet_name=sheet_name, dry_run=dry_run)
