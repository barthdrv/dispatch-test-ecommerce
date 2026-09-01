from flask import Blueprint, abort, render_template, request

from .. import catalog

bp = Blueprint("catalog", __name__)


@bp.get("/")
def index():
    category = request.args.get("category") or None
    query = (request.args.get("q") or "").strip() or None
    origin = catalog.normalize_origin(request.args.get("origin"))
    sort = catalog.normalize_sort(request.args.get("sort"))
    return render_template(
        "index.html",
        products=catalog.list_products(
            category=category, query=query, origin=origin, sort=sort
        ),
        categories=catalog.list_categories(),
        origins=catalog.list_origins(),
        active_category=category,
        active_origin=origin,
        query=query,
        sort=sort,
        sort_options=catalog.SORT_OPTIONS,
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
