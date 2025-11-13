import hashlib
import os
import sqlite3
import time
from typing import Any, Dict, Optional

DB_DIR = os.path.join(".secrets")
DB_PATH = os.path.join(DB_DIR, "users.db")


def _ensure_dir():
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        os.chmod(DB_DIR, 0o700)
    except Exception:
        pass


def _get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at INTEGER
    )
    """
    )
    conn.commit()
    conn.close()


def _hash_password(password: str, iterations: int = 100000) -> str:
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:{iterations}:{salt.hex()}:{dk.hex()}"


def _verify_hash(stored: str, candidate: str) -> bool:
    try:
        parts = stored.split(":")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
        dk = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, iterations)
        return hmac_compare(dk, expected)
    except Exception:
        return False


def hmac_compare(a: bytes, b: bytes) -> bool:
    # Constant-time comparison
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def create_user(
    username: str,
    password: Optional[str] = None,
    password_hash: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    role: str = "user",
) -> Dict[str, Any]:
    """Create a user. Provide either `password` (plain) or `password_hash` (precomputed pbkdf2 string)."""
    if not (password or password_hash):
        raise ValueError("password or password_hash required")
    if password:
        password_hash = _hash_password(password)

    _init_db()
    conn = _get_conn()
    cur = conn.cursor()
    now = int(time.time())
    try:
        cur.execute(
            "INSERT INTO users (username, name, email, phone, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, name, email, phone, password_hash, role, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("username already exists")
    conn.close()
    return {
        "username": username,
        "name": name,
        "email": email,
        "phone": phone,
        "role": role,
    }


def authenticate(username: str, password: str) -> bool:
    _init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    stored = row["password_hash"]
    return _verify_hash(stored, password)


def get_user_metadata(username: str) -> Optional[Dict[str, Any]]:
    _init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, name, email, phone, role, created_at FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def list_users() -> list:
    _init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, name, email, phone, role, created_at FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def import_password_hash(username: str, password_hash: str, **meta):
    """Import a precomputed password hash (the pbkdf2:... string)."""
    return create_user(username=username, password_hash=password_hash, **meta)


if __name__ == "__main__":
    print(
        "users.py helper module. Use the script in scripts/user_create.py to create users."
    )
