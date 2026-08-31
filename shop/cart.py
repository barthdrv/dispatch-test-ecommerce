"""Session-backed shopping cart.

The cart lives in the signed session cookie as {product_id: quantity}. Session
keys are strings once the cookie round-trips, so ids are normalised on the way
in and out.
"""
from flask import session

from .catalog import get_products_by_id
from .pricing import totals_for

SESSION_KEY = "cart"
MAX_QUANTITY = 99


def _raw():
    return session.setdefault(SESSION_KEY, {})


def _save(cart):
    session[SESSION_KEY] = cart
    session.modified = True


def add(product_id, quantity=1):
    """Add to the running quantity for a product. Returns the new quantity."""
    cart = _raw()
    key = str(product_id)
    new_quantity = clamp(cart.get(key, 0) + quantity)
    if new_quantity == 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity
    _save(cart)
    return new_quantity


def set_quantity(product_id, quantity):
    """Set an absolute quantity. Zero removes the line."""
    cart = _raw()
    key = str(product_id)
    quantity = clamp(quantity)
    if quantity == 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    _save(cart)
    return quantity


def remove(product_id):
    cart = _raw()
    cart.pop(str(product_id), None)
    _save(cart)


def clear():
    session.pop(SESSION_KEY, None)
    session.modified = True


def clamp(quantity):
    return max(0, min(int(quantity), MAX_QUANTITY))


def count():
    return sum(_raw().values())


def contents():
    """Resolve the cart against the catalog.

    Returns (lines, totals). Products that have been deleted from the catalog
    are dropped from the session rather than raising.
    """
    cart = _raw()
    products = get_products_by_id([int(pid) for pid in cart])

    lines, stale = [], False
    for key, quantity in list(cart.items()):
        product = products.get(int(key))
        if product is None:
            cart.pop(key)
            stale = True
            continue
        lines.append(
            {
                "product": product,
                "quantity": quantity,
                "line_cents": product["price_cents"] * quantity,
                "in_stock": product["stock"] >= quantity,
            }
        )
    if stale:
        _save(cart)

    lines.sort(key=lambda line: line["product"]["name"])
    subtotal = sum(line["line_cents"] for line in lines)
    return lines, totals_for(subtotal)
