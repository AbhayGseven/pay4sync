"""
Webhook relay: pay4done hands RAMASETU a payout status webhook, RAMASETU sends
it on to the merchant and logs it.

Used for users with "Send Webhook via RAMASETU" ticked in pay4done's User
Settings. pay4done calls:

  POST /api/method/pay4sync.api.webhook.receive
  X-RS-Webhook-Key: <pay4sync_webhook_key from this site's site_config>
  {"url": <merchant's Webhook URL>, "user": <merchant email>, "payload": {...}}

RAMASETU POSTs `payload` unchanged to `url`, writes a Pay4sync Webhook Log row
(success or failure), and answers with the merchant's result:

  {"delivered": true|false, "status_code": <merchant's HTTP status>, "error": ...}

HTTP 200 when the merchant accepted it, 502 when not - so pay4done's own retry
chain (Payout Webhook Logs) retries through RAMASETU again.
"""

import hmac
import time
from urllib.parse import urlparse

import frappe
import requests

from pay4sync.utils.logger import log_webhook

MERCHANT_TIMEOUT = 10  # seconds; pay4done waits 20s for this whole call
USER_AGENT = "RAMASETU-Webhook/1.0"


def _answer(status, delivered, status_code=None, error=None):
	frappe.local.response.http_status_code = status
	return {"delivered": delivered, "status_code": status_code, "error": error}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive(**kwargs):
	remote_ip = frappe.local.request_ip
	expected = frappe.conf.get("pay4sync_webhook_key") or ""
	given = frappe.request.headers.get("X-RS-Webhook-Key") or ""
	if not (expected and hmac.compare_digest(expected, given)):
		# Keep a trace of the attempt, but not the (untrusted) body.
		log_webhook(None, {}, False, remote_ip)
		frappe.local.response.http_status_code = 401
		return {"success": False}

	body = frappe.request.get_json(silent=True)
	body = body if isinstance(body, dict) else {}
	url = str(body.get("url") or "").strip()
	user = str(body.get("user") or "").strip() or None
	payload = body.get("payload")

	parsed = urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.netloc or not isinstance(payload, dict):
		error = "Invalid relay request: url must be http(s) and payload a JSON object"
		log_webhook(user, payload if isinstance(payload, dict) else {}, True, remote_ip,
			target_url=url, delivered=False, error=error)
		return _answer(400, False, error=error)

	start = time.monotonic()
	status_code, error = None, None
	try:
		response = requests.post(url, json=payload, timeout=MERCHANT_TIMEOUT,
			headers={"User-Agent": USER_AGENT})
		status_code = response.status_code
		if not response.ok:
			error = f"Merchant answered HTTP {status_code}"
	except requests.RequestException as e:
		error = f"Could not reach merchant: {e.__class__.__name__}: {e}"
	duration_ms = int((time.monotonic() - start) * 1000)

	delivered = error is None
	log_webhook(user, payload, True, remote_ip, target_url=url, delivered=delivered,
		response_code=status_code, error=error, duration_ms=duration_ms)
	return _answer(200 if delivered else 502, delivered, status_code, error)
