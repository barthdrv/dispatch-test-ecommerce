"""Money helpers.

Everything is integer cents until the moment it is rendered.
"""
from flask import current_app


def money(cents):
    """Format integer cents as a display string: 8900 -> '$89.00'."""
    return f"${cents / 100:,.2f}"


def shipping_for(subtotal_cents):
    if subtotal_cents == 0:
        return 0
    threshold = current_app.config["FREE_SHIPPING_THRESHOLD_CENTS"]
    if subtotal_cents >= threshold:
        return 0
    return current_app.config["SHIPPING_FLAT_CENTS"]


def tax_for(subtotal_cents):
    return round(subtotal_cents * current_app.config["TAX_RATE"])


def totals_for(subtotal_cents):
    """Return the full price breakdown for a given subtotal."""
    shipping = shipping_for(subtotal_cents)
    tax = tax_for(subtotal_cents)
    return {
        "subtotal_cents": subtotal_cents,
        "shipping_cents": shipping,
        "tax_cents": tax,
        "total_cents": subtotal_cents + shipping + tax,
    }
