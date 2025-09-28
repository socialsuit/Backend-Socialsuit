import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.database.database import Base

@pytest.fixture(scope="session")
def engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables):
    """Returns an sqlalchemy session, and after the test tears down everything."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()