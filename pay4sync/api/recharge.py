"""
Wallet Recharge APIs for the pay4push pages — read only.

Same as pay4done: recharges are created and submitted by a pay4done admin once
the merchant's payment is received. Merchants only see their history.
"""

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant


@frappe.whitelist()
def list_recharges(start=0, limit=20, recharge_date=None, amount=None, remarks=None):
	require_merchant()
	return client.get("recharge.list_wallet_recharges", {
		"start": start, "limit": limit, "recharge_date": recharge_date,
		"amount": amount, "remarks": remarks,
	})


@frappe.whitelist()
def get_recharge(name=None):
	require_merchant()
	return client.get("recharge.get_wallet_recharge", {"name": name}, reference=name)
