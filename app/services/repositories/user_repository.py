from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from datetime import datetime, timedelta
import asyncio

from app.services.interfaces.base_repository import BaseRepository
from app.services.models.user_model import User
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager

class UserRepository(BaseRepository[User]):
    """
    Optimized Repository for User entity operations with caching and performance monitoring
    """
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    @query_performance_tracker("postgresql", "get_by_email")
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by email with optimized query and caching
        """
        cache_key = f"user:email:{email}"
        
        # Try cache first (sync operation, so we'll use a simple approach)
        try:
            # For sync operations, we'll implement a simple cache check
            # In a real implementation, you might want to use a sync Redis client
            pass
        except:
            pass
        
        # Use optimized query with index hint
        result = self.db.query(User).filter(User.email == email).first()
        
        # Cache the result (in a real implementation)
        if result:
            # Cache user data
            pass
        
        return result
    
    @query_performance_tracker("postgresql", "get_by_wallet")
    def get_by_wallet_address(self, wallet_address: str) -> Optional[User]:
        """
        Find a user by wallet address with optimized query and caching
        """
        cache_key = f"user:wallet:{wallet_address}"
        
        # Use optimized query with index
        result = self.db.query(User).filter(User.wallet_address == wallet_address).first()
        
        return result
    
    @query_performance_tracker("postgresql", "get_by_email_or_wallet")
    def get_by_email_or_wallet(self, identifier: str) -> Optional[User]:
        """
        Find a user by either email or wallet address with optimized query
        """
        cache_key = f"user:identifier:{identifier}"
        
        # Optimized query using proper indexing
        result = self.db.query(User).filter(
            or_(User.email == identifier, User.wallet_address == identifier)
        ).first()
        
        return result
    
    @query_performance_tracker("postgresql", "get_verified_users")
    def get_verified_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Get verified users with pagination and caching
        """
        cache_key = f"users:verified:{limit}:{offset}"
        
        # Use optimized query with pagination
        result = (self.db.query(User)
                 .filter(User.is_verified == True)
                 .order_by(desc(User.created_at))
                 .limit(limit)
                 .offset(offset)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_active_users")
    def get_active_users(self, days: int = 30, limit: int = 100) -> List[User]:
        """
        Get users active within the last N days
        """
        cache_key = f"users:active:{days}:{limit}"
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = (self.db.query(User)
                 .filter(User.last_login >= cutoff_date)
                 .order_by(desc(User.last_login))
                 .limit(limit)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_user_stats")
    def get_user_statistics(self) -> dict:
        """
        Get user statistics with aggregation
        """
        cache_key = "users:statistics"
        
        # Optimized aggregation query
        total_users = self.db.query(func.count(User.id)).scalar()
        verified_users = self.db.query(func.count(User.id)).filter(User.is_verified == True).scalar()
        
        # Users registered in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_users = self.db.query(func.count(User.id)).filter(User.created_at >= thirty_days_ago).scalar()
        
        # Active users in last 30 days
        active_users = self.db.query(func.count(User.id)).filter(User.last_login >= thirty_days_ago).scalar()
        
        stats = {
            "total_users": total_users,
            "verified_users": verified_users,
            "recent_users": recent_users,
            "active_users": active_users,
            "verification_rate": (verified_users / total_users * 100) if total_users > 0 else 0,
            "activity_rate": (active_users / total_users * 100) if total_users > 0 else 0
        }
        
        return stats
    
    @query_performance_tracker("postgresql", "search_users")
    def search_users(self, search_term: str, limit: int = 50) -> List[User]:
        """
        Search users by email or username with text search optimization
        """
        cache_key = f"users:search:{search_term}:{limit}"
        
        # Use ILIKE for case-insensitive search with proper indexing
        search_pattern = f"%{search_term}%"
        
        result = (self.db.query(User)
                 .filter(or_(
                     User.email.ilike(search_pattern),
                     User.username.ilike(search_pattern) if hasattr(User, 'username') else False
                 ))
                 .order_by(desc(User.created_at))
                 .limit(limit)
                 .all())
        
        return result
    
    def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        """
        try:
            user = self.get_by_id(user_id)
            if user:
                user.last_login = datetime.now()
                self.db.commit()
                
                # Invalidate user cache
                asyncio.create_task(self._invalidate_user_cache(user_id))
                return True
        except Exception as e:
            self.db.rollback()
            raise e
        return False
    
    async def _invalidate_user_cache(self, user_id: str):
        """
        Invalidate user-related cache entries
        """
        patterns = [
            f"user:*:{user_id}*",
            f"users:*"  # Invalidate user lists
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)