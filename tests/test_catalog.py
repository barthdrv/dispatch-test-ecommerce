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


def test_api_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}
