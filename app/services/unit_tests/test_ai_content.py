import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.ai_client import ai_client

# Use the unified AI client
assert ai_client is not None

# Test content generation
print("Testing generate_content()...")
content = ai.generate_content("Explain Web3 in simple words")
print("Generated Content:", content)

# Test caption generation
print("\nTesting generate_caption()...")
caption = ai.generate_caption("Web3 trends")
print("Generated Caption:", caption)
