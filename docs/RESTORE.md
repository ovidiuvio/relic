# Relic Manual Restore Guide

This guide covers manually restoring Relic from backups using existing tools and infrastructure.

## Overview

Relic maintains automated PostgreSQL database backups stored in S3/MinIO with a tiered retention policy:
- **Daily backups**: Last 7 days (all backups kept)
- **Weekly backups**: Last 30 days (one per week)
- **Monthly backups**: Forever (one per month)

Additionally, all S3 artifacts are mirrored to a remote S3-compatible storage for disaster recovery.

## Prerequisites

Ensure you have access to:
- PostgreSQL client tools (`psql`, `pg_restore`)
- MinIO client (`mc`) or AWS CLI
- Docker/Docker Compose
- Database credentials (user, password, host, port)
- S3/MinIO credentials (access key, secret key)

## Available Restore Scenarios

### Scenario 1: Restore Full Database (Blue-Green Deployment)
**Use case**: Database corruption, accidental deletion, point-in-time recovery

**Safety level**: High (non-destructive to active database)

**Steps**:
1. List and select backup
2. Download and decompress backup
3. Create new database (`relic_restore`)
4. Restore backup to new database
5. Verify restored database
6. Switch application to new database
7. Keep old database as backup (optional rollback)

### Scenario 2: Restore Single Deleted Relic
**Use case**: User accidentally deleted an artifact

**Safety level**: High (minimal impact)

**Steps**:
1. Find relic in backup
2. Extract relic's INSERT statement
3. Execute in current database
4. Restore artifact from S3 backup

### Scenario 3: Disaster Recovery (Full Destructive Restore)
**Use case**: Complete data loss, need to restore everything

**Safety level**: Low (destructive, replaces current data)

**Steps**:
1. Drop current database
2. Create fresh database
3. Restore from backup
4. Restart application

---

## Step-by-Step Restore Procedures

### Prerequisites Setup

First, set up environment variables:

```bash
# Database connection (from docker-compose.yml or .env)
export DB_HOST="postgres"  # or "localhost" if running locally
export DB_PORT="5432"
export DB_USER="relic_user"
export DB_PASSWORD="relic_password"
export DB_NAME="relic_db"

# S3/MinIO connection
export S3_ENDPOINT_URL="http://minio:9000"  # or "http://localhost:9000"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin"
export S3_BUCKET="relics"
```

If using MinIO client (`mc`):

```bash
# Add MinIO alias
mc alias set minio $S3_ENDPOINT_URL $S3_ACCESS_KEY $S3_SECRET_KEY

# Test connection
mc ls minio/relics
```

---

## Procedure 1: Blue-Green Full Database Restore

### Step 1: List Available Backups

**Using MinIO client**:
```bash
mc ls minio/relics/db/ --recursive
```

**Using AWS CLI** (if using S3):
```bash
aws s3 ls s3://relics/db/ --recursive
```

**Expected output**:
```
[2024-01-15 02:00:35]   2.5MiB db/backup-2024-01-15-02-00-00.sql.gz
[2024-01-15 14:00:45]   2.6MiB db/backup-2024-01-15-14-00-00.sql.gz
[2024-01-16 02:01:12]   2.5MiB db/backup-2024-01-16-02-00-00.sql.gz
[2024-01-16 14:00:58]   2.6MiB db/backup-2024-01-16-14-00-00.sql.gz
[2024-02-01 02:00:22]   2.7MiB db/backup-2024-02-01-02-00-00.sql.gz
```

**Choose the backup you want to restore** (typically the most recent one before the incident).

### Step 2: Download and Decompress Backup

Create a temporary directory:
```bash
mkdir -p /tmp/relic-restore
cd /tmp/relic-restore
```

**Download backup using MinIO**:
```bash
BACKUP_FILE="db/backup-2024-01-16-02-00-00.sql.gz"

mc cp minio/relics/$BACKUP_FILE backup.sql.gz
```

**Or download using AWS CLI**:
```bash
BACKUP_FILE="db/backup-2024-01-16-02-00-00.sql.gz"

aws s3 cp s3://relics/$BACKUP_FILE backup.sql.gz
```

**Decompress the backup**:
```bash
gunzip backup.sql.gz
# Result: backup.sql (uncompressed SQL dump)

# Verify file was decompressed
ls -lh backup.sql
```

### Step 3: Create Restore Database

Connect to PostgreSQL and create new database:

```bash
# Connect to PostgreSQL
psql -h $DB_HOST -U $DB_USER -d postgres

# In psql prompt:
CREATE DATABASE relic_restore;
\q
```

**Or in one command**:
```bash
psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE relic_restore;"
```

### Step 4: Restore Backup to New Database

**Method A: Using `psql` (recommended for most cases)**:
```bash
psql -h $DB_HOST \
     -U $DB_USER \
     -d relic_restore \
     -f backup.sql
```

