app_name = "inventario_cedhi"
app_title = "Sistema de Gestión de Inventario CEDHI Nueva Arequipa"
app_publisher = "CEDHI Nueva Arequipa"
app_description = "Sistema de Inventario que permitira, administrar de manera correcta los elementos u objetos con los que cuenta."
app_email = "soporte@cedhi.local"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "inventario_cedhi",
# 		"logo": "/assets/inventario_cedhi/logo.png",
# 		"title": "Sistema de Gestión de Inventario CEDHI Nueva Arequipa",
# 		"route": "/inventario_cedhi",
# 		"has_permission": "inventario_cedhi.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/inventario_cedhi/css/inventario_cedhi_mobile.css?v=20260629_2"
app_include_js = "/assets/inventario_cedhi/js/mobile_navigation.js?v=20260621_4"

# include js, css files in header of web template
# web_include_css = "/assets/inventario_cedhi/css/inventario_cedhi.css"
# web_include_js = "/assets/inventario_cedhi/js/inventario_cedhi.js"

# Fondo rotativo de ambientes CEDHI en la pantalla de login
web_include_css = "/assets/inventario_cedhi/css/login_cedhi.css?v=20260615_1"
web_include_js = "/assets/inventario_cedhi/js/login_cedhi.js?v=20260615_1"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "inventario_cedhi/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "inventario_cedhi/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "login"

# Tras el login, cada rol del CEDHI aterriza en el workspace de inventario en vez
# del Desk generico de ERPNext (que mostraria modulos ajenos como Accounting/CRM).
# El contenido visible dentro del workspace ya esta filtrado por los permisos de rol.
role_home_page = {
	"SuperAdministrador Inventario": "app/inventario-cedhi",
	"Admin TI": "app/inventario-cedhi",
	"Admin Cocina": "app/inventario-cedhi",
	"Revisor": "app/inventario-cedhi",
	"Reportante": "app/inventario-cedhi",
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "inventario_cedhi.utils.jinja_methods",
# 	"filters": "inventario_cedhi.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "inventario_cedhi.install.before_install"
after_install = "inventario_cedhi.install.after_install"

# Re-asegura configuracion idempotente (campos, permisos, workspaces) tras cada migrate
after_migrate = "inventario_cedhi.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "inventario_cedhi.uninstall.before_uninstall"
# after_uninstall = "inventario_cedhi.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "inventario_cedhi.utils.before_app_install"
# after_app_install = "inventario_cedhi.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "inventario_cedhi.utils.before_app_uninstall"
# after_app_uninstall = "inventario_cedhi.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "inventario_cedhi.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Articulo de Inventario": "inventario_cedhi.permissions.article_query_conditions",
	"Alerta de Inventario": "inventario_cedhi.permissions.alert_query_conditions",
	"Movimiento de Inventario": "inventario_cedhi.permissions.movement_query_conditions",
	"User": "inventario_cedhi.permissions.user_query_conditions",
}

has_permission = {
	"Articulo de Inventario": "inventario_cedhi.permissions.article_has_permission",
	"Alerta de Inventario": "inventario_cedhi.permissions.alert_has_permission",
	"Movimiento de Inventario": "inventario_cedhi.permissions.movement_has_permission",
	"Ubicacion": "inventario_cedhi.permissions.ubicacion_has_permission",
	"User": "inventario_cedhi.permissions.user_has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
	"Articulo de Inventario": {
		"validate": [
			"inventario_cedhi.inventory_logic.set_internal_code",
			"inventario_cedhi.inventory_logic.require_estado_change_reason",
		],
	},
	"Alerta de Inventario": {
		"before_insert": "inventario_cedhi.alerts.set_alert_defaults",
		"validate": "inventario_cedhi.alerts.set_alert_defaults",
	},
	"Movimiento de Inventario": {
		"validate": "inventario_cedhi.inventory_logic.validate_stock_on_movement",
		"on_submit": "inventario_cedhi.inventory_logic.update_stock_on_movement",
		"on_cancel": "inventario_cedhi.inventory_logic.reverse_stock_on_cancel",
	},
	"User": {
		"before_insert": "inventario_cedhi.inventory_logic.enforce_user_language",
		"validate": [
			"inventario_cedhi.inventory_logic.enforce_user_language",
			"inventario_cedhi.inventory_logic.enforce_default_workspace",
		],
	},
	"Data Import": {
		# Admin TI/Cocina/General pueden usar Data Import nativo para cargas
		# masivas recurrentes de SU modulo (ej. "llegaron 40 CPUs nuevas"), pero
		# sin esto podrian apuntarlo a cualquier doctype o modulo ajeno.
		"validate": "inventario_cedhi.permissions.validate_data_import_module_scope",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"inventario_cedhi.tasks.all"
# 	],
# 	"daily": [
# 		"inventario_cedhi.tasks.daily"
# 	],
# 	"hourly": [
# 		"inventario_cedhi.tasks.hourly"
# 	],
# 	"weekly": [
# 		"inventario_cedhi.tasks.weekly"
# 	],
# 	"monthly": [
# 		"inventario_cedhi.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "inventario_cedhi.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "inventario_cedhi.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "inventario_cedhi.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
before_request = ["inventario_cedhi.inventory_logic.force_spanish_language"]
# after_request = ["inventario_cedhi.utils.after_request"]

# Job Events
# ----------
before_job = ["inventario_cedhi.inventory_logic.force_spanish_language"]
# after_job = ["inventario_cedhi.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"inventario_cedhi.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Fixtures
# ------------------
# Respaldo versionado de configuracion que no vive en .json: roles del CEDHI y
# campos custom del doctype User (usados por el rol Reportante). Tambien viajan
# via install.py/after_migrate, pero declararlos como fixtures garantiza que
# `bench export-fixtures` los capture y se restauren en cualquier despliegue.
fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"SuperAdministrador Inventario",
					"Admin TI",
					"Admin Cocina",
					"Revisor",
					"Reportante",
				],
			]
		],
	},
	{
		"dt": "Custom Field",
		"filters": [["fieldname", "in", ["inventario_modulo_asignado", "inventario_ubicacion_asignada"]]],
	},
]
