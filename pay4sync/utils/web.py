"""Shared get_context helper for the merchant and manager pages in www/."""

import frappe
from frappe.sessions import get_csrf_token

from pay4sync.utils.permissions import MANAGER_ROLE, MERCHANT_ROLE

# Same menu (and order) as pay4done's portal, minus API docs / reports / my account.
NAV = [
	{"key": "new-payout", "label": "Simple Payout", "route": "/payout/new"},
	{"key": "payouts", "label": "My Payouts", "route": "/payout"},
	{"key": "wallet", "label": "My Wallet", "route": "/wallet"},
	{"key": "recharge", "label": "Recharge History", "route": "/recharge-history"},
	{"key": "statement", "label": "Statement", "route": "/statement"},
	{"key": "settings", "label": "Settings", "route": "/settings"},
	{"key": "bulk", "label": "Payout Bulk Import", "route": "/payout-bulk-upload"},
]

# Read-only views of all RAMASETU merchants, shown under a "Manager" heading.
MANAGER_NAV = [
	{"key": "m-payouts", "label": "All Payouts", "route": "/manager/payouts"},
	{"key": "m-wallet", "label": "Wallet Transactions", "route": "/manager/wallet-transactions"},
	{"key": "m-recharges", "label": "Recharges", "route": "/manager/recharges"},
	{"key": "m-bulk", "label": "Bulk Imports", "route": "/manager/bulk-imports"},
]

ASSET_VERSION = "9"


def merchant_page(context, title, active, breadcrumbs=None, role=MERCHANT_ROLE):
	"""Guests go to /login (and come back); users without `role` get a 403.

	role: MERCHANT_ROLE for merchant pages, MANAGER_ROLE for manager pages.
	The sidebar shows the merchant section and/or the manager section, by the user's roles.
	"""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to=/{frappe.local.path}"
		raise frappe.Redirect

	roles = frappe.get_roles()
	if role not in roles:
		frappe.throw("You are not allowed to open this page.", frappe.PermissionError)

	# Frappe only *injects* the session's CSRF token into web pages; it never creates
	# one for a Website User (that happens on /app). Without this the page gets
	# frappe.csrf_token = "None" and Frappe skips CSRF checks on our POST APIs.
	get_csrf_token()

	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	context.no_cache = 1
	context.title = title
	context.active = active
	context.p4s_breadcrumbs = breadcrumbs or []
	context.p4s_nav = NAV if MERCHANT_ROLE in roles else []
	context.p4s_manager_nav = MANAGER_NAV if MANAGER_ROLE in roles else []
	context.p4s_user = frappe.session.user
	context.p4s_initial = full_name[:1].upper()
	context.p4s_version = ASSET_VERSION
	return context


def route_name():
	"""The <name> part of /payout/<name> style routes (see website_route_rules in hooks)."""
	return (frappe.form_dict.get("name") or "").strip()


def manager_page(context, title, active, breadcrumbs=None):
	return merchant_page(context, title, active, breadcrumbs, role=MANAGER_ROLE)
