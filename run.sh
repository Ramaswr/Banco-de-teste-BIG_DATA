#!/usr/bin/env bash
# Script para executar o Streamlit app automaticamente
# Usa: ./run.sh
# - Cria/ativa venv se necessário
# - Instala requirements
# - Abre o navegador automaticamente
# - Executa o Streamlit app

set -euo pipefail

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

echo "==========================================="
echo "Banco de teste BIG_DATA — Streamlit App"
echo "==========================================="
echo ""

# 1. Verificar se Python está disponível
if ! command -v "$PYTHON" &> /dev/null; then
  echo "❌ Erro: Python não encontrado ($PYTHON)"
  exit 1
fi

# 2. Criar/ativar venv se não existir
if [ ! -d "$VENV_DIR" ]; then
  echo "📦 Criando ambiente virtual..."
  $PYTHON -m venv "$VENV_DIR"
fi

echo "✓ Ambiente virtual pronto"

# 3. Ativar venv
source "$VENV_DIR/bin/activate" || true

# 4. Instalar/atualizar requirements
if [ -f "requirements.txt" ]; then
  echo "📥 Instalando dependências..."
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  echo "✓ Dependências instaladas"
else
  echo "⚠️  Atenção: requirements.txt não encontrado"
fi

echo ""
echo "🚀 Iniciando Streamlit app..."
echo ""
if [ "${PUBLIC_MODE:-0}" = "1" ]; then
  STREAMLIT_ADDRESS="0.0.0.0"
  STREAMLIT_URL="http://localhost:8501"
  echo "📍 Abrindo em: http://0.0.0.0:8501 (modo público - somente execução via login)"
  echo "⚠️ ATENÇÃO: Em modo público, configure HTTPS/reverse-proxy em produção!"
else
  STREAMLIT_ADDRESS="localhost"
  STREAMLIT_URL="http://localhost:8501"
  echo "📍 Abrindo em: $STREAMLIT_URL"
fi
echo "   (Se o navegador não abrir automaticamente, acesse a URL acima)"
echo ""
echo "💡 Dicas:"
echo "   - Para parar: Pressione Ctrl+C"
echo "   - Recarregar o app: Pressione 'R' no navegador"
echo "   - Mostrar menu: Pressione 'C' no navegador"
echo ""

# 5. Abrir navegador (se disponível) — somente em modo local
open_browser_command() {
  local url="$1"
  if command -v xdg-open &> /dev/null; then
    echo "🔗 Usando xdg-open para abrir $url"
    xdg-open "$url" >/dev/null 2>&1 &
    return 0
  elif command -v open &> /dev/null; then
    echo "🔗 Usando open para abrir $url"
    open "$url" >/dev/null 2>&1 &
    return 0
  elif command -v start &> /dev/null; then
    echo "🔗 Usando start para abrir $url"
    start "$url" >/dev/null 2>&1 &
    return 0
  elif command -v "$PYTHON" &> /dev/null; then
    echo "🔗 Usando Python webbrowser para abrir $url"
    "$PYTHON" -c "import webbrowser; webbrowser.open('$url')" >/dev/null 2>&1 &
    return 0
  fi
  return 1
}

wait_for_streamlit() {
  local url="$1"
  local attempts=15
  local i
  for i in $(seq 1 "$attempts"); do
    if "$PYTHON" - "$url" <<'PY' >/dev/null 2>&1
import os
import sys
import urllib.request

url = sys.argv[1]
try:
    urllib.request.urlopen(url, timeout=1)
except Exception:
    sys.exit(1)
sys.exit(0)
PY
    then
      return 0
    fi
    sleep 1
  done
  return 1
}

if [ "${PUBLIC_MODE:-0}" != "1" ]; then
  (
    if wait_for_streamlit "$STREAMLIT_URL"; then
      if open_browser_command "$STREAMLIT_URL"; then
        echo "🔗 Abri o navegador automaticamente."
      else
        echo "⚠️  Nenhum comando de abertura automática disponível; abra $STREAMLIT_URL manualmente."
      fi
    else
      echo "⚠️  O Streamlit não respondeu em $STREAMLIT_URL antes de tentar abrir o navegador. Use o comando acima manualmente."
    fi
  ) &
fi

# 6. Executar Streamlit
if [ "${PUBLIC_MODE:-0}" = "1" ]; then
  # Bind to all interfaces for public access; keep app authentication enforced.
  streamlit run app.py --server.port=8501 --server.address="$STREAMLIT_ADDRESS" \
    --server.enableCORS=false --server.enableXsrfProtection=true
else
  streamlit run app.py --server.port=8501 --server.address="$STREAMLIT_ADDRESS"
fi

echo ""
echo "✓ App finalizado"

