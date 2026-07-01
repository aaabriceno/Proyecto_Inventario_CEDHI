# Copyright (c) 2026, CEDHI Nueva Arequipa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# Permisos base que cada Role "Admin {modulo}" necesita sobre los doctypes del
# inventario, calcados de los que ya tienen los 3 roles historicos (Admin TI/
# Cocina) en los .json versionados. SIN ESTO un rol nuevo queda sin ningun
# DocPerm base: Frappe no concede un permiso via has_permission/
# permission_query_conditions (ver permissions.py) si no existe AL MENOS una
# fila de permiso base para algun rol del usuario -- el hook solo puede
# RESTRINGIR un acceso que el permiso base ya otorga, nunca otorgarlo desde
# cero. Bug real encontrado: un usuario con SOLO rol "Admin Estilismo" no
# podia ni leer Articulo de Inventario, porque ese doctype solo lista los 3
# roles historicos en su tabla de permisos.
_MODULE_ROLE_PERMISSIONS = {
	"Articulo de Inventario": {
		"create": 1, "delete": 1, "email": 1, "export": 1, "import": 1,
		"print": 1, "read": 1, "report": 1, "select": 1, "write": 1,
	},
	"Ubicacion": {"print": 1, "read": 1, "report": 1, "select": 1},
	"Alerta de Inventario": {
		"create": 1, "delete": 1, "email": 1, "export": 1,
		"print": 1, "read": 1, "report": 1, "select": 1, "write": 1,
	},
	"Movimiento de Inventario": {
		"cancel": 1, "create": 1, "delete": 1, "email": 1, "export": 1,
		"print": 1, "read": 1, "report": 1, "select": 1, "submit": 1, "write": 1,
	},
}


class Modulo(Document):
	def before_rename(self, old_name, new_name, merge=False):
		"""Si el Role "Admin {old_name}" sigue llamandose igual que el Modulo
		(caso normal, sin rol_admin custom), lo renombra junto con el Modulo.

		Sin esto, renombrar un Modulo desde el menu "..." -> Rename (que el
		CEDHI puede hacer libremente, allow_rename:1) deja el Modulo con
		nombre nuevo pero su Role de acceso con el nombre VIEJO -- el campo
		`rol_admin` queda apuntando a un Role que ya no coincide con el
		nombre del Modulo, confuso y con riesgo de que alguien borre ese Role
		pensando que es basura (los usuarios de ese modulo perderian acceso).
		"""
		default_role_name = f"Admin {old_name}"
		if self.rol_admin == default_role_name and frappe.db.exists("Role", default_role_name):
			frappe.rename_doc("Role", default_role_name, f"Admin {new_name}", force=True)

	def after_rename(self, old_name, new_name, merge=False):
		"""Mantiene rol_admin sincronizado con el nuevo nombre tras el rename
		de Role hecho en before_rename (rename_doc no actualiza el doc en
		memoria que se esta renombrando)."""
		default_role_name = f"Admin {old_name}"
		if self.rol_admin == default_role_name:
			frappe.db.set_value("Modulo", new_name, "rol_admin", f"Admin {new_name}", update_modified=False)

	def before_insert(self):
		"""Crea automaticamente el Role "Admin {nombre_modulo}" para este modulo,
		y le otorga los permisos base que necesita sobre los doctypes del
		inventario (ver _MODULE_ROLE_PERMISSIONS arriba).

		Asi cualquier modulo nuevo (creado por el SuperAdministrador) tiene de
		inmediato un rol usable, con acceso de escritura solo a su modulo (el
		ALCANCE lo sigue filtrando permissions.py dinamicamente segun
		Modulo.rol_admin; aqui solo se otorga el permiso BASE que Frappe exige
		para que ese filtrado dinamico pueda aplicarse). Si rol_admin ya viene
		asignado (ej. seed de los modulos historicos TI/Gastronomia, que
		reusan los roles "Admin TI"/"Admin Cocina" ya existentes, los cuales
		YA tienen sus permisos en los .json versionados), no se duplican
		permisos para esos roles.
		"""
		role_name = self.rol_admin or f"Admin {self.nombre_modulo}"
		is_new_role = not frappe.db.exists("Role", role_name)
		if is_new_role:
			frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}).insert(ignore_permissions=True)
			self._grant_module_role_permissions(role_name)
		self.rol_admin = role_name

	def after_insert(self):
		"""Crea el filtro de lista 'Inventario {nombre}' para el modulo nuevo.

		before_insert ya crea el Role y sus DocPerms. Aqui creamos el filtro
		guardado en la lista de Articulo de Inventario para que el Admin del
		modulo tenga de inmediato un acceso rapido a sus articulos, igual que
		TI y Gastronomia tienen 'Inventario TI' / 'Inventario Gastronomia'.
		"""
		import json
		doctype_name = "Articulo de Inventario"
		filter_name = f"Inventario {self.nombre_modulo}"
		if frappe.db.exists("List Filter", {"filter_name": filter_name, "reference_doctype": doctype_name}):
			return
		filters = [[doctype_name, "modulo", "=", self.nombre_modulo, False]]
		frappe.get_doc({
			"doctype": "List Filter",
			"filter_name": filter_name,
			"reference_doctype": doctype_name,
			"filters": json.dumps(filters),
		}).insert(ignore_permissions=True)
		frappe.db.commit()

	def _grant_module_role_permissions(self, role_name):
		for doctype, perms in _MODULE_ROLE_PERMISSIONS.items():
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role_name}):
				continue
			frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": role_name,
				**perms,
			}).insert(ignore_permissions=True)
