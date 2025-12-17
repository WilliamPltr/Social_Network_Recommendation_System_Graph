"""
FastAPI application for the minimal MVP snapshot.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException
from neo4j import AsyncSession

from .db import neo4j_session
from .models import Job, RecommendationResponse, User
from .recommendation import get_friend_recommendations, get_job_recommendations


app = FastAPI(
    title="Professional Social Network Graph API",
    description="Minimal snapshot with very simple job embeddings.",
    version="0.1.0",
)


async def get_session() -> AsyncSession:
    """Dependency to inject a Neo4j session."""
    async with neo4j_session() as session:
        yield session


@app.get("/api/users/{user_id}/recommendations/friends", response_model=RecommendationResponse)
async def recommend_friends(
    user_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    """Friend recommendations based on mutual connections."""
    recs = await get_friend_recommendations(session, user_id, limit)
    friends: List[User] = [
        User(user_id=uid, name=name, score=float(mutuals))
        for uid, name, mutuals in recs
    ]

    if not friends:
        raise HTTPException(status_code=404, detail="No friend recommendations found")

    return RecommendationResponse(user=User(user_id=user_id), friends=friends)


@app.get("/api/users/{user_id}/recommendations/jobs", response_model=RecommendationResponse)
async def recommend_jobs(
    user_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    """
    Job recommendations based on extremely simple skill-based embeddings.
    """
    recs = await get_job_recommendations(session, user_id, limit)
    jobs: List[Job] = [
        Job(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            score=score,
        )
        for job_id, title, company, location, score in recs
    ]

    if not jobs:
        raise HTTPException(status_code=404, detail="No job recommendations found")

    return RecommendationResponse(user=User(user_id=user_id), jobs=jobs)


@app.get("/api/paths/shortest")
async def shortest_path(
    from_user: int,
    to_user: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Shortest path between professionals using the KNOWS graph.
    Returns the sequence of user ids on the path.
    """
    query = """
    MATCH (a:User {id: $from_id}), (b:User {id: $to_id}),
          p = shortestPath((a)-[:KNOWS*..6]-(b))
    RETURN [n IN nodes(p) | n.id] AS path
    """
    result = await session.run(query, from_id=from_user, to_id=to_user)
    record = await result.single()
    if record is None:
        raise HTTPException(status_code=404, detail="No path found")
    return {"path": record["path"]}


@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}



