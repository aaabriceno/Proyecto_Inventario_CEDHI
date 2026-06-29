
import frappe
from frappe import _
from inventario_cedhi.permissions import article_report_condition

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("ID"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Articulo de Inventario",
            "width": 140
        },
        {
            "label": _("Articulo"),
            "fieldname": "nombre_articulo",
            "fieldtype": "Data",
            "width": 260
        },
        {
            "label": _("Modulo"),
            "fieldname": "modulo",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Ubicacion"),
            "fieldname": "ubicacion",
            "fieldtype": "Link",
            "options": "Ubicacion",
            "width": 140
        },
        {
            "label": _("Asignacion"),
            "fieldname": "asignacion",
            "fieldtype": "Link",
            "options": "Asignacion",
            "width": 140
        },
        {
            "label": _("Estado"),
            "fieldname": "estado",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Stock Actual"),
            "fieldname": "stock_actual",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Stock Critico"),
            "fieldname": "stock_critico",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Unidad"),
            "fieldname": "unidad_medida",
            "fieldtype": "Data",
            "width": 80
        },
        {
            "label": _("Fecha Adquisicion"),
            "fieldname": "fecha_adquisicion",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Marca"),
            "fieldname": "marca",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Modelo"),
            "fieldname": "modelo",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Codigo Interno"),
            "fieldname": "codigo_interno",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Atributos"),
            "fieldname": "atributos",
            "fieldtype": "Data",
            "width": 220
        }
    ]

def get_data(filters):
    conditions = f" and {article_report_condition(table_alias='a')}"
    if filters.get("modulo"):
        conditions += f" and a.modulo = {frappe.db.escape(filters.get('modulo'))}"
    if filters.get("ubicacion"):
        conditions += f" and a.ubicacion = {frappe.db.escape(filters.get('ubicacion'))}"
    if filters.get("estado"):
        conditions += f" and a.estado = {frappe.db.escape(filters.get('estado'))}"
    if filters.get("fecha_desde"):
        conditions += f" and a.fecha_adquisicion >= {frappe.db.escape(filters.get('fecha_desde'))}"
    if filters.get("fecha_hasta"):
        conditions += f" and a.fecha_adquisicion <= {frappe.db.escape(filters.get('fecha_hasta'))}"
    if filters.get("nombre_articulo"):
        conditions += f" and a.nombre_articulo like {frappe.db.escape('%' + filters.get('nombre_articulo') + '%')}"
    if filters.get("solo_stock_critico"):
        conditions += " and ifnull(a.stock_critico, 0) > 0 and ifnull(a.stock_actual, 0) < ifnull(a.stock_critico, 0)"

    rows = frappe.db.sql(f"""
        select
            a.name, a.nombre_articulo, a.modulo, a.ubicacion, a.asignacion, a.estado,
            a.stock_actual, a.stock_critico, a.unidad_medida, a.fecha_adquisicion,
            a.marca, a.modelo, a.codigo_interno
        from
            `tabArticulo de Inventario` a
        where
            1=1 {conditions}
        order by
            a.modulo, a.nombre_articulo
    """, as_dict=1)

    if not rows:
        return rows

    # Atributos libres (tabla "Atributo de Articulo", ver Parte C): se
    # concatenan como texto "Caracteristica: Valor; ..." en una sola columna
    # -- cada articulo puede tener un numero distinto de atributos, no
    # encajan como columnas fijas en una tabla plana.
    nombres = [r.name for r in rows]
    atributos_rows = frappe.db.sql(
        """
        select parent, nombre_caracteristica, valor
        from `tabAtributo de Articulo`
        where parent in %(nombres)s
        order by parent, idx
        """,
        {"nombres": nombres},
        as_dict=1,
    )
    atributos_por_articulo = {}
    for ar in atributos_rows:
        atributos_por_articulo.setdefault(ar.parent, []).append(f"{ar.nombre_caracteristica}: {ar.valor}")

    for r in rows:
        r["atributos"] = "; ".join(atributos_por_articulo.get(r.name, []))

    return rows
