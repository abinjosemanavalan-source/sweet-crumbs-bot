import os
import uuid
import random
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from database import init_db, save_order, get_all_orders, get_order_by_id, \
                     update_order_status, get_analytics, save_message, get_history, \
                     cancel_order, can_cancel

# ---- Setup ----
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ---- Bakery Data ----
MENU = {
    "Chocolate Cake": 500,
    "Black Forest":   550,
    "Red Velvet":     650,
    "Vanilla Cake":   450,
}
DELIVERY_CHARGE = 30

# Counter stored simply in memory (resets on restart; DB is source of truth)
def next_order_id():
    from database import get_db
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    return f"SCB{1001 + count}"

# ---- FAQ Knowledge Base ----
FAQ = {
    "opening hours": "We are open **9:00 AM – 6:00 PM**, every day. 🕘",
    "delivery charge": f"Delivery charge is **Rs.{DELIVERY_CHARGE}** for all orders.",
    "payment": "We accept **Cash** and **Online Payment**. 💳",
    "cancel": "Orders can be cancelled within **1 hour** of placing. After that, cancellation is not possible. To cancel, type: **cancel SCB####**",
    "contact": "📞 Call us: **+91 98765 43210** | 📧 hello@sweetcrumbs.com",
    "location": "📍 We are located at **Main Street, Your City**.",
    "menu": "\n".join([f"- {k}: Rs.{v}" for k, v in MENU.items()]),
}

def faq_response(message: str):
    """Return an instant FAQ answer if the message matches, else None."""
    msg = message.lower()
    if any(k in msg for k in ["hour", "open", "time"]):
        return FAQ["opening hours"]
    if any(k in msg for k in ["delivery charge", "delivery fee", "charge", "fee"]):
        return FAQ["delivery charge"]
    if any(k in msg for k in ["payment", "pay", "cash", "online"]):
        return FAQ["payment"]
    if any(k in msg for k in ["cancel", "cancell"]) and "scb" not in msg:
        return FAQ["cancel"]
    if any(k in msg for k in ["contact", "phone", "email", "number"]):
        return FAQ["contact"]
    if any(k in msg for k in ["location", "address", "where"]):
        return FAQ["location"]
    if any(k in msg for k in ["menu", "item", "product", "cake", "list"]):
        return f"**Our Menu:**\n{FAQ['menu']}"
    return None

# ---- System Prompt ----
SYSTEM_PROMPT = f"""
You are a helpful assistant for Sweet Crumbs Bakery.

Menu:
{chr(10).join([f'- {k}: Rs.{v}' for k, v in MENU.items()])}

Rules:
1. Answer politely and professionally.
2. Keep replies SHORT and SIMPLE. Use bullet points.
3. Delivery charge: Rs.{DELIVERY_CHARGE}.
4. Payment: Cash and Online Payment only.
5. Hours: 9:00 AM – 6:00 PM.
6. No discounts or price negotiation.
7. For orders, collect: Name, Phone, Address. Then confirm with an invoice.
8. Only recommend items from the menu above.
9. If asked to track an order, tell the customer to type: track SCB####
10. If a customer wants to cancel, tell them to type: cancel SCB####
11. Cancellation is only allowed within 1 hour of placing the order.

When confirming an order, format it exactly like this:
---
ORDER CONFIRMED ✅
Order ID: SCB####
Product: [name] x[qty]
Subtotal: Rs.[amount]
Delivery: Rs.30
Grand Total: Rs.[total]
---
Estimated delivery time: 2 hours.
"""

# ------------------------------------------------------------------ #
#                           ROUTES                                     #
# ------------------------------------------------------------------ #

@app.route("/")
def home():
    return send_from_directory("templates", "index.html")

@app.route("/admin")
def admin():
    return send_from_directory("templates", "admin.html")

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)

