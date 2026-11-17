"""
Login for pay4push.in ("login via pay4done").

Merchants are created and managed only on pay4done; pay4push stores no
merchant passwords. On login:

  * Administrator / System Users of pay4push (the team) log in with their own
    pay4push password, exactly as Frappe's normal login.
  * Everyone else is a merchant and/or a RAMASETU manager: the email + password
    are checked against pay4done (merchant_api.login.verify_merchant_login),
    which also says which of the two the user is. On success the local Website
    User (no password) is created the first time, its local roles (Pay4sync
    Merchant / Ramasetu Manager) are synced to that answer on every login, and
    a session is started for it.

A pay4done account can never become a pay4push System User this way: if the
email already belongs to a System User here, only the pay4push password works.
"""

import hashlib
import secrets

import frappe

from pay4sync.utils import client
from pay4sync.utils.client import UNAVAILABLE, Pay4doneTimeout
from pay4sync.utils.permissions import MANAGER_ROLE, MERCHANT_ROLE

INVALID = "Invalid login. Please check your email and password."
MAX_IP_ATTEMPTS = 30
IP_WINDOW_SECONDS = 10 * 60


def _too_many_attempts():
	"""Per-IP throttle on top of pay4done's per-email lockout. Fails open if the cache is down."""
	key = f"p4s_login_ip:{frappe.local.request_ip}"
	try:
		count = frappe.utils.cint(frappe.cache.get_value(key)) + 1
		frappe.cache.set_value(key, count, expires_in_sec=IP_WINDOW_SECONDS)
		return count > MAX_IP_ATTEMPTS
	except Exception:
		return False


def _login_team_member(email, password):
	lm = frappe.local.login_manager
	lm.authenticate(user=email, pwd=password)  # raises AuthenticationError on a wrong password
	lm.post_login()
	return {"success": True, "home_page": "/app"}


def _sync_local_user(email, full_name, is_merchant, is_manager):
	"""Create (first login) or update the local Website User for this RAMASETU user, and give it
	exactly the local roles that match its pay4done roles (merchant and/or manager)."""
	wanted = {MERCHANT_ROLE: is_merchant, MANAGER_ROLE: is_manager}
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": (full_name or email)[:140],
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": role} for role, keep in wanted.items() if keep],
		})
		user.flags.no_welcome_mail = True
		user.flags.ignore_password_policy = True
		user.insert(ignore_permissions=True)
	else:
		current = set(frappe.get_roles(email))
		add = [role for role, keep in wanted.items() if keep and role not in current]
		remove = [role for role, keep in wanted.items() if not keep and role in current]
		if add or remove:
			user = frappe.get_doc("User", email)
			# Runs before login_as, i.e. as Guest: the role sync is decided by pay4done, not the caller.
			user.flags.ignore_permissions = True
			if add:
				user.add_roles(*add)
			if remove:
				user.remove_roles(*remove)
	frappe.db.commit()


