#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import logging
import os
import sys

from main.settings.base import ENV


def main():
    """Run administrative tasks."""
    logging.basicConfig(level=logging.INFO)
    if ENV == "production":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.production")
    elif ENV == "staging":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.staging")
    elif ENV == "development" or ENV == "demo":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.development")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
