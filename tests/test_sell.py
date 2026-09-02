import pytest

from shop import forms
from shop.db import get_db

# Kitchen is category id 2 in the seed.
VALID = {
    "name": "Oak Bottle Opener",
    "category": "2",
    "price": "12.50",
    "stock": "7",
    "summary": "Turned oak handle with a stainless lever.",
    "description": "Turned from a single oak offcut and finished with beeswax. "
    "The lever is pressed stainless steel and pops a crown cap without "
    "chewing the bottle neck.",
    "sku": "",
    "image": "",
}

CUSTOMER = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "address": "12 Analytical Way",
    "city": "London",
    "postcode": "NW1 4RY",
    "country": "United Kingdom",
}

SEEDED_PRODUCTS = 10


def count_products(app):
    with app.app_context():
        return get_db().execute("SELECT COUNT(*) c FROM products").fetchone()["c"]


def fetch(app, slug):
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM products WHERE slug = ?", (slug,)
        ).fetchone()


# Unit tests — no request context needed.


@pytest.mark.parametrize(
    "raw,cents", [("12.50", 1250), ("0", 0), ("9", 900), ("3.5", 350), ("0.09", 9)]
)
def test_parse_price_dollars_accepts_decimal_dollars(raw, cents):
    assert forms.parse_price_dollars(raw) == cents


@pytest.mark.parametrize("raw", ["-1", "abc", "1.999", "", " ", "1.", "+1", "1,50"])
def test_parse_price_dollars_rejects_bad_input(raw):
    with pytest.raises(forms.Invalid):
        forms.parse_price_dollars(raw)


@pytest.mark.parametrize("raw,stock", [("0", 0), ("7", 7), ("9999", 9999)])
def test_parse_stock_accepts_whole_numbers(raw, stock):
    assert forms.parse_stock(raw) == stock


@pytest.mark.parametrize("raw", ["", "-1", "10000", "1.5", "abc"])
def test_parse_stock_rejects_bad_input(raw):
    with pytest.raises(forms.Invalid):
        forms.parse_stock(raw)


@pytest.mark.parametrize(
    "name,slug",
    [
        ("Ceramic Pen Cup", "ceramic-pen-cup"),
        ("Cast Iron Skillet 26 cm", "cast-iron-skillet-26-cm"),
        ("  Café Crème!  ", "cafe-creme"),
        ("Pour-Over Kettle", "pour-over-kettle"),
        ("???", ""),
    ],
)
def test_slug_base(name, slug):
    assert forms.slug_base(name) == slug


@pytest.mark.parametrize(
    "name,code",
    [
        ("Ceramic Mug", "CM"),
        ("Oak Bottle Opener", "OB"),
        ("Trowel", "TR"),
        ("X", "XX"),
        ("", "XX"),
    ],
)
def test_default_image_uses_initials(name, code):
    assert forms.default_image(name) == code


# The form itself.


def test_form_renders_with_every_seeded_category(client):
    response = client.get("/sell/new")
    assert response.status_code == 200
    for name in (b"Desk", b"Kitchen", b"Outdoor"):
        assert name in response.data


def test_nav_links_to_the_form(client):
    assert b"List an item" in client.get("/").data


def test_valid_post_creates_the_product(app, client):
    response = client.post("/sell/new", data=VALID)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/products/oak-bottle-opener")
    assert count_products(app) == SEEDED_PRODUCTS + 1

    row = fetch(app, "oak-bottle-opener")
    assert row["name"] == "Oak Bottle Opener"
    assert row["price_cents"] == 1250
    assert row["stock"] == 7
    assert row["category_id"] == 2
    assert row["sku"] == "OAK-001"  # generated from the name
    assert row["image"] == "OB"  # initials
    assert row["origin_id"] is None


def test_new_product_is_confirmed_and_browsable(client):
    response = client.post("/sell/new", data=VALID, follow_redirects=True)
    assert response.status_code == 200
    assert b"Listed Oak Bottle Opener." in response.data
    assert b"Turned from a single oak offcut" in response.data

    assert b"Oak Bottle Opener" in client.get("/").data
    slugs = [p["slug"] for p in client.get("/api/products").get_json()["products"]]
    assert "oak-bottle-opener" in slugs


def test_new_product_can_be_bought(app, client):
    client.post("/sell/new", data=VALID)
    client.post("/cart/add", data={"slug": "oak-bottle-opener", "quantity": 2})
    assert b"Oak Bottle Opener" in client.get("/cart/").data

    response = client.post("/checkout", data=CUSTOMER, follow_redirects=True)
    assert response.status_code == 200
    assert b"Oak Bottle Opener" in response.data

    with app.app_context():
        item = get_db().execute("SELECT * FROM order_items").fetchone()
        assert item["sku"] == "OAK-001"
        assert item["quantity"] == 2
        assert item["unit_cents"] == 1250
        stock = fetch(app, "oak-bottle-opener")["stock"]
    assert stock == 5


