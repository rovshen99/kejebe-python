#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kejebe}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
SUPERUSER_PHONE="${SUPERUSER_PHONE:-+9936100000}"
SUPERUSER_NAME="${SUPERUSER_NAME:-admin}"
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-Admin123!}"
LEAFLET_DIR="apps/services/static/vendor/leaflet/images"
LEAFLET_REQUIRED_FILES=("layers.png" "layers-2x.png")

check_required_static_assets() {
  local missing=0
  for file in "${LEAFLET_REQUIRED_FILES[@]}"; do
    if [ ! -f "${LEAFLET_DIR}/${file}" ]; then
      echo "Missing required static asset: ${LEAFLET_DIR}/${file}"
      missing=1
    fi
  done

  if [ "$missing" -ne 0 ]; then
    echo "Static preflight failed."
    echo "Place missing files into ${LEAFLET_DIR} and rerun this script."
    exit 1
  fi
}

cd "$APP_DIR"

if [ -f ".env" ]; then
  echo "==> Loading .env..."
  set -a
  . ./.env
  set +a
fi

echo "==> Activating venv..."
source .venv/bin/activate

echo "==> Running migrations..."
python manage.py migrate

echo "==> Compiling translations..."
python manage.py compilemessages

echo "==> Collecting static..."
check_required_static_assets
python manage.py collectstatic --noinput

echo "==> Ensuring superuser exists..."
DJANGO_SUPERUSER_USERNAME="$SUPERUSER_NAME" \
DJANGO_SUPERUSER_EMAIL="$SUPERUSER_EMAIL" \
DJANGO_SUPERUSER_PASSWORD="$SUPERUSER_PASSWORD" \
python manage.py createsuperuser --noinput --phone "$SUPERUSER_PHONE" || true

echo "==> Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/kejebe.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Kejebe Django App
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn kejebe.wsgi:application \
  --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now kejebe
sudo systemctl status kejebe --no-pager

echo "==> Done. App is running on 127.0.0.1:8000"
