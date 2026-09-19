# PostgreSQL & Storage Backup and Restore Guide

This document outlines the backup, retention, and disaster recovery procedures for the College OWASP CTF Platform.

> [!IMPORTANT]
> **Operational Status Note**: This guide defines standard operational procedures. No automated external cloud backup service is currently configured on your local machine; implementing scheduled backups requires external cron or cloud provider backup configuration (e.g. AWS S3, Supabase daily backups, or pg_dump cron jobs).

---

## 1. Backup Strategy Overview

A robust CTF platform requires dual-plane backups:
1. **Relational Database (PostgreSQL)**: Contains users, challenges, submissions, flags, dynamic scoring state, anti-cheat event logs, badges, teams, and event registrations.
2. **Challenge Media & File Attachments**: Files uploaded to `uploads/` (or mounted volume `ctf_uploads`).

### Recommended Frequency
| Type | Frequency | Retention Period | Target Storage |
| :--- | :--- | :--- | :--- |
| **Full DB Dump** | Daily at 02:00 UTC | 30 days | Encrypted Object Storage (S3 / Cloud Storage) |
| **Pre-Migration Snapshot** | Before every `alembic upgrade` | Kept until migration verified | Local + Remote |
| **Event Snapshot** | Immediately upon CTF event start & conclusion | 1 year | Encrypted Archive |
| **File Storage Backup**| Daily incremental | 30 days | Encrypted Object Storage |

---

## 2. PostgreSQL Backup Procedures

### A. Performing a Full Compressed Backup (`pg_dump`)

Using the custom PostgreSQL archive format (`-Fc`), which supports parallel restore, compression, and selective table recovery:

```bash
# Set timestamp and backup directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="/backups/owasp_ctf_${TIMESTAMP}.dump"

# Run pg_dump from host or inside docker container
docker exec -t ctf_postgres pg_dump \
  -U postgres \
  -d owasp_ctf \
  -F c \
  -b \
  -v \
  -f "/tmp/backup_${TIMESTAMP}.dump"

# Copy archive out of container
docker cp ctf_postgres:/tmp/backup_${TIMESTAMP}.dump "${BACKUP_FILE}"
```

For plain SQL format (human-readable text, compressed with gzip):
```bash
docker exec -t ctf_postgres pg_dump -U postgres -d owasp_ctf | gzip > "owasp_ctf_${TIMESTAMP}.sql.gz"
```

---

## 3. PostgreSQL Restore Procedures

> [!CAUTION]
> Restoring a database drops and recreates schema objects. Always test the backup file in an isolated staging environment before restoring in production!

### A. Pre-Restore Checklist
1. Terminate all active backend connections to prevent write locks and partial mutations.
2. Take an emergency safety dump of the existing database state if accessible.
3. Validate that the backup file is intact and not corrupted.

### B. Restoring from Custom Archive (`pg_restore`)

```bash
# 1. Stop backend service to prevent live writes during restore
docker stop ctf_backend

# 2. Recreate or clean the target database
docker exec -i ctf_postgres psql -U postgres -c "DROP DATABASE IF EXISTS owasp_ctf_restored;"
docker exec -i ctf_postgres psql -U postgres -c "CREATE DATABASE owasp_ctf_restored;"

# 3. Restore schema and data using pg_restore
docker cp ./my_backup.dump ctf_postgres:/tmp/restore.dump
docker exec -i ctf_postgres pg_restore \
  -U postgres \
  -d owasp_ctf_restored \
  -v \
  --no-owner \
  --no-privileges \
  /tmp/restore.dump

# 4. Verify data integrity
docker exec -i ctf_postgres psql -U postgres -d owasp_ctf_restored -c "SELECT COUNT(*) FROM users;"
docker exec -i ctf_postgres psql -U postgres -d owasp_ctf_restored -c "SELECT COUNT(*) FROM challenges;"

# 5. Swap databases and restart backend
docker exec -i ctf_postgres psql -U postgres -c "ALTER DATABASE owasp_ctf RENAME TO owasp_ctf_old;"
docker exec -i ctf_postgres psql -U postgres -c "ALTER DATABASE owasp_ctf_restored RENAME TO owasp_ctf;"
docker start ctf_backend
```

---

## 4. File Attachment Storage Backup

Files uploaded via `/api/challenges/{challenge_id}/files` reside in `ctf_uploads` volume:

```bash
# Archive the uploads directory
tar -czvf "ctf_uploads_${TIMESTAMP}.tar.gz" -C /var/lib/docker/volumes/ctf_uploads/_data .

# Restore uploads directory
tar -xzvf "ctf_uploads_${TIMESTAMP}.tar.gz" -C /var/lib/docker/volumes/ctf_uploads/_data/
```

---

## 5. Migration Safety Protocol

Before running `alembic upgrade head` in production:
1. Always run a snapshot: `pg_dump -U postgres -d owasp_ctf -F c -f pre_migration.dump`.
2. Inspect migration sql without executing: `alembic upgrade head --sql`.
3. Apply migration: `alembic upgrade head`.
4. Run health check: `curl -f http://localhost:8000/health/ready`.
5. In case of failure: `alembic downgrade -1` or restore from `pre_migration.dump`.
