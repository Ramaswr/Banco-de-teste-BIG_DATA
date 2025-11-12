#!/usr/bin/env bash
# make_public_readonly.sh
# Ajusta permissões para deixar o código do app visível em modo leitura para outros usuários,
# preservando a capacidade do proprietário (usuário 'jerr') de editar localmente.

set -euo pipefail

PROJECT_DIR="$(pwd)"
SENSITIVE_DIRS=(".secrets" "secure_uploads" "logs")

echo "🔐 Ajustando permissões para modo público (somente leitura para 'others')"

# 1) Garantir que o usuário dono tenha permissão completa
echo "➡️ Definindo permissões de dono (u+rwX) e removendo escrita para grupo/outros (go-w)"
find "$PROJECT_DIR" -type d -exec chmod u+rwx,go+rx,go-w {} +
find "$PROJECT_DIR" -type f -exec chmod u+rw,go+r,go-w {} +

# 2) Tornar diretórios sensíveis acessíveis somente ao dono
for d in "${SENSITIVE_DIRS[@]}"; do
  if [ -d "$PROJECT_DIR/$d" ]; then
    echo "➡️ Protegendo $d (700)"
    chmod 700 "$PROJECT_DIR/$d"
  fi
done

# 3) Garantir que o arquivo .secrets/credentials.json não seja comitado e esteja protegido
if [ -f ".secrets/credentials.json" ]; then
  chmod 600 .secrets/credentials.json
  echo "➡️ .secrets/credentials.json protegido (600)"
fi

# 4) Bloquear escrita de ocorrências de scripts de inicialização para outros
for file in run.sh setup_security.sh; do
  if [ -f "$file" ]; then
    chmod u+rwx,go+rx,go-w "$file"
  fi
done

# 5) Informação final
echo "\n✅ Permissões ajustadas."
echo "- Código e arquivos são legíveis por outros (somente leitura)."
echo "- Diretórios sensíveis (.secrets, secure_uploads, logs) são somente do dono (700)."

echo "\n⚠️ Recomendações adicionais para modo público:
 - Execute o app atrás de um reverse-proxy com TLS (nginx/caddy) para habilitar HTTPS.
 - Limite o acesso de IP caso necessário (firewall).
 - Monitore security.log regularmente."
