"""Pagina de carga del catalogo inicial del CEDHI.

Muestra un boton que dispara el importador idempotente. Solo accesible para
SuperAdministrador / System Manager.
"""

import frappe

ALLOWED_ROLES = {"System Manager", "SuperAdministrador Inventario", "Administrator"}


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.throw("Debe iniciar sesion.", frappe.PermissionError)

	roles = set(frappe.get_roles())
	context.puede_importar = bool(roles & ALLOWED_ROLES)
	context.resultado = None

	if frappe.request and frappe.request.method == "POST" and context.puede_importar:
		from inventario_cedhi.data_import import import_catalogo_inicial

		only_module = frappe.form_dict.get("modulo") or None
		context.resultado = import_catalogo_inicial(only_module=only_module)

	return context
