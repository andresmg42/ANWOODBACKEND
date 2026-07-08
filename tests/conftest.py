import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import RoleEnum, assign_role_to_user, get_password_hash
from app.database import get_session
from app.main import app
from app.models import User
from app.seed import seed_data

TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "adminpass"
TEST_USER_USERNAME = "regular_user"
TEST_USER_PASSWORD = "userpass"


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        seed_data(session)

        admin = User(
            username=TEST_ADMIN_USERNAME,
            email="admin@test.com",
            hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        assign_role_to_user(admin, RoleEnum.ADMIN, session)

        regular_user = User(
            username=TEST_USER_USERNAME,
            email="user@test.com",
            hashed_password=get_password_hash(TEST_USER_PASSWORD),
        )
        session.add(regular_user)
        session.commit()
        session.refresh(regular_user)
        assign_role_to_user(regular_user, RoleEnum.USER, session)

        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient) -> str:
    response = client.post(
        "/token",
        data={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(client: TestClient) -> str:
    response = client.post(
        "/token",
        data={"username": TEST_USER_USERNAME, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}
