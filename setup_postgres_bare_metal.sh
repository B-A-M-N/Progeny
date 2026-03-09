#!/bin/bash
# setup_postgres_bare_metal.sh - Progeny Database Easy-Setup (Bare Metal)

set -e

DB_NAME="progeny_brain"
DB_USER="bitling"
DB_PASS="tutor_brain"

echo "--- 🐘 Progeny Database Setup (Bare Metal) ---"

# 1. Install Postgres and pgvector (Apt)
echo "[1/4] Installing PostgreSQL and pgvector..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib postgresql-server-dev-all

# Detect Postgres major version
PG_VER=$(psql --version | grep -oE '[0-9]+' | head -1)
echo "Detected PostgreSQL version: $PG_VER"

# Install pgvector (matching version)
sudo apt-get install -y "postgresql-$PG_VER-pgvector" || {
    echo "Warning: could not find postgresql-$PG_VER-pgvector via apt. Attempting manual build..."
    cd /tmp
    git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
    cd pgvector
    make
    sudo make install
}

# 2. Configure Database & User
echo "[2/4] Setting up database and user..."
sudo -u postgres psql <<EOF
-- Create User
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
    END IF;
END
\$\$;

-- Create Database
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Permissions
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# 3. Enable Extension
echo "[3/4] Enabling pgvector extension..."
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 4. Update Python Requirements
echo "[4/4] Updating python requirements..."
# Add to main requirements if not there
if ! grep -q "psycopg2-binary" ai-companion/requirements.txt; then
    echo "psycopg2-binary" >> ai-companion/requirements.txt
fi
if ! grep -q "pgvector" ai-companion/requirements.txt; then
    echo "pgvector" >> ai-companion/requirements.txt
fi

# Also update the venv if it exists
if [ -d "ai-companion/venv" ]; then
    source ai-companion/venv/bin/activate
    pip install psycopg2-binary pgvector
    deactivate
fi

echo "--- ✅ Database Ready! ---"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
