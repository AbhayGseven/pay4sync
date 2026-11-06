"""Shared get_context helper for the pay4push merchant pages in www/."""

import frappe
from frappe.sessions import get_csrf_token

from pay4sync.utils.permissions import MERCHANT_ROLE

# Same menu as pay4done's portal, minus settings / API docs / reports.
NAV = [
	{"key": "new-payout", "label": "Simple Payout", "route": "/payout/new"},
	{"key": "payouts", "label": "My Payouts", "route": "/payout"},
	{"key": "wallet", "label": "My Wallet", "route": "/wallet"},
	{"key": "recharge", "label": "Recharge History", "route": "/recharge-history"},
	{"key": "statement", "label": "Statement", "route": "/statement"},
	{"key": "bulk", "label": "Payout Bulk Import", "route": "/payout-bulk-upload"},
]

ASSET_VERSION = "2"


def merchant_page(context, title, active, breadcrumbs=None):
	"""Guests go to /login (and come back); logged-in non-merchants get a 403."""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to=/{frappe.local.path}"
		raise frappe.Redirect

	if MERCHANT_ROLE not in frappe.get_roles():
		frappe.throw("This page is only for merchants.", frappe.PermissionError)

	# Frappe only *injects* the session's CSRF token into web pages; it never creates
	# one for a Website User (that happens on /app). Without this the page gets
	# frappe.csrf_token = "None" and Frappe skips CSRF checks on our POST APIs.
	get_csrf_token()

	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	context.no_cache = 1
	context.title = title
	context.active = active
	context.p4s_breadcrumbs = breadcrumbs or []
	context.p4s_nav = NAV
	context.p4s_user = frappe.session.user
	context.p4s_initial = full_name[:1].upper()
	context.p4s_version = ASSET_VERSION
	return context


def route_name():
	"""The <name> part of /payout/<name> style routes (see website_route_rules in hooks)."""
	return (frappe.form_dict.get("name") or "").strip()
