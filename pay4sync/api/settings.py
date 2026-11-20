"""
Settings APIs for the RAMASETU Settings page: the same fields as the merchant's
User Settings record, which lives in pay4done (see utils/client.py).

API Token (token 1): shown and editable. Saving a changed token removes the hash in
  pay4done, so the typed token is the one that works.
API Token 2 (hash): never sent to the browser, only `api_token_hash_set`. "Generate /
  Regenerate Token" makes a new token in pay4done, which saves only its hash (API Token is
  left as it is and stops working) and returns the token once, for the popup.
Webhook Secret: never sent to the browser after it is created (`webhook_secret_set` only);
  only `regenerate` replaces it, and returns it once.
Encryption Keys: "Generate Encryption Keys" makes a merchant key pair in pay4done. The public
  key is saved there; the private key comes back once (with the server public key) for the
  popup and is never stored. Enable Encryption itself is switched on by support.
"""

import secrets

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant

# Fields the Save button may change.
EDITABLE_FIELDS = ["webhook", "enable_webhook", "api_token", "enable_api", "ip_address", "enable_ip_address"]
# Secrets that only `regenerate` may change.
SECRET_FIELDS = ("api_token", "webhook_secret", "encryption_keys")
SECRET_BYTES = 32  # -> 43-character URL-safe value


def _without_secrets(response):
	"""Keep the API Token (shown, editable); replace the Webhook Secret with a flag; never send the hash."""
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
	if field == "api_token":
		# pay4done makes the token and saves only its hash; API Token (token 1) is not changed.
		response = client.post("settings.regenerate_token", {})
		return {**_without_secrets(response), "field": field, "value": response["value"]}
	if field == "encryption_keys":
		response = client.post("settings.regenerate_encryption_keys", {})
		return {**_without_secrets(response), "field": field, "value": response["value"],
			"server_public_key": response["server_public_key"]}
	value = secrets.token_urlsafe(SECRET_BYTES)
	response = client.post("settings.update_settings", {field: value})
	return {**_without_secrets(response), "field": field, "value": value}
