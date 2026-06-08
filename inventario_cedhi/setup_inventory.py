import frappe
import json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.password import update_password
from frappe.utils import cint


INVENTORY_MODULE = "Sistema de Gestión de Inventario CEDHI Nueva Arequipa"


def setup_inventory_mvp():
	"""Create and configure the complete MVP structure in the right order."""
	results = {}
	results["Core DocTypes"] = create_core_inventory_doctypes()
	results["Reference Data"] = ensure_initial_reference_data()
	results["Gastronomy Fields"] = add_gastronomy_catalog_fields()
	results["Import Traceability Fields"] = add_import_traceability_fields()
	results["Module Form Rules"] = configure_module_specific_article_form()
	results["Article Status Options"] = configure_article_status_options()
	results["Alert DocType"] = create_alerta_inventario_doctype()
	results["Movimiento DocType"] = create_movimiento_inventario_doctype()
	results["Movimiento Traceability"] = configure_movimiento_traceability_fields()
	results["Role Permissions"] = configure_inventory_role_permissions()
	results["List Views"] = configure_inventory_list_views()
	results["Reports"] = create_basic_inventory_reports()
	results["Number Cards"] = create_inventory_number_cards()
	results["Charts"] = create_inventory_charts()
	results["Client Scripts"] = create_inventory_client_scripts()
	results["Initial Users"] = create_initial_users()
	results["Workspace"] = create_inventory_workspace()
	results["Child Workspaces"] = create_child_workspaces()
	results["Hide Workspaces"] = hide_unwanted_workspaces()
	enforce_system_language()
	frappe.db.commit()
	frappe.clear_cache()
	return results


def create_core_inventory_doctypes():
	"""Create the base custom DocTypes required before fields/reports are configured."""
	ensure_inventory_module_def()
	results = {
		"Ubicacion": create_ubicacion_doctype(),
		"Asignacion": create_asignacion_doctype(),
		"Articulo de Inventario": create_articulo_inventario_doctype(),
	}
	frappe.db.commit()
	return results


def ensure_inventory_module_def():
	"""Ensure the app module exists for custom DocTypes and workspace links."""
	if frappe.db.exists("Module Def", INVENTORY_MODULE):
		return {"created": False, "module": INVENTORY_MODULE}

	module = frappe.get_doc(
		{
			"doctype": "Module Def",
			"module_name": INVENTORY_MODULE,
			"app_name": "inventario_cedhi",
			"custom": 1,
		}
	)
	module.insert(ignore_permissions=True)
	return {"created": True, "module": INVENTORY_MODULE}


