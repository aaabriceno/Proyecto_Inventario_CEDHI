frappe.query_reports["Bandeja de Alertas CEDHI"] = {
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
			"fieldname": "tipo_alerta",
			"label": __("Tipo de alerta"),
			"fieldtype": "Select",
			"options": "\nStock bajo\nDañado\nPerdido\nVencido\nAjuste de stock\nOtro",
		},
		{
			"fieldname": "estado_alerta",
			"label": __("Estado"),
			"fieldtype": "Select",
			"options": "\nPendiente\nEn revision\nResuelto",
			"default": "Pendiente",
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
