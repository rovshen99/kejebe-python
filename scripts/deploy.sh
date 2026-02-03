#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kejebe}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
SUPERUSER_NAME="${SUPERUSER_NAME:-admin}"
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-Admin123!}"

cd "$APP_DIR"

echo "==> Activating venv..."
source .venv/bin/activate

echo "==> Running migrations..."
python manage.py migrate

echo "==> Collecting static..."
python manage.py collectstatic --noinput

echo "==> Ensuring superuser exists..."
DJANGO_SUPERUSER_USERNAME="$SUPERUSER_NAME" \
DJANGO_SUPERUSER_EMAIL="$SUPERUSER_EMAIL" \
DJANGO_SUPERUSER_PASSWORD="$SUPERUSER_PASSWORD" \
python manage.py createsuperuser --noinput || true

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
