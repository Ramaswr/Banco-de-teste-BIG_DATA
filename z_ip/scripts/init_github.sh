#!/usr/bin/env bash
# Script rápido para inicializar um repositório Git e subir para GitHub (assume que git está configurado)
# Uso:
# chmod +x scripts/init_github.sh
# ./scripts/init_github.sh <github-remote-url>

set -e
if [ -z "$1" ]; then
  echo "Uso: $0 <github-remote-url>"
  exit 1
fi
REMOTE_URL="$1"

git init
git add .
git commit -m "chore: initial commit - ETL Vendas (Banco de teste BIG_DATA)"

# adiciona remoto e empurra branch main
git branch -M main
git remote add origin "$REMOTE_URL"
git push -u origin main

echo "Pronto. Repositório inicializado e push para $REMOTE_URL"