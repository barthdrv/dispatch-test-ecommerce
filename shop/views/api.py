"""Small read-only JSON API, handy for smoke tests and integrations."""
from flask import Blueprint, jsonify, request

from .. import cart as cart_service
from .. import catalog

bp = Blueprint("api", __name__, url_prefix="/api")


def serialize(product):
    return {
        "id": product["id"],
        "sku": product["sku"],
        "slug": product["slug"],
        "name": product["name"],
        "summary": product["summary"],
        "price_cents": product["price_cents"],
        "stock": product["stock"],
        "category": product["category_slug"],
    }


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/products")
def products():
    rows = catalog.list_products(
        category=request.args.get("category") or None,
        query=(request.args.get("q") or "").strip() or None,
        sort=request.args.get("sort"),
    )
    return jsonify(products=[serialize(row) for row in rows], count=len(rows))


@bp.get("/products/<slug>")
def product(slug):
    row = catalog.get_product(slug)
    if row is None:
        return jsonify(error="not found"), 404
    payload = serialize(row)
    payload["description"] = row["description"]
    return jsonify(payload)


@bp.get("/cart")
def cart():
    lines, totals = cart_service.contents()
    return jsonify(
        items=[
            {
                "slug": line["product"]["slug"],
                "name": line["product"]["name"],
                "quantity": line["quantity"],
                "line_cents": line["line_cents"],
            }
            for line in lines
        ],
        **totals,
    )
