"""Post repository implementation.

This module provides a repository for post-related database operations.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from shared.database.repository import BaseRepository
from shared.database.pagination import Page, paginate_query


class PostRepository(BaseRepository[Post]):
    """Repository for post-related database operations."""
    
    def __init__(self):
        super().__init__(Post)
    
    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> List[Post]:
        """Get posts by user ID.
        
        Args:
            db: The database session
            user_id: The user ID
            
        Returns:
            A list of posts by the user
        """
        query = select(Post).where(Post.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_user_id_paginated(
        self, 
        db: AsyncSession, 
        user_id: int,
        page: int = 1, 
        size: int = 10
    ) -> Page[Post]:
        """Get paginated posts by user ID.
        
        Args:
            db: The database session
            user_id: The user ID
            page: The page number
            size: The page size
            
        Returns:
            A Page object containing posts by the user
        """
        query = select(Post).where(Post.user_id == user_id)
        return await paginate_query(db, query, page, size)
    
    async def get_recent_posts(
        self, 
        db: AsyncSession, 
        limit: int = 10
    ) -> List[Post]:
        """Get recent posts.
        
        Args:
            db: The database session
            limit: The maximum number of posts to return
            
        Returns:
            A list of recent posts
        """
        query = select(Post).order_by(Post.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()