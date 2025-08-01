from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from ..core.config import settings

engine = create_async_engine(settings.postgres_url, echo=False)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()
