"""Wallet APIs for the pay4push pages."""

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant


@frappe.whitelist()
def get_balance():
	require_merchant()
	return client.get("wallet.get_wallet_balance")


@frappe.whitelist()
def list_transactions(transaction_type=None, from_date=None, to_date=None, start=0, limit=20):
	require_merchant()
	return client.get("wallet.list_wallet_transactions", {
		"transaction_type": transaction_type, "from_date": from_date, "to_date": to_date,
		"start": start, "limit": limit,
	})