def create_ubicacion_doctype():
	"""Create the Ubicacion DocType used as the physical inventory location."""
	doctype_name = "Ubicacion"
	fields = [
		{
			"fieldname": "datos_ubicacion_section",
			"label": "Datos de Ubicacion",
			"fieldtype": "Section Break",
		},
		{
			"fieldname": "nombre_ubicacion",
			"label": "Nombre de ubicacion",
			"fieldtype": "Data",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "modulo",
			"label": "Modulo",
			"fieldtype": "Select",
			"options": "TI\nGastronomia\nGeneral",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{"fieldname": "pabellon", "label": "Pabellon", "fieldtype": "Data"},
		{"fieldname": "aula", "label": "Aula", "fieldtype": "Data"},
		{
			"fieldname": "activo",
			"label": "Activo",
			"fieldtype": "Select",
			"options": "Si\nNo",
			"default": "Si",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	]
	return _create_or_update_core_doctype(doctype_name, fields, "nombre_ubicacion")


def create_asignacion_doctype():
	"""Create the Asignacion DocType used to group article responsibility."""
	doctype_name = "Asignacion"
	fields = [
		{
			"fieldname": "datos_asignacion_section",
			"label": "Datos de Asignacion",
			"fieldtype": "Section Break",
		},
		{
			"fieldname": "nombre_asignacion",
			"label": "Nombre de asignacion",
			"fieldtype": "Data",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "modulo",
			"label": "Modulo",
			"fieldtype": "Select",
			"options": "TI\nGastronomia\nGeneral",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "activo",
			"label": "Activo",
			"fieldtype": "Select",
			"options": "Si\nNo",
			"default": "Si",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	]
	return _create_or_update_core_doctype(doctype_name, fields, "nombre_asignacion")


def create_articulo_inventario_doctype():
	"""Create the main inventory article DocType."""
	doctype_name = "Articulo de Inventario"
	fields = [
		{
			"fieldname": "datos_generales_section",
			"label": "Datos Generales",
			"fieldtype": "Section Break",
		},
		{
			"fieldname": "nombre_articulo",
			"label": "Nombre del Articulo",
			"fieldtype": "Data",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{"fieldname": "descripcion", "label": "Descripcion", "fieldtype": "Small Text"},
		{
			"fieldname": "modulo",
			"label": "Modulo",
			"fieldtype": "Select",
			"options": "TI\nGastronomia\nGeneral",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "ubicacion",
			"label": "Ubicacion",
			"fieldtype": "Link",
			"options": "Ubicacion",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "asignacion",
			"label": "Asignacion",
			"fieldtype": "Link",
			"options": "Asignacion",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "estado",
			"label": "Estado",
			"fieldtype": "Select",
			"options": "Activo\nDe baja\nEn reparación",
			"default": "Activo",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{"fieldname": "fecha_adquisicion", "label": "Fecha de adquisicion", "fieldtype": "Date"},
		{
			"fieldname": "codigo_interno",
			"label": "Codigo interno",
			"fieldtype": "Data",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "datos_tecnicos_section",
			"label": "Datos Tecnicos",
			"fieldtype": "Section Break",
		},
		{"fieldname": "marca", "label": "Marca", "fieldtype": "Data"},
		{"fieldname": "modelo", "label": "Modelo", "fieldtype": "Data"},
		{"fieldname": "fotografia", "label": "Fotografia", "fieldtype": "Attach Image"},
		{
			"fieldname": "datos_de_stock_section",
			"label": "Datos de Stock",
			"fieldtype": "Section Break",
		},
		{"fieldname": "stock_actual", "label": "Stock actual", "fieldtype": "Float"},
		{"fieldname": "stock_critico", "label": "Stock critico", "fieldtype": "Float"},
		{"fieldname": "unidad_medida", "label": "Unidad de medida", "fieldtype": "Data"},
		{
			"fieldname": "es_perecible",
			"label": "Es perecible",
			"fieldtype": "Select",
			"options": "Si\nNo",
			"default": "No",
		},
		{"fieldname": "fecha_vencimiento", "label": "Fecha de vencimiento", "fieldtype": "Date"},
		{
			"fieldname": "trazabilidad_section",
			"label": "Trazabilidad",
			"fieldtype": "Section Break",
		},
		{
			"fieldname": "motivo_cambio_estado",
			"label": "Motivo de cambio de estado",
			"fieldtype": "Small Text",
		},
	]
	return _create_or_update_core_doctype(doctype_name, fields, "nombre_articulo")


def _create_or_update_core_doctype(doctype_name, fields, title_field):
	if frappe.db.exists("DocType", doctype_name):
		doc = frappe.get_doc("DocType", doctype_name)
		created = False
	else:
		doc = frappe.get_doc(
			{
				"doctype": "DocType",
				"name": doctype_name,
				"module": INVENTORY_MODULE,
				"custom": 1,
				"allow_import": 1,
				"fields": [],
				"permissions": [
					{
						"role": "System Manager",
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
						"report": 1,
						"export": 1,
						"import": 1,
						"print": 1,
						"email": 1,
					}
				],
			}
		)
		created = True

	doc.module = INVENTORY_MODULE
	doc.custom = 1
	doc.allow_import = 1
	doc.title_field = title_field
	doc.show_title_field_in_link = 1
	doc.show_name_in_global_search = 1

	existing = {df.fieldname: df for df in doc.fields}
	added = []
	updated = []
	next_idx = max((cint(df.idx) for df in doc.fields), default=0) + 1
	for field_data in fields:
		fieldname = field_data["fieldname"]
		if fieldname in existing:
			field = existing[fieldname]
			for key, value in field_data.items():
				if getattr(field, key, None) != value:
					setattr(field, key, value)
					if fieldname not in updated:
						updated.append(fieldname)
			continue
		
		row = doc.append("fields", field_data)
		row.idx = next_idx
		next_idx += 1
		added.append(fieldname)

	# Re-sort doc.fields to match the order of fields in the source code definition list
	field_order = {fd["fieldname"]: i for i, fd in enumerate(fields)}
	def get_field_sort_key(df):
		if df.fieldname in field_order:
			return (0, field_order[df.fieldname])
		else:
			return (1, cint(df.idx))
	
	doc.fields.sort(key=get_field_sort_key)
	for idx, df in enumerate(doc.fields, start=1):
		df.idx = idx

	if created:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	frappe.clear_cache(doctype=doctype_name)
	return {"created": created, "added_fields": added, "updated_fields": updated}


def add_gastronomy_catalog_fields():
	"""Add MVP catalog fields used by the gastronomy inventory import."""
	doctype_name = "Articulo de Inventario"
	doc = frappe.get_doc("DocType", doctype_name)
	existing = {df.fieldname for df in doc.fields}
	next_idx = max((cint(df.idx) for df in doc.fields), default=0) + 1

	fields = [
		{
			"fieldname": "datos_catalogo_gastronomia_section",
			"label": "Datos de Catalogo Gastronomia",
			"fieldtype": "Section Break",
		},
		{"fieldname": "grupo", "label": "Grupo", "fieldtype": "Data"},
		{"fieldname": "categoria", "label": "Categoria", "fieldtype": "Data"},
		{"fieldname": "presentacion", "label": "Presentacion", "fieldtype": "Data"},
		{
			"fieldname": "proveedor_referencia",
			"label": "Proveedor de referencia",
			"fieldtype": "Data",
		},
		{"fieldname": "medida", "label": "Medida", "fieldtype": "Float"},
		{
			"fieldname": "porcentaje_desperdicio",
			"label": "Porcentaje desperdicio",
			"fieldtype": "Percent",
		},
		{"fieldname": "cantidad_minima", "label": "Cantidad minima", "fieldtype": "Float"},
		{"fieldname": "precio_referencial", "label": "Precio referencial", "fieldtype": "Currency"},
	]

	added = []
	for field in fields:
		if field["fieldname"] in existing:
			continue
		row = doc.append("fields", field)
		row.idx = next_idx
		next_idx += 1
		added.append(field["fieldname"])

	if added:
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype=doctype_name)

	return {"added": added}


def configure_module_specific_article_form():
	"""Show article fields by inventory module and add General-module fields."""
	doctype_name = "Articulo de Inventario"
	doc = frappe.get_doc("DocType", doctype_name)
	existing = {df.fieldname for df in doc.fields}
	next_idx = max((cint(df.idx) for df in doc.fields), default=0) + 1

	fields = [
		{
			"fieldname": "datos_mobiliario_section",
			"label": "Datos de Mobiliario",
			"fieldtype": "Section Break",
		},
		{"fieldname": "pabellon", "label": "Pabellon", "fieldtype": "Data"},
		{"fieldname": "aula", "label": "Aula", "fieldtype": "Data"},
	]

	added = []
	for field in fields:
		if field["fieldname"] in existing:
			continue
		row = doc.append("fields", field)
		row.idx = next_idx
		next_idx += 1
		added.append(field["fieldname"])

	depends_on = {
		"datos_tecnicos_section": 'eval:doc.modulo=="TI"',
		"marca": 'eval:doc.modulo=="TI"',
		"modelo": 'eval:doc.modulo=="TI"',
		"datos_de_stock_section": 'eval:doc.modulo=="Gastronomia"',
		"stock_actual": 'eval:doc.modulo=="Gastronomia"',
		"stock_critico": 'eval:doc.modulo=="Gastronomia"',
		"unidad_medida": 'eval:doc.modulo=="Gastronomia"',
		"es_perecible": 'eval:doc.modulo=="Gastronomia"',
		"fecha_vencimiento": 'eval:doc.modulo=="Gastronomia"',
		"datos_catalogo_gastronomia_section": 'eval:doc.modulo=="Gastronomia"',
		"grupo": 'eval:doc.modulo=="Gastronomia"',
		"categoria": 'eval:doc.modulo=="Gastronomia"',
		"presentacion": 'eval:doc.modulo=="Gastronomia"',
		"proveedor_referencia": 'eval:doc.modulo=="Gastronomia"',
		"medida": 'eval:doc.modulo=="Gastronomia"',
		"porcentaje_desperdicio": 'eval:doc.modulo=="Gastronomia"',
		"cantidad_minima": 'eval:doc.modulo=="Gastronomia"',
		"precio_referencial": 'eval:doc.modulo=="Gastronomia"',
		"datos_mobiliario_section": 'eval:doc.modulo=="General"',
		"pabellon": 'eval:doc.modulo=="General"',
		"aula": 'eval:doc.modulo=="General"',
	}

	mandatory_depends_on = {
		"marca": 'eval:doc.modulo=="TI"',
		"modelo": 'eval:doc.modulo=="TI"',
		"unidad_medida": 'eval:doc.modulo=="Gastronomia"',
		"pabellon": 'eval:doc.modulo=="General"',
		"aula": 'eval:doc.modulo=="General"',
		"motivo_cambio_estado": 'eval:doc.estado!="Activo"',
	}

	for field in doc.fields:
		if field.fieldname in depends_on:
			field.depends_on = depends_on[field.fieldname]
		if field.fieldname in mandatory_depends_on:
			field.mandatory_depends_on = mandatory_depends_on[field.fieldname]
		if field.fieldname == "pabellon":
			field.fetch_from = "ubicacion.pabellon"
			field.fetch_if_empty = 1
		if field.fieldname == "aula":
			field.fetch_from = "ubicacion.aula"
			field.fetch_if_empty = 1

	doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(doctype=doctype_name)

	return {"added": added, "configured": sorted(depends_on)}


def configure_article_status_options():
	"""Ensure article status values match the PRD traceability states."""
	doctype_name = "Articulo de Inventario"
	if not frappe.db.exists("DocType", doctype_name):
		return {"updated": False, "reason": "missing doctype"}

	doc = frappe.get_doc("DocType", doctype_name)
	updated = False
	for field in doc.fields:
		if field.fieldname == "estado":
			field.fieldtype = "Select"
			field.options = "Activo\nDe baja\nEn reparación"
			field.default = "Activo"
			field.reqd = 1
			field.in_list_view = 1
			field.in_standard_filter = 1
			field.in_filter = 1
			updated = True
		if field.fieldname == "motivo_cambio_estado":
			field.mandatory_depends_on = 'eval:doc.estado!="Activo"'

	if updated:
		doc.save(ignore_permissions=True)
		frappe.db.set_value(
			doctype_name,
			{"estado": "Inactivo"},
			"estado",
			"De baja",
			update_modified=False,
		)
		frappe.db.commit()
		frappe.clear_cache(doctype=doctype_name)

	return {"updated": updated, "options": ["Activo", "De baja", "En reparación"]}


def fill_general_location_details_from_ubicacion():
	"""Copy Pabellon/Aula from linked Ubicacion into General inventory items."""
	items = frappe.get_all(
		"Articulo de Inventario",
		filters={"modulo": "General", "ubicacion": ["is", "set"]},
		fields=["name", "ubicacion", "pabellon", "aula"],
		limit_page_length=5000,
	)

	updated = []
	for item in items:
		ubicacion = frappe.db.get_value(
			"Ubicacion",
			item.ubicacion,
			["pabellon", "aula"],
			as_dict=True,
		)
		if not ubicacion:
			continue

		values = {}
		if not item.pabellon and ubicacion.pabellon:
			values["pabellon"] = ubicacion.pabellon
		if not item.aula and ubicacion.aula:
			values["aula"] = ubicacion.aula

		if values:
			frappe.db.set_value(
				"Articulo de Inventario",
				item.name,
				values,
				update_modified=False,
			)
			updated.append(item.name)

	frappe.db.commit()
	return {"updated": len(updated), "items": updated[:20]}


def add_import_traceability_fields():
	"""Add fields needed to preserve source Excel data during imports."""
	doctype_name = "Articulo de Inventario"
	doc = frappe.get_doc("DocType", doctype_name)
	existing = {df.fieldname for df in doc.fields}
	next_idx = max((cint(df.idx) for df in doc.fields), default=0) + 1

	fields = [
		{"fieldname": "cantidad", "label": "Cantidad", "fieldtype": "Float"},
		{
			"fieldname": "estado_conservacion",
			"label": "Estado de conservacion",
			"fieldtype": "Data",
		},
		{
			"fieldname": "trazabilidad_importacion_section",
			"label": "Trazabilidad de Importacion",
			"fieldtype": "Section Break",
		},
		{"fieldname": "fuente_datos", "label": "Fuente de datos", "fieldtype": "Data"},
		{"fieldname": "hoja_origen", "label": "Hoja origen", "fieldtype": "Data"},
		{"fieldname": "numero_origen", "label": "Numero origen", "fieldtype": "Data"},
	]

	added = []
	for field in fields:
		if field["fieldname"] in existing:
			continue
		row = doc.append("fields", field)
		row.idx = next_idx
		next_idx += 1
		added.append(field["fieldname"])

	for field in doc.fields:
		if field.fieldname == "cantidad":
			field.depends_on = 'eval:doc.modulo!="Gastronomia"'
		if field.fieldname == "estado_conservacion":
			field.depends_on = 'eval:doc.modulo!="Gastronomia"'

	if added:
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype=doctype_name)

	return {"added": added}


def ensure_initial_reference_data():
	"""Ensure import target locations and assignments exist; return their names."""
	records = [
		("Ubicacion", "nombre_ubicacion", "Laboratorio de computo", "TI"),
		("Ubicacion", "nombre_ubicacion", "Almacen Soldadura", "TI"),
		("Asignacion", "nombre_asignacion", "Laboratorio de computo", "TI"),
		("Asignacion", "nombre_asignacion", "Almacen Soldadura", "TI"),
	]
	result = {}
	for doctype, fieldname, value, modulo in records:
		name = frappe.db.get_value(doctype, {fieldname: value})
		if not name:
			doc = frappe.get_doc(
				{
					"doctype": doctype,
					fieldname: value,
					"modulo": modulo,
					"activo": "Si",
				}
			)
			doc.insert(ignore_permissions=True)
			name = doc.name
		result[f"{doctype}:{value}"] = name

	frappe.db.commit()
	return result


def mark_gastronomy_catalog_import_source():
	"""Mark the imported gastronomy catalog records with their source file."""
	names = frappe.get_all(
		"Articulo de Inventario",
		filters={
			"fuente_datos": ["is", "not set"],
			"modulo": "Gastronomia",
			"codigo_interno": ["!=", "GAS-0001"],
		},
		pluck="name",
		limit_page_length=2000,
	)

	for name in names:
		frappe.db.set_value(
			"Articulo de Inventario",
			name,
			{
				"fuente_datos": "lista de insumos gastronomia.xlsx",
				"hoja_origen": "INSUMOS",
			},
			update_modified=False,
		)

	frappe.db.commit()
	return {"updated": len(names)}


def configure_inventory_list_views():
	"""Configure list columns, standard filters, and saved filters for inventory."""
	doctype_name = "Articulo de Inventario"
	doc = frappe.get_doc("DocType", doctype_name)

	standard_filters = {
		"modulo",
		"grupo",
		"ubicacion",
		"estado",
		"stock_actual",
		"unidad_medida",
		"es_perecible",
		"categoria",
	}
	list_fields = {
		"nombre_articulo",
		"modulo",
		"ubicacion",
		"estado",
		"grupo",
		"stock_actual",
		"unidad_medida",
	}

	for field in doc.fields:
		if field.fieldname in standard_filters:
			field.in_standard_filter = 1
			field.in_filter = 1
		if field.fieldname in list_fields:
			field.in_list_view = 1

	doc.save(ignore_permissions=True)

	settings = frappe.db.exists("List View Settings", doctype_name)
	fields = [
		"`nombre_articulo`",
		"`modulo`",
		"`ubicacion`",
		"`estado`",
		"`grupo`",
		"`stock_actual`",
		"`unidad_medida`",
	]
	if settings:
		settings_doc = frappe.get_doc("List View Settings", doctype_name)
		is_new_settings = False
	else:
		settings_doc = frappe.get_doc({"doctype": "List View Settings", "name": doctype_name})
		is_new_settings = True
	settings_doc.total_fields = "7"
	settings_doc.fields = json.dumps(fields)
	if is_new_settings:
		settings_doc.insert(ignore_permissions=True)
	else:
		settings_doc.save(ignore_permissions=True)

	saved_filters = {
		"Inventario TI": [[doctype_name, "modulo", "=", "TI", False]],
		"Inventario Gastronomia": [[doctype_name, "modulo", "=", "Gastronomia", False]],
		"Inventario General": [[doctype_name, "modulo", "=", "General", False]],
		"Licores": [
			[doctype_name, "modulo", "=", "Gastronomia", False],
			[doctype_name, "grupo", "=", "LICORES", False],
		],
		"Gastronomia con Stock": [
			[doctype_name, "modulo", "=", "Gastronomia", False],
			[doctype_name, "stock_actual", ">", 0, False],
		],
	}

	created = []
	updated = []
	for filter_name, filters in saved_filters.items():
		name = frappe.db.exists(
			"List Filter",
			{"filter_name": filter_name, "reference_doctype": doctype_name},
		)
		payload = {
			"filter_name": filter_name,
			"reference_doctype": doctype_name,
			"filters": json.dumps(filters),
		}
		if name:
			filter_doc = frappe.get_doc("List Filter", name)
			filter_doc.update(payload)
			updated.append(filter_name)
		else:
			filter_doc = frappe.get_doc({"doctype": "List Filter", **payload})
			created.append(filter_name)
		filter_doc.save(ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache(doctype=doctype_name)

	return {"created_filters": created, "updated_filters": updated}


def create_alerta_inventario_doctype():
	"""Create the custom DocType used for inventory incidents and alerts."""
	doctype_name = "Alerta de Inventario"
	module = INVENTORY_MODULE

	if frappe.db.exists("DocType", doctype_name):
		return {"created": False, "doctype": doctype_name}

	doc = frappe.get_doc(
		{
			"doctype": "DocType",
			"name": doctype_name,
			"module": module,
			"custom": 1,
			"allow_import": 1,
			"title_field": "articulo",
			"show_title_field_in_link": 1,
			"fields": [
				{
					"fieldname": "datos_alerta_section",
					"label": "Datos de Alerta",
					"fieldtype": "Section Break",
				},
				{
					"fieldname": "articulo",
					"label": "Articulo",
					"fieldtype": "Link",
					"options": "Articulo de Inventario",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "tipo_alerta",
					"label": "Tipo de alerta",
					"fieldtype": "Select",
					"options": "Stock bajo\nDañado\nPerdido\nVencido\nAjuste de stock\nOtro",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "modulo",
					"label": "Modulo",
					"fieldtype": "Select",
					"options": "TI\nGastronomia\nGeneral",
					"fetch_from": "articulo.modulo",
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "ubicacion",
					"label": "Ubicacion",
					"fieldtype": "Link",
					"options": "Ubicacion",
					"fetch_from": "articulo.ubicacion",
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "estado_alerta",
					"label": "Estado de alerta",
					"fieldtype": "Select",
					"options": "Pendiente\nVerificado\nAjustado\nRechazado",
					"default": "Pendiente",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "fecha_reporte",
					"label": "Fecha de reporte",
					"fieldtype": "Date",
					"default": "Today",
					"reqd": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "reportado_por",
					"label": "Reportado por",
					"fieldtype": "Link",
					"options": "User",
				},
				{
					"fieldname": "observacion",
					"label": "Observacion",
					"fieldtype": "Small Text",
				},
				{
					"fieldname": "resolucion_section",
					"label": "Resolucion",
					"fieldtype": "Section Break",
				},
				{
					"fieldname": "accion_tomada",
					"label": "Accion tomada",
					"fieldtype": "Small Text",
				},
				{
					"fieldname": "fecha_resolucion",
					"label": "Fecha de resolucion",
					"fieldtype": "Date",
				},
			],
			"permissions": [
				{
					"role": "System Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"report": 1,
					"export": 1,
					"import": 1,
					"print": 1,
					"email": 1,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(doctype=doctype_name)

	return {"created": True, "doctype": doctype_name}


def create_basic_inventory_reports():
	"""Create query reports useful for the MVP presentation."""
	module = INVENTORY_MODULE
	reports = [
		{
			"report_name": "Resumen Inventario por Modulo",
			"ref_doctype": "Articulo de Inventario",
			"roles": ["SuperAdministrador Inventario", "Admin General", "Revisor", "System Manager"],
			"query": """
select
  modulo as "Modulo:Data:160",
  count(name) as "Total:Int:100",
  sum(case when estado = 'Activo' then 1 else 0 end) as "Activos:Int:100",
  sum(case when estado != 'Activo' then 1 else 0 end) as "No Operativos:Int:120"
from `tabArticulo de Inventario`
group by modulo
order by modulo
""",
		},
		{
			"report_name": "Stock Critico Gastronomia",
			"ref_doctype": "Articulo de Inventario",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin Cocina",
				"Admin General",
				"Revisor",
				"System Manager",
			],
			"query": """
select
  name as "ID:Link/Articulo de Inventario:140",
  nombre_articulo as "Articulo:Data:260",
  grupo as "Grupo:Data:140",
  categoria as "Categoria:Data:160",
  stock_actual as "Stock actual:Float:120",
  stock_critico as "Stock critico:Float:120",
  unidad_medida as "Unidad:Data:100",
  ubicacion as "Ubicacion:Link/Ubicacion:160"
from `tabArticulo de Inventario`
where modulo = 'Gastronomia'
  and ifnull(stock_critico, 0) > 0
  and ifnull(stock_actual, 0) < ifnull(stock_critico, 0)
order by grupo, nombre_articulo
""",
		},
		{
			"report_name": "Inventario TI por Ubicacion",
			"ref_doctype": "Articulo de Inventario",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin TI",
				"Admin General",
				"Revisor",
				"System Manager",
			],
			"query": """
select
  a.ubicacion as "Ubicacion:Link/Ubicacion:180",
  u.nombre_ubicacion as "Nombre ubicacion:Data:220",
  count(a.name) as "Total articulos:Int:120",
  sum(case when a.estado = 'Activo' then 1 else 0 end) as "Activos:Int:100",
  sum(case when a.estado != 'Activo' then 1 else 0 end) as "No Operativos:Int:120"
from `tabArticulo de Inventario`
  a
left join `tabUbicacion` u on u.name = a.ubicacion
where a.modulo = 'TI'
group by a.ubicacion, u.nombre_ubicacion
order by u.nombre_ubicacion
""",
		},
		{
			"report_name": "Detalle TI por Tipo y Ubicacion",
			"ref_doctype": "Articulo de Inventario",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin TI",
				"Admin General",
				"Revisor",
				"System Manager",
			],
			"query": """
select
  a.ubicacion as "Ubicacion:Link/Ubicacion:180",
  u.nombre_ubicacion as "Nombre ubicacion:Data:220",
  a.nombre_articulo as "Articulo:Data:180",
  count(a.name) as "Cantidad:Int:100"
from `tabArticulo de Inventario` a
left join `tabUbicacion` u on u.name = a.ubicacion
where a.modulo = 'TI'
group by a.ubicacion, u.nombre_ubicacion, a.nombre_articulo
order by u.nombre_ubicacion, a.nombre_articulo
""",
		},
		{
			"report_name": "Gastronomia sin Stock Critico",
			"ref_doctype": "Articulo de Inventario",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin Cocina",
				"Admin General",
				"System Manager",
			],
			"query": """
select
  name as "ID:Link/Articulo de Inventario:140",
  nombre_articulo as "Articulo:Data:260",
  grupo as "Grupo:Data:140",
  categoria as "Categoria:Data:160",
  stock_actual as "Stock actual:Float:120",
  stock_critico as "Stock critico:Float:120",
  unidad_medida as "Unidad:Data:100"
from `tabArticulo de Inventario`
where modulo = 'Gastronomia'
  and ifnull(stock_critico, 0) = 0
order by grupo, nombre_articulo
""",
		},
		{
			"report_name": "Reporte Maestro de Inventario",
			"ref_doctype": "Articulo de Inventario",
			"is_standard": "Yes",
			"report_type": "Script Report",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin TI",
				"Admin Cocina",
				"Admin General",
				"Revisor",
				"System Manager",
			],
		},
		{
			"report_name": "Bandeja de Alertas CEDHI",
			"ref_doctype": "Alerta de Inventario",
			"is_standard": "Yes",
			"report_type": "Script Report",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin TI",
				"Admin Cocina",
				"Admin General",
				"Revisor",
				"Reportante",
				"System Manager",
			],
		},
		{
			"report_name": "Kardex de Movimientos",
			"ref_doctype": "Movimiento de Inventario",
			"is_standard": "Yes",
			"report_type": "Script Report",
			"roles": [
				"SuperAdministrador Inventario",
				"Admin TI",
				"Admin Cocina",
				"Admin General",
				"Revisor",
				"System Manager",
			],
		},
	]

	created = []
	updated = []
	for item in reports:
		name = frappe.db.exists("Report", item["report_name"])
		payload = {
			"report_name": item["report_name"],
			"ref_doctype": item["ref_doctype"],
			"is_standard": item.get("is_standard", "No"),
			"module": module,
			"report_type": item.get("report_type", "Query Report"),
			"disabled": 0,
		}
		if item.get("query"):
			payload["query"] = item["query"].strip()

		if name:
			report = frappe.get_doc("Report", name)
			report.update(payload)
			report.roles = []
			updated.append(item["report_name"])
		else:
			report = frappe.get_doc({"doctype": "Report", **payload})
			created.append(item["report_name"])
		for role in item["roles"]:
			report.append("roles", {"role": role})
		report.save(ignore_permissions=True)

	frappe.db.commit()
	return {"created": created, "updated": updated}


def generate_stock_critical_alerts():
	"""Create pending stock-low alerts for Gastronomia items under critical stock."""
	items = frappe.get_all(
		"Articulo de Inventario",
		filters={
			"modulo": "Gastronomia",
			"stock_critico": [">", 0],
		},
		fields=[
			"name",
			"nombre_articulo",
			"stock_actual",
			"stock_critico",
			"unidad_medida",
			"ubicacion",
		],
		limit_page_length=5000,
	)

	created = []
	for item in items:
		if (item.stock_actual or 0) >= (item.stock_critico or 0):
			continue

		existing = frappe.db.exists(
			"Alerta de Inventario",
			{
				"articulo": item.name,
				"tipo_alerta": "Stock bajo",
				"estado_alerta": "Pendiente",
			},
		)
		if existing:
			continue

		alert = frappe.get_doc(
			{
				"doctype": "Alerta de Inventario",
				"articulo": item.name,
				"tipo_alerta": "Stock bajo",
				"estado_alerta": "Pendiente",
				"fecha_reporte": frappe.utils.today(),
				"observacion": (
					f"Stock actual {item.stock_actual or 0} {item.unidad_medida or ''} "
					f"menor al stock critico {item.stock_critico or 0}."
				),
			}
		)
		alert.insert(ignore_permissions=True)
		created.append(item.nombre_articulo)

	frappe.db.commit()
	return {"created": len(created), "items": created[:20]}


def apply_default_gastronomy_stock_critical(default_value=10):
	"""Set a default critical stock for Gastronomia items without a minimum."""
	items = frappe.get_all(
		"Articulo de Inventario",
		filters={
			"modulo": "Gastronomia",
			"stock_critico": ["<=", 0],
		},
		pluck="name",
		limit_page_length=5000,
	)

	for name in items:
		frappe.db.set_value(
			"Articulo de Inventario",
			name,
			"stock_critico",
			default_value,
			update_modified=False,
		)

	frappe.db.commit()
	return {"updated": len(items), "stock_critico": default_value}


def create_movimiento_inventario_doctype():
	"""Create the DocType for inventory transactions (Kardex)."""
	doctype_name = "Movimiento de Inventario"
	module = INVENTORY_MODULE

	if frappe.db.exists("DocType", doctype_name):
		return {"created": False, "doctype": doctype_name}

	doc = frappe.get_doc(
		{
			"doctype": "DocType",
			"name": doctype_name,
			"module": module,
			"custom": 1,
			"allow_import": 1,
			"autoname": "format:MOV-{YYYY}-{#####}",
			"is_submittable": 1,
			"fields": [
				{
					"fieldname": "datos_movimiento_section",
					"label": "Datos del Movimiento",
					"fieldtype": "Section Break",
				},
				{
					"fieldname": "articulo",
					"label": "Articulo",
					"fieldtype": "Link",
					"options": "Articulo de Inventario",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "tipo_movimiento",
					"label": "Tipo de Movimiento",
					"fieldtype": "Select",
					"options": "Entrada\nSalida\nAjuste",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "cantidad",
					"label": "Cantidad",
					"fieldtype": "Float",
					"reqd": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "estado_actual",
					"label": "Estado actual",
					"fieldtype": "Data",
					"fetch_from": "articulo.estado",
					"read_only": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "stock_actual_articulo",
					"label": "Stock actual del articulo",
					"fieldtype": "Float",
					"fetch_from": "articulo.stock_actual",
					"read_only": 1,
				},
				{
					"fieldname": "fecha",
					"label": "Fecha",
					"fieldtype": "Date",
					"default": "Today",
					"reqd": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "responsable",
					"label": "Responsable",
					"fieldtype": "Link",
					"options": "User",
					"default": "Session User",
				},
				{
					"fieldname": "motivo_section",
					"label": "Motivo",
					"fieldtype": "Section Break",
				},
				{
					"fieldname": "motivo",
					"label": "Motivo / Referencia",
					"fieldtype": "Small Text",
					"reqd": 1,
				},
			],
			"permissions": [
				{
					"role": "System Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"submit": 1,
					"cancel": 1,
					"amend": 1,
					"report": 1,
					"export": 1,
					"import": 1,
					"print": 1,
					"email": 1,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(doctype=doctype_name)

	return {"created": True, "doctype": doctype_name}


def configure_movimiento_traceability_fields():
	"""Ensure Kardex rows show the current article state and stock."""
	doctype_name = "Movimiento de Inventario"
	if not frappe.db.exists("DocType", doctype_name):
		return {"updated": False, "reason": "missing doctype"}

	doc = frappe.get_doc("DocType", doctype_name)
	existing = {df.fieldname for df in doc.fields}
	next_idx = max((cint(df.idx) for df in doc.fields), default=0) + 1
	fields = [
		{
			"fieldname": "estado_actual",
			"label": "Estado actual",
			"fieldtype": "Data",
			"fetch_from": "articulo.estado",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "stock_actual_articulo",
			"label": "Stock actual del articulo",
			"fieldtype": "Float",
			"fetch_from": "articulo.stock_actual",
			"read_only": 1,
		},
	]

	added = []
	for field in fields:
		if field["fieldname"] in existing:
			continue
		row = doc.append("fields", field)
		row.idx = next_idx
		next_idx += 1
		added.append(field["fieldname"])

	for field in doc.fields:
		if field.fieldname == "estado_actual":
			field.label = "Estado actual"
			field.fetch_from = "articulo.estado"
			field.read_only = 1
			field.in_list_view = 1
			field.in_standard_filter = 1
		if field.fieldname == "stock_actual_articulo":
			field.label = "Stock actual del articulo"
			field.fetch_from = "articulo.stock_actual"
			field.read_only = 1
		if field.fieldname == "tipo_movimiento":
			field.options = "Entrada\nSalida\nAjuste"

	doc.autoname = "format:MOV-{YYYY}-{#####}"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(doctype=doctype_name)
	return {"updated": True, "added": added}


def configure_inventory_role_permissions():
	"""Configure the PRD roles and base permissions for the inventory MVP."""
	roles = [
		"SuperAdministrador Inventario",
		"Admin TI",
		"Admin Cocina",
		"Admin General",
		"Revisor",
		"Reportante",
	]
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

	article_perms = {
		"SuperAdministrador Inventario": _full_permission(import_=1),
		"Admin TI": _manager_permission(import_=1),
		"Admin Cocina": _manager_permission(import_=1),
		"Admin General": _manager_permission(import_=1),
		"Revisor": _read_only_permission(),
		"Reportante": _read_only_permission(select=1),
		"System Manager": _full_permission(import_=1),
	}
	alert_perms = {
		"SuperAdministrador Inventario": _full_permission(import_=1),
		"Admin TI": _manager_permission(),
		"Admin Cocina": _manager_permission(),
		"Admin General": _manager_permission(),
		"Revisor": _read_only_permission(),
		"Reportante": {
			"read": 1,
			"write": 1,
			"create": 1,
			"print": 1,
			"select": 1,
		},
		"System Manager": _full_permission(import_=1),
	}
	reference_perms = {
		"SuperAdministrador Inventario": _full_permission(import_=1),
		"Admin TI": _read_only_permission(select=1),
		"Admin Cocina": _read_only_permission(select=1),
		"Admin General": _manager_permission(),
		"Revisor": _read_only_permission(select=1),
		"Reportante": _read_only_permission(select=1),
		"System Manager": _full_permission(import_=1),
	}
	user_perms = {
		"SuperAdministrador Inventario": _manager_permission(),
		"Admin TI": _read_only_permission(),
		"Admin Cocina": _read_only_permission(),
		"Admin General": _read_only_permission(),
		"Revisor": _read_only_permission(),
		"Reportante": _read_only_permission(),
		"System Manager": _full_permission(),
	}
	user_role_management_perms = {
		"SuperAdministrador Inventario": {
			**_manager_permission(),
			"permlevel": 1,
		},
		"System Manager": {
			**_full_permission(),
			"permlevel": 1,
		},
	}
	movimiento_perms = {
		"SuperAdministrador Inventario": _full_permission(submit=1, cancel=1),
		"Admin TI": _manager_permission(submit=1, cancel=1),
		"Admin Cocina": _manager_permission(submit=1, cancel=1),
		"Admin General": _manager_permission(submit=1, cancel=1),
		"Revisor": _read_only_permission(),
		"Reportante": _read_only_permission(select=1),
		"System Manager": _full_permission(submit=1, cancel=1),
	}
	user_reference_perms = {
		"SuperAdministrador Inventario": _read_only_permission(select=1),
		"System Manager": _full_permission(),
	}
	data_import_perms = {
		"SuperAdministrador Inventario": _manager_permission(),
		"Admin TI": _manager_permission(),
		"Admin Cocina": _manager_permission(),
		"Admin General": _manager_permission(),
		"System Manager": _full_permission(),
	}
	social_login_key_perms = {
		"SuperAdministrador Inventario": _manager_permission(),
		"System Manager": _full_permission(),
	}

	results = {}
	for doctype, permissions in {
		"Articulo de Inventario": article_perms,
		"Alerta de Inventario": alert_perms,
		"Movimiento de Inventario": movimiento_perms,
		"Ubicacion": reference_perms,
		"Asignacion": reference_perms,
		"User": user_perms,
		"Data Import": data_import_perms,
		"Data Import Log": data_import_perms,
		"Social Login Key": social_login_key_perms,
	}.items():
		if frappe.db.exists("DocType", doctype):
			results[doctype] = _apply_doctype_permissions(doctype, permissions)

	results["User Permlevel 1"] = _apply_custom_docperms("User", user_role_management_perms)
	for doctype in ("Role Profile", "Module Profile"):
		if frappe.db.exists("DocType", doctype):
			results[doctype] = _apply_doctype_permissions(doctype, user_reference_perms)
	for doctype in ("Data Import", "Data Import Log"):
		if frappe.db.exists("DocType", doctype):
			results[doctype] = _apply_doctype_permissions(doctype, data_import_perms)
	results["Role Profiles"] = create_inventory_role_profiles()
	results["Reporter User Fields"] = configure_reporter_user_fields()

	frappe.db.commit()
	frappe.clear_cache()
	return results


def configure_reporter_user_fields():
	"""Add User fields used to scope reportantes by module and location."""
	fields = [
		{
			"fieldname": "inventario_reportante_section",
			"label": "Inventario CEDHI",
			"fieldtype": "Section Break",
			"insert_after": "roles",
			"collapsible": 1,
		},
		{
			"fieldname": "inventario_modulo_asignado",
			"label": "Modulo asignado",
			"fieldtype": "Select",
			"options": "\nTI\nGastronomia\nGeneral",
			"insert_after": "inventario_reportante_section",
		},
		{
			"fieldname": "inventario_ubicacion_asignada",
			"label": "Ubicacion asignada",
			"fieldtype": "Link",
			"options": "Ubicacion",
			"insert_after": "inventario_modulo_asignado",
			"depends_on": 'eval:doc.inventario_modulo_asignado',
		},
	]
	create_custom_fields({"User": fields}, update=True)
	frappe.clear_cache(doctype="User")
	return {"configured": [field["fieldname"] for field in fields]}


def recreate_lab_computacion_reporter_user():
	"""Recreate the lab reporting user used for MVP alert tests."""
	return recreate_reporter_station_user(
		email="lab.computacion01@cedhi.local",
		full_name="Lab. Computacion 01",
		modulo="TI",
		ubicacion_label="Laboratorio 1",
		remove_users=["profesor@cedhi.local", "lab.computacion01@cedhi.local"],
	)


def repair_lab_computacion_reporter_user():
	"""Ensure the lab reporting user has the auxiliary records Frappe needs."""
	return repair_reporter_station_user("lab.computacion01@cedhi.local")


def repair_reporter_station_user(email):
	"""Create auxiliary records required for a reporter user session."""
	if not frappe.db.exists("User", email):
		frappe.throw(f"No existe el usuario {email}.")

	created = []
	if not frappe.db.exists("Notification Settings", email):
		frappe.get_doc(
			{
				"doctype": "Notification Settings",
				"name": email,
				"user": email,
				"enabled": 1,
				"enable_email_notifications": 1,
				"enable_email_mention": 1,
				"enable_email_assignment": 1,
				"enable_email_threads_on_assigned_document": 1,
				"enable_email_energy_point": 1,
				"enable_email_share": 1,
				"enable_email_event_reminders": 1,
				"energy_points_system_notifications": 1,
			}
		).db_insert()
		created.append("Notification Settings")

	frappe.db.commit()
	frappe.clear_cache(user=email)
	return {"user": email, "created": created}


def recreate_reporter_station_user(
	email,
	full_name,
	modulo,
	ubicacion_label,
	password="Cedhi12345",
	remove_users=None,
):
	"""Create a Reportante user assigned to one inventory location."""
	remove_users = remove_users or []
	for user in remove_users:
		_delete_user_direct(user)

	ubicacion = frappe.db.get_value(
		"Ubicacion",
		{"nombre_ubicacion": ubicacion_label, "modulo": modulo},
		"name",
	)
	if not ubicacion:
		frappe.throw(f"No se encontro la ubicacion {ubicacion_label} para el modulo {modulo}.")

	first_name, *rest = full_name.split(" ", 1)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"name": email,
			"email": email,
			"enabled": 1,
			"first_name": first_name,
			"last_name": rest[0] if rest else "",
			"full_name": full_name,
			"username": email.split("@")[0].replace(".", "_"),
			"user_type": "System User",
			"send_welcome_email": 0,
			"role_profile_name": "Perfil Reportante",
			"inventario_modulo_asignado": modulo,
			"inventario_ubicacion_asignada": ubicacion,
		}
	)
	user.db_insert()

	frappe.get_doc(
		{
			"doctype": "Has Role",
			"parent": email,
			"parenttype": "User",
			"parentfield": "roles",
			"role": "Reportante",
		}
	).db_insert()

	frappe.db.commit()
	update_password(email, password)
	repair_reporter_station_user(email)
	frappe.db.commit()
	frappe.clear_cache(user=email)

	return {
		"user": email,
		"full_name": full_name,
		"role": "Reportante",
		"modulo": modulo,
		"ubicacion": ubicacion_label,
		"password": password,
	}


def _delete_user_direct(user):
	"""Delete a local test user without triggering User hooks that need Redis."""
	if not frappe.db.exists("User", user):
		return

	frappe.db.delete("Has Role", {"parent": user})
	frappe.db.delete("DefaultValue", {"parent": user})
	frappe.db.delete("User Permission", {"user": user})
	frappe.db.delete("Notification Settings", {"name": user})
	frappe.db.delete("__Auth", {"doctype": "User", "name": user})
	frappe.db.delete("User", {"name": user})
	frappe.db.commit()


def create_inventory_role_profiles():
	"""Create role profiles used by the User quick-entry dialog."""
	profiles = {
		"Perfil SuperAdministrador Inventario": ["SuperAdministrador Inventario"],
		"Perfil Admin TI": ["Admin TI"],
		"Perfil Admin Cocina": ["Admin Cocina"],
		"Perfil Admin General": ["Admin General"],
		"Perfil Revisor": ["Revisor"],
		"Perfil Reportante": ["Reportante"],
	}

	created = []
	updated = []
	for profile_name, roles in profiles.items():
		if frappe.db.exists("Role Profile", profile_name):
			frappe.db.delete("Has Role", {"parenttype": "Role Profile", "parent": profile_name})
			updated.append(profile_name)
		else:
			profile = frappe.get_doc(
				{
					"doctype": "Role Profile",
					"name": profile_name,
					"role_profile": profile_name,
				}
			)
			profile.db_insert()
			created.append(profile_name)

		for role in roles:
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": profile_name,
					"parenttype": "Role Profile",
					"parentfield": "roles",
					"role": role,
				}
			).db_insert()

	frappe.db.commit()
	return {"created": created, "updated": updated}


def _full_permission(import_=0, submit=0, cancel=0):
	return {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"submit": submit,
		"cancel": cancel,
		"report": 1,
		"export": 1,
		"import": import_,
		"print": 1,
		"email": 1,
		"share": 1,
		"select": 1,
	}


def _manager_permission(import_=0, submit=0, cancel=0):
	return {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"submit": submit,
		"cancel": cancel,
		"report": 1,
		"export": 1,
		"import": import_,
		"print": 1,
		"email": 1,
		"select": 1,
	}


def _read_only_permission(select=0):
	return {
		"read": 1,
		"report": 1,
		"print": 1,
		"select": select,
	}


def _apply_doctype_permissions(doctype_name, permissions_by_role):
	doc = frappe.get_doc("DocType", doctype_name)
	if not doc.custom:
		return _apply_custom_docperms(doctype_name, permissions_by_role)

	existing = {(perm.role, cint(perm.permlevel)): perm for perm in doc.permissions}
	updated = []
	created = []

	for role, permissions in permissions_by_role.items():
		key = (role, 0)
		if key in existing:
			perm = existing[key]
			updated.append(role)
		else:
			perm = doc.append("permissions", {"role": role, "permlevel": 0})
			created.append(role)

		for field in (
			"read",
			"write",
			"create",
			"delete",
			"submit",
			"cancel",
			"amend",
			"report",
			"export",
			"import",
			"print",
			"email",
			"share",
			"select",
		):
			setattr(perm, field, cint(permissions.get(field)))

	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype=doctype_name)
	return {"created": created, "updated": updated}


def _apply_custom_docperms(doctype_name, permissions_by_role):
	updated = []
	created = []
	for role, permissions in permissions_by_role.items():
		permlevel = cint(permissions.get("permlevel"))
		name = frappe.db.exists(
			"Custom DocPerm",
			{"parent": doctype_name, "role": role, "permlevel": permlevel},
		)
		if name:
			perm = frappe.get_doc("Custom DocPerm", name)
			updated.append(role)
		else:
			perm = frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": doctype_name,
					"role": role,
					"permlevel": permlevel,
				}
			)
			created.append(role)

		for field in (
			"read",
			"write",
			"create",
			"delete",
			"submit",
			"cancel",
			"amend",
			"report",
			"export",
			"import",
			"print",
			"email",
			"share",
			"select",
		):
			setattr(perm, field, cint(permissions.get(field)))

		if name:
			perm.save(ignore_permissions=True)
		else:
			perm.insert(ignore_permissions=True)

	frappe.clear_cache(doctype=doctype_name)
	return {"created": created, "updated": updated}


