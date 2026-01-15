import os
import sqlite3
import hashlib
import binascii
import secrets

BASE_DIR = os.path.dirname(__file__)
DB_DIR = os.path.join(BASE_DIR, ".secrets")
DB_PATH = os.path.join(DB_DIR, "users.db")


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, salt TEXT, pw_hash TEXT)"
    )
    conn.commit()
    conn.close()
    try:
        os.chmod(DB_PATH, 0o600)
    except Exception:
        pass


def _hash_password(password, salt_hex=None):
    if salt_hex is None:
        salt = secrets.token_bytes(16)
    else:
        salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()


def create_user(username, password):
    init_db()
    salt_hex, pw_hash = _hash_password(password)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)",
            (username, salt_hex, pw_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("username already exists")
    conn.close()
    return True


def authenticate(username, password):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT salt, pw_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    salt_hex, stored_hash = row
    _, check_hash = _hash_password(password, salt_hex)
    return check_hash == stored_hash