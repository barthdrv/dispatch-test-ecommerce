"""Validation for user-submitted forms.

Deliberately free of Flask and of the database so the rules can be unit
tested without a request context. Money is parsed here, once, at the form
boundary: dollars in, integer cents out, never a float.
"""
import re
import unicodedata
from decimal import Decimal

# Field limits, mirroring the storefront copy and the schema's CHECKs.
NAME_MIN = 2
NAME_MAX = 120
SUMMARY_MAX = 200
DESCRIPTION_MAX = 4000
STOCK_MIN = 0
STOCK_MAX = 9999

# Order matters: it is the order the form renders and reports errors in.
PRODUCT_FIELDS = (
    "name",
    "category",
    "price",
    "stock",
    "summary",
    "description",
    "sku",
    "image",
)

REQUIRED = "This field is required."

PRICE_RE = re.compile(r"^\d+(\.\d{1,2})?$")
STOCK_RE = re.compile(r"^\d{1,4}$")
SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,31}$")
IMAGE_RE = re.compile(r"^[A-Za-z]{2}$")
NON_SLUG_RE = re.compile(r"[^a-z0-9]+")
NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")


class Invalid(ValueError):
    """A submitted value could not be parsed. ``str(exc)`` is form copy."""


def parse_price_dollars(raw):
    """Return decimal dollars as integer cents, or raise :class:`Invalid`.

    Accepts ``"12"``, ``"12.5"`` and ``"12.50"``. Anything else — a negative
    number, three decimal places, a stray sign, free text — is rejected
    rather than rounded or coerced.
    """
    value = str(raw or "").strip()
    if not value:
        raise Invalid(REQUIRED)
    if not PRICE_RE.match(value):
        raise Invalid("Enter a price in dollars, e.g. 12.50.")
    return int(Decimal(value).scaleb(2))


def parse_stock(raw):
    """Return the stock count as an int, or raise :class:`Invalid`."""
    value = str(raw or "").strip()
    if not value:
        raise Invalid(REQUIRED)
    if not STOCK_RE.match(value):
        raise Invalid(f"Enter a whole number between {STOCK_MIN} and {STOCK_MAX}.")
    stock = int(value)
    if not STOCK_MIN <= stock <= STOCK_MAX:
        raise Invalid(f"Enter a whole number between {STOCK_MIN} and {STOCK_MAX}.")
    return stock


def slug_base(name):
    """A URL-safe slug for ``name``, without any uniqueness guarantee."""
    folded = unicodedata.normalize("NFKD", str(name or ""))
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return NON_SLUG_RE.sub("-", ascii_only.lower()).strip("-")


def _letters(name):
    """The name's words, reduced to their A-Z0-9 characters."""
    folded = unicodedata.normalize("NFKD", str(name or ""))
    ascii_only = folded.encode("ascii", "ignore").decode("ascii").upper()
    return [word for word in NON_ALNUM_RE.split(ascii_only) if word]


def default_image(name):
    """Two-letter tile code from the name's initials, e.g. "CM"."""
    words = _letters(name)
    if len(words) >= 2:
        code = words[0][0] + words[1][0]
    elif words:
        code = words[0][:2]
    else:
        code = ""
    return (code + "XX")[:2]


def default_sku(name):
    """Three-character SKU prefix from the name, e.g. "CER"."""
    letters = "".join(_letters(name))
    return (letters + "XXX")[:3]


def trimmed_values(form_data):
    """Every product field, whitespace-trimmed, for re-rendering the form."""
    return {
        field: (form_data.get(field) or "").strip() for field in PRODUCT_FIELDS
    }


def validate_product_form(values, category_ids):
    """Validate a submitted listing.

    ``values`` is a mapping of the product fields (see :func:`trimmed_values`)
    and ``category_ids`` the ids currently in ``categories``. Returns
    ``(cleaned, errors)``: ``cleaned`` holds database-ready keyword arguments
    for :func:`shop.catalog.create_product` and ``errors`` maps a field name
    to a message. ``cleaned`` is only complete when ``errors`` is empty.
    """
    values = trimmed_values(values)
    cleaned, errors = {}, {}

    name = values["name"]
    if not name:
        errors["name"] = REQUIRED
    elif not NAME_MIN <= len(name) <= NAME_MAX:
        errors["name"] = f"Use between {NAME_MIN} and {NAME_MAX} characters."
    else:
        cleaned["name"] = name

    category = values["category"]
    if not category:
        errors["category"] = REQUIRED
    else:
        try:
            category_id = int(category)
        except ValueError:
            category_id = None
        if category_id is None or category_id not in set(category_ids):
            errors["category"] = "Choose one of the listed categories."
        else:
            cleaned["category_id"] = category_id

    try:
        cleaned["price_cents"] = parse_price_dollars(values["price"])
    except Invalid as exc:
        errors["price"] = str(exc)

    try:
        cleaned["stock"] = parse_stock(values["stock"])
    except Invalid as exc:
        errors["stock"] = str(exc)

    summary = values["summary"]
    if not summary:
        errors["summary"] = REQUIRED
    elif len(summary) > SUMMARY_MAX:
        errors["summary"] = f"Keep the summary under {SUMMARY_MAX} characters."
    else:
        cleaned["summary"] = summary

    description = values["description"]
    if not description:
        errors["description"] = REQUIRED
    elif len(description) > DESCRIPTION_MAX:
        errors["description"] = (
            f"Keep the description under {DESCRIPTION_MAX} characters."
        )
    else:
        cleaned["description"] = description

    # SKU and image are optional: blank means "derive one from the name".
    sku = values["sku"].upper()
    if not sku:
        cleaned["sku"] = None
    elif not SKU_RE.match(sku):
        errors["sku"] = "Use 2 to 32 letters, digits or dashes."
    else:
        cleaned["sku"] = sku

    image = values["image"]
    if not image:
        cleaned["image"] = None
    elif not IMAGE_RE.match(image):
        errors["image"] = "Use exactly two letters, e.g. CM."
    else:
        cleaned["image"] = image.upper()

    return cleaned, errors
