#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kejebe}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-kejebe}"
SERVER_NAME="${SERVER_NAME:-}"
UPSTREAM_HOST="${UPSTREAM_HOST:-127.0.0.1}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8000}"
CLIENT_MAX_BODY_SIZE="${CLIENT_MAX_BODY_SIZE:-20m}"

MEDIA_PROXY_ENABLED="${MEDIA_PROXY_ENABLED:-false}"
MEDIA_SERVER_NAME="${MEDIA_SERVER_NAME:-}"
MINIO_UPSTREAM_HOST="${MINIO_UPSTREAM_HOST:-127.0.0.1}"
MINIO_UPSTREAM_PORT="${MINIO_UPSTREAM_PORT:-9000}"

ENABLE_SSL="${ENABLE_SSL:-false}"
SSL_MODE="${SSL_MODE:-auto}"            # auto|existing
SSL_PROVIDER="${SSL_PROVIDER:-letsencrypt}"  # letsencrypt|zerossl
ACME_EMAIL="${ACME_EMAIL:-${CERTBOT_EMAIL:-}}"
ZEROSSL_EAB_KID="${ZEROSSL_EAB_KID:-}"
ZEROSSL_EAB_HMAC_KEY="${ZEROSSL_EAB_HMAC_KEY:-}"

RAW_API_SSL_CERT_PATH="${API_SSL_CERT_PATH:-}"
RAW_API_SSL_KEY_PATH="${API_SSL_KEY_PATH:-}"
RAW_MEDIA_SSL_CERT_PATH="${MEDIA_SSL_CERT_PATH:-}"
RAW_MEDIA_SSL_KEY_PATH="${MEDIA_SSL_KEY_PATH:-}"

SITE_FILE="/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"

to_bool() {
  case "${1,,}" in
    1|true|yes|y) echo "true" ;;
    *) echo "false" ;;
  esac
}

ensure_required() {
  local name="$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "$name is required"
    exit 1
  fi
}

activate_site() {
  sudo ln -sf "$SITE_FILE" "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf"
  sudo rm -f /etc/nginx/sites-enabled/default
}

test_and_reload_nginx() {
  sudo nginx -t
  sudo systemctl enable --now nginx
  sudo systemctl reload nginx
}

write_http_config() {
  local tmp_file
  tmp_file="$(mktemp)"

  cat > "$tmp_file" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${SERVER_NAME};

    client_max_body_size ${CLIENT_MAX_BODY_SIZE};

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
        access_log off;
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    location / {
        proxy_pass http://${UPSTREAM_HOST}:${UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 120s;
    }
}
EOF

  if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
    cat >> "$tmp_file" <<EOF

server {
    listen 80;
    listen [::]:80;
    server_name ${MEDIA_SERVER_NAME};

    client_max_body_size ${CLIENT_MAX_BODY_SIZE};

    location / {
        proxy_pass http://${MINIO_UPSTREAM_HOST}:${MINIO_UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
    }
}
EOF
  fi

  sudo mv "$tmp_file" "$SITE_FILE"
  sudo chown root:root "$SITE_FILE"
  sudo chmod 644 "$SITE_FILE"
}

write_ssl_config() {
  local tmp_file
  tmp_file="$(mktemp)"

  cat > "$tmp_file" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${SERVER_NAME};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${SERVER_NAME};

    ssl_certificate ${API_SSL_CERT_PATH};
    ssl_certificate_key ${API_SSL_KEY_PATH};

    client_max_body_size ${CLIENT_MAX_BODY_SIZE};

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
        access_log off;
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    location / {
        proxy_pass http://${UPSTREAM_HOST}:${UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 120s;
    }
}
EOF

  if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
    cat >> "$tmp_file" <<EOF

server {
    listen 80;
    listen [::]:80;
    server_name ${MEDIA_SERVER_NAME};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${MEDIA_SERVER_NAME};

    ssl_certificate ${MEDIA_SSL_CERT_PATH};
    ssl_certificate_key ${MEDIA_SSL_KEY_PATH};

    client_max_body_size ${CLIENT_MAX_BODY_SIZE};

    location / {
        proxy_pass http://${MINIO_UPSTREAM_HOST}:${MINIO_UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
    }
}
EOF
  fi

  sudo mv "$tmp_file" "$SITE_FILE"
  sudo chown root:root "$SITE_FILE"
  sudo chmod 644 "$SITE_FILE"
}

