/* Hisab SPA — hash router, API client, views. Vanilla JS, no build step. */
"use strict";

const API = "/api";
const $ = (sel) => document.querySelector(sel);

/* ---------- helpers ---------- */
const fmtMoney = (n, cur = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: cur, maximumFractionDigits: 2 }).format(n || 0);

const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(msg, isError = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("error", isError);
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 3200);
}

const statusTag = (s) => {
  const map = { paid: ["paid", "Paid"], overdue: ["overdue", "Overdue"], sent: ["sent", "Sent"], draft: ["draft", "Draft"] };
  const [cls, label] = map[s] || ["draft", s];
  return `<span class="tag ${cls}">${label}</span>`;
};

/* ---------- API client ---------- */
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = localStorage.getItem("hisab_token");
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401 && !path.includes("/login") && !path.includes("/register")) {
    localStorage.removeItem("hisab_token");
    location.hash = "#/";
    return;
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : detail ? detail.map((d) => d.msg).join("; ") : "Something went wrong";
    throw new Error(msg);
  }
  return data;
}

/* ---------- auth state ---------- */
const token = () => localStorage.getItem("hisab_token");

/* ---------- views ---------- */
const views = {};

views.landing = () => {
  if (token()) return views.dashboard();
  return `
    <div class="landing">
      <div class="brand-badge"><span class="dot"></span> Hisab</div>
      <h1>Your freelance income, <span class="grad">finally in one place.</span></h1>
      <p class="sub">Send invoices in USD or PKR, chase overdue payments, and see exactly what you've earned — in dollars and in rupees.</p>
      <div class="auth-card">
        <div class="tabs">
          <button id="tabLogin" class="active">Log in</button>
          <button id="tabRegister">Sign up</button>
        </div>
        <form id="authForm">
          <div class="field"><label>Email</label><input type="email" id="authEmail" required placeholder="you@example.com" autocomplete="email" /></div>
          <div class="field"><label>Password</label><input type="password" id="authPassword" required minlength="8" placeholder="At least 8 chars, letters + numbers" autocomplete="current-password" /></div>
          <div class="field" id="nameField" style="display:none"><label>Full name</label><input id="authName" minlength="2" placeholder="Your name" autocomplete="name" /></div>
          <button class="btn primary full" type="submit" id="authSubmit">Log in</button>
        </form>
        <p class="hint">Demo: <code>demo@hisab.pk</code> / <code>demo1234</code></p>
      </div>
    </div>`;
};

