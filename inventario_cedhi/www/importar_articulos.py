"""Pagina de subida de Excel de articulos desde el navegador, con preview
antes de tocar la base de datos.

Flujo: subir archivo -> preview (dry_run, sin tocar BD) -> confirmar
(importacion real) o cancelar. Solo SuperAdministrador/System Manager,
igual que `importar_articulos_excel_endpoint` (el importador por consola
que ya existia).
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

	return context
