#!/usr/bin/env bash
set -euo pipefail

SERVER_IP="13.38.71.209"
REPO_URL="https://github.com/dvillegastech/seguridad_back.git"
APP_DIR="/opt/seguridad_back"
NGINX_SITE="/etc/nginx/sites-available/seguridad_back"
NGINX_LINK="/etc/nginx/sites-enabled/seguridad_back"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

echo "Installing packages..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release git nginx ufw

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

systemctl enable --now docker

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker install failed." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Cloning repository..."
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "Updating repository..."
  git -C "$APP_DIR" pull --ff-only
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  cat > "$APP_DIR/.env" <<EOF
APNS_TOPIC=com.tu.bundleid
APNS_TEAM_ID=TU_TEAM_ID
APNS_KEY_ID=TU_KEY_ID
APNS_AUTH_KEY=-----BEGIN PRIVATE KEY-----\\nTU_P8_KEY\\n-----END PRIVATE KEY-----
EOF
  echo "Created $APP_DIR/.env with placeholders. Update APNs values before production use."
fi

cat > "$NGINX_SITE" <<EOF
server {
  listen 80;
  server_name $SERVER_IP;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
EOF

ln -sf "$NGINX_SITE" "$NGINX_LINK"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

ufw allow OpenSSH
ufw allow 80
ufw --force enable

echo "Starting backend..."
cd "$APP_DIR"
docker compose up -d --build

echo "Backend should be reachable at: http://$SERVER_IP/health"
