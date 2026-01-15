import os
from pathlib import Path
import time
import io
import json
import pytest
import importlib
import datetime

# importar módulos do projeto
security = importlib.import_module('security')
users = importlib.import_module('users')
from app import _sanitize_cell_for_csv, sanitize_dataframe_for_export


def test_password_strength(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_dir = str(tmp_path / '.secrets')
    db_path = str(tmp_path / '.secrets' / 'users.db')
    monkeypatch.setattr(users, 'DB_DIR', db_dir)
    monkeypatch.setattr(users, 'DB_PATH', db_path)
    # senha fraca deve falhar
    with pytest.raises(ValueError):
        users.create_user('weakuser', 'short')
    # senha forte deve passar
    strong = 'S3nh@ForteExemplo!'
    res = users.create_user('stronguser', strong)
    assert res['username'] == 'stronguser'


def test_lockout_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # usar arquivo de locks em tmp
    locks = str(tmp_path / '.secrets' / 'locks.json')
    monkeypatch.setattr(security, 'LOCKS_FILE', locks)
    # garantir reset
    security._ensure_locks()
    ident = 'attemptuser'
    # reset
    security.reset_attempts(ident)
    # registrar 5 falhas
    for _ in range(5):
        security.register_failed_attempt(ident, max_attempts=5, window=60, lock_time=2)
    assert security.is_locked(ident) is True
    # aguardar expiração
    time.sleep(2.1)
    assert security.is_locked(ident) is False


def test_csv_sanitization():
    # cells starting with =, +, -, @ should be prefixed with '
    import pandas as pd
    df = pd.DataFrame({'a': ['=SUM(A1:A2)', '+1', '-2', '@shell', 'normal']})
    out = sanitize_dataframe_for_export(df)
    assert str(out.loc[0, 'a']).startswith("'")
    assert str(out.loc[1, 'a']).startswith("'")
    assert str(out.loc[2, 'a']).startswith("'")
    assert str(out.loc[3, 'a']).startswith("'")
    assert str(out.loc[4, 'a']) == 'normal'
