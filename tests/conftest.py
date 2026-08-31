import pytest

from shop import create_app
from shop.db import init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "test.sqlite")})
    with app.app_context():
        init_db()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def filled_cart(client):
    """A client with two skillets and one camp mug in the cart."""
    client.post("/cart/add", data={"slug": "cast-iron-skillet", "quantity": 2})
    client.post("/cart/add", data={"slug": "enamel-camp-mug", "quantity": 1})
    return client
