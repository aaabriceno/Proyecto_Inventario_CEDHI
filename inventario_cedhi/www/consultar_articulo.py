"""Pagina de consulta rapida de un Articulo de Inventario por codigo
escaneado (QR de la etiqueta o codigo de barras).

Accesible a cualquier usuario logueado (no solo roles admin): el alcance
real lo filtra `buscar_articulo_por_codigo` (inventory_logic.py) via
`article_has_permission`, igual que el resto del sistema -- un Admin TI
que escanea un articulo de otro modulo recibe error de permiso, no la
ficha.
"""

import frappe


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.throw("Debe iniciar sesion.", frappe.PermissionError)

	return context
