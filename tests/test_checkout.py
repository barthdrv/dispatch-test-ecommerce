import pytest

from shop.db import get_db

VALID = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "address": "12 Analytical Way",
    "city": "London",
    "postcode": "NW1 4RY",
    "country": "United Kingdom",
}


def test_checkout_page_requires_a_cart(client):
    response = client.get("/checkout", follow_redirects=True)
    assert b"Your cart is empty" in response.data


def test_checkout_page_shows_summary(filled_cart):
    response = filled_cart.get("/checkout")
    assert response.status_code == 200
    assert b"Cast Iron Skillet" in response.data


def test_missing_fields_are_reported(filled_cart):
    response = filled_cart.post("/checkout", data={**VALID, "city": ""})
    assert response.status_code == 200
    assert b"This field is required." in response.data


def test_invalid_email_is_reported(filled_cart):
    response = filled_cart.post("/checkout", data={**VALID, "email": "not-an-email"})
    assert b"Enter a valid email address." in response.data


def test_successful_order(app, filled_cart):
    response = filled_cart.post("/checkout", data=VALID, follow_redirects=True)
    assert response.status_code == 200
    assert b"Thanks, Ada." in response.data
    assert b"Cast Iron Skillet" in response.data

    with app.app_context():
        order = get_db().execute("SELECT * FROM orders").fetchone()
        assert order["email"] == "ada@example.com"
        assert order["subtotal_cents"] == 14900
        assert order["total_cents"] == 14900 + round(14900 * 0.085)

        items = get_db().execute("SELECT * FROM order_items").fetchall()
        assert {item["sku"]: item["quantity"] for item in items} == {
            "KTC-001": 2,
            "OUT-001": 1,
        }


def test_order_decrements_stock(app, filled_cart):
    filled_cart.post("/checkout", data=VALID)
    with app.app_context():
        stock = get_db().execute(
            "SELECT stock FROM products WHERE sku = 'KTC-001'"
        ).fetchone()["stock"]
    assert stock == 31  # seeded at 33, ordered 2


def test_cart_is_emptied_after_ordering(filled_cart):
    filled_cart.post("/checkout", data=VALID)
    assert filled_cart.get("/api/cart").get_json()["items"] == []


def test_checkout_blocked_when_stock_dropped(app, client):
    client.post("/cart/add", data={"slug": "waxed-rain-shell", "quantity": 6})
    with app.app_context():
        db = get_db()
        db.execute("UPDATE products SET stock = 2 WHERE sku = 'OUT-002'")
        db.commit()

    response = client.post("/checkout", data=VALID, follow_redirects=True)
    assert b"Not enough stock" in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) c FROM orders").fetchone()["c"] == 0


def test_unknown_order_is_404(client):
    assert client.get("/orders/ORD-NOPE").status_code == 404


def test_empty_order_is_rejected(app):
    from shop.orders import place_order

    with app.app_context():
        with pytest.raises(ValueError):
            place_order([], {}, VALID)
