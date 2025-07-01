import frappe


@frappe.whitelist()
def has_app_permission():
	"""Check if user has permission to access WeBiz app"""
	# Allow all users with desk access for now
	# You can customize this based on your requirements
	return True
