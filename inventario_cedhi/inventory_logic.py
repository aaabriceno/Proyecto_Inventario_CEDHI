
import frappe
from frappe import _
from frappe.utils import flt


def require_estado_change_reason(doc, method=None):
    """RF-C03: exige motivo obligatorio al marcar un articulo como 'De baja' o
    'En reparación', para mantener la integridad/trazabilidad del inventario.

    Solo valida cuando el estado cambia hacia un estado critico (no en cada save),
    para no molestar al editar articulos ya dados de baja.
    """
    estados_con_motivo = {"De baja", "En reparación"}
    if doc.estado not in estados_con_motivo:
        return

    # Determinar el estado anterior para validar solo en la transicion.
    estado_anterior = None
    if not doc.is_new():
        estado_anterior = frappe.db.get_value("Articulo de Inventario", doc.name, "estado")

    # Si ya estaba en ese estado y no cambio, no re-exigimos motivo.
    if estado_anterior == doc.estado:
        return

    if not (doc.motivo_cambio_estado or "").strip():
        frappe.throw(
            _("Debe indicar el motivo del cambio de estado al marcar el articulo como '{0}'.").format(
                _(doc.estado)
            ),
            title=_("Motivo obligatorio"),
        )


def set_internal_code(doc, method=None):
    """RF-GE-02: Automatically assign a unique internal code for all inventory modules if not provided."""
    if not doc.codigo_interno and doc.modulo:
        # Map module names to internal prefixes
        tag_map = {
            "TI": "TI",
            "Gastronomia": "GAS",
            "General": "GEN"
        }
        tag = tag_map.get(doc.modulo)
        if not tag:
            return

        # Generate a unique code based on year and next sequential number
        year = frappe.utils.nowdate()[:4]
        prefix = f"INV-{tag}-{year}-"
        
        # Get all existing codes matching this prefix to determine the max suffix
        existing_codes = frappe.get_all(
            "Articulo de Inventario",
            filters={"codigo_interno": ["like", f"{prefix}%"]},
            pluck="codigo_interno"
        )
        
        max_num = 0
        for code in existing_codes:
            if code and code.startswith(prefix):
                suffix = code.replace(prefix, "")
                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))
                    
        # Increment to find the next strictly unused code
        next_num = max_num + 1
        while True:
            candidate = f"{prefix}{str(next_num).zfill(4)}"
            if not frappe.db.exists("Articulo de Inventario", {"codigo_interno": candidate}):
                doc.codigo_interno = candidate
                break
            next_num += 1

def validate_stock_on_movement(doc, method=None):
    """Validación Estricta: Previene salidas de stock mayores al stock actual."""
    if doc.tipo_movimiento == "Salida" and doc.articulo:
        stock_actual = frappe.db.get_value("Articulo de Inventario", doc.articulo, "stock_actual") or 0
        if doc.cantidad > stock_actual:
            frappe.throw(_("Operación bloqueada: No hay suficiente stock. Intentas retirar {0} unidades, pero el stock actual es de solo {1} unidades.").format(doc.cantidad, stock_actual))

def update_stock_on_movement(doc, method=None):
    """Update stock_actual in Articulo de Inventario when a movement is submitted."""
    if not doc.articulo:
        return

    articulo = frappe.get_doc("Articulo de Inventario", doc.articulo)
    
    # Calculate adjustment
    adjustment = doc.cantidad
    if doc.tipo_movimiento == "Salida":
        adjustment = -adjustment
    elif doc.tipo_movimiento == "Ajuste":
        # Ajuste sets the stock directly to doc.cantidad
        current_stock = articulo.stock_actual or 0
        adjustment = doc.cantidad - current_stock
        
    # Validación estricta ya ocurre en `validate` (validate_stock_on_movement)
    # Por lo que aquí asumimos que el stock es correcto.

    new_stock = (articulo.stock_actual or 0) + adjustment
    
    # Update the article
    articulo.db_set("stock_actual", new_stock)
    
    # Log the change in the article's comments/timeline
    articulo.add_comment("Comment", _("Stock actualizado a {0} ({1} por {2})").format(
        new_stock, doc.tipo_movimiento, doc.name
    ))

def reverse_stock_on_cancel(doc, method=None):
    """Reverse the stock update if a movement is cancelled."""
    if not doc.articulo:
        return

    articulo = frappe.get_doc("Articulo de Inventario", doc.articulo)
    
    if doc.tipo_movimiento == "Ajuste":
        # Revert back to the stock value before this adjustment was submitted
        prev_stock = doc.stock_actual_articulo or 0
        articulo.db_set("stock_actual", prev_stock)
        articulo.add_comment("Comment", _("Movimiento {0} cancelado. Stock revertido a {1} (anterior al Ajuste)").format(
            doc.name, prev_stock
        ))
        return

    # Calculate reverse adjustment
    adjustment = doc.cantidad
    if doc.tipo_movimiento == "Entrada":
        adjustment = -adjustment
        
    new_stock = (articulo.stock_actual or 0) + adjustment
    articulo.db_set("stock_actual", new_stock)
    
    articulo.add_comment("Comment", _("Movimiento {0} cancelado. Stock revertido a {1}").format(
        doc.name, new_stock
    ))


@frappe.whitelist()
def create_quick_movement(articulo, tipo_movimiento, cantidad, motivo):
    """Allow quick creation and submission of a Movimiento de Inventario from UI dialogs."""
    if not frappe.has_permission("Movimiento de Inventario", "create"):
        frappe.throw(_("No tiene permisos para registrar movimientos de inventario"))
        
    doc = frappe.get_doc({
        "doctype": "Movimiento de Inventario",
        "articulo": articulo,
        "tipo_movimiento": tipo_movimiento,
        "cantidad": flt(cantidad),
        "motivo": motivo,
        "fecha": frappe.utils.today(),
        "responsable": frappe.session.user
    })
    
    from inventario_cedhi.permissions import movement_has_permission
    if not movement_has_permission(doc, "create", frappe.session.user):
        frappe.throw(_("No tiene permisos para registrar movimientos en este módulo"))
        
    doc.insert(ignore_permissions=True)
    doc.submit()
    return doc.name


def force_spanish_language(*args, **kwargs):
    """Enforce Spanish ('es') language on all requests and background jobs."""
    import frappe
    if hasattr(frappe.local, "lang"):
        frappe.local.lang = "es"


def enforce_user_language(doc, method=None):
    """Ensure user language is forced to Spanish ('es')."""
    doc.language = "es"






