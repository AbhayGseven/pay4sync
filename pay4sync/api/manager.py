"""
Manager APIs for the RAMASETU manager pages — READ ONLY.

A manager sees every RAMASETU merchant's payouts, wallet transactions,
recharges and bulk imports. Which merchants those are is decided by pay4done
(merchant_api.manager), never here. Nothing in this file creates or changes data.
"""

import csv
import io

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_manager, send_file

PAYOUT_FILTERS = [
	"merchant", "status", "from_date", "to_date", "search", "beneficiary_name", "beneficiary_account_number",
	"beneficiary_ifsc_code", "cust_ref_number", "reference_utr", "payment_type",
	"beneficiary_account_type", "amount", "payout_date",
]
WALLET_FILTERS = ["merchant", "transaction_type", "from_date", "to_date"]
RECHARGE_FILTERS = ["merchant", "from_date", "to_date", "amount", "remarks"]
BULK_FILTERS = ["merchant", "from_date", "to_date", "payout_status"]

# list kind -> (pay4done endpoint, allowed filters, CSV columns as (field, header))
LISTS = {
	"payouts": ("manager.list_payouts", PAYOUT_FILTERS, [
		("merchant", "Merchant"), ("name", "Payout ID"), ("creation", "Created On"),
		("payout_date", "Payout Date"), ("beneficiary_name", "Beneficiary Name"),
		("beneficiary_account_number", "Beneficiary Account Number"), ("beneficiary_ifsc_code", "IFSC Code"),
		("beneficiary_account_type", "Account Type"), ("amount", "Amount"), ("status", "Status"),
		("payment_type", "Payment Type"), ("reference_utr", "Reference UTR"),
		("cust_ref_number", "Cust Ref Number"),
	]),
	"wallet": ("manager.list_wallet_transactions", WALLET_FILTERS, [
		("merchant", "Merchant"), ("name", "Transaction ID"), ("posting_date", "Posting Date"),
		("transaction_type", "Type"), ("amount", "Amount"), ("reference_name", "Reference"),
		("remarks", "Remarks"),
	]),
	"recharges": ("manager.list_recharges", RECHARGE_FILTERS, [
		("merchant", "Merchant"), ("name", "Recharge ID"), ("recharge_date", "Recharge Date"),
		("amount", "Amount"), ("status", "Status"), ("remarks", "Remarks"),
	]),
	"bulk": ("manager.list_bulk_imports", BULK_FILTERS, [
		("merchant", "Merchant"), ("name", "Import ID"), ("creation", "Created On"),
		("payout_status", "Status"), ("total_number_of_records", "Records"), ("total_amount", "Total Amount"),
	]),
}


def _cell(value):
	"""CSV cell; text starting with = + - @ is prefixed with ' so Excel never runs it as a formula."""
	if value is None:
		return ""
	if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
		return "'" + value
	return value


def _params(allowed, values):
	return {f: values[f] for f in allowed if values.get(f) not in (None, "")}


def _list(kind, start, limit, filters):
	endpoint, allowed, _ = LISTS[kind]
	params = _params(allowed, filters)
	params.update({"start": start, "limit": limit})
	return client.get(endpoint, params)


@frappe.whitelist()
def list_merchants():
	require_manager()
	return client.get("manager.list_merchants")


@frappe.whitelist()
def list_payouts(start=0, limit=20, **filters):
	require_manager()
	return _list("payouts", start, limit, filters)


@frappe.whitelist()
def get_payout(name=None):
	require_manager()
	return client.get("manager.get_payout", {"name": name}, reference=name)


@frappe.whitelist()
def list_wallet_transactions(start=0, limit=20, **filters):
	require_manager()
	return _list("wallet", start, limit, filters)


@frappe.whitelist()
def list_recharges(start=0, limit=20, **filters):
	require_manager()
	return _list("recharges", start, limit, filters)


@frappe.whitelist()
def list_bulk_imports(start=0, limit=20, **filters):
	require_manager()
	return _list("bulk", start, limit, filters)


@frappe.whitelist()
def get_bulk_import(name=None):
	require_manager()
	return client.get("manager.get_bulk_import", {"name": name}, reference=name)


@frappe.whitelist()
def export_csv(kind=None, **filters):
	"""Open in the browser (GET): the filtered list as CSV (up to 10,000 rows)."""
	require_manager()
	if kind not in LISTS:
		frappe.throw("Unknown list")
	endpoint, allowed, columns = LISTS[kind]
	params = _params(allowed, filters)
	params["export"] = 1
	data = client.get(endpoint, params, timeout=120)["data"]

	out = io.StringIO()
	writer = csv.writer(out)
	writer.writerow([header for _, header in columns])
	for row in data:
		writer.writerow([_cell(row.get(f)) for f, _ in columns])
	send_file(f"{kind}-{frappe.utils.today()}.csv", out.getvalue())
