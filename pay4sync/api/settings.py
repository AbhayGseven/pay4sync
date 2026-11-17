"""
Settings APIs for the RAMASETU Settings page: the same fields as the merchant's
User Settings record, which lives in pay4done (see utils/client.py).

API Token and Webhook Secret:
  * are never typed by the merchant: only `regenerate` can replace them with a new
    random value, so they are always strong;
  * are never sent to the browser again after they are created. The page only gets
    `api_token_set` / `webhook_secret_set` (True/False). The new value is returned
    once, by `regenerate`, so the page can show it a single time in a popup.
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


def _without_secrets(response):
	"""Replace each secret with a <field>_set flag before anything reaches the browser."""
	data = dict((response or {}).get("data") or {})
	for field in SECRET_FIELDS:
		data[f"{field}_set"] = bool(data.pop(field, None))
	data.pop("api_token_hash", None)
	return {**response, "data": data}


@frappe.whitelist()
def get_settings():
	require_merchant()
	return _without_secrets(client.get("settings.get_settings"))


@frappe.whitelist(methods=["POST"])
def update_settings(**kwargs):
	require_merchant()
	body = {f: kwargs.get(f) for f in EDITABLE_FIELDS if f in kwargs}
	return _without_secrets(client.post("settings.update_settings", body))


@frappe.whitelist(methods=["POST"])
def regenerate(field=None):
	"""Replace the API Token or the Webhook Secret with a new random value.

	The old value stops working at once. The new value is returned only in this
	response (`value`), so the page can show it once; it is never sent again.
	"""
	require_merchant()
	if field not in SECRET_FIELDS:
		frappe.throw("Unknown field")
	value = secrets.token_urlsafe(SECRET_BYTES)
	response = client.post("settings.update_settings", {field: value})
	return {**_without_secrets(response), "field": field, "value": value}
