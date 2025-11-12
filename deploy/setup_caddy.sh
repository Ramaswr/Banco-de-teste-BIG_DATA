#!/usr/bin/env bash
# setup_caddy.sh
# Automatiza instalação/configuração do Caddy, deploy do serviço streamlit e firewall.
# IMPORTANTE: Execute este script como root (sudo) em seu servidor de produção.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Este script precisa ser executado com sudo/root. Ex: sudo ./setup_caddy.sh"
  exit 1
fi

read -p "Qual é o domínio que você quer usar? (ex: example.com): " DOMAIN
read -p "Qual é o email para certificados Let's Encrypt? (ex: you@example.com): " EMAIL

CADDYFILE_PATH="/etc/caddy/Caddyfile"
SYSTEMD_SRC="$(pwd)/deploy/systemd/streamlit-jerr.service"
SYSTEMD_DST="/etc/systemd/system/streamlit-jerr.service"

echo "\n=== Configurando Caddy para domain: $DOMAIN ===\n"

# 1) Instalar Caddy via repositório oficial (Debian/Ubuntu)
if command -v caddy >/dev/null 2>&1; then
  echo "Caddy já instalado"
else
  echo "Instalando Caddy..."
  apt update
  apt install -y debian-keyring debian-archive-keyring apt-transport-https
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | apt-key add -
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt update
  apt install -y caddy
fi

# 2) Gerar Caddyfile baseado no exemplo do repositório
if [ -f "$CADDYFILE_PATH" ]; then
  echo "Arquivo $CADDYFILE_PATH já existe." 
  read -p "Deseja sobrescrever? [y/N]: " OVER
  OVER=${OVER:-N}
  if [[ ! "$OVER" =~ ^[Yy]$ ]]; then
    echo "Pulando escrita do Caddyfile. Verifique /etc/caddy/Caddyfile manualmente." 
  else
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
    echo "Caddyfile escrito em $CADDYFILE_PATH"
  fi
else
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
  echo "Caddyfile criado em $CADDYFILE_PATH"
fi

# 3) Copiar unit systemd do app Streamlit
if [ -f "$SYSTEMD_SRC" ]; then
  echo "Copiando unit systemd para $SYSTEMD_DST"
  cp "$SYSTEMD_SRC" "$SYSTEMD_DST"
  systemctl daemon-reload
  systemctl enable --now streamlit-jerr.service
  echo "Serviço streamlit-jerr habilitado e iniciado (verifique com: systemctl status streamlit-jerr)"
else
  echo "Aviso: unit systemd fonte nao encontrada em $SYSTEMD_SRC. Verifique o arquivo no repositório." >&2
fi

# 4) Reload Caddy
echo "Recarregando Caddy..."
systemctl enable --now caddy
systemctl reload caddy || true

# 5) Firewall (UFW) - permissões recomendadas
if command -v ufw >/dev/null 2>&1; then
  echo "Configurando UFW: permitir SSH, HTTP, HTTPS; negar 8501 publicamente"
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw deny 8501/tcp || true
  ufw --force enable
  echo "UFW configurado"
else
  echo "UFW não encontrado — por favor, configure seu firewall manualmente (iptables/nft)."
fi

# 6) Recomendações finais
echo "\n✅ Setup concluído. A seguir:
 - Garanta que o DNS do domínio ($DOMAIN) aponte para este servidor
 - Verifique logs: sudo journalctl -u caddy -f
 - Verifique serviço: sudo systemctl status streamlit-jerr
 - Teste acessar: https://$DOMAIN
 - Se houver problemas, consulte deploy/README-deploy.md para passos manuais\n"
