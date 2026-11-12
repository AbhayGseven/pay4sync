"""pay4push's /login — overrides Frappe's login page (pay4sync is installed after frappe).

Merchants log in with their pay4done email + password; the pay4push team
(Administrator / System Users) with their pay4push password. See api/auth.py.
"""

import frappe

from pay4sync.utils.permissions import MERCHANT_ROLE
from pay4sync.utils.web import ASSET_VERSION

no_cache = 1


def _home_for(user):
	return "/payout" if MERCHANT_ROLE in frappe.get_roles(user) else "/app"


def get_context(context):
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = _home_for(frappe.session.user)
		raise frappe.Redirect

	context.no_cache = 1
	context.title = "Login"
	context.p4s_version = ASSET_VERSION
	return context
