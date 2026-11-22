from models import QRCode, User
from extensions import db


def test_dashboard_stats(auth_client, app):
    """Verify aggregated stats on dashboard reflect stored records."""
    client, user_id = auth_client

    with app.app_context():
        # Add 2 URLs, 1 Email, 1 Phone
        db.session.add(QRCode(user_id=user_id, title="URL 1", qr_type="url", content="https://u1.com"))
        db.session.add(QRCode(user_id=user_id, title="URL 2", qr_type="url", content="https://u2.com"))
        db.session.add(QRCode(user_id=user_id, title="Email 1", qr_type="email", content="admin@test.com"))
        db.session.add(QRCode(user_id=user_id, title="Phone 1", qr_type="phone", content="+1234567890"))
        db.session.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"TOTAL SAVED" in response.data
    # Check that titles appear in recent list
    assert b"URL 1" in response.data
    assert b"Email 1" in response.data


def test_history_filtering(auth_client, app):
    """Verify history filtering by type and search terms."""
    client, user_id = auth_client

    with app.app_context():
        db.session.add(QRCode(user_id=user_id, title="UniqueSearchTerm", qr_type="text", content="Secret memo"))
        db.session.add(QRCode(user_id=user_id, title="Another Link", qr_type="url", content="https://site.org"))
        db.session.commit()

    # Search filter
    search_resp = client.get("/history?q=UniqueSearchTerm")
    assert search_resp.status_code == 200
    assert b"UniqueSearchTerm" in search_resp.data
    assert b"Another Link" not in search_resp.data

    # Type filter
    type_resp = client.get("/history?type=url")
    assert type_resp.status_code == 200
    assert b"Another Link" in type_resp.data
    assert b"UniqueSearchTerm" not in type_resp.data


def test_delete_qr_record(auth_client, app):
    """Verify QR code deletion by authorized owner."""
    client, user_id = auth_client

    with app.app_context():
        record = QRCode(user_id=user_id, title="Delete Me", qr_type="text", content="Temporary")
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    del_resp = client.delete(f"/api/qr/{record_id}")
    assert del_resp.status_code == 200
    assert del_resp.json["success"] is True

    # Ensure record is deleted from database
    with app.app_context():
        assert db.session.get(QRCode, record_id) is None


def test_cross_user_delete_prevention(app):
    """Verify User B cannot delete User A's QR code."""
    with app.app_context():
        user_a = User(username="owner", email="owner@example.com")
        user_a.set_password("pass123")
        user_b = User(username="intruder", email="intruder@example.com")
        user_b.set_password("pass123")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        record = QRCode(user_id=user_a.id, title="Protected Code", qr_type="url", content="https://myprotect.org")
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    # User B logs in and attempts to delete User A's record
    client_b = app.test_client()
    client_b.get("/logout", follow_redirects=True)
    client_b.post("/login", data={"email": "intruder@example.com", "password": "pass123"}, follow_redirects=True)
    unauth_resp = client_b.delete(f"/api/qr/{record_id}")
    assert unauth_resp.status_code == 404

    # Ensure record is still intact
    with app.app_context():
        assert db.session.get(QRCode, record_id) is not None
