"""Read queries against the product catalog."""
from .db import get_db

PRODUCT_COLUMNS = """
    p.id, p.sku, p.slug, p.name, p.summary, p.description,
    p.price_cents, p.stock, p.image,
    c.slug AS category_slug, c.name AS category_name
"""


DEFAULT_SORT = "name"

# Public ?sort= value -> fixed ORDER BY fragment. Only fragments from this
# table ever reach SQL; the untrusted parameter is used solely as a lookup key.
SORT_ORDERS = {
    "name": "p.name",
    "price-asc": "p.price_cents ASC, p.name",
    "price-desc": "p.price_cents DESC, p.name",
}

# Ordered (key, label) pairs for the storefront sort control.
SORT_OPTIONS = (
    ("name", "Name"),
    ("price-asc", "Price: low to high"),
    ("price-desc", "Price: high to low"),
)


def normalize_sort(value):
    """Map an untrusted ?sort= value onto a known sort key."""
    return value if value in SORT_ORDERS else DEFAULT_SORT


def list_categories():
    db = get_db()
    return db.execute("SELECT slug, name FROM categories ORDER BY name").fetchall()


def list_products(category=None, query=None, sort=None):
    sql = f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products p
        JOIN categories c ON c.id = p.category_id
    """
    where, params = [], []
    if category:
        where.append("c.slug = ?")
        params.append(category)
    if query:
        where.append("(p.name LIKE ? OR p.summary LIKE ?)")
        like = f"%{query}%"
        params += [like, like]
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
        WHERE p.id IN ({marks})
        """,
        list(ids),
    ).fetchall()
    return {row["id"]: row for row in rows}
