"""/manager/bulk-imports — all RAMASETU merchants' bulk payout imports (read-only)."""

from pay4sync.utils.web import manager_page

no_cache = 1


def get_context(context):
	return manager_page(context, "Bulk Imports", "m-bulk")
