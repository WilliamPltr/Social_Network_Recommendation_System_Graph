"""
FastAPI application exposing graph-based recommendation endpoints.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from neo4j import AsyncSession

from app.config import get_settings
from app.db import neo4j_session
from app.models import Job, RecommendationResponse, User
from app.recommendation import (
    get_friend_recommendations,
    get_friend_counts,
    get_job_recommendations,
    get_people_you_may_know,
)


app = FastAPI(
    title="Professional Social Network Graph API",
    description="Neo4j-backed LinkedIn-style recommendation service.",
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

    direct_count, fof_count = await get_friend_counts(session, user_id)

    if not friends:
        raise HTTPException(status_code=404, detail="No friend recommendations found")

    return RecommendationResponse(
        user=User(user_id=user_id),
        friends=friends,
        direct_friends_count=direct_count,
        friends_of_friends_count=fof_count,
    )


@app.get("/api/users/{user_id}/suggestions/people", response_model=RecommendationResponse)
async def suggest_people(
    user_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    """'People you may know' suggestions using Pearson correlation on features."""
    recs = await get_people_you_may_know(session, user_id, limit)
    people = [
        User(user_id=uid, name=name, score=float(score)) for uid, name, score in recs
    ]

    if not people:
        raise HTTPException(status_code=404, detail="No suggestions found")

    return RecommendationResponse(user=User(user_id=user_id), people_you_may_know=people)


@app.get("/api/users/{user_id}/recommendations/jobs", response_model=RecommendationResponse)
async def recommend_jobs(
    user_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    """
    Job recommendations based on embeddings stored on :User and :Job nodes.

    The mapping from SNAP features to user embeddings and from LinkedIn titles
    to job embeddings is handled by offline ETL scripts.
    """
    recs = await get_job_recommendations(session, user_id, limit)
    jobs: List[Job] = [
        Job(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            job_posting_url=None,  # filled in UI from Neo4j, kept simple here
            normalized_salary=normalized_salary,
            score=score,
        )
        for job_id, title, company, location, normalized_salary, score in recs
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
    """Simple health-check endpoint used by Docker Desktop and external probes."""
    return {"status": "ok"}


@app.get("/api/debug/stats")
async def debug_stats(session: AsyncSession = Depends(get_session)) -> dict:
    """
    Diagnostic endpoint to check Neo4j connection and data counts.
    Useful for debugging why data might not be visible.
    """
    try:
        # Test connection
        test_query = "RETURN 1 AS test"
        result = await session.run(test_query)
        await result.single()
        connection_ok = True
    except Exception as e:
        return {
            "connection_ok": False,
            "error": str(e),
            "neo4j_uri": get_settings().neo4j_uri,
        }

    # Count nodes
    user_count_query = "MATCH (u:User) RETURN count(u) AS cnt"
    job_count_query = "MATCH (j:Job) RETURN count(j) AS cnt"
    knows_count_query = "MATCH ()-[r:KNOWS]->() RETURN count(r) AS cnt"
    user_with_features_query = "MATCH (u:User) WHERE u.features IS NOT NULL RETURN count(u) AS cnt"
    user_with_embedding_query = "MATCH (u:User) WHERE u.embedding IS NOT NULL RETURN count(u) AS cnt"
    job_with_embedding_query = "MATCH (j:Job) WHERE j.embedding IS NOT NULL RETURN count(j) AS cnt"

    stats = {"connection_ok": True, "neo4j_uri": get_settings().neo4j_uri}

    try:
        result = await session.run(user_count_query)
        record = await result.single()
        stats["user_count"] = record["cnt"] if record else 0
    except Exception as e:
        stats["user_count_error"] = str(e)

    try:
        result = await session.run(job_count_query)
        record = await result.single()
        stats["job_count"] = record["cnt"] if record else 0
    except Exception as e:
        stats["job_count_error"] = str(e)

    try:
        result = await session.run(knows_count_query)
        record = await result.single()
        stats["knows_relationships_count"] = record["cnt"] if record else 0
    except Exception as e:
        stats["knows_relationships_error"] = str(e)

    try:
        result = await session.run(user_with_features_query)
        record = await result.single()
        stats["users_with_features"] = record["cnt"] if record else 0
    except Exception as e:
        stats["users_with_features_error"] = str(e)

    try:
        result = await session.run(user_with_embedding_query)
        record = await result.single()
        stats["users_with_embedding"] = record["cnt"] if record else 0
    except Exception as e:
        stats["users_with_embedding_error"] = str(e)

    try:
        result = await session.run(job_with_embedding_query)
        record = await result.single()
        stats["jobs_with_embedding"] = record["cnt"] if record else 0
    except Exception as e:
        stats["jobs_with_embedding_error"] = str(e)

    # Sample user IDs
    try:
        sample_query = "MATCH (u:User) RETURN u.id AS id, u.name AS name LIMIT 5"
        result = await session.run(sample_query)
        records = await result.data()
        stats["sample_users"] = [{"id": r["id"], "name": r.get("name")} for r in records]
    except Exception as e:
        stats["sample_users_error"] = str(e)

    return stats


@app.get("/api/users/search", response_model=list[User])
async def search_users(
    q: str = Query(..., description="User id or part of the user name"),
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    """
    Search users by numeric id or case-insensitive name substring.
    """
    query = """
    MATCH (u:User)
    WHERE toString(u.id) = $q
       OR toLower(u.name) CONTAINS toLower($q)
    RETURN u.id AS id, u.name AS name
    LIMIT $limit
    """
    result = await session.run(query, q=q, limit=limit)
    records = await result.data()
    return [User(user_id=r["id"], name=r.get("name")) for r in records]


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """
    Simple UI to explore recommendations and shortest paths.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>Professional Graph Explorer</title>
      <style>
        body { font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; background: #0f172a; color: #e5e7eb; }
        header { padding: 16px 24px; background: #020617; border-bottom: 1px solid #1f2937; }
        h1 { margin: 0; font-size: 20px; }
        main { max-width: 1100px; margin: 24px auto; padding: 0 16px 32px; }
        section { background: #020617; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; border: 1px solid #1f2937; }
        section h2 { margin-top: 0; font-size: 18px; }
        label { display: block; margin-bottom: 4px; font-size: 13px; color: #9ca3af; }
        input[type="text"], input[type="number"] {
          width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid #374151;
          background: #020617; color: #e5e7eb; box-sizing: border-box; margin-bottom: 8px;
        }
        input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }
        button {
          background: #3b82f6; color: white; border: none; border-radius: 20px; padding: 8px 16px;
          font-size: 14px; cursor: pointer; margin-top: 4px;
        }
        button:hover { background: #2563eb; }
        .row { display: flex; flex-wrap: wrap; gap: 16px; }
        .col { flex: 1 1 260px; }
        ul { list-style: none; padding-left: 0; margin: 8px 0 0; font-size: 14px; }
        li { padding: 4px 0; border-bottom: 1px solid #111827; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; background: #111827; color: #9ca3af; margin-left: 6px; }
        .error { color: #f97316; font-size: 13px; margin-top: 4px; }
        .small { font-size: 12px; color: #6b7280; }
        code { background: #111827; padding: 2px 4px; border-radius: 4px; }
      </style>
    </head>
    <body>
      <header>
        <h1>Professional Social Graph Explorer</h1>
        <p class="small">Search users by name or id, see recommendations, and compute shortest paths.</p>
      </header>
      <main>
        <section>
          <h2>User recommendations</h2>
          <div class="row">
            <div class="col" style="max-width: 280px; flex: 0 0 260px;">
              <label for="userQuery">User name or id</label>
              <input id="userQuery" type="text" placeholder="e.g. 42 or benji" />
              <button onclick="loadRecommendations()">Load recommendations</button>
              <div id="userError" class="error"></div>
              <div id="userCard" style="margin-top: 10px; padding: 10px 12px; border-radius: 10px; background:#020617; border:1px solid #1f2937; display:none;">
                <div style="font-weight:600;" id="userName"></div>
                <div class="small" id="userId"></div>
                <div class="small" id="userStats"></div>
              </div>
            </div>
            <div class="col">
              <strong>Friends (mutual connections)</strong>
              <ul id="friendsList"></ul>
            </div>
            <div class="col">
              <strong>People you may know (Pearson on features)</strong>
              <ul id="peopleList"></ul>
            </div>
          </div>
          <div class="row" style="margin-top: 8px;">
            <div class="col">
              <strong>Job recommendations (embeddings)</strong>
              <ul id="jobsList"></ul>
            </div>
          </div>
        </section>

        <section>
          <h2>Shortest path between professionals</h2>
          <div class="row">
            <div class="col">
              <label for="fromQuery">From (name or id)</label>
              <input id="fromQuery" type="text" placeholder="e.g. 10 or bob" />
            </div>
            <div class="col">
              <label for="toQuery">To (name or id)</label>
              <input id="toQuery" type="text" placeholder="e.g. 99 or carol" />
            </div>
          </div>
          <button onclick="loadShortestPath()">Compute shortest path</button>
          <div id="pathError" class="error"></div>
          <div id="pathResult" class="small"></div>
        </section>
      </main>

      <script>
        async function resolveUser(query) {
          // Try numeric id first
          if (/^\\d+$/.test(query.trim())) {
            return { user_id: parseInt(query.trim(), 10), name: null };
          }
          const resp = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
          if (!resp.ok) return null;
          const data = await resp.json();
          return data[0] || null;
        }

        async function loadRecommendations() {
          const q = document.getElementById("userQuery").value;
          const errEl = document.getElementById("userError");
          const userCard = document.getElementById("userCard");
          const userName = document.getElementById("userName");
          const userId = document.getElementById("userId");
          const userStats = document.getElementById("userStats");
          const friendsEl = document.getElementById("friendsList");
          const peopleEl = document.getElementById("peopleList");
          const jobsEl = document.getElementById("jobsList");
          errEl.textContent = "";
          userCard.style.display = "none";
          userName.textContent = "";
          userId.textContent = "";
          userStats.textContent = "";
          friendsEl.innerHTML = "";
          peopleEl.innerHTML = "";
          jobsEl.innerHTML = "";

          if (!q.trim()) {
            errEl.textContent = "Please enter a name or id.";
            return;
          }

          const user = await resolveUser(q);
          if (!user) {
            errEl.textContent = "User not found.";
            return;
          }

          userCard.style.display = "block";
          userName.textContent = user.name || "Unknown user";
          userId.textContent = `id: ${user.user_id}`;

          try {
            const [friendsResp, peopleResp, jobsResp] = await Promise.all([
              fetch(`/api/users/${user.user_id}/recommendations/friends`),
              fetch(`/api/users/${user.user_id}/suggestions/people`),
              fetch(`/api/users/${user.user_id}/recommendations/jobs`),
            ]);

            if (friendsResp.ok) {
              const data = await friendsResp.json();
              if (data.direct_friends_count != null || data.friends_of_friends_count != null) {
                const parts = [];
                if (data.direct_friends_count != null) {
                  parts.push(`friends: ${data.direct_friends_count}`);
                }
                if (data.friends_of_friends_count != null) {
                  parts.push(`friends of friends: ${data.friends_of_friends_count}`);
                }
                userStats.textContent = parts.join(" • ");
              }
              (data.friends || []).forEach((u) => {
                const li = document.createElement("li");
                li.textContent = `${u.user_id}` + (u.name ? ` – ${u.name}` : "");
                if (u.score != null) {
                  const span = document.createElement("span");
                  span.className = "badge";
                  span.textContent = `${u.score} mutuals`;
                  li.appendChild(span);
                }
                friendsEl.appendChild(li);
              });
            }

            if (peopleResp.ok) {
              const data = await peopleResp.json();
              (data.people_you_may_know || []).forEach((u) => {
                const li = document.createElement("li");
                li.textContent = `${u.user_id}` + (u.name ? ` – ${u.name}` : "");
                if (u.score != null) {
                  const span = document.createElement("span");
                  span.className = "badge";
                  span.textContent = `corr ${u.score.toFixed(3)}`;
                  li.appendChild(span);
                }
                peopleEl.appendChild(li);
              });
            }

            if (jobsResp.ok) {
              const data = await jobsResp.json();
              (data.jobs || []).forEach((j) => {
                const li = document.createElement("li");
                if (j.job_posting_url) {
                  li.style.cursor = "pointer";
                  li.onclick = () => {
                    window.open(j.job_posting_url, "_blank", "noopener");
                  };
                }
                const main = document.createElement("div");
                main.textContent = `${j.title}` + (j.company ? ` @ ${j.company}` : "");

                const meta = document.createElement("div");
                meta.className = "small";
                const parts = [];
                if (j.location) parts.push(j.location);
                if (j.normalized_salary != null) {
                  parts.push(`normalized salary: ${j.normalized_salary.toFixed(0)}`);
                }
                if (parts.length) {
                  meta.textContent = parts.join(" • ");
                }

                const actions = document.createElement("div");
                const scoreSpan = document.createElement("span");
                scoreSpan.className = "badge";
                scoreSpan.textContent = `score ${j.score.toFixed(3)}`;
                actions.appendChild(scoreSpan);
                if (j.job_posting_url) {
                  const link = document.createElement("a");
                  link.href = j.job_posting_url;
                  link.target = "_blank";
                  link.rel = "noopener noreferrer";
                  link.textContent = "View job posting";
                  link.style.marginLeft = "8px";
                  link.className = "small";
                  actions.appendChild(link);
                }

                li.appendChild(main);
                if (meta.textContent) li.appendChild(meta);
                li.appendChild(actions);
                jobsEl.appendChild(li);
              });
            }
          } catch (e) {
            console.error(e);
            errEl.textContent = "Error while loading recommendations.";
          }
        }

        async function loadShortestPath() {
          const fromQ = document.getElementById("fromQuery").value;
          const toQ = document.getElementById("toQuery").value;
          const errEl = document.getElementById("pathError");
          const resEl = document.getElementById("pathResult");
          errEl.textContent = "";
          resEl.textContent = "";

          if (!fromQ.trim() || !toQ.trim()) {
            errEl.textContent = "Please fill both ends of the path.";
            return;
          }

          const fromUser = await resolveUser(fromQ);
          const toUser = await resolveUser(toQ);

          if (!fromUser || !toUser) {
            errEl.textContent = "Could not resolve one or both users.";
            return;
          }

          try {
            const resp = await fetch(`/api/paths/shortest?from_user=${fromUser.user_id}&to_user=${toUser.user_id}`);
            if (!resp.ok) {
              errEl.textContent = "No path found.";
              return;
            }
            const data = await resp.json();
            resEl.textContent = `Path (user ids): ${data.path.join(" → ")}`;
          } catch (e) {
            console.error(e);
            errEl.textContent = "Error while computing path.";
          }
        }
      </script>
    </body>
    </html>
    """


