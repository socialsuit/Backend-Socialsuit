#!/usr/bin/env python
"""
Script to generate Alembic migrations automatically based on model changes.

Usage:
    python scripts/generate_migration.py "migration message"
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent


def generate_migration(message: str) -> None:
    """Generate a new migration with the given message."""
    if not message:
        print("Error: Migration message is required")
        print("Usage: python scripts/generate_migration.py \"migration message\"")
        sys.exit(1)

    # Change to the project root directory
    os.chdir(ROOT_DIR)

    # Run alembic revision command with autogenerate
    try:
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", message],
            check=True,
        )
        print(f"Successfully generated migration: {message}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Get migration message from command line arguments
    message = sys.argv[1] if len(sys.argv) > 1 else ""
    generate_migration(message)