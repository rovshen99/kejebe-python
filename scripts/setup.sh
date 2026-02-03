#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kejebe}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"

echo "==> Installing system packages..."
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential \
  libpq-dev postgresql postgresql-contrib

if [ ! -d "$APP_DIR" ]; then
  echo "App directory not found: $APP_DIR"
  echo "Clone the repo first, then rerun this script."
  exit 1
fi

cd "$APP_DIR"

if [ -f ".env" ]; then
  echo "==> Loading .env..."
  set -a
  . ./.env
  set +a
fi

DB_NAME="${DB_NAME:-kejebe}"
DB_USER="${DB_USER:-kejebe_user}"
DB_PASSWORD="${DB_PASSWORD:-STRONG_PASS}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

SMS_INIT_API_KEY="${SMS_INIT_API_KEY:-}"
DEBUG="${DEBUG:-false}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-*}"

echo "==> Setting up Python venv..."
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

echo "==> Creating database/user (idempotent)..."
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}') THEN
    CREATE DATABASE ${DB_NAME};
  END IF;
END
\$\$;

DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

if [ ! -f ".env" ]; then
  echo "==> Creating .env..."
  cat > .env <<EOF
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}

DEBUG=${DEBUG}
ALLOWED_HOSTS=${ALLOWED_HOSTS}

SMS_INIT_API_KEY=${SMS_INIT_API_KEY}
SMS_BYPASS_ENABLED=false
SMS_BYPASS_NUMBERS=

SERVICE_STORY_TTL_HOURS=24
DEVICE_LAST_SEEN_ENABLED=true
DEFAULT_REGION_ID=0

OSM_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
EOF
fi

echo "==> Running migrations and collectstatic..."
python manage.py migrate
python manage.py collectstatic --noinput

echo "==> Done. Run scripts/deploy.sh to start the service."
