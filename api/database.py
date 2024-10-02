from dotenv import dotenv_values
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

config = dotenv_values(".env.docker")

DB_USER = config.get("POSTGRES_USER", "user")
DB_PASSWORD = config.get("POSTGRES_PASSWORD", "password")
DB_NAME = config.get("POSTGRES_DB", "db")

SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@postgres:5432/{DB_NAME}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()

async def async_get_db():
    session = async_session
    async with session() as db:
        try:
            yield db
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
