# Corner Shop

A small, deliberately plain ecommerce site: browse a catalog, add things to a
cart, check out, get an order confirmation. Flask + SQLite, server-rendered
templates, no build step and no JavaScript framework.

It exists as a realistic-but-small codebase to test tooling against.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

flask --app shop:create_app init-db   # creates shop.sqlite and loads the demo catalog
python run.py                         # http://127.0.0.1:5000
```

In production, point a WSGI server at `wsgi:app` and set `SECRET_KEY`:

```bash
gunicorn wsgi:app
```

## Tests

```bash
pytest
```

27 tests covering the catalog, cart arithmetic, and the checkout flow. Each
test gets a fresh seeded SQLite file, so they can run in any order.

## Layout

```
run.py               dev entrypoint
wsgi.py              production entrypoint
shop/
  __init__.py        app factory
  config.py          env-driven settings (tax rate, shipping, secret key)
  db.py              sqlite3 connection handling + the init-db CLI command
  schema.sql         tables
  seed.sql           ten demo products in three categories
  catalog.py         product read queries
  cart.py            session-backed cart
  pricing.py         money formatting, tax, shipping, totals
  orders.py          order placement and stock decrement
  views/
    catalog.py       /  and  /products/<slug>
    cart.py          /cart/*
    checkout.py      /checkout  and  /orders/<number>
    api.py           read-only JSON under /api
  templates/         Jinja2
  static/            one stylesheet, one small progressive-enhancement script
tests/
```

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Catalog, with `?category=` and `?q=` filters |
| GET | `/products/<slug>` | Product detail |
| GET | `/cart/` | Cart contents |
| POST | `/cart/add` | Add a product by slug |
| POST | `/cart/update` | Set an absolute quantity (0 removes) |
| POST | `/cart/remove` | Remove a line |
| GET, POST | `/checkout` | Address form, then place the order |
| GET | `/orders/<number>` | Order confirmation |
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/products` | Catalog as JSON, same filters as `/` |
| GET | `/api/products/<slug>` | One product as JSON |
| GET | `/api/cart` | Current session cart and totals as JSON |

## Notes on how it works

- **Money is integer cents** everywhere, formatted only at render time by
  `pricing.money`. Tax is 8.5%; shipping is a flat $4.95 and free over $50.
  All three are configurable in `shop/config.py`.
- **The cart lives in the signed session cookie** as `{product_id: quantity}`.
  Nothing about a cart is persisted server-side until an order is placed.
  Quantities are clamped to 0–99, and products deleted from the catalog are
  silently dropped from the cart rather than raising.
- **Orders are transactional.** `orders.place_order` writes the order and
  decrements stock in one transaction, using
  `UPDATE ... WHERE stock >= ?` so two concurrent checkouts cannot both take
  the last unit. A shortfall raises `OutOfStock` and rolls the whole thing back.
- **No payment integration and no user accounts.** Checkout collects a shipping
  address, marks the order `paid`, and stops there.
- **Product images are two-letter placeholders** rendered as CSS tiles, so the
  repo carries no binary assets.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `SECRET_KEY` | `dev-secret-change-me` | Session cookie signing key |
| `DATABASE` | `shop.sqlite` | SQLite file path |
| `PORT` | `5000` | Dev server port |
| `DEBUG` | `1` | Dev server reloader/debugger |
