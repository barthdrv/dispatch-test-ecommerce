"""Thin sqlite3 wrapper.

One connection per request, stored on ``g`` and closed on teardown.
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA = Path(__file__).parent / "schema.sql"
SEED = Path(__file__).parent / "seed.sql"


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


@click.command("init-db")
@click.option("--no-seed", is_flag=True, help="Create tables without demo data.")
def init_db_command(no_seed):
    """Drop and recreate the database, then load the demo catalog."""
    init_db(seed=not no_seed)
    click.echo(f"Initialised {current_app.config['DATABASE']}")


def register(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
