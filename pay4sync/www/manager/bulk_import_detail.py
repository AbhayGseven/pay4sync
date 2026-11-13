"""/manager/bulk-imports/<name> — one bulk import with its rows, read-only. See website_route_rules."""

from pay4sync.utils.web import manager_page, route_name

no_cache = 1


def get_context(context):
	context.doc_name = route_name()
	return manager_page(context, context.doc_name or "Bulk Import", "m-bulk",
		breadcrumbs=[{"label": "Bulk Imports", "route": "/manager/bulk-imports"}])
