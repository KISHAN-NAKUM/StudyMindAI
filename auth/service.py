"""
Authentication service for StudyMind.
Provides secure password hashing with salt, validation, registration, and login verification.
"""

import hashlib
import hmac
import os
import re
from typing import Tuple, Optional
from database.db import DatabaseManager
from database.models import Student


class AuthService:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashes a password with PBKDF2-HMAC-SHA256 and returns (hash_hex, salt_hex)."""
        if not salt:
            salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100000
        ).hex()
        return pwd_hash, salt

    @staticmethod
    def verify_password(stored_hash: str, salt: str, password_attempt: str) -> bool:
        """Verifies candidate password against stored hash using constant-time comparison."""
        attempt_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password_attempt.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100000
        ).hex()
        return hmac.compare_digest(stored_hash, attempt_hash)

    def register(self, username: str, display_name: str, password: str) -> Tuple[bool, str, Optional[Student]]:
        """
        Validates input and registers a new student.
        Returns: (success: bool, message: str, student: Optional[Student])
        """
        username = (username or "").strip().lower()
        display_name = (display_name or "").strip()
        password = password or ""

        # Validation
        if not username or len(username) < 3 or len(username) > 30:
            return False, "Username must be between 3 and 30 characters.", None

        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            return False, "Username can only contain letters, numbers, underscores, dots, or hyphens.", None

        if not display_name or len(display_name) < 2:
            return False, "Display name must be at least 2 characters.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        # Check existing user
        existing = self.db.get_student_by_username(username)
        if existing:
            return False, f"Username '{username}' is already registered. Please log in or pick another username.", None

        # Create user
        pwd_hash, salt = self.hash_password(password)
        student_id = self.db.create_student(username, display_name, pwd_hash, salt)

        if not student_id:
            return False, "Failed to create student account due to a database error.", None

        student = self.db.get_student_by_id(student_id)
        return True, "Registration successful!", student

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[Student]]:
        """
        Authenticates a student by username and password.
        Returns: (success: bool, message: str, student: Optional[Student])
        """
        username = (username or "").strip().lower()
        password = password or ""

        if not username or not password:
            return False, "Please enter both username and password.", None

        student = self.db.get_student_by_username(username)
        if not student:
            return False, "Invalid username or password.", None

        if not self.verify_password(student.password_hash, student.salt, password):
            return False, "Invalid username or password.", None

        return True, "Login successful!", student
