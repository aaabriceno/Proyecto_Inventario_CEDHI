
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


def _slug_for_codigo(value):
    """Normaliza un nombre (modulo/ubicacion) a un slug corto para el codigo_interno."""
    import re
    slug = re.sub(r"[^A-Za-z0-9]+", "", (value or "").upper())
    return slug[:12] or "SN"


def set_internal_code(doc, method=None):
    """RF-GE-02: Genera/actualiza codigo_interno como etiqueta legible de la
    ubicacion fisica actual del articulo (modulo + ubicacion + secuencial).

    A diferencia del identificador permanente del articulo (campo `ID`, fijo
    de por vida, ver create_articulo_inventario_doctype), codigo_interno SI
    se recalcula cuando el articulo cambia de modulo o de ubicacion -- es
    una etiqueta descriptiva del estado actual, no un identificador estable.
    Por eso corre en validate (no solo before_insert): debe reaccionar a
    cualquier update que cambie modulo/ubicacion, no solo a la creacion.
    """
    if not doc.modulo or not doc.ubicacion:
        return

    modulo_anterior = ubicacion_anterior = None
    if not doc.is_new():
        prev = frappe.db.get_value(
            "Articulo de Inventario", doc.name, ["modulo", "ubicacion"], as_dict=True
        )
        if prev:
            modulo_anterior, ubicacion_anterior = prev.modulo, prev.ubicacion

    sin_cambio_de_lugar = doc.modulo == modulo_anterior and doc.ubicacion == ubicacion_anterior
    if doc.codigo_interno and sin_cambio_de_lugar:
        return

    prefix = f"INV-{_slug_for_codigo(doc.modulo)}-{_slug_for_codigo(doc.ubicacion)}-"

    existing_codes = frappe.get_all(
        "Articulo de Inventario",
        filters={"codigo_interno": ["like", f"{prefix}%"]},
        pluck="codigo_interno",
    )

    max_num = 0
    for code in existing_codes:
        if code and code.startswith(prefix):
            suffix = code[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

    next_num = max_num + 1
    while True:
        candidate = f"{prefix}{str(next_num).zfill(4)}"
        if not frappe.db.exists("Articulo de Inventario", {"codigo_interno": candidate}):
            doc.codigo_interno = candidate
            break
        next_num += 1

def validate_stock_on_movement(doc, method=None):
    """Validación Estricta: Previene salidas de stock mayores al stock actual."""
    # En Ajuste, cantidad es el stock TOTAL nuevo (no un delta): 0 es valido
    # (ej. perdida total confirmada). En Entrada/Salida, cantidad es un delta
    # y 0/negativo no tiene sentido.
    if doc.tipo_movimiento != "Ajuste" and doc.cantidad is not None and doc.cantidad <= 0:
        frappe.throw(_("La cantidad debe ser mayor a cero."))
    elif doc.tipo_movimiento == "Ajuste" and doc.cantidad is not None and doc.cantidad < 0:
        frappe.throw(_("La cantidad no puede ser negativa."))

    if doc.tipo_movimiento == "Salida" and doc.articulo:
        stock_actual = frappe.db.get_value("Articulo de Inventario", doc.articulo, "stock_actual") or 0
        if doc.cantidad > stock_actual:
            frappe.throw(_("Operación bloqueada: No hay suficiente stock. Intentas retirar {0} unidades, pero el stock actual es de solo {1} unidades.").format(doc.cantidad, stock_actual))


def update_stock_on_movement(doc, method=None):
    """Update stock_actual in Articulo de Inventario when a movement is submitted.

    Guarda stock_antes_del_movimiento/stock_despues_del_movimiento como
    snapshot real (no fetch_from, que se recalcularia con el valor actual al
    leer el doc despues): reverse_stock_on_cancel necesita el delta EXACTO
    aplicado por este movimiento especifico, no un recalculo basado en el
    stock de hoy, que puede ya estar afectado por movimientos posteriores.
    """
    if not doc.articulo:
        return

    articulo = frappe.get_doc("Articulo de Inventario", doc.articulo)
    stock_antes = articulo.stock_actual or 0

    if doc.tipo_movimiento == "Salida":
        adjustment = -doc.cantidad
    elif doc.tipo_movimiento == "Ajuste":
        # Ajuste sets the stock directly to doc.cantidad
        adjustment = doc.cantidad - stock_antes
    else:
        adjustment = doc.cantidad

    new_stock = stock_antes + adjustment
    if new_stock < 0:
        frappe.throw(
            _("Operación bloqueada: el stock resultante seria negativo ({0}).").format(new_stock)
        )

    articulo.db_set("stock_actual", new_stock)
    doc.db_set("stock_antes_del_movimiento", stock_antes, update_modified=False)
    doc.db_set("stock_despues_del_movimiento", new_stock, update_modified=False)

    articulo.add_comment("Comment", _("Stock actualizado a {0} ({1} por {2})").format(
        new_stock, doc.tipo_movimiento, doc.name
    ))


def reverse_stock_on_cancel(doc, method=None):
    """Reverse the stock update if a movement is cancelled.

    Usa el snapshot guardado en update_stock_on_movement (stock_antes_del_movimiento):
    si hubo movimientos posteriores sobre el mismo articulo, recalcular en vez
    de usar el snapshot daria un valor incorrecto. Movimientos anteriores a la
    introduccion de este snapshot se completan via el patch
    backfill_stock_antes_del_movimiento durante la migracion.
    """
    if not doc.articulo:
        return

    prev_stock = doc.stock_antes_del_movimiento or 0
    articulo = frappe.get_doc("Articulo de Inventario", doc.articulo)
    articulo.db_set("stock_actual", prev_stock)
    articulo.add_comment("Comment", _("Movimiento {0} cancelado. Stock revertido a {1}").format(
        doc.name, prev_stock
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


@frappe.whitelist()
def reasignar_articulo(articulo, modulo, ubicacion):
    """Cambia el modulo y/o ubicacion de un Articulo de Inventario sin abrir
    el formulario completo (requerimientosNuevos.md punto 6: "boton de
    reasignar... dentro de cada modulo").

    Solo valida permiso de escritura sobre el modulo ACTUAL del articulo
    (el de origen): si el usuario ya podia editar ese articulo, puede
    reasignarlo a cualquier modulo destino, sin necesitar permiso en ese
    destino -- lo que importa es si tenia derecho a tocar el articulo
    antes de moverlo, no a donde lo manda (decision confirmada con el
    usuario: a diferencia de Ubicacion, que es independiente de modulo,
    el modulo de un Articulo SI es la unidad de responsabilidad real).

    Si el modulo cambia, se borran los atributos libres (tabla `atributos`,
    ej. "IP asignada"): una caracteristica de TI no tiene sentido si el
    articulo pasa a Mobiliaria. El aviso/confirmacion de que esto va a
    pasar vive en el dialog del frontend (ver reasignar_dialog_helper en
    setup_inventory.py), aqui solo se ejecuta el borrado ya confirmado.
    """
    doc = frappe.get_doc("Articulo de Inventario", articulo)
    if not doc.has_permission("write"):
        frappe.throw(
            _("No tiene permisos para reasignar este articulo."),
            frappe.PermissionError,
        )

    if doc.modulo != modulo:
        doc.atributos = []

    doc.modulo = modulo
    doc.ubicacion = ubicacion
    doc.save(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def articulo_tiene_atributos(articulo):
    """Devuelve True si el Articulo tiene al menos 1 fila en `atributos`.

    Usado por el dialog de Reasignar (frontend) para decidir el texto del
    aviso de confirmacion antes de cambiar de modulo: distinto mensaje si
    hay atributos que se van a perder vs si no hay nada que perder.
    """
    return bool(frappe.db.count("Atributo de Articulo", {"parent": articulo}))


def force_spanish_language(*args, **kwargs):
    """Enforce Spanish ('es') language on all requests and background jobs."""
    import frappe
    if hasattr(frappe.local, "lang"):
        frappe.local.lang = "es"


def enforce_user_language(doc, method=None):
    """Ensure user language is forced to Spanish ('es')."""
    doc.language = "es"


def _cedhi_roles():
    """Todos los roles del CEDHI: Admin de cada modulo existente (dinamico,
    ver permissions.py:_admin_module_roles) + los roles fijos restantes."""
    from inventario_cedhi.permissions import (
        INVENTORY_SUPERADMIN_ROLE,
        REPORTER_ROLE,
        _admin_module_roles,
    )
    return _admin_module_roles() | {INVENTORY_SUPERADMIN_ROLE, "Revisor", REPORTER_ROLE}


def enforce_default_workspace(doc, method=None):
    """Fuerza que todo usuario del CEDHI aterrice en el workspace de inventario.

    role_home_page (hooks.py) NO aplica a Desk/System Users (solo a Website
    Users, ver frappe/www/login.py): para System Users, Frappe resuelve la
    pagina tras login via User.default_workspace, y si esta vacio cae al
    workspace por defecto del sitio (Home). Sin esto, cualquier usuario del
    CEDHI sin default_workspace propio termina en /app/home en vez de su panel.
    """
    if doc.user_type != "System User":
        return
    roles = {r.role for r in doc.roles}
    if roles & _cedhi_roles() and not doc.default_workspace:
        doc.default_workspace = "Inventario CEDHI"






