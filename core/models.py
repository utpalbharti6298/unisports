"""
Core Application Models & Architectural Specification.

UniSports utilizes MongoDB document collections via MongoEngine ODM across domain apps:
- `accounts.models.User` (Role-based access & authentication)
- `universities.models.University` (Participating athletic institutions)
- `sports.models.Sport` (Disciplines & tournament scoring points)
- `tournaments.models.Tournament` & `Fixture` (Championships & matches)
- `analytics.models.RankingSnapshot` (Cached leaderboard projections)

The `core` application serves as the system orchestrator, homepage dashboard,
head-to-head comparative engine, and global template context processor.
"""
