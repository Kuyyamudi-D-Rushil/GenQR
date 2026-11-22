from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
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


def test_history_pagination(auth_client, app):
    """Verify server-side pagination across multiple pages with filter preservation."""
    client, user_id = auth_client

    with app.app_context():
        # Insert 15 items
        for i in range(1, 16):
            db.session.add(QRCode(
                user_id=user_id,
                title=f"Paginated QR {i:02d}",
                qr_type="url",
                content=f"https://example{i}.org"
            ))
        db.session.commit()

    # Request page 1 with 5 items per page
    resp_p1 = client.get("/history?page=1&per_page=5")
    assert resp_p1.status_code == 200
    assert b"Paginated QR 15" in resp_p1.data  # Newest first
    assert b"Paginated QR 11" in resp_p1.data
    assert b"Paginated QR 10" not in resp_p1.data
    assert b"page=2" in resp_p1.data
    assert b"Showing 1 to 5 of 15 records" in resp_p1.data

    # Request page 2 with 5 items per page
    resp_p2 = client.get("/history?page=2&per_page=5")
    assert resp_p2.status_code == 200
    assert b"Paginated QR 10" in resp_p2.data
    assert b"Paginated QR 06" in resp_p2.data
    assert b"Paginated QR 15" not in resp_p2.data

    # Request page 3 with 5 items per page
    resp_p3 = client.get("/history?page=3&per_page=5")
    assert resp_p3.status_code == 200
    assert b"Paginated QR 05" in resp_p3.data
    assert b"Paginated QR 01" in resp_p3.data


def test_history_xss_safe_rendering(auth_client, app):
    """Verify malicious titles and content cannot inject script or break HTML markup."""
    client, user_id = auth_client

    xss_title = "<script>alert('xss_title')</script>"
    xss_content = "\"><img src=x onerror=alert('xss_content')>"

    with app.app_context():
        db.session.add(QRCode(
            user_id=user_id,
            title=xss_title,
            qr_type="text",
            content=xss_content
        ))
        db.session.commit()

    response = client.get("/history")
    assert response.status_code == 200

    # Ensure unescaped raw script tag is NEVER rendered in the HTML body
    assert b"<script>alert('xss_title')</script>" not in response.data

    # Ensure no inline onclick handler with interpolated strings
    assert b"onclick=\"openPreviewModal(" not in response.data

    # Ensure HTML escaping is applied to title and content attributes
    assert b"&lt;script&gt;alert(&#39;xss_title&#39;)&lt;/script&gt;" in response.data or b"&lt;script&gt;" in response.data


def test_delete_qr_record(auth_client, app):
    """Verify QR code deletion by authorized owner returns remaining count."""
    client, user_id = auth_client

    with app.app_context():
        record = QRCode(user_id=user_id, title="Delete Me", qr_type="text", content="Temporary")
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    del_resp = client.delete(f"/api/qr/{record_id}")
    assert del_resp.status_code == 200
    assert del_resp.json["success"] is True
    assert "remaining_count" in del_resp.json

    # Ensure record is deleted from database
    with app.app_context():
        assert db.session.get(QRCode, record_id) is None


def test_delete_qr_db_error_rollback(auth_client, app):
    """Verify database deletion failure rolls back and returns HTTP 500 JSON."""
    client, user_id = auth_client

    with app.app_context():
        record = QRCode(user_id=user_id, title="Cannot Delete", qr_type="text", content="Temporary")
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    with patch("extensions.db.session.commit", side_effect=SQLAlchemyError("Delete lock error")):
        del_resp = client.delete(f"/api/qr/{record_id}")
        assert del_resp.status_code == 500
        assert "database error" in del_resp.json["error"].lower()

    # Record must still be present in database after rollback
    with app.app_context():
        assert db.session.get(QRCode, record_id) is not None


def test_cross_user_delete_prevention(app):
    """Verify User B cannot delete User A's QR code."""
    with app.app_context():
        user_a = User(username="owner", email="owner@example.com")
        user_a.set_password("SecurePassword123!")
        user_b = User(username="intruder", email="intruder@example.com")
        user_b.set_password("SecurePassword123!")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        record = QRCode(user_id=user_a.id, title="Protected Code", qr_type="url", content="https://myprotect.org")
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    # User B logs in and attempts to delete User A's record
    client_b = app.test_client()
    client_b.post("/logout", follow_redirects=True)
    client_b.post("/login", data={"email": "intruder@example.com", "password": "SecurePassword123!"}, follow_redirects=True)
    unauth_resp = client_b.delete(f"/api/qr/{record_id}")
    assert unauth_resp.status_code == 404

    # Ensure record is still intact
    with app.app_context():
        assert db.session.get(QRCode, record_id) is not None
