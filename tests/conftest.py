import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from app.database import get_session
from app.app import app
from app.models import table_registry

# URL do banco de testes (pode usar um database separado)
TEST_DATABASE_URL = "postgresql+psycopg://postgres:Henry2407@localhost:5432/medico_test"

@pytest.fixture(scope="session")
def engine():
    # Cria o banco de testes se não existir
    if not database_exists(TEST_DATABASE_URL):
        create_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    table_registry.metadata.create_all(bind=engine)
    yield engine
    table_registry.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(engine):
    # Cria uma sessão para cada teste e faz rollback no final (isolamento)
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()