install_nginx() {
  echo "==> Installing nginx..."
  sudo apt update
  sudo apt install -y nginx
}

issue_ssl_auto() {
  local domains
  domains=(-d "$SERVER_NAME")
  if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
    domains+=(-d "$MEDIA_SERVER_NAME")
  fi

  if [ "$SSL_PROVIDER" = "letsencrypt" ]; then
    echo "==> Installing certbot..."
    sudo apt install -y certbot python3-certbot-nginx
    echo "==> Requesting certificates from Let's Encrypt..."
    sudo certbot certonly --nginx \
      --non-interactive \
      --agree-tos \
      -m "$ACME_EMAIL" \
      "${domains[@]}"
  else
    echo "==> Installing acme.sh dependencies..."
    sudo apt install -y curl

    local acme_sh
    acme_sh="/root/.acme.sh/acme.sh"
    if [ ! -x "$acme_sh" ]; then
      echo "==> Installing acme.sh..."
      curl -fsSL https://get.acme.sh | sudo sh
    fi

    echo "==> Registering ZeroSSL account..."
    if [ -n "$ZEROSSL_EAB_KID" ] && [ -n "$ZEROSSL_EAB_HMAC_KEY" ]; then
      sudo "$acme_sh" --register-account \
        -m "$ACME_EMAIL" \
        --server zerossl \
        --eab-kid "$ZEROSSL_EAB_KID" \
        --eab-hmac-key "$ZEROSSL_EAB_HMAC_KEY"
    else
      sudo "$acme_sh" --register-account -m "$ACME_EMAIL" --server zerossl || {
        echo "ZeroSSL registration failed. Set ZEROSSL_EAB_KID and ZEROSSL_EAB_HMAC_KEY if required."
        exit 1
      }
    fi

    echo "==> Issuing ZeroSSL certificate..."
    sudo "$acme_sh" --issue --nginx --server zerossl "${domains[@]}"

    sudo mkdir -p /etc/nginx/ssl
    sudo "$acme_sh" --install-cert -d "$SERVER_NAME" \
      --key-file "/etc/nginx/ssl/${SERVER_NAME}.key" \
      --fullchain-file "/etc/nginx/ssl/${SERVER_NAME}.crt" \
      --reloadcmd "systemctl reload nginx"

    API_SSL_CERT_PATH="/etc/nginx/ssl/${SERVER_NAME}.crt"
    API_SSL_KEY_PATH="/etc/nginx/ssl/${SERVER_NAME}.key"
    if [ "$MEDIA_PROXY_ENABLED" = "true" ] && [ -z "$RAW_MEDIA_SSL_CERT_PATH" ] && [ -z "$RAW_MEDIA_SSL_KEY_PATH" ]; then
      MEDIA_SSL_CERT_PATH="$API_SSL_CERT_PATH"
      MEDIA_SSL_KEY_PATH="$API_SSL_KEY_PATH"
    fi
  fi
}

MEDIA_PROXY_ENABLED="$(to_bool "$MEDIA_PROXY_ENABLED")"
ENABLE_SSL="$(to_bool "$ENABLE_SSL")"
SSL_PROVIDER="${SSL_PROVIDER,,}"
SSL_MODE="${SSL_MODE,,}"

ensure_required "SERVER_NAME" "$SERVER_NAME"
if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
  ensure_required "MEDIA_SERVER_NAME" "$MEDIA_SERVER_NAME"
fi
if [ "$ENABLE_SSL" = "true" ] && [ "$SERVER_NAME" = "_" ]; then
  echo "SERVER_NAME cannot be '_' when ENABLE_SSL=true"
  exit 1
fi
if [ "$ENABLE_SSL" = "true" ] && [ "$SSL_MODE" = "auto" ]; then
  ensure_required "ACME_EMAIL (or CERTBOT_EMAIL)" "$ACME_EMAIL"
