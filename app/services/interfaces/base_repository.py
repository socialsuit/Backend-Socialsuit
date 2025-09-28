from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any, Type
from sqlalchemy.orm import Session
from app.services.database.database import Base

# Generic type for SQLAlchemy models
T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T], ABC):
    """
    Base repository interface that defines common database operations.
    All repository implementations should inherit from this class.
    """
    def __init__(self, db: Session, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Retrieve an entity by its ID
        """
        return self.db.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self) -> List[T]:
        """
        Retrieve all entities of this type
        """
        return self.db.query(self.model_class).all()
    
    def create(self, entity: T) -> T:
        """
        Create a new entity
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update(self, entity: T) -> T:
        """
        Update an existing entity
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def delete(self, entity: T) -> None:
        """
        Delete an entity
        """
        self.db.delete(entity)
        self.db.commit()
    
    def delete_by_id(self, id: Any) -> bool:
        """
        Delete an entity by its ID
        Returns True if entity was found and deleted, False otherwise
        """
        entity = self.get_by_id(id)
        if entity:
            self.delete(entity)
            return True
        return False