"""Production entrypoint: gunicorn wsgi:app"""
from shop import create_app

app = create_app()
