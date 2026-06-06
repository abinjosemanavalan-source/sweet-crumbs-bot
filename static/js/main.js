/* ============================================================
   SWEET CRUMBS BAKERY — MAIN FRONTEND JAVASCRIPT
   ============================================================ */

const API = "http://127.0.0.1:5000";
const SESSION_ID = "session_" + Math.random().toString(36).slice(2, 10);

// ── Cake images (Unsplash) ──────────────────────────────────
const CAKE_IMAGES = {
  "Chocolate Cake": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400",
  "Black Forest":   "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400",
  "Red Velvet":     "https://images.unsplash.com/photo-1614707267537-b85aaf00c4b7?w=400",
  "Vanilla Cake":   "https://images.unsplash.com/photo-1621303837174-89787a7d4729?w=400",
};

// ── Navbar scroll ───────────────────────────────────────────
window.addEventListener("scroll", () => {
  document.getElementById("navbar").classList.toggle("scrolled", window.scrollY > 50);
});

// ── Load menu cards ─────────────────────────────────────────
async function loadMenu() {
  try {
    const res = await fetch(`${API}/api/menu`);
    const menu = await res.json();
    const grid = document.getElementById("menuGrid");
    grid.innerHTML = "";
    for (const [name, price] of Object.entries(menu)) {
      const img = CAKE_IMAGES[name] || "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400";
      grid.innerHTML += `
        <div class="menu-card">
          <img src="${img}" alt="${name}" loading="lazy">
          <div class="menu-card-body">
            <h3>${name}</h3>
            <p>Freshly baked with premium ingredients.</p>
            <div class="menu-card-footer">
              <span class="price-tag">Rs.${price}</span>
              <button class="order-btn" onclick="openOrderModal('${name}')">Order Now</button>
            </div>
          </div>
        </div>`;
    }
    // populate modal select
    const sel = document.getElementById("orderProduct");
    sel.innerHTML = '<option value="">-- Select Cake --</option>';
    for (const name of Object.keys(menu)) {
      sel.innerHTML += `<option value="${name}">${name}</option>`;
    }
  } catch (e) {
    console.error("Menu load failed:", e);
  }
}

// ── Chatbot ─────────────────────────────────────────────────
const chatToggle   = document.getElementById("chatToggle");
const chatbotWidget= document.getElementById("chatbot");
const chatbox      = document.getElementById("chatbox");
const chatInput    = document.getElementById("chatInput");
const typingIndicator = document.getElementById("typingIndicator");

chatToggle.addEventListener("click", () => {
  document.body.classList.toggle("chat-open");
  chatbotWidget.classList.toggle("open");
});

function currentTime() {
  return new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
}

function addMessage(role, text) {
  const li = document.createElement("li");
  li.classList.add("msg", role === "user" ? "outgoing" : "incoming");

  // Convert **bold** and newlines to HTML
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");

  if (role === "user") {
    li.innerHTML = `<div><div class="bubble"><p>${formatted}</p></div><div class="msg-time">${currentTime()}</div></div>`;
  } else {
    li.innerHTML = `<span class="bot-icon">🤖</span><div><div class="bubble"><p>${formatted}</p></div><div class="msg-time">${currentTime()}</div></div>`;
  }
  chatbox.appendChild(li);
  chatbox.scrollTop = chatbox.scrollHeight;
  return li;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";

  addMessage("user", text);

  // Show typing
  typingIndicator.style.display = "flex";

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: SESSION_ID }),
    });
    const data = await res.json();
    typingIndicator.style.display = "none";
    addMessage("bot", data.reply || data.error || "Sorry, something went wrong.");
  } catch (e) {
    typingIndicator.style.display = "none";
    addMessage("bot", "❌ Could not connect to server.");
  }
}

// Enter key to send
chatInput.addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); sendMessage(); }
});

function quickSend(msg) {
  chatInput.value = msg;
  sendMessage();
}

// ── Order Modal ─────────────────────────────────────────────
function openOrderModal(product) {
  document.getElementById("orderProduct").value = product || "";
  document.getElementById("orderResult").style.display = "none";
  document.getElementById("orderModal").style.display = "flex";
}
function closeModal() {
  document.getElementById("orderModal").style.display = "none";
}

