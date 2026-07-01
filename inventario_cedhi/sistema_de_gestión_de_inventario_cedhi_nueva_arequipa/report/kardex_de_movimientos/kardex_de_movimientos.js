frappe.query_reports["Kardex de Movimientos"] = {
	"filters": [
		{
			"fieldname": "modulo",
			"label": __("Módulo"),
			"fieldtype": "Link",
			"options": "Modulo",
		},
		{
			"fieldname": "ubicacion",
			"label": __("Ubicación"),
			"fieldtype": "Link",
			"options": "Ubicacion",
		},
		{
			"fieldname": "articulo",
			"label": __("Artículo"),
			"fieldtype": "Link",
			"options": "Articulo de Inventario",
		},
		{
			"fieldname": "tipo_movimiento",
			"label": __("Tipo de movimiento"),
			"fieldtype": "Select",
			"options": "\nEntrada\nSalida\nAjuste",
		},
		{
			"fieldname": "fecha_desde",
			"label": __("Fecha desde"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "fecha_hasta",
			"label": __("Fecha hasta"),
			"fieldtype": "Date",
		},
	]
};
