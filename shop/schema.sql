DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS origins;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    slug  TEXT UNIQUE NOT NULL,
    name  TEXT NOT NULL
);

CREATE TABLE origins (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    code    TEXT UNIQUE NOT NULL,
    name    TEXT NOT NULL,
    region  TEXT NOT NULL
);

CREATE TABLE products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL REFERENCES categories (id),
    origin_id    INTEGER REFERENCES origins (id),
    sku          TEXT UNIQUE NOT NULL,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    summary      TEXT NOT NULL,
    description  TEXT NOT NULL,
    price_cents  INTEGER NOT NULL CHECK (price_cents >= 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    image        TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products (category_id);
CREATE INDEX idx_products_origin ON products (origin_id);

CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    number          TEXT UNIQUE NOT NULL,
    email           TEXT NOT NULL,
    name            TEXT NOT NULL,
    address         TEXT NOT NULL,
    city            TEXT NOT NULL,
    postcode        TEXT NOT NULL,
    country         TEXT NOT NULL,
    subtotal_cents  INTEGER NOT NULL,
    shipping_cents  INTEGER NOT NULL,
    tax_cents       INTEGER NOT NULL,
    total_cents     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'paid',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products (id),
    name         TEXT NOT NULL,
    sku          TEXT NOT NULL,
    unit_cents   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE INDEX idx_order_items_order ON order_items (order_id);
