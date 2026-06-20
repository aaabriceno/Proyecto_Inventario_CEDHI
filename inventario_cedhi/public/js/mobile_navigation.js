(function () {
    const MOBILE_QUERY = "(max-width: 1024px)";

    document.documentElement.dataset.cedhiMobileNavigation = "loaded";
    window.cedhi_mobile_navigation = window.cedhi_mobile_navigation || {};

    function isMobile() {
        const visualWidth = window.visualViewport ? window.visualViewport.width : window.innerWidth;
        return (
            window.matchMedia(MOBILE_QUERY).matches
            || window.innerWidth <= 1024
            || document.documentElement.clientWidth <= 1024
            || visualWidth <= 1024
        );
    }

    function shouldShowBackButton() {
        const path = window.location.pathname.toLowerCase();
        if (!path.startsWith("/app")) {
            return false;
        }

        return !["/app", "/app/home"].includes(path);
    }

    function goBack() {
        if (window.history.length > 1) {
            window.history.back();
            return;
        }

        if (window.frappe && frappe.set_route) {
            frappe.set_route("Workspaces", "Inventario CEDHI");
        }
    }

    function applyButtonStyles(button) {
        const styles = {
            position: "fixed",
            left: "12px",
            bottom: "14px",
            zIndex: "2147483000",
            display: "inline-flex",
            visibility: "visible",
            opacity: "1",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "34px",
            padding: "7px 12px",
            border: "1px solid #e5e7eb",
            borderRadius: "999px",
            background: "#ffffff",
            boxShadow: "0 8px 18px rgba(15, 23, 42, 0.18)",
            color: "#111827",
            fontWeight: "600",
            pointerEvents: "auto",
        };
        Object.entries(styles).forEach(([property, value]) => {
            button.style.setProperty(property, value, "important");
        });
    }

    function ensureBackButton() {
        let existingButton = document.querySelector(".cedhi-mobile-back");

        if (!isMobile() || !shouldShowBackButton()) {
            if (existingButton) {
                existingButton.remove();
            }
            return;
        }

        if (existingButton) {
            applyButtonStyles(existingButton);
            return;
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-default btn-sm cedhi-mobile-back";
        button.textContent = "Volver";
        button.setAttribute("aria-label", "Volver a la vista anterior");
        applyButtonStyles(button);
        button.addEventListener("click", goBack);

        document.body.appendChild(button);
    }

    function scheduleMobileBackButton() {
        window.setTimeout(ensureBackButton, 100);
        window.setTimeout(ensureBackButton, 350);
        window.setTimeout(ensureBackButton, 900);
        if (window.cedhi_apply_role_theme) {
            window.setTimeout(window.cedhi_apply_role_theme, 100);
            window.setTimeout(window.cedhi_apply_role_theme, 350);
            window.setTimeout(window.cedhi_apply_role_theme, 900);
        }
        if (window.cedhi_hide_restricted_shortcuts) {
            window.setTimeout(window.cedhi_hide_restricted_shortcuts, 100);
            window.setTimeout(window.cedhi_hide_restricted_shortcuts, 350);
            window.setTimeout(window.cedhi_hide_restricted_shortcuts, 900);
        }
    }

    function hookHistoryMethod(methodName) {
        const originalMethod = window.history[methodName];
        if (!originalMethod || originalMethod.cedhiHooked) {
            return;
        }

        window.history[methodName] = function () {
            const result = originalMethod.apply(this, arguments);
            scheduleMobileBackButton();
            return result;
        };
        window.history[methodName].cedhiHooked = true;
    }

    window.cedhi_mobile_navigation.ensure = ensureBackButton;
    scheduleMobileBackButton();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", scheduleMobileBackButton);
    }

    window.addEventListener("load", scheduleMobileBackButton);
    window.addEventListener("hashchange", scheduleMobileBackButton);
    window.addEventListener("popstate", scheduleMobileBackButton);
    window.addEventListener("resize", scheduleMobileBackButton);
    window.addEventListener("focus", scheduleMobileBackButton);
    window.addEventListener("pageshow", scheduleMobileBackButton);
    document.addEventListener("visibilitychange", scheduleMobileBackButton);
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", scheduleMobileBackButton);
    }

    if (window.frappe && frappe.router && typeof frappe.router.on === "function") {
        frappe.router.on("change", scheduleMobileBackButton);
    }

    hookHistoryMethod("pushState");
    hookHistoryMethod("replaceState");

    if (!window.cedhi_mobile_navigation.observer && document.body) {
        window.cedhi_mobile_navigation.observer = new MutationObserver(scheduleMobileBackButton);
        window.cedhi_mobile_navigation.observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }

    if (!window.cedhi_mobile_navigation.interval) {
        window.cedhi_mobile_navigation.interval = window.setInterval(ensureBackButton, 800);
    }
})();

