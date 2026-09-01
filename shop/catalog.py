"""Read queries against the product catalog."""
from flask import g

from .db import get_db

PRODUCT_COLUMNS = """
    p.id, p.sku, p.slug, p.name, p.summary, p.description,
    p.price_cents, p.stock, p.image,
    c.slug AS category_slug, c.name AS category_name,
    o.code AS origin_code, o.name AS origin_name, o.region AS origin_region
"""


DEFAULT_SORT = "name"

# Public ?sort= value -> fixed ORDER BY fragment. Only fragments from this
# table ever reach SQL; the untrusted parameter is used solely as a lookup key.
SORT_ORDERS = {
    "name": "p.name",
    "origin": "o.region IS NULL, o.region, o.name, p.name",
    "price-asc": "p.price_cents ASC, p.name",
    "price-desc": "p.price_cents DESC, p.name",
}

# Ordered (key, label) pairs for the storefront sort control.
SORT_OPTIONS = (
    ("name", "Name"),
    ("origin", "Origin"),
    ("price-asc", "Price: low to high"),
    ("price-desc", "Price: high to low"),
)


def normalize_sort(value):
    """Map an untrusted ?sort= value onto a known sort key."""
    return value if value in SORT_ORDERS else DEFAULT_SORT


def list_categories():
    db = get_db()
    return db.execute("SELECT slug, name FROM categories ORDER BY name").fetchall()


def list_origins():
    if "catalog_origins" not in g:
        g.catalog_origins = get_db().execute(
            "SELECT code, name, region FROM origins ORDER BY region, name"
        ).fetchall()
    return g.catalog_origins


def normalize_origin(value):
    """Return a known country code, or no filter for an untrusted value."""
    if not value:
        return None
    return value if any(row["code"] == value for row in list_origins()) else None


def list_products(category=None, query=None, origin=None, sort=None):
    sql = f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products p
        JOIN categories c ON c.id = p.category_id
        LEFT JOIN origins o ON o.id = p.origin_id
    """
    where, params = [], []
    if category:
        where.append("c.slug = ?")
        params.append(category)
    if query:
        where.append("(p.name LIKE ? OR p.summary LIKE ?)")
        like = f"%{query}%"
        params += [like, like]
    origin = normalize_origin(origin)
    if origin:
        where.append("o.code = ?")
        params.append(origin)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + SORT_ORDERS[normalize_sort(sort)]
    return get_db().execute(sql, params).fetchall()


def get_product(slug):
    return get_db().execute(
        f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products p
        JOIN categories c ON c.id = p.category_id
        LEFT JOIN origins o ON o.id = p.origin_id
        WHERE p.slug = ?
        """,
        (slug,),
    ).fetchone()


def get_products_by_id(ids):
    """Fetch many products at once, returned as {id: row}."""
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = get_db().execute(
        f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products p
        JOIN categories c ON c.id = p.category_id
        LEFT JOIN origins o ON o.id = p.origin_id
        WHERE p.id IN ({marks})
        """,
        list(ids),
    ).fetchall()
    return {row["id"]: row for row in rows}
