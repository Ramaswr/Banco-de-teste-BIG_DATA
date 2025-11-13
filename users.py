import hashlib
import hashlib as _hashlib
import os
import secrets
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
        email_verified INTEGER DEFAULT 0,
        phone_verified INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        created_at INTEGER
    )
    """
    )
    # Ensure verification_tokens table exists
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS verification_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        token_type TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """
    )
    conn.commit()
    conn.close()


def _ensure_user_columns():
    # Add columns if missing (for upgrades)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    if "email_verified" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
    if "phone_verified" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0")
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
    _ensure_user_columns()
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
    _ensure_user_columns()
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
    _ensure_user_columns()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, name, email, phone, role, created_at, email_verified, phone_verified FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def list_users() -> list:
    _init_db()
    _ensure_user_columns()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, name, email, phone, role, created_at, email_verified, phone_verified FROM users"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _hash_token(token: str) -> str:
    return _hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_verification_token(
    username: str,
    token_type: str = "email",
    ttl_seconds: int = 3600,
    token: Optional[str] = None,
) -> str:
    """Generate a token (or use provided `token`) for `username` and store its hash. Returns the raw token."""
    _init_db()
    _ensure_user_columns()
    if token is None:
        token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = int(time.time()) + int(ttl_seconds)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO verification_tokens (username, token_hash, token_type, expires_at) VALUES (?, ?, ?, ?)",
        (username, token_hash, token_type, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def verify_and_consume_token(token: str, token_type: str = "email") -> bool:
    """Verify token and mark corresponding flag on user. Returns True if successful."""
    _init_db()
    _ensure_user_columns()
    token_hash = _hash_token(token)
    now = int(time.time())
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, expires_at FROM verification_tokens WHERE token_hash = ? AND token_type = ?",
        (token_hash, token_type),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    if row["expires_at"] < now:
        # expired, delete
        cur.execute("DELETE FROM verification_tokens WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return False
    username = row["username"]
    # mark verified
    if token_type == "email":
        cur.execute(
            "UPDATE users SET email_verified = 1 WHERE username = ?", (username,)
        )
    elif token_type == "phone":
        cur.execute(
            "UPDATE users SET phone_verified = 1 WHERE username = ?", (username,)
        )
    # delete token
    cur.execute("DELETE FROM verification_tokens WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return True


def mark_email_verified(username: str):
    _init_db()
    _ensure_user_columns()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET email_verified = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def mark_phone_verified(username: str):
    _init_db()
    _ensure_user_columns()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone_verified = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def import_password_hash(username: str, password_hash: str, **meta):
    """Import a precomputed password hash (the pbkdf2:... string)."""
    return create_user(username=username, password_hash=password_hash, **meta)


if __name__ == "__main__":
    print(
        "users.py helper module. Use the script in scripts/user_create.py to create users."
    )
