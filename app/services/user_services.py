# services/user_service.py
from sqlalchemy.orm import Session
from app.services.models.user_model import User
import uuid
from datetime import datetime

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_wallet(db: Session, wallet_address: str):
    return db.query(User).filter(User.wallet_address == wallet_address).first()

def create_user_with_email(db: Session, email: str, hashed_password: str):
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hashed_password,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_user_with_wallet(db: Session, wallet_address: str, network: str):
    user = User(
        id=str(uuid.uuid4()),
        wallet_address=wallet_address,
        network=network,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_last_login(db: Session, user: User):
    user.last_login = datetime.utcnow()
    db.commit()
