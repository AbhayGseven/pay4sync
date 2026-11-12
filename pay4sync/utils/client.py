"""
The one place pay4sync talks to pay4done (pay4done.pay4done.merchant_api.*).

Auth is server-to-server: the shared server key from site_config plus
X-P4D-User = the logged-in pay4push user (same email exists on pay4done).
The user ALWAYS comes from frappe.session.user, never from request input.

site_config:
  pay4done_url        — base URL, e.g. https://pay4done.com (dev: http://127.0.0.1:8000)
  pay4done_host       — optional Host header, for reaching a named site on a shared bench
  pay4done_server_key — must equal pay4done's pay4push_server_key
"""

import time

import frappe
import requests

from pay4sync.utils.logger import log_api_call

API_PREFIX = "/api/method/pay4done.pay4done.merchant_api."
DEFAULT_TIMEOUT = 30

# Messages a merchant sees. pay4done's own text is shown only for 400/404/409,
# which are about the merchant's input; anything else could leak internals.
GENERIC_ERRORS = {
	401: "Your account is not enabled for payouts. Please contact support.",
	403: "Your account is not enabled for payouts. Please contact support.",
	429: "Too many requests. Please wait a minute and try again.",
}
UNAVAILABLE = "Service is temporarily unavailable. Please try again in a few minutes."
PROCESSING_FAILED = ("Something went wrong while processing your request. "
	"Please check My Payouts before trying again, or contact support.")
SHOW_REMOTE_MESSAGE = {400, 404, 409}


class Pay4doneTimeout(Exception):
	"""pay4done did not answer in time; the request may or may not have been applied."""


def _config():
	conf = frappe.conf
	base = (conf.get("pay4done_url") or "").rstrip("/")
	key = conf.get("pay4done_server_key")
	if not base or not key:
		frappe.log_error("pay4done_url / pay4done_server_key missing in site_config", "Pay4sync Config")
		frappe.throw(UNAVAILABLE)
	return base, key, conf.get("pay4done_host")


def _reference(data):
	if not isinstance(data, dict):
		return None
	for key in ("payout", "recharge", "name"):
		if data.get(key):
			return str(data[key])
	inner = data.get("data")
	if isinstance(inner, dict) and inner.get("name"):
		return str(inner["name"])
	return None


def _logout_disabled_merchant():
	"""pay4done refused this merchant (user disabled or enable_api off): end the pay4push session too."""
	try:
		if frappe.session.user not in ("Guest", "Administrator") and getattr(frappe.local, "login_manager", None):
			frappe.local.login_manager.logout()
			frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Pay4sync logout of disabled merchant failed")


def call(http_method, endpoint, params=None, body=None, timeout=DEFAULT_TIMEOUT, reference=None,
		as_user=None, raise_on_error=True):
	"""Call pay4done.pay4done.merchant_api.<endpoint> as the logged-in merchant.

	Returns pay4done's JSON on success. Raises frappe.ValidationError with a
	merchant-safe message on failure, or Pay4doneTimeout on a timeout.

	as_user: only for the login check, where nobody is logged in yet.
	raise_on_error=False: return (status_code, data) instead of raising on a pay4done error.
	"""
	user = as_user or frappe.session.user
	if user in ("Guest", "Administrator"):
		frappe.throw("Please log in", frappe.PermissionError)

	base, key, host = _config()
	headers = {"X-P4D-Server-Key": key, "X-P4D-User": user, "Accept": "application/json"}
	if host:
		headers["Host"] = host

	started = time.monotonic()
	status_code, data, error = 0, None, None

	def elapsed():
		return int((time.monotonic() - started) * 1000)

	try:
		response = requests.request(
			http_method, base + API_PREFIX + endpoint, headers=headers,
			params=params if http_method == "GET" else None,
			json=body if http_method != "GET" else None,
			timeout=timeout,
		)
		status_code = response.status_code
		try:
			data = response.json().get("message")
		except ValueError:
			data = None
	except requests.Timeout:
		log_api_call(endpoint, http_method, 0, False, elapsed(), reference, "Timeout", user=user)
		raise Pay4doneTimeout(endpoint)
	except requests.RequestException as e:
		log_api_call(endpoint, http_method, 0, False, elapsed(), reference, f"Connection error: {e}", user=user)
		frappe.throw(UNAVAILABLE)

	ok = status_code == 200 and isinstance(data, dict) and data.get("success")
	if not ok:
		error = (data.get("error") if isinstance(data, dict) else None) or f"HTTP {status_code}"

	log_api_call(endpoint, http_method, status_code, ok, elapsed(), reference or _reference(data), error, user=user)

	if not raise_on_error:
		return status_code, data
	if ok:
		return data
	if status_code == 401 and not as_user:
		_logout_disabled_merchant()
		frappe.throw("Your account is not enabled. You have been logged out. Please contact support.")
	if status_code in SHOW_REMOTE_MESSAGE:
		frappe.throw(error)
	if status_code == 500:
		# pay4done answered but failed internally (its Error Log has the traceback).
		frappe.throw(PROCESSING_FAILED)
	frappe.throw(GENERIC_ERRORS.get(status_code, UNAVAILABLE))


def get(endpoint, params=None, **kwargs):
	return call("GET", endpoint, params=params, **kwargs)


def post(endpoint, body=None, **kwargs):
	return call("POST", endpoint, body=body, **kwargs)
