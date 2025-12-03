#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration with defaults
SYNC_INTERVAL=${SYNC_INTERVAL:-1800}
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-60}
SYNC_ENABLED=${SYNC_ENABLED:-true}

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

# Validate required environment variables
validate_config() {
    local missing_vars=()

    [ -z "$MINIO_ENDPOINT" ] && missing_vars+=("MINIO_ENDPOINT")
    [ -z "$MINIO_ACCESS_KEY" ] && missing_vars+=("MINIO_ACCESS_KEY")
    [ -z "$MINIO_SECRET_KEY" ] && missing_vars+=("MINIO_SECRET_KEY")
    [ -z "$MINIO_BUCKET" ] && missing_vars+=("MINIO_BUCKET")
    [ -z "$S3_ENDPOINT" ] && missing_vars+=("S3_ENDPOINT")
    [ -z "$S3_ACCESS_KEY" ] && missing_vars+=("S3_ACCESS_KEY")
    [ -z "$S3_SECRET_KEY" ] && missing_vars+=("S3_SECRET_KEY")
    [ -z "$S3_BUCKET" ] && missing_vars+=("S3_BUCKET")

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
}

# Configure mc aliases
configure_mc() {
    log "Configuring MinIO client aliases..."

    # Configure source (MinIO)
    if mc alias set source "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" > /dev/null 2>&1; then
        log_success "Source alias configured: ${MINIO_ENDPOINT}"
    else
        log_error "Failed to configure source alias"
        return 1
    fi

    # Configure destination (S3)
    local s3_url="${S3_ENDPOINT}"
    [[ ! "$s3_url" =~ ^https?:// ]] && s3_url="https://${s3_url}"

    if mc alias set dest "${s3_url}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" > /dev/null 2>&1; then
        log_success "Destination alias configured: ${s3_url}"
    else
        log_error "Failed to configure destination alias"
        return 1
    fi

    return 0
}

# Check if buckets are accessible
check_buckets() {
    log "Checking bucket accessibility..."

    # Check source bucket
    if mc ls "source/${MINIO_BUCKET}" > /dev/null 2>&1; then
        log_success "Source bucket accessible: ${MINIO_BUCKET}"
    else
        log_error "Cannot access source bucket: ${MINIO_BUCKET}"
        return 1
    fi

    # Check/create destination bucket
    if mc ls "dest/${S3_BUCKET}" > /dev/null 2>&1; then
        log_success "Destination bucket accessible: ${S3_BUCKET}"
    else
        log_warning "Destination bucket not found, attempting to create: ${S3_BUCKET}"
        if mc mb "dest/${S3_BUCKET}" > /dev/null 2>&1; then
            log_success "Destination bucket created: ${S3_BUCKET}"
        else
            log_error "Cannot access or create destination bucket: ${S3_BUCKET}"
            return 1
        fi
    fi

    return 0
}

# Perform sync with retry logic
perform_sync() {
    local attempt=1
    local success=false

    while [ $attempt -le $MAX_RETRIES ] && [ "$success" = false ]; do
        if [ $attempt -gt 1 ]; then
            log_warning "Retry attempt $attempt/$MAX_RETRIES after ${RETRY_DELAY}s delay..."
            sleep $RETRY_DELAY
        fi

        log "Starting sync (attempt $attempt/$MAX_RETRIES)..."

        # Perform the mirror operation
        if mc mirror --overwrite --remove "source/${MINIO_BUCKET}" "dest/${S3_BUCKET}" 2>&1; then
            log_success "Sync completed successfully"
            success=true
            return 0
        else
            log_error "Sync failed on attempt $attempt"
            attempt=$((attempt + 1))
        fi
    done

    if [ "$success" = false ]; then
        log_error "Sync failed after $MAX_RETRIES attempts"
        return 1
    fi
}

# Main sync loop
main() {
    echo ""
    echo "========================================="
    echo "  Relic S3 Bucket Sync Service"
    echo "========================================="
    echo ""

    # Validate configuration
    validate_config

    # Check if sync is enabled
    if [ "$SYNC_ENABLED" != "true" ]; then
        log_warning "Sync is disabled (SYNC_ENABLED=${SYNC_ENABLED})"
        log "Exiting..."
        exit 0
    fi

    # Configure mc
    if ! configure_mc; then
        log_error "Failed to configure MinIO client"
        exit 1
    fi

    # Check buckets
    if ! check_buckets; then
        log_error "Bucket accessibility check failed"
        exit 1
    fi

    # Display configuration
    echo ""
    log "Configuration:"
    echo "  Source:      ${MINIO_ENDPOINT}/${MINIO_BUCKET}"
    echo "  Destination: ${S3_ENDPOINT}/${S3_BUCKET}"
    echo "  Interval:    ${SYNC_INTERVAL} seconds"
    echo "  Max Retries: ${MAX_RETRIES}"
    echo ""

    # Perform initial sync
    log "Performing initial sync..."
    perform_sync

    # Start sync loop
    log "Starting continuous sync loop..."
    echo ""

    while true; do
        log "Next sync in ${SYNC_INTERVAL} seconds..."
        sleep "$SYNC_INTERVAL"

        echo ""
        perform_sync
        echo ""
    done
}

# Handle graceful shutdown
trap 'log_warning "Received shutdown signal, exiting..."; exit 0' SIGTERM SIGINT

# Run main function
main
