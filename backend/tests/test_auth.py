from fastapi.testclient import TestClient

from tests.conftest import STUDENT_EMAIL, STUDENT_PASSWORD, register


def test_register_returns_tokens_and_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Asha", "email": "asha@example.com", "password": STUDENT_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["role"] == "student"
    assert "password" not in response.text.lower()


def test_password_is_hashed(client: TestClient, db) -> None:
    register(client)
    from app.models import User

    user = db.query(User).filter(User.email == STUDENT_EMAIL).one()
    assert user.password_hash != STUDENT_PASSWORD
    assert user.password_hash.startswith("$2")


def test_duplicate_email_rejected(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Student", "email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )
    assert response.status_code == 409


def test_weak_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"name": "Student", "email": "weak@example.com", "password": "123"}
    )
    assert response.status_code == 422


def test_login_wrong_password(client: TestClient) -> None:
    register(client)
    response = client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": "WrongPass1!"})
    assert response.status_code == 401


def test_login_is_case_insensitive_on_email(client: TestClient) -> None:
    register(client)
    response = client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL.upper(), "password": STUDENT_PASSWORD})
    assert response.status_code == 200


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_me_returns_profile(client: TestClient) -> None:
    headers = register(client)
    body = client.get("/api/v1/auth/me", headers=headers).json()
    assert body["email"] == STUDENT_EMAIL
    assert body["level"] >= 1


def test_refresh_issues_new_access_token(client: TestClient) -> None:
    created = client.post(
        "/api/v1/auth/register",
        json={"name": "Student", "email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    ).json()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": created["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_rejected_as_refresh_token(client: TestClient) -> None:
    created = client.post(
        "/api/v1/auth/register",
        json={"name": "Student", "email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    ).json()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": created["access_token"]})
    assert response.status_code == 401


def test_forgot_password_does_not_leak_account_existence(client: TestClient) -> None:
    register(client)
    known = client.post("/api/v1/auth/forgot-password", json={"email": STUDENT_EMAIL}).json()
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}).json()
    assert known["message"] == unknown["message"]
    assert known["reset_token"] and unknown["reset_token"] is None


def test_reset_password_changes_credentials(client: TestClient) -> None:
    register(client)
    token = client.post("/api/v1/auth/forgot-password", json={"email": STUDENT_EMAIL}).json()["reset_token"]
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"reset_token": token, "new_password": "BrandNew1!"}
        ).status_code
        == 200
    )
    assert (
        client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD}).status_code
        == 401
    )
    assert client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": "BrandNew1!"}).status_code == 200


def test_logout_requires_auth(client: TestClient) -> None:
    headers = register(client)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
