# OWASP CTF Platform — CyberLab Arena

A modern, production-grade, zero-budget collegiate Capture The Flag (CTF) training and competition platform engineered for cybersecurity student chapters.

---

## 1. Project Overview

The **OWASP CTF Platform** serves as an end-to-end security proving ground providing both continuous practice and live tournament competition:
- **Practice Arena**: Continuous jeopardy training across Web Exploitation, Cryptography, Forensics, Reverse Engineering, Binary Exploitation (Pwn), OSINT, Steganography, and Misc.
- **Tournament Events**: Scheduled competitions featuring team/solo registration, dynamic point decay, first-blood bonuses, live scoreboards, suspense scoreboard freezing, and verifiable digital certificates.
- **Live Sandbox Challenges**: On-demand, isolated Docker container provisioning with per-player dynamic flags and zero host database access.
- **Anti-Cheat & Telemetry**: Duplicate flag submission flags, rapid solve heuristics, IP collision detection, and full moderator review workflows.

---

## 2. Technology Stack & Architecture

```
                                  +---------------------------------------+
                                  |         Browser / Operative           |
                                  +---------------------------------------+
                                                     |
                                            HTTP / JSON / Assets
                                                     |
                                                     v
                                  +---------------------------------------+
                                  |     FastAPI App / Static Server       |
                                  |   - HTTP Security Headers (HSTS/XSS)  |
                                  |   - Request ID Tracing Middleware     |
                                  |   - Global Error Masking (500)        |
                                  +---------------------------------------+
                                         |                         |
               +-------------------------+                         +-------------------------+
               |                                                                             |
               v                                                                             v
+-------------------------------+                                             +-------------------------------+
|     PostgreSQL Database       |                                             |      Docker Engine Daemon     |
| - Users & Teams (RBAC)        |                                             | - Bridge Network Isolation    |
| - Challenges & Submissions    |                                             | - Dropped Capabilities        |
| - Solves & Hints & Writeups   |                                             | - Ephemeral Ports (30000+)    |
| - Badges & Notifications      |                                             | - Automatic TTL Cleanup       |
| - Anti-Cheat Security Events  |                                             +-------------------------------+
+-------------------------------+
```

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Vanilla JS (ES6+), Modern CSS Design System | Zero-build deployment, low latency, mobile-responsive, $0 infrastructure cost. |
| **Backend API**| Python 3.12+, FastAPI, Pydantic v2 | High-performance async ASGI server with automated OpenAPI / Swagger docs. |
| **Database** | PostgreSQL, SQLAlchemy 2.0, Alembic | ACID compliant relational models with strictly audited database migrations. |
| **Containerization**| Docker Engine, Docker Compose | Isolated challenge sandboxing with CPU/RAM caps and no host socket exposure. |
| **Cryptography** | bcrypt, PyJWT (HS256), HMAC-SHA256 | High-assurance password hashing, token validation, and certificate authentication. |

---

## 3. Implemented Features (Completed)

### 3.1 Student Experience
- **Authentication & Sessions**: Secure signup, login, JWT token management, and auto session recovery.
- **Challenge Arena**: Filter by category, difficulty tiers (Easy/Medium/Hard/Insane), status (solved/unsolved), and live Docker tag.
- **Authoritative Flag Validation**: Instant server-side verification; zero flag disclosure in responses or client code.
- **Hint System**: Tiered hint reveals with permanent point penalties and confirmation safeguards.
- **Post-Solve Solutions**: Challenge writeups accessible strictly after solve or event conclusion.
- **Live Ephemeral Containers**: One-click Docker container provisioning with external links, live countdown timers, and manual stop.
- **Student Dashboard**: Real-time score ribbons, global rank, collegiate rank, active streaks, recent solves stream, and unread notifications.
- **Teams & Squads**: Create teams, invite members via 8-character secret join codes (up to 4 members), and leave squads.
- **52-Week GitHub-Style Activity Heatmap**: Visual 365-day calendar grid tracking challenge solves.
- **Digital Certificates**: HMAC-SHA256 verifiable credentials with public recruiter verification widget (`/api/events/certificates/verify/{token}`).

### 3.2 Tournament & Event Management
- **Event Scheduling**: Start/end time windows, description, and rules.
- **Registration**: Solo and team registration with eligibility validation.
- **Isolated Event Leaderboards**: Real-time scoreboard with frozen state banner near tournament completion.
- **Results Export**: One-click download of event results in structured JSON or CSV format.

