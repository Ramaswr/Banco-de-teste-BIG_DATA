#!/usr/bin/env bash
# setup_security.sh - Script para configurar segurança da aplicação

set -e

echo "🔐 ============================================"
echo "   Configuração de Segurança da Aplicação"
echo "============================================"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== CRIAR DIRETÓRIOS SEGUROS ====================
echo -e "\n${YELLOW}1️⃣ Criando diretórios seguros...${NC}"

mkdir -p .secrets
chmod 700 .secrets
echo -e "${GREEN}✅ .secrets/ (modo 700)${NC}"

mkdir -p secure_uploads
chmod 700 secure_uploads
echo -e "${GREEN}✅ secure_uploads/ (modo 700)${NC}"

mkdir -p logs
chmod 700 logs
echo -e "${GREEN}✅ logs/ (modo 700)${NC}"

# ==================== ADICIONAR AO GITIGNORE ====================
echo -e "\n${YELLOW}2️⃣ Configurando .gitignore...${NC}"

if [ ! -f .gitignore ]; then
    echo "" > .gitignore
fi

# Adicionar entradas de segurança se não existirem
for entry in ".secrets/" "security.log" "secure_uploads/" "logs/"; do
    if ! grep -q "^$entry$" .gitignore; then
        echo "$entry" >> .gitignore
        echo -e "${GREEN}✅ Adicionado ao .gitignore: $entry${NC}"
    fi
done

# ==================== GERAR CREDENCIAIS INICIAIS ====================
echo -e "\n${YELLOW}3️⃣ Verificando credenciais...${NC}"

if [ ! -f .secrets/credentials.json ]; then
    echo -e "${YELLOW}⚠️  Arquivo de credenciais não encontrado!${NC}"
    echo -e "  As credenciais padrão estão em memory em security.py"
    echo -e "  Para usar arquivo custom, crie .secrets/credentials.json"
else
    echo -e "${GREEN}✅ .secrets/credentials.json encontrado${NC}"
fi

# ==================== VERIFICAR PERMISSÕES ====================
echo -e "\n${YELLOW}4️⃣ Verificando permissões de diretórios...${NC}"

for dir in .secrets secure_uploads logs; do
    perms=$(stat -c %a "$dir" 2>/dev/null || stat -f %A "$dir" 2>/dev/null || echo "???")
    if [ "$perms" = "700" ] || [ "$perms" = "rwx------" ]; then
        echo -e "${GREEN}✅ $dir: $perms${NC}"
    else
        echo -e "${RED}❌ $dir: $perms (esperado 700)${NC}"
        chmod 700 "$dir"
        echo -e "${GREEN}✅ Permissões corrigidas${NC}"
    fi
done

# ==================== CRIAR ARQUIVO DE SECRETS EXEMPLO ====================
echo -e "\n${YELLOW}5️⃣ Criando template de credenciais (exemplo)...${NC}"

SECRETS_TEMPLATE=".secrets/credentials.example.json"

cat > "$SECRETS_TEMPLATE" << 'EOF'
{
  "users": {
    "admin": "pbkdf2:100000:salt_hex:hash_hex",
    "usuario": "pbkdf2:100000:salt_hex:hash_hex"
  },
  "api_key": "chave_secreta_aqui",
  "encryption_key": "chave_encriptacao_32_bytes_hex"
}
EOF

echo -e "${GREEN}✅ Template criado em: $SECRETS_TEMPLATE${NC}"
echo -e "${YELLOW}   Customize este arquivo conforme necessário${NC}"

# ==================== GERAR HASH DE SENHA ====================
echo -e "\n${YELLOW}6️⃣ Script para gerar hash de senha...${NC}"

cat > .secrets/generate_password_hash.py << 'EOF'
#!/usr/bin/env python3
"""Gera hash seguro de senha para credentials.json"""

import hashlib
import os
import getpass

