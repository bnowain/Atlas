"""Async SQLAlchemy engine + session factory for Atlas (SQLite/WAL via aiosqlite)."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an async session."""
    async with AsyncSessionLocal() as session:
        yield session


async def validate_schema_columns():
    """Compare ORM model columns against the live database and auto-add
    any missing nullable columns.  Logs errors for non-nullable columns
    that require manual migration.  Safe to call on every startup.
    """
    async with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            rows = await conn.execute(text(f"PRAGMA table_info('{table_name}')"))
            rows = rows.fetchall()
            if not rows:
                continue

            existing_cols = {row[1] for row in rows}
            for col in table.columns:
                if col.name in existing_cols:
                    continue

                col_type = str(col.type)

                if col.nullable:
                    await conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                    ))
                    logger.warning(
                        "Schema drift fixed: added %s.%s (%s)",
                        table_name, col.name, col_type,
                    )
                else:
                    logger.error(
                        "Schema drift detected: %s.%s (%s) is NOT NULL — "
                        "requires manual migration",
                        table_name, col.name, col_type,
                    )


# WAL + foreign-key pragmas on every raw connection
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
