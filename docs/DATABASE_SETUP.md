# Supabase PostgreSQL Database Setup & Configuration

This guide provides the complete documentation for connecting the College OWASP CTF Platform backend to **Supabase PostgreSQL**, running database migrations with Alembic, and maintaining production schema integrity.

---

## 1. Overview & Architecture

The CTF Platform backend connects to Supabase PostgreSQL using:
- **SQLAlchemy 2.0+** ORM for relational queries, relationships, and connection pooling.
- **psycopg (v3)** asynchronous/synchronous PostgreSQL DBAPI driver.
- **Alembic** migration management ensuring zero data-loss, versioned, reproducible DDL migrations.

```
+-------------------------------------------------------------+
|                     FastAPI Application                     |
|           (Authentication, Scoring, Events, RBAC)           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                      SQLAlchemy 2.0                         |
|         (Connection Pooling, Session Lifecycle)            |
+-------------------------------------------------------------+
                              | (psycopg3 driver)
                              v
+-------------------------------------------------------------+
|                     Supabase PostgreSQL                     |
|            (db.<project-ref>.supabase.co:5432)              |
|        23 Application Tables + 45 Foreign Keys + 145 Idxs   |
+-------------------------------------------------------------+
```

---

## 2. Environment Configuration

Set the database connection string in your `backend/.env` file:

```bash
# Standard Supabase Direct PostgreSQL Connection:
DATABASE_URL=postgresql://postgres:<YOUR_PASSWORD>@db.<YOUR_PROJECT_REF>.supabase.co:5432/postgres

# Connection Pool Settings (Configured in backend/app/config.py)
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
```

> [!IMPORTANT]
> **Password URL Encoding**: If your database password contains reserved URI characters (such as `@`, `:`, `/`, `?`, `#`), URL-encode them. For example, `@` becomes `%40`.
>
> **Protocol Normalization**: The backend automatically normalizes `postgres://` or `postgresql://` connection strings to `postgresql+psycopg://` to use the modern psycopg v3 driver seamlessly.

---

## 3. Running Database Migrations

All schema definitions are managed through Alembic revisions located in `backend/alembic/versions/`.

To apply all migrations to Supabase PostgreSQL:

```bash
cd backend
python -m alembic upgrade head
```

To verify current database head:

```bash
python -m alembic current
```

---

## 4. Schema Inventory

The database contains **23 application tables** spanning all CTF platform features:

