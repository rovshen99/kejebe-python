#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kejebe}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"

echo "==> Installing system packages..."
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential \
  libpq-dev postgresql postgresql-contrib gettext

if [ ! -d "$APP_DIR" ]; then
  echo "App directory not found: $APP_DIR"
  echo "Clone the repo first, then rerun this script."
  exit 1
fi

sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

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

SMS_INBOUND_API_KEY="${SMS_INBOUND_API_KEY:-}"
DEBUG="${DEBUG:-false}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-*}"

echo "==> Setting up Python venv..."
if [ -d ".venv" ] && [ ! -w ".venv" ]; then
  sudo chown -R "$APP_USER":"$APP_USER" ".venv"
fi
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -U pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
  deps=$(python - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text())
deps = data.get("project", {}).get("dependencies", [])
print("\n".join(deps))
PY
)
  if [ -n "$deps" ]; then
    echo "$deps" | xargs -r pip install
  else
    echo "No dependencies found in pyproject.toml."
    exit 1
  fi
else
  echo "No requirements.txt or pyproject.toml found."
  exit 1
fi

echo "==> Creating database/user (idempotent)..."
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  sudo -u postgres createdb "${DB_NAME}"
fi

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

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

SMS_INBOUND_API_KEY=${SMS_INBOUND_API_KEY:-}
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
python manage.py compilemessages
python manage.py collectstatic --noinput

echo "==> Done. Run scripts/deploy.sh to start the service."
