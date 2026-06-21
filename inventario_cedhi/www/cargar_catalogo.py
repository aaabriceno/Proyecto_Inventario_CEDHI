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
	context.encolado = False

	# La carga corre en background (ver data_import.encolar_catalogo_inicial):
	# con ~1150 filas, ejecutarla dentro de este request HTTP excede el
	# timeout de nginx en produccion. El POST solo encola el job; la pagina
	# escucha el evento realtime "cedhi_catalogo_inicial_done" para mostrar
	# el resultado sin que el usuario tenga que recargar.
	if frappe.request and frappe.request.method == "POST" and context.puede_importar:
		from inventario_cedhi.data_import import encolar_catalogo_inicial

		only_module = frappe.form_dict.get("modulo") or None
		encolar_catalogo_inicial(only_module=only_module)
		context.encolado = True

	return context
