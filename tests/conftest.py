import pytest
from app import create_app
from config import TestingConfig
from extensions import db
from models import User, QRCode


@pytest.fixture
def app():
    """Create and configure a clean application instance for testing."""
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Client authenticated with a sample user."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("securepassword123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Log in
    client.post("/login", data={
        "email": "test@example.com",
        "password": "securepassword123"
    }, follow_redirects=True)

    return client, user_id


@pytest.fixture
def second_user_client(app):
    """Client authenticated with a second independent user for isolation tests."""
    test_client = app.test_client()
    with app.app_context():
        user2 = User(username="otheruser", email="other@example.com")
        user2.set_password("otherpassword123")
        db.session.add(user2)
        db.session.commit()
        user2_id = user2.id

    test_client.post("/login", data={
        "email": "other@example.com",
        "password": "otherpassword123"
    }, follow_redirects=True)

    return test_client, user2_id
