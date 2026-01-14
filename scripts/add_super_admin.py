import os
import sys
import json
import base64
import secrets
import hashlib
from pathlib import Path

def hash_password(password: str, iterations: int = 100_000):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "hash": base64.b64encode(dk).decode("utf-8"),
        "iterations": iterations,
    }

def ensure_secrets_dir(path: Path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)

def load_credentials(path: Path):
    if not path.exists():
        return {"users": {}}
    return json.loads(path.read_text())

def save_credentials(path: Path, data):
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)

def main():
    if len(sys.argv) < 2:
        print("Usage: python add_super_admin.py <username>")
        sys.exit(1)
    username = sys.argv[1]
    password = os.getenv("PASSWORD")
    if not password:
        print("Defina a senha via env var PASSWORD ou use stdin seguro (ex.: export PASSWORD='...' )")
        sys.exit(1)

    secrets_dir = Path(".secrets")
    ensure_secrets_dir(secrets_dir)
    cred_file = secrets_dir / "credentials.json"

    creds = load_credentials(cred_file)
    creds.setdefault("users", {})

    creds["users"][username] = hash_password(password)
    creds["users"][username]["roles"] = ["super_admin"]

    save_credentials(cred_file, creds)
    print(f"Usuário '{username}' adicionado como super_admin em {cred_file}")

if __name__ == "__main__":
    main()