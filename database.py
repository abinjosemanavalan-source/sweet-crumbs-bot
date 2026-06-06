import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "bakery.db"

def get_db():
    """Return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return rows as dicts
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            phone       TEXT NOT NULL,
            address     TEXT NOT NULL,
            product     TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            price       REAL NOT NULL,
            subtotal    REAL NOT NULL,
            delivery    REAL NOT NULL DEFAULT 30,
            total       REAL NOT NULL,
            status      TEXT NOT NULL DEFAULT 'Pending',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            message     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database ready.")

# ---- Order helpers ----

def save_order(order_id, name, phone, address, product, quantity, price):
    subtotal = price * quantity
    delivery = 30
    total = subtotal + delivery
    conn = get_db()
    conn.execute("""
        INSERT INTO orders (order_id, name, phone, address, product, quantity, price, subtotal, delivery, total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, name, phone, address, product, quantity, price, subtotal, delivery, total))
    conn.commit()
    conn.close()
    return total

def get_all_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_order_by_id(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_order_status(order_id, status):
    valid = ["Pending", "Preparing", "Out for Delivery", "Delivered", "Cancelled"]
    if status not in valid:
        return False
    conn = get_db()
    conn.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return True

def can_cancel(order):
    """Return True if the order is still within the 1-hour cancellation window."""
    try:
        placed_at = datetime.strptime(order["created_at"][:19], "%Y-%m-%d %H:%M:%S")
        return datetime.utcnow() <= placed_at + timedelta(hours=1)
    except Exception:
        return False

def cancel_order(order_id):
    """
    Cancel an order if:
    - It exists
    - It hasn't been delivered
    - It was placed within the last 1 hour
    Returns (success: bool, message: str)
    """
    order = get_order_by_id(order_id)
    if not order:
        return False, "Order not found."
    if order["status"] == "Delivered":
        return False, "Order has already been delivered and cannot be cancelled."
    if order["status"] == "Cancelled":
        return False, "Order is already cancelled."
    if not can_cancel(order):
        return False, "Cancellation window has passed. Orders can only be cancelled within 1 hour of placing."
    conn = get_db()
    conn.execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    return True, f"Order {order_id} has been successfully cancelled."

def get_analytics():
    conn = get_db()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_revenue = conn.execute("SELECT SUM(total) FROM orders").fetchone()[0] or 0
    top_product = conn.execute("""
        SELECT product, SUM(quantity) as qty FROM orders
        GROUP BY product ORDER BY qty DESC LIMIT 1
    """).fetchone()
    today_orders = conn.execute("""
        SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')
    """).fetchone()[0]
    weekly_rev = conn.execute("""
        SELECT SUM(total) FROM orders WHERE created_at >= DATE('now', '-7 days')
    """).fetchone()[0] or 0
    monthly_rev = conn.execute("""
        SELECT SUM(total) FROM orders WHERE created_at >= DATE('now', '-30 days')
    """).fetchone()[0] or 0

    # Status breakdown for chart
    status_rows = conn.execute("""
        SELECT status, COUNT(*) as count FROM orders GROUP BY status
    """).fetchall()
    status_breakdown = {r["status"]: r["count"] for r in status_rows}

    # Top 5 products
    top_products = conn.execute("""
        SELECT product, SUM(quantity) as qty, SUM(total) as revenue
        FROM orders GROUP BY product ORDER BY qty DESC LIMIT 5
    """).fetchall()

    conn.close()
    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "top_product": top_product["product"] if top_product else "N/A",
        "today_orders": today_orders,
        "weekly_revenue": round(weekly_rev, 2),
        "monthly_revenue": round(monthly_rev, 2),
        "status_breakdown": status_breakdown,
        "top_products": [dict(r) for r in top_products],
    }

# ---- Chat history helpers ----

def save_message(session_id, role, message):
    conn = get_db()
    conn.execute("INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)",
                 (session_id, role, message))
    conn.commit()
    conn.close()

def get_history(session_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT role, message FROM chat_history
        WHERE session_id = ? ORDER BY created_at ASC
    """, (session_id,)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["message"]} for r in rows]
