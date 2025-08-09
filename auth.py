"""
Authentication and authorization helpers for the distributed inventory system.

User credentials and roles are stored in the `users` collection on server3.
Each user document contains a username, a hashed password, a role
(CongTy, ChiNhanh, or User) and an optional branch code. Branch codes are
only set for users belonging to a particular branch (ChiNhanh or User roles).

Passwords are hashed using SHA‑256 to avoid storing plain text. In a more
secure implementation you could use the `bcrypt` library or another strong
password hashing algorithm. This module does not enforce password
complexity – that is left to the UI layer.

The PyMongo tutorial explains that to get a collection you simply access it
via the database: `collection = db.test_collection`【282328984375463†L202-L214】. We
follow the same pattern here.
"""

import hashlib
from typing import Optional, Dict, Any

from database import DatabaseManager


def _hash_password(password: str) -> str:
    """Return a SHA‑256 hash of the given password.

    Args:
        password: Plain text password.

    Returns:
        Hexadecimal digest of the password.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(
    dbm: DatabaseManager,
    username: str,
    password: str,
    role: str,
    branch: Optional[str] = None,
) -> None:
    """Create a new user with the specified role and branch.

    Args:
        dbm: Instance of `DatabaseManager` for DB access.
        username: Desired login name. Must be unique.
        password: Plain text password that will be hashed.
        role: One of "CongTy", "ChiNhanh" or "User".
        branch: Branch code (e.g. "CN1" or "CN2"). Required for roles
            "ChiNhanh" and "User". Ignored for "CongTy".

    Raises:
        ValueError: If the username already exists or required arguments are
            missing.
    """
    role = role.strip().capitalize() if role else None
    if role not in {"Congty", "Chinhanh", "User"}:
        raise ValueError("Role must be one of CongTy, ChiNhanh or User")
    if role in {"Chinhanh", "User"} and not branch:
        raise ValueError("Branch must be provided for ChiNhanh and User roles")
    # Normalize username
    username = username.lower()

    users_col = dbm.get_collection(None, "users")
    if users_col.find_one({"username": username}):
        raise ValueError(f"User '{username}' already exists")

    user_doc: Dict[str, Any] = {
        "username": username,
        "password_hash": _hash_password(password),
        "role": role,
    }
    if role in {"Chinhanh", "User"}:
        user_doc["branch"] = branch.upper()

    users_col.insert_one(user_doc)


def authenticate(dbm: DatabaseManager, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validate credentials and return user document on success.

    Args:
        dbm: Database manager for DB access.
        username: Login name (case insensitive).
        password: Plain text password to verify.

    Returns:
        The user document without the password hash if authentication passes,
        otherwise `None`.
    """
    if not username or not password:
        return None
    users_col = dbm.get_collection(None, "users")
    user = users_col.find_one({"username": username.lower()})
    if user and user.get("password_hash") == _hash_password(password):
        # Remove sensitive fields before returning
        user.pop("password_hash", None)
        return user
    return None


def get_user(dbm: DatabaseManager, username: str) -> Optional[Dict[str, Any]]:
    """Fetch a user document by username without verifying the password.

    Args:
        dbm: Database manager for DB access.
        username: Username to search for.

    Returns:
        User document if found, otherwise `None`.
    """
    users_col = dbm.get_collection(None, "users")
    user = users_col.find_one({"username": username.lower()})
    if user:
        user.pop("password_hash", None)
    return user
