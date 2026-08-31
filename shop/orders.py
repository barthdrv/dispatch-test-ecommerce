"""Order placement.

Stock is decremented in the same transaction that writes the order, so two
concurrent checkouts cannot both take the last unit.
"""
import secrets

from .db import get_db


class OutOfStock(Exception):
    def __init__(self, product_name):
        super().__init__(f"{product_name} is no longer available in that quantity")
        self.product_name = product_name


def new_order_number():
    return "ORD-" + secrets.token_hex(4).upper()


def place_order(lines, totals, customer):
    """Persist an order and return its number.

    ``lines`` is the output of :func:`shop.cart.contents`. Raises
    :class:`OutOfStock` if any line exceeds available stock.
    """
    if not lines:
        raise ValueError("cannot place an empty order")

    db = get_db()
    number = new_order_number()
    with db:  # commits on success, rolls back on exception
        cursor = db.execute(
            """
            INSERT INTO orders (
                number, email, name, address, city, postcode, country,
                subtotal_cents, shipping_cents, tax_cents, total_cents
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                number,
                customer["email"],
                customer["name"],
                customer["address"],
                customer["city"],
                customer["postcode"],
                customer["country"],
                totals["subtotal_cents"],
                totals["shipping_cents"],
                totals["tax_cents"],
                totals["total_cents"],
            ),
        )
        order_id = cursor.lastrowid

        for line in lines:
            product = line["product"]
            updated = db.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (line["quantity"], product["id"], line["quantity"]),
            )
            if updated.rowcount == 0:
                raise OutOfStock(product["name"])
            db.execute(
                """
                INSERT INTO order_items (order_id, product_id, name, sku, unit_cents, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    product["id"],
                    product["name"],
                    product["sku"],
                    product["price_cents"],
                    line["quantity"],
                ),
            )
    return number


def get_order(number):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE number = ?", (number,)).fetchone()
    if order is None:
        return None, []
    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY name", (order["id"],)
    ).fetchall()
    return order, items
