"""Pagina de carga de las ubicaciones reales del CEDHI.

Muestra un boton que dispara el importador idempotente de Ubicacion a partir
de los archivos en datos_iniciales/INVENTARIO_2026/. Solo accesible para
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
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.resultado = None

	if frappe.request and frappe.request.method == "POST" and context.puede_importar:
		from inventario_cedhi.data_import import importar_ubicaciones_reales

		context.resultado = importar_ubicaciones_reales()

	return context
