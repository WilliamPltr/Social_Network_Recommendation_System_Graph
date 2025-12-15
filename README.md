# Social Network Recommendation System

Use Case: Build a LinkedIn-style professional network

* Graph Model: Users, Skills, Companies, Connections (KNOWS, WORKS_AT, HAS_SKILL)

* API Features:

  * Friend recommendations based on mutual connections
    * e.g. GET `/api/users/{user_id}/recommendations/friends`

  * Job recommendations based on skills graph
    * e.g. GET `/api/users/{user_id}/recommendations/jobs`

  * "People you may know" algorithm
    * e.g. GET `/api/users/{user_id}/suggestions/people`

* Shortest path between professionals
    * e.g. GET `/api/paths/shortest?from={user_id_a}&to={user_id_b}`

Difficulty: 2

## Data Sources

1. SNAP (Stanford Network Analysis Project) - GitHub Developers

    * URL: https://snap.stanford.edu/data/github-social.html
    * 138k+ developers with follower relationships

2. Twitch/Deezer Social Networks (Benedek Rozemberczki)

    * GitHub: https://github.com/benedekrozemberczki/datasets

    * Multiple social networks (Twitch gamers, Deezer users)

    * Includes user features and follower relationships

3. Sample Social Network Datasets

    * GitHub: https://github.com/melaniewalsh/sample-social-network-datasets

    * Curated collection for teaching (Jazz musicians, Marvel characters, etc.)


