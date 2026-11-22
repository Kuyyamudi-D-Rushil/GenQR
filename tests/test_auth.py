from models import User
from extensions import db


def test_register_success(client, app):
    """Verify new user registration and database persistence."""
    response = client.post("/register", data={
        "username": "johndoe",
        "email": "john@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="john@example.com").first()
        assert user is not None
        assert user.username == "johndoe"
        assert user.check_password("password123") is True


def test_register_duplicate_email(client, app):
    """Verify registration fails when email is already registered."""
    with app.app_context():
        user = User(username="existing", email="existing@example.com")
        user.set_password("pass1234")
        db.session.add(user)
        db.session.commit()

    response = client.post("/register", data={
        "username": "newname",
        "email": "existing@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)

    assert b"already exists" in response.data


def test_register_password_mismatch(client):
    """Verify registration fails when passwords do not match."""
    response = client.post("/register", data={
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
        "confirm_password": "differentpassword"
    }, follow_redirects=True)

    assert b"Passwords do not match" in response.data


def test_register_short_password(client):
    """Verify password length requirement (>= 6 chars)."""
    response = client.post("/register", data={
        "username": "bob",
        "email": "bob@example.com",
        "password": "123",
        "confirm_password": "123"
    }, follow_redirects=True)

    assert b"at least 6 characters" in response.data


def test_login_success_and_logout(client, app):
    """Verify successful login and session termination on logout."""
    with app.app_context():
        user = User(username="charlie", email="charlie@example.com")
        user.set_password("correctpass123")
        db.session.add(user)
        db.session.commit()

    # Valid Login
    login_resp = client.post("/login", data={
        "email": "charlie@example.com",
        "password": "correctpass123"
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Welcome back" in login_resp.data

    # Access protected dashboard
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200

    # Logout
    logout_resp = client.get("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"logged out" in logout_resp.data

    # Protected page now redirects to login
    dash_after_logout = client.get("/dashboard")
    assert dash_after_logout.status_code == 302


def test_login_invalid_credentials(client, app):
    """Verify invalid password rejection."""
    with app.app_context():
        user = User(username="dave", email="dave@example.com")
        user.set_password("actualpass123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/login", data={
        "email": "dave@example.com",
        "password": "wrongpassword"
    }, follow_redirects=True)

    assert b"Invalid email or password" in response.data