def get_inventory_permission_summary():
	"""Return a compact permission summary for the PRD roles."""
	roles = {
		"SuperAdministrador Inventario",
		"Admin TI",
		"Admin Cocina",
		"Admin General",
		"Revisor",
		"System Manager",
	}
	summary = {}
	for doctype_name in ("Articulo de Inventario", "Alerta de Inventario", "Ubicacion", "Asignacion"):
		if not frappe.db.exists("DocType", doctype_name):
			continue
		doc = frappe.get_doc("DocType", doctype_name)
		doctype_permissions = [
			{
				"role": perm.role,
				"read": perm.read,
				"write": perm.write,
				"create": perm.create,
				"delete": perm.delete,
				"report": perm.report,
				"export": perm.export,
				"import": perm.get("import"),
				"print": perm.print,
				"select": perm.select,
			}
			for perm in doc.permissions
			if perm.role in roles
		]
		custom_permissions = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype_name, "role": ["in", list(roles)]},
			fields=[
				"role",
				"read",
				"write",
				"create",
				"delete",
				"report",
				"export",
				"import",
				"print",
				"select",
			],
			limit_page_length=100,
		)
		summary[doctype_name] = doctype_permissions + custom_permissions
	return summary


def create_inventory_number_cards():
	"""Create Number Cards for the inventory dashboard."""
	cards = [
		{
			"label": "Total Articulos",
			"document_type": "Articulo de Inventario",
			"function": "Count",
		},
		{
			"label": "Artículos Activos",
			"document_type": "Articulo de Inventario",
			"function": "Count",
			"filters_json": json.dumps([["Articulo de Inventario", "estado", "=", "Activo"]]),
		},
		{
			"label": "Artículos en Reparación",
			"document_type": "Articulo de Inventario",
			"function": "Count",
			"filters_json": json.dumps([["Articulo de Inventario", "estado", "=", "En reparación"]]),
		},
		{
			"label": "Artículos de Baja",
			"document_type": "Articulo de Inventario",
			"function": "Count",
			"filters_json": json.dumps([["Articulo de Inventario", "estado", "=", "De baja"]]),
		},
		{
			"label": "Alertas Pendientes",
			"document_type": "Alerta de Inventario",
			"function": "Count",
			"filters_json": json.dumps([["Alerta de Inventario", "estado_alerta", "=", "Pendiente"]]),
		},
		{
			"label": "Alertas Totales",
			"document_type": "Alerta de Inventario",
			"function": "Count",
		},
	]

	results = []
	for card_data in cards:
		if not frappe.db.exists("Number Card", card_data["label"]):
			card = frappe.get_doc(
				{
					"doctype": "Number Card",
					"is_standard": 1,
					"module": INVENTORY_MODULE,
					**card_data,
				}
			)
			card.currency = None
			card.insert(ignore_permissions=True)
			results.append(card.name)
		else:
			card = frappe.get_doc("Number Card", card_data["label"])
			card.update(card_data)
			card.currency = None
			card.save(ignore_permissions=True)
			results.append(card_data["label"])

	return results


