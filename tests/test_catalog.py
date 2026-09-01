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


def test_product_detail(client):
    response = client.get("/products/brass-desk-lamp")
    assert response.status_code == 200
    assert b"$145.00" in response.data
    assert b"DSK-002" in response.data


def test_missing_product_is_404(client):
    assert client.get("/products/nope").status_code == 404


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


def test_api_invalid_sort_falls_back(client):
    response = client.get("/api/products?sort=bogus")
    assert response.status_code == 200
    assert _slugs(response.get_json()) == _slugs(client.get("/api/products").get_json())


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


def test_sort_preserves_filters_in_links(client):
    body = client.get("/?category=kitchen&sort=price-desc").data
    assert b"sort=price-desc" in body
    assert b"category=kitchen" in body

    body = client.get("/?q=brass&sort=price-asc").data
    assert b"sort=price-asc" in body
    assert b'name="sort"' in body
    assert b'value="price-asc"' in body


def test_api_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}