| Table Name | Description | Primary Key | Foreign Keys | Key Indexes |
| :--- | :--- | :--- | :--- | :--- |
| `users` | User accounts, credentials, RBAC roles, moderation state (`is_banned`, `is_muted`) | `id` (UUID) | None | `username`, `email`, `role`, `is_active` |
| `categories` | Challenge categories (e.g. Web Exploitation, Reverse Eng) | `id` (UUID) | None | `name` (unique) |
| `challenges` | CTF challenges, dynamic scoring formulas, difficulty, tags | `id` (UUID) | `category_id` | `category_id`, `is_active`, `title` |
| `challenge_files` | Challenge attachment artifacts and hashes | `id` (UUID) | `challenge_id` | `challenge_id` |
| `challenge_hints` | Tiered hints with point deduction cost | `id` (UUID) | `challenge_id` | `challenge_id`, `order` |
| `challenge_writeups` | Official author writeups (locked until solved/ended) | `id` (UUID) | `challenge_id`, `user_id` | `challenge_id` |
| `submissions` | Authoritative audit log of every flag submission | `id` (UUID) | `user_id`, `challenge_id`, `team_id`, `event_id` | `user_id`, `challenge_id`, `created_at` |
| `solves` | Unique solves ledger preventing duplicate points | `id` (UUID) | `user_id`, `challenge_id`, `team_id`, `event_id` | `(user_id, challenge_id)`, `created_at` |
| `hint_usage` | Recorded hint unlocks and deducted penalty ledger | `id` (UUID) | `user_id`, `hint_id`, `team_id` | `(user_id, hint_id)` |
| `teams` | Student teams for collaborative CTFs | `id` (UUID) | `captain_id` | `name` (unique), `invite_code` |
| `team_members` | Team membership mapping and roles | `id` (UUID) | `team_id`, `user_id` | `(team_id, user_id)` |
| `events` | Timed CTF competitions and scoreboard freezing | `id` (UUID) | `created_by` | `slug` (unique), `start_at`, `end_at` |
| `event_challenges` | Event-challenge association and point overrides | `id` (UUID) | `event_id`, `challenge_id` | `(event_id, challenge_id)` |
| `event_registrations` | User/team registrations for competitions | `id` (UUID) | `event_id`, `user_id`, `team_id` | `(event_id, user_id)`, `(event_id, team_id)` |
| `user_activities` | User action activity feed & timeline | `id` (UUID) | `user_id` | `user_id`, `created_at` |
| `badges` | System achievements and milestone badges | `id` (UUID) | None | `slug` (unique), `category` |
| `user_badges` | User-earned badge association ledger | `id` (UUID) | `user_id`, `badge_id` | `(user_id, badge_id)` |
| `discussions` | Challenge community threads & forums | `id` (UUID) | `challenge_id`, `user_id` | `challenge_id`, `user_id`, `created_at` |
| `discussion_comments` | Hierarchical replies on discussion threads | `id` (UUID) | `discussion_id`, `user_id`, `parent_id` | `discussion_id`, `user_id`, `created_at` |
| `notifications` | In-app user notifications with read state | `id` (UUID) | `user_id` | `user_id`, `is_read`, `created_at` |
| `security_events` | Anti-cheat detection, brute-force logs, flag sharing alerts | `id` (UUID) | `user_id`, `challenge_id` | `user_id`, `event_type`, `severity` |
| `security_event_reviews` | Admin anti-cheat investigation notes & dispositions | `id` (UUID) | `security_event_id`, `reviewer_id` | `security_event_id` |
| `challenge_instances` | Live on-demand Docker container challenge instances | `id` (UUID) | `user_id`, `challenge_id`, `team_id` | `user_id`, `status`, `expires_at` |

**Total Database Constraints**:
- **Application Tables**: 23
- **Foreign Key Constraints**: 45
- **Performance & Integrity Indexes**: 145

---

## 5. Verifying Database Connectivity

To verify database readiness and connectivity from the backend:

```bash
# Using the production readiness endpoint:
curl http://127.0.0.1:8000/health/ready
```

Expected response:
```json
{
  "status": "ready",
  "database": "connected"
}
```

Or via Python CLI:

```python
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1")).scalar()
    print("Database connected:", result == 1)
```

---

## 6. Seed Data

Migration `0009_badges_and_achievements` automatically populates default achievement badges upon migration:
1. `first-blood` (First Blood)
2. `web-master` (Web Exploiter)
3. `crypto-cracked` (Cipher Breaker)
4. `pwn-star` (Binary Exploiter)
5. `forensics-detective` (Digital Sleuth)
6. `reverse-engineer` (Decompiler Ace)
7. `streak-master` (Persistent Solver)
8. `top-ten` (Top 10 Finisher)

---

## 7. Troubleshooting & Best Practices

1. **Connection Timeouts in Cloud/Serverless**:
   If hosting in containerized environments with aggressive idle timeouts, ensure `pool_pre_ping=True` is maintained (configured by default in `backend/app/database.py`).
2. **Migration Rollbacks**:
   PostgreSQL supports transactional DDL. If any migration step encounters a syntax error or constraint conflict, the transaction automatically rolls back without corrupting existing schema.
3. **Sensitive Logs**:
   Database query echoing is automatically disabled in production environments (`settings.ENVIRONMENT == "production"` or `DEBUG=False`).
