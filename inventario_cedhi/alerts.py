import frappe

from inventario_cedhi.permissions import FULL_ACCESS_ROLES, _admin_module_roles


def set_alert_defaults(doc, method=None):
	"""Set reporting defaults and keep reporter-created alerts in report state."""
	article = None
	if doc.articulo:
		article = frappe.db.get_value(
			"Articulo de Inventario",
			doc.articulo,
			["modulo", "ubicacion"],
			as_dict=True,
		)
		if article:
			doc.modulo = article.modulo
			doc.ubicacion = article.ubicacion

	if not doc.reportado_por:
		doc.reportado_por = frappe.session.user

	if not doc.fecha_reporte:
		doc.fecha_reporte = frappe.utils.today()

	if _is_reporter_only():
		_validate_reporter_location(article)
		doc.estado_alerta = "Pendiente"
		doc.accion_tomada = None
		doc.fecha_resolucion = None


def _is_reporter_only():
	if frappe.session.user == "Administrator":
		return False

	roles = set(frappe.get_roles(frappe.session.user))
	admin_roles = FULL_ACCESS_ROLES | _admin_module_roles()
	return "Reportante" in roles and not roles & admin_roles


def _validate_reporter_location(article):
	assigned_location = frappe.db.get_value(
		"User",
		frappe.session.user,
		"inventario_ubicacion_asignada",
	)
	if not assigned_location:
		frappe.throw(
			"El usuario reportante no tiene una ubicacion asignada para crear alertas."
		)

	if not article or article.ubicacion != assigned_location:
		frappe.throw(
			"El usuario reportante solo puede crear alertas de articulos de su ubicacion asignada."
		)
