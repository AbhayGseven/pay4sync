"""
Pay4sync API Log / Pay4sync Webhook Log writers.

Logs are committed straight away: pay4sync stores no business data of its
own, so the only writes in a request are logs, and a log must survive the
rollback that follows a frappe.throw (that is exactly when it is needed).

Never pass tokens, keys or signatures in here.
"""

import json

import frappe

DEFAULT_LOG_RETENTION_DAYS = 30  # used when pay4done settings has no value
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


def log_webhook(user, payload, key_valid, remote_ip, target_url=None, delivered=False,
		response_code=None, error=None, duration_ms=None):
	"""One row per webhook pay4done hands to RAMASETU: what came in, where it was
	sent (target_url, the merchant's Webhook URL) and what the merchant answered."""
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
		"target_url": target_url,
		"delivered": 1 if delivered else 0,
		"response_code": response_code or 0,
		"duration_ms": duration_ms,
		"error": (error or "")[:MAX_ERROR_LENGTH] or None,
		"payload": json.dumps(payload, indent=1, default=str),
	})


def _retention_days():
	"""Days to keep logs, from pay4done settings > RAMASETU Log Retention (days).
	None when pay4done cannot be asked - then nothing is deleted that day."""
	import requests

	from pay4sync.utils.client import API_PREFIX, _config

	try:
		base, key, host = _config()
		headers = {"X-P4D-Server-Key": key, "Accept": "application/json"}
		if host:
			headers["Host"] = host
		response = requests.get(base + API_PREFIX + "ramasetu_config.get_config", headers=headers, timeout=20)
		data = response.json().get("message") or {}
		days = int(data.get("log_retention_days") or 0)
		return days if days > 0 else DEFAULT_LOG_RETENTION_DAYS
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Pay4sync log cleanup: could not read retention days")
		return None


def clear_old_logs():
	"""Daily scheduler job: drop logs older than the retention days set in pay4done
	settings (30 when empty). If pay4done can't be reached, keep everything until
	the next run rather than guess."""
	days = _retention_days()
	if not days:
		return
	cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -days)
	for doctype in LOG_DOCTYPES:
		frappe.db.delete(doctype, {"creation": ("<", cutoff)})
	frappe.db.commit()
