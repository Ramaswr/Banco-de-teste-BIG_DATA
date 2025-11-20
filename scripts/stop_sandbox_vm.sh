#!/usr/bin/env bash
# Desliga a VM de sandbox Linux endurecida no VirtualBox e desmonta recursos auxiliares.
set -euo pipefail

VM_NAME=${VM_NAME:-sandbox-linux}
SHARED_FOLDER_NAME=${SHARED_FOLDER_NAME:-sandboxqueue}

command -v VBoxManage >/dev/null 2>&1 || {
  echo "[ERRO] VBoxManage não encontrado no PATH." >&2
  exit 1
}

if ! VBoxManage list vms | grep -q "\"${VM_NAME}\""; then
  echo "[ERRO] VM ${VM_NAME} não encontrada no VirtualBox." >&2
  exit 1
fi

VM_INFO=$(VBoxManage showvminfo "${VM_NAME}" --machinereadable)
if echo "${VM_INFO}" | grep -q 'VMState="running"'; then
  echo "[INFO] Enviando sinal de desligamento para ${VM_NAME}." >&2
  VBoxManage controlvm "${VM_NAME}" acpipowerbutton || VBoxManage controlvm "${VM_NAME}" poweroff
  # Aguarda até parar
  for _ in {1..20}; do
    sleep 1
    if ! VBoxManage showvminfo "${VM_NAME}" --machinereadable | grep -q 'VMState="running"'; then
      break
    fi
  done
else
  echo "[INFO] VM ${VM_NAME} já estava desligada." >&2
fi

VBoxManage sharedfolder remove "${VM_NAME}" "${SHARED_FOLDER_NAME}" >/dev/null 2>&1 || true

echo "[OK] VM ${VM_NAME} parada e compartilhamento ${SHARED_FOLDER_NAME} removido." >&2
