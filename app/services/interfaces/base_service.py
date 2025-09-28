from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class BaseService(ABC):
    """
    Base service class that all service implementations should inherit from.
    Provides a consistent interface for dependency injection of database sessions.
    """
    def __init__(self, db: Session):
        self.db = db