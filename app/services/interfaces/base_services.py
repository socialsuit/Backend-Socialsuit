# services/interfaces/base_service.py
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class BaseService(ABC):
    def __init__(self, db: Session):
        self.db = db