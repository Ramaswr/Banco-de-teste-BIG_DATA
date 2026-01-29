#!/usr/bin/env python3
"""
Gerador simples de arquivo de credenciais para `.secrets/credentials.json`.
Uso:
    python scripts/create_credentials.py --username admin --role super_admin
O script irá pedir a senha e gravar o arquivo (cria .secrets/ se necessário).
"""
import argparse
import getpass
import json
import os
from security import CredentialManager

parser = argparse.ArgumentParser(description="Gerar .secrets/credentials.json com usuário admin")
parser.add_argument("--username", required=True)
parser.add_argument("--role", default="super_admin")
args = parser.parse_args()

username = args.username
role = args.role
pwd = getpass.getpass(f"Senha para {username}: ")
if not pwd:
    print("Senha vazia, abortando")
    raise SystemExit(1)

cm = CredentialManager()
# usar método estático para criar hash
pwd_hash = cm._hash_password(pwd)

os.makedirs('.secrets', exist_ok=True)
creds_path = os.path.join('.secrets', 'credentials.json')
creds = {"users": {username: {"password": pwd_hash, "role": role}}}
with open(creds_path + '.tmp', 'w') as f:
    json.dump(creds, f, indent=2)
os.replace(creds_path + '.tmp', creds_path)
try:
    os.chmod(creds_path, 0o600)
except Exception:
    pass
print(f"Arquivo gravado em {creds_path}")
