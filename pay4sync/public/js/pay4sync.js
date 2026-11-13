/* Shared helpers for the merchant pages. Exposes window.P4S. */
(function () {
	"use strict";

	const API = "/api/method/";

	function esc(value) {
		if (value === null || value === undefined) return "";
		return String(value)
			.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
	}

	function stripHtml(text) {
		const div = document.createElement("div");
		div.innerHTML = text;
		return (div.textContent || div.innerText || "").trim();
	}

	/* Pull a readable message out of a Frappe error response. */
	function errorMessage(body, status) {
		try {
			if (body && body._server_messages) {
				const msgs = JSON.parse(body._server_messages).map((m) => {
					try { return stripHtml(JSON.parse(m).message || ""); } catch (e) { return stripHtml(m); }
				}).filter(Boolean);
				if (msgs.length) return msgs.join("\n");
			}
			if (body && body.message && typeof body.message === "string") return stripHtml(body.message);
		} catch (e) { /* fall through */ }
		if (status === 400 || status === 403) {
			return "Your session has expired or you are not allowed to do this. Please refresh the page and log in again.";
		}
		return "Something went wrong. Please try again.";
	}

	/* Call a whitelisted server method. Resolves with `message`, rejects with an Error. */
	async function call(method, args, httpMethod) {
		httpMethod = httpMethod || "GET";
		const clean = {};
		Object.keys(args || {}).forEach((k) => {
			if (args[k] !== undefined && args[k] !== null && args[k] !== "") clean[k] = args[k];
		});

		let url = API + method;
		const opts = {
			method: httpMethod,
			headers: { Accept: "application/json", "X-Frappe-CSRF-Token": (window.frappe && frappe.csrf_token) || "" },
			credentials: "same-origin",
		};
		if (httpMethod === "GET") {
			const qs = new URLSearchParams(clean).toString();
			if (qs) url += "?" + qs;
		} else {
			opts.headers["Content-Type"] = "application/json";
			opts.body = JSON.stringify(clean);
		}

		let response, body;
		try {
			response = await fetch(url, opts);
		} catch (e) {
			throw new Error("Could not reach the server. Check your internet connection.");
		}
		try { body = await response.json(); } catch (e) { body = null; }

		if (!response.ok) {
			const err = new Error(errorMessage(body, response.status));
			err.status = response.status;
			throw err;
		}
		return body ? body.message : null;
	}

	function download(method, args) {
		const qs = new URLSearchParams(args || {}).toString();
		window.location.href = API + method + (qs ? "?" + qs : "");
	}

	function showAlert(message, kind) {
		const box = document.getElementById("p4s-alert");
		if (!box) return window.alert(message);
		box.className = "p4s-alert " + (kind || "error");
		box.textContent = message;
		box.hidden = false;
		box.scrollIntoView({ behavior: "smooth", block: "nearest" });
	}
	function hideAlert() {
		const box = document.getElementById("p4s-alert");
		if (box) box.hidden = true;
	}

	function number(value) {
		return Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}
	/* "INR 2,500.00" — how lists show currency. */
	function inr(value) {
		if (value === null || value === undefined || value === "") return "";
		return isNaN(Number(value)) ? esc(value) : "INR " + number(value);
	}
	/* "₹ 2,500.00" — how the wallet shows currency. */
	function rupee(value) {
		if (value === null || value === undefined || value === "") return "";
		return isNaN(Number(value)) ? esc(value) : "₹ " + number(value);
	}
	/* 2026-11-06 or "2026-11-06 15:55:50" -> 06-11-2026 */
	function dmy(value) {
		if (!value) return "";
		const parts = String(value).slice(0, 10).split("-");
		return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : esc(value);
	}

	const PILL = {
		Completed: "green", Submitted: "green", Approved: "green",
		Pending: "orange", Draft: "orange", "Not Saved": "orange", "Pending Approval": "orange",
		"In Process": "blue",
		Failed: "red", Cancelled: "red",
	};
	function pill(status) {
		return status ? `<span class="p4s-pill ${PILL[status] || ""}">${esc(status)}</span>` : "";
	}
	function setHeader(title, status) {
		const t = document.getElementById("p4s-title");
		const i = document.getElementById("p4s-indicator");
		if (t && title) t.textContent = title;
		if (i) i.innerHTML = pill(status);
		if (title) document.title = title + " · RAMASETU";
	}

	function emptyRow(cols, text) {
		return `<tr><td class="p4s-empty" colspan="${cols}">${esc(text || "No records found")}</td></tr>`;
	}

	/* Disable a button while `promise` runs. */
	async function busy(button, promise, label) {
		const original = button.innerHTML;
		button.disabled = true;
		if (label) button.textContent = label;
		try { return await promise; } finally { button.disabled = false; button.innerHTML = original; }
	}

	function formData(form) {
		const out = {};
		new FormData(form).forEach((v, k) => { out[k] = typeof v === "string" ? v.trim() : v; });
		return out;
	}

	function fileToBase64(file) {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
			reader.onerror = () => reject(new Error("Could not read the file."));
			reader.readAsDataURL(file);
		});
	}

	function debounce(fn, ms) {
		let timer = null;
		return function () {
			clearTimeout(timer);
			const args = arguments;
			timer = setTimeout(() => fn.apply(null, args), ms);
		};
	}

	/* Local (not UTC) YYYY-MM-DD, so IST mornings don't show yesterday. */
	function isoDate(d) {
		const pad = (n) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
	}
	function today() { return isoDate(new Date()); }
	function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return isoDate(d); }
	function monthStart() { const d = new Date(); d.setDate(1); return isoDate(d); }

	/*
	 * Manager list pages: fill the Merchant <select>, default the From/To dates to this
	 * month, wire the "Download CSV" button, then start the list. Resolves to a
	 * {email: "Full Name"} map used to show merchant names in rows.
	 */
	async function managerList(opts) {
		const form = opts.filters;
		const names = {};
		if (form.from_date && !form.from_date.value) form.from_date.value = monthStart();
		if (form.to_date && !form.to_date.value) form.to_date.value = today();
		try {
			const r = await call("pay4sync.api.manager.list_merchants");
			r.data.forEach((m) => {
				names[m.user] = m.full_name || m.user;
				form.merchant.insertAdjacentHTML("beforeend",
					`<option value="${esc(m.user)}">${esc(m.full_name || m.user)} (${esc(m.user)})</option>`);
			});
		} catch (e) {
			showAlert(e.message);
		}
		if (opts.csv) {
			opts.csv.addEventListener("click", () => {
				const args = Object.assign({ kind: opts.kind }, formData(form));
				Object.keys(args).forEach((k) => { if (!args[k]) delete args[k]; });
				download("pay4sync.api.manager.export_csv", args);
			});
		}
		const merchantName = (email) => esc(names[email] || email || "");
		list(Object.assign({}, opts, { row: (item, sr) => opts.row(item, sr, merchantName) }));
		return names;
	}

	/*
	 * Frappe-style list with a filter bar and "Load More".
	 *   opts.method   whitelisted method returning {data, total}
	 *   opts.tbody    <tbody> element
	 *   opts.cols     number of columns (for empty / loading rows)
	 *   opts.row      (item, srNo) -> "<tr>…</tr>"
	 *   opts.filters  optional <form>; its inputs filter the list (debounced)
	 *   opts.more     the Load More wrapper element
	 *   opts.onClick  optional (name) => void for rows with data-name
	 */
	function list(opts) {
		const LIMIT = 20;
		let start = 0;
		let token = 0;
		const button = opts.more.querySelector("button");

		async function load(append) {
			const mine = ++token;
			if (!append) {
				start = 0;
				opts.tbody.innerHTML = `<tr><td class="p4s-empty" colspan="${opts.cols}">Loading…</td></tr>`;
			}
			const args = Object.assign({ start, limit: LIMIT }, opts.filters ? formData(opts.filters) : {});
			try {
				const r = await call(opts.method, args);
				if (mine !== token) return;
				const rows = r.data.map((item, i) => opts.row(item, start + i + 1)).join("");
				if (append) opts.tbody.insertAdjacentHTML("beforeend", rows);
				else opts.tbody.innerHTML = rows || emptyRow(opts.cols, opts.empty);
				start += r.data.length;
				opts.more.classList.toggle("p4s-hidden", start >= r.total);
			} catch (e) {
				if (mine !== token) return;
				if (!append) opts.tbody.innerHTML = emptyRow(opts.cols, "Could not load records");
				showAlert(e.message);
			}
		}

		button.addEventListener("click", () => busy(button, load(true), "Loading…"));
		if (opts.filters) {
			const reload = debounce(() => { hideAlert(); load(false); }, 400);
			opts.filters.addEventListener("input", reload);
			opts.filters.addEventListener("change", reload);
			opts.filters.addEventListener("submit", (e) => { e.preventDefault(); load(false); });
		}
		if (opts.onClick) {
			opts.tbody.addEventListener("click", (ev) => {
				const tr = ev.target.closest("tr[data-name]");
				if (tr) opts.onClick(tr.dataset.name);
			});
		}
		load(false);
		return { reload: () => load(false) };
	}

	/* Avatar dropdown in the top bar. */
	document.addEventListener("click", (ev) => {
		const menu = document.getElementById("p4s-dropdown");
		if (!menu) return;
		if (ev.target.closest("#p4s-avatar")) menu.hidden = !menu.hidden;
		else if (!ev.target.closest("#p4s-dropdown")) menu.hidden = true;
	});

	window.P4S = {
		esc, call, download, showAlert, hideAlert, inr, rupee, dmy, pill, setHeader, emptyRow, busy,
		formData, fileToBase64, debounce, today, daysAgo, monthStart, list, managerList,
	};
})();
