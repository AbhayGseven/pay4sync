"""
Pay4sync API Log / Pay4sync Webhook Log writers.

Logs are committed straight away: pay4sync stores no business data of its
own, so the only writes in a request are logs, and a log must survive the
rollback that follows a frappe.throw (that is exactly when it is needed).

Never pass tokens, keys or signatures in here.
"""

import json

import frappe

LOG_RETENTION_DAYS = 90
LOG_DOCTYPES = ("Pay4sync API Log", "Pay4sync Webhook Log")
MAX_ERROR_LENGTH = 1000


def _insert(doc):
	try:
		frappe.get_doc(doc).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Logging must never break the request it is logging.
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), f"Failed to write {doc['doctype']}")


def log_api_call(endpoint, http_method, status_code, success, duration_ms, reference=None, error=None,
		user=None):
	"""`user` is the merchant email the call was made for (plain text, not a link:
	merchants are managed on pay4done and may not exist, or no longer exist, here)."""
	user = user or (frappe.session.user if frappe.session.user != "Guest" else None)
	_insert({
		"doctype": "Pay4sync API Log",
		"user": user,
		"endpoint": endpoint,
		"http_method": http_method,
		"status_code": status_code or 0,
		"success": 1 if success else 0,
		"duration_ms": duration_ms,
		"reference": reference,
		"error": (error or "")[:MAX_ERROR_LENGTH] or None,
	})


def mask_account(value):
	value = str(value or "")
	return f"XXXX{value[-4:]}" if len(value) > 4 else value


def log_webhook(user, payload, key_valid, remote_ip):
	payload = dict(payload or {})
	if "beneficiary_account_number" in payload:
		payload["beneficiary_account_number"] = mask_account(payload["beneficiary_account_number"])

	_insert({
		"doctype": "Pay4sync Webhook Log",
		"user": user,
		"payout": payload.get("payout"),
		"status": payload.get("status"),
		"amount": payload.get("amount"),
		"reference_utr": payload.get("reference_utr"),
		"key_valid": 1 if key_valid else 0,
		"remote_ip": remote_ip,
		"payload": json.dumps(payload, indent=1, default=str),
	})


def clear_old_logs():
	"""Daily scheduler job: drop logs older than LOG_RETENTION_DAYS."""
	cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -LOG_RETENTION_DAYS)
	for doctype in LOG_DOCTYPES:
		frappe.db.delete(doctype, {"creation": ("<", cutoff)})
	frappe.db.commit()
