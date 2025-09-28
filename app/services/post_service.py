"""Post service implementation.

This module provides services for post-related operations.
"""

from typing import List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.schemas.post import PostCreate, PostUpdate
from shared.database.pagination import Page


class PostService:
    """Service for post-related operations.
    
    This service uses the PostRepository for database operations and provides
    business logic for post-related operations.
    """
    
    def __init__(self, repository: PostRepository = Depends()):
        """Initialize the service with a repository.
        
        Args:
            repository: The post repository
        """
        self.repository = repository
    
    async def get_by_id(self, db: AsyncSession, post_id: int) -> Optional[Post]:
        """Get a post by ID.
        
        Args:
            db: The database session
            post_id: The post ID
            
        Returns:
            The post if found, None otherwise
        """
        return await self.repository.get_by_id(db, post_id)
    
    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> List[Post]:
        """Get posts by user ID.
        
        Args:
            db: The database session
            user_id: The user ID
            
        Returns:
            A list of posts by the user
        """
        return await self.repository.get_by_user_id(db, user_id)
    
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
        return await self.repository.get_by_user_id_paginated(db, user_id, page, size)
    
    async def get_recent_posts(self, db: AsyncSession, limit: int = 10) -> List[Post]:
        """Get recent posts.
        
        Args:
            db: The database session
            limit: The maximum number of posts to return
            
        Returns:
            A list of recent posts
        """
        return await self.repository.get_recent_posts(db, limit)
    
    async def create(self, db: AsyncSession, post_in: PostCreate, user_id: int) -> Post:
        """Create a new post.
        
        Args:
            db: The database session
            post_in: The post data
            user_id: The user ID
            
        Returns:
            The created post
        """
        post_data = post_in.dict()
        post_data["user_id"] = user_id
        
        return await self.repository.create(db, post_data)
    
    async def update(self, db: AsyncSession, post: Post, post_in: PostUpdate) -> Post:
        """Update a post.
        
        Args:
            db: The database session
            post: The post to update
            post_in: The post data
            
        Returns:
            The updated post
        """
        update_data = post_in.dict(exclude_unset=True)
        return await self.repository.update(db, post, update_data)
    
    async def delete(self, db: AsyncSession, post_id: int) -> Optional[Post]:
        """Delete a post.
        
        Args:
            db: The database session
            post_id: The post ID
            
        Returns:
            The deleted post if found, None otherwise
        """
        return await self.repository.delete(db, post_id)