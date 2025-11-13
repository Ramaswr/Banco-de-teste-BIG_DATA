#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"
LOGFILE="$PROJECT_DIR/deploy/run-caddy-on-host.log"

DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"

if [ "$EUID" -ne 0 ]; then
  echo "Aviso: este script usa comandos que requerem sudo. Execute como:"
  echo "  DOMAIN=example.duckdns.org EMAIL=you@domain.tld sudo bash $0"
  echo "Ou execute e confirme sudo quando solicitado."
fi

if [ -z "$DOMAIN" ]; then
  echo "Uso: DOMAIN=seu_domino.duckdns.org EMAIL=seu@email sudo bash $0"
  exit 1
fi

mkdir -p "$(dirname "$LOGFILE")"

echo "=== run-caddy-on-host.sh START: $DOMAIN ($TIMESTAMP) ===" | tee -a "$LOGFILE"

echo "Projeto: $PROJECT_DIR" | tee -a "$LOGFILE"

# Backup de arquivos de configuração do Caddy
if [ -f /etc/caddy/Caddyfile ]; then
  sudo mkdir -p /etc/caddy/backup
  sudo cp -a /etc/caddy/Caddyfile /etc/caddy/backup/Caddyfile.$TIMESTAMP
  echo "Backup: /etc/caddy/Caddyfile -> /etc/caddy/backup/Caddyfile.$TIMESTAMP" | tee -a "$LOGFILE"
fi

# Parar servidores web que possam conflitar (nginx/apache)
for svc in nginx apache2 httpd; do
  if sudo systemctl is-active --quiet "$svc" 2>/dev/null; then
    echo "Parando $svc para liberar portas 80/443" | tee -a "$LOGFILE"
    sudo systemctl stop "$svc" || true
  fi
done

# Executa o script de setup não-interativo
SETUP_SCRIPT="$PROJECT_DIR/deploy/setup_caddy_noninteractive.sh"
if [ ! -f "$SETUP_SCRIPT" ]; then
  echo "Erro: script de setup não encontrado: $SETUP_SCRIPT" | tee -a "$LOGFILE"
  exit 1
fi

sudo chmod +x "$SETUP_SCRIPT" || true

echo "Executando setup: $SETUP_SCRIPT" | tee -a "$LOGFILE"
# Executa o setup com as variáveis necessárias e grava saída no log
if ! sudo DOMAIN="$DOMAIN" EMAIL="${EMAIL}" bash "$SETUP_SCRIPT" 2>&1 | tee -a "$LOGFILE"; then
  echo "Aviso: o setup retornou com erro. Verifique $LOGFILE e o journal do sistema." | tee -a "$LOGFILE"
fi

# Verificações pós-instalação
echo "--- Verificando status do Caddy ---" | tee -a "$LOGFILE"
sudo systemctl status caddy --no-pager 2>&1 | tee -a "$LOGFILE" || true

echo "--- Verificando escutas nas portas 80/443 ---" | tee -a "$LOGFILE"
sudo ss -ltnp | grep -E ':80|:443' 2>/dev/null || true

echo "--- Teste HTTPS (curl) ---" | tee -a "$LOGFILE"
if command -v curl >/dev/null 2>&1; then
  curl -I -k "https://$DOMAIN" 2>&1 | tee -a "$LOGFILE" || true
else
  echo "curl não encontrado; pulei o teste HTTPS" | tee -a "$LOGFILE"
fi

echo "=== run-caddy-on-host.sh END ===" | tee -a "$LOGFILE"

echo "Logs gravados em: $LOGFILE"
exit 0
