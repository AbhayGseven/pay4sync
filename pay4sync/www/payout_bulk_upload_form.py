"""/payout-bulk-upload/new and /payout-bulk-upload/<name>. See website_route_rules."""

from pay4sync.utils.web import merchant_page, route_name

no_cache = 1


def get_context(context):
	name = route_name() or "new"
	context.doc_name = name
	title = "New Payout Bulk Upload" if name == "new" else name
	return merchant_page(context, title, "bulk",
		breadcrumbs=[{"label": "Payout Bulk Upload", "route": "/payout-bulk-upload"}])
