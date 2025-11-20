#!/usr/bin/env bash
# Inicia a VM de sandbox Linux endurecida no VirtualBox restaurando um snapshot limpo
# e montando a pasta secure_uploads/sandbox_queue em modo somente leitura.
set -euo pipefail

VM_NAME=${VM_NAME:-sandbox-linux}
SNAPSHOT_NAME=${SNAPSHOT_NAME:-baseline}
SHARED_FOLDER_NAME=${SHARED_FOLDER_NAME:-sandboxqueue}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOST_QUEUE_DIR=${HOST_QUEUE_DIR:-"${REPO_ROOT}/secure_uploads/sandbox_queue"}

command -v VBoxManage >/dev/null 2>&1 || {
  echo "[ERRO] VBoxManage não encontrado no PATH." >&2
  exit 1
}

if [[ ! -d "${HOST_QUEUE_DIR}" ]]; then
  echo "[INFO] Criando diretório ${HOST_QUEUE_DIR}" >&2
  mkdir -p "${HOST_QUEUE_DIR}"
  chmod 700 "${HOST_QUEUE_DIR}"
fi

# Migrar VM para snapshot limpo caso esteja em execução
if VBoxManage showvminfo "${VM_NAME}" --machinereadable | grep -q 'VMState="running"'; then
  echo "[INFO] VM ${VM_NAME} em execução, forçando desligamento seguro." >&2
  VBoxManage controlvm "${VM_NAME}" poweroff || true
  sleep 3
fi

# Restaurar snapshot de referência
echo "[INFO] Restaurando snapshot ${SNAPSHOT_NAME} da VM ${VM_NAME}." >&2
VBoxManage snapshot "${VM_NAME}" restore "${SNAPSHOT_NAME}"

# Recriar compartilhamento somente leitura
VBoxManage sharedfolder remove "${VM_NAME}" "${SHARED_FOLDER_NAME}" >/dev/null 2>&1 || true
VBoxManage sharedfolder add "${VM_NAME}" --name "${SHARED_FOLDER_NAME}" --hostpath "${HOST_QUEUE_DIR}" --readonly

# Iniciar VM em modo headless
echo "[INFO] Iniciando VM ${VM_NAME} em modo headless." >&2
VBoxManage startvm "${VM_NAME}" --type headless

echo "[OK] Sandbox inicializada com snapshot limpo e pasta ${HOST_QUEUE_DIR} montada." >&2
