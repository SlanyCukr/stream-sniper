"""Contract tests for the shared user-creation workflow."""

from datetime import UTC, datetime

import bcrypt
import pytest

from stream_sniper.application.identity import user_creation
from stream_sniper.database.gateways.identity.records import UserRow


def _row(*, active: bool = True) -> UserRow:
    return UserRow(7, "alice", "alice@example.com", "stored-hash", "user", active, datetime.now(UTC))


def test_create_user_hashes_inserts_and_reloads(monkeypatch):
    inserted: dict[str, object] = {}
    monkeypatch.setattr(user_creation, "user_exists_db", lambda **_kwargs: False)

    def insert_user_db(**kwargs):
        inserted.update(kwargs)
        return 7

    monkeypatch.setattr(user_creation, "insert_user_db", insert_user_db)
    monkeypatch.setattr(user_creation, "select_user_by_id_db", lambda user_id: _row() if user_id == 7 else None)

    result = user_creation.create_user("alice", "alice@example.com", "password7")

    assert result.id == 7
    assert inserted["role"] == "user"
    assert bcrypt.checkpw(b"password7", str(inserted["password_hash"]).encode("utf-8"))


def test_create_user_applies_inactive_state_before_reload(monkeypatch):
    deactivated: list[int] = []
    monkeypatch.setattr(user_creation, "user_exists_db", lambda **_kwargs: False)
    monkeypatch.setattr(user_creation, "insert_user_db", lambda **_kwargs: 7)
    monkeypatch.setattr(user_creation, "deactivate_user_db", lambda user_id: deactivated.append(user_id) or True)
    monkeypatch.setattr(user_creation, "select_user_by_id_db", lambda _user_id: _row(active=False))

    result = user_creation.create_user("alice", "alice@example.com", "password7", is_active=False)

    assert deactivated == [7]
    assert result.is_active is False


def test_create_user_distinguishes_conflict_from_persistence_failure(monkeypatch):
    monkeypatch.setattr(user_creation, "user_exists_db", lambda **_kwargs: True)
    with pytest.raises(user_creation.UserAlreadyExistsError):
        user_creation.create_user("alice", "alice@example.com", "password7")

    monkeypatch.setattr(user_creation, "user_exists_db", lambda **_kwargs: False)
    monkeypatch.setattr(user_creation, "insert_user_db", lambda **_kwargs: None)
    with pytest.raises(user_creation.UserCreationError, match="no identifier"):
        user_creation.create_user("alice", "alice@example.com", "password7")
