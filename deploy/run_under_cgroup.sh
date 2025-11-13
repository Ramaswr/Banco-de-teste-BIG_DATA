#!/usr/bin/env bash
set -euo pipefail

# Helper para rodar um comando sob controlos de recursos via systemd-run (escopo)
# Uso:
#   DOMAIN=... EMAIL=... sudo ./deploy/run_under_cgroup.sh --cmd "python3 worker.py"
# Ou sem sudo para --user (systemd --user)

CMD="${1:-}"
if [ -z "$CMD" ]; then
  echo "Uso: sudo $0 --cmd \"seu comando aqui\""
  echo "Exemplo: sudo $0 --cmd \"python3 /path/to/worker_daemon.py\""
  exit 1
fi

# Configurações padrão de recurso (ajustáveis)
CPU_QUOTA="50%"   # usar no máximo 50% do CPU total
MEMORY_MAX="80%"  # limite genérico (systemd aceita bytes; % pode não ser suportado em algumas versões)

# montar comando systemd-run
# observar: este script deve ser rodado com sudo para aplicar limites no sistema
if [ "$EUID" -ne 0 ]; then
  echo "Requer sudo/root para aplicar limites globais via systemd-run. Execute com sudo." >&2
  exit 1
fi

SERVICE_NAME=bigdata-worker-$(date +%s)

echo "Criando scope systemd com CPUQuota=$CPU_QUOTA para o comando: $CMD"

# Nota: MemoryMax aceita unidade (ex: 4G). Usar uma aproximação caso queira ajustar.
sudo systemd-run --scope -p CPUQuota=$CPU_QUOTA $CMD

echo "Serviço em execução sob systemd scope. Use 'systemctl status' para verificar."

echo "Para parar, encontre o PID com: ps aux | grep '$CMD' ou use 'systemctl list-sessions' e mate o processo desejado." 
