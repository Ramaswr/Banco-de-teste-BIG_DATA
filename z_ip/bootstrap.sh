#!/usr/bin/env bash
set -euo pipefail

# bootstrap.sh — prepara ambiente para análise/pentest
# Uso: ./bootstrap.sh
# - cria virtualenv em .venv
# - instala dependências do requirements.txt
# - imprime instruções de uso

echo "Iniciando bootstrap do ambiente..."
PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"

if [ ! -x "$(command -v $PYTHON)" ]; then
  echo "Python não encontrado: $PYTHON" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Criando virtualenv em $VENV_DIR..."
  $PYTHON -m venv "$VENV_DIR"
fi

# ativar venv e instalar requirements
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ -f requirements.txt ]; then
  echo "Instalando dependências do requirements.txt..."
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "Atenção: requirements.txt não encontrado. Instalações puladas." >&2
fi

# checagens rápidas
python -c "import sys; print('Python:', sys.version.splitlines()[0])"
python -c "import pkgutil; print('pandas:', bool(pkgutil.find_loader('pandas'))); print('streamlit:', bool(pkgutil.find_loader('streamlit')))"

echo ""
echo "Ambiente pronto. Para ativar use: source .venv/bin/activate"
echo "Executar app Streamlit: streamlit run app.py"

echo "Bootstrap finalizado."
