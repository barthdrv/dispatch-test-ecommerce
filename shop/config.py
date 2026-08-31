"""Application configuration.

Values come from the environment so the same image can run in dev and prod.
"""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE = os.environ.get("DATABASE", "shop.sqlite")

    # Storefront settings. Money is handled in integer cents everywhere.
    CURRENCY = "USD"
    TAX_RATE = 0.085
    SHIPPING_FLAT_CENTS = 495
    FREE_SHIPPING_THRESHOLD_CENTS = 5000
