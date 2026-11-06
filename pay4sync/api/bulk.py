"""
Bulk payout APIs for the pay4push pages.

The uploaded file is passed straight through to pay4done (base64) and never
stored on pay4push. Bulk payouts are always NEFT (pay4done's behaviour).
"""

import base64

import frappe

from pay4sync.utils import client
from pay4sync.utils.client import Pay4doneTimeout
from pay4sync.utils.permissions import require_merchant, send_file

LONG_TIMEOUT = 120  # parsing a file / creating one payout per row takes a while


@frappe.whitelist()
def download_template():
	"""Open in the browser (GET) to download the Excel template."""
	require_merchant()
	data = client.get("bulk.get_bulk_template")
	send_file(data["filename"], base64.b64decode(data["filecontent"]))


@frappe.whitelist(methods=["POST"])
def upload(filename=None, filecontent=None, name=None):
	"""filecontent: the file's bytes, base64-encoded by the page.
	With `name`, the file is attached to that existing draft import (after Clear)."""
	require_merchant()
	return client.post("bulk.upload_bulk_payout",
		{"filename": filename, "filecontent": filecontent, "name": name},
		timeout=LONG_TIMEOUT, reference=name)


@frappe.whitelist(methods=["POST"])
def clear(name=None):
	"""Remove the file and rows from a draft import so a new file can be attached."""
	require_merchant()
	return client.post("bulk.clear_bulk_payout", {"name": name}, reference=name)


@frappe.whitelist(methods=["POST"])
def submit(name=None):
	require_merchant()
	try:
		return client.post("bulk.submit_bulk_payout", {"name": name},
			timeout=LONG_TIMEOUT, reference=name)
	except Pay4doneTimeout:
		frappe.throw("This is taking longer than expected. Please refresh the import in a minute "
			"to see whether it was submitted, before submitting again.")


@frappe.whitelist()
def get_import(name=None):
	require_merchant()
	return client.get("bulk.get_bulk_payout", {"name": name}, reference=name)


@frappe.whitelist()
def list_imports(start=0, limit=20):
	require_merchant()
	return client.get("bulk.list_bulk_payouts", {"start": start, "limit": limit})
