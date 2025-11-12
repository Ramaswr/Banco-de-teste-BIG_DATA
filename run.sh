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
  echo "📍 Abrindo em: http://0.0.0.0:8501 (modo público - somente execução via login)"
  echo "⚠️ ATENÇÃO: Em modo público, configure HTTPS/reverse-proxy em produção!"
else
  echo "📍 Abrindo em: http://localhost:8501"
fi
echo "   (Se o navegador não abrir automaticamente, acesse a URL acima)"
echo ""
echo "💡 Dicas:"
echo "   - Para parar: Pressione Ctrl+C"
echo "   - Recarregar o app: Pressione 'R' no navegador"
echo "   - Mostrar menu: Pressione 'C' no navegador"
echo ""

# 5. Abrir navegador (se disponível)
if [ "${PUBLIC_MODE:-0}" != "1" ]; then
  if command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:8501 &
  elif command -v open &> /dev/null; then
    # macOS
    open http://localhost:8501 &
  elif command -v start &> /dev/null; then
    # Windows
    start http://localhost:8501 &
  fi
fi
elif command -v open &> /dev/null; then
  # macOS
  open http://localhost:8501 &
elif command -v start &> /dev/null; then
  # Windows
  start http://localhost:8501 &
fi

# 6. Executar Streamlit
if [ "${PUBLIC_MODE:-0}" = "1" ]; then
  # Bind to all interfaces for public access; keep app authentication enforced.
  streamlit run app.py --server.port=8501 --server.address=0.0.0.0 \
    --server.enableCORS=false --server.enableXsrfProtection=true
else
  streamlit run app.py --server.port=8501 --server.address=localhost
fi

echo ""
echo "✓ App finalizado"
