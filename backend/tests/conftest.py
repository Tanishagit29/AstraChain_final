import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.all_models  # noqa
from app.main import app
from app.database.base import Base
from app.database.session import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 60}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Run seed script on test DB
    import app.database.session as session_mod
    orig_engine = session_mod.engine
    orig_session = session_mod.SessionLocal
    session_mod.engine = engine
    session_mod.SessionLocal = TestingSessionLocal
    
    from app.database.seed import seed_database
    seed_database()
    
    session_mod.engine = orig_engine
    session_mod.SessionLocal = orig_session

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "multi_agent_tester@astrachain.ai",
            "password": "SecretPassword123!",
            "full_name": "Multi Agent Tester",
            "role": "OPERATIONS_LEAD"
        }
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "multi_agent_tester@astrachain.ai", "password": "SecretPassword123!"}
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
