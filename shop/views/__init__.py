from . import api, cart, catalog, checkout, sell


def register(app):
    app.register_blueprint(catalog.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(checkout.bp)
    app.register_blueprint(sell.bp)
    app.register_blueprint(api.bp)
