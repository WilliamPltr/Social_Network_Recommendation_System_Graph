"""
Pydantic models for API payloads and responses.
"""

from typing import List, Optional
from pydantic import BaseModel


class User(BaseModel):
    """Basic user representation."""

    user_id: int
    name: Optional[str] = None
    score: Optional[float] = None


class Job(BaseModel):
    """Job representation for API responses."""

    job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_posting_url: Optional[str] = None
    normalized_salary: Optional[float] = None
    score: float


class RecommendationResponse(BaseModel):
    """Generic recommendation wrapper."""

    user: User
    friends: List[User] | None = None
    people_you_may_know: List[User] | None = None
    jobs: List[Job] | None = None
    direct_friends_count: Optional[int] = None
    friends_of_friends_count: Optional[int] = None