def _login_merchant(email, password):
	local = frappe.db.get_value("User", email, ["enabled"], as_dict=True)
	if local and not local.enabled:
		frappe.throw(INVALID, frappe.AuthenticationError)

	try:
		status, data = client.post("login.verify_merchant_login", {"password": password},
			as_user=email, raise_on_error=False)
	except Pay4doneTimeout:
		frappe.throw(UNAVAILABLE)

	if status == 429:
		frappe.throw((data or {}).get("error") or INVALID, frappe.AuthenticationError)
	if status != 200 or not (data or {}).get("success"):
		if status in (0, 500, 502, 503, 504):
			frappe.throw(UNAVAILABLE)
		frappe.throw(INVALID, frappe.AuthenticationError)

	is_merchant, is_manager = bool(data.get("is_merchant")), bool(data.get("is_manager"))
	if not (is_merchant or is_manager):
		frappe.throw(INVALID, frappe.AuthenticationError)
	_sync_local_user(email, data.get("full_name"), is_merchant, is_manager)
	frappe.local.login_manager.login_as(email)
	return {"success": True, "home_page": "/manager/payouts" if is_manager else "/payout"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def login(usr=None, pwd=None):
	email = (usr or "").strip()
	if email.lower() != "administrator":
		email = email.lower()  # Frappe stores user ids (emails) in lower case on both sites
	if not email or not pwd:
		frappe.throw("Please enter your email and password.")
	if _too_many_attempts():
		frappe.throw("Too many login attempts. Please try again after a few minutes.", frappe.AuthenticationError)

	user_type = frappe.db.get_value("User", email, "user_type")
	if email == "Administrator" or user_type == "System User":
		return _login_team_member(email, pwd)
	return _login_merchant(email, pwd)


# ---------------------------------------------------------------------------
# Forgot password. The password lives in pay4done. RAMASETU makes the link (RAMASETU
# URL), pay4done emails it from its own outgoing account (RAMASETU wording), and
# RAMASETU checks the link before asking pay4done to set the new password.
#
# The link key is random, single-use, valid RESET_LINK_MINUTES, and only its
# SHA-256 hash is stored (in the cache). Every request gets the same answer,
# so the page never reveals which emails have an account.
# ---------------------------------------------------------------------------

RESET_LINK_MINUTES = 30
RESET_SENT = ("If an account exists for this email, we have sent a link to reset the password. "
	"Please check your inbox.")
RESET_INVALID = "This reset link is invalid or has expired. Please request a new one."
MAX_RESET_PER_EMAIL = 5  # per hour
MAX_RESET_PER_IP = 20  # per hour


def _reset_cache_key(key):
	return "p4s_reset:" + hashlib.sha256(key.encode()).hexdigest()


def _over_limit(cache_key, limit, seconds=3600):
	try:
		count = frappe.utils.cint(frappe.cache.get_value(cache_key)) + 1
		frappe.cache.set_value(cache_key, count, expires_in_sec=seconds)
		return count > limit
	except Exception:
		return False


@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_reset_link(email=None):
	email = (email or "").strip().lower()
	if not email or "@" not in email:
		frappe.throw("Please enter your email.")
	if _over_limit(f"p4s_reset_ip:{frappe.local.request_ip}", MAX_RESET_PER_IP) or \
			_over_limit(f"p4s_reset_email:{email}", MAX_RESET_PER_EMAIL):
		frappe.throw("Too many requests. Please try again after some time.")

	# Team members (System Users) reset their password from the desk, not here.
	if frappe.db.get_value("User", email, "user_type") == "System User":
		return {"success": True, "message": RESET_SENT}

	key = secrets.token_urlsafe(32)
	link = frappe.utils.get_url(f"/reset-password?key={key}")
	# pay4done checks the user may use RAMASETU and sends the mail from its own outgoing account.
	try:
		status, data = client.post("login.send_reset_email", {"link": link, "minutes": RESET_LINK_MINUTES},
			as_user=email, raise_on_error=False)
	except Pay4doneTimeout:
		frappe.throw(UNAVAILABLE)

	if status == 200 and (data or {}).get("success"):
		frappe.cache.set_value(_reset_cache_key(key), email, expires_in_sec=RESET_LINK_MINUTES * 60)
	elif status == 503 and isinstance(data, dict):
		frappe.throw("We could not send the email right now. Please try again later or contact support.")
	elif status in (0, 500, 502, 503, 504):
		frappe.throw(UNAVAILABLE)
	# Any other answer (e.g. 401: no such RAMASETU user) gets the same reply, so emails can't be probed.
	return {"success": True, "message": RESET_SENT}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password(key=None, new_password=None):
	if not key:
		frappe.throw(RESET_INVALID)
	cache_key = _reset_cache_key(key)
	email = frappe.cache.get_value(cache_key)
	if not email:
		frappe.throw(RESET_INVALID)
	if not new_password:
		frappe.throw("Please enter a new password.")

	try:
		status, data = client.post("login.set_merchant_password", {"new_password": new_password},
			as_user=email, raise_on_error=False)
	except Pay4doneTimeout:
		frappe.throw(UNAVAILABLE)

	if status == 400:
		frappe.throw((data or {}).get("error") or "Please choose a stronger password.")
	if status != 200 or not (data or {}).get("success"):
		if status == 401:
			frappe.cache.delete_value(cache_key)
			frappe.throw(RESET_INVALID)
		frappe.throw(UNAVAILABLE)

	frappe.cache.delete_value(cache_key)  # single use
	# Log the user out of every RAMASETU session as well.
	from frappe.sessions import clear_sessions
	clear_sessions(user=email, keep_current=False, force=True)
	frappe.db.commit()
	return {"success": True}