### 3.3 Admin & Moderation Suite
- **Analytics Dashboard**: Overview KPIs (users, challenges, solves, submissions), category engagement, difficulty breakdown, and top solves.
- **Challenge Authoring**: Create challenges with points, difficulty, category, file uploads, hints, and Docker definitions.
- **Security Incident Monitor**: Detection of duplicate flags across accounts, rapid solve spikes, and IP collisions with moderator review status.
- **Live Container Orchestrator**: Monitor running sandboxes, inspect host ports, terminate rogue containers, and trigger TTL cleanup.
- **User Moderation**: Paginated user search, role modification (student/moderator/admin), ban/unban toggles, and discussion mute/unmute.

---

## 4. Local Setup & Quickstart

### Prerequisites
- Python 3.12 or newer
- PostgreSQL (or local SQLite for dev/test)
- Docker Desktop (for live container challenges)

### Backend Setup
1. Clone the repository and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
7. Open `http://localhost:8000` in your browser.

---

## 5. Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://ctf_user:ctf_pass@localhost:5432/ctf_db` | PostgreSQL connection string. |
| `SECRET_KEY` | *(Required in Production)* | Minimum 32-character secret for signing JWTs and HMAC certificates. |
| `ENVIRONMENT` | `development` | `development`, `testing`, or `production`. |
| `DEBUG` | `False` | When False, masks internal server stack traces on 500 errors. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT token validity window (in minutes). |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins. In production, wildcard `*` with credentials is automatically rejected. |
| `DOCKER_PORT_RANGE_START` | `30000` | Starting port for ephemeral challenge allocation. |
| `DOCKER_PORT_RANGE_END` | `31000` | Ending port for ephemeral challenge allocation. |
| `DOCKER_CONTAINER_TTL_MINUTES` | `60` | Auto-expiration lifetime for challenge sandboxes. |

---

## 6. Docker Live Challenge Setup

To enable live challenge sandbox provisioning:
1. Ensure the Docker daemon is running locally or in your host environment.
2. Build sample challenge images located in `challenges/` (e.g. `challenges/web-sqli`):
   ```bash
   docker build -t ctf-web-sqli challenges/web-sqli
   ```
3. When creating or editing a challenge in the Admin Control Center, check **"Docker Live Challenge"** and set the image name to `ctf-web-sqli`.
4. Players can now click **"Launch Instance"** to receive an isolated container.

---

## 7. Running Automated Tests

Run the complete 233+ test suite across all 17 phases:
```bash
pytest -v
```

Run specific verification suites:
```bash
# Security Hardening (15 tests)
pytest tests/test_security_hardening.py -v

# Admin User Moderation (7 tests)
pytest tests/test_admin_users.py -v

# Export & Certificates (7 tests)
pytest tests/test_event_export_and_certificates.py -v

# Database Migration Upgrade/Downgrade (1 test)
pytest tests/test_migrations.py -v
```

---

## 8. Security Considerations

- **Authoritative Flag Secrecy**: Challenge flags are stored as salted hashes (`flag_hash`). Plaintext flags are never returned by any public or participant endpoint.
- **HTTP Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and HSTS.
- **Request Tracing**: `X-Request-ID` is assigned to each incoming request and attached to response headers and log records.
- **Error Masking**: Global exception handlers mask internal Python stack traces when `DEBUG=False`.
- **Upload Hardening**: File upload sizes are limited to 50MB with strict extension allowlists.
- **Container Isolation**: Live challenge containers drop all Linux capabilities (`cap_drop=['ALL']`), have memory limits (256MB), and communicate over an isolated Docker network.

---

## 9. Known Limitations & Planned Future Work

The following items are planned for subsequent milestones beyond Phase 17:
- [ ] **Google OAuth 2.0 / College SSO**: Third-party OAuth login integration alongside standard email/password.
- [ ] **Per-Team Dynamic Flags Engine**: Generating unique cryptographic flags per team for static file downloads.
- [ ] **Cloudflare R2 / S3 Storage**: Offloading challenge uploads from the local filesystem to S3-compatible cloud object storage.
- [ ] **Binary PDF Certificate Generation**: Direct `.pdf` file generation via headless browser or Python PDF generator.
- [ ] **Email Dispatch Integration**: Outbound transactional emails (Resend / SendGrid / SMTP) for event start alerts.

---

## 10. License

Developed for the college OWASP Cybersecurity Club under the MIT License.
