"""
Configuration utilities for this minimal MVP application.
"""

from functools import lru_cache
import os
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()



