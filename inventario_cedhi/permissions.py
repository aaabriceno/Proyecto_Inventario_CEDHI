import frappe


SYSTEM_ACCESS_ROLES = {"Administrator", "System Manager"}
INVENTORY_SUPERADMIN_ROLE = "SuperAdministrador Inventario"
REPORTER_ROLE = "Reportante"
FULL_ACCESS_ROLES = SYSTEM_ACCESS_ROLES | {INVENTORY_SUPERADMIN_ROLE}
# "Revisor" (antes "Admin General", fusionados: ver requerimientosNuevos.md
# punto 5) mantiene lectura de todo (ver _read_all_roles abajo) + puede
# registrar Movimientos (Kardex) en cualquier modulo (ver movement_has_permission).
GENERAL_ADMIN_ROLE = "Revisor"


def _module_write_access():
	"""Mapa {rol_admin: {nombre_modulo}} leido de la tabla Modulo.

	Reemplaza el dict fijo que existia antes de que los modulos fueran
	creables dinamicamente (SuperAdministrador crea un Modulo nuevo -> se
	genera su Role "Admin {nombre}" automaticamente, ver modulo.py
	before_insert): este lookup hace que ese rol tenga permisos de escritura
	reales sobre su modulo sin tocar este archivo de nuevo.
	"""
	modulos = frappe.get_all(
		"Modulo",
		filters={"rol_admin": ["is", "set"]},
		fields=["nombre_modulo", "rol_admin"],
	)
	access = {}
	for m in modulos:
		access.setdefault(m.rol_admin, set()).add(m.nombre_modulo)
	return access


def _admin_module_roles():
	"""Todos los roles "Admin {modulo}" existentes (uno por cada Modulo)."""
	return set(_module_write_access())


def _limited_user_roles():
	"""Roles con acceso restringido al sistema (no total): un Admin por cada
	modulo existente + Revisor + Reportante."""
	return _admin_module_roles() | {"Revisor", REPORTER_ROLE}


def _inventory_user_roles():
	return _limited_user_roles() | {INVENTORY_SUPERADMIN_ROLE}


def _read_all_roles():
	return FULL_ACCESS_ROLES | {GENERAL_ADMIN_ROLE}


