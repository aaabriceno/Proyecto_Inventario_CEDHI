
frappe.query_reports["Reporte Maestro de Inventario"] = {
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
			"fieldname": "estado",
			"label": __("Estado"),
			"fieldtype": "Select",
			"options": "\nActivo\nDe baja\nEn reparación",
		},
		{
			"fieldname": "fecha_desde",
			"label": __("Fecha adquisición desde"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "fecha_hasta",
			"label": __("Fecha adquisición hasta"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "nombre_articulo",
			"label": __("Nombre del Artículo"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "solo_stock_critico",
			"label": __("Solo stock crítico"),
			"fieldtype": "Check",
		}
	]
};
