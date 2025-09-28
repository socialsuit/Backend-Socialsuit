"""Repository package for database access.

This package provides repositories for database access using the repository pattern.
Repositories abstract database operations and provide a clean interface for services.
"""

from app.repositories.post_repository import PostRepository

# Export repositories
__all__ = ["PostRepository"]