def test_free_items_are_allowed(app, client):
    client.post("/sell/new", data={**VALID, "price": "0"})
    assert fetch(app, "oak-bottle-opener")["price_cents"] == 0


def test_supplied_sku_and_image_are_normalized(app, client):
    client.post("/sell/new", data={**VALID, "sku": "opn-42", "image": "bo"})
    row = fetch(app, "oak-bottle-opener")
    assert row["sku"] == "OPN-42"
    assert row["image"] == "BO"


@pytest.mark.parametrize("price", ["-1", "abc", "1.999", ""])
def test_bad_prices_are_rejected(app, client, price):
    response = client.post("/sell/new", data={**VALID, "price": price})
    assert response.status_code == 400
    assert b"Oak Bottle Opener" in response.data  # submitted values preserved
    if price:
        assert price.encode() in response.data
    assert count_products(app) == SEEDED_PRODUCTS


@pytest.mark.parametrize("stock", ["", "-1", "10000", "1.5", "abc"])
def test_bad_stock_is_rejected(app, client, stock):
    response = client.post("/sell/new", data={**VALID, "stock": stock})
    assert response.status_code == 400
    assert b"whole number between 0 and 9999" in response.data
    assert count_products(app) == SEEDED_PRODUCTS


@pytest.mark.parametrize(
    "field", ["name", "category", "price", "stock", "summary", "description"]
)
def test_required_fields_are_reported(app, client, field):
    response = client.post("/sell/new", data={**VALID, field: ""})
    assert response.status_code == 400
    assert f'id="{field}"'.encode() in response.data
    assert b"required" in response.data or b"Choose one of the listed" in response.data
    assert count_products(app) == SEEDED_PRODUCTS


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("name", "A", b"Use between 2 and 120 characters."),
        ("name", "A" * 121, b"Use between 2 and 120 characters."),
        ("summary", "s" * 201, b"Keep the summary under 200 characters."),
        ("description", "d" * 4001, b"Keep the description under 4000 characters."),
        ("image", "A", b"Use exactly two letters"),
        ("image", "ABC", b"Use exactly two letters"),
        ("image", "12", b"Use exactly two letters"),
        ("sku", "!!", b"Use 2 to 32 letters, digits or dashes."),
    ],
)
def test_field_limits_are_reported(app, client, field, value, message):
    response = client.post("/sell/new", data={**VALID, field: value})
    assert response.status_code == 400
    assert message in response.data
    assert count_products(app) == SEEDED_PRODUCTS


def test_all_errors_are_reported_at_once(client):
    response = client.post(
        "/sell/new",
        data={"name": "", "category": "", "price": "x", "stock": "", "summary": "",
              "description": "", "sku": "", "image": ""},
    )
    assert response.status_code == 400
    body = response.data.decode()
    assert body.count("class=\"error\"") == 6


def test_submitted_category_stays_selected(client):
    response = client.post("/sell/new", data={**VALID, "price": ""})
    assert b'value="2" selected' in response.data


def test_colliding_names_get_distinct_slugs(app, client):
    listing = {**VALID, "name": "Ceramic Pen Cup"}
    first = client.post("/sell/new", data=listing)
    second = client.post("/sell/new", data=listing)

    assert first.headers["Location"].endswith("/products/ceramic-pen-cup-2")
    assert second.headers["Location"].endswith("/products/ceramic-pen-cup-3")
    assert count_products(app) == SEEDED_PRODUCTS + 2
    assert client.get("/products/ceramic-pen-cup-3").status_code == 200


@pytest.mark.parametrize("category", ["9999", "abc", "0"])
def test_unknown_category_is_rejected(app, client, category):
    response = client.post("/sell/new", data={**VALID, "category": category})
    assert response.status_code == 400
    assert b"Choose one of the listed categories." in response.data
    assert count_products(app) == SEEDED_PRODUCTS


def test_duplicate_sku_is_a_field_error(app, client):
    response = client.post("/sell/new", data={**VALID, "sku": "DSK-001"})
    assert response.status_code == 400
    assert b"That SKU is already taken." in response.data
    assert count_products(app) == SEEDED_PRODUCTS


def test_generated_skus_do_not_collide(app, client):
    client.post("/sell/new", data={**VALID, "name": "Oakum Rope"})
    client.post("/sell/new", data={**VALID, "name": "Oaken Bucket"})
    assert fetch(app, "oakum-rope")["sku"] == "OAK-001"
    assert fetch(app, "oaken-bucket")["sku"] == "OAK-002"
