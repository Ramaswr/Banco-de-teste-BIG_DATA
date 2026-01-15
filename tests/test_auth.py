import os
import tempfile
import importlib.util
import shutil

from pytest import MonkeyPatch
import pytest
import auth

def test_create_and_authenticate(tmp_path, monkeypatch):
    db_dir = str(tmp_path / ".secrets")
    db_path = str(tmp_path / ".secrets" / "users.db")
    monkeypatch.setattr(auth, "DB_DIR", db_dir)
    monkeypatch.setattr(auth, "DB_PATH", db_path)
    auth.init_db()

    assert auth.create_user("alice", "s3cr3t")
    assert auth.authenticate("alice", "s3cr3t") is True
    assert auth.authenticate("alice", "wrong") is False
    assert auth.authenticate("noone", "nopw") is False
    assert (tmp_path / ".secrets" / "users.db").exists()

def test_duplicate_user(tmp_path, monkeypatch):
    db_dir = str(tmp_path / ".secrets")
    db_path = str(tmp_path / ".secrets" / "users.db")
    monkeypatch.setattr(auth, "DB_DIR", db_dir)
    monkeypatch.setattr(auth, "DB_PATH", db_path)
    auth.init_db()

    assert auth.create_user("bob", "pw")
    with pytest.raises(ValueError):
        auth.create_user("bob", "pw2")