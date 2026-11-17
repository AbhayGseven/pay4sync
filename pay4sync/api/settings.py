"""
Settings APIs for the RAMASETU Settings page: the same fields as the merchant's
User Settings record, which lives in pay4done (see utils/client.py).

API Token and Webhook Secret are never typed by the merchant: they can only be
replaced with a new random value by `regenerate`, so they are always strong.
`update_settings` ignores them.
"""

import secrets

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant

# Fields the Save button may change.
EDITABLE_FIELDS = ["webhook", "enable_webhook", "enable_api", "ip_address", "enable_ip_address"]
# Secrets that only `regenerate` may change.
SECRET_FIELDS = ("api_token", "webhook_secret")
SECRET_BYTES = 32  # -> 43-character URL-safe value


@frappe.whitelist()
def get_settings():
	require_merchant()
	return client.get("settings.get_settings")


@frappe.whitelist(methods=["POST"])
def update_settings(**kwargs):
	require_merchant()
	body = {f: kwargs.get(f) for f in EDITABLE_FIELDS if f in kwargs}
	return client.post("settings.update_settings", body)


@frappe.whitelist(methods=["POST"])
def regenerate(field=None):
	"""Replace the API Token or the Webhook Secret with a new random value.
	The old value stops working at once."""
	require_merchant()
	if field not in SECRET_FIELDS:
		frappe.throw("Unknown field")
	return client.post("settings.update_settings", {field: secrets.token_urlsafe(SECRET_BYTES)})
