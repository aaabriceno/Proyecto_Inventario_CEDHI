"""Hooks de instalacion y migracion para inventario_cedhi.

Objetivo: que la app quede 100% funcional en cualquier despliegue (local, Oracle,
servidor del CEDHI) sin pasos manuales. Los DocTypes viven versionados en .json y
los sincroniza el migrate estandar de Frappe; aqui solo aseguramos la configuracion
que NO viaja en .json: custom fields de User, permisos de rol, workspaces, branding
y datos de referencia minimos.

Todas las funciones llamadas aqui son idempotentes: correr esto multiples veces no
duplica ni rompe nada.
"""

from contextlib import contextmanager

import frappe


@contextmanager
def _developer_mode():
	"""Activa developer_mode temporalmente.

	El setup ajusta la estructura de DocTypes de app (custom=0). Frappe solo
	permite modificar esos DocTypes en developer_mode; sin el, lanza
	CannotCreateStandardDoctypeError (caso tipico al instalar en un contenedor
	de produccion). Lo activamos solo durante el setup y lo restauramos al final.
	"""
	previous = frappe.conf.get("developer_mode")
	frappe.flags.in_developer_mode = True
	frappe.conf.developer_mode = 1
	try:
		yield
	finally:
		frappe.conf.developer_mode = previous
		frappe.flags.in_developer_mode = bool(previous)


def after_install():
	"""Se ejecuta una vez al instalar la app en un sitio nuevo.

	Construye toda la estructura MVP desde cero (incluye usuarios iniciales y
	datos de referencia), ya que un sitio recien instalado esta vacio.
	"""
	from inventario_cedhi.setup_inventory import setup_inventory_mvp

	with _developer_mode():
		setup_inventory_mvp()
	frappe.db.commit()


def after_migrate():
	"""Se ejecuta tras cada `bench migrate`.

	Re-asegura solo la configuracion idempotente (campos, permisos, workspaces,
	branding). No recrea usuarios ni datos para no pisar informacion real del
	sitio en produccion.
	"""
	ensure_runtime_configuration()
	frappe.db.commit()


def ensure_runtime_configuration():
	"""Configuracion segura de re-aplicar en cualquier migracion.

	Mantiene la app consistente tras actualizaciones de codigo sin tocar datos.
	"""
	import inventario_cedhi.setup_inventory as setup

	steps = [
		("Module Def", setup.ensure_inventory_module_def),
		("Disable Unused Roles", setup.disable_unused_erpnext_roles),
		("Reporter User Fields", setup.configure_reporter_user_fields),
		("Role Permissions", setup.configure_inventory_role_permissions),
		("List Views", setup.configure_inventory_list_views),
		("Article Status Options", setup.configure_article_status_options),
		("Module Form Rules", setup.configure_module_specific_article_form),
		("Workspace", setup.create_inventory_workspace),
		("Child Workspaces", setup.create_child_workspaces),
		("Hide Workspaces", setup.hide_unwanted_workspaces),
		("Client Scripts", setup.create_inventory_client_scripts),
	]

	results = {}
	with _developer_mode():
		for label, fn in steps:
			try:
				results[label] = fn()
			except Exception:
				# Un paso de config que falle no debe abortar todo el migrate.
				frappe.log_error(
					title=f"inventario_cedhi after_migrate: {label}",
					message=frappe.get_traceback(),
				)
				results[label] = {"error": True}

	setup.enforce_system_language()
	setup.apply_cedhi_branding()
	return results