views.dashboard = async () => {
  if (!token()) return views.landing();
  try {
    const [me, dash] = await Promise.all([api("/auth/me"), api("/stats/dashboard")]);
    const s = dash.summary;
    const rows = dash.recent_invoices.map(
      (i) => `<tr>
        <td><strong>${esc(i.invoice_number)}</strong><div class="muted" style="font-size:12px">${esc(i.client.name)}</div></td>
        <td>${fmtMoney(i.total, i.currency)}</td>
        <td>${fmtDate(i.due_date)}</td>
        <td>${statusTag(i.status)}</td>
      </tr>`
    ).join("");
    return `
      <div class="page-head">
        <div><h2>Salaam, ${esc(me.name.split(" ")[0])} 👋</h2><p>Here's how your freelance money is doing.</p></div>
        <button class="btn primary" onclick="location.hash='#/invoices/new'">+ New Invoice</button>
      </div>
      <div class="stats-grid">
        <div class="stat-card blue"><div class="lbl">Total Invoiced</div><div class="val">${fmtMoney(s.total_invoiced)}</div><div class="sub">${s.invoice_count} invoices</div></div>
        <div class="stat-card green"><div class="lbl">Paid</div><div class="val">${fmtMoney(s.total_paid)}</div><div class="sub">${s.paid_count} collected</div></div>
        <div class="stat-card amber"><div class="lbl">Pending</div><div class="val">${fmtMoney(s.total_pending)}</div><div class="sub">awaiting payment</div></div>
        <div class="stat-card red"><div class="lbl">Overdue</div><div class="val">${fmtMoney(s.total_overdue)}</div><div class="sub">${s.overdue_count} invoices</div></div>
        <div class="stat-card green"><div class="lbl">Outstanding in PKR</div><div class="val">₨${fmtMoney(s.outstanding_pkr, "PKR").replace(/PKR|₨/g, "").trim()}</div><div class="sub">@ ${s.usd_to_pkr}/USD for tax season</div></div>
      </div>
      <div class="card">
        <div class="card-head"><h3>Recent invoices</h3><a class="mini-btn" href="#/invoices">View all</a></div>
        ${rows ? `<table class="table"><thead><tr><th>Invoice</th><th>Total</th><th>Due</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty"><div class="big">🧾</div>No invoices yet — create your first one.</div>`}
      </div>`;
  } catch (e) {
    toast(e.message, true);
    return `<div class="empty"><div class="big">😕</div>${esc(e.message)}</div>`;
  }
};

views.invoices = async () => {
  if (!token()) return views.landing();
  try {
    const list = await api("/invoices");
    const rows = list.map(
      (i) => `<tr>
        <td><strong>${esc(i.invoice_number)}</strong><div style="font-size:12px;color:var(--muted)">${esc(i.client_name)}</div></td>
        <td>${fmtMoney(i.total, i.currency)}</td>
        <td>${fmtDate(i.due_date)}</td>
        <td>${statusTag(i.status)}</td>
        <td><div class="row-actions">
          ${i.status !== "paid" ? `<button class="mini-btn pay" onclick="hisab.pay(${i.id})">Mark paid</button>` : ""}
          ${i.status === "draft" ? `<button class="mini-btn" onclick="hisab.send(${i.id})">Send</button>` : ""}
          <button class="mini-btn danger" onclick="hisab.del('invoices', ${i.id})">Delete</button>
        </div></td>
      </tr>`
    ).join("");
    return `
      <div class="page-head">
        <div><h2>Invoices</h2><p>Create, send, and track every invoice.</p></div>
        <button class="btn primary" onclick="location.hash='#/invoices/new'">+ New Invoice</button>
      </div>
      <div class="card">
        ${rows ? `<table class="table"><thead><tr><th>Invoice</th><th>Total</th><th>Due</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty"><div class="big">🧾</div>No invoices yet.</div>`}
      </div>`;
  } catch (e) {
    toast(e.message, true);
    return "";
  }
};

views.invoiceNew = async () => {
  if (!token()) return views.landing();
  try {
    const clients = await api("/clients");
    return `
      <div class="page-head"><div><h2>New Invoice</h2><p>Fill in the details — totals are calculated for you.</p></div></div>
      <div class="card" style="padding:24px">
        ${clients.length ? "" : `<div class="empty"><div class="big">👤</div>Add a client first.</div>`}
        <form id="invoiceForm">
          <label>Client
            <select id="invClient" required>${clients.map((c) => `<option value="${c.id}">${esc(c.name)}${c.company ? " — " + esc(c.company) : ""}</option>`).join("")}</select>
          </label>
          <div class="grid-2">
            <label>Currency<select id="invCurrency"><option>USD</option><option>PKR</option><option>EUR</option><option>GBP</option><option>AED</option><option>SAR</option></select></label>
            <label>Due date<input type="date" id="invDue" required /></label>
          </div>
          <div id="itemRows"></div>
          <button type="button" class="btn ghost full" id="addItem">+ Add line item</button>
          <label>Notes<textarea id="invNotes" rows="2" placeholder="Payment terms…"></textarea></label>
          <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px">
            <a class="btn ghost" href="#/invoices">Cancel</a>
            <button type="submit" class="btn primary">Create Invoice</button>
          </div>
        </form>
      </div>`;
  } catch (e) {
    toast(e.message, true);
    return "";
  }
};

views.clients = async () => {
  if (!token()) return views.landing();
  try {
    const list = await api("/clients");
    const rows = list.map(
      (c) => `<tr>
        <td><strong>${esc(c.name)}</strong></td>
        <td>${esc(c.company || "—")}</td>
        <td>${esc(c.email || "—")}</td>
        <td>${esc(c.country || "—")}</td>
        <td><button class="mini-btn danger" onclick="hisab.del('clients', ${c.id})">Delete</button></td>
      </tr>`
    ).join("");
    return `
      <div class="page-head">
        <div><h2>Clients</h2><p>Everyone you invoice, in one list.</p></div>
        <button class="btn primary" onclick="hisab.newClient()">+ Add Client</button>
      </div>
      <div class="card">
        ${rows ? `<table class="table"><thead><tr><th>Name</th><th>Company</th><th>Email</th><th>Country</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty"><div class="big">👥</div>No clients yet.</div>`}
      </div>`;
  } catch (e) {
    toast(e.message, true);
    return "";
  }
};

views.income = async () => {
  if (!token()) return views.landing();
  try {
    const s = (await api("/stats/summary"));
    return `
      <div class="page-head"><div><h2>Income Report</h2><p>Roughly what you've made, in rupees — handy for FBR season.</p></div></div>
      <div class="stats-grid">
        <div class="stat-card blue"><div class="lbl">Invoiced (USD)</div><div class="val">${fmtMoney(s.total_invoiced)}</div></div>
        <div class="stat-card green"><div class="lbl">Paid (USD)</div><div class="val">${fmtMoney(s.total_paid)}</div></div>
        <div class="stat-card red"><div class="lbl">Overdue (USD)</div><div class="val">${fmtMoney(s.total_overdue)}</div></div>
        <div class="stat-card green"><div class="lbl">Outstanding ≈ PKR</div><div class="val" style="font-size:22px">₨ ${Number(s.outstanding_pkr).toLocaleString("en-PK")}</div><div class="sub">@ ${s.usd_to_pkr}/USD</div></div>
      </div>
      <div class="card" style="padding:20px">
        <p style="color:var(--muted);font-size:14px;line-height:1.7">💡 <strong style="color:var(--text)">How to use this:</strong> add up your paid invoices in USD, multiply by the current rate when you convert, and you have a solid estimate of your taxable income. Hisab shows the outstanding figure as a planning aid — always use the real bank rate on your conversion date.</p>
      </div>`;
  } catch (e) {
    toast(e.message, true);
    return "";
  }
};

/* ---------- router ---------- */
async function router() {
  const app = $("#app");
  const route = location.hash.replace(/^#/, "") || "/";
  const [path, param] = route.slice(1).split("/");
  let html = "";

  if (path === "" || path === "/") html = views.landing();
  else if (path === "dashboard") html = await views.dashboard();
  else if (path === "invoices" && param === "new") html = await views.invoiceNew();
  else if (path === "invoices") html = await views.invoices();
  else if (path === "clients") html = await views.clients();
  else if (path === "income") html = await views.income();
  else html = views.landing();

  app.innerHTML = html;
  bindPage(path, param);
}

/* ---------- per-page bindings ---------- */
function bindPage(path, param) {
  // sidebar
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === (path || "dashboard"));
  });

  const form = $("#authForm");
  if (form) {
    $("#tabLogin").addEventListener("click", () => setAuthTab("login"));
    $("#tabRegister").addEventListener("click", () => setAuthTab("register"));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = $("#authEmail").value.trim();
      const password = $("#authPassword").value;
      const isRegister = $("#nameField").style.display !== "none";
      try {
        if (isRegister) {
          await api("/auth/register", { method: "POST", body: JSON.stringify({ email, password, name: $("#authName").value.trim() }) });
          toast("Account created — logging you in");
        }
        const fd = new URLSearchParams();
        fd.append("username", email);
        fd.append("password", password);
        const res = await fetch(`${API}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: fd.toString(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");
        localStorage.setItem("hisab_token", data.access_token);
        toast("Welcome back! 🎉");
        location.hash = "#/dashboard";
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const invForm = $("#invoiceForm");
  if (invForm) {
    if (!$("#itemRows").children.length) addItemRow();
    $("#addItem").addEventListener("click", addItemRow);
    invForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rows = [...document.querySelectorAll(".item-row")].map((r) => ({
        description: r.querySelector(".it-desc").value.trim(),
        quantity: parseFloat(r.querySelector(".it-qty").value) || 1,
        unit_price: parseFloat(r.querySelector(".it-price").value) || 0,
      })).filter((r) => r.description);
      if (!rows.length) return toast("Add at least one line item", true);
      try {
        const created = await api("/invoices", {
          method: "POST",
          body: JSON.stringify({
            client_id: parseInt($("#invClient").value, 10),
            currency: $("#invCurrency").value,
            due_date: new Date($("#invDue").value + "T23:59:59").toISOString(),
            notes: $("#invNotes").value.trim() || null,
            items: rows,
          }),
        });
        toast(`${created.invoice_number} created — ${fmtMoney(created.total, created.currency)}`);
        location.hash = "#/invoices";
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const clientForm = $("#clientForm");
  if (clientForm) {
    clientForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/clients", {
          method: "POST",
          body: JSON.stringify({
            name: $("#clientName").value.trim(),
            company: $("#clientCompany").value.trim() || null,
            email: $("#clientEmail").value.trim() || null,
            country: $("#clientCountry").value.trim() || null,
          }),
        });
        $("#clientModal").classList.add("hidden");
        toast("Client added ✅");
        router();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  // logout
  document.querySelectorAll("[data-logout]").forEach((el) =>
    el.addEventListener("click", () => {
      localStorage.removeItem("hisab_token");
      location.hash = "#/";
    })
  );
}

function setAuthTab(mode) {
  const isReg = mode === "register";
  $("#tabLogin").classList.toggle("active", !isReg);
  $("#tabRegister").classList.toggle("active", isReg);
  $("#nameField").style.display = isReg ? "block" : "none";
  $("#authSubmit").textContent = isReg ? "Create account" : "Log in";
}

function addItemRow() {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <input class="it-desc" placeholder="Description — e.g. Landing page design" required />
    <input class="it-qty" type="number" min="0.01" step="0.01" value="1" title="Qty" />
    <input class="it-price" type="number" min="0" step="0.01" placeholder="Price" title="Unit price" required />
    <button type="button" class="icon-btn" title="Remove" onclick="this.parentElement.remove()">&times;</button>`;
  $("#itemRows").appendChild(row);
}

/* ---------- global actions ---------- */
window.hisab = {
  async pay(id) {
    try {
      await api(`/invoices/${id}/pay`, { method: "POST" });
      toast("Marked as paid 🎉");
      router();
    } catch (e) { toast(e.message, true); }
  },
  async send(id) {
    try {
      await api(`/invoices/${id}/send`, { method: "POST" });
      toast("Invoice sent 📨");
      router();
    } catch (e) { toast(e.message, true); }
  },
  async del(kind, id) {
    if (!confirm(`Delete this ${kind.slice(0, -1)}? This can't be undone.`)) return;
    try {
      await api(`/${kind}/${id}`, { method: "DELETE" });
      toast(`${kind.slice(0, -1)} deleted`);
      router();
    } catch (e) { toast(e.message, true); }
  },
  newClient() {
    $("#clientModal").classList.remove("hidden");
  },
};

document.querySelectorAll("[data-close-modal], [data-close-client]").forEach((el) =>
  el.addEventListener("click", () => el.closest(".modal-backdrop").classList.add("hidden"))
);

window.addEventListener("hashchange", router);
router();
