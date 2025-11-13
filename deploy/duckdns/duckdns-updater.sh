#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="$SCRIPT_DIR/../../.secrets"
ENV_FILE="$SECRETS_DIR/duckdns.env"
LOGFILE="$SCRIPT_DIR/duckdns-update.log"

if [ ! -f "$ENV_FILE" ]; then
  echo "Arquivo de ambiente $ENV_FILE não encontrado. Crie .secrets/duckdns.env com DOMAIN e TOKEN." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [ -z "$DOMAIN" ] || [ -z "$TOKEN" ]; then
  echo "DOMAIN ou TOKEN não configurados em $ENV_FILE" >&2
  exit 1
fi

URL="https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip="
RESP=$(curl -fsS --retry 3 "$URL" || true)
if [ -z "$RESP" ]; then
  echo "Falha ao contactar DuckDNS" | tee -a "$LOGFILE"
  exit 1
fi

echo "$(date -u +"%Y-%m-%d %H:%M:%S") - $RESP" >> "$LOGFILE"
echo "$RESP"
