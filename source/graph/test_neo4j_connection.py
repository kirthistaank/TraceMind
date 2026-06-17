"""
Smoke-test Neo4j connectivity using TraceMind settings from ``tracemind/.env``.

Run from the project root:

  python -m tracemind.graph.test_neo4j_connection

Or directly:

  python tracemind/graph/test_neo4j_connection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (cwd may be anywhere).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.config import Settings
from source.graph.neo4j_client import close_driver, get_driver, run_cypher


def test_connection() -> None:
    settings = Settings.from_env()

    if settings.skip_neo4j:
        print("TRACEMIND_SKIP_NEO4J / CARETRACE_SKIP_NEO4J is enabled — Neo4j is skipped.")
        return

    if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
        print("Neo4j is not configured. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in tracemind/.env")
        return

    print(f"URI: {settings.neo4j_uri}")
    print(f"User: {settings.neo4j_user}")
    print(f"Database: {settings.neo4j_database or '(default)'}")
    print(f"Password loaded: {'yes' if settings.neo4j_password else 'no'}")

    driver = get_driver(settings)
    if driver is None:
        print("Could not create Neo4j driver.")
        return

    try:
        driver.verify_connectivity()
        print("Successfully connected to Neo4j (authentication OK).")

        try:
            rows = run_cypher(
                driver,
                "RETURN 'Hello, Neo4j Graph!' AS greeting",
                database=settings.neo4j_database,
            )
        except Exception as query_exc:
            if settings.neo4j_database and "DatabaseNotFound" in type(query_exc).__name__ + str(query_exc):
                print(
                    f"Database '{settings.neo4j_database}' was not found; retrying on the default database."
                )
                rows = run_cypher(
                    driver,
                    "RETURN 'Hello, Neo4j Graph!' AS greeting",
                    database=None,
                )
            else:
                raise

        for row in rows:
            print(f"Database response: {row['greeting']}")
    except Exception as exc:
        print(f"Connection failed: {exc}")
    finally:
        close_driver(driver)


if __name__ == "__main__":
    test_connection()
