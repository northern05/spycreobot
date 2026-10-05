from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.core.config import db_config


class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False):
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            pool_recycle=1800,
            future=True
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def scoped_session_dependency(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


db_helper = DatabaseHelper(
    url=db_config.SQLALCHEMY_DATABASE_URL,
    echo=db_config.db_echo,
)