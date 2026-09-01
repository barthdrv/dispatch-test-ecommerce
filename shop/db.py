"""Thin sqlite3 wrapper.

One connection per request, stored on ``g`` and closed on teardown.
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA = Path(__file__).parent / "schema.sql"
SEED = Path(__file__).parent / "seed.sql"

ORIGINS = (
    ("CN", "China", "Asia"),
    ("JP", "Japan", "Asia"),
    ("GB", "United Kingdom", "Europe"),
    ("LT", "Lithuania", "Europe"),
    ("PT", "Portugal", "Europe"),
    ("US", "United States", "North America"),
)
PRODUCT_ORIGINS = (
    ("US", "DSK-001"),
    ("GB", "DSK-002"),
    ("GB", "DSK-003"),
    ("PT", "DSK-004"),
    ("US", "KTC-001"),
    ("JP", "KTC-002"),
    ("LT", "KTC-003"),
    ("CN", "OUT-001"),
    ("GB", "OUT-002"),
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(seed=True):
    db = get_db()
    db.executescript(SCHEMA.read_text())
    if seed:
        db.executescript(SEED.read_text())
    db.commit()


def upgrade_db():
    """Add the origin schema to an existing catalog without losing orders."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS origins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            region TEXT NOT NULL
        )
        """
    )
    db.executemany(
        "INSERT OR IGNORE INTO origins (code, name, region) VALUES (?, ?, ?)",
        ORIGINS,
    )
    columns = {row["name"] for row in db.execute("PRAGMA table_info(products)")}
    if "origin_id" not in columns:
        db.execute(
            "ALTER TABLE products ADD COLUMN origin_id INTEGER REFERENCES origins (id)"
        )
        db.executemany(
            """
            UPDATE products
            SET origin_id = (SELECT id FROM origins WHERE code = ?)
            WHERE sku = ?
            """,
            PRODUCT_ORIGINS,
        )
    db.execute("CREATE INDEX IF NOT EXISTS idx_products_origin ON products (origin_id)")
    db.commit()


@click.command("init-db")
@click.option("--no-seed", is_flag=True, help="Create tables without demo data.")
def init_db_command(no_seed):
    """Drop and recreate the database, then load the demo catalog."""
    init_db(seed=not no_seed)
    click.echo(f"Initialised {current_app.config['DATABASE']}")


@click.command("upgrade-db")
def upgrade_db_command():
    """Upgrade an existing catalog without deleting its data."""
    upgrade_db()
    click.echo(f"Upgraded {current_app.config['DATABASE']}")


def register(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(upgrade_db_command)
