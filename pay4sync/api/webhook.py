"""
Receives pay4done's payout status webhook. Log only.

pay4done does not sign its webhooks, so the shared secret travels in the URL
that pay4done team sets in each merchant's User Settings.webhook:

  https://pay4push.in/api/method/pay4sync.api.webhook.receive?key=<pay4sync_webhook_key>&user=<merchant email>

Answers 200 to a valid call so pay4done does not retry it, 401 otherwise.
"""

import hmac

import frappe

from pay4sync.utils.logger import log_webhook


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive(**kwargs):
	args = frappe.request.args
	expected = frappe.conf.get("pay4sync_webhook_key") or ""
	key_valid = bool(expected) and hmac.compare_digest(expected, args.get("key") or "")
	user = (args.get("user") or "").strip() or None

	if not key_valid:
		# Keep a trace of the attempt, but not the (untrusted) body.
		log_webhook(user, {}, False, frappe.local.request_ip)
		frappe.local.response.http_status_code = 401
		return {"success": False}

	payload = frappe.request.get_json(silent=True)
	log_webhook(user, payload if isinstance(payload, dict) else {}, True, frappe.local.request_ip)
	return {"success": True}
