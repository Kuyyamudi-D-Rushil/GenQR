import io
import re
import qrcode
from flask import Blueprint, request, jsonify, send_file, url_for
from flask_login import login_required, current_user
from extensions import db
from models import QRCode

generator_bp = Blueprint("generator", __name__)

HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-\(\)\.]{7,25}$")


def format_qr_content(content: str, qr_type: str) -> str:
    """Format and normalize content according to QR code standards."""
    clean_content = content.strip()

    if qr_type == "url":
        if not clean_content.startswith(("http://", "https://")):
            return f"https://{clean_content}"
        return clean_content

    if qr_type == "email":
        if not clean_content.startswith("mailto:"):
            return f"mailto:{clean_content}"
        return clean_content

    if qr_type == "phone":
        if not clean_content.startswith("tel:"):
            # Strip spaces/formatting characters for the tel URI
            digits_only = re.sub(r"[^\d+]", "", clean_content)
            return f"tel:{digits_only}"
        return clean_content

    # Plain text
    return clean_content


def validate_input(content: str, qr_type: str, foreground: str, background: str):
    """Validate all generation parameters."""
    if not content or len(content) > 2048:
        return "Content is required and must not exceed 2048 characters."

    if qr_type not in ["url", "text", "email", "phone"]:
        return "Invalid QR code type specified."

    if qr_type == "phone":
        if not PHONE_REGEX.match(content.strip()):
            return "Please enter a valid phone number format (e.g. +1 555-123-4567)."

    if not HEX_COLOR_REGEX.fullmatch(foreground):
        return "Foreground color must be a valid 6-digit hex code (e.g. #000000)."

    if not HEX_COLOR_REGEX.fullmatch(background):
        return "Background color must be a valid 6-digit hex code (e.g. #FFFFFF)."

    if foreground.lower() == background.lower():
        return "Foreground and background colors must be different for QR scanning."

    return None


def create_qr(payload: str, foreground: str, background: str):
    """Generate a high-quality QR code PIL image in memory."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    # Make image with requested colors
    image = qr.make_image(
        fill_color=foreground,
        back_color=background
    ).convert("RGB")
    return image


@generator_bp.route("/api/generate", methods=["POST"])
@login_required
def generate():
    """Generate a QR code, persist record in cloud database, and return PNG image."""
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    raw_content = str(data.get("content", "")).strip()
    qr_type = str(data.get("qr_type", "text")).strip().lower()
    title = str(data.get("title", "My QR Code")).strip()
    foreground = str(data.get("foreground", "#000000")).strip()
    background = str(data.get("background", "#FFFFFF")).strip()

    # Validate parameters
    error_msg = validate_input(raw_content, qr_type, foreground, background)
    if error_msg:
        return jsonify({"error": error_msg}), 400

    # Format content for QR standard
    formatted_payload = format_qr_content(raw_content, qr_type)

    # Persist in cloud PostgreSQL / SQLite
    qr_record = QRCode(
        user_id=current_user.id,
        title=title[:150] if title else "My QR Code",
        qr_type=qr_type,
        content=raw_content,  # Store raw content for human display
        foreground=foreground,
        background=background,
    )
    db.session.add(qr_record)
    db.session.commit()

    # Render image in memory
    image = create_qr(formatted_payload, foreground, background)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    # If JSON response requested
    if request.args.get("format") == "json" or request.headers.get("Accept") == "application/json":
        return jsonify({
            "success": True,
            "id": qr_record.id,
            "title": qr_record.title,
            "qr_type": qr_record.qr_type,
            "content": qr_record.content,
            "image_url": url_for("generator.get_qr_image", qr_id=qr_record.id),
            "created_at": qr_record.created_at.isoformat()
        })

    # Return binary PNG stream with metadata headers
    response = send_file(
        output,
        mimetype="image/png",
        as_attachment=False,
        download_name="qr_code.png"
    )
    response.headers["X-QR-ID"] = str(qr_record.id)
    response.headers["X-QR-Title"] = qr_record.title
    return response


@generator_bp.route("/api/preview", methods=["POST"])
def preview():
    """Public instant preview endpoint without database persistence."""
    data = request.get_json(silent=True) or {}
    raw_content = str(data.get("content", "")).strip()
    qr_type = str(data.get("qr_type", "text")).strip().lower()
    foreground = str(data.get("foreground", "#000000")).strip()
    background = str(data.get("background", "#FFFFFF")).strip()

    if not raw_content:
        raw_content = "https://cloud-qr-generator.onrender.com"

    error_msg = validate_input(raw_content, qr_type, foreground, background)
    if error_msg:
        return jsonify({"error": error_msg}), 400

    formatted_payload = format_qr_content(raw_content, qr_type)
    image = create_qr(formatted_payload, foreground, background)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return send_file(output, mimetype="image/png")


@generator_bp.route("/api/qr/<int:qr_id>/image")
@login_required
def get_qr_image(qr_id: int):
    """Regenerate and retrieve QR image on-the-fly from stored database record."""
    record = QRCode.query.filter_by(
        id=qr_id,
        user_id=current_user.id
    ).first_or_404()

    formatted_payload = format_qr_content(record.content, record.qr_type)
    image = create_qr(
        formatted_payload,
        record.foreground,
        record.background
    )

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return send_file(output, mimetype="image/png")


@generator_bp.route("/api/qr/<int:qr_id>/download")
@login_required
def download_qr(qr_id: int):
    """Download saved QR image as PNG attachment."""
    record = QRCode.query.filter_by(
        id=qr_id,
        user_id=current_user.id
    ).first_or_404()

    formatted_payload = format_qr_content(record.content, record.qr_type)
    image = create_qr(
        formatted_payload,
        record.foreground,
        record.background
    )

    safe_title = re.sub(r"[^\w\-_\. ]", "_", record.title).strip().replace(" ", "_")
    filename = f"{safe_title or 'qr_code'}.png"

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return send_file(
        output,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename
    )