// Role themed accent coloring
function cedhi_apply_role_theme() {
    var roles = (window.frappe && frappe.user_roles) || [];

    // Mapa de rol → color de acento en sidebar
    var roleColors = {
        'Admin Cocina':                   '#2DAE6A',  // verde
        'Admin TI':                        '#00AECC',  // cian
        'Admin General':                   '#F5C300',  // amarillo
        'Revisor':                         '#1A2F6E',  // navy
        'Reportante':                      '#5A6A8E',  // gris
        'SuperAdministrador Inventario':   '#D9202A',  // rojo
    };

    var matchedRole = Object.keys(roleColors).find(function(r) {
        return roles.includes(r);
    });

    if (matchedRole) {
        var color = roleColors[matchedRole];
        // Pintar indicador activo del sidebar con el color del rol
        document.querySelectorAll('.sidebar-item.selected > .standard-sidebar-item')
            .forEach(function(el) {
                el.style.setProperty('border-left-color', color, 'important');
            });
    }
}

window.cedhi_apply_role_theme = cedhi_apply_role_theme;

if (window.frappe && typeof frappe.after_ajax === "function") {
    frappe.after_ajax(function() {
        cedhi_apply_role_theme();
    });
}

// Algunos shortcuts del workspace "Inventario CEDHI" solo funcionan para
// ciertos roles (el server-side ya los bloquea, ver data_import.py), pero
// Frappe no permite ocultar un shortcut individual por rol dentro de un mismo
// workspace (el campo "roles" del Workspace oculta el workspace ENTERO, no
// shortcuts sueltos). Los ocultamos via JS para que cada rol solo vea botones
// que realmente puede usar:
// - CARGAR CATALOGO INICIAL: solo SuperAdmin/System Manager.
// - PLANTILLA <modulo>: cada Admin de modulo solo ve la plantilla de SU
//   modulo (Admin TI -> PLANTILLA TI, etc.); SuperAdmin/System Manager ven
//   las 3.
function cedhi_hide_restricted_shortcuts() {
    var roles = (window.frappe && frappe.user_roles) || [];
    var fullAccess = ['SuperAdministrador Inventario', 'System Manager', 'Administrator'];
    var hasFullAccess = roles.some(function (r) { return fullAccess.includes(r); });

    var moduleTemplateByRole = {
        'Admin TI': 'PLANTILLA TI',
        'Admin Cocina': 'PLANTILLA GASTRONOM',
        'Admin General': 'PLANTILLA GENERAL',
    };
    var ownTemplateLabel = Object.keys(moduleTemplateByRole)
        .map(function (r) { return roles.includes(r) ? moduleTemplateByRole[r] : null; })
        .find(Boolean);

    document.querySelectorAll('.shortcut-widget-box').forEach(function (box) {
        var label = box.textContent || '';
        var widget = box.closest('.widget') || box;
        var hide = false;

        if (!hasFullAccess && label.indexOf('CARGAR CAT') !== -1) {
            hide = true;
        }
        if (!hasFullAccess && label.indexOf('PLANTILLA') !== -1) {
            // Si el rol tiene una plantilla propia, oculta las demas; si no
            // tiene modulo asignado (Revisor/Reportante), oculta todas.
            hide = !ownTemplateLabel || label.indexOf(ownTemplateLabel) === -1;
        }

        if (hide) {
            widget.style.setProperty('display', 'none', 'important');
        }
    });
}

window.cedhi_hide_restricted_shortcuts = cedhi_hide_restricted_shortcuts;

if (window.frappe && typeof frappe.after_ajax === "function") {
    frappe.after_ajax(cedhi_hide_restricted_shortcuts);
}

// Si un usuario cambia de sesion (logout/login) mientras el navegador todavia
// tiene cargada una ruta a la que su rol no tiene acceso (ej. la pagina de
// Usuarios abierta por el Superadmin), Frappe muestra "No tiene permiso para
// ver esta pagina" en vez de llevarlo a su panel. Sobrescribimos el manejador
// global para que en su lugar redirija al home configurado por rol
// (role_home_page en hooks.py).
if (window.frappe) {
    frappe.show_not_permitted = function (page_name) {
        const fallback_route = "app/inventario-cedhi";
        frappe.set_route(fallback_route);
    };
}

// El hash de la URL (#/app/user, etc.) vive en el navegador, no en la sesion.
// Si el SuperAdmin cierra sesion estando en /app/user y otro usuario inicia
// sesion despues, Frappe carga esa misma ruta para el usuario nuevo (el hash
// no se limpia solo). Si esa ruta SI es accesible para el nuevo usuario -aunque
// sea de forma filtrada, como ver su propio registro en Usuarios- no hay
// PermissionError que interceptar, y el usuario nuevo termina viendo la
// pantalla que dejo el anterior en vez de su panel de inventario.
// Solucion: recordamos en localStorage que usuario dejo la ultima ruta; si al
// cargar la app el usuario actual es distinto, forzamos ir al home del rol.
(function enforce_home_route_on_user_change() {
    const STORAGE_KEY = "cedhi_last_session_user";

    function current_user() {
        return (window.frappe && frappe.session && frappe.session.user) || null;
    }

    function go_home_and_track() {
        const user = current_user();
        if (!user || user === "Guest") return;

        const last_user = window.localStorage.getItem(STORAGE_KEY);
        if (last_user && last_user !== user) {
            frappe.set_route("app/inventario-cedhi");
        }
        window.localStorage.setItem(STORAGE_KEY, user);
    }

    if (window.frappe && typeof frappe.after_ajax === "function") {
        frappe.after_ajax(go_home_and_track);
    }
})();

