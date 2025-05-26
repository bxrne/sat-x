from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

# Create the async engine
engine = create_async_engine(
    settings.database.url,  # Use the string URL directly
    echo=settings.database.echo,
    pool_pre_ping=True,  # Good practice for reliability
    # connect_args are important for SQLite with asyncio/multithreading
    # to prevent "SQLite objects created in a thread can only be used in that same thread"
    # The check_same_thread=False is specific to sqlite3 driver used by aiosqlite
    connect_args={"check_same_thread": False}
)

# Create a configured "Session" class
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Recommended for async sessions
    class_=AsyncSession
)

# Base class for declarative models
class Base(DeclarativeBase):
    pass

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to provide a database session per request."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            # Optional: await session.commit() if auto-commit needed per request
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close() # Ensure connection is returned to the pool

async def init_db(engine_instance):
    """Initialize the database (create tables). Should be run once at startup."""
    async with engine_instance.begin() as conn:
        # This requires all models to be imported before calling init_db
        # A common pattern is to import them in models/__init__.py
        # and then import models here.
        # from . import models # Assuming models are defined in models.py or models/
        # await conn.run_sync(Base.metadata.drop_all) # Use with caution!
        await conn.run_sync(Base.metadata.create_all)
    await engine_instance.dispose() # Dispose of the engine after init
