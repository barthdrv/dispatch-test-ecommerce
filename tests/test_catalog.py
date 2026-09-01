import sqlite3

from shop import create_app
from shop.db import get_db, upgrade_db


def test_index_lists_products(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Walnut Monitor Stand" in response.data


def test_filter_by_category(client):
    response = client.get("/?category=kitchen")
    assert b"Cast Iron Skillet" in response.data
    assert b"Walnut Monitor Stand" not in response.data


def test_search_matches_name_and_summary(client):
    assert b"Brass Desk Lamp" in client.get("/?q=brass").data
    assert b"Linen Tea Towels" in client.get("/?q=stonewashed").data
    assert b"Nothing matched" in client.get("/?q=zzzz").data


def test_origin_filter_combines_with_category_and_search(client):
    body = client.get("/?origin=US&category=desk&q=walnut").data
    assert b"Walnut Monitor Stand" in body
    assert b"Cast Iron Skillet" not in body
    assert b"Brass Desk Lamp" not in body


def test_product_detail(client):
    response = client.get("/products/brass-desk-lamp")
    assert response.status_code == 200
    assert b"$145.00" in response.data
    assert b"DSK-002" in response.data


def test_missing_product_is_404(client):
    assert client.get("/products/nope").status_code == 404


def test_product_detail_shows_origin_only_when_known(client):
    assert b"Made in" in client.get("/products/walnut-monitor-stand").data
    assert b"United States" in client.get("/products/walnut-monitor-stand").data
    assert b"Made in" not in client.get("/products/folding-trowel").data


def test_sold_out_product_cannot_be_added(client):
    response = client.post(
        "/cart/add", data={"slug": "ceramic-pen-cup"}, follow_redirects=True
    )
    assert b"out of stock" in response.data
    assert client.get("/api/cart").get_json()["items"] == []


def test_api_products(client):
    payload = client.get("/api/products?category=outdoor").get_json()
    assert payload["count"] == 3
    assert {p["slug"] for p in payload["products"]} == {
        "enamel-camp-mug",
        "waxed-rain-shell",
        "folding-trowel",
    }


def _slugs(payload):
    return [p["slug"] for p in payload["products"]]


def _prices(payload):
    return [p["price_cents"] for p in payload["products"]]


def test_api_origin_filter_and_payload(client):
    payload = client.get("/api/products?origin=US").get_json()
    assert payload["count"] == 2
    assert {p["slug"] for p in payload["products"]} == {
        "walnut-monitor-stand",
        "cast-iron-skillet",
    }
    assert all(p["origin"]["code"] == "US" for p in payload["products"])
    assert all("origin" in p for p in client.get("/api/products").get_json()["products"])


def test_api_origin_and_sort_matches_index(client):
    products = client.get(
        "/api/products?origin=US&sort=price-desc"
    ).get_json()["products"]
    body = client.get("/?origin=US&sort=price-desc").data.decode()
    positions = [body.index(product["name"]) for product in products]
    prices = [product["price_cents"] for product in products]
    assert positions == sorted(positions)
    assert prices == sorted(prices, reverse=True)


def test_api_sort_origin_groups_and_puts_unknown_last(client):
    products = client.get("/api/products?sort=origin").get_json()["products"]
    keys = [
        (
            product["origin"] is None,
            product["origin"]["region"] if product["origin"] else "",
            product["origin"]["name"] if product["origin"] else "",
            product["name"],
        )
        for product in products
    ]
    assert keys == sorted(keys)
    assert products[-1]["origin"] is None


def test_api_sort_price_asc(client):
    payload = client.get("/api/products?sort=price-asc").get_json()
    prices = _prices(payload)
    assert prices == sorted(prices)
    assert payload["count"] == client.get("/api/products").get_json()["count"]


def test_api_sort_price_desc(client):
    payload = client.get("/api/products?sort=price-desc").get_json()
    prices = _prices(payload)
    assert prices == sorted(prices, reverse=True)
    assert payload["count"] == client.get("/api/products").get_json()["count"]


def test_api_sort_ties_broken_by_name(client):
    payload = client.get("/api/products?sort=price-asc").get_json()
    groups = {}
    for product in payload["products"]:
        groups.setdefault(product["price_cents"], []).append(product["name"])
    for names in groups.values():
        assert names == sorted(names)


def test_api_category_and_sort(client):
    payload = client.get("/api/products?category=kitchen&sort=price-desc").get_json()
    assert payload["products"]
    assert {p["category"] for p in payload["products"]} == {"kitchen"}
    prices = _prices(payload)
    assert prices == sorted(prices, reverse=True)


def test_api_invalid_sort_and_origin_fall_back(client):
    expected = _slugs(client.get("/api/products").get_json())
    for query in (
        "sort=bogus",
        "sort=name%29%3BDROP%20TABLE%20products--",
        "origin=ZZ",
        "origin=US%27%20OR%201%3D1--",
    ):
        response = client.get(f"/api/products?{query}")
        assert response.status_code == 200
        assert _slugs(response.get_json()) == expected


def test_index_sort_matches_api(client):
    for sort in ("price-asc", "price-desc"):
        expected = [
            p["name"]
            for p in client.get(f"/api/products?sort={sort}").get_json()["products"]
        ]
        body = client.get(f"/?sort={sort}").data.decode()
        positions = [body.index(name) for name in expected]
        assert positions == sorted(positions)


def test_index_invalid_sort_is_ok(client):
    response = client.get("/?sort=bogus")
    assert response.status_code == 200
    assert b"Walnut Monitor Stand" in response.data


def test_filter_state_round_trips_in_links_and_sort_form(client):
    body = client.get("/?category=desk&origin=US&q=walnut&sort=price-desc").data
    assert b"category=desk" in body
    assert b"origin=US" in body
    assert b"q=walnut" in body
    assert b"sort=price-desc" in body
    assert (
        b'href="/?category=kitchen&amp;q=walnut&amp;origin=US&amp;sort=price-desc"'
        in body
    )
    assert b'name="sort"' in body
    assert b'value="price-desc" selected' in body
    assert b'name="origin" value="US"' in body


def test_search_preserves_active_filters(client):
    body = client.get("/?category=desk&origin=US&sort=price-desc").data
    search = body.split(b'<form class="search"', 1)[1].split(b"</form>", 1)[0]
    assert b'name="category" value="desk"' in search
    assert b'name="origin" value="US"' in search
    assert b'name="sort" value="price-desc"' in search


def test_api_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_upgrade_db_preserves_existing_data_and_backfills_origins(tmp_path):
    database = tmp_path / "legacy.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE products (id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL);
            INSERT INTO products (sku) VALUES ('DSK-001');
            CREATE TABLE orders (id INTEGER PRIMARY KEY, number TEXT NOT NULL);
            INSERT INTO orders (number) VALUES ('CS-EXISTING');
            """
        )

    app = create_app({"TESTING": True, "DATABASE": str(database)})
    with app.app_context():
        upgrade_db()
        upgrade_db()
        db = get_db()
        product = db.execute(
            """
            SELECT o.code
            FROM products p
            LEFT JOIN origins o ON o.id = p.origin_id
            WHERE p.sku = 'DSK-001'
            """
        ).fetchone()
        assert product["code"] == "US"
        assert db.execute("SELECT number FROM orders").fetchone()["number"] == "CS-EXISTING"
