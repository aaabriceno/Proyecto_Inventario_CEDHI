"""Importador idempotente del catalogo inicial del CEDHI.

Carga los CSV de `datos_iniciales/csv/` al DocType `Articulo de Inventario` sin
duplicar y resolviendo las Ubicaciones/Asignaciones por NOMBRE (no por el id
interno del CSV, que solo existe en la BD donde se exporto). Asi funciona en
cualquier despliegue (local, contenedor, Oracle, CEDHI).

Deduplicacion segun la naturaleza de cada modulo:
- Gastronomia: la clave es nombre_articulo + grupo + categoria (un insumo como
  "arroz" existe una sola vez; el stock se mide en kg/L, no se cuentan unidades).
- TI / General: la clave es codigo_interno (cada activo fisico es unico por
  serie/codigo: cada mouse, silla o pizarra es un registro propio).

Re-ejecutar este importador NO crea duplicados: actualiza el registro existente
o lo salta.
"""

import csv
import os

import frappe

CSV_DIR = os.path.join("datos_iniciales", "csv")

# Mapa de los ids internos usados en los CSV exportados -> nombre canonico de la
# Ubicacion/Asignacion. Se resuelve a nombre para luego buscar/crear por nombre.
LEGACY_ID_TO_NAME = {
	"54achd64fg": "Cocina Principal",
	"86ao0esop6": "Cocina Principal",
	"11uanrj2fc": "Laboratorio de computo",
	"11v6pin4jc": "Laboratorio de computo",
	"11vp24qu4s": "Almacen Soldadura",
	"11vlr1tlff": "Almacen Soldadura",
}

# Ubicaciones/Asignaciones canonicas con su modulo. Se crean si no existen.
CANONICAL_PLACES = {
	"Cocina Principal": "Gastronomia",
	"Laboratorio de computo": "TI",
	"Almacen Soldadura": "TI",
}

# Archivos a importar y su modulo.
CSV_FILES = [
	("import_articulos_gastronomia.csv", "Gastronomia"),
	("import_articulos_gastronomia_licores.csv", "Gastronomia"),
	("import_articulos_ti_sala_computo.csv", "TI"),
]


def _resolve_place_name(raw_value):
	"""Convierte un valor del CSV (id legacy o ya un nombre) al nombre canonico."""
	if not raw_value:
		return None
	value = raw_value.strip()
	return LEGACY_ID_TO_NAME.get(value, value)


def _ensure_place(doctype, place_name, modulo, name_field):
	"""Devuelve el name del registro Ubicacion/Asignacion, creandolo si falta.

	Busca por el campo de nombre (no por id), de forma que el catalogo quede
	enlazado correctamente en cualquier BD.
	"""
	if not place_name:
		return None
	existing = frappe.db.get_value(doctype, {name_field: place_name})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": doctype,
		name_field: place_name,
		"modulo": modulo,
		"activo": "Si",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _gastronomy_key(row):
	return (
		(row.get("nombre_articulo") or "").strip().upper(),
		(row.get("grupo") or "").strip().upper(),
		(row.get("categoria") or "").strip().upper(),
	)


def _norm(value):
	"""Normaliza para comparar: trim + mayusculas. Vacio/None -> ''."""
	return (value or "").strip().upper()


def _find_existing_gastronomy(row):
	"""Busca un insumo de gastronomia ya cargado por nombre+grupo+categoria.

	Compara normalizado y tratando vacio == NULL (Frappe guarda los campos
	vacios como NULL, asi que un filtro `categoria=''` no los encontraria y
	generaria duplicados).
	"""
	nombre = _norm(row.get("nombre_articulo"))
	grupo = _norm(row.get("grupo"))
	categoria = _norm(row.get("categoria"))
	candidates = frappe.get_all(
		"Articulo de Inventario",
		filters={"modulo": "Gastronomia", "nombre_articulo": row.get("nombre_articulo", "").strip()},
		fields=["name", "nombre_articulo", "grupo", "categoria"],
	)
	for c in candidates:
		if _norm(c.nombre_articulo) == nombre and _norm(c.grupo) == grupo and _norm(c.categoria) == categoria:
			return c.name
	return None


def _find_existing_asset(row):
	"""Busca un activo TI/General ya cargado por codigo_interno."""
	codigo = (row.get("codigo_interno") or "").strip()
	if not codigo:
		return None
	return frappe.db.get_value(
		"Articulo de Inventario", {"codigo_interno": codigo}, "name"
	)


def _read_csv(path):
	with open(path, encoding="utf-8-sig") as f:
		return list(csv.DictReader(f))


