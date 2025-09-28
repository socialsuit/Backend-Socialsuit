#!/usr/bin/env python
"""
Script to generate static OpenAPI JSON for Social Suit API

This script imports the FastAPI app from the main module and
generates a static OpenAPI JSON file that can be committed to the repository.
"""

import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app
from main import app

# Define the output directory and file path
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "openapi"
OUTPUT_FILE = OUTPUT_DIR / "openapi.json"

def main():
    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get the OpenAPI schema
    openapi_schema = app.openapi()
    
    # Write the schema to a file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"OpenAPI schema written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()