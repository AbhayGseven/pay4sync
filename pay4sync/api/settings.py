"""
Settings APIs for the pay4push Settings page: the same fields as pay4done's
own /settings page (webhook, API token, IP list, webhook secret). The record
lives in pay4done; see utils/client.py.
"""

import frappe

from pay4sync.utils import client
from pay4sync.utils.permissions import require_merchant

SETTINGS_FIELDS = ["webhook", "enable_webhook", "api_token", "enable_api",
	"ip_address", "enable_ip_address", "webhook_secret"]


@frappe.whitelist()
def get_settings():
	require_merchant()
	return client.get("settings.get_settings")


@frappe.whitelist(methods=["POST"])
def update_settings(**kwargs):
	require_merchant()
	body = {f: kwargs.get(f) for f in SETTINGS_FIELDS if f in kwargs}
	return client.post("settings.update_settings", body)
