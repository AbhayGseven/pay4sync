"""
Token API for merchants' own servers (no login, no cookies): create payout,
wallet balance, payout status. Same rules and responses as pay4done's v1 API.

  Headers:  X-RS-User   merchant email
            X-RS-Token  API Token from the merchant's Settings (stored in pay4done
                        User Settings.api_token; RAMASETU keeps no copy)

RAMASETU checks nothing itself except that the headers are present: it forwards
the call to pay4done (merchant_api.token_api), which checks the token, Enable
API, the IP allow-list, RAMASETU access and the rate limits, exactly like
pay4done's own API. The merchant's IP is passed along so the allow-list works.

Public URLs (hooks.override_whitelisted_methods), so no app name shows:
  POST /api/method/ramasetu.payout.create_payout
  GET  /api/method/ramasetu.wallet.get_balance
  GET  /api/method/ramasetu.payout.get_payout_status?payout_name=...
"""

import frappe

from pay4sync.utils import client
from pay4sync.utils.client import Pay4doneTimeout


def _error(status, message, extra=None):
	frappe.local.response["http_status_code"] = status
	response = {"success": False, "error": message}
	if extra:
		response.update(extra)
	return response


def _client_ip():
	"""The caller's IP, read the same way pay4done's v1 API reads it: X-Real-IP, else the
	rightmost X-Forwarded-For entry (added by the proxy, not the client), else the socket."""
	headers = frappe.local.request.headers
	real_ip = headers.get("X-Real-IP")
	if real_ip:
		return real_ip.strip()
	forwarded = headers.get("X-Forwarded-For")
	if forwarded:
		return forwarded.split(",")[-1].strip()
	return frappe.local.request.remote_addr or ""


def _forward(allowed_method, endpoint, timeout=client.DEFAULT_TIMEOUT):
	if frappe.local.request.method != allowed_method:
		return _error(405, "Method Not Allowed")

	headers = frappe.local.request.headers
	user = (headers.get("X-RS-User") or "").strip().lower()
	token = headers.get("X-RS-Token") or ""
	if not user:
		return _error(400, "Missing required header: X-RS-User")
	if not token:
		return _error(400, "Missing required header: X-RS-Token")
	if user in ("guest", "administrator"):
		return _error(401, "Invalid credentials")

	payload = {k: v for k, v in frappe.local.form_dict.items() if k != "cmd"}
	try:
		status, data = client.call(
			allowed_method, "token_api." + endpoint,
			params=payload if allowed_method == "GET" else None,
			body=payload if allowed_method != "GET" else None,
			timeout=timeout, as_user=user, raise_on_error=False,
			extra_headers={"X-P4D-Api-Token": token, "X-P4D-Client-IP": _client_ip()},
		)
	except Pay4doneTimeout:
		return _error(504, "The request timed out. Check the payout status before retrying, "
			"and send the same idempotency_key when you retry.")
	except frappe.ValidationError:
		frappe.local.message_log = []
		return _error(503, "Service is temporarily unavailable. Please try again in a few minutes.")

	if not isinstance(data, dict) or not status:
		return _error(503, "Service is temporarily unavailable. Please try again in a few minutes.")
	frappe.local.response["http_status_code"] = status
	return data


@frappe.whitelist(allow_guest=True)
def create_payout(**kwargs):
	return _forward("POST", "create_payout", timeout=60)


@frappe.whitelist(allow_guest=True)
def get_balance(**kwargs):
	return _forward("GET", "get_balance")


@frappe.whitelist(allow_guest=True)
def get_payout_status(**kwargs):
	return _forward("GET", "get_payout_status")
