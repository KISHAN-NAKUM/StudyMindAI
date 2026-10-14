"""
Tests for StudyMind authentication service.
Verifies registration validation, password hashing security, and login authentication.
"""

import pytest
import tempfile
import os
from database.db import DatabaseManager
from auth.service import AuthService


@pytest.fixture
def auth_fixture():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = DatabaseManager(db_path)
    service = AuthService(db)
    yield service, db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_registration_success(auth_fixture):
    service, db = auth_fixture
    ok, msg, student = service.register("student1", "Student One", "secret_pass123")
    assert ok is True
    assert student is not None
    assert student.username == "student1"
    assert student.display_name == "Student One"
    # Verify password is not stored plaintext
    assert student.password_hash != "secret_pass123"
    assert len(student.password_hash) == 64  # sha256 hex length
    assert len(student.salt) == 32          # 16-byte hex length


def test_registration_duplicate_username_rejected(auth_fixture):
    service, _ = auth_fixture
    service.register("student1", "Student One", "password123")
    ok, msg, student = service.register("student1", "Different Name", "another_pass")
    assert ok is False
    assert "already registered" in msg.lower()
    assert student is None


def test_registration_validation_rules(auth_fixture):
    service, _ = auth_fixture
    # Short username
    ok, msg, _ = service.register("ab", "Alice", "password123")
    assert ok is False
    assert "between 3 and 30" in msg

    # Short password
    ok, msg, _ = service.register("alice", "Alice", "123")
    assert ok is False
    assert "at least 6 characters" in msg


def test_login_success_and_failure(auth_fixture):
    service, _ = auth_fixture
    service.register("bob_ross", "Bob Ross", "happy_trees123")

    # Correct login
    ok, msg, student = service.login("bob_ross", "happy_trees123")
    assert ok is True
    assert student.display_name == "Bob Ross"

    # Case insensitivity for username
    ok_upper, _, _ = service.login("BOB_ROSS", "happy_trees123")
    assert ok_upper is True

    # Incorrect password
    ok_bad, msg_bad, _ = service.login("bob_ross", "wrong_password")
    assert ok_bad is False
    assert "invalid username or password" in msg_bad.lower()

    # Nonexistent user
    ok_none, _, _ = service.login("nonexistent_user", "password123")
    assert ok_none is False
