# bro_connector/conftest.py
import os
import pytest
import psycopg2
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    """
    Override pytest-django's django_db_setup.
    1. Drop and recreate the test database fresh.
    2. Run create_schemas.sql against it.
    3. Let Django run its migrations.
    """
    from django.test.utils import setup_databases
    from django.db import connections

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
        with open(sql_path) as f:
            cur.execute(f.read())
    conn.close()
    print("[conftest] Schemas created successfully.")

    # # Step 3: Run Django migrations (keepdb=True skips DROP/CREATE since we did it,
    # # but tells Django the DB already exists — no serialization attempt)
    # with django_db_blocker.unblock():
    #     setup_databases(verbosity=1, interactive=False, keepdb=True)

    # yield

    # # Teardown
    # with django_db_blocker.unblock():
    #     for c in connections.all():
    #         c.close()

    # conn = psycopg2.connect(
    #     dbname=db["NAME"],
    #     user=db["USER"],
    #     password=db["PASSWORD"],
    #     host=db.get("HOST", "localhost"),
    #     port=db.get("PORT", 5432),
    # )
    # conn.autocommit = True
    # with conn.cursor() as cur:
    #     cur.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
    # conn.close()