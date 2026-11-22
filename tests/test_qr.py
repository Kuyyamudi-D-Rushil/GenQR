from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
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


def test_semantic_url_validation(auth_client):
    """Verify semantic URL validation rules."""
    client, _ = auth_client

    # Valid domain without scheme auto-prepends https://
    r1 = client.post("/api/generate", json={
        "qr_type": "url",
        "content": "mywebsite.com/docs",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r1.status_code == 200

    # Disallow unsupported protocols
    r2 = client.post("/api/generate", json={
        "qr_type": "url",
        "content": "ftp://files.example.com",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r2.status_code == 400
    assert "protocol" in r2.get_json()["error"]

    # Disallow missing hostname
    r3 = client.post("/api/generate", json={
        "qr_type": "url",
        "content": "https://",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r3.status_code == 400

    # Disallow invalid domain structure
    r4 = client.post("/api/generate", json={
        "qr_type": "url",
        "content": "not_a_valid_url",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r4.status_code == 400


def test_semantic_email_validation(auth_client):
    """Verify semantic email validation using email_validator."""
    client, _ = auth_client

    # Valid email
    r1 = client.post("/api/generate", json={
        "qr_type": "email",
        "content": "contact@business.org",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r1.status_code == 200

    # Malformed email
    r2 = client.post("/api/generate", json={
        "qr_type": "email",
        "content": "invalid-email-address",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r2.status_code == 400
    assert "valid email" in r2.get_json()["error"]


def test_semantic_phone_validation(auth_client):
    """Verify phone formatting and digit range validation."""
    client, _ = auth_client

    # Valid phone number
    r1 = client.post("/api/generate", json={
        "qr_type": "phone",
        "content": "+1 (555) 234-5678",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r1.status_code == 200

    # Too short (< 7 digits)
    r2 = client.post("/api/generate", json={
        "qr_type": "phone",
        "content": "12345",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r2.status_code == 400
    assert "between 7 and 15 digits" in r2.get_json()["error"]

    # Letters in phone
    r3 = client.post("/api/generate", json={
        "qr_type": "phone",
        "content": "+1 800 CALL ME",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert r3.status_code == 400


def test_oversized_unicode_capacity_overflow(auth_client):
    """Verify oversized Unicode/emoji content returns HTTP 400 capacity error instead of HTTP 500."""
    client, _ = auth_client

    # 700 emojis * 4 bytes each = 2800 bytes (exceeds 2048-byte QR capacity)
    oversized_emojis = "🎉" * 700

    response = client.post("/api/generate", json={
        "title": "Overflow Test",
        "qr_type": "text",
        "content": oversized_emojis,
        "foreground": "#000000",
        "background": "#FFFFFF"
    })

    assert response.status_code == 400
    err_json = response.get_json()
    assert "capacity" in err_json["error"].lower()


def test_generate_db_error_rollback(auth_client):
    """Verify database errors during QR save roll back and return JSON 500."""
    client, _ = auth_client

    with patch("extensions.db.session.commit", side_effect=SQLAlchemyError("Simulated DB failure")):
        response = client.post("/api/generate", json={
            "title": "DB Failure QR",
            "qr_type": "text",
            "content": "Valid text content",
            "foreground": "#000000",
            "background": "#FFFFFF"
        })

        assert response.status_code == 500
        assert "database error" in response.get_json()["error"].lower()


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
    assert "different" in r2.get_json()["error"].lower()

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
        user_a.set_password("SecurePassword123!")
        user_b = User(username="userb", email="userb@example.com")
        user_b.set_password("SecurePassword123!")
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
    client_a.post("/login", data={"email": "usera@example.com", "password": "SecurePassword123!"}, follow_redirects=True)
    resp_a = client_a.get(f"/api/qr/{qr_id}/image")
    assert resp_a.status_code == 200

    # User B logs in and is denied access to User A's QR
    client_b = app.test_client()
    client_b.post("/logout", follow_redirects=True)
    client_b.post("/login", data={"email": "userb@example.com", "password": "SecurePassword123!"}, follow_redirects=True)
    resp_b = client_b.get(f"/api/qr/{qr_id}/image")
    assert resp_b.status_code == 404


def test_public_preview_endpoint(client):
    """Verify public preview works without authentication and validates content."""
    response = client.post("/api/preview", json={
        "content": "https://example.com",
        "qr_type": "url",
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def decode_qr_png_bytes(png_bytes: bytes) -> str:
    """Decode raw PNG image bytes using OpenCV QRCodeDetector."""
    import cv2
    import numpy as np

    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert img is not None, "Failed to decode PNG image buffer with OpenCV"
    detector = cv2.QRCodeDetector()
    decoded_value, _, _ = detector.detectAndDecode(img)
    return decoded_value


def test_qr_decoding_verification_url(auth_client):
    """Verify generated URL QR code contains valid 2D matrix modules matching source URL."""
    client, _ = auth_client
    target_url = "https://example.com/cloud-computing-project"

    resp = client.post("/api/generate", json={
        "title": "Decoded URL Test",
        "qr_type": "url",
        "content": target_url,
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"

    decoded_text = decode_qr_png_bytes(resp.data)
    assert decoded_text == target_url


def test_qr_decoding_verification_text(auth_client):
    """Verify generated plain text QR code decodes back to original string."""
    client, _ = auth_client
    raw_text = "Cloud-Native QR Matrix Verification 2026"

    resp = client.post("/api/generate", json={
        "title": "Decoded Text Test",
        "qr_type": "text",
        "content": raw_text,
        "foreground": "#059669",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200

    decoded_text = decode_qr_png_bytes(resp.data)
    assert decoded_text == raw_text


def test_qr_decoding_verification_email(auth_client):
    """Verify generated email QR code decodes to normalized mailto scheme."""
    client, _ = auth_client

    resp = client.post("/api/generate", json={
        "title": "Decoded Email Test",
        "qr_type": "email",
        "content": "contact@organization.org",
        "foreground": "#4F46E5",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200

    decoded_text = decode_qr_png_bytes(resp.data)
    assert decoded_text == "mailto:contact@organization.org"


def test_qr_decoding_verification_phone(auth_client):
    """Verify generated phone QR code decodes to normalized tel scheme."""
    client, _ = auth_client

    resp = client.post("/api/generate", json={
        "title": "Decoded Phone Test",
        "qr_type": "phone",
        "content": "+1 (555) 867-5309",
        "foreground": "#DC2626",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200

    decoded_text = decode_qr_png_bytes(resp.data)
    assert decoded_text == "tel:+15558675309"


def test_generator_page_access(auth_client):
    """Verify access controls on the dedicated /generate studio page."""
    auth_c, _ = auth_client

    # Authenticated user can open generator studio
    auth_resp = auth_c.get("/generate")
    assert auth_resp.status_code == 200
    assert b"QR Code Generation Studio" in auth_resp.data
    assert b"Configure QR Parameters" in auth_resp.data

    # Log out and verify unauthenticated user redirected to login
    auth_c.post("/logout", follow_redirects=True)
    unauth_resp = auth_c.get("/generate")
    assert unauth_resp.status_code == 302
    assert "/login" in unauth_resp.headers["Location"]


def test_generate_and_decode_google_url(auth_client):
    """Verify entering https://www.google.com encodes, downloads, and decodes to exact URL."""
    client, _ = auth_client
    target_url = "https://www.google.com"

    # Step 1: Generate QR Code
    resp = client.post("/api/generate", json={
        "title": "Google Official Portal",
        "qr_type": "url",
        "content": target_url,
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    assert "X-QR-ID" in resp.headers
    qr_id = int(resp.headers["X-QR-ID"])

    # Step 2: Decode the immediate response PNG
    immediate_decoded = decode_qr_png_bytes(resp.data)
    assert immediate_decoded == target_url, f"Expected {target_url}, but decoded {immediate_decoded}"

    # Step 3: Download the generated PNG via /api/qr/<id>/download and independently decode it
    download_resp = client.get(f"/api/qr/{qr_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.mimetype == "image/png"
    downloaded_decoded = decode_qr_png_bytes(download_resp.data)
    assert downloaded_decoded == target_url, f"Downloaded QR decoded {downloaded_decoded} instead of {target_url}"

    # Step 4: Retrieve the history/preview image via /api/qr/<id>/image and independently decode it
    image_resp = client.get(f"/api/qr/{qr_id}/image")
    assert image_resp.status_code == 200
    image_decoded = decode_qr_png_bytes(image_resp.data)
    assert image_decoded == target_url, f"History image decoded {image_decoded} instead of {target_url}"


def test_generate_and_decode_different_url(auth_client):
    """Verify entering a different URL encodes, downloads, and decodes accurately."""
    client, _ = auth_client
    target_url = "https://en.wikipedia.org/wiki/Cloud_computing"

    resp = client.post("/api/generate", json={
        "title": "Wikipedia Cloud Computing",
        "qr_type": "url",
        "content": target_url,
        "foreground": "#1E40AF",
        "background": "#F0F9FF"
    })
    assert resp.status_code == 200
    qr_id = int(resp.headers["X-QR-ID"])

    # Decode download
    download_resp = client.get(f"/api/qr/{qr_id}/download")
    assert download_resp.status_code == 200
    downloaded_decoded = decode_qr_png_bytes(download_resp.data)
    assert downloaded_decoded == target_url, f"Expected {target_url}, got {downloaded_decoded}"


def test_generate_and_decode_plain_text_message(auth_client):
    """Verify plain text message encodes, downloads, and decodes without URL corruption."""
    client, _ = auth_client
    raw_message = "Project Verification: Cloud-Based QR Generator 2026 Genuine Output"

    resp = client.post("/api/generate", json={
        "title": "Verification Text Memo",
        "qr_type": "text",
        "content": raw_message,
        "foreground": "#047857",
        "background": "#ECFDF5"
    })
    assert resp.status_code == 200
    qr_id = int(resp.headers["X-QR-ID"])

    download_resp = client.get(f"/api/qr/{qr_id}/download")
    assert download_resp.status_code == 200
    downloaded_decoded = decode_qr_png_bytes(download_resp.data)
    assert downloaded_decoded == raw_message, f"Expected {raw_message}, got {downloaded_decoded}"


def test_generate_safety_swap_url_in_title(auth_client):
    """Verify backend safety swap if user enters target URL into title and leaves content empty."""
    client, _ = auth_client
    target_url = "https://www.google.com"

    resp = client.post("/api/generate", json={
        "title": target_url,  # User mistakenly entered URL in title
        "qr_type": "url",
        "content": "",        # Empty content
        "foreground": "#000000",
        "background": "#FFFFFF"
    })
    assert resp.status_code == 200
    qr_id = int(resp.headers["X-QR-ID"])

    download_resp = client.get(f"/api/qr/{qr_id}/download")
    assert download_resp.status_code == 200
    downloaded_decoded = decode_qr_png_bytes(download_resp.data)
    assert downloaded_decoded == target_url



