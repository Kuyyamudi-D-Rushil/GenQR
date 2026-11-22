from models import QRCode, User
from extensions import db


def test_generate_qr_url(auth_client, app):
    """Verify generating a URL QR code returns PNG and saves to database."""
    client, user_id = auth_client

    response = client.post("/api/generate", json={
        "title": "Google Link",
        "qr_type": "url",
        "content": "https://google.com",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert "X-QR-ID" in response.headers

    qr_id = int(response.headers["X-QR-ID"])
    with app.app_context():
        record = db.session.get(QRCode, qr_id)
        assert record is not None
        assert record.user_id == user_id
        assert record.qr_type == "url"
        assert record.content == "https://google.com"


def test_generate_qr_validation_errors(auth_client):
    """Verify input validation rules for QR generation."""
    client, _ = auth_client

    # Empty content
    r1 = client.post("/api/generate", json={
        "title": "Empty",
        "qr_type": "url",
        "content": "",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r1.status_code == 400

    # Same foreground and background
    r2 = client.post("/api/generate", json={
        "title": "Same colors",
        "qr_type": "text",
        "content": "Sample text",
        "foreground": "#000000",
        "background": "#000000"
    })
    assert r2.status_code == 400
    assert b"different" in r2.data

    # Invalid hex color
    r3 = client.post("/api/generate", json={
        "title": "Bad Hex",
        "qr_type": "text",
        "content": "Sample text",
        "foreground": "blue",
        "background": "#FFFFFF"
    })
    assert r3.status_code == 400

    # Invalid QR type
    r4 = client.post("/api/generate", json={
        "title": "Bad Type",
        "qr_type": "invalid_type",
        "content": "Sample text",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r4.status_code == 400


def test_retrieve_qr_image_dynamic(auth_client, app):
    """Verify that stored QR codes can be dynamically rendered on demand."""
    client, user_id = auth_client

    with app.app_context():
        record = QRCode(
            user_id=user_id,
            title="Dynamic Test",
            qr_type="text",
            content="Persistent Cloud Content",
            foreground="#112233",
            background="#FFFFFF"
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    img_response = client.get(f"/api/qr/{record_id}/image")
    assert img_response.status_code == 200
    assert img_response.mimetype == "image/png"
    assert len(img_response.data) > 100


def test_cross_user_isolation_prevent_access(app):
    """Verify User B cannot access User A's private QR code image."""
    with app.app_context():
        user_a = User(username="usera", email="usera@example.com")
        user_a.set_password("pass123")
        user_b = User(username="userb", email="userb@example.com")
        user_b.set_password("pass123")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        record = QRCode(
            user_id=user_a.id,
            title="User A Secret QR",
            qr_type="text",
            content="Confidential Data",
            foreground="#000000",
            background="#FFFFFF"
        )
        db.session.add(record)
        db.session.commit()
        qr_id = record.id

    # User A logs in and accesses the image
    client_a = app.test_client()
    client_a.post("/login", data={"email": "usera@example.com", "password": "pass123"}, follow_redirects=True)
    resp_a = client_a.get(f"/api/qr/{qr_id}/image")
    assert resp_a.status_code == 200

    # User B logs in and is denied access to User A's QR
    client_b = app.test_client()
    client_b.get("/logout", follow_redirects=True)
    client_b.post("/login", data={"email": "userb@example.com", "password": "pass123"}, follow_redirects=True)
    resp_b = client_b.get(f"/api/qr/{qr_id}/image")
    assert resp_b.status_code == 404


def test_public_preview_endpoint(client):
    """Verify public preview works without authentication."""
    response = client.post("/api/preview", json={
        "content": "https://example.com",
        "qr_type": "url",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert response.status_code == 200
    assert response.mimetype == "image/png"
