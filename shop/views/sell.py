"""Listing a new item for sale. Public, like the rest of the storefront."""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import catalog, forms

bp = Blueprint("sell", __name__, url_prefix="/sell")


@bp.route("/new", methods=["GET", "POST"])
def new():
    categories = catalog.list_category_choices()
    values, errors = forms.trimmed_values({}), {}

    if request.method == "POST":
        values = forms.trimmed_values(request.form)
        cleaned, errors = forms.validate_product_form(
            values, {row["id"] for row in categories}
        )
        if not errors and cleaned["sku"] and catalog.sku_exists(cleaned["sku"]):
            errors["sku"] = "That SKU is already taken."

        if not errors:
            product = _create(cleaned)
            if product is not None:
                flash(f"Listed {product['name']}.", "success")
                return redirect(url_for("catalog.product", slug=product["slug"]))
            errors["sku"] = "That SKU is already taken."

    return (
        render_template(
            "sell_new.html", categories=categories, values=values, errors=errors
        ),
        400 if errors else 200,
    )


def _create(cleaned, attempts=2):
    """Insert the product, retrying once if a concurrent write won the race.

    Slug and SKU uniqueness is resolved in application code, so an
    ``IntegrityError`` here means another insert landed in between. Retrying
    re-resolves both; only then do we give up and report a field error.
    """
    for _attempt in range(attempts):
        try:
            return catalog.create_product(**cleaned)
        except sqlite3.IntegrityError:
            continue
    return None
