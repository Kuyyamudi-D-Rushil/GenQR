import io
import re
import urllib.parse
import qrcode
from flask import Blueprint, request, jsonify, send_file, url_for, current_app, render_template
from flask_login import login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.exc import SQLAlchemyError
from extensions import db, limiter
from models import QRCode

generator_bp = Blueprint("generator", __name__)

HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
PHONE_ALLOWED_CHARS_REGEX = re.compile(r"^\+?[0-9\s\-\(\)\.]{7,25}$")
MAX_QR_BYTES = 2048  # Sensible byte limit for QR Code Error Correction Level M


class QRCapacityError(Exception):
    """Raised when encoded content exceeds QR matrix capacity."""
    pass


def validate_url(raw_url: str):
    """Validate URL syntax and hostname using standard Python parsing."""
    candidate = raw_url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    try:
        parsed = urllib.parse.urlsplit(candidate)
    except Exception:
        return None, "Invalid URL structure."

    if parsed.scheme not in ("http", "https"):
        return None, "URL must use http:// or https:// protocol."

    if not parsed.netloc or not parsed.hostname:
        return None, "URL must include a valid domain or hostname."

    hostname = parsed.hostname
    if len(hostname) > 253:
        return None, "URL hostname exceeds maximum allowable domain length."

    labels = hostname.split(".")
    if not all(label and len(label) <= 63 for label in labels):
        return None, "URL hostname contains invalid domain labels."

    if len(labels) < 2 and hostname != "localhost":
        return None, "URL must include a complete domain name (e.g. example.com)."

    return candidate, None


def validate_email_content(raw_email: str):
    """Validate email syntax using email_validator."""
    clean = raw_email.strip()
    if clean.lower().startswith("mailto:"):
        clean = clean[7:].strip()

    try:
        valid = validate_email(clean, check_deliverability=False)
        return valid.normalized, None
    except (EmailNotValidError, ValueError):
        return None, "Please enter a valid email address (e.g. name@domain.com)."


def validate_phone_content(raw_phone: str):
    """Validate phone syntax and digit length according to E.164 guidelines."""
    clean = raw_phone.strip()
    if clean.lower().startswith("tel:"):
        clean = clean[4:].strip()

    if not re.fullmatch(r"^\+?[0-9\s\-\(\)\.]+$", clean):
        return None, "Phone number contains invalid characters."

    digits = re.sub(r"\D", "", clean)
    if len(digits) < 7 or len(digits) > 15:
        return None, "Phone number must contain between 7 and 15 digits."

    prefix = "+" if clean.startswith("+") else ""
    return f"{prefix}{digits}", None


def validate_input(content: str, qr_type: str, foreground: str, background: str):
    """Validate all generation parameters and semantic correctness."""
    if not content:
        return "Content is required.", None

    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_QR_BYTES:
        return f"Content exceeds maximum allowable QR data capacity ({len(content_bytes)} bytes > {MAX_QR_BYTES} bytes).", None

    if qr_type not in ["url", "text", "email", "phone"]:
        return "Invalid QR code type specified.", None

    normalized_payload = content.strip()

    if qr_type == "url":
        normalized_url, err = validate_url(content)
        if err:
            return err, None
        normalized_payload = normalized_url

    elif qr_type == "email":
        normalized_email, err = validate_email_content(content)
        if err:
            return err, None
        normalized_payload = f"mailto:{normalized_email}"

    elif qr_type == "phone":
        normalized_phone, err = validate_phone_content(content)
        if err:
            return err, None
        normalized_payload = f"tel:{normalized_phone}"

    if not HEX_COLOR_REGEX.fullmatch(foreground):
        return "Foreground color must be a valid 6-digit hex code (e.g. #000000).", None

    if not HEX_COLOR_REGEX.fullmatch(background):
        return "Background color must be a valid 6-digit hex code (e.g. #FFFFFF).", None

    if foreground.lower() == background.lower():
        return "Foreground and background colors must be different for QR scanning.", None

    return None, normalized_payload


def create_qr(payload: str, foreground: str, background: str):
    """Generate a high-quality QR code PIL image in memory safely catching capacity errors."""
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        image = qr.make_image(
            fill_color=foreground,
            back_color=background
        ).convert("RGB")
        return image
    except (qrcode.exceptions.DataOverflowError, ValueError) as e:
        raise QRCapacityError("Content exceeds QR code data capacity.") from e
    except Exception as e:
        raise QRCapacityError(f"Failed to generate QR code: {str(e)}") from e


@generator_bp.route("/generate", methods=["GET"])
@login_required
def generate_page():
    """Dedicated standalone QR Code Generator studio page."""
    return render_template("generator.html")


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

    # Validate parameters and semantic content
    error_msg, formatted_payload = validate_input(raw_content, qr_type, foreground, background)
    if error_msg:
        return jsonify({"error": error_msg}), 400

    # Render image in memory first to verify capacity before database commit
    try:
        image = create_qr(formatted_payload, foreground, background)
    except QRCapacityError as e:
        return jsonify({"error": str(e)}), 400

    # Persist in cloud PostgreSQL / SQLite with rollback error handling
    qr_record = QRCode(
        user_id=current_user.id,
        title=title[:150] if title else "My QR Code",
        qr_type=qr_type,
        content=raw_content,  # Store user-entered content for human display
        foreground=foreground,
        background=background,
    )

    try:
        db.session.add(qr_record)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception("Database error saving QR record: %s", str(e))
        return jsonify({"error": "Failed to save QR code due to a database error."}), 500

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
@limiter.limit("20 per minute")
def preview():
    """Public instant preview endpoint with IP rate limiting and capacity protection."""
    data = request.get_json(silent=True) or {}
    raw_content = str(data.get("content", "")).strip()
    qr_type = str(data.get("qr_type", "text")).strip().lower()
    foreground = str(data.get("foreground", "#000000")).strip()
    background = str(data.get("background", "#FFFFFF")).strip()

    if not raw_content:
        raw_content = "https://cloud-qr-generator.onrender.com"

    error_msg, formatted_payload = validate_input(raw_content, qr_type, foreground, background)
    if error_msg:
        return jsonify({"error": error_msg}), 400

    try:
        image = create_qr(formatted_payload, foreground, background)
    except QRCapacityError as e:
        return jsonify({"error": str(e)}), 400

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

    # Re-normalize payload
    _, formatted_payload = validate_input(record.content, record.qr_type, record.foreground, record.background)
    if not formatted_payload:
        formatted_payload = record.content

    try:
        image = create_qr(
            formatted_payload,
            record.foreground,
            record.background
        )
    except QRCapacityError as e:
        return jsonify({"error": str(e)}), 400

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

    _, formatted_payload = validate_input(record.content, record.qr_type, record.foreground, record.background)
    if not formatted_payload:
        formatted_payload = record.content

    try:
        image = create_qr(
            formatted_payload,
            record.foreground,
            record.background
        )
    except QRCapacityError as e:
        return jsonify({"error": str(e)}), 400

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
