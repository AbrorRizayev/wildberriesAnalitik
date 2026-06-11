#!/usr/bin/env bash
set -euo pipefail

# ---- Wait for PostgreSQL to accept connections ----
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} ..."
for i in $(seq 1 60); do
    if python -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0) if s.connect_ex(('${DB_HOST}', ${DB_PORT}))==0 else sys.exit(1)" 2>/dev/null; then
        echo "Database is up."
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: database not reachable after 60 attempts." >&2
        exit 1
    fi
    sleep 1
done

# ---- Compile translation catalogs (UZ/RU) ----
echo "Compiling translation messages ..."
python manage.py compilemessages -l ru -l uz 2>/dev/null || echo "compilemessages skipped"

# ---- Apply database migrations ----
echo "Applying migrations ..."
python manage.py migrate --noinput

# ---- Collect static files (skipped in DEBUG) ----
if [ "${DEBUG:-False}" != "True" ] && [ "${DEBUG:-False}" != "true" ] && [ "${DEBUG:-False}" != "1" ]; then
    echo "Collecting static files ..."
    python manage.py collectstatic --noinput --clear
fi

echo "Starting: $*"
exec "$@"