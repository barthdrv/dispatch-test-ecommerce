"""Corner Shop — a small demo storefront built on Flask and SQLite."""
from flask import Flask, render_template

from . import db, views
from .cart import count as cart_count
from .config import Config
from .pricing import money

__version__ = "0.1.0"


def create_app(config=None):
    """Build the app. ``config`` is a mapping of overrides, mainly for tests."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.register(app)
    views.register(app)

    # Available in every template.
    app.jinja_env.globals.update(money=money, cart_count=cart_count)

    @app.errorhandler(404)
    def not_found(_exc):
        return render_template("404.html"), 404

    return app
