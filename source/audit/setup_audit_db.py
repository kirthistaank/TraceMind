#!/usr/bin/env python3
"""
Initialize the audit database in Neon.

Run this once to create the audit_logs table:
    python setup_audit_db.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Loading Env variables
load_dotenv()  # automatically finds .env in parent dirs
sys.path.insert(0, str(Path(__file__).parent))

from postgres_logger import create_audit_table

if __name__ == "__main__":
    print("Initializing audit database...")
    success = create_audit_table()
    if success:
        print("✅ Audit table created successfully!")
        print("\nYou can now use CareTrace with audit logging enabled.")
        print("All triage decisions will be logged to Neon Postgres.")
    else:
        print("❌ Failed to create audit table.")
        print("Please check:")
        print("  1. DATABASE_URL is set in .env")
        print("  2. Neon instance is running")
        print("  3. psycopg2-binary is installed (pip install psycopg2-binary)")
        sys.exit(1)
