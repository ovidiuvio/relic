#!/bin/bash
set -e

# Extract database host from DATABASE_URL if possible
# Format: postgresql://relic_user:relic_password@postgres:5432/relic_db
DB_HOST=$(echo $DATABASE_URL | sed -e 's|.*@||' -e 's|:.*||' -e 's|/.*||')
DB_USER=$(echo $DATABASE_URL | sed -e 's|.*//||' -e 's|:.*@||')

if [ "$DB_HOST" != "" ] && [ "$DB_HOST" != "$DATABASE_URL" ]; then
    echo "Waiting for database at $DB_HOST..."
    until pg_isready -h "$DB_HOST" -U "$DB_USER"; do
      echo "Postgres is unavailable - sleeping"
      sleep 1
    done
fi

echo "Running database initialization..."
# Run init_db once before starting workers to prevent race conditions
export PYTHONPATH=$PYTHONPATH:/app
python3 -c "from backend.database import init_db; init_db()"

# Set flag to avoid redundant (and potentially racing) init in workers
export SKIP_DB_INIT=true

echo "Database initialization completed."

# Start the application
echo "Starting application with command: $@"
exec "$@"

