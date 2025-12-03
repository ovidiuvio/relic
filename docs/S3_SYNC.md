# S3 Bucket Sync Service

Automatic mirroring service that synchronizes your MinIO bucket to an S3-compatible storage backend.

## Overview

The S3 Sync Service is a Docker sidecar container that automatically mirrors the contents of your local MinIO bucket to a remote S3-compatible storage service (AWS S3, Backblaze B2, Wasabi, etc.). It runs independently of your main application and performs incremental syncs at configurable intervals.

## Features

- **Automatic sync** - Runs continuously at configurable intervals
- **Incremental updates** - Only syncs changed objects (efficient)
- **Retry logic** - Automatic retries with exponential backoff
- **Health checks** - Validates bucket accessibility before syncing
- **Colored logging** - Easy-to-read status updates
- **Graceful shutdown** - Handles SIGTERM/SIGINT properly
- **Zero downtime** - Runs independently without affecting your app

## Quick Start

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and update the S3 sync settings:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Enable the sync service
S3_SYNC_ENABLED=true

# S3 destination credentials
S3_SYNC_ACCESS_KEY=your_aws_access_key_id
S3_SYNC_SECRET_KEY=your_aws_secret_access_key
S3_SYNC_BUCKET=relics-backup

# Optional: customize sync behavior
S3_SYNC_INTERVAL=1800  # Sync every 30 minutes
```

### 2. Start the Service

```bash
docker-compose up -d s3-sync
```

### 3. Monitor Logs

```bash
# Watch live logs
docker logs -f Relic-s3-sync

# Check recent logs
docker logs --tail 100 Relic-s3-sync
```

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `S3_SYNC_ACCESS_KEY` | S3 access key ID | `AKIAIOSFODNN7EXAMPLE` |
| `S3_SYNC_SECRET_KEY` | S3 secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `S3_SYNC_BUCKET` | Destination bucket name | `relics-backup` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_SYNC_ENABLED` | `false` | Enable/disable sync service |
| `S3_SYNC_ENDPOINT` | `s3.amazonaws.com` | S3 endpoint URL |
| `S3_SYNC_REGION` | `us-east-1` | S3 region |
| `S3_SYNC_INTERVAL` | `1800` | Sync interval (seconds) |
| `S3_SYNC_MAX_RETRIES` | `3` | Max retry attempts on failure |
| `S3_SYNC_RETRY_DELAY` | `60` | Delay between retries (seconds) |
| `S3_SYNC_TIMEZONE` | `UTC` | Timezone for log timestamps |

### Source Configuration (MinIO)

These are configured in `docker-compose.yml` and typically don't need changes:

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO endpoint (internal) |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `relics` | Source bucket name |

## Usage Examples

### AWS S3

```bash
# .env
S3_SYNC_ENABLED=true
S3_SYNC_ENDPOINT=s3.amazonaws.com
S3_SYNC_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SYNC_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_SYNC_BUCKET=my-relic-backups
S3_SYNC_REGION=us-east-1
```

### Backblaze B2

```bash
# .env
S3_SYNC_ENABLED=true
S3_SYNC_ENDPOINT=s3.us-west-000.backblazeb2.com
S3_SYNC_ACCESS_KEY=your_b2_key_id
S3_SYNC_SECRET_KEY=your_b2_application_key
S3_SYNC_BUCKET=my-relic-backups
S3_SYNC_REGION=us-west-000
```

### Wasabi

```bash
# .env
S3_SYNC_ENABLED=true
S3_SYNC_ENDPOINT=s3.wasabisys.com
S3_SYNC_ACCESS_KEY=your_wasabi_access_key
S3_SYNC_SECRET_KEY=your_wasabi_secret_key
S3_SYNC_BUCKET=my-relic-backups
S3_SYNC_REGION=us-east-1
```

### DigitalOcean Spaces

```bash
# .env
S3_SYNC_ENABLED=true
S3_SYNC_ENDPOINT=nyc3.digitaloceanspaces.com
S3_SYNC_ACCESS_KEY=your_spaces_access_key
S3_SYNC_SECRET_KEY=your_spaces_secret_key
S3_SYNC_BUCKET=my-relic-backups
S3_SYNC_REGION=nyc3
```

## Common Operations

### Start Sync Service

```bash
docker-compose up -d s3-sync
```

### Stop Sync Service

```bash
docker-compose stop s3-sync
```

### Restart Sync Service

```bash
docker-compose restart s3-sync
```

### Trigger Manual Sync

```bash
# Execute sync immediately (doesn't affect scheduled syncs)
docker exec Relic-s3-sync mc mirror --overwrite --remove \
  source/relics dest/relics-backup
```

### Check Sync Status

```bash
# View recent logs
docker logs --tail 50 Relic-s3-sync

# Follow logs in real-time
docker logs -f Relic-s3-sync
```

### Rebuild Container

After modifying sync scripts:

```bash
docker-compose build s3-sync
docker-compose up -d s3-sync
```

## Troubleshooting

### Sync service won't start

**Check if sync is enabled:**
```bash
docker-compose config | grep S3_SYNC_ENABLED
```

**Check for missing credentials:**
```bash
docker-compose logs s3-sync
```

Look for "Missing required environment variables" errors.

### Bucket access errors

**Verify MinIO is accessible:**
```bash
docker exec Relic-s3-sync mc ls source/relics
```

**Verify S3 is accessible:**
```bash
docker exec Relic-s3-sync mc ls dest/relics-backup
```

**Check credentials:**
```bash
# Test AWS credentials
docker exec Relic-s3-sync mc alias set test-dest \
  https://s3.amazonaws.com \
  "$S3_SYNC_ACCESS_KEY" \
  "$S3_SYNC_SECRET_KEY"
```

