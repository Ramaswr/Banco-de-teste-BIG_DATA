"""Rotate the master key for .secure_users without losing data."""

from __future__ import annotations

import base64
import getpass
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet

SECURE_DIR = Path(".secure_users")
KEY_PATH = SECURE_DIR / "master.key"
DB_PATH = SECURE_DIR / "users.db.enc"


def _read_bytes(path: Path) -> bytes:
    if not path.exists():
        return b""
    return path.read_bytes()


def _write_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.write_bytes(data)
    try:
        os.chmod(path, mode)
    except Exception:
        pass


def _derive_key(passphrase: str) -> bytes:
    digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def rotate(passphrase: str) -> None:
    SECURE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SECURE_DIR, 0o700)
    except Exception:
        pass

    old_key = _read_bytes(KEY_PATH)
    plaintext = b""
    if old_key and DB_PATH.exists():
        try:
            plaintext = Fernet(old_key).decrypt(_read_bytes(DB_PATH))
        except Exception:
            plaintext = b""

    new_key = _derive_key(passphrase)
    if plaintext:
        ciphertext = Fernet(new_key).encrypt(plaintext)
        _write_bytes(DB_PATH, ciphertext)
    _write_bytes(KEY_PATH, new_key)
    print("Nova chave aplicada com sucesso.")


def main() -> None:
    passphrase = os.getenv("NEW_MASTER_PASSPHRASE") or getpass.getpass(
        "Nova senha mestre: "
    )
    if len(passphrase) < 16:
        raise SystemExit("Passphrase muito curta; forneça pelo menos 16 caracteres.")
    rotate(passphrase)


if __name__ == "__main__":
    main()