**Method B: Using `pg_restore` (if backup was created with pg_dump in binary format)**:
```bash
pg_restore -h $DB_HOST \
           -U $DB_USER \
           -d relic_restore \
           -v \
           backup.sql
```

**Expected output**:
```
SET
SET
SET
SET
CREATE SCHEMA
CREATE EXTENSION
COMMENT ON EXTENSION
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
...
```

**Note**: The SQL dump includes `--clean` and `--if-exists` flags, so it will drop existing objects first.

### Step 5: Verify Restored Database

**Check database is accessible**:
```bash
psql -h $DB_HOST -U $DB_USER -d relic_restore -c "\dt"
```

**Expected output** (tables):
```
             List of relations
 Schema |      Name      | Type  | Owner
--------+----------------+-------+-----
 public | relic          | table | relic_user
 public | user           | table | relic_user
 public | tag            | table | relic_user
 public | relic_tag      | table | relic_user
(4 rows)
```

**Verify row counts**:
```bash
psql -h $DB_HOST -U $DB_USER -d relic_restore -c "
  SELECT 'relic' as table_name, COUNT(*) as count FROM relic
  UNION ALL
  SELECT 'user', COUNT(*) FROM \"user\"
  UNION ALL
  SELECT 'tag', COUNT(*) FROM tag
  ORDER BY 1;
"
```

**Check latest relic**:
```bash
psql -h $DB_HOST -U $DB_USER -d relic_restore -c "
  SELECT id, name, created_at, size_bytes
  FROM relic
  ORDER BY created_at DESC
  LIMIT 5;
"
```

### Step 6: Verify S3 Artifacts

Verify that artifacts referenced in database exist in S3 backup:

```bash
# Get a sample of relics from restored database
psql -h $DB_HOST -U $DB_USER -d relic_restore -c "
  COPY (SELECT id FROM relic ORDER BY RANDOM() LIMIT 10)
  TO STDOUT;" > /tmp/sample_relics.txt

# Check each exists in S3 backup bucket
while read relic_id; do
  if mc stat minio/relics/relics/$relic_id > /dev/null 2>&1; then
    echo "✓ Found: $relic_id"
  else
    echo "✗ Missing: $relic_id"
  fi
done < /tmp/sample_relics.txt
```

### Step 7: Switch Application to Restored Database

**Option A: Environment Variable Switch** (if app reloads config)

Update `.env` or docker-compose:
```bash
# Change from:
DATABASE_URL=postgresql://relic_user:relic_password@postgres:5432/relic_db

# To:
DATABASE_URL=postgresql://relic_user:relic_password@postgres:5432/relic_restore
```

Restart backend service:
```bash
docker-compose restart backend
```

**Option B: PostgreSQL Rename** (atomic switch without app restart)

```bash
# Rename databases
psql -h $DB_HOST -U $DB_USER -d postgres << EOF
ALTER DATABASE relic_db RENAME TO relic_db_old;
ALTER DATABASE relic_restore RENAME TO relic_db;
EOF

# Restart backend (it will reconnect to renamed database)
docker-compose restart backend
```

### Step 8: Post-Restore Verification

Test application functionality:

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Verify recent relics are accessible
curl http://localhost:8000/api/v1/relics -s | jq '.results | length'

# Test relic access
curl http://localhost:8000/:relic_id/raw
```

### Step 9: Rollback (If Issues Found)

If issues occur with restored database:

```bash
# Rename databases back
psql -h $DB_HOST -U $DB_USER -d postgres << EOF
ALTER DATABASE relic_db RENAME TO relic_restore_broken;
ALTER DATABASE relic_db_old RENAME TO relic_db;
EOF

# Restart backend
docker-compose restart backend

# Verify original database is active
curl http://localhost:8000/api/v1/health
```

---

## Procedure 2: Restore Single Deleted Relic

### Step 1: Identify Relic in Backup

Find the relic you need to restore by searching the SQL dump:

```bash
# Search for relic ID in backup
grep "INSERT INTO relic VALUES" backup.sql | grep "'relic_id_here'"
```

Or search interactively:

```bash
# Count total relics in backup
grep "INSERT INTO relic VALUES" backup.sql | wc -l

# Find relics by name or pattern
grep "INSERT INTO relic VALUES" backup.sql | grep "name_pattern"
```

### Step 2: Extract Relic's INSERT Statement

```bash
# Extract specific relic's INSERT statement
RELIC_ID="abc123def456"

grep "INSERT INTO relic VALUES.*'$RELIC_ID'" backup.sql > /tmp/relic_insert.sql