def hash_password(password: str) -> str:
    """Hash seguro de senha com salt."""
    salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return f"pbkdf2:100000:{salt.hex()}:{pwd_hash.hex()}"

if __name__ == '__main__':
    print("=== Gerador de Hash de Senha ===")
    password = getpass.getpass("Digite a senha: ")
    confirm = getpass.getpass("Confirme a senha: ")
    
    if password != confirm:
        print("❌ Senhas não correspondem!")
        exit(1)
    
    if len(password) < 8:
        print("❌ Senha deve ter no mínimo 8 caracteres!")
        exit(1)
    
    hashed = hash_password(password)
    print(f"\n✅ Hash gerado (copie para credentials.json):")
    print(hashed)
EOF

chmod +x .secrets/generate_password_hash.py
echo -e "${GREEN}✅ Script gerador de hash criado${NC}"

# ==================== CRIAR ARQUIVO DE CONFIGURAÇÃO ====================
echo -e "\n${YELLOW}7️⃣ Configuração de Segurança...${NC}"

cat > .env.security << 'EOF'
# Configurações de Segurança da Aplicação

# Rate Limiting
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Session
SESSION_TIMEOUT=3600

# Arquivo
MAX_FILE_SIZE=104857600  # 100 MB em bytes

# SSL/TLS (para Streamlit)
STREAMLIT_SERVER_SSL_CERTFILE=
STREAMLIT_SERVER_SSL_KEYFILE=

# Logging
LOG_LEVEL=INFO
LOG_FILE=security.log
EOF

echo -e "${GREEN}✅ Arquivo .env.security criado${NC}"

# ==================== VERIFICAR DEPENDÊNCIAS ====================
echo -e "\n${YELLOW}8️⃣ Verificando dependências de segurança...${NC}"

python3 << 'PYEOF'
import sys

required_modules = [
    'hashlib',
    'hmac',
    'secrets',
    'logging',
    'json'
]

missing = []
for module in required_modules:
    try:
        __import__(module)
        print(f"✅ {module}")
    except ImportError:
        print(f"❌ {module}")
        missing.append(module)

if missing:
    print(f"\n⚠️  Módulos faltando: {', '.join(missing)}")
    sys.exit(1)
else:
    print("\n✅ Todas as dependências instaladas!")
PYEOF

# ==================== RESUMO ====================
echo -e "\n${GREEN}============================================"
echo "   ✅ Configuração de Segurança Completa!"
echo "============================================${NC}"

echo -e "\n${YELLOW}📋 Próximos passos:${NC}"
echo -e "  1. ${GREEN}Altere credenciais padrão${NC} em security.py"
echo -e "  2. ${GREEN}Gere hashes de senha${NC}: python3 .secrets/generate_password_hash.py"
echo -e "  3. ${GREEN}Configure .secrets/credentials.json${NC} (opcional, em produção)"
echo -e "  4. ${GREEN}Revise SECURITY.md${NC} para mais detalhes"
echo -e "  5. ${GREEN}Teste as proteções${NC} localmente antes de produção"

echo -e "\n${YELLOW}🔒 Diretórios de segurança:${NC}"
echo -e "  .secrets/          ${GREEN}(modo 700)${NC} - Credenciais sensíveis"
echo -e "  secure_uploads/    ${GREEN}(modo 700)${NC} - Uploads validados"
echo -e "  logs/              ${GREEN}(modo 700)${NC} - Logs de segurança"

echo -e "\n${YELLOW}📚 Documentação:${NC}"
echo -e "  Leia ${GREEN}SECURITY.md${NC} para guia completo de segurança"

echo -e "\n${YELLOW}⚠️  Lembre-se:${NC}"
echo -e "  • NÃO commita .secrets/ no Git"
echo -e "  • NÃO use senhas padrão em produção"
echo -e "  • USE HTTPS em produção (não HTTP)"
echo -e "  • REVISE security.log regularmente"

echo -e "\n${GREEN}Sucesso! Aplicação segura e protegida.${NC}\n"
