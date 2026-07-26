import ssl as ssl_module
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

database_url = settings.database_url

# Auto-convert postgresql:// to postgresql+asyncpg:// for async driver
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args: dict = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "postgresql" in database_url:
    # Strip query params asyncpg doesn't understand, use SSL context instead
    database_url = database_url.split("?")[0]
    ssl_context = ssl_module.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl_module.CERT_NONE
    connect_args = {"ssl": ssl_context}

engine = create_async_engine(database_url, echo=settings.debug, connect_args=connect_args)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