def import_catalogo_inicial(only_module=None):
	"""Importa (idempotente) el catalogo inicial desde los CSV.

	:param only_module: si se indica ("Gastronomia"/"TI"/"General"), solo carga
		ese modulo. Por defecto carga todos.
	:return: resumen con creados/actualizados/saltados por archivo.
	"""
	# get_app_path -> .../inventario_cedhi/inventario_cedhi (paquete). Los CSV
	# viven en la raiz del repo (.../inventario_cedhi/datos_iniciales), un nivel
	# arriba del paquete.
	app_path = os.path.dirname(frappe.get_app_path("inventario_cedhi"))
	# Asegura ubicaciones/asignaciones canonicas antes de enlazar articulos.
	for place_name, modulo in CANONICAL_PLACES.items():
		_ensure_place("Ubicacion", place_name, modulo, "nombre_ubicacion")
		_ensure_place("Asignacion", place_name, modulo, "nombre_asignacion")

	resumen = {}
	for filename, modulo in CSV_FILES:
		if only_module and modulo != only_module:
			continue
		path = os.path.join(app_path, CSV_DIR, filename)
		if not os.path.exists(path):
			resumen[filename] = {"error": "archivo no encontrado"}
			continue

		creados = actualizados = saltados = 0
		for row in _read_csv(path):
			row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
			row["modulo"] = modulo

			# Resolver ubicacion/asignacion por nombre canonico -> name local.
			ubic_name = _resolve_place_name(row.get("ubicacion"))
			asig_name = _resolve_place_name(row.get("asignacion"))
			row["ubicacion"] = _ensure_place("Ubicacion", ubic_name, modulo, "nombre_ubicacion") if ubic_name else None
			row["asignacion"] = _ensure_place("Asignacion", asig_name, modulo, "nombre_asignacion") if asig_name else None

			# Deduplicacion segun el modulo.
			if modulo == "Gastronomia":
				existing = _find_existing_gastronomy(row)
			else:
				existing = _find_existing_asset(row)

			if existing:
				# Actualiza stock/datos sin duplicar.
				doc = frappe.get_doc("Articulo de Inventario", existing)
				_apply_row(doc, row)
				doc.save(ignore_permissions=True)
				actualizados += 1
			else:
				doc = frappe.new_doc("Articulo de Inventario")
				_apply_row(doc, row)
				doc.insert(ignore_permissions=True)
				creados += 1

		frappe.db.commit()
		resumen[filename] = {
			"modulo": modulo,
			"creados": creados,
			"actualizados": actualizados,
			"saltados": saltados,
		}

	return resumen


# Campos del CSV que se copian tal cual al DocType (los que existen como campo).
_COPY_FIELDS = [
	"nombre_articulo", "descripcion", "modulo", "ubicacion", "asignacion",
	"estado", "fecha_de_adquisición", "marca", "modelo", "codigo_interno",
	"cantidad", "estado_conservacion", "stock_actual", "stock_critico",
	"unidad_medida", "es_perecible", "grupo", "categoria", "presentacion",
	"proveedor_referencia", "medida", "porcentaje_desperdicio", "cantidad_minima",
	"precio_referencial", "fuente_datos", "hoja_origen", "numero_origen",
]


_NUMERIC_FIELDS = {
	"stock_actual", "stock_critico", "cantidad", "medida",
	"porcentaje_desperdicio", "cantidad_minima", "precio_referencial",
}


def _to_number(value):
	try:
		return float(str(value).replace(",", "").strip())
	except (ValueError, TypeError):
		return 0


def _apply_row(doc, row):
	meta = doc.meta
	for field in _COPY_FIELDS:
		if field not in row:
			continue
		value = row[field]
		if value in (None, ""):
			continue
		if not meta.has_field(field):
			continue
		# Los campos numericos del CSV llegan como string: convertir, porque la
		# notificacion de stock critico compara numericamente y rompe con strings.
		if field in _NUMERIC_FIELDS:
			doc.set(field, _to_number(value))
		else:
			doc.set(field, value)

	# Garantiza stock numerico (nunca None) aunque la fila no lo traiga.
	for numeric_field in ("stock_actual", "stock_critico", "cantidad"):
		if meta.has_field(numeric_field) and doc.get(numeric_field) in (None, ""):
			doc.set(numeric_field, 0)


@frappe.whitelist()
def importar_catalogo_inicial(only_module=None):
	"""Endpoint llamable desde la UI (boton del workspace).

	Solo SuperAdministrador / System Manager pueden ejecutarlo, ya que carga el
	catalogo maestro. Se encola en background (ver encolar_catalogo_inicial):
	con ~1150 filas, correrlo dentro del request HTTP excede el timeout de
	nginx en produccion (proxy_read_timeout) aunque localmente parezca rapido.
	"""
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para importar el catalogo inicial.")
	return encolar_catalogo_inicial(only_module=only_module)


_CATALOGO_INICIAL_CACHE_KEY = "cedhi_catalogo_inicial_status"


def encolar_catalogo_inicial(only_module=None):
	"""Encola el import en background y devuelve de inmediato.

	El job real (_run_catalogo_inicial_job) corre fuera del request HTTP: con
	~1150 filas, ejecutarlo dentro del request excede el timeout de nginx en
	produccion (proxy_read_timeout) aunque localmente parezca rapido y termine
	bien. El estado se guarda en cache (no hay cliente de socketio cargado en
	esta pagina web publica) y se consulta por polling desde el frontend.
	"""
	frappe.cache().set_value(_CATALOGO_INICIAL_CACHE_KEY, {"status": "running"}, expires_in_sec=3600)
	frappe.enqueue(
		"inventario_cedhi.data_import._run_catalogo_inicial_job",
		queue="long",
		timeout=3600,
		job_name="cargar_catalogo_inicial",
		only_module=only_module,
	)
	return {"queued": True}


