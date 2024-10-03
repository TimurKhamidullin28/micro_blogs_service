from typing import AsyncGenerator
from dotenv import dotenv_values
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.database import Base
from api.database import async_get_db as get_db_session
from api.main import app_api as api
from api.models import User

config = dotenv_values(".env.test")

DB_USER = config.get("POSTGRES_USER", "user")
DB_PASSWORD = config.get("POSTGRES_PASSWORD", "password")
DB_NAME = config.get("POSTGRES_DB", "db")

DATABASE_URL_TEST = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@postgres_test:5432/{DB_NAME}"

engine = create_async_engine(DATABASE_URL_TEST, echo=True)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base.metadata.bind = engine


def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    with async_session_maker() as session:
        yield session

api.dependency_overrides[get_db_session] = override_get_async_session

@pytest_asyncio.fixture(autouse=True, scope="session")
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        first_user = User(name="Ivan", api_key="test-key-ivan")
        second_user = User(name="Anton", api_key="test-anton-key")
        session.add(first_user)
        session.add(second_user)
        await session.close()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=api)
    async with AsyncClient(
            transport=transport,
            base_url="http://localhost:8000/",
            headers={"api-key": "test"},
    ) as client:
        yield client
