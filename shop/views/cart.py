from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import cart as cart_service
from ..catalog import get_product

bp = Blueprint("cart", __name__, url_prefix="/cart")


@bp.get("/")
def show():
    lines, totals = cart_service.contents()
    return render_template("cart.html", lines=lines, totals=totals)


@bp.post("/add")
def add():
    slug = request.form.get("slug", "")
    product = get_product(slug)
    if product is None:
        flash("That product no longer exists.", "error")
        return redirect(url_for("catalog.index"))
    if product["stock"] == 0:
        flash(f"{product['name']} is out of stock.", "error")
        return redirect(url_for("catalog.product", slug=slug))

    quantity = _int(request.form.get("quantity"), default=1)
    cart_service.add(product["id"], quantity)
    flash(f"Added {product['name']} to your cart.", "success")
    return redirect(request.form.get("next") or url_for("cart.show"))


@bp.post("/update")
def update():
    product_id = _int(request.form.get("product_id"), default=0)
    if product_id:
        cart_service.set_quantity(product_id, _int(request.form.get("quantity"), 0))
    return redirect(url_for("cart.show"))


@bp.post("/remove")
def remove():
    product_id = _int(request.form.get("product_id"), default=0)
    if product_id:
        cart_service.remove(product_id)
    return redirect(url_for("cart.show"))


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