def create_inventory_charts():
	"""Create Dashboard Charts for the inventory workspace."""
	charts = [
		{
			"chart_name": "Estado de Activos",
			"chart_type": "Group By",
			"document_type": "Articulo de Inventario",
			"group_by_based_on": "estado",
			"group_by_type": "Count",
			"type": "Donut",
			"module": INVENTORY_MODULE,
		},
		{
			"chart_name": "Distribución por Módulo",
			"chart_type": "Group By",
			"document_type": "Articulo de Inventario",
			"group_by_based_on": "modulo",
			"group_by_type": "Count",
			"type": "Bar",
			"module": INVENTORY_MODULE,
		},
		{
			"chart_name": "Alertas por Tipo",
			"chart_type": "Group By",
			"document_type": "Alerta de Inventario",
			"group_by_based_on": "tipo_alerta",
			"group_by_type": "Count",
			"type": "Donut",
			"module": INVENTORY_MODULE,
		},
		{
			"chart_name": "Alertas por Estado",
			"chart_type": "Group By",
			"document_type": "Alerta de Inventario",
			"group_by_based_on": "estado_alerta",
			"group_by_type": "Count",
			"type": "Bar",
			"module": INVENTORY_MODULE,
		},
	]

	results = []
	for chart_data in charts:
		if not frappe.db.exists("Dashboard Chart", chart_data["chart_name"]):
			chart = frappe.get_doc(
				{
					"doctype": "Dashboard Chart",
					"is_standard": 0,
					"filters_json": json.dumps({}),
					**chart_data,
				}
			)
			chart.currency = None
			chart.insert(ignore_permissions=True)
			results.append(chart.name)
		else:
			chart = frappe.get_doc("Dashboard Chart", chart_data["chart_name"])
			chart.update(chart_data)
			chart.currency = None
			chart.save(ignore_permissions=True)
			results.append(chart_data["chart_name"])
	return results


