from httpx import AsyncClient, ASGITransport
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models import Base, User
from api.database import async_get_db as get_db_session
from api.main import app_api as api

DATABASE_URL_TEST = f"postgresql+asyncpg://admin:admin@localhost:5433/test_micro_blogs"


@pytest.fixture()
async def db_session():
    engine = create_async_engine(DATABASE_URL_TEST, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        test_user = User(name="Anton", api_key="test")
        new_user = User(name="Ivan", api_key="test_key")
        session.add(test_user)
        session.add(new_user)
        yield session
        await session.close()


@pytest.fixture()
def test_app(db_session: AsyncSession):
    api.dependency_overrides[get_db_session] = lambda: db_session
    return api


@pytest.fixture()
async def async_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost:8000/",
        headers={"api-key": "test"},
    ) as client:
        yield client
