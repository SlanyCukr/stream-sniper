"""HTTP contracts for every mounted user-administration route family."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from stream_sniper.api.asgi import app
from stream_sniper.api.security.auth import UserInDB, create_access_token, hash_password
from stream_sniper.application.identity.user_creation import UserCreationError
from stream_sniper.database.gateways.identity.records import (
    PublicUserRow,
    UserRow,
)

NOW = datetime.now(UTC)


def _admin() -> UserInDB:
    return UserInDB(
        id=1,
        username="administrator",
        email="admin@example.com",
        password_hash=hash_password("administrator 1"),
        role="admin",
        is_active=True,
        created_at=NOW.isoformat(),
    )


def _headers() -> dict[str, str]:
    token = create_access_token({"sub": "administrator"}, app.state.config.auth)
    return {"Authorization": f"Bearer {token}"}


def _user(user_id: int = 8) -> UserRow:
    return UserRow(user_id, "viewer", "viewer@example.com", "hash", "user", True, NOW)


def _public_user(user_id: int = 8) -> PublicUserRow:
    return PublicUserRow(user_id, "viewer", "viewer@example.com", "user", True, NOW)


def _client():
    return TestClient(app)


def test_admin_creation_logs_persistence_failure_without_exposing_it() -> None:
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch(
            "stream_sniper.api.features.auth.user_admin_endpoints.create_user",
            side_effect=UserCreationError("database detail"),
        ),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.logger.exception") as log_exception,
        _client() as client,
    ):
        response = client.post(
            "/auth/users",
            headers=_headers(),
            json={
                "username": "new_operator",
                "email": "new.operator@gmail.com",
                "password": "password7",
                "role": "user",
            },
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Could not create the account because of a server problem. Try again in a moment."}
    assert "database detail" not in response.text
    log_exception.assert_called_once_with("Admin user creation failed for username %s", "new_operator")


def test_list_and_get_user_routes_return_public_contracts():
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch(
            "stream_sniper.api.features.auth.user_admin_endpoints.select_user_page_db",
            return_value=[_public_user()],
        ),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.count_users_db", return_value=1),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.select_user_by_id_db", return_value=_user()),
        _client() as client,
    ):
        listing = client.get("/auth/users?offset=0&limit=10", headers=_headers())
        item = client.get("/auth/users/8", headers=_headers())

    assert listing.status_code == 200
    assert listing.json()["users"][0]["username"] == "viewer"
    assert listing.json()["total"] == 1
    assert item.status_code == 200
    assert item.json()["id"] == 8
    assert "password_hash" not in item.json()


def test_role_activation_and_deactivation_routes_delegate_to_gateways():
    role_user = _user()._replace(role="admin")
    active_user = _user()._replace(is_active=True)
    inactive_user = _user()._replace(is_active=False)
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.update_user_role_db", return_value=True) as role,
        patch("stream_sniper.api.features.auth.user_admin_endpoints.activate_user_db", return_value=True) as activate,
        patch(
            "stream_sniper.api.features.auth.user_admin_endpoints.deactivate_user_db", return_value=True
        ) as deactivate,
        patch(
            "stream_sniper.api.features.auth.user_admin_endpoints.select_user_by_id_db",
            side_effect=[role_user, active_user, inactive_user],
        ),
        _client() as client,
    ):
        role_response = client.put("/auth/users/8/role?new_role=admin", headers=_headers())
        activate_response = client.put("/auth/users/8/activate", headers=_headers())
        deactivate_response = client.put("/auth/users/8/deactivate", headers=_headers())

    assert [role_response.status_code, activate_response.status_code, deactivate_response.status_code] == [
        200,
        200,
        200,
    ]
    role.assert_called_once_with(8, "admin")
    activate.assert_called_once_with(8)
    deactivate.assert_called_once_with(8)
    assert role_response.json()["role"] == "admin"
    assert activate_response.json()["is_active"] is True
    assert deactivate_response.json()["is_active"] is False
    assert "password_hash" not in role_response.json()


def test_admin_cannot_demote_or_deactivate_their_own_account():
    admin_row = _user(1)._replace(username="administrator", role="admin")
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.select_user_by_id_db", return_value=admin_row),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.update_user_role_db") as update_role,
        patch("stream_sniper.api.features.auth.user_admin_endpoints.deactivate_user_db") as deactivate,
        patch("stream_sniper.api.features.auth.user_admin_endpoints.update_user_db") as update,
        _client() as client,
    ):
        role_response = client.put("/auth/users/1/role?new_role=user", headers=_headers())
        deactivate_response = client.put("/auth/users/1/deactivate", headers=_headers())
        general_response = client.put("/auth/users/1", headers=_headers(), json={"is_active": False})

    assert role_response.status_code == 400
    assert deactivate_response.status_code == 400
    assert general_response.status_code == 400
    update_role.assert_not_called()
    deactivate.assert_not_called()
    update.assert_not_called()


def test_delete_route_prevents_self_deletion_and_deletes_other_users():
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.delete_user_db", return_value=True) as delete,
        _client() as client,
    ):
        self_delete = client.delete("/auth/users/1", headers=_headers())
        other_delete = client.delete("/auth/users/8", headers=_headers())

    assert self_delete.status_code == 400
    assert other_delete.status_code == 204
    assert other_delete.content == b""
    delete.assert_called_once_with(8)


def test_admin_update_accepts_privileged_fields_and_reloads_the_user():
    updated = _user()._replace(role="admin", is_active=False)
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch(
            "stream_sniper.api.features.auth.user_admin_endpoints.select_user_by_id_db",
            side_effect=[_user(), updated],
        ),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.update_user_db", return_value=True) as update,
        _client() as client,
    ):
        response = client.put(
            "/auth/users/8",
            headers=_headers(),
            json={"role": "admin", "is_active": False},
        )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["is_active"] is False
    update.assert_called_once_with(8, email=None, role="admin", is_active=False)


def test_system_statistics_route_maps_all_four_counts():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(10,), (8,), (2,), (3,)]
    pool = MagicMock()
    pool.get_cursor.return_value.__enter__.return_value = cursor

    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.get_active_pool", return_value=pool),
        _client() as client,
    ):
        response = client.get("/auth/admin/stats", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "total_users": 10,
        "active_users": 8,
        "admin_users": 2,
        "recent_registrations": 3,
    }


def test_admin_creation_route_returns_the_created_public_user():
    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=_admin()),
        patch("stream_sniper.api.features.auth.user_admin_endpoints.create_user", return_value=_user(9)) as create,
        _client() as client,
    ):
        response = client.post(
            "/auth/users",
            headers=_headers(),
            json={
                "username": "new_viewer",
                "email": "new.viewer@gmail.com",
                "password": "password 9",
                "role": "user",
                "is_active": True,
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == 9
    create.assert_called_once_with(
        "new_viewer",
        "new.viewer@gmail.com",
        "password 9",
        role="user",
        is_active=True,
    )