def create_inventory_client_scripts():
	"""Create Client Scripts to enforce PRD logic and improve UX."""
	mobile_navigation_helper = """
window.cedhi_mobile_navigation = window.cedhi_mobile_navigation || {};
window.cedhi_mobile_navigation.applyStyles = function(button) {
    const styles = {
        position: "fixed",
        left: "12px",
        bottom: "14px",
        zIndex: "2147483000",
        display: "inline-flex",
        visibility: "visible",
        opacity: "1",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "34px",
        padding: "7px 12px",
        border: "1px solid #e5e7eb",
        borderRadius: "999px",
        background: "#ffffff",
        boxShadow: "0 8px 18px rgba(15, 23, 42, 0.18)",
        color: "#111827",
        fontWeight: "600",
        pointerEvents: "auto",
    };
    Object.entries(styles).forEach(([property, value]) => {
        button.style.setProperty(property, value, "important");
    });
};
window.cedhi_mobile_navigation.ensure = function() {
    const mobileQuery = "(max-width: 1024px)";
    const path = window.location.pathname.toLowerCase();
    const visualWidth = window.visualViewport ? window.visualViewport.width : window.innerWidth;
    const isMobile = window.matchMedia(mobileQuery).matches
        || window.innerWidth <= 1024
        || document.documentElement.clientWidth <= 1024
        || visualWidth <= 1024;
    const shouldShow = isMobile
        && path.startsWith("/app")
        && !["/app", "/app/home"].includes(path);

    if (!document.getElementById("cedhi-mobile-navigation-style")) {
        const style = document.createElement("style");
        style.id = "cedhi-mobile-navigation-style";
        style.textContent = `
            .cedhi-mobile-back { display: none; }
            @media (max-width: 1024px) {
                .cedhi-mobile-back {
                    position: fixed;
                    left: 12px;
                    bottom: 14px;
                    z-index: 1050;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 34px;
                    padding: 7px 12px;
                    border: 1px solid #e5e7eb;
                    border-radius: 999px;
                    background: #ffffff;
                    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
                    font-weight: 600;
                }
            }
        `;
        document.head.appendChild(style);
    }

    const existingButton = document.querySelector(".cedhi-mobile-back");
    if (!shouldShow) {
        if (existingButton) {
            existingButton.remove();
        }
        return;
    }

    if (existingButton) {
        window.cedhi_mobile_navigation.applyStyles(existingButton);
        return;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-default btn-sm cedhi-mobile-back";
    button.textContent = "Volver";
    button.setAttribute("aria-label", "Volver a la vista anterior");
    window.cedhi_mobile_navigation.applyStyles(button);
    button.addEventListener("click", function() {
        if (window.history.length > 1) {
            window.history.back();
            return;
        }
        if (window.frappe && frappe.set_route) {
            frappe.set_route("Workspaces", "Inventario CEDHI");
        }
    });

    document.body.appendChild(button);
};
window.cedhi_mobile_navigation.ensure();
window.setTimeout(window.cedhi_mobile_navigation.ensure, 150);
window.setTimeout(window.cedhi_mobile_navigation.ensure, 600);
window.addEventListener("resize", window.cedhi_mobile_navigation.ensure);
window.addEventListener("focus", window.cedhi_mobile_navigation.ensure);
window.addEventListener("pageshow", window.cedhi_mobile_navigation.ensure);
document.addEventListener("visibilitychange", window.cedhi_mobile_navigation.ensure);
if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", window.cedhi_mobile_navigation.ensure);
}
if (window.frappe && frappe.router && typeof frappe.router.on === "function" && !window.cedhi_mobile_navigation.routerHooked) {
    frappe.router.on("change", function() {
        window.setTimeout(window.cedhi_mobile_navigation.ensure, 100);
        window.setTimeout(window.cedhi_mobile_navigation.ensure, 500);
    });
    window.cedhi_mobile_navigation.routerHooked = true;
}
if (!window.cedhi_mobile_navigation.historyHooked) {
    ["pushState", "replaceState"].forEach(function(methodName) {
        const originalMethod = window.history[methodName];
        if (!originalMethod) {
            return;
        }
        window.history[methodName] = function() {
            const result = originalMethod.apply(this, arguments);
            window.setTimeout(window.cedhi_mobile_navigation.ensure, 100);
            window.setTimeout(window.cedhi_mobile_navigation.ensure, 500);
            return result;
        };
    });
    window.cedhi_mobile_navigation.historyHooked = true;
}
if (!window.cedhi_mobile_navigation.observer && document.body) {
    window.cedhi_mobile_navigation.observer = new MutationObserver(function() {
        window.setTimeout(window.cedhi_mobile_navigation.ensure, 100);
    });
    window.cedhi_mobile_navigation.observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}
if (!window.cedhi_mobile_navigation.interval) {
    window.cedhi_mobile_navigation.interval = window.setInterval(window.cedhi_mobile_navigation.ensure, 800);
}
"""
	kardex_dialog_helper = """
window.open_quick_kardex_dialog = function(opts) {
    opts = opts || {};
    let d = new frappe.ui.Dialog({
        title: __('Actualización Rápida de Inventario (Kardex)'),
        fields: [
            {
                label: __('Artículo'),
                fieldname: 'articulo',
                fieldtype: 'Link',
                options: 'Articulo de Inventario',
                reqd: 1,
                default: opts.articulo || '',
                read_only: opts.articulo ? 1 : 0,
                onchange: function() {
                    let art = d.get_value('articulo');
                    if (art) {
                        frappe.db.get_value('Articulo de Inventario', art, ['nombre_articulo', 'stock_actual', 'modulo'], (r) => {
                            if (r) {
                                d.set_description('articulo', `<div style="margin-top: 4px; padding: 6px 10px; background-color: #f8f9fa; border-left: 3px solid #3498db; border-radius: 3px; font-size: 13px;"><b>${r.nombre_articulo}</b> | Stock actual: <strong style="color: #2c3e50;">${r.stock_actual || 0}</strong></div>`);
                                update_qty_description(d, r.stock_actual || 0);
                                
                                let current_motivo = d.get_value('motivo');
                                if (!current_motivo || current_motivo === 'Ajuste rápido de inventario' || current_motivo === 'Ajuste rápido de cocina') {
                                    if (r.modulo === 'Gastronomia') {
                                        d.set_value('motivo', 'Ajuste rápido de cocina');
                                    } else {
                                        d.set_value('motivo', 'Ajuste rápido de inventario');
                                    }
                                }
                            }
                        });
                    } else {
                        d.set_description('articulo', '');
                        update_qty_description(d, 0);
                    }
                }
            },
            {
                label: __('Tipo de Movimiento'),
                fieldname: 'tipo_movimiento',
                fieldtype: 'Select',
                options: ['Entrada', 'Salida', 'Ajuste'],
                default: 'Ajuste',
                reqd: 1,
                onchange: function() {
                    let art = d.get_value('articulo');
                    if (art) {
                        frappe.db.get_value('Articulo de Inventario', art, 'stock_actual', (r) => {
                            update_qty_description(d, (r && r.stock_actual) ? r.stock_actual : 0);
                        });
                    } else {
                        update_qty_description(d, 0);
                    }
                }
            },
            {
                label: __('Cantidad / Existencia'),
                fieldname: 'cantidad',
                fieldtype: 'Float',
                reqd: 1,
                description: __('Para Ajuste, ingrese la nueva existencia total.')
            },
            {
                label: __('Motivo / Referencia'),
                fieldname: 'motivo',
                fieldtype: 'Small Text',
                reqd: 1,
                default: 'Ajuste rápido de cocina'
            }
        ],
        primary_action_label: __('Registrar'),
        primary_action: function(values) {
            if (!values.articulo || !values.tipo_movimiento || values.cantidad === undefined || !values.motivo) {
                frappe.msgprint(__('Todos los campos son obligatorios.'));
                return;
            }
            if (values.cantidad < 0) {
                frappe.msgprint(__('La cantidad no puede ser negativa.'));
                return;
            }
            
            d.get_primary_btn().prop('disabled', true);
            frappe.call({
                method: 'inventario_cedhi.inventory_logic.create_quick_movement',
                args: {
                    articulo: values.articulo,
                    tipo_movimiento: values.tipo_movimiento,
                    cantidad: values.cantidad,
                    motivo: values.motivo
                },
                callback: function(r) {
                    d.get_primary_btn().prop('disabled', false);
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Movimiento registrado exitosamente: {0}', [r.message]),
                            indicator: 'green'
                        });
                        d.hide();
                        if (opts.callback) {
                            opts.callback();
                        }
                    }
                },
                error: function(err) {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    function update_qty_description(dialog_inst, current_stock) {
        let type = dialog_inst.get_value('tipo_movimiento');
        let qty_field = dialog_inst.fields_dict.cantidad;
        if (!qty_field) return;
        
        if (type === 'Ajuste') {
            dialog_inst.set_label('cantidad', __('Nueva Existencia Total'));
            dialog_inst.set_description('cantidad', `<div style="margin-top: 4px; color: #7f8c8d; font-size: 12px;">El stock se establecerá exactamente a este valor (Diferencia de ajuste: <strong id="kardex-dialog-delta">0</strong>). Actual: ${current_stock}</div>`);
            
            let $input = dialog_inst.$wrapper.find('input[data-fieldname="cantidad"]');
            $input.off('input.kardex_calc').on('input.kardex_calc', function() {
                let val = parseFloat($(this).val()) || 0;
                let delta = val - current_stock;
                let delta_text = delta >= 0 ? '+' + delta : '' + delta;
                let color = delta >= 0 ? '#27ae60' : '#c0392b';
                dialog_inst.$wrapper.find('#kardex-dialog-delta')
                    .text(delta_text)
                    .css('color', color);
            });
            $input.trigger('input.kardex_calc');
        } else if (type === 'Entrada') {
            dialog_inst.set_label('cantidad', __('Cantidad a Ingresar'));
            dialog_inst.set_description('cantidad', `<div style="margin-top: 4px; color: #7f8c8d; font-size: 12px;">Se sumará al stock actual. Nuevo stock proyectado: <strong id="kardex-dialog-projected">${current_stock}</strong></div>`);
            
            let $input = dialog_inst.$wrapper.find('input[data-fieldname="cantidad"]');
            $input.off('input.kardex_calc').on('input.kardex_calc', function() {
                let val = parseFloat($(this).val()) || 0;
                let projected = current_stock + val;
                dialog_inst.$wrapper.find('#kardex-dialog-projected')
                    .text(projected);
            });
            $input.trigger('input.kardex_calc');
        } else if (type === 'Salida') {
            dialog_inst.set_label('cantidad', __('Cantidad a Retirar'));
            dialog_inst.set_description('cantidad', `<div style="margin-top: 4px; color: #7f8c8d; font-size: 12px;">Se restará del stock actual. Nuevo stock proyectado: <strong id="kardex-dialog-projected">${current_stock}</strong></div>`);
            
            let $input = dialog_inst.$wrapper.find('input[data-fieldname="cantidad"]');
            $input.off('input.kardex_calc').on('input.kardex_calc', function() {
                let val = parseFloat($(this).val()) || 0;
                let projected = current_stock - val;
                let color = projected < 0 ? '#c0392b' : '#7f8c8d';
                dialog_inst.$wrapper.find('#kardex-dialog-projected')
                    .text(projected)
                    .css('color', color);
            });
            $input.trigger('input.kardex_calc');
        }
    }

    d.show();
    if (opts.articulo) {
        d.trigger('articulo');
    }
};
"""

	list_view_doctypes = [
		"Alerta de Inventario",
		"Movimiento de Inventario",
		"Ubicacion",
		"Asignacion",
	]
	scripts = [
		{
			"dt": "Articulo de Inventario",
			"name": "Articulo de Inventario - PRD Logic",
			"script": """
frappe.ui.form.on('Articulo de Inventario', {
    refresh: function(frm) {
        // RF-TI-01: Brand/Model mandatory for TI
        frm.toggle_reqd('marca', frm.doc.modulo === 'TI');
        frm.toggle_reqd('modelo', frm.doc.modulo === 'TI');
        
        // RF-GE-01: Pabellon/Aula visibility for General
        let is_general = frm.doc.modulo === 'General' || frm.doc.modulo === 'TI';
        frm.toggle_display(['pabellon', 'aula'], is_general);
        
        // RF-GA-03: Visual feedback for Critical Stock
        if (frm.doc.stock_actual <= frm.doc.stock_critico && frm.doc.stock_critico > 0) {
            frm.set_df_property('stock_actual', 'description', 
                '<b style="color: #e74c3c;">⚠️ STOCK CRÍTICO: El inventario está por debajo del límite definido.</b>');
        } else {
            frm.set_df_property('stock_actual', 'description', '');
        }

        // RF-GE-02: Auto-generate code placeholder hint
        if (frm.is_new() && frm.doc.modulo) {
            frm.set_df_property('codigo_interno', 'placeholder', 'Generado automáticamente al guardar');
        } else {
            frm.set_df_property('codigo_interno', 'placeholder', '');
        }

        // Personalidad: Color de fondo según módulo
        if (frm.doc.modulo === 'TI') {
            frm.set_df_property('datos_generales_section', 'label', '💻 Datos Técnicos TI');
        } else if (frm.doc.modulo === 'Gastronomia') {
            frm.set_df_property('datos_generales_section', 'label', '🍳 Control de Gastronomía');
        }

        // RF-GA-01: Quick movement button on Form View
        if (!frm.is_new()) {
            frm.add_custom_button(__('Registrar Movimiento (Kardex)'), function() {
                window.open_quick_kardex_dialog({
                    articulo: frm.doc.name,
                    modulo: frm.doc.modulo,
                    callback: function() {
                        frm.reload_doc();
                    }
                });
            });
        }
    },
    modulo: function(frm) {
        frm.trigger('refresh');
    },
    estado: function(frm) {
        // RF-C03: Mandatory reason for status change
        if (frm.doc.estado !== 'Activo') {
            frm.set_df_property('motivo_cambio_estado', 'reqd', 1);
            frappe.msgprint(__('Por favor, especifique el motivo del cambio de estado para cumplir con la trazabilidad (RF-C03).'));
        } else {
            frm.set_df_property('motivo_cambio_estado', 'reqd', 0);
        }
    }
});
""" + mobile_navigation_helper + kardex_dialog_helper,
		},
		{
			"dt": "Articulo de Inventario",
			"view": "List",
			"name": "Articulo de Inventario - Navegacion movil Lista",
			"script": """
frappe.listview_settings['Articulo de Inventario'] = frappe.listview_settings['Articulo de Inventario'] || {};
frappe.listview_settings['Articulo de Inventario'].onload = function(listview) {
    window.cedhi_mobile_navigation && window.cedhi_mobile_navigation.ensure && window.cedhi_mobile_navigation.ensure();
    
    // RF-GA-01: Quick movement button on List View
    listview.page.add_inner_button(__('Kardex Rápido (Cocina)'), function() {
        let selected = listview.get_checked_items();
        let art = '';
        if (selected && selected.length > 0) {
            art = selected[0].name;
        }
        window.open_quick_kardex_dialog({
            articulo: art,
            callback: function() {
                listview.refresh();
            }
        });
    });
};
frappe.listview_settings['Articulo de Inventario'].refresh = function(listview) {
    window.cedhi_mobile_navigation && window.cedhi_mobile_navigation.ensure && window.cedhi_mobile_navigation.ensure();
};
""" + mobile_navigation_helper + kardex_dialog_helper,
		}
	]

	for doctype_name in list_view_doctypes:
		scripts.extend(
			[
				{
					"dt": doctype_name,
					"view": "Form",
					"name": f"{doctype_name} - Navegacion movil",
					"script": mobile_navigation_helper,
				},
				{
					"dt": doctype_name,
					"view": "List",
					"name": f"{doctype_name} - Navegacion movil Lista",
					"script": f"frappe.listview_settings[{json.dumps(doctype_name)}] = frappe.listview_settings[{json.dumps(doctype_name)}] || {{}}; frappe.listview_settings[{json.dumps(doctype_name)}].onload = function() {{ window.cedhi_mobile_navigation && window.cedhi_mobile_navigation.ensure && window.cedhi_mobile_navigation.ensure(); }}; frappe.listview_settings[{json.dumps(doctype_name)}].refresh = function() {{ window.cedhi_mobile_navigation && window.cedhi_mobile_navigation.ensure && window.cedhi_mobile_navigation.ensure(); }};" + mobile_navigation_helper,
				},
			]
		)

	# Delete redundant form script if exists to consolidate form logic
	if frappe.db.exists("Client Script", "Articulo de Inventario - Navegacion movil"):
		frappe.delete_doc("Client Script", "Articulo de Inventario - Navegacion movil", ignore_permissions=True)

	results = []
	for script_data in scripts:
		if not frappe.db.exists("Client Script", script_data["name"]):
			script = frappe.get_doc(
				{
					"doctype": "Client Script",
					"module": INVENTORY_MODULE,
					"enabled": 1,
					**script_data,
				}
			)
			script.insert(ignore_permissions=True)
			results.append(script.name)
		else:
			script = frappe.get_doc("Client Script", script_data["name"])
			script.script = script_data["script"]
			script.save(ignore_permissions=True)
			results.append(script.name)
	return results


