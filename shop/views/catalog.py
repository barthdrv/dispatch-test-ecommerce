from flask import Blueprint, abort, render_template, request

from .. import catalog

bp = Blueprint("catalog", __name__)


@bp.get("/")
def index():
    category = request.args.get("category") or None
    query = (request.args.get("q") or "").strip() or None
    return render_template(
        "index.html",
        products=catalog.list_products(category=category, query=query),
        categories=catalog.list_categories(),
        active_category=category,
        query=query,
    )


@bp.get("/products/<slug>")
def product(slug):
    item = catalog.get_product(slug)
    if item is None:
        abort(404)
    related = [
        p
        for p in catalog.list_products(category=item["category_slug"])
        if p["id"] != item["id"]
    ][:3]
    return render_template("product.html", product=item, related=related)
