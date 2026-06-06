/* ============================================================
   SWEET CRUMBS BAKERY — ADMIN DASHBOARD JAVASCRIPT
   ============================================================ */

const API = "http://127.0.0.1:5000";
let statusChart, productChart, revenueChart, donutChart, qtyChart;

// ── Tab Navigation ───────────────────────────────────────────
document.querySelectorAll(".nav-item[data-tab]").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    document.querySelectorAll(".nav-item").forEach(l => l.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    link.classList.add("active");
    document.getElementById("tab-" + link.dataset.tab).classList.add("active");

    if (link.dataset.tab === "orders") loadOrders();
    if (link.dataset.tab === "analytics") loadAnalyticsFull();
  });
});

// ── Analytics: Summary Cards ─────────────────────────────────
async function loadAnalytics() {
  try {
    const res  = await fetch(`${API}/api/analytics`);
    const data = await res.json();

    setText("sTotalOrders",  data.total_orders);
    setText("sTotalRevenue", "Rs." + data.total_revenue.toLocaleString());
    setText("sTodayOrders",  data.today_orders);
    setText("sTopProduct",   data.top_product);
    setText("sWeeklyRev",    "Rs." + data.weekly_revenue.toLocaleString());
    setText("sMonthlyRev",   "Rs." + data.monthly_revenue.toLocaleString());

    buildStatusChart(data.status_breakdown);
    buildProductChart(data.top_products);
  } catch (e) {
    console.error("Analytics load failed:", e);
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Charts (Dashboard) ──────────────────────────────────────
const COLORS = ["#d97706","#3b82f6","#10b981","#8b5cf6","#f43f5e"];

function buildStatusChart(data) {
  const ctx = document.getElementById("statusChart");
  if (!ctx) return;
  if (statusChart) statusChart.destroy();
  const labels = Object.keys(data);
  const values = Object.values(data);
  statusChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: COLORS, borderWidth: 0 }]
    },
    options: { plugins: { legend: { position:"bottom" } }, cutout:"65%" }
  });
}

function buildProductChart(products) {
  const ctx = document.getElementById("productChart");
  if (!ctx) return;
  if (productChart) productChart.destroy();
  productChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: products.map(p => p.product),
      datasets: [{
        label: "Qty Sold",
        data: products.map(p => p.qty),
        backgroundColor: COLORS,
        borderRadius: 6,
      }]
    },
    options: { plugins:{ legend:{display:false} }, scales:{ y:{beginAtZero:true} } }
  });
}

// ── Analytics Page Charts ────────────────────────────────────
async function loadAnalyticsFull() {
  try {
    const res  = await fetch(`${API}/api/analytics`);
    const data = await res.json();
    buildRevenueChart(data.top_products);
    buildDonutChart(data.status_breakdown);
    buildQtyChart(data.top_products);
  } catch (e) { console.error(e); }
}

function buildRevenueChart(products) {
  const ctx = document.getElementById("revenueChart");
  if (!ctx) return;
  if (revenueChart) revenueChart.destroy();
  revenueChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: products.map(p => p.product),
      datasets: [{
        label: "Revenue (Rs.)",
        data: products.map(p => p.revenue),
        backgroundColor: COLORS,
        borderRadius: 8,
      }]
    },
    options: { responsive:true, plugins:{legend:{display:false}},
      scales:{ y:{beginAtZero:true, ticks:{ callback: v => "Rs."+v }} } }
  });
}

function buildDonutChart(data) {
  const ctx = document.getElementById("donutChart");
  if (!ctx) return;
  if (donutChart) donutChart.destroy();
  donutChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(data),
      datasets: [{ data: Object.values(data), backgroundColor: COLORS, borderWidth:0 }]
    },
    options: { plugins:{ legend:{ position:"bottom" } }, cutout:"60%" }
  });
}

function buildQtyChart(products) {
  const ctx = document.getElementById("qtyChart");
  if (!ctx) return;
  if (qtyChart) qtyChart.destroy();
  qtyChart = new Chart(ctx, {
    type: "polarArea",
    data: {
      labels: products.map(p => p.product),
      datasets: [{ data: products.map(p => p.qty), backgroundColor: COLORS }]
    },
    options: { plugins:{ legend:{ position:"bottom" } } }
  });
}

// ── Orders Table ─────────────────────────────────────────────
async function loadOrders() {
  const search = (document.getElementById("searchInput")?.value || "").trim();
  const status = document.getElementById("statusFilter")?.value || "";
  let url = `${API}/api/orders`;
  const params = [];
  if (search) params.push("search=" + encodeURIComponent(search));
  if (status) params.push("status=" + encodeURIComponent(status));
  if (params.length) url += "?" + params.join("&");

  try {
    const res    = await fetch(url);
    const orders = await res.json();
    const tbody  = document.getElementById("ordersBody");
    tbody.innerHTML = "";

    if (!orders.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#6b7280;padding:32px">No orders found.</td></tr>`;
      return;
    }

    orders.forEach(o => {
      const badge = statusBadge(o.status);
      tbody.innerHTML += `
        <tr>
          <td><strong>${o.order_id}</strong></td>
          <td>${o.name}</td>
          <td>${o.phone}</td>
          <td>${o.product}</td>
          <td>${o.quantity}</td>
          <td>Rs.${o.total}</td>
          <td>${badge}</td>
          <td>${o.created_at.slice(0,16)}</td>
          <td>
            <select class="status-select" onchange="updateStatus('${o.order_id}', this.value)">
              <option value="">Update</option>
              <option>Pending</option>
              <option>Preparing</option>
              <option>Out for Delivery</option>
              <option>Delivered</option>
              <option>Cancelled</option>
            </select>
          </td>
        </tr>`;
    });
  } catch (e) {
    console.error("Orders load failed:", e);
  }
}

function statusBadge(status) {
  const map = {
    "Pending":         "badge-pending",
    "Preparing":       "badge-preparing",
    "Out for Delivery":"badge-delivery",
    "Delivered":       "badge-delivered",
    "Cancelled":       "badge-cancelled",
  };
  return `<span class="badge ${map[status] || ''}">${status}</span>`;
}

async function updateStatus(orderId, status) {
  if (!status) return;
  try {
    const res = await fetch(`${API}/api/order/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId, status }),
    });
    const data = await res.json();
    if (data.message) { loadOrders(); loadAnalytics(); }
    else alert("Update failed.");
  } catch (e) { alert("Error updating status."); }
}

// ── Load all on page start ───────────────────────────────────
function loadAll() {
  loadAnalytics();
}
loadAll();
