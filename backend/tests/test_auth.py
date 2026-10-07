import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Anil Deshmukh",
            "email": "anil@example.com",
            "password": "strongpassword123",
            "preferred_language": "mr",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "anil@example.com"
    assert data["name"] == "Anil Deshmukh"
    assert data["preferred_language"] == "mr"
    assert data["role"] == "FARMER"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data
    assert "id" in data


def test_register_duplicate_email(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate Ramesh",
            "email": test_user.email,
            "password": "anotherpassword",
            "preferred_language": "en",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_login_success_json(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ramesh@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_form(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "ramesh@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_incorrect_password(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ramesh@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "somepassword",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client: TestClient, auth_headers: dict, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name
