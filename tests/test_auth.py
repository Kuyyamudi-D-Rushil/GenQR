from unittest.mock import patch
from sqlalchemy.exc import IntegrityError
from models import User
from extensions import db


def test_register_success(client, app):
    """Verify new user registration and database persistence with >= 12 char password."""
    response = client.post("/register", data={
        "username": "johndoe",
        "email": "john@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="john@example.com").first()
        assert user is not None
        assert user.username == "johndoe"
        assert user.check_password("SecurePassword123!") is True


def test_register_duplicate_email(client, app):
    """Verify registration fails when email is already registered."""
    with app.app_context():
        user = User(username="existing", email="existing@example.com")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    response = client.post("/register", data={
        "username": "newname",
        "email": "existing@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }, follow_redirects=True)

    assert b"already exists" in response.data


def test_register_password_mismatch(client):
    """Verify registration fails when passwords do not match."""
    response = client.post("/register", data={
        "username": "alice",
        "email": "alice@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "DifferentPassword123!"
    }, follow_redirects=True)

    assert b"Passwords do not match" in response.data


def test_register_short_password(client):
    """Verify password length requirement of at least 12 characters."""
    response = client.post("/register", data={
        "username": "bob",
        "email": "bob@example.com",
        "password": "shortpass11",  # 11 chars
        "confirm_password": "shortpass11"
    }, follow_redirects=True)

    assert b"at least 12 characters" in response.data


def test_register_integrity_error_rollback(client, app):
    """Verify that an unexpected database collision during registration rolls back cleanly."""
    with patch("extensions.db.session.commit", side_effect=IntegrityError("duplicate", {}, Exception())):
        response = client.post("/register", data={
            "username": "collision_user",
            "email": "collision@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!"
        }, follow_redirects=True)

        assert response.status_code == 400
        assert b"already exists" in response.data


def test_login_success_and_logout_post_only(client, app):
    """Verify login, dashboard access, and CSRF/POST-only logout behavior."""
    with app.app_context():
        user = User(username="charlie", email="charlie@example.com")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    # Valid Login
    login_resp = client.post("/login", data={
        "email": "charlie@example.com",
        "password": "SecurePassword123!"
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Welcome back" in login_resp.data

    # Access protected dashboard
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200

    # GET /logout is strictly forbidden (Method Not Allowed)
    get_logout_resp = client.get("/logout")
    assert get_logout_resp.status_code == 405

    # POST /logout succeeds
    logout_resp = client.post("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"logged out" in logout_resp.data

    # Protected page now redirects to login
    dash_after_logout = client.get("/dashboard")
    assert dash_after_logout.status_code == 302


def test_login_invalid_credentials(client, app):
    """Verify invalid password rejection."""
    with app.app_context():
        user = User(username="dave", email="dave@example.com")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    response = client.post("/login", data={
        "email": "dave@example.com",
        "password": "WrongPassword123!"
    }, follow_redirects=True)

    assert b"Invalid email or password" in response.data


def test_profile_page_access_and_password_update(auth_client, app):
    """Verify user profile review and secure credential modification."""
    client, user_id = auth_client

    # Authenticated user can access profile
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"Account & Security Settings" in resp.data
    assert b"testuser" in resp.data

    # Fail: Incorrect current password
    fail_resp1 = client.post("/profile", data={
        "current_password": "WrongPassword123!",
        "new_password": "BrandNewSecurePassword123!",
        "confirm_password": "BrandNewSecurePassword123!"
    }, follow_redirects=True)
    assert fail_resp1.status_code == 400
    assert b"Current password is incorrect" in fail_resp1.data

    # Fail: Short new password (< 12 characters)
    fail_resp2 = client.post("/profile", data={
        "current_password": "securepassword123",
        "new_password": "short",
        "confirm_password": "short"
    }, follow_redirects=True)
    assert fail_resp2.status_code == 400
    assert b"at least 12 characters" in fail_resp2.data

    # Fail: Password mismatch
    fail_resp3 = client.post("/profile", data={
        "current_password": "securepassword123",
        "new_password": "BrandNewSecurePassword123!",
        "confirm_password": "DifferentPassword123!"
    }, follow_redirects=True)
    assert fail_resp3.status_code == 400
    assert b"Passwords do not match" in fail_resp3.data

    # Success: Valid password update
    success_resp = client.post("/profile", data={
        "current_password": "securepassword123",
        "new_password": "BrandNewSecurePassword123!",
        "confirm_password": "BrandNewSecurePassword123!"
    }, follow_redirects=True)
    assert success_resp.status_code == 200
    assert b"successfully updated" in success_resp.data

    # Verify new password can be used to log in
    client.post("/logout", follow_redirects=True)
    new_login = client.post("/login", data={
        "email": "test@example.com",
        "password": "BrandNewSecurePassword123!"
    }, follow_redirects=True)
    assert new_login.status_code == 200
    assert b"Welcome back" in new_login.data