def _user_roles(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return {"Administrator"}
	return set(frappe.get_roles(user))


def _allowed_modules_for_read(user=None):
	roles = _user_roles(user)
	if roles & _read_all_roles():
		return None

	modules = set()
	for role, role_modules in _module_write_access().items():
		if role in roles:
			modules.update(role_modules)
	return modules


def _allowed_modules_for_write(user=None):
	roles = _user_roles(user)
	if roles & FULL_ACCESS_ROLES:
		return None

	modules = set()
	for role, role_modules in _module_write_access().items():
		if role in roles:
			modules.update(role_modules)
	return modules


def _module_condition(doctype, modules):
	if modules is None:
		return None
	if not modules:
		return "1=0"

	escaped_modules = ", ".join(frappe.db.escape(module) for module in sorted(modules))
	return f"`tab{doctype}`.`modulo` in ({escaped_modules})"


def article_report_condition(user=None, table_alias="a"):
	"""Return a SQL condition for reports that read Articulo de Inventario directly."""
	roles = _user_roles(user)
	if REPORTER_ROLE in roles:
		ubicacion = _reporter_location(user)
		if not ubicacion:
			return "1=0"
		return f"`{table_alias}`.`ubicacion` = {frappe.db.escape(ubicacion)}"

	modules = _allowed_modules_for_read(user)
	if modules is None:
		return "1=1"
	if not modules:
		return "1=0"

	escaped_modules = ", ".join(frappe.db.escape(module) for module in sorted(modules))
	return f"`{table_alias}`.`modulo` in ({escaped_modules})"


def alert_report_condition(user=None, table_alias="a"):
	"""Return a SQL condition for reports that read Alerta de Inventario directly."""
	user = user or frappe.session.user
	roles = _user_roles(user)
	if REPORTER_ROLE in roles and not roles & (FULL_ACCESS_ROLES | _admin_module_roles() | {GENERAL_ADMIN_ROLE}):
		return f"`{table_alias}`.`reportado_por` = {frappe.db.escape(user)}"

	modules = _allowed_modules_for_read(user)
	if modules is None:
		return "1=1"
	if not modules:
		return "1=0"

	escaped_modules = ", ".join(frappe.db.escape(module) for module in sorted(modules))
	return f"`{table_alias}`.`modulo` in ({escaped_modules})"


def article_query_conditions(user=None):
	roles = _user_roles(user)
	if REPORTER_ROLE in roles:
		ubicacion = _reporter_location(user)
		if not ubicacion:
			return "1=0"
		return f"`tabArticulo de Inventario`.`ubicacion` = {frappe.db.escape(ubicacion)}"
	return _module_condition("Articulo de Inventario", _allowed_modules_for_read(user))


def alert_query_conditions(user=None):
	user = user or frappe.session.user
	roles = _user_roles(user)
	if REPORTER_ROLE in roles and not roles & (FULL_ACCESS_ROLES | _admin_module_roles() | {GENERAL_ADMIN_ROLE}):
		return f"`tabAlerta de Inventario`.`reportado_por` = {frappe.db.escape(user)}"
	return _module_condition("Alerta de Inventario", _allowed_modules_for_read(user))


def movement_query_conditions(user=None):
	roles = _user_roles(user)
	if REPORTER_ROLE in roles:
		ubicacion = _reporter_location(user)
		if not ubicacion:
			return "1=0"
		return f"""
			exists (
				select 1
				from `tabArticulo de Inventario` article
				where article.name = `tabMovimiento de Inventario`.`articulo`
				  and article.ubicacion = {frappe.db.escape(ubicacion)}
			)
		"""

	modules = _allowed_modules_for_read(user)
	if modules is None:
		return None
	if not modules:
		return "1=0"

	escaped_modules = ", ".join(frappe.db.escape(module) for module in sorted(modules))
	return f"""
		exists (
			select 1
			from `tabArticulo de Inventario` article
			where article.name = `tabMovimiento de Inventario`.`articulo`
			  and article.modulo in ({escaped_modules})
		)
	"""


def user_query_conditions(user=None):
	user = user or frappe.session.user
	roles = _user_roles(user)
	if roles & SYSTEM_ACCESS_ROLES:
		return None
	if INVENTORY_SUPERADMIN_ROLE in roles:
		inventory_roles = ", ".join(frappe.db.escape(role) for role in sorted(_inventory_user_roles()))
		system_roles = ", ".join(frappe.db.escape(role) for role in sorted(SYSTEM_ACCESS_ROLES))
		return f"""
			exists (
				select 1
				from `tabHas Role`
				where `tabHas Role`.`parent` = `tabUser`.`name`
				  and `tabHas Role`.`role` in ({inventory_roles})
			)
			and not exists (
				select 1
				from `tabHas Role`
				where `tabHas Role`.`parent` = `tabUser`.`name`
				  and `tabHas Role`.`role` in ({system_roles})
			)
		"""
	if roles & _limited_user_roles():
		# Ver (read) esta permitido entre usuarios del mismo rol (ej. un Admin
		# Cocina puede ver a otros Admin Cocina), pero modificar sigue limitado
		# a si mismo (ver user_has_permission). Esto es solo lectura/listado.
		own_roles = roles & _limited_user_roles()
		role_list = ", ".join(frappe.db.escape(role) for role in sorted(own_roles))
		return f"""
			exists (
				select 1
				from `tabHas Role`
				where `tabHas Role`.`parent` = `tabUser`.`name`
				  and `tabHas Role`.`role` in ({role_list})
			)
		"""
	return None


def article_has_permission(doc, ptype=None, user=None):
	ptype = ptype or "read"
	roles = _user_roles(user)
	if REPORTER_ROLE in roles:
		if ptype not in {"read", "select", "print", "report"}:
			return False
		ubicacion = _reporter_location(user)
		if not doc or not ubicacion:
			return bool(ubicacion)
		return doc.ubicacion == ubicacion
	return _has_inventory_module_permission(doc, ptype, user)


def alert_has_permission(doc, ptype=None, user=None):
	ptype = ptype or "read"
	user = user or frappe.session.user
	roles = _user_roles(user)
	if REPORTER_ROLE in roles and not roles & (FULL_ACCESS_ROLES | _admin_module_roles() | {GENERAL_ADMIN_ROLE}):
		if ptype == "create":
			return True
		if ptype in {"read", "write", "select", "print"}:
			return bool(doc and doc.reportado_por == user)
		return False
	return _has_inventory_module_permission(doc, ptype, user)


def movement_has_permission(doc, ptype=None, user=None):
	ptype = ptype or "read"
	roles = _user_roles(user)

	if REPORTER_ROLE in roles:
		if ptype not in {"read", "select", "print", "report"}:
			return False
		ubicacion = _reporter_location(user)
		if not doc or not ubicacion:
			return bool(ubicacion)
		article_location = frappe.db.get_value("Articulo de Inventario", doc.articulo, "ubicacion")
		return article_location == ubicacion

	if ptype in {"read", "select", "print", "email", "report", "export"}:
		modules = _allowed_modules_for_read(user)
	elif GENERAL_ADMIN_ROLE in roles:
		# Admin General ya no administra un modulo propio (el Modulo "General"
		# se elimino, ver requerimientosNuevos.md punto 5: "General" es la
		# vista agregada de TODO, no un modulo mas). Conserva la capacidad de
		# registrar Movimientos (Kardex) en CUALQUIER modulo -- util como rol
		# de supervisor que ayuda a mover stock donde sea necesario sin ser
		# dueno de un modulo especifico. NO puede editar el Articulo de
		# Inventario mismo (eso sigue limitado a quien administra ese modulo).
		modules = None
	else:
		modules = _allowed_modules_for_write(user)

	if modules is None:
		return True
	if not doc:
		return bool(modules)

	article_module = frappe.db.get_value("Articulo de Inventario", doc.articulo, "modulo")
	return article_module in modules


def user_has_permission(doc, ptype=None, user=None):
	ptype = ptype or "read"
	user = user or frappe.session.user
	roles = _user_roles(user)
	if roles & SYSTEM_ACCESS_ROLES:
		return True
	if INVENTORY_SUPERADMIN_ROLE in roles:
		if ptype == "create":
			return True
		if not doc:
			return True
		if getattr(doc, "is_new", None) and doc.is_new():
			return True
		target_roles = set(frappe.get_roles(doc.name))
		return bool(target_roles & _inventory_user_roles()) and not bool(target_roles & SYSTEM_ACCESS_ROLES)
	if roles & _limited_user_roles():
		if not doc:
			return True
		if doc.name == user:
			return True
		if ptype in {"read", "select", "print", "report", "email", "export"}:
			# Solo lectura: puede ver a otros usuarios con su mismo rol.
			own_roles = roles & _limited_user_roles()
			target_roles = set(frappe.get_roles(doc.name))
			return bool(own_roles & target_roles)
		# Cualquier modificacion (write/create/delete) sigue limitada a si mismo.
		return False
	return True


def _has_inventory_module_permission(doc, ptype=None, user=None):
	if ptype in {"read", "select", "print", "email", "report", "export"}:
		modules = _allowed_modules_for_read(user)
	else:
		modules = _allowed_modules_for_write(user)

	if modules is None:
		return True

	if not doc:
		return bool(modules)

	doc_module = getattr(doc, "modulo", None)
	if not doc_module:
		return bool(modules)

	return doc_module in modules


def _reporter_location(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value("User", user, "inventario_ubicacion_asignada")


def validate_data_import_module_scope(doc, method=None):
	"""Restringe Data Import nativo de Frappe para Admin TI/Cocina/General.

	Data Import puede apuntar a cualquier doctype y, sin esta validacion, un
	Admin de modulo (que tiene permiso de import en este doctype para poder
	cargar CSV de su propia area) podria usarlo para tocar otros doctypes
	(User, Role, etc.) o filas de un modulo que no es el suyo. Forzamos:
	1. El doctype de referencia debe ser Articulo de Inventario.
	2. Cada fila del CSV debe pertenecer a su modulo permitido (si la fila no
	   trae modulo, se lo asignamos automaticamente).
	"""
	roles = _user_roles()
	module_write_access = _module_write_access()
	allowed_modules = module_write_access.get(
		next(iter(roles & set(module_write_access)), None)
	)
	if not allowed_modules or roles & FULL_ACCESS_ROLES:
		return

	if doc.reference_doctype != "Articulo de Inventario":
		frappe.throw(
			frappe._("Solo puede importar datos de Articulo de Inventario."),
			frappe.PermissionError,
		)

	if not (doc.import_file or doc.google_sheets_url):
		return

	allowed_module = next(iter(allowed_modules))
	importer = doc.get_importer()
	for payload in importer.import_file.get_payloads_for_import():
		row_module = (payload.doc.get("modulo") or "").strip()
		if row_module != allowed_module:
			frappe.throw(
				frappe._(
					"La fila {0} debe tener modulo '{1}' (su rol solo puede "
					"importar articulos de ese modulo). Incluya la columna "
					"'modulo' con ese valor en cada fila."
				).format(payload.rows[0].row_number, allowed_module),
				frappe.PermissionError,
			)


def ubicacion_has_permission(doc, ptype=None, user=None):
	"""Lectura de Ubicacion para cualquier Admin de modulo.

	El doctype Ubicacion solo tiene permisos de lectura hardcodeados para
	los 3 roles historicos (Admin TI/Cocina/General): un Admin de un modulo
	creado dinamicamente despues (ej. Admin Estilismo) no podia ver/elegir
	ubicaciones al crear un Articulo de su propio modulo. Esto da lectura a
	TODOS los roles "Admin {modulo}" existentes, sin tener que tocar
	permisos cada vez que se crea un modulo nuevo.
	"""
	if ptype != "read":
		return True
	roles = _user_roles(user)
	if roles & (FULL_ACCESS_ROLES | _admin_module_roles()):
		return True
	return None
