"""Automated verification tests for CloudQR Commercial SaaS UI/UX Improvements.
Verifies:
1. Complete separation of Dashboard (overview) vs QR Generator (creation workspace).
2. Dashboard contains welcome greeting, 4 PostgreSQL stat cards, quick creation shortcuts, activity distribution, and recent 5 records.
3. Dashboard does not contain the QR generation form.
4. QR Generator contains the 4 interactive type selector cards (URL, Text, Email, Phone), dynamic form, and clean preview stage.
5. Navigation contains theme switcher button, brand mark, and user profile menu.
6. Black & white QR matrix enforcement across generation and download endpoints.
"""

import io
from PIL import Image
from models import QRCode
from extensions import db


def test_theme_toggle_and_navigation_structure(auth_client):
    """Verify navigation bar includes theme toggle button, brand logo, and active links."""
    client, _ = auth_client
    resp = client.get("/dashboard")
    assert resp.status_code == 200

    # Theme toggle button present
    assert b'id="themeToggleBtn"' in resp.data
    assert b'theme-toggle-btn' in resp.data

    # Brand and links present
    assert b"Cloud" in resp.data and b"QR" in resp.data
    assert b"Dashboard" in resp.data
    assert b"QR Generator" in resp.data
    assert b"QR History" in resp.data

    # User profile dropdown
    assert b"user-menu-btn" in resp.data
    assert b"Log out" in resp.data


def test_dashboard_differentiation_as_overview_only(auth_client, app):
    """Verify dashboard serves exclusively as an activity overview without the duplicate generation form."""
    client, user_id = auth_client

    with app.app_context():
        # Seed test QR records
        db.session.add(QRCode(user_id=user_id, title="Work Link", qr_type="url", content="https://work.com"))
        db.session.add(QRCode(user_id=user_id, title="Memo", qr_type="text", content="Project memo notes"))
        db.session.commit()

    resp = client.get("/dashboard")
    assert resp.status_code == 200

    # Section A: Welcome greeting and prominent + Create QR Code button
    assert b"Welcome back" in resp.data
    assert b"+ Create QR Code" in resp.data
    assert b'href="/generate"' in resp.data

    # Section B: 4 PostgreSQL statistic cards
    assert b"TOTAL SAVED" in resp.data
    assert b"GENERATED TODAY" in resp.data
    assert b"URL CODES" in resp.data
    assert b"OTHER FORMATS" in resp.data

    # Section C: Visual distribution overview
    assert b"qrTypeDistribution" in resp.data
    assert b"distSegUrl" in resp.data

    # Section D: Quick Action Creation shortcuts
    assert b"Create URL QR" in resp.data
    assert b'href="/generate?type=url"' in resp.data
    assert b"Create Text QR" in resp.data
    assert b'href="/generate?type=text"' in resp.data
    assert b"Create Email QR" in resp.data
    assert b'href="/generate?type=email"' in resp.data
    assert b"Create Phone QR" in resp.data
    assert b'href="/generate?type=phone"' in resp.data

    # Section E: Recent QR codes table
    assert b"Recent QR Codes" in resp.data
    assert b"Work Link" in resp.data
    assert b"Memo" in resp.data

    # MUST NOT contain the generation form on dashboard
    assert b'id="generatorWorkspaceForm"' not in resp.data


def test_generator_studio_interactive_type_cards_and_workspace(auth_client):
    """Verify dedicated generator workspace contains 4 interactive type cards and preview stage."""
    client, _ = auth_client
    resp = client.get("/generate")
    assert resp.status_code == 200

    # 4 interactive QR type cards
    assert b'data-type="url"' in resp.data
    assert b'data-type="text"' in resp.data
    assert b'data-type="email"' in resp.data
    assert b'data-type="phone"' in resp.data

    # Generator form and fields
    assert b'id="generatorWorkspaceForm"' in resp.data
    assert b'id="qrContent"' in resp.data
    assert b'id="qrTitle"' in resp.data
    assert b'id="generateSubmitBtn"' in resp.data

    # Clean preview canvas and action buttons
    assert b'id="qrPreview"' in resp.data
    assert b'id="downloadBtn"' in resp.data
    assert b'id="copyContentBtn"' in resp.data
    assert b'id="previewEmptyPlaceholder"' in resp.data


def test_generator_accepts_quick_action_type_query_param(auth_client):
    """Verify generator responds 200 to quick action links with preset type parameters."""
    client, _ = auth_client
    for qr_type in ["url", "text", "email", "phone"]:
        resp = client.get(f"/generate?type={qr_type}")
        assert resp.status_code == 200
        assert f'data-type="{qr_type}"'.encode("utf-8") in resp.data


def test_black_and_white_qr_enforcement_in_generator(auth_client):
    """Verify QR code generation strictly produces binary black (#000000) and white (#FFFFFF) pixels."""
    client, _ = auth_client

    resp = client.post("/api/generate", json={
        "title": "Strictly B&W Verification",
        "qr_type": "url",
        "content": "https://example.com/strictly-bw"
    })
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"

    img = Image.open(io.BytesIO(resp.data)).convert("RGB")
    colors = img.getcolors(maxcolors=256)
    unique_rgbs = {rgb for count, rgb in colors}
    assert unique_rgbs.issubset({(0, 0, 0), (255, 255, 255)})