fi
if [ "$ENABLE_SSL" = "true" ] && [ "$SSL_PROVIDER" != "letsencrypt" ] && [ "$SSL_PROVIDER" != "zerossl" ]; then
  echo "Unsupported SSL_PROVIDER: $SSL_PROVIDER (use letsencrypt or zerossl)"
  exit 1
fi
if [ "$ENABLE_SSL" = "true" ] && [ "$SSL_MODE" != "auto" ] && [ "$SSL_MODE" != "existing" ]; then
  echo "Unsupported SSL_MODE: $SSL_MODE (use auto or existing)"
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "App directory not found: $APP_DIR"
  exit 1
fi

if [ -f "$APP_DIR/.env" ]; then
  echo "==> Loading .env..."
  set -a
  # shellcheck disable=SC1090
  . "$APP_DIR/.env"
  set +a
fi

API_SSL_CERT_PATH="${RAW_API_SSL_CERT_PATH:-/etc/letsencrypt/live/${SERVER_NAME}/fullchain.pem}"
API_SSL_KEY_PATH="${RAW_API_SSL_KEY_PATH:-/etc/letsencrypt/live/${SERVER_NAME}/privkey.pem}"
if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
  MEDIA_SSL_CERT_PATH="${RAW_MEDIA_SSL_CERT_PATH:-/etc/letsencrypt/live/${MEDIA_SERVER_NAME}/fullchain.pem}"
  MEDIA_SSL_KEY_PATH="${RAW_MEDIA_SSL_KEY_PATH:-/etc/letsencrypt/live/${MEDIA_SERVER_NAME}/privkey.pem}"
fi

install_nginx

echo "==> Writing HTTP nginx config..."
write_http_config
activate_site
test_and_reload_nginx

if [ "$ENABLE_SSL" = "true" ]; then
  if [ "$SSL_MODE" = "auto" ]; then
    issue_ssl_auto
  fi

  if [ "$MEDIA_PROXY_ENABLED" = "true" ] && [ ! -f "$MEDIA_SSL_CERT_PATH" ] && [ -f "$API_SSL_CERT_PATH" ] && [ -f "$API_SSL_KEY_PATH" ]; then
    MEDIA_SSL_CERT_PATH="$API_SSL_CERT_PATH"
    MEDIA_SSL_KEY_PATH="$API_SSL_KEY_PATH"
  fi

  ensure_required "API_SSL_CERT_PATH" "$API_SSL_CERT_PATH"
  ensure_required "API_SSL_KEY_PATH" "$API_SSL_KEY_PATH"
  if [ ! -f "$API_SSL_CERT_PATH" ] || [ ! -f "$API_SSL_KEY_PATH" ]; then
    echo "API certificate files not found:"
    echo "  $API_SSL_CERT_PATH"
    echo "  $API_SSL_KEY_PATH"
    exit 1
  fi

  if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
    ensure_required "MEDIA_SSL_CERT_PATH" "$MEDIA_SSL_CERT_PATH"
    ensure_required "MEDIA_SSL_KEY_PATH" "$MEDIA_SSL_KEY_PATH"
    if [ ! -f "$MEDIA_SSL_CERT_PATH" ] || [ ! -f "$MEDIA_SSL_KEY_PATH" ]; then
      echo "Media certificate files not found:"
      echo "  $MEDIA_SSL_CERT_PATH"
      echo "  $MEDIA_SSL_KEY_PATH"
      exit 1
    fi
  fi

  echo "==> Writing SSL nginx config..."
  write_ssl_config
  activate_site
  test_and_reload_nginx
fi

echo "==> Done."
echo "Configured API: ${SERVER_NAME} -> http://${UPSTREAM_HOST}:${UPSTREAM_PORT}"
if [ "$MEDIA_PROXY_ENABLED" = "true" ]; then
  echo "Configured Media: ${MEDIA_SERVER_NAME} -> http://${MINIO_UPSTREAM_HOST}:${MINIO_UPSTREAM_PORT}"
fi
if [ "$ENABLE_SSL" = "true" ]; then
  echo "SSL enabled (${SSL_MODE}/${SSL_PROVIDER})"
fi