def create_initial_users():
	"""Create the initial users defined in the PRD."""
	users_to_create = [
		{
			"email": "andree@cedhi.local",
			"first_name": "Andree",
			"role_profile_name": "Perfil SuperAdministrador Inventario",
			"additional_roles": ["Admin TI", "System Manager", "Desk User"],
		},
		{
			"email": "luis@cedhi.local",
			"first_name": "Chef Luis",
			"role_profile_name": "Perfil Admin Cocina",
			"additional_roles": ["Desk User"],
		},
		{
			"email": "angie@cedhi.local",
			"first_name": "Angie",
			"role_profile_name": "Perfil Admin Cocina",
			"additional_roles": ["Desk User"],
		},
		{
			"email": "manuel@cedhi.local",
			"first_name": "Sr. Manuel",
			"role_profile_name": "Perfil Admin General",
			"additional_roles": ["Desk User"],
		},
	]

	results = []
	for user_data in users_to_create:
		if not frappe.db.exists("User", user_data["email"]):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": user_data["email"],
					"first_name": user_data["first_name"],
					"send_welcome_email": 0,
					"role_profile_name": user_data["role_profile_name"],
					"user_type": "System User",
				}
			)
			user.insert(ignore_permissions=True)
			
			if user_data.get("additional_roles"):
				for role in user_data["additional_roles"]:
					if not any(r.role == role for r in user.roles):
						user.append("roles", {"role": role})
				user.save(ignore_permissions=True)
			# Set a random password to avoid issues, though Google Auth is preferred
			update_password(user.name, "cedhi123")
			results.append({"email": user_data["email"], "status": "created"})
		else:
			user = frappe.get_doc("User", user_data["email"])
			updated = False
			if user.role_profile_name != user_data["role_profile_name"]:
				user.role_profile_name = user_data["role_profile_name"]
				updated = True
			
			if user_data.get("additional_roles"):
				for role in user_data["additional_roles"]:
					if not any(r.role == role for r in user.roles):
						user.append("roles", {"role": role})
						updated = True
			
			if updated:
				user.save(ignore_permissions=True)
				results.append({"email": user_data["email"], "status": "updated"})
			else:
				results.append({"email": user_data["email"], "status": "exists"})

	return results


