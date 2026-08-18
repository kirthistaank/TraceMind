#!/usr/bin/env python3
"""
Generate and load Neo4j KG for pediatric clinical conditions (Asthma, Anaphylaxis, Croup).

This script creates Concept and CPGMention nodes in Neo4j, linked to clinical decision rules.

Usage:
    python load_condition_kg.py --condition asthma
    python load_condition_kg.py --all
"""

import argparse
import sys
import os

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from source.config import Settings
from source.graph.neo4j_client import get_driver, close_driver
from source.graph.kg_loader import load_condition_kg, load_all_condition_kg


def main():
    parser = argparse.ArgumentParser(description="Load pediatric condition KGs into Neo4j")
    parser.add_argument(
        "--condition",
        choices=["fever", "asthma", "anaphylaxis", "croup"],
        help="Specific condition to load",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all conditions",
    )

    args = parser.parse_args()

    settings = Settings()
    driver = get_driver(settings)

    if not driver:
        print("❌ Neo4j driver not configured.")
        print("   Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")
        sys.exit(1)

    try:
        if args.all or (not args.condition):
            print("📚 Loading all condition KGs...")
            load_all_condition_kg(driver)
        elif args.condition:
            print(f"📚 Loading {args.condition} KG...")
            load_condition_kg(driver, args.condition)

        print("✅ KG load complete!")

    except Exception as e:
        print(f"❌ Error loading KG: {e}")
        sys.exit(1)

    finally:
        close_driver(driver)


if __name__ == "__main__":
    main()