async function submitOrder() {
  const product  = document.getElementById("orderProduct").value;
  const qty      = document.getElementById("orderQty").value;
  const name     = document.getElementById("orderName").value.trim();
  const phone    = document.getElementById("orderPhone").value.trim();
  const address  = document.getElementById("orderAddress").value.trim();

  if (!product || !qty || !name || !phone || !address) {
    alert("Please fill in all fields.");
    return;
  }

  try {
    const res = await fetch(`${API}/api/order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product, quantity: qty, name, phone, address }),
    });
    const data = await res.json();

    if (data.error) { alert("Error: " + data.error); return; }

    const resultDiv = document.getElementById("orderResult");
    resultDiv.style.display = "block";
    resultDiv.innerHTML = `
      <div class="invoice">
        <div class="inv-title">✅ Order Confirmed!</div>
        <div><strong>Order ID:</strong> ${data.order_id}</div>
        <div><strong>${data.product} x${data.quantity}</strong> — Rs.${data.subtotal}</div>
        <div>Delivery Charge — Rs.${data.delivery}</div>
        <div class="inv-total">Grand Total — Rs.${data.total}</div>
        <div style="margin-top:8px;color:#059669;font-size:.85rem">🚚 Estimated delivery: <strong>2 hours</strong></div>
        <div style="margin-top:4px;color:#6b7280;font-size:.8rem">⚠️ You can cancel within 1 hour of placing.</div>
      </div>`;

    // Also send to chat
    chatbotWidget.classList.add("open");
    document.body.classList.add("chat-open");
    addMessage("bot",
      `✅ Order confirmed!\n` +
      `**Order ID:** ${data.order_id}\n` +
      `**${data.product} x${data.quantity}** — Rs.${data.subtotal}\n` +
      `Delivery — Rs.${data.delivery}\n` +
      `**Total — Rs.${data.total}**\n` +
      `🚚 Estimated delivery: **2 hours**\n` +
      `⚠️ Cancel within 1 hour: type \`cancel ${data.order_id}\``
    );
    // Show quick track button in chat
    const li = document.createElement("li");
    li.classList.add("msg", "incoming");
    li.innerHTML = `<span class="bot-icon">🤖</span><div><div class="bubble"><p>Want to track your order?</p><div class="quick-btns"><button onclick="quickSend('track ${data.order_id}')">📦 Track ${data.order_id}</button><button onclick="quickSend('cancel ${data.order_id}')">❌ Cancel Order</button></div></div></div>`;
    const chatbox = document.getElementById("chatbox");
    chatbox.appendChild(li);
    chatbox.scrollTop = chatbox.scrollHeight;
  } catch (e) {
    alert("Failed to place order. Server may be down.");
  }
}

// ── Track Order Modal ────────────────────────────────────────
async function trackOrder() {
  const id = document.getElementById("trackId").value.trim().toUpperCase();
  if (!id) { alert("Enter an Order ID."); return; }

  try {
    const res = await fetch(`${API}/api/order/${id}`);
    const data = await res.json();
    const div = document.getElementById("trackResult");
    div.style.display = "block";

    if (data.error) {
      div.innerHTML = `<p style="color:red">❌ ${data.error}</p>`;
      return;
    }

    const statusColor = { Pending:"#d97706", Preparing:"#2563eb", "Out for Delivery":"#0284c7", Delivered:"#059669" };
    div.innerHTML = `
      <div class="invoice">
        <div class="inv-title" style="color:${statusColor[data.status] || '#333'}">📦 Status: ${data.status}</div>
        <div><strong>Order ID:</strong> ${data.order_id}</div>
        <div>${data.product} x${data.quantity}</div>
        <div class="inv-total">Total — Rs.${data.total}</div>
        <div style="font-size:.8rem;color:#6b7280;margin-top:6px">Placed: ${data.created_at.slice(0,16)}</div>
      </div>`;
  } catch (e) {
    alert("Error fetching order.");
  }
}

// Expose track to global for HTML
window.trackOrderOpen = () => {
  document.getElementById("trackModal").style.display = "flex";
};

// ── Init ─────────────────────────────────────────────────────
loadMenu();
