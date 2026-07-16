"""Authentication and authorization behavior through real FastAPI dependencies."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import ValidationError

from stream_sniper.api.asgi import app
from stream_sniper.api.features.auth.user_models import AdminUserUpdate, SelfUserUpdate, UserCreateAdmin
from stream_sniper.api.security.auth import (
    AuthenticationError,
    UserInDB,
    authenticate_user,
    create_access_token,
    get_current_admin_user,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from stream_sniper.application.identity.user_creation import UserCreationError


def make_user(*, role="user", active=True) -> UserInDB:
    return UserInDB(
        id=7,
        username="viewer",
        email="viewer@example.com",
        password_hash=hash_password("correct horse 7"),
        role=role,
        is_active=active,
        created_at=datetime.now(UTC).isoformat(),
    )


def bearer_for(username: str = "viewer") -> str:
    return create_access_token({"sub": username}, app.state.config.auth)


def app_request() -> Request:
    return Request({"type": "http", "app": app})


def test_password_hash_round_trip_and_rejection():
    password_hash = hash_password("correct horse 7")

    assert password_hash != "correct horse 7"
    assert verify_password("correct horse 7", password_hash) is True
    assert verify_password("wrong password", password_hash) is False


def test_jwt_round_trip_and_expiration():
    token = create_access_token({"sub": "viewer"}, app.state.config.auth, expires_delta=timedelta(minutes=1))
    expired = create_access_token({"sub": "viewer"}, app.state.config.auth, expires_delta=timedelta(seconds=-1))

    assert verify_token(token, app.state.config.auth).username == "viewer"
    with pytest.raises(AuthenticationError):
        verify_token(expired, app.state.config.auth)


def test_authenticate_user_requires_matching_password_and_active_account():
    user = make_user()
    with patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user):
        assert authenticate_user("viewer", "correct horse 7") == user
        assert authenticate_user("viewer", "wrong password") is None

    inactive = make_user(active=False)
    with patch("stream_sniper.api.security.auth.get_user_by_username", return_value=inactive):
        assert authenticate_user("viewer", "correct horse 7") is None


def test_current_user_dependency_and_admin_policy():
    user = make_user()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bearer_for())

    with patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user):
        assert get_current_user(app_request(), credentials) == user

    with pytest.raises(HTTPException) as denied:
        get_current_admin_user(user)
    assert denied.value.status_code == 403
    assert get_current_admin_user(make_user(role="admin")).role == "admin"


def test_login_and_me_use_real_token_flow():
    user = make_user()
    with patch("stream_sniper.api.features.auth.auth_endpoints.authenticate_user", return_value=user):
        with TestClient(app) as client:
            login_response = client.post(
                "/auth/login",
                json={"username": "viewer", "password": "correct horse 7"},
            )

    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    with patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user):
        with TestClient(app) as client:
            me_response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "viewer"


def test_login_database_failure_is_not_reported_as_bad_credentials():
    with patch(
        "stream_sniper.api.security.auth.select_user_by_username_db", side_effect=RuntimeError("database offline")
    ):
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={"username": "viewer", "password": "correct horse 7"},
            )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "database offline" not in response.text


def test_admin_router_boundaries_deny_standard_users():
    user = make_user()
    headers = {"Authorization": f"Bearer {bearer_for()}"}

    with patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user):
        with TestClient(app) as client:
            responses = [
                client.get("/auth/users", headers=headers),
                client.get("/admin/tracking/twitch-search?q=nin", headers=headers),
                client.get("/metrics", headers=headers),
            ]

    assert [response.status_code for response in responses] == [403, 403, 403]


def test_user_roles_are_one_closed_contract():
    assert (
        UserCreateAdmin(
            username="new_user",
            email="new.user@gmail.com",
            password="password7",
            role="admin",
        ).role
        == "admin"
    )
    with pytest.raises(ValidationError):
        UserCreateAdmin(
            username="new_user",
            email="new.user@gmail.com",
            password="password7",
            role="owner",
        )


def test_self_and_admin_update_contracts_have_distinct_privileges():
    assert SelfUserUpdate(email="next@example.com").model_dump(exclude_none=True) == {"email": "next@example.com"}
    with pytest.raises(ValidationError):
        SelfUserUpdate.model_validate({"role": "admin"})

    assert AdminUserUpdate(role="admin", is_active=False).model_dump(exclude_none=True) == {
        "role": "admin",
        "is_active": False,
    }


def test_password_change_uses_the_authenticated_password_contract():
    user = make_user()
    headers = {"Authorization": f"Bearer {bearer_for()}"}

    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user),
        patch("stream_sniper.api.features.auth.auth_endpoints.update_user_password_db", return_value=True) as update,
        TestClient(app) as client,
    ):
        response = client.put(
            "/auth/me/password",
            headers=headers,
            json={"current_password": "correct horse 7", "new_password": "replacement 8"},
        )

    assert response.status_code == 200
    assert response.json() == {"message": "Password changed successfully"}
    update.assert_called_once()


def test_self_update_rejects_admin_only_fields_before_the_handler_runs():
    user = make_user()
    headers = {"Authorization": f"Bearer {bearer_for()}"}

    with (
        patch("stream_sniper.api.security.auth.get_user_by_username", return_value=user),
        patch("stream_sniper.api.features.auth.auth_endpoints.update_user_db") as update,
        TestClient(app) as client,
    ):
        response = client.put("/auth/me", headers=headers, json={"role": "admin"})

    assert response.status_code == 422
    update.assert_not_called()


def test_registration_logs_persistence_failure_without_exposing_it() -> None:
    with (
        patch(
            "stream_sniper.api.features.auth.auth_endpoints.create_user",
            side_effect=UserCreationError("database detail"),
        ),
        patch("stream_sniper.api.features.auth.auth_endpoints.logger.exception") as log_exception,
        TestClient(app) as client,
    ):
        response = client.post(
            "/auth/register",
            json={"username": "new_viewer", "email": "new.viewer@gmail.com", "password": "password7"},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to create user"}
    assert "database detail" not in response.text
    log_exception.assert_called_once_with("Self-service registration failed for username %s", "new_viewer")


def test_administrative_persistence_errors_use_shared_openapi_schema() -> None:
    schema = app.openapi()
    expected = {"$ref": "#/components/schemas/ErrorResponse"}

    assert (
        schema["paths"]["/auth/register"]["post"]["responses"]["500"]["content"]["application/json"]["schema"]
        == expected
    )
    assert (
        schema["paths"]["/auth/users"]["post"]["responses"]["500"]["content"]["application/json"]["schema"] == expected
    )
    assert (
        schema["paths"]["/admin/tracking/jobs/{job_id}/cancel"]["post"]["responses"]["500"]["content"][
            "application/json"
        ]["schema"]
        == expected
    )
