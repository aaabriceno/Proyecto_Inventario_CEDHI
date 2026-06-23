import frappe


def execute():
	"""Calcula stock_antes_del_movimiento/stock_despues_del_movimiento para los
	Movimiento de Inventario que se crearon antes de que estos campos existieran.

	Esos registros quedaron con el default de columna (0.0, no NULL, porque el
	campo es Float/decimal NOT NULL), indistinguible de un snapshot real en 0.
	reverse_stock_on_cancel ya no tiene un fallback "legacy": asume que el
	snapshot siempre es correcto, asi que sin este backfill cancelar un
	movimiento viejo pondria el stock del articulo en 0 en vez de revertirlo
	bien.

	Reconstruye el historial reproduciendo los movimientos de cada articulo en
	orden cronologico inverso a partir de su stock_actual de hoy.
	"""
	if not frappe.db.has_column("Movimiento de Inventario", "stock_antes_del_movimiento"):
		return

	candidatos = frappe.get_all(
		"Movimiento de Inventario",
		filters={
			"docstatus": 1,
			"stock_antes_del_movimiento": 0,
			"stock_despues_del_movimiento": 0,
		},
		fields=["name", "articulo"],
	)
	articulos = {c.articulo for c in candidatos if c.articulo}

	for articulo in articulos:
		movimientos = frappe.get_all(
			"Movimiento de Inventario",
			filters={"articulo": articulo, "docstatus": 1},
			fields=["name", "tipo_movimiento", "cantidad", "stock_antes_del_movimiento", "stock_despues_del_movimiento"],
			order_by="creation desc",
		)
		if not movimientos:
			continue

		stock_despues = frappe.db.get_value("Articulo de Inventario", articulo, "stock_actual") or 0

		for mov in movimientos:
			# Si ya tiene snapshot real (no es 0/0), confiar en el y seguir
			# reconstruyendo hacia atras desde su stock_antes.
			ya_tiene_snapshot = not (mov.stock_antes_del_movimiento == 0 and mov.stock_despues_del_movimiento == 0)

			if mov.tipo_movimiento == "Salida":
				stock_antes = stock_despues + (mov.cantidad or 0)
			elif mov.tipo_movimiento == "Ajuste":
				# El delta real de un Ajuste viejo no es recuperable (cantidad es
				# el total nuevo, no el delta): usamos stock_despues como mejor
				# estimacion de stock_antes tambien, ya que es el unico dato que
				# tenemos con certeza para seguir la cadena hacia atras.
				stock_antes = stock_despues
			else:
				stock_antes = stock_despues - (mov.cantidad or 0)

			if not ya_tiene_snapshot:
				frappe.db.set_value(
					"Movimiento de Inventario",
					mov.name,
					{
						"stock_antes_del_movimiento": stock_antes,
						"stock_despues_del_movimiento": stock_despues,
					},
					update_modified=False,
				)

			stock_despues = stock_antes

	frappe.db.commit()
