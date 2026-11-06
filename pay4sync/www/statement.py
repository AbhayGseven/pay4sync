from pay4sync.utils.web import merchant_page

no_cache = 1


def get_context(context):
	return merchant_page(context, "Statement", "statement")
