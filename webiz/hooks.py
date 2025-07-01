app_name = "webiz"
app_title = "WeBiz"
app_publisher = "JYT AI"
app_description = "WeBiz"
app_email = "ktk@jyt.ai"
app_license = "unlicense"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "webiz",
		"title": "WeBiz FM",
		"route": "/app/webiz",
		"has_permission": "webiz.api.permission.has_app_permission"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/webiz/css/webiz.css"
# app_include_js = "/assets/webiz/js/webiz.js"

# include js, css files in header of web template
# web_include_css = "/assets/webiz/css/webiz.css"
# web_include_js = "/assets/webiz/js/webiz.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "webiz/public/scss/website"

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
# app_include_icons = "webiz/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "webiz.utils.jinja_methods",
# 	"filters": "webiz.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "webiz.install.before_install"
after_install = "webiz.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "webiz.uninstall.before_uninstall"
# after_uninstall = "webiz.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "webiz.utils.before_app_install"
# after_app_install = "webiz.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "webiz.utils.before_app_uninstall"
# after_app_uninstall = "webiz.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "webiz.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Customer": {
		"validate": "webiz.fm_customer_management.utils.validate_fm_customer"
	},
	"Quotation": {
		"validate": "webiz.fm_sales_management.utils.validate_fm_quotation"
	},
	"Contract": {
		"validate": "webiz.fm_sales_management.utils.validate_fm_contract"
	},
	"Project": {
		"validate": "webiz.fm_project_management.utils.validate_fm_project"
	},
	"Issue": {
		"validate": "webiz.fm_service_management.utils.validate_fm_issue"
	},
	"Sales Invoice": {
		"validate": "webiz.fm_billing_management.utils.validate_fm_invoice"
	},
	"Warehouse": {
		"validate": "webiz.webiz.custom.warehouse.validate_warehouse_site"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"webiz.tasks.all"
# 	],
# 	"daily": [
# 		"webiz.tasks.daily"
# 	],
# 	"hourly": [
# 		"webiz.tasks.hourly"
# 	],
# 	"weekly": [
# 		"webiz.tasks.weekly"
# 	],
# 	"monthly": [
# 		"webiz.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "webiz.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "webiz.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "webiz.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["webiz.utils.before_request"]
# after_request = ["webiz.utils.after_request"]

# Job Events
# ----------
# before_job = ["webiz.utils.before_job"]
# after_job = ["webiz.utils.after_job"]

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
# 	"webiz.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