def _run_catalogo_inicial_job(only_module=None):
	"""Ejecuta el import real (llamado por el worker, no por el request HTTP)."""
	try:
		resumen = import_catalogo_inicial(only_module=only_module)
		frappe.cache().set_value(
			_CATALOGO_INICIAL_CACHE_KEY, {"status": "done", "resumen": resumen}, expires_in_sec=3600
		)
	except Exception:
		frappe.log_error(title="Carga de catalogo inicial CEDHI", message=frappe.get_traceback())
		frappe.cache().set_value(
			_CATALOGO_INICIAL_CACHE_KEY, {"status": "error", "error": str(frappe.get_traceback())}, expires_in_sec=3600
		)


@frappe.whitelist()
def consultar_estado_catalogo_inicial():
	"""Endpoint de polling para que la pagina sepa si el job ya termino."""
	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}:
		frappe.throw("No tiene permiso para consultar esta carga.")
	return frappe.cache().get_value(_CATALOGO_INICIAL_CACHE_KEY) or {"status": "idle"}


# --- Exportador de plantilla de importacion para el CEDHI -------------------

# Columnas de la plantilla por modulo. El CEDHI llena estas columnas para cargar
# articulos nuevos a futuro; coinciden con los campos del importador.
PLANTILLA_COLUMNS = {
	"Gastronomia": [
		"nombre_articulo", "descripcion", "grupo", "categoria", "marca",
		"unidad_medida", "presentacion", "proveedor_referencia", "es_perecible",
		"stock_actual", "stock_critico", "cantidad_minima", "precio_referencial",
		"ubicacion", "estado",
	],
	"TI": [
		"nombre_articulo", "descripcion", "marca", "modelo", "codigo_interno",
		"cantidad", "estado_conservacion", "ubicacion", "fecha_de_adquisición",
		"estado",
	],
	"General": [
		"nombre_articulo", "descripcion", "codigo_interno", "cantidad",
		"pabellon", "aula", "estado_conservacion", "ubicacion", "estado",
	],
}

# Fila de ejemplo orientativa por modulo (se incluye como segunda fila guia).
PLANTILLA_EJEMPLO = {
	"Gastronomia": {
		"nombre_articulo": "ARROZ EXTRA", "grupo": "ABARROTES", "categoria": "GRANOS",
		"unidad_medida": "KG", "es_perecible": "No", "stock_actual": "0",
		"stock_critico": "10", "ubicacion": "Cocina Principal", "estado": "Activo",
	},
	"TI": {
		"nombre_articulo": "MOUSE OPTICO", "marca": "LOGITECH", "modelo": "M90",
		"codigo_interno": "TI-0001", "cantidad": "1", "estado_conservacion": "B",
		"ubicacion": "Laboratorio de computo", "estado": "Activo",
	},
	"General": {
		"nombre_articulo": "SILLA APILABLE", "codigo_interno": "GEN-0001",
		"cantidad": "1", "pabellon": "A", "aula": "201",
		"ubicacion": "Aula General 201", "estado": "Activo",
	},
}


def generar_plantilla_csv(modulo):
	"""Devuelve el contenido CSV (texto) de una plantilla vacia para un modulo."""
	import io

	if modulo not in PLANTILLA_COLUMNS:
		frappe.throw(f"Modulo invalido: {modulo}. Use Gastronomia, TI o General.")

	columns = PLANTILLA_COLUMNS[modulo]
	buffer = io.StringIO()
	writer = csv.DictWriter(buffer, fieldnames=columns)
	writer.writeheader()
	# Fila de ejemplo orientativa.
	ejemplo = {c: PLANTILLA_EJEMPLO.get(modulo, {}).get(c, "") for c in columns}
	writer.writerow(ejemplo)
	return buffer.getvalue()


_MODULE_TEMPLATE_ROLE = {
	"TI": "Admin TI",
	"Gastronomia": "Admin Cocina",
	"General": "Admin General",
}


@frappe.whitelist()
def descargar_plantilla(modulo="Gastronomia"):
	"""Endpoint que descarga la plantilla de importacion de un modulo.

	El CEDHI usa este archivo para registrar articulos nuevos y luego cargarlos.
	Cada Admin de modulo solo puede descargar la plantilla de SU modulo, ya que
	el importador (validate_data_import_module_scope) tampoco le permitiria
	cargar articulos de otro modulo.
	"""
	roles = set(frappe.get_roles())
	full_access = roles & {"System Manager", "SuperAdministrador Inventario", "Administrator"}
	own_module_role = _MODULE_TEMPLATE_ROLE.get(modulo)
	if not full_access and own_module_role not in roles:
		frappe.throw("No tiene permiso para descargar la plantilla de este modulo.")

	contenido = generar_plantilla_csv(modulo)
	frappe.response["type"] = "download"
	frappe.response["filename"] = f"plantilla_{modulo.lower()}.csv"
	frappe.response["filecontent"] = contenido
	frappe.response["content_type"] = "text/csv"