def create_inventory_workspace():
	"""Create a visible workspace with shortcuts for the inventory MVP."""
	module = INVENTORY_MODULE
	name = "Inventario CEDHI"

	# Define Content structure (The Layout)
	content = [
		{"id": "hero", "type": "header", "data": {"text": '<div class="hero-banner main-banner"><h1>Inventario CEDHI</h1><p>Gestión inteligente de activos y suministros.</p></div>', "col": 12}},
		# Row 1: KPI Artículos
		{"id": "mc_total", "type": "number_card", "data": {"number_card_name": "Total Articulos", "col": 3}},
		{"id": "mc_activos", "type": "number_card", "data": {"number_card_name": "Artículos Activos", "col": 3}},
		{"id": "mc_reparacion", "type": "number_card", "data": {"number_card_name": "Artículos en Reparación", "col": 3}},
		{"id": "mc_baja", "type": "number_card", "data": {"number_card_name": "Artículos de Baja", "col": 3}},
		
		# Row 2: KPI Alertas
		{"id": "mc_alertas_pend", "type": "number_card", "data": {"number_card_name": "Alertas Pendientes", "col": 6}},
		{"id": "mc_alertas_tot", "type": "number_card", "data": {"number_card_name": "Alertas Totales", "col": 6}},
		
		{"id": "s1", "type": "spacer", "data": {"col": 12}},
		
		# Row 3: Shortcuts & Actions
		{"id": "sh1", "type": "shortcut", "data": {"shortcut_name": "REPORTE MAESTRO (EXCEL)", "col": 12}},
		
		{"id": "s2", "type": "spacer", "data": {"col": 12}},
		
		# Row 4: Navigation Cards
		{"id": "c1", "type": "card", "data": {"card_name": "Operaciones", "col": 4}},
		{"id": "c2", "type": "card", "data": {"card_name": "Reportes", "col": 4}},
		{"id": "c3", "type": "card", "data": {"card_name": "Configuración", "col": 4}},
		
		{"id": "s3", "type": "spacer", "data": {"col": 12}},
		
		# Row 5: Charts for Assets & Modules
		{"id": "ch_activos", "type": "chart", "data": {"chart_name": "Estado de Activos", "col": 6}},
		{"id": "ch_modulos", "type": "chart", "data": {"chart_name": "Distribución por Módulo", "col": 6}},
		
		# Row 6: Charts for Alerts
		{"id": "ch_alertas_tipo", "type": "chart", "data": {"chart_name": "Alertas por Tipo", "col": 6}},
		{"id": "ch_alertas_estado", "type": "chart", "data": {"chart_name": "Alertas por Estado", "col": 6}},
	]

	# Define Links grouped using Card Breaks sequential rows (Frappe v15 format)
	links = [
		# Operaciones Card Break
		{"label": "Operaciones", "type": "Card Break"},
		{"label": "Catálogo Maestro", "link_to": "Articulo de Inventario", "link_type": "DocType", "type": "Link"},
		{"label": "Kardex Digital", "link_to": "Movimiento de Inventario", "link_type": "DocType", "type": "Link"},
		{"label": "Incidencias", "link_to": "Alerta de Inventario", "link_type": "DocType", "type": "Link"},
		
		# Reportes Card Break
		{"label": "Reportes", "type": "Card Break"},
		{"label": "Reporte Maestro (Excel)", "link_to": "Reporte Maestro de Inventario", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
		{"label": "Bandeja de Alertas", "link_to": "Bandeja de Alertas CEDHI", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Alerta de Inventario"},
		{"label": "Kardex de Movimientos", "link_to": "Kardex de Movimientos", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Movimiento de Inventario"},
		{"label": "Stock Crítico", "link_to": "Stock Critico Gastronomia", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
		{"label": "Resumen por Área", "link_to": "Resumen Inventario por Modulo", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
		
		# Configuración Card Break
		{"label": "Configuración", "type": "Card Break"},
		{"label": "Espacios Físicos", "link_to": "Ubicacion", "link_type": "DocType", "type": "Link"},
		{"label": "Importación Masiva", "link_to": "Data Import", "link_type": "DocType", "type": "Link"},
		{"label": "Gestión de Usuarios", "link_to": "User", "link_type": "DocType", "type": "Link"},
	]

	shortcuts = [
		{
			"type": "URL",
			"url": "/app/query-report/Reporte Maestro de Inventario",
			"label": "REPORTE MAESTRO (EXCEL)",
			"color": "Green",
		}
	]

	roles = [
		{"role": "System Manager"},
		{"role": "SuperAdministrador Inventario"},
		{"role": "Admin TI"},
		{"role": "Admin Cocina"},
		{"role": "Admin General"},
		{"role": "Revisor"},
		{"role": "Reportante"},
	]

	number_cards = [
		{"number_card_name": "Total Articulos"},
		{"number_card_name": "Artículos Activos"},
		{"number_card_name": "Artículos en Reparación"},
		{"number_card_name": "Artículos de Baja"},
		{"number_card_name": "Alertas Pendientes"},
		{"number_card_name": "Alertas Totales"},
	]

	charts = [
		{"chart_name": "Estado de Activos"},
		{"chart_name": "Distribución por Módulo"},
		{"chart_name": "Alertas por Tipo"},
		{"chart_name": "Alertas por Estado"},
	]

	if frappe.db.exists("Workspace", name):
		workspace = frappe.get_doc("Workspace", name)
		workspace.shortcuts = []
		workspace.links = []
		workspace.roles = []
		workspace.number_cards = []
		workspace.charts = []
		created = False
	else:
		workspace = frappe.get_doc({"doctype": "Workspace", "label": name, "title": name})
		created = True

	workspace.update(
		{
			"label": name,
			"title": name,
			"module": module,
			"icon": "package",
			"indicator_color": "blue",
			"public": 1,
			"is_hidden": 0,
			"hide_custom": 1,
			"content": json.dumps(content),
		}
	)

	for link in links:
		workspace.append("links", link)
	for shortcut in shortcuts:
		workspace.append("shortcuts", shortcut)
	for role in roles:
		workspace.append("roles", role)
	for card in number_cards:
		workspace.append("number_cards", card)
	for chart in charts:
		workspace.append("charts", chart)

	if created:
		workspace.insert(ignore_permissions=True)
	else:
		workspace.save(ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache()
	return {"created": created, "workspace": name}


def create_child_workspaces():
	"""Create child workspaces (Operaciones, Reportes, Configuración) under 'Inventario CEDHI' parent."""
	parent = "Inventario CEDHI"
	module = INVENTORY_MODULE
	results = []

	child_pages = [
		{
			"name": "Operaciones",
			"icon": "list",
			"banner_text": '<div class="hero-banner operations-banner"><h1>Operaciones</h1><p>Control de transacciones, incidencias y catálogo maestro de artículos.</p></div>',
			"roles": ["System Manager", "SuperAdministrador Inventario", "Admin TI", "Admin Cocina", "Admin General", "Revisor", "Reportante"],
			"links": [
				{"label": "Documentos de Inventario", "type": "Card Break"},
				{"label": "Catálogo Maestro", "link_to": "Articulo de Inventario", "link_type": "DocType", "type": "Link"},
				{"label": "Kardex Digital", "link_to": "Movimiento de Inventario", "link_type": "DocType", "type": "Link"},
				{"label": "Incidencias", "link_to": "Alerta de Inventario", "link_type": "DocType", "type": "Link"},
			]
		},
		{
			"name": "Reportes",
			"icon": "trending-up",
			"banner_text": '<div class="hero-banner reports-banner"><h1>Reportes</h1><p>Visualización de datos analíticos, stock crítico y reportes históricos.</p></div>',
			"roles": ["System Manager", "SuperAdministrador Inventario", "Admin TI", "Admin Cocina", "Admin General", "Revisor"],
			"links": [
				{"label": "Reportes de Gestión", "type": "Card Break"},
				{"label": "Reporte Maestro (Excel)", "link_to": "Reporte Maestro de Inventario", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
				{"label": "Bandeja de Alertas", "link_to": "Bandeja de Alertas CEDHI", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Alerta de Inventario"},
				{"label": "Kardex de Movimientos", "link_to": "Kardex de Movimientos", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Movimiento de Inventario"},
				{"label": "Stock Crítico", "link_to": "Stock Critico Gastronomia", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
				{"label": "Resumen por Área", "link_to": "Resumen Inventario por Modulo", "link_type": "Report", "type": "Link", "is_query_report": 1, "dependencies": "Articulo de Inventario"},
			]
		},
		{
			"name": "Configuración",
			"icon": "settings",
			"banner_text": '<div class="hero-banner configuration-banner"><h1>Configuración</h1><p>Gestión de espacios físicos, usuarios e importación de catálogos.</p></div>',
			"roles": ["System Manager", "SuperAdministrador Inventario", "Admin TI", "Admin Cocina", "Admin General"],
			"links": [
				{"label": "Parámetros del Sistema", "type": "Card Break"},
				{"label": "Espacios Físicos", "link_to": "Ubicacion", "link_type": "DocType", "type": "Link"},
				{"label": "Importación Masiva", "link_to": "Data Import", "link_type": "DocType", "type": "Link"},
				{"label": "Gestión de Usuarios", "link_to": "User", "link_type": "DocType", "type": "Link"},
			]
		}
	]

	for page in child_pages:
		ws_name = page["name"]
		if frappe.db.exists("Workspace", ws_name):
			workspace = frappe.get_doc("Workspace", ws_name)
			workspace.links = []
			workspace.roles = []
			created = False
		else:
			workspace = frappe.get_doc({"doctype": "Workspace", "label": ws_name, "title": ws_name})
			created = True

		content = [
			{"id": "header", "type": "header", "data": {"text": page["banner_text"], "col": 12}},
			{"id": "card_break", "type": "card", "data": {"card_name": page["links"][0]["label"], "col": 12}}
		]

		workspace.update({
			"label": ws_name,
			"title": ws_name,
			"parent_page": parent,
			"module": module,
			"icon": page["icon"],
			"indicator_color": "blue",
			"public": 1,
			"is_hidden": 0,
			"hide_custom": 1,
			"content": json.dumps(content)
		})

		for link in page["links"]:
			workspace.append("links", link)
		for r in page["roles"]:
			workspace.append("roles", {"role": r})

		if created:
			workspace.insert(ignore_permissions=True)
		else:
			workspace.save(ignore_permissions=True)

		results.append({"name": ws_name, "status": "created" if created else "saved"})

	frappe.db.commit()
	frappe.clear_cache()
	return results


def hide_unwanted_workspaces():
	"""Hide all public workspaces except 'Inventario CEDHI' and its children to keep the sidebar clean."""
	allowed_workspaces = ["Inventario CEDHI", "Operaciones", "Reportes", "Configuración"]

	# Show allowed workspaces
	for ws_name in allowed_workspaces:
		if frappe.db.exists("Workspace", ws_name):
			frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)

	# Hide all other public workspaces
	workspaces_to_hide = frappe.get_all(
		"Workspace",
		filters={"public": 1, "name": ["not in", allowed_workspaces]},
		pluck="name"
	)
	for ws_name in workspaces_to_hide:
		frappe.db.set_value("Workspace", ws_name, "is_hidden", 1, update_modified=False)

	frappe.db.commit()
	frappe.clear_cache()
	return {"hidden_workspaces": workspaces_to_hide}


def enforce_system_language():
	"""Enforce system-wide language to Spanish ('es')."""
	import frappe
	from frappe.translate import set_default_language
	
	# Update System Settings
	system_settings = frappe.get_doc("System Settings")
	system_settings.db_set("language", "es")
	
	# Ensure the global default is set in the DB
	set_default_language("es")
	
	# Update all users to Spanish
	frappe.db.sql("UPDATE `tabUser` SET language = 'es'")
	frappe.clear_cache()
