# Production Deployment Guide — College OWASP CTF Platform

This document details the production architecture, configuration, deployment procedures, and security checklist for deploying the OWASP CTF platform.

---

## 1. System Architecture

```text
               +----------------------------------+
               |        Clients / Browsers        |
               +----------------------------------+
                                |
                                | HTTPS (TLS 1.3 / Port 443)
                                v
               +----------------------------------+
               | Reverse Proxy (Nginx / Cloudflare|
               |       / Caddy / Ingress)         |
               +----------------------------------+
                                |
                   +------------+------------+
                   |                         |
            HTTP   v                  Static v
        +----------------------+   +-------------------+
        | FastAPI Backend      |   | Static Assets /   |
        | (uvicorn / Port 8000)|   | Frontend Host     |
        +----------------------+   +-------------------+
             |            |
             | SQL        | Docker API (unix:///var/run/docker.sock)
             v            v
    +-------------+  +-------------------------------------+
    | PostgreSQL  |  | Docker Engine                       |
    | Database    |  |  +-------------------------------+  |
    +-------------+  |  | Challenge Containers (Sandboxed)|  |
                     |  | Network: ctf_challenges_net   |  |
                     |  | Non-root, Read-only, Quotas   |  |
                     |  +-------------------------------+  |
                     +-------------------------------------+
```

---

## 2. Configuration Matrix

### Status Classification
* **Configured / Verified**: Implemented directly in the application code and verified by automated unit tests.
* **Requires External Deployment Configuration**: Platform infrastructure items that must be provisioned on your cloud or server environment.

| Configuration Item | Status | Location / Detail |
| :--- | :--- | :--- |
| **Pydantic Settings & Env Validation** | **Configured / Verified** | `backend/app/config.py` |
| **Production Weak Secret Rejection** | **Configured / Verified** | Startup validator in `backend/app/config.py` |
| **Strict CORS & Wildcard Rejection** | **Configured / Verified** | `backend/app/config.py` + `backend/app/main.py` |
| **HTTP Security Headers** | **Configured / Verified** | `backend/app/main.py` (nosniff, DENY, CSP, HSTS) |
| **X-Request-ID Correlation** | **Configured / Verified** | `backend/app/main.py` |
| **Safe Error Handling (No Tracebacks)**| **Configured / Verified** | `backend/app/main.py` global 500 handler |
| **Liveness Probe (`/health`)** | **Configured / Verified** | `GET /health` |
| **Readiness Probe (`/health/ready`)**| **Configured / Verified** | `GET /health/ready` (tests DB connection) |
| **Flag / Hash Exposure Masking** | **Configured / Verified** | Pydantic schemas & response validation |
| **Anti-Cheat & Rate Limiting** | **Configured / Verified** | `backend/app/services/anti_cheat_service.py` |
| **Challenge File Upload/Download Guards** | **Configured / Verified** | `backend/app/api/challenges.py` (50MB, extensions, inactive auth) |
| **Live Challenge Sandboxing** | **Configured / Verified** | `backend/app/services/docker_challenge_service.py` |
| **Multi-Stage Dockerfile** | **Configured / Verified** | `backend/Dockerfile` |
| **Docker Compose Orchestrator** | **Configured / Verified** | `docker-compose.yml` |
| **External HTTPS / TLS Certificate** | *Requires External Deployment* | Nginx / Caddy / Cloudflare / Let's Encrypt |
| **Managed Cloud Database** | *Requires External Deployment* | Supabase / Neon / AWS RDS / Self-hosted PG |
| **Automated Off-site Backups** | *Requires External Deployment* | S3 Cron / Cloud Provider Automated Snapshots |
| **Host Docker Daemon Socket Access** | *Requires External Deployment* | Linux host `/var/run/docker.sock` permissions |

---

## 3. Environment Variables Specification

All production secrets and parameters must be passed through environment variables. Use `backend/.env.example` as a baseline:

