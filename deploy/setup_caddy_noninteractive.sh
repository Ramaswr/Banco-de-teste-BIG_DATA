#!/usr/bin/env bash
# setup_caddy_noninteractive.sh
# Script não-interativo para instalar/configurar Caddy + systemd + UFW.
# Uso (exemplo):
# DOMAIN=example.com EMAIL=you@example.com sudo ./setup_caddy_noninteractive.sh

set -euo pipefail

# Read DOMAIN and EMAIL from env or args
DOMAIN=${DOMAIN:-""}
EMAIL=${EMAIL:-""}

# Allow passing as args: ./script domain email
if [ -z "$DOMAIN" ] && [ "$#" -ge 1 ]; then
  DOMAIN="$1"
fi
if [ -z "$EMAIL" ] && [ "$#" -ge 2 ]; then
  EMAIL="$2"
fi

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "Usage: DOMAIN=example.com EMAIL=you@example.com sudo $0"
  echo "Or: sudo $0 example.com you@example.com"
  exit 1
fi

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)."
  exit 1
fi

CADDYFILE_PATH="/etc/caddy/Caddyfile"
SYSTEMD_SRC="$(pwd)/deploy/systemd/streamlit-jerr.service"
SYSTEMD_DST="/etc/systemd/system/streamlit-jerr.service"

echo "[1/6] Installing Caddy if missing..."
if command -v caddy >/dev/null 2>&1; then
  echo "Caddy already installed"
else
  apt update
  apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | apt-key add -
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt update
  apt install -y caddy
fi

echo "[2/6] Writing Caddyfile for $DOMAIN..."
cat > "$CADDYFILE_PATH" <<EOF
$DOMAIN {
    reverse_proxy localhost:8501

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy same-origin
    }

    tls $EMAIL
}
EOF

chmod 644 "$CADDYFILE_PATH"

echo "[3/6] Installing systemd service for Streamlit..."
if [ -f "$SYSTEMD_SRC" ]; then
  cp "$SYSTEMD_SRC" "$SYSTEMD_DST"
  systemctl daemon-reload
  systemctl enable --now streamlit-jerr.service
else
  echo "Warning: source systemd unit not found at $SYSTEMD_SRC" >&2
fi

echo "[4/6] Enabling and reloading Caddy..."
systemctl enable --now caddy
systemctl reload caddy || true

echo "[5/6] Configuring UFW (if present)..."
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw deny 8501/tcp || true
  ufw --force enable
else
  echo "UFW not found; please configure firewall manually (iptables/nft)"
fi

echo "[6/6] Done. Final checks:"
cat <<EOF
- Verify DNS points: $DOMAIN -> this server IP
- Check Caddy logs: sudo journalctl -u caddy -f
- Check Streamlit service: sudo systemctl status streamlit-jerr
- Access: https://$DOMAIN
EOF

exit 0
