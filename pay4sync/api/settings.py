"""
Settings APIs for the RAMASETU Settings page: the same fields as the merchant's
User Settings record, which lives in pay4done (see utils/client.py).

API Token (token 1) is shown to the merchant as it is and can be edited and saved
(its hash is set by pay4done on save). "API Token 2" is its hash: the browser only
learns whether it exists (`api_token_hash_set`), never the hash.

Webhook Secret is never sent to the browser after it is created: the page gets
`webhook_secret_set` only, and the new value once from `regenerate`.

The Webhook Secret is never typed: only `regenerate` replaces it. The API Token can be
typed and saved, or replaced by `regenerate`.
"""

import secrets

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant

# Fields the Save button may change.
EDITABLE_FIELDS = ["webhook", "enable_webhook", "api_token", "enable_api", "ip_address", "enable_ip_address"]
# Secrets that only `regenerate` may change.
SECRET_FIELDS = ("api_token", "webhook_secret")
SECRET_BYTES = 32  # -> 43-character URL-safe value


def _without_secrets(response):
	"""Keep the API Token (shown read-only); replace the Webhook Secret with a flag; never send the hash."""
	data = dict((response or {}).get("data") or {})
	data["api_token_set"] = bool(data.get("api_token"))
	data["webhook_secret_set"] = bool(data.pop("webhook_secret", None))
	data["api_token_hash_set"] = bool(data.get("api_token_hash_set"))
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
