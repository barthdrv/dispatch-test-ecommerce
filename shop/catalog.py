"""Queries against the product catalog."""
from flask import g

from . import forms
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


def list_category_choices():
    """Categories with their ids, for the "list an item" select."""
    return get_db().execute(
        "SELECT id, slug, name FROM categories ORDER BY name"
    ).fetchall()


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


# Write queries -------------------------------------------------------------

# Fixed statements, selected by key, for the "is this value taken?" lookups.
TAKEN_QUERIES = {
    "slug": "SELECT slug AS value FROM products WHERE slug = ? OR slug LIKE ?",
    "sku": "SELECT sku AS value FROM products WHERE sku = ? OR sku LIKE ?",
}


def _taken(column, base):
    """Existing values in ``column`` equal to ``base`` or a ``base-N`` variant."""
    rows = get_db().execute(TAKEN_QUERIES[column], (base, f"{base}-%")).fetchall()
    return {row["value"] for row in rows}


def slugify(name):
    """A URL-safe slug for ``name``, de-duplicated with a -2, -3 suffix."""
    base = forms.slug_base(name) or "item"
    taken = _taken("slug", base)
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _unique_sku(base):
    """Turn a SKU prefix into a free SKU, e.g. "CER" -> "CER-001"."""
    taken = _taken("sku", base)
    number = 1
    while f"{base}-{number:03d}" in taken:
        number += 1
    return f"{base}-{number:03d}"


def sku_exists(sku):
    """Whether a product already uses ``sku``."""
    row = get_db().execute("SELECT 1 FROM products WHERE sku = ?", (sku,)).fetchone()
    return row is not None


def create_product(
    category_id,
    name,
    summary,
    description,
    price_cents,
    stock,
    sku=None,
    image=None,
    origin_id=None,
):
    """Insert a product, returning it in the same shape as :func:`get_product`.

    A blank ``sku`` or ``image`` is derived from the name; the slug is always
    generated and de-duplicated. Values are expected to be validated already
    (see :mod:`shop.forms`) — the schema's constraints are only a backstop.
    """
    slug = slugify(name)
    db = get_db()
    db.execute(
        """
        INSERT INTO products
            (category_id, origin_id, sku, slug, name, summary, description,
             price_cents, stock, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            category_id,
            origin_id,
            sku or _unique_sku(forms.default_sku(name)),
            slug,
            name,
            summary,
            description,
            price_cents,
            stock,
            image or forms.default_image(name),
        ),
    )
    db.commit()
    return get_product(slug)