# View the statement
cat /tmp/relic_insert.sql
```

**Example output**:
```sql
INSERT INTO relic VALUES('abc123def456', NULL, 'client_123', 'MyDocument', 'A backup file', 'application/pdf', NULL, 1024000, 'relics/abc123def456', 'public', NULL, '2024-01-15 10:30:00', NULL, NULL, 0);
```

### Step 3: Execute in Current Database

```bash
# Apply the INSERT statement to current database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f /tmp/relic_insert.sql
```

**Verify relic was inserted**:
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
  SELECT id, name, size_bytes, created_at
  FROM relic
  WHERE id = '$RELIC_ID';
"
```

### Step 4: Restore Artifact from S3 Backup

If S3 backup is available, copy artifact back:

```bash
# Copy from backup bucket to current bucket
# (assumes relics are mirrored to backup location)

RELIC_ID="abc123def456"
BACKUP_BUCKET="relics-backup"  # Remote backup

# List where backup is stored
aws s3 ls s3://$BACKUP_BUCKET/relics/$RELIC_ID

# Copy back to current bucket
aws s3 cp s3://$BACKUP_BUCKET/relics/$RELIC_ID \
         s3://relics/relics/$RELIC_ID

# Verify copy succeeded
aws s3 ls s3://relics/relics/$RELIC_ID
```

**Verify in application**:
```bash
# Relic should now be accessible
curl http://localhost:8000/$RELIC_ID/raw -o recovered_file.pdf
```

---

## Procedure 3: Disaster Recovery (Full Restore)

### ⚠️ Warning: Destructive Operation

This procedure will **delete all current data** and restore from backup. Only use in true disaster scenarios.

### Step 1: Backup Current State

Before proceeding, backup current database (if possible):

```bash
# Create emergency backup of current state
pg_dump -h $DB_HOST \
        -U $DB_USER \
        -d $DB_NAME \
        -F c \
        -f /tmp/emergency_backup_$(date +%s).dump
```

### Step 2: Drop Current Database

```bash
# Connect to postgres database (not relic_db)
psql -h $DB_HOST -U $DB_USER -d postgres << EOF
-- Terminate all connections to relic_db
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'relic_db'
  AND pid <> pg_backend_pid();

-- Drop the database
DROP DATABASE IF EXISTS relic_db;

-- Create fresh database
CREATE DATABASE relic_db;
EOF
```

### Step 3: Restore from Backup

```bash
# Restore the backup
psql -h $DB_HOST -U $DB_USER -d relic_db -f backup.sql

# Verify restoration
psql -h $DB_HOST -U $DB_USER -d relic_db -c "\dt"
```

### Step 4: Restart Application

```bash
# Restart backend service
docker-compose restart backend

# Verify application is healthy
sleep 5
curl http://localhost:8000/api/v1/health
```

### Step 5: Restore S3 Artifacts

If S3 artifacts were lost, restore from backup:

```bash
# Using AWS CLI - copy all artifacts from backup bucket
aws s3 sync s3://relics-backup/relics/ s3://relics/relics/

# Using MinIO client
mc mirror --overwrite minio-backup/relics-backup/relics/ \
          minio/relics/relics/
```

---

## Backup File Structure

### Database Backup Format

Backups are created using `pg_dump` with specific flags:

```bash
pg_dump --clean           # Include DROP statements
        --if-exists       # Don't fail if objects don't exist
        --no-owner        # Don't include ownership info
        --no-acl          # Don't include ACLs
```

**File naming convention**:
- Scheduled: `db/backup-YYYY-MM-DD-HH-MM-SS.sql.gz`
- Startup: `db/backup-YYYY-MM-DD-startup.sql.gz`
- Shutdown: `db/backup-YYYY-MM-DD-shutdown.sql.gz`

### Compression

All backups are compressed with Gzip (compression level 9):
- Typical database: 30-50 MB uncompressed → 2-5 MB compressed
- Compression ratio: 70-90% reduction

---

## Troubleshooting

### Issue: "Connection refused" when connecting to PostgreSQL

**Cause**: Database server not running or wrong host/port

**Solution**:
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check if port is listening
nc -zv $DB_HOST $DB_PORT

# Update connection parameters
export DB_HOST="localhost"  # try localhost instead of container name
export DB_PORT="5432"
```

### Issue: "FATAL: role 'relic_user' does not exist"

**Cause**: PostgreSQL user not created

**Solution**:
```bash
# Connect as superuser (postgres) and create user
psql -h $DB_HOST -U postgres -c "
  CREATE USER relic_user WITH ENCRYPTED PASSWORD 'relic_password';
  ALTER ROLE relic_user CREATEDB;
"
```

### Issue: "ERROR: relation 'relic' does not exist"

**Cause**: Database not fully restored or wrong database selected

**Solution**:
```bash
# Check which database is selected
psql -h $DB_HOST -U $DB_USER -c "SELECT current_database();"

# Verify table exists
psql -h $DB_HOST -U $DB_USER -d relic_db -c "\dt relic"

