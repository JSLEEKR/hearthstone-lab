import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.tables import Base


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
