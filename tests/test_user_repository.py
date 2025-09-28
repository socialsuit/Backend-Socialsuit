import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

from services.models.user_model import User
from services.repositories.user_repository import UserRepository
from tests.utils import mock_db_session, user_repository

# Sample test data
@pytest.fixture
def sample_user():
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password_here",
        wallet_address=None,
        network=None,
        is_verified=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )

@pytest.fixture
def sample_wallet_user():
    return User(
        id=uuid.uuid4(),
        email=None,
        hashed_password=None,
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        network="ethereum",
        is_verified=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )

# Test cases
def test_get_by_id(user_repository, sample_user):
    # Setup
    user_id = str(sample_user.id)
    user_repository.db.query().filter().first.return_value = sample_user
    
    # Execute
    result = user_repository.get_by_id(user_id)
    
    # Assert
    assert result == sample_user
    user_repository.db.query.assert_called_once_with(User)

def test_get_by_email(user_repository, sample_user):
    # Setup
    email = sample_user.email
    user_repository.db.query().filter().first.return_value = sample_user
    
    # Execute
    result = user_repository.get_by_email(email)
    
    # Assert
    assert result == sample_user
    user_repository.db.query.assert_called_once_with(User)

def test_get_by_wallet(user_repository, sample_wallet_user):
    # Setup
    wallet_address = sample_wallet_user.wallet_address
    network = sample_wallet_user.network
    user_repository.db.query().filter().first.return_value = sample_wallet_user
    
    # Execute
    result = user_repository.get_by_wallet(wallet_address, network)
    
    # Assert
    assert result == sample_wallet_user
    user_repository.db.query.assert_called_once_with(User)

def test_get_by_email_or_wallet_with_email(user_repository, sample_user):
    # Setup
    email = sample_user.email
    user_repository.db.query().filter().first.return_value = sample_user
    
    # Execute
    result = user_repository.get_by_email_or_wallet(email=email)
    
    # Assert
    assert result == sample_user
    user_repository.db.query.assert_called_once_with(User)

def test_get_by_email_or_wallet_with_wallet(user_repository, sample_wallet_user):
    # Setup
    wallet_address = sample_wallet_user.wallet_address
    network = sample_wallet_user.network
    user_repository.db.query().filter().first.return_value = sample_wallet_user
    
    # Execute
    result = user_repository.get_by_email_or_wallet(wallet_address=wallet_address, network=network)
    
    # Assert
    assert result == sample_wallet_user
    user_repository.db.query.assert_called_once_with(User)

def test_get_verified_users(user_repository, sample_user):
    # Setup
    user_repository.db.query().filter().all.return_value = [sample_user]
    
    # Execute
    result = user_repository.get_verified_users()
    
    # Assert
    assert result == [sample_user]
    user_repository.db.query.assert_called_once_with(User)

def test_create_user(user_repository, sample_user):
    # Setup
    user_repository.db.add = MagicMock()
    user_repository.db.commit = MagicMock()
    user_repository.db.refresh = MagicMock()
    
    # Execute
    result = user_repository.create(sample_user)
    
    # Assert
    assert result == sample_user
    user_repository.db.add.assert_called_once_with(sample_user)
    user_repository.db.commit.assert_called_once()
    user_repository.db.refresh.assert_called_once_with(sample_user)

def test_update_user(user_repository, sample_user):
    # Setup
    user_repository.db.add = MagicMock()
    user_repository.db.commit = MagicMock()
    user_repository.db.refresh = MagicMock()
    
    # Execute
    result = user_repository.update(sample_user)
    
    # Assert
    assert result == sample_user
    user_repository.db.add.assert_called_once_with(sample_user)
    user_repository.db.commit.assert_called_once()
    user_repository.db.refresh.assert_called_once_with(sample_user)

def test_delete_user(user_repository, sample_user):
    # Setup
    user_repository.db.delete = MagicMock()
    user_repository.db.commit = MagicMock()
    
    # Execute
    user_repository.delete(sample_user)
    
    # Assert
    user_repository.db.delete.assert_called_once_with(sample_user)
    user_repository.db.commit.assert_called_once()

def test_delete_user_by_id(user_repository, sample_user):
    # Setup
    user_id = str(sample_user.id)
    user_repository.get_by_id = MagicMock(return_value=sample_user)
    user_repository.delete = MagicMock()
    
    # Execute
    user_repository.delete_by_id(user_id)
    
    # Assert
    user_repository.get_by_id.assert_called_once_with(user_id)
    user_repository.delete.assert_called_once_with(sample_user)