```env
# Runtime Environment
ENVIRONMENT=production
DEBUG=false

# Security & Tokens
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=wX8_vR7tY3-uK9pL2oN1mQ5sA4dF6gH8jK0zX2cV4bN6mQ8=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# PostgreSQL Database Connection
DATABASE_URL=postgresql+psycopg://ctf_prod_user:StrongPassword123@db-host.internal:5432/owasp_ctf_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# CORS & Transport
CORS_ORIGINS=https://ctf.college.edu
CORS_ALLOW_CREDENTIALS=true
ENABLE_HSTS=true

# File Upload Protection
MAX_FILE_UPLOAD_SIZE=52428800

# Anti-Cheat & Rate Limiting
SUBMISSION_RATE_LIMIT_PER_MINUTE=10
SUBMISSION_COOLDOWN_SECONDS=2
ANTI_CHEAT_WINDOW_MINUTES=10
BURST_SUBMISSION_THRESHOLD=15
SOLVE_VELOCITY_THRESHOLD=4
FAILED_SUBMISSIONS_THRESHOLD=20

# Live Challenges (Optional: Only if running dynamic Docker containers)
DOCKER_NETWORK=ctf_challenges_net
CHALLENGE_PUBLIC_HOST=challenges.ctf.college.edu
CHALLENGE_PORT_RANGE_START=30000
CHALLENGE_PORT_RANGE_END=31000
CHALLENGE_CONTAINER_CPU_LIMIT=0.5
CHALLENGE_CONTAINER_MEM_LIMIT=256m
CHALLENGE_CONTAINER_PIDS_LIMIT=100
```

---

## 4. Production Deployment Steps

### Step 1: Provision Infrastructure
- 1x Virtual Server (e.g. Ubuntu 24.04 LTS, 4GB RAM, 2 vCPU) or Container Platform (Fly.io / Render / Railway).
- 1x PostgreSQL 16 database instance (managed e.g. Neon/Supabase or containerized).

### Step 2: Configure Environment
Copy `.env.example` to `.env` on the host and inject secure random credentials:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))" >> backend/.env
```

### Step 3: Run Database Migrations
Always upgrade database tables via Alembic prior to launching application instances:
```bash
cd backend
alembic upgrade head
```

### Step 4: Launch Backend Service
Run via Uvicorn with multiple workers or process supervisor:
```bash
# Direct startup respecting environment $PORT
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4 --proxy-headers --forwarded-allow-ips="*"

# Or via Docker Compose
docker compose up -d
```

### Step 5: Verify Health Probes
```bash
# 1. Check application liveness
curl -i http://localhost:8000/health
# Expected: HTTP 200 {"status":"ok","service":"owasp-ctf-backend","environment":"production"}

# 2. Check database readiness
curl -i http://localhost:8000/health/ready
# Expected: HTTP 200 {"status":"ready","database":"connected"}
```

---

## 5. Reverse Proxy & HTTPS Configuration

Production deployments **MUST** enforce HTTPS. Here is a battle-tested Nginx configuration:

```nginx
server {
    listen 80;
    server_name ctf.college.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ctf.college.edu;

    ssl_certificate /etc/letsencrypt/live/ctf.college.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ctf.college.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    client_max_body_size 50M;

    # API and Websockets
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 6. Live Docker Challenges Sandboxing Rules

When live Docker challenges are activated:
1. **Network Isolation**: All challenge instances run on the separate `ctf_challenges_net` bridge network with no connectivity to `ctf_platform_net` or the PostgreSQL database.
2. **Resource Throttling**: Every container is bounded by `--cpus=0.5`, `--memory=256m`, and `--pids-limit=100`.
3. **Privileges Dropped**: Challenge containers must never run with `--privileged`, never mount host paths, and never receive Docker daemon socket mounts.
4. **Automatic Garbage Collection**: Containers expire and terminate after `CHALLENGE_DEFAULT_DURATION_MINUTES`.

---

## 7. Production Go-Live Checklist

- [ ] `ENVIRONMENT=production` and `DEBUG=false` are verified.
- [ ] `SECRET_KEY` is high-entropy and does not match any development sample.
- [ ] `CORS_ORIGINS` points strictly to legitimate frontend domains (no `*`).
- [ ] TLS 1.3 / HTTPS certificate is active and auto-renewing.
- [ ] `alembic upgrade head` executed cleanly on production database.
- [ ] Healthcheck endpoints `/health` and `/health/ready` return 200 OK.
- [ ] Admin endpoints (`/api/analytics`, `/api/anti-cheat`, `/api/live-challenges/admin`) strictly forbid student access.
- [ ] Challenge files directory is persistent and restricted to 50MB per upload.
- [ ] PostgreSQL automated backup script or cloud service is active.
