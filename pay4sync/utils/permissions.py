import frappe

MERCHANT_ROLE = "Pay4sync Merchant"
MANAGER_ROLE = "Ramasetu Manager"


def require_merchant():
	"""Only logged-in merchants may call the pay4sync APIs."""
	if frappe.session.user in ("Guest", "Administrator"):
		frappe.throw("Please log in", frappe.PermissionError)
	frappe.only_for(MERCHANT_ROLE)


def require_manager():
	"""Only logged-in RAMASETU managers may call the manager APIs (read-only)."""
	if frappe.session.user in ("Guest", "Administrator"):
		frappe.throw("Please log in", frappe.PermissionError)
	frappe.only_for(MANAGER_ROLE)


def send_file(filename, content):
	"""Make the current request return `content` (bytes or str) as a file download."""
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
