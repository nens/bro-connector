# bro_connector/conftest.py
import os

import psycopg2
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connections


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    """
    Override pytest-django's django_db_setup.
    1. Drop and recreate the test database fresh.
    2. Run create_schemas.sql against it.
    3. Let Django run its migrations.
    """

    db = settings.DATABASES["default"]
    test_db_name = f"test_{db['NAME']}"

    # Step 1: Drop and recreate the test database from scratch
    conn = psycopg2.connect(
        dbname=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        host=db.get("HOST", "localhost"),
        port=db.get("PORT", 5432),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        # Terminate any existing connections to the test DB so we can drop it
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{test_db_name}'
            AND pid <> pg_backend_pid()
        """)
        cur.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
        cur.execute(f'CREATE DATABASE "{test_db_name}"')
    conn.close()

    # Step 2: Create schemas inside the fresh test database
    sql_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "installation_help",
        "create_schemas.sql",
    )
    print(f"\n[conftest] Running schema SQL: {sql_path}")
    conn = psycopg2.connect(
        dbname=test_db_name,
        user=db["USER"],
        password=db["PASSWORD"],
        host=db.get("HOST", "localhost"),
        port=db.get("PORT", 5432),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        with open(sql_path) as f:
            cur.execute(f.read())
    conn.close()
    print("[conftest] Schemas created successfully.")

    connection = connections["default"]
    connection.close()
    connection.settings_dict["NAME"] = test_db_name
    with django_db_blocker.unblock():
        call_command(
            "migrate",
            database="default",
            interactive=False,
            verbosity=0,
        )
        call_command(
            "migrate",
            database="default",
            interactive=False,
            run_syncdb=True,
            verbosity=0,
        )
        from bro.models import BROProject, Organisation

        organisation = Organisation.objects.filter(pk=1).first()
        if organisation is None:
            organisation = Organisation.objects.create(
                name="Test Organisation",
                company_number=1,
            )

        if not BROProject.objects.filter(pk=1).exists():
            BROProject.objects.create(
                name="Test Project",
                project_number=1,
                owner=organisation,
            )
