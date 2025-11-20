#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/security_reports"
mkdir -p "$REPORT_DIR"

info() { printf '\033[1;34m[info]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$1"; }

if ! command -v bandit >/dev/null 2>&1; then
  warn "Bandit não encontrado. Instale-o com: pip install -r requirements-dev.txt"
  exit 1
fi

info "Executando Bandit..."
bandit -ll -ii -x .venv,logs,streamlit_output,security_reports -r "$ROOT_DIR" \
  | tee "$REPORT_DIR/bandit.txt"

if command -v gitleaks >/dev/null 2>&1; then
  info "Executando Gitleaks..."
  gitleaks detect --source "$ROOT_DIR" --report-path "$REPORT_DIR/gitleaks.json" \
    --no-banner --redact --exit-code 1 || warn "Gitleaks encontrou possíveis segredos (ver relatório)."
else
  warn "Gitleaks não encontrado. Instale via https://github.com/gitleaks/gitleaks/releases e reexecute."
fi

info "Relatórios salvos em $REPORT_DIR"
