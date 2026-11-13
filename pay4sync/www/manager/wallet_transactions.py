"""/manager/wallet-transactions — all RAMASETU merchants' wallet transactions (read-only)."""

from pay4sync.utils.web import manager_page

no_cache = 1


def get_context(context):
	return manager_page(context, "Wallet Transactions", "m-wallet")
