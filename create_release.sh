#!/usr/bin/env bash
# Script interativo para criar release no GitHub
# Pede o token do usuário de forma segura (não fica salvo no histórico)

set -e

echo "=========================================="
echo "GitHub Release Creator — Banco de teste BIG_DATA"
echo "=========================================="
echo ""
echo "Este script criará uma Release no GitHub com o arquivo zip_Jerr.js"
echo ""
echo "Instruções para gerar o token:"
echo "1. Abra: https://github.com/settings/tokens"
echo "2. Generate new token (classic)"
echo "3. Scope: repo (ou public_repo)"
echo "4. Copie o token gerado"
echo ""

read -sp "Cole seu GitHub Personal Access Token (não será exibido): " TOKEN
echo ""

if [ -z "$TOKEN" ]; then
  echo "Erro: Token não fornecido."
  exit 1
fi

echo ""
echo "Criando release v0.1.0..."
echo ""

# Executar o script Python com o token
python3 create_release.py "$TOKEN" Ramaswr Banco-de-teste-BIG_DATA v0.1.0 zip_Jerr.js

echo ""
echo "✅ Concluído!"
echo ""
echo "Acesse a Release em:"
echo "https://github.com/Ramaswr/Banco-de-teste-BIG_DATA/releases/tag/v0.1.0"
