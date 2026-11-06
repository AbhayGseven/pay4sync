"""Statement and report APIs for the pay4push pages."""

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant, send_file


@frappe.whitelist()
def get_statement(from_date=None, to_date=None):
	require_merchant()
	return client.get("statement.get_statement", {"from_date": from_date, "to_date": to_date})


@frappe.whitelist()
def download_statement(from_date=None, to_date=None):
	"""Open in the browser (GET) to download the statement as CSV."""
	require_merchant()
	data = client.get("statement.download_statement", {"from_date": from_date, "to_date": to_date})
	send_file(data["filename"], data["content"])
