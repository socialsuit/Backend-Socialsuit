#!/usr/bin/env python
"""
Script to run Alembic migrations.

Usage:
    python scripts/run_migrations.py [--down] [revision]

Options:
    --down      Run downgrade instead of upgrade
    revision    Specific revision to migrate to (default: head)
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent


def run_migrations(downgrade=False, revision="head") -> None:
    """Run database migrations.
    
    Args:
        downgrade: If True, run downgrade instead of upgrade
        revision: The revision to migrate to (default: head)
    """
    # Change to the project root directory
    os.chdir(ROOT_DIR)

    # Prepare the command
    command = ["alembic"]
    if downgrade:
        command.extend(["downgrade", revision])
    else:
        command.extend(["upgrade", revision])

    # Run the command
    try:
        subprocess.run(command, check=True)
        direction = "downgraded" if downgrade else "upgraded"
        print(f"Successfully {direction} database to {revision}")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    args = sys.argv[1:]
    downgrade = "--down" in args
    if downgrade:
        args.remove("--down")
    
    revision = args[0] if args else "head"
    run_migrations(downgrade, revision)