# Re-run restore
psql -h $DB_HOST -U $DB_USER -d relic_db -f backup.sql
```

### Issue: "Backup file appears corrupted"

**Cause**: Download interrupted, file truncated, or decompression failed

**Solution**:
```bash
# Verify backup file size matches S3 metadata
ls -lh backup.sql.gz

mc stat minio/relics/db/backup-2024-01-16-02-00-00.sql.gz

# Try re-downloading
rm backup.sql.gz
mc cp minio/relics/db/backup-2024-01-16-02-00-00.sql.gz backup.sql.gz

# Try decompressing again
gunzip -v backup.sql.gz
```

### Issue: "Foreign key constraint violation" during restore

**Cause**: Data corruption or incomplete dump

**Solution**:
```bash
# Check constraint violations
psql -h $DB_HOST -U $DB_USER -d relic_db -c "
  ALTER TABLE relic_tag DROP CONSTRAINT IF EXISTS relic_tag_fk_relic;
  ALTER TABLE relic_tag DROP CONSTRAINT IF EXISTS relic_tag_fk_tag;
"

# Re-run restore
psql -h $DB_HOST -U $DB_USER -d relic_db -f backup.sql
```

---

## Performance Optimization

### Restore Speed Tips

1. **Increase `maintenance_work_mem`** (speeds up index creation):
```bash
psql -h $DB_HOST -U $DB_USER -d relic_restore -c "
  SET maintenance_work_mem = '1GB';
"
```

2. **Disable indexes during restore** (then rebuild):
```bash
# Before restore
SET fsync = off;
SET synchronous_commit = off;

# After restore
SET fsync = on;
SET synchronous_commit = on;
VACUUM ANALYZE;
```

3. **Use parallel restore** (for binary format backups):
```bash
# Create backup in binary format first
pg_dump -h $DB_HOST -U $DB_USER -d relic_db -F c -f backup.dump

# Restore with parallelism
pg_restore -h $DB_HOST -U $DB_USER -d relic_restore -j 4 backup.dump
```

---

## S3 Artifact Backup & Recovery

### Checking Backup Status

```bash
# List all backed-up artifacts
mc ls minio/relics/relics/ --recursive

# Count artifacts
mc ls minio/relics/relics/ --recursive | wc -l

# Check sync status to remote S3
mc ls minio-backup/relics-backup/relics/ --recursive | head -20
```

### Manual S3 Sync

```bash
# Mirror relics to backup location
mc mirror --overwrite minio/relics/relics/ \
          minio-backup/relics-backup/relics/

# Check sync progress
mc diff minio/relics/relics/ minio-backup/relics-backup/relics/
```

### Recover Missing Artifact

```bash
# If artifact exists in backup but not current S3
RELIC_ID="abc123def456"

# Check if exists in backup
mc stat minio-backup/relics-backup/relics/$RELIC_ID

# Copy from backup to current
mc cp minio-backup/relics-backup/relics/$RELIC_ID \
     minio/relics/relics/$RELIC_ID

# Verify
curl http://localhost:8000/$RELIC_ID/raw -o recovered_file
```

---

## Automation Scripts

### Script: List Recent Backups

```bash
#!/bin/bash
# list-backups.sh

echo "Recent database backups:"
echo "========================"

mc ls minio/relics/db/ --recursive | sort -r | head -20

echo ""
echo "Total backups:"
mc ls minio/relics/db/ --recursive | wc -l
```

### Script: Restore Latest Backup

```bash
#!/bin/bash
# restore-latest.sh

set -e

export DB_HOST="postgres"
export DB_USER="relic_user"
export DB_PASSWORD="relic_password"

# Find latest backup
LATEST_BACKUP=$(mc ls minio/relics/db/ --recursive | grep "\.sql\.gz" | sort -r | head -1 | awk '{print $NF}')

echo "Restoring from: $LATEST_BACKUP"

# Download
mkdir -p /tmp/relic-restore
cd /tmp/relic-restore
mc cp minio/relics/$LATEST_BACKUP backup.sql.gz

# Decompress
gunzip backup.sql.gz

# Create database
psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE relic_restore;"

# Restore
psql -h $DB_HOST -U $DB_USER -d relic_restore -f backup.sql

echo "✓ Restore complete. Database: relic_restore"
```

---

## Summary

| Scenario | Downtime | Data Risk | Steps |
|----------|----------|-----------|-------|
| Blue-Green Restore | None (until switch) | Low | 9 steps |
| Single Relic Restore | None | Very Low | 4 steps |
| Disaster Recovery | Yes (maintenance window) | High | 5 steps |

**Recommended**: Use blue-green restore for all scenarios when possible. Only use disaster recovery in true emergency situations.

For automated restore implementation, refer to `RESTORE_AUTOMATION.md` (when available).
