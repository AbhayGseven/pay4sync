"""/reset-password?key=… — set a new password from the emailed link (see api/auth.reset_password)."""

import frappe

from pay4sync.utils.web import ASSET_VERSION

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.title = "Reset Password"
	context.p4s_version = ASSET_VERSION
	return context
