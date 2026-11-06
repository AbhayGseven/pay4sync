"""Payout APIs for the pay4push pages. Data lives in pay4done; see utils/client.py."""

import uuid

import frappe

from pay4sync.utils import client
from pay4sync.utils.client import Pay4doneTimeout
from pay4sync.utils.permissions import require_merchant

# Fields a merchant may send for a payout; anything else in the request is dropped.
PAYOUT_FIELDS = [
	"payment_type", "beneficiary_name", "beneficiary_account_number", "beneficiary_account_type",
	"amount", "beneficiary_ifsc_code", "beneficiary_bank_name", "beneficiary_email",
	"beneficiary_phone", "cust_ref_number", "remarks",
]
UNCONFIRMED = ("We could not confirm whether this payout was created. "
	"Please check My Payouts before trying again.")


def _recover_after_timeout(idempotency_key):
	"""The create call timed out: look the payout up by its key instead of retrying it."""
	try:
		found = client.get("payout.get_payout_status_by_ref", {"idempotency_key": idempotency_key})
	except (Pay4doneTimeout, frappe.ValidationError):
		frappe.local.message_log = []
		frappe.throw(UNCONFIRMED)
	data = found["data"]
	return {"success": True, "payout": data["name"], "status": data["status"], "recovered": True}


@frappe.whitelist(methods=["POST"])
def create_payout(**kwargs):
	require_merchant()
	body = {f: kwargs[f] for f in PAYOUT_FIELDS if kwargs.get(f) not in (None, "")}
	# Generated here, never taken from the browser: pay4done's key is unique system-wide.
	idempotency_key = f"p4s-{uuid.uuid4().hex}"
	body["idempotency_key"] = idempotency_key

	try:
		return client.post("payout.create_payout", body)
	except Pay4doneTimeout:
		return _recover_after_timeout(idempotency_key)


# Per-column filters of the My Payouts list, passed straight through to pay4done.
LIST_FILTERS = [
	"status", "from_date", "to_date", "search", "beneficiary_name", "beneficiary_account_number",
	"beneficiary_ifsc_code", "cust_ref_number", "reference_utr", "payment_type",
	"beneficiary_account_type", "amount", "payout_date",
]


@frappe.whitelist()
def list_payouts(start=0, limit=20, **filters):
	require_merchant()
	params = {f: filters[f] for f in LIST_FILTERS if filters.get(f) not in (None, "")}
	params.update({"start": start, "limit": limit})
	return client.get("payout.list_payouts", params)


@frappe.whitelist()
def get_payout(name=None):
	require_merchant()
	return client.get("payout.get_payout", {"name": name}, reference=name)
