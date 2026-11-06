"""/payout/new (Simple Payout form) and /payout/<name> (read-only view). See website_route_rules."""

from pay4sync.utils.web import merchant_page, route_name

no_cache = 1


def get_context(context):
	name = route_name() or "new"
	context.doc_name = name
	if name == "new":
		return merchant_page(context, "New Simple Payout", "new-payout",
			breadcrumbs=[{"label": "Simple Payout", "route": "/payout/new"}])
	return merchant_page(context, name, "payouts",
		breadcrumbs=[{"label": "My Payouts", "route": "/payout"}])