# -- Chat API --
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    session_id   = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # 1. Check FAQ for instant reply
    fast = faq_response(user_message)
    if fast:
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", fast)
        return jsonify({"reply": fast})

    # 2. Check order tracking
    if user_message.lower().startswith("track"):
        parts = user_message.upper().split()
        order_id = next((p for p in parts if p.startswith("SCB")), None)
        if order_id:
            order = get_order_by_id(order_id)
            if order:
                cancellable = can_cancel(order) and order["status"] not in ["Delivered", "Cancelled"]
                cancel_hint = "\n- ✏️ Type `cancel " + order_id + "` to cancel (within 1 hr)" if cancellable else ""
                reply = (
                    f"📦 **Order {order_id}**\n"
                    f"- Status: **{order['status']}**\n"
                    f"- Product: {order['product']} x{order['quantity']}\n"
                    f"- Total: Rs.{order['total']}\n"
                    f"- Placed: {order['created_at'][:16]}"
                    + cancel_hint
                )
            else:
                reply = f"❌ Order **{order_id}** not found. Please check the ID."
            save_message(session_id, "user", user_message)
            save_message(session_id, "assistant", reply)
            return jsonify({"reply": reply})

    # 3. Check order cancellation via chat
    msg_lower = user_message.lower()
    if msg_lower.startswith("cancel"):
        parts = user_message.upper().split()
        order_id = next((p for p in parts if p.startswith("SCB")), None)
        if order_id:
            success, message = cancel_order(order_id)
            icon = "✅" if success else "❌"
            reply = f"{icon} {message}"
            save_message(session_id, "user", user_message)
            save_message(session_id, "assistant", reply)
            return jsonify({"reply": reply})

    # 3. AI response with history
    history = get_history(session_id)[-10:]  # last 10 turns for context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    save_message(session_id, "user", user_message)
    save_message(session_id, "assistant", reply)
    return jsonify({"reply": reply})

# -- Order API --
@app.route("/api/order", methods=["POST"])
def place_order():
    data = request.json or {}
    required = ["name", "phone", "address", "product", "quantity"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    product  = data["product"].strip().title()
    quantity = int(data["quantity"])

    # Find product (case-insensitive partial match)
    price = None
    matched_product = product
    for k, v in MENU.items():
        if k.lower() == product.lower() or product.lower() in k.lower():
            price = v
            matched_product = k
            break

    if price is None:
        return jsonify({"error": "Product not found in menu"}), 404

    order_id = next_order_id()
    total = save_order(order_id, data["name"], data["phone"], data["address"],
                       matched_product, quantity, price)

    subtotal = price * quantity
    return jsonify({
        "order_id":  order_id,
        "product":   matched_product,
        "quantity":  quantity,
        "price":     price,
        "subtotal":  subtotal,
        "delivery":  DELIVERY_CHARGE,
        "total":     total,
        "status":    "Pending",
    }), 201

@app.route("/api/orders", methods=["GET"])
def list_orders():
    status = request.args.get("status")
    search = request.args.get("search", "").lower()
    orders = get_all_orders()
    if status:
        orders = [o for o in orders if o["status"] == status]
    if search:
        orders = [o for o in orders if search in o["order_id"].lower()
                  or search in o["name"].lower()
                  or search in o["phone"].lower()]
    return jsonify(orders)

@app.route("/api/order/<order_id>", methods=["GET"])
def get_order(order_id):
    order = get_order_by_id(order_id.upper())
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)

@app.route("/api/order/status", methods=["PUT"])
def update_status():
    data = request.json or {}
    order_id = data.get("order_id", "").upper()
    status   = data.get("status", "")
    if not update_order_status(order_id, status):
        return jsonify({"error": "Invalid order ID or status"}), 400
    return jsonify({"message": f"Order {order_id} updated to '{status}'"})

@app.route("/api/order/cancel", methods=["POST"])
def api_cancel_order():
    data = request.json or {}
    order_id = data.get("order_id", "").upper()
    if not order_id:
        return jsonify({"error": "order_id is required"}), 400
    success, message = cancel_order(order_id)
    if success:
        return jsonify({"message": message})
    return jsonify({"error": message}), 400

@app.route("/api/analytics", methods=["GET"])
def analytics():
    return jsonify(get_analytics())

@app.route("/api/menu", methods=["GET"])
def menu():
    return jsonify(MENU)

# ---- Start ----
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
