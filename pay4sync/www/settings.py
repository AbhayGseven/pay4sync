"""/settings — the merchant's webhook / API settings (same fields as pay4done's /settings)."""

from pay4sync.utils.web import merchant_page

no_cache = 1


def get_context(context):
	return merchant_page(context, "Settings", "settings")
