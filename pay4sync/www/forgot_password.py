"""/forgot-password — ask for a reset link (see api/auth.send_reset_link)."""

import frappe

from pay4sync.utils.web import ASSET_VERSION

no_cache = 1


def get_context(context):
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = "/login"
		raise frappe.Redirect
	context.no_cache = 1
	context.title = "Forgot Password"
	context.p4s_version = ASSET_VERSION
	return context
