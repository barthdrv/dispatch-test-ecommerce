import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import cart as cart_service
from .. import orders

bp = Blueprint("checkout", __name__)

FIELDS = ("name", "email", "address", "city", "postcode", "country")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate(form):
    """Return (customer, errors) for a submitted checkout form."""
    customer = {field: (form.get(field) or "").strip() for field in FIELDS}
    errors = {}
    for field, value in customer.items():
        if not value:
            errors[field] = "This field is required."
    if customer["email"] and not EMAIL_RE.match(customer["email"]):
        errors["email"] = "Enter a valid email address."
    return customer, errors


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    lines, totals = cart_service.contents()
    if not lines:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart.show"))

    customer, errors = {field: "" for field in FIELDS}, {}
    if request.method == "POST":
        customer, errors = validate(request.form)
        unavailable = [line for line in lines if not line["in_stock"]]
        if unavailable:
            names = ", ".join(line["product"]["name"] for line in unavailable)
            flash(f"Not enough stock for: {names}", "error")
            return redirect(url_for("cart.show"))

        if not errors:
            try:
                number = orders.place_order(lines, totals, customer)
            except orders.OutOfStock as exc:
                flash(str(exc), "error")
                return redirect(url_for("cart.show"))
            cart_service.clear()
            return redirect(url_for("checkout.confirmation", number=number))

    return render_template(
        "checkout.html", lines=lines, totals=totals, customer=customer, errors=errors
    )


@bp.get("/orders/<number>")
def confirmation(number):
    order, items = orders.get_order(number)
    if order is None:
        abort(404)
    return render_template("order.html", order=order, items=items)
