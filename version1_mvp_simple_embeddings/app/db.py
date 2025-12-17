"""
Neo4j driver management for the minimal MVP.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from neo4j import AsyncGraphDatabase, AsyncDriver

from .config import get_settings


_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    """
    Lazily create and cache the Neo4j async driver.
    """
    global _driver  # noqa: PLW0603
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


@asynccontextmanager
async def neo4j_session() -> AsyncIterator:
    """
    Provide an async Neo4j session as a context manager.
    """
    driver = get_driver()
    async with driver.session() as session:
        yield session



