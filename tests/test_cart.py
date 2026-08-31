def test_add_accumulates_quantity(client):
    client.post("/cart/add", data={"slug": "enamel-camp-mug", "quantity": 2})
    client.post("/cart/add", data={"slug": "enamel-camp-mug", "quantity": 3})
    items = client.get("/api/cart").get_json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 5


def test_cart_page_shows_lines_and_totals(filled_cart):
    response = filled_cart.get("/cart/")
    assert b"Cast Iron Skillet" in response.data
    assert b"Enamel Camp Mug" in response.data
    # 2 x $65.00 + 1 x $19.00
    assert b"$149.00" in response.data


def test_update_quantity(filled_cart):
    product_id = _product_id(filled_cart, "enamel-camp-mug")
    filled_cart.post("/cart/update", data={"product_id": product_id, "quantity": 4})
    assert _quantity(filled_cart, "enamel-camp-mug") == 4


def test_update_to_zero_removes_line(filled_cart):
    product_id = _product_id(filled_cart, "enamel-camp-mug")
    filled_cart.post("/cart/update", data={"product_id": product_id, "quantity": 0})
    assert _quantity(filled_cart, "enamel-camp-mug") is None


def test_quantity_is_clamped(client):
    client.post("/cart/add", data={"slug": "enamel-camp-mug", "quantity": 500})
    assert _quantity(client, "enamel-camp-mug") == 99


def test_remove_line(filled_cart):
    product_id = _product_id(filled_cart, "cast-iron-skillet")
    filled_cart.post("/cart/remove", data={"product_id": product_id})
    assert _quantity(filled_cart, "cast-iron-skillet") is None


def test_free_shipping_over_threshold(client):
    client.post("/cart/add", data={"slug": "enamel-camp-mug", "quantity": 1})
    assert client.get("/api/cart").get_json()["shipping_cents"] == 495

    client.post("/cart/add", data={"slug": "cast-iron-skillet", "quantity": 1})
    assert client.get("/api/cart").get_json()["shipping_cents"] == 0


def test_totals_add_up(filled_cart):
    cart = filled_cart.get("/api/cart").get_json()
    assert cart["subtotal_cents"] == 14900
    assert cart["shipping_cents"] == 0
    assert cart["tax_cents"] == round(14900 * 0.085)
    assert cart["total_cents"] == cart["subtotal_cents"] + cart["tax_cents"]


def test_empty_cart_has_no_shipping_charge(client):
    assert client.get("/api/cart").get_json() == {
        "items": [],
        "subtotal_cents": 0,
        "shipping_cents": 0,
        "tax_cents": 0,
        "total_cents": 0,
    }


def _product_id(client, slug):
    return client.get(f"/api/products/{slug}").get_json()["id"]


def _quantity(client, slug):
    for item in client.get("/api/cart").get_json()["items"]:
        if item["slug"] == slug:
            return item["quantity"]
    return None