### Sync is running but not working

**Check sync logs for errors:**
```bash
docker logs Relic-s3-sync | grep -i error
```

**Verify network connectivity:**
```bash
docker exec Relic-s3-sync ping -c 3 s3.amazonaws.com
```

**Check bucket permissions:**
- Ensure your S3 credentials have `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` permissions

### Service keeps crashing

**View full logs:**
```bash
docker logs Relic-s3-sync
```

**Check resource usage:**
```bash
docker stats Relic-s3-sync
```

**Validate configuration:**
```bash
docker-compose config
```

## Advanced Configuration

### Change Sync Frequency

For more frequent syncs (e.g., every 5 minutes):

```bash
# .env
S3_SYNC_INTERVAL=300
```

For less frequent syncs (e.g., every 2 hours):

```bash
# .env
S3_SYNC_INTERVAL=7200
```

### Adjust Retry Behavior

```bash
# .env
S3_SYNC_MAX_RETRIES=5       # Try 5 times before giving up
S3_SYNC_RETRY_DELAY=120     # Wait 2 minutes between retries
```

### Disable Automatic Deletion

By default, the sync service uses `mc mirror --remove`, which deletes objects from the destination if they're removed from the source. To disable this behavior:

Edit `sync/sync.sh` and remove the `--remove` flag:

```bash
mc mirror --overwrite "source/${MINIO_BUCKET}" "dest/${S3_BUCKET}"
```

### One-Way Sync vs Bidirectional

The current implementation is **one-way** (MinIO → S3). For bidirectional sync, consider using MinIO's built-in site replication feature instead.

## Performance Considerations

### Bandwidth

- Each sync operation transfers only changed objects (incremental)
- Large files may take time on first sync
- Subsequent syncs are typically fast (only deltas)

### Sync Interval Recommendations

| Use Case | Recommended Interval | Setting |
|----------|---------------------|---------|
| High-traffic site | Every 5-15 minutes | `300-900` |
| Medium traffic | Every 30 minutes | `1800` |
| Low traffic | Every 1-2 hours | `3600-7200` |
| Archive/backup | Every 6-24 hours | `21600-86400` |

### Resource Usage

The sync service is lightweight:
- **CPU**: Minimal (only during active sync)
- **Memory**: ~50-100MB
- **Network**: Depends on data volume and frequency
- **Disk**: None (runs in memory)

## Security Best Practices

1. **Use IAM roles** (AWS) instead of access keys when possible
2. **Limit S3 permissions** to only required operations:
   - `s3:ListBucket`
   - `s3:GetObject`
   - `s3:PutObject`
   - `s3:DeleteObject`
3. **Enable encryption** on your S3 bucket
4. **Use `.env` file** and never commit credentials to git
5. **Rotate credentials** regularly
6. **Monitor access logs** for unusual activity

## Monitoring & Alerts

### Log Monitoring

Set up log aggregation to track:
- Sync success/failure rates
- Sync duration
- Network errors
- Bucket access issues

### Metrics to Track

- Sync success rate (should be >99%)
- Average sync duration
- Number of objects synced
- Bandwidth usage
- Error rate

### Example Log Output

```
=========================================
  Relic S3 Bucket Sync Service
=========================================

[2025-12-03 10:30:00] Configuring MinIO client aliases...
[2025-12-03 10:30:00] ✓ Source alias configured: http://minio:9000
[2025-12-03 10:30:00] ✓ Destination alias configured: https://s3.amazonaws.com
[2025-12-03 10:30:01] Checking bucket accessibility...
[2025-12-03 10:30:01] ✓ Source bucket accessible: relics
[2025-12-03 10:30:01] ✓ Destination bucket accessible: relics-backup

Configuration:
  Source:      http://minio:9000/relics
  Destination: s3.amazonaws.com/relics-backup
  Interval:    1800 seconds
  Max Retries: 3

[2025-12-03 10:30:01] Performing initial sync...
[2025-12-03 10:30:01] Starting sync (attempt 1/3)...
[2025-12-03 10:30:15] ✓ Sync completed successfully
[2025-12-03 10:30:15] Starting continuous sync loop...
[2025-12-03 10:30:15] Next sync in 1800 seconds...
```

## FAQ

### Q: Does this affect my application performance?
**A:** No, the sync service runs independently in a separate container and doesn't impact your application.

### Q: What happens if the sync fails?
**A:** The service automatically retries up to 3 times (configurable) with delays between attempts.

### Q: Can I sync to multiple destinations?
**A:** Not out of the box, but you can run multiple sync containers with different configurations.

### Q: Is the sync real-time?
**A:** No, it's periodic (default: every 30 minutes). For real-time sync, consider MinIO site replication.

### Q: What if my S3 bucket doesn't exist?
**A:** The sync service will attempt to create it automatically on first run.

### Q: Can I pause syncing temporarily?
**A:** Yes, either stop the container (`docker-compose stop s3-sync`) or set `S3_SYNC_ENABLED=false`.

### Q: Does this sync deleted files?
**A:** Yes, by default the `--remove` flag ensures deletions are mirrored to S3.

## Support

For issues or questions:
1. Check logs: `docker logs Relic-s3-sync`
2. Review this documentation
3. Check MinIO client documentation: https://min.io/docs/minio/linux/reference/minio-mc.html
4. Open an issue in the project repository

## Architecture

```
┌─────────────────┐
│  Application    │
│   (Backend)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────────┐
│     MinIO       │─────→│   S3 Sync        │
│   (Source)      │      │   Container      │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ↓
                         ┌──────────────────┐
                         │   AWS S3 / B2    │
                         │  (Destination)   │
                         └──────────────────┘
```

## License

Same as the main Relic project.
